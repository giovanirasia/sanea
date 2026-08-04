# -*- coding: utf-8 -*-
"""
Internacao por doenca intestinal, no mesmo desenho da mortalidade.

Para que serve: mortalidade.py encontrou no Maranhao um padrao suspeito — o
esgoto inadequado sai protetor em adulto e idoso, e a fossa septica sai como
fator de risco. O diagnostico de la aponta sub-registro do obito: morre-se
menos *registrado* onde e mais pobre e mais rural, e o vies atinge numerador e
denominador juntos.

Se esse diagnostico estiver certo, ele faz uma previsao verificavel. Internacao
e obito sao apurados por sistemas diferentes, com incentivos diferentes: a AIH
existe porque o hospital precisa ser pago, e por isso e razoavelmente completa
onde ha hospital. O obito depende de cartorio e de declaracao. Se o sinal
protetor for artefato do SIM, ele deve **sumir ou mudar** quando o desfecho
vem do SIH, no mesmo estado, nos mesmos municipios, com os mesmos controles.

Se, ao contrario, o sinal protetor aparecer igual nas duas bases, a explicacao
de sub-registro cai e sobra outra coisa — provavelmente confundimento por
ruralidade que nenhum dos dois desenhos separa.

Este modulo tambem repete no Maranhao o teste que definiu o resultado do
Parana: o controle negativo por idade. La, a exposicao predizia internacao em
adulto e idoso mas nao em menor de 5, que e a assinatura etaria errada para
transmissao hidrica. A pergunta aqui e se isso se repete num estado com
saneamento muito pior.

Desenho: identico ao de mortalidade.py, trocando so o desfecho e a fonte.
  painel municipio-ano-faixa
  desfecho  internacoes por A00-A09 (CID-10), do SIH/SUS
  offset    log(populacao da faixa), estrutura etaria do Censo 2022
  exposicao esgoto_inadequado_pct do Censo, por 10 p.p.
  controles log(PIB per capita), log(densidade), tendencia anual
  Poisson, EP agrupado por municipio

Nao depende do SINISA, de proposito: o recorte do Maranhao nao tem as
planilhas carregadas, e a exposicao do Censo e melhor de qualquer forma.

Resultado (Maranhao, 217 municipios, 2008-2026)

  A previsao se confirmou, e o diagnostico de sub-registro do SIM fica de pe.
  O sinal protetor sumiu ao trocar de base: onde o SIM dava 0,918 em adultos e
  0,943 em idosos, o SIH da 1,069 e 1,076. E o descritivo explica por que —
  internacao por TODAS as causas em menores de 5 nao varia com a exposicao
  (Spearman -0,018), enquanto a mortalidade por todas as causas caia (-0,158).
  A lacuna de apuracao estava no SIM, nao na exposicao.

  Sobre a hipotese em si, porem, a resposta e a mesma do Parana. Por 10 p.p.
  de esgoto inadequado:

    0 a 4      1,060  (IC 1,007-1,116, p=0,026)
    20 a 59    1,069  (IC 0,972-1,174, p=0,17)    <- controle negativo
    60+        1,076  (IC 1,001-1,156, p=0,047)

  As tres estimativas sao praticamente a mesma. Que a de menores de 5 alcance
  significancia e a de adultos nao e diferenca de precisao, nao de magnitude —
  e ler isso como assinatura etaria seria confundir p com tamanho de efeito. O
  padrao continua sendo o de uma caracteristica de municipio que eleva
  internacao em qualquer idade.

  A fossa septica, que deveria espelhar, nao espelha em faixa nenhuma (0,972 /
  0,989 / 0,974, todas longe da significancia).

  Poco raso, sozinho, nao se associa a internacao infantil (0,998, p=0,97). A
  interacao com esgoto inadequado e negativa e forte (0,924, p=0,0003) —
  oposto da sinergia que a hipotese de contaminacao preve. A leitura provavel
  nao e biologica: o produto das duas variaveis marca ruralidade extrema, e la
  o que cai e o acesso a internacao.

  Uma armadilha que este modulo documenta: na primeira especificacao, sem
  centrar, o poco raso saiu 1,814 por 10 p.p. — o que daria fator 36 ao longo
  da amplitude observada, absurdo epidemiologico. Era o coeficiente lido em
  esgoto inadequado = 0%, ponto que nao existe no painel (o minimo e 9%).

Limites
  - internacao nao e incidencia: so entra quem foi hospitalizado pelo SUS, o
    que depende de haver leito. No Maranhao isso e limitacao seria, e e
    justamente por isso que o obito foi o desfecho primario
  - os demais limites sao os de mortalidade.py

Saida
  dados/internacao_{escopo}.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import escopo                                                  # noqa: E402
sys.path.insert(0, str(RAIZ / "saude"))
from sih_bp3 import idade_anos                                 # noqa: E402

ESCOPO = escopo.atual()
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
CACHE_SIH = RAIZ / "dados" / "bruto" / "sih"
CONTEXTO = RAIZ / "dados" / f"contexto_{ESCOPO}.csv"
CENSO = RAIZ / "dados" / f"censo_domiciliar_{ESCOPO}.csv"
IDADE = RAIZ / "dados" / f"idade_{ESCOPO}.csv"
SAIDA = RAIZ / "dados" / f"internacao_{ESCOPO}.csv"

FAIXAS = {"0a4": (0, 5), "20a59": (20, 60), "60mais": (60, 200)}


def casos_por_faixa() -> pd.DataFrame:
    mun = pd.read_csv(MUNICIPIOS)
    mapa = {str(c)[:6]: m for c, m in zip(mun["cod_ibge"], mun["municipio"])}

    linhas = []
    for arq in sorted(CACHE_SIH.glob(f"{ESCOPO}_*.csv")):
        d = pd.read_csv(arq, dtype={"MUNIC_RES": str, "COD_IDADE": str})
        if d.empty:
            continue
        if "COD_IDADE" not in d.columns:
            raise SystemExit(f"{arq.name} sem COD_IDADE: rode sih_bp3.py antes")
        d["municipio"] = d["MUNIC_RES"].map(mapa)
        d = d.dropna(subset=["municipio"])
        if d.empty:
            continue

        cid = d["DIAG_PRINC"].fillna("").str.strip().str.upper().str[:3]
        d = d.assign(hidrica=((cid >= "A00") & (cid <= "A09")).astype(int),
                     anos=[idade_anos(i, c)
                           for i, c in zip(d["IDADE"], d["COD_IDADE"])])
        d = d.dropna(subset=["anos"])

        ano = int(arq.stem.split("_")[1][:4])
        for faixa, (lo, hi) in FAIXAS.items():
            f = d[(d["anos"] >= lo) & (d["anos"] < hi)]
            if f.empty:
                continue
            g = f.groupby("municipio").agg(
                casos=("hidrica", "sum"),
                internacoes_total=("hidrica", "size")).reset_index()
            linhas.append(g.assign(ano=ano, faixa=faixa))

    return (pd.concat(linhas, ignore_index=True)
            .groupby(["municipio", "ano", "faixa"], as_index=False)
            [["casos", "internacoes_total"]].sum())


def monta() -> pd.DataFrame:
    d = (casos_por_faixa()
         .merge(pd.read_csv(CONTEXTO)[["municipio", "ano", "populacao",
                                       "densidade", "pib_per_capita"]],
                on=["municipio", "ano"], how="inner")
         .merge(pd.read_csv(CENSO)[["municipio", "esgoto_inadequado_pct",
                                    "fossa_septica_pct", "agua_poco_raso_pct",
                                    "agua_rede_pct"]], on="municipio")
         .merge(pd.read_csv(IDADE)[["municipio", "pct_0a4", "pct_20a59",
                                    "pct_60mais"]], on="municipio"))

    fr = {f: d[f"pct_{f}"] / 100 for f in FAIXAS}
    d["pop_faixa"] = np.select([d["faixa"] == f for f in fr],
                               [d["populacao"] * v for v in fr.values()])

    d["inadeq_10pp"] = d["esgoto_inadequado_pct"] / 10.0
    d["septica_10pp"] = d["fossa_septica_pct"] / 10.0
    d["poco_10pp"] = d["agua_poco_raso_pct"] / 10.0
    d["log_pib"] = np.log(d["pib_per_capita"])
    d["log_dens"] = np.log(d["densidade"])
    d["ano_c"] = d["ano"] - d["ano"].min()
    d["log_int_pc"] = np.log(
        (d["internacoes_total"] / d["pop_faixa"]).clip(lower=1e-6))
    return d[(d["pop_faixa"] > 0) & d["log_pib"].notna() & d["log_dens"].notna()]


def roda(d: pd.DataFrame, cols: list[str], rotulo: str, mostrar: int = 1) -> None:
    if d["casos"].sum() < 50:
        print(f"{rotulo}\n  eventos de menos ({int(d['casos'].sum())})\n")
        return
    X = sm.add_constant(d[cols].astype(float))
    m = sm.GLM(d["casos"], X, family=sm.families.Poisson(),
               offset=np.log(d["pop_faixa"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})
    ic = m.conf_int()
    print(rotulo)
    for c in cols[:mostrar]:
        p = m.pvalues[c]
        print(f"  {c:<16}{np.exp(m.params[c]):>7.3f}  "
              f"IC {np.exp(ic.loc[c, 0]):.3f} a {np.exp(ic.loc[c, 1]):.3f}  "
              f"p={p:.4f}{' *' if p < 0.05 else ''}   "
              f"casos={int(d['casos'].sum()):,}")
    print()


def main() -> None:
    d = monta()
    d.to_csv(SAIDA, index=False)

    ctrl = ["log_pib", "log_dens", "ano_c"]
    print(f"painel: {d['municipio'].nunique()} municipios, "
          f"{d['ano'].nunique()} anos, {len(d)} observacoes")
    print(f"internacoes A00-A09 por faixa: "
          f"{d.groupby('faixa')['casos'].sum().to_dict()}")
    print()

    print("=== 1. esgoto inadequado -> internacao, por faixa ===")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["inadeq_10pp"] + ctrl,
             f"{f}" + ("   <-- controle negativo" if f == "20a59" else ""))

    print("=== 2. espelho: fossa septica ===")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["septica_10pp"] + ctrl, f"{f}")

    print("=== 3. mecanismo: esgoto cru x agua de poco raso, menores de 5 ===")
    # As duas variaveis entram CENTRADAS na media. Num modelo com produto, o
    # coeficiente de cada termo principal vale no ponto em que o outro e zero,
    # e zero aqui fica fora dos dados: o esgoto inadequado minimo do painel e
    # 9%, nao 0. Sem centrar, o poco raso saia 1,814 por 10 p.p. — que nao e
    # efeito, e extrapolacao. Centrado, da 1,030 e nao e significativo.
    # A interacao em si nao muda com a centragem; so os termos principais.
    z = d[d["faixa"] == "0a4"].copy()
    mi, mp = z["inadeq_10pp"].mean(), z["poco_10pp"].mean()
    z["inadeq_c"] = z["inadeq_10pp"] - mi
    z["poco_c"] = z["poco_10pp"] - mp
    z["inadeq_x_poco"] = z["inadeq_c"] * z["poco_c"]
    roda(z, ["inadeq_c", "poco_c", "inadeq_x_poco"] + ctrl,
         "0a4: termos centrados na media e interacao", mostrar=3)

    print("=== 3b. poco raso sozinho, sem interacao ===")
    for f in FAIXAS:
        w = d[d["faixa"] == f].copy()
        w["poco_c"] = w["poco_10pp"] - mp
        roda(w, ["poco_c"] + ctrl, f"{f}")

    print("=== 4. controlando propensao geral a internar ===")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["inadeq_10pp", "log_int_pc"] + ctrl,
             f"{f}", mostrar=2)

    print("=== 5. descritivo por quartil de exposicao, menores de 5 ===")
    z = d[d["faixa"] == "0a4"]
    g = z.groupby("municipio").agg(
        casos=("casos", "sum"), tot=("internacoes_total", "sum"),
        popf=("pop_faixa", "sum"),
        esg=("esgoto_inadequado_pct", "first")).reset_index()
    g["tx_a09"] = 1e5 * g["casos"] / g["popf"]
    g["tx_tot"] = 1e5 * g["tot"] / g["popf"]
    q = pd.qcut(g["esg"], 4, labels=["Q1 menos exp", "Q2", "Q3", "Q4 mais exp"])
    print(g.groupby(q, observed=True).agg(
        munic=("municipio", "size"), esgoto=("esg", "median"),
        tx_A00A09=("tx_a09", "median"),
        tx_TODAS_CAUSAS=("tx_tot", "median")).round(1).to_string())
    print()
    print("  internacao por TODAS as causas vs exposicao (Spearman): "
          f"{g['esg'].corr(g['tx_tot'], method='spearman'):.3f}")
    print()
    print("Razao > 1 = mais internacoes por 10 p.p. EP agrupado por municipio.")


if __name__ == "__main__":
    main()
