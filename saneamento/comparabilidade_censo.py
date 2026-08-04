# -*- coding: utf-8 -*-
"""
O que do Censo 2010 pode ser comparado com o de 2022 — e o que nao pode.

Por que esta pergunta importa: todas as estimativas deste repositorio sao
transversais, e todas foram contaminadas por confundimento de municipio —
ruralidade, acesso a leito, qualidade de registro, limiar de internacao. Esses
confundidores tem uma propriedade util: sao praticamente fixos no tempo. Um
desenho de primeiras diferencas (ou efeitos fixos) os elimina por construcao,
comparando o municipio com ele mesmo antes e depois.

Isso exige exposicao que varie no tempo. O caminho obvio seria a serie do SNIS;
o caminho barato e o proprio Censo, que tem 2010 e 2022 para os 5.570
municipios, sem adesao voluntaria e com o mesmo instrumento.

Mas "mesmo instrumento" e a parte que precisa ser verificada, nao assumida.

O que este modulo mede
  a mudanca 2010->2022 de duas coisas, separadamente:
    rede          domicilio ligado a rede geral ou pluvial — exige obra fisica
    fossa septica solucao individual, declarada pelo morador

Resultado

  No Maranhao o contraste e limpo (217 municipios):
    rede            media +3,4 p.p., dp  5,6, amplitude  -3,8 a +27,4
    fossa septica   media +8,8 p.p., dp 23,3, amplitude -51,2 a +73,3

  Fossa septica nao cai 51 pontos percentuais num municipio em 12 anos. A
  variancia quatro vezes maior e bidirecional e assinatura de reclassificacao,
  nao de mudanca real: o questionario de 2022 dividiu "fossa septica" em ligada
  e nao ligada a rede, acrescentou "fossa filtro" e separou "vala" como
  categoria propria. Um domicilio que se declarou fossa septica em 2010 pode
  aparecer como fossa rudimentar em 2022, e vice-versa.

  No pais inteiro (5.565 municipios) o contraste e o mesmo, porem menos nitido:
    rede            media +8,3 p.p., dp 11,9
    fossa septica   media +4,5 p.p., dp 17,7

  A razao entre os desvios cai de 4x para 1,5x, e a rede tambem tem cauda ruim:
  117 municipios perdem mais de 5 p.p. de cobertura e 42 perdem mais de 10, o
  que tambem nao acontece de verdade. Concentram-se em municipios pequenos de
  Minas Gerais, onde denominador pequeno e a distincao entre rede geral e rede
  pluvial produzem ruido.

  A cauda e pequena — o percentil 1 do delta e -7,9 p.p., ou seja, 99% dos
  municipios estao acima disso — mas existe, e quem usar esta variavel deve
  trata-la (excluir, winsorizar) em vez de fingir que nao viu. Ruido de
  classificacao na exposicao atenua coeficiente na direcao do zero.

Conclusao operacional
  **A medida boa nao e comparavel, e a comparavel e a medida ruim.**

  O esgotamento inadequado do domicilio — a variavel que este repositorio
  mostrou ser superior a cobertura do SINISA — nao pode ser diferenciada entre
  censos. Diferenciar amplifica ruido: se o nivel tem erro de classificacao, a
  diferenca tem o dobro dele.

  Sobra a cobertura de rede, que e justamente a variavel do tipo SINISA. Mas
  aqui ela e legitima, por um motivo que vale escrever: como **nivel**, a
  cobertura municipal e proxy ruim da exposicao domiciliar. Como **mudanca**,
  ela e um tratamento de verdade — a rede chegou ou nao chegou, e e isso que
  governo faz. A pergunta muda de "quem esta exposto adoece mais?" para
  "ligar domicilios a rede reduz morte infantil?", que e a pergunta de politica.

Amplitude disponivel no pais (5.565 municipios com as duas medidas)
  media de expansao +8,3 p.p.; 1.613 municipios expandiram mais de 10 p.p. e
  713 mais de 20 p.p.

    regiao   munic   media    dp   >10pp  >20pp
    S         1188    13,4  16,1     541    324
    CO         466    10,2  14,8     161     94
    NE        1794     7,0   9,1     489    151
    SE        1668     6,7   9,6     368    124
    N          449     3,9   7,9      54     20

  O Norte e fraco demais para identificar qualquer coisa. O Nordeste tem 489
  municipios com expansao relevante, o que basta.

Limites do desenho que isto viabiliza
  - primeira diferenca remove confundimento de NIVEL fixo no tempo, nao
    tendencia diferencial. Municipio que recebeu rede nao e sorteado: e o que
    recebeu investimento, provavelmente maior e em crescimento
  - com dois pontos de exposicao nao da para testar tendencia previa, que e a
    checagem central de credibilidade de um DiD. Para isso seria preciso serie
    anual, e ai sim o SNIS entra — nao para medir o nivel, mas para verificar
    se o tratamento foi antecipado pelo desfecho
  - "rede" tambem mudou de redacao entre censos, so que muito menos: a
    magnitude e a direcao das mudancas sao compativeis com obra

Saida: apenas impressao; nao gera arquivo.
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
CENSO_BR = RAIZ / "dados" / "censo_domiciliar_br.csv"

# tabela 3154, Censo 2010, classificacao 299. As categorias sao mais grossas
# que as de 2022: "outro" agrega fossa rudimentar, vala e corpo d'agua.
SIDRA = ("https://apisidra.ibge.gov.br/values/t/3154/n6/in%20n3%20{uf}"
         "/v/96/p/2010/c299/2942,10941,10942,10962,10963")
ROTULO = {"2942": "total", "10941": "rede", "10942": "septica",
          "10962": "outro", "10963": "sem_banheiro"}

UFS = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
       21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
       28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
       42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}

REGIAO = {r: us for r, us in {
    "N": ["RO", "AC", "AM", "RR", "PA", "AP", "TO"],
    "NE": ["MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"],
    "SE": ["MG", "ES", "RJ", "SP"], "S": ["PR", "SC", "RS"],
    "CO": ["MS", "MT", "GO", "DF"]}.items()}


def censo2010() -> pd.DataFrame:
    linhas: dict[int, dict] = {}
    for uf, sigla in UFS.items():
        destino = BRUTO / f"censo3154_{sigla.lower()}.json"
        if destino.exists():
            js = json.loads(destino.read_text(encoding="utf-8"))
        else:
            with urllib.request.urlopen(SIDRA.format(uf=uf), timeout=300) as r:
                dados = r.read()
            if dados[:2] == b"\x1f\x8b":
                dados = gzip.decompress(dados)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(dados.decode("utf-8"), encoding="utf-8")
            js = json.loads(dados.decode("utf-8"))
            time.sleep(1)
        for r in js[1:]:
            cod, valor = int(r["D1C"]), r["V"]
            n = int(valor) if str(valor).isdigit() else 0
            linhas.setdefault(cod, {"cod_ibge": cod})[ROTULO[r["D4C"]]] = n

    d = pd.DataFrame(linhas.values())
    d["rede_2010"] = (100 * d["rede"] / d["total"]).round(2)
    d["septica_2010"] = (100 * d["septica"] / d["total"]).round(2)
    return d[["cod_ibge", "rede_2010", "septica_2010"]]


def main() -> None:
    d = censo2010().merge(
        pd.read_csv(CENSO_BR)[["cod_ibge", "uf", "esgoto_rede_pct",
                               "fossa_septica_pct"]], on="cod_ibge")
    d["d_rede"] = (d["esgoto_rede_pct"] - d["rede_2010"]).round(2)
    d["d_septica"] = (d["fossa_septica_pct"] - d["septica_2010"]).round(2)

    print(f"{len(d)} municipios com as duas medidas\n")
    print("=== a medida comparavel e a nao comparavel ===")
    print("mudanca 2010->2022, em pontos percentuais\n")
    for col, nome in [("d_rede", "rede (exige obra)"),
                      ("d_septica", "fossa septica (declarada)")]:
        s = d[col]
        print(f"  {nome:<28} media {s.mean():>6.1f}   dp {s.std():>5.1f}   "
              f"de {s.min():>6.1f} a {s.max():>6.1f}")
    print(f"\n  correlacao entre as duas mudancas: "
          f"{d['d_rede'].corr(d['d_septica']):.3f}")
    print("  fossa septica nao cai 50 p.p. em 12 anos: isso e reclassificacao,")
    print("  e diferenciar uma variavel mal classificada dobra o erro dela.\n")

    reg = {u: r for r, us in REGIAO.items() for u in us}
    d["regiao"] = d["uf"].map(reg)
    g = d.groupby("regiao").agg(munic=("cod_ibge", "size"),
                                media=("d_rede", "mean"), dp=("d_rede", "std"))
    g["exp_10pp"] = d[d["d_rede"] > 10].groupby("regiao").size()
    g["exp_20pp"] = d[d["d_rede"] > 20].groupby("regiao").size()

    print("=== amplitude para primeiras diferencas, na variavel que serve ===")
    print("expansao de rede 2010->2022\n")
    print(g.fillna(0).round(1).to_string())
    print(f"\nBrasil: media {d['d_rede'].mean():.1f} p.p.; "
          f"{(d['d_rede'] > 10).sum()} municipios acima de 10 p.p., "
          f"{(d['d_rede'] > 20).sum()} acima de 20.")
    print("Ha variacao suficiente. O que falta e serie anual para testar")
    print("tendencia previa — e so para isso o SNIS seria necessario.")


if __name__ == "__main__":
    main()
