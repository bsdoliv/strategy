#!/usr/bin/env python3
"""qxfetch.py - a escada de tentativas do QX-HARVEST, automatizada.

O runbook manda subir degrau por degrau antes de declarar uma fonte perdida.
Fazer isso a mao custa 4 a 6 comandos por URL, entao na pratica ninguem sobe a
escada inteira - foi assim que 7 fontes viraram `skipped` em 2026-08-23 sem uma
unica tentativa alternativa registrada. Esta ferramenta faz os degraus 1, 3 e 4
numa chamada e devolve ja o `fetch_status` e o `tried=` prontos para a linha do
`ledger/manifest.csv`.

Degraus implementados (na ordem em que sao tentados):
  ua-browser  degrau 3 - User-Agent de browser real + Accept-Language
  amp         degrau 1 - outro caminho da mesma fonte (/amp, ?amp)
  archive.org degrau 4 - copia legitima na Wayback Machine

Degraus 2 (JSON do front / API do SPA) e 5 (escrever ferramenta) continuam
sendo trabalho humano: dependem de olhar o bundle da pagina. Quando o texto
extraido vier curto e a pagina tiver `__NEXT_DATA__`, `ld+json` ou um
`/graphql`, a saida avisa `hint=` com o que procurar.

Nao contorna login, captcha, formulario de lead nem paywall - por decisao do
runbook, texto obtido por contorno nao e citavel num blog institucional.

Uso:
    python3 tools/qxfetch.py <url> [<url> ...]        # texto no stdout
    python3 tools/qxfetch.py --text-dir DIR <url>...  # salva o texto por URL
    python3 tools/qxfetch.py --report <url>...        # so o status, uma linha por URL

Saida do --report, pronta para colar na nota do manifest:
    <url>\t<fetch_status>\ttried=<degrau>+<degrau>\t<chars>\t<title>

Sem dependencia externa: urllib da stdlib.
"""

import argparse
import gzip
import html
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}

# Marcadores de bloqueio na PAGINA (nao no status HTTP), em duas forcas.
# A distincao nao e cosmetica: a primeira versao desta ferramenta tratava
# "captcha" como prova de bloqueio e marcou GitHub, InfoMoney, interop.io,
# theScreener e Peak Technology como `bot-block` - todas HTTP 200 com o texto
# inteiro servido. A palavra aparece em qualquer pagina que carregue reCAPTCHA
# num formulario de comentario ou newsletter. Marcador fraco so vale se a
# pagina tambem vier vazia.
BOT_MARKERS_STRONG = ("are you a robot", "access denied", "pardon our interruption",
                      "attention required! | cloudflare", "checking your browser before")
BOT_MARKERS_WEAK = ("captcha", "simple page", "enable javascript and cookies")
BOT_MARKERS = BOT_MARKERS_STRONG + BOT_MARKERS_WEAK

MIN_CHARS = 600  # abaixo disso a pagina e casca, nao conteudo

# Muro de login. Bug encontrado pelo `h-social` em 2026-08-23: as tres paginas de
# feed (`linkedin.com/company/<x>/posts/`) devolviam HTTP 200 com ~950 chars de
# formulario de login, e o `--report` dizia `ok` - o agente registraria muro como
# fonte lida. `login-wall` ja estava no vocabulario do manifest e nao tinha
# deteccao nenhuma aqui. Regra: titulo de pagina de login decide sozinho; marcador
# no corpo so vale se a pagina tambem vier curta, pela mesma razao que o marcador
# fraco de bot: "sign in" aparece no menu de qualquer site.
LOGIN_TITLES = ("entrar no linkedin", "sign up | linkedin", "log in or sign up",
                "sign in | linkedin", "iniciar sesion", "inicia sesion",
                "sign in to", "log in | ", "login | ", "entrar | ")
LOGIN_MARKERS = ("sign in to continue", "sign in to see", "please log in to",
                 "faca login para continuar", "join linkedin", "authwall",
                 "you must be logged in", "members only", "create an account to")

# marcadores de conteudo servido so por JS
JS_MARKERS = ("__next_data__", "__nuxt__", "window.__initial")


def _decompress(raw, encoding):
    if encoding == "gzip":
        try:
            return gzip.decompress(raw)
        except Exception:
            return raw
    if encoding == "deflate":
        try:
            return zlib.decompress(raw)
        except Exception:
            try:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except Exception:
                return raw
    return raw


def http_get(url, timeout=45):
    """Devolve (status, body_bytes, final_url). Nunca levanta por status HTTP."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = _decompress(r.read(), r.headers.get("Content-Encoding", ""))
            return r.status, raw, r.geturl()
    except urllib.error.HTTPError as e:
        raw = _decompress(e.read(), e.headers.get("Content-Encoding", "") if e.headers else "")
        return e.code, raw, url
    except Exception as e:
        return 0, str(e).encode("utf-8", "replace"), url


def to_text(body):
    """HTML -> texto legivel. Serve para julgar se a pagina tem conteudo."""
    try:
        s = body.decode("utf-8")
    except UnicodeDecodeError:
        s = body.decode("latin-1", "replace")
    s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
    s = re.sub(r"(?is)<(h1|h2|h3|h4|p|li|br|tr|div)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def title_of(body):
    try:
        s = body.decode("utf-8", "replace")
    except Exception:
        return ""
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", s)
    return html.unescape(m.group(1)).strip().replace("\n", " ")[:160] if m else ""


def looks_blocked(body, text=None):
    """Bloqueio de bot? Marcador forte decide sozinho; fraco so com pagina vazia."""
    low = body[:200000].decode("utf-8", "replace").lower()
    if any(m in low for m in BOT_MARKERS_STRONG):
        return True
    if text is None:
        text = to_text(body)
    return len(text) < MIN_CHARS and any(m in low for m in BOT_MARKERS_WEAK)


def looks_walled(body, text=None, title=""):
    """Muro de login? Devolve True so quando a pagina servida E o formulario."""
    t = (title or "").lower()
    if any(m in t for m in LOGIN_TITLES):
        return True
    low = body[:200000].decode("utf-8", "replace").lower()
    if text is None:
        text = to_text(body)
    return len(text) < 3000 and any(m in low for m in LOGIN_MARKERS)


def hints(body):
    low = body[:400000].decode("utf-8", "replace").lower()
    out = []
    if any(m in low for m in JS_MARKERS):
        out.append("json-no-html")
    if "application/ld+json" in low:
        out.append("ld+json")
    if "/graphql" in low:
        out.append("graphql")
    if "mktoform" in low or "marketo" in low:
        out.append("marketo-form")
    return "+".join(out)


def amp_variants(url):
    p = urllib.parse.urlsplit(url)
    yield urllib.parse.urlunsplit((p.scheme, p.netloc, p.path.rstrip("/") + "/amp", p.query, ""))
    sep = "&" if p.query else ""
    yield urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, p.query + sep + "amp", ""))


def wayback(url, timeout=45):
    """Snapshot mais recente na Wayback. Devolve (status, body, snapshot_url)."""
    api = "http://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
    st, raw, _ = http_get(api, timeout=timeout)
    if st != 200:
        return 0, b"", ""
    try:
        snap = json.loads(raw.decode("utf-8", "replace"))
        snap = snap["archived_snapshots"]["closest"]
        if not snap.get("available"):
            return 0, b"", ""
        ts = snap["timestamp"]
    except Exception:
        return 0, b"", ""
    # `id_` devolve o original, sem a barra de navegacao da Wayback
    raw_url = "http://web.archive.org/web/%sid_/%s" % (ts, url)
    st2, body, _ = http_get(raw_url, timeout=timeout * 2)
    return st2, body, raw_url


def climb(url, timeout=45, sleep=1.0):
    """Sobe a escada. Devolve dict com status, tried, texto e a URL que serviu."""
    tried = []
    best = None

    st, body, final = http_get(url, timeout)
    tried.append("ua-browser")
    text = to_text(body) if body else ""
    blocked = st in (403, 429) or (st == 200 and looks_blocked(body, text))
    walled = st == 200 and looks_walled(body, text, title_of(body))
    if walled:
        blocked = True   # sobe a escada igual: amp e archive as vezes vem sem o muro
    if st == 200 and not blocked and len(text) >= MIN_CHARS:
        return dict(status="ok", tried=tried, text=text, used=final,
                    title=title_of(body), hint=hints(body), http=st)
    if st == 200 and not blocked:
        best = dict(status="js-render", tried=list(tried), text=text, used=final,
                    title=title_of(body), hint=hints(body), http=st)

    if blocked:
        time.sleep(sleep)
        for v in amp_variants(url):
            st2, body2, final2 = http_get(v, timeout)
            t2 = to_text(body2)
            if st2 == 200 and not looks_blocked(body2, t2) and not looks_walled(body2, t2, title_of(body2)):
                if len(t2) >= MIN_CHARS:
                    tried.append("amp")
                    return dict(status="ok", tried=tried, text=t2, used=final2,
                                title=title_of(body2), hint=hints(body2), http=st2)
        tried.append("amp")

    time.sleep(sleep)
    st3, body3, snap = wayback(url, timeout)
    tried.append("archive.org")
    if st3 == 200 and body3:
        t3 = to_text(body3)
        if (len(t3) >= MIN_CHARS and not looks_blocked(body3, t3)
                and not looks_walled(body3, t3, title_of(body3))):
            return dict(status="ok", tried=tried, text=t3, used=snap,
                        title=title_of(body3), hint=hints(body3), http=st3)

    if best:
        best["tried"] = tried
        return best
    if st == 404:
        return dict(status="404", tried=tried, text="", used=url, title="", hint="", http=st)
    if walled:
        return dict(status="login-wall", tried=tried, text="", used=url,
                    title=title_of(body), hint=hints(body), http=st)
    if blocked:
        return dict(status="bot-block", tried=tried, text="", used=url,
                    title=title_of(body), hint=hints(body), http=st)
    return dict(status="js-render", tried=tried, text=text, used=url,
                title=title_of(body), hint=hints(body), http=st)


def slug(url):
    p = urllib.parse.urlsplit(url)
    s = (p.netloc + p.path).strip("/")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)[:120] or "index"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--text-dir", help="salva o texto de cada URL neste diretorio")
    ap.add_argument("--report", action="store_true", help="so a linha de status")
    ap.add_argument("--timeout", type=int, default=45)
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="intervalo entre requisicoes, para nao virar bot (default 1s)")
    ap.add_argument("--max-chars", type=int, default=0,
                    help="corta o texto impresso (0 = inteiro)")
    a = ap.parse_args()

    import os
    if a.text_dir:
        os.makedirs(a.text_dir, exist_ok=True)

    for u in a.urls:
        r = climb(u, a.timeout, a.sleep)
        tried = "tried=" + "+".join(r["tried"])
        if r["hint"]:
            tried += "; hint=" + r["hint"]
        if a.report or a.text_dir:
            print("%s\t%s\t%s\t%d\t%s" % (u, r["status"], tried, len(r["text"]), r["title"]),
                  flush=True)
        if a.text_dir:
            with open(os.path.join(a.text_dir, slug(u) + ".txt"), "w", encoding="utf-8") as f:
                f.write("URL: %s\nUSED: %s\nSTATUS: %s\n%s\nTITLE: %s\n\n%s\n"
                        % (u, r["used"], r["status"], tried, r["title"], r["text"]))
        if not a.report and not a.text_dir:
            print("===== %s [%s] %s" % (u, r["status"], tried))
            print("TITLE:", r["title"])
            print(r["text"][:a.max_chars] if a.max_chars else r["text"])
            print()
        time.sleep(a.sleep)


if __name__ == "__main__":
    main()
