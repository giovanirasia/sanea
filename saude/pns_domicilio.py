# -*- coding: utf-8 -*-
"""
Saneamento e doenca gastrointestinal, no domicilio — sem falacia ecologica.

Por que este modulo e o fim do argumento
  Todo resultado nulo deste repositorio tem a mesma porta de fuga: "pode ser a
  unidade de analise". E ela e procedente — foi o proprio repositorio que a
  demonstrou, quatro vezes. Enquanto exposicao e desfecho forem medidos em
  agregados municipais, a objecao nunca morre, porque a fracao exposta e a
  fracao adoecida nao precisam ser as mesmas pessoas.

  A PNS mede as duas coisas **na mesma casa**. Isso fecha a porta nos dois
  sentidos: se o efeito aparecer aqui, a explicacao ecologica estava certa e o
  municipio o diluia; se nao aparecer nem aqui, o nulo perde a desculpa.

Fonte
  PNS 2019 (IBGE/MS), microdados publicos. 293.726 moradores, 274.592 com
  destino do esgoto informado.

A exposicao e a mesma de censo_domiciliar.py, categoria por categoria
  A01501, "para onde vai o esgoto do banheiro":
    1 rede geral ou pluvial          ]
    2 fossa septica ligada a rede    ] adequado
    3 fossa septica nao ligada       ]
    4 fossa rudimentar               ]
    5 vala                           ] inadequado
    6 rio, lago, corrego ou mar      ]
    7 outra                          -> excluida, categoria residual sem
                                        conteudo sanitario definido
  Isso nao e coincidencia: PNS e Censo usam a mesma classificacao do IBGE.
  A comparacao com os resultados municipais e, portanto, direta.

O desfecho e o ponto fraco, e isso precisa ficar na frente
  Nao existe variavel de diarreia na PNS — nem em 2019 nem em 2013. O modulo
  de criancas menores de 2 anos e sobre aleitamento, testes neonatais e vacina,
  sem morbidade.

  O que existe e J00402 = 06, "problemas gastrointestinais (diarreia / vomito /
  nausea / gastrite / dor de barriga)", como motivo principal de ter deixado de
  fazer atividades habituais nas duas ultimas semanas (J002).

  Tres defeitos, todos atenuando na direcao do zero:
    composto      gastrite e dor de barriga nao sao veiculacao hidrica
    limiar        so conta quem parou de fazer suas atividades
    recordatorio  duas semanas, autorrelatado, por proxy no caso de crianca

  Consequencia para a leitura: **um efeito aqui e forte; um nulo aqui e
  fraco.** O contraste etario, esse sim, e informativo nos dois sentidos.

Desenho
  unidade    morador
  desfecho   problema gastrointestinal como motivo de limitacao (2 semanas)
  exposicao  destino do esgoto do domicilio, e fonte de agua como secundaria
  faixas     0-9 anos, 20-59 (controle negativo), 60+
  controles  situacao urbana/rural, renda domiciliar per capita, regiao
  variancia  erro-padrao agrupado por UPA, a unidade primaria de amostragem

  A estimativa principal e **nao ponderada**, com erro-padrao agrupado por UPA.
  Nao e descuido: o statsmodels avisa que cov_type nao e plenamente suportado
  junto com peso de frequencia, entao o intervalo do modelo ponderado nao e
  confiavel. Fazer certo exigiria pacote de amostragem complexa.

  Para pergunta etiologica o nao ponderado e defensavel — os determinantes do
  peso (regiao, situacao urbana/rural, renda) entram como covariaveis, que e
  a alternativa padrao a ponderar. O modelo ponderado aparece so como
  sensibilidade do ponto estimado.

Por que 0-9 e nao 0-4
  Menores de 5 dao so 214 eventos, o que detectaria razao de chances acima de
  ~1,7 e nao menos. Ate 9 anos sao 438, e doenca de veiculacao hidrica ainda se
  concentra ai. Perde-se especificidade etaria, ganha-se poder — e a
  especificidade que importa mesmo esta no contraste com adulto, que tem 934
  eventos e e o braco bem alimentado.

Resultado (PNS 2019, 273.393 moradores, 1.913 eventos)

  Nulo, e — o que importa mais — **uniforme entre as idades**. Razao de
  chances de problema gastrointestinal, para esgoto inadequado no domicilio:

    0 a 9      1,029  (IC 0,761-1,391, p=0,85)
    20 a 59    1,044  (IC 0,882-1,235, p=0,62)   <- controle negativo
    60+        1,149  (IC 0,852-1,550, p=0,36)

  As tres sao a mesma estimativa. Se houvesse transmissao hidrica, crianca
  teria de superar adulto, e nao supera nem um pouco. E agora isso vale sem a
  desculpa da unidade de analise: exposicao e desfecho estao na mesma casa.

  O descritivo e ainda mais direto. Entre criancas de 0 a 9 anos, por destino
  do esgoto do domicilio:

    rede geral            13.506 moradores   1,20%
    fossa septica          8.261             1,28%
    fossa rudimentar       9.549             1,19%
    vala                   1.432             1,47%

  Domicilio ligado a rede e domicilio com fossa rudimentar tem exatamente a
  mesma taxa. Nao ha gradiente. (As categorias extremas — fossa septica ligada
  e corpo d'agua — dao taxas mais baixas ainda, 0,63% e 0,60%, mas tem 2.234 e
  830 moradores, poucos demais para ler.)

  Agua de fonte vulneravel tambem nao aparece: 0,726 (p=0,15) em 0 a 9.

Quanto peso dar a este nulo

  Menos do que a limpeza do desenho sugere, e a razao esta no desfecho. Se so
  parte dos "problemas gastrointestinais" for diarreia de veiculacao hidrica, e
  se so os casos graves o bastante para interromper atividades entrarem, uma
  razao verdadeira de 1,5 para diarreia apareceria aqui como algo em torno de
  1,2 — dentro do intervalo observado. O nulo nao exclui efeito moderado.

  O que **nao** e questao de poder e a uniformidade entre idades. Essa e a
  mesma assinatura encontrada no Parana, no Maranhao e nas primeiras
  diferencas, e aqui ela aparece num desenho onde a explicacao ecologica nao
  se aplica. Isso e o que este modulo acrescenta de fato.

  E ha sinal de que o vies de relato chega ate aqui: "corpo d'agua", o pior
  destino possivel, tem a menor taxa da tabela. Com 830 moradores pode ser
  ruido, mas e o mesmo padrao que o SIM do Maranhao mostrou — quem tem menos
  acesso relata menos.

Limites
  - transversal: associacao, nao trajetoria
  - o erro-padrao ignora a estratificacao (usa so o conglomerado), o que torna
    o intervalo levemente conservador — erra para o lado seguro
  - morbidade autorrelatada tem gradiente social proprio: quem tem menos acesso
    tende a relatar menos, o mesmo vies que ja apareceu no SIM do Maranhao
  - "deixar de fazer atividades habituais" significa coisa diferente para uma
    crianca de 2 anos e para um adulto que trabalha; o contraste etario carrega
    isso junto

Saida: apenas impressao; nao gera arquivo.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# os microdados sao grandes (455 MB) e nao entram no repositorio; aponte para
# onde estiverem com SANEA_PNS
PADRAO = Path.home() / "Downloads" / "PNS_2019"
RAIZ_PNS = Path(os.environ.get("SANEA_PNS", str(PADRAO)))
ARQUIVO = RAIZ_PNS / "PNS_2019.txt"

# posicao inicial e tamanho, do input SAS que acompanha o dicionario
CAMPOS = {
    "uf": (1, 2), "upa": (10, 9), "situacao": (31, 1),
    "agua": (43, 1), "agua_beber": (46, 1), "esgoto": (52, 1),
    "idade": (117, 3), "parou": (372, 1), "motivo": (375, 2),
    "peso": (1412, 14), "renda_pc": (1527, 8),
}

ADEQUADO = {"1", "2", "3"}      # rede, fossa septica ligada, fossa septica
INADEQUADO = {"4", "5", "6"}    # fossa rudimentar, vala, corpo d'agua
FAIXAS = {"0a9": (0, 10), "20a59": (20, 60), "60mais": (60, 200)}

REGIAO = {**{u: "N" for u in ["11", "12", "13", "14", "15", "16", "17"]},
          **{u: "NE" for u in ["21", "22", "23", "24", "25", "26", "27",
                               "28", "29"]},
          **{u: "SE" for u in ["31", "32", "33", "35"]},
          **{u: "S" for u in ["41", "42", "43"]},
          **{u: "CO" for u in ["50", "51", "52", "53"]}}


def carrega() -> pd.DataFrame:
    if not ARQUIVO.exists():
        raise SystemExit(
            f"nao achei {ARQUIVO}.\n"
            "Baixe os microdados da PNS 2019 e aponte SANEA_PNS para a pasta:\n"
            "  https://ftp.ibge.gov.br/PNS/2019/Microdados/Dados/")

    specs = [(i - 1, i - 1 + t) for i, t in CAMPOS.values()]
    d = pd.read_fwf(ARQUIVO, colspecs=specs, names=list(CAMPOS),
                    dtype=str, encoding="latin-1")

    for c in ("idade", "peso", "renda_pc"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    for c in ("esgoto", "agua", "agua_beber", "situacao", "parou", "motivo"):
        d[c] = d[c].fillna("").str.strip()

    d["gi"] = (d["motivo"] == "06").astype(int)
    d["inadequado"] = d["esgoto"].map(
        lambda x: 1.0 if x in INADEQUADO else (0.0 if x in ADEQUADO else np.nan))
    # poco raso, nascente, chuva e corpo d'agua: fontes vulneraveis
    d["agua_vulneravel"] = d["agua"].map(
        lambda x: 1.0 if x in {"3", "4", "5"} else (0.0 if x in {"1", "2"}
                                                   else np.nan))
    d["rural"] = (d["situacao"] == "2").astype(float)
    d["log_renda"] = np.log(d["renda_pc"].clip(lower=1))
    d["regiao"] = d["uf"].map(REGIAO)
    return d.dropna(subset=["inadequado", "idade", "peso", "log_renda"])


def roda(d: pd.DataFrame, exposicao: str, rotulo: str,
         ponderado: bool = True) -> None:
    if d["gi"].sum() < 40:
        print(f"{rotulo}\n  eventos de menos ({int(d['gi'].sum())})\n")
        return

    cols = [exposicao, "rural", "log_renda"]
    X = pd.get_dummies(d[cols + ["regiao"]], columns=["regiao"],
                       drop_first=True).astype(float)
    X = sm.add_constant(X)
    kw = {"freq_weights": d["peso"]} if ponderado else {}
    m = sm.GLM(d["gi"], X, family=sm.families.Binomial(), **kw).fit(
        cov_type="cluster", cov_kwds={"groups": d["upa"]})

    ic = m.conf_int()
    p = m.pvalues[exposicao]
    print(rotulo)
    print(f"  {exposicao:<17}{np.exp(m.params[exposicao]):>7.3f}  "
          f"IC {np.exp(ic.loc[exposicao, 0]):.3f} a "
          f"{np.exp(ic.loc[exposicao, 1]):.3f}  "
          f"p={p:.4f}{' *' if p < 0.05 else ''}   "
          f"n={len(d):,}  eventos={int(d['gi'].sum()):,}")
    print()


def main() -> None:
    d = carrega()
    print(f"PNS 2019: {len(d):,} moradores com exposicao e controles")
    print(f"  esgoto inadequado: {100 * d['inadequado'].mean():.1f}% "
          f"dos moradores")
    print(f"  problema gastrointestinal em 2 semanas: "
          f"{int(d['gi'].sum()):,} eventos\n")

    faixas = {n: d[(d["idade"] >= lo) & (d["idade"] < hi)]
              for n, (lo, hi) in FAIXAS.items()}

    print("=== 1. esgoto inadequado do domicilio ===")
    print("se for transmissao, 0a9 tem de superar 20a59\n")
    for n, u in faixas.items():
        roda(u, "inadequado",
             n + ("   <-- controle negativo" if n == "20a59" else ""),
             ponderado=False)

    print("=== 2. sensibilidade: com peso amostral ===")
    print("ponto estimado so; o EP agrupado nao e confiavel junto com peso de")
    print("frequencia no statsmodels, e a alternativa correta exigiria pacote")
    print("de amostragem complexa. Serve para ver se a estimativa se move.\n")
    for n, u in faixas.items():
        roda(u, "inadequado", n, ponderado=True)

    print("=== 3. fonte de agua vulneravel (poco raso, nascente, chuva) ===")
    for n, u in faixas.items():
        roda(u.dropna(subset=["agua_vulneravel"]), "agua_vulneravel", n,
             ponderado=False)

    print("=== 4. gradiente por categoria de destino, 0 a 9 anos ===")
    u = faixas["0a9"]
    g = (u.assign(esg=u["esgoto"]).groupby("esg")
         .agg(moradores=("gi", "size"), eventos=("gi", "sum")).reset_index())
    g["pct"] = (100 * g["eventos"] / g["moradores"]).round(2)
    rot = {"1": "rede geral", "2": "fossa septica ligada",
           "3": "fossa septica", "4": "fossa rudimentar", "5": "vala",
           "6": "rio/lago/mar"}
    g["destino"] = g["esg"].map(rot)
    print(g.dropna(subset=["destino"])[
        ["destino", "moradores", "eventos", "pct"]].to_string(index=False))
    print()
    print("Razao > 1 = mais problema gastrointestinal. EP agrupado por UPA.")


if __name__ == "__main__":
    main()
