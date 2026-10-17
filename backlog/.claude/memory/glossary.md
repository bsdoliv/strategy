# Glossary

## Acronyms & Terms
| Term | Meaning | Context |
|------|---------|---------|
| FX | Câmbio | Classe de ativo core |
| NDF | Non-Deliverable Forward | Derivativo de balcão FX e commodities; core do Valuation e PLEXUS |
| NTNF / LTN | Títulos públicos federais prefixados (Tesouro) | Renda fixa no PLEXUS |
| RFQ | Request for Quote | Fluxo de cotação do balcão (FX.AUTOHEDGE) |
| OTC | Over-the-counter / balcão | |
| eSales | Electronic sales — distribuição eletrônica de preços a clientes | AUTO.QUOTE, FLOW.SIGHT |
| MtM | Mark-to-market | HEDGE.OS, Valuation |
| VaR | Value at Risk (99%) | Risk engine do HEDGE.OS |
| TCA | Transaction Cost Analysis | PLEXUS |
| STP | Straight-Through Processing | PLEXUS |
| P&L | Profit & Loss | |
| Whitelabel | Módulos revendidos com a marca do parceiro | Modelo de distribuição |
| B3 / BM&F, CBOT, CME, ICE | Bolsas / feeds de dados | |

## Nicknames → Full Names
| Nickname | Person |
|----------|--------|
| Andre | Andre de Oliveira (founder-CEO) |

## Project Codenames / Módulos
| Name | Project |
|------|---------|
| QUARTIX Markets / quartix-markets | Plataforma principal |
| NEXUS | Curve engine + visão consolidada |
| AUTO.QUOTE | Pricing e distribuição de cotações |
| FX.AUTOHEDGE | Hedge automático do fluxo FX |
| PLEXUS | Execução eletrônica/algorítmica |
| HEDGE.OS | Gestão de exposição e hedge (tesouraria corporativa) |
| FLOW.SIGHT | Analytics de fluxo eSales |
| LAUNCHPAD | Monitor de mercado |

## Termos do mind map (inferidos — a confirmar)
| Term | Provável significado |
|------|---------------------|
| cfx / clearfxai | Produto/linha ClearFX AI (control-plane, rfqd, whitelabel/PRX) |
| octaxpro / oxpro | Sistema legado/core de trading (octax-api, sandbox, integração com quartix-markets) |
| metaox / Metaoxengine / metaox-next | Infra de monitoração, cron e CI/CD |
| prodsafra / prodfibra | Ambientes de produção por cliente (Safra, Fibra) |
| Safra | Banco cliente (certificados TLS, ngrok) |
| Banco Pine | Cliente/prospect em integração (auto-quote) |
| Damke | Cliente-alvo do hedgeOS (release + convite p/ apresentação) |
| valorpro | Cliente/parceiro ligado ao Plexus |
| cherry / chery / PortAR / Port.AR | Integração/parceiro (relacionado a hedgeOS) |
| bpipe | Bloomberg B-PIPE (feed de dados) |
| pulse | Serviço de alertas/contagem (mail alerts pulse, pulseclean) |
| isabel | Protótipo de chat |
| Braza | Parceiro com API a integrar (backlog CFX) |
| Fernando Silveira | Contato estratégico (follow up; possivelmente "Opensource Fernando") |
| Marcos I9DC | Contato/frente estratégica |
| Sangria (de dados) | Extração diária dos dados de produção das instâncias octaxpro para a plataforma de dados (confirmado por Andre; no mind map aparecia como "Daily Data leak from oxpro") |
