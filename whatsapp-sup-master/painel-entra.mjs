/**
 * Login do painel pelo Microsoft Entra ID.
 *
 * O fluxo é o authorization code com PKCE, e ele acontece INTEIRO no servidor:
 * o navegador nunca recebe token nenhum, só um cookie de sessão assinado e
 * HttpOnly. Isso é o que faz a proteção cobrir também os arquivos estáticos —
 * num login feito no navegador, o `index.html` e o `app.js` continuariam
 * abertos para quem alcançasse a porta, e só as chamadas de API estariam
 * guardadas.
 *
 * Quem pode entrar NÃO se decide aqui. Isso é atribuição do App Registration no
 * Entra ("Assignment required" + atribuir a equipe). Uma segunda lista neste
 * arquivo seria uma cópia para divergir da primeira. O que este módulo faz é
 * traduzir a recusa do Entra numa frase que o atendente entenda.
 *
 * Sem dependências: só a biblioteca padrão do Node, como o resto do painel.
 */
import {
  createHash,
  createHmac,
  createPublicKey,
  randomBytes,
  timingSafeEqual,
  verify as verificarAssinatura,
} from 'node:crypto';

const AUTORIDADE = 'https://login.microsoftonline.com';

const COOKIE_SESSAO = 'painel_sessao';
const COOKIE_TRANSACAO = 'painel_login';

// Uma transação de login (o ida-e-volta até o Entra) que passe disto é gente
// que abriu a tela de senha e foi almoçar. Recomeçar é um clique.
const TRANSACAO_SEGUNDOS = 600;

const ESCOPO = 'openid profile email';

/* ------------------------------------------------------------------ *
 *  Configuração
 * ------------------------------------------------------------------ */

/**
 * Lê o .env e decide se o login está ligado.
 *
 * Três estados, e a diferença entre os dois últimos é o ponto:
 *
 *   - NADA configurado  -> login desligado, o painel abre como antes. É o que
 *     permite instalar a versão nova antes de ter o App Registration pronto.
 *   - TUDO configurado  -> login exigido.
 *   - METADE configurada -> erro fatal. Subir sem login porque faltou uma
 *     variável seria o pior dos três: alguém pediu proteção, não recebeu, e
 *     nada avisou.
 */
export function lerConfigEntra(env) {
  // Estas quatro são a CHAVE DE LIGA/DESLIGA: nenhuma preenchida significa
  // "sem login". O segredo de sessão fica de fora dessa conta de propósito -
  // ele já vem gerado no .env e não é credencial do Entra, então tê-lo ali
  // sozinho não pode significar que alguém tentou ligar o login.
  const bruto = {
    ENTRA_TENANT_ID: (env.ENTRA_TENANT_ID || '').trim(),
    ENTRA_CLIENT_ID: (env.ENTRA_CLIENT_ID || '').trim(),
    ENTRA_CLIENT_SECRET: (env.ENTRA_CLIENT_SECRET || '').trim(),
    PAINEL_URL_BASE: (env.PAINEL_URL_BASE || '').trim(),
  };

  const segredoSessao = (env.PAINEL_SESSAO_SEGREDO || '').trim();

  const nomes = Object.keys(bruto);
  const preenchidas = nomes.filter((n) => bruto[n] !== '');

  if (preenchidas.length === 0) return { ligado: false, faltando: [] };

  // Com o login pedido, o segredo passa a ser obrigatório: sem ele não há como
  // assinar o cookie, e uma sessão que qualquer um pudesse forjar seria pior
  // que não ter login nenhum. Gerar um na hora também não serve - a cada
  // reinício todo mundo seria deslogado, sem explicação.
  const faltando = nomes.filter((n) => bruto[n] === '');
  if (segredoSessao === '') faltando.push('PAINEL_SESSAO_SEGREDO');
  if (faltando.length > 0) return { ligado: false, faltando };

  const tenant = bruto.ENTRA_TENANT_ID;
  // Sem a barra final, para `urlBase + '/auth/retorno'` não virar barra dupla —
  // e redirect_uri no Entra é comparado caractere a caractere.
  const urlBase = bruto.PAINEL_URL_BASE.replace(/\/+$/, '');

  const horas = Number(env.PAINEL_SESSAO_HORAS || 8);

  return {
    ligado: true,
    faltando: [],
    tenant,
    cliente: bruto.ENTRA_CLIENT_ID,
    segredoCliente: bruto.ENTRA_CLIENT_SECRET,
    segredoSessao,
    urlBase,
    redirect: urlBase + '/auth/retorno',
    sessaoSegundos: (Number.isFinite(horas) && horas > 0 ? horas : 8) * 3600,
    // `https` no urlBase é o que decide o atributo Secure do cookie. O Entra só
    // aceita redirect_uri http em localhost, então na prática isto é sempre
    // true fora da máquina de desenvolvimento.
    seguro: urlBase.startsWith('https://'),
    autorizar: `${AUTORIDADE}/${tenant}/oauth2/v2.0/authorize`,
    token: `${AUTORIDADE}/${tenant}/oauth2/v2.0/token`,
    sair: `${AUTORIDADE}/${tenant}/oauth2/v2.0/logout`,
    jwks: `${AUTORIDADE}/${tenant}/discovery/v2.0/keys`,
    emissor: `${AUTORIDADE}/${tenant}/v2.0`,
  };
}

/* ------------------------------------------------------------------ *
 *  Cookies e assinatura
 * ------------------------------------------------------------------ */

export function lerCookies(req) {
  const fora = {};
  for (const parte of (req.headers.cookie || '').split(';')) {
    const i = parte.indexOf('=');
    if (i < 0) continue;
    const nome = parte.slice(0, i).trim();
    if (!nome) continue;
    try {
      fora[nome] = decodeURIComponent(parte.slice(i + 1).trim());
    } catch {
      // Cookie com percent-encoding quebrado: ignorar é melhor que derrubar a
      // requisição inteira por causa de um valor que nem é nosso.
    }
  }
  return fora;
}

function montarCookie(nome, valor, cfg, segundos) {
  const partes = [
    `${nome}=${encodeURIComponent(valor)}`,
    'Path=/',
    'HttpOnly',
    // Lax, e não Strict: o retorno do Entra é uma navegação vinda de outro site,
    // e com Strict o cookie da transação não seria mandado justamente na
    // requisição que precisa dele. Lax cobre isso porque o retorno é um GET.
    'SameSite=Lax',
    `Max-Age=${segundos}`,
  ];
  if (cfg.seguro) partes.push('Secure');
  return partes.join('; ');
}

function apagarCookie(nome, cfg) {
  const partes = [`${nome}=`, 'Path=/', 'HttpOnly', 'SameSite=Lax', 'Max-Age=0'];
  if (cfg.seguro) partes.push('Secure');
  return partes.join('; ');
}

/**
 * Assina um objeto com HMAC-SHA256 e devolve `corpo.assinatura`.
 *
 * Não é criptografia: o conteúdo é legível por quem tiver o cookie. Isso está
 * certo — o que ele guarda é nome e e-mail de quem já está olhando a própria
 * tela. A assinatura existe para o valor não poder ser FORJADO, que é o que
 * importaria.
 */
function assinar(dados, segredo) {
  const corpo = Buffer.from(JSON.stringify(dados), 'utf8').toString('base64url');
  const mac = createHmac('sha256', segredo).update(corpo).digest('base64url');
  return `${corpo}.${mac}`;
}

function abrirAssinado(valor, segredo) {
  if (typeof valor !== 'string') return null;

  const corte = valor.lastIndexOf('.');
  if (corte <= 0) return null;

  const corpo = valor.slice(0, corte);
  const mac = Buffer.from(valor.slice(corte + 1));
  const esperado = Buffer.from(createHmac('sha256', segredo).update(corpo).digest('base64url'));

  // `timingSafeEqual` exige o mesmo tamanho; comparar antes evita a exceção e
  // não vaza nada, porque o tamanho da assinatura é fixo e público.
  if (mac.length !== esperado.length || !timingSafeEqual(mac, esperado)) return null;

  try {
    const dados = JSON.parse(Buffer.from(corpo, 'base64url').toString('utf8'));
    if (typeof dados.exp !== 'number' || dados.exp * 1000 <= Date.now()) return null;
    return dados;
  } catch {
    return null;
  }
}

/** A sessão de quem está pedindo, ou `null`. */
export function sessaoDe(req, cfg) {
  return abrirAssinado(lerCookies(req)[COOKIE_SESSAO], cfg.segredoSessao);
}

/* ------------------------------------------------------------------ *
 *  Validação do id_token
 * ------------------------------------------------------------------ */

// As chaves públicas do tenant, por `kid`. Elas giram, então o cache tem prazo -
// e um `kid` desconhecido força uma releitura, com piso de tempo para um token
// forjado com `kid` aleatório não virar uma enxurrada de requisições ao Entra.
const chaves = new Map();
let chavesLidasEm = 0;
const CACHE_CHAVES_MS = 60 * 60 * 1000;
const PISO_RELEITURA_MS = 60 * 1000;

async function buscarChaves(cfg) {
  const resposta = await fetch(cfg.jwks, { signal: AbortSignal.timeout(10_000) });
  if (!resposta.ok) throw new Error(`JWKS respondeu ${resposta.status}`);

  const { keys } = await resposta.json();
  chaves.clear();
  for (const jwk of keys || []) {
    if (jwk.kid) chaves.set(jwk.kid, jwk);
  }
  chavesLidasEm = Date.now();
}

async function chavePara(kid, cfg) {
  const velho = Date.now() - chavesLidasEm > CACHE_CHAVES_MS;
  if (chaves.size === 0 || velho) await buscarChaves(cfg);

  if (!chaves.has(kid) && Date.now() - chavesLidasEm > PISO_RELEITURA_MS) {
    await buscarChaves(cfg);
  }

  return chaves.get(kid) || null;
}

function pedacos(jwt) {
  const partes = String(jwt).split('.');
  if (partes.length !== 3) throw new Error('id_token malformado');

  const ler = (p) => JSON.parse(Buffer.from(p, 'base64url').toString('utf8'));
  return { cabecalho: ler(partes[0]), corpo: ler(partes[1]), partes };
}

/**
 * Confere assinatura e claims do id_token.
 *
 * A assinatura é verificada mesmo o token tendo chegado por uma conexão TLS
 * direta com o endpoint de token — situação em que o OIDC Core (§3.1.3.7) deixa
 * pular essa checagem. Custa uma leitura de JWKS em cache e fecha a porta caso
 * este código um dia passe a receber o token por outro caminho.
 */
export async function validarIdToken(idToken, cfg, nonceEsperado) {
  const { cabecalho, corpo, partes } = pedacos(idToken);

  if (cabecalho.alg !== 'RS256') {
    throw new Error(`algoritmo inesperado no id_token: ${cabecalho.alg}`);
  }

  const jwk = await chavePara(cabecalho.kid, cfg);
  if (!jwk) throw new Error(`o tenant não publica a chave ${cabecalho.kid}`);

  const assinado = Buffer.from(`${partes[0]}.${partes[1]}`, 'utf8');
  const assinatura = Buffer.from(partes[2], 'base64url');
  const chave = createPublicKey({ key: jwk, format: 'jwk' });

  if (!verificarAssinatura('RSA-SHA256', assinado, chave, assinatura)) {
    throw new Error('assinatura do id_token não confere');
  }

  // `iss` e `tid` juntos: é o que amarra o token AO SEU tenant. Sem eles, um
  // token legítimo de outra organização passaria por todo o resto.
  if (corpo.iss !== cfg.emissor) throw new Error(`emissor inesperado: ${corpo.iss}`);
  if (corpo.tid !== cfg.tenant) throw new Error(`tenant inesperado: ${corpo.tid}`);
  if (corpo.aud !== cfg.cliente) throw new Error('o token foi emitido para outro aplicativo');

  const agora = Math.floor(Date.now() / 1000);
  // 5 minutos de folga, o padrão de fato para relógio de servidor fora de sincronia.
  if (typeof corpo.exp !== 'number' || corpo.exp + 300 < agora)
    throw new Error('id_token expirado');
  if (typeof corpo.nbf === 'number' && corpo.nbf - 300 > agora)
    throw new Error('id_token ainda não vale');

  // O nonce é o que impede alguém replayar um id_token capturado noutro login.
  if (corpo.nonce !== nonceEsperado) throw new Error('nonce não confere');

  return corpo;
}

/* ------------------------------------------------------------------ *
 *  As três rotas
 * ------------------------------------------------------------------ */

/**
 * Só caminho interno vira destino pós-login.
 *
 * Sem isto, `/auth/entrar?destino=https://sitedele` faria o painel devolver a
 * pessoa, já autenticada, para um site de terceiro — o open redirect clássico.
 * `//host` é recusado junto porque o navegador o lê como protocolo relativo.
 */
function destinoSeguro(bruto) {
  if (typeof bruto !== 'string' || !bruto.startsWith('/') || bruto.startsWith('//')) return '/';
  return bruto;
}

export function iniciarLogin(req, res, cfg, destino) {
  const verificador = randomBytes(32).toString('base64url');
  const desafio = createHash('sha256').update(verificador).digest('base64url');

  const transacao = {
    estado: randomBytes(16).toString('base64url'),
    nonce: randomBytes(16).toString('base64url'),
    verificador,
    destino: destinoSeguro(destino),
    exp: Math.floor(Date.now() / 1000) + TRANSACAO_SEGUNDOS,
  };

  const url = new URL(cfg.autorizar);
  url.searchParams.set('client_id', cfg.cliente);
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('redirect_uri', cfg.redirect);
  // `query` e não `form_post`: o retorno vira um GET, e um GET carrega o cookie
  // SameSite=Lax da transação. Com form_post o cookie não viria e o login
  // falharia sempre, de um jeito difícil de ler.
  url.searchParams.set('response_mode', 'query');
  url.searchParams.set('scope', ESCOPO);
  url.searchParams.set('state', transacao.estado);
  url.searchParams.set('nonce', transacao.nonce);
  url.searchParams.set('code_challenge', desafio);
  url.searchParams.set('code_challenge_method', 'S256');

  res.writeHead(302, {
    'set-cookie': montarCookie(
      COOKIE_TRANSACAO,
      assinar(transacao, cfg.segredoSessao),
      cfg,
      TRANSACAO_SEGUNDOS
    ),
    location: url.toString(),
    'cache-control': 'no-store',
  });
  res.end();
}

export async function concluirLogin(req, res, cfg, log) {
  const url = new URL(req.url, cfg.urlBase);
  const limpar = apagarCookie(COOKIE_TRANSACAO, cfg);

  // O Entra recusou antes mesmo de emitir código. O caso de longe mais comum é
  // AADSTS50105: a conta existe, mas não está atribuída ao aplicativo.
  const erro = url.searchParams.get('error');
  if (erro) {
    const descricao = url.searchParams.get('error_description') || '';
    log?.(`[painel] login recusado pelo Entra: ${erro} ${descricao.split('\n')[0]}`);
    return paginaDeErro(res, limpar, tituloDaRecusa(erro, descricao), descricao.split('\n')[0]);
  }

  const transacao = abrirAssinado(lerCookies(req)[COOKIE_TRANSACAO], cfg.segredoSessao);
  if (!transacao) {
    return paginaDeErro(
      res,
      limpar,
      'A tentativa de login expirou',
      'A ida até a Microsoft demorou demais, ou esta aba não é a que começou o login. Tente de novo.'
    );
  }

  // O state é o que amarra o retorno À ida: sem conferi-lo, um atacante poderia
  // fazer o navegador de alguém concluir um login que não foi essa pessoa quem
  // começou (CSRF de login).
  if (url.searchParams.get('state') !== transacao.estado) {
    log?.('[painel] login recusado: state nao confere');
    return paginaDeErro(
      res,
      limpar,
      'Login inválido',
      'O retorno não corresponde ao pedido de login.'
    );
  }

  const codigo = url.searchParams.get('code');
  if (!codigo) {
    return paginaDeErro(
      res,
      limpar,
      'Login inválido',
      'A Microsoft não devolveu o código de autorização.'
    );
  }

  let identidade;
  try {
    const resposta = await fetch(cfg.token, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: cfg.cliente,
        client_secret: cfg.segredoCliente,
        grant_type: 'authorization_code',
        code: codigo,
        redirect_uri: cfg.redirect,
        code_verifier: transacao.verificador,
        scope: ESCOPO,
      }),
      signal: AbortSignal.timeout(15_000),
    });

    const dados = await resposta.json();
    if (!resposta.ok) {
      // `error_description` da Microsoft traz o código AADSTS, que é o que
      // resolve o problema. O log leva; a tela, não - ela é lida por quem só
      // quer entrar.
      log?.(
        `[painel] troca de codigo falhou: ${dados.error} ${(dados.error_description || '').split('\n')[0]}`
      );
      return paginaDeErro(
        res,
        limpar,
        'Não foi possível concluir o login',
        'A Microsoft recusou a troca do código. O motivo está no log do painel.'
      );
    }

    identidade = await validarIdToken(dados.id_token, cfg, transacao.nonce);
  } catch (err) {
    log?.(`[painel] login falhou: ${err.message}`);
    return paginaDeErro(
      res,
      limpar,
      'Não foi possível concluir o login',
      'Houve uma falha ao validar a resposta da Microsoft. O motivo está no log do painel.'
    );
  }

  const sessao = {
    // `oid` é o identificador estável da pessoa no diretório: e-mail e nome
    // mudam, ele não. É por ele que se casa a sessão com qualquer coisa que um
    // dia venha a ser gravada por usuário.
    oid: identidade.oid,
    nome: identidade.name || identidade.preferred_username || '',
    email: identidade.preferred_username || identidade.email || '',
    exp: Math.floor(Date.now() / 1000) + cfg.sessaoSegundos,
  };

  log?.(`[painel] login: ${sessao.email}`);

  // O perfil de quem entrou nasce AQUI, no servidor, com a identidade que
  // acabou de ser validada contra as chaves do tenant.
  //
  // `await` de propósito, e não fogo-e-esquece: o destino do 302 é o quadro, que
  // pede a lista de pessoas na primeira carga. Sem esperar, o primeiro login
  // ainda mostraria o seletor de "Responsável" vazio, e a pessoa só apareceria
  // no refresh seguinte - exatamente o sintoma que isto vem corrigir.
  //
  // O `try` é AQUI, e não só dentro de quem registra: cadastro de exibição
  // incompleto é um incômodo, "não consigo entrar no painel" é uma parada de
  // trabalho. Confiar no try/catch do outro lado deixaria essa diferença
  // depender de disciplina de quem injeta a função - e este arquivo não tem
  // como garantir isso.
  try {
    await cfg.registrarPerfil?.(sessao);
  } catch (err) {
    log?.(`[painel] perfil de ${sessao.email} nao registrado: ${err.message}`);
  }

  res.writeHead(302, {
    'set-cookie': [
      limpar,
      montarCookie(COOKIE_SESSAO, assinar(sessao, cfg.segredoSessao), cfg, cfg.sessaoSegundos),
    ],
    location: transacao.destino,
    'cache-control': 'no-store',
  });
  res.end();
}

/**
 * Encerra a sessão aqui E na Microsoft.
 *
 * Só apagar o cookie daqui deixaria o próximo clique em "entrar" passar direto,
 * sem pedir nada — a sessão do navegador com o Entra continua de pé. Numa
 * máquina compartilhada, isso é o oposto de sair.
 */
export function sairDoPainel(res, cfg) {
  const url = new URL(cfg.sair);
  url.searchParams.set('post_logout_redirect_uri', cfg.urlBase + '/');

  res.writeHead(302, {
    'set-cookie': apagarCookie(COOKIE_SESSAO, cfg),
    location: url.toString(),
    'cache-control': 'no-store',
  });
  res.end();
}

/* ------------------------------------------------------------------ *
 *  Telas
 * ------------------------------------------------------------------ */

function tituloDaRecusa(erro, descricao) {
  if (descricao.includes('AADSTS50105')) return 'Sua conta não tem acesso ao painel';
  if (erro === 'access_denied') return 'Acesso negado';
  return 'Não foi possível entrar';
}

function paginaDeErro(res, cookieParaLimpar, titulo, detalhe) {
  const ehAtribuicao = titulo.startsWith('Sua conta não tem acesso');
  const ajuda = ehAtribuicao
    ? 'Peça à equipe de TI para atribuir a sua conta ao aplicativo do painel no Microsoft Entra ID.'
    : 'Se continuar acontecendo, avise a equipe de TI.';

  const html = `<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de chamados</title>
<style>
  /* Mesma paleta do painel (activity-dashboard/styles.css), com os valores
     cravados: esta página é servida ANTES de qualquer sessão existir, e não
     pode depender de um arquivo que fica atrás do portão de login.

     Aqui só existe prefers-color-scheme, e não o data-theme do painel: quem
     cai nesta tela não passou pelo tema.js, então a escolha salva no navegador
     não está disponível. Seguir o sistema é o mais perto do certo que dá para
     chegar sem script.

     (Sem crases neste comentário de propósito: ele mora dentro de um template
     literal, e uma crase aqui fecharia a string no meio do CSS.) */
  :root { color-scheme: light dark; }
  body { margin:0; min-height:100vh; display:grid; place-items:center;
         font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
         background:#EEF1F5; color:#593115; }
  .cartao { background:#fff; padding:32px; border-radius:8px; max-width:420px;
            box-shadow:0 1px 3px rgba(89,49,21,.18); }
  h1 { font-size:18px; margin:0 0 12px; }
  p { margin:0 0 12px; color:#4A5461; }
  .detalhe { font-size:12px; color:#667180; word-break:break-word; }
  a { display:inline-block; margin-top:8px; padding:8px 16px; border-radius:4px;
      background:#02542A; color:#fff; text-decoration:none; }
  @media (prefers-color-scheme: dark) {
    body { background:#17140F; color:#F1E9DF; }
    .cartao { background:#211D17; box-shadow:0 1px 3px rgba(0,0,0,.5); }
    p { color:#C8BFB2; }
    .detalhe { color:#A79F92; }
    a { background:#1E7D49; }
  }
</style>
<div class="cartao">
  <h1>${escaparHtml(titulo)}</h1>
  <p>${escaparHtml(ajuda)}</p>
  <p class="detalhe">${escaparHtml(detalhe || '')}</p>
  <a href="/auth/entrar">Tentar de novo</a>
</div>
</html>`;

  res.writeHead(403, {
    'content-type': 'text/html; charset=utf-8',
    'content-length': Buffer.byteLength(html),
    'set-cookie': cookieParaLimpar,
    'cache-control': 'no-store',
  });
  res.end(html);
}

const ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

function escaparHtml(texto) {
  return String(texto).replace(/[&<>"']/g, (c) => ESCAPES[c]);
}
