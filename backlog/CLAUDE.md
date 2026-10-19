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
- Colunas: `id,parent,status,title,frente,today,attention,i,u,e,nota,done`. `id` é estável; subtarefa é uma linha com `parent` = id da task. Arquivo em **Latin-1** (acentos sim, símbolos não — decisão de Andre). Editar sempre com parser CSV (Python `csv`, `encoding='latin-1'`), nunca sed. `.gitattributes` faz o git guardá-lo em UTF-8 (diffs legíveis)
- Frente (coluna no Grid, cor no Scored): grupos com subcategoria `platforms/{quartix-markets,oxpro,cfx,quartix-intel,sre}` e `produto/{quartix-markets,cfx}` (gestão de produto). Outras: ceo, release, advisory, marketing, explorar. Valor novo vira categoria nova (`grupo/sub` cria subcategoria)
- Sem coluna de dono: removida em 2026-10-19 (Andre: irrelevante; o histórico está no git). Dependência do quant de Andre: deduzir pelo conteúdo da task (ou "quant" na nota). Today: `x` — flag do que Andre quer tocar agora; substituiu `urgente` em 2026-10-19 (o dashboard ainda lê a coluna antiga). Attention: `x` — flag amarela de "precisa de atenção", independente do today (criada em 2026-10-19; CSV sem a coluna é lido normalmente)
- Done é flag (`done=x`), não status (desde 2026-10-19): status são só Active, Someday e Waiting On. Marcar Done (checkbox no Grid) não move a task: ela fica no status/posição em que está, riscada; "Ocultar Done" esconde as tasks com a flag. CSV antigo com `status=Done` é lido como Active + `done=x` e regravado assim
- Granularidade: cada item é uma task própria — nada de listas em texto corrido na nota. (Em 2026-10-15 todas as subtarefas existentes viraram tasks; subtarefas novas são permitidas, Andre as cria/edita no Scored.) Task desmembrada de outra leva `origem: <task de origem>` na nota e herda frente/today; a task de origem fica como agrupadora. Hierarquia mais funda vai no título com ` - ` (ex.: `Metaoxengine - Backup diário`)
- Títulos únicos entre as tasks
- Prioridade: colunas i/u/e (1–5); o score não é gravado: Score = 200×(0,5·I + 0,35·U + 0,15·(6−E)) → 0 a 1000. Toda task nova recebe score próprio, calibrado pelas tasks semelhantes já pontuadas por Andre — não copiar o da origem
- Nota única (`nota`): justificativa do score primeiro, depois o resto (ex.: `origem: ...`), separados por ` · `. Em 2026-10-19 a coluna `por_que` foi mesclada nela (o dashboard ainda lê CSV antigo com `por_que` e junta na nota)

## Dashboard (dashboard.html)
- Abas, nesta ordem: Grid (ex-Tabela; seções × frentes; aba padrão), Scored (ex-Ranking), Mindmap. Removidas: Mapa (2026-10-16), List e Board/Kanban (2026-10-17). O **Scored é a visão de trabalho principal** de Andre: ali ele cria task, edita título/frente/status/today (⚑)/IMP/URG/EFF/nota, edita subtarefas e exclui (🗑 ao lado da ⚑)
- Scored: ordena por status (Active → Waiting On → Someday → outros; tasks com Done ficam no lugar, riscadas) e depois score (desc); linhas com today ficam verdes e com attention amarelas (sem mudar a ordem; botão "!" ao lado da ⚑ marca attention); filtros de Frente e de Status no cabeçalho (localStorage `rankCatHidden`/`rankStatusHidden`); status colorido (Active verde, Waiting On amarelo, Someday padrão)
- Scored, colunas: #, Score, Tarefa (+ subtarefas), Frente, Status, IMP, URG, EFF, Nota (editável; tags de frente/today da nota são preservadas)
- Grid, ordem das colunas (frentes) = ordem do `CATEGORY_META`: CEO / Comercial, Platforms (quartix-markets, oxpro, cfx, quartix-intel, sre), Produto (quartix-markets, cfx), Advisory, Marketing, Release, Exploratório; frente nova entra no fim
- Grid, show/hide de coluna: "–" no cabeçalho (hover) recolhe a frente numa faixa estreita (rótulo vertical + contagem por linha; continua aceitando drop); clicar na faixa reexibe; "N colunas ocultas · mostrar todas" na toolbar. localStorage `gridColHidden`
- Grid, filtro "Ocultar frentes sem Active/today/attention" (toolbar, ao lado de Ocultar Done, só no Grid): recolhe em faixa (igual ao "–") as frentes sem nenhuma task não-Done em Active nem com today/attention (respeita os demais filtros); entram na contagem "N colunas ocultas"; clicar na faixa reabre a frente (até ligar/desligar o filtro); "mostrar todas" também desliga o filtro. Salvo em `viewFilters.focusCols`. Regra: "ocultar" no Grid = recolher em faixa, nunca remover
- Grid, linhas (status): Active → Waiting On → Someday → outras; linha sem tasks visíveis fica discreta (baixa, título apagado, sem contagem), mas aceita drop e "+ nova tarefa"
- Grid: cards com today ficam verdes (qualquer status) e com attention amarelos (com as duas, amarelo prevalece; as duas pills aparecem); as pills today/attention são clicáveis (cor = marcada, clique desmarca; "⚑ today"/"! attention" aparecem no hover para marcar); card fechado mostra score, today, nota (cinza) e subtarefas; clicar no score (ou "+ score") abre IMP/URG/EFF no card; clicar no título abre o card em edição (título, nota, subtarefas; × fecha; aberto não arrasta). Arrastar muda status/frente; 🗑 pequena (9px, menor que a do Scored) no canto do card, visível no hover, exclui com confirmação (mesma função do Scored)
- Título da aplicação: founder/dash (até 2026-10-19: Backlog). Cards de topo: Active, today e attention (clicáveis = filtro; today/attention mostram só tasks com a flag, em todas as abas). Não há dono (UI removida em 2026-10-17, coluna em 2026-10-19)
- Filtros persistem no localStorage (sobrevivem ao recarregar): `viewFilters` (cards Active/today/attention, Ocultar Done), `minScore`, `gridColHidden`, `rankCatHidden`/`rankStatusHidden`, `showSubs`, `taskView` (aba)
- Botão "Mostrar/Ocultar notas e subtarefas" (todas as abas; no Grid também esconde a nota dos cards fechados; estado em localStorage `showSubs`, padrão visível)
- Lê e grava só o `tasks.csv` (gravações em fila) e recarrega sozinho quando ele muda por fora — dá para editar o arquivo direto enquanto o dashboard está aberto
- Relatórios (PDF) vão em `reports/` (`AAAA-MM-DD-<tema>.pdf`); uma página só
- Arquivo único: `dashboard.html` em `backlog/` (desde 2026-10-17, junto com `tasks.csv` e `.claude/`; versionado no git; não há cópia em `.claude/skills/`). A pasta conectada deve ser `backlog/`; se a pasta guardada for `strategy/`, o dashboard desce sozinho para `backlog/`
- Teste: cópia no scratchpad com script injetado (`applyTasksCsv(...)` + `switchTaskView`; para gravar, simular `taskFileHandle` com getFile/createWritable em memória), Chrome headless `--dump-dom`/`--screenshot`; macOS não tem `timeout`, usar `perl -e 'alarm 30; exec @ARGV' …`. Nunca testar sobre os arquivos reais. Armadilhas: o autosave espera 500 ms (aguardar >1 s antes de ler o que foi gravado); em heredoc sem aspas `\n` vira quebra de linha real e quebra o JS injetado (usar `<<'EOF'` ou `String.fromCharCode(10)`); `grep` no tasks.csv falha em linhas com acento (Latin-1) — ler com Python; validar sintaxe extraindo o `<script>` e rodando `node --check`
