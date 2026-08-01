# -*- coding: utf-8 -*-
"""
Chuva e internacoes por doenca intestinal na Bacia Parana 3, 2008-2026.

A pergunta que fecha a tese do SANEA: nos meses de chuva anomala ou extrema,
sobem as internacoes por A00-A09 na bacia?

Por que nao da para correlacionar as series direto
  As internacoes por diarreia cairam 86% no periodo — de 51,2 por mil
  internacoes em 2008 para 7,0 em 2023 — por avanco de saneamento e atencao
  basica. Essa queda e ordens de grandeza maior que qualquer efeito de chuva.
  Correlacionar as series brutas mediria o calendario, nao o clima.

Metodo
  - binomial negativo com alpha ESTIMADO, nao fixado. Fixar alpha em 1.0
    infla os erros-padrao a ponto de esconder o efeito: aqui o alpha real e
    ~0.04, e com 1.0 todo intervalo de confianca cruzava 1.
  - offset log(total de internacoes no mes): o efeito e sobre a PROPORCAO,
    o que controla mudanca de volume hospitalar e de cobertura
  - tendencia linear em tempo, sazonalidade por dois pares de harmonicos
  - temperatura media do mes como covariavel: e o confundidor obvio, porque
    mes seco na bacia tende a ser mes frio e doenca intestinal tem
    sazonalidade termica propria
  - quatro exposicoes, porque acumulado mensal e ruim para enchente:
      anomalia mensal (por 100 mm)
      dias com chuva >= 20 mm (por dia)
      dias com chuva >= 50 mm (por dia)
      maximo diario do mes (por 10 mm)
  - defasagem 0, 1 e 2 meses: a data do SIH e a de internacao, que atrasa
    dias a semanas em relacao a exposicao

Leitura
  Razao de taxas acima de 1 = mais internacoes. IC que cruza 1 = efeito nao
  distinguivel de nenhum. Sao 12 modelos; a 5%, esperam-se ~0,6 falsos
  positivos so por acaso, entao resultado isolado no limiar nao e achado.

Limites
  - internacao nao e incidencia: so entra quem foi hospitalizado pelo SUS,
    e chuva forte tambem atrapalha chegar ao hospital, o que pode produzir
    associacao negativa por acesso, nao por biologia
  - mes e grosseiro para exposicao a enchente; o ideal seria semana
  - chuva da bacia e media dos 35 municipios; enchente e local
  - associacao nao e causa; nao ha controle de confundidor social

Saida
  dados/chuva_x_diarreia.csv
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import NegativeBinomial

RAIZ = Path(__file__).resolve().parent.parent
CHUVA = RAIZ / "dados" / "chuva_bp3_mensal.csv"
EXTREMOS = RAIZ / "dados" / "extremos_bp3_mensal.csv"
SIH = RAIZ / "dados" / "sih_bp3_mensal.csv"
SAIDA = RAIZ / "dados" / "chuva_x_diarreia.csv"

DEFASAGENS = [0, 1, 2]

# coluna -> (rotulo, divisor para a escala do coeficiente)
EXPOSICOES = {
    "anomalia_mm": ("anomalia mensal (por 100 mm)", 100.0),
    "dias_20mm": ("dias com >= 20 mm (por dia)", 1.0),
    "dias_50mm": ("dias com >= 50 mm (por dia)", 1.0),
    "max_diario_mm": ("maximo diario (por 10 mm)", 10.0),
}


def monta() -> pd.DataFrame:
    sih = pd.read_csv(SIH)
    p = (sih.pivot_table(index=["ano", "mes"], columns="grupo",
                         values="internacoes", fill_value=0)
         .reset_index()
         .rename(columns={"A00-A09 intestinais": "casos",
                          "TODAS AS CAUSAS": "total"}))[["ano", "mes",
                                                         "casos", "total"]]

    chuva = pd.read_csv(CHUVA)[["ano", "mes", "anomalia_mm", "oni", "fase"]]
    ext = pd.read_csv(EXTREMOS)[["ano", "mes", "dias_20mm", "dias_50mm",
                                 "max_diario_mm", "temp_media"]]

    d = (p.merge(chuva, on=["ano", "mes"], how="inner")
          .merge(ext, on=["ano", "mes"], how="inner")
          .sort_values(["ano", "mes"])
          .reset_index(drop=True))
    d["t"] = np.arange(len(d))

    for col in EXPOSICOES:
        for k in DEFASAGENS:
            d[f"{col}_lag{k}"] = d[col].shift(k)
    return d


def ajusta(d: pd.DataFrame, coluna: str, divisor: float):
    """Binomial negativo com alpha estimado. Devolve (razao, ic_inf, ic_sup, p)."""
    dd = d.dropna(subset=[coluna]).copy()
    ang = 2 * np.pi * (dd["mes"] - 1) / 12

    X = sm.add_constant(pd.DataFrame({
        "tendencia": dd["t"].to_numpy() / 12.0,
        "sin1": np.sin(ang), "cos1": np.cos(ang),
        "sin2": np.sin(2 * ang), "cos2": np.cos(2 * ang),
        "temp": dd["temp_media"].to_numpy(),
        "exposicao": dd[coluna].to_numpy() / divisor,
    }, index=dd.index))

    m = NegativeBinomial(dd["casos"], X,
                         offset=np.log(dd["total"])).fit(disp=0)
    lo, hi = m.conf_int().loc["exposicao"]
    return (float(np.exp(m.params["exposicao"])), float(np.exp(lo)),
            float(np.exp(hi)), float(m.pvalues["exposicao"]))


def main() -> None:
    d = monta()
    d.to_csv(SAIDA, index=False)

    print(f"meses no modelo: {len(d)}  "
          f"({d['ano'].iloc[0]}-{d['mes'].iloc[0]:02d} a "
          f"{d['ano'].iloc[-1]}-{d['mes'].iloc[-1]:02d})")
    print(f"casos A00-A09: {int(d['casos'].sum()):,} em "
          f"{int(d['total'].sum()):,} internacoes")
    print()
    print("Razao de taxas, binomial negativo com alpha estimado,")
    print("controlando tendencia, sazonalidade, temperatura e volume hospitalar")
    print()
    print(f"{'exposicao':<32}{'lag':>4}{'razao':>9}{'IC95%':>18}{'p':>9}")
    print("-" * 72)

    for col, (rotulo, div) in EXPOSICOES.items():
        for k in DEFASAGENS:
            rr, lo, hi, p = ajusta(d, f"{col}_lag{k}", div)
            marca = " *" if p < 0.05 else ""
            print(f"{rotulo if k == 0 else '':<32}{k:>4}{rr:>9.3f}"
                  f"{f'{lo:.3f} a {hi:.3f}':>18}{p:>9.3f}{marca}")
        print()

    print("* p < 0,05. Sao 12 modelos: a 5%, ~0,6 falsos positivos sao")
    print("  esperados por acaso. Resultado isolado no limiar nao e achado.")


if __name__ == "__main__":
    main()
