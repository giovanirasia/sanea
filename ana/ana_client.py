# -*- coding: utf-8 -*-
"""
Cliente do HidroWebService da ANA (API de estacoes telemetricas).

Contrato conferido no manual oficial "Servico de Disponibilizacao de Dados
Hidrologicos - API HidroWebService", versao 20/02/2026:

  base   https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas
  auth   GET /OAUth/v1  com headers "Identificador" e "Senha"
         -> items.tokenautenticacao, validade de 60 minutos
  dados  header Authorization: Bearer <token>

O manual avisa explicitamente que autenticacoes em alta frequencia sao
monitoradas e podem levar ao bloqueio automatico do IP. Por isso o token e
gravado em cache em disco e so e renovado quando falta menos de 5 minutos
para expirar.

Credenciais: nunca ficam no codigo. Preencha o arquivo .env ao lado deste
script (veja .env.example).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
AQUI = Path(__file__).resolve().parent
CACHE = AQUI / ".token_cache.json"
TTL_SEGUNDOS = 60 * 60
MARGEM = 5 * 60


# --------------------------------------------------------------------------
# credenciais
# --------------------------------------------------------------------------
def carrega_env() -> None:
    """Le o .env ao lado do script para o ambiente, sem sobrescrever o que ja existe."""
    env = AQUI / ".env"
    if not env.exists():
        return
    for linha in env.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


def credenciais() -> tuple[str, str]:
    carrega_env()
    ident = os.environ.get("ANA_IDENTIFICADOR")
    senha = os.environ.get("ANA_SENHA")
    if not ident or not senha:
        sys.exit(
            "Faltam credenciais.\n"
            f"Crie {AQUI / '.env'} com:\n"
            "  ANA_IDENTIFICADOR=seu_cpf_ou_cnpj\n"
            "  ANA_SENHA=sua_senha\n"
        )
    return ident, senha


# --------------------------------------------------------------------------
# token
# --------------------------------------------------------------------------
def _token_em_cache() -> str | None:
    if not CACHE.exists():
        return None
    try:
        dados = json.loads(CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if time.time() - dados.get("obtido_em", 0) > TTL_SEGUNDOS - MARGEM:
        return None
    return dados.get("token")


def token(forcar: bool = False) -> str:
    if not forcar:
        cache = _token_em_cache()
        if cache:
            return cache

    ident, senha = credenciais()
    req = urllib.request.Request(
        f"{BASE}/OAUth/v1",
        headers={"Identificador": ident, "Senha": senha},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        corpo = json.loads(resp.read().decode("utf-8"))

    itens = corpo.get("items") or {}
    tok = itens.get("tokenautenticacao")
    if not tok:
        sys.exit(f"Autenticacao sem token na resposta: {json.dumps(corpo)[:400]}")

    CACHE.write_text(
        json.dumps({"token": tok, "obtido_em": time.time(), "validade": itens.get("validade")}),
        encoding="utf-8",
    )
    try:
        os.chmod(CACHE, 0o600)
    except OSError:
        pass
    return tok


# --------------------------------------------------------------------------
# rotas
# --------------------------------------------------------------------------
class HidroError(RuntimeError):
    """Erro HTTP vindo do servico, com o codigo preservado para o chamador decidir."""

    def __init__(self, codigo: int, mensagem: str):
        super().__init__(f"HTTP {codigo}: {mensagem}")
        self.codigo = codigo
        self.mensagem = mensagem


def consulta(rota: str, params: dict | None = None) -> dict:
    """
    GET autenticado numa rota do servico. Renova o token uma vez em caso de 401/403.

    Atencao: os nomes dos parametros da API tem ESPACOS E ACENTOS
    ("Unidade Federativa", "Codigo da Estacao"). Por isso params vem como dict,
    e nao como **kwargs. O exemplo Java do manual usa nomes sem espaco
    (CodigoDaEstacao) que NAO funcionam — o spec em /hidrowebservice/api-docs
    e a fonte correta.
    """
    params = params or {}
    for tentativa in (1, 2):
        url = f"{BASE}/{rota}"
        limpos = {k: v for k, v in params.items() if v is not None}
        if limpos:
            url += "?" + urllib.parse.urlencode(limpos, quote_via=urllib.parse.quote)
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {token(forcar=tentativa == 2)}"}, method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and tentativa == 1:
                continue
            corpo = e.read().decode("utf-8", "replace")
            # o 503 vem como pagina HTML do proxy; nao adianta mostrar o HTML inteiro
            if "<html" in corpo.lower():
                corpo = "servico indisponivel (resposta HTML do proxy)"
            raise HidroError(e.code, corpo[:300])
    raise HidroError(0, "falha inesperada")


def inventario(uf: str | None = None, codigo_estacao: str | None = None,
               codigo_bacia: int | None = None) -> dict:
    """
    Inventario de estacoes. Exige pelo menos um de: UF, codigo da estacao ou bacia
    (senao a API devolve 406). Retorna Latitude, Longitude, Municipio_Nome,
    Tipo_Estacao, Operando, entre outros.
    """
    return consulta("HidroInventarioEstacoes/v1", {
        "Unidade Federativa": uf,
        "Código da Estação": codigo_estacao,
        "Código da Bacia": codigo_bacia,
    })


def serie_adotada(codigos: str, range_busca: str = "DIAS_30") -> dict:
    """
    Serie telemetrica adotada (chuva, cota, vazao) com status de qualidade.
    Usa a v2, que aceita varias estacoes de uma vez (separadas por virgula).
    """
    return consulta("HidroinfoanaSerieTelemetricaAdotada/v2", {
        "Codigos_Estacoes": codigos,
        "Tipo Filtro Data": "DATA_LEITURA",
        "Range Intervalo de busca": range_busca,
    })


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(description="Cliente do HidroWebService da ANA")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("token", help="obtem/renova o token e mostra apenas o prefixo")
    s.add_argument("--forcar", action="store_true")

    s = sub.add_parser("inventario", help="baixa o inventario de estacoes")
    s.add_argument("--uf", help="sigla da UF, ex: SP")
    s.add_argument("--estacao", help="codigo da estacao")
    s.add_argument("--bacia", type=int, help="codigo da bacia (1-9)")
    s.add_argument("--out", type=Path)

    s = sub.add_parser("serie", help="serie telemetrica adotada (aceita varios codigos)")
    s.add_argument("codigos", help="um codigo ou varios separados por virgula")
    s.add_argument("--range", default="DIAS_30")
    s.add_argument("--out", type=Path)

    a = p.parse_args()

    if a.cmd == "token":
        t = token(forcar=a.forcar)
        print(f"token ok: {t[:12]}... ({len(t)} chars) — cache em {CACHE.name}")
        return

    try:
        if a.cmd == "inventario":
            if not (a.uf or a.estacao or a.bacia):
                sys.exit("Informe --uf, --estacao ou --bacia (a API exige ao menos um).")
            r = inventario(uf=a.uf, codigo_estacao=a.estacao, codigo_bacia=a.bacia)
        else:
            r = serie_adotada(a.codigos, a.range)
    except HidroError as e:
        sys.exit(str(e))

    itens = r.get("items") or []
    print(f"status={r.get('status')} code={r.get('code')} itens={len(itens)}")
    if a.out:
        a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"gravado em {a.out}")
    elif itens:
        print(json.dumps(itens[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
