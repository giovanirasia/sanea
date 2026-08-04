# -*- coding: utf-8 -*-
"""
Menores de 5 anos, e um controle negativo para separar as duas explicacoes.

O impasse que este modulo existe para resolver: em exposicao_censo.py, a fracao
de domicilios com destino inadequado de esgoto prediz internacao por A00-A09
dentro dos 155 municipios sem rede (1,114 por 10 p.p., p=0,0008), e o achado
sobrevive as checagens de robustez. Mas ha duas leituras possiveis e o desenho
de la nao as separa:

  transmissao   esgoto cru contamina agua e alimento, e as pessoas adoecem
  artefato      municipios com muita fossa rudimentar sao os mais rurais e
                pobres, e o que se mede e ruralidade — reforcado pelo PIB
                sair invertido justamente nesse subgrupo

O que distingue as duas nao e mais controle, e sim **em quem** o efeito
aparece. Doenca de veiculacao hidrica tem alvo etario conhecido: mata e interna
crianca pequena, muito acima do resto. Se o gradiente for transmissao, tem de
ser bem maior em menores de 5 anos que em adultos. Se for ruralidade ou acesso
a servico, atinge todo mundo por igual, porque distancia do hospital e pobreza
nao escolhem idade.

Por isso o modelo roda em tres faixas, e a do meio e controle negativo:

  0 a 4     onde a transmissao hidrica deve bater mais forte
  20 a 59   controle negativo — adulto saudavel adoece pouco de A00-A09 por
            agua; se o coeficiente for igual ao das criancas, a hipotese de
            transmissao perde
  60+       segunda ponta da vida, tambem sensivel

Desfecho secundario: obito. Internacao depende de haver leito e de a familia
procurar; obito por A00-A09 e evento mais duro e menos sujeito a limiar de
hospitalizacao, que foi justamente o mecanismo que contaminou o efeito da
densidade em densidade.py.

Resultado (Parana, 397 municipios, 2008-2026)

  O controle negativo reprovou a hipotese de transmissao. Dentro dos 155 sem
  rede, por 10 p.p. de esgotamento inadequado:

    0 a 4      1,074  (IC 1,023-1,127, p=0,004)
    20 a 59    1,119  (IC 1,028-1,219, p=0,010)   <- controle negativo
    60+        1,114  (IC 1,053-1,179, p=0,0002)

  Adulto em idade de trabalhar responde MAIS que crianca pequena. Se fosse
  agua e alimento contaminados, a ordem teria de ser a inversa, e com folga.

  No estado inteiro fica ainda mais nitido: em menores de 5 anos o efeito
  desaparece (1,032, p=0,11), enquanto em adultos (1,080, p=0,006) e idosos
  (1,085, p=0,0001) permanece. A exposicao prediz internacao em todo mundo,
  menos exatamente em quem a doenca de veiculacao hidrica mais atinge.

  A fossa septica acompanha o mesmo padrao errado: protege idoso (0,924,
  p=0,015) e nao crianca (0,953, p=0,099).

  Leitura: o gradiente achado em exposicao_censo.py e real, mas nao e
  transmissao. E caracteristica de municipio que eleva internacao em qualquer
  idade — ruralidade, acesso, limiar de internacao, perfil socioeconomico. O
  sinal de alerta do PIB invertido naquele subgrupo apontava para isso.

  A tese central segue de pe como estava: cobertura de saneamento nao explica
  internacao por doenca intestinal no Parana. Agora com um argumento mais
  forte que o nulo anterior — nao e so que a associacao some, e que quando
  aparece tem a assinatura etaria errada.

  Achado lateral que importa para o proximo passo: em 19 anos, o Parana
  inteiro registrou 58 obitos por A00-A09 em menores de 5 anos. Doenca
  hidrica letal em crianca praticamente nao existe mais aqui, e nao se mede
  variacao no que ja foi resolvido. A pergunta continua viva onde a cobertura
  de agua e baixa — nao neste estado.

Por que exigiu rebaixar o SIH
  IDADE no arquivo RD so e interpretavel junto com COD_IDADE: lactente vem
  gravado em dias ou meses, entao 8 pode ser 8 meses. Sem esse campo, qualquer
  corte por menores de 5 mistura bebe com crianca de 8 anos. A extracao antiga
  nao o guardava; sih_bp3.py foi corrigido e o cache, refeito.

Limites
  - o denominador etario vem do Censo 2022 aplicado a todos os anos: a
    populacao de 0 a 4 de cada municipio-ano e estimada como populacao total
    daquele ano vezes a fracao de 2022. O Parana envelheceu no periodo, entao
    isso subestima a base infantil no comeco da serie e infla a taxa la
  - obito por A00-A09 e raro; a serie aguenta o modelo agregado, nao recortes
    finos dentro dele
  - continua observacional

Saida
  dados/menores5_{escopo}.csv   painel municipio-ano por faixa etaria
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "saude"))
from sih_bp3 import idade_anos                                # noqa: E402

ESCOPO = os.environ.get("SANEA_ESCOPO", "parana")
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
CACHE_SIH = RAIZ / "dados" / "bruto" / "sih"
PAINEL = RAIZ / "dados" / f"gradiente_ajustado_{ESCOPO}.csv"
CENSO = RAIZ / "dados" / f"censo_domiciliar_{ESCOPO}.csv"
IDADE = RAIZ / "dados" / f"idade_{ESCOPO}.csv"
SAIDA = RAIZ / "dados" / f"menores5_{ESCOPO}.csv"

FAIXAS = {"0a4": (0, 5), "20a59": (20, 60), "60mais": (60, 200)}


def casos_por_faixa() -> pd.DataFrame:
    """Casos e obitos de A00-A09 por municipio, ano e faixa etaria."""
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
        cid = d["DIAG_PRINC"].fillna("").str.strip().str.upper().str[:3]
        d = d[(cid >= "A00") & (cid <= "A09")]
        if d.empty:
            continue

        d["anos"] = [idade_anos(i, c)
                     for i, c in zip(d["IDADE"], d["COD_IDADE"])]
        d = d.dropna(subset=["anos"])
        d["obito"] = (pd.to_numeric(d["MORTE"], errors="coerce") == 1).astype(int)

        ano = int(arq.stem.split("_")[1][:4])
        for faixa, (lo, hi) in FAIXAS.items():
            f = d[(d["anos"] >= lo) & (d["anos"] < hi)]
            if f.empty:
                continue
            g = f.groupby("municipio").agg(casos=("obito", "size"),
                                           obitos=("obito", "sum")).reset_index()
            linhas.append(g.assign(ano=ano, faixa=faixa))

    return (pd.concat(linhas, ignore_index=True)
            .groupby(["municipio", "ano", "faixa"], as_index=False)
            [["casos", "obitos"]].sum())


def monta() -> pd.DataFrame:
    d = (casos_por_faixa()
         .merge(pd.read_csv(PAINEL)[["municipio", "ano", "populacao",
                                     "log_pib", "log_dens", "ano_c",
                                     "esgoto_pct"]],
                on=["municipio", "ano"], how="inner")
         .merge(pd.read_csv(CENSO)[["municipio", "esgoto_inadequado_pct",
                                    "fossa_septica_pct"]], on="municipio")
         .merge(pd.read_csv(IDADE)[["municipio", "pct_0a4", "pct_20a59",
                                    "pct_60mais"]], on="municipio"))

    # denominador especifico da faixa: a estrutura etaria de 2022 aplicada a
    # populacao do ano. As tres fracoes vem somadas do Censo, cada uma da sua
    # faixa. Tomar 20-59 como complemento das outras duas seria erro: engloba
    # os de 5 a 19, e o tamanho desse pedaco varia com a estrutura etaria do
    # municipio, que por sua vez anda junto com ruralidade — ou seja, o vies
    # entraria exatamente no braco que serve de controle negativo.
    fr = {"0a4": d["pct_0a4"] / 100,
          "20a59": d["pct_20a59"] / 100,
          "60mais": d["pct_60mais"] / 100}
    d["pop_faixa"] = np.select(
        [d["faixa"] == f for f in fr], [d["populacao"] * v for v in fr.values()])

    d["inadeq_10pp"] = d["esgoto_inadequado_pct"] / 10.0
    d["septica_10pp"] = d["fossa_septica_pct"] / 10.0
    return d[d["pop_faixa"] > 0]


def roda(d: pd.DataFrame, y: str, cols: list[str], rotulo: str) -> None:
    if d[y].sum() < 50:
        print(f"{rotulo}\n  eventos de menos ({int(d[y].sum())}); nao modelado\n")
        return
    X = sm.add_constant(d[cols].astype(float))
    m = sm.GLM(d[y], X, family=sm.families.Poisson(),
               offset=np.log(d["pop_faixa"])).fit(
        cov_type="cluster", cov_kwds={"groups": d["municipio"]})
    ic = m.conf_int()
    print(rotulo)
    for c in cols[:1]:
        p = m.pvalues[c]
        print(f"  {c:<14}{np.exp(m.params[c]):>7.3f}  "
              f"IC {np.exp(ic.loc[c, 0]):.3f} a {np.exp(ic.loc[c, 1]):.3f}  "
              f"p={p:.4f}{' *' if p < 0.05 else ''}   "
              f"n={len(d)}, eventos={int(d[y].sum()):,}")
    print()


def main() -> None:
    d = monta()
    d.to_csv(SAIDA, index=False)

    ctrl = ["log_pib", "log_dens", "ano_c"]
    z = d[d["esgoto_pct"] == 0]

    print(f"painel: {d['municipio'].nunique()} municipios")
    print(f"casos A00-A09 por faixa: "
          f"{d.groupby('faixa')['casos'].sum().to_dict()}")
    print(f"obitos por faixa:        "
          f"{d.groupby('faixa')['obitos'].sum().to_dict()}")
    print(f"\nsubgrupo sem rede: {z['municipio'].nunique()} municipios\n")

    print("=== INTERNACAO, dentro dos sem-rede ===")
    print("se for transmissao hidrica, 0a4 tem de superar 20a59 com folga\n")
    for faixa in FAIXAS:
        roda(z[z["faixa"] == faixa], "casos", ["inadeq_10pp"] + ctrl,
             f"esgoto inadequado -> internacao, {faixa}"
             + ("   <-- controle negativo" if faixa == "20a59" else ""))

    print("=== OBITO, dentro dos sem-rede ===")
    for faixa in FAIXAS:
        roda(z[z["faixa"] == faixa], "obitos", ["inadeq_10pp"] + ctrl,
             f"esgoto inadequado -> obito, {faixa}")

    print("=== espelho: fossa septica deve proteger quem o esgoto cru ataca ===")
    for faixa in FAIXAS:
        roda(z[z["faixa"] == faixa], "casos", ["septica_10pp"] + ctrl,
             f"fossa septica -> internacao, {faixa}")

    print("=== estado inteiro, para comparar com o subgrupo ===")
    for faixa in FAIXAS:
        roda(d[d["faixa"] == faixa], "casos", ["inadeq_10pp"] + ctrl,
             f"esgoto inadequado -> internacao, {faixa}")

    print("Razao > 1 = mais eventos por 10 p.p. EP agrupado por municipio.")


if __name__ == "__main__":
    main()
