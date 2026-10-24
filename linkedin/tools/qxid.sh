#!/bin/sh
# Compute a backlog item id from a working title.  Usage: tools/qxid.sh "Meu Título"
#
# Do NOT use `tr 'A-Z' 'a-z'` for this: tr is byte-wise and does not lowercase accented
# characters, so "Precificação" and "PRECIFICAÇÃO" hash differently and the dedupe that the
# whole deterministic-id design depends on silently fails on Portuguese titles.
printf '%s' "$1" | python3 -c '
import sys, hashlib, unicodedata
s = unicodedata.normalize("NFC", " ".join(sys.stdin.read().lower().split()))
print("QXB-" + hashlib.sha1(s.encode()).hexdigest()[:8])'
