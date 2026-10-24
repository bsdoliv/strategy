#!/usr/bin/env python3
"""Gera tagspostmap.csv: id, titulo e tags de cada post PUBLICADO.

  python3 tools/qxtags.py            # regenera e mostra o resumo
  python3 tools/qxtags.py --quiet    # regenera calado
  python3 tools/qxtags.py --check    # nao escreve; exit 1 se o arquivo estiver desatualizado

DERIVADO, NAO LEDGER. Este e o unico arquivo do projeto que se reescreve por inteiro, porque nao
guarda estado nenhum: e uma projecao de `ledger/backlog.done.csv` (titulo do que foi publicado) sobre
`ledger/backlog.meta.csv` (tags). Nao edite a mao - a proxima execucao apaga a edicao. Para mudar uma tag,
acrescente a linha corrigida em `ledger/backlog.meta.csv` (vale a mais recente) e rode isto de novo.

Em ambos os arquivos de origem vale a MESMA regra: a linha mais recente de cada id vence.
"""
import csv, io, pathlib, re, sys

R = pathlib.Path(__file__).resolve().parent.parent
OUT = R / 'tagspostmap.csv'
HDR = ['id', 'title', 'tags']

def rows(name):
    p = R / 'ledger' / name
    return list(csv.DictReader(open(p, encoding='utf-8'))) if p.exists() else []

def build():
    # linha efetiva = a mais recente de cada id, nos dois arquivos
    pub = {}
    for r in sorted(rows('backlog.done.csv'), key=lambda r: r.get('ts') or ''):
        if (r.get('status') or '').strip() == 'published':
            pub[r['item_id']] = r
    meta = {r['id']: r for r in sorted(rows('backlog.meta.csv'), key=lambda r: r.get('ts') or '')}

    out, sem_tag = [], []
    for i in sorted(pub):
        t = (pub[i].get('title_final') or '').strip()
        # alguns titulos vem com o prefixo do nome do Doc; a coluna aqui e o titulo, so
        t = re.sub(rf'^{re.escape(i)}\s*-\s*', '', t).strip()
        # origem vem com separador inconsistente ('a;b' e 'a; b'); o arquivo gerado e canonico
        tags = ';'.join(x.strip() for x in (meta.get(i, {}).get('tags') or '').split(';') if x.strip())
        if not tags: sem_tag.append(i)
        out.append({'id': i, 'title': t, 'tags': tags})
    return out, sem_tag

def render(out):
    b = io.StringIO()
    w = csv.DictWriter(b, HDR, lineterminator='\n')
    w.writeheader(); w.writerows(out)
    return b.getvalue()

def main():
    out, sem_tag = build()
    txt = render(out)
    check = '--check' in sys.argv
    quiet = '--quiet' in sys.argv
    atual = OUT.read_text(encoding='utf-8') if OUT.exists() else ''

    if check:
        if atual != txt:
            print(f'tagspostmap.csv desatualizado ({len(out)} posts publicados). '
                  f'Rode: python3 tools/qxtags.py')
            return 1
        if not quiet: print(f'tagspostmap.csv em dia ({len(out)} posts).')
        return 0

    OUT.write_text(txt, encoding='utf-8')
    if quiet: return 0
    n_tags = sum(len([x for x in r['tags'].split(';') if x.strip()]) for r in out)
    from collections import Counter
    c = Counter(x.strip() for r in out for x in r['tags'].split(';') if x.strip())
    print(f'tagspostmap.csv: {len(out)} posts, {n_tags} aplicacoes de tag, {len(c)} tags distintas')
    print('  mais usadas: ' + ', '.join(f'{k} ({v})' for k, v in c.most_common(8)))
    if sem_tag: print(f'  ATENCAO {len(sem_tag)} post(s) sem tags em meta.csv: {sem_tag}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
