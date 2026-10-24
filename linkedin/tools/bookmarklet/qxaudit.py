#!/usr/bin/env python3
"""qxaudit - confere se uma pasta tem o JSON de cada link de um lote.

    python3 tools/bookmarklet/qxaudit.py <pasta> <lote.txt>

**A chave e o id do post dentro do JSON, nao o nome do arquivo.** O `qxgrab` corta o id em 60
chars e o Chrome ainda acrescenta ` (1)` quando dois downloads colidem.

Um link do lote pode cair num id diferente: o LinkedIn redireciona `activity-<id>` para o
`ugcPost-<id>` de baixo. O id muda e o slug nao, entao o slug e a segunda chave.
"""
import json, pathlib, re, sys

RE_ID = re.compile(r'(?:activity|ugcPost|share)[:\-](\d{6,})', re.I)
RE_SLUG = re.compile(r'/posts/([\w%-]{6,})')
RE_CAUDA = re.compile(r'-(?:activity|ugcpost|share)-\d{6,}(?:-\w{2,8})?$', re.I)


def chave(u):
    u = (u or '').split('?')[0].rstrip('/')
    m = RE_ID.search(u)
    return m.group(1) if m else u.lower()


def slug(u):
    """Slug sem o autor na frente nem o `-<tipo>-<id>-<sufixo>` no fim. Curto demais colide."""
    m = RE_SLUG.search((u or '').split('?')[0].rstrip('/'))
    if not m:
        return ''
    s = re.sub(r'^[a-z0-9-]{3,40}_', '', RE_CAUDA.sub('', m.group(1).lower()))
    return s if len(s) >= 12 else ''


def main(pasta, lote):
    links = []
    for linha in pathlib.Path(lote).read_text(encoding='utf-8').splitlines():
        u = linha.strip()
        if u and not any(l['url'] == u for l in links):
            links.append({'url': u, 'k': chave(u), 'slug': slug(u), 'caps': []})

    achados, ilegiveis = {}, []
    for f in sorted(pathlib.Path(pasta).expanduser().glob('qx-linkedin-*.json')):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            ilegiveis.append(f'{f.name}: {e}')
            continue
        u = d.get('url', '')
        achados.setdefault(chave(u), []).append(
            {'arq': f.name, 'url': u, 'slug': slug(u),
             'chars': len((d.get('texto') or '').strip()), 'imgs': len(d.get('imagens') or [])})

    usados = set()
    for l in links:                                    # 1a passada: id
        if l['k'] in achados:
            l['caps'] = achados[l['k']]
            usados.add(l['k'])
    sobrando = {}                                      # 2a passada: slug, so quando e 1-para-1
    for k, caps in achados.items():
        if k not in usados and caps[0]['slug']:
            sobrando.setdefault(caps[0]['slug'], []).append(k)
    querem = {}
    for l in links:
        if not l['caps'] and l['slug']:
            querem.setdefault(l['slug'], []).append(l)
    for l in links:
        cands = sobrando.get(l['slug'], []) if not l['caps'] else []
        if len(cands) == 1 and len(querem[l['slug']]) == 1:
            l['caps'] = achados[cands[0]]
            usados.add(cands[0])

    n = sum(len(c) for c in achados.values())
    print(f'qxaudit - {pathlib.Path(lote).name} x {pasta}')
    print(f'{len(links)} links no lote | {n} json na pasta\n')

    faltando = [l for l in links if not l['caps']]
    if faltando:
        print(f'FALTANDO ({len(faltando)})')
        for l in faltando:
            print(f'  {l["url"]}')
        print()

    def crua(u):
        return (u or '').split('?')[0].rstrip('/')

    redir = [l for l in links if l['caps'] and crua(l['caps'][0]['url']) != crua(l['url'])]
    if redir:
        print(f'REDIRECIONADO ({len(redir)}) - sucesso, casou pelo slug; o id do lote nao e o da pagina')
        for l in redir:
            print(f'  lote  {l["url"]}\n  json  {l["caps"][0]["url"]}')
        print()

    dup = [l for l in links if len(l['caps']) > 1]
    if dup:
        print(f'DUPLICADO ({len(dup)}) - mesmo post baixado 2x')
        for l in dup:
            print(f'  {l["k"]}: ' + ', '.join(c['arq'] for c in l['caps']))
        print()

    if ilegiveis:
        print(f'ILEGIVEL ({len(ilegiveis)})')
        for x in ilegiveis:
            print(f'  {x}')
        print()

    extras = [c for k, caps in achados.items() if k not in usados for c in caps]
    if extras:
        print(f'FORA DO LOTE ({len(extras)})')
        for c in extras:
            print(f'  {c["arq"]}\n    {c["url"]}')
        print()

    ok = [l for l in links if l['caps']]
    print(f'OK ({len(ok)})')
    for l in ok:
        c = l['caps'][0]
        print(f'  {l["k"]}  {c["chars"]} chars  {c["imgs"]} img  {c["arq"]}')
    print(f'\nresumo: {len(ok)} ok, {len(faltando)} faltando')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
