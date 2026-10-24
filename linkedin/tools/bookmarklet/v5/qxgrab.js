/* qxgrab v5 - extrai um post do LinkedIn a partir da propria pagina, logado.
 *
 * Por que bookmarklet e nao iframe: o LinkedIn manda X-Frame-Options SAMEORIGIN e CSP
 * frame-ancestors 'self', entao pagina local nao consegue embutir; e mesmo que embutisse, a
 * same-origin policy impediria ler o DOM. Codigo que le a pagina precisa RODAR na pagina.
 *
 * ESTE arquivo e a fonte. O `qxgrab.url.txt` ao lado e DERIVADO dele - gerado com comentario
 * removido, tudo numa linha e percent-encoded, que e o formato que a URL de um favorito aceita.
 * **Nao edite o .txt**: a proxima geracao sobrescreve. Edite aqui e regenere.
 *
 * Historico das versoes, porque cada uma errou de um jeito util:
 *   v1  seletor por nome de classe. Falhou na primeira tentativa real - e as classes do LinkedIn
 *       sao HASHEADAS (`_904d28f2`, `e59df0f9`), geradas no build. Nao ha alvo estavel. O fallback
 *       tambem filtrava por classe, entao a protecao era ilusoria.
 *   v2  maior bloco de texto por densidade. Testado contra o HTML real salvo pelo usuario:
 *       escolhia um container de profundidade 3 com o cabecalho e o overlay de mensagens junto.
 *       Bonus de profundidade de 1% por nivel era fraco demais para separar.
 *   v5  conta <br> COMO ELEMENTO DO DOM (`getElementsByTagName('br').length`), nao como '\n' do
 *       innerText. Erro de modelagem meu na v3/v4: no navegador o innerText poe '\n' tambem em
 *       elemento de bloco (div, p, li), entao barra lateral e rodape tambem "tem quebra" e a
 *       descida parava cedo - a v4 trouxe 3555 chars com perfil, comentario e rodape junto.
 *       Minha simulacao em Python so contava <br>, e por isso dava certo e o navegador nao:
 *       eu tinha validado contra um modelo que nao era o do browser. Contar o elemento <br>
 *       significa a mesma coisa nos dois lugares.
 *   v4  imagem do post embutida em base64. O CDN manda `Access-Control-Allow-Origin: *`, entao
 *       `fetch` da propria pagina funciona. Base64 e melhor que guardar a URL: o link do
 *       media.licdn.com e ASSINADO E EXPIRA (`?e=<epoch>`, ~2 semanas) - referencia salva hoje
 *       nao abre depois. Filtro por `feedshare` no path, que e marcador semantico do CDN e nao
 *       muda com deploy, ao contrario de nome de classe.
 *   v3  desce para o filho que concentra as QUEBRAS DE LINHA. Post de LinkedIn e escrito em
 *       paragrafos curtos separados por <br><br>; barra lateral, card de perfil e rodape nao tem
 *       quebra nenhuma. Medido no HTML real: 65 das 83 quebras da pagina estao no post.
 *       Resultado: 1807 chars, do "Most people think correlation" ate o link final, sem sobra.
 */
(function () {
  var MAX_IMG = 4 * 1024 * 1024;          /* nao embutir imagem gigante no json */
  var lim = function (s) {
    return (s || '').replace(/[ \t]+/g, ' ').replace(/\n\s*\n\s*\n+/g, '\n\n').trim();
  };
  /* <br> como ELEMENTO, nao como '\n' de innerText - ver o historico da v5 acima. */
  var quebras = function (el) { return el.getElementsByTagName('br').length; };

  var atual = document.body, guarda = 0;
  while (guarda++ < 60) {
    var total = quebras(atual);
    if (total < 6) break;
    var melhor = null, melhorQ = -1;
    for (var i = 0; i < atual.children.length; i++) {
      var q = quebras(atual.children[i]);
      if (q > melhorQ) { melhorQ = q; melhor = atual.children[i]; }
    }
    /* so desce se o filho ainda concentra o grosso das quebras: senao o texto esta espalhado
       entre irmaos e este ja e o bloco certo. */
    if (!melhor || melhorQ < total * 0.85) break;
    atual = melhor;
  }

  var texto = lim(atual.innerText);
  if (!texto || texto.length < 120) {
    var diag = { erro: 'nao achei o corpo do post', url: location.href,
                 titulo_pagina: document.title, body_chars: document.body.innerText.length,
                 body_quebras: quebras(document.body), parou_em: atual.tagName,
                 amostra: lim(document.body.innerText).slice(0, 1500) };
    var bd = new Blob([JSON.stringify(diag, null, 2)], { type: 'application/json' });
    var ad = document.createElement('a');
    ad.href = URL.createObjectURL(bd); ad.download = 'qx-linkedin-DIAGNOSTICO.json';
    document.body.appendChild(ad); ad.click();
    alert('qxgrab: nao achei o corpo do post.\n\nBaixei qx-linkedin-DIAGNOSTICO.json em Downloads.\n' +
          'Manda esse arquivo para o QX-PLAN.');
    return;
  }

  /* Autor: primeiro link de perfil ou empresa subindo a partir do bloco de texto. */
  var autor = '', cargo = '', quando = '', ctx = atual, limite = texto.length * 3;
  for (var k = 0; k < 8 && ctx && ctx !== document.body; k++) {
    ctx = ctx.parentElement;
    /* se o ancestral ja e muito maior que o post, saiu do card e alcancou a pagina inteira */
    if (lim(ctx.innerText).length > limite) break;
    var link = ctx.querySelector('a[href*="/company/"], a[href*="/in/"]');
    if (link) {
      var linhas = lim(link.innerText).split('\n').filter(function (x) { return x; });
      if (linhas.length) {
        autor = linhas[0];
        var volta = lim(ctx.innerText).split('\n').filter(function (x) { return x; });
        for (var m = 0; m < volta.length; m++) {
          if (volta[m] === autor) { cargo = volta[m + 1] || ''; quando = volta[m + 2] || ''; break; }
        }
        break;
      }
    }
  }

  var social = '', nos = document.body.querySelectorAll('span, button');
  for (var n = 0; n < nos.length; n++) {
    var s = lim(nos[n].innerText);
    if (s.length < 60 && /^\d[\d.,]*\s*(reaction|reac|coment|comment)/i.test(s)) {
      if (social.indexOf(s) < 0) social += (social ? ' | ' : '') + s;
      if (social.length > 90) break;
    }
  }

  /* Imagem do post: `feedshare` no path e o marcador do CDN para midia de publicacao.
     Foto de perfil (`profile-displayphoto`), logo (`company-logo`) e capa ficam de fora. */
  var urls = [], vistos = {};
  var escopo = atual;
  for (var v = 0; v < 8 && escopo && escopo !== document.body; v++) escopo = escopo.parentElement;
  var achadas = (escopo || document.body).querySelectorAll('img');
  for (var w = 0; w < achadas.length; w++) {
    var src = achadas[w].currentSrc || achadas[w].src || '';
    if (src.indexOf('feedshare') < 0 && src.indexOf('/image/') < 0) continue;
    if (/profile-|company-|displaybackground|framedphoto|ghost/.test(src)) continue;
    if (!src || vistos[src]) continue;
    vistos[src] = 1;
    urls.push({ src: src, alt: achadas[w].alt || '' });
  }

  var pega = function (u) {
    return fetch(u.src).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.blob();
    }).then(function (bl) {
      if (bl.size > MAX_IMG) return { url: u.src, alt: u.alt, erro: 'maior que 4MB, nao embutida' };
      return new Promise(function (ok) {
        var fr = new FileReader();
        fr.onloadend = function () {
          ok({ url: u.src, alt: u.alt, mime: bl.type, bytes: bl.size,
               base64: String(fr.result).split(',')[1] });
        };
        fr.readAsDataURL(bl);
      });
    }).catch(function (e) { return { url: u.src, alt: u.alt, erro: String(e) }; });
  };

  Promise.all(urls.map(pega)).then(function (imagens) {
    var dados = { fonte: 'linkedin-bookmarklet', versao: 5, url: location.href,
                  capturado_em: new Date().toISOString(), autor: autor, autor_cargo: cargo,
                  publicado: quando, engajamento_bruto: social, texto: texto,
                  titulo_pagina: document.title, imagens: imagens };

    var id = (location.href.match(/activity[:-](\d+)/) ||
              location.href.match(/\/posts\/([\w-]{6,})/) || ['', 'sem-id'])[1].slice(0, 60);
    var b = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = 'qx-linkedin-' + id + '.json';
    document.body.appendChild(a); a.click();
    setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(a.href); }, 1000);

    var okimg = imagens.filter(function (x) { return x.base64; }).length;
    alert('qxgrab: capturado.\n\nautor: ' + (autor || '(nao identificado)') +
          '\ntexto: ' + texto.length + ' caracteres' +
          '\nimagens: ' + okimg + ' de ' + imagens.length + ' embutidas' +
          (social ? '\nengajamento: ' + social : '') +
          '\n\nSalvo em Downloads. Depois: python3 tools/qxinbox.py');
  });
})();
