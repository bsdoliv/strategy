#!/usr/bin/env python3
"""Recupera, DENTRO do JSON ja salvo, o corpo do post que a v9 do `qxgrab` gravou errado.

Nove das trinta capturas em `linkedin/` sairam com a PAGINA INTEIRA no campo `texto`: a descida
por quebras da v9 parava em `document.body` quando nenhum filho concentrava 85% das quebras, e o
resultado passava folgado no teste de 120 chars - falhava gravando, em silencio. Junto com o
`texto` vieram errados `autor` (virava "Premium", da barra lateral do proprio usuario), o cargo e
a data. As imagens desses arquivos em sua maioria nem baixaram (`HTTP 403`, `Failed to fetch`), e
varias nem eram do post - eram `article-cover` da coluna de sugestoes.

**Por que da para consertar sem reabrir o LinkedIn:** o texto da pagina inteira CONTEM o post, e o
innerText do LinkedIn tem esqueleto fixo e nomeado. Nao e adivinhacao por formato:

    Feed post          <- marcador literal, presente em 8 dos 9
    <autor>
     - <grau>          (opcional)
    <cargo>
    <tempo> - [Edited] <- ancora do fim do cabecalho
    [Follow|Connect]   (opcional)
    <CORPO>            <- o que queremos
    <N reactions>      <- ancora do fim do corpo

Artigo `/pulse/` nao tem "Feed post" e usa outro esqueleto; ali a ancora e a linha igual ao
`titulo_pagina` (sem o sufixo " | LinkedIn"), seguida de autor, cargo e data.

**Cada reparo e VERIFICADO antes de valer**, com o mesmo criterio da v12 do `qxgrab`: as palavras
do slug da URL tem que aparecer no corpo extraido (>=60% dos tokens, minimo 2). Post que nao passa
nao e gravado - fica listado para reclique. Nao ha palpite silencioso aqui: a v9 ja errou assim.

Uso:
    python3 qxrepair.py <dir>            # DRY-RUN: mostra o que faria, nao escreve
    python3 qxrepair.py <dir> --write    # grava, apos copiar o original para <dir>/pre-reparo/

O JSON reparado leva `metodo: 'reparo-offline'` e `reparado_em`, para que ninguem confunda corpo
recuperado com corpo capturado do DOM.
"""
import json, glob, os, re, sys, shutil, unicodedata
from datetime import datetime, timezone

RE_TEMPO = re.compile(r'^\d+\s*(min|h|d|w|mo|yr|s)\b.*•')
RE_FIM   = re.compile(r'^\d[\d.,]*\s*(reactions?|comments?|reposts?)$', re.I)
PULAR    = ('Follow', 'Connect', 'Following', '+ Follow', 'Message')

# O corpo nao termina exatamente na ancora: entre a ultima frase e a contagem de reacoes o
# LinkedIn ainda imprime rotulo de botao e o total de reacoes solto. Sem podar isso, o post
# terminava em "Activate to view larger image, / 61". Sao strings de UI e numero pelado -
# medidos nos 9 arquivos, nao imaginados.
LIXO = ('Activate to view larger image,', 'See content credentials', 'Show translation',
        'Comments', 'Reactions', 'Like', 'Comment', 'Share', 'Send', 'Repost', '…see more')
RE_SOLTO = re.compile(r'^(\d[\d.,]*|\+\d+)$')                 # 61, 349, +53
RE_OUTROS = re.compile(r'\band \d[\d.,]* others?$', re.I)      # "Rafael Passos and 348 others"
RE_BOTAO = re.compile(r'^(Connect|Follow|Message) with .+$')    # "Connect with Diego Pagano"


def eh_lixo(l):
    return (not l) or l in LIXO or RE_SOLTO.match(l) or RE_OUTROS.search(l) or RE_BOTAO.match(l)


def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', ' ', s)


def tokens_do_slug(url):
    m = re.search(r'/(?:posts|pulse)/([\w-]+)', url or '')
    if not m:
        return []
    s = re.sub(r'-(?:activity|ugcpost|share)-\d{6,}(?:-[\w-]{2,12})?$', '', m.group(1), flags=re.I)
    if '_' in s:
        s = s.split('_', 1)[1]
    return [t for t in norm(s).split()
            if len(t) > 2 and not t.isdigit() and t not in ('activity', 'ugcpost', 'share')]


def corta_corpo(linhas, inicio):
    """Do inicio ate a primeira ancora de fim (reacoes, ou o botao Like)."""
    fim = next((k for k in range(inicio, len(linhas)) if RE_FIM.match(linhas[k].strip())), None)
    if fim is None:
        fim = next((k for k in range(inicio, len(linhas)) if linhas[k].strip() == 'Like'), len(linhas))
    corte = [l.rstrip() for l in linhas[inicio:fim]]
    while corte and eh_lixo(corte[0].strip()):
        corte.pop(0)
    while corte and eh_lixo(corte[-1].strip()):
        corte.pop()
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(corte).strip())


def extrai_post(linhas):
    i = next((k for k, l in enumerate(linhas) if l.strip() == 'Feed post'), None)
    if i is None:
        return None
    autor, cargo, quando = linhas[i + 1].strip(), '', ''
    j = i + 2
    while j < len(linhas) and j < i + 8:
        l = linhas[j].strip()
        if RE_TEMPO.search(l):
            quando = l
            j += 1
            break
        if l and '•' not in l[:4]:
            cargo = l
        j += 1
    while j < len(linhas) and (not linhas[j].strip() or linhas[j].strip() in PULAR):
        j += 1
    return dict(autor=autor, autor_cargo=cargo, publicado=quando, texto=corta_corpo(linhas, j))


def extrai_artigo(linhas, titulo_pagina):
    """Artigo /pulse/: a ancora e a linha igual ao titulo da aba."""
    titulo = re.sub(r'\s*\|\s*LinkedIn\s*$', '', titulo_pagina or '').strip()
    if not titulo:
        return None
    i = next((k for k, l in enumerate(linhas) if l.strip() == titulo), None)
    if i is None:
        return None
    autor = linhas[i + 1].strip() if i + 1 < len(linhas) else ''
    cargo = linhas[i + 2].strip() if i + 2 < len(linhas) else ''
    quando = linhas[i + 3].strip() if i + 3 < len(linhas) else ''
    j = i + 4
    while j < len(linhas) and not linhas[j].strip():
        j += 1
    return dict(autor=autor, autor_cargo=cargo, publicado=quando, texto=corta_corpo(linhas, j))


def suja(texto):
    return any(m in texto for m in ('Skip to search', 'My Network', 'Profile viewers',
                                    'Post impressions', 'Keyboard shortcuts'))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    escrever = '--write' in sys.argv
    alvo = args[0] if args else 'linkedin'
    reparados, recusados, intactos = [], [], 0

    for f in sorted(glob.glob(os.path.join(alvo, '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        if not suja(d.get('texto', '')):
            intactos += 1
            continue
        linhas = d['texto'].split('\n')
        r = extrai_post(linhas) or extrai_artigo(linhas, d.get('titulo_pagina'))
        nome = os.path.basename(f)
        if not r or not r['texto']:
            recusados.append((nome, 'nao achei a ancora do corpo'))
            continue
        if suja(r['texto']):
            recusados.append((nome, 'o corpo extraido ainda tem navegacao'))
            continue
        tk = tokens_do_slug(d.get('url', ''))
        achados = sum(1 for t in tk if t in norm(r['texto']))
        if len(tk) < 2 or achados < max(2, len(tk) * 0.6):
            recusados.append((nome, 'slug nao confirma o corpo (%d/%d tokens)' % (achados, len(tk))))
            continue
        reparados.append((f, nome, d, r, achados, len(tk)))

    for _, nome, d, r, ok, tot in reparados:
        print('  REPARA %-52s %5d ch  slug %d/%d  autor=%r'
              % (nome[12:64], len(r['texto']), ok, tot, r['autor']))
    for nome, por in recusados:
        print('  RECUSA %-52s %s' % (nome[12:64], por))
    print('\n%d reparados, %d recusados, %d ja intactos' % (len(reparados), len(recusados), intactos))

    if not escrever:
        print('\nDRY-RUN - nada foi escrito. Repita com --write para gravar.')
        return 0

    bkp = os.path.join(alvo, 'pre-reparo')
    os.makedirs(bkp, exist_ok=True)
    for f, nome, d, r, _, _ in reparados:
        shutil.copy2(f, os.path.join(bkp, nome))
        d.update(r)
        d['metodo'] = 'reparo-offline'
        d['reparado_em'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        with open(f, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
    print('gravados %d; originais copiados para %s/' % (len(reparados), bkp))
    return 0


if __name__ == '__main__':
    sys.exit(main())
