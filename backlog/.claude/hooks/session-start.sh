#!/bin/bash
# Injeta o contexto do projeto no início de cada sessão (stdout vira contexto).
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

echo "## Contexto do projeto carregado automaticamente"
echo
echo "### Arquivos em .claude/"
find .claude -type f \
  -not -path '*/hooks/*' -not -name 'settings*.json' -not -name '.DS_Store' 2>/dev/null | sort

# tasks.csv (tasks + scores): resumo legível por status, ordenado por score
if [ -f tasks.csv ]; then
  echo
  echo "### tasks.csv (resumo; formato na skill task-management)"
  python3 - <<'PY'
import csv
raw = open('tasks.csv', 'rb').read()
try: text = raw.decode('utf-8-sig')   # caso alguma planilha tenha salvo em UTF-8
except UnicodeDecodeError: text = raw.decode('latin-1')
rows = list(csv.DictReader(text.splitlines()))
def score(r):
    try: return round(200 * (0.5 * int(r['i']) + 0.35 * int(r['u']) + 0.15 * (6 - int(r['e']))))
    except (ValueError, KeyError): return None
subs = {}
for r in rows:
    if r.get('parent'): subs.setdefault(r['parent'], []).append(r)
order = []
for r in rows:
    if not r.get('parent') and r['status'] not in order: order.append(r['status'])
for st in order:
    ts = sorted((r for r in rows if not r.get('parent') and r['status'] == st), key=lambda r: -(score(r) or -1))
    print(f"\n#### {st} ({len(ts)})")
    for r in ts:
        s = score(r)
        extra = ' · '.join(x for x in [r['frente'], 'TODAY' if (r.get('today') or r.get('urgente')) else '', 'ATTENTION' if r.get('attention') else '', 'VICTORIA' if '[victoria=1]' in (r.get('tags') or '') else '', 'DELAYED' if '[delayed=1]' in (r.get('tags') or '') else '', r['nota']] if x)
        print(f"- [{r['id']}] {s if s is not None else '–'} {r['title']}" + (f" — {extra}" if extra else ''))
        for c in subs.get(r['id'], []):
            print(f"    - [{'x' if c['done'] else ' '}] {c['title']}")
PY
fi

for f in .claude/memory/glossary.md; do
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
