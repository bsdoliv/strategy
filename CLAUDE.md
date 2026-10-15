# Memory

## Me
Andre de Oliveira, founder-CEO da **Quartix** (desde 2017; SP + Miami). Acumula quatro papéis:
- **CEO** — visão, ideação, direção da empresa
- **Estrategista de produto** da plataforma **quartix-markets**
- **Engenheiro-chefe de software** — lidera time de 3 pessoas
- **Quant líder** — a pessoa com finanças quantitativas mais avançadas da empresa; features quantitativas dependem da atenção profunda dele (prototipação, desenvolvimento e validação)

Este folder (`strategy/`) é a base de coordenação, gestão e execução da empresa.

## People
| Who | Role |
|-----|------|
| **Andre** | Andre de Oliveira, founder-CEO |
→ Time de engenharia (3 pessoas): a mapear. Perfis: .claude/memory/people/

## Terms
| Term | Meaning |
|------|---------|
| NDF | Non-Deliverable Forward |
| RFQ | Request for Quote |
| eSales | Distribuição eletrônica de preços |
| NTNF/LTN | Títulos prefixados do Tesouro |
| MtM | Mark-to-market |
| octaxpro/oxpro | Sistema core de trading (inferido) |
| cfx/clearfxai | Linha ClearFX AI (inferido) |
| metaox | Infra monitoração/CI-CD (inferido) |
→ Glossário completo: .claude/memory/glossary.md

## Projects
| Name | What |
|------|------|
| **QUARTIX Markets** | SaaS em nuvem p/ FX, juros e commodities (EM): dados, pricing, execução, hedge algorítmico; whitelabel |
| **NEXUS** | Curve engine + visão consolidada |
| **AUTO.QUOTE** | Pricing/distribuição multicanal de cotações |
| **PLEXUS** | Execução eletrônica + regras algorítmicas |
| **FX.AUTOHEDGE** | Hedge automático do fluxo RFQ |
| **HEDGE.OS** | Exposição e hedge p/ tesouraria corporativa (FX×commodities) |
| **FLOW.SIGHT** | Analytics do fluxo eSales |
| **LAUNCHPAD** | Monitor de mercado/notícias |
→ Detalhes: .claude/memory/projects/

## Preferences
- Comunicação em português
- Features quant passam por Andre (gargalo conhecido) — sinalizar quando uma tarefa depende dele

## TASKS.md — convenções
- Frente (coluna na Tabela/Mapa, cor no Board): uma tag na nota. Grupos com subcategoria: #platforms/{quartix-markets,oxpro,cfx,quartix-intel,sre} e #produto/{quartix-markets,cfx} (gestão de produto). Outras: #ceo #release #advisory #marketing #explorar. Tag nova vira categoria nova (#grupo/sub cria subcategoria)
- Dono: [só Andre] · [quant: Andre] · [misto] · [delegável]
- Flag: #urgente
- Done = concluída: task em `## Done` é sempre `- [x]`, e `- [x]` só existe em Done (o dashboard move/marca sozinho)
- Granularidade: cada item é uma task própria — nada de listas em texto corrido na nota nem subtarefas. Task desmembrada de outra leva `↳ <task de origem>` na nota e herda dono/frente/flags; a task de origem fica como agrupadora. Hierarquia mais funda vai no título com `›` (ex.: `Metaoxengine › Backup diário`)
- Se precisar de sub-itens: `  - [ ] ...` (o dashboard descarta bullets simples e subtítulos ###)
- Títulos únicos (o score casa pelo título) e sem `*` ou `|` (quebram o negrito e a tabela)
- Prioridade: PRIORITIES.md (I/U/E 1–5 + por quê, casado pelo título exato da tarefa); Score = 20×(0,5·I + 0,35·U + 0,15·(6−E)). Toda task nova recebe score próprio, calibrado pelas tasks semelhantes já pontuadas por Andre — não copiar o da origem
