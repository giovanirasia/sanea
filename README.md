# SANEA

Dados abertos de saneamento básico, saúde e clima no Brasil — cruzados por município.

> *Open data on sanitation, public health and climate in Brazil, joined at the municipal level.*

## O que é

O Brasil publica muita coisa sobre saneamento, muita coisa sobre saúde e muita coisa
sobre clima — em bases separadas, com chaves diferentes, sem ninguém cruzando. O SANEA
existe para juntar as três e responder perguntas simples que hoje exigem trabalho manual:

- onde falta água encanada e coleta de esgoto, e para quem
- como está a qualidade da água nos corpos hídricos perto dessas populações
- se as doenças ligadas à falta de saneamento acompanham essas lacunas
- como cheias e secas mexem nas três coisas acima

O recorte é sempre territorial. Um número nacional não ajuda ninguém; o que importa é
o município, e quando possível o ponto de coleta.

## Estado atual

**Análise, sem aplicação.** Não há app, API nem release — o que existe são scripts que
baixam as bases públicas, cruzam e testam hipóteses.

Três recortes, e a comparação entre eles é parte do método. Todo módulo aceita
`SANEA_ESCOPO`, e cada recorte novo nasceu de um limite do anterior:

| Recorte | Municípios | Por que existe |
|---|---|---|
| **Bacia Hidrográfica do Paraná 3** | 35 | piloto, com relação institucional na região |
| **Paraná** | 399 | o achado da bacia não replicou, e isso só apareceu ao escalar |
| **Maranhão** | 217 | no Paraná a doença letal infantil já foi resolvida; sem variância não há o que medir |

A Região Metropolitana de São Paulo foi um piloto anterior, com o programa Observando os
Rios.

## Dados publicados

Dois subprodutos da análise viraram os artefatos mais reaproveitáveis daqui, e valem
independentemente do que este repositório conclua sobre saúde. São as duas pontas do
cruzamento que o projeto se propõe a fazer, e casam pelo `cod_ibge`.

📄 **[`dados/censo_domiciliar_br.csv`](dados/censo_domiciliar_br.csv)** — esgotamento
sanitário e fonte de água dos domicílios, por município, Censo 2022. 5.570 municípios.
[Dicionário](dados/censo_domiciliar_br.md).

O indicador usado por padrão no país — cobertura de rede do SNIS/SINISA — mede a rede do
prestador, e por isso zera todo município sem rede coletora. No Paraná esse achatamento
atinge **39% dos municípios**, que na verdade vão de 9,5% a 99,6% de domicílios com
destino inadequado de esgoto. O detalhe está em
[O nulo é da hipótese ou da variável?](#o-nulo-é-da-hipótese-ou-da-variável).

📄 **[`dados/obitos_hidricas_br.csv`](dados/obitos_hidricas_br.csv)** — óbitos por doença
infecciosa intestinal (A00–A09), por município, ano e faixa etária, 2008–2024, do
SIM/DATASUS. [Dicionário](dados/obitos_hidricas_br.md).

O SIM é público mas não vem em forma de painel: são 459 arquivos DBC, um por UF e ano, e o
campo de idade não é um número — `310` é dez meses e `410` é dez anos. Cada linha traz
também os **óbitos totais** e os **óbitos por causa mal definida**, e isso não é enfeite:
a taxa de mortalidade por causa específica cai onde o registro é pior, não onde a doença é
menor. Quem usar a coluna do desfecho sozinha vai encontrar saneamento precário associado
a *menos* morte — foi o que quase aconteceu aqui, e está contado em
[Um sinal invertido que era da base, não do mundo](#um-sinal-invertido-que-era-da-base-não-do-mundo).

## Resultados

Tudo abaixo é reproduzível pelos scripts deste repositório. Os números foram revisados
mais de uma vez; onde um controle metodológico derrubou um achado, o histórico do Git
registra o antes e o depois.

### Saneamento e doença intestinal: a hipótese não se sustenta

Internações por doenças infecciosas intestinais (CID-10 A00–A09) de residentes na BP3,
2008–2026: **27.228 casos** em 1,58 milhão de internações.

Por estrato de saneamento, em incidência por 100 mil habitantes por ano:

| Estrato | Municípios | Cobertura de esgoto | Incidência |
|---|---|---|---|
| Sem rede coletora | 15 | 0% | 331,7 |
| Cobertura baixa | 10 | 49% em média | 236,3 |
| Cobertura alta | 10 | 84% em média | 71,1 |

A razão bruta entre extremos é 4,7×. **Esse número não deve ser citado como efeito do
saneamento.** Municípios sem rede também são menos densos, e ao controlar densidade,
renda e tendência, o contraste entre estratos cai para 2,1× e perde significância
(p = 0,10). Ruralidade explica boa parte do gradiente bruto.

Na bacia, o que sobrevivia ao ajuste era a dose-resposta contínua: 0,884 por 10 pontos
percentuais de cobertura (IC 0,803–0,973), p = 0,012 — cerca de 12% menos internação.

**Esse número não replicou em escala estadual, e a estimativa boa é a estadual.**
Repetindo a mesma análise nos 399 municípios do Paraná (7.543 observações, 255 mil casos,
com cobertura de água também controlada):

| | Bacia Paraná 3 (35 mun.) | Paraná (397 mun.) |
|---|---|---|
| Dose-resposta por 10 p.p. | 0,884 (p = 0,012) | **0,967 (p = 0,074)** |
| Sem rede vs cobertura alta, ajustado | 2,09× (p = 0,10) | **1,22× (p = 0,18)** |

O efeito cai de ~12% para ~3% e o intervalo passa a incluir 1 (0,933–1,003). Não é falta
de poder: com 11× mais municípios o intervalo ficou **mais estreito**, não mais largo.
A leitura honesta é que o resultado da bacia era superestimativa de amostra pequena.

E o desfecho, com o modelo completo — idade, densidade, renda, tendência e propensão geral
a internar:

> **cobertura de esgoto = 1,000 por 10 p.p. (IC95% 0,976–1,025, p = 0,98)**

Nenhuma associação. Não é efeito pequeno: é ausência, e o intervalo exclui qualquer efeito
maior que ~2,5% por 10 pontos percentuais de cobertura. **A hipótese de que a cobertura municipal de esgoto prediz internação
por doença de veiculação hídrica não se sustenta no Paraná.**

### O nulo é da hipótese ou da variável?

Um resultado nulo admite sempre duas objeções: faltou poder, ou a variável era ruim. A
primeira já estava respondida — ao escalar de 35 para 397 municípios o intervalo ficou
mais estreito. A segunda não, e havia razão concreta para levá-la a sério.

O SINISA mede a rede do prestador: quantos domicílios o operador atende. Os 157
municípios do Paraná sem rede coletora entram todos como cobertura zero, como se fossem
o mesmo caso. Pelo Censo 2022, não são. Entre esses 157, a fração de domicílios com
destino inadequado de esgoto — fossa rudimentar, vala, corpo d'água ou nenhum banheiro —
vai de **9,5% a 99,6%**, com desvio-padrão de 26 pontos. Um município onde todos têm
fossa séptica e um onde todos lançam em vala a céu aberto recebem a mesma nota.

Em 39% da amostra, portanto, a exposição estava achatada num ponto só. Isso é erro de
medida na variável independente, e erro de medida atenua coeficiente na direção do zero.

Onde há rede, as duas medidas concordam — correlação 0,87 entre o IES0001 e a cobertura
de rede do Censo. O SINISA não está errado sobre o que se propõe a medir; o problema é o
que ele não vê.

Trocar a variável, sozinho, não muda o resultado estadual: 1,025 (p = 0,24) contra 0,982
(p = 0,28). Mas dentro dos 155 municípios sem rede — subconjunto onde o SINISA é
constante e não pode produzir coeficiente nenhum — o Censo enxerga gradiente:

| Por 10 pontos percentuais | Razão | IC95% | p |
|---|---|---|---|
| Esgoto inadequado → internação | 1,114 | 1,046–1,186 | 0,0008 |
| Fossa séptica → internação | 0,914 | 0,845–0,988 | 0,023 |

E sobrevive às duas checagens que derrubaram achados anteriores aqui: controlando
propensão geral a internar dá 1,064 (p = 0,024), e com internações totais no offset,
1,091 (p = 0,0025).

Duas ressalvas seguram a leitura. A interação formal com "tem rede" dá p = 0,148, então
"o efeito existe só onde não há rede" é leitura de subgrupo, não resultado estabelecido.
E dentro do subgrupo o PIB per capita volta a sair invertido (1,466, p = 0,003) — o mesmo
sintoma de instabilidade já catalogado na bacia.

### A assinatura etária decide: não é veiculação hídrica

O gradiente acima tem duas explicações possíveis, e nenhum controle adicional as separa:

- **transmissão** — esgoto cru contamina água e alimento, e as pessoas adoecem
- **artefato** — municípios com muita fossa rudimentar são os mais rurais e pobres, e o
  que se mede é ruralidade

O que distingue as duas não é mais controle, é **em quem** o efeito aparece. Doença de
veiculação hídrica interna criança pequena muito acima de adulto. Ruralidade, pobreza e
distância do hospital não escolhem idade.

Rodando três faixas, com **20 a 59 anos como controle negativo**, dentro dos sem-rede:

| Faixa | Razão por 10 p.p. | IC95% | p |
|---|---|---|---|
| 0 a 4 anos | 1,074 | 1,023–1,127 | 0,004 |
| **20 a 59 anos** — controle negativo | **1,119** | 1,028–1,219 | 0,010 |
| 60 anos ou mais | 1,114 | 1,053–1,179 | 0,0002 |

Adulto em idade de trabalhar responde *mais* que criança pequena. No estado inteiro fica
ainda mais nítido: em menores de 5 anos o efeito desaparece (1,032, p = 0,11), enquanto
em adultos (1,080, p = 0,006) e idosos (1,085, p = 0,0001) permanece. A fossa séptica
repete o padrão errado — protege idoso (0,924, p = 0,015) e não criança (0,953, p = 0,10).

> O gradiente é real, mas não é saneamento. É característica de município que eleva
> internação em qualquer idade.

Isso reforça o nulo em vez de contradizê-lo, e com argumento melhor: não é só que a
associação some sob controle — é que, quando ela aparece, tem a assinatura etária errada.

O teste exigiu rebaixar o SIH inteiro. `IDADE` só é interpretável junto com `COD_IDADE`:
em 2019, **899 dos 10.197 casos** de A00–A09 vinham gravados em meses ou dias, de modo
que um lactente de 8 meses era indistinguível de uma criança de 8 anos — exatamente o
grupo da pergunta.

### Por que o Paraná é o lugar errado para testar isso

Em 19 anos, o Paraná inteiro registrou **58 óbitos por A00–A09 em menores de 5 anos**.
Poucos demais para modelar, e esse é justamente o ponto: doença hídrica letal infantil já
foi resolvida aqui.

Não se mede variação no que não varia mais. O nulo do Paraná é um resultado sobre o Paraná
— estado com 79,8% de cobertura de água tratada mesmo nos municípios sem esgoto — e não se
transfere para onde as duas coberturas são baixas ao mesmo tempo. A interação esgoto ×
poço raso, que testaria o mecanismo de contaminação diretamente, não tinha amplitude ali:
a mediana de domicílios com poço raso no Paraná é de 1%.

### Maranhão: o caso mais favorável possível

Então a pergunta foi levada para onde ela ainda vive. O Maranhão tem a pior cobertura de
saneamento do país e mortalidade infantil por diarreia ainda existente:

| | Paraná | Maranhão |
|---|---|---|
| Esgotamento inadequado, mediana | 43,4% | **79,9%** |
| Domicílios com poço raso, mediana | 1,0% | **8,1%** (até 61,5%) |
| Óbitos por A00–A09 em menores de 5 | 58 (hospitalares, 19 anos) | **982** (17 anos) |

E o desfecho mudou junto: **óbito, do SIM, não internação**. `MORTE` no SIH só enxerga
quem morreu internado, e quem morre de diarreia em município sem leito ou sem estrada
morre sem internar — o sub-registro seria maior exatamente onde a exposição é maior, o que
puxa a associação para zero. Usar SIH ali seria construir o nulo. O SIM registra a partir
da declaração de óbito.

Com desfecho duro, exposição ampla e a doença ainda matando:

> **esgoto inadequado → óbito em menor de 5 anos = 1,005 (IC95% 0,958–1,055, p = 0,84)**

Nulo. A interação com poço raso, agora com amplitude de verdade, dá 0,980 (p = 0,33).
Água de rede não protege menor de 5 (0,997, p = 0,90).

### Um sinal invertido que era da base, não do mundo

Nas faixas adultas o coeficiente saiu **protetor** (0,918 em 20–59, p = 0,013) e a fossa
séptica saiu como **fator de risco** (1,089, p = 0,014) — o inverso da hipótese nas duas
pontas ao mesmo tempo. Isso quase nunca é efeito.

Duas explicações foram testadas. Causa mal definida existe mas é fraca (correlação 0,18
com a exposição; mediana de 2,9% para 4,0% entre quartis extremos). A que explica é outra:
**a mortalidade por todas as causas em menores de 5 também cai com a exposição**
(Spearman −0,16). Não é crível que se morra menos, de qualquer causa, nos municípios mais
pobres e rurais do Maranhão — o que cai é o registro. E como o viés atinge numerador e
denominador juntos, controlar mortalidade geral não corrige.

Isso gerou uma previsão falseável: se o sinal protetor fosse artefato do SIM, deveria
sumir num desfecho apurado por outro sistema. A AIH existe porque o hospital precisa ser
pago; a declaração de óbito depende de cartório.

| Faixa | SIM (óbito) | SIH (internação) |
|---|---|---|
| 20–59 | 0,918 (p = 0,013) | 1,069 (p = 0,17) |
| 60+ | 0,943 (p = 0,028) | 1,076 (p = 0,047) |

Sumiu. E o descritivo fecha o argumento: internação por todas as causas em menores de 5
**não varia** com a exposição (Spearman −0,018), enquanto a mortalidade por todas as
causas caía. A lacuna estava na apuração do óbito, não na exposição.

Sobre a hipótese, porém, a internação no Maranhão repete o Paraná: 1,060 em menores de 5,
1,069 em adultos de 20 a 59, 1,076 em idosos. As três são a mesma estimativa — que uma
alcance significância e outra não é diferença de precisão, não de magnitude, e lê-la como
assinatura etária seria confundir p-valor com tamanho de efeito.

> Uma armadilha documentada em [`saude/internacao.py`](saude/internacao.py): na primeira
> especificação, poço raso saiu 1,814 por 10 p.p. — o que daria fator 36 ao longo da
> amplitude observada. Num modelo com termo de produto, o efeito principal vale onde o
> outro termo é zero, e esgoto inadequado zero não existe no painel (o mínimo é 9%).
> Centrado na média: 1,030 (p = 0,48). Sozinho: 0,998 (p = 0,97).

### Três nulos, uma explicação

Cuidado com a leitura fácil. **Isto não é "saneamento não afeta saúde"** — o efeito do
saneamento sobre doença diarreica é das relações mais bem estabelecidas da saúde pública,
medida em ensaio comunitário e em coorte.

O que este repositório mostra é outra coisa, três vezes no mesmo sentido:

- na **RMSP**, a cobertura municipal não explicou o IQA do ponto de coleta
- no **Paraná**, não explicou internação
- no **Maranhão**, não explica óbito infantil — no caso mais favorável que existe

Quando o mesmo desenho falha em três contextos tão diferentes, a hipótese mais econômica
não é que o mundo mudou: é que **a unidade de análise está errada**. A média municipal
dilui uma exposição que é domiciliar, e o município é grande demais para que a fração
exposta e a fração adoecida sejam as mesmas pessoas. É falácia ecológica operando a favor
do nulo.

Isso é o que justifica pedir dado no nível do ponto e do domicílio, em vez de mais uma
volta no agregado municipal.

> **Esta explicação foi testada depois, e ganhou uma concorrente.** Com a PNS 2019, que mede
> exposição e desfecho na mesma casa, o resultado continua nulo — ver
> [O teste da própria explicação](#o-teste-da-própria-explicação-descer-ao-domicílio).
> E com o ENANI-2019, que mede diarreia de verdade, aparece sinal — mas por um motivo
> diferente: a linha entre saneamento adequado e inadequado parece estar no lugar errado,
> e todas as análises municipais daqui a usaram. Ver
> [A segunda explicação](#a-segunda-explicação-a-linha-da-exposição-está-no-lugar-errado).

### Atacar o confundimento pela raiz: primeiras diferenças

Há uma segunda saída, que não exige dado novo. Todos os confundidores que estragaram as
estimativas acima — ruralidade, acesso a leito, qualidade de registro, limiar de internação
— têm uma propriedade que até então não tinha sido usada: **são praticamente fixos no
tempo.** Comparar o município com ele mesmo, antes e depois da rede chegar, elimina todos
de uma vez, sem precisar medi-los.

Isso exige exposição que varie no tempo, e a verificação de comparabilidade
([`saneamento/comparabilidade_censo.py`](saneamento/comparabilidade_censo.py)) produziu um
resultado incômodo: **a medida boa não é comparável, e a comparável é a medida ruim.**

| Mudança 2010→2022 | Média | Desvio-padrão | Amplitude |
|---|---|---|---|
| Rede (exige obra física) | +3,4 p.p. | 5,6 | −3,8 a +27,4 |
| Fossa séptica (autodeclarada) | +8,8 p.p. | **23,3** | **−51,2 a +73,3** |

*(Maranhão; no país o contraste é o mesmo mas menos nítido.)* Fossa séptica não cai 51
pontos em 12 anos — o questionário de 2022 redividiu a categoria. É reclassificação, e
diferenciar uma variável mal classificada dobra o erro dela. Sobra a cobertura de rede,
justamente a variável do tipo SINISA. Mas como **mudança** ela é legítima: a rede chegou ou
não chegou. A pergunta deixa de ser "quem está exposto adoece mais?" e passa a ser **"ligar
domicílios à rede reduz morte infantil?"** — que é a pergunta que governo responde com
orçamento.

O desenho usa óbitos infantis por todas as causas como denominador, não população. Isso
cancela o sub-registro diagnosticado no Maranhão, que atinge numerador e denominador
juntos. Resultado, por 10 p.p. de expansão:

| | Razão | IC95% | p |
|---|---|---|---|
| Menores de 5 anos | 1,022 | 0,963–1,084 | 0,48 |
| 20 a 59 *(controle negativo)* | 1,021 | 0,963–1,082 | 0,49 |
| Expansão > 20 p.p. (binário) | 1,093 | 0,894–1,337 | 0,39 |

**Este nulo não é um quarto na lista acima, e a diferença importa.** Nos outros havia como
mostrar que o desenho enxergaria um efeito se houvesse. Aqui não: o **controle positivo
também deu nulo** — a variação de rede não prediz nem a mudança na fração de causas mal
definidas, que é marcador de desenvolvimento do serviço de saúde. Some-se o intervalo largo
do tratamento binário e o denominador conservador por construção. É um desenho que rodou e
não achou, não uma demonstração de ausência.

### O placebo reprova o desenho

A premissa das primeiras diferenças é que, sem tratamento, tratados e não tratados teriam
seguido juntos. Isso é testável: basta aplicar o mesmo estimador a duas janelas **anteriores
ao tratamento**, onde ele não pode ter efeito.

A ideia original era usar a série anual do SNIS para isso. Não foi necessária — o SNIS
daria o *momento* da expansão, mas o teste precisa do *desfecho antes* dela, e o SIM começa
em **1996**, catorze anos antes da janela de tratamento.

| Janela | Coeficiente | IC95% | p |
|---|---|---|---|
| **1998–2002 → 2006–2010** *(placebo: tudo antes)* | **0,960** | 0,922–1,000 | **0,048** |
| 2006–2010 → 2020–2024 *(o tratamento)* | 1,015 | 0,958–1,076 | 0,61 |

O coeficiente que tinha de ser 1 não é. **Municípios que depois expandiriam a rede já
vinham reduzindo mais rápido a fração de óbitos infantis por doença intestinal, dez anos
antes da obra.** Tendências paralelas não valem, e a estimativa acima não é causal.

A falha é marginal — o intervalo encosta em 1. Mas um placebo que cai bem na borda não se
descarta, ainda mais quando a função dele é tranquilizar.

**Não é artefato de certificação.** A fração de causa mal definida caiu de 12,7% (1996–2007)
para 5,7% (2008–2024), e melhora diferencial dela produziria exatamente esse falso sinal —
mas ela não se move com o tratamento (1,025, p = 0,34) na mesma janela do placebo.

Um aspecto tranquiliza: o viés aponta para **achar** efeito protetor, já que os tratados
melhoravam sozinhos, e ainda assim não se achou nada. O nulo não esconde efeito; se algo, é
conservador. Mas isso é leitura da direção do viés, não estimativa válida.

E a tendência prévia é substantivamente coerente com o resto: a expansão foi para
municípios já em trajetória melhor — o mesmo fenômeno que a tabela abaixo mostra por outro
ângulo.

### O achado mais firme desta parte não é causal

| Quartil de cobertura em 2010 | Cobertura | Expansão média 2010→2022 |
|---|---|---|
| Q1 — sem rede | 0,4% | **+4,7 p.p.** |
| Q2 | 3,9% | +10,1 p.p. |
| Q3 | 34,8% | **+12,9 p.p.** |
| Q4 — já tinha | 77,1% | +5,4 p.p. |

**A expansão de rede no Brasil passou ao largo de quem não tinha nada.** Quem começou do
zero ganhou um terço do que ganhou quem já tinha um terço de cobertura. O investimento foi
estender rede existente, não começar do zero — o que é caro e difícil, e explica o padrão
sem supor má-fé. Isso independe de qualquer estimativa causal.

Como pano de fundo: no período, os óbitos infantis por A00–A09 caíram **55%** no país
(5.243 em 2008–2012 para 2.383 em 2020–2024), enquanto os de adultos subiram. Queda grande
e razoavelmente uniforme é o padrão de causas nacionais e simultâneas — rotavírus desde
2006, reidratação oral, transferência de renda, tratamento de água. Um efeito municipal de
esgoto teria de aparecer por cima disso.

### O teste da própria explicação: descer ao domicílio

Todo nulo acima admitia a mesma resposta — *"pode ser a unidade de análise"* — e este
repositório não só a admitia como a defendia. Mas explicação preferida também se testa.

A **PNS 2019** (IBGE/MS) mede exposição e desfecho **na mesma casa**: 273.393 moradores com
o destino do esgoto do próprio domicílio informado. E a classificação é idêntica à do
Censo, categoria por categoria, porque as duas usam o padrão do IBGE — a comparação com os
resultados municipais é direta, não analógica.

| Faixa | Razão de chances | IC95% | p |
|---|---|---|---|
| 0 a 9 anos | 1,029 | 0,761–1,391 | 0,85 |
| 20 a 59 *(controle negativo)* | 1,044 | 0,882–1,235 | 0,62 |
| 60 anos ou mais | 1,149 | 0,852–1,550 | 0,36 |

O descritivo dispensa modelo. Entre crianças de 0 a 9 anos, por destino do esgoto do
domicílio onde moram:

| Destino | Moradores | Problema gastrointestinal |
|---|---|---|
| Rede geral | 13.506 | **1,20%** |
| Fossa séptica | 8.261 | 1,28% |
| Fossa rudimentar | 9.549 | **1,19%** |
| Vala | 1.432 | 1,47% |

**Casa ligada à rede e casa com fossa rudimentar têm a mesma taxa.**

### O que esse resultado pode e não pode sustentar

**Não pode** encerrar a questão, e o motivo é o desfecho. Não existe variável de diarreia na
PNS — nem em 2019 nem em 2013; o módulo de crianças é sobre aleitamento, testes neonatais e
vacinação. O que há é *"problemas gastrointestinais (diarreia / vômito / náusea / gastrite /
dor de barriga)"* como motivo principal de ter interrompido atividades habituais nas duas
últimas semanas. Composto, com limiar de gravidade e recordatório curto — tudo atenuando
para zero. Um efeito verdadeiro de 1,5 sobre diarreia apareceria aqui como ~1,2, dentro do
intervalo observado.

**Pode** sustentar duas coisas. A primeira é a **uniformidade entre idades**, que não é
questão de poder: é a mesma assinatura errada encontrada no Paraná, no Maranhão e nas
primeiras diferenças, agora num desenho onde a falácia ecológica não se aplica. A segunda é
mais desconfortável para este repositório — **a explicação que ele vinha defendendo não se
confirmou.** Remover o agregado municipal não fez efeito nenhum aparecer.

Isso não refuta a explicação (o desfecho é fraco demais para refutar seja o que for), mas
retira dela o status de resposta pronta.

E há indício de que o viés de relato alcança até aqui: "rio, lago, córrego ou mar", o pior
destino possível, tem a menor taxa da tabela (0,60%). São 830 moradores, então pode ser
ruído — mas é o mesmo padrão que o SIM do Maranhão mostrou, de quem tem menos acesso
relatar menos.

> Uma versão anterior deste README concluía aqui que *"nenhum dado observacional brasileiro
> de acesso público consegue ver o efeito"*. **Isso estava errado**, e a seção seguinte
> mostra por quê: faltava uma base que medisse diarreia como diarreia.

### O ENANI: medir diarreia como diarreia

Cinco análises nunca mediram o desfecho certo. Mediram internação (que depende de haver
leito), óbito (que depende de cartório) e "problema gastrointestinal" da PNS (composto com
gastrite, e só quando grave o bastante para interromper atividades). O gargalo sempre foi o
desfecho, não o desenho.

O **ENANI-2019** (UFRJ/Ministério da Saúde) pergunta direto: *"a criança está ou esteve com
diarreia nos últimos 15 dias?"* — a 14.558 crianças menores de 5 anos, com o saneamento do
próprio domicílio na mesma entrevista. São **2.343 casos**, prevalência de 16,1%.

Pela primeira vez em seis análises, o descritivo tem gradiente monotônico:

| Destino do esgoto do domicílio | Crianças | Diarreia |
|---|---|---|
| Rede geral | 10.005 | **14,9%** |
| Fossa séptica | 3.202 | 18,3% |
| Fossa rudimentar | 895 | 19,7% |
| Vala | 186 | **22,0%** |

Teste pré-especificado, adequado × inadequado na classificação do IBGE:
**1,170 (IC95% 0,995–1,376, p = 0,058)**. Positivo, direção certa, encostando.

### A segunda explicação: a linha da exposição está no lugar errado

Repare onde cai a fossa séptica: **18,3%, mais perto de fossa rudimentar (19,7%) que de
rede geral (14,9%)** — embora o IBGE a classifique como adequada, e embora *todas* as
análises municipais deste repositório a tenham posto do lado adequado.

Testando o contraste que a tabela sugere:

| Contra rede geral | Razão de chances | IC95% | p |
|---|---|---|---|
| **Sem ligação à rede** (fossa séptica inclusa) | **1,180** | 1,040–1,339 | **0,010** |
| Fossa séptica | 1,155 | 1,002–1,332 | 0,047 |
| Fossa rudimentar | 1,218 | 0,997–1,488 | 0,054 |
| Vala | 1,472 | 1,037–2,089 | 0,031 |

> **Este resultado nasceu de olhar a tabela, não de hipótese prévia.** Não é confirmatório:
> é hipótese gerada aqui, que precisa de outro dado para ser testada. Registrar isso importa
> mais que o p-valor.

Se a divisão certa for "tem rede ou não tem", então todas as análises municipais mediram a
exposição com a linha errada, juntando fossa séptica — de risco elevado — com rede geral, de
risco baixo. **Erro de classificação não diferencial atenua na direção do zero.**

Isso não transforma nenhum nulo anterior em erro: eles medem o que mediram, com a variável
que existia. O que muda é a explicação. Não era só a unidade de análise — era também a
definição da exposição, e as duas empurravam para o mesmo lado.

### O mecanismo não é o copo d'água

Fonte de água fora da rede geral: 0,953 (p = 0,63), nulo. E o efeito do esgoto é
praticamente igual entre quem **filtra ou ferve** a água da criança (1,105) e quem não trata
(1,159). Se a transmissão fosse pela água ingerida, tratar a água deveria reduzir o efeito.

Aponta para contato e ambiente — criança engatinhando e brincando em solo contaminado — e é
coerente com o sinal aparecer em **2 a 4 anos** (1,239) e não em menores de 2 (1,080), que
são mais amamentados e menos móveis. Os intervalos se sobrepõem demais para afirmar a
diferença etária, mas a direção é a esperada.

**E o tamanho é modesto.** Razão de chances de 1,18 é pequena perto do que ensaios
comunitários reportam, e pode conter confundimento residual: domicílio com rede difere em
escolaridade, aglomeração e higiene, e só parte disso está controlada.

### O que prediz, então

Duas coisas, ambas robustas e nenhuma delas ambiental.

**Composição etária.** Cada ponto percentual a mais de crianças menores de 5 anos
associa-se a ~39% mais internação por A00–A09 (1,391, p = 0,0004); cada ponto a mais de
população com 60 anos ou mais, a ~9% (1,088, p = 0,0007). Diarreia interna os extremos da
vida, e a distribuição etária do município importa mais que sua infraestrutura.

**Densidade demográfica** sobrevive a tudo — 0,904 (p = 0,009) no modelo completo, 0,717
antes dos controles. Municípios menos densos internam mais. Ela entrou como controle de
ruralidade, não como hipótese, e foi investigada em [`saude/densidade.py`](saude/densidade.py):

- **não é acesso ao serviço** — se fosse, o rural teria *menos* internação registrada, e a
  direção é a oposta, o que sugere que a carga real lá é ainda maior que a medida
- **é em parte idade** — com % 0–4 e % 60+ no modelo, o coeficiente vai de 0,717 para 0,809
- **é em parte limiar de internação** — densidade prediz internação por *qualquer* causa
  (0,945, p < 0,0001); sem atenção básica por perto, uma diarreia que na cidade seria
  resolvida na UBS vira internação no interior
- **não é saneamento domiciliar.** Este era o candidato mais forte — poço e nascente não
  entram no IAG0001, e solução individual mal executada não entra no IES0001. O Censo
  2022 trouxe as duas coisas, e o coeficiente da densidade não se move: 0,809 com a
  cobertura do SINISA, 0,809 com o esgotamento inadequado do Censo no lugar dela
- **sobra um resto sem explicação**, agora menor e mais cercado. Candidato ainda em pé:
  distância até atenção básica, que nenhuma das bases usadas aqui mede

Na bacia o modelo também mostrava PIB per capita associado a *mais* internação (2,03,
p = 0,018), o que era contraintuitivo e foi investigado: colinearidade descartada
(VIF 1,3–1,5), intensidade pecuária descartada (a bacia tem 111 milhões de galináceos e
3,4 milhões de suínos para 1,3 milhão de habitantes, e ainda assim suínos/km² dá p = 0,54),
e o coeficiente perdia significância ao controlar a propensão geral a internar. A conclusão
foi não interpretá-lo.

A escala estadual confirmou: no Paraná o mesmo coeficiente é **0,755** (p = 0,028) — mais
renda, menos internação, direção esperada. O sinal invertido da bacia era instabilidade de
amostra pequena, como suspeitado.

### El Niño e chuva na bacia

Em El Niño forte ou muito forte, a BP3 recebe **+42,5 mm/mês acima de meses neutros**
(Mann-Whitney, p = 0,0001), comparando apenas meses do mesmo período do calendário — as
classes intensas do ONI só ocorrem entre setembro e fevereiro. O efeito escala com a
intensidade do evento, o que é o padrão esperado de um sinal físico:

| Fase | Meses | Anomalia mediana |
|---|---|---|
| El Niño muito forte | 17 | +47,1 mm |
| El Niño forte | 35 | +17,0 mm |
| El Niño moderado | 55 | +4,9 mm |
| Neutro | 418 | −18,9 mm |

La Niña forte não é distinguível de neutro (p = 0,17, n = 25).

### Chuva e doença: sem associação detectável

Cruzando os dois lados, **não há efeito detectável da chuva sobre internação por A00–A09**
na bacia — nem no agregado, nem estratificado por saneamento, nem nos 15 municípios sem
rede nenhuma. Foram testadas quatro exposições (anomalia mensal, dias com ≥20 mm, dias com
≥50 mm, máximo diário) em defasagem de 0, 1 e 2 meses, controlando tendência, sazonalidade,
temperatura e volume hospitalar.

Os intervalos são estreitos o bastante para serem informativos: efeitos acima de ~4% por
100 mm estão excluídos. Não é "não sabemos"; é "se existe, é pequeno".

A leitura provável é que a falta de saneamento produz exposição **crônica**, não sazonal —
e que a cobertura alta de água tratada (79,8% mesmo nos municípios sem esgoto) rompe o
caminho chuva → contaminação. Isso é hipótese, não resultado.

### Limites que valem para tudo acima

- internação não é incidência: só entra quem foi hospitalizado pelo SUS
- o SINISA é de 2024 e o painel começa em 2008; a cobertura mudou no período
- "sem rede" é inferido da ausência do município no módulo de esgoto do SINISA. Não é dado
  faltante: esses municípios aparecem normalmente no módulo de água. São 15 dos 35 na
  bacia e **157 dos 399 no estado** — 39% do Paraná sem rede coletora
- a estrutura etária e o saneamento domiciliar vêm do Censo 2022, um ponto no tempo
  aplicado a um painel de 19 anos; descrevem melhor o fim da série que o começo
- "adequado" segue a classificação do IBGE, que julga o tipo de solução e não sua
  execução: fossa séptica mal dimensionada conta como adequada
- a interação esgoto × poço raso usa frações municipais, não o cruzamento no domicílio.
  Um município pode ter muita fossa rudimentar e muito poço raso sem que sejam as mesmas
  casas — é falácia ecológica em potencial, e por isso aquele resultado é indício
- os denominadores por faixa etária aplicam a estrutura de 2022 a todos os anos
- o SIM tem sub-registro próprio, historicamente maior no Norte e Nordeste e caindo ao
  longo da série; parte da tendência temporal é melhora de cobertura, não queda de
  mortalidade. No Maranhão isso foi diagnosticado, não apenas listado
- causa básica mal definida (capítulo R do CID-10) absorve óbitos que deveriam estar em
  A00–A09, e essa má definição também é maior onde há menos assistência
- primeira diferença remove confundimento de **nível** fixo no tempo, não tendência
  diferencial — e aqui a tendência diferencial existe: o placebo reprovou (p = 0,048)
- o que ainda falta, e para isso o SNIS seria necessário, é saber **quando** cada município
  expandiu. Isso permitiria um estudo de evento, vendo o desfecho ano a ano em torno da
  obra, em vez de dois blocos
- até 2005 o SIM grava o código de município com 7 dígitos e de 2006 em diante com 6;
  quem for reprocessar a série longa precisa uniformizar, ou anos inteiros somem no join
- o desfecho da PNS é morbidade autorrelatada, composta e condicionada a ter interrompido
  atividades: atenua qualquer efeito na direção do zero
- o contraste "com rede × sem rede" do ENANI é hipótese **gerada** olhando a tabela, não
  testada: precisa de outro dado para valer como achado
- o ENANI amostrou 123 municípios, não os 5.570 — representa o país, mas não permite
  recorte municipal
- a estimativa da PNS é não ponderada, com erro-padrão agrupado pela unidade primária de
  amostragem. O `statsmodels` não dá variância confiável junto com peso de frequência;
  fazer certo exigiria pacote de amostragem complexa, e os determinantes do peso entram
  como covariáveis no lugar
- controlar a propensão geral a internar é diagnóstico, não especificação final: é um
  desfecho, não covariável exógena, e ajustá-la pode ser sobreajuste
- ERA5 é reanálise, não pluviômetro; validar contra ANA/INMET antes de publicar número
- associação não é causa; não há aleatorização de saneamento

## Fontes de dados

| Fonte | O que traz | Acesso |
|---|---|---|
| ANA — HidroWebService | estações telemétricas, séries de qualidade da água | credenciado, por e-mail a `hidro@ana.gov.br` |
| SINISA 2024 | água e esgoto por município (Ministério das Cidades) | planilhas públicas |
| SNIS | série histórica de saneamento | público, também via Base dos Dados |
| IBGE — Censo 2022 (SIDRA) | saneamento e fonte de água do domicílio, estrutura etária | público |
| DATASUS — SIH/SUS | internações por agravo de veiculação hídrica | público |
| DATASUS — SIM | óbitos por causa básica, independentes de internação | público |
| IBGE/MS — PNS 2019 | saneamento e saúde no mesmo domicílio (microdados) | público |
| UFRJ/MS — ENANI 2019 | diarreia infantil e saneamento no mesmo domicílio | público |
| Observando os Rios | qualidade da água por voluntários (SOS Mata Atlântica) | público |
| CEMADEN / INMET | chuva, alertas de desastre | público |
| NOAA CPC — ONI | índice El Niño / La Niña, série desde 1950 | público |

## Camada climática

Está em curso um El Niño forte, com pico previsto para outubro–dezembro de 2026
(NOAA/CPC, julho de 2026: 81% de chance de evento *very strong*; IRI: 23 de 26 modelos
com Niño 3.4 ≥ +2,0 °C no pico).

A camada é **retrospectiva por decisão de projeto**. O objetivo não é prever o que vai
acontecer num município — teleconexão é probabilística, e afirmar impacto local a partir
de índice global seria sobrepassar o dado. O objetivo é medir o que já aconteceu ali nos
eventos anteriores, usando a série ONI desde 1950 para classificá-los.

O que essa decisão produziu está em [Resultados](#resultados): o sinal do El Niño sobre a
chuva da bacia existe e escala com a intensidade do evento; o sinal sobre internação não
aparece. Foi a camada climática que permitiu afirmar as duas coisas com o mesmo rigor —
inclusive a segunda, que é um resultado negativo.

## Estrutura

```
escopo.py    qual recorte territorial está ativo (SANEA_ESCOPO)
ana/         cliente da API da ANA e cruzamentos (piloto RMSP)
clima/       bacia, série ONI, chuva e extremos por município
saude/       internações do SIH, óbitos do SIM, e os modelos
saneamento/  indicadores do SINISA e o saneamento domiciliar do Censo
dados_ibge/  população, PIB, área, estrutura etária e rebanho
dados/       saídas derivadas, versionadas (os dumps brutos não são)
```

Os dumps brutos ficam em `dados/bruto/`, fora do versionamento: são grandes e
reprodutíveis a partir dos scripts. O do SIH baixa cerca de 1 GB do FTP e guarda 446 MB
já filtrados no recorte estadual — 42 MB no da bacia.

## Como rodar

Dependências: `pandas`, `numpy`, `scipy`, `statsmodels`, `openpyxl`, `datasus-dbc`,
`dbfread`.

A ordem importa, porque os módulos reaproveitam o cache uns dos outros:

```bash
python clima/bp3.py            # municípios da bacia, códigos IBGE e centroides
python clima/oni.py            # série ONI e episódios ENSO
python clima/chuva_bp3.py      # chuva mensal e anomalia (baixa o diário do ERA5)
python clima/extremos_bp3.py   # extremos e temperatura (reusa o cache acima)
python dados_ibge/populacao_bp3.py
python dados_ibge/contexto_bp3.py
python saude/sih_bp3.py        # ~1,2 GB do FTP do DATASUS; resumível
python dados_ibge/rebanho_bp3.py    # opcional: efetivo de suínos e aves
python dados_ibge/estrutura_etaria.py  # % 0-4 e % 60+ do Censo 2022
python saneamento/sinisa_bp3.py   # exige as planilhas do SINISA em disco
python saneamento/censo_domiciliar.py  # esgoto e água do domicílio, Censo 2022
# ...ou SANEA_ESCOPO=br, que gera o arquivo nacional dos 5.570 municípios
python saneamento/comparabilidade_censo.py  # o que dá para comparar entre censos
python saude/chuva_x_diarreia.py  # chuva x doença, bacia agregada
python saude/estratificado.py     # o mesmo, por estrato de saneamento
python saude/gradiente_ajustado.py  # o gradiente com renda e ruralidade controladas
python saude/densidade.py         # o que a densidade demográfica está medindo
python saude/exposicao_censo.py   # o nulo é da hipótese ou da variável?
python saude/menores5.py          # controle negativo por idade
```

O desenho de primeiras diferenças é nacional e depende só dos dois arquivos publicados
mais o Censo 2010, então roda sem escopo:

```bash
python saude/primeiras_diferencas.py
```

O teste de tendência prévia precisa da extensão retroativa do SIM, que grava em arquivo
próprio para não tocar no painel publicado:

```bash
SANEA_ESCOPO=br SANEA_ANO_INICIO=1996 SANEA_ANO_FIM=2007 python saude/sim.py
```

```bash
python saude/tendencia_previa.py
```

A análise no domicílio usa os microdados da PNS 2019, que são grandes (455 MB) e não entram
no repositório. Baixe de
[ftp.ibge.gov.br/PNS/2019/Microdados/Dados](https://ftp.ibge.gov.br/PNS/2019/Microdados/Dados/)
e aponte `SANEA_PNS` para a pasta:

```bash
SANEA_PNS=~/Downloads/PNS_2019 python saude/pns_domicilio.py
```

E a análise com diarreia medida como diarreia usa os microdados do ENANI-2019
([`bancos_Enani.csv.zip`](https://dadosabertos.saude.gov.br/dataset/estudo-nacional-de-alimentacao-e-nutricao-infantil-enani-2019)):

```bash
SANEA_ENANI=~/Downloads/ENANI_2019 python saude/enani_diarreia.py
```

O `sih_bp3.py` baixa 221 meses do FTP do DATASUS em processos paralelos (`SANEA_PARALELO`,
padrão 6) e cacheia cada mês já filtrado. O cache se rebaixa sozinho quando lhe falta uma
coluna que a versão atual do script pede, então trocar `COLUNAS` basta para forçar a
reextração — não é preciso apagar nada.

Para trocar de recorte, prefixe com `SANEA_ESCOPO`. Os escopos gravam em arquivos
separados e convivem lado a lado:

```bash
SANEA_ESCOPO=parana python saude/gradiente_ajustado.py
```

O recorte do Maranhão usa desfecho de mortalidade e não depende do SINISA:

```bash
export SANEA_ESCOPO=maranhao
python clima/bp3.py                    # apesar do nome, monta a lista de qualquer UF
python dados_ibge/populacao_bp3.py
python dados_ibge/contexto_bp3.py
python dados_ibge/estrutura_etaria.py
python saneamento/censo_domiciliar.py
python saude/sim.py                    # óbitos, 17 anos do FTP
# ...ou SANEA_ESCOPO=br, que gera o painel nacional de óbitos (459 arquivos)
python saude/mortalidade.py            # o teste principal
python saude/sih_bp3.py                # internação, para comparar as duas bases
python saude/internacao.py
```

Só dois passos precisam de coisa externa. O `sinisa_bp3.py` lê as planilhas do
Ministério das Cidades, que não são versionadas por tamanho — ajuste `RAIZ_SINISA` para
onde estiverem. E o cliente da ANA precisa de credencial própria:

```bash
export ANA_IDENTIFICADOR=seu_cpf_ou_cnpj
export ANA_SENHA=sua_senha
```

O token vale 60 minutos e é cacheado em disco de propósito — o manual da ANA avisa que
autenticação em alta frequência leva a bloqueio automático de IP. A API do Open-Meteo
também tem quota: `chuva_bp3.py` e `extremos_bp3.py` cacheiam tudo e o segundo tem recuo
progressivo no 429.

## Licença

MIT — ver [LICENSE](LICENSE).

Os dados de origem seguem as licenças de suas respectivas fontes, listadas acima.
