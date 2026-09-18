/**
 * Diagnóstico do go-live, camada por camada.
 *
 * Existe porque "a Meta não valida o webhook" é o mesmo sintoma para seis
 * causas diferentes, em quatro camadas distintas — e olhar todas na mão, na
 * ordem errada, é como se perde uma tarde. Aqui elas são checadas de dentro
 * para fora, e a primeira que falhar é a que interessa: as de fora só podem
 * funcionar se as de dentro funcionarem.
 *
 *   1. .env       — os valores têm o formato certo?
 *   2. processos  — o bot e o painel estão atendendo nas portas?
 *   3. localhost  — o handshake do webhook funciona pelo painel?
 *   4. internet   — a Meta consegue chegar aqui pelo domínio?
 *
 * Rode com:  node diagnostico.mjs
 *
 * Nenhum segredo é impresso: tokens aparecem como tamanho, nunca como valor.
 */
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const AQUI = dirname(fileURLToPath(import.meta.url));

try {
  process.loadEnvFile(join(AQUI, '.env'));
} catch {
  console.log('!! nao achei o .env nesta pasta. Rode o diagnostico na raiz do projeto.');
  process.exit(1);
}

const v = (t) => `\x1b[32m${t}\x1b[0m`;
const x = (t) => `\x1b[31m${t}\x1b[0m`;
const a = (t) => `\x1b[33m${t}\x1b[0m`;

let problemas = 0;
const ok = (m) => console.log(`  ${v('OK')}    ${m}`);
const erro = (m, comoResolver) => {
  problemas++;
  console.log(`  ${x('ERRO')}  ${m}`);
  if (comoResolver) console.log(`        -> ${comoResolver}`);
};
const aviso = (m) => console.log(`  ${a('AVISO')} ${m}`);

const env = (n) => (process.env[n] || '').trim();

const PORTA_BOT = Number(env('PORT') || 9511);
const PORTA_PAINEL = Number(env('PAINEL_PORT') || 8511);
const URL_BASE = env('PAINEL_URL_BASE').replace(/\/+$/, '');

/* ---------- 1. .env --------------------------------------------------- */

console.log('\n1. CONFIGURACAO (.env)');

const segredo = env('WEBHOOK_SEGREDO');
if (segredo === '') {
  erro('WEBHOOK_SEGREDO vazio', 'e o pedaco final da URL que voce cadastra na Evolution');
} else if (segredo.length < 16) {
  erro(
    `WEBHOOK_SEGREDO tem so ${segredo.length} caracteres`,
    'ele e a UNICA prova de que o POST veio da sua instancia - use 32 ou mais'
  );
} else if (/[^A-Za-z0-9._~-]/.test(segredo)) {
  erro(
    'WEBHOOK_SEGREDO tem caractere que nao sobrevive a uma URL',
    'use so letras, numeros, ponto, hifen, underline e til'
  );
} else ok(`WEBHOOK_SEGREDO presente (${segredo.length} caracteres)`);

const evoUrl = env('EVOLUTION_URL');
if (evoUrl === '') erro('EVOLUTION_URL vazio');
else if (!/^https?:\/\//.test(evoUrl)) erro('EVOLUTION_URL sem http:// ou https://');
else if (/^http:\/\/127\.0\.0\.1:4000/.test(evoUrl)) {
  erro(
    'EVOLUTION_URL aponta para a Evolution DE MENTIRA (porta 4000)',
    'e o alvo de desenvolvimento: nada sai para o WhatsApp de verdade'
  );
} else if (evoUrl.endsWith('/')) {
  aviso('EVOLUTION_URL termina em barra - o codigo remove, mas confira o valor');
} else ok(`EVOLUTION_URL = ${evoUrl}`);

if (env('EVOLUTION_API_KEY') === '') erro('EVOLUTION_API_KEY vazio');
else ok('EVOLUTION_API_KEY presente');

const instancia = env('EVOLUTION_INSTANCIA');
if (instancia === '') erro('EVOLUTION_INSTANCIA vazio');
else ok(`EVOLUTION_INSTANCIA = ${instancia}`);

// TLS: o acidente conhecido e colar o PEM na variavel em vez do caminho.
for (const nome of ['PAINEL_TLS_CERT', 'PAINEL_TLS_KEY']) {
  const valor = env(nome);
  if (valor === '') continue;
  if (valor.startsWith('-----BEGIN') || /^M[IH][A-Za-z0-9+/=]{16}/.test(valor)) {
    erro(
      `${nome} tem o CONTEUDO do certificado, nao um caminho`,
      'com tunel na frente, o certo e deixar as duas VAZIAS (o painel serve HTTP)'
    );
  } else if (!existsSync(valor)) {
    erro(`${nome} aponta para arquivo inexistente: ${valor}`);
  } else ok(`${nome} aponta para um arquivo que existe`);
}

const entra = ['ENTRA_TENANT_ID', 'ENTRA_CLIENT_ID', 'ENTRA_CLIENT_SECRET', 'PAINEL_URL_BASE'];
const preenchidas = entra.filter((n) => env(n) !== '');
if (preenchidas.length === 0)
  aviso('login pelo Entra DESLIGADO - quem alcancar a porta entra direto');
else if (preenchidas.length < 4) {
  erro(
    `login pelo Entra pela metade (${preenchidas.length} de 4) - o painel se recusa a subir`,
    `falta: ${entra.filter((n) => env(n) === '').join(', ')}`
  );
} else if (env('PAINEL_SESSAO_SEGREDO') === '') {
  erro('login pelo Entra ligado, mas sem PAINEL_SESSAO_SEGREDO');
} else ok('login pelo Entra configurado');

/* ---------- 2. processos ---------------------------------------------- */

console.log('\n2. SERVICOS (nesta maquina)');

async function tenta(url, opcoes = {}) {
  try {
    return await fetch(url, { signal: AbortSignal.timeout(5000), redirect: 'manual', ...opcoes });
  } catch (e) {
    return { erroDeRede: e.cause?.code || e.message };
  }
}

const health = await tenta(`http://127.0.0.1:${PORTA_BOT}/health`);
if (health.erroDeRede) {
  erro(`o bot nao atende em 127.0.0.1:${PORTA_BOT} (${health.erroDeRede})`, 'rode o run.bat');
} else {
  ok(`bot respondendo em /health (${health.status})`);
  const ready = await tenta(`http://127.0.0.1:${PORTA_BOT}/ready`);
  if (ready.status === 200) ok('banco acessivel pelo bot (/ready)');
  else erro('/ready recusou: o bot esta de pe, mas SEM BANCO');
}

const painel = await tenta(`http://127.0.0.1:${PORTA_PAINEL}/`);
if (painel.erroDeRede) {
  erro(
    `o painel nao atende em 127.0.0.1:${PORTA_PAINEL} (${painel.erroDeRede})`,
    'e a causa mais comum de 502 no dominio: o tunel entrega aqui e nao tem ninguem'
  );
} else if (painel.status === 302) {
  ok('painel respondendo (302 para o login do Entra, como esperado)');
} else {
  ok(`painel respondendo (${painel.status})`);
}

/* ---------- 3. webhook por dentro ------------------------------------- */

console.log('\n3. WEBHOOK POR DENTRO (localhost)');

/*
 * Nao existe mais handshake: a Evolution nao valida a URL antes de usar. O que
 * da para provar daqui e o par que importa em producao - o segredo certo passa,
 * o errado nao.
 *
 * O evento escolhido e `connection.update`, que o bot le e descarta: exercita o
 * caminho inteiro (roteamento, corpo, autenticacao) sem criar chamado nem mandar
 * mensagem para ninguem.
 */
const PING = JSON.stringify({ event: 'connection.update', instance: 'diagnostico', data: {} });
const postarWebhook = (base, seg) =>
  tenta(`${base}/webhook/${seg}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: PING,
  });

const BOT = `http://127.0.0.1:${PORTA_BOT}`;
const PAINEL = `http://127.0.0.1:${PORTA_PAINEL}`;
const segredoErrado = 'nao-e-esse-' + Math.random().toString(36).slice(2, 8);

const direto = await postarWebhook(BOT, segredo);
if (direto.erroDeRede) {
  erro(`bot inacessivel (${direto.erroDeRede})`);
} else if (direto.status === 200) {
  ok('bot aceita o webhook com o segredo do .env');
} else if (direto.status === 404) {
  erro(
    'o bot devolve 404 com este segredo',
    'o WEBHOOK_SEGREDO do .env e diferente do que o processo carregou - reinicie o bot'
  );
} else {
  erro(`o bot respondeu ${direto.status} ao webhook`);
}

const recusado = await postarWebhook(BOT, segredoErrado);
if (recusado.status === 404) ok('segredo errado recusado (404)');
else if (!recusado.erroDeRede) {
  erro(
    `segredo ERRADO respondeu ${recusado.status} - deveria ser 404`,
    'assim qualquer um que descobrir a URL forja mensagem em nome de qualquer numero'
  );
}

const viaPainel = await postarWebhook(PAINEL, segredo);
if (viaPainel.erroDeRede) {
  erro(`painel inacessivel (${viaPainel.erroDeRede})`);
} else if (viaPainel.status === 302) {
  erro(
    'o painel manda /webhook para o LOGIN (302)',
    'este servidor-painel.mjs e antigo: falta o repasse de /webhook. Atualize o codigo.'
  );
} else if (viaPainel.status === 404) {
  erro(
    'o painel devolve 404 em /webhook',
    'ou falta o repasse de /webhook no servidor-painel.mjs, ou ele repassa PERDENDO o segredo do caminho'
  );
} else if (viaPainel.status === 200) {
  ok('painel repassa o webhook para o bot, com o segredo intacto');
} else erro(`o painel respondeu ${viaPainel.status} ao webhook`);

/* ---------- 4. pela internet ------------------------------------------ */

console.log('\n4. PELA INTERNET (o caminho da Evolution)');

if (URL_BASE === '') {
  aviso('PAINEL_URL_BASE vazio - pulando');
} else {
  if (!URL_BASE.startsWith('https://')) {
    erro(
      `PAINEL_URL_BASE nao e HTTPS (${URL_BASE})`,
      'o segredo vai no CAMINHO da URL: em HTTP ele viaja legivel pela rede'
    );
  }

  const publico = await postarWebhook(URL_BASE, segredo);

  if (publico.erroDeRede) {
    erro(`nao consegui alcancar ${URL_BASE} (${publico.erroDeRede})`, 'DNS ou saida de rede');
  } else if (publico.status === 502 || publico.status === 521 || publico.status === 523) {
    erro(
      `${URL_BASE} respondeu ${publico.status} - a Cloudflare nao alcanca esta maquina`,
      'o tunel esta no ar, mas aponta para uma porta onde ninguem atende. ' +
        `O ingress tem de ser http://localhost:${PORTA_PAINEL}`
    );
  } else if (publico.status === 530 || publico.status === 1033) {
    erro(`${URL_BASE} respondeu ${publico.status}`, 'o cloudflared nao esta rodando');
  } else if (publico.status === 200) {
    ok('a Evolution alcanca o bot pelo dominio, com o segredo certo');
  } else if (publico.status === 404) {
    erro(
      'o dominio devolve 404 no webhook',
      'segredo diferente do que o processo no ar carregou, ou o tunel aponta para outro servico'
    );
  } else if (publico.status === 302) {
    erro(
      'o dominio manda /webhook para o login (302)',
      'o codigo no ar nao tem o repasse de /webhook, ou o tunel aponta para outro servico'
    );
  } else {
    const corpo = await publico.text();
    erro(`${URL_BASE} respondeu ${publico.status}`, corpo.slice(0, 120));
  }
}

/* ---------- veredito --------------------------------------------------- */

console.log(
  problemas === 0
    ? `\n${v('Tudo certo.')} Se nao chegar mensagem, confira a URL do webhook na Evolution e se a instancia esta conectada.\n`
    : `\n${x(`${problemas} problema(s).`)} Resolva o PRIMEIRO da lista - os de baixo costumam ser consequencia.\n`
);
