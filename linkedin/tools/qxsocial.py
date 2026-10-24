#!/usr/bin/env python3
"""qxsocial.py - mede a FORMA de um post publico de rede social.

Existe porque a particao `QX-HARVEST part=social` precisa trocar a regra escrita
a mao da skill `content-repurposer` (120-250 palavras no LinkedIn) por medicao.
Medir a mao 30 posts e inviavel e nao e reprodutivel; esta ferramenta le a pagina
publica do post e devolve a linha pronta do `workdir/harvest/social/benchmarks.csv`.

O que ela usa (tudo publico, sem login e sem contorno de credencial):
  - o bloco `application/ld+json` do tipo SocialMediaPosting que o LinkedIn serve
    na permalink publica `linkedin.com/posts/<slug>_<hash>`: `articleBody`,
    `datePublished`, `commentCount`, `image`/`video`;
  - o atributo `data-num-reactions` do proprio HTML, que e o contador publico de
    reacoes. **So isso conta como engajamento.** Nao ha estimativa em lugar nenhum:
    se o numero nao vier, os campos saem vazios.

A permalink de post e publica; o FEED (`/company/<x>/posts/`) exige login e devolve
authwall. A ferramenta reconhece o authwall e devolve `login-wall` em vez de fingir
que leu algo.

Convencoes de medicao (fixadas aqui para a contagem ser reprodutivel):
  palavras     tokens do corpo, **descontando** hashtags soltas e URLs - as duas
               tem coluna propria e inflariam a contagem de texto.
  linhas_hook  quantas linhas do corpo cabem nos primeiros 210 caracteres, que e
               onde o LinkedIn desktop corta com "ver mais". Linha vazia nao conta.
  paragrafos   blocos separados por linha em branco.
  cta          `link` | `pergunta` | `imperativo` | combinacoes com `+` | `nenhum`.

Uso:
    python3 tools/qxsocial.py --empresa MarketAxess <url> [<url> ...]   # linhas CSV
    python3 tools/qxsocial.py --empresa X --text <url>                  # + o corpo
    python3 tools/qxsocial.py --empresa X --json <url>                  # tudo cru
"""
import argparse
import gzip
import html as htmlmod
import json
import re
import sys
import time
import urllib.error
import unicodedata
import urllib.request
import zlib
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
}

HOOK_CHARS = 210          # corte do "ver mais" no LinkedIn desktop
IMPERATIVOS = (
    "find out more", "learn more", "read more", "read the", "register", "sign up",
    "download", "join us", "watch", "discover", "explore", "click", "visit",
    "get in touch", "contact us", "book a", "request a", "subscribe", "see how",
    "saiba mais", "leia", "assista", "inscreva", "baixe", "acesse", "confira",
    "cadastre", "participe", "veja",
)


def _decompress(raw, enc):
    if enc == "gzip":
        try:
            return gzip.decompress(raw)
        except Exception:
            return raw
    if enc == "deflate":
        for wb in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
            try:
                return zlib.decompress(raw, wb)
            except Exception:
                pass
    return raw


def http_get(url, timeout=45):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, _decompress(r.read(), r.headers.get("Content-Encoding", "")), r.geturl()
    except urllib.error.HTTPError as e:
        try:
            body = _decompress(e.read(), e.headers.get("Content-Encoding", ""))
        except Exception:
            body = b""
        return e.code, body, url
    except Exception:
        return 0, b"", url


def ldjson_blocks(page):
    out = []
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
        raw = htmlmod.unescape(m.group(1)).strip()
        try:
            out.append(json.loads(raw))
        except Exception:
            continue
    return out


def find_posting(blocks):
    stack = list(blocks)
    while stack:
        b = stack.pop(0)
        if isinstance(b, list):
            stack.extend(b)
        elif isinstance(b, dict):
            if b.get("@type") in ("SocialMediaPosting", "DiscussionForumPosting"):
                return b
            stack.extend([v for v in b.values() if isinstance(v, (dict, list))])
    return None


def is_authwall(page):
    low = page.lower()
    return ("authwall" in low or "/uas/login" in low
            or "sign in to see" in low
            or ("entrar no linkedin" in low and "articlebody" not in low))


def strip_urls(text):
    return re.sub(r'https?://\S+|\b\w+\.(?:com|io|net|org|to|ly)/\S+', ' ', text)


def measure(body):
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")

    hashtags = re.findall(r'(?<!\w)#\w[\w-]*', body)
    no_tags = re.sub(r'(?<!\w)#\w[\w-]*', ' ', body)
    words = [w for w in re.findall(r"[^\s]+", strip_urls(no_tags))
             if re.search(r'[0-9A-Za-zÀ-ÿ]', w)]

    # linhas do hook: as que comecam antes do corte de 210 caracteres
    hook_lines, used = 0, 0
    for ln in lines:
        if used >= HOOK_CHARS:
            break
        if ln.strip():
            hook_lines += 1
        used += len(ln) + 1

    paras = [p for p in re.split(r'\n\s*\n', body) if p.strip()]

    low = body.lower()
    cta = []
    if re.search(r'https?://|\b\w+\.(?:com|io|to|ly)/', body):
        cta.append("link")
    if "?" in body:
        cta.append("pergunta")
    if any(k in low for k in IMPERATIVOS):
        cta.append("imperativo")
    return dict(
        palavras=len(words),
        linhas_hook=hook_lines,
        paragrafos=len(paras),
        hashtags=len(hashtags),
        hashtag_list=hashtags,
        cta="+".join(cta) if cta else "nenhum",
        hook_text=" / ".join([l.strip() for l in lines if l.strip()][:2])[:220],
    )


def scrape(url, timeout=45):
    st, raw, final = http_get(url, timeout)
    page = raw.decode("utf-8", "replace")
    if st != 200:
        return dict(status="http-%d" % st, url=url)
    post = find_posting(ldjson_blocks(page))
    body = ""
    if post:
        body = post.get("articleBody") or ""
    if not body:
        m = re.search(r'attributed-text-segment-list__content[^>]*>(.*?)</p>', page, re.S)
        if m:
            body = re.sub(r'<[^>]+>', '', htmlmod.unescape(m.group(1)))
    if not body.strip():
        # so aqui o authwall importa: a permalink publica LINKA para o authwall em
        # varios botoes mesmo quando serve o post inteiro, entao a presenca do
        # marcador nao prova bloqueio - a ausencia do corpo e que prova.
        return dict(status="login-wall" if is_authwall(page) else "js-render", url=url)

    body = htmlmod.unescape(body).strip()

    reactions = None
    m = re.search(r'data-num-reactions="(\d+)"', page)
    if m:
        reactions = int(m.group(1))
    comments = None
    if post and isinstance(post.get("commentCount"), int):
        comments = post["commentCount"]
    else:
        m = re.search(r'data-num-comments="(\d+)"', page)
        if m:
            comments = int(m.group(1))

    data = post.get("datePublished", "") if post else ""
    if not data:
        m = re.search(r'"datePublished":"([^"]+)"', page)
        data = m.group(1) if m else ""

    has_img = bool((post or {}).get("image")) or 'property="og:image"' in page
    vid = (post or {}).get("video")
    has_vid = bool(vid) or 'property="og:video' in page or '"@type":"VideoObject"' in page
    # og:image existe ate em post so de texto (avatar da empresa); so conta imagem
    # de midia real, servida do CDN de imagem de post
    if not (post or {}).get("image"):
        has_img = bool(re.search(r'og:image"\s+content="https://media\.licdn\.com/dms/image/[^"]*image-shrink', page))

    out = measure(body)
    out.update(status="ok", url=final, body=body, data_post=data[:10],
               reactions=reactions, comments=comments,
               tem_imagem="sim" if has_img else "nao",
               tem_video="sim" if has_vid else "nao")
    return out


ORNAMENTOS = {
    "—": "-", "–": "-", "‒": "-", "‐": "-", "‑": "-",
    "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'",
    "‚": "'", "…": "...", "·": "-", "•": "-", " ": " ",
    "​": "", "‌": "", "‍": "", "️": "", "→": "->",
    "←": "<-", "↔": "<->", "⇒": "=>", "≤": "<=", "≥": ">=",
    "™": "(TM)", "‹": "<", "›": ">", "«": '"', "»": '"',
}
PERMITIDO_EXTRA = "®"


def emoji_names(s):
    """Nomes dos simbolos fora do conjunto permitido. Emoji no hook e DADO DE FORMA:
    saber que a empresa abre post com foguete importa para o benchmark, entao o
    simbolo e descrito por nome em vez de apagado."""
    nomes = []
    for ch in s:
        if ord(ch) < 128 or ch in ORNAMENTOS or ch == PERMITIDO_EXTRA:
            continue
        if unicodedata.category(ch) in ("Ll", "Lu", "Lt", "Lm", "Lo") and ord(ch) < 0x0500:
            continue  # letra acentuada do portugues e afins - fica
        try:
            nomes.append(unicodedata.name(ch).lower())
        except ValueError:
            nomes.append("u+%04x" % ord(ch))
    return nomes


def sanitize(s):
    """ASCII + acentos do portugues + marca registrada (regra dura do runbook).
    Ornamento tipografico vira o equivalente ASCII; simbolo/emoji vira o nome
    entre colchetes, para a citacao do hook sobreviver sem quebrar o charset."""
    out = []
    for ch in s:
        if ch in ORNAMENTOS:
            out.append(ORNAMENTOS[ch])
        elif ord(ch) < 128 or ch == PERMITIDO_EXTRA:
            out.append(ch)
        elif unicodedata.category(ch) in ("Ll", "Lu", "Lt", "Lm", "Lo") and ord(ch) < 0x0500:
            out.append(ch)
        else:
            try:
                out.append("[%s]" % unicodedata.name(ch).lower())
            except ValueError:
                out.append("[u+%04x]" % ord(ch))
    return "".join(out)


def csv_field(s):
    s = str(s).replace('"', "'").replace("\n", " ").replace("\r", " ")
    return '"%s"' % s if ("," in s or '"' in s) else s


def row(empresa, r, plataforma="linkedin", nota="", prefix=""):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    eng, fonte = "", ""
    if r.get("reactions") is not None:
        eng = "reac=%d" % r["reactions"]
        if r.get("comments") is not None:
            eng += ";com=%d" % r["comments"]
        fonte = "contador publico na permalink (data-num-reactions + ld+json commentCount)"
    if not nota:
        emos = emoji_names(r.get("hook_text", ""))
        pre = "emoji=%d(%s); " % (len(emos), ";".join(sorted(set(emos))[:3])) if emos else ""
        nota = sanitize(prefix + pre + "hook: " + r.get("hook_text", ""))
    cols = [ts, empresa, plataforma, r["url"], r.get("data_post", ""),
            r["palavras"], r["linhas_hook"], r["paragrafos"], r["hashtags"],
            r["tem_imagem"], r["tem_video"], r["cta"], eng, fonte, nota]
    return ",".join(csv_field(c) for c in cols)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--empresa", required=True)
    ap.add_argument("--plataforma", default="linkedin")
    ap.add_argument("--text", action="store_true", help="imprime tambem o corpo")
    ap.add_argument("--json", action="store_true", help="imprime o dict cru")
    ap.add_argument("--nota-prefix", default="", help="texto no inicio da nota (ex.: conta=<slug>; )")
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--timeout", type=int, default=45)
    args = ap.parse_args()

    for i, u in enumerate(args.urls):
        if i:
            time.sleep(args.sleep)
        r = scrape(u, args.timeout)
        if r.get("status") != "ok":
            print("# FALHA\t%s\t%s" % (r.get("status"), u), file=sys.stderr)
            continue
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
            continue
        print(row(args.empresa, r, args.plataforma, prefix=args.nota_prefix))
        if args.text:
            print("----- corpo -----")
            print(r["body"])
            print("----- fim -----")


if __name__ == "__main__":
    main()
