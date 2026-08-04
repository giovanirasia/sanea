# Saneamento domiciliar por município — Censo 2022

Esgotamento sanitário e fonte de água dos domicílios, para os **5.570 municípios
brasileiros**, em percentual. Extraído do Censo Demográfico 2022 (IBGE) via SIDRA.

Arquivo: [`censo_domiciliar_br.csv`](censo_domiciliar_br.csv) · 72.456.368 domicílios
particulares permanentes ocupados · gerado por
[`saneamento/censo_domiciliar.py`](../saneamento/censo_domiciliar.py)

## Por que este arquivo existe

O indicador usado por padrão em pesquisa municipal de saneamento no Brasil é a cobertura
de rede do SNIS/SINISA — quantos domicílios o **prestador** atende. Ele tem um defeito
que só aparece quando se olha para quem fica de fora: municípios sem rede coletora entram
todos como cobertura zero, como se fossem o mesmo caso.

Não são. No Paraná, entre os 157 municípios que o SINISA zera, a fração de domicílios com
destino inadequado de esgoto vai de **9,5% a 99,6%**. Um município onde todos têm fossa
séptica e um onde todos lançam em vala a céu aberto recebem a mesma nota. São 39% dos
municípios do estado com a exposição achatada num ponto só — e erro de medida na variável
independente atenua coeficiente na direção do zero.

O Censo mede outra coisa: o que o domicílio de fato tem. Isso dá uma variável de exposição
definida para todo município, inclusive os que não têm rede.

Onde há rede as duas medidas concordam (correlação 0,87 com o IES0001 do SINISA). O SINISA
não está errado sobre o que se propõe a medir; o problema é o que ele não vê.

## Colunas

### Identificação

| Coluna | Descrição |
|---|---|
| `cod_ibge` | código IBGE do município, 7 dígitos |
| `municipio` | nome do município |
| `uf` | sigla da unidade da federação |
| `domicilios` | domicílios particulares permanentes ocupados (denominador do esgoto) |

### Esgotamento sanitário — tabela SIDRA 6805

Percentual sobre `domicilios`.

| Coluna | Descrição |
|---|---|
| `esgoto_inadequado_pct` | fossa rudimentar, vala, corpo d'água, ou sem banheiro |
| `esgoto_adequado_pct` | rede, fossa ligada à rede, ou fossa séptica/filtro |
| `esgoto_rede_pct` | rede geral/pluvial ou fossa ligada à rede — o comparável ao SINISA |
| `fossa_septica_pct` | fossa séptica ou filtro **não** ligada à rede |
| `fossa_rudimentar_pct` | fossa rudimentar ou buraco |
| `sem_banheiro_pct` | domicílios sem banheiro nem sanitário |

`esgoto_adequado_pct + esgoto_inadequado_pct` não fecha exatamente 100: falta a categoria
residual "outra forma", que fica de fora por não ter conteúdo sanitário definido. A soma
fica em 99,7% na mediana e nunca passa de 100.

### Fonte de água — tabela SIDRA 6803

Percentual sobre o total de domicílios da tabela de água, que difere marginalmente do de
esgoto. Cada fonte soma as duas situações que o Censo separa: domicílio com ligação à rede
que usa principalmente outra coisa, e domicílio sem ligação nenhuma. O que importa para
exposição é a fonte principal, tenha ou não um cano parado na porta.

| Coluna | Descrição |
|---|---|
| `agua_rede_pct` | possui ligação à rede geral **e a usa** como forma principal |
| `agua_poco_profundo_pct` | poço profundo ou artesiano |
| `agua_poco_raso_pct` | poço raso, freático ou cacimba — vulnerável a fossa vizinha |
| `agua_nascente_pct` | fonte, nascente ou mina |
| `agua_carropipa_pct` | carro-pipa |
| `agua_chuva_pct` | água da chuva armazenada |
| `agua_superficial_pct` | rios, açudes, córregos, lagos e igarapés |
| `agua_sem_rede_pct` | não possui ligação com a rede geral, por qualquer fonte |

`agua_sem_rede_pct` é um recorte transversal aos demais, não uma categoria a somar.

## Como cruzar

`cod_ibge` tem 7 dígitos, com dígito verificador. **O DATASUS usa 6** (`MUNIC_RES` no
SIH/SUS, por exemplo) — junte pelos 6 primeiros:

```python
censo["cod6"] = censo["cod_ibge"].astype(str).str[:6]
```

## Limites

- **Censo 2022 é um ponto no tempo.** Aplicado a painéis longos, descreve melhor o fim da
  série que o começo.
- **"Adequado" segue a classificação do IBGE**, que julga o tipo de solução e não sua
  execução: fossa séptica mal dimensionada conta como adequada.
- **Domicílio não é pessoa.** Municípios com domicílios maiores ficam sub-representados na
  fração.
- **Fração municipal não é o cruzamento no domicílio.** Um município pode ter muita fossa
  rudimentar e muito poço raso sem que sejam as mesmas casas — combinar as duas colunas
  para inferir mecanismo é falácia ecológica em potencial.

## Reproduzir

```bash
SANEA_ESCOPO=br python saneamento/censo_domiciliar.py
```

São 54 requisições ao SIDRA (27 UFs × 2 tabelas), cacheadas em `dados/bruto/ibge/`. O
cache confere quais categorias foram pedidas na época, então acrescentar uma coluna ao
script rebaixa sozinho o que faltar.

Fonte: IBGE, Censo Demográfico 2022 — tabelas [6805](https://sidra.ibge.gov.br/tabela/6805)
(esgotamento sanitário) e [6803](https://sidra.ibge.gov.br/tabela/6803) (abastecimento de
água). Os dados de origem seguem a licença do IBGE; o código deste repositório é MIT.
