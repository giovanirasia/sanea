# Óbitos por doença infecciosa intestinal, por município — 2008 a 2024

Óbitos com causa básica em **A00–A09** (CID-10: cólera, febre tifoide, shigelose,
amebíase, diarreias e gastroenterites de origem infecciosa presumível), por município, ano
e faixa etária, para os 5.570 municípios brasileiros. Fonte: SIM/DATASUS.

Arquivo: [`obitos_hidricas_br.csv`](obitos_hidricas_br.csv) · gerado por
[`saude/sim.py`](../saude/sim.py) com `SANEA_ESCOPO=br`

## O que tem dentro

327.271 linhas, 5.570 municípios, 27 UFs, 17 anos — as 459 combinações UF × ano estão
todas presentes. Confira sua cópia contra estes totais:

| | |
|---|---|
| Óbitos por A00–A09 | **81.125** |
| Óbitos por qualquer causa | 22.510.733 |
| Óbitos por causa mal definida | 1.292.285 (5,7%) |

Por faixa etária, os óbitos por A00–A09: **12.187** em menores de 5 anos, 1.462 de 5 a 19,
10.537 de 20 a 59, e 56.939 de 60 ou mais.

Em menores de 5 a queda no período é grande e real: 1.470 óbitos em 2008, 684 em 2016,
566 em 2024.

## Por que existe

O SIM é público, mas não em forma de painel. O TabNet entrega uma consulta por vez, em
HTML, e não cruza município com faixa etária de forma exportável; quem quer a série monta
na mão a partir dos arquivos DBC, um por UF e ano — 459 arquivos para este recorte.

E monta errado com facilidade, porque o campo de idade do SIM não é um número. São três
caracteres em que o **primeiro dígito é a unidade** e os dois seguintes a quantidade:

| Primeiro dígito | Unidade |
|---|---|
| 0 | minutos |
| 1 | horas |
| 2 | dias |
| 3 | meses |
| 4 | anos |
| 5 | anos, somar 100 |

Assim `310` é dez meses e `410` é dez anos. Ler o campo como inteiro mistura lactente com
criança e adulto — e óbito de lactente é justamente o que mais importa nesta causa.

## O denominador de qualidade vai junto — e não é opcional

Cada linha traz três contagens, não uma:

- `obitos_a00a09` — o desfecho
- `obitos_total` — todos os óbitos daquele município, ano e faixa
- `obitos_mal_definidos` — óbitos com causa básica no capítulo XVIII (R00–R99):
  sintomas, sinais e achados anormais, ou seja, morte sem causa determinada

A terceira coluna existe por uma razão concreta, aprendida ao analisar o Maranhão. **A
taxa de mortalidade por causa específica cai onde o registro é pior, não onde a doença é
menor.** Nos municípios mais pobres e rurais, a mortalidade registrada por *todas* as
causas em menores de 5 anos é mais baixa — o que não é crível como fato biológico, e é
sub-registro. Quem usar `obitos_a00a09` sozinho, com denominador populacional, vai
encontrar saneamento precário associado a *menos* morte, e vai publicar isso.

Publicar a série de causa específica sem as duas colunas de contexto é entregar uma
armadilha. Com elas, dá para checar antes de concluir:

```python
d = pd.read_csv("obitos_hidricas_br.csv")
g = d.groupby("uf").sum(numeric_only=True)
g["pct_mal_definidos"] = 100 * g.obitos_mal_definidos / g.obitos_total
```

Agregado por região, o gradiente aparece — e é o mesmo gradiente da exposição a saneamento
precário, que é exatamente o problema:

| Região | Óbitos A00–A09 | Causa mal definida |
|---|---|---|
| Norte | 7.949 | 8,3% |
| Nordeste | 30.977 | 6,6% |
| Sudeste | 27.004 | 6,0% |
| Sul | 9.985 | 3,8% |
| Centro-Oeste | 5.210 | 3,0% |

## Colunas

| Coluna | Descrição |
|---|---|
| `cod_ibge` | código IBGE do município, 7 dígitos |
| `municipio` | nome do município |
| `uf` | sigla da unidade da federação |
| `ano` | 2008 a 2024 |
| `faixa` | `0a4`, `5a19`, `20a59`, `60mais` |
| `obitos_a00a09` | óbitos com causa básica em A00–A09 |
| `obitos_mal_definidos` | óbitos com causa básica em R00–R99 |
| `obitos_total` | óbitos por qualquer causa |

Há linha apenas para as combinações município × ano × faixa com pelo menos um óbito
registrado. Ausência de linha é ausência de óbito, não dado faltante.

O município é o de **residência** (`CODMUNRES`), não o de ocorrência — é o que casa com
denominador populacional. Óbitos com município ignorado (código terminado em `0000`) são
descartados.

## Como cruzar

Com o saneamento domiciliar do mesmo repositório, pelo `cod_ibge`:

```python
obitos = pd.read_csv("obitos_hidricas_br.csv")
sanea  = pd.read_csv("censo_domiciliar_br.csv")
d = obitos.merge(sanea, on=["cod_ibge", "municipio", "uf"])
```

Os nomes de município das duas tabelas vêm da mesma fonte, então casam sem normalização.
Ver [`censo_domiciliar_br.md`](censo_domiciliar_br.md).

Para denominador populacional você precisa de população por faixa etária — o Censo 2022
dá a estrutura (SIDRA 9514) e a tabela 6579 dá a população anual.

## Limites

- **Sub-registro de óbito**, historicamente maior no Norte e Nordeste e caindo ao longo da
  série. Parte da tendência temporal é melhora de cobertura do sistema, não queda de
  mortalidade.
- **Causa mal definida** absorve óbitos que deveriam estar em A00–A09, e essa má definição
  é maior onde há menos assistência médica. Daí a coluna.
- **Causa básica, não causa associada.** Diarreia que contribuiu para uma morte atribuída
  a desnutrição ou pneumonia não aparece aqui.
- **2024 é o último ano fechado** na publicação do SIM; anos recentes podem sofrer revisão.
- A faixa etária usa idade no óbito, não coorte.

## Reproduzir

```bash
SANEA_ESCOPO=br python saude/sim.py
```

São 459 arquivos do FTP do DATASUS (~4,4 GB), baixados em processos paralelos
(`SANEA_PARALELO`, padrão 4) e cacheados já filtrados em `dados/bruto/sim/`. O cache é por
UF e ano, então um recorte estadual e o nacional reaproveitam o mesmo disco.

Fonte: Ministério da Saúde, DATASUS — Sistema de Informações sobre Mortalidade (SIM),
arquivos DO. Os dados de origem seguem a licença do DATASUS; o código deste repositório é
MIT.
