#!/usr/bin/env python3
"""qxslide - renderiza o carrossel de Instagram na identidade QUARTIX, localmente.

    python3 tools/qxslide.py <item_id>          # le workdir/posts/social/carrossel.csv
    python3 tools/qxslide.py --all              # todos os itens do CSV
    python3 tools/qxslide.py --demo             # amostra sem gravar no pipeline

Existe porque a geracao de arte por prompt **nao e confiavel para marca**. Medido em
2026-08-23, duas tentativas no Canva com o brand kit correto: saiu azul (azul nao e cor da
QUARTIX), inventou o wordmark "QUARTIX tecnologia financeira", pos telefone falso
"(12) 3456-7890" e dominio errado "quartix.com.br", e desenhou diagramas com rotulos que
nao sao palavras - `Pocecsfar Pricing`, `Auta Inpot`, `tecnologia s que transform`.
Numa peca tecnica para mesa de operacao isso e pior que nao publicar.

Aqui nao ha modelo generativo. Cor, texto, logo e posicao sao deterministicos: a mesma linha
do CSV produz sempre o mesmo PNG. A identidade vem de `.claude/memory/brand-visual.md`, que
foi extraida do site e das apresentacoes reais.

Saida: `workdir/posts/social/<item_id>/slide-NN.png`, 1080x1350 (4:5 do Instagram).
"""
import csv, pathlib, re, sys
from PIL import Image, ImageDraw, ImageFont

R = pathlib.Path(__file__).resolve().parent.parent
CSV = R / 'workdir' / 'posts' / 'social' / 'carrossel.csv'
LOGO = pathlib.Path('/Users/andre/www-quartix/site-v2-next/images/logo-quartix.io-branco.png')
# Imagem do acervo do site NAO entra na arte por enquanto. A tentativa de 2026-08-23 recortou
# uma faixa de `quartix_concept_band.png` e colou no topo da capa: o recorte pegou predio, preco
# e tabela sem criterio, e o resultado foi reprovado pelo usuario. Usar o acervo exige escolher
# a imagem certa para o assunto do post, nao fatiar a primeira que couber. Fica para quando
# houver criterio de selecao, e com aprovacao peca a peca.

W, H = 1080, 1350
PRETO   = (0, 0, 0)
OURO    = (254, 189, 11)      # #febd0b
AMBAR   = (255, 106, 0)       # #ff6a00
CLARO   = (229, 229, 229)     # #e5e5e5
CINZA   = (191, 191, 191)     # #bfbfbf
CARD    = (18, 18, 20)

MARGEM = 96
FONTE_BOLD = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
FONTE_REG  = '/System/Library/Fonts/Supplemental/Arial.ttf'


def f(caminho, tam):
    try:
        return ImageFont.truetype(caminho, tam)
    except OSError:
        return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', tam)


def quebra(draw, texto, fonte, largura):
    linhas, atual = [], ''
    for p in texto.split():
        teste = (atual + ' ' + p).strip()
        if draw.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual: linhas.append(atual)
            atual = p
    if atual: linhas.append(atual)
    return linhas


def ajusta(draw, texto, caminho, largura, tam_max, tam_min, max_linhas):
    """Maior corpo que cabe em max_linhas. Encolher e o ultimo recurso, nao o primeiro."""
    for tam in range(tam_max, tam_min - 1, -2):
        fonte = f(caminho, tam)
        ls = quebra(draw, texto, fonte, largura)
        if len(ls) <= max_linhas:
            return fonte, ls
    fonte = f(caminho, tam_min)
    return fonte, quebra(draw, texto, fonte, largura)[:max_linhas]


def passo(d, n, total):
    """Contador em toda pagina, capa e CTA inclusive: o leitor precisa saber onde esta."""
    fonte = f(FONTE_BOLD, 22)
    d.text((MARGEM, H - 250), f'{n:02d} / {total:02d}', font=fonte, fill=OURO)


def regua_chevron(d, y, n=26, cor=OURO, tam=26):
    """A fileira de `>` que abre a pagina - motivo da marca."""
    fonte = f(FONTE_BOLD, tam)
    x = MARGEM
    for _ in range(n):
        d.text((x, y), '>', font=fonte, fill=cor)
        x += tam * 0.62
        if x > W - MARGEM: break


def assina(img, d, alto=False):
    """Logo oficial no canto inferior direito.

    Nao desenhe sparkline aqui: o PNG do logo ja traz o glifo. A primeira versao desenhava
    um por cima e a peca saia com dois.
    """
    y = 150 if alto else H - 150
    if LOGO.exists():
        lg = Image.open(LOGO).convert('RGBA')
        alt = 34
        lg = lg.resize((int(lg.width * alt / lg.height), alt), Image.LANCZOS)
        img.alpha_composite(lg, (W - MARGEM - lg.width, y - alt // 2))
    else:
        fonte = f(FONTE_BOLD, 34)
        t = 'quartix.io'
        d.text((W - MARGEM - d.textlength(t, font=fonte), y - 18), t, font=fonte, fill=CLARO)


def degrade_esquerda(img):
    """Degrade quente sangrando da borda esquerda, como na capa institucional."""
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for x in range(0, 420):
        a = int(150 * (1 - x / 420) ** 2.2)
        gd.line([(x, 0), (x, H)], fill=(212, 75, 0, a))
    img.alpha_composite(g)


def capa(titulo, subtitulo, total=None):
    img = Image.new('RGBA', (W, H), PRETO)
    degrade_esquerda(img)
    d = ImageDraw.Draw(img)
    regua_chevron(d, 108)
    fonte, linhas = ajusta(d, titulo.upper(), FONTE_BOLD, W - 2 * MARGEM, 108, 56, 4)
    y = 430
    for l in linhas:
        d.text((MARGEM, y), l, font=fonte, fill=OURO)
        y += fonte.size * 1.06
    if subtitulo:
        fs, ls = ajusta(d, subtitulo, FONTE_REG, W - 2 * MARGEM, 40, 26, 4)
        y += 44
        for l in ls:
            d.text((MARGEM, y), l, font=fs, fill=CINZA)
            y += fs.size * 1.34
    if total: passo(d, 1, total)
    rod = f(FONTE_BOLD, 22)
    x = MARGEM
    for palavra in ('INTELIG\u00caNCIA', 'PRECIS\u00c3O', 'TEMPO REAL'):
        d.text((x, H - 190), '>>', font=rod, fill=OURO); x += d.textlength('>> ', font=rod)
        d.text((x, H - 190), palavra, font=rod, fill=CLARO)
        x += d.textlength(palavra + '   ', font=rod)
    assina(img, d)
    return img


def conteudo(texto, n, total):
    img = Image.new('RGBA', (W, H), PRETO)
    d = ImageDraw.Draw(img)
    regua_chevron(d, 108, n=14)
    d.rounded_rectangle([MARGEM - 32, 300, W - MARGEM + 32, H - 320], radius=28, fill=CARD)
    fonte, linhas = ajusta(d, texto, FONTE_BOLD, W - 2 * MARGEM - 40, 62, 32, 7)
    alt = len(linhas) * fonte.size * 1.24
    y = 300 + ((H - 320) - 300 - alt) / 2
    chev = f(FONTE_BOLD, fonte.size)
    d.text((MARGEM - 4, y), '>', font=chev, fill=OURO)
    for l in linhas:
        d.text((MARGEM + 44, y), l, font=fonte, fill=CLARO)
        y += fonte.size * 1.24
    passo(d, n, total)
    assina(img, d)
    return img


def cta(texto, n=None, total=None):
    img = Image.new('RGBA', (W, H), PRETO)
    degrade_esquerda(img)
    d = ImageDraw.Draw(img)
    regua_chevron(d, 108)
    texto = apara_marca(texto)
    fonte, linhas = ajusta(d, texto, FONTE_BOLD, W - 2 * MARGEM, 84, 44, 5)
    alt = len(linhas) * fonte.size * 1.12
    y = (H - alt) / 2 - 60
    for l in linhas:                                   # ouro, mesma hierarquia da capa
        d.text((MARGEM, y), l, font=fonte, fill=OURO)
        y += fonte.size * 1.12
    # Sem link na arte: medido em 6 carrosseis do setor, zero fecha com chamada para acao.
    # O link vive na caption, que e onde o corpus poe. A assinatura fica no logo, so.
    if n: passo(d, n, total)
    assina(img, d)
    return img


MARCA_FINAL = re.compile(
    r'\s*(QUARTIX\s+Markets(\u00ae|\(R\))?|QUARTIX)\s*[.\u2022|-]*\s*$', re.I)


def apara_marca(texto):
    """Tira a assinatura de marca do fim do texto de CTA.

    O bloco de carrossel do Doc termina com 'QUARTIX Markets(R)' porque la ele e texto solto,
    sem arte. Na peca a marca ja aparece duas vezes - no `>> quartix.io` e no logo - e uma
    terceira vira ruido.
    """
    return MARCA_FINAL.sub('', texto or '').strip()


def origem_do_item(item_id):
    """Subdiretorio do lote, quando o item declara `origem=<nome>` na nota do backlog.

    Serve para lote com fonte propria (hoje `lehman_manual`) manter os artefatos separados sem
    bifurcar o ledger, que e CSV plano e nao suporta subdiretorio.
    """
    todo = R / 'ledger' / 'backlog.todo.csv'
    if not todo.exists():
        return None
    ultimo = None
    for r in csv.DictReader(open(todo, encoding='utf-8')):
        if (r.get('id') or '').strip() == item_id:
            ultimo = r                                  # vale a mais recente
    if not ultimo:
        return None
    m = re.search(r'origem=([a-z0-9_\-]+)', ultimo.get('notes') or '', re.I)
    return m.group(1) if m else None


def render(linha, destino):
    destino.mkdir(parents=True, exist_ok=True)
    corpo = [linha.get(f'slide{i}_texto', '').strip() for i in range(2, 7)]
    corpo = [c for c in corpo if c]
    total = len(corpo) + 1 + (1 if (linha.get('cta_texto') or '').strip() else 0)
    slides = [capa(linha['capa_titulo'], linha.get('capa_subtitulo', ''), total)]
    for i, txt in enumerate(corpo, 2):
        slides.append(conteudo(txt, i, total))
    # Sem fecho escrito, NAO se inventa um: a config 38 tirou o CTA da pagina 7 porque o corpus
    # mediu que ninguem no setor fecha assim. Um default de fabrica reintroduziria exatamente o
    # que a medicao derrubou. Sem `cta_texto`, o carrossel termina no ultimo slide de conteudo.
    fecho = (linha.get('cta_texto') or '').strip()
    if fecho:
        slides.append(cta(fecho, total, total))
    saidas = []
    for i, im in enumerate(slides, 1):
        p = destino / f'slide-{i:02d}.png'
        im.convert('RGB').save(p, 'PNG', optimize=True)
        saidas.append(p)
    return saidas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    todos = '--all' in sys.argv
    demo = '--demo' in sys.argv
    brutas = list(csv.DictReader(open(CSV, encoding='utf-8'))) if CSV.exists() else []
    # append-only: item corrigido aparece duas vezes e **vale a mais recente**, como em todo o
    # ledger. Sem isto a arte sai da versao velha e ninguem percebe.
    porid = {}
    for r in brutas:
        if r.get('item_id'): porid[r['item_id']] = r
    linhas = list(porid.values())
    if not linhas:
        sys.exit('carrossel.csv vazio - o QX-SMEDIA ainda nao entregou nenhuma linha')
    alvo = linhas if todos else [r for r in linhas if r['item_id'] in args] or linhas[:1]
    for r in alvo:
        if demo:
            dest = pathlib.Path(sys.argv[sys.argv.index('--demo') + 1])
        else:
            base = R / 'workdir' / 'posts' / 'social'
            org = origem_do_item(r['item_id'])
            dest = (base / org / r['item_id']) if org else (base / r['item_id'])
        saidas = render(r, dest)
        print(f"  {r['item_id']}: {len(saidas)} slides -> {dest}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
