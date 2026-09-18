import { janelas } from '../estado/janelas';
import { erroSeguro, log } from '../log';
import { OpcoesEnvio, enviarDireto } from './client';
import { ehTelefoneValido } from './telefone';

/**
 * Aviso de indisponibilidade.
 *
 * Quando o processamento estoura (tipicamente banco inacessível), o webhook
 * respondia 200 e o usuário ficava no silêncio absoluto, sem saber se o bot
 * morreu. Este caminho fala com a Evolution direto, sem tocar no banco — que é
 * justamente o que costuma estar quebrado.
 *
 * Recebe a lista de telefones que realmente falharam, e não o payload inteiro:
 * num lote em que só uma mensagem estourou, avisar todo mundo do lote é mandar
 * "estamos com problema" para quem foi atendido normalmente.
 */

const AVISO =
  'Estamos com um problema técnico no atendimento agora. ' +
  'Sua mensagem não foi registrada — pode tentar de novo daqui a alguns minutos?';

// Um aviso por telefone a cada 10 minutos: numa queda do banco, cada mensagem
// do usuário passaria por aqui e ele receberia o mesmo texto em looping.
//
// O controle vive em `src/estado/janelas.ts` — em memória por padrão, no Redis
// quando `REDIS_URL` está definida. Com N instâncias e estado em memória, este
// limite virava N avisos por telefone a cada 10 minutos.
const INTERVALO_MS = 10 * 60 * 1000;

const chave = (telefone: string): string => `aviso:${telefone}`;

/** `true` quando este telefone já recebeu aviso na janela atual. */
async function devePular(telefone: string, agora: number): Promise<boolean> {
  // `reservar` devolve true para quem chegou primeiro — que é justamente quem
  // NÃO deve pular.
  return !(await janelas.reservar(chave(telefone), INTERVALO_MS, agora));
}

export async function avisarIndisponibilidade(
  telefones: readonly string[],
  opts: OpcoesEnvio = {}
): Promise<void> {
  try {
    const agora = Date.now();
    for (const telefone of new Set(telefones)) {
      if (!ehTelefoneValido(telefone)) continue;
      if (await devePular(telefone, agora)) continue;
      await enviarDireto(telefone, AVISO, opts);
    }
  } catch (err) {
    // Nunca deixa o aviso derrubar o 200 devido ao webhook. `erroSeguro` porque um
    // erro da Evolution pode trazer o telefone na mensagem.
    log.error(erroSeguro(err), 'Falha ao avisar indisponibilidade');
  }
}

export function _resetAvisos(): void {
  janelas._limpar();
}
