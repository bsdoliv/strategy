/* qxdprobe - sonda de DIAGNOSTICO para post de DOCUMENTO (PDF anexo). Nao captura post.
 *
 * Irma do `qxvprobe.js`, e pela mesma razao: no caso do video, a v8 do `qxgrab` embutiu uma
 * SUPOSICAO sobre como o LinkedIn entrega midia, errou, e o conserto custou uma ferramenta
 * inteira (`qxvideo`). Aqui a pergunta e a mesma, trocando video por PDF:
 *
 *   o PDF original de um post de documento tem URL que `fetch` alcanca da pagina logada,
 *   ou o LinkedIn so entrega o documento RASTERIZADO, uma imagem por pagina?
 *
 * O que ja e FATO, medido nas capturas que existem em `linkedin/` (traditiondata, waltertukahiirwa):
 * as paginas chegam como `feedshare-document-images_800/<tag>/<n>/<ts>`, uma URL por pagina,
 * numeradas a partir de 1, e o `alt` de cada imagem traz o texto TRANSCRITO da pagina. O que
 * NAO se sabe: (a) se existe o PDF de verdade em algum lugar do HTML, e (b) se as paginas no
 * DOM sao TODAS - o visualizador carrega sob demanda, entao doc de 12 paginas pode ter deixado
 * 3 no DOM e o `qxgrab` levaria 3 achando que levou o documento.
 *
 * Esta sonda responde as duas, e se achar PDF alcancavel JA BAIXA - entao no melhor caso voce
 * sai daqui com o arquivo na mao, nao so com o diagnostico.
 *
 * Uso: abrir o post de documento no LinkedIn logado, ROLAR O VISUALIZADOR ATE O FIM (para forcar
 * o carregamento de todas as paginas) e clicar. Baixa qx-DPROBE-<id>.json.
 */
(function () {
  var corta = function (s, n) {
    s = String(s == null ? '' : s);
    return s.length > n ? s.slice(0, n) + '...[+' + (s.length - n) + ']' : s;
  };
  /* dentro dos <code> o LinkedIn embute JSON, e ali a barra vem escapada como \/ */
  /* `split/join` e nao regex de proposito: a regex da barra escapada precisaria escrever duas
     barras seguidas no fonte, e o `compile.py` recusa isso - numa URL de favorito o `//` viraria
     comentario de linha e mataria o resto do bookmarklet. */
  var limpaUrl = function (u) {
    return u.split('\\/').join('/').split('\\u0026').join('&').split('&amp;').join('&');
  };

  var html = document.documentElement.innerHTML;

  /* 1. TODA url https do HTML, uma vez so, separada por assunto. Uma varredura, sem depender de
        nome de classe (que no LinkedIn e hasheado) nem de estrutura de DOM. */
  var brutas = html.match(/https:[^"'\s<>()]{4,500}/g) || [];
  var vistas = {}, baldes = { pdf: [], dms_document: [], document_images: [], outros_document: [] };
  for (var i = 0; i < brutas.length; i++) {
    var u = limpaUrl(brutas[i]);
    if (vistas[u]) continue;
    vistas[u] = 1;
    var b = null;
    if (/\.pdf(\?|$|&)/i.test(u)) b = 'pdf';
    else if (/dms\/document/i.test(u)) b = 'dms_document';
    else if (/feedshare-document-images/i.test(u)) b = 'document_images';
    else if (/document/i.test(u)) b = 'outros_document';
    if (b && baldes[b].length < 40) baldes[b].push(corta(u, 500));
  }

  /* 2. Chaves que o modelo de dados do feed usaria para apontar o documento. Se alguma existir,
        o valor dela vale mais que qualquer regex de URL - por isso vai com o contexto em volta. */
  var chaves = ['transcribedDocumentUrl', 'manifestUrl', 'totalPageCount', 'pageCount',
                'docUrl', 'documentUrl', 'DocumentComponent', 'feedshare-document-pdf',
                'com.linkedin.voyager.feed.render.Document'];
  var achadas = {};
  for (var c = 0; c < chaves.length; c++) {
    var alvo = chaves[c], pos = html.indexOf(alvo), n = 0, ctx = [];
    while (pos >= 0 && n < 2) {
      ctx.push(corta(html.slice(Math.max(0, pos - 120), pos + 320), 460));
      n++;
      pos = html.indexOf(alvo, pos + 1);
    }
    var tot = html.split(alvo).length - 1;
    if (tot) achadas[alvo] = { ocorrencias: tot, contexto: ctx };
  }

  /* 3. Quantas paginas o DOM tem AGORA, e quantas o documento diz ter. A diferenca entre as duas
        e o defeito silencioso: captura parcial que parece completa. */
  var paginas = [], imgs = document.getElementsByTagName('img');
  for (var k = 0; k < imgs.length; k++) {
    var src = imgs[k].currentSrc || imgs[k].src || '';
    if (src.indexOf('feedshare-document-images') < 0) continue;
    var m = src.match(/feedshare-document-images_(\d+)\/([^/]+)\/(\d+)[\/]/);
    paginas.push({ pagina: m ? Number(m[3]) : null, largura: m ? Number(m[1]) : null,
                   tem_alt: !!(imgs[k].alt || '').trim(), url: corta(src, 300) });
  }
  paginas.sort(function (a, b) { return (a.pagina || 0) - (b.pagina || 0); });

  /* o visualizador mostra "3 / 12" em algum no de texto; e a unica fonte do TOTAL sem ler JSON */
  var contador = '', nos = document.body.querySelectorAll('span, div, button');
  for (var t = 0; t < nos.length; t++) {
    var s = (nos[t].textContent || '').trim();
    if (/^\d{1,3}\s*\/\s*\d{1,3}$/.test(s)) { contador = s; break; }
  }

  /* 4. O visualizador pode ser um iframe (documento servido de outra origem, e ai o DOM de dentro
        e inalcancavel) ou inline. Isso muda tudo, entao e medido, nao presumido. */
  var quadros = [], ifr = document.getElementsByTagName('iframe');
  for (var f = 0; f < ifr.length; f++) {
    quadros.push({ src: corta(ifr[f].src, 300), title: corta(ifr[f].title, 120),
                   id: corta(ifr[f].id, 120), classe: corta(ifr[f].className, 160) });
  }
  var incorp = [], emb = document.querySelectorAll('embed, object');
  for (var e = 0; e < emb.length; e++) {
    incorp.push({ tag: emb[e].tagName, src: corta(emb[e].src || emb[e].data, 300),
                  type: corta(emb[e].type, 80) });
  }

  /* 5. A pergunta so fica respondida se a gente TENTAR. Cada candidato leva um fetch de verdade,
        e o resultado (status, content-type, tamanho) e o que decide o desenho do qxgrab. */
  var cand = baldes.pdf.concat(baldes.dms_document).slice(0, 5);
  var tentar = function (u) {
    return fetch(u).then(function (r) {
      var ct = r.headers.get('content-type') || '';
      if (!r.ok) return { url: u, status: r.status, content_type: ct, ok: false };
      return r.blob().then(function (bl) {
        return { url: u, status: r.status, content_type: ct || bl.type, bytes: bl.size,
                 ok: true, eh_pdf: /pdf/i.test(ct) || /pdf/i.test(bl.type), blob: bl };
      });
    }).catch(function (err) { return { url: u, ok: false, erro: String(err) }; });
  };

  Promise.all(cand.map(tentar)).then(function (res) {
    /* o blob sai do relatorio antes de ele virar JSON - mas so DEPOIS de guardado aqui, senao
       o PDF que a sonda acabou de achar seria jogado fora junto */
    var pdfOk = null, pdfBlob = null;
    for (var r = 0; r < res.length; r++) {
      if (res[r].eh_pdf && res[r].bytes > 1000 && !pdfOk) { pdfOk = res[r]; pdfBlob = res[r].blob; }
      delete res[r].blob;
    }

    var id = (location.href.match(/(?:activity|ugcPost|share)[:-](\d{6,})/i) || ['', 'sem-id'])[1];
    var d = { sonda: 'qxdprobe', versao: 1, url: location.href, quando: new Date().toISOString(),
              html_chars: html.length,
              paginas_no_dom: paginas.length, contador_do_visualizador: contador,
              paginas: paginas, iframes: quadros, embeds: incorp,
              urls: baldes, chaves_no_html: achadas, tentativas_de_fetch: res };

    var baixa = function (blob, nome) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = nome;
      document.body.appendChild(a); a.click();
      setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(a.href); }, 1000);
    };
    baixa(new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' }), 'qx-DPROBE-' + id + '.json');
    if (pdfBlob) setTimeout(function () { baixa(pdfBlob, 'qx-DPROBE-' + id + '.pdf'); }, 1200);

    var veredito = pdfOk ? 'PDF ALCANCAVEL (' + Math.round(pdfOk.bytes / 1024) + ' KB)'
                         : (cand.length ? 'nenhum candidato devolveu PDF'
                                        : 'nenhuma URL de PDF no HTML - so as paginas rasterizadas');
    alert('qxdprobe: ' + veredito + '\n\n' +
          'paginas no DOM: ' + paginas.length + (contador ? '  |  visualizador diz: ' + contador : '') + '\n' +
          'urls: pdf ' + baldes.pdf.length + ' | dms-document ' + baldes.dms_document.length +
          ' | paginas ' + baldes.document_images.length + '\n' +
          'iframes ' + quadros.length + ' | embeds ' + incorp.length + '\n\n' +
          'Baixei qx-DPROBE-' + id + '.json em Downloads. Manda esse arquivo.');
  });
})();
