# -*- coding: utf-8 -*-
"""
Serie temporal de qualidade de agua por ponto, do Observando os Rios.

sosma/observando_rios.py extraiu o mapa e testou o primeiro elo da cadeia
causal em corte transversal. O resultado foi nulo, e o motivo ficou claro: a
associacao bruta saiu INVERTIDA (esgotamento inadequado com rio melhor, +0,482)
porque cobertura de saneamento e qualidade de rio sao ambas funcao do porte do
municipio. Com log(domicilios) e efeito fixo de UF, tudo vai a zero — inclusive
o controle negativo (agua de rede), que nao tem como sujar rio nenhum e mesmo
assim "explicava" o IQA.

Corte transversal nao resolve isso. Mesmo ponto ao longo do tempo, sim: porte
do municipio, selecao do ponto, heranca industrial e canalizacao sao fixos
dentro do ponto. E a cobertura varia (Censo 2010 -> 2022, SINISA anual).

O que a pagina de cada grupo entrega
  /grupo/{grupo_id}/{slug}?de=DD/MM/AAAA&ate=DD/MM/AAAA

  O slug e ignorado pelo servidor — basta o grupo_id. Sem paginacao: uma
  requisicao com janela larga traz a serie inteira. O padrao da pagina e uma
  janela movel de 12 meses, entao SEM os parametros de data se perde quase
  tudo (o ponto 476 mostra 10 analises no padrao e 99 com a janela aberta).

  Alem da serie, a pagina tem campos que o JSON do mapa nao tem:
    bacia               unidade hidrografica — a unidade certa para rio, e a
                        que o limite municipal nao respeita
    ponto monitorado    descricao textual e coordenada exata do ponto
    data de formacao    quando o grupo comecou a medir
    participantes       quantos estiveram em cada coleta

  E cada analise traz os parametros com VALOR, nao so a nota do kit: OD e DBO
  em ppm, nitrato, fosfato, turbidez em UTJ, pH. Isso importa porque o IQA
  composto quase nao varia (intervalo interquartil de 5 pontos numa escala de
  14 a 40), enquanto DBO e fosfato sao marcadores diretos de carga de esgoto e
  tem variancia de verdade.

O QUE AINDA AMEACA O DESENHO
  1. Rotatividade de voluntario NAO e fixa dentro do ponto. Grupo que troca de
     observador muda de leitura, e numa medida com julgamento visual de
     espuma, cheiro e lixo flutuante isso desloca o nivel sem que o rio tenha
     mudado. Efeito fixo de ponto nao corrige. O campo "participantes" e o
     hiato entre coletas sao os unicos sintomas disponiveis.

  2. O placebo e obrigatorio. saude/tendencia_previa.py reprovou o desenho de
     primeiras diferencas na mortalidade (0,960, p=0,048). Nao ha razao para
     supor que aqui passe, e o custo de descobrir depois e alto.

  3. Buraco da COVID: 2020-2021 quase sem coleta em muitos grupos.

  4. Nota final igual a zero e registro invalido, nao rio morto.

CONDUTA DE COLETA
  Sao ~1.400 requisicoes contra o servidor de uma ONG. O intervalo padrao e de
  2 segundos e nao existe modo paralelo de proposito. O cache e por grupo e a
  coleta e retomavel: interromper e repetir nao rebaixa o que ja veio.

  A autorizacao veio de Gustavo Veronesi, coordenador tecnico do programa, que
  confirmou por mensagem que os dados sao publicos e apontou esta pagina.

Uso:
  python sosma/historico.py --coleta [--limite 15] [--intervalo 2.0]
  python sosma/historico.py --parse
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRUTO = RAIZ / "dados" / "bruto" / "sosma"
PAGINAS = BRUTO / "grupos"
GRUPOS = BRUTO / "grupos.json"
SAIDA_PONTOS = BRUTO / "historico_pontos.csv"
SAIDA_ANALISES = BRUTO / "historico_analises.csv"

BASE = "https://observandoosrios.sosma.org.br/grupo/{id}/x?de={de}&ate={ate}"
CABECALHO = {"User-Agent": "SANEA/1.0 (pesquisa academica; dados publicos)"}

# janela larga: o programa comecou em 1993, e ha digitacao ate 2026
DE, ATE = "01%2F01%2F1990", "31%2F12%2F2026"

MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
         "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
         "outubro": 10, "novembro": 11, "dezembro": 12}

# rotulo na pagina -> nome de coluna. Deixar explicito em vez de gerar slug
# automatico: se a SOS renomear um parametro, o parse falha alto em vez de
# criar uma coluna nova em silencio e quebrar a serie ao meio.
PARAMETROS = {
    "Nota Final": "nota",
    "Participantes": "participantes",
    "Temperatura Ambiente": "temp_ambiente",
    "Temperatura da Água": "temp_agua",
    "Transparência da Água / Turbidez": "turbidez",
    "Espumas": "espumas",
    "Lixo Flutuante": "lixo_flutuante",
    "Cheiro": "cheiro",
    "Material Sedimentável": "sedimentavel",
    "Peixes": "peixes",
    "Larvas e Vermes Vermelhos": "larvas_vermelhas",
    "Larvas/Vermes Transp. ou escuros": "larvas_transp",
    "Coliformes Totais": "coliformes",
    "Oxigênio Dissolvido (OD)": "od",
    "Demanda Bioquímica de Oxigênio (DBO)": "dbo",
    "Potencial Hidrogeniônico (pH)": "ph",
    "Nitrato (NO3)": "nitrato",
    "Fosfatos (PO4)": "fosfato",
}

# parametros em que o numero entre parenteses e o valor medido; nos demais o
# unico numero e a nota do kit (1 a 3)
COM_VALOR = {"turbidez", "od", "dbo", "ph", "nitrato", "fosfato"}

INFO = {"Bacia": "bacia", "Cidade": "cidade",
        "Corpo d´Água Monitorado": "corpo_dagua",
        "Ponto Monitorado": "ponto", "Categoria": "categoria",
        "Faixa Etária": "faixa_etaria", "Data de Formação": "formacao"}


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

class PaginaGrupo(HTMLParser):
    """Extrai cabecalho do grupo e a lista de analises.

    HTMLParser da stdlib em vez de BeautifulSoup: o repositorio nao tem
    dependencia de terceiros para leitura de HTML e nao vale criar uma por
    uma pagina de estrutura fixa. Em compensacao o estado e explicito.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.info: dict[str, str] = {}
        self.coord: str | None = None
        self.analises: list[dict] = []
        # profundidade de <div> aberta desde o inicio do bloco; None = fora.
        # Contar divs em vez de manter pilha de todas as tags e deliberado:
        # HTMLParser nao emite handle_endtag para elemento vazio (<br>, <img>,
        # <input>), entao qualquer pilha generica desalinha e os blocos passam
        # a fechar no lugar errado. Custou 99 analises viradas 31 antes de
        # aparecer. <div> nunca e vazia, entao contar so ela e exato.
        self._div_card: int | None = None
        self._div_info: int | None = None
        self._buf: list[str] = []
        self._captura = False
        self._rotulo: str | None = None
        self._atual: dict | None = None

    # -- helpers ----------------------------------------------------------
    def _texto(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._buf)).strip()

    def _destino(self) -> dict | None:
        if self._div_card is not None:
            return self._atual
        if self._div_info is not None:
            return self.info
        return None

    # -- eventos ----------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")

        if tag == "div":
            if self._div_card is not None:
                self._div_card += 1
            elif "card-analisys" in cls:
                self._div_card, self._atual = 1, {}

            if self._div_info is not None:
                self._div_info += 1
            elif a.get("id") == "grupo-info":
                self._div_info = 1

        if tag == "a" and "maps.google" in a.get("href", "") and not self.coord:
            self.coord = a["href"].split("q=", 1)[-1]

        if tag in ("dt", "dd") or (tag == "h5" and "card-title" in cls):
            self._buf, self._captura = [], True

    def handle_data(self, data):
        if self._captura:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._captura and tag in ("dt", "dd", "h5"):
            txt = self._texto()
            self._captura = False
            if tag == "h5":
                if self._atual is not None:
                    self._atual["quando"] = txt
            elif tag == "dt":
                self._rotulo = txt
            elif tag == "dd" and self._rotulo:
                d = self._destino()
                if d is not None:
                    d[self._rotulo] = txt
                self._rotulo = None

        if tag == "div":
            if self._div_card is not None:
                self._div_card -= 1
                if self._div_card == 0:
                    if self._atual:
                        self.analises.append(self._atual)
                    self._div_card, self._atual = None, None
            if self._div_info is not None:
                self._div_info -= 1
                if self._div_info == 0:
                    self._div_info = None


def _numero(txt: str) -> float | None:
    m = re.search(r"-?\d+(?:[.,]\d+)?", txt or "")
    return float(m.group().replace(",", ".")) if m else None


def _quando(txt: str) -> tuple[str | None, str | None]:
    """'02 de maio, 2026 - 14h45min Parcialmente Nublado' -> data, clima."""
    m = re.match(r"(\d{1,2}) de ([^,]+),\s*(\d{4})\s*-\s*(\d{1,2})h(\d{2})",
                 txt or "")
    if not m:
        return None, None
    dia, mes, ano, h, mi = m.groups()
    n = MESES.get(mes.strip().lower())
    if not n:
        return None, None
    clima = txt[m.end():].strip() or None
    return f"{ano}-{n:02d}-{int(dia):02d} {int(h):02d}:{mi}", clima


def parse(html: str, grupo_id: str) -> tuple[dict, list[dict]]:
    p = PaginaGrupo()
    p.feed(html)

    lat, lon = (None, None)
    if p.coord and "," in p.coord:
        lat, lon = (x.strip() for x in p.coord.split(",", 1))

    ponto = {"grupo_id": grupo_id, "lat_ponto": lat, "lon_ponto": lon,
             "n_analises": len(p.analises)}
    for rot, col in INFO.items():
        ponto[col] = p.info.get(rot)
    if ponto.get("ponto") and lat:
        # a descricao vem com a coordenada colada; separar
        ponto["ponto"] = ponto["ponto"].replace(f"{lat},{lon}", "").strip()

    linhas = []
    desconhecidos = set()
    for a in p.analises:
        data, clima = _quando(a.get("quando", ""))
        if not data:
            continue
        L = {"grupo_id": grupo_id, "data": data, "clima": clima}
        for rot, val in a.items():
            if rot == "quando":
                continue
            col = PARAMETROS.get(rot)
            if col is None:
                desconhecidos.add(rot)
                continue
            if col == "nota":
                L["nota"] = _numero(val)
                L["classe"] = val.split("-", 1)[-1].strip() if "-" in val else None
            elif col in ("participantes", "temp_ambiente", "temp_agua"):
                L[col] = _numero(val)
            else:
                m = re.match(r"\s*(\d+)\s*(?:\(([^)]*)\))?", val or "")
                L[col] = float(m.group(1)) if m else None
                if col in COM_VALOR:
                    L[col + "_valor"] = _numero(m.group(2)) if m and m.group(2) else None
        linhas.append(L)

    if desconhecidos:
        print(f"  ! grupo {grupo_id}: rotulo nao mapeado {sorted(desconhecidos)}",
              file=sys.stderr)
    return ponto, linhas


# --------------------------------------------------------------------------
# coleta
# --------------------------------------------------------------------------

def caminho(grupo_id: str) -> Path:
    return PAGINAS / f"{grupo_id}.html.gz"


def coleta(ids: list[str], intervalo: float, limite: int | None) -> None:
    PAGINAS.mkdir(parents=True, exist_ok=True)
    pendentes = [i for i in ids if not caminho(i).exists()]
    if limite:
        pendentes = pendentes[:limite]

    print(f"{len(ids)} grupos, {len(ids) - len([i for i in ids if not caminho(i).exists()])} em cache, "
          f"{len(pendentes)} a buscar (intervalo {intervalo}s)")
    if not pendentes:
        return
    print(f"tempo estimado: {len(pendentes) * intervalo / 60:.0f} min\n")

    falhas = []
    for n, gid in enumerate(pendentes, 1):
        url = BASE.format(id=gid, de=DE, ate=ATE)
        try:
            req = urllib.request.Request(url, headers=CABECALHO)
            with urllib.request.urlopen(req, timeout=120) as r:
                corpo = r.read()
            tmp = caminho(gid).with_suffix(".gz.parcial")
            with gzip.open(tmp, "wb") as f:
                f.write(corpo)
            tmp.replace(caminho(gid))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            falhas.append((gid, str(e)))
            print(f"  ! {gid}: {e}", file=sys.stderr)

        if n % 25 == 0 or n == len(pendentes):
            print(f"  {n}/{len(pendentes)}")
        if n < len(pendentes):
            time.sleep(intervalo)

    if falhas:
        print(f"\n{len(falhas)} falhas; rodar de novo retoma so elas")


def processa() -> None:
    arquivos = sorted(PAGINAS.glob("*.html.gz"))
    if not arquivos:
        raise SystemExit("nada coletado ainda; rodar com --coleta")

    mapa = {str(g["grupo_id"]): g for g in json.loads(
        GRUPOS.read_text(encoding="utf-8"))}

    pontos, analises = [], []
    for a in arquivos:
        gid = a.name.split(".")[0]
        with gzip.open(a, "rb") as f:
            html = f.read().decode("utf-8", errors="replace")
        p, ls = parse(html, gid)
        m = mapa.get(gid, {})
        p.update(codigo=m.get("codigo"), municipio_id=m.get("municipio_id"),
                 municipio_uf=m.get("municipio_uf"), ativo=m.get("grupo_status"),
                 lat_mapa=m.get("latitude"), lon_mapa=m.get("longitude"))
        pontos.append(p)
        analises.extend(ls)

    def grava(caminho_saida: Path, linhas: list[dict]) -> None:
        cols: list[str] = []
        for l in linhas:
            for k in l:
                if k not in cols:
                    cols.append(k)
        with caminho_saida.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(linhas)

    grava(SAIDA_PONTOS, pontos)
    grava(SAIDA_ANALISES, analises)

    anos = sorted({l["data"][:4] for l in analises})
    com_serie = sum(1 for p in pontos if (p["n_analises"] or 0) >= 8)
    print(f"pontos processados: {len(pontos)}")
    print(f"analises: {len(analises):,}  de {anos[0]} a {anos[-1]}")
    print(f"pontos com 8+ analises (serie usavel): {com_serie}")
    print(f"com coordenada do ponto: "
          f"{sum(1 for p in pontos if p['lat_ponto'])}")
    print(f"com bacia: {sum(1 for p in pontos if p.get('bacia'))}")
    zeros = sum(1 for l in analises if l.get("nota") == 0)
    print(f"nota zero (registro invalido): {zeros}")
    print(f"\n{SAIDA_PONTOS.relative_to(RAIZ)}\n{SAIDA_ANALISES.relative_to(RAIZ)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coleta", action="store_true")
    ap.add_argument("--parse", action="store_true")
    ap.add_argument("--intervalo", type=float, default=2.0)
    ap.add_argument("--limite", type=int,
                    help="buscar apenas os N primeiros pendentes (piloto)")
    a = ap.parse_args()
    if not (a.coleta or a.parse):
        ap.error("escolher --coleta e/ou --parse")

    if a.coleta:
        ids = [str(g["grupo_id"]) for g in json.loads(
            GRUPOS.read_text(encoding="utf-8"))]
        coleta(ids, a.intervalo, a.limite)
    if a.parse:
        processa()


if __name__ == "__main__":
    main()
