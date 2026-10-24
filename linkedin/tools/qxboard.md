# qxboard - dashboard read-only do pipeline

Observabilidade dos agentes que rodam o pipeline do blog. Le `ledger/`, `workdir/locks/`,
`workdir/agents/`, `workdir/posts/` e `control.conf`, e desenha o estado no navegador com
atualizacao periodica.

Dois arquivos: `tools/qxboard.py` (servidor + derivacao) e `tools/qxboard.html` (a pagina).
Nenhuma dependencia externa - so a stdlib do Python e JS puro, sem CDN.

## Rodando

```
make dashrun      # sobe em http://127.0.0.1:8787 (erros vao para .qxboard.log)
make dashstop     # mata
make dashrestart  # depois de editar o qxboard
make dashrun PORT=9000
```

O Makefile e lean de proposito: sem pidfile, sem checagem de porta ocupada, sem confirmar
que subiu. `dashstop` e um `pkill -f tools/qxboard.py`, entao **mata toda instancia do
qxboard**, inclusive uma que esteja em outra porta. Para o estado do pipeline no terminal,
sem servidor, use `--once`.

Sem o Makefile:

```
python3 tools/qxboard.py                 # abre o navegador sozinho
python3 tools/qxboard.py --port 9000 --no-open
python3 tools/qxboard.py --once          # snapshot JSON no stdout, sem servidor
```

`--once` e util em pipe:

```
python3 tools/qxboard.py --once | jq '.fleet[] | select(.active)'
python3 tools/qxboard.py --once | jq .live
```

## Garantia de read-only

O tool **nao tem caminho de escrita**. Nenhum arquivo e aberto em modo de escrita, nenhum
diretorio e criado ou removido. A regra append-only do `ledger/` nao corre risco nem por
acidente, e o `qxboard` nunca compete por um lock com um agente de verdade.

Consequencia deliberada: **nao ha botao de acao na pagina**. Pausar um estagio e
`tools/qxctl.py pause`, e so o `QX-PLAN` escreve o `control.conf`. O dashboard observa.

## Por que existe um servidor

O pedido original era um HTML que fizesse o re-scan sozinho. Nao da, por duas razoes:

1. Um HTML em `file://` nao consegue listar `workdir/locks/`. Locks sao diretorios criados
   por `mkdir`, e nao existe API de listagem de diretorio para paginas locais. A File System
   Access API resolveria, mas e Chrome-only e exige secure context - ou seja, precisaria de
   um servidor de qualquer jeito.
2. O estado do pipeline e **derivado, nunca armazenado** (`runbook.md`: `status = todo - done
   - claim vivo`). Reimplementar essa derivacao em JS criaria uma segunda definicao de "lock
   morto", que pode divergir da do `qxnext.py`. Duas definicoes divergentes seriam pior que
   nao ter dashboard.

Entao quem varre o disco e o processo Python; o JS so faz polling em `/api/state.json` e
desenha. O `qxboard.py` importa `STALE_LOCK_SEC` do `qxnext` e `read()`/`STAGES` do `qxctl`
em vez de repetir as constantes - quando o runbook mudar a regra dos 90 min ou surgir um
estagio novo (foi o caso do `smedia`), o dashboard acompanha sem edicao.

## Atualizacao em tempo real

Polling a cada **10 s** (`POLL_MS` no `qxboard.html`). Nao ha WebSocket nem SSE.

Cada poll manda o fingerprint que o navegador ja tem:

```
GET /api/state.json?fp=<fp atual>
  -> {"unchanged": true, "fp": "..."}     disco identico, o DOM nao e tocado
  -> {snapshot completo}                  algo mudou, a pagina re-renderiza
```

Ha uma terceira rota, tambem de leitura: `GET /meta/<item_id>.txt` devolve o
`workdir/posts/<item_id>-meta.txt` cru, como `text/plain`. Ela existe porque um `file://`
partindo de uma pagina servida por `http://` e bloqueado pelo navegador - sem essa rota nao
haveria como abrir o sidecar sem sair do painel. So um id no formato canonico do `qxid.sh`
(`QXB-` + 8 hex) e aceito: casar o id inteiro, em vez de filtrar `..`, e o que impede um
caminho montado pelo cliente de escapar de `workdir/posts/`. Id fora do formato: `400`.
Sidecar inexistente: `404`.

O fingerprint e um blake2b de `(mtime_ns, size)` dos nove CSVs do `ledger/` mais o
`control.conf`, mais o mtime de cada entrada de `workdir/locks/`, mais mtime e tamanho de
cada rascunho em `workdir/agents/<agente>/`, de cada post e sidecar em `workdir/posts/` e de
cada arquivo de arte em `workdir/posts/social/<item>/`. Custa um punhado de `stat()` por poll.

Entra tambem o mtime do proprio `qxboard.html`, e o snapshot repete esse valor no campo `ui`.
O poll so busca JSON: sem isso, uma aba aberta continuava rodando o JS antigo contra o
snapshot novo depois de o painel mudar - coluna que sumiu, link que virou pilula morta,
tela mentindo sobre o que o painel tem. Agora a aba se recarrega sozinha quando o `ui` muda.

O que isso da na pratica:

- **Latencia**: ate 10 s, media 5 s, entre o `>>` do agente e a mudanca na tela.
- **Nada pisca a toa.** Sem mudanca no disco, o DOM nao e reescrito - scroll, hover e o
  tooltip aberto sobrevivem. O canto direito marca `sem mudanca` ou `disco mudou`.
- **Aba escondida nao consome scan.** O `visibilitychange` para o timer e dispara um scan
  imediato quando a aba volta, entao o que voce ve ao voltar ja e o estado atual.
- **Servidor caiu** vira aviso vermelho no canto, sem apagar a tela.
- **Painel editado** recarrega a aba sozinho no proximo poll (campo `ui`).
- O fingerprint e estavel entre reinicios do servidor, entao `make dashrestart` nao forca
  um re-render inutil.

Coisas que o polling **nao** cobre: mudanca de arquivo com mtime preservado (`touch -t`,
restore de backup) passa batido ate o proximo append de verdade. Nenhum agente faz isso.

## Os paineis

Nesta ordem: **Claims abertos** primeiro, porque a pergunta que se faz com a tela aberta e
"o que esta sendo escrito agora, e ha quanto tempo" - claim parado e o unico painel com
prazo (15 min de heartbeat, 90 min de reclaim). A **Frota** vem logo abaixo e responde "tem
agente de pe?", inclusive o que nao reivindica nada. **Produzidos** e o acumulado, consulta
e nao vigilancia. **Locks** fica por ultimo porque passa a maior parte do tempo alinhado.

### Banner do control plane

`state` (run/pause/stop) com a cor da faixa lateral, `config_version` vigente, quem mexeu
por ultimo e ha quanto tempo, `reason` e `note`. Os chips mostram o estado efetivo por
estagio; um chip amarelo com `(override)` e um estagio pausado individualmente enquanto o
global segue `run`.

### Claims abertos

Um item reivindicado por linha. Vem do replay de `ledger/backlog.wip.csv`: `claim` abre,
`heartbeat` renova, `release`/`abandon`/`exit`/`reclaim` fecham. O que sobra esta vivo.

| coluna | leitura |
|---|---|
| `lock` | `presente` = ok. `AUSENTE` = claim aberto sem lock em disco: outro agente pode reclamar o mesmo item. `reclaimavel` = lock parado ha mais de 90 min |
| `sem evento ha` | idade do ultimo evento. Amarelo aos 15 min (o runbook pede heartbeat nesse ritmo em item longo), vermelho aos 90 min. A barrinha e a fracao do caminho ate o reclaim |
| `claim ha` | idade total do claim, sem cor - item longo e legitimo |
| `rascunho` | `workdir/agents/<agente>/<item>.md`, tamanho e idade. Rascunho crescendo com heartbeat velho e agente vivo que esqueceu de bater ponto |
| `ja publicado` | badge no item: existe `published` no done com o claim ainda aberto. Quase sempre e release que faltou |

**Zero claims nao quer dizer zero agentes.** O `qxboard` le o ledger, nao a tabela de
processos: um agente que esta orientando, que esta entre itens, ou cujo estagio nao
reivindica nada e invisivel aqui e aparece so na **Frota**. Este painel ja se chamou
"Agentes vivos" e o nome enganava - foi renomeado em 2026-08-23 depois de um `QX-REVIEW`
de pe na tela do usuario nao aparecer nele.

Zero claims tambem nao significa trabalho terminado - pode ser o estagio anterior nao ter
entregue. E o buraco que o `qxnext.py` foi escrito para cobrir.

### Frota

Ultimo evento por agente, juntando `ledger/agents.log.csv` e `ledger/master.log.csv` (o
`QX-PLAN` loga no segundo; sem juntar os dois ele apareceria eternamente defasado).

Pill verde **`ativo`** = escreveu no ledger ha menos de 10 min (`ACTIVE_SEC`) e nao
registrou `exit`. E a resposta para "tem agente rodando?", e o contador `agentes ativos`
no topo repete o numero. Ativos vem primeiro na lista. E uma aproximacao pelo ledger, nao
pela tabela de processos: agente que morreu sem `exit` segue marcado ativo por ate 10 min,
e agente vivo que passou 10 min sem escrever nada deixa de aparecer como ativo.
`v<N> defasada` em vermelho = o agente confirmou uma config mais velha que a vigente, ou
seja esta rodando com spec velha. Agente que registrou `exit` fica esmaecido.

### Produzidos

Um post por linha, a partir de `workdir/posts/<item>.md` e do sidecar `<item>-meta.txt` -
a copia local que o `QX-WRITE` passou a salvar na calibracao de 2026-08-23 e que o
`QX-SMEDIA` le. O `-meta.txt` e parseado como `chave: valor` por linha; so `^[a-z_]+:` no
inicio da linha abre campo novo, senao uma continuacao de `angle:` com dois-pontos viraria
campo fantasma. Mais recente primeiro, pelo `published:` do sidecar (mtime do arquivo como
desempate).

| coluna | leitura |
|---|---|
| `meta` | abre o `-meta.txt` cru em outra aba, via `/meta/<item>.txt`. Fica na primeira coluna porque o link do `item` ja vai para o Drive: sem ela nao ha caminho para o metadado sem sair do painel. Vira `--` quando nao ha sidecar (o mesmo caso que acende `sem meta` no `estado`) |
| `social` | abre o Doc do pacote do `QX-SMEDIA` (`drive_url` de `ledger/social.done.csv`). Ao contrario do `meta`, aponta para fora: o pacote nao tem copia local para servir, o Doc e a unica fonte. O `title` do link diz se a arte ja chegou. `--` = item sem pacote de social ainda |
| `item` | vira link para o Doc quando o sidecar tem `url:` - o Drive continua sendo a fonte de verdade |
| `palavras` | a banda da calibracao: verde 850-1100, amarelo abaixo de 850, **vermelho acima de 1100** (teto duro) |
| `estado` | `no done` = tem linha `published` no `backlog.done.csv`. `so em disco` = copia local sem registro de publicacao. `revisado` = o `QX-REVIEW` fechou. `sem meta` = o `.md` esta la sem o sidecar |

O contador no cabecalho ganha `(+N so no Drive)` quando existe `published` no `done` sem
`.md` correspondente: post anterior a regra da copia local, ou copia que nao foi salva. A
lista desses ids aparece abaixo da tabela.

Nao ha chamada ao Drive aqui, e de proposito (ver **O que ficou de fora**): conferir se um
`drive_file_id` ainda existe custa uma chamada de API por post.

### Social

O que o `QX-SMEDIA` entregou, um pacote por linha, de `ledger/social.done.csv` cruzado com
`workdir/posts/social/<item>/`. O estagio nao produz post: produz um Doc `<item>-social` com
os blocos de LinkedIn e Instagram, e a arte quase sempre chega depois. Antes desta tabela o
unico rastro dele no painel era uma pilula em **Produzidos** - dava para saber que o item
tinha saido, nao o que tinha saido. A coluna `social` de **Produzidos** entra nesta tabela
pelo mesmo `drive_url`. Mais recente primeiro.

| coluna | leitura |
|---|---|
| `item` | vira link para o Doc do pacote quando a linha tem `drive_url` |
| `pacote` | o `title_final` sem o prefixo `QXB-<id>-social - ` (o id ja esta na coluna ao lado), e embaixo a `note` do ledger, que e onde o agente registra skill, contagem de slides e claims respeitados |
| `arte` | `N arquivos` = a pasta do item tem entrega. `pendente` = pasta criada e vazia, o estado normal logo depois do recut. `sem pasta` = nem o diretorio existe |
| `estado` | `ok` quando nao ha nada a dizer. `N recuts` = mais de uma linha para o mesmo item, vale a mais recente. `sem post local` = nao ha `workdir/posts/<item>.md`, ou seja o pacote nao saiu da copia que o `QX-SMEDIA` deveria ler |

O contador ganha `(N sem arte)`, e fica vermelho quando existe pasta de arte sem linha
correspondente no ledger - pacote em andamento, ou entrega que ninguem registrou. A lista
desses ids aparece abaixo da tabela.

O fingerprint desce ate `social/<item>/<arquivo>`: sem isso um PNG que chega nao mexeria no
mtime de nenhum diretorio observado e o painel so notaria a arte no proximo scan por outro
motivo.

### Locks

So acende quando `workdir/locks/` e os claims do wip discordam:

- **lock orfao** - diretorio em disco sem claim aberto. Agente morreu entre o `mkdir` e o
  append, ou soltou o claim sem `rmdir`. Passados 90 min o `qxnext` limpa sozinho.
- **claim sem lock** - o inverso, e o mais perigoso: dois agentes podem pegar o mesmo item.

## O que ficou de fora

Escolha explicita do v1, que cobre control plane, agentes e locks. Desenhados e cabendo sem
mexer na arquitetura:

- funil `manifest` -> `curated` -> `todo` -> `wip` -> `done`, por `fetch_status`;
- throughput no tempo (o `Produzidos` mostra o acumulado, nao a curva);
- saida do `qxlint.py --quiet` a cada scan;
- feed unificado dos cinco logs por timestamp.

Fora de escopo por natureza: qualquer coisa que dependa do Drive. Conferir se um
`drive_file_id` ainda existe custa uma chamada de API por post e nao e observabilidade de
agente.
