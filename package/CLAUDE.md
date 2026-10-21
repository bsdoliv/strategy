# Memory

## Me
[Nome], [papel] na **[Empresa]**. [Uma frase sobre o que faz.]
(Preenchido pelo `/start` na primeira sessão.)

## People
| Who | Role |
|-----|------|
| **[Apelido]** | [Nome completo], [papel] |
→ Perfis: .claude/memory/people/

## Terms
| Term | Meaning |
|------|---------|
| [sigla] | [significado] |
→ Glossário completo: .claude/memory/glossary.md

## Projects
| Name | What |
|------|------|
| **[Codinome]** | [descrição] |
→ Detalhes: .claude/memory/projects/

## Preferences
- Comunicação em português

## tasks.csv — convenções
Tasks e scores ficam num arquivo só, `tasks.csv` (formato e regras de edição: skill task-management).
- Colunas: `id,parent,status,title,frente,today,attention,i,u,e,nota,done,tags`. `id` é estável; subtarefa é uma linha com `parent` = id da task. Arquivo em **Latin-1** (acentos sim, símbolos não). Editar sempre com parser CSV (Python `csv`, `encoding='latin-1'`), nunca sed. `.gitattributes` faz o git guardá-lo em UTF-8 (diffs legíveis)
- Frente (coluna no Grid, cor no Scored): texto livre, sem `#`; `grupo/sub` cria subcategoria (ex.: `produto/app`). Valor novo vira categoria nova
- Today: `x` — flag do que se quer tocar agora. Attention: `x` — flag amarela de "precisa de atenção", independente do today. Tags: pares `[chave=valor]` concatenados; por ora só `[victoria=1]` = flag Victoria (roxa); pares desconhecidos são preservados
- Done é flag (`done=x`), não status: status são Active, Someday e Waiting On. Marcar Done não move a task: ela fica no status/posição, riscada; "Ocultar Done" esconde as tasks com a flag
- Granularidade: cada item é uma task própria — nada de listas em texto corrido na nota. Task desmembrada de outra leva `origem: <task de origem>` na nota e herda frente/today; a de origem fica como agrupadora. Hierarquia mais funda vai no título com ` - `
- Títulos únicos entre as tasks
- Prioridade: colunas i/u/e (1–5); o score não é gravado: Score = 200×(0,5·I + 0,35·U + 0,15·(6−E)) → 0 a 1000. Toda task nova recebe score próprio, calibrado pelas tasks semelhantes já pontuadas — não copiar o da origem
- Nota única (`nota`): justificativa do score primeiro, depois o resto (ex.: `origem: ...`), separados por ` · `

## Dashboard (dashboard.html)
- Abrir `dashboard.html` no Chrome/Edge (precisa da File System Access API) e conectar a pasta que contém o `tasks.csv` (só na 1ª vez)
- Abas: Grid (status × frentes; padrão), Scored (lista por score; visão de trabalho principal: cria task, edita título/frente/status/flags/IMP/URG/EFF/nota/subtarefas, exclui), Mindmap
- Flags: today (verde), attention (amarelo), Victoria (roxo). Cards de topo Active/today/attention/Victoria são clicáveis = filtro
- Grid: arrastar muda status/frente; "–" no cabeçalho recolhe a frente numa faixa; "Ocultar frentes sem: [Active] [today] [attention]" recolhe as frentes sem tasks que atendam aos chips ligados. Ordem das colunas = `CATEGORY_META` em `dashboard.html` (vem com as frentes de quem criou o framework — editar para as suas; frente nova entra no fim)
- Scored: ordena por status e score; tasks com Done riscadas
- Filtros persistem no localStorage. Lê e grava só o `tasks.csv` e recarrega sozinho quando ele muda por fora — dá para editar o arquivo direto com o dashboard aberto
- Teste de mudanças no dashboard: sempre numa cópia (nunca sobre os arquivos reais); Chrome headless `--dump-dom`/`--screenshot`; validar sintaxe extraindo o `<script>` e rodando `node --check`
