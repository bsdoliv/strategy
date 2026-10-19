---
name: task-management
description: Task management using the shared tasks.csv file (tasks + priority scores in one place). Reference this when the user asks about their tasks, wants to add/complete/prioritize tasks, or needs help tracking commitments.
user-invocable: false
---

# Task Management

Tasks and their priority scores live in **one file: `tasks.csv`** at the project root. Andre edits it through the dashboard (`dashboard.html`, mainly the Scored tab, formerly Ranking); you edit it directly. The project conventions (frentes, today, score) are in `CLAUDE.md` — follow them.

## File format

**Latin-1 (ISO-8859-1), no BOM**, `\n` line endings, comma-separated, RFC 4180 quoting (fields with `,` `"` or line breaks go in double quotes; `"` is doubled). Accents are fine; **no symbols outside Latin-1** (Andre's decision, 2026-10-15): write `origem: X` instead of an arrow, ` - ` as hierarchy separator in titles, `com`/`para` instead of arrows, `...` instead of an ellipsis, plain quotes and hyphens. `.gitattributes` makes git store it as UTF-8, so diffs show accents correctly. Header:

```
id,parent,status,title,frente,today,attention,i,u,e,nota,done
```

| Column | Meaning |
|---|---|
| `id` | Stable integer id of the task. Subtasks use `<parent id>.<n>` |
| `parent` | Empty for a task; the task's `id` for a subtask row |
| `status` | Section: `Someday`, `Active`, `Waiting On` (a new value becomes a new section). Done is NOT a status — it is the `done` flag |
| `title` | Task title (any text; must be unique among tasks) |
| `frente` | Category, without `#` (e.g. `platforms/cfx`, `ceo`) |
| `today` | `x` or empty — flag for what Andre wants to work on now (renamed from `urgente` on 2026-10-19) |
| `attention` | `x` or empty — flag for tasks that need Andre's attention (yellow in the dashboard; added 2026-10-19). Independent of `today` |
| `i`,`u`,`e` | Impact, Urgency, Effort, 1–5. Score is **not stored**: 200×(0,5·I + 0,35·U + 0,15·(6−E)) → 0–1000 |
| `nota` | Single note: score rationale first, then other context, joined with ` · ` (e.g. `Risco de perda de dados; barato · origem: <task de origem>`) — never a list in running text. (A separate `por_que` column existed until 2026-10-19 and was merged here.) |
| `done` | `x` when done. Independent of `status`: the task keeps its status and position |

Rows of a section appear in board order; subtask rows come right after their task. Only task rows carry frente/today/attention/score. (There is no owner column: `dono` was removed on 2026-10-19; the dashboard ignores it in old files.)

## How to edit safely

- Edit with a script that uses a real CSV parser: read with `encoding='latin-1'` (the dashboard also accepts UTF-8 if a spreadsheet saved it that way), write back with `encoding='latin-1'`, `newline=''` and `lineterminator='\n'`. Never sed/regex on lines.
- Keep the column order and header exactly as above.
- New task: next free integer `id`, own I/U/E judged against similar tasks already scored (do not copy the parent's score).
- The dashboard reloads the file by itself when it changes on disk.

## Dashboard

`dashboard.html` at the project root (`strategy/backlog/`) is the only copy (versioned in git). If it is missing, restore it with `git checkout -- dashboard.html`. It reads/writes `tasks.csv`, auto-saves, and watches for external changes.

## How to Interact

**"What's on my plate" / "my tasks":** read `tasks.csv`, summarize Active and Waiting On by score, list `today` tasks first, then highlight the rest by status/score.

**"Add a task" / "remind me to":** add a row (status Active unless told otherwise) with frente and a judged score.

**"Done with X":** set `done=x` (keep `status` as is).

**"What am I waiting on":** list `status=Waiting On`.

## Extracting Tasks

When summarizing meetings or conversations, offer to add extracted tasks (commitments, action items, follow-ups). Ask before adding.
