# -*- coding: utf-8 -*-
"""
Metricas diarias de chuva extrema e temperatura na BP3.

Por que existe: o total mensal de chuva e uma exposicao ruim para enchente.
Um mes com um temporal de 120 mm num dia e seco no resto tem anomalia mensal
modesta, mas e ele que extravasa esgoto e contamina captacao. O que separa os
dois casos e chuva EXTREMA, nao acumulado.

E temperatura entra porque e o confundidor obvio da relacao chuva-diarreia:
mes seco na bacia tende a ser mes frio, e doenca intestinal tem sazonalidade
termica propria. Sem controlar temperatura, chuva vira proxy de estacao.

Metodo
  - chuva diaria: reaproveita o cache de chuva_bp3.py (ERA5, 1950-2026, os 35
    centroides). Nao rebaixa nada — a API cobra quota por intervalo pedido.
  - temperatura: unico download novo, so temperature_2m_mean, 2007-2026, que
    e o periodo do SIH com folga para defasagem
  - por mes e municipio: dias com chuva >= 20 mm, >= 50 mm, maximo diario,
    temperatura media; serie da bacia = media dos municipios

Saida
  dados/extremos_bp3_mensal.csv
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"
CACHE_CHUVA = RAIZ / "dados" / "bruto" / "chuva"
CACHE_TEMP = RAIZ / "dados" / "bruto" / "extremos"
SAIDA = RAIZ / "dados" / "extremos_bp3_mensal.csv"

ARQUIVO = "https://archive-api.open-meteo.com/v1/archive"
INICIO_TEMP, FIM_TEMP = "2007-01-01", "2026-06-30"
LOTE = 7

LIMIARES = [20, 50]


def _pede(url: str, tentativas: int = 5) -> str:
    """GET com recuo progressivo. A Open-Meteo devolve 429 por quota de
    intervalo pedido, nao so por numero de chamadas."""
    espera = 30
    for n in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as erro:
            if erro.code != 429 or n == tentativas - 1:
                raise
            print(f"    429 — aguardando {espera}s (tentativa {n + 1})")
            time.sleep(espera)
            espera *= 2
    raise RuntimeError("inalcancavel")


def _lotes(mun: pd.DataFrame):
    for i in range(0, len(mun), LOTE):
        yield i // LOTE, mun.iloc[i:i + LOTE]


def chuva_diaria(mun: pd.DataFrame) -> pd.DataFrame:
    """Chuva diaria do cache de chuva_bp3.py. Exige que ele ja tenha rodado."""
    quadros = []
    for idx, bloco in _lotes(mun):
        arq = CACHE_CHUVA / f"lote_{idx:02d}.json"
        if not arq.exists():
            raise SystemExit(f"falta {arq} — rode clima/chuva_bp3.py antes")
        resp = json.loads(arq.read_text(encoding="utf-8"))
        for (_, linha), ponto in zip(bloco.iterrows(), resp):
            quadros.append(pd.DataFrame({
                "data": pd.to_datetime(ponto["daily"]["time"]),
                "mm": ponto["daily"]["precipitation_sum"],
                "municipio": linha["municipio"],
            }))
    return pd.concat(quadros, ignore_index=True)


def temperatura_diaria(mun: pd.DataFrame) -> pd.DataFrame:
    """Temperatura media diaria. Unico download novo deste modulo."""
    quadros = []
    for idx, bloco in _lotes(mun):
        destino = CACHE_TEMP / f"lote_{idx:02d}.json"
        if destino.exists():
            resp = json.loads(destino.read_text(encoding="utf-8"))
        else:
            q = urllib.parse.urlencode({
                "latitude": ",".join(str(v) for v in bloco["lat"]),
                "longitude": ",".join(str(v) for v in bloco["lon"]),
                "start_date": INICIO_TEMP,
                "end_date": FIM_TEMP,
                "daily": "temperature_2m_mean",
                "timezone": "America/Sao_Paulo",
            })
            print(f"  baixando temperatura, lote {idx}")
            bruto = _pede(f"{ARQUIVO}?{q}")
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(bruto, encoding="utf-8")
            resp = json.loads(bruto)
            if not isinstance(resp, list):
                resp = [resp]
            time.sleep(5)

        for (_, linha), ponto in zip(bloco.iterrows(), resp):
            quadros.append(pd.DataFrame({
                "data": pd.to_datetime(ponto["daily"]["time"]),
                "temp": ponto["daily"]["temperature_2m_mean"],
                "municipio": linha["municipio"],
            }))
    return pd.concat(quadros, ignore_index=True)


def main() -> None:
    mun = pd.read_csv(MUNICIPIOS)

    chuva = chuva_diaria(mun)
    for lim in LIMIARES:
        chuva[f"dia_{lim}"] = (chuva["mm"] >= lim).astype(int)
    chuva["ano"] = chuva["data"].dt.year
    chuva["mes"] = chuva["data"].dt.month

    ext = chuva.groupby(["ano", "mes", "municipio"], as_index=False).agg(
        **{f"dias_{lim}mm": (f"dia_{lim}", "sum") for lim in LIMIARES},
        max_diario_mm=("mm", "max"),
    )

    temp = temperatura_diaria(mun)
    temp["ano"] = temp["data"].dt.year
    temp["mes"] = temp["data"].dt.month
    tm = temp.groupby(["ano", "mes", "municipio"], as_index=False).agg(
        temp_media=("temp", "mean"))

    junto = ext.merge(tm, on=["ano", "mes", "municipio"], how="inner")
    bacia = (junto.groupby(["ano", "mes"], as_index=False)
             .mean(numeric_only=True).round(3))
    bacia.to_csv(SAIDA, index=False)

    print()
    print(f"{len(bacia)} meses, {bacia['ano'].min()} a {bacia['ano'].max()}")
    print("medias da bacia:")
    print(f"  dias/mes com >= 20 mm: {bacia['dias_20mm'].mean():.2f}")
    print(f"  dias/mes com >= 50 mm: {bacia['dias_50mm'].mean():.2f}")
    print(f"  maximo diario medio:   {bacia['max_diario_mm'].mean():.1f} mm")
    print(f"  temperatura media:     {bacia['temp_media'].mean():.1f} C")


if __name__ == "__main__":
    main()
