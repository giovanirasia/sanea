# -*- coding: utf-8 -*-
"""
Que recorte territorial estamos analisando.

Todo modulo deste repositorio le SANEA_ESCOPO e se comporta de acordo. Ate
aqui cada um carregava sua propria copia da lista de escopos validos e do
codigo da UF, o que funcionava enquanto havia dois recortes do mesmo estado.
Ao acrescentar o Maranhao isso vira seis lugares para editar por estado novo,
e basta esquecer um para o modulo baixar dado do Parana e gravar em arquivo
com nome de Maranhao — erro silencioso e caro de achar.

Dois tipos de recorte
  lista propria   a Bacia Parana 3, que e um conjunto de municipios definido
                  por criterio hidrografico e nao coincide com nenhuma UF
  UF inteira      Parana, Maranhao — o filtro e o prefixo do codigo IBGE, e
                  nao ha lista a manter

Por que o Maranhao entrou: no Parana a doenca de veiculacao hidrica letal em
crianca praticamente nao existe mais (58 obitos em 19 anos no estado inteiro),
e nao se mede variacao no que ja foi resolvido. O Maranhao tem a pior
cobertura de saneamento do pais e mortalidade infantil por diarreia ainda
existente, entao e onde a pergunta original continua viva.
"""

from __future__ import annotations

import os

# escopo -> (codigo IBGE da UF, sigla)
ESCOPOS = {
    "bp3": (41, "PR"),
    "parana": (41, "PR"),
    "maranhao": (21, "MA"),
}

# recortes que precisam de uma lista de municipios mantida a mao; os demais
# sao a UF inteira e se resolvem pelo prefixo do codigo IBGE
COM_LISTA_PROPRIA = {"bp3"}


def atual() -> str:
    esc = os.environ.get("SANEA_ESCOPO", "bp3")
    if esc not in ESCOPOS:
        raise SystemExit(
            f"SANEA_ESCOPO invalido: {esc}. "
            f"Validos: {', '.join(sorted(ESCOPOS))}")
    return esc


def uf(esc: str | None = None) -> int:
    """Codigo IBGE da UF do recorte (41 = PR, 21 = MA)."""
    return ESCOPOS[esc or atual()][0]


def sigla(esc: str | None = None) -> str:
    """Sigla da UF, como o DATASUS nomeia os arquivos: RDPR, DOMA."""
    return ESCOPOS[esc or atual()][1]


def uf_inteira(esc: str | None = None) -> bool:
    return (esc or atual()) not in COM_LISTA_PROPRIA
