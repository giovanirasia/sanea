# -*- coding: utf-8 -*-
"""
Estrutura etaria dos municipios, do Censo 2022.

Por que existe: no modelo do gradiente de saneamento, densidade demografica
foi a unica variavel robusta nas duas escalas — 0,564 na BP3 e 0,712 no Parana
inteiro, ambas com p pequeno. Municipio menos denso interna mais por doenca
intestinal, e isso nao e explicado por saneamento, renda nem tendencia.

Densidade entrou como controle de ruralidade, nao como hipotese. Antes de
tratar isso como achado, e preciso saber o que ela esta medindo.

Uma explicacao nao serve: acesso a servico. Se fosse acesso, o sinal seria o
oposto — mais longe do hospital significa MENOS internacao registrada, nao
mais. O efeito ser protetor com a densidade implica que a carga real no rural
e ainda maior que a medida.

A hipotese que este modulo permite testar e composicao etaria. Internacao por
A00-A09 concentra-se em crianca pequena e idoso (a mediana de idade desses
casos e 22,5 anos, contra 46 do total de internacoes), e o interior do Parana
envelheceu muito com a saida dos jovens. Se municipios menos densos tem mais
idosos, parte do efeito da densidade e demografia, nao saneamento nem ambiente.

Fonte: SIDRA/IBGE tabela 9514, Censo 2022, populacao por grupos quinquenais.

Limites
  - o Censo 2022 e um ponto no tempo, aplicado a um painel de 2008 a 2026. O
    envelhecimento e progressivo, entao a variavel descreve melhor o fim da
    serie que o comeco.
  - a tabela traz grupos quinquenais e idades simples ao mesmo tempo; aqui so
    os quinquenais sao somados, para nao contar duas vezes

Saida
  dados/idade_{escopo}.csv
"""

from __future__ import annotations

import gzip
import json
import os
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

ESCOPO = os.environ.get("SANEA_ESCOPO", "bp3")
if ESCOPO not in ("bp3", "parana"):
    raise SystemExit(f"SANEA_ESCOPO invalido: {ESCOPO}")

MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = RAIZ / "dados" / f"idade_{ESCOPO}.csv"

SIDRA = ("https://apisidra.ibge.gov.br/values/t/9514/n6/{cod}/v/93/p/2022"
         "/c287/all/c2/6794/c286/113635")

# rotulo de grupo quinquenal: "0 a 4 anos" ... "95 a 99 anos", "100 anos ou mais"
QUINQUENAL = re.compile(r"^(\d+) a (\d+) anos$")


def _baixa(cod: int) -> list[dict]:
    destino = BRUTO / f"idade_{cod}.json"
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


def perfil(cod: int) -> dict | None:
    """Populacao por faixa agregada. Soma so os grupos quinquenais."""
    total = criancas = idosos = adultos = pop_grupos = 0

    for r in _baixa(cod)[1:]:
        rotulo = str(r.get("D4N", "")).strip()
        valor = r.get("V")
        if not str(valor).isdigit():
            continue
        valor = int(valor)

        if rotulo == "Total":
            total = valor
            continue
        if rotulo == "100 anos ou mais":
            idosos += valor
            pop_grupos += valor
            continue
        m = QUINQUENAL.match(rotulo)
        if not m:
            continue                       # idade simples: ignorada
        inicio = int(m.group(1))
        pop_grupos += valor
        if inicio == 0:
            criancas += valor              # 0 a 4 anos
        if 20 <= inicio < 60:
            adultos += valor               # 20 a 59: o controle negativo
        if inicio >= 60:
            idosos += valor

    if not pop_grupos:
        return None
    return {"cod_ibge": cod, "pop_censo": total or pop_grupos,
            "pct_0a4": round(100 * criancas / pop_grupos, 2),
            "pct_20a59": round(100 * adultos / pop_grupos, 2),
            "pct_60mais": round(100 * idosos / pop_grupos, 2)}


def main() -> None:
    mun = pd.read_csv(MUNICIPIOS)
    linhas = []
    for _, m in mun.iterrows():
        p = perfil(int(m["cod_ibge"]))
        if p:
            p["municipio"] = m["municipio"]
            linhas.append(p)
        time.sleep(0.2)

    d = pd.DataFrame(linhas)[["cod_ibge", "municipio", "pop_censo",
                              "pct_0a4", "pct_20a59", "pct_60mais"]]
    d.to_csv(SAIDA, index=False)

    print(f"{ESCOPO}: {len(d)} municipios")
    print(f"  % 60 ou mais: mediana {d['pct_60mais'].median():.1f}, "
          f"de {d['pct_60mais'].min():.1f} a {d['pct_60mais'].max():.1f}")
    print(f"  % 0 a 4 anos: mediana {d['pct_0a4'].median():.1f}, "
          f"de {d['pct_0a4'].min():.1f} a {d['pct_0a4'].max():.1f}")


if __name__ == "__main__":
    main()
