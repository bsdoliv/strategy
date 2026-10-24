#!/usr/bin/env python3
"""Verifica/corrige o charset do conteudo publicado.

Regra: ASCII + letras acentuadas do portugues + o simbolo (R) da marca. Nada de ornamento
tipografico -- travessao, aspas curvas, reticencias, ponto medio, setas, bullets, emoji,
espaco nao-quebravel. O texto continua ACENTUADO: o alvo e tirar ornamento, nao tirar acento.

  python3 tools/qxtext.py check <arquivo|-->     # lista o que esta fora da regra

NOTA: travessao usado como PAR (--- texto ---) fica melhor virando parenteses, escrito a mao,
do que virando hifen. O `fix` resolve o caso mecanico e remove o hifen orfao antes de virgula,
mas leia o resultado: `binaria - construir tudo, e essa` e correto e um pouco seco;
`binaria (construir tudo), e essa` e melhor portugues.
  python3 tools/qxtext.py fix   <arquivo|-->     # imprime a versao corrigida (stdin com --)
"""
import re, sys, unicodedata

PT = set('aaaaeeiooouucnAAAAEEIOOOUUCN')
ALLOWED_EXTRA = set('áàâãéêíóôõúüç'
                    'ÁÀÂÃÉÊÍÓÔÕÚÜÇ'
                    '®')                       # (R) da marca QUARTIX Markets(R)

REPL = {
    '—': '-', '–': '-', '―': '-', '−': '-',      # travessoes e menos
    '“': '"', '”': '"', '„': '"', '«': '"', '»': '"',
    '‘': "'", '’': "'", '‚': "'", '′': "'", '″': '"',
    '…': '...', '·': '-', '•': '-', '◦': '-', '⁃': '-',
    '→': '->', '←': '<-', '⇒': '=>', '≤': '<=', '≥': '>=',
    '×': 'x', '≠': '!=', '≈': '~', '∩': '+',
    ' ': ' ', ' ': ' ', ' ': ' ', '​': '', '﻿': '',
    '™': '(TM)', 'º': 'o', 'ª': 'a', '≤': '<=',
    '­': '', '️': '',
    # sinais que TEM referente no texto: descartar em silencio muda o sentido.
    '§': 'secao ', '¶': 'par. ', '†': '*', '‡': '**', '‰': ' por mil',
    '±': '+/-', '≡': '==', '∞': 'infinito', '√': 'raiz de ', '∑': 'soma',
    '½': '1/2', '¼': '1/4', '¾': '3/4', '¹': '1', '²': '2', '³': '3',
}

def ok(ch):
    return ch in '\n\t' or 0x20 <= ord(ch) <= 0x7e or ch in ALLOWED_EXTRA

def fix(s):
    out = []
    for ch in s:
        if ok(ch):
            out.append(ch)
        elif ch in REPL:
            out.append(REPL[ch])
        else:
            # ultimo recurso: tenta decompor (e' -> e), senao descarta
            d = ''.join(c for c in unicodedata.normalize('NFD', ch) if not unicodedata.combining(c))
            out.append(d if d and all(ok(c) for c in d) else '')
    out = ''.join(out)
    # Travessao usado como parentese deixa " -," / " -." quando o par fecha antes da pontuacao.
    # Isso e pontuacao invalida em portugues, entao o hifen orfao sai.
    out = re.sub(r'\s+-\s*([,.;:!?])', r'\1', out)
    return re.sub(r'[ \t]+\n', '\n', out)

def check(s, label):
    bad = {}
    for i, ln in enumerate(s.split('\n'), 1):
        for j, ch in enumerate(ln, 1):
            if not ok(ch):
                bad.setdefault(ch, []).append((i, j))
    if not bad:
        print(f'{label}: OK')
        return 0
    print(f'{label}: {sum(len(v) for v in bad.values())} ocorrencias, {len(bad)} caracteres distintos')
    for ch, pos in sorted(bad.items(), key=lambda x: -len(x[1])):
        nome = unicodedata.name(ch, '?')
        p = ', '.join(f'{a}:{b}' for a, b in pos[:4]) + (' ...' if len(pos) > 4 else '')
        print(f"  U+{ord(ch):04X} {ch!r:>10}  x{len(pos):<4} -> {REPL.get(ch,'(descartado)')!r:>8}  {nome[:38]}  [{p}]")
    return 1

if __name__ == '__main__':
    if len(sys.argv) < 3: sys.exit(__doc__)
    cmd, src = sys.argv[1], sys.argv[2]
    data = sys.stdin.read() if src == '--' else open(src, encoding='utf-8').read()
    if cmd == 'fix': sys.stdout.write(fix(data))
    else: sys.exit(check(data, src if src != '--' else '(stdin)'))
