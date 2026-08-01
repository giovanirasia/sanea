# -*- coding: utf-8 -*-
"""
Contexto socioeconomico e territorial dos municipios da BP3: PIB per capita e
densidade demografica.

Por que existe: o gradiente de 4,7x entre municipios sem rede de esgoto e
municipios com cobertura alta e uma correlacao bruta. A objecao imediata e que
municipios sem rede sao menores, mais rurais e mais pobres — e que o gradiente
mede pobreza, nao saneamento. Sem controlar isso, o numero nao aguenta
pergunta.

Fontes
  PIB       SIDRA tabela 5938, PIB municipal a precos correntes, anual
  populacao dados/populacao_bp3.csv (SIDRA tabela 6579)
  area      calculada da malha municipal ja em cache de clima/bp3.py

Por que densidade e nao taxa de urbanizacao
  A tabela 4709 do Censo 2022 traz populacao, variacao e taxa de crescimento,
  mas nao a divisao urbano/rural. Densidade e proxy de ruralidade, nao a
  mesma coisa que grau de urbanizacao — esta declarado aqui para nao ser lido
  como se fosse.

Metodo da area
  Projecao local equivalente: x = R*lon*cos(lat_media), y = R*lat, depois
  formula do shoelace no anel externo de cada poligono. Para area municipal a
  aproximacao e boa; nao serve para geometria fina.

Limites
  - PIB municipal do IBGE vai ate 2023; anos seguintes repetem o ultimo
  - PIB per capita a precos correntes nao esta deflacionado, o que nao
    atrapalha comparacao ENTRE municipios no mesmo ano, que e o uso aqui

Saida
  dados/contexto_bp3.csv
"""

from __future__ import annotations

import os
import gzip
import json
import math
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

# escopo: "bp3" (35 municipios da bacia) ou "parana" (os 399 do estado)
ESCOPO = os.environ.get("SANEA_ESCOPO", "bp3")
if ESCOPO not in ("bp3", "parana"):
    raise SystemExit(f"SANEA_ESCOPO invalido: {ESCOPO}")

MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
POPULACAO = RAIZ / "dados" / f"populacao_{ESCOPO}.csv"
MALHAS = RAIZ / "dados" / "bruto" / "malhas"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = RAIZ / "dados" / f"contexto_{ESCOPO}.csv"

SIDRA_PIB = "https://apisidra.ibge.gov.br/values/t/5938/n6/{cod}/p/all/v/37"
RAIO_TERRA_KM = 6371.0


def _baixa(url: str, destino: Path) -> list[dict]:
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url, timeout=120) as resp:
        dados = resp.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    bruto = dados.decode("utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(bruto, encoding="utf-8")
    return json.loads(bruto)


def _aneis(geom: dict) -> list[list]:
    """Aneis externos do poligono, tratando Polygon e MultiPolygon."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [p[0] for p in geom["coordinates"]]
    raise ValueError(f"geometria inesperada: {geom['type']}")


def area_km2(cod: int) -> float:
    """Area do municipio pela malha do IBGE, em km2."""
    arq = MALHAS / f"malha_{cod}.json"
    if not arq.exists():
        raise SystemExit(f"falta {arq} — rode clima/bp3.py antes")
    geom = json.loads(arq.read_text(encoding="utf-8"))["features"][0]["geometry"]

    total = 0.0
    for anel in _aneis(geom):
        lat_media = sum(p[1] for p in anel) / len(anel)
        k = math.cos(math.radians(lat_media))
        pts = [(math.radians(x) * RAIO_TERRA_KM * k,
                math.radians(y) * RAIO_TERRA_KM) for x, y in anel]
        s = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            s += x1 * y2 - x2 * y1
        total += abs(s) / 2
    return total


def pib_municipal(cod: int) -> pd.DataFrame:
    """PIB a precos correntes, em mil reais, por ano."""
    registros = _baixa(SIDRA_PIB.format(cod=cod), BRUTO / f"pib_{cod}.json")
    linhas = []
    for r in registros[1:]:
        try:
            linhas.append({"ano": int(r["D2N"]), "pib_mil": float(r["V"])})
        except (ValueError, TypeError, KeyError):
            continue
    return pd.DataFrame(linhas)


def main() -> None:
    mun = pd.read_csv(MUNICIPIOS)
    pop = pd.read_csv(POPULACAO)

    quadros = []
    for _, m in mun.iterrows():
        cod = int(m["cod_ibge"])
        pib = pib_municipal(cod)
        pib["cod_ibge"] = cod
        quadros.append(pib)
        time.sleep(0.2)

    pib = pd.concat(quadros, ignore_index=True)
    areas = {int(m["cod_ibge"]): area_km2(int(m["cod_ibge"]))
             for _, m in mun.iterrows()}

    d = pop.merge(pib, on=["cod_ibge", "ano"], how="left")
    d["area_km2"] = d["cod_ibge"].map(areas).round(1)

    # PIB para depois de 2023 repete o ultimo publicado
    d = d.sort_values(["cod_ibge", "ano"])
    d["pib_mil"] = d.groupby("cod_ibge")["pib_mil"].ffill()

    d["pib_per_capita"] = (1000 * d["pib_mil"] / d["populacao"]).round(2)
    d["densidade"] = (d["populacao"] / d["area_km2"]).round(2)

    d = d[["cod_ibge", "municipio", "ano", "populacao", "area_km2",
           "densidade", "pib_per_capita"]].reset_index(drop=True)
    d.to_csv(SAIDA, index=False)

    print(f"area total da BP3 pelas malhas: {sum(areas.values()):,.0f} km2")
    print("(referencia do IAT para a bacia: 8.744 km2 — a area dos municipios")
    print(" e maior porque varios so tem parte do territorio dentro da bacia)")
    print()
    x = d[d["ano"] == 2023].sort_values("densidade", ascending=False)
    print("2023, extremos de densidade e renda:")
    print(x.head(3)[["municipio", "densidade", "pib_per_capita"]]
          .to_string(index=False))
    print(x.tail(3)[["municipio", "densidade", "pib_per_capita"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
