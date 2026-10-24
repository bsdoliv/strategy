#!/usr/bin/env python3
"""Gera `qxgrab.url.txt` a partir de `qxgrab.js`.

    python3 tools/bookmarklet/gerar.py

O `.js` e a fonte: legivel, comentado, versionado. O `.txt` e o mesmo codigo no formato que a
URL de um favorito aceita - **uma linha so**, sem comentario e percent-encoded. As tres coisas
sao necessarias: quebra de linha encerra a URL, `//` comentaria o resto da linha unica, e
caractere como espaco, aspas e `%` quebra no campo de endereco.

Verifica parenteses e chaves antes de gravar: bookmarklet quebrado falha em silencio no clique.
"""
import pathlib, re, sys, urllib.parse

D = pathlib.Path(__file__).resolve().parent
src = (D / 'qxgrab.js').read_text(encoding='utf-8')
corpo = src[src.index('(function ()'):]
corpo = re.sub(r'/\*.*?\*/', '', corpo, flags=re.S)          # comentario de bloco
corpo = re.sub(r'\n\s*', ' ', corpo)                          # uma linha so
corpo = re.sub(r'\s{2,}', ' ', corpo).strip()

if corpo.count('(') != corpo.count(')') or corpo.count('{') != corpo.count('}'):
    sys.exit('ERRO: parenteses ou chaves desbalanceados - nao gravei')
if '//' in re.sub(r'https?://', '', corpo):
    sys.exit('ERRO: comentario de linha (//) sobreviveu - ele mataria o resto do bookmarklet')

url = 'javascript:' + urllib.parse.quote(corpo, safe="!#$&'()*+,-./:;=?@_~[]{}|^%")
(D / 'qxgrab.url.txt').write_text(url + '\n', encoding='utf-8')
versao = re.search(r'versao:\s*(\d+)', corpo)
print(f'qxgrab.url.txt gerado: v{versao.group(1) if versao else "?"}, {len(url)} caracteres')
