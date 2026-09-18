/**
 * Sobe o bot e o painel num TERMINAL SÓ.
 *
 * Antes eram três janelas: a do `run.bat` mais uma para cada serviço, abertas
 * com `start ... cmd /k`. Três janelas custam mais do que parecem — ninguém
 * sabe qual olhar quando algo falha, fechar a errada derruba metade do sistema
 * sem aviso, e a máquina reiniciada volta sem nenhuma delas.
 *
 * Aqui os dois viram filhos deste processo. Cada linha de log sai marcada com
 * a origem, e um Ctrl+C encerra os dois de uma vez — o bot tem tratamento de
 * SIGINT e fecha o banco direito (ver src/server.ts).
 *
 * A divisão de trabalho com o `run.bat` é: ele confere o AMBIENTE (Node, .env,
 * portas livres, dependências, Prisma, build) e este arquivo cuida da EXECUÇÃO.
 * Por isso ele não repete checagem nenhuma daqui.
 *
 * Sem dependências: só a biblioteca padrão, como o resto do projeto.
 */
import { spawn } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const AQUI = dirname(fileURLToPath(import.meta.url));

try {
  process.loadEnvFile(join(AQUI, '.env'));
} catch {
  // Sem .env: valem os padrões abaixo. Quem reclama disso é o run.bat.
}

const PORTA_BOT = Number(process.env.PORT || 9511);
// 8511: a porta que o tunel aponta. Ver servidor-painel.mjs.
const PORTA_PAINEL = Number(process.env.PAINEL_PORT || 8511);
const URL_PAINEL = (process.env.PAINEL_URL_BASE || '').trim() || `http://localhost:${PORTA_PAINEL}`;
const COM_LOGIN = (process.env.ENTRA_CLIENT_ID || '').trim() !== '';

// O painel fala HTTPS consigo mesmo só quando ELE termina o TLS. Com o túnel na
// frente (o arranjo em uso), ele serve HTTP aqui dentro.
const PAINEL_TLS =
  (process.env.PAINEL_TLS_CERT || process.env.PAINEL_TLS_CERTIFICADO || '').trim() !== '';
const SONDA_PAINEL = `${PAINEL_TLS ? 'https' : 'http'}://127.0.0.1:${PORTA_PAINEL}/`;

/* ---------- Saída marcada ------------------------------------------- */

// Largura fixa para as duas colunas de log ficarem alinhadas: com [bot] e
// [painel] de tamanhos diferentes, o olho perde a coluna do texto.
const MARCA = { bot: '[bot   ]', painel: '[painel]', geral: '[iniciar]' };

// O painel marca as proprias linhas com "[painel]", e faz certo: ele tambem
// roda sozinho, pelo painel.bat, onde essa marca e a unica que existe. Aqui ela
// seria a segunda, e "[painel] [painel] servindo ..." e ruido.
const AUTO_MARCA = /^\[(painel|iniciar)\]\s?/;

function escrever(quem, texto) {
  for (const linha of texto.split('\n')) {
    if (linha.trim() === '') continue;
    console.log(`${MARCA[quem]} ${linha.replace(AUTO_MARCA, '')}`);
  }
}

/**
 * Um pedaço de stdout não chega em linhas inteiras: o fim de um chunk costuma
 * ser meia linha, e imprimi-la já marcaria a origem no meio de uma frase. Este
 * acumulador segura o resto até a próxima quebra.
 */
function fluxoMarcado(quem, fluxo) {
  let resto = '';
  fluxo.setEncoding('utf8');
  fluxo.on('data', (pedaco) => {
    const partes = (resto + pedaco).split('\n');
    resto = partes.pop();
    if (partes.length) escrever(quem, partes.join('\n'));
  });
  fluxo.on('end', () => {
    if (resto.trim() !== '') escrever(quem, resto);
    resto = '';
  });
}

/* ---------- Os filhos ------------------------------------------------ */

const filhos = new Map();
let encerrando = false;

function subir(quem, script, extraEnv = {}) {
  const filho = spawn(process.execPath, [join(AQUI, script)], {
    cwd: AQUI,
    env: { ...process.env, ...extraEnv },
    // `pipe` e não `inherit`: é o que permite marcar a origem de cada linha.
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  fluxoMarcado(quem, filho.stdout);
  fluxoMarcado(quem, filho.stderr);

  filho.on('exit', (codigo, sinal) => {
    filhos.delete(quem);
    if (encerrando) return;

    // Morte inesperada. Derrubar o irmão é deliberado: meio sistema no ar é o
    // estado que mais confunde — o painel abre, o atendente trabalha, e nada
    // do WhatsApp entra. Melhor cair inteiro e ser reiniciado.
    escrever('geral', `!! ${quem} morreu (${sinal || `codigo ${codigo}`}). Encerrando o resto.`);
    encerrar(1);
  });

  filhos.set(quem, filho);
  return filho;
}

function encerrar(codigo) {
  if (encerrando) return;
  encerrando = true;

  for (const [quem, filho] of filhos) {
    escrever('geral', `parando ${quem}...`);
    filho.kill('SIGINT');
  }

  // Rede de segurança: se algum não sair sozinho, o processo não pode ficar
  // pendurado para sempre segurando as portas.
  const prazo = setTimeout(() => {
    for (const filho of filhos.values()) filho.kill();
    process.exit(codigo);
  }, 8000);
  prazo.unref();

  const esperar = setInterval(() => {
    if (filhos.size === 0) {
      clearInterval(esperar);
      process.exit(codigo);
    }
  }, 100);
}

/* ---------- Sondas ---------------------------------------------------- */

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * `aceita` decide o que conta como "está de pé", e o padrão não serve para os
 * dois casos:
 *
 *   - /health e /ready respondem 200, então `r.ok` é a pergunta certa;
 *   - a raiz do painel responde 302 para o login quando o Entra está ligado.
 *     Com `r.ok` ali, a sonda falharia SEMPRE nessa configuração - gastando as
 *     tentativas todas e terminando num aviso falso de "não respondeu".
 *
 * Para o painel, portanto, qualquer resposta HTTP serve: ela já prova que a
 * porta está atendendo, que é tudo o que a sonda precisa saber.
 */
async function esperarResposta(url, tentativas, { aceita = (r) => r.ok, ...opcoes } = {}) {
  for (let i = 0; i < tentativas; i++) {
    if (encerrando) return false;
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(2000), ...opcoes });
      if (aceita(r)) return true;
    } catch {
      // Ainda subindo, ou não vai subir. Quem decide é o número de tentativas.
    }
    await dormir(1000);
  }
  return false;
}

/* ---------- Início ---------------------------------------------------- */

// Ctrl+C chega aos filhos junto (eles dividem o console), mas o handler daqui é
// o que garante a ORDEM: avisa, espera os dois fecharem, e só então sai.
process.on('SIGINT', () => {
  console.log('');
  escrever('geral', 'Ctrl+C recebido.');
  encerrar(0);
});
process.on('SIGTERM', () => encerrar(0));

escrever('geral', `subindo o bot na porta ${PORTA_BOT}`);
// PORT no ambiente do filho, e não só no .env: o dotenv não sobrescreve
// variável existente, então isto vence um PORT herdado da máquina.
subir('bot', 'dist/server.js', { PORT: String(PORTA_BOT) });

const botOk = await esperarResposta(`http://127.0.0.1:${PORTA_BOT}/health`, 30);

if (botOk) {
  escrever('geral', `bot respondendo em /health`);

  // /ready pergunta pelo BANCO. O bot sobe mesmo sem conseguir abrir o arquivo,
  // e aí todo chamado falha na hora de gravar.
  const banco = await esperarResposta(`http://127.0.0.1:${PORTA_BOT}/ready`, 1);
  escrever(
    'geral',
    banco ? 'banco acessivel (/ready)' : 'AVISO: /ready recusou - bot de pe, SEM BANCO'
  );
} else if (!encerrando) {
  escrever('geral', 'AVISO: o bot nao respondeu em /health. Subindo o painel assim mesmo.');
}

if (!encerrando) {
  escrever('geral', `subindo o painel na porta ${PORTA_PAINEL}`);
  subir('painel', 'servidor-painel.mjs');

  // Qualquer resposta serve (ver `aceita` acima): com o Entra ligado a raiz
  // devolve 302 para o login, e `redirect: manual` evita seguir o desvio até a
  // Microsoft só para saber se a porta atende.
  const painelOk = await esperarResposta(SONDA_PAINEL, 15, {
    redirect: 'manual',
    aceita: () => true,
  });

  console.log('');
  escrever('geral', '================================================================');
  escrever('geral', botOk ? '  NO AR' : '  PAINEL NO AR  -  BOT FORA');
  escrever('geral', '================================================================');
  escrever('geral', `  Painel   ${URL_PAINEL}`);
  escrever('geral', `  API bot  http://localhost:${PORTA_BOT}`);
  escrever(
    'geral',
    COM_LOGIN
      ? '  Entrada: login pelo Microsoft Entra ID.'
      : '  Entrada: o painel pede o PAINEL_TOKEN do .env ao abrir.'
  );

  if (!botOk) {
    escrever('geral', '');
    escrever('geral', '  Com o bot fora, NENHUMA mensagem de WhatsApp entra nem sai.');
    escrever('geral', '  O motivo esta nas linhas marcadas [bot   ] acima.');
  }
  if (!painelOk) {
    escrever('geral', '  AVISO: o painel nao respondeu a sonda - veja as linhas [painel].');
  }

  escrever('geral', '');
  escrever('geral', '  Ctrl+C aqui encerra os DOIS. Esta janela e a aplicacao.');
  escrever('geral', '================================================================');
  console.log('');
}
