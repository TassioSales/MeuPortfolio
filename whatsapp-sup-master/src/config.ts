import 'dotenv/config';

// Toda variável de ambiente é lida e validada aqui, uma única vez, no boot.
// O objetivo é falhar alto e cedo: se faltar qualquer segredo, o processo morre
// antes de aceitar a primeira requisição - em vez de subir "funcionando" com a
// verificação do webhook desligada.

const faltando: string[] = [];

function obrigatoria(nome: string): string {
  const valor = process.env[nome];
  if (valor === undefined || valor.trim() === '') {
    faltando.push(nome);
    return '';
  }
  return valor.trim();
}

function textoOpcional(nome: string, padrao: string): string {
  const bruto = process.env[nome];
  return bruto === undefined || bruto.trim() === '' ? padrao : bruto.trim();
}

/**
 * `trustProxy` decide se o Fastify acredita no header `X-Forwarded-For` para
 * descobrir o IP do cliente. Atrás de ngrok/Render/nginx, sem isso todo o
 * tráfego aparece com o IP do proxy e o rate limit por IP vira um contador
 * global. Fica desligado por padrão porque ligar sem um proxy confiável na
 * frente é pior: aí qualquer um forja o header e escapa do limite.
 */
function trustProxyOpcional(): boolean | number | string {
  const bruto = process.env.TRUST_PROXY?.trim();
  if (bruto === undefined || bruto === '' || bruto === 'false') return false;
  if (bruto === 'true') return true;
  if (/^\d+$/.test(bruto)) return Number(bruto); // número de hops confiáveis
  return bruto; // lista de IPs/CIDRs separada por vírgula
}

/** Lê uma variável com valores separados por vírgula. Vazia = lista vazia. */
function listaOpcional(nome: string): string[] {
  const bruto = process.env[nome];
  if (bruto === undefined || bruto.trim() === '') return [];
  return bruto
    .split(',')
    .map((v) => v.trim())
    .filter((v) => v !== '');
}

/**
 * Como `numeroOpcional`, mas aceita fração. Existe para prazos medidos em
 * horas: `SESSAO_TTL_HORAS=0.5` (meia hora) é o valor natural para exercitar a
 * expiração de sessão sem esperar uma hora, e com a validação de inteiro ele
 * não era "arredondado" - derrubava o processo no boot com "precisa ser inteiro
 * >= 1", que não é o que quem escreveu 0.5 esperava ler.
 */
function fracaoOpcional(nome: string, padrao: number): number {
  const bruto = process.env[nome];
  if (bruto === undefined || bruto.trim() === '') return padrao;

  const valor = Number(bruto);
  if (!Number.isFinite(valor) || valor <= 0) {
    faltando.push(`${nome} (precisa ser um número > 0, veio "${bruto}")`);
    return padrao;
  }
  return valor;
}

function numeroOpcional(nome: string, padrao: number, permiteZero = false): number {
  const bruto = process.env[nome];
  if (bruto === undefined || bruto.trim() === '') return padrao;

  const valor = Number(bruto);
  const minimo = permiteZero ? 0 : 1;
  if (!Number.isInteger(valor) || valor < minimo) {
    faltando.push(`${nome} (precisa ser inteiro >= ${minimo}, veio "${bruto}")`);
    return padrao;
  }
  return valor;
}

export const config = {
  port: numeroOpcional('PORT', 3000),

  /**
   * O SEGREDO DO WEBHOOK — e por que ele é obrigatório.
   *
   * A Meta assinava cada webhook com HMAC-SHA256 sobre os bytes crus do corpo, e
   * era isso que impedia qualquer um que descobrisse a URL de injetar mensagem
   * falsa. A Evolution NÃO assina nada: ela faz um POST simples no endereço
   * configurado.
   *
   * Sem substituto, o `/webhook` viraria uma porta aberta — e o estrago não é
   * "aceita chamado falso": quem postasse ali faria o bot ENVIAR mensagem para
   * qualquer número, o que termina com o número banido.
   *
   * O substituto é um segredo no CAMINHO: a Evolution é configurada para chamar
   * `/webhook/<segredo>`, e o valor é comparado em tempo constante. Não é tão
   * bom quanto assinatura (o segredo viaja na URL e pode acabar em log de proxy),
   * mas é o que a Evolution permite em qualquer versão — e é infinitamente melhor
   * que nada. Com HTTPS, a URL não trafega em claro.
   *
   * Gere com 32 bytes aleatórios:
   *   node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"
   */
  webhookSegredo: obrigatoria('WEBHOOK_SEGREDO'),

  // Endereço da Evolution. Sem barra no fim - ela é acrescentada na montagem.
  //
  // Existe como variável, e não fixo, pelo mesmo motivo que o host da Graph
  // existia: é o que permite apontar para a Evolution de mentira em
  // desenvolvimento (`npm run dev:evolution`) e rodar a conversa inteira sem
  // instância de verdade.
  evolutionUrl: obrigatoria('EVOLUTION_URL'),

  // A chave vai no cabeçalho `apikey` de toda chamada. Pode ser a global da
  // instalação ou a da instância - a Evolution aceita as duas.
  evolutionApiKey: obrigatoria('EVOLUTION_API_KEY'),

  // O nome da instância conectada ao número. Entra no CAMINHO de toda rota de
  // envio (`/message/sendText/{instancia}`), não no corpo.
  evolutionInstancia: obrigatoria('EVOLUTION_INSTANCIA'),

  // Ver comentário em trustProxyOpcional().
  trustProxy: trustProxyOpcional(),

  // Caminho do arquivo SQLite, no formato `file:...`. Relativo é resolvido
  // contra a RAIZ DO PROJETO, e não contra o diretório de onde o comando foi
  // rodado - ver src/db/caminho.ts, que é quem faz essa conta para o runtime e
  // para o CLI do Prisma ao mesmo tempo.
  //
  // Ex.: file:./dados/whatsapp-suporte.db  ·  file:/app/dados/whatsapp-suporte.db
  //
  // NÃO aceita parâmetros na URL (`?connection_limit=1` e afins): o adaptador
  // apenas tira o `file:` e usa o resto como nome de arquivo, então a query
  // string viraria parte do nome.
  databaseUrl: obrigatoria('DATABASE_URL'),

  // `PRAGMA busy_timeout`: quanto esperar pelo lock de escrita do arquivo antes
  // de devolver SQLITE_BUSY.
  //
  // Não é pool - SQLite não tem pool, tem UM escritor por banco. Isto existe
  // para o caso de outro PROCESSO estar escrevendo: um `npm run retencao` no
  // cron, um `npm run db:view` do deploy, um `sqlite3` aberto para conferir
  // dado. Dentro deste processo as transações já são serializadas pelo
  // adaptador (ver src/db/client.ts), então o timeout nunca é atingido por
  // concorrência interna.
  dbBusyTimeoutMs: numeroOpcional('DB_BUSY_TIMEOUT_MS', 10_000),

  // Tamanho máximo do corpo da requisição (bytes). Webhooks da Evolution são
  // pequenos; qualquer coisa acima disso é abuso ou bug.
  bodyLimitBytes: numeroOpcional('BODY_LIMIT_BYTES', 256 * 1024),

  // Limite duro de caracteres por mensagem. O próprio WhatsApp corta texto em
  // 4096, então nada legítimo passa disso - só payload forjado.
  maxCaracteresMensagem: numeroOpcional('MAX_CARACTERES_MENSAGEM', 4096),

  // Tamanho máximo de UM anexo de chamado, em bytes.
  //
  // Tem limite próprio, e não o `bodyLimitBytes` acima, porque as duas rotas
  // recebem coisas de tamanho incomparável: o webhook da Evolution é um JSON de
  // alguns kilobytes, e um print de tela do PDV tem megabytes. Com um limite só,
  // ou o webhook aceitaria payload grande demais para o que ele faz, ou não
  // caberia anexo nenhum.
  //
  // O binário vai para dentro do SQLite (ver o model `Anexo`), então este número
  // é o que decide quão rápido o arquivo do banco cresce: 5 MB x quantos anexos
  // por chamado x quantos chamados. Baixar é seguro; subir exige olhar o disco.
  anexoMaxBytes: numeroOpcional('ANEXO_MAX_BYTES', 5 * 1024 * 1024),

  // Flood de requisições NÃO autenticadas (ver comentário em server.ts sobre
  // por que limitar por IP é uma proteção grossa neste caso).
  rateLimitPorMinuto: numeroOpcional('RATE_LIMIT_POR_MINUTO', 300),

  // Limite por telefone - esse é o controle de abuso que realmente importa.
  mensagensPorMinutoPorTelefone: numeroOpcional('MSGS_POR_MINUTO_POR_TELEFONE', 20),

  // --- Estado compartilhado entre instâncias (Redis) ---
  //
  // Vazio = os limites por telefone vivem em memória, no processo. É o padrão e
  // é CORRETO com uma instância só - que é o que o render.yaml declara hoje.
  //
  // Com mais de uma instância, memória deixa de ser suficiente sem nada quebrar:
  // cada processo passa a ter a sua contagem e o limite efetivo vira
  // INSTÂNCIAS x o configurado, silenciosamente. Preencher esta variável é o que
  // faz throttle e aviso de indisponibilidade valerem para a frota inteira.
  //
  // Falha do Redis NÃO desliga o limite: ele volta a valer por instância, que é
  // o comportamento anterior. Ver src/estado/janelas.ts.
  //
  // Ex.: redis://default:senha@host:6379  ·  rediss://... para TLS
  redisUrl: textoOpcional('REDIS_URL', ''),

  // Prefixo de toda chave gravada no Redis. Existe porque um Redis gerenciado
  // costuma ser compartilhado entre serviços: sem prefixo, dois sistemas que
  // usem "5511999999999" como chave se atropelam.
  redisPrefixo: textoOpcional('REDIS_PREFIXO', 'wa'),

  // Tempo de inatividade após o qual a coleta em andamento é descartada e a
  // conversa recomeça do zero.
  sessaoTtlHoras: fracaoOpcional('SESSAO_TTL_HORAS', 24),

  // Token do endpoint interno que muda a situação do chamado. Obrigatório:
  // subir um endpoint de escrita sem autenticação seria repetir exatamente o
  // erro que a validação de assinatura do webhook corrigiu.
  internalApiToken: obrigatoria('INTERNAL_API_TOKEN'),

  // --- observabilidade ---------------------------------------------------

  // Token que o Prometheus manda em `Authorization: Bearer` para raspar
  // GET /metrics. SEM ELE A ROTA NAO EXISTE - falha fechada, igual ao Estudio.
  //
  // E SEPARADO do INTERNAL_API_TOKEN de proposito: sao consumidores diferentes,
  // com ciclos de rotacao diferentes. Revogar o acesso do Prometheus nao pode
  // derrubar o quadro, e vice-versa.
  metricsToken: textoOpcional('METRICS_TOKEN', ''),

  // Identidade da versao em execucao, para o painel "versao no ar" do Grafana.
  // Injetados na CONSTRUCAO da imagem (ARG no Dockerfile).
  gitCommit: textoOpcional('GIT_COMMIT', 'desconhecido'),
  appVersion: textoOpcional('APP_VERSION', 'desconhecida'),

  // --- Painel de chamados (o quadro que lê estes dados no navegador) ---

  // Origens autorizadas a chamar esta API pelo navegador. Vazio = CORS desligado,
  // e aí a API só é consumível fora do navegador. Nunca use `*`: estas rotas
  // pedem token, e `*` com credencial é justamente o que o CORS existe para
  // impedir.
  // Ex.: PAINEL_ORIGENS=http://127.0.0.1:5500,https://painel.suaempresa.com.br
  painelOrigens: listaOpcional('PAINEL_ORIGENS'),

  // Token do painel. Opcional: sem ele, o painel usa o INTERNAL_API_TOKEN.
  //
  // Vale separar porque este token vive no NAVEGADOR de cada atendente, e não
  // num servidor: ele vaza com mais facilidade (máquina compartilhada, extensão,
  // print de tela). Com um token só para o painel, revogar não derruba nenhuma
  // outra integração.
  painelToken: textoOpcional('PAINEL_TOKEN', ''),

  // Envio: tentativas imediatas antes de deixar a mensagem para o varredor.
  enviosTentativas: numeroOpcional('ENVIOS_TENTATIVAS', 3),
  // Teto de tentativas somando as imediatas e as do varredor.
  enviosMaxTentativas: numeroOpcional('ENVIOS_MAX_TENTATIVAS', 6),
  varredorIntervaloSegundos: numeroOpcional('VARREDOR_INTERVALO_SEGUNDOS', 60),

  // Orçamento de tempo para os envios feitos DENTRO de uma requisição de
  // webhook, somando todas as mensagens do lote. Quem entrega desiste de esperar o 200
  // em poucos segundos e reentrega o lote inteiro; sem esse teto, um lote de 5
  // mensagens com a Evolution lenta segurava a requisição por minutos. O que não
  // couber no orçamento fica pendente e sai pelo varredor.
  envioSincronoMs: numeroOpcional('ENVIO_SINCRONO_MS', 10_000),

  // De quanto em quanto tempo varrer sessões abandonadas (ver
  // conversation/sessoes.ts). O prazo em si é o SESSAO_TTL_HORAS.
  limpezaSessoesMinutos: numeroOpcional('LIMPEZA_SESSOES_MINUTOS', 60),

  // --- Alerta operacional ---
  // Webhook (Slack, Discord ou qualquer coletor que aceite JSON) avisado quando
  // a outbox DESISTE de uma mensagem - ou seja, quando um usuário mandou
  // mensagem e não recebeu resposta nenhuma. Vazio = desligado, e aí só sobra o
  // `log.error`, que é como era antes. Ver src/alerta.ts.
  alertaWebhookUrl: textoOpcional('ALERTA_WEBHOOK_URL', ''),

  // Janela de coalescência dos alertas. Numa queda longa da Evolution toda
  // mensagem pendente desiste ao mesmo tempo; sem esta janela o canal recebe
  // centenas de avisos iguais e ninguém lê nenhum.
  alertaIntervaloSegundos: numeroOpcional('ALERTA_INTERVALO_SEGUNDOS', 300),

  // Retenção (LGPD). 0 = desligado. Ver `npm run retencao`.
  retencaoMensagensDias: numeroOpcional('RETENCAO_MENSAGENS_DIAS', 0, true),
  retencaoChamadosDias: numeroOpcional('RETENCAO_CHAMADOS_DIAS', 0, true),
} as const;

if (faltando.length > 0) {
  console.error(
    'Configuração inválida. Corrija no .env antes de subir o servidor:\n' +
      faltando.map((v) => `  - ${v}`).join('\n') +
      '\n\nUse o .env.example como referência.'
  );
  process.exit(1);
}
