# -*- coding: utf-8 -*-
"""
Ingestao do ONI (Oceanic Nino Index) do CPC/NOAA e classificacao dos episodios
de El Nino e La Nina desde 1950.

A pergunta: quais anos foram de El Nino forte, e com que intensidade? Sem essa
lista nao da para perguntar "o que aconteceu aqui nos eventos anteriores", que
e o objetivo da camada climatica do SANEA.

O ONI e a media movel de 3 meses da anomalia de TSM na regiao Nino 3.4
(ERSSTv5). O arquivo do CPC traz 12 temporadas sobrepostas por ano (DJF, JFM,
FMA, ...), entao "temporada" aqui nao e mes: e uma janela de 3 meses centrada.

Metodo (definicao oficial do CPC)
  - episodio de El Nino  = ONI >= +0.5 por 5 temporadas consecutivas
  - episodio de La Nina  = ONI <= -0.5 por 5 temporadas consecutivas
  - intensidade pelo pico do episodio:
      fraco     0.5 a 0.9
      moderado  1.0 a 1.4
      forte     1.5 a 1.9
      muito forte >= 2.0

Limite importante: essa classificacao e RETROSPECTIVA. Um evento em curso ainda
nao acumulou as 5 temporadas e por isso nao vira episodio formal aqui — ele sai
marcado como 'em curso'. Previsao de intensidade nao entra neste script; para
isso a fonte e o boletim do CPC/IRI, e a incerteza e deles, nao nossa.

Saidas
  dados/oni_serie.csv    serie completa, uma linha por temporada
  dados/oni_episodios.csv um episodio por linha, com pico e intensidade
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "oni.ascii.txt"
SERIE = RAIZ / "dados" / "oni_serie.csv"
EPISODIOS = RAIZ / "dados" / "oni_episodios.csv"

FONTE = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"

# as 12 janelas de 3 meses, na ordem em que ocorrem dentro do ano
TEMPORADAS = [
    "DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
    "JJA", "JAS", "ASO", "SON", "OND", "NDJ",
]

LIMIAR = 0.5
MIN_TEMPORADAS = 5


def baixa(forcar: bool = False) -> Path:
    """Baixa o arquivo do CPC. Cacheia em dados/bruto/ (fora do versionamento)."""
    if BRUTO.exists() and not forcar:
        return BRUTO
    BRUTO.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(FONTE, timeout=60) as resp:
        BRUTO.write_bytes(resp.read())
    return BRUTO


def carrega() -> pd.DataFrame:
    """Le o arquivo do CPC em DataFrame ordenado cronologicamente.

    Colunas: temporada, ano, tsm_total, oni, ordem
    """
    df = pd.read_csv(baixa(), sep=r"\s+", engine="python")
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={"seas": "temporada", "yr": "ano",
                            "total": "tsm_total", "anom": "oni"})

    # nao confiar na ordem do arquivo: reconstruir a partir de (ano, temporada)
    pos = {t: i for i, t in enumerate(TEMPORADAS)}
    faltando = set(df["temporada"]) - set(pos)
    if faltando:
        raise ValueError(f"temporada desconhecida no arquivo do CPC: {faltando}")

    df["ordem"] = df["ano"] * 12 + df["temporada"].map(pos)
    df = df.sort_values("ordem").reset_index(drop=True)
    return df[["temporada", "ano", "tsm_total", "oni", "ordem"]]


def _intensidade(pico: float) -> str:
    p = abs(pico)
    if p >= 2.0:
        return "muito forte"
    if p >= 1.5:
        return "forte"
    if p >= 1.0:
        return "moderado"
    return "fraco"


def episodios(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa temporadas consecutivas acima/abaixo do limiar em episodios.

    Sequencias com menos de 5 temporadas nao sao episodio pela definicao do CPC.
    A excecao e a sequencia que vai ate o fim da serie: essa pode ser um evento
    ainda em formacao, entao ela sai marcada como em curso em vez de descartada.
    """
    linhas = []
    atual: list[dict] = []
    sinal_atual = 0

    def fecha(seq: list[dict], sinal: int, ate_o_fim: bool) -> None:
        if not seq:
            return
        n = len(seq)
        em_curso = ate_o_fim and n < MIN_TEMPORADAS
        if n < MIN_TEMPORADAS and not em_curso:
            return
        picos = [r["oni"] for r in seq]
        pico = max(picos) if sinal > 0 else min(picos)
        topo = seq[picos.index(pico)]
        linhas.append({
            "tipo": "El Nino" if sinal > 0 else "La Nina",
            "inicio": f"{seq[0]['temporada']} {seq[0]['ano']}",
            "fim": f"{seq[-1]['temporada']} {seq[-1]['ano']}",
            "temporadas": n,
            "pico_temporada": f"{topo['temporada']} {topo['ano']}",
            "pico_oni": round(float(pico), 2),
            "intensidade": _intensidade(pico),
            "em_curso": em_curso,
        })

    for _, r in df.iterrows():
        oni = float(r["oni"])
        sinal = 1 if oni >= LIMIAR else (-1 if oni <= -LIMIAR else 0)
        if sinal != 0 and sinal == sinal_atual:
            atual.append(r.to_dict())
        else:
            fecha(atual, sinal_atual, ate_o_fim=False)
            atual = [r.to_dict()] if sinal != 0 else []
            sinal_atual = sinal

    fecha(atual, sinal_atual, ate_o_fim=True)

    out = pd.DataFrame(linhas)
    return out.sort_values("pico_oni", key=abs, ascending=False).reset_index(drop=True)


def main() -> None:
    df = carrega()
    ep = episodios(df)

    SERIE.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["ordem"]).to_csv(SERIE, index=False)
    ep.to_csv(EPISODIOS, index=False)

    ultimo = df.iloc[-1]
    ninos = ep[(ep["tipo"] == "El Nino") & (~ep["em_curso"])]

    print(f"serie: {len(df)} temporadas, "
          f"{df.iloc[0]['temporada']} {df.iloc[0]['ano']} a "
          f"{ultimo['temporada']} {ultimo['ano']}")
    print(f"ultimo ONI publicado: {ultimo['oni']:+.2f} "
          f"({ultimo['temporada']} {ultimo['ano']})")
    print(f"episodios: {len(ep)}  |  El Nino fechados: {len(ninos)}")
    print()
    print("El Nino forte ou muito forte (candidatos a analogo historico):")
    fortes = ninos[ninos["intensidade"].isin(["forte", "muito forte"])]
    for _, r in fortes.iterrows():
        print(f"  {r['inicio']:>9} a {r['fim']:<9} "
              f"pico {r['pico_oni']:+.2f} em {r['pico_temporada']:<9} "
              f"{r['intensidade']}")

    curso = ep[ep["em_curso"]]
    if not curso.empty:
        r = curso.iloc[0]
        print()
        print(f"em curso: {r['tipo']} desde {r['inicio']}, "
              f"{r['temporadas']} temporada(s), ONI ate agora {r['pico_oni']:+.2f}")
        print("  (ainda nao e episodio formal: exige 5 temporadas consecutivas)")


if __name__ == "__main__":
    main()
