#!/usr/bin/env python3
"""qxnext - pega o proximo item da fila e RECLAMA o lock, esperando se a fila estiver vazia.

Existe por causa do buraco de 2026-08-23: os writers drenaram a fila as 07:23 e encerraram;
o QX-CURATE entregou 25 itens novos as 07:28 e nao havia mais ninguem para consumir.
Fila vazia num instante nao significa trabalho terminado - significa que o estagio anterior
ainda nao entregou. Este comando espera; o agente nunca decide sozinho que acabou.

    python3 tools/qxnext.py --agent w1 --stage write --version 6

Exit codes:
     0  item reclamado (dados em stdout, uma chave por linha)
    10  pause  (control plane)   -> encerre depois de soltar o que estiver na mao
    20  stop   (control plane)   -> idem
    30  fila seca por --wait segundos inteiros -> SO AQUI o agente pode encerrar
    40  config mudou -> releia os arquivos listados e chame de novo

Nao escreve backlog.done.csv. Ordem obrigatoria continua com o agente:
done row -> rmdir do lock -> release no wip.
"""
import argparse, csv, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / 'ledger' / 'backlog.todo.csv'
DONE    = ROOT / 'ledger' / 'backlog.done.csv'
SOCIAL  = ROOT / 'ledger' / 'social.done.csv'
WIP     = ROOT / 'ledger' / 'backlog.wip.csv'
LOCKS   = ROOT / 'workdir' / 'locks'
QXCTL   = ROOT / 'tools' / 'qxctl.py'

PRIO = {'P1': 0, 'P2': 1, 'P3': 2}
STALE_LOCK_SEC = 90 * 60          # regra do runbook: 90 min sem evento e sem done

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def wip_append(agent, stage, item, event, note=''):
    note = note.replace('"', "'").replace('\n', ' ')[:200]
    with open(WIP, 'a') as f:
        f.write(f'{now()},{agent},{stage},{item},{event},"{note}"\n')

def read_rows(path):
    if not path.exists():
        return []
    with open(path, newline='') as f:
        return [r for r in csv.DictReader(f) if r.get('id') or r.get('item_id')]

def done_status(stage):
    """ids ja terminados NESTE estagio."""
    if stage == 'smedia':                      # ledger proprio: um item, um Doc social
        return {(r.get('item_id') or '').strip() for r in read_rows(SOCIAL)
                if (r.get('status') or '').strip() == 'published'}
    if stage == 'smedia-recut':
        # Pronto = a linha MAIS RECENTE daquele item ja declara o formato novo. Olhar qualquer
        # linha faria o item sumir da fila assim que a versao antiga existisse, que e o oposto.
        ultimo = {}
        for r in sorted(read_rows(SOCIAL), key=lambda x: x.get('ts') or ''):
            if (r.get('item_id') or '').strip():
                ultimo[r['item_id'].strip()] = (r.get('note') or '')
        return {i for i, nota in ultimo.items() if 'formato=7p' in nota}
    want = 'published' if stage == 'write' else 'reviewed'
    out = set()
    for r in read_rows(DONE):
        if (r.get('status') or '').strip() == want:
            out.add((r.get('item_id') or '').strip())
    return out


def lock_name(stage, item):
    """WRITE e REVIEW disputam o mesmo item de proposito (recorte x revisao).
    SMEDIA trabalha sobre post ja publicado e nao deve bloquear nenhum dos dois."""
    if stage == 'smedia': return f'sm-{item}'
    if stage == 'smedia-recut': return f'rc-{item}'
    return item

def published_ids():
    return {(r.get('item_id') or '').strip()
            for r in read_rows(DONE) if (r.get('status') or '').strip() == 'published'}

def candidates(stage):
    """Fila do estagio, ja ordenada. write: tudo que nunca foi publicado.
       review: publicado e ainda nao revisado."""
    feito = done_status(stage)
    if stage == 'smedia-recut':
        # so entra na fila quem JA tem versao social: recorte reescreve, nao cria do zero
        pool = {(r.get('item_id') or '').strip() for r in read_rows(SOCIAL)} & published_ids()
    else:
        pool = published_ids() if stage in ('review', 'smedia') else None
    # Vale a linha MAIS RECENTE de cada id, como em todo o resto do ledger. Ate 2026-08-24 isto
    # ficava com a PRIMEIRA: corrigir um item por append (a unica forma num arquivo append-only)
    # nao surtia efeito nenhum, em silencio - o agente lia a versao velha achando que era a atual.
    porid = {}
    for r in read_rows(BACKLOG):
        i = (r.get('id') or '').strip()
        if i: porid[i] = r
    out = []
    for i, r in porid.items():
        if i in feito:
            continue
        if pool is not None and i not in pool:
            continue
        out.append(r)
    out.sort(key=lambda r: (PRIO.get((r.get('priority') or '').strip(), 9),
                            (r.get('created_at') or ''), r['id']))
    return out

def reclaim_stale(item, agent, stage):
    """Lock parado ha mais de 90 min e sem done row pode ser retomado (regra do runbook)."""
    d = LOCKS / lock_name(stage, item)
    try:
        age = time.time() - d.stat().st_mtime
    except FileNotFoundError:
        return True
    if age < STALE_LOCK_SEC:
        return False
    wip_append(agent, stage, item, 'reclaim', f'lock parado ha {int(age//60)} min, sem done row')
    try:
        os.rmdir(d)
    except OSError:
        return False
    return True

def try_claim(row, agent, stage):
    item = row['id'].strip()
    lk = LOCKS / lock_name(stage, item)
    LOCKS.mkdir(parents=True, exist_ok=True)
    try:
        os.mkdir(lk)
    except FileExistsError:
        if not reclaim_stale(item, agent, stage):
            return False
        try:
            os.mkdir(lk)
        except OSError:
            return False
    wip_append(agent, stage, item, 'claim')
    return True

def control(agent, stage, version, do_log):
    cmd = [sys.executable, str(QXCTL), 'check', '--agent', agent, '--stage', stage]
    if version:
        cmd += ['--version', version]
    if do_log:
        cmd += ['--log']
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--agent', required=True)
    ap.add_argument('--stage', default='write',
                    choices=['write', 'review', 'smedia', 'smedia-recut'])
    ap.add_argument('--version', default='')
    ap.add_argument('--wait', type=int, default=1800,
                    help='segundos de fila vazia antes de desistir (default 1800 = 30 min)')
    ap.add_argument('--poll', type=int, default=30, help='intervalo entre releituras (s)')
    ap.add_argument('--no-claim', action='store_true', help='so mostra a fila, nao reclama nada')
    a = ap.parse_args()

    t0 = time.time()
    last_log = 0.0
    quiet = 0
    while True:
        do_log = (time.time() - last_log) > 600 or last_log == 0
        rc, out = control(a.agent, a.stage, a.version, do_log)
        if do_log:
            last_log = time.time()
        if rc in (10, 20):
            sys.stdout.write(out)
            print(f'# directive={"pause" if rc == 10 else "stop"}: '
                  'termine o item atual inteiro, solte o lock, registre e encerre.')
            return rc
        if 'reload=yes' in out:
            sys.stdout.write(out)
            print('# releia a config acima e chame qxnext de novo.')
            return 40

        fila = candidates(a.stage)
        if a.no_claim:
            print(f'fila={len(fila)}')
            for r in fila:
                print(f"  {r['id']}  {r.get('priority','')}  {r.get('effort','')}  "
                      f"{r.get('category','')}  {(r.get('working_title') or '')[:70]}")
            return 0
        for r in fila:
            if try_claim(r, a.agent, a.stage):
                print(f'waited_s={int(time.time() - t0)}')
                print(f'queue_len={len(fila)}')
                for k in ('id', 'category', 'working_title', 'angle', 'audience',
                          'product_tie', 'lang', 'priority', 'effort', 'sources', 'notes'):
                    v = (r.get(k) or '').replace('\n', ' ')
                    print(f'{k}={v}')
                return 0

        waited = time.time() - t0
        if waited >= a.wait:
            print(f'queue_len=0\nwaited_s={int(waited)}')
            print(f'# fila seca por {int(waited)}s seguidos. Agora sim pode encerrar: '
                  'registre exit no agents.log.csv com o resumo do que publicou.')
            return 30
        quiet += 1
        if quiet == 1 or quiet % 10 == 0:
            print(f'# fila vazia ha {int(waited)}s, aguardando o estagio anterior entregar '
                  f'(teto {a.wait}s)...', file=sys.stderr)
        time.sleep(a.poll)

if __name__ == '__main__':
    sys.exit(main())
