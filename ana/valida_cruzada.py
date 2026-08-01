# -*- coding: utf-8 -*-
"""
Validacao cruzada: IQA dos voluntarios do Observando os Rios (SOS Mata Atlantica)
contra as medicoes de qualidade de agua da propria ANA, no mesmo rio e municipio.

A pergunta: onde as duas redes medem o mesmo curso d'agua, elas concordam?

Metodo
  - pareia ponto do SOS com estacao da ANA por municipio + nome do curso d'agua
  - agrega as medicoes da ANA na janela (mediana por estacao/rio)
  - compara a ORDEM: a classe de IQA do SOS e ordinal (Pessima<Ruim<Regular<Boa),
    entao o teste honesto e de correlacao de postos (Spearman), nao de valor absoluto
  - sinal esperado: OD positivo (mais oxigenio = melhor); DBO, coliformes,
    turbidez e fosforo negativos (mais carga = pior)

Limite: sao poucos pares. Isso e uma checagem de consistencia, nao um estudo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vincula_estacoes import nome_curso, normaliza  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
QA = RAIZ / "dados" / "qa_medicoes.csv"
PONTOS = RAIZ / "dados" / "rmsp_pontos.csv"
SAIDA = RAIZ / "dados" / "validacao_cruzada.csv"

ORDEM = {"Pessima": 0, "Ruim": 1, "Regular": 2, "Boa": 3, "Otima": 4}

# parametro -> sinal esperado da correlacao com a qualidade (classe do SOS)
ESPERADO = {
    "od_mgl": +1, "od_saturacao_pct": +1,
    "dbo_mgl": -1, "dqo_mgl": -1,
    "colif_termotolerantes": -1, "colif_fecais": -1, "ecoli": -1,
    "n_total_mgl": -1, "n_amoniacal_mgl": -1, "p_total_mgl": -1,
    "turbidez_ntu": -1, "condutividade_us_cm": -1,
    "iqa_ana": +1,
}


def main() -> None:
    if not QA.exists():
        raise SystemExit(f"Falta {QA}. Rode antes: python ana/serie_qualidade.py")

    qa = pd.read_csv(QA)
    pontos = pd.read_csv(PONTOS)
    print(f"medicoes da ANA: {len(qa)} em {qa['estacao'].nunique()} estacoes")
    print(f"pontos do SOS:   {len(pontos)}\n")

    qa["chave"] = qa["municipio"].map(normaliza) + "|" + qa["rio"].map(nome_curso)
    pontos["chave"] = pontos["municipio"].map(normaliza) + "|" + pontos["ponto"].map(nome_curso)

    # agrega a ANA por municipio+rio
    cols = [c for c in ESPERADO if c in qa.columns]
    ana = (qa.groupby("chave")
             .agg(n_medicoes=("data", "size"),
                  n_estacoes=("estacao", "nunique"),
                  primeira=("data", "min"), ultima=("data", "max"),
                  **{c: (c, "median") for c in cols})
             .reset_index())

    # agrega o SOS por municipio+rio (varios grupos podem medir o mesmo rio)
    pontos["iqa_ord"] = pontos["iqa"].map(ORDEM)
    sos = (pontos.groupby(["chave", "municipio"])
                 .agg(n_pontos=("ponto", "size"),
                      iqa_ord=("iqa_ord", "mean"),
                      iqa_classes=("iqa", lambda s: "/".join(sorted(set(s)))),
                      rio=("ponto", "first"))
                 .reset_index())

    par = sos.merge(ana, on="chave", how="inner")
    print(f"pares SOS x ANA no mesmo municipio e rio: {len(par)}")
    if par.empty:
        print("Nenhum par. Sem sobreposicao entre as duas redes nesses municipios.")
        return

    # so vale mostrar parametro que tem valor em pelo menos um par
    cols = [c for c in cols if par[c].notna().any()]
    vazios = [c for c in ESPERADO if c in qa.columns and c not in cols]
    if vazios:
        print(f"sem nenhum dado nos pares (ignorados): {', '.join(vazios)}")

    mostra = ["municipio", "rio", "iqa_classes", "n_pontos", "n_estacoes", "n_medicoes"] + cols
    pd.set_option("display.width", 250, "display.max_columns", 40)
    par = par.sort_values("iqa_ord")
    print("\n===== pares =====")
    print(par[mostra].to_string(index=False))

    if len(par) < 5:
        print(f"\n{len(par)} pares e pouco demais para correlacao — qualquer rho seria ruido.")
        print("Leitura descritiva: os pares estao ordenados do pior IQA do SOS para o melhor.")
        print("Se a ANA concorda, OD deve subir e E.coli/turbidez/fosforo devem cair na tabela acima.")
        par[mostra + ["iqa_ord"]].to_csv(SAIDA, index=False, encoding="utf-8-sig")
        print(f"\npares gravados em {SAIDA}")
        return

    print("\n===== correlacao de postos (Spearman) com a classe do SOS =====")
    print(f"{'parametro':24s} {'n':>3s} {'rho':>7s}  {'esperado':>8s}  veredito")
    resultados = []
    for c in cols:
        sub = par[["iqa_ord", c]].dropna()
        if len(sub) < 3 or sub[c].nunique() < 2:
            print(f"{c:24s} {len(sub):3d}      —   {ESPERADO[c]:+d}        dados insuficientes")
            continue
        rho = sub["iqa_ord"].corr(sub[c], method="spearman")
        bate = "consistente" if (rho > 0) == (ESPERADO[c] > 0) else "CONTRARIO ao esperado"
        if abs(rho) < 0.2:
            bate = "sem sinal"
        print(f"{c:24s} {len(sub):3d} {rho:+7.3f}  {ESPERADO[c]:+8d}  {bate}")
        resultados.append({"parametro": c, "n": len(sub), "rho": round(rho, 3),
                           "sinal_esperado": ESPERADO[c], "veredito": bate})

    par[mostra + ["iqa_ord"]].to_csv(SAIDA, index=False, encoding="utf-8-sig")
    print(f"\npares gravados em {SAIDA}")

    if resultados:
        ok = sum(1 for r in resultados if r["veredito"] == "consistente")
        print(f"\nresumo: {ok} de {len(resultados)} parametros com sinal na direcao esperada.")
        print("Com poucos pares isso e checagem de consistencia, nao evidencia estatistica.")


if __name__ == "__main__":
    main()
