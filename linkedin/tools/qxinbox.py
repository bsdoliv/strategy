#!/usr/bin/env python3
"""qxinbox - ingere as capturas do bookmarklet e as coloca no pipeline.

    python3 tools/qxinbox.py            # le ~/Downloads/qx-linkedin-*.json
    python3 tools/qxinbox.py --dir <d>  # outra pasta
    python3 tools/qxinbox.py --dry      # mostra o que faria, sem escrever

Cada captura vira um arquivo em `workdir/harvest/catalog/linkedin/` e uma linha em
`ledger/manifest.csv` com `kind=social`. O `QX-CURATE` passa a ver o material como qualquer
outra nota de harvest.

**Procedencia importa mais aqui do que em qualquer outra fonte.** O texto vem da sessao logada do
usuario, num post de terceiro. Entao cada arquivo guarda a URL, o autor e a data de captura, e o
`QX-WRITE` continua sem poder citar longamente nem afirmar numero que a §8 nao cubra. Isto e
**sinal de tema**, nao acervo citavel.
"""
import argparse, base64, binascii, csv, hashlib, json, pathlib, re, sys
from datetime import datetime, timezone

R = pathlib.Path(__file__).resolve().parent.parent
DESTINO = R / 'workdir' / 'harvest' / 'catalog' / 'linkedin'
MANIFEST = R / 'ledger' / 'manifest.csv'


def limpa(s):
    return re.sub(r'[ \t]+', ' ', (s or '').replace('\r', '')).strip()


def slug(u, autor):
    base = re.sub(r'[^a-z0-9]+', '-', (autor or 'sem-autor').lower()).strip('-')[:40]
    return f"{base or 'sem-autor'}-{hashlib.sha1(u.encode()).hexdigest()[:8]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(pathlib.Path.home() / 'Downloads'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    arquivos = sorted(pathlib.Path(a.dir).glob('qx-linkedin-*.json'))
    if not arquivos:
        print(f'nada em {a.dir} (procuro por qx-linkedin-*.json)')
        return 0

    ja = set()
    if MANIFEST.exists():
        ja = {r['source_ref'] for r in csv.DictReader(open(MANIFEST, encoding='utf-8'))}

    novos = repetidos = ruins = 0
    linhas = []
    for f in arquivos:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  ILEGIVEL {f.name}: {e}'); ruins += 1; continue
        url, texto = d.get('url', ''), limpa(d.get('texto'))
        if not url or len(texto) < 40:
            print(f'  VAZIO    {f.name}'); ruins += 1; continue
        if url in ja:
            print(f'  JA TINHA {url[:66]}'); repetidos += 1; continue

        nome = slug(url, d.get('autor'))
        nota = DESTINO / f'{nome}.md'

        # A URL do media.licdn.com e assinada e EXPIRA (~2 semanas). Por isso o bookmarklet
        # embute base64 e aqui a imagem vira arquivo: guardar so o link daria referencia morta.
        imgs, falhas = [], []
        for k, im in enumerate(d.get('imagens') or [], 1):
            if not im.get('base64'):
                falhas.append(im.get('erro') or 'sem base64'); continue
            ext = {'image/jpeg': '.jpg', 'image/png': '.png',
                   'image/gif': '.gif', 'image/webp': '.webp'}.get(im.get('mime'), '.jpg')
            alvo = DESTINO / f'{nome}-{k:02d}{ext}'
            try:
                dados = base64.b64decode(im['base64'], validate=True)
            except (binascii.Error, ValueError) as e:
                falhas.append(f'base64 invalido: {e}'); continue
            if not a.dry:
                DESTINO.mkdir(parents=True, exist_ok=True)
                alvo.write_bytes(dados)
            imgs.append((alvo.name, len(dados), im.get('alt') or ''))
        corpo = (
            f"# Post de LinkedIn - {d.get('autor') or 'autor nao identificado'}\n\n"
            f"- **Origem:** {url}\n"
            f"- **Capturado em:** {d.get('capturado_em', '')} (bookmarklet, sessao do usuario)\n"
            f"- **Autor:** {d.get('autor') or '?'} - {limpa(d.get('autor_cargo'))}\n"
            f"- **Publicado:** {limpa(d.get('publicado'))}\n"
            f"- **Engajamento no momento da captura:** {limpa(d.get('engajamento_bruto')) or '(nao capturado)'}\n\n"
            "> Post de terceiro, capturado da sessao logada do usuario. Serve como **sinal de tema**.\n"
            "> Nao cite longamente e nao afirme numero daqui sem fonte primaria - vale a secao 8 do\n"
            "> `quartix-profile.md` como em qualquer outra fonte.\n\n"
            + (("## Imagens\n\n" + "".join(
                f"- `{n}` ({b // 1024} KB)" + (f" - alt: {al}" if al else "") + "\n"
                for n, b, al in imgs) + "\n") if imgs else "")
            + (("> Imagem nao embutida: " + "; ".join(falhas) + "\n\n") if falhas else "")
            + "## Texto\n\n" + texto + "\n"
        )
        if a.dry:
            print(f'  [dry] {nota.relative_to(R)}  ({len(texto)} chars)')
        else:
            DESTINO.mkdir(parents=True, exist_ok=True)
            nota.write_text(corpo, encoding='utf-8')
            linhas.append([datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                           'qxinbox', 'catalog', url, str(nota.relative_to(R)), 'social', 'ok',
                           f"capturado por bookmarklet na sessao do usuario; {len(texto)} chars"])
            extra = f' + {len(imgs)} img' if imgs else ''
            print(f'  OK       {nota.name}  ({len(texto)} chars{extra})')
        novos += 1
        ja.add(url)

    if linhas and not a.dry:
        with open(MANIFEST, 'a', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh, lineterminator='\n')
            for l in linhas:
                l[-1] = l[-1][:380]
                w.writerow(l)
    print(f'\n  novos={novos} repetidos={repetidos} ilegiveis={ruins}')
    if novos and not a.dry:
        print('  Os .json em Downloads podem ser apagados - a nota ja esta no workdir.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
