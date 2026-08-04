# -*- coding: utf-8 -*-
"""
Saneamento do domicilio, do Censo 2022 — a exposicao que o SINISA nao mede.

Por que existe: a tese central do projeto foi testada com a cobertura municipal
de esgoto do SINISA (IES0001) e nao se sustentou — 1,000 (IC 0,998-1,002,
p=0,98) no Parana, com modelo completo. Antes de aceitar o nulo, e preciso
descartar que ele seja artefato da variavel, e ha razao concreta para suspeitar
disso.

O SINISA mede a rede do prestador: quantos domicilios o operador atende. Isso
tem dois defeitos como medida de exposicao a esgoto:

  1. os 157 municipios do Parana sem rede coletora entram todos como zero, como
     se fossem iguais. Nao sao. Um municipio onde todo mundo tem fossa septica
     e um municipio onde todo mundo lanca em vala a ceu aberto recebem a mesma
     nota. Sao situacoes sanitarias opostas.
  2. nao ter rede nao e o mesmo que estar exposto. Fossa septica bem executada
     e solucao adequada, e o proprio IBGE a classifica assim.

O Censo mede outra coisa: o que o domicilio de fato tem. Isso permite construir
a variavel que interessa — a fracao de domicilios com destino **inadequado**
(fossa rudimentar, vala, corpo d'agua, ou sem banheiro nenhum) — que existe para
os 399 municipios, inclusive os 157 que o SINISA zera.

A hipotese de contaminacao, escrita como se testa
  esgoto cru no solo so vira doenca se houver caminho ate a boca. O caminho
  classico no rural e poco raso: fossa rudimentar contamina o lencol freatico
  raso que o poco do vizinho capta. Por isso este modulo traz tambem a fonte de
  agua do domicilio, e nao so a cobertura de rede. A interacao
  esgoto_inadequado x agua_poco_raso e o teste direto do mecanismo, e nada no
  SINISA permite monta-la.

Isso tambem enderaca a densidade, que sobrou sem explicacao em densidade.py:
poco e nascente nao entram no IAG0001, e sao justamente o que o rural usa.

Fontes: SIDRA/IBGE, Censo 2022
  tabela 6805  domicilios por tipo de esgotamento sanitario
  tabela 6803  domicilios por ligacao a rede de agua e forma de abastecimento

Limites
  - o Censo 2022 e um ponto no tempo, aplicado a um painel de 2008 a 2026. Vale
    o mesmo aviso da estrutura etaria: descreve melhor o fim da serie.
  - "adequado" aqui segue a classificacao do IBGE, que julga o tipo de solucao,
    nao sua execucao. Fossa septica mal dimensionada conta como adequada.
  - domicilio nao e pessoa: municipios com domicilios maiores ficam
    subrepresentados na fracao. Para o cruzamento com internacao isso e ruido,
    nao vies sistematico.

Saida
  dados/censo_domiciliar_{escopo}.csv
"""

from __future__ import annotations

import gzip
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent

ESCOPO = os.environ.get("SANEA_ESCOPO", "bp3")
if ESCOPO not in ("bp3", "parana"):
    raise SystemExit(f"SANEA_ESCOPO invalido: {ESCOPO}")

MUNICIPIOS = RAIZ / "dados" / f"{ESCOPO}_municipios.csv"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = RAIZ / "dados" / f"censo_domiciliar_{ESCOPO}.csv"

# uma requisicao traz o estado inteiro; no escopo da bacia filtra-se depois
SIDRA = ("https://apisidra.ibge.gov.br/values/t/{t}/n6/in%20n3%2041"
         "/v/381/p/2022/c{c}/{cats}")

# tabela 6805, classificacao 11558 — tipo de esgotamento sanitario.
# 46290 (agregado "rede geral, pluvial ou fossa ligada a rede") e omitido de
# proposito: e a soma de 72110 e 72111, e somar os tres contaria duas vezes.
ESGOTO = {
    "total": "46292",
    "rede": "72110",              # rede geral ou pluvial
    "fossa_ligada": "72111",      # fossa septica ou filtro ligada a rede
    "fossa_septica": "72112",     # fossa septica ou filtro NAO ligada a rede
    "fossa_rudimentar": "72113",  # fossa rudimentar ou buraco
    "vala": "92858",
    "corpo_dagua": "72114",       # rio, lago, corrego ou mar
    "outra": "72115",
    "sem_banheiro": "92861",
}

# tabela 6803, classificacao 1821 — ligacao a rede e forma principal de agua
AGUA = {
    "total": "72129",
    "rede_usa": "72144",          # tem ligacao e a usa como forma principal
    "lig_poco_raso": "72147",     # tem ligacao, mas usa poco raso
    "lig_superficial": "72151",   # tem ligacao, mas usa rio/acude/corrego
    "sem_lig": "72153",
    "sem_lig_poco_prof": "72154",
    "sem_lig_poco_raso": "72155",
    "sem_lig_nascente": "72156",
    "sem_lig_superficial": "72159",
}

# destino que expoe a populacao a esgoto cru; "outra forma" fica de fora por
# ser categoria residual sem conteudo sanitario definido
INADEQUADO = ["fossa_rudimentar", "vala", "corpo_dagua", "sem_banheiro"]


def _baixa(tabela: int, classif: int, cats: dict[str, str]) -> list[dict]:
    destino = BRUTO / f"censo{tabela}_pr.json"
    if destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    url = SIDRA.format(t=tabela, c=classif, cats=",".join(cats.values()))
    with urllib.request.urlopen(url, timeout=600) as resp:
        dados = resp.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    bruto = dados.decode("utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(bruto, encoding="utf-8")
    return json.loads(bruto)


def tabela(t: int, classif: int, cats: dict[str, str]) -> pd.DataFrame:
    """Contagens por municipio, uma coluna por categoria pedida."""
    rotulo = {cod: nome for nome, cod in cats.items()}
    linhas: dict[int, dict] = {}
    for r in _baixa(t, classif, cats)[1:]:      # [0] e o cabecalho descritivo
        cod = int(r["D1C"])
        valor = r["V"]
        # SIDRA usa "-" para zero e "..." para nao aplicavel
        n = int(valor) if str(valor).isdigit() else 0
        linhas.setdefault(cod, {"cod_ibge": cod})[rotulo[r["D4C"]]] = n
    return pd.DataFrame(linhas.values())


def main() -> None:
    esg = tabela(6805, 11558, ESGOTO)
    agu = tabela(6803, 1821, AGUA)

    d = esg.merge(agu, on="cod_ibge", suffixes=("_esg", "_agu"))
    mun = pd.read_csv(MUNICIPIOS)[["cod_ibge", "municipio"]]
    d = mun.merge(d, on="cod_ibge", how="inner")

    te, ta = d["total_esg"], d["total_agu"]
    pct = lambda n, t: (100 * n / t).round(2)

    d["domicilios"] = te
    # a variavel nova: exposicao a esgoto cru, definida para todo municipio
    d["esgoto_inadequado_pct"] = pct(d[INADEQUADO].sum(axis=1), te)
    # comparavel ao IES0001 do SINISA, para checar as duas medidas uma na outra
    d["esgoto_rede_pct"] = pct(d["rede"] + d["fossa_ligada"], te)
    # a solucao individual adequada, que o SINISA conta como zero
    d["fossa_septica_pct"] = pct(d["fossa_septica"], te)

    d["agua_rede_pct"] = pct(d["rede_usa"], ta)
    # fonte vulneravel a contaminacao por fossa vizinha
    d["agua_poco_raso_pct"] = pct(d["lig_poco_raso"] + d["sem_lig_poco_raso"], ta)
    d["agua_superficial_pct"] = pct(d["lig_superficial"]
                                    + d["sem_lig_superficial"], ta)
    d["agua_nascente_pct"] = pct(d["sem_lig_nascente"], ta)
    d["agua_sem_rede_pct"] = pct(d["sem_lig"], ta)

    cols = ["cod_ibge", "municipio", "domicilios", "esgoto_inadequado_pct",
            "esgoto_rede_pct", "fossa_septica_pct", "agua_rede_pct",
            "agua_poco_raso_pct", "agua_superficial_pct", "agua_nascente_pct",
            "agua_sem_rede_pct"]
    d[cols].to_csv(SAIDA, index=False)

    print(f"{ESCOPO}: {len(d)} municipios, {int(te.sum()):,} domicilios")
    print()
    for c in cols[3:]:
        print(f"  {c:<24} mediana {d[c].median():>6.2f}   "
              f"de {d[c].min():>6.2f} a {d[c].max():>6.2f}")


if __name__ == "__main__":
    main()
