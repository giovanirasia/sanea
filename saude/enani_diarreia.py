# -*- coding: utf-8 -*-
"""
Saneamento do domicilio e diarreia na crianca — a pergunta original, enfim.

O que este modulo tem que nenhum outro teve
  Cinco analises antes desta nunca mediram diarreia. Mediram internacao por
  A00-A09 (que depende de haver leito), obito (que depende de cartorio) e
  "problema gastrointestinal" da PNS (composto com gastrite e nausea, e so
  quando grave o bastante para interromper atividades). Em todas, o gargalo foi
  o desfecho, nao o desenho.

  O ENANI-2019 pergunta direto: **"a crianca esta ou esteve com diarreia nos
  ultimos 15 dias?"** — a 14.558 criancas menores de 5 anos, com o saneamento
  do proprio domicilio na mesma entrevista.

  E a exposicao usa a mesma classificacao do Censo e da PNS, entao a comparacao
  com todos os resultados anteriores deste repositorio e direta.

Fonte
  ENANI-2019 (UFRJ / Ministerio da Saude), microdados publicos e anonimizados.
  14.558 criancas, 123 municipios, 26 UFs e DF.

Exposicao — p10_esgoto, "o esgoto do banheiro e lancado em"
  1 rede geral de esgoto ou pluvial   ] adequado
  2 fossa septica                     ]
  3 fossa rudimentar                  ]
  4 vala                              ] inadequado
  5 direto para rio, lago ou mar      ]
  6 outra condicao                    -> excluida, residual sem conteudo
                                         sanitario definido

Desfecho — h13_diarreia
  1 sim, 2 nao, 9 nao sabe/nao quis responder (excluido)

Mediador, que nenhuma base anterior tinha
  e03_filtrada_fervida diz se a agua que a crianca bebeu era filtrada ou
  fervida. Se o efeito do esgoto existir e passar pela agua ingerida, ele deve
  ser menor entre quem trata a agua em casa. Isso e teste de mecanismo, nao so
  de associacao — e o repositorio nunca pode faze-lo antes.

Desenho
  unidade    crianca
  desfecho   diarreia nos ultimos 15 dias
  exposicao  destino do esgoto do domicilio; fonte de agua como secundaria
  controles  idade da crianca, regiao, situacao urbana/rural, faixa de renda
  variancia  erro-padrao agrupado pela UPA

  Como na PNS, a estimativa principal e nao ponderada com EP agrupado: o
  statsmodels nao da variancia confiavel junto com peso de frequencia, e os
  determinantes do peso entram como covariaveis. O ponderado aparece como
  sensibilidade do ponto estimado.

Por que um nulo aqui pesaria, e nos anteriores nao
  Com prevalencia de diarreia em torno de 10%, sao ~1.400 eventos contra 214 da
  PNS em menores de 5 — e o desfecho e especifico em vez de composto. O
  intervalo fica estreito o bastante para excluir efeitos da magnitude que a
  literatura de saneamento reporta. Pela primeira vez neste projeto, um nulo
  seria informativo em vez de apenas atenuado.

Resultado — o primeiro sinal positivo do repositorio

  14.533 criancas, 2.343 com diarreia nos ultimos 15 dias (16,1%).

  Pela primeira vez em seis analises, o descritivo tem gradiente monotonico:

    rede geral de esgoto      10.005 criancas   14,9%
    fossa septica              3.202            18,3%
    fossa rudimentar             895            19,7%
    vala                         186            22,0%
    rio, lago ou mar             233            18,9%

  Teste pre-especificado, adequado contra inadequado na classificacao do IBGE:
    1,170  (IC 0,995-1,376, p=0,058)

  Positivo, na direcao certa, e encostando na significancia.

A linha do IBGE parece estar no lugar errado — e isso e POSTERIOR aos dados

  A tabela acima mostra fossa septica (18,3%) mais perto de fossa rudimentar
  (19,7%) que de rede geral (14,9%), embora o IBGE a classifique como adequada.
  Testando o contraste que isso sugere:

    sem ligacao a rede (fossa septica inclusa)   1,180  (IC 1,040-1,339, p=0,010)

    contra rede geral, categoria a categoria:
      fossa septica      1,155  (IC 1,002-1,332, p=0,047)
      fossa rudimentar   1,218  (IC 0,997-1,488, p=0,054)
      vala               1,472  (IC 1,037-2,089, p=0,031)
      rio, lago ou mar   1,148  (IC 0,831-1,587, p=0,40)

  Vala, a pior exposicao com tamanho utilizavel, tem a maior razao. E fossa
  septica, tratada como solucao adequada em todas as analises anteriores deste
  repositorio, carrega risco elevado.

  **Este resultado nasceu de olhar a tabela, nao de hipotese previa.** Nao e
  confirmatorio: e uma hipotese gerada aqui, que precisa de outro dado para ser
  testada. Registrar isso importa mais que o p-valor.

Por que isso reorganiza os nulos anteriores em vez de contradize-los

  Se a divisao correta e "tem rede ou nao tem", e nao "adequado ou inadequado",
  entao todas as analises municipais deste repositorio mediram a exposicao com
  a linha no lugar errado — juntando fossa septica, de risco elevado, com rede
  geral, de risco baixo. Erro de classificacao nao diferencial atenua na
  direcao do zero.

  Somando ao desfecho: internacao depende de leito, obito depende de cartorio,
  "problema gastrointestinal" da PNS mistura gastrite. Corrigindo os dois lados
  ao mesmo tempo — exposicao no domicilio com a linha certa, desfecho
  especifico — aparece sinal. E ele e **pequeno**: razao de chances de 1,18.

  Nenhum nulo anterior precisa ser reinterpretado como erro. Eles medem o que
  mediram, com a variavel que existia. O que muda e a explicacao: nao era so a
  unidade de analise, era tambem a definicao da exposicao.

O mecanismo nao passa pela agua de beber

  Fonte de agua fora da rede geral: 0,953 (p=0,63), nulo. E o efeito do esgoto
  e praticamente igual entre quem filtra ou ferve a agua da crianca (1,105) e
  quem nao trata (1,159). Se a transmissao fosse pela agua ingerida, tratar a
  agua deveria reduzir o efeito, e nao reduz.

  Compativel com transmissao por contato e ambiente — crianca de 2 a 4 anos
  brincando em solo contaminado — e nao pelo copo. Coerente com a faixa etaria
  onde o sinal aparece (2 a 4 anos: 1,239; menores de 2: 1,080), embora os
  intervalos se sobreponham demais para afirmar diferenca.

Limites
  - o achado principal e p=0,058 no teste pre-especificado; so passa de 0,05
    numa especificacao escolhida depois de ver os dados
  - razao de chances de 1,18 e modesta perto do que ensaios de saneamento
    reportam, e pode ser confundimento residual: domicilio com rede difere em
    escolaridade, aglomeracao e higiene, e so parte disso esta controlada
  - transversal: associacao, nao trajetoria
  - diarreia autorrelatada pela mae, recordatorio de 15 dias
  - o ENANI amostrou 123 municipios, nao os 5.570: representa o pais, mas nao
    permite recorte municipal
  - "fossa septica" aqui e uma categoria so, sem separar ligada e nao ligada a
    rede como faz o Censo 2022
  - continua observacional

Saida: apenas impressao; nao gera arquivo.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

# microdados grandes; aponte SANEA_ENANI para a pasta com os CSV
PADRAO = Path.home() / "Downloads" / "ENANI_2019"
RAIZ = Path(os.environ.get("SANEA_ENANI", str(PADRAO)))
ARQUIVO = RAIZ / "data_crianca_calib_anon.csv"

COLUNAS = ["id_upa_anon", "estrato_sel_anon", "peso_crianca_calib",
           "a00_regiao", "a11_situacao", "q07_renda_faixa",
           "idade_anos_comp", "b05a_idade_em_meses",
           "p10_esgoto", "p11_agua", "e03_filtrada_fervida", "h13_diarreia"]

# o CSV publicado traz os ROTULOS, nao os codigos do dicionario — daí o
# mapeamento ser por texto normalizado, e nao pelos numeros 1 a 6
ADEQUADO = {"rede geral de esgoto ou pluvial", "fossa septica"}
INADEQUADO = {"fossa rudimentar", "vala", "direto para rio, lago ou mar"}
# fonte vulneravel a contaminacao; rede geral e a referencia
AGUA_REDE = "rede geral de distribuicao"


def _norm(x) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", str(x))
    return " ".join("".join(c for c in s
                            if unicodedata.category(c) != "Mn").lower().split())


def carrega() -> pd.DataFrame:
    if not ARQUIVO.exists():
        raise SystemExit(
            f"nao achei {ARQUIVO}.\n"
            "Baixe bancos_Enani.csv.zip e aponte SANEA_ENANI para a pasta:\n"
            "  https://dadosabertos.saude.gov.br/dataset/"
            "estudo-nacional-de-alimentacao-e-nutricao-infantil-enani-2019")

    # ponto-e-virgula, virgula decimal e UTF-8. A codificacao nao e detalhe:
    # lido como latin-1, "Nao" vira outra coisa, o filtro do desfecho so deixa
    # passar "Sim", e a prevalencia sai 100% — falha barulhenta, por sorte
    d = pd.read_csv(ARQUIVO, usecols=COLUNAS, sep=";", decimal=",",
                    encoding="utf-8", low_memory=False)
    for c in ("p10_esgoto", "p11_agua", "h13_diarreia",
              "e03_filtrada_fervida", "a11_situacao", "a00_regiao",
              "q07_renda_faixa"):
        d[c] = d[c].map(_norm)

    d = d[d["h13_diarreia"].isin({"sim", "nao"})]
    d["diarreia"] = (d["h13_diarreia"] == "sim").astype(int)
    d["inadequado"] = d["p10_esgoto"].map(
        lambda x: 1.0 if x in INADEQUADO else (0.0 if x in ADEQUADO else np.nan))
    d["agua_vulneravel"] = d["p11_agua"].map(
        lambda x: 0.0 if x == AGUA_REDE else (np.nan if x in ("outra", "nan")
                                              else 1.0))
    d["trata_agua"] = d["e03_filtrada_fervida"].map({"sim": 1.0, "nao": 0.0})
    d["rural"] = (d["a11_situacao"].str.contains("rural")).astype(float)
    # "3 meses", "1 mes", "16 meses" -> numero
    d["idade_m"] = pd.to_numeric(
        d["b05a_idade_em_meses"].astype(str).str.extract(r"(\d+)")[0],
        errors="coerce")
    d["renda"] = d["q07_renda_faixa"]
    return d


def roda(d: pd.DataFrame, exposicao: str, rotulo: str,
         extra: list[str] | None = None, ponderado: bool = False) -> None:
    cols = [exposicao, "idade_m", "rural"] + (extra or [])
    u = d.dropna(subset=cols + ["renda", "a00_regiao"])
    if u["diarreia"].sum() < 30:
        print(f"{rotulo}\n  eventos de menos ({int(u['diarreia'].sum())})\n")
        return

    X = pd.get_dummies(u[cols + ["a00_regiao", "renda"]],
                       columns=["a00_regiao", "renda"], drop_first=True)
    X = sm.add_constant(X.astype(float))
    kw = {"freq_weights": u["peso_crianca_calib"]} if ponderado else {}
    m = sm.GLM(u["diarreia"], X, family=sm.families.Binomial(), **kw).fit(
        cov_type="cluster", cov_kwds={"groups": u["id_upa_anon"]})

    ic = m.conf_int()
    p = m.pvalues[exposicao]
    print(rotulo)
    print(f"  {exposicao:<17}{np.exp(m.params[exposicao]):>7.3f}  "
          f"IC {np.exp(ic.loc[exposicao, 0]):.3f} a "
          f"{np.exp(ic.loc[exposicao, 1]):.3f}  "
          f"p={p:.4f}{' *' if p < 0.05 else ''}   "
          f"n={len(u):,}  diarreia={int(u['diarreia'].sum()):,}")
    print()


def main() -> None:
    d = carrega()
    print(f"ENANI-2019: {len(d):,} criancas com desfecho valido")
    print(f"  prevalencia de diarreia em 15 dias: "
          f"{100 * d['diarreia'].mean():.1f}%  "
          f"({int(d['diarreia'].sum()):,} casos)")
    print(f"  esgoto inadequado: "
          f"{100 * d['inadequado'].mean():.1f}% dos domicilios\n")

    print("=== 1. descritivo por destino do esgoto ===")
    ordem = ["rede geral de esgoto ou pluvial", "fossa septica",
             "fossa rudimentar", "vala", "direto para rio, lago ou mar"]
    g = (d.groupby("p10_esgoto")
         .agg(criancas=("diarreia", "size"), casos=("diarreia", "sum"))
         .reindex(ordem).dropna().reset_index())
    g["pct"] = (100 * g["casos"] / g["criancas"]).round(1)
    g.columns = ["destino", "criancas", "casos", "pct"]
    print(g.to_string(index=False))
    print()

    print("=== 2. o teste principal ===")
    roda(d, "inadequado", "esgoto inadequado -> diarreia")
    roda(d, "inadequado", "o mesmo, com peso amostral (ponto estimado)",
         ponderado=True)

    print("=== 2b. a linha adequado/inadequado esta no lugar certo? ===")
    print("A tabela acima motivou esta pergunta, entao ela e POSTERIOR aos")
    print("dados, nao pre-especificada: fossa septica (18,3%) esta mais perto")
    print("de fossa rudimentar (19,7%) que de rede geral (14,9%), embora o")
    print("IBGE a classifique como adequada.\n")
    u = d[d["p10_esgoto"] != "outra"].copy()
    u["sem_rede"] = (u["p10_esgoto"]
                     != "rede geral de esgoto ou pluvial").astype(float)
    roda(u, "sem_rede", "sem ligacao a rede geral (fossa septica inclusa)")

    print("=== 2c. cada destino contra rede geral ===")
    for cat, nome in [("fossa septica", "c_septica"),
                      ("fossa rudimentar", "c_rudimentar"),
                      ("vala", "c_vala"),
                      ("direto para rio, lago ou mar", "c_corpo_dagua")]:
        u[nome] = (u["p10_esgoto"] == cat).astype(float)
    termos = ["c_septica", "c_rudimentar", "c_vala", "c_corpo_dagua"]
    for t in termos:
        roda(u, t, t, extra=[x for x in termos if x != t])

    print("=== 2d. por faixa de idade ===")
    for lo, hi, nome in [(0, 24, "menores de 2 anos"), (24, 60, "2 a 4 anos")]:
        roda(d[(d["idade_m"] >= lo) & (d["idade_m"] < hi)],
             "inadequado", nome)

    print("=== 3. fonte de agua ===")
    roda(d, "agua_vulneravel", "agua fora da rede geral -> diarreia")

    print("=== 4. mecanismo: o efeito passa pela agua ingerida? ===")
    print("se passar, o esgoto deve pesar menos em quem filtra ou ferve\n")
    for trata, nome in [(0.0, "nao trata a agua da crianca"),
                        (1.0, "filtra ou ferve")]:
        roda(d[d["trata_agua"] == trata], "inadequado", nome)

    print("Razao > 1 = mais diarreia. EP agrupado por UPA.")


if __name__ == "__main__":
    main()
