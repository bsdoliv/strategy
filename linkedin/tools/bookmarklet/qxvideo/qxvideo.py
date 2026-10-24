#!/usr/bin/env python3
"""qxvideo - baixa o video dos posts que o `qxgrab` marcou com `tem_video`.

    python3 tools/bookmarklet/qxvideo.py            # le ~/Downloads/qx-linkedin-*.json
    python3 tools/bookmarklet/qxvideo.py --dir <d>  # outra pasta
    python3 tools/bookmarklet/qxvideo.py --dry      # mostra o que faria, sem baixar

**Por que isto nao mora no bookmarklet.** Na pagina LOGADA o video e MediaSource: o `src` do
`<video>` e um `blob:`, que `fetch` nao le, e a sonda `qxvprobe.js` nao achou uma unica URL de
midia nos 194KB de HTML (`playlist 0 | mp4 0 | m3u8 0 | mpd 0`). Nao ha o que baixar de dentro da
pagina. Ja a pagina PUBLICA do mesmo post embute MP4 progressivo, e e de la que o `yt-dlp` tira.
Duas paginas diferentes para o mesmo post - o bookmarklet estava olhando para a errada.

**O nome do MP4 e o basename do JSON.** Nao e derivado de novo a partir da URL: e copiado. Assim
o par nunca desalinha, e captura velha (v7, nome em slug) e nova (v9, slug + id) funcionam sem o
script saber qual convencao gerou cada uma.

**Usa o `yt-dlp` desta pasta, nao o do PATH.** `qxvideo/yt-dlp` + `qxvideo/yt_dlp/` sao uma copia
local, e o script so chama essa. Se ela sumir, ele para e diz - nao cai para o binario da maquina,
porque fallback silencioso derrotaria o proposito de ter a copia.

**Nao cai para cookie.** Post restrito nao abre na pagina publica, e a saida seria mandar o cookie
de sessao do usuario para um processo externo. Isso e decisao de politica, nao de ferramenta:
enquanto nao houver uma, aqui falha e registra. Ver RECOMMENDATIONS.md, 2026-08-25.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys

# O `yt-dlp` que este script usa e o que mora AQUI, ao lado dele - nao o do PATH. O launcher faz
# `from yt_dlp import main`, e o Python poe o diretorio do script no inicio do `sys.path`, entao
# ele carrega `qxvideo/yt_dlp/` de qualquer cwd (verificado). Assim a versao do extrator fica
# presa a esta pasta e nao muda porque a maquina mudou.
AQUI = pathlib.Path(__file__).resolve().parent
YTDLP = AQUI / 'yt-dlp'


def ffprobe(caminho):
    """Confere que o arquivo e video de verdade. Download que devolve pagina de erro tambem grava
    bytes: sem isto, um HTML de 4KB salvo como .mp4 passaria por sucesso."""
    if not shutil.which('ffprobe'):
        # avisa uma vez: sem ffprobe a checagem de "isso e video mesmo?" nao roda, e um HTML de
        # erro salvo como .mp4 passaria por sucesso. Silencio aqui seria pior que a falta.
        if not getattr(ffprobe, 'avisou', False):
            print('  AVISO    ffprobe nao encontrado no PATH - nao da para conferir se o arquivo '
                  'baixado e video', file=sys.stderr)
            ffprobe.avisou = True
        return None
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-show_entries', 'stream=codec_name,width,height',
                        '-of', 'default=noprint_wrappers=1:nokey=1', str(caminho)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return 'RECUSADO'
    return ' '.join(r.stdout.split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(pathlib.Path.home() / 'Downloads'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    # sem fallback para o PATH de proposito: cair no binario da maquina em silencio anularia o
    # motivo de a copia existir - voce acharia que roda a versao fixada e nao rodaria.
    if not YTDLP.is_file():
        sys.exit(f'qxvideo: nao achei o yt-dlp local em {YTDLP} - e ele que resolve a pagina publica')
    if not os.access(YTDLP, os.X_OK):
        sys.exit(f'qxvideo: {YTDLP} existe mas nao esta executavel - `chmod +x` nele')
    if not (AQUI / 'yt_dlp').is_dir():
        sys.exit(f'qxvideo: o launcher esta aqui mas a lib {AQUI / "yt_dlp"} nao - copia incompleta')

    pasta = pathlib.Path(a.dir).expanduser()
    arquivos = sorted(pasta.glob('qx-linkedin-*.json'))
    if not arquivos:
        print(f'nada em {pasta} (procuro por qx-linkedin-*.json)')
        return 0

    baixados = pulados = falhas = 0
    for f in arquivos:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'  ILEGIVEL {f.name}: {e}'); falhas += 1; continue

        # `tem_video` so existe da v8 em diante. Captura v7 e anterior nao tem o campo, mas a
        # capa do video ja entrava como imagem: `videocover` na URL identifica as antigas.
        marcado = bool(d.get('tem_video'))
        capa = any('videocover' in (im.get('url') or '') for im in (d.get('imagens') or []))
        if not (marcado or capa):
            continue
        url = d.get('url')
        if not url:
            print(f'  SEM URL  {f.name}'); falhas += 1; continue

        alvo = f.with_suffix('.mp4')            # mesmo basename do JSON, so troca a extensao
        if alvo.exists():
            print(f'  JA TINHA {alvo.name} ({alvo.stat().st_size // 1024} KB)')
            pulados += 1; continue
        if a.dry:
            print(f'  [dry]    {alvo.name}\n           <- {url[:96]}')
            baixados += 1; continue

        print(f'  BAIXANDO {alvo.name}')
        r = subprocess.run([str(YTDLP), '--no-playlist', '--socket-timeout', '30',
                            '--no-warnings', '-o', str(alvo), url],
                           capture_output=True, text=True)
        if r.returncode != 0 or not alvo.exists():
            # falha ALTA e com o motivo: extrator de site quebra quando o site muda, e o proximo a
            # rodar isto precisa saber se foi post restrito, rede, ou o extrator que caiu.
            msg = (r.stderr or r.stdout or '').strip().splitlines()
            print(f'  FALHOU   {f.name}\n           yt-dlp saiu {r.returncode}: '
                  f'{msg[-1][:200] if msg else "sem mensagem"}')
            falhas += 1; continue

        info = ffprobe(alvo)
        if info == 'RECUSADO':
            print(f'  FALHOU   {alvo.name}: baixou {alvo.stat().st_size} bytes que nao sao video')
            falhas += 1; continue
        print(f'  OK       {alvo.name}  ({alvo.stat().st_size // 1024} KB'
              + (f'; {info}' if info else '') + ')')
        baixados += 1

    print(f'\nbaixados={baixados} ja_tinha={pulados} falhas={falhas}')
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(main())
