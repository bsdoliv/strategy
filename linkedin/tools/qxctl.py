#!/usr/bin/env python3
"""Control plane do pipeline de blog. O MASTER (`QX-PLAN`) manda; os agentes obedecem.

Resolve dois problemas que apareceram na prática:
  1. Agente rodando com spec velha depois que a configuração mudou.
  2. Não haver como pausar/parar um agente sem mandar mensagem para ele na mão.

MASTER (só o QX-PLAN escreve aqui):
    tools/qxctl.py status
    tools/qxctl.py pause  [--stage write] [--reason "..."]
    tools/qxctl.py resume [--stage write]
    tools/qxctl.py stop   [--stage write]
    tools/qxctl.py bump   "o que mudou na config"      # força todo agente a reler a config

AGENTE (nunca escreve o control.conf):
    tools/qxctl.py check --agent 4 --stage write [--version N]
        exit 0  -> siga
        exit 10 -> PAUSE: termine o item atual, solte o lock, registre e saia
        exit 20 -> STOP: idem
    Saída inclui `reload=yes` quando a config mudou desde a sua `--version`.
"""
import argparse, os, pathlib, sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = ROOT / 'control.conf'
LOG = ROOT / 'ledger' / 'agents.log.csv'        # fleet: harvest/curate/write/review
MASTER_LOG = ROOT / 'ledger' / 'master.log.csv'  # so o QX-PLAN: bump/pause/resume/stop/fix
# smedia-recut faltava aqui desde a config 31: o `check` recusava o estagio e o agente
# NAO CONSEGUIA fazer check-in nenhum - o INV8b acusava o agente por um defeito do tool.
STAGES = ('harvest', 'curate', 'write', 'review', 'plan', 'smedia', 'smedia-recut')
CONFIG_FILES = ('CLAUDE.md', 'runbook.md', '.claude/memory/tags.md',
                '.claude/memory/categories.md', '.claude/memory/editorial-conventions.md',
                'workdir/harvest/identity/quartix-profile.md')

def now(): return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def read():
    d = {'state': 'run', 'config_version': '1', 'reason': '', 'note': '',
         'updated_at': '', 'updated_by': ''}
    d.update({f'stage.{s}': '' for s in STAGES})
    if CONF.exists():
        for ln in CONF.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith('#') or '=' not in ln: continue
            k, v = ln.split('=', 1); d[k.strip()] = v.strip()
    return d

def write(d, who='QX-PLAN'):
    d['updated_at'] = now(); d['updated_by'] = who
    out = ['# Control plane do pipeline. ESCRITO SÓ PELO QX-PLAN (master).',
           '# Agentes LEEM via `tools/qxctl.py check` e nunca escrevem aqui.',
           '# state: run | pause | stop   (stage.<nome> vazio = herda o global)', '']
    for k in ('state', 'config_version', 'reason', 'note', 'updated_at', 'updated_by'):
        out.append(f'{k}={d.get(k,"")}')
    out.append('')
    for s in STAGES: out.append(f'stage.{s}={d.get(f"stage.{s}","")}')
    CONF.write_text('\n'.join(out) + '\n')

def log(agent, stage, event, ver, note=''):
    # O master tem log proprio: as decisoes dele (bump/pause/stop) sao poucas e precisam ficar
    # legiveis, sem se perder no meio de centenas de ack-config da frota.
    dest = MASTER_LOG if agent == 'QX-PLAN' else LOG
    if not dest.exists():
        dest.write_text('ts,agent_id,stage,event,config_version,note\n')
    note = note.replace('"', "'").replace('\n', ' ')[:300]
    with open(dest, 'a') as f:                     # append-only, uma linha por registro
        f.write(f'{now()},{agent},{stage},{event},{ver},"{note}"\n')

def directive(d, stage):
    return (d.get(f'stage.{stage}') or d.get('state') or 'run').strip()

def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('cmd', choices=['status', 'pause', 'resume', 'stop', 'bump', 'note', 'check'])
    ap.add_argument('text', nargs='?', default='')
    ap.add_argument('--stage', choices=STAGES); ap.add_argument('--reason', default='')
    ap.add_argument('--agent', default='?'); ap.add_argument('--version', default='')
    ap.add_argument('--log', action='store_true')
    a = ap.parse_args()
    d = read()

    if a.cmd == 'status':
        print(f"state={d['state']}  config_version={d['config_version']}  "
              f"updated_at={d['updated_at']} por {d['updated_by']}")
        if d['reason']: print(f"reason={d['reason']}")
        if d['note']: print(f"note={d['note']}")
        for s in STAGES:
            v = d.get(f'stage.{s}')
            print(f'  stage.{s:8} {v or "(herda " + d["state"] + ")"}')
        return 0

    if a.cmd in ('pause', 'resume', 'stop'):
        new = {'pause': 'pause', 'resume': 'run', 'stop': 'stop'}[a.cmd]
        if a.stage:
            d[f'stage.{a.stage}'] = '' if a.cmd == 'resume' else new
            scope = f'stage {a.stage}'
        else:
            d['state'] = new
            if a.cmd == 'resume':
                for s in STAGES: d[f'stage.{s}'] = ''      # resume global limpa overrides
            scope = 'global'
        d['reason'] = a.reason or a.text
        write(d); log('QX-PLAN', a.stage or 'all', a.cmd, d['config_version'], d['reason'])
        print(f"{a.cmd} aplicado ({scope}). state={d['state']} "
              f"stage.{a.stage}={d.get('stage.'+a.stage)}" if a.stage else
              f"{a.cmd} aplicado ({scope}). state={d['state']}")
        return 0

    if a.cmd == 'note':
        # Registro sem sinal: o `bump` custa uma releitura de config para TODA a frota, entao
        # so vale quando muda algo que o agente le. Mudanca em ferramenta que so o humano usa,
        # ou em arquivo fora da lista de config, entra aqui.
        log('QX-PLAN', 'all', 'note', d['config_version'], a.text or a.reason)
        print(f"anotado em master.log.csv (sem bump; config_version segue {d['config_version']})")
        return 0

    if a.cmd == 'bump':
        d['config_version'] = str(int(d['config_version']) + 1)
        d['note'] = a.text or a.reason
        write(d); log('QX-PLAN', 'all', 'bump', d['config_version'], d['note'])
        print(f"config_version -> {d['config_version']}  ({d['note']})")
        print("Todo agente vai reler a config no próximo checkpoint:")
        for f in CONFIG_FILES: print('  -', f)
        return 0

    # ---- agente ----
    dr = directive(d, a.stage if a.stage else 'plan')
    cur = d['config_version']
    reload_needed = bool(a.version) and a.version != cur
    print(f'directive={dr}')
    print(f'config_version={cur}')
    print(f'reload={"yes" if reload_needed else "no"}')
    if d['reason']: print(f'reason={d["reason"]}')
    if d['note']: print(f'note={d["note"]}')
    if reload_needed:
        print('# releia, nesta ordem, antes de continuar:')
        for f in CONFIG_FILES: print(f'#   {f}')
    if a.log or dr != 'run' or reload_needed:
        log(a.agent, a.stage or '?', dr if dr != 'run' else 'ack-config', cur,
            'reload' if reload_needed else '')
    return {'run': 0, 'pause': 10, 'stop': 20}.get(dr, 0)

if __name__ == '__main__':
    sys.exit(main())
