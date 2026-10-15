#!/bin/bash
# Injeta o contexto do projeto no início de cada sessão (stdout vira contexto).
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

echo "## Contexto do projeto carregado automaticamente"
echo
echo "### Arquivos em .claude/"
find .claude -type f \
  -not -path '*/hooks/*' -not -name 'settings*.json' -not -name '.DS_Store' 2>/dev/null | sort

for f in TASKS.md .claude/memory/glossary.md; do
  if [ -f "$f" ]; then
    echo
    echo "### $f"
    cat "$f"
  fi
done

for d in .claude/memory/people .claude/memory/projects .claude/memory/context; do
  if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
    echo
    echo "### $d/ (perfis disponíveis — leia sob demanda)"
    ls "$d"
  fi
done
exit 0
