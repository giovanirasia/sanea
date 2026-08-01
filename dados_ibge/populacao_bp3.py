# -*- coding: utf-8 -*-
"""
Populacao anual dos municipios da Bacia Parana 3, do IBGE.

Por que existe: o modelo estratificado usa offset log(total de internacoes),
o que mede PROPORCAO de internacoes que sao diarreicas, nao incidencia. No
corte transversal isso e perigoso: municipio pequeno e sem rede tende a ter
menos internacao por causa complexa — cirurgia eletiva, oncologia, cardiologia
— porque quem precisa disso e atendido em Cascavel ou Toledo. Se o denominador
encolhe por falta de acesso a alta complexidade, a proporcao de diarreia sobe
sem que ninguem a mais tenha adoecido.

Com populacao no denominador a medida vira incidencia por habitante, que nao
tem esse vies. Se o gradiente de 3,2x sobreviver a troca, ele fica solido.

Fonte: SIDRA/IBGE, tabela 6579 (populacao residente estimada), anual.

Limites
  - a tabela nao cobre todos os anos: em ano de Censo o IBGE publica o Censo,
    nao estimativa. Os buracos sao preenchidos por interpolacao linear.
  - a serie do SIH vai ate 2026 e a tabela para em 2025; 2026 repete 2025.
    Sao 5 meses de 2026 sobre 221, entao o efeito e pequeno, mas esta aqui
    declarado em vez de escondido.

Saida
  dados/populacao_bp3.csv
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = RAIZ / "dados" / "populacao_bp3.csv"

SIDRA = "https://apisidra.ibge.gov.br/values/t/6579/n6/{cod}/p/all"
ANO_INICIO, ANO_FIM = 2008, 2026


def _baixa(cod: int) -> list[dict]:
    destino = BRUTO / f"pop_{cod}.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    with urllib.request.urlopen(SIDRA.format(cod=cod), timeout=120) as resp:
        dados = resp.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    bruto = dados.decode("utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(bruto, encoding="utf-8")
    return json.loads(bruto)


def main() -> None:
    mun = pd.read_csv(MUNICIPIOS)
    linhas = []

    for _, m in mun.iterrows():
        registros = _baixa(int(m["cod_ibge"]))
        for r in registros[1:]:          # a primeira linha e o cabecalho
            try:
                ano, valor = int(r["D2N"]), int(r["V"])
            except (ValueError, TypeError, KeyError):
                continue
            linhas.append({"cod_ibge": int(m["cod_ibge"]),
                           "municipio": m["municipio"],
                           "ano": ano, "populacao": valor})
        time.sleep(0.2)

    d = pd.DataFrame(linhas)
    anos_ibge = sorted(d["ano"].unique())

    # completa a grade ano x municipio e interpola os buracos
    grade = pd.MultiIndex.from_product(
        [sorted(d["cod_ibge"].unique()), range(ANO_INICIO, ANO_FIM + 1)],
        names=["cod_ibge", "ano"]).to_frame(index=False)
    d = grade.merge(d, on=["cod_ibge", "ano"], how="left")
    d["municipio"] = d.groupby("cod_ibge")["municipio"].ffill().bfill()
    d["populacao"] = (d.groupby("cod_ibge")["populacao"]
                      .transform(lambda s: s.interpolate().ffill().bfill())
                      .round().astype(int))

    d = d.sort_values(["municipio", "ano"]).reset_index(drop=True)
    d.to_csv(SAIDA, index=False)

    faltantes = [a for a in range(ANO_INICIO, ANO_FIM + 1) if a not in anos_ibge]
    print(f"anos publicados pelo IBGE no intervalo: "
          f"{[a for a in anos_ibge if ANO_INICIO <= a <= ANO_FIM]}")
    print(f"anos preenchidos por interpolacao/repeticao: {faltantes}")
    print()
    tot = d.groupby("ano")["populacao"].sum()
    print(f"populacao total da BP3: {tot.iloc[0]:,} em {tot.index[0]} -> "
          f"{tot.iloc[-1]:,} em {tot.index[-1]}")
    print()
    print("maiores e menores em 2024:")
    x = d[d["ano"] == 2024].sort_values("populacao", ascending=False)
    print(x.head(3)[["municipio", "populacao"]].to_string(index=False))
    print(x.tail(3)[["municipio", "populacao"]].to_string(index=False))


if __name__ == "__main__":
    main()
