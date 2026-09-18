# Go-live — subir o bot e o painel num servidor Windows

O `README.md` descreve o projeto. Este arquivo cobre só uma coisa: colocar o bot
e o painel de chamados no ar num servidor, com a Evolution apontando para eles.

## O que foi acrescentado ao projeto

| arquivo | o que é |
| --- | --- |
| `run.bat` | sobe os dois serviços — é o que você executa |
| `parar.bat` | derruba os dois |
| `servidor-painel.mjs` | serve o painel e repassa `/internal/*` para o bot |
| `.env` | a configuração — um arquivo só (ignorado pelo git) |
| `activity-dashboard/` | o painel de chamados |

| serviço | porta | exposto? | o que é |
| --- | --- | --- | --- |
| painel | **8511** | sim, pelo túnel | quadro de chamados, e a porta que a Evolution alcança |
| bot | 9511 | não | processa os webhooks e expõe a API de chamados |

**Uma porta pública atende os dois.** O túnel da Cloudflare aponta para a
**8511**, do painel, e é o painel que repassa `/webhook` e `/internal/*` para o
bot em `127.0.0.1:9511`. A Evolution nunca fala com o bot diretamente.

Duas consequências que economizam confusão:

- **o bot não precisa de porta pública** — mudá-la não mexe em nada na Evolution
  nem no túnel;
- **a 8511 é fixa** porque é para lá que o túnel aponta. Trocá-la exige
  reapontar o túnel, e enquanto isso não acontece o domínio bate no bot, que
  não tem rota `/` e responde `{"erro":"rota não encontrada"}`.

A 9511 do bot está deliberadamente **fora da faixa 8500–8600**, reservada a
outros serviços deste servidor. A 8511 é a exceção carimbada para o painel.

## Um único `.env`

Toda a configuração vive em **`.env`**. O `run.bat` e o `npm run dev` leem o
mesmo arquivo; não existe `.env.producao` nem nada paralelo. O `.env.example`
segue sendo apenas o modelo comentado, para consulta.

Os valores estão ajustados para **produção**: porta 9511, Evolution de verdade,
`TRUST_PROXY=1`, caminho do banco e prazos de operação definidos.

No fim do arquivo há um bloco **MODO DE TESTE LOCAL** comentado. Descomentar
aquelas cinco linhas devolve o comportamento de desenvolvimento — porta 3000,
credenciais de mentira e a Evolution falsa em `127.0.0.1:4000` — sem trocar de
arquivo. Elas vêm depois das de produção de propósito: o dotenv fica com a
última ocorrência de cada chave, então as de baixo vencem.

Esse bloco serve ao `npm run dev`. O `run.bat` continua exigindo os valores
reais da Evolution, e deve mesmo: um go-live apontado para a Evolution de
mentira sobe sem erro nenhum e não entrega uma única mensagem.

`.env` está coberto pelo `.gitignore`. Ele guarda segredo; não commite.

---

## 2. Preencher os três valores do `.env`

O `run.bat` se recusa a subir enquanto qualquer um deles ainda estiver marcado
com `PREENCHER_`:

| variável | onde encontrar |
| --- | --- |
| `EVOLUTION_URL` | o endereço da sua instalação da Evolution, com `https` e sem barra no fim |
| `EVOLUTION_API_KEY` | a `AUTHENTICATION_API_KEY` da instalação, ou o token da instância |
| `EVOLUTION_INSTANCIA` | o nome da instância conectada — `GET /instance/fetchInstances` lista |

`DATABASE_URL` **saiu desta lista** na troca do Postgres pelo SQLite: não há mais
senha, host nem porta para acertar. O valor que vem no `.env`
(`file:./dados/whatsapp-suporte.db`) funciona como está, e o caminho relativo é
resolvido contra a raiz do projeto — não contra o diretório de onde o comando foi
rodado.

> Vale registrar por que ela estava aqui: a senha era o único valor que o
> `run.bat` não conseguia checar. Senha errada passava pelo passo 2 como ".env
> preenchido" e morria no passo 6, com `P1000: Authentication failed` — mensagem
> que manda procurar no lugar errado, porque um P1000 só existe se o servidor
> respondeu. A classe inteira de problema desapareceu junto com o servidor.

> **A instância tem de estar conectada.** Uma instância desconectada aceita o
> `POST` de envio e não entrega nada. Confira o `state` em
> `GET /instance/connectionState/<instancia>` antes de dar o go-live por feito:
> tem de ser `open`.

`WEBHOOK_SEGREDO`, `INTERNAL_API_TOKEN` e `PAINEL_TOKEN` já vieram gerados
(aleatórios, 256 bits). Não precisa mexer.

## 3. Subir

Execute **`run.bat`**. Tudo acontece numa **janela só** — ela é a aplicação.

O `run.bat` confere o ambiente:

1. Node presente e ≥ 24
2. `.env` existe e não tem pendências
3. `WEBHOOK_SEGREDO` com 16 caracteres ou mais — é a única prova de origem do webhook
4. login do Entra: as quatro variáveis, ou nenhuma — meia configuração não sobe
5. lê o `PORT` do `.env` — é ele que manda, não um número fixo no script
6. portas livres
7. dependências instaladas (`npm ci` se faltarem)
8. `prisma generate` e `prisma migrate deploy`
9. `npm run build`

Qualquer um desses que falhe interrompe tudo com a mensagem do que fazer — e
sem deixar meio serviço no ar.

Passado o ambiente, ele entrega o bastão ao **`iniciar.mjs`**, que roda na mesma
janela e cuida da execução: sobe o bot, espera o `/health`, confere o `/ready`
(isso é o banco — se recusar, o bot está de pé mas não grava chamado), sobe o
painel e imprime o resumo.

Os dois serviços viram **filhos** desse supervisor, e cada linha de log sai
marcada com a origem:

```
[bot   ] {"level":30,...,"msg":"Server listening at http://127.0.0.1:9511"}
[painel] [painel] login pelo Entra ID, tenant 5a29ae3d-...
[iniciar]   NO AR
```

**Um Ctrl+C encerra os dois.** O bot trata `SIGINT` e fecha o banco direito.

> Eram três janelas até então: a do `run.bat` mais uma por serviço. Três custam
> mais do que parecem — ninguém sabe qual olhar quando algo falha, fechar a
> errada derruba metade do sistema sem aviso, e ninguém percebe que só metade
> voltou.

**Se o bot não responder, o painel sobe do mesmo jeito** — e isso é de
propósito. O painel serve a página sozinho e só procura o bot na hora de buscar
um chamado; segurá-lo aí trocaria "quadro aberto, dizendo o que falta" por
"portal que não abre", que é pior de diagnosticar. O resumo avisa em qual dos
dois estados a máquina ficou (`NO AR` ou `PAINEL NO AR - BOT FORA`).

Depois de tudo no ar, porém, a regra se inverte: **se um dos dois morrer, o
supervisor derruba o outro e sai com código 1.** Meio sistema rodando é o
estado que mais engana — o painel abre, o atendente trabalha, e nada do
WhatsApp entra. Cair inteiro é o que faz alguém perceber (e o que permite ao
Agendador de Tarefas reiniciar).

Nada precisa ser reiniciado quando o bot voltar: cada requisição do painel abre
a sua própria conexão, então a atualização seguinte do quadro (30 s) já traz os
chamados.

Para subir **só o painel** — janela fechada sem querer, máquina reiniciada, ou
o painel no Agendador de Tarefas — use **`painel.bat`**. Ele lê a porta do
`.env` e roda o servidor na própria janela, então fechar a janela para o
painel.

Para parar: **Ctrl+C na janela**, que é o caminho normal. Fechar a janela também
serve — conferido: nem o bot nem o painel sobrevivem ao fim do supervisor, e as
portas ficam livres.

**`parar.bat`** continua útil para o caso de sobrar algo de uma execução
anterior. Ele mata por porta, não por `node.exe` — um `taskkill` em `node.exe`
levaria junto o `npm run dev` e qualquer outro Node aberto na máquina.

### Atualizando uma instalação que já está no ar

O passo 6 do `run.bat` é `prisma migrate deploy`, então **subir de novo aplica as
migrações pendentes** — não há comando extra a rodar. O ciclo é:

```
parar.bat
git pull
run.bat
```

`parar.bat` primeiro **não é opcional** quando há migração de estrutura: o SQLite
é um arquivo, e um processo com o banco aberto faz o `migrate deploy` falhar com
`database is locked`. A mensagem é clara, e nada é aplicado pela metade — mas o
serviço fica parado até você fechar o que estava segurando o arquivo.

> [!info] A migração de 2026-08-31 (`classificacao_de_chamados`) merece um aviso
> Ela **reconstrói a tabela `Chamado`** — é assim que o SQLite adiciona coluna —,
> derruba a view `chamados_para_cards` antes e a recria depois, e **semeia os 11
> setores iniciais** (TI, Financeiro, Operações, Marketing, Manutenção, RH,
> Comercial, Jurídico, Suprimentos, Logística, Expansão).
>
> Nada precisa ser rodado à mão: a recriação da view está dentro da própria
> migração, justamente porque ela roda em servidor sem ninguém por perto. E os
> setores entram com `INSERT OR IGNORE`, então rodar num banco que já os tenha
> mantém o que existe em vez de falhar.
>
> **Faça uma cópia de `dados/whatsapp-suporte.db` antes.** Reconstrução de tabela
> não tem volta, e é o único momento deste projeto em que isso vale o incômodo.

## 4. Expor por HTTPS

**A Evolution não alcança `localhost`** — a não ser que ela rode na mesma
máquina. Fora isso, precisa de uma URL pública. E de HTTPS, por um motivo que
mudou de natureza na saída da Meta: o segredo do webhook viaja no **caminho** da
URL, não num cabeçalho, então em HTTP ele passa legível pela rede.

O painel, com login pelo Entra, precisa do mesmo: o Entra só aceita
`redirect_uri` em `http://` quando é `localhost`.

### A topologia em uso

Um nome DNS só, atendendo os dois serviços:

```
                            ┌────────────────────────────────┐
 Evolution ─┐                │  servidor-painel.mjs  :8511    │
            ├─ Cloudflare ──►│                                │
  navegador ┘    Tunnel      │  /webhook/<segredo> ─► bot:9511│
    (HTTPS)     (termina o   │  /internal/*        ─► bot:9511│
                 TLS)        │  resto              ─► arquivos│
                            └────────────────────────────────┘
```

O túnel entrega **tudo** na 8511 e o painel roteia por caminho. Isso é o que faz
um nome só bastar. O `/webhook` passa **antes** do portão do Entra, e tem de
passar: a Evolution não faz login — ela se autentica pelo segredo do caminho.

> O painel casa `/webhook` **e tudo abaixo dele**, de propósito: com o segredo no
> caminho, casar só o caminho exato mandaria a Evolution para a tela de login. O
> sintoma seria mensagem que nunca chega, sem erro em lugar nenhum. Quem julga o
> segredo é o bot, não o painel — segredo errado vira 404 lá.

### Subir o túnel

O arquivo de exemplo está em **`cloudflared.exemplo.yml`**, já com o domínio.

```
cloudflared tunnel login
cloudflared tunnel create suportebio
cloudflared tunnel route dns suportebio suportebio.portalbiomundo.com.br
```

O `create` imprime o UUID e o caminho do arquivo de credenciais — são as duas
linhas `PREENCHER` do exemplo. Copie-o para
`C:\Users\<você>\.cloudflared\config.yml` e rode:

```
cloudflared tunnel run suportebio
```

Funcionando, instale como serviço do Windows para sobreviver a reboot:

```
cloudflared service install
```

### Duas consequências no `.env`

- **`PAINEL_TLS_CERT` / `PAINEL_TLS_KEY` ficam vazios.** Quem faz HTTPS é a
  Cloudflare; o painel serve HTTP em claro na própria máquina. O cookie de
  sessão ganha o atributo `Secure` de qualquer forma, porque quem decide isso é
  o `PAINEL_URL_BASE` começar com `https`.
- **`PAINEL_HOST=127.0.0.1` passa a ser o certo.** Com o túnel, quem alcança o
  painel é o `cloudflared`, da própria máquina. O padrão (`0.0.0.0`) deixaria a
  porta 8511 aberta na rede local também — um segundo caminho de entrada, esse
  sem o login do Entra na frente.

`TRUST_PROXY=1` continua correto: o `repassar` do painel é transparente, não
acrescenta `X-Forwarded-For`, então o bot continua vendo **um** proxy (a
Cloudflare) e extrai dali o IP real de quem escreveu.

## 5. Configurar a Evolution

Três coisas, nesta ordem: ter a instância, conectar o número, cadastrar o
webhook. Pular a ordem não quebra nada, mas gera silêncio difícil de explicar —
webhook cadastrado numa instância desconectada não entrega nada e não avisa.

> [!warning] Antes de conectar o número, suba o `servidor-painel.mjs` atual
> A versão anterior casava `/webhook` **exato** e manda `/webhook/<segredo>`
> para a tela de login do Entra. Com ela no ar, as mensagens chegam na
> Cloudflare e morrem num 302 — sem erro em lugar nenhum, nem aqui nem na
> Evolution. Confirme com `node diagnostico.mjs` (bloco 4) antes de seguir.

### 5.1 A instância

A Evolution organiza tudo por **instância**: uma instância = um número de
WhatsApp. O nome dela entra no `.env` (`EVOLUTION_INSTANCIA`) e na URL de envio.

Pelo Manager (a interface web da Evolution) é o caminho normal: **Instances →
Create**, nome `suporte`, integração **Baileys**. Pela API dá no mesmo:

```
curl -X POST "$EVOLUTION_URL/instance/create" ^
  -H "apikey: SUA_AUTHENTICATION_API_KEY" -H "content-type: application/json" ^
  -d "{\"instanceName\":\"suporte\",\"integration\":\"WHATSAPP-BAILEYS\",\"qrcode\":true}"
```

Se ela já existe, `GET /instance/fetchInstances` lista os nomes — e é de lá que
sai o valor exato de `EVOLUTION_INSTANCIA`, que diferencia maiúscula de
minúscula.

### 5.2 Conectar o número

No Manager, **Connect** mostra o QR code; no celular, *Aparelhos conectados →
Conectar aparelho*. Pela API o QR sai em `GET /instance/connect/suporte`.

O QR expira em cerca de 40 segundos e é regerado — não é erro.

Confirme que pegou:

```
curl -H "apikey: SUA_API_KEY" "$EVOLUTION_URL/instance/connectionState/suporte"
```

Tem de dizer `"state":"open"`. `connecting` é QR ainda não lido; `close` é sessão
caída.

> [!danger] O número é um aparelho conectado, não uma credencial de servidor
> Esta é a diferença de natureza em relação à Meta, e ela tem consequências que
> não são detalhe:
>
> - **Use um número dedicado ao suporte.** A sessão é do WhatsApp comum; o
>   número não deve estar em uso por outra ferramenta ao mesmo tempo.
> - **A sessão cai.** Chip trocado, "sair de todos os aparelhos", muito tempo
>   sem o celular ver a internet — e o bot passa a responder para o vazio: o
>   `POST` de envio é aceito e nada é entregue. Monitorar `connectionState` é o
>   que transforma isso em aviso em vez de em reclamação de franqueado.
> - **Baileys não é a API oficial.** Volume alto e disparo para quem não
>   escreveu primeiro são o caminho conhecido para banimento. Este bot só
>   responde a quem inicia a conversa, que é o uso de menor risco — vale manter
>   assim.

### 5.3 O webhook

No painel da Evolution, na **instância → Webhook**:

| campo | valor |
| --- | --- |
| URL | `https://suportebio.portalbiomundo.com.br/webhook/SEU_WEBHOOK_SEGREDO` |
| Enabled | ligado |
| Events | marque **`MESSAGES_UPSERT`**, e só ele |

Marcar `MESSAGES_UPSERT` é o que faz as mensagens chegarem. Sem esse evento o
webhook fica cadastrado e mesmo assim nada acontece — é o erro mais comum e o
mais difícil de perceber.

**Não marque `SEND_MESSAGE`.** As mensagens que o próprio bot envia voltariam
como evento; ele as descarta pelo `key.fromMe`, mas é tráfego que não serve para
nada. (Se marcar por engano, nada quebra — só é ruído.)

> **Não existe handshake.** A Evolution não valida a URL antes de usá-la: ela
> simplesmente começa a postar. Um erro de digitação no segredo não aparece no
> momento de salvar — aparece como silêncio.

Por isso, confira você mesmo. Da própria máquina:

```
curl -i -X POST "http://127.0.0.1:9511/webhook/SEU_WEBHOOK_SEGREDO" -H "content-type: application/json" -d "{\"event\":\"connection.update\",\"instance\":\"teste\",\"data\":{}}"
```

Deve responder **200**. Trocando o segredo por qualquer outra coisa, **404**.
O evento `connection.update` é lido e descartado pelo bot, então isso não cria
chamado nem manda mensagem para ninguém.

Depois, o mesmo pelo domínio. Se responder 200 na máquina e 302 pelo domínio, é o
painel no ar que está desatualizado (ver a topologia acima); se der 404 pelo
domínio, o segredo cadastrado não é o que o processo carregou.

Ou rode `node diagnostico.mjs`, que faz os dois e mais o resto.

E confirme o que a Evolution **realmente gravou**, que nem sempre é o que a tela
mostrou — o formato do corpo de `/webhook/set` mudou entre versões da v2, e um
`enabled` no nível errado salva um webhook desligado sem reclamar:

```
curl -H "apikey: SUA_API_KEY" "$EVOLUTION_URL/webhook/find/suporte"
```

Tem de voltar a URL com o segredo, `enabled: true` e `MESSAGES_UPSERT` na lista.

### 5.4 A primeira conversa

Mande "oi" de outro celular para o número da instância. O esperado é o menu de
assuntos numerado chegar em segundos. Se não chegar, a ordem de suspeita é:

| onde olhar | o que prova |
| --- | --- |
| `connectionState` | a instância está `open`? |
| `webhook/find` | a URL e o `MESSAGES_UPSERT` estão gravados? |
| `node diagnostico.mjs` | o domínio entrega no bot (200), ou dá 302/404? |
| log do bot | chegou requisição no `/webhook`? Se não chegou, o problema é antes dele |

## 6. O painel

`http://localhost:8511` no servidor, ou `http://IP-DO-SERVIDOR:8511` da rede.

Sobe junto pelo `run.bat`, ou sozinho pelo `painel.bat`. Ele não depende do bot
para abrir: sem o bot, o quadro aparece e mostra `bot fora do ar em
127.0.0.1:9511` no lugar dos cartões. Um 502 nessa mensagem é sempre isso — o
painel no ar e o bot não — e nunca um problema do navegador ou do painel.

**Quem autentica é o servidor.** Com `PAINEL_TOKEN_NO_SERVIDOR=1` no `.env` —
como está nesta instalação — o `servidor-painel.mjs` injeta o `PAINEL_TOKEN` em
cada chamada a `/internal/*`. O atendente abre o endereço e cai direto no
quadro: não há token para digitar, e o token não chega ao navegador.

O preço é explícito: **o token é a única autenticação do painel.** Com ele no
servidor, quem alcança `IP-DO-SERVIDOR:8511` tem acesso — lê nome, telefone e
descrição dos chamados, e move cartão, o que dispara WhatsApp para uma pessoa
real. Isso só se sustenta com a porta restrita à rede interna ou atrás de VPN.
Não publique o painel na internet com essa chave ligada.

Com `PAINEL_TOKEN_NO_SERVIDOR=0` volta o comportamento anterior: o painel pede o
token na primeira abertura. Ele fica em `sessionStorage` e some ao fechar a aba,
a menos que a pessoa marque "Lembrar neste navegador" — o padrão é não lembrar
de propósito, porque esse token altera chamado e dispara WhatsApp.

### O que o painel faz desde 2026-08-31

O quadro deixou de ser só "mover cartão entre colunas":

- **Seis colunas** em vez de quatro. Entraram AGUARDANDO RESPOSTA (chamado parado
  esperando quem pediu — esse tempo não é demora da equipe) e FECHADO
  (encerramento administrativo depois de resolvido).
- **Criar chamado** pelo botão *Criar*. O formulário pede o **tipo** primeiro:
  ele decide se a tela mostra os campos de chamado interno (setor de origem,
  sistema afetado, impacto, tempo estimado) ou de franquia (unidade, franqueado,
  localização, custo, urgência comercial).
- **Clicar no cartão** abre a ficha completa e **tudo o que tem rota para
  persistir é editável ali**: setor, prioridade, responsável, prazo, canal,
  contato e os campos do bloco do tipo. Não há botão de salvar — cada campo grava
  ao sair dele, porque um botão criaria o estado "mudei e não salvei", que é onde
  o trabalho se perde quando alguém fecha a aba. Resumo, descrição e nome do
  solicitante continuam travados: vieram da conversa e não há rota para
  reescrevê-los.
- **Comentário interno, anexo e dependência** na mesma ficha. Comentário nunca
  vira mensagem de WhatsApp; anexo aceita imagem, PDF, texto e Office até
  `ANEXO_MAX_BYTES` (padrão 5 MB) e vai para dentro do próprio arquivo do banco.
- **Setores** na barra lateral: a lista de áreas que atendem, compartilhada e
  editável sem deploy. Não é a lista de *Assuntos* — assunto é o que o cliente lê
  no menu do WhatsApp.
- **Filtros** por assunto, setor, tipo, prioridade e responsável, e o *Resumo*
  passou a mostrar três cortes do período: por assunto, por setor e por tipo.

Nada disso mora no navegador. **Todos os atendentes veem os mesmos chamados, os
mesmos setores e as mesmas pessoas** — o quadro lê e escreve no banco, e a única
coisa guardada localmente é o token (quando ele não está no servidor) e a
preferência de "avisar usuário ao mover".

O painel **não** fala com a porta 9511 direto: o `servidor-painel.mjs` repassa
`/internal/*` para o bot. Isso deixa painel e API na mesma origem, e é o que faz
o quadro funcionar por `localhost`, por IP da rede ou por domínio sem
reconfigurar `PAINEL_ORIGENS` a cada endereço novo. Por isso `apiBaseUrl` está
vazio em `activity-dashboard/data.js`, e `PAINEL_ORIGENS` está comentado no
`.env`: nenhum dos dois é necessário enquanto o painel for servido assim.

Para publicar o painel na internet também, aponte outro host do seu proxy para
`127.0.0.1:8511` — mas ele mostra nome, resumo e descrição dos chamados, que são
dado pessoal. Prefira deixá-lo só na rede interna ou atrás de VPN. E se
`PAINEL_TOKEN_NO_SERVIDOR=1`, não faça isso de jeito nenhum sem uma camada de
autenticação na frente: sem o token no navegador, a URL pública seria acesso
aberto ao histórico de chamados.

## 7. Login pelo Microsoft Entra ID

Opcional, e desligado por padrão. Enquanto as variáveis `ENTRA_*` do `.env`
estiverem em branco, o painel sobe como sempre subiu. Preenchidas, ele passa a
exigir conta da empresa antes de entregar qualquer coisa — inclusive o
`index.html`.

O login acontece **no servidor**, não no navegador: o `servidor-painel.mjs` faz
o authorization code com PKCE e guarda um cookie de sessão assinado e HttpOnly.
Nenhum token da Microsoft chega ao navegador. É isso que faz a proteção cobrir
os arquivos estáticos também — num login feito no navegador, o `app.js` ficaria
aberto para quem alcançasse a porta.

### O que criar no Entra

Em **portal.azure.com → Microsoft Entra ID → App registrations → New registration**:

| campo | valor |
| --- | --- |
| Name | Painel de chamados (ou o que preferir) |
| Supported account types | Accounts in this organizational directory only |
| Redirect URI | plataforma **Web**, valor `<PAINEL_URL_BASE>/auth/retorno` |

Depois, ainda dentro do app:

1. **Certificates & secrets → New client secret.** Copie o **Value** na hora —
   ele não aparece de novo. Anote a validade: quando o segredo expirar, o login
   para de funcionar, e a mensagem no log é a da Microsoft, não uma nossa.
2. **Enterprise applications → (o app) → Properties → Assignment required = Yes**,
   e em **Users and groups** atribua a equipe de TI. É aqui, e não no código,
   que se decide quem entra: uma segunda lista no `.env` seria uma cópia para
   divergir desta. Atribuir por **grupo** exige Entra ID P1; por **usuário**
   funciona em qualquer plano.

As permissões delegadas `openid`, `profile` e `email` já vêm por padrão e bastam.
Não é preciso consentimento de administrador.

### O redirect URI é a parte que mais quebra

Ele tem de bater com `PAINEL_URL_BASE` + `/auth/retorno` **caractere a**
**caractere** — porta incluída, sem barra sobrando. E o Entra **só aceita**
**`http://` em `localhost`**: para a rede, tem de ser `https://` com nome DNS.
Publicar em `http://192.168.x.x:8511` e ligar o login são coisas incompatíveis,
e é por isso que o certificado (`PAINEL_TLS_CERT`/`PAINEL_TLS_KEY`) mora ao lado
das variáveis do login e não numa seção separada.

O `run.bat` imprime o redirect URI que o painel vai usar. Compare com o do
portal antes de sair testando.

### Quando alguém não consegue entrar

A recusa mais comum é **AADSTS50105**: a conta existe, mas não está atribuída ao
aplicativo. O painel traduz isso numa tela dizendo para pedir a atribuição à TI,
em vez de mostrar o código da Microsoft. O código completo fica no log da janela
do painel.

Para desligar o login sem mexer em mais nada, apague (ou comente) as quatro
variáveis `ENTRA_*`. Deixar só algumas preenchidas **não sobe**: o painel
recusa, de propósito, para ninguém ficar sem a proteção que pediu achando que
está protegido.

### Cortar acesso na hora

Remover a pessoa do app no Entra impede o **próximo** login, mas a sessão já
aberta vale até vencer (`PAINEL_SESSAO_HORAS`, padrão 8). Para derrubar todo
mundo agora, troque o `PAINEL_SESSAO_SEGREDO` e reinicie o painel: todo cookie
existente deixa de conferir.

## 8. O cadastro de pessoas

A lista de **Pessoas** (nome e cor, as bolhas do quadro) mora no banco, na
tabela `Pessoa`, e é a mesma para todo mundo. Antes ela vivia no `localStorage`
de cada navegador, então cada atendente mantinha um cadastro só seu e ninguém
via o do outro.

Ela é **independente do login**. Quem pode entrar é o Entra que decide; este
cadastro é de exibição, e por isso não guarda e-mail nem identificador de
diretório — nada que sirva para autenticar. Acrescentar alguém aqui não dá
acesso a nada, e ter acesso não cria linha aqui.

A bolha do canto superior direito é a exceção: ela mostra **quem está logado**,
com as iniciais e o e-mail que vieram da Microsoft, e clicar nela encerra a
sessão aqui e no Entra. Sem login configurado, ela continua como estava.

---

## Depois de subir

- **Retenção: só metade está decidida.** O `.env` traz
  `RETENCAO_MENSAGENS_DIAS=1827` (5 anos) e `RETENCAO_CHAMADOS_DIAS=0`
  (desligado) — mensagem tem prazo, chamado não tem. Nada é apagado hoje porque
  não existe dado com 5 anos, e não porque o mecanismo esteja desligado. Falta
  decidir o prazo dos chamados e agendar `npm run retencao` num cron.
  Sessões abandonadas são limpas de qualquer forma (24 h).
- **Uma instância só.** Os limites por telefone vivem em memória, o que está
  correto assim. Ao subir uma segunda, preencha `REDIS_URL` — senão cada
  processo passa a ter a sua contagem e o limite efetivo dobra, em silêncio.
- **Reiniciar depois do boot do servidor:** o `run.bat` não se registra como
  serviço do Windows. Se a máquina reiniciar, alguém precisa rodá-lo de novo —
  ou você o coloca no Agendador de Tarefas com gatilho "ao iniciar o sistema".
  Para o painel, agende o `painel.bat`: ele roda o servidor na própria janela,
  então a tarefa espera pelo processo em vez de achar que terminou.
- **Docker e Render não incluem o painel.** O `Dockerfile` copia arquivo por
  arquivo (`src`, `prisma`, `sql`) e não pega `activity-dashboard/` nem os
  `.bat`. A imagem continua sendo só o bot — o caminho deste documento é outro,
  e os dois não se atrapalham.

## Se algo falhar

| sintoma | causa provável |
| --- | --- |
| `run.bat` diz "não existe .env" | falta criar; comece de `.env.example` |
| `run.bat` para em "porta já em uso" | serviço de uma execução anterior, ou o `npm run dev` aberto; rode `parar.bat` |
| `prisma migrate deploy` falha | `DATABASE_URL` não começa com `file:`, ou a pasta do arquivo não pode ser escrita |
| `database is locked` / `SQLITE_BUSY` | outro processo está escrevendo no banco: um `npm run dev` esquecido, um `sqlite3` aberto |
| bot não responde `/health` | veja as linhas `[bot   ]` na janela; quase sempre é variável faltando no `.env` — a mensagem lista qual |
| `/ready` recusa | o bot subiu, mas não consegue abrir o arquivo do banco — confira o `DATABASE_URL` e a permissão da pasta `dados/` |
| painel abre e diz "servidor fora do ar" | o bot caiu; a janela dele mostra o motivo |
| painel diz "token recusado" | é o `PAINEL_TOKEN`, não o `INTERNAL_API_TOKEN` |
| webhook cadastrado mas nada chega | faltou marcar o evento **`MESSAGES_UPSERT`** na instância |
| nada chega, e o domínio devolve 302 no webhook | o `servidor-painel.mjs` no ar é antigo: ele casa `/webhook` exato e manda `/webhook/<segredo>` para o login |
| nada chega, e o domínio devolve 404 no webhook | o segredo cadastrado na Evolution não é o `WEBHOOK_SEGREDO` que o bot carregou — reinicie o bot depois de mexer no `.env` |
| bot responde, mas ninguém recebe | a instância da Evolution está desconectada: `GET /instance/connectionState/<instancia>` tem de dizer `open` |
| bot subiu na porta 3000 | o bloco MODO DE TESTE LOCAL do `.env` está descomentado |
