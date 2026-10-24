#!/usr/bin/env python3
"""qxboard - dashboard read-only do pipeline. Serve o HTML e um snapshot JSON do disco.

    python3 tools/qxboard.py                 # http://127.0.0.1:8787
    python3 tools/qxboard.py --port 9000
    python3 tools/qxboard.py --once          # snapshot JSON no stdout, sem servidor

O navegador nao consegue listar `workdir/locks/` sozinho, e o estado do pipeline e DERIVADO
(runbook: status = todo - done - claim vivo), nunca armazenado. Entao quem varre o disco e
este processo; o JS so faz polling em /api/state.json e desenha.

NAO ESCREVE NADA. Nenhum arquivo e aberto em modo de escrita - nem em ledger/, nem em
workdir/. A regra append-only nao corre risco porque este tool nao tem caminho de escrita.

A regra dos 90 min e a leitura do control.conf sao importadas de qxnext/qxctl de proposito:
duas definicoes divergentes de "lock morto" seriam pior que nao ter dashboard.
"""
import argparse, csv, hashlib, html, importlib.util, json, mimetypes, os, re, sys, webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote, unquote

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / 'ledger'
LOCKS = ROOT / 'workdir' / 'locks'
AGENTDIR = ROOT / 'workdir' / 'agents'
POSTS = ROOT / 'workdir' / 'posts'
SOCIAL = POSTS / 'social'
HTML = Path(__file__).resolve().parent / 'qxboard.html'

CSVS = ('backlog.todo.csv', 'backlog.done.csv', 'backlog.wip.csv',
        'backlog.meta.csv', 'agents.log.csv', 'master.log.csv',
        'manifest.csv', 'curated.csv', 'social.done.csv')

# chave de sidecar: so `^[a-z_]+:` no inicio da linha conta como campo novo. Sem isso, uma
# continuacao de `angle:`/`note:` que contenha ':' viraria um campo fantasma.
META_KEY = re.compile(r'^([a-z_]{2,24}):(.*)$')

# `/meta/` e `/art/` so servem o que o qxid.sh podia ter gerado. Casar o id inteiro (e nao
# filtrar `..`) e o que garante que nenhum caminho montado pelo cliente escape de workdir/posts/.
ITEM_ID = re.compile(r'^QXB-[0-9a-f]{8}$')

HEARTBEAT_WARN_SEC = 15 * 60      # runbook: heartbeat a cada ~15 min em item longo
ACTIVE_SEC = 10 * 60              # evento no ledger ha menos que isso = agente de pe agora


def _load(name):
    """Importa um tool irmao por caminho (tools/ nao e pacote)."""
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


qxctl = _load('qxctl')
qxnext = _load('qxnext')
STALE_LOCK_SEC = qxnext.STALE_LOCK_SEC          # 90 min, a regra de reclaim do runbook

# ---------------------------------------------------------------- leitura

def rows(name):
    p = LEDGER / name
    if not p.exists():
        return []
    with open(p, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def ts_epoch(s):
    s = (s or '').strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def age(epoch, now):
    return None if epoch is None else max(0, int(now - epoch))


# ---------------------------------------------------------------- derivacao

def open_claims(now):
    """Replay do wip: claim/heartbeat abrem ou renovam, release/abandon/exit/reclaim fecham.

    O que sobra sao os claims vivos. Fonte de verdade para "quem esta trabalhando agora" -
    o lock e a exclusao mutua, nao o registro."""
    live = {}
    for r in rows('backlog.wip.csv'):
        item = (r.get('item_id') or '').strip()
        ev = (r.get('event') or '').strip()
        if not item or item == '-':
            continue
        if ev == 'claim':
            live[item] = {'item_id': item,
                          'agent_id': (r.get('agent_id') or '').strip(),
                          'stage': (r.get('stage') or '').strip(),
                          'claimed_at': (r.get('ts') or '').strip(),
                          'last_ts': (r.get('ts') or '').strip(),
                          'last_event': ev,
                          'note': (r.get('note') or '').strip()}
        elif ev == 'heartbeat' and item in live:
            live[item]['last_ts'] = (r.get('ts') or '').strip()
            live[item]['last_event'] = ev
            live[item]['note'] = (r.get('note') or '').strip()
        elif ev in ('release', 'abandon', 'exit', 'reclaim'):
            live.pop(item, None)
    for c in live.values():
        c['claim_age_s'] = age(ts_epoch(c['claimed_at']), now)
        c['idle_s'] = age(ts_epoch(c['last_ts']), now)
    return live


# O lock nao se chama sempre como o item: estagios que trabalham sobre item ja publicado usam
# prefixo proprio para nao bloquear WRITE/REVIEW (`sm-` no smedia, `rc-` no smedia-recut).
# Sem isto o painel mostrava "LOCK AUSENTE" para claim que TINHA lock - erro pior que nao mostrar,
# porque sugere protocolo violado onde nao ha.
LOCK_PREFIXOS = ('sm-', 'rc-')


def item_do_lock(nome):
    for p in LOCK_PREFIXOS:
        if nome.startswith(p):
            return nome[len(p):]
    return nome


def scan_locks(now):
    out = {}
    if not LOCKS.is_dir():
        return out
    for e in os.scandir(LOCKS):
        if e.name.startswith('.') or not e.is_dir():
            continue
        item = item_do_lock(e.name)
        out[item] = {'item_id': item, 'lock_name': e.name,
                     'age_s': max(0, int(now - e.stat().st_mtime))}
    return out


def scan_drafts(now):
    """workdir/agents/<agent>/<item>.md - rascunho antes do Drive (runbook L499)."""
    out = []
    if not AGENTDIR.is_dir():
        return out
    for d in sorted(os.scandir(AGENTDIR), key=lambda e: e.name):
        if d.name.startswith('.') or not d.is_dir():
            continue
        for f in sorted(os.scandir(d.path), key=lambda e: e.name):
            if not f.is_file() or f.name.startswith('.'):
                continue
            st = f.stat()
            out.append({'agent_id': d.name, 'item_id': Path(f.name).stem,
                        'bytes': st.st_size, 'age_s': max(0, int(now - st.st_mtime))})
    return out


def read_meta(path):
    """Sidecar `QXB-<id>-meta.txt`: um `chave: valor` por linha, ASCII, sem aninhamento.

    E o mesmo arquivo que sobe para o Drive ao lado do Doc, entao o que se le aqui e
    exatamente o que o QX-SMEDIA le - nenhuma segunda fonte de metadado do post."""
    out = {}
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return out
    for line in text.splitlines():
        m = META_KEY.match(line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def scan_posts(now, published, reviewed, social):
    """workdir/posts/<item>.md - a copia local do que ja virou Doc (calibracao 2026-08-23).

    O Drive e a fonte de verdade, mas nao e observavel daqui sem uma chamada de API por
    post. Entao o painel mostra o que esta em disco e cruza com o `done` do ledger: post
    sem linha `published` e copia que nunca chegou ao Drive (ou chegou sem registro), e
    `published` sem .md e post anterior a regra da copia local."""
    out = []
    if not POSTS.is_dir():
        return out, []
    seen = set()
    for f in sorted(os.scandir(POSTS), key=lambda e: e.name):
        if not f.is_file() or f.name.startswith('.') or not f.name.endswith('.md'):
            continue
        item = Path(f.name).stem
        seen.add(item)
        st = f.stat()
        meta = read_meta(POSTS / f'{item}-meta.txt')
        try:
            words = int(meta.get('words') or 0)
        except ValueError:
            words = 0
        pub_ts = (meta.get('published') or '').strip()
        out.append({
            'item_id': item,
            'title': meta.get('title', ''),
            'agent_id': meta.get('agent', ''),
            'category': meta.get('category', ''),
            'tags': meta.get('tags', ''),
            'url': meta.get('url', ''),
            'words': words,
            'bytes': st.st_size,
            'has_meta': bool(meta),
            'published_at': pub_ts,
            'published_age_s': age(ts_epoch(pub_ts), now),
            'file_age_s': max(0, int(now - st.st_mtime)),
            'in_done': item in published,
            'reviewed': item in reviewed,
            # o pacote do QX-SMEDIA so existe no Drive - nao ha copia local para servir de
            # /meta/, entao aqui o link e o proprio Doc, como ja acontece na coluna `item`
            'social': item in social,
            'social_url': (social.get(item) or {}).get('drive_url', ''),
            'social_art': (social.get(item) or {}).get('art_files', 0),
            # teto duro da calibracao de 2026-08-23: 850-1100 palavras
            'over_cap': words > 1100,
        })
    # mais recente primeiro; post sem `published` legivel cai para o mtime do arquivo
    out.sort(key=lambda p: (ts_epoch(p['published_at']) or (now - p['file_age_s'])), reverse=True)
    return out, sorted(published - seen)


def scan_social(now):
    """ledger/social.done.csv cruzado com workdir/posts/social/<item>/ - o pacote do QX-SMEDIA.

    O ledger registra o Doc (o texto de LinkedIn/Instagram); a arte, quando existe, cai na
    pasta do item. Pasta vazia nao e erro: e o estado normal logo depois do recut, com o
    texto entregue e a arte pendente. Linha repetida para o mesmo item e recut - vale a mais
    recente, e as anteriores viram a contagem `revisoes`."""
    by_item = {}
    for r in rows('social.done.csv'):
        item = (r.get('item_id') or '').strip()
        if not item:
            continue
        ts = (r.get('ts') or '').strip()
        prev = by_item.get(item)
        if prev and (ts_epoch(ts) or 0) < (ts_epoch(prev['ts']) or 0):
            prev['revisions'] += 1
            continue
        by_item[item] = {
            'item_id': item,
            'ts': ts,
            'agent_id': (r.get('agent_id') or '').strip(),
            'status': (r.get('status') or '').strip(),
            'platforms': [x for x in re.split(r'[;,]', r.get('platforms') or '') if x.strip()],
            'drive_url': (r.get('drive_url') or '').strip(),
            'title': (r.get('title_final') or '').strip(),
            'note': (r.get('note') or '').strip(),
            'revisions': (prev['revisions'] + 1) if prev else 1,
        }
    art = {}
    if SOCIAL.is_dir():
        for d in os.scandir(SOCIAL):
            if d.name.startswith('.') or not d.is_dir():
                continue
            files = [f for f in os.scandir(d.path) if f.is_file() and not f.name.startswith('.')]
            newest = max([f.stat().st_mtime for f in files], default=None)
            art[d.name] = {'files': len(files),
                           'age_s': None if newest is None else max(0, int(now - newest))}
    out = []
    for item, rec in by_item.items():
        a = art.get(item)
        rec['age_s'] = age(ts_epoch(rec['ts']), now)
        rec['art_dir'] = a is not None
        rec['art_files'] = a['files'] if a else 0
        rec['art_age_s'] = a['age_s'] if a else None
        out.append(rec)
    out.sort(key=lambda r: ts_epoch(r['ts']) or 0, reverse=True)
    # pasta de arte sem linha no ledger: arte sendo montada antes do recut, ou pacote que
    # nunca foi registrado - nos dois casos o painel precisa mostrar, nao esconder.
    return out, sorted(k for k in art if k not in by_item)


def fleet(conf, now):
    """Um registro por agente a partir do agents.log.csv: ultimo evento e ultima versao vista.

    `stale_config` = o agente confirmou uma config mais velha que a vigente, ou seja esta
    rodando com spec velha - exatamente o problema 1 que o qxctl existe para resolver."""
    cur = conf.get('config_version', '1')
    try:
        cur_n = int(cur)
    except ValueError:
        cur_n = 0
    seen = {}
    # o QX-PLAN tem log proprio (master.log.csv); sem juntar os dois ele aparece defasado,
    # porque os bumps recentes dele nao passam pelo agents.log da frota.
    log = sorted(rows('agents.log.csv') + rows('master.log.csv'),
                 key=lambda r: (r.get('ts') or ''))
    for r in log:
        a = (r.get('agent_id') or '').strip()
        if not a:
            continue
        ver = (r.get('config_version') or '').strip()
        s = seen.setdefault(a, {'agent_id': a, 'stage': '', 'last_event': '', 'last_ts': '',
                                'version': '', 'events': 0, 'note': ''})
        s['stage'] = (r.get('stage') or '').strip() or s['stage']
        s['last_event'] = (r.get('event') or '').strip()
        s['last_ts'] = (r.get('ts') or '').strip()
        s['note'] = (r.get('note') or '').strip()
        s['events'] += 1
        if ver:
            s['version'] = ver
    out = []
    for s in seen.values():
        try:
            vn = int(s['version'])
        except ValueError:
            vn = -1
        s['stale_config'] = s['last_event'] != 'exit' and 0 <= vn < cur_n
        s['exited'] = s['last_event'] == 'exit'
        s['idle_s'] = age(ts_epoch(s['last_ts']), now)
        # de pe agora: escreveu no ledger ha pouco e nao registrou exit. Um agente pode estar
        # ativo sem claim aberto - orientando, entre itens, ou num estagio que nao reivindica.
        s['active'] = not s['exited'] and s['idle_s'] is not None and s['idle_s'] < ACTIVE_SEC
        out.append(s)
    out.sort(key=lambda s: (s['exited'], s['idle_s'] if s['idle_s'] is not None else 1 << 40))
    return out


def counts():
    todo, done_pub, done_rev = set(), set(), set()
    for r in rows('backlog.todo.csv'):
        i = (r.get('id') or '').strip()
        if i:
            todo.add(i)
    for r in rows('backlog.done.csv'):
        i = (r.get('item_id') or '').strip()
        st = (r.get('status') or '').strip()
        if not i:
            continue
        if st == 'published':
            done_pub.add(i)
        elif st == 'reviewed':
            done_rev.add(i)
    return {'todo': len(todo), 'published': len(done_pub), 'reviewed': len(done_rev),
            'write_queue': len(todo - done_pub), 'review_queue': len(done_pub - done_rev)}, done_pub, done_rev


def social_map(social):
    return {r['item_id']: r for r in social}


def snapshot():
    now = datetime.now(timezone.utc).timestamp()
    conf = qxctl.read()
    claims = open_claims(now)
    locks = scan_locks(now)
    cnt, published, reviewed = counts()
    social, orphan_art = scan_social(now)
    posts, missing_local = scan_posts(now, published, reviewed, social_map(social))
    cnt['posts_local'] = len(posts)
    seen = {p['item_id'] for p in posts}
    for r in social:
        r['has_post'] = r['item_id'] in seen
    cnt['social'] = len(social)
    cnt['social_art_pending'] = sum(1 for r in social if not r['art_files'])
    # Fila do QX-SMEDIA: ate 2026-08-24 o painel so mostrava o que o smedia JA entregou
    # (`social`), nunca o que falta - trabalho pendente invisivel. A fila vem do proprio
    # qxnext.candidates para nao existir uma segunda definicao de fila que possa divergir.
    cnt['smedia_queue'] = len(qxnext.candidates('smedia'))
    cnt['recut_queue'] = len(qxnext.candidates('smedia-recut'))
    # Feito e fila do MESMO qxnext de proposito: um estagio com duas definicoes de 'pronto'
    # acaba com o painel dizendo zero enquanto o agente ainda tem trabalho.
    cnt['smedia_done'] = len(qxnext.done_status('smedia'))
    cnt['recut_done'] = len(qxnext.done_status('smedia-recut'))

    live = []
    for item, c in claims.items():
        lk = locks.get(item)
        c = dict(c)
        c['has_lock'] = lk is not None
        c['lock_age_s'] = lk['age_s'] if lk else None
        # a idade que importa para o reclaim e a do lock; sem lock, a do ultimo evento
        ref = c['lock_age_s'] if c['lock_age_s'] is not None else c['idle_s']
        c['reclaimable'] = ref is not None and ref >= STALE_LOCK_SEC
        c['already_published'] = item in published
        live.append(c)
    live.sort(key=lambda c: -(c['idle_s'] or 0))

    orphan_locks = [dict(l, reclaimable=l['age_s'] >= STALE_LOCK_SEC)
                    for k, l in sorted(locks.items()) if k not in claims]
    unlocked_claims = [c['item_id'] for c in live if not c['has_lock']]

    stage_state = {}
    for s in qxctl.STAGES:
        ov = (conf.get(f'stage.{s}') or '').strip()
        stage_state[s] = {'effective': ov or conf.get('state', 'run'), 'override': ov}

    return {
        'now': datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'root': str(ROOT),
        'fp': fingerprint(),
        'ui': ui_stamp(),
        'thresholds': {'stale_lock_s': STALE_LOCK_SEC, 'heartbeat_warn_s': HEARTBEAT_WARN_SEC,
                       'active_s': ACTIVE_SEC},
        'control': {'state': conf.get('state', 'run'),
                    'config_version': conf.get('config_version', ''),
                    'reason': conf.get('reason', ''), 'note': conf.get('note', ''),
                    'updated_at': conf.get('updated_at', ''), 'updated_by': conf.get('updated_by', ''),
                    'updated_age_s': age(ts_epoch(conf.get('updated_at')), now),
                    'stages': stage_state},
        'counts': cnt,
        'live': live,
        'fleet': fleet(conf, now),
        'locks': {'total': len(locks), 'orphans': orphan_locks, 'unlocked_claims': unlocked_claims},
        'drafts': scan_drafts(now),
        'posts': posts,
        'posts_missing_local': missing_local,
        'social': social,
        'social_orphan_art': orphan_art,
    }


def ui_stamp():
    """mtime+tamanho do proprio qxboard.html. O poll so busca JSON, entao editar o HTML nunca
    chegava a uma aba ja aberta: ela seguia rodando o JS antigo contra o snapshot novo -
    coluna que sumiu, link que virou pilula morta. Com o stamp no snapshot, a aba se recarrega."""
    try:
        st = HTML.stat()
        return f'{st.st_mtime_ns}:{st.st_size}'
    except OSError:
        return ''


def fingerprint():
    """Barato o bastante para rodar a cada poll: (mtime, size) dos CSVs + estado dos diretorios."""
    parts = []
    parts.append(f'ui:{ui_stamp()}')       # HTML editado forca snapshot, e a aba recarrega
    for name in CSVS + ('../control.conf',):
        p = (LEDGER / name).resolve()
        try:
            st = p.stat()
            parts.append(f'{p.name}:{st.st_mtime_ns}:{st.st_size}')
        except OSError:
            parts.append(f'{p.name}:-')
    for base in (LOCKS, AGENTDIR, POSTS):
        try:
            for e in sorted(os.scandir(base), key=lambda e: e.name):
                if e.name.startswith('.'):
                    continue
                st = e.stat()
                # em POSTS o que muda e o conteudo do arquivo, entao o tamanho entra junto -
                # reescrever um post do mesmo tamanho ja mexeria no mtime, mas o par e barato.
                parts.append(f'{base.name}/{e.name}:{st.st_mtime_ns}'
                             + (f':{st.st_size}' if base is POSTS else ''))
                # descer um nivel em workdir/agents/<agente>/: reescrever um rascunho ja
                # existente nao mexe no mtime do diretorio pai, so no do arquivo.
                if base is AGENTDIR and e.is_dir():
                    for f in sorted(os.scandir(e.path), key=lambda x: x.name):
                        if not f.name.startswith('.'):
                            st = f.stat()
                            parts.append(f'{e.name}/{f.name}:{st.st_mtime_ns}:{st.st_size}')
        except OSError:
            pass
    # a arte do social fica dois niveis abaixo de POSTS (social/<item>/<arquivo>): sem descer
    # ate ela, um PNG que chega nao mexe no mtime de nada que o loop acima observa.
    try:
        for d in sorted(os.scandir(SOCIAL), key=lambda e: e.name):
            if d.name.startswith('.') or not d.is_dir():
                continue
            for f in sorted(os.scandir(d.path), key=lambda x: x.name):
                if not f.name.startswith('.'):
                    st = f.stat()
                    parts.append(f'social/{d.name}/{f.name}:{st.st_mtime_ns}:{st.st_size}')
    except OSError:
        pass
    # hash() de str e randomizado por processo; blake2b mantem o fp estavel
    # entre reinicios, entao trocar de servidor nao forca um re-render inutil.
    return hashlib.blake2b('|'.join(parts).encode('utf-8'), digest_size=8).hexdigest()


# ---------------------------------------------------------------- arte do social

# so estes tipos sao servidos inline; qualquer outra extensao vira download, para a pasta
# de arte nunca virar um caminho para servir .html/.js a partir do painel.
ART_INLINE = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.mp4', '.webm',
              '.pdf', '.txt', '.md'}


def art_listing(item):
    """Indice HTML de workdir/posts/social/<item>/ - a pasta da arte do pacote.

    O navegador bloqueia `file://` a partir de uma pagina http, entao o link da coluna
    `item` nao consegue abrir a pasta no Finder: o painel serve a propria listagem. Leitura,
    nunca escrita, igual ao `/meta/`."""
    d = SOCIAL / item
    esc = html.escape
    head = ('<!doctype html><meta charset="utf-8">'
            f'<title>arte {esc(item)}</title>'
            '<style>body{background:#0e1116;color:#d8dee9;font:14px/1.5 ui-sans-serif,system-ui,'
            'sans-serif;margin:24px}a{color:#8ab4f8}h1{font-size:16px;margin:0 0 4px}'
            'code{color:#9aa5b1;font:12px ui-monospace,monospace;word-break:break-all}'
            'ul{list-style:none;padding:0}li{padding:6px 0;border-bottom:1px solid #222836}'
            '.s{color:#7c8798;font-size:12px}img,video{max-width:320px;max-height:220px;'
            'display:block;margin:6px 0;border-radius:6px;background:#181d26}</style>'
            f'<h1>arte de {esc(item)}</h1><p><code>{esc(str(d))}</code></p>')
    if not d.is_dir():
        return 404, (head + '<p>pasta ainda nao existe: arte pendente no pacote.</p>'
                     ).encode('utf-8')
    files = sorted((f for f in os.scandir(d) if f.is_file() and not f.name.startswith('.')),
                   key=lambda f: f.name)
    if not files:
        return 200, (head + '<p>pasta vazia: o recut saiu, a arte nao chegou.</p>').encode('utf-8')
    out = [head, '<ul>']
    for f in files:
        href = f'/art/{item}/{quote(f.name)}'
        ext = os.path.splitext(f.name)[1].lower()
        st = f.stat()
        prev = ''
        if ext in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'):
            prev = f'<img src="{href}" alt="{esc(f.name)}">'
        elif ext in ('.mp4', '.webm'):
            prev = f'<video src="{href}" controls></video>'
        out.append(f'<li><a href="{href}">{esc(f.name)}</a> '
                   f'<span class="s">{st.st_size // 1024 or 1} KB</span>{prev}</li>')
    out.append('</ul>')
    return 200, ''.join(out).encode('utf-8')


def art_file(item, name):
    """Um arquivo da pasta de arte. O nome tem que bater com uma entrada real do scandir -
    e isso, e nao um filtro de `..`, que fecha o caminho para fora de workdir/posts/."""
    d = SOCIAL / item
    if not d.is_dir():
        return 404, b'pasta de arte nao encontrada', 'text/plain; charset=utf-8'
    if name not in {f.name for f in os.scandir(d) if f.is_file() and not f.name.startswith('.')}:
        return 404, b'arquivo nao encontrado na pasta de arte', 'text/plain; charset=utf-8'
    ext = os.path.splitext(name)[1].lower()
    ctype = (mimetypes.guess_type(name)[0] or 'application/octet-stream') \
        if ext in ART_INLINE else 'application/octet-stream'
    try:
        return 200, (d / name).read_bytes(), ctype
    except OSError:
        return 404, b'arquivo ilegivel', 'text/plain; charset=utf-8'


# ---------------------------------------------------------------- servidor

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ('/', '/index.html'):
            try:
                self._send(200, HTML.read_bytes(), 'text/html; charset=utf-8')
            except OSError:
                self._send(500, b'qxboard.html nao encontrado ao lado de qxboard.py', 'text/plain')
        elif u.path == '/api/state.json':
            want = (parse_qs(u.query).get('fp') or [''])[0]
            fp = fingerprint()
            data = {'unchanged': True, 'fp': fp} if want and want == fp else snapshot()
            self._send(200, json.dumps(data, ensure_ascii=False).encode('utf-8'),
                       'application/json; charset=utf-8')
        elif u.path.startswith('/art/'):
            # a coluna `item` da tabela Social aponta para ca: a pasta da arte do pacote.
            rest = unquote(u.path[len('/art/'):])
            item, _, name = rest.partition('/')
            if not ITEM_ID.match(item):
                self._send(400, b'id de item invalido', 'text/plain; charset=utf-8')
                return
            if name:
                code, body, ctype = art_file(item, name)
            else:
                code, body = art_listing(item)
                ctype = 'text/html; charset=utf-8'
            self._send(code, body, ctype)
        elif u.path.startswith('/meta/'):
            # o sidecar e texto plano em disco; servir daqui evita o file:// que o navegador
            # bloqueia a partir de uma pagina http. Leitura, nunca escrita.
            item = u.path[len('/meta/'):]
            if item.endswith('.txt'):
                item = item[:-4]
            src = POSTS / f'{item}-meta.txt'
            if not ITEM_ID.match(item):
                self._send(400, b'id de item invalido', 'text/plain; charset=utf-8')
                return
            try:
                body = src.read_bytes()
            except OSError:
                self._send(404, b'sidecar -meta.txt nao encontrado', 'text/plain; charset=utf-8')
                return
            self._send(200, body, 'text/plain; charset=utf-8')
        else:
            self._send(404, b'404', 'text/plain')

    def log_message(self, *a):
        pass                                  # sem ruido no terminal do agente


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--port', type=int, default=8787)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--once', action='store_true', help='imprime o snapshot JSON e sai')
    ap.add_argument('--no-open', action='store_true', help='nao abre o navegador')
    a = ap.parse_args()

    if a.once:
        json.dump(snapshot(), sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    url = f'http://{a.host}:{a.port}/'
    print(f'qxboard read-only em {url}   (ROOT={ROOT})\nctrl-c para sair')
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
