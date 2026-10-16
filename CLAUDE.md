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

## tasks.csv — convenções
Tasks e scores ficam num arquivo só, `tasks.csv` (formato e regras de edição: skill task-management). Até 2026-10-15 eram `TASKS.md` + `PRIORITIES.md` (estão no histórico do git).
- Colunas: `id,parent,status,title,frente,dono,urgente,i,u,e,por_que,nota,done`. `id` é estável; subtarefa é uma linha com `parent` = id da task. Arquivo em **Latin-1** (acentos sim, símbolos não — decisão de Andre). Editar sempre com parser CSV (Python `csv`, `encoding='latin-1'`), nunca sed. `.gitattributes` faz o git guardá-lo em UTF-8 (diffs legíveis)
- Frente (coluna na Tabela/Mapa, cor no Board): grupos com subcategoria `platforms/{quartix-markets,oxpro,cfx,quartix-intel,sre}` e `produto/{quartix-markets,cfx}` (gestão de produto). Outras: ceo, release, advisory, marketing, explorar. Valor novo vira categoria nova (`grupo/sub` cria subcategoria)
- Dono: só Andre · quant: Andre · misto · delegável. Urgente: `x`
- Done = concluída: `status=Done` sempre com `done=x`, e `done=x` só existe em Done (o dashboard move/marca sozinho)
- Granularidade: cada item é uma task própria — nada de listas em texto corrido na nota. (Em 2026-10-15 todas as subtarefas existentes viraram tasks; subtarefas novas são permitidas, Andre as cria/edita no Ranking.) Task desmembrada de outra leva `origem: <task de origem>` na nota e herda dono/frente/urgente; a task de origem fica como agrupadora. Hierarquia mais funda vai no título com ` - ` (ex.: `Metaoxengine - Backup diário`)
- Títulos únicos entre as tasks
- Prioridade: colunas i/u/e (1–5) + por_que; o score não é gravado: Score = 200×(0,5·I + 0,35·U + 0,15·(6−E)) → 0 a 1000. Toda task nova recebe score próprio, calibrado pelas tasks semelhantes já pontuadas por Andre — não copiar o da origem

## Dashboard (dashboard.html)
- Abas: Board, List, Tabela (seções × frentes), Ranking, Mindmap (a aba Mapa foi removida em 2026-10-16). O **Ranking é a visão de trabalho principal** de Andre: ali ele cria task, edita título/frente/status/urgente/I/U/E/por quê, edita subtarefas (sempre visíveis) e exclui (🗑 ao lado da ⚑)
- Lê e grava só o `tasks.csv` (gravações em fila) e recarrega sozinho quando ele muda por fora — dá para editar o arquivo direto enquanto o dashboard está aberto
- Arquivo único: `dashboard.html` na raiz (versionado no git; não há cópia em `.claude/skills/`)
- Teste: cópia no scratchpad com script injetado (`applyTasksCsv(...)` + `switchTaskView`; para gravar, simular `taskFileHandle` com getFile/createWritable em memória), Chrome headless `--dump-dom`/`--screenshot`; macOS não tem `timeout`, usar `perl -e 'alarm 30; exec @ARGV' …`. Nunca testar sobre os arquivos reais
