# -*- coding: utf-8 -*-
"""
Teste de tendencia previa: o desenho de primeiras diferencas se sustenta?

A lacuna que este modulo fecha
  primeiras_diferencas.py compara o municipio com ele mesmo antes e depois da
  rede chegar, o que elimina todo confundidor fixo no tempo. Mas nao elimina
  **tendencia diferencial**: se os municipios que receberam rede ja vinham
  melhorando mais rapido por outros motivos — investimento geral, urbanizacao,
  crescimento economico — o efeito estimado seria deles, nao da rede.

  A checagem padrao para isso e olhar o periodo ANTERIOR ao tratamento. Se o
  futuro tratado e o futuro nao tratado caminhavam juntos antes, a hipotese de
  tendencias paralelas fica plausivel. Se ja divergiam, o desenho nao vale.

Por que sem o SNIS
  A ideia original era usar a serie anual do SNIS para isso. Ela nao esta
  acessivel de forma automatizavel: o portal de serie historica e uma aplicacao
  de formulario com estado de sessao, sem endpoint direto nem API, e a copia do
  Base dos Dados exige BigQuery autenticado.

  Mas o SNIS nao e necessario para esta pergunta. Ele daria o **momento** da
  expansao; o teste de tendencia previa precisa e do **desfecho antes** dela. E
  o SIM comeca em 1996, quatorze anos antes da janela de tratamento.

  O que o SNIS ainda daria de diferente esta em Limites.

Desenho
  tratamento  variacao da cobertura de rede entre os censos de 2010 e 2022,
              a mesma de primeiras_diferencas.py
  periodo pre-A   1998-2002
  periodo pre-B   2006-2010
  periodo pos     2020-2024

  O teste placebo aplica exatamente o mesmo estimador de pre-A para pre-B —
  dois periodos que terminam antes de a expansao acontecer. O tratamento nao
  pode ter efeito ali. Se o coeficiente aparecer mesmo assim, ele esta medindo
  tendencia, nao rede.

  Desfecho e denominador sao os de primeiras_diferencas.py: obitos por A00-A09
  em menores de 5, sobre obitos infantis por todas as causas.

Leitura
  placebo nulo e efeito nulo  o desenho e valido e nao ha efeito a detectar
  placebo nulo e efeito != 0  o desenho e valido e o efeito e interpretavel
  placebo != 0                o desenho nao vale; qualquer efeito e suspeito

Resultado: o placebo REPROVA o desenho

  1998-2002 -> 2006-2010, tudo antes do tratamento:
      0,960 por 10 p.p.  (IC 0,922-1,000, p=0,048)

  2006-2010 -> 2020-2024, o periodo do tratamento:
      1,015 por 10 p.p.  (IC 0,958-1,076, p=0,61)

  O coeficiente que deveria ser nulo nao e. Municipios que **depois** iriam
  expandir a rede ja vinham reduzindo mais rapido a fracao de obitos infantis
  por doenca intestinal, dez anos antes de a obra acontecer. A hipotese de
  tendencias paralelas nao se sustenta, e portanto a estimativa de
  primeiras_diferencas.py **nao pode ser lida como causal**.

  A falha e marginal (p=0,048, intervalo encostando em 1), mas um placebo que
  cai bem na borda nao se descarta — ainda mais quando a funcao dele e
  justamente tranquilizar.

  Nao e artefato de certificacao. A fracao de causas mal definidas caiu muito
  entre os periodos (12,7% em 1996-2007 contra 5,7% em 2008-2024), e melhora
  diferencial dela produziria exatamente esse falso sinal. Mas ela nao se move
  com o tratamento: 1,025 (p=0,34) na mesma janela do placebo. A tendencia
  previa e real.

O que isso faz com a conclusao anterior

  Confirma a cautela, e da a ela um motivo concreto. primeiras_diferencas.py se
  recusou a contar seu nulo como quarta confirmacao da tese, por nao conseguir
  demonstrar que o desenho detectaria um efeito. Agora sabe-se mais: o desenho
  tem premissa violada.

  A direcao da violacao importa e e tranquilizadora num aspecto so. O vies
  aponta para **achar efeito protetor** — os tratados ja vinham melhorando
  sozinhos — e mesmo assim nao se achou nada (1,015, levemente do lado errado).
  Ou seja, o nulo nao esconde um efeito; se algo, e conservador. Mas isso e
  raciocinio sobre a direcao do vies, nao estimativa valida.

  Substantivamente, a tendencia previa diz uma coisa coerente com o resto: a
  expansao de rede foi para municipios que ja estavam numa trajetoria melhor,
  o que e o mesmo fenomeno que o descritivo de primeiras_diferencas.py mostrou
  por outro angulo — o investimento foi para onde ja havia infraestrutura, nao
  para onde faltava tudo. Selecao, e visivel no dado.

Limites
  - municipios criados entre 1997 e 2013 nao existem na janela pre-A e saem do
    teste; o painel de la e menor
  - a codificacao de causa mudou de CID-9 para CID-10 no SIM em 1996, e a
    janela pre-A esta logo depois dessa transicao, quando a qualidade do
    registro ainda estava melhorando
  - o que o SNIS daria e que isto nao da: saber **quando** cada municipio
    expandiu, o que permitiria um estudo de evento — ver o desfecho ano a ano
    em torno da obra, em vez de dois blocos. Tambem permitiria testar se o
    proprio tratamento foi antecipado pelo desfecho
  - as demais ressalvas sao as de primeiras_diferencas.py

Saida: apenas impressao; nao gera arquivo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "saneamento"))
from comparabilidade_censo import censo2010                    # noqa: E402

OBITOS = RAIZ / "dados" / "obitos_hidricas_br.csv"
OBITOS_PRE = RAIZ / "dados" / "obitos_hidricas_br_1996_2007.csv"
CENSO_BR = RAIZ / "dados" / "censo_domiciliar_br.csv"

JANELAS = {"preA": (1998, 2002), "preB": (2006, 2010), "pos": (2020, 2024)}
PERDA_IMPLAUSIVEL = -5.0


def obitos() -> pd.DataFrame:
    """Painel publicado mais a extensao retroativa, so menores de 5."""
    partes = [pd.read_csv(OBITOS)]
    if OBITOS_PRE.exists():
        partes.append(pd.read_csv(OBITOS_PRE))
    else:
        raise SystemExit(
            f"falta {OBITOS_PRE.name}. Gere com:\n"
            "  SANEA_ESCOPO=br SANEA_ANO_INICIO=1996 SANEA_ANO_FIM=2007 "
            "python saude/sim.py")
    d = pd.concat(partes, ignore_index=True)
    return d[d["faixa"] == "0a4"]


def bloco(d: pd.DataFrame, janela: tuple[int, int]) -> pd.DataFrame:
    ini, fim = janela
    u = d[d["ano"].between(ini, fim)]
    return (u.groupby("cod_ibge", as_index=False)
            [["obitos_a00a09", "obitos_total"]].sum())


def painel() -> pd.DataFrame:
    d = obitos()
    largo = None
    for nome, janela in JANELAS.items():
        b = bloco(d, janela).rename(columns={
            "obitos_a00a09": f"y_{nome}", "obitos_total": f"n_{nome}"})
        largo = b if largo is None else largo.merge(b, on="cod_ibge", how="outer")
    largo = largo.fillna(0)

    exp = censo2010().merge(
        pd.read_csv(CENSO_BR)[["cod_ibge", "esgoto_rede_pct"]], on="cod_ibge")
    exp["d_rede_10pp"] = (exp["esgoto_rede_pct"] - exp["rede_2010"]) / 10.0
    exp = exp[exp["d_rede_10pp"] > PERDA_IMPLAUSIVEL / 10.0]
    return largo.merge(exp[["cod_ibge", "d_rede_10pp"]], on="cod_ibge")


def estima(d: pd.DataFrame, de: str, para: str, rotulo: str) -> None:
    """Mesmo estimador de primeiras_diferencas.py, entre duas janelas."""
    u = d[(d[f"y_{de}"] + d[f"y_{para}"] > 0)
          & (d[f"n_{de}"] > 0) & (d[f"n_{para}"] > 0)].copy()
    if len(u) < 30:
        print(f"{rotulo}\n  municipios de menos ({len(u)})\n")
        return

    X = sm.add_constant(u[["d_rede_10pp"]].astype(float))
    m = sm.GLM(u[[f"y_{para}", f"y_{de}"]], X, family=sm.families.Binomial(),
               offset=np.log(u[f"n_{para}"] / u[f"n_{de}"])).fit(cov_type="HC1")
    ic = m.conf_int()
    p = m.pvalues["d_rede_10pp"]
    print(rotulo)
    print(f"  d_rede_10pp    {np.exp(m.params['d_rede_10pp']):>7.3f}  "
          f"IC {np.exp(ic.loc['d_rede_10pp', 0]):.3f} a "
          f"{np.exp(ic.loc['d_rede_10pp', 1]):.3f}  "
          f"p={p:.4f}{' *' if p < 0.05 else ''}")
    print(f"  municipios={len(u):,}  obitos A00-A09={int(u[f'y_{de}'].sum()):,}"
          f" -> {int(u[f'y_{para}'].sum()):,}\n")


def main() -> None:
    d = painel()
    print(f"painel: {len(d):,} municipios com as tres janelas\n")
    for nome, (i, f) in JANELAS.items():
        print(f"  {nome:<5} {i}-{f}: "
              f"{int(d[f'y_{nome}'].sum()):>6,} obitos por A00-A09, "
              f"{int(d[f'n_{nome}'].sum()):>7,} por todas as causas")
    print()

    print("=== PLACEBO: pre-A -> pre-B, tudo antes do tratamento ===")
    print("aqui o coeficiente TEM de ser nulo; se nao for, o desenho nao vale\n")
    estima(d, "preA", "preB", "1998-2002 contra 2006-2010")

    print("=== O EFEITO: pre-B -> pos ===")
    estima(d, "preB", "pos", "2006-2010 contra 2020-2024")

    print("Razao < 1 = a fracao de obitos infantis por A00-A09 caiu mais onde")
    print("a rede se expandiu mais.")


if __name__ == "__main__":
    main()
