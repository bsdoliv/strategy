#!/usr/bin/env python3
"""qxocr - le PDF sem camada de texto, usando o OCR nativo do macOS (Vision).

    python3 tools/qxocr.py <arquivo.pdf> [--paginas 1-8] [--dpi 300]

Existe porque `tools/pdftext.py` **detecta** PDF de imagem e avisa, mas nao le. Duas fontes boas
ficaram travadas nisso, entre elas o white paper de TCA da LMAX - o material mais proximo do que a
QUARTIX faz em qualidade de execucao (last look x liquidez firme).

Nao ha `tesseract` nem `pdftoppm` nesta maquina, e nao precisa: o macOS traz o **Vision**, que faz
reconhecimento de texto, e o `gs` (ghostscript) rasteriza a pagina. O Vision so e alcancavel por
PyObjC, que nao existe no interpretador padrao - por isso o tool chama um venv proprio:

    /Users/andre/.qx-ocr-venv        (criar com: python3 -m venv <caminho> &&
                                      <caminho>/bin/pip install pyobjc-framework-Vision pyobjc-framework-Quartz)

O texto sai com a mesma marcacao de pagina do `pdftext.py`, para as duas ferramentas serem
intercambiaveis para quem consome.

**OCR erra.** Numero lido por OCR NAO e numero verificado: confira contra a imagem antes de citar
qualquer valor. A regra do projeto continua valendo - numero errado vira afirmacao errada.
"""
import argparse, os, pathlib, shutil, subprocess, sys, tempfile

VENV = pathlib.Path('/Users/andre/.qx-ocr-venv')
GS = shutil.which('gs')

LEITOR = r'''
import sys, Vision, Quartz
from Foundation import NSURL
def ocr(caminho):
    url = NSURL.fileURLWithPath_(caminho)
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None: return ''
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    if img is None: return ''
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setUsesLanguageCorrection_(True)
    req.setRecognitionLanguages_(['en-US', 'pt-BR'])
    handler = Vision.VNImageRequestHandlerCliCGImage_options_(img, {}) \
        if hasattr(Vision, 'VNImageRequestHandlerCliCGImage_options_') \
        else Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
    ok, err = handler.performRequests_error_([req], None)
    if not ok: return ''
    linhas = []
    for obs in (req.results() or []):
        cand = obs.topCandidates_(1)
        if cand and len(cand): linhas.append(cand[0].string())
    return '\n'.join(linhas)
for p in sys.argv[1:]:
    print('\x00PAGINA\x00' + p)
    print(ocr(p))
'''


def rasteriza(pdf, destino, dpi, paginas):
    if not GS:
        sys.exit('ghostscript (gs) nao encontrado - e ele que rasteriza a pagina')
    cmd = [GS, '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=png16m', f'-r{dpi}',
           '-dTextAlphaBits=4', '-dGraphicsAlphaBits=4']
    if paginas:
        ini, fim = paginas
        cmd += [f'-dFirstPage={ini}', f'-dLastPage={fim}']
    cmd += [f'-sOutputFile={destino}/p-%04d.png', str(pdf)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'gs falhou: {r.stderr[:300]}')
    return sorted(destino.glob('p-*.png'))


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('pdf')
    ap.add_argument('--paginas', help='faixa 1-8; o default e o documento inteiro')
    ap.add_argument('--dpi', type=int, default=300)
    a = ap.parse_args()

    py = VENV / 'bin' / 'python'
    if not py.exists():
        sys.exit(f'venv de OCR ausente em {VENV} - ver o docstring deste arquivo')

    faixa = None
    if a.paginas:
        ini, _, fim = a.paginas.partition('-')
        faixa = (int(ini), int(fim or ini))

    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        imgs = rasteriza(a.pdf, d, a.dpi, faixa)
        if not imgs:
            sys.exit('gs nao produziu pagina nenhuma')
        script = d / 'ler.py'
        script.write_text(LEITOR)
        r = subprocess.run([str(py), str(script)] + [str(i) for i in imgs],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f'Vision falhou: {r.stderr[:400]}')
        deslocamento = (faixa[0] - 1) if faixa else 0
        n = 0
        for bloco in r.stdout.split('\x00PAGINA\x00')[1:]:
            _, _, corpo = bloco.partition('\n')
            corpo = corpo.strip()
            n += 1
            if corpo:
                print(f'\n----- P{n + deslocamento} -----\n{corpo}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
