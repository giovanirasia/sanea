# -*- coding: utf-8 -*-
"""
O nulo do saneamento e efeito real ou erro de medida?

O que motivou: com a cobertura de esgoto do SINISA, o modelo completo deu
1,000 (IC 0,998-1,002, p=0,98). Ausencia de associacao, com intervalo apertado.
A leitura publicada foi que a tese nao se sustenta no Parana.

Ha uma explicacao concorrente que aquele desenho nao conseguia separar. O
SINISA registra a rede do prestador, entao os 157 municipios sem rede — 39% da
amostra — entram todos como cobertura zero. O Censo 2022 mostra que esses 157
nao sao um grupo: a fracao de domicilios com destino inadequado de esgoto vai
de 9,5% a 99,6% entre eles, com desvio-padrao de 26 pontos.

Ou seja, em 39% da amostra a exposicao foi achatada num ponto so. Isso e erro
de medida na variavel independente, e erro de medida atenua coeficiente na
direcao do zero. O nulo pode ser o efeito real, ou pode ser esse achatamento.

Como separar
  1. trocar a exposicao pela do Censo (fracao de domicilios com destino
     inadequado) e refazer o mesmo modelo. Se o nulo persistir com uma variavel
     que nao achata ninguem, o nulo e do saneamento.
  2. o teste decisivo: rodar **so dentro dos 157**. Para o SINISA esse
     subconjunto e uma constante e nao pode produzir coeficiente nenhum. Se o
     Censo encontrar gradiente ali dentro, a variavel antiga estava cega para
     variacao real de exposicao — e o nulo anterior era artefato.
  3. testar o mecanismo, nao so a exposicao. Esgoto cru no solo so vira doenca
     se houver caminho ate a boca; no rural o caminho e poco raso captando
     lencol contaminado pela fossa do vizinho. A interacao
     esgoto_inadequado x agua_poco_raso e esse teste.

Desenho: o mesmo de gradiente_ajustado.py, para que a comparacao seja limpa —
Poisson, offset log(populacao), EP agrupado por municipio, painel 2008-2026.
Só a variavel de exposicao muda.

Resultado (Parana, 397 municipios, 255 mil casos)
  Trocar a variavel, sozinho, nao muda nada: no estado inteiro o Censo da 1,025
  (p=0,24) contra 0,982 (p=0,28) do SINISA. Os dois nulos, o do Censo na
  direcao esperada mas sem significancia.

  Dentro dos 155 sem rede, porem, o Censo enxerga o que o SINISA nao podia:
  1,114 por 10 p.p. de destino inadequado (IC 1,046-1,186, p=0,0008), com a
  fossa septica como espelho protetor (0,914, p=0,023). O achado sobrevive as
  duas checagens que derrubaram achados anteriores neste projeto — controlando
  propensao a internar cai para 1,064 (p=0,024), e com internacoes totais no
  offset da 1,091 (p=0,0025).

  Mas o teste formal de modificacao de efeito NAO confirma que esse subgrupo
  seja diferente do resto: a interacao da 1,067 com p=0,148. Sem isso, "o
  efeito existe so onde nao ha rede" e leitura de subgrupo, nao resultado.

  E ha um sinal de alerta concreto: dentro do subgrupo o PIB per capita volta a
  sair invertido e forte (1,466, p=0,003) — mais renda, mais internacao. Esse
  e exatamente o sintoma que na BP3 foi investigado e classificado como
  estimativa instavel. Sua presenca aqui indica confundimento residual no
  subgrupo, e parte do 1,114 pode ser isso, nao saneamento.

  Conclusao honesta: o nulo publicado era, em parte, erro de medida — havia
  gradiente real onde a variavel antiga via constante. Mas isso ainda nao
  restabelece a tese. O que separa as duas leituras e o desfecho: se for
  transmissao hidrica de verdade, tem de ser mais forte em menores de 5 anos;
  se for artefato de ruralidade e acesso, sera igual em todas as idades.

Limites
  - Censo 2022 e um ponto no tempo aplicado a um painel de 19 anos
  - continua observacional; nada aqui identifica efeito causal
  - a interacao usa a fracao municipal de cada coisa, nao o cruzamento no
    domicilio: um municipio pode ter muita fossa rudimentar e muito poco raso
    sem que sejam as mesmas casas. E falacia ecologica em potencial, e por isso
    o resultado dela e indicio, nao prova de mecanismo.

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
CENSO = RAIZ / "dados" / f"censo_domiciliar_{ESCOPO}.csv"
IDADE = RAIZ / "dados" / f"idade_{ESCOPO}.csv"


def total_internacoes() -> pd.DataFrame:
    """Internacoes por qualquer causa, para controlar propensao a internar."""
    mun = pd.read_csv(RAIZ / "dados" / f"{ESCOPO}_municipios.csv")
    mapa = {str(c)[:6]: m for c, m in zip(mun["cod_ibge"], mun["municipio"])}
    linhas = []
    for arq in sorted((RAIZ / "dados" / "bruto" / "sih").glob(f"{ESCOPO}_*.csv")):
        d = pd.read_csv(arq, dtype={"MUNIC_RES": str}, usecols=["MUNIC_RES"])
        d["municipio"] = d["MUNIC_RES"].map(mapa)
        g = d.dropna(subset=["municipio"]).groupby("municipio").size()
        linhas.append(g.rename("total").reset_index().assign(
            ano=int(arq.stem.split("_")[1][:4])))
    return (pd.concat(linhas, ignore_index=True)
            .groupby(["municipio", "ano"], as_index=False)["total"].sum())


def roda(d: pd.DataFrame, cols: list[str], rotulo: str,
         y: str = "casos", offset: str = "populacao") -> None:
    X = sm.add_constant(d[cols].astype(float))
    m = sm.GLM(d[y], X, family=sm.families.Poisson(),
               offset=np.log(d[offset])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})
    ic = m.conf_int()
    print(rotulo)
    for c in cols:
        p = m.pvalues[c]
        print(f"  {c:<26}{np.exp(m.params[c]):>7.3f}  "
              f"IC {np.exp(ic.loc[c, 0]):.3f} a {np.exp(ic.loc[c, 1]):.3f}  "
              f"p={p:.4f}{' *' if p < 0.05 else ''}")
    print()


def main() -> None:
    d = (pd.read_csv(PAINEL)
         .merge(pd.read_csv(CENSO), on="municipio", how="inner")
         .merge(pd.read_csv(IDADE)[["municipio", "pct_0a4", "pct_60mais"]],
                on="municipio", how="inner"))

    # tudo por 10 pontos percentuais, para as razoes serem comparaveis entre si
    d["esgoto_10pp"] = d["esgoto_pct"] / 10.0            # SINISA, o antigo
    d["inadeq_10pp"] = d["esgoto_inadequado_pct"] / 10.0  # Censo, o novo
    d["poco_10pp"] = d["agua_poco_raso_pct"] / 10.0
    d["septica_10pp"] = d["fossa_septica_pct"] / 10.0
    d["agua_rede_10pp"] = d["agua_rede_pct"] / 10.0

    ctrl = ["log_pib", "log_dens", "ano_c"]
    etario = ["pct_60mais", "pct_0a4"]

    print(f"painel: {d['municipio'].nunique()} municipios, {len(d)} obs, "
          f"{int(d['casos'].sum()):,} casos A00-A09")
    print()

    print("--- as duas medidas de exposicao, mesmo modelo ---")
    roda(d, ["esgoto_10pp"] + ctrl + etario,
         "1) SINISA: cobertura de rede (sinal esperado: < 1)")
    roda(d, ["inadeq_10pp"] + ctrl + etario,
         "2) Censo: domicilios com destino inadequado (sinal esperado: > 1)")

    print("--- o teste decisivo: so onde o SINISA nao ve variacao ---")
    z = d[d["esgoto_pct"] == 0]
    print(f"    {z['municipio'].nunique()} municipios sem rede, {len(z)} obs, "
          f"{int(z['casos'].sum()):,} casos")
    print(f"    exposicao do Censo neste grupo: "
          f"{z['esgoto_inadequado_pct'].min():.1f}% a "
          f"{z['esgoto_inadequado_pct'].max():.1f}%\n")
    roda(z, ["inadeq_10pp"] + ctrl + etario,
         "3) dentro dos sem-rede, o Censo enxerga gradiente?")
    roda(z, ["septica_10pp"] + ctrl + etario,
         "4) e a fossa septica, que o SINISA conta como zero, protege?")

    print("--- o achado do subgrupo aguenta o que derrubou os anteriores? ---")
    tot = total_internacoes()
    z2 = z.merge(tot, on=["municipio", "ano"], how="inner")
    z2["log_tot_pc"] = np.log(z2["total"] / z2["populacao"])
    roda(z2, ["inadeq_10pp", "log_tot_pc"] + ctrl + etario,
         "5) subgrupo + propensao geral a internar")
    roda(z2, ["inadeq_10pp"] + ctrl + etario,
         "6) subgrupo, offset = internacoes totais (nao populacao)",
         offset="total")

    # o teste que decide se o subgrupo e mesmo diferente do resto, em vez de
    # so parecer diferente por ter sido olhado separado
    d["sem_rede"] = (d["esgoto_pct"] == 0).astype(float)
    d["inadeq_x_semrede"] = d["inadeq_10pp"] * d["sem_rede"]
    roda(d, ["inadeq_10pp", "sem_rede", "inadeq_x_semrede"] + ctrl + etario,
         "7) modificacao de efeito: o gradiente difere entre com e sem rede?")

    print("--- mecanismo: esgoto cru precisa de caminho ate a boca ---")
    d["inadeq_x_poco"] = d["inadeq_10pp"] * d["poco_10pp"]
    roda(d, ["inadeq_10pp", "poco_10pp", "inadeq_x_poco"] + ctrl + etario,
         "8) interacao esgoto inadequado x agua de poco raso")

    print("Razao > 1 = mais internacoes. EP agrupado por municipio.")


if __name__ == "__main__":
    main()
