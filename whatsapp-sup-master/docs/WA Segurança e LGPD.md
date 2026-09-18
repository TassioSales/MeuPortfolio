---
tags: [projeto/whatsapp-suporte, seguranca, lgpd]
projeto: whatsapp-suporte
atualizado: 2026-08-18
---

# WA Segurança e LGPD

Volta para [[WhatsApp Suporte]].

## A ameaça que define o desenho

Um `/webhook` sem autenticação não é só "aceita chamado falso". Quem
descobrisse a URL poderia fazer o bot **enviar mensagem para qualquer número** —
e isso costuma terminar com o número banido. Daí a autenticação acontecer no
roteamento, antes de qualquer lógica.

## Autenticação do webhook

[whatsapp/signature.ts](../src/whatsapp/signature.ts)

- O segredo vai no **caminho**: `POST /webhook/:segredo`, comparado ao
  `WEBHOOK_SEGREDO` por `segredoValido`.
- Segredo errado → **404**, e não 401. É deliberado: um 401 confirmaria que
  existe um webhook naquele caminho, e o `notFoundHandler` ainda mascara a URL
  como `/webhook/***` no log.
- `comparacaoSegura` usa `crypto.timingSafeEqual` com checagem de tamanho antes —
  um `===` sai no primeiro byte diferente e vaza, por medição de tempo, o quanto
  o atacante já acertou.

> [!warning] O que se perdeu ao sair da Meta
> O HMAC da Meta era calculado sobre os bytes crus do corpo e provava **duas**
> coisas: **quem** chamou e que o **corpo chegou intacto**. Um segredo no
> caminho prova só a primeira.
>
> Some-se a diferença de exposição: cabeçalho não é registrado por padrão em
> lugar nenhum; **caminho de URL aparece em log de proxy, em log de CDN e em
> histórico**. A Evolution não oferece assinatura de corpo — é o que ela
> permite configurar.
>
> O que isso obriga:
> - **HTTPS não é recomendação, é requisito.** Em HTTP o segredo viaja legível.
> - O segredo é longo (32+) e **rotacionável**: trocar é editar o `.env`,
>   reiniciar o bot e atualizar a URL na instância.
> - `req.url` entrou no `redact` do logger, junto com o cabeçalho `apikey`.
> - Um corpo adulterado em trânsito por quem esteja entre a Evolution e o bot
>   não é mais detectável. O TLS é o que cobre isso agora.

## Endpoint interno

`PATCH /internal/chamados/:id/situacao` exige
`Authorization: Bearer $INTERNAL_API_TOKEN`, também em comparação de tempo
constante. Subir um endpoint de **escrita** sem autenticação repetiria
exatamente o erro que a autenticação do webhook corrigiu.

`notificarUsuario` é **opcional e desligado por padrão**: manda mensagem para uma
pessoa real, então quem chama decide. Ver [[WA Outbox e entrega]].

## Limites

| limite | valor padrão | contra o quê |
| --- | --- | --- |
| corpo da requisição | 256 KB | payload gigante antes de alocar memória |
| caracteres por mensagem | 4096 | encher a coluna `texto` (que é `TEXT`, sem limite) |
| requisições/min por IP | 300 | flood **não autenticado** — proteção grossa |
| mensagens/min por telefone | 20 | **o controle de abuso que importa** |
| telefones rastreados no throttle | 50.000 | o `Map` virar vetor de exaustão de memória |

Por que o limite por IP é grosso: depois do segredo do webhook, todo tráfego
legítimo vem do mesmo lugar (a instalação da Evolution) — então limitar por IP
funciona quase como um teto global do endpoint. Por isso o valor é folgado e o
controle real é por telefone.

Atrás de proxy, `TRUST_PROXY` deixa de ser detalhe: sem ele o rate limit por IP
vira um contador único. Ver [[WA Configuração]].

## Validação de entrada

- `ehTelefoneValido` ([whatsapp/telefone.ts](../src/whatsapp/telefone.ts)):
  `/^\d{6,20}$/`. Este valor vai direto para o campo `to` da API de envio — é o
  que impede transformar o bot em relay para um destino arbitrário. Módulo
  próprio porque a regra é aplicada em três lugares (webhook, aviso de
  indisponibilidade, retenção) e três cópias da regex seriam três chances de
  divergir.
- `ehCampo` e `ehSituacao` são **whitelists de verdade**: um `as Campo` não
  valida nada em runtime, e id de botão desconhecido virando `etapa` explodia no
  banco.
- Id interno de botão nunca é aceito digitado — ver [[WA Fluxo da conversa]].

## Logs sem dado pessoal

[log.ts](../src/log.ts)

- `mascararTelefones`: sequências de 8+ dígitos viram `***7665`.
- `erroSeguro`: reduz o erro a tipo/código/mensagem truncada em 300 chars. Existe
  porque **erros do Prisma podem carregar os parâmetros da query** — telefone,
  nome e o texto do chamado — direto para o log.
- Fastify com `redact`: `authorization`, o cabeçalho `apikey` da Evolution e
  **`req.url`** são removidos dos logs de requisição. A URL entrou nessa lista
  ao sair da Meta, e por um motivo direto: agora é ela que carrega o segredo.
- Todo código fora de rota (outbox, varredor, limpeza) escreve no mesmo logger,
  injetado no boot por `usarLogger`. Antes o varredor usava `console.error`:
  saída sem estrutura e alheia ao `redact`.

## Dados pessoais armazenados

Nome, telefone e texto livre descrevendo o problema — em `SessaoConversa`,
`Chamado` e `Mensagem` (inclusive dentro de `payload`, que contém o corpo enviado
ao usuário).

## Retenção — mecanismo pronto, política pendente

```bash
npm run retencao                    # simula: mostra o que seria apagado
npm run retencao -- --confirmar     # apaga de verdade
```

[src/scripts/retencao.ts](../src/scripts/retencao.ts)

- **Modo simulação por padrão.** Só apaga com `--confirmar`.
- Apaga em **lotes de 1.000**: depois de meses sem política configurada, o
  primeiro `--confirmar` montaria um `IN (...)` gigante numa instrução só.
- Chamados antigos saem **com as mensagens deles** (a FK exige essa ordem).
- **Nada é apagado enquanto `RETENCAO_MENSAGENS_DIAS` /
  `RETENCAO_CHAMADOS_DIAS` não forem definidos** — o sistema não inventa prazo.
  O script avisa em letras claras quando está sem política.
- Em produção, agendar com cron.
- **Coberto por testes desde 2026-08-18** —
  [test/retencao.test.ts](../test/retencao.test.ts), 14 casos. Até então era o
  código mais destrutivo do repositório e o menos verificado.

> [!warning] Pendência de negócio, não de código
> Definir esses prazos é decisão do negócio e é o item mais antigo em aberto:
> ver [[WA Pendências]].

### A simulação já mentiu — para menos

Escrever os testes que faltavam encontrou um bug real. A contagem da simulação
olhava só `timestamp < corte de mensagens`, mas o `--confirmar` **também** apaga
as mensagens penduradas em chamados vencidos (a FK exige essa ordem).

Com `RETENCAO_CHAMADOS_DIAS=30` e `RETENCAO_MENSAGENS_DIAS=90`, um chamado de 60
dias produzia isto:

```
[SIMULAÇÃO] Seriam apagados 0 mensagem(ns), 1 chamado(s)      <- mentira
Apagados                    4 mensagem(ns), 1 chamado(s)      <- o que aconteceu
```

> [!danger] Num comando destrutivo, a simulação **é** a trava de segurança
> Uma trava que mente para menos é pior que nenhuma: ela produz confiança que
> não se justifica. O operador lê "0 mensagens", roda o `--confirmar` e descobre
> o estrago depois.

A contagem agora usa `OR` sobre os dois critérios — o `OR` também evita contar
em dobro a mensagem que se encaixa nos dois. Há teste fixando que **simulação e
realidade devolvem o mesmo número**.

## Sessões abandonadas são a exceção

`SessaoConversa` guarda nome, resumo e descrição de um chamado que **nunca foi
confirmado**. Antes o TTL era aplicado só de forma preguiçosa — a sessão vencida
era descartada quando *aquele* telefone mandava outra mensagem — então quem
abandonava na etapa da descrição e nunca voltava deixava esses dados no banco
para sempre.

Agora a varredura roda sozinha no processo (`LIMPEZA_SESSOES_MINUTOS`, e uma vez
no boot) e também no `npm run retencao`. Aqui **não há decisão de negócio**:
passado o `SESSAO_TTL_HORAS`, a sessão já seria descartada no próximo contato de
todo jeito.

## Direito à eliminação (titular)

```bash
npm run retencao -- --esquecer 5511998877665              # simula
npm run retencao -- --esquecer 5511998877665 --confirmar  # apaga
```

Remove chamados, mensagens e sessão daquele telefone. O telefone é validado antes
e aparece mascarado na saída.

Duas garantias com teste, porque aqui o erro tem dois lados e cada um é grave:

- **apaga tudo do titular** — mensagens soltas, mensagens ligadas aos chamados
  dele, os chamados e a sessão;
- **não encosta em mais ninguém** — o teste monta dois titulares e verifica que
  o segundo sai intacto.

> [!important] A validação do telefone não é frescura
> `--esquecer` sem argumento faria `telefone` virar `undefined`, e um
> `deleteMany` com filtro vazio apaga a tabela inteira. O telefone é validado
> antes de qualquer coisa e há teste cobrindo esse caminho.

## Minimização no acesso externo

A plataforma de cards consulta a view `chamados_para_cards`, que **não expõe
`telefone`**.

> [!danger] A view virou contrato, não fronteira
> Com o banco em SQLite não existe usuário nem `GRANT`: o controle de acesso é a
> permissão do **arquivo** no sistema operacional, tudo ou nada. Quem recebe o
> arquivo recebe TODAS as tabelas, telefone incluído — a view não protege nada
> nesse cenário, só documenta quais colunas o consumidor deve usar.
>
> Enquanto o banco era Postgres, dava para criar um papel somente-leitura com
> `SELECT` apenas na view. Hoje, para expor os cards sem entregar o banco, há dois
> caminhos: a rota `/internal/chamados` (mesma minimização de campos, exigindo
> token) ou entregar uma **cópia** do arquivo aberta em modo `readonly`. Nunca
> compartilhe o arquivo de produção. Ver [[WA Banco de dados]].

## Proteções do painel no navegador

[servidor-painel.mjs](../servidor-painel.mjs)

O painel serve HTML/JS por um processo próprio (não pelo Fastify), então o
`helmet` do bot **não** o cobre. As proteções abaixo vivem nesse servidor:

- **Cabeçalhos de segurança** em toda página servida (`CABECALHOS_SEGURANCA`):
  - `Content-Security-Policy` — `default-src 'self'`, `object-src 'none'`,
    `base-uri 'none'`, `frame-ancestors 'none'`. É a segunda linha caso um
    `esc()` seja esquecido no `app.js`. `style-src` inclui `'unsafe-inline'`
    porque os avatares pintam a cor com `style="background:"` inline; `img-src`
    inclui `data:` (SVG de fundo do CSS) e `blob:` (download de anexo).
  - `X-Frame-Options: DENY` + `frame-ancestors 'none'` — **anti-clickjacking**.
    Sem isso, um site de terceiro embutiria o painel em iframe e enganaria o
    atendente a arrastar um cartão — e mover cartão dispara WhatsApp para uma
    pessoa real.
  - `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer`.
- **CSRF por verificação de `Origin`** (`origemBloqueada`): todo pedido que
  ALTERA estado (`POST`/`PUT`/`PATCH`/`DELETE`) em `/internal/*` cujo `Origin`
  não seja o do próprio painel é recusado com 403 **antes** de tocar o bot. No
  modo com login do Entra, o cookie de sessão viaja sozinho, então antes disso
  só o `SameSite=Lax` segurava o CSRF; esta é a segunda tranca. Cliente sem
  `Origin` (curl, integração) continua passando — o CSRF de navegador sempre
  manda o cabeçalho. **O `/webhook` não é afetado**: a Evolution não manda
  `Origin` e se autentica pelo segredo do caminho.
- **Escape das cores** no `app.js`: `person.color` é inserido em
  `style="background:…"` e `value="…"` já escapado, mesmo com a validação
  `#RRGGBB` no servidor — para uma futura folga na regra não virar XSS por
  quebra de atributo. (As cores dos gráficos saem de tokens CSS do tema, não de
  dado de usuário.)

> [!danger] O modo aberto agora falha alto
> Sem login do Entra **e** com o token injetado no servidor
> (`PAINEL_TOKEN_NO_SERVIDOR=1`), quem alcança a porta lê e altera chamado sem
> autenticar. Se além disso o bind for para fora do loopback, o painel **recusa
> subir** (`process.exit(1)`), a menos que a exposição seja confirmada de
> propósito com `PAINEL_EXPOSICAO_SEM_LOGIN=1`. Saídas: ligar o login,
> `PAINEL_HOST=127.0.0.1`, ou a confirmação explícita para porta já atrás de
> firewall/VPN.

## Limite de anexos por chamado

[internal/detalhes.ts](../src/internal/detalhes.ts)

Cada anexo, além do teto de tamanho (`ANEXO_MAX_BYTES`), conta para um **teto de
`MAX_ANEXOS_POR_CHAMADO` (10) por chamado**. O binário mora dentro do SQLite, e
sem esse teto quem tem o token do painel poderia subir milhares de anexos e
encher o disco — e disco cheio derruba a escrita do webhook, ou seja, o serviço
inteiro. A contagem não está numa transação com a criação, então dois uploads
simultâneos podem passar de 10 por um: é limite grosso contra enchimento de
disco, não uma trava exata do décimo anexo.

## Higiene de segredos

- `.env` **não é versionado** (está no `.gitignore`) e não é copiado para estas
  notas.
- **Não há mais senha de banco para rotacionar**: SQLite não tem credencial. O
  que existe em troca é um arquivo com dado pessoal em disco — `dados/` está no
  `.gitignore` e no `.dockerignore`, e o arquivo **nunca** deve ser copiado para
  fora sem necessidade. Backup é dado pessoal também: guarde com o mesmo cuidado.
  Ver [[WA Banco de dados#Backup]].
- `INTERNAL_API_TOKEN` deve ser longo e aleatório: quem o tiver pode alterar
  qualquer chamado.
