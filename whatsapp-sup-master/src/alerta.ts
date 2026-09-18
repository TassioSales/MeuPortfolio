import { config } from './config';
import { erroSeguro, log } from './log';

/**
 * Alerta operacional para o que precisa de gente, não de log.
 *
 * Existe por um caso só, e é o pior do sistema: a outbox desistir de uma
 * mensagem. Quando isso acontece, alguém mandou mensagem e NUNCA recebeu
 * resposta - e até aqui o único registro era um `log.error` que só aparece para
 * quem estivesse olhando os logs naquele momento.
 *
 * Desligado por padrão. Sem `ALERTA_WEBHOOK_URL` nada é postado e o
 * comportamento é exatamente o de antes (o log continua saindo nos dois casos).
 */

// O corpo carrega `text` E `content` além dos campos estruturados porque os
// dois destinos prováveis aqui esperam chaves diferentes: Slack lê `text`,
// Discord lê `content`. Mandar os dois faz o webhook funcionar nos dois sem
// nenhuma configuração de formato - um coletor genérico ignora o que não usa.
type CorpoAlerta = {
  text: string;
  content: string;
  evento: string;
  detalhes: Record<string, unknown>;
};

const TIMEOUT_MS = 5_000;

// Coalescência: numa queda longa da Evolution, TODA mensagem pendente estoura as
// tentativas e desiste. Sem janela, isso vira uma rajada de alertas idênticos -
// e um canal com 300 alertas é um canal que ninguém lê. O primeiro sai na hora;
// os seguintes da janela são contados e resumidos no próximo.
let proximoEnvioEm = 0;
let suprimidos = 0;

/** Só para testes: zera a janela de coalescência entre casos. */
export function _resetAlertas(): void {
  proximoEnvioEm = 0;
  suprimidos = 0;
}

async function postar(corpo: CorpoAlerta): Promise<void> {
  try {
    const res = await fetch(config.alertaWebhookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (!res.ok) {
      log.warn({ status: res.status }, 'Webhook de alerta recusou o alerta');
    }
  } catch (err) {
    // Alerta que falha não pode derrubar o varredor: ele existe para avisar
    // sobre a falha, não para virar uma segunda.
    log.error(erroSeguro(err), 'Falha ao postar alerta');
  }
}

/**
 * Dispara um alerta, se houver webhook configurado.
 *
 * NÃO recebe nem telefone nem texto de propósito: o destino é um canal de
 * equipe (Slack, Discord), fora do controle de retenção deste sistema, e o
 * `mensagemId` já é suficiente para achar a linha no banco.
 *
 * Não é `await`-ado por quem chama: a rede do alerta não pode atrasar o
 * varredor nem a resposta do webhook.
 */
export function alertar(evento: string, detalhes: Record<string, unknown>): void {
  if (config.alertaWebhookUrl === '') return;

  const agora = Date.now();
  if (agora < proximoEnvioEm) {
    suprimidos += 1;
    return;
  }

  const repetidos = suprimidos;
  suprimidos = 0;
  proximoEnvioEm = agora + config.alertaIntervaloSegundos * 1_000;

  const linhas = Object.entries(detalhes)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join(' ');
  const resumo =
    repetidos > 0
      ? `[whatsapp-suporte] ${evento} | ${linhas} | +${repetidos} evento(s) semelhante(s) na última janela`
      : `[whatsapp-suporte] ${evento} | ${linhas}`;

  void postar({
    text: resumo,
    content: resumo,
    evento,
    detalhes: { ...detalhes, ...(repetidos > 0 ? { suprimidos: repetidos } : {}) },
  });
}
