# QUARTIX Markets

**Status:** Em produção (desde 2017)
**Owner:** Andre (estratégia de produto + engenharia-chefe + modelos quant)
**Fonte:** assets/V2_brochure-QUARTIX.Markets-pt.pdf

## What It Is
Plataforma SaaS 100% em nuvem que reúne dados de mercado em tempo real, análise e precificação,
execução eletrônica e automação algorítmica para **FX (câmbio), juros/renda fixa e commodities**
em mercados emergentes. Integração com Microsoft Office/planilhas. Também oferecida em **whitelabel**.

**Clientes:** bancos, corretoras, gestoras, tesourarias corporativas, assessorias/intermediadores.
**Posicionamento:** tecnologia de nível institucional sem a complexidade e custo dos produtos globais.
Plataforma não comissionada e neutra em relação às contrapartes (Quartix não é parte de acordos de liquidez).

## Módulos
| Módulo | O que faz |
|--------|-----------|
| **NEXUS** / Curve Engine | Visão consolidada (preços, dados, notícias); valuation + construção/calibração de curvas em tempo real |
| **AUTO.QUOTE** | Pricing algorítmico a partir das curvas do NEXUS; distribui cotações multicanal (Bloomberg, 360T, Reuters, APIs, whitelabel); spreads por cliente/par/prazo |
| **FX.AUTOHEDGE** | Exposição líquida + P&L da sessão + fluxo de RFQs; regras de hedge (imediato por RFQ ou por teto de exposição por sentido bid/ask); blotter de offsets |
| **PLEXUS** | Execução eletrônica manual + algorítmica (FX spot/forward/NDF, NDF de commodities, NTNF/LTN); motor de regras com hit rate e P&L simulado; TCA, STP; oferecível em whitelabel |
| **HEDGE.OS** | Exposure & Hedge Management para tesouraria corporativa: book FX + commodities reavaliado a cada tick (CBOT, CME, B3), MtM ao vivo, VaR 99%, sinais de exposição composta FX×commodity, hedge accounting, compliance/auditoria |
| **FLOW.SIGHT** | Analytics de eSales: conversão por prazo, volume por contraparte, heatmaps, spreads; feedback loop para calibrar pricing e auto-hedge |
| **LAUNCHPAD** | Monitor de mercado: notícias, calendário econômico, painéis e alertas |
| **Serviço de Valuation** | Valuation independente/auditável (MtM) de NDFs e demais instrumentos |

**Pipeline eSales & Trading Autoflow:** NEXUS (curvas) → AUTO.QUOTE (cotação) → PLEXUS (execução) → FX.AUTOHEDGE (hedge) → FLOW.SIGHT (analytics/feedback).

## Capacidades quant (dependem do Andre)
Interpolação robusta de curvas, calibração automática de superfícies de volatilidade, pricing de derivativos
FX/juros/commodities, vol implícita vs realizada, carry/momentum, Monte Carlo, stress testing, otimização de
portfólio, VaR, valuation MtM, regras de hedge algorítmico.

## Outras features
- Confirmação de negociação via **WhatsApp** (recap → cliente confirma → vira negociação eletrônica)
- Atendimento 24/7 e treinamento

## Números (brochura)
Desde 2017: US$ 1 trilhão transacionado, 1,4 bilhão de cotações distribuídas, 500 mil ordens no balcão.

## Key People
- Andre — produto, engenharia, quant
- Time de engenharia (3 pessoas) — a mapear
