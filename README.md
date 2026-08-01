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
baixam as bases públicas, cruzam e testam hipóteses. O recorte trabalhado é a **Bacia
Hidrográfica do Paraná 3** (35 municípios do oeste do Paraná), com a Região Metropolitana
de São Paulo como piloto anterior.

## Resultados

Tudo abaixo é reproduzível pelos scripts deste repositório. Os números foram revisados
mais de uma vez; onde um controle metodológico derrubou um achado, o histórico do Git
registra o antes e o depois.

### Falta de esgoto e doença intestinal

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

O que sobrevive ao ajuste é a dose-resposta contínua:

> **Cada 10 pontos percentuais de cobertura de rede coletora associam-se a ~12% menos
> internação por A00–A09** — razão 0,884 (IC95% 0,803–0,973), p = 0,012.

Painel município-ano, Poisson com erro-padrão agrupado por município, offset de população.

Um resultado do modelo segue sem explicação: PIB per capita aparece associado a *mais*
internação (razão 2,03, p = 0,018). Pode ser acesso a leito, pode ser colinearidade com
cobertura. Está registrado como pendência, não interpretado.

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
- "sem rede" é inferido da ausência do município no módulo de esgoto do SINISA — os 15
  aparecem normalmente no módulo de água, com 60% a 100% de cobertura
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
dados_ibge/  população, PIB e área municipal
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
python saneamento/sinisa_bp3.py   # exige as planilhas do SINISA em disco
python saude/chuva_x_diarreia.py  # chuva x doença, bacia agregada
python saude/estratificado.py     # o mesmo, por estrato de saneamento
python saude/gradiente_ajustado.py  # o gradiente com renda e ruralidade controladas
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
