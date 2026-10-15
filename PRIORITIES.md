# Priorities

Score = 200 × (0,5·I + 0,35·U + 0,15·(6 − E)) + Aj → 0 a 1000
- **I – Impacto (1–5):** receita, cliente, captação ou risco evitado
- **U – Urgência (1–5):** prazo, janela comercial ou risco iminente
- **E – Esforço (1–5):** quanto maior o esforço, menor o score

A coluna Tarefa precisa ser igual ao título no TASKS.md. Ajuste I/U/E aqui ou na aba Ranking do dashboard.
- **Aj – Ajuste fino:** somado ao score; usado para deixar tasks de um mesmo grupo com scores vizinhos no Ranking

| Tarefa | I | U | E | Aj | Por quê |
|---|---|---|---|---|---|
| safra tls rotate / certificados safra | 5 | 5 | 2 |  | A ação que evita a queda do cliente; prazo duro |
| Rotacionar certificados TLS Safra | 4 | 5 | 2 |  | Certificado vencido derruba cliente em produção; prazo duro |
| Integração Banco Pine: auto-quote / quartix-markets / octaxpro | 5 | 4 | 4 |  | Receita nova com banco; já em WIP; depende do seu quant |
| Ajustes de pricing no auto-quote | 4 | 4 | 2 |  | Minimum spread/manual-quote afetam receita por cotação e a integração Pine |
| timeout ngrok safra #platforms/oxpro | 5 | 3 | 3 |  |  |
| bpipe zfp tls-cert | 4 | 4 | 2 |  | Mesmo risco de certificado, no feed B-PIPE |
| Metaoxengine › Backup diário | 4 | 4 | 2 |  | Risco de perda de dados; barato |
| Deploy quartix-markets | 4 | 4 | 3 |  | Sem deploy, os releases não chegam ao cliente |
| Deploy da plataforma | 4 | 4 | 3 |  | Sem deploy, os releases não chegam ao cliente |
| aumentar streaming workers | 4 | 3 | 3 |  |  |
| mail alerts pulse | 4 | 3 | 3 |  |  |
| criar conta de cliente por tela | 4 | 3 | 3 |  |  |
| ajustar suspend octax-api | 4 | 3 | 3 |  |  |
| ajustar suspend octax-api, operations on tradingsettings_api | 4 | 3 | 3 |  |  |
| Metaoxengine › Infra monitor | 4 | 3 | 3 |  | Detectar incidente antes do cliente |
| prodsafra › Duas máquinas | 4 | 3 | 3 |  | Disponibilidade do cliente Safra |
| Login do flow.sight | 3 | 4 | 2 |  | Bloqueia acesso de cliente ao flow.sight; pequeno |
| Advisory: material de apoio a terceiro (estratégia financeira cross-border) | 3 | 3 | 2 |  | Receita de serviço via parceiro; já em WIP |
| Integrar Braza API | 4 | 2 | 3 |  | Nova integração/receita no cfx; sem prazo conhecido |
| Operacional | 3 | 3 | 2 |  | Atritos operacionais em clientes (Safra, alertas, contas) |
| Ajustar Jenkins build com metaox | 3 | 3 | 2 |  | Destrava build/deploy; ajuste pontual |
| prodsafra › Principal desliga 19h30 e liga 7h30 | 3 | 3 | 2 |  | Reduz custo de infra; depende da secundária |
| prodsafra › Sobe a secundária | 3 | 3 | 2 |  | Parte do esquema de duas máquinas |
| prodsafra › Testar antes em prodfibra | 3 | 3 | 2 |  | Pré-requisito seguro do prodsafra |
| split off spreads do customer-import CSV | 3 | 3 | 2 |  | Pricing do auto-quote; similar a Minimum spread |
| clearfxai whitelabel / PRX | 4 | 2 | 4 |  | Canal whitelabel; esforço alto |
| Minimum spread | 3 | 3 | 3 |  |  |
| manual-quote | 3 | 3 | 3 |  |  |
| Solução de governança TLS built-in no octaxpro | 4 | 2 | 4 |  | Evita a próxima crise de certificado; estrutural, mais esforço |
| SRE / metaox: painel de monitoração, cron tasks, CI/CD | 3 | 3 | 4 |  | Reduz trabalho manual e risco; delegável |
| Ambiente de integração octaxpro + quartix-markets | 3 | 3 | 4 |  | Apoia Pine e deploy do quartix-markets |
| Tela de apuração / earnings do partner (UX) | 3 | 2 | 2 |  | Transparência para parceiros |
| Bugfix: deletar conta-company demora demais | 2 | 3 | 1 |  | Bug visível, correção barata |
| clearfxai control-plane | 3 | 2 | 2 | -1 | Operação do cfx |
| Atualizar OS com solicitação dos detalhes dos clientes | 3 | 2 | 2 | -2 | Operação do cfx; barato |
| rfqd / Integrar Braza API | 3 | 2 | 3 | 27 | Serviço de RFQ do cfx; escopo a confirmar |
| Sangria diária de dados de produção (octaxpro → plataforma de dados) | 3 | 2 | 3 |  | Base de dados p/ analytics/intelligence; sem prazo; reclassificado de "data leak" |
| Release cherry / PortAR | 3 | 2 | 3 |  | Integração de parceiro; sem prazo conhecido |
| flow.sight: análise period-over-period, flow.sight spot, ideias | 3 | 2 | 3 |  | Melhora produto existente; depende do seu quant |
| clearfxai / quartix advisory | 3 | 2 | 3 |  | Linha de serviço; ainda difusa |
| Metaoxengine › Trigger de VMs p/ build e deploy | 3 | 2 | 3 |  | Automação de build/deploy |
| Análise period-over-period | 3 | 2 | 3 |  | Como o pai: melhora produto existente; quant |
| flow.sight spot | 3 | 2 | 3 |  | Como o pai: extensão do flow.sight; quant |
| Ajustar pipeline de CI/CD do octaxpro | 3 | 2 | 3 |  | Produtividade do time; delegável |
| Automação de workflows | 3 | 2 | 3 |  | Serviço de advisory recorrente |
| Release Plexus (valorpro): integrar à plataforma qxmarkets | 2 | 3 | 3 |  | Consolida cliente valorpro na plataforma |
| Integração oxpro / plexus-backend / octaxpro | 3 | 2 | 4 |  | Dívida de integração; esforço alto |
| CI/CD | 3 | 2 | 4 |  | Ganho de produtividade do time; delegável |
| metaox-next como orquestrador dos pipelines de CI/CD | 3 | 2 | 4 |  | Como o pai: produtividade; esforço alto |
| Integração com bancos | 3 | 2 | 4 |  | Serviço de advisory; integração pesada |
| bpipe cortesia | 2 | 2 | 1 |  | Pequeno; contexto pouco claro |
| Testes: UI (Playwright), API, API mock, autotests das libs | 3 | 2 | 3 | -41 | Reduz regressões; delegável |
| Escrever testes de API | 3 | 2 | 2 | -72 | Maior retorno por esforço entre os testes |
| Escrever autotests (libs) | 3 | 2 | 2 | -73 | Barato e protege as libs compartilhadas |
| docstored › autotests (libs) | 2 | 1 | 2 | 96 | Testes baratos, alinhado a "Escrever autotests (libs)" |
| Escrever testes de UI (Playwright) | 3 | 2 | 3 | -45 | Como o pai: reduz regressões; delegável |
| API mock | 2 | 2 | 2 | 24 | Habilita testes isolados |
| UI + api-mock | 2 | 1 | 3 | 123 | Depende de API mock e testes de UI |
| Revisar taxonomia | 2 | 2 | 2 |  | Base do quartix-intelligence, que está em modo exploratório |
| Opensource Fernando | 2 | 2 | 2 |  | Visibilidade/comunidade |
| octaxpro addon / excel-plugin | 3 | 1 | 3 |  | Diferencial de produto; sem demanda urgente |
| Organizar repos | 2 | 2 | 2 |  | Higiene de engenharia |
| Metaoxengine › Pulse count | 2 | 2 | 2 |  | Observabilidade do pulse; pequeno |
| Metaoxengine › Pulseclean | 2 | 2 | 2 |  | Higiene do pulse; pequeno |
| AutoFlow / One Pager | 2 | 2 | 2 |  | Material de venda reutilizável |
| Taxonomia | 2 | 2 | 2 |  | Igual a "Revisar taxonomia" |
| marketdata | 2 | 2 | 2 |  | Como o pai: higiene de engenharia |
| oxpro etc. | 2 | 2 | 2 |  | Como o pai: higiene de engenharia |
| Release hedgeOS (Damke) | 1 | 4 | 4 |  | Produto novo com cliente-alvo definido; precisa estar pronto p/ a apresentação |
| Integração hedgeOS ↔ nexus | 1 | 4 | 4 |  | Como o release: precisa estar pronto p/ a apresentação |
| Integração hedgeOS ↔ plexus | 1 | 4 | 4 |  | Como o release: precisa estar pronto p/ a apresentação |
| MOU empresa nova / QUARTIX ADVISORY | 1 | 3 | 2 |  | Parceria/novo negócio pendente; estava parado |
| Ambiente dev/beta do cfx | 2 | 2 | 3 |  | Produtividade no cfx |
| Pipeline de CI/CD do cfx | 2 | 2 | 3 |  | Produtividade no cfx |
| chery | 2 | 2 | 3 |  | Ligado a "Release cherry / PortAR" |
| Acolher dados de eventos (logs, preços) | 3 | 1 | 4 |  | Conversa com a Sangria de dados |
| E-mail no estilo Dropbox | 1 | 3 | 2 |  | Primeiro passo barato da captação |
| Pitch e segmentos | 1 | 3 | 3 |  | Necessário para captação e para vender hedgeOS |
| quartix-intelligence: datalake | 3 | 1 | 5 |  | Exploratório e caro |
| Plataforma FP&A para empresas comex | 1 | 3 | 3 |  | Como o pai: necessário p/ captação e venda |
| Enfoque ferramentas para execução | 1 | 3 | 3 |  | Como o pai: necessário p/ captação e venda |
| settings-apps-spotlight | 2 | 1 | 2 |  | Melhoria pequena de UX |
| News + calendar | 2 | 1 | 2 |  | Já existe no LAUNCHPAD; incremental |
| Ideias para o flow.sight | 2 | 1 | 2 |  | Backlog de ideias; baixo esforço de registrar |
| Giba / Santander | 2 | 1 | 2 |  | Banco grande; maior potencial do pipeline hedgeOS |
| Blog › AutoFlow Post | 2 | 1 | 2 |  | Conteúdo pontual; barato |
| Ask for strategic capital | 1 | 3 | 4 |  | Fôlego financeiro e escala do time; processo longo, começar cedo (e-mail estilo Dropbox) |
| Integração hedgeOS ↔ port.ar | 1 | 3 | 4 |  | Parceiro com contexto pouco claro |
| Frentes Marcos I9DC | 1 | 2 | 2 |  | Frente estratégica; contexto pouco claro |
| Design do ambiente quartix-markets live (market.desk?) | 2 | 1 | 3 |  | Indefinido |
| Manifesto / blog planning | 2 | 1 | 3 |  | Marketing de longo prazo |
| Marketing farm / Braindump marketing | 2 | 1 | 3 |  | Marketing de longo prazo |
| Estruturar marketing / blogposts | 2 | 1 | 3 |  | Marketing de longo prazo |
| Social Media Agent | 2 | 1 | 3 |  | Automação de marketing; exploratório |
| Marketing Agent | 2 | 1 | 3 |  | Automação de marketing; exploratório |
| Platform overhaul | 3 | 1 | 5 | -51 | Refatoração grande; adiar até depois dos releases |
| api-auth | 3 | 2 | 3 | -182 | Segurança de API; o item mais relevante do overhaul |
| Email orch › mailsend-d | 2 | 1 | 4 | 17 | Parte do Platform overhaul; adiar |
| Email orch › emailorchd | 2 | 1 | 4 | 16 | Parte do Platform overhaul; adiar |
| rabbitmq | 2 | 1 | 4 | 15 | Infra de mensageria; adiar |
| messaging-integration | 2 | 1 | 3 | -16 | Sem demanda clara |
| dbentities | 2 | 1 | 5 | 43 | Refatoração grande; adiar |
| dbentity2 | 2 | 1 | 4 | 9 | Refatoração de entidades |
| Overhaul do data-store de docs | 2 | 1 | 5 | 38 | Refatoração grande sem dor urgente |
| Data-store layers: (1) blobs, (2) metadados | 2 | 1 | 5 | 37 | Núcleo do overhaul; grande |
| docstored (engine) | 2 | 1 | 5 | 36 | Engine nova; grande |
| docstored › libs | 2 | 1 | 3 | -25 | Parte do docstored |
| docstored › mini-exec | 1 | 1 | 3 | 74 | Detalhe do docstored |
| Content publishing platform | 2 | 1 | 4 |  | Exploratório e caro |
| Design do oxpro sandbox sobre Cloud Run | 2 | 1 | 4 |  | Design exploratório; sem prazo |
| cloud-storage | 2 | 1 | 4 |  | Parte do overhaul do data-store |
| Tesouraria institucional e corretoras › Commodities | 1 | 2 | 3 |  | Segmento do pitch |
| Tesouraria institucional e corretoras › Renda fixa | 1 | 2 | 3 |  | Segmento do pitch |
| Tesouraria institucional e corretoras › Moedas | 1 | 2 | 3 |  | Segmento do pitch (core FX) |
| Acolher dados do LinkedIn | 2 | 1 | 4 |  | Exploratório |
| Chat prototype / isabel | 2 | 1 | 3 | -31 | Exploratório |
| Avaliar chat no quartix-markets | 2 | 1 | 2 | -62 | Decide se o protótipo segue |
| Tutorial para marcar mensagens gmail como importantes | 1 | 1 | 2 | 37 | Detalhe do protótipo |
| QA do chat | 1 | 1 | 3 | 66 | Só faz sentido após a avaliação |
| Convite Damke: apresentar hedgeOS | 1 | 1 | 1 |  | Abre a 1ª venda do hedgeOS; custo de uma mensagem; estava parado |
| Follow up Fernando Silveira | 1 | 1 | 1 |  | Conversa parada; esfria se demorar; custo mínimo |
| Damke | 1 | 1 | 1 |  | Igual a "Convite Damke": mesmo alvo |
| Alvos hedgeOS | 1 | 1 | 2 |  | Pipeline comercial do hedgeOS (Campanelli, Santander, Giva, FK…) |
| Transformar livro em skill | 1 | 1 | 2 |  | Pessoal/experimental |
| Campanelli | 1 | 1 | 2 |  | Como o pai: pipeline hedgeOS |
| Giva | 1 | 1 | 2 |  | Como o pai: pipeline hedgeOS |
| FK Partners | 1 | 1 | 2 |  | Como o pai: pipeline hedgeOS |
| Instituições de ensino | 1 | 1 | 2 |  | Canal de baixo valor imediato |
| Estudantes de curso, etc | 1 | 1 | 2 |  | Audiência de longo prazo |
| Seguidores página enfoque | 1 | 1 | 2 |  | Audiência de longo prazo |
| notebooklm | 1 | 1 | 2 |  | Como o pai: pessoal/experimental |
| beautiful data | 1 | 1 | 2 |  | Como o pai: pessoal/experimental |
| Pegar skills prontas, treinar notebooklm com um livro teste | 1 | 1 | 2 |  | Como o pai: pessoal/experimental |
| Integração com Port.AR | 1 | 1 | 3 |  | Ligada ao hedgeOS; contexto pouco claro |
| Research / opensource | 1 | 1 | 3 |  | Exploratório |
| Tesouraria institucional e corretoras › Crédito de carbono | 1 | 1 | 3 |  | Segmento mais especulativo |
| Acolher outros dados | 1 | 1 | 4 |  | Indefinido |
