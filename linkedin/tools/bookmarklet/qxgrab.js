/* qxgrab v9 - extrai post do LinkedIn da propria pagina logada, com FILA.
 *
 * Por que bookmarklet e nao iframe: o LinkedIn manda X-Frame-Options SAMEORIGIN e CSP
 * frame-ancestors 'self', entao pagina local nao consegue embutir; e mesmo que embutisse, a
 * same-origin policy impediria ler o DOM. Codigo que le a pagina precisa RODAR na pagina.
 *
 * ESTE arquivo e a fonte. O `qxgrab.url.txt` ao lado e DERIVADO dele - gerado com comentario
 * removido, tudo numa linha e percent-encoded, que e o formato que a URL de um favorito aceita.
 * **Nao edite o .txt**: a proxima geracao sobrescreve. Edite aqui e regenere.
 *
 * FILA (v6+): bookmarklet **morre na navegacao** - trocou de pagina, o contexto JS acabou, e
 * favorito nao executa sozinho. Entao nao existe "visita todos automaticamente" sem extensao.
 * O que da: guardar a fila em `localStorage` (mesma origem linkedin.com) e cada clique
 * extrair-baixar-avancar. Voce cola a lista UMA vez e depois so clica em cada post; nao
 * digita nem procura URL. Um clique por post, e o ritmo continua humano.
 *
 * Historico das versoes, porque cada uma errou de um jeito util:
 *   v12 captura post de POUCAS QUEBRAS, que a v11 so sabia diagnosticar. O bloco do post nao e
 *       achado por estrutura de DOM - e pela URL: o path do LinkedIn e
 *       `<handle>_<primeiras-palavras-do-post>-<tipo>-<id>`, entao as palavras do slug estao no
 *       texto do post, e o bloco que contem mais delas e o corpo. Isso NAO e suposicao: medido
 *       nos 28 JSONs de `linkedin/` que tem slug (25 batem 60%+ dos tokens) e, o que importava
 *       mais, medido no diagnostico do post que motivou a versao - corpo 4/4, comentarios 1/4 e
 *       0/4. A v2 ja tinha tentado achar o corpo por DENSIDADE DE TEXTO e falhado; a diferenca e
 *       que densidade nao sabe do que o post fala, e o slug sabe.
 *       Duas travas, porque escolher errado aqui grava COMENTARIO no lugar do post: precisa de no
 *       minimo 2 tokens achados, e no empate descarta quem contem outro empatado (senao o <html>,
 *       que contem o post inteiro, ganha sempre). Sem escolha confiante, segue o diagnostico da
 *       v11. O JSON passa a dizer em `metodo` se o corpo veio por `quebras` ou por `slug`.
 *   v11 em cima de um post aberto, o bookmarklet PEDIA A LISTA DE URLS em vez de capturar. O
 *       teste de "tem post na tela?" era `document.getElementsByTagName('br').length < 6`, e ele
 *       nao mede o que diz medir: <br> so aparece onde o AUTOR apertou Enter. Post escrito em
 *       prosa corrida, post que e so uma linha mais hashtags, e artigo `/pulse/` (paragrafo em
 *       <p>, zero <br>) tem menos de 6 - e caiam no prompt da fila. Agora o teste e o PATH da URL
 *       (`/posts/`, `/feed/update/`, `/pulse/`), que nao depende de como o texto foi escrito.
 *       Consertar so o portao nao bastava: a descida da v3 usa a MESMA contagem (`total < 6` para
 *       de descer), entao a pagina de poucas quebras passaria pelo portao e sairia com o
 *       innerText da pagina inteira gravado como se fosse o post - troca de falha visivel por
 *       captura errada em silencio. Por isso `atual === document.body` (descida que nao saiu do
 *       lugar) agora e ERRO, e o `qx-linkedin-DIAGNOSTICO.json` leva os blocos de texto grandes
 *       da pagina com suas contagens, que e o dado que falta para desenhar o caminho alternativo.
 *       **O que a v11 NAO faz: extrair post de poucas quebras.** Ela para de mentir sobre o caso
 *       e junta a medicao; o extrator alternativo se desenha em cima do diagnostico, nao antes.
 *   v10 post de DOCUMENTO (o "PDF anexo") deixa de passar por post de imagem. O defeito era o
 *       mesmo (a) da v8, um andar adiante: as paginas do documento ja entravam na captura, mas
 *       por ACIDENTE - a clausula `/image/` do filtro as aceitava - e chegavam ao `qxinbox`
 *       indistinguiveis de tres fotos soltas, fora de ordem garantida e sem dizer que eram
 *       paginas de um documento. Agora sao `tipo: 'pagina'`, numeradas, ordenadas, e o topo do
 *       JSON leva `tem_documento`.
 *       **O PDF em si NAO e baixado, e isso nao e omissao: ele nao existe na pagina.** Medido,
 *       nao suposto - `qxdprobe.js` num post de documento real (dhrumilsavaliya, 5 paginas):
 *       nos 180KB de HTML ha ZERO URL de `.pdf`, zero de `dms/document`, zero ocorrencia de
 *       `transcribedDocumentUrl`/`manifestUrl`/`totalPageCount`/`DocumentComponent`, e nenhum
 *       `<embed>`. O LinkedIn entrega o documento RASTERIZADO e mais nada. Tambem nao adianta
 *       fabricar a URL da pagina seguinte: cada pagina tem `t=` proprio, assinatura presa ao
 *       path, entao trocar o `/N/` da URL da 403.
 *       **Limite que fica de pe:** so existe a pagina que o visualizador RENDERIZOU. Buraco no
 *       meio (1,2,5) o codigo detecta e reporta em `paginas_faltando`; cauda cortada (doc de 12
 *       que parou na 5) e INDETECTAVEL - a sonda nao achou na pagina nenhum contador "5 / 12"
 *       nem campo com o total. Por isso o alerta manda rolar o documento ate o fim antes de
 *       capturar: e a unica defesa, e ela e humana.
 *   v9  o nome do arquivo volta a ser LEGIVEL, sem perder o id. A v8 consertou o id cortado
 *       (defeito (b) abaixo) mas trocou o nome de `<slug>` para `<id>` puro sem que isso fosse
 *       pedido - mudanca de convencao disfarcada de conserto de bug, e o corpus inteiro ate
 *       entao era `<slug>`. Agora e `<slug legivel>-<id inteiro>`, que atende os dois.
 *   v8  tres defeitos vistos no primeiro post de VIDEO capturado de verdade (Hedgepoint):
 *       (a) o JSON nao dizia que era video. A capa (`videocover-high`) entrava por acaso, pela
 *           clausula `/image/` do filtro - `feedshare` NAO aparece em post de video - e ficava
 *           indistinguivel de imagem comum, entao o pipeline tratava post de video como post de
 *           imagem. Agora a capa e marcada `tipo: 'cover'` e o topo do JSON leva `tem_video`.
 *           O video EM SI continua fora, e por um motivo AINDA NAO VERIFICADO: a hipotese e que
 *           o `<video>` use MediaSource, com `src` `blob:` que `fetch` nao le. Isso e suposicao
 *           sobre como plataforma grande entrega video, nao observacao - ninguem olhou o DOM.
 *           Quem for mexer nisso: rode `qxvprobe.js` num post de video ANTES de desenhar nada.
 *           O que e certo: base64 de video estouraria o JSON, entao vai em arquivo separado.
 *       (b) o id saiu cortado NO MEIO DO NUMERO. A URL era `ugcPost-`, que o regex de `activity`
 *           nao pegava, entao caia no slug e o `.slice(0, 60)` partia `...8147` em `...814`.
 *           Agora aceita activity|ugcPost|share, igual ao `RE_ID` do `qxaudit.py`.
 *       (c) o autor era a pessoa MENCIONADA, nao quem publicou: `querySelector` devolve o
 *           primeiro link em ordem de DOM, e a mencao de perfil mora dentro do corpo do post,
 *           antes do cabecalho. O criterio novo e posicional - autor fica FORA do bloco de
 *           texto, mencao fica dentro. Preferir `/company/` a `/in/` NAO resolve: quebraria
 *           post de pessoa cujo cabecalho cita o empregador.
 *   v7  apaga a fila ao processar o ULTIMO item. Na v6 o `removeItem` estava num ramo
 *       inalcancavel: no ultimo post `pendentes` ja estava vazio, a funcao caia no primeiro
 *       `if` e voltava sem limpar. A fila ficava no localStorage com `pendentes: []` e o
 *       bookmarklet nunca mais oferecia criar lista nova - ficava mudo para sempre.
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
  var FILA = 'qxgrab_fila_v6';
  var MAX_IMG = 4 * 1024 * 1024;          /* nao embutir imagem gigante no json */
  var lim = function (s) {
    return (s || '').replace(/[ \t]+/g, ' ').replace(/\n\s*\n\s*\n+/g, '\n\n').trim();
  };
  /* <br> como ELEMENTO, nao como '\n' de innerText - ver o historico da v5 acima. */
  var quebras = function (el) { return el.getElementsByTagName('br').length; };

  /* Sem fila e fora de uma pagina de post? oferece criar a fila.
     O criterio e a URL, nao o conteudo. Ate a v10 a pergunta era `a pagina tem menos de 6 <br>?`,
     e por isso post de prosa corrida caia aqui: o bookmarklet pedia a lista de URLs em cima de um
     post aberto na tela. Path de post e estavel; numero de <br> e o jeito do autor escrever. */
  var filaAtual = null;
  try { filaAtual = JSON.parse(localStorage.getItem(FILA) || 'null'); } catch (e) {}
  /* fila sem pendentes e resto de execucao interrompida: nao pode travar uma lista nova */
  if (filaAtual && !(filaAtual.pendentes || []).length) localStorage.removeItem(FILA);
  /* `indexOf` e nao regex de proposito: a regex terminaria em `\//`, que o `compile.py` recusa -
     numa URL de favorito o `//` viraria comentario e mataria o resto do bookmarklet. */
  var caminho = location.pathname;
  var ehPost = caminho.indexOf('/posts/') >= 0 || caminho.indexOf('/feed/update/') >= 0 ||
               caminho.indexOf('/pulse/') >= 0;
  if ((!filaAtual || !(filaAtual.pendentes || []).length) && !ehPost) {
    var col = prompt('qxgrab - colar a lista de URLs do LinkedIn (uma por linha).\n' +
                     'Deixe vazio para cancelar.', '');
    if (!col || !col.trim()) return;
    var lista = col.split(/[\s,;]+/).filter(function (u) { return /^https?:\/\/.*linkedin\.com/.test(u); });
    if (!lista.length) { alert('qxgrab: nenhuma URL de linkedin.com reconhecida.'); return; }
    var primeira = lista.shift();
    localStorage.setItem(FILA, JSON.stringify({ pendentes: lista, feitos: [], criada: new Date().toISOString() }));
    alert('qxgrab: fila com ' + (lista.length + 1) + ' posts.\n\n' +
          'Vou abrir o primeiro. Em cada post, clique no favorito de novo:\n' +
          'ele baixa e ja avanca para o proximo.');
    location.href = primeira;
    return;
  }

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

  var texto = lim(atual.innerText), metodo = 'quebras';

  /* Caminho alternativo para post de POUCAS QUEBRAS, onde a descida acima nao sai do lugar.
     O anzol nao e estrutura de DOM - e a URL. O LinkedIn monta o path como
     `<handle>_<primeiras-palavras-do-post>-<tipo>-<id>`, entao as palavras do slug ESTAO no texto
     do post. Medido nos 28 JSONs de `linkedin/` que tem slug: 25 batem 60% ou mais dos tokens; dos
     3 que nao batem, dois tem slug de duas palavras e um nao tem palavra nenhuma (`ugcPost-<id>`).
     E medido tambem que SEPARA post de comentario, que era a duvida real: no post que motivou a
     v12 (marcoscscarreira, documento de 73 paginas) o corpo pontua 4/4 tokens e os dois
     comentarios 1/4 e 0/4 - comentario fala do assunto, mas nao repete o titulo.
     Empate se resolve em dois passos: descarta quem CONTEM outro empatado (o <html> contem o post
     inteiro e ganharia sempre) e fica o primeiro na ordem do DOM, porque post vem antes de
     comentario. Menos de 2 tokens no slug, ou menos de 2 tokens achados: NAO escolhe - cai no
     diagnostico. Palpite errado aqui grava comentario no lugar do post, que e pior que falhar. */
  var semAcento = function (t) {
    return String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
             .toLowerCase().replace(/[^a-z0-9]+/g, ' ');
  };
  var porSlug = function () {
    var bruto = (location.pathname.match(/\/posts\/([\w-]+)/) || ['', ''])[1];
    if (bruto.indexOf('_') >= 0) bruto = bruto.slice(bruto.indexOf('_') + 1);
    var toks = semAcento(bruto).split(' ').filter(function (t) {
      return t.length > 2 && !/^\d+$/.test(t) && !/^(activity|ugcpost|share)$/.test(t);
    });
    if (toks.length < 2) return null;
    var caixas = document.querySelectorAll('article, [dir="ltr"], p'), pont = [], melhor = 0;
    for (var i = 0; i < caixas.length; i++) {
      var t = semAcento(caixas[i].innerText), n = 0;
      for (var j = 0; j < toks.length; j++) if (t.indexOf(toks[j]) >= 0) n++;
      if (n > melhor) melhor = n;
      pont.push(n);
    }
    if (melhor < 2) return null;
    var empate = [];
    for (var k = 0; k < caixas.length; k++) if (pont[k] === melhor) empate.push(caixas[k]);
    for (var m = 0; m < empate.length; m++) {
      var contem = false;
      for (var c2 = 0; c2 < empate.length; c2++) {
        if (c2 !== m && empate[m].contains(empate[c2])) { contem = true; break; }
      }
      if (!contem) return empate[m];
    }
    return null;
  };
  if (atual === document.body || !texto || texto.length < 120) {
    var alvo = porSlug();
    if (alvo) { atual = alvo; texto = lim(atual.innerText); metodo = 'slug'; }
  }

  /* `atual === document.body` quer dizer que a descida NAO SAIU DO LUGAR: o laco parou na
     primeira volta porque a pagina inteira tem menos de 6 <br>. Sem esta clausula o `texto` seria
     o innerText da PAGINA TODA - barra lateral, rodape, sugestoes - que passa folgado dos 120
     chars, e o JSON sairia com lixo no lugar do post sem ninguem ser avisado. Falhar visivel e
     melhor que capturar errado em silencio. */
  if (atual === document.body || !texto || texto.length < 120) {
    /* de que a pagina e feita, para o conserto do caso "poucas quebras" sair de medicao e nao de
       suposicao: cada bloco de texto grande, com quantas quebras e quantos <p> tem dentro. */
    var cands = [], caixas = document.querySelectorAll('article, [dir="ltr"], p');
    for (var c = 0; c < caixas.length && cands.length < 8; c++) {
      var tc = lim(caixas[c].innerText);
      if (tc.length < 200) continue;
      cands.push({ tag: caixas[c].tagName, dir: caixas[c].getAttribute('dir') || '',
                   chars: tc.length, quebras: quebras(caixas[c]),
                   ps: caixas[c].getElementsByTagName('p').length, amostra: tc.slice(0, 300) });
    }
    var diag = { erro: 'nao achei o corpo do post', versao: 12, url: location.href,
                 titulo_pagina: document.title, body_chars: document.body.innerText.length,
                 body_quebras: quebras(document.body), parou_em: atual.tagName,
                 candidatos: cands,
                 amostra: lim(document.body.innerText).slice(0, 1500) };
    var bd = new Blob([JSON.stringify(diag, null, 2)], { type: 'application/json' });
    var ad = document.createElement('a');
    ad.href = URL.createObjectURL(bd); ad.download = 'qx-linkedin-DIAGNOSTICO.json';
    document.body.appendChild(ad); ad.click();
    alert('qxgrab: nao achei o corpo do post.\n\nBaixei qx-linkedin-DIAGNOSTICO.json em Downloads.\n' +
          'Manda esse arquivo para o QX-PLAN.');
    return;
  }

  /* Autor: o link que identifica QUEM PUBLICOU. A v7 pegava o primeiro link em ordem de DOM e
     por isso deu "Marcelo Lacerda" num post da Hedgepoint - uma MENCAO no corpo do texto.
     A regra que separa os dois casos NAO e "empresa ganha de pessoa": isso quebra post de
     pessoa cujo cabecalho cita o empregador (testado - virava "Cargill" num post da Ana).
     O que separa e a posicao: **mencao mora DENTRO do bloco de texto, autor mora FORA dele**.
     Entao subimos ate o primeiro ancestral com link fora de `atual`, e ali vale a ordem do DOM,
     que e a ordem do cabecalho. Link sem texto (o do logotipo, so com <img> dentro) nao vale.
     Se nada aparecer fora do bloco em toda a subida, cai no de dentro - o que a v7 faria. */
  var achaLink = function (el, fora) {
    var as = el.querySelectorAll('a[href*="/company/"], a[href*="/in/"]');
    for (var i = 0; i < as.length; i++) {
      if (!lim(as[i].innerText)) continue;
      if (fora && atual.contains(as[i])) continue;
      return as[i];
    }
    return null;
  };
  var autor = '', cargo = '', quando = '', ctx = atual, limite = texto.length * 3;
  var achLink = null, achCtx = null;
  for (var k = 0; k < 8 && ctx && ctx !== document.body; k++) {
    ctx = ctx.parentElement;
    /* se o ancestral ja e muito maior que o post, saiu do card e alcancou a pagina inteira */
    if (lim(ctx.innerText).length > limite) break;
    var fora = achaLink(ctx, true);
    if (fora) { achLink = fora; achCtx = ctx; break; }
    if (!achLink) {
      var dentro = achaLink(ctx, false);
      if (dentro) { achLink = dentro; achCtx = ctx; }   /* guarda e CONTINUA subindo */
    }
  }
  if (achLink) {
    autor = lim(achLink.innerText).split('\n').filter(function (x) { return x; })[0] || '';
    var volta = lim(achCtx.innerText).split('\n').filter(function (x) { return x; });
    for (var m = 0; m < volta.length; m++) {
      if (volta[m] === autor) { cargo = volta[m + 1] || ''; quando = volta[m + 2] || ''; break; }
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
  var urls = [], vistos = {}, temVideo = false, temDocumento = false;
  var escopo = atual;
  for (var v = 0; v < 8 && escopo && escopo !== document.body; v++) escopo = escopo.parentElement;
  var achadas = (escopo || document.body).querySelectorAll('img');
  for (var w = 0; w < achadas.length; w++) {
    var src = achadas[w].currentSrc || achadas[w].src || '';
    if (src.indexOf('feedshare') < 0 && src.indexOf('/image/') < 0) continue;
    if (/profile-|company-|displaybackground|framedphoto|ghost/.test(src)) continue;
    if (!src || vistos[src]) continue;
    vistos[src] = 1;
    /* `videocover` e o marcador do CDN para o frame de capa de um post de VIDEO. E a unica
       evidencia de video que temos sem ler o <video>, e ela ja esta na mao.
       `feedshare-document-images_<largura>/<tag>/<pagina>/<ts>` e o marcador equivalente para
       post de DOCUMENTO, e o numero da pagina vem de graca no proprio path. Os dois sao path
       do CDN, nao nome de classe: nao mudam com deploy. */
    var pag = (src.match(/feedshare-document-images_\d+\/[^/]+\/(\d+)[\/]/) || [])[1];
    var tipo = /videocover/.test(src) ? 'cover' : (pag ? 'pagina' : 'imagem');
    if (tipo === 'cover') temVideo = true;
    if (tipo === 'pagina') temDocumento = true;
    var item = { src: src, alt: achadas[w].alt || '', tipo: tipo };
    if (pag) item.pagina = Number(pag);
    urls.push(item);
  }

  /* Ordem de DOM nao e ordem de documento: o visualizador pode ter reciclado nos, e um leitor
     que recebe pagina 3 antes da 1 le o documento embaralhado sem perceber. Aqui a ordem passa a
     vir do NUMERO DA PAGINA, que e dado do CDN. Imagem que nao e pagina vai para o fim. */
  var faltando = [];
  if (temDocumento) {
    urls.sort(function (a, b) { return (a.pagina || 9999) - (b.pagina || 9999); });
    var temPag = {}, maxPag = 0;
    for (var y = 0; y < urls.length; y++) {
      if (!urls[y].pagina) continue;
      temPag[urls[y].pagina] = 1;
      if (urls[y].pagina > maxPag) maxPag = urls[y].pagina;
    }
    /* buraco NO MEIO da sequencia e detectavel; cauda cortada nao e - ver a v10 no cabecalho */
    for (var z = 1; z < maxPag; z++) if (!temPag[z]) faltando.push(z);
  }

  var pega = function (u) {
    return fetch(u.src).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.blob();
    }).then(function (bl) {
      if (bl.size > MAX_IMG) return { url: u.src, alt: u.alt, tipo: u.tipo, erro: 'maior que 4MB, nao embutida' };
      return new Promise(function (ok) {
        var fr = new FileReader();
        fr.onloadend = function () {
          ok({ url: u.src, alt: u.alt, tipo: u.tipo, mime: bl.type, bytes: bl.size,
               base64: String(fr.result).split(',')[1] });
        };
        fr.readAsDataURL(bl);
      });
    }).catch(function (e) { return { url: u.src, alt: u.alt, tipo: u.tipo, erro: String(e) }; });
  };

  Promise.all(urls.map(pega)).then(function (imagens) {
    var dados = { fonte: 'linkedin-bookmarklet', versao: 12, url: location.href,
                  capturado_em: new Date().toISOString(), autor: autor, autor_cargo: cargo,
                  publicado: quando, engajamento_bruto: social, texto: texto, metodo: metodo,
                  titulo_pagina: document.title, tem_video: temVideo,
                  tem_documento: temDocumento, paginas_faltando: faltando, imagens: imagens };

    /* Nome do arquivo: <slug legivel>-<id inteiro>. A v8 gravava so o id, o que e correto mas
       ilegivel na pasta de Downloads; a v7 gravava so o slug cortado em 60 chars, o que era
       legivel mas partia o id no meio do numero - e as vezes nem incluia id.
       O id vem de activity|ugcPost|share, igual ao `RE_ID` do `qxaudit.py`. O slug perde a cauda
       `-<tipo>-<id>-<sufixo>` pela mesma regra do `RE_CAUDA` de la, troca `_` por `-` e so entao
       e cortado - em FRONTEIRA DE PALAVRA, para nao terminar em meia palavra. */
    var id = (location.href.match(/(?:activity|ugcPost|share)[:-](\d{6,})/i) || ['', 'sem-id'])[1];
    var slug = (location.href.match(/\/posts\/([\w-]+)/) || ['', ''])[1]
                 .replace(/-(?:activity|ugcpost|share)-\d{6,}(?:-[\w-]{2,12})?$/i, '')
                 .replace(/_/g, '-').toLowerCase().replace(/[^a-z0-9-]+/g, '-');
    if (slug.length > 45) slug = slug.slice(0, 45).replace(/-[^-]*$/, '');
    slug = slug.replace(/^-+|-+$/g, '').replace(/-{2,}/g, '-');
    var nome = 'qx-linkedin-' + (slug ? slug + '-' : '') + id;
    var b = new Blob([JSON.stringify(dados, null, 2)], { type: 'application/json' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = nome + '.json';
    document.body.appendChild(a); a.click();
    setTimeout(function () { document.body.removeChild(a); URL.revokeObjectURL(a.href); }, 1000);

    var okimg = imagens.filter(function (x) { return x.base64; }).length;
    var nPag = imagens.filter(function (x) { return x.tipo === 'pagina'; }).length;
    var resumo = 'texto ' + texto.length + ' chars, ' + okimg + '/' + imagens.length + ' img' +
                 (temVideo ? ' (POST DE VIDEO - so a capa foi baixada)' : '') +
                 (temDocumento ? ' (DOCUMENTO - ' + nPag + ' paginas; o LinkedIn nao serve o PDF,' +
                                 ' so as paginas em imagem. Se o documento tinha MAIS paginas,' +
                                 ' role o visualizador ate o fim e capture de novo)' : '') +
                 (faltando.length ? ' FALTANDO paginas: ' + faltando.join(', ') : '');
    avancar(resumo);
  });

  /* --- fila -------------------------------------------------------------------------- */
  function lerFila() {
    try { return JSON.parse(localStorage.getItem(FILA) || 'null'); } catch (e) { return null; }
  }
  function gravarFila(f) {
    try { localStorage.setItem(FILA, JSON.stringify(f)); } catch (e) {}
  }
  function avancar(resumo) {
    var f = lerFila();

    /* Sem fila: captura avulsa, nada a limpar. */
    if (!f) {
      alert('qxgrab: capturado.\n\n' + resumo + '\n\nSalvo em Downloads. ' +
            'Depois: python3 tools/qxinbox.py');
      return;
    }

    f.feitos.push({ url: location.href, resumo: resumo });

    /* ULTIMO da fila: `pendentes` ja esta vazio porque o item atual foi retirado quando
       navegamos para ca. Aqui a fila TEM que ser apagada, senao ela fica no localStorage com
       `pendentes: []` e o bookmarklet nunca mais oferece criar lista nova - foi o defeito da
       v6, onde este `removeItem` estava num ramo inalcancavel. */
    if (!f.pendentes.length) {
      localStorage.removeItem(FILA);
      alert('qxgrab: FILA CONCLUIDA.\n\n' + f.feitos.length + ' posts capturados.\n' +
            'localStorage limpo - pronto para uma lista nova.\n\n' +
            'Rode: python3 tools/qxinbox.py');
      return;
    }

    var prox = f.pendentes.shift();
    gravarFila(f);
    /* espera o download comecar antes de navegar - navegar antes cancela o Blob */
    setTimeout(function () { location.href = prox; }, 1800);
  }
})();
