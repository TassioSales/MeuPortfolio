/**
 * Métricas do BOT no formato Prometheus.
 *
 * Este processo é um dos dois que compõem o painel de chamados. Ele é o que fala
 * com a Evolution e é dono do banco, então o que ele mede é o TRABALHO: chamados por
 * situação, quanto tempo o mais antigo está esperando, prazos vencidos,
 * conversas em andamento. Quem está CONECTADO ao quadro é o outro processo
 * (servidor-painel.mjs, onde vive a sessão do Entra) e mede lá.
 *
 * A rota é protegida por token e só existe se `METRICS_TOKEN` estiver
 * configurado — mesmo desenho do Estúdio, e pelo mesmo motivo: ela revela nomes
 * de rota, volume de chamados e tempos internos, e o túnel entrega tudo na
 * mesma porta.
 *
 * Fica FORA do rate limit, como /health e /ready: uma raspagem a cada 15
 * segundos não pode consumir a cota do webhook.
 */
import { timingSafeEqual } from 'node:crypto';
import type { FastifyInstance } from 'fastify';
import { Counter, Gauge, Histogram, Registry, collectDefaultMetrics } from '@prometheus-io/client';
import { config } from './config';
import { prisma } from './db/client';

export const registro = new Registry();

collectDefaultMetrics({ register: registro, prefix: 'painel_bot_processo_' });

/* ------------------------------------------------------------------ *
 *  HTTP
 * ------------------------------------------------------------------ */

export const httpTotal = new Counter({
  name: 'painel_bot_http_requisicoes_total',
  help: 'Requisições HTTP atendidas pelo bot, por método, rota e status.',
  labelNames: ['metodo', 'rota', 'status'] as const,
  registers: [registro],
});

export const httpDuracao = new Histogram({
  name: 'painel_bot_http_duracao_segundos',
  help: 'Tempo de resposta do bot, por método e rota.',
  labelNames: ['metodo', 'rota'] as const,
  // O webhook tem orçamento apertado (quem entrega desiste e reenvia), então os
  // buckets vão mais fundo no começo do que os do Estúdio: aqui a diferença
  // entre 100ms e 500ms importa de verdade.
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [registro],
});

/* ------------------------------------------------------------------ *
 *  Estado, lido no momento da raspagem
 * ------------------------------------------------------------------ */

/** Substitui o gauge de mesmo nome, para o módulo poder ser carregado duas vezes. */
function gauge(opcoes: ConstructorParameters<typeof Gauge>[0]) {
  registro.removeSingleMetric(opcoes.name);
  return new Gauge({ ...opcoes, registers: [registro] });
}

/**
 * Todas as situações possíveis, para o gauge nunca ter buraco.
 *
 * Sem a lista explícita, uma situação que ficou sem nenhum chamado simplesmente
 * some da exposição — e some do gráfico, o que parece coleta quebrada em vez de
 * "zero chamados nesse estado".
 */
const SITUACOES = [
  'aberto',
  'em_andamento',
  'aguardando_resposta',
  'resolvido',
  'fechado',
  'cancelado',
] as const;

/**
 * O que conta como fila viva.
 *
 * `fechado` entra junto de `resolvido` e `cancelado`: sao os tres estados
 * terminais do enum. Deixar `fechado` de fora faria todo chamado encerrado por
 * esse caminho continuar sendo contado como espera, e o gauge de "mais antigo
 * aberto" cresceria para sempre apontando para um chamado que ninguem deve mais
 * nada. `aguardando_resposta` NAO entra: o chamado esta parado esperando o
 * cliente, mas continua aberto.
 */
const ENCERRADOS = ['resolvido', 'fechado', 'cancelado'] as const;

/** Valores do enum `Remetente`, pelo mesmo motivo de SITUACOES. */
const REMETENTES = ['usuario', 'sistema'] as const;

export function registrarColetoresDeEstado(): void {
  gauge({
    name: 'painel_chamados',
    help: 'Chamados por situação.',
    labelNames: ['situacao'] as const,
    async collect(this: Gauge<string>) {
      this.reset();
      for (const s of SITUACOES) this.set({ situacao: s }, 0);
      const linhas = await prisma.chamado.groupBy({
        by: ['situacao'],
        _count: { _all: true },
      });
      for (const l of linhas) this.set({ situacao: String(l.situacao) }, l._count._all);
    },
  });

  gauge({
    name: 'painel_chamados_sem_responsavel',
    help: 'Chamados ainda não atribuídos a ninguém e não encerrados. É a fila que ninguém pegou.',
    async collect(this: Gauge<string>) {
      this.set(
        await prisma.chamado.count({
          where: { responsavelId: null, situacao: { notIn: [...ENCERRADOS] } },
        })
      );
    },
  });

  gauge({
    name: 'painel_chamado_mais_antigo_aberto_segundos',
    help: 'Há quanto tempo o chamado aberto mais antigo espera. É o número que diz se a fila está sendo atendida.',
    async collect(this: Gauge<string>) {
      const mais = await prisma.chamado.findFirst({
        where: { situacao: { notIn: [...ENCERRADOS] } },
        orderBy: { dataAbertura: 'asc' },
        select: { dataAbertura: true },
      });
      // Zero quando não há nada aberto — e não "sem valor": um buraco no
      // gráfico parece coleta quebrada, zero é a leitura correta.
      this.set(mais ? Math.round((Date.now() - mais.dataAbertura.getTime()) / 1000) : 0);
    },
  });

  gauge({
    name: 'painel_chamados_prazo_vencido',
    help: 'Chamados não encerrados cujo prazoEm já passou.',
    async collect(this: Gauge<string>) {
      this.set(
        await prisma.chamado.count({
          where: {
            prazoEm: { lt: new Date() },
            situacao: { notIn: [...ENCERRADOS] },
          },
        })
      );
    },
  });

  gauge({
    name: 'painel_banco_ok',
    help: 'Se o banco responde a uma consulta trivial. Mesma pergunta de /ready, como metrica.',
    async collect(this: Gauge<string>) {
      // Existe porque `/ready` e ROTA, e alerta se escreve sobre METRICA - e
      // porque `up` do Prometheus fica 1 enquanto o processo servir HTTP. Com
      // SQLite o modo de falha mais comum e exatamente esse: o processo sobe
      // perfeitamente e so a escrita falha (disco cheio, permissao no volume).
      try {
        await prisma.$queryRaw`SELECT 1`;
        this.set(1);
      } catch {
        this.set(0);
      }
    },
  });
  gauge({
    name: 'painel_conversas_em_andamento',
    help: 'Sessões de conversa do WhatsApp no meio do formulário. Subindo e não descendo significa gente desistindo no meio.',
    async collect(this: Gauge<string>) {
      this.set(await prisma.sessaoConversa.count());
    },
  });

  gauge({
    name: 'painel_mensagens',
    help: 'Mensagens registradas, por remetente.',
    labelNames: ['remetente'] as const,
    async collect(this: Gauge<string>) {
      this.reset();
      // Mesma razão da lista de SITUACOES: sem semear os valores possíveis, uma
      // tabela vazia não produz série nenhuma e o painel fica em branco — o que
      // parece coleta quebrada, e não "nenhuma mensagem ainda". Foi exatamente o
      // que aconteceu na primeira verificação contra o banco vazio.
      for (const r of REMETENTES) this.set({ remetente: r }, 0);
      const linhas = await prisma.mensagem.groupBy({
        by: ['remetente'],
        _count: { _all: true },
      });
      for (const l of linhas) this.set({ remetente: String(l.remetente) }, l._count._all);
    },
  });
}

/**
 * `painel_bot_build_info{commit,versao} 1` — o padrão de "info metric".
 *
 * O valor é sempre 1; a informação está nos RÓTULOS. Cruzada com
 * `painel_bot_processo_process_start_time_seconds`, responde "qual commit está
 * rodando e desde quando" no painel de versão no ar.
 */
export function registrarBuildInfo(commit: string, versao: string): void {
  gauge({
    name: 'painel_bot_build_info',
    help: 'Identidade da versão em execução. O valor é sempre 1; leia os rótulos.',
    labelNames: ['commit', 'versao'] as const,
    collect(this: Gauge<string>) {
      this.set({ commit: commit || 'desconhecido', versao: versao || 'desconhecida' }, 1);
    },
  });
}

/* ------------------------------------------------------------------ *
 *  A rota
 * ------------------------------------------------------------------ */

function tokenConfere(recebido: string, esperado: string): boolean {
  const a = Buffer.from(recebido);
  const b = Buffer.from(esperado);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function registrarRotaDeMetricas(app: FastifyInstance): void {
  const esperado = config.metricsToken;

  if (!esperado) {
    app.log.warn(
      'METRICS_TOKEN não configurado: GET /metrics não existe e o Prometheus vai marcar este alvo como fora do ar.'
    );
    return;
  }

  registrarColetoresDeEstado();
  registrarBuildInfo(config.gitCommit, config.appVersion);

  app.addHook('onResponse', async (request, reply) => {
    // O MOLDE da rota, nunca a URL: com a URL, cada id de chamado viraria uma
    // série nova no Prometheus e a cardinalidade cresceria sem teto.
    const rota = request.routeOptions?.url ?? 'desconhecida';
    httpTotal.inc({ metodo: request.method, rota, status: reply.statusCode });
    httpDuracao.observe({ metodo: request.method, rota }, reply.elapsedTime / 1000);
  });

  app.get('/metrics', { config: { rateLimit: false } }, async (request, reply) => {
    const cabecalho = String(request.headers.authorization ?? '');
    const recebido = cabecalho.startsWith('Bearer ') ? cabecalho.slice(7) : '';

    if (!tokenConfere(recebido, esperado)) {
      // 404, e não 401: para quem não tem o token, esta rota é indistinguível
      // de uma que não existe.
      return reply.status(404).send({ erro: 'rota não encontrada' });
    }

    return reply.type(registro.contentType).send(await registro.metrics());
  });
}
