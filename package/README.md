# founder/dash — backlog com Claude Code

Backlog pessoal em um único `tasks.csv`, com dashboard local (`dashboard.html`) e memória de trabalho para o Claude Code.

## Conteúdo

| Arquivo | Para quê |
|---|---|
| `dashboard.html` | Dashboard (Grid, Scored, Mindmap). Arquivo único, sem servidor |
| `tasks.csv` | Tasks + scores (vazio, só o cabeçalho) |
| `CLAUDE.md` | Memória de trabalho do Claude + convenções do backlog (modelo a preencher) |
| `.claude/skills/` | Skills: `start`, `update`, `task-management`, `memory-management` |
| `.claude/hooks/session-start.sh` | Injeta o resumo do `tasks.csv` e da memória no início de cada sessão |
| `.claude/settings.json` | Registra o hook |
| `.claude/memory/` | Memória profunda (people/, projects/, context/, glossary.md) — começa vazia |
| `.gitattributes` | Git guarda o `tasks.csv` (Latin-1) em UTF-8 |

## Instalação

1. Copie esta pasta para onde quiser (ex.: `~/backlog`) e, de preferência, faça `git init` nela.
2. Requisitos: Claude Code, `python3` (usado pelo hook), Chrome ou Edge.
3. Abra o Claude Code dentro da pasta e rode `/start` — ele aprende seus termos, pessoas e projetos e preenche o `CLAUDE.md`.
4. Abra o `dashboard.html` no navegador e clique em **Conectar pasta** escolhendo esta pasta (só na 1ª vez).

## Uso

- Crie e edite tasks no dashboard (aba Scored) ou peça ao Claude ("adiciona uma task...", "o que tenho para hoje?").
- `/update` sincroniza tasks e completa lacunas da memória.
- Frentes (colunas do Grid): vêm genéricas (Gestão, Comercial, Produto, Engenharia, Marketing, Financeiro, Pessoas, Exploratório) no `CATEGORY_META` de `dashboard.html`; edite labels/cores/ordem para as suas. Frentes novas aparecem sozinhas no fim.
