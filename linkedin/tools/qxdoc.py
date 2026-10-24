#!/usr/bin/env python3
"""qxdoc.py - mede a FORMA de um post de documento (carrossel) publico do LinkedIn.

Existe porque `tools/qxsocial.py` mede o texto do post e o corpus de
`workdir/harvest/social/benchmarks.csv` nao responde nenhuma pergunta de formato
visual - e o `QX-SMEDIA --stage smedia-recut` precisa exatamente disso para
fixar o brand template de carrossel em capa + 5 + CTA.

Rota publica, sem login e sem contorno de credencial (a permalink de post de
documento e servida sem sessao, igual a de post comum):

  1. `linkedin.com/posts/<conta>_<slug>-activity-<id>-<hash>` traz, no HTML,
     o atributo `data-native-document-config` - um JSON com `totalPageCount`,
     `title`, `type` e as URLs das capas de pagina;
  2. o `manifestUrl` de dentro dele devolve um JSON com `transcriptManifestUrl`;
  3. o transcript e `{"pages": ["texto da pagina 1", ...]}` - texto por pagina,
     que e o que permite contar palavra por pagina, ver se a ultima e CTA, se ha
     numeracao e se o titulo se repete no rodape.

Documento montado a partir de imagem (deck exportado como imagem, sem camada de
texto) devolve transcript com paginas vazias. Nesse caso `paginas_com_texto` sai
menor que `paginas` e as colunas de palavra ficam VAZIAS - **nunca estimadas**.
O PDF (`transcribedDocumentUrl`) tambem e image-only nesses casos e chega a 10 MB,
entao a ferramenta nao o baixa: nao ha texto para extrair dele.

Uso:
    python3 tools/qxdoc.py --empresa MarketAxess <url> [<url> ...]   # linha CSV
    python3 tools/qxdoc.py --empresa X --text <url>                  # + texto por pagina
    python3 tools/qxdoc.py --classify <url> [...]                    # doc? imagem? video?

Cabecalho de `workdir/harvest/social/carrosseis.csv` (arquivo proprio, porque o
cabecalho de `benchmarks.csv` e fixado no runbook e append-only):

ts,empresa,plataforma,url,data_post,doc_titulo,paginas,paginas_com_texto,palavras_total,palavras_por_pagina_mediana,palavras_capa,palavras_ultima,ultima_e_cta,tem_numeracao,titulo_repetido,palavras_post,fonte,nota
"""
import argparse
import html as htmlmod
import json
import re
import statistics
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from qxsocial import HEADERS, http_get, ldjson_blocks, find_posting, sanitize, csv_field, measure  # noqa: E402

# CTA da ultima pagina: so frase de acao INTEIRA ou endereco. Verbo solto
# ("explore", "discover", "learn") aparece no meio de prosa e dava falso
# positivo - a ultima pagina do carrossel "Meet Mariko" da Bloomberg fecha com
# "Learn from the people around you... explore different areas", que e conselho,
# nao chamada.
CTA_MARKS = (
    "learn more", "find out more", "read more", "read the full", "get in touch",
    "contact us", "book a", "request a", "sign up", "apply now", "register now",
    "register here", "download the", "follow us", "reach out to", "subscribe",
    "see how", "click here", "join us at", "visit us", "www.", "http",
    "saiba mais", "fale com", "acesse", "cadastre-se", "inscreva-se",
)
URL_RE = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|io|net|org|co)\b")


def fetch_json(url, timeout=45):
    # `HEADERS` pede gzip: sem passar pelo `_decompress` do qxsocial o json.loads
    # recebe bytes comprimidos e falha com "Expecting value: line 1 column 1".
    st, raw, _ = http_get(url, timeout)
    if st != 200:
        raise RuntimeError("http-%d" % st)
    return json.loads(raw.decode("utf-8", "replace"))


def main_region(page):
    """So o card do POST. A permalink publica serve, embaixo, ate 7 cards de
    "More Relevant Posts" de OUTROS autores, cada um com o proprio
    `data-native-document-config`. Pegar o primeiro match da pagina inteira e
    falso-positivo: em 2026-08-23 tres posts das empresas-alvo foram
    classificados como carrossel por causa disso, e um deles chegou a render
    transcript de um deck de terceiro (`HFT Optimization Case Study`, autor
    `Ahmed Hassan`) atribuido a MarketAxess. O corte usa a classe do card,
    `base-main-feed-card`, que independe de idioma - o texto "More Relevant
    Posts" nao existe nas paginas em espanhol."""
    pos = [m.start() for m in re.finditer(r"base-main-feed-card", page)]
    return page[:pos[1]] if len(pos) > 1 else page


def doc_config(page, autor=None):
    m = re.search(r'data-native-document-config="([^"]+)"', main_region(page))
    if not m:
        return None
    try:
        cfg = json.loads(htmlmod.unescape(m.group(1)))
    except Exception:
        return None
    # segunda trava: o documento tem que ser do autor do post.
    dono = (cfg.get("doc") or {}).get("authorTitle", "")
    if autor and dono and dono.strip().lower() != autor.strip().lower():
        return None
    return cfg


def classify(page, post=None):
    """Que midia o post carrega. Barato: so olha o HTML servido."""
    autor = ((post or {}).get("author") or {}).get("name")
    if doc_config(page, autor):
        return "documento"
    if (post or {}).get("video"):
        return "video"
    if (post or {}).get("image"):
        return "imagem"
    if '"@type":"VideoObject"' in main_region(page) or 'property="og:video' in page:
        return "video"
    if 'data-test-id="article-content"' in main_region(page):
        return "link-artigo"
    if re.search(r'og:image"\s+content="https://media\.licdn\.com/dms/image/[^"]*image-shrink', page):
        return "imagem"
    return "so-texto"


def words(s):
    return [w for w in re.findall(r"[^\s]+", s) if re.search(r"[0-9A-Za-zÀ-ÿ]", w)]


def page_numbered(pages):
    """Numeracao de pagina: quantas paginas terminam (ou comecam) com o proprio
    indice, isolado ou em `n/N`."""
    hits = 0
    for i, t in enumerate(pages, 1):
        toks = t.split()
        if not toks:
            continue
        # titulo em caixa alta espacado letra a letra (`2 0 2 5  W R A P P E D`)
        # coloca digito solto na borda e vira numeracao falsa. Descarta a borda
        # quando ela e uma sequencia de caracteres soltos.
        while len(toks) > 4 and all(len(x) == 1 for x in toks[:4]):
            toks = toks[1:]
        while len(toks) > 4 and all(len(x) == 1 for x in toks[-4:]):
            toks = toks[:-1]
        edge = " ".join(toks[:2] + toks[-2:])
        if re.search(r"(?<!\d)%d\s*/\s*%d(?!\d)" % (i, len(pages)), edge):
            hits += 1
        elif re.fullmatch(r"0?%d" % i, toks[-1]) or re.fullmatch(r"0?%d" % i, toks[0]):
            hits += 1
    return hits


def compact(s):
    """Sem espaco e sem pontuacao. O transcript devolve titulo em caixa alta
    espacado letra a letra (`2 0 2 5  W R A P P E D`) - comparar token a token
    perde a repeticao, que existe."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def repeticao_entre_paginas(pages):
    """Texto que se repete em TODA pagina interna - a "moldura" do template
    (titulo corrido, marca, secao). Nao usa o titulo do documento como chave:
    a Bloomberg repete `2025 WRAPPED` em todas as paginas enquanto o titulo do
    arquivo e `Bloomberg 2025 Wrapped`, e casar pelo titulo dava zero.

    ATENCAO: o transcript nao traz coordenada. Isto mede REPETICAO, nao posicao -
    nao da para afirmar pelo texto que a repeticao esta no rodape."""
    alvo = [compact(t) for t in pages[1:] if t.strip()]
    if len(alvo) < 2:
        return ""
    ref = min(alvo, key=len)
    outros = [a for a in alvo if a is not ref]
    for L in range(min(40, len(ref)), 7, -1):
        for i in range(len(ref) - L + 1):
            s = ref[i:i + L]
            if all(s in o for o in outros):
                return s
    return ""


def scrape_doc(url, timeout=45):
    st, raw, final = http_get(url, timeout)
    page = raw.decode("utf-8", "replace")
    if st != 200:
        return dict(status="http-%d" % st, url=url)
    post = find_posting(ldjson_blocks(page))
    cfg = doc_config(page, ((post or {}).get("author") or {}).get("name"))
    kind = classify(page, post)
    body = htmlmod.unescape((post or {}).get("articleBody") or "").strip()
    data = ((post or {}).get("datePublished") or "")[:10]
    out = dict(url=final, midia=kind, data_post=data,
               palavras_post=len(words(re.sub(r"(?<!\w)#\w[\w-]*", " ", body))) if body else "",
               hook=" / ".join([l.strip() for l in body.split("\n") if l.strip()][:2])[:200])
    if not cfg:
        out["status"] = "nao-documento"
        return out
    doc = cfg.get("doc", {})
    out.update(status="ok", doc_titulo=doc.get("title", ""),
               paginas=doc.get("totalPageCount"), doc_tipo=doc.get("type", ""))
    pages = []
    try:
        man = fetch_json(doc["manifestUrl"], timeout)
        tr = fetch_json(man["transcriptManifestUrl"], timeout)
        pages = [(p or "").strip() for p in tr.get("pages", [])]
    except Exception as e:
        out["transcript_erro"] = str(e)[:80]
    out["pages"] = pages
    com_texto = [p for p in pages if p]
    out["paginas_com_texto"] = len(com_texto)
    if com_texto:
        wc = [len(words(p)) for p in pages]
        out["palavras_total"] = sum(wc)
        out["palavras_por_pagina_mediana"] = round(statistics.median([w for w in wc if w]), 1)
        out["palavras_capa"] = wc[0]
        out["palavras_ultima"] = wc[-1]
        low = pages[-1].lower()
        out["ultima_e_cta"] = "sim" if (any(k in low for k in CTA_MARKS)
                                        or URL_RE.search(low)) else "nao"
        out["tem_numeracao"] = "%d/%d" % (page_numbered(pages), len(pages))
        rep = repeticao_entre_paginas(pages)
        out["titulo_repetido"] = ("sim:" + rep) if rep else "nao"
    return out


COLS = ["ts", "empresa", "plataforma", "url", "data_post", "doc_titulo", "paginas",
        "paginas_com_texto", "palavras_total", "palavras_por_pagina_mediana",
        "palavras_capa", "palavras_ultima", "ultima_e_cta", "tem_numeracao",
        "titulo_repetido", "palavras_post", "fonte", "nota"]

FONTE = "data-native-document-config + transcriptManifestUrl da permalink publica"


def row(empresa, r, plataforma="linkedin", prefix=""):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    nota = sanitize(prefix + "tipo=%s; " % r.get("doc_tipo", "") + "hook: " + r.get("hook", ""))
    vals = dict(ts=ts, empresa=empresa, plataforma=plataforma, fonte=FONTE, nota=nota)
    for c in COLS:
        if c not in vals:
            vals[c] = r.get(c, "")
    return ",".join(csv_field(sanitize(str(vals[c])) if c in ("doc_titulo", "nota") else vals[c]) for c in COLS)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*")
    ap.add_argument("--empresa", default="")
    ap.add_argument("--plataforma", default="linkedin")
    ap.add_argument("--classify", action="store_true", help="so diz que midia o post carrega")
    ap.add_argument("--text", action="store_true", help="imprime o texto de cada pagina")
    ap.add_argument("--header", action="store_true", help="imprime o cabecalho do CSV e sai")
    ap.add_argument("--nota-prefix", default="")
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()

    if args.header:
        print(",".join(COLS))
        return
    for i, u in enumerate(args.urls):
        if i:
            time.sleep(args.sleep)
        r = scrape_doc(u, args.timeout)
        if args.classify:
            print("%s\t%s\t%s\t%s" % (r.get("midia", "?"), r.get("paginas", ""), r.get("data_post", ""), u))
            continue
        if r.get("status") != "ok":
            print("# FALHA\t%s\t%s" % (r.get("status"), u), file=sys.stderr)
            continue
        if not args.empresa:
            print(json.dumps({k: v for k, v in r.items() if k != "pages"}, ensure_ascii=False, indent=1))
        else:
            print(row(args.empresa, r, args.plataforma, prefix=args.nota_prefix))
        if args.text:
            for n, p in enumerate(r.get("pages", []), 1):
                print("--- p%d (%d palavras) ---" % (n, len(words(p))))
                print(p if p else "[sem camada de texto]")


if __name__ == "__main__":
    main()
