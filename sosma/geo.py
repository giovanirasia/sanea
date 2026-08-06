# -*- coding: utf-8 -*-
"""
Qual e a unidade certa para qualidade de agua: municipio, bacia ou rio?

Este repositorio vem afirmando que percentual municipal de cobertura e uma
variavel de exposicao ruim. A afirmacao sempre foi indireta — inferida de
modelos que davam nulo. sosma/observando_rios.py mostrou que o corte
transversal municipal nao explica o IQA do ponto, mas isso ainda pode ser
falha da exposicao, do desfecho ou da escala, sem distinguir qual.

Agora da para perguntar direto. Sao 1.135 pontos georreferenciados, 320
municipios e 143 bacias, e os dois niveis se cruzam de verdade: 66 bacias
tocam 2 ou mais municipios e 75 municipios tocam 2 ou mais bacias. Como nao
sao aninhados, a variancia atribuivel a cada um e separavel.

A pergunta vira mensuravel
  Se o municipio fosse a unidade certa, dois pontos no mesmo municipio teriam
  IQA parecido e a maior parte da variancia estaria ENTRE municipios. Se o
  corpo d'agua for a unidade certa, quem manda e o rio, e municipio vira
  ruido administrativo.

  175 municipios tem mais de um ponto (1.256 pontos no total), entao ha
  replicacao interna suficiente para medir isso, e nao para inferir.

Tres testes, do mais descritivo ao mais exigente

  1. DECOMPOSICAO DE VARIANCIA
     Correlacao intraclasse por municipio, por bacia e por corpo d'agua.
     Usa-se ICC e nao R2 de variaveis indicadoras: com 320 municipios e ~1.100
     pontos, o R2 sobe por contagem de parametro e nao por explicacao. O ICC
     compara o quadrado medio entre grupos com o de dentro do grupo e nao tem
     esse vies.

  2. SEMIVARIOGRAMA
     A que distancia dois pontos deixam de se parecer? Isso mede a escala
     espacial em que a qualidade da agua efetivamente varia, direto do dado,
     sem supor nenhuma unidade. Se a escala de correlacao for muito menor que
     o raio tipico de um municipio, o agregado municipal e grosso demais por
     construcao — nao por causa de confundidor.

  3. O PRIMEIRO ELO, DE NOVO, COM EFEITO FIXO DE BACIA
     Comparar pontos dentro da mesma bacia elimina o que a bacia compartilha
     a montante. Se a exposicao municipal continuar nula ai, o problema nao e
     confundimento regional.

O QUE ESTE MODULO NAO FAZ
  Nao delimita area de contribuicao a montante, que seria o certo — rio
  integra o que vem de cima e nada aqui sabe para que lado a agua corre.
  Isso exigiria modelo digital de elevacao ou as ottobacias da ANA, e o
  ambiente nao tem geopandas, shapely nem pyproj. O que ha aqui e a bacia
  nomeada pela propria SOS e a distancia entre pontos, que sao aproximacoes
  grosseiras de "compartilham a mesma agua".

  Distancia e haversine sobre lat/lon, sem projecao. Para as escalas em jogo
  (dezenas de km) o erro e irrelevante.

Uso:  python sosma/geo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "sosma"
PONTOS = BRUTO / "historico_pontos.csv"
ANALISES = BRUTO / "historico_analises.csv"
CENSO = RAIZ / "dados" / "censo_domiciliar_br.csv"

# so medicoes desta safra entram no ponto: o Censo e de 2022 e um ponto medido
# em 2005 descreve outro pais. 2018 e nao 2022 porque a 2022 sozinha derruba a
# amostra pela metade e a inercia de saneamento e de decada, nao de ano.
ANO_MIN = 2018

RAIO_TERRA_KM = 6371.0


def carrega() -> pd.DataFrame:
    a = pd.read_csv(ANALISES)
    a["ano"] = a["data"].str[:4].astype(int)
    # nota zero e registro invalido, nao rio morto
    a = a[a["nota"].notna() & (a["nota"] > 0) & (a["ano"] >= ANO_MIN)]

    agg = (a.groupby("grupo_id")
             .agg(iqa=("nota", "mean"), n_analises=("nota", "size"),
                  iqa_dp=("nota", "std"), ano_ini=("ano", "min"),
                  ano_fim=("ano", "max"))
             .reset_index())

    p = pd.read_csv(PONTOS, dtype={"municipio_id": str})
    d = p.merge(agg, on="grupo_id", how="inner")

    c = pd.read_csv(CENSO, dtype={"cod_ibge": str})
    c["municipio_id"] = c["cod_ibge"].str[:6]
    d = d.merge(c.drop(columns=["municipio", "uf"]), on="municipio_id",
                how="left")

    d = d[d["lat_ponto"].notna() & d["lon_ponto"].notna()].copy()
    d["lat_ponto"] = pd.to_numeric(d["lat_ponto"], errors="coerce")
    d["lon_ponto"] = pd.to_numeric(d["lon_ponto"], errors="coerce")
    return d.dropna(subset=["lat_ponto", "lon_ponto"])


# --------------------------------------------------------------------------
# 1. decomposicao de variancia
# --------------------------------------------------------------------------

def icc(d: pd.DataFrame, chave: str, y: str = "iqa") -> dict | None:
    """Correlacao intraclasse por ANOVA de um fator.

    ICC = (MSB - MSW) / (MSB + (k0-1) * MSW)

    k0 e o tamanho medio corrigido do grupo, nao a media simples: grupos de
    tamanhos muito diferentes enviesam a media simples. E a correcao padrao
    de ANOVA desbalanceada.
    """
    s = d[[chave, y]].dropna()
    g = s.groupby(chave)[y]
    n = g.size()
    s = s[s[chave].isin(n[n >= 1].index)]
    grupos = s[chave].nunique()
    N = len(s)
    if grupos < 2 or N - grupos < 2:
        return None

    media = s[y].mean()
    medias = g.mean()
    ssb = float((n * (medias - media) ** 2).sum())
    ssw = float(((s[y] - s[chave].map(medias)) ** 2).sum())
    msb, msw = ssb / (grupos - 1), ssw / (N - grupos)

    k0 = (N - (n ** 2).sum() / N) / (grupos - 1)
    val = (msb - msw) / (msb + (k0 - 1) * msw) if (msb + (k0 - 1) * msw) else 0.0
    return {"grupos": grupos, "n": N, "k0": k0,
            "icc": max(val, 0.0), "dp_entre": float(np.sqrt(max(
                (msb - msw) / k0, 0.0))), "dp_dentro": float(np.sqrt(msw))}


# --------------------------------------------------------------------------
# 2. semivariograma
# --------------------------------------------------------------------------

def haversine(lat, lon) -> np.ndarray:
    la, lo = np.radians(lat), np.radians(lon)
    dla = la[:, None] - la[None, :]
    dlo = lo[:, None] - lo[None, :]
    h = (np.sin(dla / 2) ** 2
         + np.cos(la)[:, None] * np.cos(la)[None, :] * np.sin(dlo / 2) ** 2)
    return 2 * RAIO_TERRA_KM * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def semivariograma(d: pd.DataFrame, bins) -> pd.DataFrame:
    D = haversine(d["lat_ponto"].to_numpy(), d["lon_ponto"].to_numpy())
    y = d["iqa"].to_numpy()
    dif2 = (y[:, None] - y[None, :]) ** 2
    iu = np.triu_indices(len(d), k=1)
    dist, dif2 = D[iu], dif2[iu]

    linhas = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (dist >= lo) & (dist < hi)
        if m.sum() >= 30:
            linhas.append({"de_km": lo, "ate_km": hi, "pares": int(m.sum()),
                           "semivariancia": dif2[m].mean() / 2})
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------
# 3. o primeiro elo com efeito fixo
# --------------------------------------------------------------------------

def estima(d: pd.DataFrame, x: str, rotulo: str, fe: str | None = None,
           porte: bool = False) -> None:
    s = d.dropna(subset=[x, "iqa"]).copy()
    if fe:
        s = s.dropna(subset=[fe])
        # grupo de um ponto so nao informa nada dentro do grupo e ainda gasta
        # um parametro; sem isso o efeito fixo come a amostra em silencio
        s = s[s.groupby(fe)[fe].transform("size") >= 2]
    if len(s) < 40:
        print(f"  {rotulo:<40} amostra de menos ({len(s)})")
        return

    X = pd.DataFrame({x: s[x] / 10.0}, index=s.index)
    if porte:
        X["log_domicilios"] = np.log(s["domicilios"])
    if fe:
        X = pd.concat([X, pd.get_dummies(s[fe], prefix="fe", drop_first=True,
                                         dtype=float)], axis=1)
    X = sm.add_constant(X)

    m = sm.OLS(s["iqa"], X).fit(cov_type="cluster",
                                cov_kwds={"groups": s["municipio_id"]})
    li, ls = m.conf_int().loc[x]
    print(f"  {rotulo:<40} {m.params[x]:+6.3f}  IC95 [{li:+6.3f}, {ls:+6.3f}]"
          f"  p={m.pvalues[x]:.3f}  n={len(s)}")


def main() -> None:
    d = carrega()
    print(f"pontos com coordenada, bacia e medicao de {ANO_MIN}+: {len(d):,}")
    print(f"municipios {d['municipio_id'].nunique()}   "
          f"bacias {d['bacia'].nunique()}   "
          f"corpos d'agua {d['corpo_dagua'].nunique()}")
    print(f"IQA por ponto: media {d['iqa'].mean():.2f}  "
          f"dp {d['iqa'].std():.2f}\n")

    print("=== 1. a variancia do IQA pertence a que unidade? ===")
    print("ICC alto = pontos do mesmo grupo se parecem = a unidade importa\n")
    print("  'so 2+' descarta grupo de um ponto so: ele nao carrega nenhuma")
    print("  informacao de dentro do grupo e ainda encolhe o k0, que e o que")
    print("  torna o ICC fragil. Se o numero so aparece com singleton, e")
    print("  artefato de grupo pequeno.\n")
    print(f"  {'unidade':<22} {'grupos':>7} {'pontos':>7} {'k0':>5} {'ICC':>7} "
          f"{'dp entre':>9} {'dp dentro':>10}")
    for chave, rot in [("municipio_id", "municipio"), ("bacia", "bacia"),
                       ("corpo_dagua", "corpo d'agua"), ("municipio_uf", "UF")]:
        for minimo, tag in ((1, "todos"), (2, "so 2+")):
            s = d.dropna(subset=[chave])
            s = s[s.groupby(chave)[chave].transform("size") >= minimo]
            r = icc(s, chave)
            if r:
                print(f"  {rot + ' (' + tag + ')':<22} {r['grupos']:7d} "
                      f"{r['n']:7d} {r['k0']:5.1f} {r['icc']:7.3f} "
                      f"{r['dp_entre']:9.2f} {r['dp_dentro']:10.2f}")

    print("\n  E dentro do municipio, quanto o IQA varia?")
    mult = d[d.groupby("municipio_id")["municipio_id"].transform("size") >= 3]
    amp = mult.groupby("municipio_id")["iqa"].agg(["min", "max", "size"])
    amp["amplitude"] = amp["max"] - amp["min"]
    print(f"  {len(amp)} municipios com 3+ pontos; amplitude mediana do IQA "
          f"dentro do municipio: {amp['amplitude'].median():.1f}")
    print(f"  amplitude do IQA entre TODOS os pontos: "
          f"{d['iqa'].max() - d['iqa'].min():.1f}")
    print(f"  razao: {amp['amplitude'].median() / (d['iqa'].max() - d['iqa'].min()):.0%} "
          f"da variacao nacional cabe dentro de um municipio")

    print("\n=== 2. a que distancia dois pontos deixam de se parecer? ===")
    print("semivariancia baixa = parecidos. O patamar e onde a distancia")
    print("deixa de importar; ate la, a agua e compartilhada\n")
    bins = [0, 2, 5, 10, 20, 40, 80, 160, 320, 640, 1280, 6000]
    sv = semivariograma(d, bins)
    patamar = sv["semivariancia"].iloc[-3:].mean()
    print(f"  {'faixa (km)':<14} {'pares':>9} {'semivariancia':>14} "
          f"{'% do patamar':>13}")
    for _, r in sv.iterrows():
        print(f"  {r['de_km']:>5.0f}-{r['ate_km']:<8.0f} {r['pares']:9,.0f} "
              f"{r['semivariancia']:14.2f} {r['semivariancia']/patamar:12.0%}")
    print(f"\n  patamar (media das 3 ultimas faixas): {patamar:.2f}")

    print("\n=== 3. o primeiro elo, controlando o que a bacia compartilha ===")
    print("se a exposicao municipal continuar nula dentro da bacia, o")
    print("problema nao e confundimento regional\n")
    for x, rot in [("esgoto_inadequado_pct", "esgotamento inadequado"),
                   ("esgoto_rede_pct", "cobertura de rede")]:
        estima(d, x, f"{rot}, bruto")
        estima(d, x, f"{rot}, FE de bacia", fe="bacia")
        estima(d, x, f"{rot}, FE de corpo d'agua", fe="corpo_dagua")
        estima(d, x, f"{rot}, FE de bacia + porte", fe="bacia", porte=True)
        print()

    print("=== 4. o teste limpo: mesmo municipio, mesmo rio ou nao ===")
    print("Compara so pares de pontos DENTRO do mesmo municipio, o que segura")
    print("saneamento, renda, registro e porte constantes por construcao. Se")
    print("o municipio fosse a unidade, estar no mesmo rio nao mudaria nada.\n")
    pares(d)

    print("\nCoeficiente = variacao do IQA por 10 p.p. a mais de exposicao.")
    print("Hipotese preve sinal negativo para esgotamento inadequado.")


def pares(d: pd.DataFrame) -> None:
    """Diferenca de IQA entre pares de pontos do mesmo municipio."""
    import itertools

    s = d.dropna(subset=["corpo_dagua"])
    s = s[s.groupby("corpo_dagua")["corpo_dagua"].transform("size") >= 2]

    L = []
    for mun, g in s.groupby("municipio_id"):
        for a, b in itertools.combinations(g.index, 2):
            dist = haversine(
                np.array([s.loc[a, "lat_ponto"], s.loc[b, "lat_ponto"]]),
                np.array([s.loc[a, "lon_ponto"], s.loc[b, "lon_ponto"]]))[0, 1]
            L.append({"mun": mun,
                      "dif": abs(s.loc[a, "iqa"] - s.loc[b, "iqa"]),
                      "mesmo_rio": float(s.loc[a, "corpo_dagua"]
                                         == s.loc[b, "corpo_dagua"]),
                      "dist": dist})
    P = pd.DataFrame(L)
    if len(P) < 40:
        print("  pares de menos")
        return

    print(f"  {len(P)} pares em {P['mun'].nunique()} municipios")
    print(f"  diferenca media do IQA — mesmo rio: "
          f"{P.loc[P.mesmo_rio == 1, 'dif'].mean():.2f}   "
          f"rios diferentes: {P.loc[P.mesmo_rio == 0, 'dif'].mean():.2f}\n")

    # pares que compartilham um ponto nao sao independentes; agrupar por
    # municipio e o mais proximo de honesto sem partir para permutacao
    for cols, rot in [(["mesmo_rio"], "mesmo rio"),
                      (["mesmo_rio", "dist"], "mesmo rio, controlando dist.")]:
        m = sm.OLS(P["dif"], sm.add_constant(P[cols])).fit(
            cov_type="cluster", cov_kwds={"groups": P["mun"]})
        li, ls = m.conf_int().loc["mesmo_rio"]
        print(f"  {rot:<32} {m.params['mesmo_rio']:+6.2f}  "
              f"IC95 [{li:+6.2f}, {ls:+6.2f}]  p={m.pvalues['mesmo_rio']:.4f}")
        if "dist" in cols:
            print(f"  {'    distancia, por km':<32} {m.params['dist']:+6.4f}"
                  f"{'':>22}  p={m.pvalues['dist']:.3f}")


if __name__ == "__main__":
    main()
