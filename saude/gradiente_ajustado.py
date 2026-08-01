# -*- coding: utf-8 -*-
"""
O gradiente de saneamento sobrevive ao controle de renda e ruralidade?

O achado bruto: quem mora em municipio da BP3 sem rede de esgoto interna por
doenca intestinal 4,7 vezes mais que quem mora onde a cobertura e alta (331,7
contra 71,1 por 100 mil habitantes por ano).

A objecao imediata: municipios sem rede sao menores, mais rurais e mais
pobres. O gradiente mede saneamento ou mede pobreza? Sem responder isso, o
numero e correlacao bruta.

Desenho
  painel municipio-ano, 35 municipios x 2008-2026
  desfecho  internacoes anuais por A00-A09
  offset    log(populacao) — incidencia por habitante
  controles log(PIB per capita), log(densidade demografica), tendencia anual
  exposicao saneamento, em duas codificacoes:
      dummies de estrato, comparaveis com o 4,7x bruto
      IES0001 continuo, com sem rede = 0, que da dose-resposta

  Poisson com erros-padrao agrupados por municipio. O agrupamento nao e
  detalhe: sao 19 observacoes do mesmo municipio, e trata-las como
  independentes estreitaria os intervalos artificialmente. O EP robusto
  tambem absorve a superdispersao, entao nao e preciso fixar alpha.

Por que sem rede = 0 e honesto
  Nao ter rede coletora e cobertura zero, nao dado faltante. Os 15 municipios
  aparecem no modulo de agua do SINISA; so nao tem esgoto para reportar.

Limites
  - o SINISA e de 2024 e o painel comeca em 2008: cobertura mudou no periodo,
    o que atenua o contraste
  - densidade e proxy de ruralidade, nao grau de urbanizacao
  - PIB per capita a precos correntes, sem deflacionar; serve para comparar
    municipios no mesmo ano, que e o uso aqui
  - continua sendo observacional: nao ha aleatorizacao de saneamento

Saida
  dados/gradiente_ajustado.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"
SINISA = RAIZ / "dados" / "sinisa_bp3.csv"
CONTEXTO = RAIZ / "dados" / "contexto_bp3.csv"
CACHE_SIH = RAIZ / "dados" / "bruto" / "sih"
SAIDA = RAIZ / "dados" / "gradiente_ajustado.csv"

ESTRATOS = ["cobertura alta", "cobertura baixa", "sem rede"]


def casos_anuais(mapa6: dict[str, str]) -> pd.DataFrame:
    linhas = []
    for arq in sorted(CACHE_SIH.glob("bp3_*.csv")):
        ano = int(arq.stem[4:8])
        d = pd.read_csv(arq, dtype={"MUNIC_RES": str})
        if d.empty:
            continue
        d["municipio"] = d["MUNIC_RES"].map(mapa6)
        d = d.dropna(subset=["municipio"])
        cid = d["DIAG_PRINC"].fillna("").str.strip().str.upper().str[:3]
        d["caso"] = ((cid >= "A00") & (cid <= "A09")).astype(int)
        g = d.groupby("municipio", as_index=False)["caso"].sum()
        g["ano"] = ano
        linhas.append(g.rename(columns={"caso": "casos"}))
    return (pd.concat(linhas, ignore_index=True)
            .groupby(["municipio", "ano"], as_index=False)["casos"].sum())


def monta() -> pd.DataFrame:
    mun = pd.read_csv(MUNICIPIOS)
    mapa6 = {str(c)[:6]: m for c, m in zip(mun["cod_ibge"], mun["municipio"])}

    casos = casos_anuais(mapa6)
    ctx = pd.read_csv(CONTEXTO)[["municipio", "ano", "populacao",
                                 "densidade", "pib_per_capita"]]
    san = pd.read_csv(SINISA)[["municipio", "estrato", "IES0001"]]

    d = (casos.merge(ctx, on=["municipio", "ano"], how="inner")
              .merge(san, on="municipio", how="left"))

    # sem rede e cobertura zero, nao dado faltante
    d["esgoto_pct"] = d["IES0001"].fillna(0.0)
    d["log_pib"] = np.log(d["pib_per_capita"])
    d["log_dens"] = np.log(d["densidade"])
    d["ano_c"] = d["ano"] - d["ano"].min()
    return d.dropna(subset=["populacao", "log_pib", "log_dens"])


def roda(d: pd.DataFrame, termos: pd.DataFrame, rotulo: str) -> None:
    X = sm.add_constant(termos)
    m = sm.GLM(d["casos"], X, family=sm.families.Poisson(),
               offset=np.log(d["populacao"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})

    print(rotulo)
    ic = m.conf_int()
    for nome in termos.columns:
        rr = np.exp(m.params[nome])
        lo, hi = np.exp(ic.loc[nome])
        p = m.pvalues[nome]
        marca = " *" if p < 0.05 else ""
        print(f"  {nome:<22}{rr:>8.3f}  IC {lo:.3f} a {hi:.3f}   p={p:.4f}{marca}")
    print()


def main() -> None:
    d = monta()
    d.to_csv(SAIDA, index=False)

    print(f"painel: {d['municipio'].nunique()} municipios x "
          f"{d['ano'].nunique()} anos = {len(d)} observacoes")
    print(f"casos A00-A09: {int(d['casos'].sum()):,}")
    print()

    # 1) estratos, sem controle — reproduz o gradiente bruto
    dummies = pd.get_dummies(d["estrato"], prefix="", prefix_sep="").astype(float)
    base = dummies[["sem rede", "cobertura baixa"]].rename(
        columns={"sem rede": "sem_rede", "cobertura baixa": "cob_baixa"})
    roda(d, base.set_index(d.index),
         "1) Estratos, sem controle (referencia: cobertura alta)")

    # 2) estratos, com renda, ruralidade e tendencia
    comp = base.set_index(d.index).assign(
        log_pib=d["log_pib"], log_dens=d["log_dens"], ano=d["ano_c"])
    roda(d, comp, "2) Estratos, controlando renda, densidade e tendencia")

    # 3) dose-resposta continua
    cont = pd.DataFrame({
        "esgoto_10pp": d["esgoto_pct"] / 10.0,
        "log_pib": d["log_pib"], "log_dens": d["log_dens"], "ano": d["ano_c"],
    }, index=d.index)
    roda(d, cont, "3) Dose-resposta: cobertura de esgoto, por 10 pontos")

    print("Razao > 1 = mais internacoes. EP agrupado por municipio.")


if __name__ == "__main__":
    main()
