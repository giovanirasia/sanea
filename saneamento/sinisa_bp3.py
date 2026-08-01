# -*- coding: utf-8 -*-
"""
Indicadores do SINISA 2024 para os municipios da Bacia Parana 3, e a
estratificacao por capacidade de saneamento.

Por que existe: o modelo agregado da bacia inteira nao achou efeito de chuva
sobre internacao por doenca intestinal. Isso nao refuta a tese — a BP3 tem
saneamento razoavel na media, e onde a infraestrutura funciona a chuva nao
vira contaminacao. O efeito, se existe, tem de aparecer onde falta rede.

O achado que define a estratificacao
  15 dos 35 municipios da BP3 nao tem NENHUM dado no modulo de esgoto do
  SINISA. Nao e dado faltante: os 15 aparecem normalmente no modulo de agua,
  com cobertura de 60% a 100%. Eles reportam ao sistema — nao tem rede de
  esgoto para reportar. Sao 43% dos municipios da bacia.

Estratos
  sem rede      15 municipios, sem modulo de esgoto no SINISA
  cobertura baixa  IES0001 abaixo da mediana dos que tem rede
  cobertura alta   IES0001 acima da mediana

Indicadores usados
  IES0001  atendimento da populacao total com rede coletora de esgoto
  IES0007  atendimento dos domicilios com coleta E tratamento
  IAG0001  atendimento da populacao total com rede de agua
  IES3001  extravasamentos de esgoto reparados por extensao de rede
  IES3003  extravasamentos reparados por reclamacao

Limites
  - o SINISA e autodeclarado pelo prestador, com qualidade desigual
  - "sem rede" e inferencia da ausencia no modulo, nao afirmacao do SINISA;
    vale confirmar com o comite antes de publicar
  - IES2004 (tratado sobre coletado) e 100 em todos os municipios da BP3,
    sem variacao, entao nao serve para estratificar

Fonte: planilhas do Ministerio das Cidades, ano de referencia 2024. Nao sao
versionadas aqui por tamanho — ajuste RAIZ_SINISA para onde estiverem.

Saida
  dados/sinisa_bp3.csv
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

# escopo: "bp3" (35 municipios da bacia) ou "parana" (os 399 do estado)
ESCOPO = os.environ.get("SANEA_ESCOPO", "bp3")
if ESCOPO not in ("bp3", "parana"):
    raise SystemExit(f"SANEA_ESCOPO invalido: {ESCOPO}")

SAIDA = RAIZ / "dados" / f"sinisa_{ESCOPO}.csv"
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"

RAIZ_SINISA = Path.home() / "Downloads" / "Projetos e Pastas"
ESGOTO = (RAIZ_SINISA / "SINISA_ESGOTO_Planilhas_2024" / "Esgoto - Base Municipal"
          / "SINISA_ESGOTO_Indicadores_Base Municipal_2024.xlsx")
AGUA = (RAIZ_SINISA / "SINISA_Resultados_Ref2024" / "Água - Base Municipal"
        / "SINISA_AGUA_Indicadores_Base Municipal_2024_Retificação.xlsx")


def _le(caminho: Path) -> pd.DataFrame:
    """Le planilha do SINISA. O cabecalho tecnico nao esta na primeira linha:
    ha um bloco de titulo, e a linha de codigos e a que comeca com cod_IBGE."""
    if not caminho.exists():
        raise SystemExit(f"nao encontrei {caminho}\najuste RAIZ_SINISA")

    aba = pd.ExcelFile(caminho).sheet_names[0]
    topo = pd.read_excel(caminho, sheet_name=aba, header=None, nrows=14)
    linhas = [i for i in range(len(topo))
              if str(topo.iloc[i].tolist()[0]).lower().startswith("cod")]
    if not linhas:
        raise SystemExit(f"nao achei a linha de cabecalho em {caminho.name}")
    h = linhas[-1]

    d = pd.read_excel(caminho, sheet_name=aba, header=None, skiprows=h + 1)
    d.columns = topo.iloc[h].tolist()
    d["cod_IBGE"] = pd.to_numeric(d["cod_IBGE"], errors="coerce")
    return d


def main() -> None:
    bp3 = pd.read_csv(MUNICIPIOS)

    esg = _le(ESGOTO)
    agua = _le(AGUA)

    col_esg = [c for c in ["IES0001", "IES0007", "IES3001", "IES3003"]
               if c in esg.columns]
    col_agua = [c for c in ["IAG0001"] if c in agua.columns]

    d = (bp3[["cod_ibge", "municipio"]]
         .merge(esg[["cod_IBGE"] + col_esg], left_on="cod_ibge",
                right_on="cod_IBGE", how="left")
         .merge(agua[["cod_IBGE"] + col_agua], left_on="cod_ibge",
                right_on="cod_IBGE", how="left", suffixes=("", "_ag"))
         .drop(columns=[c for c in ["cod_IBGE", "cod_IBGE_ag"] if c in
                        list(esg.columns) + ["cod_IBGE", "cod_IBGE_ag"]],
               errors="ignore"))

    for c in col_esg + col_agua:
        d[c] = pd.to_numeric(d[c], errors="coerce")

    tem_rede = d["IES0001"].notna()
    mediana = d.loc[tem_rede, "IES0001"].median()

    d["estrato"] = "sem rede"
    d.loc[tem_rede & (d["IES0001"] < mediana), "estrato"] = "cobertura baixa"
    d.loc[tem_rede & (d["IES0001"] >= mediana), "estrato"] = "cobertura alta"

    d = d[["cod_ibge", "municipio", "estrato"] + col_esg + col_agua]
    d = d.sort_values(["estrato", "IES0001"]).reset_index(drop=True)
    d.to_csv(SAIDA, index=False)

    print(f"mediana de IES0001 entre os {int(tem_rede.sum())} com rede: "
          f"{mediana:.1f}%")
    print()
    print(d.groupby("estrato")
          .agg(municipios=("municipio", "size"),
               esgoto_medio=("IES0001", "mean"),
               agua_media=("IAG0001", "mean"))
          .round(1).to_string())
    print()
    print(d[["municipio", "estrato", "IES0001", "IAG0001"]].to_string(index=False))


if __name__ == "__main__":
    main()
