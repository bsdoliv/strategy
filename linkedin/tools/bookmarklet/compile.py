#!/usr/bin/env python3
"""Converte um bookmarklet .js no formato percent-encoded que a URL de um favorito aceita.

    python3 gerar.py < qxgrab.js > qxgrab.url.txt

**Filtro: le stdin, escreve stdout.** Nao conhece nome de arquivo e nao decide onde nada e
gravado - quem chama decide. A versao anterior recebia o caminho por argumento e derivava a
saida com `.stem`, que descarta o diretorio: fonte em subpasta era lida de la e o .txt caia na
pasta do `gerar.py`, deixando a copia antiga obsoleta sem ninguem perceber. Ferramenta que nao
escolhe caminho nao erra caminho.

O `.js` e a fonte: legivel, comentado, versionado. O `.txt` e o mesmo codigo em uma linha so,
sem comentario e percent-encoded. As tres coisas sao necessarias: quebra de linha encerra a URL,
`//` comentaria o resto da linha unica, e caractere como espaco, aspas e `%` quebra no campo de
endereco.

Verifica parenteses e chaves antes de emitir: bookmarklet quebrado falha em silencio no clique.
Se a checagem falhar, **nada** vai para stdout e o exit e 1.

**Redirecionar com `>` trunca o alvo ANTES daqui rodar** - checagem que falha te deixa sem o
favorito que funcionava. Por isso o Makefile grava em `.new` e so entao renomeia. Quem chamar na
mao deveria fazer o mesmo.

Todo diagnostico vai para **stderr**, para stdout carregar so o payload.
"""
import re, sys, urllib.parse

src = sys.stdin.read()
if '(function ()' not in src:
    sys.exit('ERRO: nao achei o inicio do bookmarklet - esperava um IIFE `(function () {`')

corpo = src[src.index('(function ()'):]
corpo = re.sub(r'/\*.*?\*/', '', corpo, flags=re.S)          # comentario de bloco
corpo = re.sub(r'\n\s*', ' ', corpo)                          # uma linha so
corpo = re.sub(r'\s{2,}', ' ', corpo).strip()

if corpo.count('(') != corpo.count(')') or corpo.count('{') != corpo.count('}'):
    sys.exit('ERRO: parenteses ou chaves desbalanceados - nao emiti nada')
if '//' in re.sub(r'https?://', '', corpo):
    sys.exit('ERRO: comentario de linha (//) sobreviveu - ele mataria o resto do bookmarklet')

url = 'javascript:' + urllib.parse.quote(corpo, safe="!#$&'()*+,-./:;=?@_~[]{}|^%")
sys.stdout.write(url + '\n')

versao = re.search(r'versao:\s*(\d+)', corpo)
print(f'ok: v{versao.group(1) if versao else "?"}, {len(url)} caracteres', file=sys.stderr)
