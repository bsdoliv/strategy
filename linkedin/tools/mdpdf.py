#!/usr/bin/env python3
"""Render Markdown to PDF. Pure stdlib — no pandoc, no Chrome, no network.

Why hand-rolled: this machine has no pandoc/wkhtmltopdf/weasyprint/python-markdown,
`cupsfilter` has no HTML filter, and headless Chrome is killed by the sandbox. The only
remaining offline path is emitting PDF directly, which is what this does, using the base-14
Helvetica/Courier fonts (no embedding needed).

Usage: python3 tools/mdpdf.py -o out.pdf [--title "..."] file1.md file2.md ...
Supports: ATX headings, pipe tables, fenced code, blockquotes, bullet lists, hr, and inline
**bold** / *italic* / `code` / [links](x) / ~~strike~~.
Limits: WinAnsi (Latin-1) charset — arrows and emoji are transliterated, see XLATE.
"""
import re, sys, unicodedata, pathlib

# ---------- base-14 metrics (units/1000) ----------
_HELV = "278 278 355 556 556 889 667 191 333 333 389 584 278 333 278 278 556 556 556 556 556 556 556 556 556 556 278 278 584 584 584 556 1015 667 667 722 722 667 611 778 722 278 500 667 556 833 722 778 667 778 722 667 611 722 667 944 667 667 611 278 278 278 469 556 333 556 556 500 556 556 278 556 556 222 222 500 222 833 556 556 556 556 333 500 278 556 500 722 500 500 500 334 260 334 584"
_HELB = "278 333 474 556 556 889 722 238 333 333 389 584 278 333 278 278 556 556 556 556 556 556 556 556 556 556 333 333 584 584 584 611 975 722 722 722 722 667 611 778 722 278 556 722 611 833 722 778 667 778 722 667 611 722 667 944 667 667 611 333 278 333 584 556 333 556 611 556 611 556 333 611 611 278 278 556 278 889 611 611 611 611 389 556 333 611 556 778 556 556 500 389 280 389 584"
W = {}
for name, tbl in (('R', _HELV), ('B', _HELB)):
    W[name] = {chr(32 + i): int(v) for i, v in enumerate(tbl.split())}
W['I'] = W['R']; W['BI'] = W['B']

XLATE = {'→': '->', '←': '<-', '≥': '>=', '≤': '<=', '×': 'x',
         '✓': 'OK', '✅': '[OK]', '\U0001f534': '[!]', '⚠': '[!]', '⚙': '',
         '\U0001f501': '[...]', '⏳': '[...]', '─': '-', '️': '', '•': '-',
         '·': '-', '‑': '-', '▸': '>', '∩': '+', '≈': '~', '√': 'v', '±': '+/-',
         '🔄': '[...]', '📊': '', '⚡': '', '🔍': '', '≠': '!='}

def clean(s):
    for k, v in XLATE.items(): s = s.replace(k, v)
    return ''.join(c if c.isprintable() or c == '\n' else '' for c in s)

def width(runs, size):
    t = 0
    for txt, st in runs:
        tbl = {'mono': None}.get(st)
        for ch in txt:
            if st == 'mono': t += 600
            else:
                f = 'B' if 'b' in st else ('I' if 'i' in st else 'R')
                w = W[f].get(ch)
                if w is None:
                    base = unicodedata.normalize('NFD', ch)[:1]
                    w = W[f].get(base, 556)
                t += w
    return t * size / 1000.0

# ---------- inline parsing -> runs [(text, style)] ----------
def runs_of(t):
    t = clean(t)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    out, pos = [], 0
    pat = re.compile(r'`([^`]+)`|\*\*([^*]+)\*\*|(?<![\w*])\*([^*\n]+)\*(?![\w*])|~~([^~]+)~~')
    for m in pat.finditer(t):
        if m.start() > pos: out.append((t[pos:m.start()], ''))
        if m.group(1) is not None: out.append((m.group(1), 'mono'))
        elif m.group(2) is not None: out.append((m.group(2), 'b'))
        elif m.group(3) is not None: out.append((m.group(3), 'i'))
        else: out.append((m.group(4), ''))
        pos = m.end()
    if pos < len(t): out.append((t[pos:], ''))
    return [r for r in out if r[0]]

def wrap(runs, size, maxw):
    lines, cur = [], []
    for txt, st in runs:
        for i, word in enumerate(re.split(r'(\s+)', txt)):
            if not word: continue
            if word.isspace():
                if cur: cur.append((' ', st))
                continue
            if width(cur + [(word, st)], size) > maxw and cur:
                while cur and cur[-1][0] == ' ': cur.pop()
                lines.append(cur); cur = []
            cur.append((word, st))
    if cur: lines.append(cur)
    return lines or [[]]

# ---------- markdown -> blocks ----------
def blocks_of(md):
    B, lines, i = [], md.split('\n'), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith('```'):
            i += 1; buf = []
            while i < len(lines) and not lines[i].startswith('```'): buf.append(clean(lines[i])); i += 1
            i += 1; B.append(('code', buf)); continue
        if ln.lstrip().startswith('|') and i+1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i+1]):
            hdr = [runs_of(c.strip()) for c in ln.strip().strip('|').split('|')]
            i += 2; rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                r = [runs_of(c.strip()) for c in lines[i].strip().strip('|').split('|')]
                r += [[]] * (len(hdr) - len(r)); rows.append(r[:len(hdr)]); i += 1
            B.append(('table', hdr, rows)); continue
        if re.match(r'^\s*---+\s*$', ln): B.append(('hr',)); i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)', ln)
        if m: B.append(('h', len(m.group(1)), runs_of(m.group(2)))); i += 1; continue
        if ln.lstrip().startswith('>'):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith('>'):
                buf.append(lines[i].lstrip()[1:].strip()); i += 1
            B.append(('quote', runs_of(' '.join(buf)))); continue
        m = re.match(r'^(\s*)[-*]\s+(.*)', ln)
        if m:
            lvl = min(len(m.group(1)) // 2, 2); body = m.group(2); i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^\s*([-*]\s|#{1,6}\s|\||>|```)', lines[i]):
                body += ' ' + lines[i].strip(); i += 1
            B.append(('li', lvl, runs_of(body))); continue
        if not ln.strip(): i += 1; continue
        buf = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^\s*([-*]\s|#{1,6}\s|\||>|```|---+\s*$)', lines[i]):
            buf.append(lines[i]); i += 1
        B.append(('p', runs_of(' '.join(buf))))
    return B

# ---------- PDF emitter ----------
PW, PH, MX, MTOP, MBOT = 595.0, 842.0, 52.0, 62.0, 56.0
CW = PW - 2 * MX
FONT = {'': '/F1', 'b': '/F2', 'i': '/F3', 'mono': '/F4'}

_CP1252_HIGH = {0x20AC:0x80,0x201A:0x82,0x0192:0x83,0x201E:0x84,0x2026:0x85,0x2020:0x86,
    0x2021:0x87,0x02C6:0x88,0x2030:0x89,0x0160:0x8A,0x2039:0x8B,0x0152:0x8C,0x017D:0x8E,
    0x2018:0x91,0x2019:0x92,0x201C:0x93,0x201D:0x94,0x2022:0x95,0x2013:0x96,0x2014:0x97,
    0x02DC:0x98,0x2122:0x99,0x0161:0x9A,0x203A:0x9B,0x0153:0x9C,0x017E:0x9E,0x0178:0x9F}

def cp1252(s):
    """Encode to WinAnsi by table, never touching Python's cp1252 codec.

    That codec SEGFAULTS on this machine's interpreter (/opt/pkg python3.9) — both with an
    error handler and in strict mode. Mapping the bytes ourselves is the only reliable path:
    ASCII and Latin-1 pass through, the 27 CP1252-specific high chars are mapped explicitly,
    anything else becomes '?'.
    """
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if o < 0x80 or 0xA0 <= o <= 0xFF: out.append(o)
        elif o in _CP1252_HIGH: out.append(_CP1252_HIGH[o])
        else: out.append(0x3F)
    return bytes(out)

def esc(s):
    return s.replace('\\', r'\\').replace('(', r'\(').replace(')', r'\)')

class Doc:
    def __init__(self): self.pages, self.buf, self.y = [], [], PH - MTOP
    def newpage(self):
        if self.buf: self.pages.append(''.join(self.buf))
        self.buf, self.y = [], PH - MTOP
    def need(self, h):
        if self.y - h < MBOT: self.newpage()
    def text(self, x, y, runs, size):
        self.buf.append('BT\n')
        cx = x
        for txt, st in runs:
            f = FONT.get(st, '/F1')
            self.buf.append(f'{f} {size} Tf 1 0 0 1 {cx:.2f} {y:.2f} Tm ({esc(txt)}) Tj\n')
            cx += width([(txt, st)], size)
        self.buf.append('ET\n')
    def rect(self, x, y, w, h, fill=None, stroke=None, lw=0.5):
        if fill: self.buf.append(f'{fill} rg ')
        if stroke: self.buf.append(f'{stroke} RG {lw} w ')
        op = 'B' if (fill and stroke) else ('f' if fill else 'S')
        self.buf.append(f'{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {op}\n0 0 0 rg 0 0 0 RG\n')

HS = {1: (17, 9, 7), 2: (13, 13, 5), 3: (10.8, 10, 3), 4: (9.8, 8, 2), 5: (9.5, 7, 2), 6: (9.5, 7, 2)}

def render(blocks, title):
    d = Doc()
    body, lead = 9.3, 1.5
    for b in blocks:
        k = b[0]
        if k == 'h':
            lvl = b[1]; size, before, after = HS[lvl]
            d.y -= before
            ls = wrap(b[2], size, CW)
            d.need(len(ls) * size * 1.3 + after + 8)
            for l in ls:
                d.text(MX, d.y - size, [(t, ('b' if s != 'mono' else s)) for t, s in l], size)
                d.y -= size * 1.3
            if lvl <= 2:
                d.buf.append(f'0.15 w 0.1 0.1 0.1 RG {MX} {d.y+3:.2f} m {PW-MX} {d.y+3:.2f} l S\n')
            d.y -= after
        elif k == 'p':
            ls = wrap(b[1], body, CW); d.need(len(ls) * body * lead + 4)
            for l in ls:
                d.need(body * lead); d.text(MX, d.y - body, l, body); d.y -= body * lead
            d.y -= 3
        elif k == 'li':
            ind = MX + 10 + b[1] * 12
            ls = wrap(b[2], body, CW - (ind - MX) - 4)
            d.need(len(ls) * body * lead + 2)
            for j, l in enumerate(ls):
                d.need(body * lead)
                if j == 0: d.text(ind - 9, d.y - body, [('-', '')], body)
                d.text(ind, d.y - body, l, body); d.y -= body * lead
            d.y -= 1.5
        elif k == 'quote':
            ls = wrap(b[1], body, CW - 22); h = len(ls) * body * lead + 8
            d.need(h + 4); top = d.y
            for l in ls:
                d.text(MX + 16, d.y - body - 4, [(t, 'i' if s == '' else s) for t, s in l], body)
                d.y -= body * lead
            d.y -= 8
            d.rect(MX, d.y + 4, 2.5, top - d.y - 4, fill='0.55 0.55 0.55')
            d.y -= 3
        elif k == 'code':
            cs = 7.6; h = len(b[1]) * cs * 1.42 + 9
            d.need(h + 4); top = d.y
            d.rect(MX, top - h, CW, h, fill='0.96 0.965 0.97', stroke='0.85 0.86 0.88')
            d.y -= 7
            for l in b[1]:
                d.text(MX + 7, d.y - cs, [(l[:118], 'mono')], cs); d.y -= cs * 1.42
            d.y -= 8
        elif k == 'hr':
            d.need(12); d.buf.append(f'0.4 w 0.8 0.8 0.82 RG {MX} {d.y-4:.2f} m {PW-MX} {d.y-4:.2f} l S\n'); d.y -= 13
        elif k == 'table':
            hdr, rows = b[1], b[2]; n = len(hdr); ts = 7.9
            nat = [max([width(hdr[c], ts)] + [width(r[c], ts) for r in rows] + [20]) for c in range(n)]
            tot = sum(nat)
            cols = [max(38.0, CW * w / tot) for w in nat]
            s = CW / sum(cols); cols = [c * s for c in cols]
            def rowh(cells):
                return max(len(wrap(cells[c], ts, cols[c] - 8)) for c in range(n)) * ts * 1.35 + 5
            def draw(cells, head):
                h = rowh(cells); d.need(h)
                x = MX
                for c in range(n):
                    d.rect(x, d.y - h, cols[c], h, fill='0.93 0.94 0.95' if head else None, stroke='0.78 0.79 0.81', lw=0.4)
                    yy = d.y - ts - 3
                    for l in wrap(cells[c], ts, cols[c] - 8):
                        d.text(x + 4, yy, [(t, 'b' if head and st != 'mono' else st) for t, st in l], ts)
                        yy -= ts * 1.35
                    x += cols[c]
                d.y -= h
            d.need(rowh(hdr) + 14); d.y -= 4
            draw(hdr, True)
            for r in rows: draw(r, False)
            d.y -= 7
    d.newpage()
    return d.pages

def build(pages, title, out):
    """Emit the PDF. Object numbers are contiguous: gaps in the xref table with type 'n'
    are malformed and some readers reject the file, so nothing is allocated out of band."""
    N = len(pages)
    F1, F2, F3, F4 = 3, 4, 5, 6           # Helvetica, -Bold, -Oblique, Courier
    res = '<< /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R >> >>'
    body, seq = {}, []
    kids = ' '.join(f'{7+i*2} 0 R' for i in range(N))
    body[1] = b'<< /Type /Catalog /Pages 2 0 R >>'
    body[2] = ('<< /Type /Pages /Count %d /Kids [%s] >>' % (N, kids)).encode()
    for num, base in ((F1, 'Helvetica'), (F2, 'Helvetica-Bold'),
                      (F3, 'Helvetica-Oblique'), (F4, 'Courier')):
        body[num] = ('<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>' % base).encode()
    seq = [1, 2, F1, F2, F3, F4]
    streams = set()
    for i, content in enumerate(pages):
        content += (f'BT /F1 7.5 Tf 0.45 0.45 0.45 rg 1 0 0 1 {PW/2-8:.1f} {MBOT-26:.1f} Tm '
                    f'({i+1}) Tj ET\n')
        pg, ct = 7 + i * 2, 8 + i * 2
        body[pg] = ('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.0f %.0f] /Resources %s /Contents %d 0 R >>'
                    % (PW, PH, res, ct)).encode()
        # NOTE: no /FlateDecode. zlib.compress() segfaults on this machine's Python
        # (/opt/pkg python3.9), so content streams are emitted raw. Larger file, valid PDF.
        body[ct] = cp1252(content)
        streams.add(ct); seq += [pg, ct]
    parts = [b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n']
    off, cur = {}, len(parts[0])
    for num in seq:
        off[num] = cur
        d = body[num]
        if num in streams:
            chunk = (b'%d 0 obj\n<< /Length %d >>\nstream\n' % (num, len(d))
                     + d + b'\nendstream\nendobj\n')
        else:
            chunk = b'%d 0 obj\n' % num + d + b'\nendobj\n'
        parts.append(chunk); cur += len(chunk)
    size = max(seq) + 1
    xr = ['xref\n0 %d\n' % size, '0000000000 65535 f \n']
    for n in range(1, size):
        xr.append('%010d 00000 n \n' % off[n])   # contiguous: every n exists
    parts.append(cp1252(''.join(xr) + 'trailer\n<< /Size %d /Root 1 0 R /Info << /Title (%s) >> >>\n'
                  'startxref\n%d\n%%%%EOF\n' % (size, esc(clean(title)), cur)))
    pathlib.Path(out).write_bytes(b''.join(parts))

if __name__ == '__main__':
    a = sys.argv[1:]
    out = a[a.index('-o') + 1]
    title = a[a.index('--title') + 1] if '--title' in a else 'Documento'
    files = [x for x in a if x.endswith('.md')]
    blocks = []
    for f in files:
        blocks += blocks_of(pathlib.Path(f).read_text())
    pages = render(blocks, title)
    build(pages, title, out)
    import os
    print(f'{out}  {len(pages)} páginas, {os.path.getsize(out)//1024} KB')
