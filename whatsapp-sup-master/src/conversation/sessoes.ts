import { config } from '../config';
import { prisma } from '../db/client';
import { erroSeguro, log } from '../log';

/**
 * Descarte de sessões abandonadas.
 *
 * `SessaoConversa` guarda nome, resumo e descrição — dado pessoal — enquanto o
 * chamado está sendo montado. O TTL era aplicado só de forma preguiçosa: a
 * sessão vencida era jogada fora quando AQUELE telefone mandava outra mensagem.
 * Quem abandonava a conversa na etapa da descrição e nunca voltava deixava esses
 * dados no banco para sempre, e o script de retenção nem olhava para a tabela.
 *
 * Diferente da retenção de mensagens e chamados, aqui não existe decisão de
 * negócio a tomar: passado o `SESSAO_TTL_HORAS`, a sessão já seria descartada no
 * próximo contato de todo jeito. Então esta limpeza roda sempre, sem depender de
 * nenhuma política configurada.
 */

/** Instante antes do qual uma sessão é considerada abandonada. */
export function corteExpiracao(agora: Date = new Date()): Date {
  return new Date(agora.getTime() - config.sessaoTtlHoras * 60 * 60 * 1000);
}

export async function contarSessoesExpiradas(agora?: Date): Promise<number> {
  return prisma.sessaoConversa.count({ where: { atualizadoEm: { lt: corteExpiracao(agora) } } });
}

export async function limparSessoesExpiradas(agora?: Date): Promise<number> {
  const { count } = await prisma.sessaoConversa.deleteMany({
    where: { atualizadoEm: { lt: corteExpiracao(agora) } },
  });
  return count;
}

/**
 * Varredura periódica no próprio processo.
 *
 * O script de retenção também faz isso, mas depende de alguém agendar um cron —
 * e um dado pessoal esquecido no banco não devia depender disso.
 */
export function iniciarLimpezaDeSessoes(): NodeJS.Timeout {
  const rodar = () =>
    limparSessoesExpiradas()
      .then((n) => {
        if (n > 0) log.info({ sessoes: n }, 'Sessões abandonadas descartadas');
      })
      .catch((err) => log.error(erroSeguro(err), 'Falha ao limpar sessões abandonadas'));

  // Uma passada no boot: sem isso, subir e reiniciar antes do primeiro intervalo
  // deixaria a limpeza nunca acontecer.
  void rodar();

  const timer = setInterval(rodar, config.limpezaSessoesMinutos * 60 * 1_000);
  timer.unref(); // não segura o processo no shutdown
  return timer;
}
