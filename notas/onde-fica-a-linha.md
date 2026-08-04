# Onde fica a linha entre saneamento adequado e inadequado?

**Nota metodológica** · SANEA · agosto de 2026

> Dois inquéritos domiciliares brasileiros sugerem que a fossa séptica **não ligada à rede**
> se comporta como solução inadequada, e não adequada — como a classifica o padrão em uso.
> Se isso se confirmar, estudos que cruzam saneamento com saúde no Brasil vêm medindo a
> exposição com a linha no lugar errado, o que atenua estimativas na direção do zero.
>
> A evidência aqui é sugestiva, não conclusiva: nasceu de uma tabela e o teste mais direto
> se apoia em 14 eventos. A nota existe para que outros a testem com dado melhor, não para
> encerrar o assunto.

## O problema

A classificação usada no Brasil — e no monitoramento internacional — separa destinos de
esgoto em adequados e inadequados assim:

| Adequado | Inadequado |
|---|---|
| Rede geral de esgoto ou pluvial | Fossa rudimentar |
| Fossa séptica **ligada** à rede | Vala |
| Fossa séptica **não ligada** à rede | Rio, lago, córrego ou mar |

Isso não é arbitrário nem brasileiro: o *Joint Monitoring Programme* da OMS/UNICEF trata
tanque séptico como saneamento melhorado, e o IBGE segue essa convenção. A classificação
serve bem ao propósito para o qual foi feita — comparação internacional e meta de política
pública.

A pergunta desta nota é outra: **essa linha, feita para monitoramento, serve como variável
de exposição em estudo epidemiológico?**

## O que os dados sugerem

### ENANI-2019 — onde a suspeita nasceu

O ENANI pergunta diretamente se a criança teve diarreia nos últimos 15 dias, a 14.558
crianças menores de 5 anos, com o saneamento do próprio domicílio na mesma entrevista.

| Destino do esgoto | Crianças | Diarreia em 15 dias |
|---|---|---|
| Rede geral | 10.005 | **14,9%** |
| Fossa séptica | 3.202 | 18,3% |
| Fossa rudimentar | 895 | 19,7% |
| Vala | 186 | **22,0%** |

A fossa séptica — classificada como adequada — está mais perto da fossa rudimentar (19,7%)
do que da rede geral (14,9%).

Trocando a linha da exposição, ajustando por idade, situação urbana/rural, região e faixa de
renda, com erro-padrão agrupado pela unidade primária de amostragem:

| Contraste | Razão de chances | IC95% | p |
|---|---|---|---|
| Inadequado × adequado (linha oficial) | 1,170 | 0,995–1,376 | 0,058 |
| **Sem ligação à rede × com ligação** | **1,180** | 1,040–1,339 | **0,010** |

**Este contraste nasceu de olhar a tabela.** É hipótese gerada pelos dados, não testada por
eles. Reportá-lo como achado confirmatório seria erro elementar.

### PNS 2019 — o teste que o ENANI não permite

A PNS separa a fossa séptica **ligada** à rede da **não ligada**. O ENANI junta as duas numa
categoria só. Essa separação é exatamente o que discrimina a hipótese: são duas soluções que
diferem apenas pela conexão, e que a classificação oficial trata como igualmente adequadas.

Em moradores de 0 a 9 anos, com desfecho de problema gastrointestinal:

| | Linha oficial | Linha por ligação |
|---|---|---|
| PNS | 1,029 | **1,179** |
| ENANI | 1,170 | **1,180** |

A troca de definição move a estimativa na mesma direção e quase na mesma magnitude em duas
pesquisas independentes, com desfechos diferentes e amostras diferentes.

E o teste direto:

> **fossa séptica não ligada × ligada à rede = 2,030 (IC95% 1,103–3,737, p = 0,023)**

## Onde esta evidência é frágil

Três coisas, e nenhuma delas está em nota de rodapé por escolha:

**O grupo de referência tem 14 eventos.** O intervalo de 1,10 a 3,74 mostra a instabilidade
sozinho. Qualquer estimativa apoiada nisso é provisória.

**Duas categorias contradizem o gradiente.** Na PNS, a fossa séptica ligada sai *melhor que
a própria rede geral* (0,512), o que é difícil de sustentar. E o corpo d'água — o pior
destino possível — dá 0,521 contra rede geral, com 5 eventos. Não refutam a hipótese, mas
também não sustentam dose-resposta.

**O desfecho da PNS é fraco.** "Problema gastrointestinal" mistura diarreia com gastrite e
só conta quem interrompeu atividades habituais. Isso atenua qualquer efeito.

## Por que importaria, se estiver certo

Erro de classificação **não diferencial** na exposição atenua estimativas na direção do
zero. Se fossa séptica não ligada carrega risco parecido com o de fossa rudimentar, colocá-la
do lado adequado mistura exposto com não exposto em ambos os braços da comparação.

O tamanho do problema não é pequeno. Pelo Censo 2022, a mediana municipal brasileira é de
**10,4% de domicílios com fossa séptica não ligada à rede**, e **1.058 municípios passam de
30%** — chegando a 99% no extremo. É população suficiente para diluir contraste.

Isso pode contribuir para um padrão conhecido: estudos ecológicos brasileiros que cruzam
cobertura de saneamento com desfecho de saúde produzem associações fracas ou nulas com
frequência incômoda, dado que o efeito do saneamento sobre doença diarreica é bem
estabelecido em ensaio comunitário e coorte.

**Esta nota não afirma que essa é a explicação** — apenas que é uma candidata testável que
não costuma ser testada.

## O que fazer na prática

**Reporte as duas linhas.** Um teste de sensibilidade que mostre a estimativa sob a
classificação oficial e sob a divisão por ligação à rede custa duas linhas de código e
informa o leitor sobre quanto a conclusão depende de uma convenção.

**Verifique se sua base preserva a distinção.** Nem todas preservam:

| Base | Separa fossa séptica ligada da não ligada? |
|---|---|
| Censo 2022 | sim |
| PNS 2013 e 2019 | sim |
| Censo 2010 | não |
| ENANI-2019 | não |

**Se usar dado municipal**, o arquivo
[`dados/censo_domiciliar_br.csv`](../dados/censo_domiciliar_br.csv) deste repositório traz as
duas linhas prontas para os 5.570 municípios: `esgoto_adequado_pct` segue a classificação
oficial, `esgoto_rede_pct` agrega apenas rede geral e fossa séptica ligada, e
`fossa_septica_pct` isola a não ligada. Ver o [dicionário](../dados/censo_domiciliar_br.md).

## Reproduzir

```bash
SANEA_ENANI=~/Downloads/ENANI_2019 python saude/enani_diarreia.py
SANEA_PNS=~/Downloads/PNS_2019     python saude/pns_domicilio.py
```

Microdados: [ENANI-2019](https://dadosabertos.saude.gov.br/dataset/estudo-nacional-de-alimentacao-e-nutricao-infantil-enani-2019)
(UFRJ/Ministério da Saúde) e [PNS 2019](https://ftp.ibge.gov.br/PNS/2019/Microdados/) (IBGE/MS).
Ambos públicos e anonimizados.

O código é MIT; os dados seguem as licenças de suas fontes. Correções e refutações são
bem-vindas — o objetivo desta nota é que alguém teste isso com dado melhor do que o que
temos aqui.
