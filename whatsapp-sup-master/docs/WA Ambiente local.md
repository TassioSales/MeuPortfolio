---
tags: [projeto/whatsapp-suporte, ambiente, desenvolvimento]
projeto: whatsapp-suporte
atualizado: 2026-09-17
---

# WA Ambiente local

Volta para [[WhatsApp Suporte]] · o que os testes cobrem: [[WA Testes e verificação]].

Dá para exercitar a conversa inteira — **banco de verdade, advisory lock de
verdade, outbox de verdade** — sem instância da Evolution conectada e sem número
de WhatsApp. Só as duas pontas da integração são substituídas.

| ponta | de verdade | no teste local |
| --- | --- | --- |
| entra | `POST` da Evolution em `/webhook/<segredo>` | `npm run dev:simular`, que monta o mesmo envelope `messages.upsert` |
| sai | `{EVOLUTION_URL}/message/sendText/{instancia}` | `npm run dev:evolution` (com `EVOLUTION_URL` apontando para ela) |

> [!important] Isso não enfraquece o que está sendo testado
> O simulador entra pelo `/webhook/<segredo>` normal e passa pela **mesma
> autenticação**: segredo errado continua levando 404. O que é falso é o
> remetente, não o caminho.

## Três terminais

```bash
npm run dev:evolution  # 1) Evolution de mentira (porta 4000): mostra o que o bot enviaria
npm run dev            # 2) o servidor (porta 3000)
npm run dev:simular    # 3) conversa interativa
```

No terminal 3 você digita como se fosse o usuário. As respostas aparecem ali
(lidas da tabela `Mensagem`, onde a saída é gravada **antes** de ser enviada) e
também no terminal 1, com o texto exatamente como sairia:

```
5511999990000> Natan
bot [entregue]:
  Obrigado! Agora resuma seu problema em uma frase curta.
```

`bot [PENDENTE no outbox]` no lugar de `[entregue]` significa que o envio falhou
e a linha está na fila do varredor — ver [[WA Outbox e entrega]].

## Comandos dentro da conversa

| comando | efeito |
| --- | --- |
| `/botao <id>` | clica um botão de verdade (`/botao confirmar`, `/botao editar_descricao`) |
| `/audio`, `/imagem` | manda formato não suportado |
| `/estado` | sessão + chamados + pendências da outbox |
| `/repetir` | reenvia a última mensagem com o **mesmo wamid** (entrega duplicada) |
| `/ajuda`, `/sair` | — |

Um comando que falha (banco fora, servidor caído) **não encerra a conversa**:
você corrige em outra janela e continua de onde estava. Cada comando também
pré-checa só o que precisa — `assinatura` exige servidor, `estado` exige banco —
com uma mensagem acionável em vez de um stack trace do Prisma.

## Cenários prontos

```bash
npm run dev:simular -- assinatura   # payload forjado recebe 401; assinado, 200
npm run dev:simular -- duplicada    # mesma mensagem 2x não avança o fluxo
npm run dev:simular -- lote         # 3 mensagens de 3 telefones em um webhook só
npm run dev:simular -- estado       # inspeciona sessão, chamados e outbox
npm run dev:simular -- texto "Meu problema"
npm run dev:simular -- botao confirmar
npm run dev:simular -- chat 5511999990000
```

Variáveis: `ALVO` (padrão `http://127.0.0.1:3000/webhook/<WEBHOOK_SEGREDO>`) e
`TELEFONE` (padrão `5511999990000`).

`npm run dev:simular -- segredo` confere as três respostas que importam: sem
segredo 404, segredo errado 404, segredo certo 200.

## Evolution de mentira

[src/dev/evolution-fake.ts](../src/dev/evolution-fake.ts), porta 4000
(`FAKE_PORT`). Serve `POST /message/sendText/<instancia>`, **exige o cabeçalho
`apikey`** (sem ele avisa que a Evolution de verdade recusaria com 401) e
responde 201 com um envelope no formato dela.

Ela também **recusa com 400 um corpo sem `number` ou `text`**, como a de verdade.
Isso não é zelo de dublê: enquanto ela aceitava qualquer coisa e respondia 201,
uma linha de outbox no formato antigo era marcada como ENTREGUE sem destinatário
nenhum. O dublê permissivo escondia o bug; o dublê exigente o revelou em
desenvolvimento. Ver [[WA Outbox e entrega#Payload antigo depois de trocar de provedor]].

Dois endpoints de controle:

```bash
# falhar de propósito nas próximas 5 chamadas (exercita a outbox)
curl -X POST http://127.0.0.1:4000/_controle -H "content-type: application/json" -d "{\"status\":503,\"vezes\":5}"

# voltar ao normal
curl -X POST http://127.0.0.1:4000/_controle -H "content-type: application/json" -d "{\"status\":0}"

# quantas mensagens ela recebeu
curl http://127.0.0.1:4000/_estado
```

Os `curl` são de uma linha de propósito, para funcionar igual no PowerShell e no
bash.

## Ver a recuperação da outbox acontecendo

O comportamento mais difícil de observar em produção:

1. `VARREDOR_INTERVALO_SEGUNDOS=15` no `.env` (senão são 60s de espera);
2. derrube a Evolution com `/_controle`;
3. mande uma mensagem — o simulador mostra `bot [PENDENTE no outbox]`;
4. devolva a Evolution com `{"status":0}`;
5. **não faça nada.** O varredor entrega sozinho quando a espera vence.

Foi assim que o [[WA Fuso horário sem timezone|bug de fuso]] apareceu: o passo 5
nunca acontecia.

## Garantias de banco

Com o servidor de pé:

```bash
npm run dev:verificar-banco
```

38 checagens contra o arquivo SQLite de verdade (e as mesmas rodam no CI). Detalhe em [[WA Testes e verificação]].

## Com a Evolution de verdade

```bash
npm run dev
ngrok http 3000
```

- **aponte** `EVOLUTION_URL` para a sua instalação (senão o bot continua postando
  na Evolution de mentira e nenhuma mensagem chega ao usuário — ver
  [[WA Configuração]]);
- no painel da Evolution, na instância → Webhook: URL =
  `https://SEU_DOMINIO_NGROK/webhook/SEU_WEBHOOK_SEGREDO`, evento
  `MESSAGES_UPSERT` marcado;
- com ngrok na frente, considere `TRUST_PROXY`.

> [!warning] Não existe handshake
> A Evolution não valida a URL ao salvar — ela simplesmente começa a postar. Um
> erro de digitação no segredo não dá erro na tela; dá silêncio. Confira com
> `npm run dev:simular -- segredo` ou `node diagnostico.mjs`.

## Banco local

Não há nada para instalar: o banco é um arquivo SQLite, criado pela migração.

```bash
npm run prisma:generate
npm run prisma:deploy    # cria dados/whatsapp-suporte.db e as tabelas
npm run dev:view         # a view de cards; migrate não gerencia view
```

O caminho vem do `DATABASE_URL` (padrão `file:./dados/whatsapp-suporte.db`) e é
resolvido contra a **raiz do projeto**, não contra o diretório onde você rodou o
comando. `dados/` está no `.gitignore`: o banco tem dado pessoal e não vai para o
repositório.

Para começar de novo, apague os três arquivos e migre outra vez:

```bash
rm -f dados/whatsapp-suporte.db dados/whatsapp-suporte.db-wal dados/whatsapp-suporte.db-shm
npm run prisma:deploy && npm run dev:view
```

Para olhar dentro: `sqlite3 dados/whatsapp-suporte.db`. Com o WAL ligado isso não
bloqueia o servidor. Ver [[WA Banco de dados]].

## Onde as coisas travam

| sintoma | causa provável |
| --- | --- |
| processo morre no boot listando variáveis | falta segredo no `.env` — é de propósito ([[WA Configuração]]) |
| simulador recebe 404 | `WEBHOOK_SEGREDO` diferente entre `.env` e o processo em execução — reinicie o servidor |
| resposta fica `PENDENTE` para sempre | Evolution de mentira fora, ou ainda em modo falha (`/_controle` com `vezes` alto) |
| `dev:verificar-banco` diz que o servidor não respondeu | falta `npm run dev` |
| nada chega no usuário em produção | `EVOLUTION_URL` sobrou apontando para `127.0.0.1:4000` |
| a Evolution de mentira avisa "POST sem o cabeçalho apikey" | `EVOLUTION_API_KEY` vazia no `.env` — em produção isso seria 401 |
| erro de banco no Prisma nos comandos do simulador | `DATABASE_URL` errada, ou a pasta do arquivo sem permissão de escrita |
| `The table ... does not exist` | falta `npm run prisma:deploy` — ou o `DATABASE_URL` aponta para outro arquivo |
| `SQLITE_BUSY` / "database is locked" | outro processo escrevendo: um `npm run dev` esquecido, um `sqlite3` aberto |
| `DATABASE_URL aponta para um servidor` | sobrou o valor `postgresql://...` de antes; troque por `file:./dados/whatsapp-suporte.db` |
