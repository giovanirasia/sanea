# -*- coding: utf-8 -*-
"""
O que a densidade demografica esta medindo?

Densidade entrou nos modelos como controle de ruralidade, nao como hipotese, e
acabou sendo a unica variavel robusta nas duas escalas — 0,564 na BP3 e 0,717
no Parana. Municipio menos denso interna mais por A00-A09. Este modulo
investiga o que ela captura.

Uma explicacao nao serve: acesso ao servico. Se fosse acesso, o sinal seria o
oposto — mais longe do hospital significa MENOS internacao registrada. O efeito
ser protetor com a densidade implica que a carga real no rural e ainda maior
que a medida.

Hipoteses testadas
  1. composicao etaria — internacao por A00-A09 concentra-se em crianca pequena
     e idoso, e o interior do Parana envelheceu com a saida dos jovens
  2. limiar de internacao — sem atencao basica por perto, uma diarreia que na
     cidade seria resolvida na UBS vira internacao no interior. Isso nao e mais
     doenca, e mais hospitalizacao pela mesma doenca. Testado vendo se a
     densidade prediz internacao por QUALQUER causa, e controlando a propensao
     geral a internar.

Resultado (Parana, 397 municipios, 2008-2026)
  Idade explica parte: com % 60+ e % 0-4 no modelo, log(densidade) vai de 0,717
  para 0,809. Os dois coeficientes etarios sao fortes — cada ponto percentual a
  mais de menores de 5 anos associa-se a ~39% mais internacao.

  Limiar de internacao explica outra parte: densidade prediz internacao por
  qualquer causa (0,945, p<0,0001), e controlando a propensao geral a internar
  o efeito sobre diarreia cai de 0,809 para 0,904, mas permanece (p=0,009).

  Sobra densidade sem explicacao, agora menor. Candidatos nao testados aqui:
  fonte de agua domiciliar no rural (poco e nascente nao entram no IAG0001),
  solucao individual de esgoto mal executada, distancia ate atencao basica.

O que este modulo mostra sobre saneamento
  Com tudo controlado — idade, densidade, renda, tendencia e propensao a
  internar — a cobertura de esgoto da razao 1,000 por 10 p.p. (IC 0,976-1,025,
  p=0,98).
  Nenhuma associacao. A tese de que cobertura municipal de esgoto prediz
  internacao por doenca intestinal nao se sustenta nesta escala.

Limites
  - o Censo 2022 e um ponto no tempo aplicado a um painel de 19 anos
  - propensao a internar e desfecho, nao covariavel exogena: controla-la pode
    ser sobreajuste. Esta aqui como diagnostico, nao como especificacao final.
  - tudo observacional

Saida: apenas impressao; nao gera arquivo.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent

ESCOPO = os.environ.get("SANEA_ESCOPO", "parana")
PAINEL = RAIZ / "dados" / f"gradiente_ajustado_{ESCOPO}.csv"
IDADE = RAIZ / "dados" / f"idade_{ESCOPO}.csv"
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
CACHE_SIH = RAIZ / "dados" / "bruto" / "sih"


def total_internacoes() -> pd.DataFrame:
    mun = pd.read_csv(MUNICIPIOS)
    mapa = {str(c)[:6]: m for c, m in zip(mun["cod_ibge"], mun["municipio"])}
    linhas = []
    for arq in sorted(CACHE_SIH.glob(f"{ESCOPO}_*.csv")):
        ano = int(arq.stem.split("_")[1][:4])
        d = pd.read_csv(arq, dtype={"MUNIC_RES": str})
        if d.empty:
            continue
        d["municipio"] = d["MUNIC_RES"].map(mapa)
        d = d.dropna(subset=["municipio"])
        g = d.groupby("municipio").size().rename("total").reset_index()
        g["ano"] = ano
        linhas.append(g)
    return (pd.concat(linhas, ignore_index=True)
            .groupby(["municipio", "ano"], as_index=False)["total"].sum())


def roda(d: pd.DataFrame, y: str, cols: list[str], rotulo: str) -> None:
    X = sm.add_constant(d[cols].astype(float))
    m = sm.GLM(d[y], X, family=sm.families.Poisson(),
               offset=np.log(d["populacao"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})
    ic = m.conf_int()
    print(rotulo)
    for c in cols:
        p = m.pvalues[c]
        print(f"  {c:<13}{np.exp(m.params[c]):>7.3f}  "
              f"IC {np.exp(ic.loc[c, 0]):.3f} a {np.exp(ic.loc[c, 1]):.3f}  "
              f"p={p:.4f}{' *' if p < 0.05 else ''}")
    print()


def main() -> None:
    d = (pd.read_csv(PAINEL)
         .merge(pd.read_csv(IDADE)[["municipio", "pct_0a4", "pct_60mais"]],
                on="municipio", how="inner")
         .merge(total_internacoes(), on=["municipio", "ano"], how="inner"))
    d["esgoto_10pp"] = d["esgoto_pct"] / 10.0
    d["log_tot_pc"] = np.log(d["total"] / d["populacao"])

    print(f"painel: {d['municipio'].nunique()} municipios, {len(d)} observacoes")
    print()

    base = ["esgoto_10pp", "log_pib", "log_dens", "ano_c"]
    roda(d, "casos", base, "1) modelo atual")
    roda(d, "casos", base + ["pct_60mais", "pct_0a4"], "2) + composicao etaria")
    roda(d, "total", ["log_dens", "log_pib", "pct_60mais", "pct_0a4", "ano_c"],
         "3) densidade prediz internacao por QUALQUER causa?")
    roda(d, "casos", base + ["pct_60mais", "pct_0a4", "log_tot_pc"],
         "4) + propensao geral a internar")

    print("Leitura: idade e propensao a internar explicam parte da densidade,")
    print("nao toda. E com tudo controlado a cobertura de esgoto some.")


if __name__ == "__main__":
    main()
