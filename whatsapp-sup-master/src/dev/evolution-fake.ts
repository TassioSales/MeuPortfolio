import http from 'node:http';

/**
 * Evolution API de mentira, só para desenvolvimento.
 *
 * Faz o papel do endpoint `/message/sendText/{instancia}`: aceita o POST do bot,
 * imprime a mensagem de um jeito legível e devolve uma resposta com a mesma
 * forma da real. Com `EVOLUTION_URL` apontando para cá, dá para rodar a conversa
 * inteira sem instância conectada e sem número de WhatsApp.
 *
 * Também sabe fingir falha (`POST /_controle`), que é como se exercita o outbox:
 * a resposta fica pendente, o varredor tenta de novo com espera crescente e a
 * mensagem sai quando a "Evolution" voltar.
 *
 * Não faz parte do build de produção (ver `exclude` no tsconfig.json).
 */

const PORTA = Number(process.env.FAKE_PORT ?? 4000);

/** Quando `status` > 0, as próximas `vezes` chamadas respondem esse status. */
let controle = { status: 0, vezes: 0 };
let entregues = 0;

function lerCorpo(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let dados = '';
    req.on('data', (p) => (dados += p));
    req.on('end', () => resolve(dados));
    req.on('error', reject);
  });
}

function responder(res: http.ServerResponse, status: number, corpo: unknown): void {
  const texto = JSON.stringify(corpo);
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(texto);
}

/**
 * Traduz o payload da Evolution para algo que se lê no terminal.
 *
 * O corpo tem dois campos e nada mais: `number` e `text`. Não há mais o ramo de
 * mensagem interativa que existia aqui — com a Evolution, menu é texto numerado,
 * e chega como texto comum.
 */
function descrever(corpo: any): string[] {
  const linhas: string[] = [];
  const para = corpo?.number ?? '(sem destinatário)';

  if (typeof corpo?.text === 'string') {
    linhas.push(`para ${para} | texto`);
    for (const l of corpo.text.split('\n')) linhas.push(`  ${l}`);
    return linhas;
  }

  linhas.push(`para ${para} | corpo inesperado`);
  linhas.push(`  ${JSON.stringify(corpo)}`);
  return linhas;
}

const servidor = http.createServer(async (req, res) => {
  const url = req.url ?? '/';

  // Liga e desliga a simulação de falha sem reiniciar o processo.
  if (req.method === 'POST' && url === '/_controle') {
    try {
      const pedido = JSON.parse((await lerCorpo(req)) || '{}');
      controle = { status: Number(pedido.status ?? 0), vezes: Number(pedido.vezes ?? 1) };
      console.log(
        controle.status > 0
          ? `\n>> Vou responder ${controle.status} nas próximas ${controle.vezes} chamada(s).\n`
          : '\n>> Voltei a aceitar tudo normalmente.\n'
      );
      return responder(res, 200, { ok: true, controle });
    } catch {
      return responder(res, 400, { erro: 'JSON inválido' });
    }
  }

  if (req.method === 'GET' && url === '/_estado') {
    return responder(res, 200, { entregues, controle });
  }

  // A Evolution envia por `/message/sendText/{instancia}`. Qualquer instância
  // serve aqui — o que importa é a FORMA da rota.
  if (req.method !== 'POST' || !url.includes('/message/sendText/')) {
    return responder(res, 404, {
      status: 404,
      error: 'Not Found',
      message: 'Rota inexistente nesta Evolution de mentira',
    });
  }

  const bruto = await lerCorpo(req);

  // A Evolution autentica por `apikey`, e não por `Authorization: Bearer`. O
  // valor não é conferido (qualquer chave serve aqui), mas a AUSÊNCIA é bug de
  // verdade — e é o erro mais provável de quem acabou de migrar.
  if (!String(req.headers.apikey ?? '').trim()) {
    console.log('\n!! POST sem o cabeçalho apikey — a Evolution recusaria com 401.\n');
    return responder(res, 401, { status: 401, error: 'Unauthorized', message: 'apikey ausente' });
  }

  let corpo: any;
  try {
    corpo = JSON.parse(bruto);
  } catch {
    return responder(res, 400, { error: { message: 'Malformed JSON', code: 100 } });
  }

  // VALIDAÇÃO DE FORMA, e não zelo de dublê.
  //
  // A Evolution recusa com 400 um corpo sem `number` ou sem `text`. Este dublê
  // aceitava qualquer coisa e respondia 201, e isso escondia exatamente um bug:
  // uma linha de outbox gravada ANTES da migração guarda o payload no formato da
  // Meta (`{messaging_product, to, type, text:{body}}`), o varredor a reenvia
  // literal, e o 201 de mentira a marcava como ENTREGUE sem destinatário nenhum.
  //
  // Recusar aqui é o que faz esse caso aparecer em desenvolvimento em vez de em
  // produção, como mensagem que some.
  const faltando = ['number', 'text'].filter(
    (c) => typeof corpo?.[c] !== 'string' || corpo[c] === ''
  );
  if (faltando.length > 0) {
    console.log(`\n!! CORPO FORA DO FORMATO — falta ${faltando.join(' e ')}.`);
    console.log(`   ${JSON.stringify(corpo)}`);
    console.log('   A Evolution de verdade recusaria com 400.\n');
    return responder(res, 400, {
      status: 400,
      error: 'Bad Request',
      message: `Campo obrigatório ausente: ${faltando.join(', ')}`,
    });
  }

  if (controle.status > 0 && controle.vezes > 0) {
    controle.vezes -= 1;
    const restam = controle.vezes;
    if (restam === 0) controle.status = 0;
    console.log(`\n-- RECUSADO de propósito (${controle.status || 'último'}), restam ${restam}`);
    for (const l of descrever(corpo)) console.log(`   ${l}`);
    console.log('');
    return responder(res, controle.status || 503, {
      status: controle.status || 503,
      error: 'Internal Server Error',
      message: 'Falha simulada pela Evolution de mentira',
    });
  }

  entregues += 1;
  console.log(`\n<< #${entregues} ${new Date().toISOString()}`);
  for (const l of descrever(corpo)) console.log(`   ${l}`);
  console.log('');

  // A forma da resposta de sucesso da Evolution v2: a chave da mensagem, com o
  // JID do destinatário e o id gerado. O bot só olha o status HTTP, mas devolver
  // a forma certa é o que permite este dublê revelar um consumidor que passe a
  // depender do corpo.
  const jid = `${corpo?.number}@s.whatsapp.net`;
  return responder(res, 201, {
    key: { remoteJid: jid, fromMe: true, id: `FAKE${Date.now().toString(36)}${entregues}` },
    message: { extendedTextMessage: { text: corpo?.text } },
    messageTimestamp: String(Math.floor(Date.now() / 1000)),
    status: 'PENDING',
  });
});

servidor.listen(PORTA, '127.0.0.1', () => {
  console.log(`Evolution de mentira ouvindo em http://127.0.0.1:${PORTA}`);
  console.log(`Aponte o bot para cá com:  EVOLUTION_URL=http://127.0.0.1:${PORTA}`);
  console.log('');
  console.log('Simular queda da Evolution (3 respostas 503):');
  console.log(
    `  curl -X POST http://127.0.0.1:${PORTA}/_controle -H "content-type: application/json" -d "{\\"status\\":503,\\"vezes\\":3}"`
  );
  console.log('');
});
