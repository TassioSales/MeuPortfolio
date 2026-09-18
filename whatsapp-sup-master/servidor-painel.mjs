/**
 * Servidor do painel de chamados (activity-dashboard).
 *
 * Faz duas coisas, e as duas são necessárias:
 *
 * 1. Serve os arquivos estáticos do painel. Abrir o index.html direto do disco
 *    não funciona: em `file://` a origem vira "null" e nenhum CORS sensato a
 *    libera.
 *
 * 2. Repassa `/internal/*` para o bot em 127.0.0.1:PORTA_BOT. É isto que tira o
 *    CORS do caminho: para o navegador, painel e API estão na MESMA origem.
 *    Sem o proxy, `PAINEL_ORIGENS` no .env do bot precisaria listar
 *    antecipadamente todo endereço pelo qual alguém fosse abrir o painel
 *    (localhost, o IP da máquina na rede, o domínio) — e qualquer um que
 *    faltasse quebraria o quadro com um erro que o navegador se recusa a
 *    explicar. Com o proxy, nenhum desses endereços precisa ser previsto.
 *
 * Sem dependências: só a biblioteca padrão do Node, que já é requisito do bot.
 */
import 'dotenv/config';
import { createServer, request as pedirHttp } from 'node:http';
import { createServer as criarServidorTls } from 'node:https';
import { createReadStream, existsSync, readFileSync } from 'node:fs';
import { stat } from 'node:fs/promises';

import {
  concluirLogin,
  iniciarLogin,
  lerConfigEntra,
  sairDoPainel,
  sessaoDe,
} from './painel-entra.mjs';
import {
  atenderMetricas,
  registrarAtividade,
  registrarBuildInfo,
  registrarEstadoDoLogin,
} from './painel-metricas.mjs';
import { extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

const AQUI = dirname(fileURLToPath(import.meta.url));
const RAIZ = join(AQUI, 'activity-dashboard');

// O .env é a MESMA fonte que o bot e o run.bat usam. Ler daqui é o que deixa
// este servidor subir sozinho - por atalho, pelo Agendador de Tarefas, ou
// depois de alguém fechar a janela sem querer - sem depender de ter herdado as
// portas do run.bat. Variável que já exista no ambiente vence o arquivo, então
// o run.bat continua sendo quem manda quando é ele que sobe os dois.
try {
  process.loadEnvFile(join(AQUI, '.env'));
} catch {
  // Sem .env ao lado: valem os padrões abaixo.
}

// 8511 e nao outra: e a porta que o tunel da Cloudflare aponta. Como este
// servidor repassa /webhook e /internal/* para o bot, uma porta publica basta
// para os dois - e o bot foi para a 9511, fora da faixa 8500-8600 que o
// servidor reservou.
const PORTA = Number(process.env.PAINEL_PORT || 8511);

// BOT_PORT é o nome que o run.bat injeta; PORT é o que o bot de fato lê
// (src/config.ts). Cair de um para o outro fecha o desencontro que dava 502 com
// os DOIS serviços no ar e nenhum erro em lugar nenhum: o painel batia em 8511
// enquanto o bot, sem PORT definido, subia no padrão dele - 3000.
const PORTA_BOT = Number(process.env.BOT_PORT || process.env.PORT || 9511);
const HOST = process.env.PAINEL_HOST || '0.0.0.0';

// Token que o Prometheus manda para raspar GET /metrics. Sem ele a rota nao
// existe (falha fechada) - ver painel-metricas.mjs.
const METRICS_TOKEN = (process.env.METRICS_TOKEN || '').trim();
const GIT_COMMIT = (process.env.GIT_COMMIT || '').trim();
const APP_VERSION = (process.env.APP_VERSION || '').trim();

/**
 * HTTPS não é enfeite aqui: o Entra ID só aceita redirect_uri em `http` para
 * `localhost`. Publicar o painel num nome da rede e ter login pelo Entra são,
 * na prática, a mesma decisão — por isso o certificado mora ao lado das
 * variáveis do login, e não numa camada separada.
 *
 * Sem os dois caminhos, sobe em HTTP puro. Continua servindo para abrir por
 * `localhost` na própria máquina.
 */
const TLS_CERT = (process.env.PAINEL_TLS_CERT || process.env.PAINEL_TLS_CERTIFICADO || '').trim();
const TLS_KEY = (process.env.PAINEL_TLS_KEY || process.env.PAINEL_TLS_CHAVE || '').trim();

const ENTRA = lerConfigEntra(process.env);

// Configuração pela metade não sobe. Ficar de pé SEM login porque faltou uma
// variável é o pior desfecho possível: alguém pediu proteção, não recebeu, e
// nada avisou. Espelha o que o config.ts faz do lado do bot.
if (ENTRA.faltando.length > 0) {
  console.error(
    'O login pelo Entra ID esta configurado pela metade. Falta preencher no .env:\n' +
      ENTRA.faltando.map((v) => `  - ${v}`).join('\n') +
      '\n\nPreencha todas, ou apague todas para subir sem login.'
  );
  process.exit(1);
}

/**
 * Com isto ligado, o token de acesso à API deixa de ser digitado no navegador:
 * o proxy passa a injetá-lo aqui, a partir do .env, e o painel abre direto no
 * quadro.
 *
 * O que a troca custa: o token É a única autenticação do painel. No servidor,
 * quem alcança esta porta tem acesso — lê nome, telefone e descrição dos
 * chamados, e move cartão, o que dispara WhatsApp para uma pessoa real. Só faz
 * sentido com a porta restrita à rede interna ou atrás de VPN.
 *
 * Desligado (o padrão), nada muda: o navegador manda o token e o proxy repassa.
 */
const TOKEN_NO_SERVIDOR = /^(1|true|sim)$/i.test(
  (process.env.PAINEL_TOKEN_NO_SERVIDOR || '').trim()
);

// O mesmo par que a API aceita (src/internal/auth.ts). O INTERNAL_API_TOKEN
// entra como reserva porque o PAINEL_TOKEN pode não estar configurado.
const TOKEN_DO_PAINEL = (process.env.PAINEL_TOKEN || process.env.INTERNAL_API_TOKEN || '').trim();

// Ligado de fato = pedido E possível. Sem token no .env não há o que injetar,
// e o painel volta a pedir no navegador em vez de falhar com 401 em tudo.
const AUTENTICA_AQUI = TOKEN_NO_SERVIDOR && TOKEN_DO_PAINEL !== '';

/**
 * O modo mais perigoso: SEM login (Entra desligado) e COM token injetado no
 * servidor. Aí quem alcança a porta entra direto e lê/altera chamado — dado
 * pessoal de gente real e disparo de WhatsApp — sem apresentar credencial
 * nenhuma. Só é aceitável com a porta restrita à rede interna ou atrás de VPN.
 *
 * Antes isso era só um AVISO no log, fácil de não ler. Agora, se além disso o
 * bind for para fora do loopback (`0.0.0.0`, um IP da rede), o painel RECUSA
 * subir — a menos que o operador declare, explicitamente, que a porta está
 * protegida por fora. É o mesmo "falha alto e cedo" que o config.ts do bot faz.
 */
const HOST_LOOPBACK = /^(127\.0\.0\.1|::1|localhost)$/i.test(HOST);
if (!ENTRA.ligado && AUTENTICA_AQUI && !HOST_LOOPBACK) {
  const exposicaoLiberada = /^(1|true|sim)$/i.test(
    (process.env.PAINEL_EXPOSICAO_SEM_LOGIN || '').trim()
  );
  if (!exposicaoLiberada) {
    console.error(
      `[painel] RECUSANDO subir: sem login do Entra, token injetado no servidor e\n` +
        `escutando em ${HOST} (fora do loopback). Nesse estado, qualquer um que\n` +
        `alcance a porta le e altera chamado SEM autenticar.\n\n` +
        `Escolha uma saida:\n` +
        `  - ligue o login: preencha as variaveis ENTRA_* do .env; ou\n` +
        `  - restrinja o bind: PAINEL_HOST=127.0.0.1 (so a propria maquina); ou\n` +
        `  - se a porta ja esta protegida por firewall/VPN e a exposicao e\n` +
        `    intencional, confirme com PAINEL_EXPOSICAO_SEM_LOGIN=1 no .env.`
    );
    process.exit(1);
  }
  console.warn(
    `[painel] AVISO: SEM login e escutando em ${HOST}. Exposicao confirmada por\n` +
      `[painel] PAINEL_EXPOSICAO_SEM_LOGIN. Garanta que a porta esta atras de\n` +
      `[painel] firewall ou VPN - quem a alcancar le e altera chamado sem autenticar.`
  );
}

/**
 * Cria (ou reencontra) o perfil de quem acabou de entrar.
 *
 * Mora aqui, e não no painel-entra.mjs, porque é este arquivo que sabe falar
 * com o bot: a porta e o token da API são dele. O módulo do login só sabe
 * validar identidade, e é bom que continue assim.
 *
 * Por que do SERVIDOR e não do navegador: a identidade vem do `id_token` que
 * acabou de ser verificado contra as chaves do tenant. Se a página pedisse
 * "registre o oid X", qualquer um com o token da API poderia criar perfil como
 * qualquer pessoa - e o token, nesta instalação, vai para o navegador.
 *
 * Nunca lança: quem chama está no meio de um login, e bot fora do ar não pode
 * virar "não consigo entrar no painel". O pior caso é a lista de pessoas
 * demorar um login para ficar em dia.
 */
async function registrarPerfil(sessao) {
  if (TOKEN_DO_PAINEL === '' || !sessao?.oid) return;

  try {
    const r = await fetch(`http://127.0.0.1:${PORTA_BOT}/internal/pessoas/identidade`, {
      method: 'PUT',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${TOKEN_DO_PAINEL}`,
      },
      body: JSON.stringify({ oid: sessao.oid, nome: sessao.nome, email: sessao.email }),
      signal: AbortSignal.timeout(5000),
    });

    if (!r.ok) {
      console.warn(
        `[painel] nao foi possivel registrar o perfil de ${sessao.email}: HTTP ${r.status}`
      );
      return;
    }

    const pessoa = await r.json();
    console.log(`[painel] perfil de ${sessao.email} no cadastro (id ${pessoa.id})`);
  } catch (err) {
    console.warn(
      `[painel] nao foi possivel registrar o perfil de ${sessao.email}: ${err.code || err.message}`
    );
  }
}

// O módulo do login recebe a função pronta, em vez de importar daqui - assim
// ele continua sem saber que existe um bot do outro lado.
ENTRA.registrarPerfil = registrarPerfil;

// Arquivo GERADO, servido de memória - ver servirConfigDoPainel().
const CAMINHO_CONFIG = '/painel-servidor.js';

const TIPOS = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
  '.map': 'application/json; charset=utf-8',
};

/**
 * Cabeçalhos de segurança das páginas do painel.
 *
 * O bot (Fastify) já tem helmet; estas páginas são servidas por ESTE processo,
 * sem nenhum. Sem CSP não há segunda linha caso um `esc()` seja esquecido no
 * `app.js`, e sem `frame-ancestors`/`X-Frame-Options` o painel pode ser embutido
 * em iframe de terceiro (clickjacking) — e arrastar um cartão dispara WhatsApp
 * para uma pessoa real.
 *
 * `style-src 'unsafe-inline'` é necessário: os avatares pintam a cor de fundo com
 * `style="background:…"` inline (ver activity-dashboard/app.js), e o CSS usa
 * `background: url("data:image/svg+xml,…")`. `img-src` inclui `data:` (por esse
 * SVG) e `blob:` (download de anexo). Os scripts são todos locais e NÃO há
 * `<script>` inline, então `script-src 'self'` (herdado de default-src) basta.
 */
const CSP_PAINEL =
  "default-src 'self'; " +
  "style-src 'self' 'unsafe-inline'; " +
  "img-src 'self' data: blob:; " +
  "font-src 'self'; " +
  "connect-src 'self'; " +
  "object-src 'none'; " +
  "base-uri 'none'; " +
  "frame-ancestors 'none'";

const CABECALHOS_SEGURANCA = {
  'content-security-policy': CSP_PAINEL,
  'x-frame-options': 'DENY',
  'x-content-type-options': 'nosniff',
  'referrer-policy': 'no-referrer',
};

// Métodos que ALTERAM estado. São os que um site de terceiro tentaria disparar
// no navegador de um atendente logado (CSRF): criar/mover/excluir chamado.
const METODOS_ESCRITA = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/**
 * Verificação de Origin contra CSRF nas rotas `/internal/*` que alteram estado.
 *
 * A autenticação por cookie de sessão (modo Entra) é enviada pelo navegador
 * automaticamente, então `SameSite=Lax` era a ÚNICA barreira de CSRF. Esta é a
 * segunda: um pedido de escrita cujo `Origin` não seja o do próprio painel é
 * recusado.
 *
 * Regra: bloqueia só quando há `Origin` E ele não bate. Cliente que não é
 * navegador (curl, integração) não manda `Origin` e continua passando — o CSRF
 * de navegador SEMPRE manda. Não se aplica ao `/webhook`: a Evolution não manda
 * `Origin` e se autentica pela assinatura do corpo.
 */
function origemBloqueada(req) {
  const origem = req.headers.origin;
  if (!origem) return false;

  const esquema = usandoTls ? 'https' : 'http';
  const aceitas = new Set();
  if (req.headers.host) aceitas.add(`${esquema}://${req.headers.host}`);
  if (ENTRA.ligado && ENTRA.urlBase) aceitas.add(ENTRA.urlBase);

  return !aceitas.has(origem);
}

/**
 * Repassa a requisição para o bot preservando método, corpo e o header
 * `Authorization` — é ele que carrega o PAINEL_TOKEN, e sem ele a API responde
 * 401 a tudo.
 */
function repassar(req, res, injetarToken = true) {
  const cabecalhos = { ...req.headers };
  // O Host original apontaria para a porta do painel; quem vai atender é o bot.
  delete cabecalhos.host;
  // O corpo é repassado byte a byte; deixar um `content-length` antigo ou um
  // `accept-encoding` que peça compressão só cria divergência sem ganho.
  delete cabecalhos['accept-encoding'];

  // Token no servidor: o que o navegador mandou (nada, nesse modo) é
  // descartado e substituído pelo valor do .env. Quem autentica é este
  // processo, não a máquina do atendente.
  //
  // `injetarToken` é falso no caminho do webhook: quem chama ali é a Evolution, que
  // se autentica pelo segredo do caminho, e não por `Authorization`. Injetar
  // um Bearer que ninguém confere só criaria a impressão de que ele importa.
  if (AUTENTICA_AQUI && injetarToken) {
    cabecalhos.authorization = `Bearer ${TOKEN_DO_PAINEL}`;
  }

  const upstream = pedirHttp(
    { host: '127.0.0.1', port: PORTA_BOT, path: req.url, method: req.method, headers: cabecalhos },
    (resposta) => {
      res.writeHead(resposta.statusCode || 502, resposta.headers);
      resposta.pipe(res);
    }
  );

  upstream.on('error', (err) => {
    // Erro aqui é quase sempre "o bot ainda não subiu" ou "o bot caiu". Dizer
    // isso em texto evita mandar alguém procurar bug no navegador.
    console.error(`[painel] bot inacessivel em 127.0.0.1:${PORTA_BOT}: ${err.code || err.message}`);
    if (res.headersSent) return res.destroy();
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ erro: `bot fora do ar em 127.0.0.1:${PORTA_BOT}` }));
  });

  req.pipe(upstream);
}

/**
 * Injeta o token do painel na página, para o atendente não ter que digitá-lo.
 *
 * Mesma regra de fallback do backend (`src/internal/auth.ts`): usa PAINEL_TOKEN
 * e, se não houver, INTERNAL_API_TOKEN. Endpoint dinâmico (não é arquivo em
 * disco) porque o valor precisa vir do .env lido em tempo de execução, não do
 * conteúdo estático de data.js.
 *
 * Aviso: isto entrega a credencial para QUALQUER UM que alcance esta porta,
 * já que PAINEL_HOST costuma ser 0.0.0.0 - não só quem abre pelo navegador
 * local. Decisão consciente, pedida explicitamente em troca de não pedir
 * token a cada abertura; ver activity-dashboard/README.md.
 */
function servirTokenAuto(req, res) {
  const token = process.env.PAINEL_TOKEN || process.env.INTERNAL_API_TOKEN || '';
  res.writeHead(200, {
    ...CABECALHOS_SEGURANCA,
    'content-type': 'text/javascript; charset=utf-8',
    'cache-control': 'no-store',
  });
  res.end(`window.PAINEL_TOKEN_AUTO = ${JSON.stringify(token)};`);
}

async function servirArquivo(req, res) {
  // `pathname` só: querystring não faz parte do caminho em disco.
  const caminhoUrl = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const relativo = caminhoUrl.endsWith('/')
    ? caminhoUrl.slice(1) + 'index.html'
    : caminhoUrl.slice(1);

  // `normalize` resolve os `..` ANTES da checagem; sem isso, /../../.env sairia
  // daqui e serviria os segredos do bot.
  const alvo = normalize(join(RAIZ, relativo));
  if (alvo !== RAIZ && !alvo.startsWith(RAIZ + sep)) {
    res.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' });
    return res.end('403');
  }

  try {
    const info = await stat(alvo);
    // /docs -> /docs/ : sem a barra, o navegador resolveria os caminhos
    // relativos da página contra o diretório pai.
    if (info.isDirectory()) {
      res.writeHead(301, { location: caminhoUrl + '/' });
      return res.end();
    }

    res.writeHead(200, {
      ...CABECALHOS_SEGURANCA,
      'content-type': TIPOS[extname(alvo).toLowerCase()] || 'application/octet-stream',
      'content-length': info.size,
      // O painel é lido do disco a cada carga: cache aqui só serve para o
      // atendente ver uma versão antiga depois de um deploy.
      'cache-control': 'no-store',
    });
    if (req.method === 'HEAD') return res.end();
    createReadStream(alvo).pipe(res);
  } catch {
    res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    res.end('404');
  }
}

/**
 * Um arquivo gerado, e não um arquivo em disco: é o único jeito de a página
 * estática saber de uma decisão que vive no .env do servidor. Sem ele, o painel
 * abriria o modal de token mesmo com o token já sendo injetado no proxy.
 *
 * NÃO leva o token - leva só o fato de que não é preciso pedir um. O token
 * nunca chega ao navegador nesse modo, que é metade do ponto de tirá-lo de lá.
 */
function servirConfigDoPainel(req, res, sessao) {
  // `JSON.stringify` e não interpolação de texto: nome de pessoa tem aspas,
  // acento e, um dia, algum caractere que quebraria o script inteiro.
  const config = {
    tokenNoServidor: AUTENTICA_AQUI,
    login: ENTRA.ligado
      ? { ativo: true, nome: sessao?.nome || '', email: sessao?.email || '' }
      : { ativo: false },
  };

  const corpo = `window.PAINEL_SERVIDOR = ${JSON.stringify(config)};
`;

  res.writeHead(200, {
    ...CABECALHOS_SEGURANCA,
    'content-type': 'text/javascript; charset=utf-8',
    'content-length': Buffer.byteLength(corpo),
    'cache-control': 'no-store',
  });

  if (req.method === 'HEAD') return res.end();
  res.end(corpo);
}

/**
 * Pergunta uma vez pelo bot, so para o log.
 *
 * NAO condiciona a subida: o painel serve a pagina sozinho e so precisa do bot
 * na hora de buscar um chamado. Segurar o servidor aqui trocaria "quadro aberto,
 * dizendo o que falta" por "portal que nao abre" - que e pior de diagnosticar e
 * deixa o atendente sem nada.
 *
 * Nao ha retry nem estado aqui: cada requisicao abre a sua propria conexao,
 * entao o quadro volta a mostrar os chamados sozinho quando o bot subir, sem
 * reiniciar este servidor.
 */
function sondarBot() {
  const req = pedirHttp(
    { host: '127.0.0.1', port: PORTA_BOT, path: '/health', method: 'GET', timeout: 2000 },
    (resposta) => {
      resposta.resume();
      if (resposta.statusCode === 200) {
        console.log(`[painel] bot respondendo em 127.0.0.1:${PORTA_BOT}`);
      } else {
        console.warn(`[painel] AVISO: bot respondeu ${resposta.statusCode} em /health`);
      }
    }
  );

  req.on('timeout', () => req.destroy());

  req.on('error', (err) => {
    console.warn(
      `[painel] AVISO: bot fora do ar em 127.0.0.1:${PORTA_BOT} (${err.code || err.message})`
    );
    console.warn('[painel] O painel esta no ar assim mesmo: a pagina abre e o quadro mostra');
    console.warn('[painel] "bot fora do ar" no lugar dos cartoes. Ele volta sozinho quando o');
    console.warn('[painel] bot subir - nao precisa reiniciar este servidor.');
  });

  req.end();
}

/**
 * O portão.
 *
 * Roda ANTES de qualquer coisa, inclusive dos arquivos estáticos — é essa a
 * vantagem de o login viver no servidor e não no navegador. Sem sessão, quem
 * chega não recebe nem o `index.html`.
 *
 * As duas recusas são diferentes de propósito:
 *
 *   - navegação (a página)  -> 302 para o login, que é o que a pessoa espera;
 *   - `/internal/*` (fetch) -> 401 em JSON. Um 302 aqui seria seguido pelo
 *     `fetch`, que receberia o HTML do login com status 200 e tentaria lê-lo
 *     como JSON — o erro apareceria como "resposta inválida", escondendo que
 *     o que houve foi a sessão expirar.
 */
function exigirSessao(req, res) {
  if (!ENTRA.ligado) return true;

  if (req.url === '/auth/entrar' || req.url.startsWith('/auth/entrar?')) {
    const destino = new URL(req.url, ENTRA.urlBase).searchParams.get('destino');
    iniciarLogin(req, res, ENTRA, destino);
    return false;
  }

  if (req.url.startsWith('/auth/retorno')) {
    concluirLogin(req, res, ENTRA, (m) => console.warn(m)).catch((err) => {
      console.error('[painel] falha no retorno do login:', err);
      if (!res.headersSent) res.writeHead(500);
      res.end('500');
    });
    return false;
  }

  if (req.url === '/auth/sair') {
    sairDoPainel(res, ENTRA);
    return false;
  }

  // Toda requisicao autenticada e um sinal de presenca - inclusive a
  // atualizacao automatica do quadro, que e o heartbeat que ja existia.
  const sessaoAtual = sessaoDe(req, ENTRA);
  if (sessaoAtual) {
    registrarAtividade(sessaoAtual);
    return true;
  }

  if (req.url.startsWith('/internal/')) {
    res.writeHead(401, {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      // Marca a origem do 401. O 401 do BOT (token da API errado) chega pelo
      // proxy sem este cabeçalho, e o painel não pode confundir os dois.
      'x-painel-sessao': 'expirada',
    });
    res.end(JSON.stringify({ erro: 'sessão expirada' }));
    return false;
  }

  res.writeHead(302, {
    location: '/auth/entrar?destino=' + encodeURIComponent(req.url),
    'cache-control': 'no-store',
  });
  res.end();
  return false;
}

/**
 * O webhook, e o que vier abaixo dele.
 *
 * Com a Meta era `/webhook` exato. Com a Evolution o segredo vai NO CAMINHO
 * (`/webhook/<segredo>`), então casar só o caminho exato mandaria a Evolution
 * para a tela de login — e o sintoma seria mensagem que nunca chega, sem erro
 * visível em lugar nenhum.
 *
 * Quem decide se o segredo presta é o bot, não este servidor: aqui só se
 * reconhece o prefixo. Segredo errado vira 404 lá, e é o que deve virar.
 */
function ehWebhook(url) {
  return url === '/webhook' || url.startsWith('/webhook?') || url.startsWith('/webhook/');
}

function atender(req, res) {
  // O webhook vem ANTES do portão de sessão, e tem de vir: a Evolution não faz
  // login. Ela se autentica pelo segredo no caminho (ver src/whatsapp/signature.ts),
  // e mandá-la para a tela do Entra daria uma fila de mensagens sumindo sem que
  // nenhum erro aparecesse.
  //
  // Isto existe para o painel e o webhook caberem no MESMO nome DNS: o túnel
  // aponta tudo para esta porta, e o roteamento de caminho acontece aqui. O
  // corpo continua sendo repassado byte a byte por `repassar` - não é mais
  // requisito de assinatura, mas reserializar JSON alheio no meio do caminho
  // não traz vantagem nenhuma e traz risco.
  if (ehWebhook(req.url)) return repassar(req, res, false);

  // /metrics tambem vem antes do portao, e pelo mesmo tipo de motivo que o
  // webhook: quem raspa e o Prometheus, que nao faz login. A autenticacao
  // dele e o token no cabecalho, conferido em painel-metricas.mjs.
  if (req.url === '/metrics') {
    atenderMetricas(req, res, METRICS_TOKEN).then((tratou) => {
      // Sem METRICS_TOKEN configurado, `atenderMetricas` devolve false e a
      // requisicao segue para o portao - virando 302/401, e o alvo aparece
      // como fora do ar no Prometheus.
      if (!tratou && !exigirSessao(req, res)) return;
    });
    return;
  }

  if (!exigirSessao(req, res)) return;

  if (req.url.startsWith('/internal/')) {
    // CSRF: pedido de escrita com Origin de outro site morre aqui, antes do bot.
    // O webhook já passou acima (não chega neste ramo). Ver origemBloqueada().
    if (METODOS_ESCRITA.has(req.method) && origemBloqueada(req)) {
      console.warn(`[painel] escrita recusada: Origin "${req.headers.origin}" nao autorizado`);
      res.writeHead(403, {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'no-store',
      });
      return res.end(JSON.stringify({ erro: 'origem não permitida' }));
    }
    return repassar(req, res);
  }
  if (req.url === '/painel-token.js') return servirTokenAuto(req, res);
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { 'content-type': 'text/plain; charset=utf-8' });
    return res.end('405');
  }
  if (req.url === CAMINHO_CONFIG) {
    return servirConfigDoPainel(req, res, ENTRA.ligado ? sessaoDe(req, ENTRA) : null);
  }
  servirArquivo(req, res).catch((err) => {
    console.error('[painel]', err);
    if (!res.headersSent) res.writeHead(500);
    res.end('500');
  });
}

/**
 * Le o certificado ou a chave A PARTIR DO CAMINHO no .env.
 *
 * A variavel guarda o CAMINHO de um arquivo, nao o conteudo dele. Colar o PEM
 * direto na variavel e o acidente natural, e o erro que saia dai era um ENOENT
 * exibindo um pedaco de base64 como se fosse nome de arquivo - o que manda a
 * pessoa procurar um arquivo inexistente em vez de olhar a variavel.
 *
 * Pior: o .env guarda UMA LINHA. De um PEM colado sobra so a primeira, entao o
 * valor nem seria recuperavel se este codigo tentasse ser esperto e aceitar
 * conteudo. Recusar cedo, dizendo o que fazer, e o unico caminho honesto.
 */
function lerArquivoTls(caminho, nome) {
  // `-----BEGIN` cobre o PEM colado inteiro; o `MI`/`MH` seguido de base64
  // cobre o caso desta vez - o corpo colado sem a linha de cabecalho.
  const pareceConteudo =
    caminho.startsWith('-----BEGIN') || /^M[IH][A-Za-z0-9+/=]{16}/.test(caminho);

  if (pareceConteudo) {
    console.error(`[painel] ERRO: ${nome} tem o CONTEUDO do certificado, nao um caminho.`);
    console.error('[painel]');
    console.error('[painel] Grave o certificado num arquivo e aponte a variavel para ele:');
    console.error(`[painel]   ${nome}=C:\\certificados\\suportebio.crt`);
    console.error('[painel]');
    console.error('[painel] Lembre que o .env guarda uma linha so - de um PEM colado sobra');
    console.error('[painel] apenas a primeira, entao nao ha como aceitar o conteudo aqui.');
    console.error('[painel]');
    console.error('[painel] Com Cloudflare Tunnel ou proxy reverso na frente, o caminho certo');
    console.error('[painel] e deixar PAINEL_TLS_CERT e PAINEL_TLS_KEY VAZIOS: quem fala HTTPS');
    console.error('[painel] com o navegador e o tunel, e este processo serve HTTP na rede local.');
    process.exit(1);
  }

  if (!existsSync(caminho)) {
    console.error(`[painel] ERRO: ${nome} aponta para um arquivo que nao existe:`);
    console.error(`[painel]   ${caminho}`);
    console.error('[painel]');
    console.error('[painel] Confira o caminho. Em .env do Windows a barra invertida vale como');
    console.error('[painel] barra invertida mesmo - nao precisa duplicar.');
    process.exit(1);
  }

  try {
    return readFileSync(caminho);
  } catch (err) {
    console.error(
      `[painel] ERRO: nao foi possivel ler ${nome} (${caminho}): ${err.code || err.message}`
    );
    console.error(
      '[painel] Em geral e permissao: o usuario que roda o painel precisa ler o arquivo.'
    );
    process.exit(1);
  }
}

// Meio par nao sobe em HTTPS por acidente: com so um dos dois preenchido, o
// painel serviria HTTP em silencio, e a unica pista seria o navegador recusando
// o endereco https que ninguem mudou.
if ((TLS_CERT === '') !== (TLS_KEY === '')) {
  const faltando = TLS_CERT === '' ? 'PAINEL_TLS_CERT' : 'PAINEL_TLS_KEY';
  console.error(`[painel] ERRO: falta ${faltando}. Para HTTPS, as DUAS variaveis;`);
  console.error('[painel] para HTTP (tunel/proxy na frente), as duas vazias.');
  process.exit(1);
}

// Identidade da versao e estado do login, para o Grafana. `login_entra_ligado`
// vale 0 quando o painel esta sem login - o que e estado suportado em
// desenvolvimento e incidente em producao, e por isso vira alerta.
registrarBuildInfo(GIT_COMMIT, APP_VERSION);
registrarEstadoDoLogin(ENTRA.ligado);

const usandoTls = TLS_CERT !== '' && TLS_KEY !== '';

const servidor = usandoTls
  ? criarServidorTls(
      {
        cert: lerArquivoTls(TLS_CERT, 'PAINEL_TLS_CERT'),
        key: lerArquivoTls(TLS_KEY, 'PAINEL_TLS_KEY'),
      },
      atender
    )
  : createServer(atender);

servidor.listen(PORTA, HOST, () => {
  const esquema = usandoTls ? 'https' : 'http';

  console.log(`[painel] servindo ${RAIZ}`);
  console.log(`[painel] ${esquema}://localhost:${PORTA}  (escutando em ${HOST}:${PORTA})`);
  console.log(`[painel] /internal/* -> 127.0.0.1:${PORTA_BOT}`);

  if (ENTRA.ligado) {
    console.log(`[painel] login pelo Entra ID, tenant ${ENTRA.tenant}`);
    console.log(`[painel] redirect URI: ${ENTRA.redirect}`);
    console.log('[painel] este endereco precisa estar registrado, IGUAL, no App Registration.');
  } else {
    console.warn('[painel] AVISO: SEM login. Quem alcancar esta porta entra direto.');
    console.warn('[painel] Preencha as variaveis ENTRA_* do .env para exigir conta da empresa.');
  }

  // Servir HTTP com login ligado tem DOIS significados opostos, e o que os
  // separa e o PAINEL_URL_BASE - nao o fato de este processo terminar TLS ou
  // nao. E ele quem decide o atributo Secure do cookie e o redirect_uri que o
  // Entra recebe.
  //
  //   base https  -> quem faz TLS e o tunel/proxy na frente. Arranjo NORMAL e
  //                  correto: o cookie sai com Secure e o redirect e https.
  //   base http   -> nao ha TLS em lugar nenhum. So funciona em localhost, que
  //                  e a unica origem http que o Entra aceita e que o navegador
  //                  trata como segura para cookie Secure.
  if (!usandoTls && ENTRA.ligado) {
    if (ENTRA.seguro) {
      console.log('[painel] TLS por conta do tunel/proxy na frente: este processo serve HTTP');
      console.log('[painel] na porta acima, e o cookie de sessao sai com Secure porque o');
      console.log('[painel] PAINEL_URL_BASE e https. Nada mais a configurar aqui.');
      console.log('[painel] Abrir o painel direto por http, fora de localhost, NAO vai logar:');
      console.log('[painel] o navegador nao devolve cookie Secure. Use sempre o dominio.');
    } else {
      console.warn('[painel] AVISO: login ligado, e nao ha TLS em lugar nenhum -');
      console.warn('[painel] PAINEL_URL_BASE nao comeca com https. Fora de localhost o');
      console.warn('[painel] Entra recusa o redirect_uri e o login nao vai funcionar.');
    }
  }

  if (AUTENTICA_AQUI && ENTRA.ligado) {
    console.log('[painel] token da API injetado aqui, para quem ja passou pelo login.');
  } else if (AUTENTICA_AQUI) {
    console.log('[painel] token no servidor: o painel abre SEM pedir token.');
    console.log('[painel] Quem alcancar esta porta le e altera chamado - deixe-a');
    console.log('[painel] restrita a rede interna ou atras de VPN.');
  } else if (TOKEN_NO_SERVIDOR) {
    console.warn('[painel] AVISO: PAINEL_TOKEN_NO_SERVIDOR esta ligado, mas nao ha');
    console.warn('[painel] PAINEL_TOKEN nem INTERNAL_API_TOKEN no .env - nao ha o que');
    console.warn('[painel] injetar. O painel vai continuar pedindo o token no navegador.');
  }

  sondarBot();
});
