/**
 * Métricas do PAINEL-WEB (este processo), no formato Prometheus.
 *
 * O painel de chamados são dois processos, e a divisão de quem mede o quê segue
 * quem é dono do dado:
 *
 *   - o BOT (src/metricas.ts) é dono do banco, e mede o TRABALHO: chamados por
 *     situação, prazo vencido, conversas em andamento;
 *   - ESTE processo é dono da SESSÃO do Entra, e mede QUEM ESTÁ CONECTADO.
 *
 * COMO SE CONTA "CONECTADO" SEM TABELA DE SESSÃO
 *
 * O cookie é stateless (assinado, sem tabela), então não existe lista de sessões
 * abertas para contar. Mas o quadro JÁ SE ATUALIZA SOZINHO: o app.js roda um
 * `setInterval` que rebusca os chamados a cada `atualizarASegundos`, e cada uma
 * dessas requisições passa por aqui com o cookie junto. Isso é um heartbeat que
 * já existe — só não estava sendo aproveitado.
 *
 * Então a contagem é um Map em memória de `oid -> instante da última
 * requisição`, alimentado no ponto em que a sessão é validada. Três
 * consequências, todas aceitáveis e melhor ditas do que descobertas:
 *
 *   1. o número zera quando o processo reinicia. Correto: ninguém está
 *      "conectado" a um processo que acabou de subir;
 *   2. não persiste nada e não custa escrita em disco — diferente do Estúdio,
 *      onde o mesmo problema foi resolvido gravando `last_seen_at`, porque lá o
 *      heartbeat é raro (15 min) e o dado já morava no banco;
 *   3. conta ABAS ÚNICAS POR PESSOA, não abas: duas janelas do mesmo usuário
 *      contam uma vez. É o que "usuários conectados" deve significar.
 */
import { Gauge, Registry, collectDefaultMetrics } from '@prometheus-io/client';
import { timingSafeEqual } from 'node:crypto';

export const registro = new Registry();

collectDefaultMetrics({ register: registro, prefix: 'painel_web_processo_' });

/**
 * Janela de presença.
 *
 * Precisa ser mais larga que o intervalo de atualização do quadro, senão a
 * contagem oscila conforme o instante da raspagem. 3 minutos cobre com folga o
 * padrão do painel (dezenas de segundos) e uma atualização perdida, sem inventar
 * presença de quem já fechou a aba.
 */
const JANELA_MS = 3 * 60 * 1000;

/** `oid -> instante da última requisição autenticada`. */
const vistos = new Map();

/**
 * Registra que esta sessão deu sinal de vida.
 *
 * Chamada no ponto em que `sessaoDe()` confirma o cookie — ou seja, em toda
 * requisição autenticada, inclusive as de atualização automática do quadro.
 */
export function registrarAtividade(sessao) {
  if (!sessao?.oid) return;
  vistos.set(sessao.oid, Date.now());
}

/** Quantos oid distintos apareceram dentro da janela, limpando os vencidos. */
function conectadosAgora() {
  const corte = Date.now() - JANELA_MS;
  for (const [oid, quando] of vistos) {
    // Limpa aqui, e não num setInterval: o Map só cresce com gente que entrou,
    // e a varredura acontece no máximo a cada raspagem. Um timer para isso seria
    // trabalho de fundo para manter um número que ninguém está olhando.
    if (quando < corte) vistos.delete(oid);
  }
  return vistos.size;
}

new Gauge({
  name: 'painel_web_usuarios_conectados',
  help: 'Pessoas com o quadro aberto nos últimos 3 minutos. Contado por oid do Entra, então duas abas da mesma pessoa contam uma vez.',
  registers: [registro],
  collect() {
    this.set(conectadosAgora());
  },
});

/**
 * `painel_web_build_info{commit,versao} 1` — o valor é sempre 1; leia os rótulos.
 * Cruzado com `painel_web_processo_process_start_time_seconds`, responde "qual
 * commit está no ar e desde quando".
 */
export function registrarBuildInfo(commit, versao) {
  registro.removeSingleMetric('painel_web_build_info');
  new Gauge({
    name: 'painel_web_build_info',
    help: 'Identidade da versão em execução do painel-web.',
    labelNames: ['commit', 'versao'],
    registers: [registro],
    collect() {
      this.set({ commit: commit || 'desconhecido', versao: versao || 'desconhecida' }, 1);
    },
  });
}

/** Gauge de "o login pelo Entra está ligado?" — 1 ou 0. */
export function registrarEstadoDoLogin(ligado) {
  registro.removeSingleMetric('painel_web_login_entra_ligado');
  new Gauge({
    name: 'painel_web_login_entra_ligado',
    help: 'Se o painel está exigindo login pelo Entra ID. Zero em produção é incidente de segurança, não configuração.',
    registers: [registro],
    collect() {
      this.set(ligado ? 1 : 0);
    },
  });
}

function tokenConfere(recebido, esperado) {
  const a = Buffer.from(String(recebido));
  const b = Buffer.from(esperado);
  return a.length === b.length && timingSafeEqual(a, b);
}

/**
 * Atende `GET /metrics`, se for essa a requisição. Devolve `true` quando tratou.
 *
 * Precisa ser chamada ANTES do portão de sessão: quem raspa é o Prometheus, que
 * não tem cookie. A proteção dela é o token.
 *
 * Sem `METRICS_TOKEN`, devolve `false` e deixa a requisição seguir — vai cair no
 * portão e virar 302/401, e o Prometheus marca o alvo como fora do ar. Falha
 * fechada: melhor o alvo aparecer caído do que exposto por esquecimento.
 */
export async function atenderMetricas(req, res, token) {
  if (req.url !== '/metrics') return false;
  if (!token) return false;

  const cabecalho = String(req.headers.authorization || '');
  const recebido = cabecalho.startsWith('Bearer ') ? cabecalho.slice(7) : '';

  if (!tokenConfere(recebido, token)) {
    // 404: para quem não tem o token, esta rota é indistinguível de uma que não
    // existe.
    res.writeHead(404, { 'content-type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ erro: 'rota nao encontrada' }));
    return true;
  }

  const corpo = await registro.metrics();
  res.writeHead(200, {
    'content-type': registro.contentType,
    'cache-control': 'no-store',
  });
  res.end(corpo);
  return true;
}
