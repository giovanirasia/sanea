# -*- coding: utf-8 -*-
"""
Vincula os pontos do Observando os Rios (RMSP) as estacoes da ANA.

Entrada
  dados/bruto/inventario.json   dump de: ana_client.py inventario --uf SP
  dados/rmsp_pontos.csv         34 pontos do Observando os Rios (ano-base 2023)

Saida
  dados/pontos_x_estacoes.csv      pares ponto-estacao telemetrica
  dados/estacoes_qualidade_agua.csv  estacoes da ANA que medem qualidade de agua

CRITERIO DE VINCULO
  O relatorio do Observando os Rios publica municipio, rio e grupo — nao publica
  as coordenadas dos pontos. Sem lat/lon nao existe "estacao mais proxima" real.
  Por isso o vinculo e hierarquico e cada linha declara o criterio usado:

    1. "mesmo rio"        estacao no mesmo rio e no mesmo municipio  (forte)
    2. "mesmo municipio"  so o municipio confere                     (fraco)

  Preenchendo ponto_lat/ponto_lon em rmsp_pontos.csv, o script passa a calcular
  distancia real (haversine) e a ordenar por ela.
"""

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INVENTARIO = RAIZ / "dados" / "bruto" / "inventario.json"
PONTOS = RAIZ / "dados" / "rmsp_pontos.csv"
SAIDA = RAIZ / "dados" / "pontos_x_estacoes.csv"
SAIDA_QA = RAIZ / "dados" / "pontos_x_estacoes_detalhe.csv"

MUNICIPIOS = [
    "Barueri", "Biritiba-Mirim", "Guarulhos", "Itapecerica da Serra",
    "Itaquaquecetuba", "Maua", "Ribeirao Pires", "Rio Grande da Serra",
    "Santo Andre", "Sao Caetano do Sul", "Sao Paulo", "Suzano",
]

# prefixos genericos que atrapalham o casamento de nomes de curso d'agua
PREFIXOS = re.compile(
    r"^(rio|corrego|corr|ribeirao|rib|riacho|arroio|afluente do|afluente|"
    r"nascente do|nascente|represa|lago|reservatorio|do|da|dos|das)\s+", re.I
)


def normaliza(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace("-", " ").strip()


def nome_curso(s) -> str:
    """'Ribeirao dos Meninos' -> 'dos meninos'; 'Rio Tiete' -> 'tiete'."""
    n = normaliza(s)
    anterior = None
    while anterior != n:
        anterior = n
        n = PREFIXOS.sub("", n).strip()
    # remove parenteticos: "Corrego do Sapateiro (Lago do Ibirapuera)"
    n = re.sub(r"\(.*?\)", "", n).strip()
    return re.sub(r"\s+", " ", n)


def haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def carrega(campo_flag: str | None = None) -> list[dict]:
    """Estacoes da ANA nos 12 municipios. campo_flag filtra por periodo preenchido."""
    if not INVENTARIO.exists():
        raise SystemExit(
            f"Falta {INVENTARIO}.\n"
            "Rode antes:  python ana/ana_client.py inventario --uf SP --out dados/bruto/inventario.json"
        )
    itens = json.loads(INVENTARIO.read_text(encoding="utf-8")).get("items") or []
    alvo = {normaliza(m) for m in MUNICIPIOS}

    saida = []
    for e in itens:
        if normaliza(e.get("Municipio_Nome")) not in alvo:
            continue
        if campo_flag and not e.get(campo_flag):
            continue
        saida.append({
            "codigo": e.get("codigoestacao"),
            "nome": e.get("Estacao_Nome"),
            "municipio": e.get("Municipio_Nome"),
            "rio": e.get("Rio_Nome"),
            "sub_bacia": e.get("Sub_Bacia_Nome"),
            "tipo": e.get("Tipo_Estacao"),
            "operando": str(e.get("Operando")),
            "operadora": e.get("Operadora_Sigla"),
            "responsavel": e.get("Responsavel_Sigla"),
            "lat": num(e.get("Latitude")),
            "lon": num(e.get("Longitude")),
            "telemetrica_desde": e.get("Data_Periodo_Telemetrica_Inicio"),
            "qual_agua_desde": e.get("Data_Periodo_Qual_Agua_Inicio"),
            "qual_agua_ate": e.get("Data_Periodo_Qual_Agua_Fim"),
        })
    return saida


def indexa(estacoes: list[dict]) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for e in estacoes:
        idx.setdefault(normaliza(e["municipio"]), []).append(e)
    return idx


def main() -> None:
    telemetricas = [e for e in carrega("Data_Periodo_Telemetrica_Inicio") if e["operando"] == "1"]
    fluvio = [e for e in telemetricas if normaliza(e["tipo"]).startswith("fluvio")]
    pluvio = [e for e in telemetricas if normaliza(e["tipo"]).startswith("pluvio")]
    qa = [e for e in carrega("Data_Periodo_Qual_Agua_Inicio") if e["operando"] == "1"]

    print(f"telemetricas ativas nos 12 municipios: {len(telemetricas)}")
    print(f"  fluviometricas (medem o RIO):   {len(fluvio)}")
    print(f"  pluviometricas (medem a CHUVA): {len(pluvio)}")
    print(f"estacoes de qualidade de agua operando: {len(qa)}")

    i_fluvio, i_pluvio, i_qa = indexa(fluvio), indexa(pluvio), indexa(qa)
    pontos = list(csv.DictReader(PONTOS.open(encoding="utf-8-sig")))

    resumo, detalhe = [], []
    for p in pontos:
        mun = normaliza(p["municipio"])
        alvo = nome_curso(p["ponto"])
        p_lat, p_lon = num(p.get("ponto_lat")), num(p.get("ponto_lon"))

        def casa(lista):
            """estacoes do municipio, priorizando as do mesmo curso d'agua"""
            no_mun = i_fluvio.get(mun, []) if lista is fluvio else (
                i_pluvio.get(mun, []) if lista is pluvio else i_qa.get(mun, []))
            mesmo = [e for e in no_mun if alvo and nome_curso(e["rio"]) == alvo]
            return mesmo, no_mun

        f_rio, f_mun = casa(fluvio)
        q_rio, q_mun = casa(qa)
        _, p_mun = casa(pluvio)

        for e, papel in [(x, "fluviometrica") for x in (f_rio or f_mun)] + \
                        [(x, "qualidade_agua") for x in (q_rio or q_mun)]:
            dist = None
            if None not in (p_lat, p_lon, e["lat"], e["lon"]):
                dist = round(haversine(p_lat, p_lon, e["lat"], e["lon"]), 2)
            detalhe.append({
                "municipio": p["municipio"], "ponto_rio": p["ponto"],
                "ponto_grupo": p["grupo"], "iqa": p["iqa"], "papel": papel,
                "criterio": "mesmo rio" if nome_curso(e["rio"]) == alvo else "mesmo municipio",
                "estacao_codigo": e["codigo"], "estacao_nome": e["nome"],
                "estacao_rio": e["rio"], "estacao_lat": e["lat"], "estacao_lon": e["lon"],
                "distancia_km": dist,
            })

        resumo.append({
            "municipio": p["municipio"], "ponto_rio": p["ponto"],
            "ponto_grupo": p["grupo"], "iqa": p["iqa"],
            "fluvio_mesmo_rio": ";".join(e["codigo"] for e in f_rio),
            "fluvio_no_municipio": len(f_mun),
            "qa_mesmo_rio": ";".join(e["codigo"] for e in q_rio),
            "qa_no_municipio": len(q_mun),
            "pluvio_no_municipio": len(p_mun),
            "vinculo": "rio medido" if f_rio else ("qualidade no rio" if q_rio else "so chuva"),
        })

    with SAIDA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(resumo[0].keys()))
        w.writeheader()
        w.writerows(resumo)
    with SAIDA_QA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(detalhe[0].keys()))
        w.writeheader()
        w.writerows(detalhe)

    print(f"\nresumo por ponto -> {SAIDA.name} ({len(resumo)} linhas)")
    print(f"detalhe ponto-estacao -> {SAIDA_QA.name} ({len(detalhe)} linhas)")

    from collections import Counter
    print("\nsituacao dos 34 pontos:")
    for k, n in Counter(r["vinculo"] for r in resumo).most_common():
        print(f"  {k:20s} {n}")

    print("\npontos com estacao fluviometrica no MESMO rio:")
    for r in resumo:
        if r["fluvio_mesmo_rio"]:
            print(f"  {r['municipio']:22s} {r['ponto_rio']:26s} {r['iqa']:8s} -> {r['fluvio_mesmo_rio']}")


if __name__ == "__main__":
    main()
