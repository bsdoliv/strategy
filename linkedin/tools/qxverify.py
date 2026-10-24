#!/usr/bin/env python3
"""qxverify - confere se os numeros de uma nota de harvest aparecem no PDF de origem.

Existe porque `tools/pdftext.py` mudou em 2026-08-23 (config_version=22: regex casando
em endstream, CMap sem compressao descartado, decodificacao por fonte). Nota escrita
com a extracao velha pode citar numero que o PDF nao tem. Isto responde "quais notas
merecem conferencia humana", sem abrir os 9 PDFs a mao.

Descobre os pares sozinho: procura a linha `- **Origem:** `data/...pdf`` no topo da nota.

    python3 tools/qxverify.py            # relatorio
    python3 tools/qxverify.py --quiet    # exit 1 se alguma nota ficar abaixo do piso

O que ele NAO e: prova de que a nota esta certa. Numero ausente pode ser comentario
nosso, citacao de terceiro ou valor de tabela que virou imagem. Taxa baixa e um
convite a olhar, nao um veredito.
"""
import re, subprocess, sys, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PISO = 60.0                      # % de acerto abaixo da qual a nota entra no relatorio
ORIGEM = re.compile(r'-\s*\*\*Origem:\*\*\s*`([^`]+\.pdf)`', re.I)
NUM = re.compile(r'\b\d[\d.,]{2,}\b')

def normal(s):
    return re.sub(r'[.,]', '', s)

CORTE = re.compile(r'^#{1,3}\s*(mash-?up|o que disputariamos|auditoria|cuidados|angulos|'
                   r'reconquista|cobertura que faltava)', re.I | re.M)

def corpo_do_pdf(texto):
    """So a parte da nota que relata o PDF.

    Depois do primeiro `## Mash-up` / `## Auditoria` / `## Cuidados` a nota passa a citar
    OUTRAS fontes e a comentar em nome proprio - numero dali nao tem por que estar neste
    PDF, e contar isso como falha faz a ferramenta gritar lobo. Foi o que aconteceu na
    primeira versao: 4 de 9 notas 'falharam' e nenhuma tinha erro de extracao.
    """
    m = CORTE.search(texto)
    return texto[:m.start()] if m else texto

def numeros_da_nota(texto):
    """Numeros citados no corpo, tirando o que nao vem do PDF: URL, id de SSRN e data nossa."""
    limpo = re.sub(r'https?://\S+', ' ', corpo_do_pdf(texto))
    limpo = re.sub(r'`[^`]*`', ' ', limpo)
    fora = set()
    for m in NUM.finditer(limpo):
        v = m.group()
        if re.fullmatch(r'20[2-9]\d', v):      # ano corrente/futuro: carimbo do agente
            continue
        fora.add(v)
    return sorted(fora)

def main():
    quieto = '--quiet' in sys.argv
    notas = sorted(RAIZ.glob('workdir/harvest/**/*.md'))
    baixas, checadas = [], 0
    for nota in notas:
        corpo = nota.read_text(encoding='utf-8')
        m = ORIGEM.search(corpo)
        if not m:
            continue
        pdf = RAIZ / m.group(1)
        rel = nota.relative_to(RAIZ)
        if not pdf.exists():
            print(f"?? {rel}: origem nao encontrada -> {m.group(1)}")
            continue
        r = subprocess.run([sys.executable, str(RAIZ/'tools/pdftext.py'), str(pdf)],
                           capture_output=True, text=True, timeout=600)
        plano = normal(re.sub(r'\s+', '', r.stdout))
        alvos = numeros_da_nota(corpo)
        if not alvos:
            continue
        checadas += 1
        faltam = [a for a in alvos if normal(a) not in plano]
        pct = 100 * (len(alvos) - len(faltam)) / len(alvos)
        marca = 'ok' if pct >= PISO else '!!'
        if not quieto or pct < PISO:
            print(f"{marca} {rel}: {len(alvos)-len(faltam)}/{len(alvos)} ({pct:.0f}%)")
            if pct < PISO:
                print(f"      ausentes: {faltam[:14]}")
        if pct < PISO:
            baixas.append(str(rel))
    if not quieto:
        print(f"\n{checadas} notas com PDF local conferidas; {len(baixas)} abaixo de {PISO:.0f}%.")
    return 1 if (quieto and baixas) else 0

if __name__ == '__main__':
    sys.exit(main())
