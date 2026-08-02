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

Dois recortes, e a comparação entre eles é parte do método: a **Bacia Hidrográfica do
Paraná 3** (35 municípios do oeste do estado) e o **Paraná inteiro** (399 municípios).
Todo módulo aceita `SANEA_ESCOPO`, e o segundo recorte existe porque o primeiro produziu
um achado que não replicou — o que só ficou visível ao escalar. A Região Metropolitana de
São Paulo foi um piloto anterior, com o programa Observando os Rios.

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

> **cobertura de esgoto = 1,000 (IC95% 0,998–1,002, p = 0,98)**

Nenhuma associação. Não é efeito pequeno: é ausência, com intervalo apertado o bastante
para afirmar isso. **A hipótese de que a cobertura municipal de esgoto prediz internação
por doença de veiculação hídrica não se sustenta no Paraná.**

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
- **sobra um resto sem explicação.** Candidatos não testados: fonte de água domiciliar no
  rural (poço e nascente não entram no IAG0001), solução individual de esgoto mal
  executada, distância até atenção básica

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
- a estrutura etária vem do Censo 2022, um ponto no tempo aplicado a um painel de 19 anos
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
| DATASUS | internações e agravos de veiculação hídrica | público |
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
ana/         cliente da API da ANA e cruzamentos (piloto RMSP)
clima/       bacia, série ONI, chuva e extremos por município
saude/       internações do SIH/SUS e os modelos
saneamento/  indicadores do SINISA e a estratificação
dados_ibge/  população, PIB, área, estrutura etária e rebanho
dados/       saídas derivadas, versionadas (os dumps brutos não são)
```

Os dumps brutos ficam em `dados/bruto/`, fora do versionamento: são grandes e
reprodutíveis a partir dos scripts. O do SIH chega a 1,2 GB baixado, do qual sobram
33 MB depois do filtro.

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
python saude/chuva_x_diarreia.py  # chuva x doença, bacia agregada
python saude/estratificado.py     # o mesmo, por estrato de saneamento
python saude/gradiente_ajustado.py  # o gradiente com renda e ruralidade controladas
python saude/densidade.py         # o que a densidade demográfica está medindo
```

Para rodar no estado inteiro em vez da bacia, prefixe com `SANEA_ESCOPO=parana`. Os dois
escopos gravam em arquivos separados e convivem lado a lado:

```bash
SANEA_ESCOPO=parana python saude/gradiente_ajustado.py
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
