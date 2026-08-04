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
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from dbfread import DBF

import datasus_dbc

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import escopo                                                  # noqa: E402

ESCOPO = escopo.atual()
PARCIAIS = RAIZ / "dados" / "bruto" / "sim"
SAIDA = RAIZ / "dados" / f"sim_{ESCOPO}_anual.csv"
MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"

FTP_HOST = "ftp.datasus.gov.br"
FTP_ARQ = ("/dissemin/publicos/SIM/CID10/DORES/"
           "DO" + escopo.sigla(ESCOPO) + "{ano}.dbc")
ANO_INICIO, ANO_FIM = 2008, 2024
PARALELO = int(os.environ.get("SANEA_PARALELO", "4"))

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


def baixa_dbc(ano: int, destino: Path) -> None:
    ftp = ftplib.FTP(FTP_HOST, timeout=300)
    try:
        ftp.login()
        with open(destino, "wb") as saida:
            ftp.retrbinary("RETR " + FTP_ARQ.format(ano=ano), saida.write)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def ano_bruto(ano: int) -> pd.DataFrame | None:
    """Obitos de residentes no recorte, num ano. Cacheia o filtrado."""
    parcial = PARCIAIS / f"{ESCOPO}_{ano}.csv"
    if cache_completo(parcial):
        return pd.read_csv(parcial, dtype={"CODMUNRES": str, "IDADE": str})

    prefixo = str(escopo.uf(ESCOPO))
    tmp = Path(tempfile.mkdtemp())
    try:
        dbc, dbf = tmp / "a.dbc", tmp / "a.dbf"
        try:
            baixa_dbc(ano, dbc)
        except Exception as erro:
            print(f"  {ano}: indisponivel ({type(erro).__name__})", flush=True)
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


def _prefetch(ano: int) -> int:
    ano_bruto(ano)
    return ano


def preenche_cache() -> None:
    faltam = [a for a in range(ANO_INICIO, ANO_FIM + 1)
              if not cache_completo(PARCIAIS / f"{ESCOPO}_{a}.csv")]
    if not faltam:
        return
    PARCIAIS.mkdir(parents=True, exist_ok=True)
    print(f"faltam {len(faltam)} anos; {PARALELO} processos", flush=True)
    with ProcessPoolExecutor(max_workers=PARALELO) as pool:
        for f in as_completed([pool.submit(_prefetch, a) for a in faltam]):
            try:
                f.result()
            except Exception as erro:
                print(f"  falhou: {type(erro).__name__}: {erro}", flush=True)


def main() -> None:
    preenche_cache()

    mapa = None
    if not escopo.uf_inteira(ESCOPO):
        mun = pd.read_csv(MUNICIPIOS)
        mapa = {str(c)[:6] for c in mun["cod_ibge"]}

    linhas = []
    for ano in range(ANO_INICIO, ANO_FIM + 1):
        d = ano_bruto(ano)
        if d is None or d.empty:
            continue
        # o SIM tem um codigo por UF para "municipio ignorado" (210000 no MA),
        # que nao e municipio e nao tem denominador populacional. Sao 408
        # obitos no periodo, 3 deles por A00-A09.
        d = d[~d["CODMUNRES"].str.endswith("0000")]
        if mapa is not None:
            d = d[d["CODMUNRES"].isin(mapa)]
        cid = d["CAUSABAS"].fillna("").str.strip().str.upper().str[:3]
        d = d.assign(
            hidrica=((cid >= "A00") & (cid <= "A09")).astype(int),
            # capitulo XVIII do CID-10: sintomas, sinais e achados anormais,
            # ou seja, obito sem causa determinada. E o indicador padrao de
            # qualidade do registro, e importa aqui por um motivo especifico:
            # onde nao ha assistencia medica, a morte por diarreia tende a ser
            # codificada como mal definida em vez de A00-A09. Isso subtrai
            # casos do desfecho exatamente onde a exposicao e maior — vies que
            # o controle de mortalidade geral nao pega, porque o obito esta
            # registrado, so esta na gaveta errada.
            mal_definida=((cid >= "R00") & (cid <= "R99")).astype(int),
            anos=[idade_anos(i) for i in d["IDADE"]])
        d = d.dropna(subset=["anos"])

        for faixa, (lo, hi) in FAIXAS.items():
            f = d[(d["anos"] >= lo) & (d["anos"] < hi)]
            if f.empty:
                continue
            g = f.groupby("CODMUNRES").agg(
                obitos_a00a09=("hidrica", "sum"),
                obitos_mal_definidos=("mal_definida", "sum"),
                obitos_total=("hidrica", "size")).reset_index()
            linhas.append(g.assign(ano=ano, faixa=faixa))
        print(f"{ano}: {len(d):,} obitos, "
              f"{int(d['hidrica'].sum()):,} por A00-A09", flush=True)

    saida = (pd.concat(linhas, ignore_index=True)
             .rename(columns={"CODMUNRES": "cod6"})
             .groupby(["cod6", "ano", "faixa"], as_index=False)
             [["obitos_a00a09", "obitos_mal_definidos", "obitos_total"]].sum())
    saida.to_csv(SAIDA, index=False)

    print()
    print(f"{ESCOPO}: {saida['cod6'].nunique()} municipios, "
          f"{saida['ano'].nunique()} anos")
    print(f"obitos por A00-A09: {int(saida['obitos_a00a09'].sum()):,} "
          f"de {int(saida['obitos_total'].sum()):,} obitos")
    print()
    print("A00-A09 por faixa etaria:")
    print(saida.groupby("faixa")["obitos_a00a09"].sum().to_string())


if __name__ == "__main__":
    main()
