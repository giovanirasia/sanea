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

**Exploratório.** Ainda não há aplicação, API nem release — o que existe é um cliente da
API da ANA e os primeiros cruzamentos, validados num recorte piloto (Região Metropolitana
de São Paulo), para descobrir se as bases conversam antes de construir qualquer coisa em
cima delas.

O primeiro resultado está em [`relatorio-print.html`](relatorio-print.html): pontos do
programa Observando os Rios confrontados com os indicadores do SINISA na RMSP.

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

No Brasil o sinal é regionalmente oposto — excesso de chuva no Sul, seca no Nordeste e na
Amazônia — e as duas pontas degradam segurança hídrica por mecanismos contrários: cheia
extravasa esgoto e contamina abastecimento; seca leva a armazenamento domiciliar, criadouro
de vetor e concentração de poluentes em rios de vazão baixa.

A camada é **retrospectiva por decisão de projeto**. O objetivo não é prever o que vai
acontecer num município — teleconexão é probabilística e afirmar impacto local a partir de
índice global seria sobrepassar o dado. O objetivo é mostrar o que já aconteceu ali nos
eventos fortes anteriores (1982-83, 1997-98, 2015-16), usando a série ONI para classificar
os anos, e deixar o evento atual como contexto.

## Estrutura

```
ana/     cliente da API da ANA e cruzamentos
dados/   saídas derivadas, versionadas (os dumps brutos não são)
```

Os dumps brutos ficam em `dados/bruto/`, fora do versionamento: são grandes e
reprodutíveis a partir dos scripts.

## Como rodar

O cliente da ANA precisa de credencial própria, que não acompanha o repositório:

```bash
export ANA_IDENTIFICADOR=seu_cpf_ou_cnpj
export ANA_SENHA=sua_senha
```

O token vale 60 minutos e é cacheado em disco de propósito — o manual da ANA avisa que
autenticação em alta frequência leva a bloqueio automático de IP.

## Licença

MIT — ver [LICENSE](LICENSE).

Os dados de origem seguem as licenças de suas respectivas fontes, listadas acima.
