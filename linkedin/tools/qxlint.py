#!/usr/bin/env python3
"""Verifica as invariantes do ledger do pipeline. Roda em segundos, sem tocar em nada.

  python3 tools/qxlint.py            # relatorio completo
  python3 tools/qxlint.py --quiet    # so violacoes; exit 1 se houver

QUEM RODA:
  - todo agente ANTES DE ENCERRAR, para nao deixar defeito para tras;
  - o QX-PLAN sempre que quiser saber a saude do pipeline;
  - o QX-REVIEW como parte do check de metadados.

Existe porque um defeito real passou despercebido: 25 itens de backlog ficaram sem linha de
metadados por quase uma hora, e ninguem notou ate uma conferencia manual.
"""
import csv, io, os, re, sys, pathlib
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parent.parent
V, INFO = [], []
def bad(inv, msg): V.append(f'[{inv}] {msg}')
def info(msg): INFO.append(msg)

def rows(name):
    p = R / 'ledger' / name
    return list(csv.DictReader(open(p, encoding='utf-8'))) if p.exists() else []

backlog = rows('backlog.todo.csv')
meta    = rows('backlog.meta.csv')
done    = rows('backlog.done.csv')
wip     = rows('backlog.wip.csv')
log     = rows('agents.log.csv') + rows('master.log.csv')

# INV0 - estrutura antes de conteudo. Linha com numero de campos errado envenena toda leitura
# seguinte: ate 2026-08-23 ela derrubava o proprio lint com TypeError, ou seja, a ferramenta
# morria exatamente no caso que ela existe para detectar. Reportar vem primeiro.
for _n in ('backlog.todo.csv', 'backlog.meta.csv', 'backlog.done.csv', 'backlog.wip.csv',
           'social.done.csv', 'manifest.csv', 'curated.csv'):
    _p = R / 'ledger' / _n
    if not _p.exists(): continue
    _ls = _p.read_text(encoding='utf-8').splitlines()
    if not _ls: continue
    _esp = len(next(csv.reader(io.StringIO(_ls[0])), []))
    for _i, _l in enumerate(_ls[1:], 2):
        if not _l.strip(): continue
        if len(next(csv.reader(io.StringIO(_l)), [])) != _esp:
            # Linha quebrada nao pode ser encurtada num arquivo append-only. O que importa e se
            # ela levou DADO junto: se todo item citado nela tem uma linha integra em outro
            # lugar, o conteudo foi recuperado e isto vira historico. Se falta algum, ai sim ha
            # perda, e o conserto e obvio - reescrever a linha daquele item por append.
            _itens = set(re.findall(r'QXB-[0-9a-f]{8}', _l))
            _ok = {i for i in _itens
                   if any(len(next(csv.reader(io.StringIO(x)), [])) == _esp and i in x
                          for x in _ls[1:])}
            _perdidos = sorted(_itens - _ok)
            if _perdidos:
                bad('INV0', f'{_n}:{_i} linha quebrada e {_perdidos} nao tem linha integra em '
                            f'lugar nenhum - reescreva por append')
            else:
                info(f'{_n}:{_i} linha quebrada (interleaving), mas todo item dela tem linha '
                     f'integra em outro lugar: {sorted(_itens)} - historico, nao consertavel')

ids   = {r['id'] for r in backlog if r.get('id')}
mids  = [r['id'] for r in meta if r.get('id')]
pub   = {}
for r in done:
    if r.get('status') == 'published' and r.get('item_id'): pub[r['item_id']] = r    # linha mais recente vence

# --- vocabulario controlado, lido do tags.md (fonte unica) ---
vocab, RETIRED = {}, set()
tg = (R / '.claude/memory/tags.md')
if tg.exists():
    t = tg.read_text()
    def sect(h, stop='\n## '):
        i = t.find(h)
        if i < 0: return ''
        j = t.find(stop, i + 5)
        return t[i:j if j > 0 else len(t)]
    for key, head in (('tags', '## `tags`'), ('instruments', '## `instruments`'),
                      ('funnel', '## `funnel`'), ('format', '## `format`'),
                      ('claim_flags', '## `claim_flags`')):
        s = sect(head)
        got = set(re.findall(r'`([a-z0-9][a-z0-9\-]*)`', s))
        got -= {'backlog', 'csv', 'notes', 'related', 'id'}
        # os aposentados aparecem no texto como proibidos: nao entram no vocabulario
        vocab[key] = got
    RETIRED.update(re.findall(r'`([a-z0-9\-]+)`',
                   ''.join(re.findall(r'\*\*Aposentados[^*]*\*\*(.*?)(?=\n## |\Z)', t, re.S))))

# INV1 - todo item tem metadados
falta = ids - set(mids)
if falta: bad('INV1', f'{len(falta)} itens sem linha em backlog.meta.csv: {sorted(falta)[:6]}...')

# INV2 - meta orfa / duplicada
orfa = set(mids) - ids
if orfa: bad('INV2', f'meta.csv referencia id que nao existe no backlog: {sorted(orfa)}')
# Duas linhas para o mesmo id NAO sao defeito: o arquivo e append-only, entao a unica forma de
# corrigir uma linha errada e acrescentar a versao nova - vale a MAIS RECENTE. Defeito e o
# double-write: duas linhas com conteudo identico, onde a segunda nao corrige nada.
_by_id = {}
for r in meta:
    if r.get('id'): _by_id.setdefault(r['id'], []).append(r)
_ident, _corr = [], []
for i, v in _by_id.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r.get('ts') or '')
    a, b = v[-2], v[-1]
    (_ident if all(a[k] == b[k] for k in a if k not in ('ts', 'agent_id')) else _corr).append(i)
if _ident:
    bad('INV2', f'{len(_ident)} ids com linha REPETIDA identica em meta.csv (o segundo write nao '
                f'corrige nada - dois agentes escrevendo a mesma linha): {sorted(_ident)[:5]}...')
if _corr:
    info(f'{len(_corr)} ids com meta corrigida por append (esperado; vale a mais recente)')

# INV3 - publicado fora do backlog
fora = set(pub) - ids
if fora: bad('INV3', f'publicado sem item de backlog: {sorted(fora)}')

# INV4 - teto de palavras
CAP = 1100
over = {i: r.get('word_count') for i, r in pub.items()
        if (r.get('word_count') or '0').isdigit() and int(r.get('word_count') or 0) > CAP}
if over: bad('INV4', f'publicados acima de {CAP} palavras: {over}')

# INV5 - doc_id duplicado
seen = {}
for i, r in pub.items():
    d = r.get('drive_file_id', '')
    if d and d in seen: bad('INV5', f'doc_id {d} usado por {seen[d]} e {i}')
    seen[d] = i

legacy = set()
# INV6/INV7 olham a linha EFETIVA de cada id (a mais recente). Validar o historico inteiro
# tornaria a violacao inconsertavel: num ledger append-only, corrigir e acrescentar.
meta_eff = list({r['id']: r for r in sorted(meta, key=lambda x: x.get('ts') or '') if r.get('id')}.values())

# INV6 - vocabulario
for r in meta_eff:
    for col in ('tags', 'instruments', 'funnel', 'format', 'claim_flags'):
        if not vocab.get(col): continue
        for v in (x.strip() for x in (r.get(col) or '').split(';') if x.strip()):
            if v in RETIRED:
                legacy.add(v)                      # valor aposentado em linha antiga: historico, nao defeito
            elif v not in vocab[col]:
                bad('INV6', f"{r['id']}: {col}='{v}' fora do vocabulario de tags.md")

if legacy: info(f'valores aposentados em linhas antigas (esperado, append-only): {sorted(legacy)}')

# INV7 - related
for r in meta_eff:
    for v in (x.strip() for x in (r.get('related') or '').split(';') if x.strip()):
        if v == r['id']: bad('INV7', f"{r['id']}: related aponta para si mesmo")
        elif v not in ids: bad('INV7', f"{r['id']}: related={v} nao existe no backlog")

# INV8 - AGENTE FANTASMA: escreve nos ledgers mas nunca fez check-in no control plane
escreve = {r.get('created_by') for r in backlog} | {r.get('agent_id') for r in wip + meta} \
          | {r.get('agent_id') for r in done}
escreve = {a for a in escreve if a and a not in ('-', 'QX-PLAN')}
checkin = {r.get('agent_id') for r in log}
fantasma = escreve - checkin
# INV8 existe para uma pergunta operacional: "ha alguem trabalhando sem receber pause/stop?".
# Duas condicoes, e as duas precisam valer:
#   1. escreveu recentemente (fantasma parado ja morreu, e nada o alcanca de qualquer forma);
#   2. ha sinal de TRABALHO - claim em aberto, lock, ou linha em todo/meta/done.
# Sem a condicao 2 o check acusa rastro incoerente como se fosse agente ativo: em 2026-08-23 duas
# linhas caidas no ledger por erro de shell numa demo (`cd x && cmd &` - o `&` joga o `cd` no
# subshell) deixaram o lint vermelho para a frota inteira, sem nada rodando. Rastro sem claim nao
# e agente em operacao: e sujeira, e vira info.
if fantasma:
    _last, _trabalho = {}, set()
    for r in backlog:
        a = r.get('created_by'); _last[a] = max(_last.get(a, ''), r.get('created_at') or '')
        _trabalho.add(a)
    for r in meta + done:
        a = r.get('agent_id'); _last[a] = max(_last.get(a, ''), r.get('ts') or '')
        _trabalho.add(a)
    _abertos = {}
    for r in wip:
        a = r.get('agent_id'); _last[a] = max(_last.get(a, ''), r.get('ts') or '')
        k = (a, r.get('item_id'))
        ev = (r.get('event') or '').strip()
        if ev == 'claim': _abertos[k] = True
        elif ev in ('release', 'reclaim'): _abertos.pop(k, None)
    _trabalho |= {a for (a, _), v in _abertos.items() if v}
    _corte = datetime.now(timezone.utc).timestamp() - 90 * 60
    def _recente(a):
        t = _last.get(a) or ''
        try: return datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp() > _corte
        except ValueError: return True
    vivos = sorted(a for a in fantasma if _recente(a) and a in _trabalho)
    rastro = sorted(a for a in fantasma if _recente(a) and a not in _trabalho)
    mortos = sorted(a for a in fantasma if not _recente(a))
    if vivos:
        bad('INV8', f'AGENTE FANTASMA ATIVO (trabalha e nunca chamou qxctl check): {vivos} '
                    f'-> nao recebe pause nem reload; so para se for morto e relancado')
    if rastro:
        info(f'rastro de agente sem claim nem lock (sujeira, nao operacao): {rastro}')
    if mortos:
        info(f'fantasmas historicos, ja parados (sem acao possivel): {mortos}')

# INV8b - SESSAO fantasma: o agente existe no log, mas esta trabalhando SEM ter feito check-in
# nesta sessao. Detectado comparando o claim mais recente com o ultimo evento de control plane
# do mesmo agente. Em 2026-08-23 sm1 e sm2 entregaram recut por 3 minutos com o ultimo evento
# sendo `exit` - o INV8 nao viu porque so pergunta se o id ja apareceu no log alguma vez.
_ult_log = {}
for r in log:
    a = r.get('agent_id')
    if a: _ult_log[a] = max(_ult_log.get(a, ''), r.get('ts') or '')
_ult_claim, _abertos2 = {}, {}
for r in sorted(wip, key=lambda x: x.get('ts') or ''):
    a, i, ev = r.get('agent_id'), r.get('item_id'), (r.get('event') or '').strip()
    if not a: continue
    if ev == 'claim':
        _abertos2[(a, i)] = r.get('ts') or ''
        _ult_claim[a] = max(_ult_claim.get(a, ''), r.get('ts') or '')
    elif ev in ('release', 'reclaim'):
        _abertos2.pop((a, i), None)
_mudos = sorted({a for (a, _) in _abertos2
                 if _ult_claim.get(a, '') > _ult_log.get(a, '')})
if _mudos:
    bad('INV8b', f'agente com claim ABERTO e sem check-in nesta sessao: {_mudos} - reivindicou '
                 f'depois do ultimo evento de control plane, entao nao recebe pause/stop nem reload')

# INV13 - registro de artefatos: todo caminho declarado, todo declarado existente.
#          Existe porque workdir/agents/ ficou 12h no repo sem proposito conhecido: o session-log
#          guarda decisao, nao inventario. Vale nos DOIS sentidos - orfao e entrada morta.
_reg = R / 'ledger' / 'artifacts.csv'
if _reg.exists():
    # Vale a linha MAIS RECENTE de cada path, como em todo o ledger - e `dono=-` RETRATA a
    # declaracao. Ate 2026-08-25 aqui havia um set de todas as linhas: o comentario prometia
    # supersessao que o codigo nao fazia. Consequencia: uma linha errada num arquivo
    # append-only travava a frota para sempre, porque nao existia linha nova capaz de supera-la
    # e o agente ficava entre nao poder editar e nao poder sair com lint sujo (foi o que
    # aconteceu com o w12, que apagou a linha - a saida menos ruim que ele tinha).
    # Retratar: append de `<ts>,<agente>,<path>,-,"motivo"`. O lint so acusa o que da para consertar.
    _ultimo = {}
    for r in rows('artifacts.csv'):
        _pth = (r.get('path') or '').strip()
        if _pth:
            _ultimo[_pth] = (r.get('dono') or '').strip()
    _decl = {p for p, dono in _ultimo.items() if dono != '-'}
    _achado = set()
    for _p in R.iterdir():                                   # raiz
        # captura de tela e afins que o usuario larga na raiz nao sao artefato de pipeline
        if _p.name.startswith('.'): continue
        # captura de tela e pagina salva pelo navegador: material que o usuario larga para
        # o agente olhar, nao artefato de pipeline
        if _p.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.mov', '.mp4',
                                 '.mhtml', '.webarchive'): continue
        if _p.name.startswith('qx-linkedin-') and _p.suffix == '.json': continue   # captura do bookmarklet, consumida por qxinbox
        _achado.add(_p.name + ('/' if _p.is_dir() else ''))
    for _d in ('ledger', 'tools'):                           # arquivos de dentro
        if (R / _d).is_dir():
            _achado |= {f'{_d}/{x.name}' for x in (R / _d).iterdir() if x.is_file()
                        and x.name not in ('.gitkeep', '.DS_Store')}
    if (R / 'workdir').is_dir():                             # so um nivel de dir
        for _x in (R / 'workdir').iterdir():
            if _x.is_dir():
                _achado.add(f'workdir/{_x.name}/')
                if _x.name == 'harvest':
                    _achado.discard('workdir/harvest/')
                    _achado |= {f'workdir/harvest/{y.name}/' for y in _x.iterdir() if y.is_dir()}
    _achado = {a for a in _achado if a not in ('.gitkeep', '.DS_Store')}
    _orfao = sorted(_achado - _decl)
    _morta = sorted(d for d in _decl if not (R / d.rstrip('/')).exists())
    if _orfao:
        bad('INV13', f'caminho sem linha em ledger/artifacts.csv: {_orfao} '
                     f'-> declare proposito e dono, ou remova')
    if _morta:
        bad('INV13', f'ledger/artifacts.csv declara caminho que nao existe mais: {_morta}')

# INV12 - runbook.md e ASCII puro (ele descreve a regra de charset; nao pode viola-la,
#          e caractere ornamental nele vira ornamento copiado para dentro dos posts)
_rb = R / 'runbook.md'
if _rb.exists():
    _mau = sorted({c for c in _rb.read_text(encoding='utf-8') if ord(c) > 127})
    if _mau:
        bad('INV12', 'runbook.md tem nao-ASCII: ' +
                     ', '.join(f'U+{ord(c):04X}' for c in _mau[:8]))

# INV9 - linha longa / quebrada
cabecalhos = {}
for _n in ('backlog.todo.csv', 'backlog.meta.csv', 'backlog.done.csv', 'backlog.wip.csv',
           'agents.log.csv', 'master.log.csv', 'manifest.csv', 'curated.csv', 'social.done.csv'):
    _p = R / 'ledger' / _n
    if _p.exists():
        cabecalhos[_n] = next(csv.reader(io.StringIO(_p.read_text(encoding='utf-8').splitlines()[0])), [])

for name in ('backlog.todo.csv', 'backlog.meta.csv', 'backlog.done.csv', 'backlog.wip.csv',
             'agents.log.csv', 'master.log.csv', 'manifest.csv', 'curated.csv',
             'social.done.csv'):
    p = R / 'ledger' / name
    if not p.exists(): continue
    for n, ln in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if len(ln.encode()) > 1024:
            # O teto de 1KB protege contra INTERLEAVING no momento do append. Linha ja escrita e
            # integra nao tem como ser encurtada num arquivo append-only: virar violacao aqui seria
            # deixar a frota inteira com um alerta que ninguem consegue apagar. Violacao e a linha
            # QUEBRADA - que e o dano que o teto existe para evitar.
            _campos = len(next(csv.reader(io.StringIO(ln)), []))
            _esperado = len(cabecalhos.get(name, []))
            _nota = ln.split('"')[-2] if ln.count('"') >= 2 else ''
            if _esperado and _campos != _esperado:
                bad('INV9', f'{name}:{n} linha com {len(ln.encode())} bytes e {_campos} campos '
                            f'(esperado {_esperado}) - linha quebrada')
            else:
                info(f'{name}:{n} linha com {len(ln.encode())} bytes (>1KB) mas integra; '
                     f'nota tem {len(_nota.encode())}B, cap e 400 - historico, nao consertavel')

# INV10 - lock orfao
locks = R / 'workdir/locks'
if locks.exists():
    now = datetime.now(timezone.utc).timestamp()
    for d in locks.iterdir():
        if d.is_dir():
            idade = (now - d.stat().st_mtime) / 60
            if idade > 90: bad('INV10', f'lock orfao ha {idade:.0f} min: {d.name}')
            else: info(f'lock ativo ({idade:.0f} min): {d.name}')

info(f'{len(backlog)} itens | {len(pub)} publicados | {len(ids)-len(pub)} pendentes | {len(meta)} linhas de meta')
if pub:
    w = [int(r['word_count']) for r in pub.values()
         if (r.get('word_count') or '').isdigit()]
    if w: info(f'palavras: {min(w)}-{max(w)} (media {sum(w)//len(w)})')
info(f'agentes com check-in: {" ".join(sorted(checkin - {None}))}')

quiet = '--quiet' in sys.argv
if not quiet:
    for i in INFO: print('  .', i)
if V:
    print(f'\n{len(V)} VIOLACAO(OES):')
    for v in V: print('  x', v)
    sys.exit(1)
print('\nledger integro.' if not quiet else '')
