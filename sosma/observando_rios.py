# -*- coding: utf-8 -*-
"""
A cobertura municipal de esgoto prediz a qualidade do rio?

Este repositorio testou tres vezes a cadeia inteira de uma vez so

    cobertura municipal -> qualidade do corpo d'agua -> exposicao -> doenca

e recebeu nulo nas tres (BP3, Parana, Maranhao). O diagnostico ate aqui foi
que percentual municipal de cobertura e proxy ruim da exposicao domiciliar,
mas o elo do meio nunca foi medido: nao havia medida de contaminacao
ambiental com abrangencia nacional e chave municipal.

O Observando os Rios da SOS Mata Atlantica e essa medida. Grupos voluntarios
coletam amostras mensais com kit padronizado e o resultado vira um IQA. Aqui
se testa **so a primeira seta**, e o resultado e diagnostico nos dois sentidos:

  se a cobertura NAO prediz o IQA
      a variavel de exposicao falha ja no primeiro elo, e todos os nulos
      posteriores passam a ter uma explicacao unica

  se a cobertura prediz o IQA
      a quebra esta depois, entre ambiente e desfecho medido — o que aponta
      para sub-registro, ja documentado em saude/mortalidade.py

Bate com o mecanismo que a PNS sugeriu (saude/pns_domicilio.py): o efeito nao
passa pela agua de beber e aponta para contato ambiental. IQA de rio e medida
de contato ambiental.

De onde vem o dado
  A pagina do mapa (/indicadores) embute todos os pontos numa variavel
  javascript `var grupos`, sem login e sem XHR. Um request traz tudo. O site
  anuncia 215 pontos e 96 municipios — isso e so o que esta ativo; a variavel
  carrega 1.406 pontos e 321 municipios, incluindo os inativos com historico.

  Cada registro ja vem com municipio_id no codigo IBGE de 6 digitos, entao o
  cruzamento com o Censo e por codigo e nao por nome. O Censo guarda 7 digitos
  (o ultimo e verificador), entao quem trunca e o lado do Censo.

O QUE ESTE DADO NAO E
  1. Nao e serie temporal. O `grupos` traz a ULTIMA analise de cada ponto, e
     so ela. Um ponto medido em 2006 e abandonado aparece ao lado de um medido
     em 2026. Para casar com o Censo 2022 e preciso cortar em >= 2022, e ai
     sobram 129 municipios dos 321.

  2. O IQA quase nao varia. Mediana 29,7, intervalo interquartil de 27 a 32,
     numa escala que vai de 14 a 40+. Isso e pouca variancia para explicar, e
     o teste nasce subdimensionado. Por isso se usa o IQA **numerico** e nunca
     a classe: a classe joga fora a pouca variancia que existe (78% da amostra
     recente cai em "Regular").

  3. Os pontos sao autosselecionados. Grupo escolhe rio que lhe importa, e em
     geral e o sujo. Isso enviesa o nivel do IQA para baixo. Nao enviesa
     necessariamente a inclinacao, que e o que se estima aqui, mas nada
     garante que a selecao seja independente do saneamento do municipio.

  4. Metade da amostra e Sao Paulo. Por isso ha especificacao sem SP e
     especificacao com efeito fixo de UF.

ATENCAO A ESCALA
  O IQA da SOS Mata Atlantica satura perto de 40 ("Otima" e acima de 40,1). O
  IQA da ANA, que este repositorio ja usa em dados/qa_medicoes.csv na coluna
  iqa_ana, vai de 0 a 100. Sao indices diferentes com o mesmo nome. Aqui a
  coluna se chama iqa_sosma justamente para que ninguem os empilhe sem notar.

PROCEDENCIA
  Dado publico e sem login, mas e da SOS Mata Atlantica, coletado por
  voluntarios, e sem termo de uso aberto declarado. Por isso a saida vai para
  dados/bruto/, que neste repositorio e area de trabalho e nao de publicacao.
  Usar para analise e uma coisa; republicar como dataset do SANEA e outra, e
  depende de autorizacao.

Uso:  python sosma/observando_rios.py [--rebaixa]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "sosma"
CACHE = BRUTO / "grupos.json"
SAIDA = BRUTO / "observando_rios.csv"
CENSO = RAIZ / "dados" / "censo_domiciliar_br.csv"

URL = "https://observandoosrios.sosma.org.br/indicadores"
CABECALHO = {"User-Agent": "SANEA/1.0 (pesquisa academica; dados publicos)"}

# a analise transversal so faz sentido contra o Censo de 2022; medicao de 2006
# descreve outro pais. ANO_MIN e o corte principal, ANO_MAX pega digitacao
# impossivel (o dado tem uma medicao em 3004 e uma em 2028).
ANO_MIN = 2022
ANO_MAX = dt.date.today().year


# --------------------------------------------------------------------------
# extracao
# --------------------------------------------------------------------------

def _extrai_array(js: str, marcador: str = "var grupos =") -> list:
    """Recorta o array JSON que segue o marcador, respeitando strings.

    Balancear colchetes ingenuamente quebra: ha nome de grupo com colchete
    dentro da string. Este scanner sabe quando esta dentro de aspas.
    """
    inicio = js.index("[", js.index(marcador) + len(marcador))
    prof, em_string, escape = 0, False, False
    for k in range(inicio, len(js)):
        c = js[k]
        if em_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                em_string = False
            continue
        if c == '"':
            em_string = True
        elif c == "[":
            prof += 1
        elif c == "]":
            prof -= 1
            if prof == 0:
                return json.loads(js[inicio:k + 1])
    raise ValueError("array de grupos nao fecha; a pagina mudou de formato")


def baixa(rebaixa: bool = False) -> list:
    if CACHE.exists() and not rebaixa:
        return json.loads(CACHE.read_text(encoding="utf-8"))

    BRUTO.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers=CABECALHO)
    with urllib.request.urlopen(req, timeout=120) as r:
        pagina = r.read().decode("utf-8", errors="replace")

    grupos = _extrai_array(pagina)
    tmp = CACHE.with_suffix(".json.parcial")
    tmp.write_text(json.dumps(grupos, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE)
    return grupos


def limpa(grupos: list) -> pd.DataFrame:
    d = pd.DataFrame(grupos)

    d["iqa_sosma"] = pd.to_numeric(d["iqa"], errors="coerce")
    d["data"] = pd.to_datetime(d["ultima_analise"], errors="coerce")
    d["ano"] = d["data"].dt.year
    d["cod_ibge6"] = d["municipio_id"].astype(str).str.zfill(6)
    d["ativo"] = d["grupo_status"].astype(str) == "1"

    # ano fora de 2003..hoje e digitacao; nao ha como corrigir, so descartar
    d.loc[(d["ano"] < 2003) | (d["ano"] > ANO_MAX), "ano"] = np.nan

    return d[["grupo_id", "codigo", "cod_ibge6", "municipio_nome",
              "municipio_uf", "rio_monitorado", "grupo_nome", "site_nome",
              "latitude", "longitude", "iqa_sosma", "iqa_status", "ano",
              "data", "ativo"]]


# --------------------------------------------------------------------------
# cruzamento
# --------------------------------------------------------------------------

def cruza(d: pd.DataFrame) -> pd.DataFrame:
    """Junta os pontos ao Censo 2022 pelo codigo IBGE de 6 digitos."""
    c = pd.read_csv(CENSO, dtype={"cod_ibge": str})
    # o Censo guarda 7 digitos, o ultimo e verificador; o lado que trunca e ele
    c["cod_ibge6"] = c["cod_ibge"].str[:6]
    if c["cod_ibge6"].duplicated().any():
        raise SystemExit("truncar o codigo do Censo gerou colisao; investigar")

    j = d.merge(c.drop(columns=["municipio", "uf"]), on="cod_ibge6", how="left")
    return j


def amostra(j: pd.DataFrame) -> pd.DataFrame:
    """Recorte analitico: IQA numerico, medicao recente, Censo casado."""
    return j[j["iqa_sosma"].notna()
             & j["ano"].between(ANO_MIN, ANO_MAX)
             & j["esgoto_inadequado_pct"].notna()].copy()


# --------------------------------------------------------------------------
# estimacao
# --------------------------------------------------------------------------

def estima(d: pd.DataFrame, x: str, rotulo: str,
           fe_uf: bool = False, porte: bool = False) -> None:
    """MQO do IQA contra a exposicao, erro-padrao agrupado por municipio.

    Agrupar importa: 55 municipios tem mais de um ponto e todos compartilham
    exatamente a mesma exposicao, entao os residuos nao sao independentes.
    Ignorar isso estreita o intervalo artificialmente.

    porte=True acrescenta log(domicilios). Nao e refinamento: e o teste do
    confundidor que domina esta regressao — ver secao 6 do main().
    """
    d = d.dropna(subset=[x, "iqa_sosma"])
    if d["cod_ibge6"].nunique() < 15:
        print(f"  {rotulo:<34} municipios de menos ({d['cod_ibge6'].nunique()})")
        return

    # por 10 p.p., para o coeficiente ter tamanho legivel
    X = pd.DataFrame({x: d[x] / 10.0})
    if porte:
        X["log_domicilios"] = np.log(d["domicilios"])
    if fe_uf:
        X = pd.concat([X, pd.get_dummies(d["municipio_uf"], prefix="uf",
                                         drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)

    m = sm.OLS(d["iqa_sosma"], X).fit(
        cov_type="cluster", cov_kwds={"groups": d["cod_ibge6"]})

    b = m.params[x]
    li, ls = m.conf_int().loc[x]
    print(f"  {rotulo:<34} {b:+6.3f}  IC95 [{li:+6.3f}, {ls:+6.3f}]  "
          f"p={m.pvalues[x]:.3f}  n={len(d)} pts / "
          f"{d['cod_ibge6'].nunique()} mun")


def descreve(d: pd.DataFrame) -> None:
    print(f"pontos com IQA numerico e Censo casado: {len(d):,}")
    print(f"municipios: {d['cod_ibge6'].nunique():,}   "
          f"UFs: {d['municipio_uf'].nunique()}")
    q = d["iqa_sosma"].describe(percentiles=[.25, .5, .75])
    print(f"IQA SOSMA: min {q['min']:.1f}  p25 {q['25%']:.1f}  "
          f"mediana {q['50%']:.1f}  p75 {q['75%']:.1f}  max {q['max']:.1f}")
    print(f"esgotamento inadequado: mediana "
          f"{d['esgoto_inadequado_pct'].median():.1f}%  "
          f"dp {d['esgoto_inadequado_pct'].std():.1f} p.p.")
    sp = (d["municipio_uf"] == "SP").mean()
    print(f"participacao de SP: {sp:.0%}\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rebaixa", action="store_true",
                   help="ignora o cache e busca a pagina de novo")
    a = p.parse_args()

    bruto = limpa(baixa(a.rebaixa))
    j = cruza(bruto)
    j.to_csv(SAIDA, index=False)
    d = amostra(j)

    print(f"extraidos {len(bruto):,} pontos, "
          f"{bruto['cod_ibge6'].nunique():,} municipios, "
          f"{bruto['ativo'].sum():,} ativos")
    orfaos = j["esgoto_inadequado_pct"].isna().sum()
    print(f"sem correspondencia no Censo: {orfaos} pontos")
    print(f"recorte analitico: medicao de {ANO_MIN} em diante\n")
    descreve(d)

    print("Coeficiente = variacao do IQA por 10 p.p. a mais de exposicao.")
    print("IQA maior e agua melhor, entao a hipotese preve sinal NEGATIVO.\n")

    print("=== 1. o teste principal ===")
    print("esgotamento inadequado do domicilio, a medida que a ENANI e a PNS")
    print("indicaram ser a certa\n")
    estima(d, "esgoto_inadequado_pct", "inadequado, bruto")
    estima(d, "esgoto_inadequado_pct", "inadequado, efeito fixo de UF",
           fe_uf=True)
    estima(d[d["municipio_uf"] != "SP"], "esgoto_inadequado_pct",
           "inadequado, sem SP")

    print("\n=== 2. a mesma pergunta com a medida oficial ===")
    print("cobertura de rede e o que entra em plano de governo e em meta do")
    print("marco legal; se ela nao prediz nem o rio, isso e um achado\n")
    estima(d, "esgoto_rede_pct", "cobertura de rede, bruto")
    estima(d, "esgoto_rede_pct", "cobertura de rede, efeito fixo de UF",
           fe_uf=True)

    print("\n=== 3. fossa septica: adequada ou inadequada? ===")
    print("a classificacao brasileira e a do JMP contam fossa septica como")
    print("adequada. A ENANI e a PNS sugerem que ela se comporta como")
    print("inadequada. Aqui o desfecho e outro — qualidade do rio, nao")
    print("diarreia infantil — entao e teste independente da mesma hipotese.")
    print("Se fossa septica fosse adequada, o coeficiente seria ~0.\n")
    estima(d, "fossa_septica_pct", "fossa septica")
    estima(d, "fossa_rudimentar_pct", "fossa rudimentar (referencia ruim)")
    estima(d, "esgoto_rede_pct", "rede (referencia boa)")

    print("\n=== 4. controle: fonte de agua ===")
    print("o mecanismo proposto e descarga de esgoto no corpo d'agua. De onde")
    print("vem a agua de beber nao deveria explicar a sujeira do rio, exceto")
    print("pelo que ela carrega de nivel de desenvolvimento\n")
    estima(d, "agua_rede_pct", "agua de rede")

    print("\n=== 5. sensibilidade ===")
    todos = j[j["iqa_sosma"].notna() & j["esgoto_inadequado_pct"].notna()]
    estima(todos, "esgoto_inadequado_pct",
           "amostra cheia, qualquer ano")
    estima(d[d["ativo"]], "esgoto_inadequado_pct", "so pontos ativos")

    mun = (d.groupby("cod_ibge6")
             .agg(iqa_sosma=("iqa_sosma", "mean"),
                  esgoto_inadequado_pct=("esgoto_inadequado_pct", "first"),
                  municipio_uf=("municipio_uf", "first"))
             .reset_index())
    estima(mun, "esgoto_inadequado_pct", "media por municipio")

    print("\n=== 6. o confundidor: porte do municipio ===")
    print("O sinal do teste 1 saiu invertido — mais esgotamento inadequado")
    print("aparece com rio MELHOR. E o controle da secao 4 entrega o motivo:")
    print("agua de rede tambem 'suja' o rio, e agua encanada nao tem como")
    print("sujar rio nenhum. As duas variaveis estao medindo cidade grande.")
    print("Rio urbano e sujo por carga concentrada, industria e canalizacao;")
    print("municipio rural com fossa rudimentar tem rio limpo porque tem")
    print("pouca gente perto dele.\n")
    for v, r in [("esgoto_inadequado_pct", "inadequado"),
                 ("esgoto_rede_pct", "cobertura de rede"),
                 ("fossa_septica_pct", "fossa septica"),
                 ("agua_rede_pct", "agua de rede")]:
        estima(d, v, f"{r} + log(domicilios)", porte=True)
    print("\n  especificacao completa (porte + efeito fixo de UF):")
    for v, r in [("esgoto_inadequado_pct", "inadequado"),
                 ("esgoto_rede_pct", "cobertura de rede"),
                 ("fossa_septica_pct", "fossa septica"),
                 ("agua_rede_pct", "agua de rede")]:
        estima(d, v, f"{r}, completo", fe_uf=True, porte=True)

    lp = np.log(d["domicilios"])
    print(f"\n  correlacao log(domicilios) x esgotamento inadequado: "
          f"{lp.corr(d['esgoto_inadequado_pct']):+.3f}")
    print(f"  correlacao log(domicilios) x IQA:                    "
          f"{lp.corr(d['iqa_sosma']):+.3f}")

    print(f"\nsaida: {SAIDA.relative_to(RAIZ)}")
    print("dado de terceiro, area de trabalho — nao publicar sem autorizacao")


if __name__ == "__main__":
    main()
