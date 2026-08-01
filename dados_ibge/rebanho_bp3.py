# -*- coding: utf-8 -*-
"""
Efetivo de suinos e galinaceos por municipio da BP3, do IBGE.

Por que existe: no modelo ajustado do gradiente de saneamento, PIB per capita
saiu associado a MAIS internacao por doenca intestinal (razao 2,03, p=0,018),
o que e contraintuitivo e ficou como pendencia.

Colinearidade nao explica — o VIF dos preditores fica entre 1,3 e 1,5. E os
extremos de PIB per capita na bacia sao Cafelandia (R$ 138 mil, sede da
Copacol) e Palotina (R$ 105 mil, sede da BRF). Nesses municipios o PIB per
capita nao mede renda das familias: mede producao agroindustrial.

A hipotese que este modulo permite testar: o coeficiente do PIB esta captando
intensidade pecuaria. O oeste do Parana tem uma das maiores densidades de
suinos e aves do pais, e dejeto animal e fonte documentada de contaminacao
hidrica. Palotina tem 7,1 milhoes de galinaceos e 63 mil suinos para 35 mil
habitantes.

Se a densidade de rebanho explicar o sinal do PIB, a pendencia deixa de ser
ruido de modelo e vira mecanismo.

Fonte: SIDRA/IBGE tabela 3939, Pesquisa Pecuaria Municipal, efetivo dos
rebanhos em 31/12, anual.

Limites
  - efetivo e estoque no fim do ano, nao producao no ano; para aves de corte,
    que tem ciclo de ~45 dias, subestima muito o volume anual de dejeto
  - a PPM nao diz o que e feito do dejeto; municipio com muito suino e boa
    gestao de chorume nao e igual a municipio com a mesma densidade e nenhuma
  - suino e ave produzem dejetos diferentes: liquido e solido. Ficam em
    colunas separadas em vez de somados em unidade animal, para nao embutir
    uma equivalencia que nao vale para escorrimento.

Saida
  dados/rebanho_bp3.csv
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
CONTEXTO = RAIZ / "dados" / "contexto_bp3.csv"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = RAIZ / "dados" / "rebanho_bp3.csv"

SIDRA = ("https://apisidra.ibge.gov.br/values/t/3939/n6/{cod}/p/all"
         "/v/105/c79/all")

INTERESSE = {"Suíno - total": "suinos", "Galináceos - total": "galinaceos"}


def _baixa(cod: int) -> list[dict]:
    destino = BRUTO / f"ppm_{cod}.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    with urllib.request.urlopen(SIDRA.format(cod=cod), timeout=180) as resp:
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
        cod = int(m["cod_ibge"])
        for r in _baixa(cod)[1:]:
            rotulo = INTERESSE.get(str(r.get("D4N", "")).strip())
            if not rotulo:
                continue
            try:
                ano, valor = int(r["D2N"]), int(r["V"])
            except (ValueError, TypeError, KeyError):
                continue        # "-" significa zero ou nao informado
            linhas.append({"cod_ibge": cod, "ano": ano,
                           "rebanho": rotulo, "cabecas": valor})
        time.sleep(0.2)

    d = (pd.DataFrame(linhas)
         .pivot_table(index=["cod_ibge", "ano"], columns="rebanho",
                      values="cabecas", fill_value=0)
         .reset_index())

    ctx = pd.read_csv(CONTEXTO)[["cod_ibge", "municipio", "ano", "area_km2",
                                 "populacao"]]
    d = ctx.merge(d, on=["cod_ibge", "ano"], how="left")

    # anos sem PPM publicada repetem o ultimo disponivel
    d = d.sort_values(["cod_ibge", "ano"])
    for c in ["suinos", "galinaceos"]:
        d[c] = d.groupby("cod_ibge")[c].ffill().bfill()

    d["suinos_km2"] = (d["suinos"] / d["area_km2"]).round(2)
    d["galinaceos_km2"] = (d["galinaceos"] / d["area_km2"]).round(1)
    d["suinos_hab"] = (d["suinos"] / d["populacao"]).round(3)
    d["galinaceos_hab"] = (d["galinaceos"] / d["populacao"]).round(1)

    d.to_csv(SAIDA, index=False)

    x = d[d["ano"] == 2023]
    print(f"BP3 em 2023: {int(x['suinos'].sum()):,} suinos e "
          f"{int(x['galinaceos'].sum()):,} galinaceos")
    print(f"para {int(x['populacao'].sum()):,} habitantes")
    print()
    print("maiores densidades de suino por km2:")
    print(x.nlargest(5, "suinos_km2")[["municipio", "suinos_km2",
                                       "galinaceos_km2", "suinos_hab"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
