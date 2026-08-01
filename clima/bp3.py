# -*- coding: utf-8 -*-
"""
Municipios da Bacia Hidrografica do Parana 3 (BP3), com codigo IBGE e centroide.

A pergunta: quais municipios compoem a area do Comite BP3, e onde eles ficam?
Sem codigo IBGE nao da para juntar com SINISA nem DATASUS; sem coordenada nao
da para puxar serie de chuva.

Metodo
  - lista dos 35 municipios: area de atuacao do CBH Parana 3 (IAT / Governo do PR)
  - codigo IBGE: API de localidades do IBGE, pareado por nome sem acento
  - centroide: media dos vertices da malha municipal (API de malhas do IBGE)

Limites
  - o centroide da malha nao e a sede urbana; para chuva em escala de bacia a
    diferenca e irrelevante (ordem de 10 km), para qualquer coisa pontual nao e
  - a lista de municipios precisa ser confirmada com o comite antes de virar
    numero publicado: area de atuacao muda por resolucao

Saida
  dados/bp3_municipios.csv
"""

from __future__ import annotations

import gzip
import json
import time
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "malhas"
SAIDA = RAIZ / "dados" / "bp3_municipios.csv"

UF_PARANA = 41
IBGE_MUNICIPIOS = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF_PARANA}/municipios"
IBGE_MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}"
              "?formato=application/vnd.geo+json")

# Area de atuacao do Comite da Bacia Hidrografica do Parana 3 — 35 municipios,
# 8.744 km2. Fonte: Instituto Agua e Terra (IAT), Governo do Parana.
# https://www.iat.pr.gov.br/Pagina/Comite-da-Bacia-do-Parana-3
BP3 = [
    "Assis Chateaubriand", "Boa Vista da Aparecida", "Braganey", "Cafelandia",
    "Capitao Leonidas Marques", "Cascavel", "Ceu Azul", "Corbelia",
    # o IBGE grafa "Diamante D'Oeste"; materiais do comite usam "do Oeste"
    "Diamante D'Oeste", "Entre Rios do Oeste", "Foz do Iguacu", "Guaira",
    "Ibema", "Iracema do Oeste", "Jesuitas", "Lindoeste",
    "Marechal Candido Rondon", "Matelandia", "Medianeira", "Mercedes",
    "Nova Aurora", "Ouro Verde do Oeste", "Palotina", "Pato Bragado",
    "Quatro Pontes", "Ramilandia", "Santa Helena", "Santa Lucia",
    "Santa Tereza do Oeste", "Sao Jose das Palmeiras", "Sao Miguel do Iguacu",
    "Terra Roxa", "Toledo", "Tres Barras do Parana", "Vera Cruz do Oeste",
]


def normaliza(s: str) -> str:
    """Minuscula, sem acento, sem espaco duplo — para parear nome de municipio."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def _baixa_json(url: str, destino: Path | None = None) -> dict | list:
    """Baixa JSON, cacheando em disco. A API do IBGE responde gzip mesmo sem
    Accept-Encoding, e o urllib nao descomprime sozinho — dai a checagem."""
    if destino is not None and destino.exists():
        return json.loads(destino.read_text(encoding="utf-8"))
    with urllib.request.urlopen(url, timeout=60) as resp:
        dados = resp.read()
    if dados[:2] == b"\x1f\x8b":
        dados = gzip.decompress(dados)
    bruto = dados.decode("utf-8")
    if destino is not None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(bruto, encoding="utf-8")
    return json.loads(bruto)


def codigos_ibge() -> dict[str, int]:
    """Nome normalizado -> codigo IBGE, para todos os municipios do PR."""
    dados = _baixa_json(IBGE_MUNICIPIOS, BRUTO / "pr_municipios.json")
    return {normaliza(m["nome"]): m["id"] for m in dados}


def _vertices(coords) -> list[tuple[float, float]]:
    """Achata coordenadas GeoJSON de qualquer profundidade em lista de (lon, lat)."""
    if isinstance(coords[0], (int, float)):
        return [(coords[0], coords[1])]
    out = []
    for c in coords:
        out.extend(_vertices(c))
    return out


def centroide(cod: int) -> tuple[float, float]:
    """Centroide aproximado da malha municipal: media dos vertices. (lat, lon)"""
    geo = _baixa_json(IBGE_MALHA.format(cod=cod), BRUTO / f"malha_{cod}.json")
    pts = _vertices(geo["features"][0]["geometry"]["coordinates"])
    lat = sum(p[1] for p in pts) / len(pts)
    lon = sum(p[0] for p in pts) / len(pts)
    return round(lat, 5), round(lon, 5)


def main() -> None:
    mapa = codigos_ibge()

    faltando = [m for m in BP3 if normaliza(m) not in mapa]
    if faltando:
        raise SystemExit(f"nao encontrados no IBGE (PR): {faltando}")

    linhas = []
    for nome in BP3:
        cod = mapa[normaliza(nome)]
        lat, lon = centroide(cod)
        linhas.append({"cod_ibge": cod, "municipio": nome, "lat": lat, "lon": lon})
        time.sleep(0.2)  # cortesia com a API do IBGE

    df = pd.DataFrame(linhas).sort_values("municipio").reset_index(drop=True)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False)

    print(f"BP3: {len(df)} municipios")
    print(f"extensao: lat {df['lat'].min():.2f} a {df['lat'].max():.2f}, "
          f"lon {df['lon'].min():.2f} a {df['lon'].max():.2f}")
    print()
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
