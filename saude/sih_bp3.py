# -*- coding: utf-8 -*-
"""
Internacoes do SIH/SUS nos municipios da Bacia Parana 3, por mes e causa.

A pergunta: nos meses de chuva anomala, sobem as internacoes por doenca de
veiculacao hidrica na bacia? Este script produz o lado da saude; o cruzamento
com chuva fica em outro passo.

Fonte: arquivos RD (AIH reduzida) do SIH/SUS no FTP do DATASUS, um por
UF/mes. Aqui so o Parana, de 2008 (inicio do formato atual) em diante.

Metodo
  - baixa RDPR{AA}{MM}.dbc, descomprime, filtra residentes na BP3 e guarda so
    as colunas usadas; o bruto e descartado porque o DBF descomprimido e
    grande demais para valer o cache
  - o DATASUS usa codigo IBGE de 6 digitos (sem verificador); a juncao com
    bp3_municipios.csv e pelos 6 primeiros digitos
  - agrupa por mes de internacao (DT_INTER) e grupo de CID-10

Grupos de CID (subconjunto da classificacao DRSAI, doencas relacionadas ao
saneamento ambiental inadequado)
  A00-A09  infecciosas intestinais (colera, febre tifoide, shigelose,
           amebiase, diarreias) — na pratica e o unico grupo com volume
           mensal analisavel nesta bacia
  A27      leptospirose — a doenca-simbolo de enchente, mas rara aqui:
           contada para registro, nao da serie mensal
  B15      hepatite A
  B65-B83  helmintiases

Limites
  - internacao nao e incidencia: so entra quem foi hospitalizado pelo SUS, o
    que subestima os casos leves e depende da oferta de leito
  - MUNIC_RES e o municipio de residencia declarado, nao onde a pessoa adoeceu
  - a data usada e a de internacao, que atrasa dias a semanas em relacao a
    exposicao; isso importa ao cruzar com chuva mensal

Saida
  dados/sih_bp3_mensal.csv   contagem por ano, mes e grupo de CID
"""

from __future__ import annotations

import ftplib
import os
import shutil
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import datasus_dbc
import pandas as pd
from dbfread import DBF

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import escopo                                                  # noqa: E402

MUNICIPIOS = RAIZ / "dados" / "bp3_municipios.csv"

# recorte territorial, por variavel de ambiente:
#   SANEA_ESCOPO=parana python saude/sih_bp3.py
ESCOPO = escopo.atual()

PARCIAIS = RAIZ / "dados" / "bruto" / "sih"
SAIDA = RAIZ / "dados" / f"sih_{ESCOPO}_mensal.csv"

FTP_HOST = "ftp.datasus.gov.br"
FTP_ARQ = ("/dissemin/publicos/SIHSUS/200801_/Dados/"
           "RD" + escopo.sigla(ESCOPO) + "{aa:02d}{mm:02d}.dbc")
ANO_INICIO, ANO_FIM = 2008, 2026
PARALELO = int(os.environ.get("SANEA_PARALELO", "6"))

COLUNAS = ["MUNIC_RES", "DIAG_PRINC", "DT_INTER", "IDADE", "COD_IDADE", "MORTE"]

# COD_IDADE diz em que unidade IDADE esta escrita. Sem ele, o campo e
# ambiguo justamente onde mais importa: um lactente de 8 meses aparece como
# IDADE=8, indistinguivel de uma crianca de 8 anos. Isso inviabiliza qualquer
# corte por menores de 5, que e o grupo onde doenca de veiculacao hidrica
# realmente pesa. Layout RD do SIH: 2=dias, 3=meses, 4=anos, 5=anos acima de
# 100 (soma-se 100); 0 ou vazio = ignorada.
UNIDADE_IDADE = {"2": 1 / 365.25, "3": 1 / 12, "4": 1.0, "5": 1.0}


def idade_anos(idade, cod) -> float | None:
    """Idade em anos a partir de IDADE + COD_IDADE. None se ignorada."""
    if pd.isna(idade) or pd.isna(cod):
        return None
    cod = str(cod).strip()
    fator = UNIDADE_IDADE.get(cod)
    if fator is None:
        return None
    anos = float(idade) * fator
    return anos + 100 if cod == "5" else anos


def grupo_cid(cid: str) -> str | None:
    """Grupo DRSAI do CID-10, ou None se a causa nao nos interessa."""
    c = (cid or "").strip().upper()[:3]
    if not c:
        return None
    if "A00" <= c <= "A09":
        return "A00-A09 intestinais"
    if c == "A27":
        return "A27 leptospirose"
    if c == "B15":
        return "B15 hepatite A"
    if "B65" <= c <= "B83":
        return "B65-B83 helmintiases"
    return None


def codigos_alvo() -> set[str] | None:
    """Codigos IBGE de 6 digitos a manter. None = a UF inteira.

    Em recorte de UF nao ha lista: basta o prefixo do codigo IBGE. Isso exclui
    residentes de outros estados internados aqui, que existem e nao pertencem
    ao denominador populacional deste recorte.
    """
    if escopo.uf_inteira(ESCOPO):
        return None
    bp3 = pd.read_csv(MUNICIPIOS)
    return {str(c)[:6] for c in bp3["cod_ibge"]}


def _mantem(cod: str | None, alvo: set[str] | None) -> bool:
    if cod is None:
        return False
    prefixo = str(escopo.uf(ESCOPO))
    return cod.startswith(prefixo) if alvo is None else cod in alvo


def cache_completo(parcial: Path) -> bool:
    """O CSV existe e tem todas as colunas que a versao atual pede?

    Checar so a existencia nao basta: um cache gravado por uma versao anterior
    do script tem menos colunas e nao da para completar sem rebaixar o bruto.
    Quem preenche o cache em paralelo precisa usar exatamente este criterio, ou
    considera pronto o que o processamento vai rejeitar depois — e ai o
    rebaixamento acontece serializado, um mes por vez.
    """
    if not parcial.exists():
        return False
    with open(parcial, encoding="utf-8") as fh:
        cabecalho = (fh.readline() or "").strip().split(",")
    return not set(COLUNAS) - set(cabecalho)


def baixa_dbc(ano: int, m: int, destino: Path) -> None:
    """Baixa um RDPR via FTP, uma conexao propria por chamada.

    Nao usar urllib aqui: o FTPHandler dele guarda a conexao num cache global
    compartilhado, o que serializa qualquer paralelismo e ainda mistura estado
    entre chamadas. Com ftplib direto, cada processo abre a sua e o arquivo de
    4,5 MB chega em cerca de 2 segundos.
    """
    ftp = ftplib.FTP(FTP_HOST, timeout=300)
    try:
        ftp.login()
        with open(destino, "wb") as saida:
            ftp.retrbinary("RETR " + FTP_ARQ.format(aa=ano % 100, mm=m),
                           saida.write)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def mes(ano: int, m: int, alvo: set[str] | None) -> pd.DataFrame | None:
    """Registros da BP3 num mes. Cacheia o filtrado; descarta o bruto."""
    parcial = PARCIAIS / f"{ESCOPO}_{ano}{m:02d}.csv"
    if cache_completo(parcial):
        return pd.read_csv(parcial, dtype={"MUNIC_RES": str, "COD_IDADE": str})
    if parcial.exists():
        print(f"  {ano}-{m:02d}: cache incompleto, rebaixando")

    tmp = Path(tempfile.mkdtemp())
    try:
        dbc, dbf = tmp / "a.dbc", tmp / "a.dbf"
        try:
            baixa_dbc(ano, m, dbc)
        except Exception as erro:            # mes ainda nao publicado
            print(f"  {ano}-{m:02d}: indisponivel ({type(erro).__name__})")
            return None

        datasus_dbc.decompress(str(dbc), str(dbf))
        linhas = [
            {c: r.get(c) for c in COLUNAS}
            for r in DBF(str(dbf), encoding="latin-1")
            if _mantem(r.get("MUNIC_RES"), alvo)
        ]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    df = pd.DataFrame(linhas, columns=COLUNAS)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    # grava em temporario e renomeia: interromper o processo no meio de um
    # to_csv deixa arquivo truncado que o cache aceitaria como bom, e o
    # sintoma disso aparece muito depois, num modelo com dado faltando
    tmp_csv = parcial.with_suffix(".csv.parcial")
    df.to_csv(tmp_csv, index=False)
    tmp_csv.replace(parcial)
    return df


def _prefetch(args: tuple[int, int, set[str] | None]) -> tuple[int, int]:
    """Wrapper picklavel: preenche o cache e nao devolve o DataFrame."""
    ano, m, alvo = args
    mes(ano, m, alvo)
    return ano, m


def preenche_cache(alvo: set[str] | None) -> None:
    """Preenche em paralelo os meses que faltam no cache.

    Processos, nao threads: baixar um mes leva ~2 s, mas ler o DBF e filtrar
    meio milhao de registros e Python puro e segura a GIL por uns 20 s. Com
    threads o ganho seria so no trecho de rede, que e a menor parte. O numero
    de trabalhadores fica baixo de proposito — o FTP do DATASUS e publico.
    """
    faltam = [(a, m, alvo) for a in range(ANO_INICIO, ANO_FIM + 1)
              for m in range(1, 13)
              if not cache_completo(PARCIAIS / f"{ESCOPO}_{a}{m:02d}.csv")]
    if not faltam:
        return
    PARCIAIS.mkdir(parents=True, exist_ok=True)
    print(f"faltam {len(faltam)} meses; {PARALELO} processos", flush=True)
    with ProcessPoolExecutor(max_workers=PARALELO) as pool:
        for i, f in enumerate(as_completed(
                [pool.submit(_prefetch, a) for a in faltam]), 1):
            try:
                f.result()
            except Exception as erro:
                print(f"  falhou: {type(erro).__name__}: {erro}", flush=True)
            if i % 20 == 0:
                print(f"  {i}/{len(faltam)}", flush=True)


def main() -> None:
    alvo = codigos_alvo()
    preenche_cache(alvo)

    contagens: list[dict] = []
    total_internacoes = 0

    for ano in range(ANO_INICIO, ANO_FIM + 1):
        for m in range(1, 13):
            df = mes(ano, m, alvo)
            if df is None or df.empty:
                continue
            total_internacoes += len(df)

            c = Counter()
            for cid in df["DIAG_PRINC"]:
                g = grupo_cid(cid)
                if g:
                    c[g] += 1
            for grupo, n in c.items():
                contagens.append({"ano": ano, "mes": m, "grupo": grupo,
                                  "internacoes": n})
            # total do mes, para virar taxa depois
            contagens.append({"ano": ano, "mes": m, "grupo": "TODAS AS CAUSAS",
                              "internacoes": len(df)})
        print(f"{ano} concluido")

    saida = pd.DataFrame(contagens).sort_values(["ano", "mes", "grupo"])
    saida.to_csv(SAIDA, index=False)

    hidrica = saida[saida["grupo"].str.startswith(("A00", "A27", "B15", "B65"))]
    print()
    print(f"internacoes de residentes ({ESCOPO}): {total_internacoes:,}")
    print(f"meses com dado: {saida[['ano', 'mes']].drop_duplicates().shape[0]}")
    print()
    print("por grupo, no periodo inteiro:")
    print(hidrica.groupby("grupo")["internacoes"].sum().to_string())


if __name__ == "__main__":
    main()
