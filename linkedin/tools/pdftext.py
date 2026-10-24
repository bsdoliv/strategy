#!/usr/bin/env python3
"""Extract text from the PDFs in data/ without poppler.

Why this exists: `pdftotext`/`pdftoppm` are NOT installed on this machine, so the Read tool
cannot render PDFs and `QX-HARVEST` would be blocked on every one of them. Pure stdlib.

Decoding, best path first:
  1. **per-font /ToUnicode** - the CMap of the font selected by `Tf` at that point in the
     content stream. The only correct path when a PDF carries several subset fonts: they
     reuse low CIDs with different meanings (in SwapsBook/ElectronicRatesMarkets.pdf, CID 68
     is `M` in one font and `a` in another). One merged map yields text that reads fine and
     says something else - the worst possible failure for a citation source.
  2. /Encoding /Differences glyph names, when the font has no /ToUnicode.
  3. document-wide merged /ToUnicode, then flat single-byte offsets - the old heuristics,
     kept because they still win on PDFs whose page/font graph this parser cannot resolve.

Candidates are ranked by `score()`, which weighs **stopword density** heavily: a subset font
decoded with the wrong map produces perfect-looking prose with zero function words.

Usage:  python3 tools/pdftext.py <file.pdf>
Caveat: subset fonts may drop inter-word spacing ("plat af orma"); the text is still quotable
once respaced. Empty or symbol-only output means the page is a scanned image.
"""
import re, sys, zlib

SCAN_RE = re.compile(rb'stream\r?\n')            # frouxo de proposito - ver streams()
STRICT_RE = re.compile(rb'(?<!end)stream\r?\n')  # correto: grafo de objetos e CMaps

WORD_RE = re.compile(r'[A-Za-zÀ-ÿ]{2,}')
VOWELS = 'aeiouáéíóúâêôãõàü'
STOP = frozenset((
    'the and of that with for from this these those are was were which have has had been not '
    'but their there where when what who how all any can could would should will may more than '
    'then into over under between each other such only also its our your his her they them we you'
).split()) | frozenset((
    'que para com uma dos das nao mais como pelo pela sao foi ser tem seu sua entre sobre por '
    'nos nas aos ate onde quando quem qual isso este esta esse essa ou se ja nao'
).split())

BIN_SIG = (b'\x00\x01\x00\x00', b'OTTO', b'ttcf', b'\xff\xd8\xff', b'\x89PNG', b'GIF8')



def score(s):
    """Quanto disto e texto de verdade.

    Duas medidas, porque cada uma sozinha se engana:
      - fracao da string dentro de palavras plausiveis: descarta ruido de pontuacao;
      - **densidade de stopword**: descarta cifra consistente, o modo de falha perigoso -
        saida que parece prosa, tem vogal na proporcao certa, e diz outra coisa. Medido:
        0,02% de stopword no texto cifrado contra 4% no mesmo arquivo decodificado certo.
    """
    if not s: return 0.0
    palavras = WORD_RE.findall(s)
    if not palavras: return 0.0
    bom = stops = 0
    for w in palavras:
        lw = w.lower()
        v = sum(c in VOWELS for c in lw) / len(lw)
        if 0.15 <= v <= 0.75: bom += len(w)
        if lw in STOP: stops += 1
    return bom / len(s) + 6.0 * (stops / len(palavras))


def safe_chr(n):
    """Surrogate (D800-DFFF) nao e caractere: chr() aceita e todo write no stdout quebra."""
    return '' if n == 0 or 0xD800 <= n <= 0xDFFF else chr(n)


def streams(b, strict=False):
    """Yield stream bodies, inflated when Flate, raw otherwise.

    Duas varreduras, e a frouxa NAO e bug esquecido:

    `strict=True` usa o regex correto e sempre devolve o corpo cru. E o que o grafo e os
    /ToUnicode precisam: em ElectronicRatesMarkets.pdf os 9 CMaps estao sem compressao e sem
    `Tj`, entao o filtro antigo os descartava inteiros e sobrava so heuristica.

    `strict=False` mantem a varredura do tool original, que tambem casa a cauda de cada
    `endstream` e por isso inspeciona regioes deslocadas. Medido: em `QUARTIX Mail - blog.pdf`
    essas regioes rendem 6.187 palavras reais que a varredura correta nao alcanca. Enquanto o
    parser for heuristico, recall vale mais que elegancia - so nao pode subtrair.
    """
    rx = STRICT_RE if strict else SCAN_RE
    for m in rx.finditer(b):
        s = m.end(); e = b.find(b'endstream', s)
        if e < 0: continue
        raw = b[s:e]
        try:
            yield zlib.decompress(raw)
        except Exception:
            if strict or b'Tj' in raw or b'TJ' in raw: yield raw


def cmap_from(d):
    """Um /ToUnicode -> ({codigo: char}, largura do codigo em bytes)."""
    mp, width = {}, 1
    for blk in re.findall(rb'beginbfchar(.*?)endbfchar', d, re.S):
        for src, dst in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            if len(src) > 2: width = 2
            mp[int(src, 16)] = ''.join(safe_chr(int(dst[i:i+4], 16))
                                       for i in range(0, len(dst) - 3, 4))
    for blk in re.findall(rb'beginbfrange(.*?)endbfrange', d, re.S):
        for lo, hi, dst in re.findall(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk):
            if len(lo) > 2: width = 2
            lo, hi, dst = int(lo, 16), int(hi, 16), int(dst[:4], 16)
            for i in range(lo, min(hi, lo + 512) + 1):
                mp.setdefault(i, safe_chr(dst + i - lo))
    return mp, width


_AGL = {'space': ' ', 'hyphen': '-', 'period': '.', 'comma': ',', 'colon': ':', 'semicolon': ';',
        'slash': '/', 'parenleft': '(', 'parenright': ')', 'percent': '%', 'ampersand': '&',
        'quotesingle': "'", 'quotedbl': '"', 'quoteright': "'", 'quoteleft': "'",
        'endash': '-', 'emdash': '-', 'bullet': '-', 'zero': '0', 'one': '1', 'two': '2',
        'three': '3', 'four': '4', 'five': '5', 'six': '6', 'seven': '7', 'eight': '8',
        'nine': '9', 'plus': '+', 'equal': '=', 'question': '?', 'exclam': '!',
        'asterisk': '*', 'underscore': '_', 'dollar': '$', 'at': '@', 'numbersign': '#'}
_ACC = {'acute': '́', 'grave': '̀', 'circumflex': '̂', 'tilde': '̃',
        'dieresis': '̈', 'cedilla': '̧'}


def glyph_char(name):
    import unicodedata
    if name in _AGL: return _AGL[name]
    if len(name) == 1: return name
    m = re.fullmatch(r'uni([0-9A-Fa-f]{4})', name) or re.fullmatch(r'u([0-9A-Fa-f]{4,6})', name)
    if m: return safe_chr(int(m.group(1), 16))
    for suf, comb in _ACC.items():
        if name.endswith(suf) and len(name) - len(suf) == 1:
            return unicodedata.normalize('NFC', name[0] + comb)
    return ''


def differences(dic):
    """/Differences [ 1 /a /b 5 /eacute ] -> {codigo: char}."""
    m = re.search(rb'/Differences\s*\[(.*?)\]', dic, re.S)
    if not m: return {}
    out, code = {}, 0
    for tok in re.findall(rb'\d+|/[^\s/\[\]<>()]+', m.group(1)):
        if tok[:1] == b'/':
            c = glyph_char(tok[1:].decode('latin-1'))
            if c: out[code] = c
            code += 1
        else:
            code = int(tok)
    return out


def raw_objects(b):
    """num -> (bytes do dicionario, corpo do stream). Objetos diretos; ObjStm nao e aberto."""
    out = {}
    for m in re.finditer(rb'(\d+)\s+0\s+obj\b(.*?)\bendobj', b, re.S):
        body = m.group(2)
        i = STRICT_RE.search(body)
        if i:
            e = body.find(b'endstream', i.end())
            raw = body[i.end():e if e > 0 else len(body)]
            try: data = zlib.decompress(raw)
            except Exception: data = raw
            out[int(m.group(1))] = (body[:i.start()], data)
        else:
            out[int(m.group(1))] = (body, b'')
    return out


def font_table(objs):
    """numero do objeto de fonte -> ({codigo: char}, largura)."""
    fonts = {}
    for num, (dic, _) in objs.items():
        if b'/Font' not in dic: continue
        mp, width = {}, 2 if b'/Type0' in dic else 1
        m = re.search(rb'/ToUnicode\s+(\d+)\s+0\s+R', dic)
        if m and int(m.group(1)) in objs:
            mp, w = cmap_from(objs[int(m.group(1))][1])
            if mp: width = w
        if not mp:
            d = differences(dic)
            m = re.search(rb'/Encoding\s+(\d+)\s+0\s+R', dic)
            if not d and m and int(m.group(1)) in objs:
                d = differences(objs[int(m.group(1))][0])
            mp = d
        if mp: fonts[num] = (mp, width)
    return fonts


def page_units(objs, fonts):
    """(conteudo, {nome do recurso: fonte}) por pagina resolvida."""
    for num, (dic, _) in objs.items():
        if not re.search(rb'/Type\s*/Page\b', dic): continue
        res = re.search(rb'/Resources\s*<<(.*?)>>\s*(?:/|>>)', dic, re.S)
        rd = res.group(1) if res else b''
        if not rd:
            m = re.search(rb'/Resources\s+(\d+)\s+0\s+R', dic)
            if m and int(m.group(1)) in objs: rd = objs[int(m.group(1))][0]
        local = {}
        fm = re.search(rb'/Font\s*<<(.*?)>>', rd, re.S)
        if fm:
            for name, ref in re.findall(rb'/([^\s/]+)\s+(\d+)\s+0\s+R', fm.group(1)):
                if int(ref) in fonts: local[name] = fonts[int(ref)]
        refs = re.search(rb'/Contents\s*(?:(\d+)\s+0\s+R|\[(.*?)\])', dic, re.S)
        if not refs: continue
        nums = [refs.group(1)] if refs.group(1) else re.findall(rb'(\d+)\s+0\s+R', refs.group(2))
        data = b''.join(objs[int(n)][1] for n in nums if int(n) in objs)
        if data and local: yield data, local


def decode_with_fonts(data, local):
    """Percorre o content stream honrando `Tf`, decodificando cada string com A SUA fonte."""
    cur, out = None, []
    for t in re.finditer(rb'/([^\s/]+)\s+[\d.]+\s+Tf|\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>', data):
        if t.group(1) is not None:
            cur = local.get(t.group(1)); continue
        if cur is None: continue
        mp, width = cur
        if t.group(2) is not None:
            h = re.sub(rb'\s', b'', t.group(2))
            if len(h) % 2: h += b'0'
            try: r = bytes.fromhex(h.decode('ascii'))
            except ValueError: continue
        else:
            r = re.sub(rb'\\([()\\])', rb'\1', t.group(0)[1:-1])
        if width == 2:
            out.append(''.join(mp.get((r[i] << 8) | r[i+1], '') for i in range(0, len(r) - 1, 2)))
        else:
            out.append(''.join(mp.get(c, '') for c in r))
    return ''.join(out)


def tounicode(b):
    """Todos os /ToUnicode fundidos num mapa so. FALLBACK - ver docstring do modulo."""
    m2u = {}
    for d in streams(b, strict=True):
        if b'beginbfchar' not in d and b'beginbfrange' not in d: continue
        mp, _ = cmap_from(d)
        for k, v in mp.items(): m2u.setdefault(k, v)
    return m2u


def show_strings(d):
    """Bytes crus de cada operando string do PDF (literal `(...)` e hex `<...>`)."""
    for t in re.finditer(rb'\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>', d):
        if t.group(1) is not None:
            h = re.sub(rb'\s', b'', t.group(1))
            if len(h) % 2: h += b'0'
            try: yield bytes.fromhex(h.decode('ascii'))
            except ValueError: continue
        else:
            yield re.sub(rb'\\([()\\])', rb'\1', t.group(0)[1:-1])



def e_imagem(d, raws):
    """True so quando TODOS os sinais concordam que este stream e blob de imagem.

    Nenhum sinal isolado serve, e isso foi medido nos 15 PDFs de `data/` + `doc/`:
      - exigir `Tf` derruba texto real (`Post _ LinkedIn.pdf` cai de 75 palavras-funcao para 1);
      - piso de qualidade derruba pagina legitima de formula (57 das 82 do `flow-trading-paper`
        tem densidade de stopword quase zero e sao paginas de verdade);
      - proporcao de nao-ASCII tambem nao separa sozinha (paginas reais chegam a 0,99).
    A conjuncao e conservadora de proposito: na duvida, deixa passar.
    """
    if b'Tf' in d:                      # selecionou fonte: e objeto de texto, nao imagem
        return False
    txt = ''.join(chr(c) if c < 0x17F else ' ' for r in raws for c in r)
    letras = [c for c in txt if c.isalpha()]
    if len(letras) < 200:               # material insuficiente para afirmar
        return False
    nao_ascii = sum(1 for c in letras if ord(c) > 127) / len(letras)
    palavras = [w.lower() for w in WORD_RE.findall(txt)]
    stop = sum(w in STOP for w in palavras) / len(palavras) if palavras else 0.0
    return nao_ascii > 0.40 and stop < 0.005

def pages(path):
    b = open(path, 'rb').read()
    try:
        objs = raw_objects(b)
        fonts = font_table(objs)
        idx = {(len(d), d[:64]): l for d, l in page_units(objs, fonts)} if fonts else {}
    except Exception:
        idx = {}                                    # grafo nao resolveu: so heuristica
    m2u = tounicode(b)
    out = []
    for d in streams(b):
        if b'Tj' not in d and b'TJ' not in d: continue
        if d[:4] in BIN_SIG or d[:3] in BIN_SIG: continue   # programa de fonte / imagem
        raws = list(show_strings(d))
        if not raws: continue
        if e_imagem(d, raws):
            out.append('')       # conta a pagina, mas sem o ruido: o aviso final depende disto
            continue
        cands = []
        local = idx.get((len(d), d[:64]))
        if local: cands.append(decode_with_fonts(d, local))
        if m2u:
            cands.append(''.join(''.join(m2u.get((r[i] << 8) | r[i+1], '')
                                         for i in range(0, len(r) - 1, 2)) for r in raws))
        for off in (0, 29, 31):
            cands.append(''.join(''.join(chr(c + off) if 0 < c + off < 0x17F else ' ' for c in r)
                                 for r in raws))
        best = max(cands, key=score)
        out.append(re.sub(r'\s+', ' ', best).strip())
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit(__doc__)
    _pgs = pages(sys.argv[1])
    _com = 0
    for i, p in enumerate(_pgs, 1):
        if p and p.strip():
            _com += 1
            print(f'\n----- P{i} -----\n{p}')
    if _pgs and _com == 0:
        # dizer isto em voz alta importa: saida vazia por PDF de imagem e diferente de arquivo
        # ilegivel, e o agente precisa saber que nao ha o que citar aqui.
        print('PDF SEM CAMADA DE TEXTO: nenhuma das '
              f'{len(_pgs)} paginas tem camada de texto. E imagem (escaneado ou carrossel '
              'montado). Nao ha texto para citar - precisa de OCR.', file=sys.stderr)
        sys.exit(2)
