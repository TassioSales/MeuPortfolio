---
tags: [projeto/whatsapp-suporte, apresentacao, demonstracao]
projeto: whatsapp-suporte
atualizado: 2026-09-17
---

# WA Demonstração

Volta para [[WhatsApp Suporte]].

> [!info] Para que serve esta nota
> [[WA Lançamento]] tem **o que o sistema faz** (a lista para quem decide) e
> **quando ele pode ir ao ar**. Esta nota é a outra metade: o **roteiro de
> execução** da apresentação — o que rodar, em que ordem, o que precisa aparecer
> na tela e a frase que amarra cada bloco à funcionalidade que ele prova.
>
> A ordem não é a ordem do código: é a ordem em que a plateia acredita. Primeiro
> a conversa funcionando (o que se vê), depois o que sustenta a promessa (o que
> não se vê), depois quem atende (painel), e só no fim os números de teste.

> [!warning] As saídas de terminal coladas aqui são de agosto/2026
> Elas foram capturadas **antes** da troca da Meta pela Evolution API (17/09), e
> ficaram como estão de propósito: são registro do que aconteceu, não modelo do
> que vai aparecer na tela hoje.
>
> Ao reexecutar o roteiro, três coisas saem diferentes:
> - **os menus vêm numerados em texto**, não como botão ou lista interativa;
> - o terminal 1 mostra `para <telefone> | texto`, com o menu por extenso;
> - o bloco de autenticação do webhook (9) mudou de assunto: não há mais
>   assinatura para forjar, há um **segredo no caminho** para errar.
>
> As **instruções** abaixo já estão atualizadas. As **capturas**, não.

> [!success] Ensaiado em 20/08/2026 — as saídas abaixo são log real
> Roteiro executado ponta a ponta contra Postgres 18 local e a Graph de mentira.
>
> **O banco mudou depois disso**: desde 27/08/2026 é um arquivo SQLite (ver
> [[WA Banco de dados]]). As saídas de log ficaram como foram capturadas, porque
> log real reescrito deixa de ser prova. Os **comandos** do roteiro estão
> atualizados, e onde a saída de hoje difere da registrada há uma nota ao lado.
> Os logs crus estão em [`ensaio-2026-08-20/`](ensaio-2026-08-20/) (um arquivo por
> bloco, mais os dois terminais inteiros). O que **varia** a cada execução: `#id`
> de chamado, `wamid`, horário e as contagens do `/estado`.
>
> O ensaio encontrou **um bug de verdade** (logo abaixo, já corrigido) e **duas
> afirmações erradas**: as armadilhas de PowerShell no
> [[#Pré-voo (10 min, na véspera e de novo 30 min antes)]] e a espera do outbox no
> [[#Bloco 8 — Graph fora do ar (o bloco que mais convence)]].

> [!success] Corrigido em 20/08 — o primeiro contato agora recebe a pergunta
> O ensaio expôs um bug de verdade, e ele foi corrigido no mesmo dia. Antes, no
> primeiro contato a sessão nascia na etapa `nome` e **o texto que chegou era
> gravado como nome**. Abrindo a conversa com "Bom dia, preciso de ajuda", o
> chamado #17 nasceu assim (log real, `B1-conversa.log`):
>
> ```
>   *Nome:* Bom dia, preciso de ajuda
>   *Resumo:* Natan Ferreira
>   *Descrição:* A impressora da loja 12 não puxa papel
> ```
>
> Agora a primeira mensagem recebe `Olá! Para abrir seu chamado, qual é o seu
> nome?` sem ser consumida, e o fluxo segue normal. Dois testes novos cobrem o
> primeiro contato — a suíte antiga passava porque o teste do fluxo feliz já
> começava mandando `'Natan'`. Ver [[WA Fluxo da conversa]] e o item fechado em
> [[WA Pendências]].
>
> **Para a apresentação:** abra a demo com um "bom dia", que é o que uma pessoa
> real escreve — o bloco 1 abaixo é o log **depois** da correção. E lembre que o
> chamado **#17 continua no banco de desenvolvimento** com os campos trocados:
> apague antes de mostrar a listagem do painel (bloco 10).

> [!note] Sobre o formato dos trechos de conversa
> O ensaio alimentou o simulador por stdin, e o modo interativo **não ecoa** o que
> foi digitado — no log cru a linha do usuário não aparece depois do prompt. Nos
> trechos abaixo ela foi recolocada no lugar onde apareceria se você digitasse à
> mão; é exatamente o texto que foi enviado. Tudo que o **bot** respondeu está
> verbatim, e o cru está arquivado.

## Antes de começar

### Pré-voo (10 min, na véspera e de novo 30 min antes)

| #   | Conferir                                      | Como                                                     | Se falhar                             |
| --- | --------------------------------------------- | -------------------------------------------------------- | ------------------------------------- |
| 1   | Banco com as tabelas (é um arquivo; nada para subir) | `npm run prisma:deploy`                            | ver [[WA Ambiente local]]             |
| 2   | Build atual (a retenção roda de `dist/`)      | `npm run build`                                          | sem isso o bloco 12 quebra            |
| 3   | `.env` apontando para a Evolution de mentira  | `EVOLUTION_URL=http://127.0.0.1:4000`                    | o bot falaria com a Evolution de verdade |
| 4   | Varredor rápido                               | `VARREDOR_INTERVALO_SEGUNDOS=15`                         | o bloco 8 fica ainda mais lento       |
| 5   | Evolution de mentira **não** está em modo falha | `curl.exe http://127.0.0.1:4000/_estado` → `"status":0`  | mande `{"status":0}` no `/_controle`  |
| 6   | Suíte e garantias de banco passando           | `npm test` e `npm run dev:verificar-banco`               | **não apresente** antes de resolver   |
| 7   | Telefone da demo sem sessão pendurada         | `npm run dev:simular -- estado`                          | digite `cancelar` na conversa         |
| 8   | Só **uma** Evolution de mentira rodando       | `Get-NetTCPConnection -LocalPort 4000 -State Listen`      | mate o processo antigo; a segunda morre com `EADDRINUSE` |

No ensaio, os itens 6, 7 e 8 valeram o tempo: o 8 aconteceu de verdade.

> [!danger] Três armadilhas de PowerShell que o ensaio pegou
> **1. `curl` não é curl.** No PowerShell 5.1 (o desta máquina) `curl` é alias de
> `Invoke-WebRequest` e não entende `-X`. Use **`curl.exe`** — é o que esta nota
> faz em todo comando. Os exemplos do [README](../README.md) usam `curl` e falham
> aqui.
>
> **2. Corpo JSON com `"` entre aspas duplas chega quebrado.** A forma do README
> (`-d "{\"situacao\":\"resolvido\"}"`) devolveu `{"erro":"JSON inválido"}` no
> ensaio. O que funciona é **aspas simples com as internas escapadas**:
>
> ```powershell
> -d '{\"situacao\":\"resolvido\",\"notificarUsuario\":true,\"autor\":\"Ana\"}'
> ```
>
> **3. Para olhar dentro do banco, `sqlite3`** — e ele também não está no PATH por
> padrão. O banco é o arquivo `dados/whatsapp-suporte.db`; não há usuário, senha
> nem query string para acertar (a armadilha antiga era o `?schema=public` da URL
> do Postgres, que o `psql` recusava):
>
> ```powershell
> sqlite3 dados\whatsapp-suporte.db "SELECT count(*) FROM \"Chamado\""
> ```
>
> Sem o `sqlite3` instalado, `npm run dev:simular -- estado` cobre o que a demo
> precisa mostrar. Com o WAL ligado, abrir o banco para ler **não** bloqueia o
> servidor.
>
> **4. Ao canalizar algo para dentro do `npm`, use `npm.cmd`.** O wrapper
> `npm.ps1` embrulha a saída de erro em `NativeCommandError` e polui a tela. Só
> importa quando você alimenta o simulador por _pipe_ (ver [[#Log da execução]]).

> [!warning] Duas coisas que sujam o ensaio (e sujaram o meu)
> **Limite por telefone: 20 mensagens/minuto.** Ensaiar vários blocos seguidos no
> mesmo telefone estoura a cota, e a mensagem é **descartada em silêncio** — o
> simulador só diz `bot: (nenhuma resposta ...)` e o `cancelar` que você mandou
> não acontece. Deixe um minuto entre blocos, ou use `TELEFONE=...` para trocar de
> telefone. (Isso também rendeu o [[#Bloco 14 — Limite por telefone]].)
>
> **O cenário `assinatura` injeta uma mensagem no fluxo.** A terceira requisição
> dele é válida e recebe 200, então o texto `deveria ser recusada` entra na
> conversa como valor do campo da etapa atual. Rode-o **antes** da conversa da
> demo, ou em outro telefone.

### Os quatro terminais

| Terminal                 | Comando               | O que a plateia vê nele                              |
| ------------------------ | --------------------- | ---------------------------------------------------- |
| **1 — Evolution de mentira** | `npm run dev:evolution` | o que sairia para o WhatsApp, com o menu numerado por extenso |
| **2 — servidor**         | `npm run dev`         | o log estruturado (telefone mascarado)               |
| **3 — usuário**          | `npm run dev:simular` | a conversa, do lado de quem abre o chamado           |
| **4 — atendimento**      | livre                 | `curl.exe` do painel, `sqlite3`, retenção            |

Terminal 3 é o protagonista; 1 é a prova de que a mensagem realmente sai; 2 entra
em cena no bloco 8. O telefone padrão do simulador é `5511999990000` — mantenha
esse, porque os subcomandos (`texto`, `botao`) usam ele sem precisar de variável
de ambiente.

### Duas versões do roteiro

| Tempo      | Blocos          | Quando usar                                       |
| ---------- | --------------- | ------------------------------------------------- |
| **5 min**  | 1 · 8 · 10 · 12 | reunião de status, ou quando cortarem seu horário |
| **20 min** | 1 a 14          | apresentação de verdade, com TI na sala           |

O corte de 5 minutos é proposital: **um** bloco de conversa, **um** de
confiabilidade, **um** de atendimento e **um** de LGPD. É o mínimo que responde
"funciona?", "e se cair?", "quem atende?" e "e a lei?".

## Roteiro em uma tela

| #   | Bloco                       | Prova                                             | Onde    | ~     |
| --- | --------------------------- | ------------------------------------------------- | ------- | ----- |
| 1   | Conversa completa           | fluxo guiado de 5 etapas (começa no assunto), chamado criado | T3 + T1 | 3 min |
| 2   | Corrigir antes de enviar    | menu de edição, volta à confirmação               | T3      | 1 min |
| 3   | Botão x texto digitado      | id de botão é protocolo interno                   | T3      | 1 min |
| 4   | Limites e resposta curta    | aviso amigável, não erro                          | T4      | 1 min |
| 5   | Cancelar sem falso positivo | comando só vale como mensagem inteira             | T3      | 1 min |
| 6   | Áudio e imagem              | limitação explicada, pergunta repetida            | T3      | 30 s  |
| 7   | Entrega duplicada           | webhook reentregue não avança o fluxo             | T3      | 1 min |
| 8   | **Graph fora do ar**        | resposta pendente e reentregue sozinha            | T3 + T1 | 3 min |
| 9   | Assinatura e lote           | payload forjado recusado; lote inteiro processado | T3      | 1 min |
| 10  | **Painel de chamados**      | listar, mudar situação, avisar, auditar           | T4 + T1 | 3 min |
| 11  | Erros do painel             | 401, 400 útil, 404 honesto                        | T4      | 1 min |
| 12  | **LGPD**                    | simulação, retenção e direito à eliminação        | T4      | 2 min |
| 13  | Garantias e testes          | health/ready + as duas suítes                     | T4      | 2 min |
| 14  | Limite por telefone         | flood descartado em silêncio                      | T3      | 1 min |

## Bloco 1 — A conversa completa

**Prova:** fluxo guiado `assunto → nome → resumo → descrição → confirmação`,
menu de assuntos, confirmação com botões, chamado nascendo no banco.

> ![[conversa-whatsapp-1.jpg]]
> ![[conversa-whatsapp-2.jpg]]
> Conversa real capturada com a Graph de mentira: menu de assuntos, coleta campo
> a campo, o cartão de confirmação com **Confirmar / Editar / Cancelar** e o
> `#12` nascendo no banco.

Terminal 3 — abra como um usuário abriria:

```
5511999990000> Bom dia, preciso de ajuda
bot [entregue]:
  Olá! Para abrir seu chamado, qual é o seu nome?
5511999990000> Natan Ferreira
bot [entregue]:
  Obrigado! Agora resuma seu problema em uma frase curta.
5511999990000> A impressora da loja 12 não puxa papel
bot [entregue]:
  Entendido. Pode descrever o problema com mais detalhes?
5511999990000> Desde ontem ela apita tres vezes e cancela o trabalho. Ja troquei a bandeja.
bot [entregue]:
  Confirma a abertura do chamado?

  *Nome:* Natan Ferreira
  *Resumo:* A impressora da loja 12 não puxa papel
  *Descrição:* Desde ontem ela apita tres vezes e cancela o trabalho. Ja troquei a bandeja.
  [ Confirmar ] [ Editar ] [ Cancelar ]
  (responda com: /botao confirmar | /botao editar | /botao cancelar)
```

Antes de confirmar, mostre o estado — é a hora de dizer que **nada disso é
chamado ainda**:

```
5511999990000> /estado

--- estado ------------------------------------------
sessão: etapa=confirmacao editando=false
        nome="Natan Ferreira" resumo="A impressora da loja 12 não puxa papel"
        descricao="Desde ontem ela apita tres vezes e cancela o trabalho. Ja troquei a bandeja."
chamado #22: aberto — A impressora da loja 12 não puxa papel
chamado #18: resolvido — A impressora da loja 12 travou de novo
chamado #17: aberto — Natan Ferreira
saídas pendentes no outbox: 0
-----------------------------------------------------
```

E confirme:

```
5511999990000> /botao confirmar
bot [entregue]:
  Chamado #27 aberto com sucesso! Em breve alguém da equipe vai te atender.
5511999990000> /estado

--- estado ------------------------------------------
sessão: (nenhuma)
chamado #27: aberto — A impressora da loja 12 não puxa papel
chamado #22: aberto — A impressora da loja 12 não puxa papel
chamado #18: resolvido — A impressora da loja 12 travou de novo
saídas pendentes no outbox: 0
-----------------------------------------------------
```

**`sessão: (nenhuma)`** é o ponto: a sessão guardava nome e texto livre e foi
apagada no mesmo instante em que o chamado nasceu. É o primeiro argumento de LGPD
da apresentação, e ele aparece de graça aqui. Ver [[WA Fluxo da conversa]].

**No terminal 1**, o que a Evolution receberia (log de agosto, `T1-graph.log` —
hoje o menu sai numerado em texto):

```
<< #48 2026-08-20T13:45:07.220Z
   para 5511999990000 | interativa (botões)
     Confirma a abertura do chamado?

     *Nome:* Natan Ferreira
     *Resumo:* A impressora da loja 12 não puxa papel
     *Descrição:* Desde ontem ela apita tres vezes e cancela o trabalho. Ja troquei a bandeja.
     [ Confirmar ] [ Editar ] [ Cancelar ]
     ids: confirmar, editar, cancelar
```

**Fala:** _"O usuário respondeu três perguntas e o chamado nasceu estruturado —
nome, resumo, descrição e situação em campos separados. Nenhum modelo de IA leu
nada: cada resposta foi para o campo da etapa em que ela chegou."_

## Bloco 2 — Corrigir antes de enviar

**Prova:** o menu de edição, e que ele **cresce sem quebrar**.

Continuando na confirmação (log real, `B2-B3-edicao.log`):

```
5511999990000> /botao editar
bot [entregue]:
  Qual informação deseja corrigir?
  [ Nome ] [ Resumo ] [ Descrição ]
  (responda com: /botao editar_nome | /botao editar_resumo | /botao editar_descricao)
5511999990000> /botao editar_resumo
bot [entregue]:
  Obrigado! Agora resuma seu problema em uma frase curta.
5511999990000> A impressora da loja 12 travou de novo
bot [entregue]:
  Confirma a abertura do chamado?

  *Nome:* Natan Ferreira
  *Resumo:* A impressora da loja 12 travou de novo
  *Descrição:* Desde ontem ela apita tres vezes e cancela o trabalho. Ja troquei a bandeja.
  [ Confirmar ] [ Editar ] [ Cancelar ]
  (responda com: /botao confirmar | /botao editar | /botao cancelar)
```

**Fala:** _"Corrigiu um campo e voltou direto para a confirmação — não recomeçou a
conversa. E o formulário tem três campos hoje: se amanhã vocês pedirem um campo de
setor, o menu passa sozinho de botões para lista, porque a API do WhatsApp só
aceita três botões. Nenhuma opção some da tela sem avisar."_

Esse é o pedido mais provável depois do piloto — dizer que ele é barato **antes**
de alguém pedir muda a conversa.

## Bloco 3 — Botão x texto digitado

**Prova:** id de botão é protocolo interno; palavra humana é atalho aceito.

Mesmo log do bloco 2, na sequência:

```
5511999990000> editar_descricao
bot [entregue]:
  Por favor, use os botões para confirmar, editar ou cancelar.
5511999990000> sim
bot [entregue]:
  Chamado #18 aberto com sucesso! Em breve alguém da equipe vai te atender.
```

**Fala:** _"`editar_descricao` é nome interno; digitado, não vale nada. Já 'sim',
'confirmar' e 'editar' valem digitados — porque botão interativo não renderiza em
todo aparelho, e sem esse atalho o usuário ficaria preso na última etapa."_

## Bloco 4 — Limites e resposta curta

**Prova:** limite de campo com orientação, não erro.

Terminal 4, em modo tiro único, com a sessão na etapa de **resumo** (log real,
`B4-limites.log`):

```powershell
npm run dev:simular -- texto "a"
npm run dev:simular -- texto ("x" * 250)
```

```
bot [entregue]:
  Por favor, envie uma resposta um pouco mais detalhada.

bot [entregue]:
  Ficou um pouco longo (250 caracteres). Por favor, envie *Resumo* com até 200 caracteres.
```

Os limites são nome 120, resumo 200, descrição 2000. A mensagem nomeia o campo da
etapa atual, então a saída muda se você rodar isso em outra etapa.

**Fala:** _"Ele diz quantos caracteres veio e qual é o limite. O usuário conserta
sozinho, sem abrir chamado sobre o bot de chamado."_

## Bloco 5 — Cancelar sem falso positivo

**Prova:** comando só vale quando é a **mensagem inteira** (log real,
`B5-B6-cancelar-midia.log`).

```
5511999990000> preciso cancelar meu pedido no site
bot [entregue]:
  Confirma a abertura do chamado?

  *Nome:* Natan Ferreira
  *Resumo:* Impressora sem papel na loja 12
  *Descrição:* preciso cancelar meu pedido no site
  [ Confirmar ] [ Editar ] [ Cancelar ]
  (responda com: /botao confirmar | /botao editar | /botao cancelar)
```

A frase virou descrição, como devia. Agora o comando de verdade:

```
5511999990000> cancelar
bot [entregue]:
  Tudo bem, cancelei essa abertura de chamado. Quando quiser tentar de novo, é só me mandar uma mensagem.
5511999990000> cancelar
bot [entregue]:
  Não tem nenhuma abertura de chamado em andamento agora. Quando precisar de ajuda, é só me mandar uma mensagem.
```

**Fala:** _"Duas coisas aqui. A frase com a palavra 'cancelar' no meio foi tratada
como texto — cliente de varejo escreve exatamente assim. E o segundo 'cancelar'
não mentiu dizendo que cancelou algo: não havia nada em andamento."_

## Bloco 6 — Áudio e imagem

**Prova:** formato não suportado não avança o fluxo nem vira valor de campo.

```
5511999990000> /audio
bot [entregue]:
  Por enquanto só consigo ler mensagens de texto — ainda não consigo ouvir áudio nem abrir anexos. Pode escrever, por favor?

  Entendido. Pode descrever o problema com mais detalhes?
```

**Fala:** _"Explica a limitação e repete a pergunta em que a pessoa estava. A
ocorrência fica no histórico da conversa, então vamos saber quantas pessoas
tentaram mandar áudio — é o dado que decide se vale construir transcrição
depois."_ (Fora do escopo da v1; ver [[WA Pendências]].)

## Bloco 7 — Entrega duplicada

**Prova:** webhook é entregue "pelo menos uma vez"; o sistema descarta a repetição.

Dentro da conversa, `/repetir` reenvia a última mensagem com o **mesmo id**
(log real, `B7-duplicada.log`, em telefone descartável):

```
5511900000077> A impressora da loja 12 não puxa papel
bot [entregue]:
  Obrigado! Agora resuma seu problema em uma frase curta.
5511900000077> /repetir
bot: (nenhuma resposta — descartada pelo limite por telefone, ou entrega repetida)
5511900000077> /estado

--- estado ------------------------------------------
sessão: etapa=resumo editando=false
        nome="A impressora da loja 12 não puxa papel" resumo=null
        descricao=null
saídas pendentes no outbox: 0
-----------------------------------------------------
```

A etapa **não** avançou. Cenário pronto, se preferir uma tela limpa:

```powershell
npm run dev:simular -- duplicada
```

```
Primeira entrega:
bot [entregue]:
  Entendido. Pode descrever o problema com mais detalhes?

Segunda entrega (mesmo wamid) — não deve avançar o fluxo nem responder de novo:
bot: (nenhuma resposta — descartada pelo limite por telefone, ou entrega repetida)
```

**Fala:** _"Isso não é hipótese: o webhook é reentregue por design, sempre que não chega
o 200 rápido. Sem o índice único no id da mensagem, cada reentrega avançaria uma
etapa — o usuário responderia o nome e receberia a confirmação de um chamado que
ele nunca descreveu."_

## Bloco 8 — Graph fora do ar

**Prova:** a resposta é gravada antes de ser enviada, fica pendente e sai sozinha.

> [!warning] A reentrega leva ~1 minuto, não "poucos segundos"
> O README diz que com `VARREDOR_INTERVALO_SEGUNDOS=15` a mensagem sai em poucos
> segundos. Não sai, e o motivo não é o varredor: a espera é
> `30s × 2^tentativas`, e a falha dentro da requisição **já gasta a primeira
> tentativa** — então a linha só fica elegível 60s depois, e o varredor a pega na
> primeira passada seguinte. No ensaio: falha às **13:40:13**, entrega às
> **13:41:27** — **74 segundos**. Planeje a fala para cobrir esse minuto (é onde
> entra a explicação do outbox), ou dispare o bloco 8 antes do 9 e volte para ele.

Terminal 4 — derrube a "Evolution" pelas 3 tentativas imediatas:

```powershell
curl.exe -s -X POST http://127.0.0.1:4000/_controle -H "content-type: application/json" -d '{\"status\":503,\"vezes\":3}'
```

```
{"ok":true,"controle":{"status":503,"vezes":3}}
```

Terminal 1 confirma: `>> Vou responder 503 nas próximas 3 chamada(s).`

Terminal 3 — mande qualquer mensagem (log real, `B8-outbox.log`):

```
5511999990000> Bom dia
bot [PENDENTE no outbox]:
  Obrigado! Agora resuma seu problema em uma frase curta.
5511999990000> /estado
...
saídas pendentes no outbox: 1
```

Terminal 1 mostra as três recusas propositais:

```
-- RECUSADO de propósito (503), restam 2
   para 5511999990000 | texto
     Obrigado! Agora resuma seu problema em uma frase curta.

-- RECUSADO de propósito (503), restam 1
   para 5511999990000 | texto
     Obrigado! Agora resuma seu problema em uma frase curta.

-- RECUSADO de propósito (último), restam 0
   para 5511999990000 | texto
     Obrigado! Agora resuma seu problema em uma frase curta.
```

Terminal 2, uma linha só, com o telefone fora e o erro reduzido:

```json
{"level":40,"mensagemId":240,"status":503,"permanente":false,"erro":"{\"error\":{\"message\":\"Falha simulada pela Graph de mentira\",\"code\":500}}","msg":"Envio pendente"}
```

Cerca de um minuto depois, sem ninguém fazer nada, a mensagem sai:

```
<< #36 2026-08-20T13:41:27.730Z
   para 5511999990000 | texto
     Obrigado! Agora resuma seu problema em uma frase curta.
```

E o `/estado` volta a `saídas pendentes no outbox: 0`. Como o controle da Graph de
mentira zera depois das 3 recusas, não precisa desligar nada — mas confira com
`curl.exe http://127.0.0.1:4000/_estado` antes do bloco 10.

**Fala:** _"A pergunta do bot foi gravada no banco na mesma transação que mudou o
estado da conversa, e só depois enviada. Com a Evolution fora, o usuário recebe a
pergunta atrasada — nunca silêncio com o estado já avançado. A espera entre
tentativas cresce (30s, 1min, 2min, 4min...), e o teto padrão de 6 tentativas
sobrevive a mais de meia hora de Evolution fora do ar. Se ainda assim desistir, um
alerta vai para o canal da equipe — sem telefone e sem o texto do chamado."_

O alerta é o item 6 de [[WA Lançamento]]: código pronto, falta criar o webhook.
Diga isso em vez de deixar parecer que já está no ar. Ver [[WA Outbox e entrega]].

## Bloco 9 — Assinatura e lote

**Prova:** payload forjado é recusado antes da lógica; lote inteiro é processado.
(Log real, `B9-assinatura-lote.log`.)

```powershell
npm run dev:simular -- assinatura
```

```
sem assinatura        -> 401   (esperado 401)
assinatura de outro   -> 401   (esperado 401)
assinatura correta    -> 200   (esperado 200)
```

```powershell
npm run dev:simular -- lote
```

```
Enviando 3 mensagens de 3 telefones diferentes em UM webhook...
webhook respondeu 200
linhas criadas em Mensagem: 6 (esperado 6: 3 entradas + 3 respostas)
```

No terminal 1, as três respostas do lote saem em 30 milissegundos, para três
telefones diferentes:

```
<< #27 2026-08-20T13:38:33.323Z
   para 5511999990001 | texto
     Obrigado! Agora resuma seu problema em uma frase curta.

<< #28 2026-08-20T13:38:33.339Z
   para 5511999990002 | texto
     ...
<< #29 2026-08-20T13:38:33.355Z
   para 5511999990003 | texto
     ...
```

**Fala:** _"Sem autenticação nenhuma no webhook, qualquer um que descobrisse a
URL poderia abrir chamado falso e — pior — fazer o bot mandar mensagem para
qualquer número, o que termina com o número da empresa banido."_

Vale dizer que o simulador **não** contorna a autenticação: ele entra pelo
`/webhook/<segredo>` normal, com o segredo do `.env`. `npm run dev:simular -- segredo`
mostra as três respostas lado a lado — sem segredo 404, errado 404, certo 200.

> [!note] Este bloco mudou de assunto em 17/09
> Com a Meta, o que se demonstrava era **assinatura HMAC**: o corpo era assinado,
> e adulterar um byte derrubava a requisição. A Evolution não assina corpo — o
> que ela permite configurar é a URL. Então hoje o segredo vai no **caminho**.
>
> Se alguém da plateia perguntar o que se perdeu, a resposta honesta é: o HMAC
> provava **duas** coisas (quem chamou **e** que o corpo chegou intacto); o
> segredo no caminho prova só a primeira. O que cobre a segunda agora é o TLS —
> e por isso o webhook **tem** de ser HTTPS.

## Bloco 10 — O painel de chamados

**Prova:** as três rotas que o atendimento usa, e a notificação chegando.

> ![[painel-quadro.jpg]]
> Cada coluna é uma `situacao`; arrastar um cartão dispara a mudança (e, se
> marcado, o WhatsApp para o solicitante). Abrir um cartão mostra a
> classificação completa e os comentários internos:
> ![[painel-chamado-detalhe.jpg]]

Terminal 4 — leia o token do `.env` em vez de digitá-lo na tela:

```powershell
$tk = ((Get-Content .env | Select-String '^PAINEL_TOKEN=') -split '=',2)[1]
curl.exe -s -H "authorization: Bearer $tk" http://127.0.0.1:3000/internal/chamados | ConvertFrom-Json | Select-Object -ExpandProperty chamados | Format-Table id,situacao,nome,resumo -AutoSize
```

Saída real do ensaio:

```
id situacao     nome                      resumo
-- --------     ----                      ------
18 aberto       Natan Ferreira            A impressora da loja 12 travou de novo
17 aberto       Bom dia, preciso de ajuda Natan Ferreira
 4 aberto       Maria Silva               Impressora nao imprime
 1 em_andamento Natan Ferreira            Sistema de estoque fora do ar
```

> [!tip] Limpe o banco antes de mostrar esta tela
> O chamado #17 é o do aviso no topo desta nota — nome e resumo trocados porque a
> conversa começou com "Bom dia". Numa apresentação isso é a pior tela possível.
> Apague os chamados de ensaio antes (`npm run retencao -- --esquecer <telefone>
> --confirmar`) ou filtre por situação.

Mova o chamado, avisando o usuário — repare nas **aspas simples** no corpo:

```powershell
curl.exe -s -X PATCH http://127.0.0.1:3000/internal/chamados/18/situacao -H "authorization: Bearer $tk" -H "content-type: application/json" -d '{\"situacao\":\"resolvido\",\"notificarUsuario\":true,\"autor\":\"Ana\"}'
```

```json
{ "id": 18, "situacao": "resolvido", "anterior": "aberto", "notificado": true }
```

**Vire para o terminal 1**: a mensagem para o usuário já está lá.

```
<< #30 2026-08-20T13:39:24.095Z
   para 5511999990000 | texto
     Seu chamado #18 foi marcado como resolvido. Se o problema continuar, é só mandar uma mensagem que abrimos outro.
```

E a auditoria:

```powershell
curl.exe -s -H "authorization: Bearer $tk" http://127.0.0.1:3000/internal/chamados/18/historico
```

```json
{
  "chamadoId": 18,
  "mudancas": [
    { "de": "aberto", "para": "resolvido", "criadoEm": "2026-08-20T13:39:24.079Z", "autor": "Ana" }
  ]
}
```

O terminal 2 registra a mudança com autor, e sem telefone:

```json
{"level":30,"reqId":"req-1g","chamadoId":18,"de":"aberto","para":"resolvido","autor":"Ana","msg":"Situação do chamado alterada"}
```

**Fala:** _"Três coisas de propósito aqui. O bot **nunca** muda a situação
sozinho — isso é decisão de gente. Avisar o usuário é opcional e desligado por
padrão, porque manda mensagem para uma pessoa real. E nenhuma dessas rotas devolve
telefone: o painel roda no navegador de quem atende e não precisa dele."_

Se `autor` vier `null` em linhas antigas, explique: o servidor registra quem mudou
quando o painel manda o nome — hoje ele ainda não manda. É ajuste no painel, não
aqui. Ver [[WA Painel de chamados]].

## Bloco 11 — Quando o painel erra

**Prova:** 401 sem pista, 400 útil, 404 honesto. Todas as saídas abaixo são do
ensaio.

```powershell
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:3000/internal/chamados
curl.exe -s -X PATCH http://127.0.0.1:3000/internal/chamados/18/situacao -H "authorization: Bearer $tk" -H "content-type: application/json" -d '{\"situacao\":\"em_espera\"}'
curl.exe -s -X PATCH http://127.0.0.1:3000/internal/chamados/999999/situacao -H "authorization: Bearer $tk" -H "content-type: application/json" -d '{\"situacao\":\"resolvido\"}'
curl.exe -s -H "authorization: Bearer $tk" http://127.0.0.1:3000/internal/chamados/999999/historico
```

```
401
{"erro":"requisição inválida","detalhes":[{"campo":"situacao","problema":"must be equal to one of the allowed values","aceitos":["aberto","em_andamento","resolvido","cancelado"]}]}
{"erro":"chamado não encontrado"}
{"erro":"chamado não encontrado"}
```

Se quiser mostrar o corpo malformado (é o que acontece ao copiar o comando do
README no PowerShell), o servidor responde `{"erro":"JSON inválido"}` — 400 do
parser de conteúdo, antes de qualquer rota.

**Fala:** _"Sem token, 401 seco — não contamos ao atacante o que faltou. Com token,
o erro de validação devolve a lista de situações aceitas, porque aí quem está do
outro lado é quem integra o painel. E id inexistente é 404, não lista vazia: 'não
achei' e 'achei e está vazio' são respostas diferentes."_

## Bloco 12 — LGPD

**Prova:** o mecanismo de descarte existe, roda em simulação por padrão, e o
direito à eliminação funciona. (Log real, `B12b-retencao.log`.)

```powershell
npm run retencao
```

```
[SIMULAÇÃO] Seriam apagados 0 mensagem(ns), 0 chamado(s) e 0 sessão(ões) abandonada(s).
  corte de mensagens: (desligado)
  corte de chamados:  (desligado)
  corte de sessões:   2026-08-20T12:41:00.322Z
Atenção: RETENCAO_MENSAGENS_DIAS e RETENCAO_CHAMADOS_DIAS não estão definidos,
então mensagens e chamados NÃO são apagados. Esse prazo é uma decisão do
negócio; o script não assume nenhum valor. (Sessões abandonadas saem de todo
jeito: o prazo delas é o SESSAO_TTL_HORAS.)
Rode de novo com --confirmar para apagar.
```

> [!important] Esse aviso é o pedido de decisão da apresentação
> Não esconda: **o prazo de retenção não está definido**, e é o item 1 de
> [[WA Lançamento]] — decisão de 15 minutos que bloqueia qualquer uso com dado
> real. Ler o aviso em voz alta é a forma mais barata de sair da reunião com a
> resposta.

Feche apagando os dados da própria demonstração — é o encerramento mais forte que
este projeto tem:

```powershell
npm run retencao -- --esquecer 5511900000042
npm run retencao -- --esquecer 5511900000042 --confirmar
```

```
[SIMULAÇÃO] Seriam apagados: 1 chamado(s), 8 mensagem(ns), 0 sessão(ões). Rode de novo com --confirmar.
Apagado do titular ***0042: 1 chamado(s), 8 mensagem(ns), 0 sessão(ões).
```

Repare que a própria saída **mascara o telefone** (`***0042`) — é o mesmo
tratamento que os logs recebem, e vale apontar sem precisar de outro bloco.

**Fala:** _"Acabei de exercer o direito à eliminação sobre o titular desta
demonstração. Simula primeiro, apaga depois — e apaga em lotes, para não travar o
banco. As sessões abandonadas são a exceção que sai sempre: elas guardam nome e
texto livre de conversa que ninguém terminou, e ali não há decisão de negócio a
tomar."_ Ver [[WA Segurança e LGPD]].

## Bloco 13 — O que sustenta tudo isso

**Prova:** as garantias que só o banco de verdade prova, e as duas suítes.

```powershell
curl.exe -s http://127.0.0.1:3000/health
curl.exe -s http://127.0.0.1:3000/ready
npm test
npm run dev:verificar-banco
```

```
{"status":"ok"}
{"status":"ok"}
```

`npm test` no ensaio: **135 testes, 0 falhas, 7,8 s** (`B13-testes.log`).

```
ℹ tests 135
ℹ pass 135
ℹ fail 0
ℹ duration_ms 7822.4782
```

E as checagens contra o banco de verdade (`B13-verificar-banco.log`), todas `OK`:

```
0) fuso da sessão: datas gravadas em UTC, não na hora local
  OK   a sessão do Postgres está em UTC — TimeZone=UTC
  OK   a data gravada bate com o now() do banco (sem deslocamento de fuso) — diferença=0s
1) advisory lock: duas mensagens simultâneas do mesmo telefone
  OK   o fluxo avançou DUAS etapas (nenhuma mensagem se perdeu) — etapa=descricao
2) índice único: a Meta reentrega o mesmo wamid
  OK   a entrada repetida NÃO foi gravada duas vezes — entradas: 1
3) SELECT ... FOR UPDATE: dois PATCH simultâneos no mesmo chamado
  OK   o usuário foi notificado UMA vez só — notificações: 1
4) reserva da outbox: FOR UPDATE SKIP LOCKED + espera crescente
  OK   espera de 60s ainda não vencida: NÃO reservada — tentativas=1
  OK   espera de 60s vencida: reservada — tentativas=2
5) recuperação: Graph fora -> pendente -> varredor entrega
  OK   o varredor entregou o pendente — entregues=1
6) histórico de situação: gravação e ON DELETE CASCADE
  OK   apagar o chamado levou o histórico junto — sobraram: 0

Tudo certo: as garantias de banco se comportaram como o esperado.
```

> [!note] Este log é de 20/08, quando o banco era Postgres
> Hoje são **29** checagens e três títulos mudaram junto com o banco: a 0 confere
> o **formato** da data gravada em vez do fuso da sessão; a 1 se chama
> "serialização" em vez de "advisory lock"; a 3 e a 4 perderam o `FOR UPDATE` e o
> `SKIP LOCKED` do nome. O que cada uma **prova** é o mesmo, e é esse o ponto de
> mostrá-las. Ver [[WA Banco de dados]].

Repare na checagem 4: é ela que documenta a espera de 60s do bloco 8 — o mesmo
número, medido de dois jeitos.

**Fala:** _"`/health` responde sem tocar o banco: a pergunta é 'o processo está
vivo?'. `/ready` faz um SELECT 1, para o balanceador tirar a instância de rotação
em vez de mandar tráfego para um processo que vai falhar em toda mensagem. E essas
checagens de banco rodam no CI, contra um banco de verdade — foi assim que
apareceu um bug de fuso que deixava o reenvio parado por três horas."_
Ver [[WA Testes e verificação]] e [[WA Fuso horário sem timezone]].

## Bloco 14 — Limite por telefone

**Prova:** flood de um telefone é cortado, **em silêncio**, sem afetar os outros.

Este bloco entrou no roteiro porque aconteceu sozinho no ensaio: rodando vários
blocos seguidos no mesmo telefone, a 21ª mensagem do minuto sumiu.

```
5511999990000> cancelar
bot: (nenhuma resposta — descartada pelo limite por telefone, ou entrega repetida)
```

E o `/estado` prova que a mensagem não foi processada — a sessão continua onde
estava, com o `cancelar` sem efeito:

```
--- estado ------------------------------------------
sessão: etapa=descricao editando=false
        nome="Natan Ferreira" resumo="Impressora sem papel na loja 12"
        descricao=null
```

Para provocar de propósito, mande 21 mensagens no mesmo minuto:

```powershell
1..21 | ForEach-Object { npm run dev:simular -- texto "mensagem $_" | Select-String 'bot' }
```

**Fala:** _"São 20 mensagens por minuto por telefone. Quem estoura é descartado em
silêncio, de propósito: responder 'você está enviando rápido demais' a quem faz
flood só gera mais tráfego de saída. O limite de um telefone não afeta os outros —
e a reentrega do webhook devolve a cota, para uma rajada de duplicatas não consumir o
limite de quem está escrevendo de verdade."_

Vale a ressalva honesta: esse contador vive **na memória do processo**, então com
duas instâncias o limite efetivo vira 2×. É o item 7 de [[WA Lançamento]].

## Bloco extra — Sessão expirada (se perguntarem)

O TTL padrão é 24h, então não dá para esperar ao vivo. Em vez de mexer no `.env` e
reiniciar o servidor, envelheça a sessão no banco (terminal 4):

```powershell
sqlite3 dados\whatsapp-suporte.db "UPDATE \"SessaoConversa\" SET \"atualizadoEm\" = datetime('now', '-25 hours') WHERE telefone = '5511999990000'"
```

O `sqlite3` não imprime nada quando dá certo. Para conferir:

```powershell
sqlite3 dados\whatsapp-suporte.db "SELECT telefone, \"atualizadoEm\" FROM \"SessaoConversa\""
```

> [!note] Aqui `datetime('now', ...)` é seguro; no código, não seria
> A comparação que decide a expiração é feita **pelo Prisma**, com a data indo
> como parâmetro — então basta que o valor gravado esteja no passado. Em SQL crua
> comparando duas datas, `datetime('now')` é justamente o que **não** se pode
> usar: ver [[WA Banco de dados#Convenção de datas]].

Mande qualquer mensagem no terminal 3:

```
5511999990000> oi
bot [entregue]:
  Faz um tempo que a gente parou, então vou começar de novo.

  Olá! Para abrir seu chamado, qual é o seu nome?
```

E note que **é aqui que a saudação aparece** — o único caminho em que ela é enviada
hoje (ver o aviso no topo).

## Se algo der errado ao vivo

| Sintoma na tela                                | Causa provável                             | Saída em 10 segundos                                        |
| ---------------------------------------------- | ------------------------------------------ | ----------------------------------------------------------- |
| `O servidor não respondeu em .../health`       | terminal 2 caiu                            | `npm run dev` e siga                                        |
| `bot [PENDENTE no outbox]` sem você ter pedido | Graph de mentira em modo falha             | `{\"status\":0}` no `/_controle`                            |
| `bot: (nenhuma resposta ...)` inesperado       | limite por telefone ou duplicata           | espere o minuto virar, ou troque de telefone (`TELEFONE=`)  |
| conversa em etapa errada                       | sessão de ensaio anterior                  | `cancelar` e recomece                                       |
| `{"erro":"JSON inválido"}`                     | aspas do corpo comidas pelo PowerShell     | use `-d '{\"campo\":\"valor\"}'`                            |
| `Não consegui falar com o banco`               | falta `prisma:deploy`, ou o arquivo sem permissão | pule para o bloco 9 (só precisa do servidor)         |
| `Server has closed the connection`             | conexão caiu num processo de vida curta     | rode o mesmo comando de novo — no ensaio aconteceu uma vez e o `/ready` continuou `ok` |
| `EADDRINUSE ... 127.0.0.1:4000`                | duas Graphs de mentira                     | mate a antiga (pré-voo, item 8)                             |
| `curl` reclamando de `-X`                      | alias do PowerShell                        | use `curl.exe`                                              |

Regra de ouro: **um bloco que falha não trava a apresentação**. Diga o que era
esperado, siga para o próximo e volte no fim. A única exceção é o bloco 1 — sem
ele, nada do resto tem contexto.

## Perguntas que sempre aparecem

| Pergunta                                     | Resposta curta                                                                                                                                                    |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "Tem IA? Quanto custa por mensagem?"         | Nenhuma IA no caminho. Custo por token: zero. E desde 17/09 não há mais cobrança por conversa: saímos da API paga da Meta para a Evolution, que é software que hospedamos. O custo virou o servidor, não a mensagem. |
| "E se a Evolution cair?"                     | Bloco 8. A resposta fica pendente e sai sozinha (~1 min na primeira tentativa); se desistir, alerta para a equipe. Vale dizer o risco novo: a sessão é do WhatsApp Web e pode desconectar — aí o envio é aceito e nada é entregue, por isso monitoramos o estado da conexão. |
| "Quantos usuários aguenta?"                  | Uma instância hoje. Os limites foram raciocinados, não medidos — é o que o piloto fechado vai dizer. Segunda instância exige Redis (item 7 de [[WA Lançamento]]).  |
| "Guarda dado pessoal por quanto tempo?"      | O mecanismo está pronto; **o prazo é decisão de vocês**. Bloco 12.                                                                                                 |
| "Dá para adicionar campo (setor, urgência)?" | Sim, e o menu de correção acompanha sozinho. Bloco 2.                                                                                                             |
| "Quem pode mudar a situação de um chamado?"  | Só quem tem token, e fica registrado no histórico. Bloco 10.                                                                                                      |
| "E se a pessoa mandar 'oi' primeiro?"        | Recebe a pergunta do nome e a conversa segue normal. Era um bug até 20/08 — o "oi" virava o nome —, encontrado neste ensaio e corrigido com teste.                  |
| "Quando entra no ar?"                        | Marcos e premissas em [[WA Lançamento]]. A fila da Meta saiu do caminho crítico em 17/09, junto com a Meta: não há mais verificação de negócio nem espera externa. O que falta é conectar a instância e validar. |

## Log da execução

Ensaio de **20/08/2026, 13:35–13:46 UTC**, nesta máquina: Node 24.18.0,
Postgres 18 local (o banco de então; hoje é SQLite), Graph de mentira em
`127.0.0.1:4000`, servidor em `:3000`.
Logs crus em [`ensaio-2026-08-20/`](ensaio-2026-08-20/).

| Bloco | Arquivo                        | Resultado                                                     |
| ----- | ------------------------------ | ------------------------------------------------------------- |
| 1     | `B1-conversa-pos-fix.log`      | ✅ **depois da correção**: "bom dia" → saudação → chamado #27   |
| 1     | `B1-conversa-limpa.log`        | ✅ antes da correção, começando pelo nome: chamado #22          |
| 1 (1ª tentativa) | `B1-conversa.log`   | ⚠️ expôs o bug: #17 com nome/resumo trocados                   |
| 2 · 3 | `B2-B3-edicao.log`             | ✅ menu de 3 botões, edição volta à confirmação, "sim" confirma |
| 4     | `B4-limites.log`               | ✅ curta demais e 250 > 200 caracteres                         |
| 5 · 6 | `B5-B6-cancelar-midia.log`     | ✅ frase com "cancelar" virou descrição; áudio repete pergunta  |
| 7     | `B7-duplicada.log`             | ✅ `/repetir` e cenário `duplicada` sem avançar etapa           |
| 8     | `B8-outbox.log` + `B8-server-log.txt` | ✅ pendente → entregue sozinho em **74 s**              |
| 9     | `B9-assinatura-lote.log`       | ✅ 401/401/200 e 6 linhas no lote                              |
| 10·11 | (saídas nesta nota)            | ✅ listar, PATCH+notificar, histórico, 401/400/404             |
| 12    | `B12a-titular.log`, `B12b-retencao.log` | ✅ simulação, e eliminação real de 1 chamado + 8 mensagens |
| 13    | `B13-testes.log`, `B13-verificar-banco.log` | ✅ 135 testes e 28 checagens de banco, 0 falhas |
| 13    | `B13-verificar-banco-pos-fix.log` | ✅ as mesmas 28 checagens depois da correção (1, 2 e 5 ganharam aquecimento) |
| 14    | `B-throttle-estado.log`        | ✅ 21ª mensagem do minuto descartada em silêncio                |
| extra | `Bextra-expira.log`            | ✅ sessão envelhecida por SQL reinicia a conversa               |
| —     | `T1-graph.log`, `T2-server.log` | os dois terminais inteiros (45 entregas, 12 recusas)          |

Limpeza feita no fim (`B-limpeza.log`): titulares descartáveis apagados, sessão do
telefone da demo encerrada. Ficaram no banco os chamados #17, #18, #22 e #27 — o
#17 é o que **não** deve aparecer numa tela de apresentação (é o do bug, de antes
da correção).

Depois do ensaio, com a correção aplicada: **137 testes** (dois novos, de primeiro
contato) e as **28 checagens de banco** passando.

Para capturar de novo:

```powershell
npm run dev:simular -- assinatura | Tee-Object -FilePath docs/ensaio-AAAA-MM-DD/B9.log
npm run dev:verificar-banco       | Tee-Object -FilePath docs/ensaio-AAAA-MM-DD/B13.log
npm test                          | Tee-Object -FilePath docs/ensaio-AAAA-MM-DD/testes.log
```

A conversa interativa não dá para canalizar com `Tee-Object` (ela lê do teclado),
mas dá para **alimentá-la** por _here-string_ — foi assim que o ensaio rodou os
blocos de conversa. Repare no **`npm.cmd`**: com `npm`, o wrapper `npm.ps1`
transforma a saída de erro em `NativeCommandError` e enche a tela de ruído.

```powershell
@"
Natan Ferreira
A impressora da loja 12 não puxa papel
Desde ontem ela apita tres vezes e cancela o trabalho.
/estado
/botao confirmar
/sair
"@ | npm.cmd run dev:simular
```

O `"@` de fechamento tem de estar na coluna 0. Serve para ensaiar e para gravar o
log; **não** use na apresentação — sem eco do que foi digitado, a plateia vê só as
respostas do bot.

## Cobertura: funcionalidade → bloco

Conferência final, para nenhuma funcionalidade de [[WA Lançamento]] ficar de fora
sem ser por escolha.

| Funcionalidade                                           | Bloco                                        |
| -------------------------------------------------------- | -------------------------------------------- |
| Fluxo guiado em 5 etapas (assunto + 3 campos + confirmação) | 1 ✅                                       |
| Confirmação com botões                                   | 1 ✅                                          |
| Corrigir antes de enviar (menu adaptativo)               | 2 ✅                                          |
| Botão x texto digitado                                   | 3 ✅                                          |
| Limites com aviso amigável                               | 4 ✅                                          |
| Cancelar quando quiser                                   | 5 ✅                                          |
| Áudio, imagem e anexo                                    | 6 ✅                                          |
| Retomada de sessão (24h)                                 | extra ✅                                      |
| Entrega duplicada descartada                             | 7 ✅                                          |
| Outbox: pendente e reentrega com espera crescente        | 8 ✅                                          |
| `GET /internal/chamados`                                 | 10 ✅                                         |
| `PATCH .../situacao` + notificação                       | 10 ✅                                         |
| `GET .../historico`                                      | 10 ✅                                         |
| Assinatura do webhook                                    | 9 ✅                                          |
| Lote de mensagens num webhook só                         | 9 ✅                                          |
| Validação de rota, 401 e 404                             | 11 ✅                                         |
| Retenção configurável e simulação                        | 12 ✅                                         |
| Direito à eliminação                                     | 12 ✅                                         |
| Telefone mascarado (saída e log)                         | 12 ✅ (`***0042`)                             |
| `/health` e `/ready`                                     | 13 ✅                                         |
| Serialização de transações, índice único, formato da data | 13 ✅                                         |
| Limite por telefone                                      | 14 ✅                                         |
| Limpeza de sessões abandonadas                            | 12 (o corte aparece; nada expirado no ensaio) |
| Dois tokens (painel x interno) e CORS                    | 10 (o `PAINEL_TOKEN` foi o usado)            |
| Alerta ao desistir de uma mensagem                       | — falta criar o webhook (item 6)             |
| Aviso de indisponibilidade ao usuário                    | — exige tornar o banco inacessível; só falado |
| View `chamados_para_cards`                               | — só falado; ver [[WA Painel de chamados]]   |

Os três "—" são deliberados: um depende de item de operação em aberto, os outros
exigem derrubar dependência ou abrir o banco na frente da plateia, e o custo de
tela não paga o que provam.
