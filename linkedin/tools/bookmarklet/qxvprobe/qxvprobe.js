/* qxvprobe - sonda de DIAGNOSTICO. Nao captura post, nao entra no pipeline.
 *
 * Responde UMA pergunta: o video de um post do LinkedIn tem URL de arquivo que da para `fetch`,
 * ou e MediaSource (`blob:`) com o conteudo fatiado em segmentos?
 *
 * Disso depende se o download de video cabe no `qxgrab` (um fetch, um arquivo) ou se precisa de
 * uma ferramenta separada que baixe manifesto e junte segmento. Enquanto nao rodar isso numa
 * pagina de verdade, qualquer resposta e chute - inclusive a minha.
 *
 * Uso: abrir um post de video no LinkedIn logado e clicar. Baixa qx-VPROBE-<id>.json.
 */
(function () {
  var corta = function (s, n) { s = String(s == null ? '' : s); return s.length > n ? s.slice(0, n) + '...[+' + (s.length - n) + ']' : s; };

  /* 1. Todo <video> da pagina, com os atributos do proprio e do pai - o player costuma guardar
        as fontes num `data-*` do WRAPPER, nao do <video>. */
  var vids = [];
  var vs = document.getElementsByTagName('video');
  for (var i = 0; i < vs.length; i++) {
    var v = vs[i], at = {}, pa = {};
    for (var a = 0; a < v.attributes.length; a++) at[v.attributes[a].name] = corta(v.attributes[a].value, 1500);
    var p = v.parentElement;
    if (p) for (var b = 0; b < p.attributes.length; b++) pa[p.attributes[b].name] = corta(p.attributes[b].value, 1500);
    var srcs = [], ss = v.getElementsByTagName('source');
    for (var c = 0; c < ss.length; c++) srcs.push({ src: corta(ss[c].src, 400), type: ss[c].type || '' });
    vids.push({
      src: corta(v.src, 400), currentSrc: corta(v.currentSrc, 400),
      /* a resposta esta aqui: `blob:` = MediaSource, precisa de segmento; `https:` = arquivo */
      eh_blob: /^blob:/.test(v.currentSrc || v.src || ''),
      poster: corta(v.poster, 400), duracao: v.duration, readyState: v.readyState,
      atributos: at, atributos_do_pai: pa, source_filhos: srcs,
      pai_tag: p ? p.tagName : '', pai_classe: p ? corta(p.className, 200) : ''
    });
  }

  /* 2. O HTML inteiro pode conter a URL do arquivo mesmo que o DOM nao mostre: o LinkedIn embute
        JSON em <code>. Procuro os padroes de midia do CDN, sem depender de nome de classe. */
  var html = document.documentElement.innerHTML;
  var padroes = {
    playlist: /https:\\?\/\\?\/dms\.licdn\.com\\?\/playlist[^"'\s\\]{0,300}/g,
    mp4: /https:[^"'\s\\]{0,300}\.mp4[^"'\s\\]{0,120}/g,
    m3u8: /https:[^"'\s\\]{0,300}\.m3u8[^"'\s\\]{0,120}/g,
    mpd: /https:[^"'\s\\]{0,300}\.mpd[^"'\s\\]{0,120}/g,
    videocover: /https:[^"'\s\\]{0,300}videocover[^"'\s\\]{0,120}/g
  };
  var achados = {};
  for (var k in padroes) {
    var m = html.match(padroes[k]) || [], u = [];
    for (var j = 0; j < m.length && u.length < 6; j++) if (u.indexOf(m[j]) < 0) u.push(corta(m[j], 400));
    achados[k] = { total: m.length, amostra: u };
  }

  var id = (location.href.match(/(?:activity|ugcPost|share)[:-](\d{6,})/i) || ['', 'sem-id'])[1];
  var d = { sonda: 'qxvprobe', versao: 1, url: location.href, quando: new Date().toISOString(),
            html_chars: html.length, videos_no_dom: vids.length, videos: vids, urls_no_html: achados };

  var bl = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' });
  var an = document.createElement('a');
  an.href = URL.createObjectURL(bl); an.download = 'qx-VPROBE-' + id + '.json';
  document.body.appendChild(an); an.click();
  setTimeout(function () { document.body.removeChild(an); URL.revokeObjectURL(an.href); }, 1000);

  var r = vids.length ? (vids[0].eh_blob ? 'blob: (MediaSource - precisa de segmento)'
                                         : 'URL de arquivo (da para fetch)') : 'nenhum <video> no DOM';
  alert('qxvprobe: ' + vids.length + ' <video> | ' + r + '\n\n' +
        'playlist ' + achados.playlist.total + ' | mp4 ' + achados.mp4.total +
        ' | m3u8 ' + achados.m3u8.total + ' | mpd ' + achados.mpd.total + '\n\n' +
        'Baixei qx-VPROBE-' + id + '.json em Downloads.');
})();
