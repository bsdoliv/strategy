#!/usr/bin/env python3
"""qxdecrypt - extrai texto de PDF cifrado com AES (handler padrao, senha de usuario vazia).

    python3 tools/qxdecrypt.py <arquivo.pdf>

Cifra em PDF publico quase sempre **nao e controle de acesso**: e permissao (nao imprimir, nao
copiar) com senha de usuario VAZIA. Qualquer leitor abre. O que faltava aqui era a primitiva:
`cryptography` nao compila nesta maquina, entao o `pypdf` recusa. `tools/qxaes.py` supre isso.

**Escopo:** handler /Standard, /V 4 /R 4 com /AESV2 (AES-128-CBC) - que e o caso do PS21/20 da FCA.
RC4 e AESV3 nao estao implementados; o tool diz isso em voz alta em vez de devolver lixo.

**Nao contorna protecao real.** Se houver senha de usuario de verdade, a derivacao falha e o tool
para. A escada do runbook continua valendo: isto e o degrau 5 (capacidade), nao contorno de
credencial.
"""
import hashlib, pathlib, re, struct, sys, zlib, importlib.util

_d = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_d))
import qxaes

PAD = bytes([0x28,0xBF,0x4E,0x5E,0x4E,0x75,0x8A,0x41,0x64,0x00,0x4E,0x56,0xFF,0xFA,0x01,0x08,
             0x2E,0x2E,0x00,0xB6,0xD0,0x68,0x3E,0x80,0x2F,0x0C,0xA9,0xFE,0x64,0x53,0x69,0x7A])


def _str_pdf(b):
    """Le uma string PDF literal (...) com escapes, ou hex <...>."""
    if b[:1] == b'<':
        return bytes.fromhex(re.sub(rb'[^0-9A-Fa-f]', b'', b[1:-1]).decode())
    out, i = bytearray(), 1
    while i < len(b) - 1:
        c = b[i]
        if c == 0x5C:                                  # barra invertida
            i += 1
            n = b[i]
            mapa = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}
            if n in mapa: out.append(mapa[n])
            elif 0x30 <= n <= 0x37:
                oct_ = bytes(b[i:i+3]).rstrip(b')')
                out.append(int(oct_, 8) & 0xFF); i += len(oct_) - 1
            else: out.append(n)
        else:
            out.append(c)
        i += 1
    return bytes(out)


def chave_do_arquivo(dic, id0):
    # ARMADILHA: o /Length do topo esta em BITS (128) e o de dentro do /CF esta em BYTES (16).
    # Pegar o primeiro que aparecer deriva chave de 2 bytes e nada decifra - silenciosamente.
    tamanhos = [int(x) for x in re.findall(rb'/Length\s+(\d+)', dic)]
    bits = max(t for t in tamanhos if t >= 40) if any(t >= 40 for t in tamanhos) else max(tamanhos) * 8
    n = bits // 8
    R = int(re.search(rb'/R\s+(\d+)', dic).group(1))
    P = int(re.search(rb'/P\s+(-?\d+)', dic).group(1))
    O = _str_pdf(re.search(rb'/O\s*(\(.*?[^\\]\)|<[0-9A-Fa-f\s]+>)', dic, re.S).group(1))
    meta_cifrada = b'/EncryptMetadata false' not in dic.replace(b' ', b'')
    h = hashlib.md5()
    h.update(PAD)                                      # senha de usuario vazia
    h.update(O[:32])
    h.update(struct.pack('<i', P))
    h.update(id0)
    if R >= 4 and not meta_cifrada:
        h.update(b'\xff\xff\xff\xff')
    k = h.digest()
    if R >= 3:
        for _ in range(50):
            k = hashlib.md5(k[:n]).digest()
    return k[:n], R


def chave_do_objeto(chave, num, gen):
    m = hashlib.md5(chave + struct.pack('<i', num)[:3] + struct.pack('<i', gen)[:2] + b'sAlT')
    return m.digest()[:min(len(chave) + 5, 16)]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    qxaes.autoteste()                                  # sem o vetor, nada segue
    b = pathlib.Path(sys.argv[1]).read_bytes()

    m = re.search(rb'/Encrypt\s+(\d+)\s+0\s+R', b)
    if not m:
        sys.exit('PDF nao esta cifrado - use tools/pdftext.py')
    num = int(m.group(1))
    dic = re.search(rb'(?<![0-9])' + str(num).encode() + rb'\s+0\s+obj(.*?)endobj', b, re.S).group(1)
    if b'/AESV2' not in dic:
        sys.exit('so /AESV2 (AES-128) esta implementado; este arquivo usa outro filtro - '
                 'nao vou adivinhar e devolver lixo')
    mid = re.search(rb'/ID\s*\[\s*(<[0-9A-Fa-f\s]+>|\(.*?[^\\]\))', b, re.S)
    id0 = _str_pdf(mid.group(1)) if mid else b''
    chave, R = chave_do_arquivo(dic, id0)

    spec = importlib.util.spec_from_file_location('pt', str(_d / 'pdftext.py'))
    pt = importlib.util.module_from_spec(spec); spec.loader.exec_module(pt)

    paginas, achou = [], 0
    for mo in re.finditer(rb'(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj', b, re.S):
        onum, ogen, corpo = int(mo.group(1)), int(mo.group(2)), mo.group(3)
        i = pt.STRICT_RE.search(corpo)
        if not i: continue
        e = corpo.find(b'endstream', i.end())
        bruto = corpo[i.end():e if e > 0 else len(corpo)]
        try:
            claro = qxaes.cbc_decifra(chave_do_objeto(chave, onum, ogen), bruto)
        except Exception:
            continue
        try: claro = zlib.decompress(claro)
        except Exception: pass
        if b'Tj' not in claro and b'TJ' not in claro: continue
        raws = list(pt.show_strings(claro))
        if not raws or pt.e_imagem(claro, raws): continue
        achou += 1
        cands = [''.join(''.join(chr(c + off) if 0 < c + off < 0x17F else ' ' for c in r)
                         for r in raws) for off in (0, 29, 31)]
        melhor = max(cands, key=pt.score)
        paginas.append(re.sub(r'\s+', ' ', melhor).strip())

    if not achou:
        sys.exit('nenhum stream decifrou - a senha de usuario pode nao ser vazia')
    for i, p in enumerate(paginas, 1):
        if p.strip(): print(f'\n----- P{i} -----\n{p}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
