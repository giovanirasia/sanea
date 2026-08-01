# -*- coding: utf-8 -*-
"""
Chuva na Bacia Parana 3 por fase do ENSO, 1950-2026.

A pergunta que sustenta a camada climatica do SANEA: em El Nino forte, chove
mesmo mais na BP3 do que em anos neutros? Se a resposta for "nao da para
distinguir", nao ha por que cruzar ENSO com saneamento e saude nesta bacia.

Metodo
  - chuva diaria da reanalise ERA5 (Open-Meteo archive) no centroide de cada um
    dos 35 municipios da BP3, agregada em total mensal
  - serie da bacia = media dos municipios em cada mes
  - normal climatologica: media 1991-2020 por mes do calendario (padrao OMM)
  - anomalia = total do mes menos a normal daquele mes
  - fase do ENSO no mes: ONI da temporada centrada nele
      (DJF centra em janeiro, JFM em fevereiro, ..., NDJ em dezembro)
  - comparacao por Mann-Whitney bilateral, que nao assume normalidade (chuva
    mensal e assimetrica), contra meses neutros DOS MESMOS MESES DO CALENDARIO:
    as classes intensas do ONI so ocorrem entre setembro e fevereiro, porque o
    indice so cruza +-1.5 perto do pico do evento

Resultado (serie 1950-2026)
  - El Nino forte ou muito forte: +42.5 mm/mes acima do neutro, p = 0.0001
  - La Nina forte: +34.6 mm/mes, p = 0.17 — nao distinguivel de neutro com
    n = 25. A anomalia positiva aparente nao e sinal invertido, e ruido; ler
    mediana contra zero em dado assimetrico e o que a fazia parecer achado.

Limites
  - ERA5 e reanalise, nao pluviometro: e coerente no espaco e no tempo, mas nao
    substitui estacao. Validar contra ANA/INMET antes de publicar numero.
  - a grade do ERA5 e mais grossa que o municipio; centroides vizinhos podem
    cair na mesma celula, o que da peso maior a essas areas na media da bacia
  - a normal 1991-2020 contem El Ninos, entao a anomalia e conservadora
  - correlacao com ENSO nao e causa; aqui so se mede se o sinal existe e quanto

Saidas
  dados/chuva_bp3_mensal.csv  serie mensal da bacia com anomalia e fase
  dados/chuva_bp3_enso.csv    resumo por fase/intensidade
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu

RAIZ = Path(__file__).resolve().parent.parent
MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"
ONI_SERIE = RAIZ / "dados" / "oni_serie.csv"
BRUTO = RAIZ / "dados" / "bruto" / "chuva"
SAIDA_MENSAL = RAIZ / "dados" / "chuva_bp3_mensal.csv"
SAIDA_ENSO = RAIZ / "dados" / "chuva_bp3_enso.csv"

ARQUIVO = "https://archive-api.open-meteo.com/v1/archive"
INICIO = "1950-01-01"
FIM = "2026-06-30"          # ultimo mes fechado com folga para o atraso do ERA5
LOTE = 7                    # coordenadas por chamada
NORMAL = (1991, 2020)       # periodo da normal climatologica (OMM)

# temporada do ONI -> mes do calendario em que ela e centrada
CENTRO = {
    "DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
    "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12,
}


def baixa_lote(lat: list[float], lon: list[float], idx: int) -> list[dict]:
    """Baixa um lote de coordenadas do arquivo ERA5, cacheando em disco."""
    destino = BRUTO / f"lote_{idx:02d}.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))

    q = urllib.parse.urlencode({
        "latitude": ",".join(f"{v}" for v in lat),
        "longitude": ",".join(f"{v}" for v in lon),
        "start_date": INICIO,
        "end_date": FIM,
        "daily": "precipitation_sum",
        "timezone": "America/Sao_Paulo",
    })
    with urllib.request.urlopen(f"{ARQUIVO}?{q}", timeout=300) as resp:
        bruto = resp.read().decode("utf-8")

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(bruto, encoding="utf-8")
    dados = json.loads(bruto)
    return dados if isinstance(dados, list) else [dados]


def serie_mensal() -> pd.DataFrame:
    """Total mensal de chuva por municipio da BP3. Colunas: ano, mes, municipio, mm"""
    mun = pd.read_csv(MUNICIPIOS)
    quadros = []

    for i in range(0, len(mun), LOTE):
        bloco = mun.iloc[i:i + LOTE]
        resp = baixa_lote(list(bloco["lat"]), list(bloco["lon"]), i // LOTE)
        if len(resp) != len(bloco):
            raise ValueError(f"lote {i // LOTE}: pedi {len(bloco)} pontos, "
                             f"vieram {len(resp)}")
        for (_, linha), ponto in zip(bloco.iterrows(), resp):
            d = pd.DataFrame({
                "data": pd.to_datetime(ponto["daily"]["time"]),
                "mm": ponto["daily"]["precipitation_sum"],
            })
            d["municipio"] = linha["municipio"]
            quadros.append(d)
        time.sleep(1.0)  # cortesia com a API

    diario = pd.concat(quadros, ignore_index=True).dropna(subset=["mm"])
    diario["ano"] = diario["data"].dt.year
    diario["mes"] = diario["data"].dt.month

    return (diario.groupby(["ano", "mes", "municipio"], as_index=False)["mm"]
            .sum())


def fases_oni() -> pd.DataFrame:
    """ONI por (ano, mes), a partir da temporada centrada no mes."""
    oni = pd.read_csv(ONI_SERIE)
    oni["mes"] = oni["temporada"].map(CENTRO)
    if oni["mes"].isna().any():
        raise ValueError("temporada sem mes central definido")
    oni = oni.rename(columns={"ano": "ano"})[["ano", "mes", "oni"]]

    def classifica(v: float) -> str:
        if v >= 2.0:
            return "El Nino muito forte"
        if v >= 1.5:
            return "El Nino forte"
        if v >= 1.0:
            return "El Nino moderado"
        if v >= 0.5:
            return "El Nino fraco"
        if v <= -1.5:
            return "La Nina forte"
        if v <= -1.0:
            return "La Nina moderada"
        if v <= -0.5:
            return "La Nina fraca"
        return "neutro"

    oni["fase"] = oni["oni"].apply(classifica)
    return oni


def compara(bacia: pd.DataFrame, fases: list[str], rotulo: str) -> None:
    """Compara fases contra meses neutros DOS MESMOS MESES DO CALENDARIO.

    A restricao nao e refinamento: o ONI so cruza +-1.5 perto do pico do evento,
    e o pico cai sempre entre setembro e fevereiro. As classes intensas, logo,
    nao existem no outono nem no inverno. Comparar contra o conjunto neutro
    inteiro seria comparar estacao chuvosa com o ano todo, e o resultado diria
    mais sobre o calendario do que sobre o ENSO.

    O teste e bilateral de proposito: para La Nina a direcao esperada e a
    oposta, e escolher a cauda depois de ver o dado inflaria a significancia.
    """
    alvo = bacia[bacia["fase"].isin(fases)]
    if alvo.empty:
        print(f"{rotulo}: nenhum mes nessa classe")
        return

    meses = sorted(int(m) for m in alvo["mes"].unique())
    neutro = bacia[(bacia["fase"] == "neutro") & (bacia["mes"].isin(meses))]

    ma = alvo["anomalia_mm"].median()
    mn = neutro["anomalia_mm"].median()
    u, p = mannwhitneyu(alvo["anomalia_mm"], neutro["anomalia_mm"],
                        alternative="two-sided")

    print(f"{rotulo} contra neutro (Mann-Whitney bilateral, mesmos meses):")
    print(f"  meses do calendario: {meses}")
    print(f"  n = {len(alvo)} contra {len(neutro)} neutros")
    print(f"  anomalia mediana: {ma:+.1f} mm/mes contra {mn:+.1f} mm/mes")
    print(f"  efeito: {ma - mn:+.1f} mm/mes")
    print(f"  U = {u:.0f}, p = {p:.4f}")
    print("  " + ("sinal detectavel" if p < 0.05 else
                  f"nao da para distinguir de neutro — n = {len(alvo)} e pouco"))


def main() -> None:
    mensal_mun = serie_mensal()

    # serie da bacia: media dos municipios
    bacia = (mensal_mun.groupby(["ano", "mes"], as_index=False)["mm"]
             .mean().rename(columns={"mm": "chuva_mm"}))

    # normal climatologica por mes do calendario
    janela = bacia[(bacia["ano"] >= NORMAL[0]) & (bacia["ano"] <= NORMAL[1])]
    normal = (janela.groupby("mes", as_index=False)["chuva_mm"]
              .mean().rename(columns={"chuva_mm": "normal_mm"}))

    bacia = bacia.merge(normal, on="mes")
    bacia["anomalia_mm"] = bacia["chuva_mm"] - bacia["normal_mm"]
    bacia["anomalia_pct"] = 100 * bacia["anomalia_mm"] / bacia["normal_mm"]

    bacia = bacia.merge(fases_oni(), on=["ano", "mes"], how="left")
    bacia = bacia.sort_values(["ano", "mes"]).reset_index(drop=True)
    bacia.to_csv(SAIDA_MENSAL, index=False)

    # resumo por fase
    # A anomalia e medida contra a MEDIA climatologica, mas chuva mensal e
    # assimetrica a direita: a media fica acima da mediana. Por isso a mediana
    # da anomalia e negativa em quase toda fase, inclusive na neutra — isso e
    # artefato da assimetria, nao seca. As fases devem ser comparadas ENTRE SI,
    # nao contra zero. A coluna de chuva absoluta esta aqui para permitir isso.
    resumo = (bacia.dropna(subset=["fase"])
              .groupby("fase")
              .agg(meses=("anomalia_mm", "size"),
                   chuva_mediana_mm=("chuva_mm", "median"),
                   anomalia_mediana_mm=("anomalia_mm", "median"),
                   anomalia_media_mm=("anomalia_mm", "mean"),
                   anomalia_mediana_pct=("anomalia_pct", "median"))
              .round(1)
              .sort_values("anomalia_mediana_mm", ascending=False)
              .reset_index())
    resumo.to_csv(SAIDA_ENSO, index=False)

    print(f"serie da bacia: {len(bacia)} meses, "
          f"{bacia['ano'].min()} a {bacia['ano'].max()}")
    print(f"normal {NORMAL[0]}-{NORMAL[1]}: "
          f"{normal['normal_mm'].sum():.0f} mm/ano na media da bacia")
    print()
    print(resumo.to_string(index=False))

    print()
    compara(bacia, ["El Nino forte", "El Nino muito forte"], "El Nino forte+")
    print()
    compara(bacia, ["La Nina forte"], "La Nina forte")

    print()
    print("Tres ressalvas de leitura:")
    print("  - compare as fases entre si, nao contra zero: a anomalia mediana e")
    print("    negativa em quase todas porque a normal e media e a chuva mensal")
    print("    e assimetrica a direita")
    print("  - a coluna de chuva bruta nao desconta sazonalidade; serve para dar")
    print("    ordem de grandeza, nao para medir efeito")
    print("  - as classes intensas so existem em Set-Fev, porque o ONI so cruza")
    print("    +-1.5 perto do pico do evento; por isso o grupo de comparacao e")
    print("    restrito aos mesmos meses do calendario")


if __name__ == "__main__":
    main()
