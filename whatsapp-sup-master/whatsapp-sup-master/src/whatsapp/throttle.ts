import { config } from '../config';
import { janelas } from '../estado/janelas';

// Limite de mensagens por telefone, em janela fixa de 1 minuto.
//
// Este é o controle de abuso que de fato importa: depois da validação de
// segredo do webhook, todo tráfego vem legitimamente da Evolution, então limitar por IP não
// distingue um usuário fazendo flood de todos os outros.
//
// O estado vive em `src/estado/janelas.ts`: em memória quando `REDIS_URL` está
// vazia (padrão, correto com uma instância só) e no Redis quando ela está
// definida. Sem isso, subir a segunda instância multiplicava este limite pelo
// número de instâncias sem nenhum aviso - ver o cabeçalho daquele arquivo.

const JANELA_MS = 60_000;

const chave = (telefone: string): string => `throttle:${telefone}`;

/**
 * Registra uma mensagem e diz se ela deve ser processada.
 * Retorna false quando o telefone estourou o limite da janela atual.
 */
export async function permitirMensagem(telefone: string, agora?: number): Promise<boolean> {
  const total = await janelas.incrementar(chave(telefone), JANELA_MS, agora);
  return total <= config.mensagensPorMinutoPorTelefone;
}

/**
 * Devolve à janela a mensagem que acabou sendo descartada como reentrega.
 *
 * A cota é consumida ANTES de a mensagem tocar o banco - tem que ser, é a
 * checagem que existe justamente para não gastar transação com flood. O efeito
 * colateral é que uma reentrega do webhook (a mesma mensagem chegando duas vezes,
 * que é o comportamento normal dela) queimava cota de quem não mandou nada de
 * novo: numa rajada de reentregas, o usuário legítimo ficava sem os 20/min dele
 * por causa de mensagens que o sistema descartou.
 */
export async function devolverMensagem(telefone: string, agora?: number): Promise<void> {
  await janelas.devolver(chave(telefone), JANELA_MS, agora);
}

// Exposto só para testes.
export function _resetThrottle(): void {
  janelas._limpar();
}
