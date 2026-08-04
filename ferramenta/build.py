# -*- coding: utf-8 -*-
"""
Gera os dados da ferramenta a partir dos dois datasets publicados.

Por que estatico e nao API
  Os dados nao mudam: o Censo 2022 e um retrato, e o SIM atualiza uma vez por
  ano. Servico que consulta banco para devolver sempre a mesma resposta e
  custo e ponto de falha sem contrapartida. Aqui o build roda de vez em quando,
  gera JSON, e a pagina e arquivo — hospeda em qualquer lugar, funciona sem
  backend, e nao quebra quando ninguem estiver olhando.

  Isso desvia da stack planejada no inicio do projeto (Flutter + FastAPI +
  PostGIS). O desvio e deliberado: aquela pilha se justifica com dado que muda
  e usuario autenticado, e nao e o caso.

Populacao
  Nenhum dos dois datasets publicados traz populacao, e sem denominador nao ha
  taxa — e sem taxa nao da para comparar municipio grande com pequeno, que e a
  coisa mais basica que a ferramenta precisa fazer. Vem do SIDRA, tabela 4709
  (Censo 2022), uma requisicao por UF.

Saidas
  dados/municipios.json   indice para busca: codigo, nome, UF, populacao
  dados/perfil.json       saneamento e obitos por municipio
  dados/referencia.json   medianas por UF e nacional, para comparacao
"""

from __future__ import annotations

import gzip
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
SANEAMENTO = RAIZ / "dados" / "censo_domiciliar_br.csv"
OBITOS = RAIZ / "dados" / "obitos_hidricas_br.csv"
BRUTO = RAIZ / "dados" / "bruto" / "ibge"
SAIDA = Path(__file__).resolve().parent / "dados"

SIDRA_POP = "https://apisidra.ibge.gov.br/values/t/4709/n6/in%20n3%20{uf}/v/93/p/2022"
# populacao de 0 a 4 anos, tabela 9514 (Censo 2022). Sem isso a taxa infantil
# precisaria de um proxy fixo — algo como "6% da populacao" — que erra
# exatamente onde a estrutura etaria difere, que e o contraste Norte/Sul que a
# ferramenta existe para mostrar.
SIDRA_0A4 = ("https://apisidra.ibge.gov.br/values/t/9514/n6/in%20n3%20{uf}"
             "/v/93/p/2022/c287/93070/c2/6794/c286/113635")
UFS = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
       21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
       28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
       42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}

# indicadores mostrados no perfil, na ordem em que aparecem
ESGOTO = ["esgoto_rede_pct", "fossa_septica_pct", "fossa_rudimentar_pct",
          "esgoto_inadequado_pct", "esgoto_adequado_pct"]
AGUA = ["agua_rede_pct", "agua_poco_profundo_pct", "agua_poco_raso_pct",
        "agua_nascente_pct", "agua_carropipa_pct", "agua_superficial_pct"]


def _sidra(url: str, cache: Path) -> list[dict]:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url, timeout=300) as r:
        d = r.read()
    if d[:2] == b"\x1f\x8b":
        d = gzip.decompress(d)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(d.decode("utf-8"), encoding="utf-8")
    time.sleep(1)
    return json.loads(d.decode("utf-8"))


def populacao() -> pd.DataFrame:
    """Populacao total e de 0 a 4 anos, por municipio."""
    tot, inf = [], []
    for uf, sigla in UFS.items():
        s = sigla.lower()
        for js, destino, chave in (
                (_sidra(SIDRA_POP.format(uf=uf), BRUTO / f"pop4709_{s}.json"),
                 tot, "populacao"),
                (_sidra(SIDRA_0A4.format(uf=uf), BRUTO / f"pop0a4_{s}.json"),
                 inf, "pop_0a4")):
            for r in js[1:]:
                v = r["V"]
                destino.append({"cod_ibge": int(r["D1C"]),
                                chave: int(v) if str(v).isdigit() else None})
        print(f"  populacao {sigla}")
    return (pd.DataFrame(tot).dropna(subset=["populacao"])
            .merge(pd.DataFrame(inf), on="cod_ibge", how="left"))


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    san = pd.read_csv(SANEAMENTO)
    pop = populacao()
    d = san.merge(pop, on="cod_ibge", how="left")

    ob = pd.read_csv(OBITOS)
    # o desfecho da ferramenta e obito infantil, que e o mais interpretavel;
    # os totais e os mal definidos vao junto porque sem eles a taxa engana
    inf = ob[ob["faixa"] == "0a4"]
    resumo = (inf.groupby("cod_ibge")
              .agg(obitos_0a4=("obitos_a00a09", "sum"),
                   obitos_total_0a4=("obitos_total", "sum"),
                   mal_definidos_0a4=("obitos_mal_definidos", "sum"))
              .reset_index())
    todas = (ob.groupby("cod_ibge")["obitos_a00a09"].sum()
             .rename("obitos_todas_idades").reset_index())
    d = d.merge(resumo, on="cod_ibge", how="left").merge(
        todas, on="cod_ibge", how="left")
    for c in ("obitos_0a4", "obitos_total_0a4", "mal_definidos_0a4",
              "obitos_todas_idades"):
        d[c] = d[c].fillna(0).astype(int)

    # serie anual de obitos infantis, so onde houve algum: economiza muito
    serie = (inf[inf["obitos_a00a09"] > 0]
             .groupby(["cod_ibge", "ano"])["obitos_a00a09"].sum().reset_index())
    por_mun: dict[int, dict] = {}
    for cod, g in serie.groupby("cod_ibge"):
        por_mun[int(cod)] = {int(a): int(v) for a, v in
                             zip(g["ano"], g["obitos_a00a09"])}

    indice = [{"c": int(r.cod_ibge), "n": r.municipio, "u": r.uf,
               "p": int(r.populacao) if pd.notna(r.populacao) else None,
               "p4": int(r.pop_0a4) if pd.notna(r.pop_0a4) else None}
              for r in d.itertuples()]
    (SAIDA / "municipios.json").write_text(
        json.dumps(indice, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    perfil = {}
    for r in d.itertuples():
        cod = int(r.cod_ibge)
        perfil[cod] = {
            "dom": int(r.domicilios),
            "esg": [round(getattr(r, c), 1) for c in ESGOTO],
            "agu": [round(getattr(r, c), 1) for c in AGUA],
            "ob": [r.obitos_0a4, r.obitos_total_0a4, r.mal_definidos_0a4,
                   r.obitos_todas_idades],
            "serie": por_mun.get(cod, {}),
        }
    (SAIDA / "perfil.json").write_text(
        json.dumps(perfil, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    # medianas de referencia: sem elas o numero do municipio nao diz nada
    cols = ESGOTO + AGUA
    ref = {"BR": {c: round(d[c].median(), 1) for c in cols}}
    for uf, g in d.groupby("uf"):
        ref[uf] = {c: round(g[c].median(), 1) for c in cols}
    ref["_ordem"] = {"esg": ESGOTO, "agu": AGUA}
    (SAIDA / "referencia.json").write_text(
        json.dumps(ref, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    for f in ("municipios.json", "perfil.json", "referencia.json"):
        print(f"  {f}: {(SAIDA / f).stat().st_size / 1e6:.2f} MB")
    print(f"\n{len(d):,} municipios, "
          f"{int(d['obitos_todas_idades'].sum()):,} obitos por A00-A09")


if __name__ == "__main__":
    main()
