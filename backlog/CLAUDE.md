# Memory

## Me
Andre de Oliveira, founder-CEO da **Quartix** (desde 2017; SP + Miami). Acumula quatro papéis:
- **CEO** — visão, ideação, direção da empresa
- **Estrategista de produto** da plataforma **quartix-markets**
- **Engenheiro-chefe de software** — lidera time de 3 pessoas
- **Quant líder** — a pessoa com finanças quantitativas mais avançadas da empresa; features quantitativas dependem da atenção profunda dele (prototipação, desenvolvimento e validação)

O folder `strategy/` é a base de coordenação, gestão e execução da empresa; o backlog (tasks, dashboard, memória do Claude) fica em `strategy/backlog/` desde 2026-10-17 — abrir o Claude Code nesse diretório.

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
- Colunas: `id,parent,status,title,frente,dono,urgente,i,u,e,nota,done`. `id` é estável; subtarefa é uma linha com `parent` = id da task. Arquivo em **Latin-1** (acentos sim, símbolos não — decisão de Andre). Editar sempre com parser CSV (Python `csv`, `encoding='latin-1'`), nunca sed. `.gitattributes` faz o git guardá-lo em UTF-8 (diffs legíveis)
- Frente (coluna no Grid, cor no Scored): grupos com subcategoria `platforms/{quartix-markets,oxpro,cfx,quartix-intel,sre}` e `produto/{quartix-markets,cfx}` (gestão de produto). Outras: ceo, release, advisory, marketing, explorar. Valor novo vira categoria nova (`grupo/sub` cria subcategoria)
- Dono: só Andre · quant: Andre · misto · delegável. Urgente: `x`
- Done = concluída: `status=Done` sempre com `done=x`, e `done=x` só existe em Done (o dashboard move/marca sozinho)
- Granularidade: cada item é uma task própria — nada de listas em texto corrido na nota. (Em 2026-10-15 todas as subtarefas existentes viraram tasks; subtarefas novas são permitidas, Andre as cria/edita no Scored.) Task desmembrada de outra leva `origem: <task de origem>` na nota e herda dono/frente/urgente; a task de origem fica como agrupadora. Hierarquia mais funda vai no título com ` - ` (ex.: `Metaoxengine - Backup diário`)
- Títulos únicos entre as tasks
- Prioridade: colunas i/u/e (1–5); o score não é gravado: Score = 200×(0,5·I + 0,35·U + 0,15·(6−E)) → 0 a 1000. Toda task nova recebe score próprio, calibrado pelas tasks semelhantes já pontuadas por Andre — não copiar o da origem
- Nota única (`nota`): justificativa do score primeiro, depois o resto (ex.: `origem: ...`), separados por ` · `. Em 2026-10-19 a coluna `por_que` foi mesclada nela (o dashboard ainda lê CSV antigo com `por_que` e junta na nota)

## Dashboard (dashboard.html)
- Abas, nesta ordem: Grid (ex-Tabela; seções × frentes; aba padrão), Scored (ex-Ranking), Mindmap. Removidas: Mapa (2026-10-16), List e Board/Kanban (2026-10-17). O **Scored é a visão de trabalho principal** de Andre: ali ele cria task, edita título/frente/status/urgente/IMP/URG/EFF/nota, edita subtarefas e exclui (🗑 ao lado da ⚑)
- Scored: ordena por status (Active → Waiting On → Someday → outros → Done) e depois por score (desc); filtros de Frente e de Status no cabeçalho (localStorage `rankCatHidden`/`rankStatusHidden`); status colorido (Active verde, Waiting On amarelo, Someday/Done padrão)
- Título da aplicação: Backlog. Scored não tem coluna Dono
- Dono: o dashboard não usa mais o dono (pills, card "dependem de você" e "N suas" do Grid removidos em 2026-10-17); o valor segue no tasks.csv
- Grid: clicar no score de um card (ou "+ score") abre IMP/URG/EFF no próprio card e grava no tasks.csv
- Grid: clicar no título abre o card em edição (título, nota, subtarefas; × fecha). No Scored a nota é a última coluna ("Nota", editável); as tags de frente/dono/urgente da nota são preservadas
- Botão "Mostrar/Ocultar notas e subtarefas" (todas as abas; no Grid também esconde a nota dos cards fechados; estado em localStorage `showSubs`, padrão visível)
- Lê e grava só o `tasks.csv` (gravações em fila) e recarrega sozinho quando ele muda por fora — dá para editar o arquivo direto enquanto o dashboard está aberto
- Relatórios (PDF) vão em `reports/` (`AAAA-MM-DD-<tema>.pdf`); uma página só
- Arquivo único: `dashboard.html` em `backlog/` (desde 2026-10-17, junto com `tasks.csv` e `.claude/`; versionado no git; não há cópia em `.claude/skills/`). A pasta conectada deve ser `backlog/`; se a pasta guardada for `strategy/`, o dashboard desce sozinho para `backlog/`
- Teste: cópia no scratchpad com script injetado (`applyTasksCsv(...)` + `switchTaskView`; para gravar, simular `taskFileHandle` com getFile/createWritable em memória), Chrome headless `--dump-dom`/`--screenshot`; macOS não tem `timeout`, usar `perl -e 'alarm 30; exec @ARGV' …`. Nunca testar sobre os arquivos reais
