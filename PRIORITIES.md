# Priorities

Score = 20 × (0,5·I + 0,35·U + 0,15·(6 − E)) → 0 a 100
- **I – Impacto (1–5):** receita, cliente, captação ou risco evitado
- **U – Urgência (1–5):** prazo, janela comercial ou risco iminente
- **E – Esforço (1–5):** quanto maior o esforço, menor o score

A coluna Tarefa precisa ser igual ao título no TASKS.md. Ajuste I/U/E aqui ou na aba Ranking do dashboard.

| Tarefa | I | U | E | Por quê |
|---|---|---|---|---|
| Rotacionar certificados TLS Safra | 4 | 5 | 2 | Certificado vencido derruba cliente em produção; prazo duro |
| Integração Banco Pine: auto-quote / quartix-markets / octaxpro | 5 | 4 | 4 | Receita nova com banco; já em WIP; depende do seu quant |
| Ajustes de pricing no auto-quote | 4 | 4 | 2 | Minimum spread/manual-quote afetam receita por cotação e a integração Pine |
| timeout ngrok safra #platforms/oxpro | 5 | 3 | 3 |  |
| Deploy quartix-markets | 4 | 4 | 3 | Sem deploy, os releases não chegam ao cliente |
| aumentar streaming workers | 4 | 3 | 3 |  |
| mail alerts pulse | 4 | 3 | 3 |  |
| criar conta de cliente por tela | 4 | 3 | 3 |  |
| ajustar suspend octax-api | 4 | 3 | 3 |  |
| ajustar suspend octax-api, operations on tradingsettings_api | 4 | 3 | 3 |  |
| Advisory: material de apoio a terceiro (estratégia financeira cross-border) | 3 | 3 | 2 | Receita de serviço via parceiro; já em WIP |
| Integrar Braza API | 4 | 2 | 3 | Nova integração/receita no cfx; sem prazo conhecido |
| Operacional | 3 | 3 | 2 | Atritos operacionais em clientes (Safra, alertas, contas) |
| clearfxai whitelabel / PRX | 4 | 2 | 4 | Canal whitelabel; esforço alto |
| SRE / metaox: painel de monitoração, cron tasks, CI/CD | 3 | 3 | 4 | Reduz trabalho manual e risco; delegável |
| Tela de apuração / earnings do partner (UX) | 3 | 2 | 2 | Transparência para parceiros |
| clearfxai control-plane: atualizar OS c/ detalhes dos clientes; rfqd | 3 | 2 | 2 | Operação do cfx |
| Bugfix: deletar conta-company demora demais | 2 | 3 | 1 | Bug visível, correção barata |
| Sangria diária de dados de produção (octaxpro → plataforma de dados) | 3 | 2 | 3 | Base de dados p/ analytics/intelligence; sem prazo; reclassificado de "data leak" |
| Release cherry / PortAR | 3 | 2 | 3 | Integração de parceiro; sem prazo conhecido |
| flow.sight: análise period-over-period, flow.sight spot, ideias | 3 | 2 | 3 | Melhora produto existente; depende do seu quant |
| Testes: UI (Playwright), API, API mock, autotests das libs | 3 | 2 | 3 | Reduz regressões; delegável |
| clearfxai / quartix advisory | 3 | 2 | 3 | Linha de serviço; ainda difusa |
| Release Plexus (valorpro): integrar à plataforma qxmarkets | 2 | 3 | 3 | Consolida cliente valorpro na plataforma |
| Integração oxpro / plexus-backend / octaxpro | 3 | 2 | 4 | Dívida de integração; esforço alto |
| CI/CD | 3 | 2 | 4 | Ganho de produtividade do time; delegável |
| bpipe cortesia | 2 | 2 | 1 | Pequeno; contexto pouco claro |
| Revisar taxonomia | 2 | 2 | 2 | Base do quartix-intelligence, que está em modo exploratório |
| Opensource Fernando | 2 | 2 | 2 | Visibilidade/comunidade |
| octaxpro addon / excel-plugin | 3 | 1 | 3 | Diferencial de produto; sem demanda urgente |
| Organizar repos | 2 | 2 | 2 | Higiene de engenharia |
| Release hedgeOS (Damke) | 1 | 4 | 4 | Produto novo com cliente-alvo definido; precisa estar pronto p/ a apresentação |
| MOU empresa nova / QUARTIX ADVISORY | 1 | 3 | 2 | Parceria/novo negócio pendente; estava parado |
| Pitch e segmentos | 1 | 3 | 3 | Necessário para captação e para vender hedgeOS |
| Platform overhaul | 3 | 1 | 5 | Refatoração grande; adiar até depois dos releases |
| quartix-intelligence: datalake | 3 | 1 | 5 | Exploratório e caro |
| settings-apps-spotlight | 2 | 1 | 2 | Melhoria pequena de UX |
| News + calendar | 2 | 1 | 2 | Já existe no LAUNCHPAD; incremental |
| Ask for strategic capital | 1 | 3 | 4 | Fôlego financeiro e escala do time; processo longo, começar cedo (e-mail estilo Dropbox) |
| Frentes Marcos I9DC | 1 | 2 | 2 | Frente estratégica; contexto pouco claro |
| Design do ambiente quartix-markets live (market.desk?) | 2 | 1 | 3 | Indefinido |
| messaging-integration | 2 | 1 | 3 | Sem demanda clara |
| Manifesto / blog planning | 2 | 1 | 3 | Marketing de longo prazo |
| Marketing farm / Braindump marketing | 2 | 1 | 3 | Marketing de longo prazo |
| Chat prototype / isabel | 2 | 1 | 3 | Exploratório |
| Content publishing platform | 2 | 1 | 4 | Exploratório e caro |
| Convite Damke: apresentar hedgeOS | 1 | 1 | 1 | Abre a 1ª venda do hedgeOS; custo de uma mensagem; estava parado |
| Follow up Fernando Silveira | 1 | 1 | 1 | Conversa parada; esfria se demorar; custo mínimo |
| Overhaul do data-store de docs | 2 | 1 | 5 | Refatoração grande sem dor urgente |
| Alvos hedgeOS | 1 | 1 | 2 | Pipeline comercial do hedgeOS (Campanelli, Santander, Giva, FK…) |
| Transformar livro em skill | 1 | 1 | 2 | Pessoal/experimental |
| Integração com Port.AR | 1 | 1 | 3 | Ligada ao hedgeOS; contexto pouco claro |
| Research / opensource | 1 | 1 | 3 | Exploratório |
