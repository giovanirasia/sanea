# -*- coding: utf-8 -*-
"""
Obitos do SIM, por municipio, ano e faixa etaria.

Por que existe um modulo separado, se o SIH ja traz MORTE
  MORTE no SIH e obito **hospitalar**: marca quem morreu durante uma internacao
  que o SUS registrou. Serve no Parana, onde quase todo mundo que adoece grave
  chega a um hospital.

  No Maranhao serve mal, e erra na direcao pior possivel. Quem morre de diarreia
  em municipio sem leito, sem estrada ou sem transporte morre **sem internar**,
  e some do SIH inteiro — nao entra como obito nem como internacao. O
  sub-registro, portanto, e maior exatamente onde a exposicao e maior, o que
  puxa qualquer associacao para baixo. Usar SIH aqui seria construir o nulo.

  O SIM registra o obito a partir da declaracao, independente de internacao. E
  a base certa quando o desfecho e morte e a hipotese envolve acesso.

Por que o Maranhao
  No Parana a doenca de veiculacao hidrica letal em crianca praticamente nao
  existe mais: 58 obitos em menores de 5 anos em 19 anos, no estado inteiro,
  poucos demais para modelar. Nao se mede variacao no que ja foi resolvido. O
  Maranhao tem a pior cobertura de saneamento do pais — mediana de 79,9% de
  domicilios com destino inadequado de esgoto, contra 43,4% do Parana — e a
  mortalidade infantil por diarreia ainda existe.

Fonte
  arquivos DO (declaracao de obito) do SIM no FTP do DATASUS, um por UF/ano.
  DOMA1996 a DOMA2024; aqui de 2008 em diante, para casar com o painel de
  covariaveis. O SIM tem defasagem maior que o SIH: 2024 e o ultimo fechado.

Codificacao da idade, que nao e a do SIH
  No SIH ha dois campos, IDADE e COD_IDADE. No SIM ha um so, de tres
  caracteres, onde o primeiro digito e a unidade e os dois seguintes a
  quantidade: 0 minutos, 1 horas, 2 dias, 3 meses, 4 anos, 5 anos acima de 100
  (soma-se 100). Assim '310' e dez meses e '410' e dez anos. Ler o campo como
  numero misturaria as duas coisas — e obito de lactente e justamente o que
  este modulo existe para contar.

Limites
  - CODMUNRES e o municipio de residencia declarado, nao onde a pessoa adoeceu
  - o SIM tem sub-registro proprio, historicamente maior no Norte e Nordeste e
    caindo ao longo da serie; parte da tendencia temporal e melhora de
    cobertura do sistema, nao queda de mortalidade
  - causa basica mal definida (capitulo R) absorve parte dos obitos que
    deveriam estar em A00-A09, e essa mal definicao tambem e maior onde ha
    menos assistencia

Saida
  dados/sim_{escopo}_anual.csv   obitos por municipio, ano e faixa etaria
"""

from __future__ import annotations

import ftplib
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from dbfread import DBF

import datasus_dbc

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import escopo                                                  # noqa: E402

# "br" nao e unidade de analise deste repositorio: e o recorte nacional
# publicado, e por isso nao entra no escopo.py
ESCOPO = os.environ.get("SANEA_ESCOPO", "bp3")
if ESCOPO != "br":
    ESCOPO = escopo.atual()

PARCIAIS = RAIZ / "dados" / "bruto" / "sim"


def _nome_saida() -> str:
    """Nome do arquivo de saida, com o periodo quando nao for o padrao.

    Sem isso, rodar a extensao retroativa (1996-2007) sobrescreveria o painel
    nacional publicado, que e de 2008-2024, com um arquivo de outro periodo e
    mesmo nome. O erro so apareceria depois, em quem lesse o CSV esperando a
    serie publicada.
    """
    if ESCOPO != "br":
        return f"sim_{ESCOPO}_anual.csv"
    if (ANO_INICIO, ANO_FIM) == (2008, 2024):
        return "obitos_hidricas_br.csv"
    return f"obitos_hidricas_br_{ANO_INICIO}_{ANO_FIM}.csv"
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
CENSO_BR = RAIZ / "dados" / "censo_domiciliar_br.csv"

FTP_HOST = "ftp.datasus.gov.br"
FTP_ARQ = "/dissemin/publicos/SIM/CID10/DORES/DO{sigla}{ano}.dbc"
# o painel publicado comeca em 2008, para casar com as covariaveis municipais.
# O teste de tendencia previa precisa do periodo ANTERIOR ao tratamento, e o
# SIM comeca em 1996 — dai o override por variavel de ambiente.
ANO_INICIO = int(os.environ.get("SANEA_ANO_INICIO", "2008"))
ANO_FIM = int(os.environ.get("SANEA_ANO_FIM", "2024"))
PARALELO = int(os.environ.get("SANEA_PARALELO", "4"))

SAIDA = RAIZ / "dados" / _nome_saida()

UF_DE_SIGLA = {"RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16,
               "TO": 17, "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25,
               "PE": 26, "AL": 27, "SE": 28, "BA": 29, "MG": 31, "ES": 32,
               "RJ": 33, "SP": 35, "PR": 41, "SC": 42, "RS": 43, "MS": 50,
               "MT": 51, "GO": 52, "DF": 53}
SIGLAS_BR = list(UF_DE_SIGLA)


def siglas() -> list[str]:
    """UFs a baixar. O cache e por sigla+ano, que e a chave do arquivo no FTP,
    entao um recorte estadual e o nacional reaproveitam o mesmo disco."""
    return SIGLAS_BR if ESCOPO == "br" else [escopo.sigla(ESCOPO)]

COLUNAS = ["CODMUNRES", "CAUSABAS", "DTOBITO", "IDADE", "SEXO"]

FAIXAS = {"0a4": (0, 5), "5a19": (5, 20), "20a59": (20, 60), "60mais": (60, 200)}

# primeiro digito de IDADE -> quanto vale uma unidade, em anos
UNIDADE = {"0": 1 / (365.25 * 24 * 60), "1": 1 / (365.25 * 24),
           "2": 1 / 365.25, "3": 1 / 12, "4": 1.0, "5": 1.0}


def idade_anos(codigo) -> float | None:
    """Idade em anos a partir do campo IDADE do SIM."""
    s = str(codigo).strip()
    if len(s) != 3 or not s.isdigit():
        return None
    fator = UNIDADE.get(s[0])
    if fator is None:
        return None
    anos = int(s[1:]) * fator
    return anos + 100 if s[0] == "5" else anos


def cache_completo(parcial: Path) -> bool:
    if not parcial.exists():
        return False
    with open(parcial, encoding="utf-8") as fh:
        return not set(COLUNAS) - set((fh.readline() or "").strip().split(","))


def baixa_dbc(sigla: str, ano: int, destino: Path, tentativas: int = 4) -> None:
    """Baixa um DO do FTP, com recuo progressivo em falha transitoria.

    A distincao importa e nao e detalhe. error_perm e o servidor dizendo que o
    arquivo nao existe — nao adianta insistir. Qualquer outra coisa (gaierror
    de DNS, timeout, conexao derrubada) e transitoria, e tratar as duas do
    mesmo jeito significa deixar buraco silencioso no painel: a UF-ano some do
    resultado e nada no arquivo final denuncia a ausencia.

    Isso aconteceu de verdade na primeira rodada nacional — 41 arquivos
    perdidos por gaierror, quatro processos resolvendo o mesmo host ao mesmo
    tempo.
    """
    for tentativa in range(tentativas):
        ftp = None
        try:
            ftp = ftplib.FTP(FTP_HOST, timeout=300)
            ftp.login()
            with open(destino, "wb") as saida:
                ftp.retrbinary("RETR " + FTP_ARQ.format(sigla=sigla, ano=ano),
                               saida.write)
            return
        except ftplib.error_perm:
            raise                                  # arquivo nao existe mesmo
        except Exception:
            if tentativa == tentativas - 1:
                raise
            time.sleep(2 ** tentativa)
        finally:
            if ftp is not None:
                try:
                    ftp.quit()
                except Exception:
                    ftp.close()


def ano_bruto(sigla: str, ano: int) -> pd.DataFrame | None:
    """Obitos de residentes numa UF, num ano. Cacheia o filtrado.

    O filtro pelo prefixo do codigo IBGE nao e redundante com o arquivo ser da
    UF: o SIM guarda o obito na UF de ocorrencia, e CODMUNRES pode apontar para
    outro estado — quem morreu viajando ou em hospital de referencia fora. Esse
    obito pertence ao denominador da UF de residencia, nao a esta.
    """
    parcial = PARCIAIS / f"{sigla.lower()}_{ano}.csv"
    if cache_completo(parcial):
        return pd.read_csv(parcial, dtype={"CODMUNRES": str, "IDADE": str})

    prefixo = str(UF_DE_SIGLA[sigla])
    tmp = Path(tempfile.mkdtemp())
    try:
        dbc, dbf = tmp / "a.dbc", tmp / "a.dbf"
        try:
            baixa_dbc(sigla, ano, dbc)
        except Exception as erro:
            print(f"  {sigla} {ano}: indisponivel ({type(erro).__name__})",
                  flush=True)
            return None
        datasus_dbc.decompress(str(dbc), str(dbf))
        linhas = [
            {c: r.get(c) for c in COLUNAS}
            for r in DBF(str(dbf), encoding="latin-1")
            if str(r.get("CODMUNRES") or "").startswith(prefixo)
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    df = pd.DataFrame(linhas, columns=COLUNAS)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv = parcial.with_suffix(".csv.parcial")
    df.to_csv(tmp_csv, index=False)
    tmp_csv.replace(parcial)
    return df


def _prefetch(args: tuple[str, int]) -> tuple[str, int]:
    ano_bruto(*args)
    return args


def preenche_cache() -> None:
    faltam = [(s, a) for s in siglas() for a in range(ANO_INICIO, ANO_FIM + 1)
              if not cache_completo(PARCIAIS / f"{s.lower()}_{a}.csv")]
    if not faltam:
        return
    PARCIAIS.mkdir(parents=True, exist_ok=True)
    print(f"faltam {len(faltam)} arquivos; {PARALELO} processos", flush=True)
    with ProcessPoolExecutor(max_workers=PARALELO) as pool:
        for i, f in enumerate(as_completed(
                [pool.submit(_prefetch, a) for a in faltam]), 1):
            try:
                f.result()
            except Exception as erro:
                print(f"  falhou: {type(erro).__name__}: {erro}", flush=True)
            if i % 25 == 0:
                print(f"  {i}/{len(faltam)}", flush=True)

    # o painel so vale se estiver completo. Sem esta checagem, uma falha de
    # rede vira UF-ano ausente do resultado, e nada no CSV final denuncia.
    ainda = [(s, a) for s, a in faltam
             if not cache_completo(PARCIAIS / f"{s.lower()}_{a}.csv")]
    if ainda:
        resumo = ", ".join(f"{s} {a}" for s, a in ainda[:10])
        raise SystemExit(
            f"\n{len(ainda)} arquivos nao baixaram: {resumo}"
            f"{' ...' if len(ainda) > 10 else ''}\n"
            "Rode de novo — o cache retoma de onde parou. Se persistir para a "
            "mesma UF-ano, confira se o arquivo existe no FTP do DATASUS.")


def agrega(sigla: str, ano: int, mapa: set[str] | None) -> list[pd.DataFrame]:
    """Contagens por municipio e faixa etaria, de um arquivo UF/ano."""
    d = ano_bruto(sigla, ano)
    if d is None or d.empty:
        return []

    # ate 2005 o SIM grava CODMUNRES com 7 digitos (codigo IBGE completo, com
    # verificador); de 2006 em diante, com 6. Truncar uniformiza, e os 6
    # primeiros digitos sao os mesmos nos dois formatos — Sao Paulo e 3550308
    # e 355030. Sem isso os anos antigos nao casam com nenhuma chave de 6
    # digitos e somem inteiros no merge, sem erro nenhum.
    d = d.assign(CODMUNRES=d["CODMUNRES"].astype(str).str[:6])

    # o SIM tem um codigo por UF para "municipio ignorado" (210000 no MA),
    # que nao e municipio e nao tem denominador populacional
    d = d[~d["CODMUNRES"].str.endswith("0000")]
    if mapa is not None:
        d = d[d["CODMUNRES"].isin(mapa)]
    if d.empty:
        return []

    cid = d["CAUSABAS"].fillna("").str.strip().str.upper().str[:3]
    d = d.assign(
        hidrica=((cid >= "A00") & (cid <= "A09")).astype(int),
        # capitulo XVIII do CID-10: sintomas, sinais e achados anormais, ou
        # seja, obito sem causa determinada. E o indicador padrao de qualidade
        # do registro, e importa por um motivo especifico: onde nao ha
        # assistencia medica, a morte por diarreia tende a ser codificada como
        # mal definida em vez de A00-A09. Isso subtrai casos do desfecho
        # exatamente onde a exposicao e maior — vies que o controle de
        # mortalidade geral nao pega, porque o obito esta registrado, so esta
        # na gaveta errada. Por isso vai publicado junto.
        mal_definida=((cid >= "R00") & (cid <= "R99")).astype(int),
        anos=[idade_anos(i) for i in d["IDADE"]])
    d = d.dropna(subset=["anos"])

    saida = []
    for faixa, (lo, hi) in FAIXAS.items():
        f = d[(d["anos"] >= lo) & (d["anos"] < hi)]
        if f.empty:
            continue
        g = f.groupby("CODMUNRES").agg(
            obitos_a00a09=("hidrica", "sum"),
            obitos_mal_definidos=("mal_definida", "sum"),
            obitos_total=("hidrica", "size")).reset_index()
        saida.append(g.assign(ano=ano, faixa=faixa))
    print(f"{sigla} {ano}: {len(d):,} obitos, "
          f"{int(d['hidrica'].sum()):,} por A00-A09", flush=True)
    return saida


def main() -> None:
    preenche_cache()

    mapa = None
    if ESCOPO != "br" and not escopo.uf_inteira(ESCOPO):
        mun = pd.read_csv(MUNICIPIOS)
        mapa = {str(c)[:6] for c in mun["cod_ibge"]}

    linhas = [g for sigla in siglas()
              for ano in range(ANO_INICIO, ANO_FIM + 1)
              for g in agrega(sigla, ano, mapa)]

    saida = (pd.concat(linhas, ignore_index=True)
             .rename(columns={"CODMUNRES": "cod6"})
             .groupby(["cod6", "ano", "faixa"], as_index=False)
             [["obitos_a00a09", "obitos_mal_definidos", "obitos_total"]].sum())

    if ESCOPO == "br":
        # nomes vem do dataset de saneamento ja publicado, que e a outra ponta
        # do cruzamento; assim as duas tabelas usam exatamente a mesma grafia
        nomes = pd.read_csv(CENSO_BR)[["cod_ibge", "municipio", "uf"]]
        nomes["cod6"] = nomes["cod_ibge"].astype(str).str[:6]
        saida = (nomes.merge(saida, on="cod6", how="inner")
                 .sort_values(["cod_ibge", "ano", "faixa"])
                 [["cod_ibge", "municipio", "uf", "ano", "faixa",
                   "obitos_a00a09", "obitos_mal_definidos", "obitos_total"]])
    # se um ano inteiro sumiu na agregacao, e erro de chave, nao ausencia de
    # obito — nenhum ano do Brasil tem zero morte. Falhar alto: foi assim que
    # o formato de 7 digitos do CODMUNRES ate 2005 passou despercebido,
    # descartando dez dos doze anos pedidos sem levantar excecao.
    esperados = set(range(ANO_INICIO, ANO_FIM + 1))
    faltando = sorted(esperados - set(saida["ano"].unique()))
    if faltando:
        raise SystemExit(
            f"\n{len(faltando)} anos sumiram na agregacao: {faltando}\n"
            "O cache existe mas nada casou. Suspeite da chave de municipio.")

    saida.to_csv(SAIDA, index=False)

    chave = "cod_ibge" if ESCOPO == "br" else "cod6"
    print()
    print(f"{ESCOPO}: {saida[chave].nunique()} municipios, "
          f"{saida['ano'].nunique()} anos, {len(saida):,} linhas")
    print(f"obitos por A00-A09: {int(saida['obitos_a00a09'].sum()):,} "
          f"de {int(saida['obitos_total'].sum()):,} obitos")
    print(f"mal definidos: {int(saida['obitos_mal_definidos'].sum()):,} "
          f"({100 * saida['obitos_mal_definidos'].sum() / saida['obitos_total'].sum():.1f}%)")
    print()
    print("A00-A09 por faixa etaria:")
    print(saida.groupby("faixa")["obitos_a00a09"].sum().to_string())


if __name__ == "__main__":
    main()
