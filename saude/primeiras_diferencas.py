# -*- coding: utf-8 -*-
"""
Ligar domicilios a rede de esgoto reduz morte infantil por diarreia?

Esta e a primeira analise deste repositorio que nao e transversal, e a mudanca
importa. Todas as anteriores compararam municipios entre si e todas foram
contaminadas pelo mesmo problema: quem tem saneamento pior tambem e mais rural,
mais pobre, mais longe do hospital e tem registro pior. Controlar isso nunca
funcionou — o coeficiente do PIB invertia, a densidade sobrava sem explicacao,
e no Maranhao a exposicao chegou a sair protetora por sub-registro de obito.

Esses confundidores tem uma propriedade que ate agora nao foi usada: sao
praticamente fixos no tempo. Comparar o municipio **com ele mesmo**, antes e
depois da rede chegar, elimina todos de uma vez, sem precisar medi-los.

A pergunta muda junto com o desenho
  Como nivel, cobertura municipal de rede e proxy ruim da exposicao domiciliar
  — este repositorio mostrou isso em detalhe. Como mudanca, ela e um tratamento
  de verdade: a rede chegou ou nao chegou. Entao a pergunta deixa de ser "quem
  esta exposto adoece mais?" e passa a ser "ligar domicilios a rede reduz morte
  infantil?", que e a pergunta que governo consegue responder com orcamento.

  A exposicao vem do Censo, unica fonte comparavel entre 2010 e 2022. Ver
  saneamento/comparabilidade_censo.py: a medida melhor (esgotamento inadequado
  do domicilio) nao atravessa os dois censos porque a categoria de fossa
  septica foi redividida; a cobertura de rede atravessa.

Desenho
  unidade    municipio, dois periodos
  antes      2008-2012   (centrado em 2010, ano do Censo)
  depois     2020-2024   (centrado em 2022)
  exposicao  variacao da cobertura de rede entre os censos, por 10 p.p.
  desfecho   obitos por A00-A09 em menores de 5 anos
  denominador obitos por TODAS as causas em menores de 5, no mesmo periodo

Por que o denominador e obito total, e nao populacao
  Duas razoes, e a segunda e o motivo real.

  A primeira e pratica: dispensa serie populacional por faixa etaria para 5.570
  municipios em dois periodos, que exigiria estrutura etaria de dois censos
  aplicada a estimativas anuais.

  A segunda e que **o sub-registro se cancela**. No Maranhao ficou demonstrado
  que a mortalidade registrada por todas as causas cai onde o registro e pior,
  e que isso atinge numerador e denominador juntos — por isso controlar
  mortalidade geral nao corrigia nada. Usando obito total como denominador, o
  que se modela e a **fracao dos obitos infantis atribuivel a doenca
  intestinal**, e um municipio que registra metade dos obitos entra com a mesma
  fracao de um que registra todos.

  O preco: se o saneamento tambem reduzir outras causas de morte infantil — por
  desnutricao, por exemplo — a fracao subestima o efeito. E vies conservador.

Estimacao
  Poisson com efeitos fixos de municipio e offset log(obitos totais). Com dois
  periodos, essa verossimilhanca tem forma condicional fechada: condicionando
  no total de casos do municipio, o numero de casos do segundo periodo e
  binomial, e o modelo vira

      logit(p_i) = beta * (x_i2 - x_i1) + gama + log(N_i2 / N_i1)

  onde x e a cobertura de rede, N os obitos totais e gama o efeito comum de
  tempo. Isso e exatamente o estimador de efeitos fixos, sem precisar de 5.570
  variaveis indicadoras, e municipios sem nenhum obito por A00-A09 nos dois
  periodos saem sozinhos da conta — como devem, porque nao informam nada sobre
  o efeito.

O controle negativo continua valendo
  Se a rede reduzir morte infantil por transmissao hidrica, o efeito tem de
  aparecer em menor de 5 e nao em adulto de 20 a 59. Se aparecer igual nos
  dois, o que se mede e alguma coisa que mudou junto com a rede — investimento
  municipal, urbanizacao, acesso a saude — e nao saneamento.

Resultado — e por que ele vale menos que os anteriores

  Nulo em tudo. Por 10 p.p. de expansao de rede, sobre a fracao de obitos
  infantis atribuivel a A00-A09:

    menores de 5      1,022  (IC 0,963-1,084, p=0,48)
    20 a 59           1,021  (p=0,49)      <- controle negativo
    60 ou mais        0,989  (p=0,71)
    expansao > 20pp   1,093  (IC 0,894-1,337, p=0,39)

  Nenhuma regiao mostra efeito, inclusive Norte e Nordeste, onde a carga era
  alta.

  **Este nulo nao tem o mesmo peso dos outros deste repositorio, e a diferenca
  precisa ficar explicita.** Nos casos anteriores havia como mostrar que o
  desenho enxergaria um efeito se houvesse: a assinatura etaria discriminava, o
  intervalo era estreito, a troca de base confirmou o diagnostico. Aqui nao.

  O controle positivo tambem deu nulo: a variacao de rede nao prediz nem a
  mudanca na fracao de causas mal definidas (1,050, p=0,17 em menores de 5),
  que e marcador de desenvolvimento do servico de saude. Ou seja, nao consegui
  demonstrar que este desenho detectaria alguma coisa. Some-se a isso que o
  tratamento binario tem intervalo largo (0,894-1,337, nao exclui reducao de
  10%), que o denominador de mortalidade proporcional e conservador por
  construcao, e que nao ha teste de tendencia previa.

  A medida em si nao e ruido: a correlacao entre o nivel de 2010 e o de 2022 e
  0,933, e o desvio-padrao da mudanca (11,9 p.p.) e mais de um terco do desvio
  do nivel (31,5). O problema nao e a variavel ser lixo; e nao haver como
  provar a sensibilidade do desenho.

  Conclusao honesta: **isto e um nulo fraco, e nao deve ser contado como quarta
  confirmacao da tese do repositorio.** E um desenho que rodou e nao achou.

O que este modulo achou de fato, e nao e causal

  A expansao de rede entre 2010 e 2022 passou ao largo de quem nao tinha nada.
  Por quartil de cobertura inicial:

    quartil                cobertura 2010   expansao media
    Q1 (sem rede)                    0,4%          +4,7 pp
    Q2                               3,9%         +10,1 pp
    Q3                              34,8%         +12,9 pp
    Q4 (ja tinha)                   77,1%          +5,4 pp

  Quem comecou sem nada ganhou um terco do que ganhou quem ja tinha um terco de
  cobertura. O investimento foi para onde ja havia rede a estender, nao para
  onde era preciso comecar do zero — o que e caro e dificil, e explica o padrao
  sem precisar supor ma-fe. Este e um achado descritivo sobre politica publica,
  independe de qualquer estimativa causal, e e o resultado mais solido daqui.

  Vale registrar o pano de fundo: no periodo, obitos infantis por A00-A09
  cairam 55% no pais (5.243 em 2008-2012 para 2.383 em 2020-2024), enquanto os
  de adultos subiram. A queda infantil foi grande e razoavelmente uniforme, o
  que e o padrao esperado de causas nacionais e simultaneas — vacina de
  rotavirus desde 2006, reidratacao oral, transferencia de renda, tratamento de
  agua. Qualquer efeito municipal de esgoto teria de aparecer por cima disso.

Limites
  - primeira diferenca remove confundimento de NIVEL fixo, nao tendencia
    diferencial. Municipio que recebeu rede nao foi sorteado: e o que recebeu
    investimento, provavelmente maior e em crescimento. Se essas cidades ja
    vinham melhorando mais rapido por outros motivos, o efeito e superestimado
  - com dois pontos de exposicao nao ha como testar tendencia previa, que e a
    checagem central de credibilidade deste tipo de desenho. Seria preciso
    serie anual de cobertura (SNIS)
  - a cobertura de rede tem cauda de valores implausiveis: 42 municipios
    "perdem" mais de 10 p.p. entre os censos. Sao excluidos por padrao
  - proporcao de obitos, nao taxa: mede composicao de causa, nao risco absoluto
  - continua sendo o municipio como unidade, com todas as ressalvas ecologicas

Saida
  dados/primeiras_diferencas_br.csv   o painel de dois periodos, por faixa
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "saneamento"))
from comparabilidade_censo import censo2010                    # noqa: E402

OBITOS = RAIZ / "dados" / "obitos_hidricas_br.csv"
CENSO_BR = RAIZ / "dados" / "censo_domiciliar_br.csv"
SAIDA = RAIZ / "dados" / "primeiras_diferencas_br.csv"

ANTES = (2008, 2012)
DEPOIS = (2020, 2024)
# perda de cobertura de rede maior que isto nao acontece de verdade; e ruido de
# classificacao entre os censos, e diferenciar so amplifica
PERDA_IMPLAUSIVEL = -5.0


def painel() -> pd.DataFrame:
    d = pd.read_csv(OBITOS)
    d["periodo"] = np.select(
        [d["ano"].between(*ANTES), d["ano"].between(*DEPOIS)],
        ["antes", "depois"], default="")
    d = d[d["periodo"] != ""]

    contagens = ["obitos_a00a09", "obitos_mal_definidos", "obitos_total"]
    g = (d.groupby(["cod_ibge", "municipio", "uf", "faixa", "periodo"],
                   as_index=False)[contagens].sum())

    largo = g.pivot_table(index=["cod_ibge", "municipio", "uf", "faixa"],
                          columns="periodo", values=contagens,
                          fill_value=0).reset_index()
    largo.columns = ["_".join(c).strip("_") for c in largo.columns]

    exp = censo2010().merge(
        pd.read_csv(CENSO_BR)[["cod_ibge", "esgoto_rede_pct"]], on="cod_ibge")
    exp["d_rede"] = exp["esgoto_rede_pct"] - exp["rede_2010"]

    return largo.merge(exp[["cod_ibge", "rede_2010", "esgoto_rede_pct",
                            "d_rede"]], on="cod_ibge")


def estima(d: pd.DataFrame, rotulo: str, termo: str = "d_rede_10pp") -> None:
    """Poisson de efeitos fixos, na forma condicional binomial."""
    # so informa quem teve ao menos um obito por A00-A09 em algum periodo, e
    # quem tem obito total nos dois (o offset exige razao definida)
    u = d[(d["casos"] > 0) & (d["n_antes"] > 0) & (d["n_depois"] > 0)].copy()
    if len(u) < 30:
        print(f"{rotulo}\n  municipios de menos ({len(u)})\n")
        return

    X = sm.add_constant(u[[termo]].astype(float))
    m = sm.GLM(u[["y_depois", "y_antes"]], X,
               family=sm.families.Binomial(),
               offset=np.log(u["n_depois"] / u["n_antes"])).fit(cov_type="HC1")
    ic = m.conf_int()
    p = m.pvalues[termo]
    print(rotulo)
    print(f"  {termo:<14}{np.exp(m.params[termo]):>7.3f}  "
          f"IC {np.exp(ic.loc[termo, 0]):.3f} a {np.exp(ic.loc[termo, 1]):.3f}  "
          f"p={p:.4f}{' *' if p < 0.05 else ''}")
    print(f"  municipios={len(u):,}  obitos A00-A09={int(u['casos'].sum()):,}"
          f"  (antes {int(u['y_antes'].sum()):,}, "
          f"depois {int(u['y_depois'].sum()):,})\n")


def prepara(d: pd.DataFrame, faixa: str, limpa: bool = True) -> pd.DataFrame:
    u = d[d["faixa"] == faixa].rename(columns={
        "obitos_a00a09_antes": "y_antes", "obitos_a00a09_depois": "y_depois",
        "obitos_total_antes": "n_antes", "obitos_total_depois": "n_depois"})
    if limpa:
        u = u[u["d_rede"] > PERDA_IMPLAUSIVEL]
    u = u.copy()
    u["casos"] = u["y_antes"] + u["y_depois"]
    u["d_rede_10pp"] = u["d_rede"] / 10.0
    u["expandiu"] = (u["d_rede"] > 20).astype(float)
    return u


def main() -> None:
    d = painel()
    d.to_csv(SAIDA, index=False)

    m5 = prepara(d, "0a4")
    print(f"painel: {d['cod_ibge'].nunique():,} municipios, "
          f"{ANTES[0]}-{ANTES[1]} contra {DEPOIS[0]}-{DEPOIS[1]}")
    print(f"expansao de rede: mediana {m5['d_rede'].median():.1f} p.p., "
          f"{(m5['d_rede'] > 20).sum():,} municipios acima de 20 p.p.\n")

    print("=== 1. o teste principal ===")
    estima(m5, "menores de 5 anos")

    print("=== 2. controle negativo ===")
    print("se for transmissao hidrica, aqui nao deve aparecer\n")
    estima(prepara(d, "20a59"), "adultos de 20 a 59 anos")
    estima(prepara(d, "60mais"), "60 anos ou mais")

    print("=== 3. tratamento binario: expansao acima de 20 p.p. ===")
    estima(m5, "menores de 5 anos", termo="expandiu")

    print("=== 4. sem excluir a cauda implausivel ===")
    estima(prepara(d, "0a4", limpa=False), "menores de 5 anos, amostra cheia")

    print("=== 5. a exposicao prediz alguma coisa? ===")
    print("controle positivo: se a variacao de rede fosse ruido puro, nao")
    print("preveria nem um marcador de desenvolvimento do servico de saude\n")
    for faixa in ("0a4", "60mais"):
        # trocar o desfecho exige derrubar antes as colunas que prepara() ja
        # renomeou; sem isso ficam dois y_antes e o pandas usa o primeiro,
        # devolvendo silenciosamente o resultado do teste principal
        u = (prepara(d, faixa)
             .drop(columns=["y_antes", "y_depois", "casos"])
             .rename(columns={"obitos_mal_definidos_antes": "y_antes",
                              "obitos_mal_definidos_depois": "y_depois"}))
        u["casos"] = u["y_antes"] + u["y_depois"]
        estima(u, f"causa mal definida, {faixa}")

    print("=== 6. quem recebeu a rede ===")
    e = d.drop_duplicates("cod_ibge")
    print(f"  confiabilidade: correlacao entre o nivel de 2010 e o de 2022 = "
          f"{e['rede_2010'].corr(e['esgoto_rede_pct']):.3f}")
    print(f"  dp do nivel em 2010: {e['rede_2010'].std():.1f} p.p.; "
          f"dp da mudanca: {e['d_rede'].std():.1f} p.p.\n")
    q = pd.qcut(e["rede_2010"], 4,
                labels=["Q1 sem rede em 2010", "Q2", "Q3", "Q4 ja tinha"])
    print(e.groupby(q, observed=True).agg(
        munic=("cod_ibge", "size"), rede_2010=("rede_2010", "median"),
        expansao_media=("d_rede", "mean")).round(1).to_string())
    print()
    print("  A expansao passou ao largo de quem nao tinha nada: o quartil que")
    print("  comecou com 0,4% de cobertura ganhou 4,7 p.p. em doze anos,")
    print("  enquanto o que ja tinha um terco ganhou 12,9.\n")

    print("=== 7. por regiao (exploratorio, nao pre-especificado) ===")
    print("se o efeito existe, deve estar onde a carga era alta\n")
    reg = {u: r for r, us in {
        "Norte": ["RO", "AC", "AM", "RR", "PA", "AP", "TO"],
        "Nordeste": ["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"],
        "Sudeste": ["MG", "ES", "RJ", "SP"], "Sul": ["PR", "SC", "RS"],
        "Centro-Oeste": ["MS", "MT", "GO", "DF"]}.items() for u in us}
    m5r = m5.assign(regiao=m5["uf"].map(reg))
    for r in ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]:
        estima(m5r[m5r["regiao"] == r], r)

    print("Razao < 1 = a rede reduziu a fracao de obitos infantis por A00-A09.")


if __name__ == "__main__":
    main()
