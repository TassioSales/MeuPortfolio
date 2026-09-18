import Fastify, { FastifyError, FastifyInstance } from 'fastify';
import cors from '@fastify/cors';
import helmet from '@fastify/helmet';
import rateLimit from '@fastify/rate-limit';
import { config } from './config';
import { prisma } from './db/client';
import { registrarRotasDeCategorias } from './internal/categorias';
import { registrarRotasDeConfiguracao } from './internal/configuracao';
import { registrarRotasInternas } from './internal/chamados';
import { registrarRotasDeDetalhes } from './internal/detalhes';
import { registrarRotasDePessoas } from './internal/pessoas';
import { registrarRotasDeSeries } from './internal/series';
import { registrarRotasDeSetores } from './internal/setores';
import { erroSeguro, mascararTelefones } from './log';
import { registrarRotaDeMetricas } from './metricas';
import { avisarIndisponibilidade } from './whatsapp/indisponibilidade';
import { segredoValido } from './whatsapp/signature';
import { handleIncomingMessage, telefonesDoPayload } from './whatsapp/webhook';

// Orçamento do aviso de indisponibilidade. É o último recurso quando o
// processamento já falhou, e a requisição pode ter gasto quase todo o
// `ENVIO_SINCRONO_MS` antes de chegar aqui - então ele ganha um tempo próprio e
// curto, com uma tentativa só. Se não couber, é melhor perder o aviso do que
// perder o 200 devido ao webhook.
const AVISO_TIMEOUT_MS = 3_000;

// Schemas de rota. Além da validação, é o que deixa o Fastify serializar a
// resposta com um serializador compilado em vez de JSON.stringify genérico.
const RESPOSTA_STATUS = {
  type: 'object',
  properties: { status: { type: 'string' } },
  required: ['status'],
} as const;

/**
 * Monta a aplicação sem subir nenhum servidor nem timer.
 *
 * Separado de `server.ts` para os testes poderem exercitar as rotas com
 * `app.inject()`, sem porta e sem varredor rodando por baixo.
 */
export function criarApp(): FastifyInstance {
  const app = Fastify({
    // Webhook da Evolution é pequeno; corta payload gigante antes de alocar memória.
    bodyLimit: config.bodyLimitBytes,
    // Sem isso, atrás de um proxy (ngrok, Render, nginx) todo request aparece com
    // o IP do proxy e o rate limit por IP vira um contador global. Ver config.ts.
    trustProxy: config.trustProxy,
    logger: {
      redact: {
        paths: [
          'req.headers.authorization',
          'req.headers.apikey',
          // O SEGREDO DO WEBHOOK ESTÁ NA URL.
          //
          // Com a Meta, o segredo vinha num cabeçalho e bastava removê-lo daqui.
          // Agora ele é parte do caminho, e o Fastify registra `req.url` em toda
          // requisição — ou seja, sem esta linha o segredo apareceria em texto
          // puro em cada linha de log de webhook, que é o log mais volumoso do
          // sistema. Ver whatsapp/signature.ts.
          'req.url',
        ],
        remove: true,
      },
    },
  });

  // O corpo cru deixou de ser guardado.
  //
  // Ele existia por uma razão só: a assinatura da Meta era um HMAC sobre os
  // BYTES CRUS, e parsear e reserializar mudava espaçamento e ordem de chaves,
  // fazendo a assinatura nunca bater. A Evolution não assina o corpo — o
  // parseador padrão do Fastify basta, e devolve o mesmo 400 em JSON inválido.

  // Proteção grossa contra flood NÃO autenticado (requisições que ainda nem
  // chegaram na validação de assinatura).
  //
  // Note que limitar por IP tem alcance limitado aqui: todo tráfego legítimo vem
  // da mesma instalação da Evolution, então este limite funciona quase como um teto global do
  // endpoint - por isso o valor é folgado. O controle de abuso real é por
  // telefone, em whatsapp/throttle.ts.
  app.register(rateLimit, {
    max: config.rateLimitPorMinuto,
    timeWindow: '1 minute',
  });

  // Cabeçalhos de segurança. Esta API não serve HTML nenhum - só JSON e o
  // texto do handshake -, então a política mais restritiva possível é também a
  // que não custa nada: `default-src 'none'` e nada de iframe. O que de fato
  // importa aqui é `nosniff` e o HSTS, que o helmet já liga por padrão.
  app.register(helmet, {
    contentSecurityPolicy: {
      useDefaults: false,
      directives: { defaultSrc: ["'none'"], frameAncestors: ["'none'"] },
    },
  });

  // CORS, e só quando houver origem configurada. O painel de chamados roda em
  // outra origem (é um arquivo estático servido à parte), então sem isto o
  // navegador recusa a resposta antes de o JavaScript dele ver qualquer coisa.
  //
  // A lista é explícita de propósito. `origin: true` (refletir qualquer origem)
  // deixaria qualquer site que o atendente abrisse fazer requisição autenticada
  // em nome dele - e estas rotas leem e alteram chamado.
  if (config.painelOrigens.length > 0) {
    app.register(cors, {
      origin: config.painelOrigens,
      // POST cria tarefa e categoria; DELETE exclui categoria. Faltando na
      // lista, o navegador barra a requisição no preflight e o painel mostra o
      // erro genérico de rede - o mesmo de servidor fora do ar.
      methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['authorization', 'content-type'],
      maxAge: 86_400, // 24h de cache do preflight, para não gastar cota do rate limit
    });
  }

  // Sem um handler próprio, qualquer exceção inesperada saía no formato padrão
  // do Fastify - que inclui a mensagem do erro. Mensagem de erro do Prisma pode
  // carregar os parâmetros da query, ou seja, telefone e texto do chamado. É o
  // mesmo motivo que existe o `erroSeguro` no resto do código; faltava fechar
  // esta porta.
  app.setErrorHandler((err: FastifyError, req, reply) => {
    // Falha de validação de schema: o pedido está malformado e dizer QUAL campo
    // é o que torna o endpoint interno utilizável por quem integra. Não vaza
    // nada: a essa altura o autorizador já deixou a requisição passar.
    if (err.validation) {
      req.log.warn({ onde: err.validationContext }, 'Requisição recusada na validação');
      return reply.status(400).send({
        erro: 'requisição inválida',
        detalhes: err.validation.map((v) => ({
          campo: v.instancePath.replace(/^\//, '') || v.params?.missingProperty || '(corpo)',
          problema: v.message,
          // Em erro de enum o AJV só diz "must be equal to one of the allowed
          // values". Sem devolver a lista, a resposta seria menos útil que a
          // validação escrita à mão que este schema substituiu.
          ...(Array.isArray(v.params?.allowedValues) ? { aceitos: v.params.allowedValues } : {}),
        })),
      });
    }

    const status = err.statusCode ?? 500;

    // 5xx é bug nosso: registra o detalhe no log (já reduzido e mascarado) e
    // devolve uma resposta que não conta nada para quem está do outro lado.
    if (status >= 500) {
      req.log.error(erroSeguro(err), 'Erro não tratado em rota');
      return reply.status(status).send({ erro: 'erro interno' });
    }

    req.log.warn(erroSeguro(err), 'Requisição recusada');
    return reply.status(status).send({ erro: mascararTelefones(err.message).slice(0, 200) });
  });

  // Varredura de rota (`/admin`, `/.env`, `/wp-login.php`) é o tráfego normal de
  // qualquer coisa exposta na internet. Responde no mesmo formato das outras
  // rotas em vez do 404 padrão do Fastify.
  app.setNotFoundHandler((req, reply) => {
    // A URL é registrada à mão aqui, então ela NÃO passa pelo `redact` do
    // logger — que só alcança o objeto `req` serializado. Sem este corte, um
    // `GET /webhook/<segredo>` (método errado, rota não encontrada) gravaria o
    // segredo em texto puro no log. Ver whatsapp/signature.ts.
    const url = req.url.startsWith('/webhook/') ? '/webhook/***' : req.url;
    req.log.warn({ metodo: req.method, url }, 'Rota inexistente');
    return reply.status(404).send({ erro: 'rota não encontrada' });
  });

  // Métricas para o Prometheus. Registrada junto das sondas, e pelo mesmo
  // motivo delas ficarem fora do rate limit: quem consulta é máquina, de 15 em
  // 15 segundos, e não pode consumir a cota do webhook.
  //
  // Só existe se METRICS_TOKEN estiver configurado - ver src/metricas.ts.
  registrarRotaDeMetricas(app);

  // Liveness para o orquestrador (Docker, Kubernetes, Render...). Fora do rate
  // limit: um health check batendo de 10 em 10 segundos não pode consumir a cota
  // do webhook. Não toca o banco de propósito - a pergunta aqui é "o processo está
  // vivo?", não "as dependências estão de pé?".
  app.get(
    '/health',
    {
      config: { rateLimit: false },
      schema: { response: { 200: RESPOSTA_STATUS } },
    },
    async () => ({ status: 'ok' })
  );

  // Readiness: essa SIM é a pergunta "as dependências estão de pé?". Serve para o
  // balanceador tirar a instância de rotação enquanto o banco está inacessível,
  // em vez de mandar tráfego para um processo que vai falhar em toda mensagem.
  //
  // Com SQLite isto quase nunca é a rede: é o arquivo. Disco cheio, permissão
  // errada no volume montado, ou o disco simplesmente não montado - casos em que
  // o processo sobe perfeitamente e só a escrita falha.
  app.get(
    '/ready',
    {
      config: { rateLimit: false },
      schema: { response: { 200: RESPOSTA_STATUS, 503: RESPOSTA_STATUS } },
    },
    async (req, reply) => {
      try {
        await prisma.$queryRaw`SELECT 1`;
        return { status: 'ok' };
      } catch (err) {
        req.log.error(erroSeguro(err), 'Readiness: banco inacessível');
        return reply.status(503).send({ status: 'sem banco' });
      }
    }
  );

  /**
   * Recebe as mensagens dos usuários.
   *
   * O SEGREDO VAI NO CAMINHO, e não num cabeçalho: a Evolution não assina o
   * corpo como a Meta assinava, e o que ela permite configurar em qualquer
   * versão é a URL de destino. Cadastre lá
   * `https://.../webhook/<WEBHOOK_SEGREDO>`.
   *
   * Some com isto o `GET /webhook`: o handshake de verificação era exigência da
   * Meta ao cadastrar o webhook, e a Evolution não faz nada equivalente.
   */
  app.post<{ Params: { segredo: string } }>(
    '/webhook/:segredo',
    {
      preHandler: async (req, reply) => {
        if (!segredoValido(req.params.segredo, config.webhookSegredo)) {
          req.log.warn('Webhook com segredo inválido recusado');
          // 404, e não 401: para quem não tem o segredo, a rota não deve nem
          // parecer existir. Um 401 confirma o endereço e convida a insistir.
          return reply.status(404).send();
        }
      },
    },
    async (req, reply) => {
      // Orçamento único para os envios de TODO o lote. O que não couber aqui
      // fica pendente na outbox e sai pelo varredor.
      const ateMs = Date.now() + config.envioSincronoMs;

      // `handleIncomingMessage` trata cada mensagem em isolamento e devolve quem
      // falhou, então não deveria lançar - o catch é rede de segurança para não
      // deixar o usuário no silêncio se alguma coisa inesperada escapar.
      let falharam: string[];
      try {
        ({ falharam } = await handleIncomingMessage(req.body, { ateMs }));
      } catch (err) {
        req.log.error(erroSeguro(err), 'Falha inesperada ao processar o lote recebido');
        falharam = telefonesDoPayload(req.body);
      }

      if (falharam.length > 0) {
        await avisarIndisponibilidade(falharam, {
          tentativas: 1,
          ateMs: Date.now() + AVISO_TIMEOUT_MS,
        });
      }

      return reply.status(200).send();
    }
  );

  registrarRotasInternas(app);
  registrarRotasDeCategorias(app);
  registrarRotasDePessoas(app);
  // Setores (a lista de areas da empresa) e o que pende de um chamado:
  // comentarios, anexos, etiquetas e dependencias. Ver os cabecalhos dos dois
  // arquivos para por que sao modulos separados de `chamados.ts`.
  registrarRotasDeSetores(app);
  registrarRotasDeDetalhes(app);
  registrarRotasDeConfiguracao(app);
  // A serie temporal do dashboard. Separada de `chamados.ts` porque responde
  // outra pergunta: `/internal/metricas` diz quanto deu no periodo, esta diz
  // como variou ao longo dele - ver o cabecalho do arquivo.
  registrarRotasDeSeries(app);

  return app;
}
