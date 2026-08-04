# -*- coding: utf-8 -*-
"""
Saneamento e morte por doenca intestinal, onde a doenca ainda mata.

O que este modulo testa que os anteriores nao podiam
  No Parana a resposta foi nao: a exposicao a esgoto cru prediz internacao em
  adulto e idoso, mas nao em menor de 5 anos, que e a assinatura etaria errada
  para transmissao hidrica. So que o Parana registrou 58 obitos de A00-A09 em
  menores de 5 anos em 19 anos — evento raro demais para modelar, e um estado
  onde a doenca letal infantil ja foi resolvida. Nulo ali nao se transfere.

  O Maranhao registrou 983 no mesmo tipo de recorte. E a amplitude da exposicao
  tambem e outra: mediana de 79,9% de domicilios com destino inadequado de
  esgoto contra 43,4% do Parana, e — decisivo para o mecanismo — 8,1% de
  domicilios com poco raso contra 1,0%.

  Ou seja, aqui da para perguntar de novo, com o desfecho duro e com o
  mecanismo testavel.

Por que SIM e nao o MORTE do SIH
  MORTE no SIH so enxerga quem morreu internado. Quem morre de diarreia em
  municipio sem leito ou sem estrada morre sem internar e desaparece da base,
  entao o sub-registro seria maior justamente onde a exposicao e maior — vies
  que empurra a associacao para zero. O SIM registra a partir da declaracao de
  obito, independente de internacao. Ver saude/sim.py.

Desenho
  painel municipio-ano-faixa, 217 municipios x 2008-2024
  desfecho  obitos por A00-A09
  offset    log(populacao da faixa), com a estrutura etaria do Censo 2022
  exposicao esgoto_inadequado_pct do Censo, por 10 p.p.
  controles log(PIB per capita), log(densidade), tendencia anual
  faixas    0a4, 20a59 (controle negativo), 60mais

  Poisson com erros-padrao agrupados por municipio.

O controle negativo, de novo
  Vale a mesma logica do Parana: se for transmissao hidrica, menor de 5 tem de
  responder muito mais que adulto de 20 a 59. Se as duas faixas responderem
  igual, o que se mede e pobreza ou acesso, nao saneamento. A diferenca e que
  agora ha eventos suficientes na faixa que importa.

Um controle a mais, proprio do SIM
  Mortalidade geral per capita da faixa entra como covariavel opcional porque
  captura duas coisas ao mesmo tempo: quanto se morre naquele municipio por
  tudo, e quao completo e o registro do SIM ali. Cobertura do SIM e
  historicamente pior no interior do Nordeste, que e onde a exposicao e maior —
  sem esse controle, parte do efeito pode ser qualidade de registro.

Resultado (Maranhao, 217 municipios, 2008-2024, 982 obitos de menores de 5)

  Nao ha gradiente. Esgoto inadequado sobre obito em menor de 5 anos da
  **1,005 (IC 0,958-1,055, p=0,84)** — nulo, e com intervalo estreito o
  bastante para excluir efeito acima de ~5% por 10 p.p.

  Nas faixas adultas o coeficiente sai PROTETOR (0,918 em 20-59, p=0,013) e a
  fossa septica sai como fator de risco (1,089, p=0,014) — o inverso da
  hipotese nas duas pontas ao mesmo tempo, que quase nunca e efeito e quase
  sempre e medida. O diagnostico esta na funcao diagnostico() e conclui
  sub-apuracao: a mortalidade por TODAS as causas em menores de 5 tambem cai
  com a exposicao, o que nao e critivel. Esses coeficientes nao devem ser
  interpretados.

  O nulo dos menores de 5, ao contrario, sobrevive ao diagnostico: a taxa
  quase nao varia entre quartis de exposicao (10,2 / 9,1 / 8,7 / 8,0 por 100
  mil crianca-ano, do menos ao mais exposto), e a lacuna de apuracao e de
  ~5% na mortalidade geral, ordem de grandeza abaixo do necessario para
  esconder um efeito relevante.

  O mecanismo tambem nao aparece, agora com amplitude de verdade: a interacao
  esgoto inadequado x agua de poco raso da 0,980 (p=0,33), com poco raso
  chegando a 61,5% dos domicilios. Agua de rede nao protege menor de 5
  (0,997, p=0,90).

Como ler isso sem exagerar

  Nao e "saneamento nao afeta saude". O efeito do saneamento sobre doenca
  diarreica e das relacoes mais bem estabelecidas da saude publica, medida em
  ensaio comunitario e em coorte.

  O que tres analises deste repositorio mostram, no mesmo sentido, e outra
  coisa: na RMSP a cobertura municipal nao explicou o IQA do ponto; no Parana
  nao explicou internacao; no Maranhao nao explica obito infantil, que era o
  caso mais favoravel possivel — doenca ainda letal, exposicao alta e ampla,
  desfecho duro. Quando o mesmo desenho falha em tres contextos tao
  diferentes, a hipotese mais economica nao e que o mundo mudou, e que a
  unidade de analise esta errada. Media municipal dilui exposicao que e
  domiciliar, e o municipio e grande demais para que a fracao exposta e a
  fracao adoecida sejam as mesmas pessoas.

Limites
  - o Censo 2022 e um ponto no tempo aplicado a um painel de 17 anos
  - causa basica mal definida (capitulo R) absorve obitos que deveriam estar em
    A00-A09, e essa mal definicao tambem e maior onde ha menos assistencia
  - denominador por faixa usa a estrutura etaria de 2022 em todos os anos
  - fracao municipal nao e cruzamento no domicilio: a interacao esgoto x poco
    raso e indicio de mecanismo, nao prova (falacia ecologica em potencial)
  - observacional

Saida
  dados/mortalidade_{escopo}.csv
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

ESCOPO = escopo.atual()
SIM = RAIZ / "dados" / f"sim_{ESCOPO}_anual.csv"
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
POPULACAO = RAIZ / "dados" / f"populacao_{ESCOPO}.csv"
CONTEXTO = RAIZ / "dados" / f"contexto_{ESCOPO}.csv"
CENSO = RAIZ / "dados" / f"censo_domiciliar_{ESCOPO}.csv"
IDADE = RAIZ / "dados" / f"idade_{ESCOPO}.csv"
SAIDA = RAIZ / "dados" / f"mortalidade_{ESCOPO}.csv"

FAIXAS = ["0a4", "20a59", "60mais"]


def monta() -> pd.DataFrame:
    mun = pd.read_csv(MUNICIPIOS)[["cod_ibge", "municipio"]]
    mun["cod6"] = mun["cod_ibge"].astype(str).str[:6]

    d = (pd.read_csv(SIM, dtype={"cod6": str})
         .merge(mun, on="cod6", how="inner")
         .merge(pd.read_csv(CONTEXTO)[["municipio", "ano", "populacao",
                                       "densidade", "pib_per_capita"]],
                on=["municipio", "ano"], how="inner")
         .merge(pd.read_csv(CENSO), on=["cod_ibge", "municipio"], how="inner")
         .merge(pd.read_csv(IDADE)[["municipio", "pct_0a4", "pct_20a59",
                                    "pct_60mais"]], on="municipio", how="inner"))
    d = d[d["faixa"].isin(FAIXAS)]

    fr = {f: d[f"pct_{f}"] / 100 for f in FAIXAS}
    d["pop_faixa"] = np.select([d["faixa"] == f for f in fr],
                               [d["populacao"] * v for v in fr.values()])

    d["inadeq_10pp"] = d["esgoto_inadequado_pct"] / 10.0
    d["septica_10pp"] = d["fossa_septica_pct"] / 10.0
    d["poco_10pp"] = d["agua_poco_raso_pct"] / 10.0
    d["agua_rede_10pp"] = d["agua_rede_pct"] / 10.0
    d["log_pib"] = np.log(d["pib_per_capita"])
    d["log_dens"] = np.log(d["densidade"])
    d["ano_c"] = d["ano"] - d["ano"].min()
    d["log_mort_geral"] = np.log(
        (d["obitos_total"] / d["pop_faixa"]).clip(lower=1e-6))
    return d[(d["pop_faixa"] > 0) & d["log_pib"].notna() & d["log_dens"].notna()]


def roda(d: pd.DataFrame, cols: list[str], rotulo: str,
         mostrar: int = 1) -> None:
    if d["obitos_a00a09"].sum() < 50:
        print(f"{rotulo}\n  eventos de menos "
              f"({int(d['obitos_a00a09'].sum())}); nao modelado\n")
        return
    X = sm.add_constant(d[cols].astype(float))
    m = sm.GLM(d["obitos_a00a09"], X, family=sm.families.Poisson(),
               offset=np.log(d["pop_faixa"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})
    ic = m.conf_int()
    print(rotulo)
    for c in cols[:mostrar]:
        p = m.pvalues[c]
        print(f"  {c:<16}{np.exp(m.params[c]):>7.3f}  "
              f"IC {np.exp(ic.loc[c, 0]):.3f} a {np.exp(ic.loc[c, 1]):.3f}  "
              f"p={p:.4f}{' *' if p < 0.05 else ''}   "
              f"obitos={int(d['obitos_a00a09'].sum()):,}")
    print()


def main() -> None:
    d = monta()
    d.to_csv(SAIDA, index=False)

    ctrl = ["log_pib", "log_dens", "ano_c"]
    print(f"painel: {d['municipio'].nunique()} municipios, "
          f"{d['ano'].nunique()} anos, {len(d)} observacoes")
    print(f"obitos A00-A09 por faixa: "
          f"{d.groupby('faixa')['obitos_a00a09'].sum().to_dict()}")
    print(f"exposicao: esgoto inadequado de "
          f"{d['esgoto_inadequado_pct'].min():.1f}% a "
          f"{d['esgoto_inadequado_pct'].max():.1f}%, "
          f"poco raso ate {d['agua_poco_raso_pct'].max():.1f}%")
    print()

    print("=== 1. esgoto inadequado -> obito, por faixa etaria ===")
    print("se for transmissao hidrica, 0a4 supera 20a59 com folga\n")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["inadeq_10pp"] + ctrl,
             f"{f}" + ("   <-- controle negativo" if f == "20a59" else ""))

    print("=== 2. espelho: fossa septica protege? ===")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["septica_10pp"] + ctrl, f"{f}")

    print("=== 3. mecanismo: esgoto cru x agua de poco raso ===")
    print("no Parana este teste nao tinha amplitude; aqui tem\n")
    # centrados na media: num modelo com produto, o termo principal vale onde
    # o outro e zero, e esgoto inadequado zero nao existe no painel (o minimo
    # e 9%). Ver a nota equivalente em internacao.py, onde a diferenca foi
    # grande — o poco raso saltava de 1,03 para 1,81 so por causa disso.
    z = d[d["faixa"] == "0a4"].copy()
    z["inadeq_c"] = z["inadeq_10pp"] - z["inadeq_10pp"].mean()
    z["poco_c"] = z["poco_10pp"] - z["poco_10pp"].mean()
    z["inadeq_x_poco"] = z["inadeq_c"] * z["poco_c"]
    roda(z, ["inadeq_c", "poco_c", "inadeq_x_poco"] + ctrl,
         "0a4: termos centrados na media e interacao", mostrar=3)

    print("=== 4. agua de rede protege menor de 5? ===")
    roda(d[d["faixa"] == "0a4"], ["agua_rede_10pp"] + ctrl, "0a4")

    print("=== 5. robustez: controlando mortalidade geral da faixa ===")
    print("captura tanto quanto se morre quanto a completude do SIM\n")
    for f in FAIXAS:
        roda(d[d["faixa"] == f], ["inadeq_10pp", "log_mort_geral"] + ctrl,
             f"{f}", mostrar=2)

    diagnostico(d)
    print("Razao > 1 = mais obitos por 10 p.p. EP agrupado por municipio.")


def diagnostico(d: pd.DataFrame) -> None:
    """De onde vem o sinal 'protetor' do esgoto inadequado em adulto e idoso.

    Nos modelos 1 e 2 a exposicao sai protetora nas faixas adultas e a fossa
    septica sai como fator de risco — o inverso da hipotese nas duas pontas ao
    mesmo tempo. Isso quase nunca e efeito; costuma ser medida.

    Duas explicacoes foram testadas:

    causa mal definida   se a morte por diarreia virasse "causa desconhecida"
                         onde falta assistencia, o desfecho perderia casos
                         exatamente onde a exposicao e maior. Existe, mas e
                         fraco: correlacao de 0,18 com a exposicao, e a
                         mediana vai de 6,5% no quartil menos exposto para
                         8,0% no mais exposto. Nao move um coeficiente de
                         0,918.

    sub-registro do      a mortalidade por TODAS as causas em menores de 5
    obito em si          tambem cai com a exposicao (Spearman -0,16). Nao e
                         critivel que se morra menos, de qualquer causa, nos
                         municipios mais pobres e rurais do Maranhao. O que
                         cai e o registro, nao a morte. E como isso atinge
                         numerador e denominador juntos, controlar
                         mortalidade geral nao corrige — o controle esta
                         contaminado pelo mesmo vies.

    Consequencia para a leitura: os coeficientes protetores das faixas adultas
    sao sub-apuracao, nao protecao, e nao devem ser interpretados. Ja o nulo
    dos menores de 5 anos sobrevive ao diagnostico — a lacuna de apuracao entre
    o quartil menos e o mais exposto e de cerca de 5% na mortalidade geral, uma
    ordem de grandeza abaixo do que seria preciso para esconder o efeito que a
    literatura de saneamento preveria.
    """
    z = d[d["faixa"] == "0a4"]
    g = z.groupby("municipio").agg(
        a09=("obitos_a00a09", "sum"), tot=("obitos_total", "sum"),
        mal=("obitos_mal_definidos", "sum"), popf=("pop_faixa", "sum"),
        esg=("esgoto_inadequado_pct", "first")).reset_index()
    g["tx_a09"] = 1e5 * g["a09"] / g["popf"]
    g["tx_tot"] = 1e5 * g["tot"] / g["popf"]
    g["pct_mal"] = 100 * g["mal"] / g["tot"]
    q = pd.qcut(g["esg"], 4, labels=["Q1 menos exp", "Q2", "Q3", "Q4 mais exp"])

    print("=== 6. diagnostico: o 'protetor' e apuracao, nao protecao ===")
    print("menores de 5 anos, taxas por 100 mil crianca-ano\n")
    print(g.groupby(q, observed=True).agg(
        munic=("municipio", "size"), esgoto=("esg", "median"),
        tx_A00A09=("tx_a09", "median"), tx_TODAS_CAUSAS=("tx_tot", "median"),
        pct_mal_definidos=("pct_mal", "median")).round(1).to_string())
    print()
    print("  mortalidade por TODAS as causas vs exposicao (Spearman): "
          f"{g['esg'].corr(g['tx_tot'], method='spearman'):.3f}")
    print("  morrer menos de tudo onde se e mais pobre e mais rural nao e")
    print("  critivel: o que cai e o registro. Como o vies atinge numerador e")
    print("  denominador juntos, controlar mortalidade geral nao corrige.")
    print()


if __name__ == "__main__":
    main()
