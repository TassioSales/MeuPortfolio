/**
 * Login pelo Entra ID: o portão de configuração e a validação do id_token.
 *
 * Roda offline. O par RSA é gerado aqui, a chave pública é publicada num JWKS
 * de mentira e os tokens são assinados à mão — nada toca o Entra de verdade.
 *
 * Fica em `.mjs`, e não em `.ts` como o resto da suíte, porque o alvo
 * (`painel-entra.mjs`) é ESM na raiz e o build dos testes é CommonJS: um
 * `import()` compilado pelo tsc viraria `require()` e não carregaria o módulo.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { generateKeyPairSync, createSign, createHmac } from 'node:crypto';

import { concluirLogin, lerConfigEntra, validarIdToken, sessaoDe } from '../painel-entra.mjs';

const TENANT = '11111111-2222-3333-4444-555555555555';
const CLIENTE = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
const SEGREDO_SESSAO = 'x'.repeat(64);
const KID = 'chave-de-teste';

const ENV_COMPLETO = {
  ENTRA_TENANT_ID: TENANT,
  ENTRA_CLIENT_ID: CLIENTE,
  ENTRA_CLIENT_SECRET: 'segredo',
  PAINEL_URL_BASE: 'https://painel.exemplo.local:8512/',
  PAINEL_SESSAO_SEGREDO: SEGREDO_SESSAO,
};

// --- o portão de configuração -------------------------------------------

test('sem nenhuma variável do Entra o login fica desligado', () => {
  const cfg = lerConfigEntra({});
  assert.equal(cfg.ligado, false);
  assert.deepEqual(cfg.faltando, []);
});

test('regressão: só o segredo de sessão preenchido NÃO tenta ligar o login', () => {
  // O segredo já vem gerado no .env e não é credencial do Entra. Se ele
  // contasse como "alguém pediu login", o painel morreria ao subir sem App
  // Registration — que é o estado normal de quem ainda não configurou nada.
  const cfg = lerConfigEntra({ PAINEL_SESSAO_SEGREDO: SEGREDO_SESSAO });
  assert.equal(cfg.ligado, false);
  assert.deepEqual(cfg.faltando, []);
});

test('configuração pela metade não sobe sem login: acusa o que falta', () => {
  const cfg = lerConfigEntra({ ...ENV_COMPLETO, ENTRA_CLIENT_SECRET: '' });
  assert.equal(cfg.ligado, false);
  assert.deepEqual(cfg.faltando, ['ENTRA_CLIENT_SECRET']);
});

test('credenciais completas sem segredo de sessão também é configuração pela metade', () => {
  const cfg = lerConfigEntra({ ...ENV_COMPLETO, PAINEL_SESSAO_SEGREDO: '' });
  assert.equal(cfg.ligado, false);
  assert.deepEqual(cfg.faltando, ['PAINEL_SESSAO_SEGREDO']);
});

test('configuração completa liga o login e monta as URLs do tenant', () => {
  const cfg = lerConfigEntra(ENV_COMPLETO);
  assert.equal(cfg.ligado, true);
  // A barra final do PAINEL_URL_BASE não pode virar barra dupla: o Entra
  // compara o redirect_uri caractere a caractere.
  assert.equal(cfg.redirect, 'https://painel.exemplo.local:8512/auth/retorno');
  assert.equal(cfg.emissor, `https://login.microsoftonline.com/${TENANT}/v2.0`);
  assert.equal(cfg.seguro, true);
  assert.equal(cfg.sessaoSegundos, 8 * 3600);
});

test('PAINEL_SESSAO_HORAS inválido cai no padrão de 8 horas', () => {
  for (const horas of ['abc', '0', '-3', '']) {
    const cfg = lerConfigEntra({ ...ENV_COMPLETO, PAINEL_SESSAO_HORAS: horas });
    assert.equal(cfg.sessaoSegundos, 8 * 3600, `horas: ${horas}`);
  }
});

// --- cookie de sessão ----------------------------------------------------

const cfg = lerConfigEntra(ENV_COMPLETO);

const comCookie = (valor) => ({ headers: { cookie: `painel_sessao=${valor}` } });

const cookieAssinado = (dados, segredo = SEGREDO_SESSAO) => {
  const corpo = Buffer.from(JSON.stringify(dados), 'utf8').toString('base64url');
  return `${corpo}.${createHmac('sha256', segredo).update(corpo).digest('base64url')}`;
};

const sessaoValida = () => ({
  nome: 'Natan Ferreira',
  email: 'natan.ferreira@biomundo.com.br',
  exp: Math.floor(Date.now() / 1000) + 3600,
});

test('cookie de sessão assinado com o segredo certo é aceito', () => {
  const sessao = sessaoDe(comCookie(cookieAssinado(sessaoValida())), cfg);
  assert.equal(sessao.email, 'natan.ferreira@biomundo.com.br');
});

test('cookie de sessão forjado é recusado', () => {
  // O conteúdo é legível de propósito; o que não pode é ser inventado.
  assert.equal(sessaoDe(comCookie(cookieAssinado(sessaoValida(), 'outro-segredo')), cfg), null);

  const corpo = Buffer.from(JSON.stringify(sessaoValida()), 'utf8').toString('base64url');
  assert.equal(sessaoDe(comCookie(`${corpo}.assinatura-inventada`), cfg), null);
  assert.equal(sessaoDe(comCookie(corpo), cfg), null);
});

test('cookie de sessão vencido é recusado mesmo com assinatura boa', () => {
  const vencida = { ...sessaoValida(), exp: Math.floor(Date.now() / 1000) - 60 };
  assert.equal(sessaoDe(comCookie(cookieAssinado(vencida)), cfg), null);
});

test('sem cookie nenhum não há sessão', () => {
  assert.equal(sessaoDe({ headers: {} }, cfg), null);
});

// --- validação do id_token ----------------------------------------------

const { publicKey, privateKey } = generateKeyPairSync('rsa', { modulusLength: 2048 });
const jwk = { ...publicKey.export({ format: 'jwk' }), kid: KID, alg: 'RS256', use: 'sig' };

// O módulo busca o JWKS com `fetch`; trocá-lo aqui é o que torna o teste
// offline. Cada arquivo de teste roda em processo próprio, então o global
// substituído não escapa daqui.
let chamadasAoJwks = 0;

// O endpoint de token só é usado pelo teste do `concluirLogin`, mais abaixo;
// enquanto for `null`, qualquer chamada a ele é erro de teste.
let respostaDoToken = null;

globalThis.fetch = async (url) => {
  if (respostaDoToken && String(url) === cfg.token) return respostaDoToken();

  assert.equal(String(url), cfg.jwks, 'o módulo buscou chaves fora do tenant');
  chamadasAoJwks++;
  return { ok: true, status: 200, json: async () => ({ keys: [jwk] }) };
};

const b64 = (o) => Buffer.from(JSON.stringify(o), 'utf8').toString('base64url');
const NONCE = 'nonce-desta-transacao';
const agora = () => Math.floor(Date.now() / 1000);

function assinarToken(corpo, opcoes = {}) {
  const cabecalho = { alg: opcoes.alg || 'RS256', kid: opcoes.kid || KID, typ: 'JWT' };
  const base = `${b64(cabecalho)}.${b64(corpo)}`;
  if (opcoes.assinaturaRuim) {
    return `${base}.${Buffer.from('nao-e-assinatura').toString('base64url')}`;
  }
  const rubrica = createSign('RSA-SHA256').update(base).end().sign(privateKey);
  return `${base}.${rubrica.toString('base64url')}`;
}

function corpoValido(extra = {}) {
  const t = agora();
  return {
    iss: cfg.emissor,
    tid: TENANT,
    aud: CLIENTE,
    oid: '99999999-8888-7777-6666-555555555555',
    name: 'Natan Ferreira',
    preferred_username: 'natan.ferreira@biomundo.com.br',
    nonce: NONCE,
    iat: t,
    nbf: t,
    exp: t + 3600,
    ...extra,
  };
}

const deveRecusar = (nome, corpo, opcoes = {}, nonce = NONCE) =>
  test(nome, async () => {
    await assert.rejects(() => validarIdToken(assinarToken(corpo, opcoes), cfg, nonce));
  });

test('id_token legítimo é aceito e devolve quem entrou', async () => {
  const claims = await validarIdToken(assinarToken(corpoValido()), cfg, NONCE);
  assert.equal(claims.name, 'Natan Ferreira');
  assert.equal(claims.preferred_username, 'natan.ferreira@biomundo.com.br');
});

deveRecusar('id_token com assinatura adulterada é recusado', corpoValido(), {
  assinaturaRuim: true,
});
deveRecusar('id_token com alg none é recusado (troca de algoritmo)', corpoValido(), {
  alg: 'none',
});
deveRecusar('id_token com kid que o tenant não publica é recusado', corpoValido(), {
  kid: 'outra-chave',
});
deveRecusar(
  'id_token de outro tenant no iss é recusado',
  corpoValido({ iss: 'https://login.microsoftonline.com/outro/v2.0' })
);
deveRecusar('id_token de outro tenant no tid é recusado', corpoValido({ tid: 'outro-tenant' }));
deveRecusar(
  'id_token emitido para outro aplicativo é recusado',
  corpoValido({ aud: 'app-de-terceiro' })
);
deveRecusar('id_token expirado é recusado', corpoValido({ exp: agora() - 3600 }));
deveRecusar('id_token que ainda não vale é recusado', corpoValido({ nbf: agora() + 3600 }));
deveRecusar(
  'replay: id_token com nonce de outro login é recusado',
  corpoValido({ nonce: 'nonce-antigo' })
);
deveRecusar('id_token sem nonce é recusado', corpoValido({ nonce: undefined }));

// --- o fim do login: o perfil de quem entrou ----------------------------
//
// O login é o ÚNICO lugar que cria perfil de atendente. Se ele não chamar o
// registro, o cadastro de Pessoas fica vazio para sempre - e foi exatamente
// esse o sintoma relatado: duas pessoas já tinham entrado e nenhuma aparecia.
//
// O `?.` em `cfg.registrarPerfil?.(sessao)` é o que torna este teste
// necessário: se um dia a ligação em servidor-painel.mjs se desfizer, nada
// falha, nada avisa, e a lista simplesmente volta a ficar vazia.

const ESTADO = 'estado-desta-transacao';

function transacaoValida() {
  return cookieAssinado({
    estado: ESTADO,
    nonce: NONCE,
    verificador: 'verificador-pkce-desta-transacao',
    destino: '/',
    exp: agora() + 600,
  });
}

/** `res` de mentira: guarda o que o módulo escreveria na resposta. */
function respostaFalsa() {
  return {
    status: null,
    cabecalhos: null,
    corpo: '',
    writeHead(status, cabecalhos) {
      this.status = status;
      this.cabecalhos = cabecalhos;
    },
    end(corpo = '') {
      this.corpo += corpo;
    },
  };
}

function pedidoDeRetorno() {
  return {
    url: `/auth/retorno?code=codigo-de-teste&state=${encodeURIComponent(ESTADO)}`,
    headers: { cookie: `painel_login=${transacaoValida()}` },
  };
}

test('login concluído registra o perfil de quem entrou', async () => {
  respostaDoToken = () => ({
    ok: true,
    status: 200,
    json: async () => ({ id_token: assinarToken(corpoValido()) }),
  });

  const registrados = [];
  const res = respostaFalsa();
  await concluirLogin(
    pedidoDeRetorno(),
    res,
    { ...cfg, registrarPerfil: (s) => registrados.push(s) },
    () => {}
  );

  assert.equal(res.status, 302, `esperava redirecionamento, veio ${res.status}: ${res.corpo}`);
  assert.equal(registrados.length, 1, 'o login não registrou o perfil');

  // Os três campos que a rota de identidade usa. `oid` é o que amarra a pessoa
  // ao diretório; sem ele, todo login criaria um perfil novo.
  assert.equal(registrados[0].oid, '99999999-8888-7777-6666-555555555555');
  assert.equal(registrados[0].nome, 'Natan Ferreira');
  assert.equal(registrados[0].email, 'natan.ferreira@biomundo.com.br');

  respostaDoToken = null;
});

test('bot fora do ar não impede o login', async () => {
  respostaDoToken = () => ({
    ok: true,
    status: 200,
    json: async () => ({ id_token: assinarToken(corpoValido()) }),
  });

  const res = respostaFalsa();
  await concluirLogin(
    pedidoDeRetorno(),
    res,
    {
      ...cfg,
      registrarPerfil: async () => {
        throw new Error('ECONNREFUSED');
      },
    },
    () => {}
  );

  // Quem chama está no meio de um login. Cadastro de exibição incompleto é um
  // incômodo; "não consigo entrar no painel" é uma parada de trabalho.
  assert.equal(res.status, 302, 'a falha do registro derrubou o login');

  respostaDoToken = null;
});

test('login recusado pelo Entra não registra perfil nenhum', async () => {
  const registrados = [];
  const res = respostaFalsa();

  await concluirLogin(
    {
      url: '/auth/retorno?error=access_denied&error_description=AADSTS50105',
      headers: { cookie: `painel_login=${transacaoValida()}` },
    },
    res,
    { ...cfg, registrarPerfil: (s) => registrados.push(s) },
    () => {}
  );

  // Perfil criado a partir de um login que NÃO aconteceu seria identidade
  // gravada sem prova - o oposto do motivo de isto rodar no servidor.
  assert.equal(registrados.length, 0);
});

test('as chaves do tenant ficam em cache entre validações', () => {
  // Foram muitas validações acima; se cada uma tivesse ido ao Entra, um token
  // forjado com kid aleatório viraria enxurrada de requisições no tenant.
  assert.ok(chamadasAoJwks < 4, `leituras do JWKS: ${chamadasAoJwks}`);
});
