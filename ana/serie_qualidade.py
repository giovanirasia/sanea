# -*- coding: utf-8 -*-
"""
Baixa as series de qualidade de agua (rota HidroSerieQA/v1) das estacoes da ANA
nos 12 municipios da RMSP e achata para CSV.

A resposta traz ~147 parametros por medicao, quase todos nulos. Aqui ficam
apenas os que compoem o IQA e alguns auxiliares. O dump bruto e preservado
em dados/bruto/qa/ para nao precisar rebaixar.

Uso:  python ana/serie_qualidade.py [--inicio 2022-01-01] [--fim 2024-12-31]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ana_client as ac  # noqa: E402
from vincula_estacoes import carrega  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "qa"
SAIDA = RAIZ / "dados" / "qa_medicoes.csv"

# nome exato do campo na API -> rotulo limpo.
# atencao aos parenteses sobrando em alguns nomes: sao assim na resposta mesmo.
PARAMS = {
    "17_OD_mgl_02": "od_mgl",
    "78_OD_perc_saturacao": "od_saturacao_pct",
    "18_PH": "ph",
    "7_DBO_mgl_02)": "dbo_mgl",
    "9_DQO_mgl_02)": "dqo_mgl",
    "5_Coliformes_Termo_Tolerantes_ufc_100ml": "colif_termotolerantes",
    "46_Coliformes_Fecais_nmp_100ml": "colif_fecais",
    "10_Escherichiacoli_ufc_100ml": "ecoli",
    "15_Nitrogenio_Total_mgl_n": "n_total_mgl",
    "14_Nitrogenio_Amoniacal_mgl": "n_amoniacal_mgl",
    "12_Fosforo_Total_mgl)": "p_total_mgl",
    "24_Turbidez_ntu": "turbidez_ntu",
    "91_Sol_totais_mgl": "solidos_totais_mgl",
    "21_Temperatura_Amostra_c": "temp_amostra_c",
    "6_Condutividade_Especifica_25oc_us_cm_a_25c": "condutividade_us_cm",
    "68_IQA": "iqa_ana",
}


def valor(reg: dict, campo: str):
    v = reg.get(campo)
    if v in (None, "", "null"):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return v


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--inicio", default="2022-01-01")
    p.add_argument("--fim", default="2024-12-31")
    p.add_argument("--pausa", type=float, default=2.0, help="segundos entre requisicoes")
    a = p.parse_args()

    BRUTO.mkdir(parents=True, exist_ok=True)
    estacoes = [e for e in carrega("Data_Periodo_Qual_Agua_Inicio") if e["operando"] == "1"]
    print(f"estacoes de qualidade operando: {len(estacoes)}")
    print(f"janela: {a.inicio} a {a.fim}\n")

    # a API recusa intervalos maiores que 366 dias -> uma requisicao por ano
    anos = list(range(int(a.inicio[:4]), int(a.fim[:4]) + 1))
    print(f"anos: {anos} (a API limita cada consulta a 366 dias)\n")

    linhas, vazias, erros = [], 0, 0
    for i, e in enumerate(estacoes, 1):
        cod = e["codigo"]
        itens: list[dict] = []
        falhou = False

        for ano in anos:
            cache = BRUTO / f"{cod}_{ano}.json"
            if cache.exists():
                itens += json.loads(cache.read_text(encoding="utf-8")).get("items") or []
                continue

            inicio = max(f"{ano}-01-01", a.inicio)
            fim = min(f"{ano}-12-31", a.fim)
            r = None
            # o servico devolve 503 quando o ritmo aperta; backoff exponencial
            for espera in (0, 10, 30, 90):
                if espera:
                    print(f"       503 — aguardando {espera}s")
                    time.sleep(espera)
                try:
                    r = ac.consulta("HidroSerieQA/v1", {
                        "Código da Estação": cod,
                        "Tipo Filtro Data": "DATA_LEITURA",
                        "Data Inicial (yyyy-MM-dd)": inicio,
                        "Data Final (yyyy-MM-dd)": fim,
                    })
                    break
                except ac.HidroError as exc:
                    if exc.codigo != 503:
                        print(f"  [{i:2}/{len(estacoes)}] {cod} {ano} ERRO: {exc}")
                        break
            time.sleep(a.pausa)
            if r is None:
                falhou = True
                continue
            cache.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
            itens += r.get("items") or []

        if falhou:
            erros += 1
        if not itens:
            vazias += 1
        print(f"  [{i:2}/{len(estacoes)}] {cod} {str(e['municipio'])[:16]:16s} "
              f"{str(e['rio'])[:26]:26s} medicoes={len(itens)}")

        for reg in itens:
            linha = {
                "estacao": cod, "estacao_nome": e["nome"], "municipio": e["municipio"],
                "rio": e["rio"], "sub_bacia": e["sub_bacia"],
                "lat": e["lat"], "lon": e["lon"],
                "data": (reg.get("Data_Hora_Dado") or "")[:19],
                "consistencia": reg.get("Nilvel_ConsistÃªncia") or reg.get("Nilvel_Consistência"),
                "choveu": reg.get("Choveu"),
            }
            for campo, rotulo in PARAMS.items():
                linha[rotulo] = valor(reg, campo)
            linhas.append(linha)

    if not linhas:
        print(f"\nnenhuma medicao coletada. estacoes sem dado: {vazias} | erros: {erros}")
        return

    linhas.sort(key=lambda r: (r["municipio"], r["rio"], r["data"]))
    with SAIDA.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)

    print(f"\nmedicoes gravadas: {len(linhas)} -> {SAIDA}")
    print(f"estacoes sem dado na janela: {vazias} | erros: {erros}")

    preenchidos = {r: sum(1 for l in linhas if l[r] is not None) for r in PARAMS.values()}
    print("\npreenchimento por parametro:")
    for rotulo, n in sorted(preenchidos.items(), key=lambda kv: -kv[1]):
        print(f"  {rotulo:24s} {n:5d}  ({100*n/max(len(linhas),1):.0f}%)")


if __name__ == "__main__":
    main()
