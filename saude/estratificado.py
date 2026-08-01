# -*- coding: utf-8 -*-
"""
Chuva e internacoes por doenca intestinal na BP3, estratificado por saneamento.

A pergunta: o efeito que nao aparece na media da bacia aparece onde falta rede
de esgoto?

O modelo agregado (saude/chuva_x_diarreia.py) nao achou associacao entre chuva
e internacao por A00-A09 nos 35 municipios juntos. Mas 43% deles nao tem rede
de esgoto nenhuma, e esses estavam diluidos na media. Se a tese do SANEA vale,
o efeito deve concentrar-se neles.

Estratos (de saneamento/sinisa_bp3.py)
  sem rede         15 municipios sem modulo de esgoto no SINISA
  cobertura baixa  10 municipios, IES0001 abaixo da mediana (media 49%)
  cobertura alta   10 municipios, IES0001 acima da mediana (media 84%)

Metodo
  - internacoes por municipio e mes, dos arquivos ja filtrados do SIH
  - chuva por municipio e mes, do cache diario do ERA5
  - agregacao por estrato: casos e total somados, chuva media dos municipios
  - mesmo modelo do agregado: binomial negativo com alpha estimado, offset
    log(total), tendencia, harmonicos, temperatura; exposicao em lag 0, 1, 2

Leitura
  Comparar estratos entre si importa mais que cada p isolado. O padrao que
  sustentaria a tese e gradiente: efeito maior onde falta rede, menor onde
  a cobertura e alta. Um p<0,05 solto, sem gradiente, e ruido de teste
  multiplo — sao 9 modelos por exposicao.

Limites
  - herda todos os do modelo agregado (internacao nao e incidencia, mes e
    grosseiro para enchente, associacao nao e causa)
  - os municipios sem rede sao os menores da bacia: menos casos, menos poder
  - "sem rede" e inferido da ausencia no SINISA, nao afirmado por ele
  - o estrato e de 2024 e aplicado a serie inteira desde 2008; cobertura mudou
    nesse periodo, e isso atenua o contraste

Saida
  dados/estratificado_mensal.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import NegativeBinomial

RAIZ = Path(__file__).resolve().parent.parent
SINISA = RAIZ / "dados" / "sinisa_bp3.csv"
MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"
POPULACAO = RAIZ / "dados" / "populacao_bp3.csv"
CACHE_SIH = RAIZ / "dados" / "bruto" / "sih"
CACHE_CHUVA = RAIZ / "dados" / "bruto" / "chuva"
CACHE_TEMP = RAIZ / "dados" / "bruto" / "extremos"
SAIDA = RAIZ / "dados" / "estratificado_mensal.csv"

LOTE = 7
DEFASAGENS = [0, 1, 2]
EXPOSICOES = {
    "anomalia_mm": ("anomalia mensal (100 mm)", 100.0),
    "dias_20mm": ("dias >= 20 mm (por dia)", 1.0),
}


def grupo_cid(cid: str) -> bool:
    c = (cid or "").strip().upper()[:3]
    return bool(c) and "A00" <= c <= "A09"


def casos_por_municipio(mapa6: dict[str, str]) -> pd.DataFrame:
    """Casos A00-A09 e total, por municipio e mes, dos arquivos ja filtrados."""
    linhas = []
    for arq in sorted(CACHE_SIH.glob("bp3_*.csv")):
        ano, mes = int(arq.stem[4:8]), int(arq.stem[8:10])
        d = pd.read_csv(arq, dtype={"MUNIC_RES": str})
        if d.empty:
            continue
        d["municipio"] = d["MUNIC_RES"].map(mapa6)
        d = d.dropna(subset=["municipio"])
        d["caso"] = d["DIAG_PRINC"].apply(grupo_cid).astype(int)
        g = d.groupby("municipio").agg(casos=("caso", "sum"),
                                       total=("caso", "size")).reset_index()
        g["ano"], g["mes"] = ano, mes
        linhas.append(g)
    return pd.concat(linhas, ignore_index=True)


def chuva_por_municipio(mun: pd.DataFrame) -> pd.DataFrame:
    """Chuva mensal e temperatura por municipio, dos caches diarios."""
    quadros = []
    for i in range(0, len(mun), LOTE):
        idx, bloco = i // LOTE, mun.iloc[i:i + LOTE]
        chuva = json.loads((CACHE_CHUVA / f"lote_{idx:02d}.json")
                           .read_text(encoding="utf-8"))
        temp = json.loads((CACHE_TEMP / f"lote_{idx:02d}.json")
                          .read_text(encoding="utf-8"))
        for (_, linha), pc, pt in zip(bloco.iterrows(), chuva, temp):
            c = pd.DataFrame({"data": pd.to_datetime(pc["daily"]["time"]),
                              "mm": pc["daily"]["precipitation_sum"]})
            t = pd.DataFrame({"data": pd.to_datetime(pt["daily"]["time"]),
                              "temp": pt["daily"]["temperature_2m_mean"]})
            d = c.merge(t, on="data", how="left")
            d["municipio"] = linha["municipio"]
            quadros.append(d)

    diario = pd.concat(quadros, ignore_index=True).dropna(subset=["mm"])
    diario["ano"] = diario["data"].dt.year
    diario["mes"] = diario["data"].dt.month
    diario["d20"] = (diario["mm"] >= 20).astype(int)

    m = diario.groupby(["ano", "mes", "municipio"], as_index=False).agg(
        chuva_mm=("mm", "sum"), dias_20mm=("d20", "sum"),
        temp_media=("temp", "mean"))

    normal = (m[(m["ano"] >= 1991) & (m["ano"] <= 2020)]
              .groupby(["mes", "municipio"], as_index=False)["chuva_mm"]
              .mean().rename(columns={"chuva_mm": "normal_mm"}))
    m = m.merge(normal, on=["mes", "municipio"], how="left")
    m["anomalia_mm"] = m["chuva_mm"] - m["normal_mm"]
    return m


def ajusta(d: pd.DataFrame, coluna: str, divisor: float,
           denominador: str = "populacao"):
    dd = d.dropna(subset=[coluna, "temp_media"]).copy()
    if dd["casos"].sum() < 100:
        return None
    ang = 2 * np.pi * (dd["mes"] - 1) / 12
    X = sm.add_constant(pd.DataFrame({
        "tendencia": dd["t"].to_numpy() / 12.0,
        "sin1": np.sin(ang), "cos1": np.cos(ang),
        "sin2": np.sin(2 * ang), "cos2": np.cos(2 * ang),
        "temp": dd["temp_media"].to_numpy(),
        "exposicao": dd[coluna].to_numpy() / divisor,
    }, index=dd.index))
    m = NegativeBinomial(dd["casos"], X,
                         offset=np.log(dd[denominador])).fit(disp=0)
    lo, hi = m.conf_int().loc["exposicao"]
    return (float(np.exp(m.params["exposicao"])), float(np.exp(lo)),
            float(np.exp(hi)), float(m.pvalues["exposicao"]))


def main() -> None:
    mun = pd.read_csv(MUNICIPIOS)
    est = pd.read_csv(SINISA)[["municipio", "estrato"]]
    mapa6 = {str(c)[:6]: m for c, m in zip(mun["cod_ibge"], mun["municipio"])}

    casos = casos_por_municipio(mapa6)
    chuva = chuva_por_municipio(mun)

    pop = pd.read_csv(POPULACAO)[["municipio", "ano", "populacao"]]

    d = (casos.merge(chuva, on=["ano", "mes", "municipio"], how="inner")
              .merge(est, on="municipio", how="left")
              .merge(pop, on=["municipio", "ano"], how="left"))

    agg = (d.groupby(["estrato", "ano", "mes"], as_index=False)
           .agg(casos=("casos", "sum"), total=("total", "sum"),
                populacao=("populacao", "sum"),
                anomalia_mm=("anomalia_mm", "mean"),
                dias_20mm=("dias_20mm", "mean"),
                temp_media=("temp_media", "mean"))
           .sort_values(["estrato", "ano", "mes"]))
    agg.to_csv(SAIDA, index=False)

    # A comparacao que motivou este passo: o gradiente sobrevive a troca de
    # denominador? Proporcao infla onde falta acesso a alta complexidade;
    # incidencia por habitante nao tem esse vies.
    g = agg.groupby("estrato").agg(casos=("casos", "sum"),
                                   total=("total", "sum"),
                                   pop_mes=("populacao", "sum"))
    g["por_mil_internacoes"] = (1000 * g["casos"] / g["total"]).round(1)
    g["por_100mil_hab_ano"] = (100_000 * 12 * g["casos"] / g["pop_mes"]).round(1)
    ordem = ["sem rede", "cobertura baixa", "cobertura alta"]
    g = g.reindex(ordem)

    print("Gradiente por estrato, nos dois denominadores:")
    print(g[["casos", "por_mil_internacoes", "por_100mil_hab_ano"]].to_string())
    print()
    for col in ["por_mil_internacoes", "por_100mil_hab_ano"]:
        raz = g.loc["sem rede", col] / g.loc["cobertura alta", col]
        print(f"  razao sem rede / cobertura alta ({col}): {raz:.2f}x")
    print()

    for col, (rotulo, div) in EXPOSICOES.items():
        print(f"--- {rotulo} ---")
        print(f"{'estrato':<18}{'lag':>4}{'razao':>9}{'IC95%':>18}{'p':>9}")
        for estrato in ["sem rede", "cobertura baixa", "cobertura alta"]:
            s = agg[agg["estrato"] == estrato].reset_index(drop=True).copy()
            s["t"] = np.arange(len(s))
            for k in DEFASAGENS:
                s[f"{col}_lag{k}"] = s[col].shift(k)
            for k in DEFASAGENS:
                r = ajusta(s, f"{col}_lag{k}", div)
                if r is None:
                    print(f"{estrato if k == 0 else '':<18}{k:>4}"
                          f"{'casos de menos':>36}")
                    continue
                rr, lo, hi, p = r
                marca = " *" if p < 0.05 else ""
                print(f"{estrato if k == 0 else '':<18}{k:>4}{rr:>9.3f}"
                      f"{f'{lo:.3f} a {hi:.3f}':>18}{p:>9.3f}{marca}")
            print()

    print("O que sustentaria a tese e GRADIENTE entre estratos, nao um p")
    print("isolado: sao 9 modelos por exposicao, e a 5% ~0,5 saem por acaso.")


if __name__ == "__main__":
    main()
