import { alertar } from '../alerta';
import { config } from '../config';
import { prisma } from '../db/client';
import { erroSeguro, log } from '../log';
import { corpoTexto, CorpoWhatsApp, OpcoesEnvio, postarComRetry } from './client';

/**
 * Outbox de saída.
 *
 * A linha em `Mensagem` é criada dentro da transação que muda o estado da
 * conversa. O envio acontece depois do commit. Se falhar, a linha continua
 * pendente (`enviadaEm IS NULL`) e este varredor tenta de novo — sem isso, uma
 * falha da Evolution deixava o usuário esperando uma pergunta que nunca chegou.
 *
 * Entrega é "pelo menos uma vez": se o processo morrer entre o POST aceito e a
 * marcação de enviado, a mensagem é reenviada. Preferimos repetir uma pergunta
 * a deixar a pessoa no vácuo.
 */

// Espera mínima antes da primeira retentativa; dobra a cada tentativa gasta
// (30s, 1min, 2min, 4min...). Com o teto padrão de 6 tentativas, a mensagem
// sobrevive a mais de meia hora de Evolution fora.
const BACKOFF_BASE_SEGUNDOS = 30;

async function marcarEnviada(id: number): Promise<void> {
  await prisma.mensagem.update({ where: { id }, data: { enviadaEm: new Date() } });
}

async function marcarFalha(id: number, permanente: boolean): Promise<void> {
  const agora = new Date();
  await prisma.mensagem.update({
    where: { id },
    data: permanente
      ? { tentativas: config.enviosMaxTentativas, ultimaTentativaEm: agora } // desiste
      : { tentativas: { increment: 1 }, ultimaTentativaEm: agora },
  });
}

function registrarDesistencia(
  id: number,
  status: number,
  tentativas: number,
  permanente: boolean
): void {
  // Sem este log a mensagem simplesmente parava de aparecer nas varreduras e
  // ninguém ficava sabendo que o usuário nunca recebeu a resposta.
  log.error({ mensagemId: id, status, tentativas, permanente }, 'Mensagem descartada sem entrega');

  // E o log sozinho não bastava: este é o único evento do sistema em que uma
  // pessoa real ficou sem resposta, e ele só era visto por quem estivesse
  // olhando os logs na hora. Sem `ALERTA_WEBHOOK_URL` configurado, não faz nada.
  // Sem telefone e sem texto: o destino é um canal de equipe (ver src/alerta.ts).
  alertar('Mensagem descartada sem entrega', {
    mensagemId: id,
    status,
    tentativas,
    permanente,
  });
}

/** Tenta entregar agora. Retorna true se o usuário recebeu. */
export async function despachar(
  id: number,
  corpo: CorpoWhatsApp,
  opts: OpcoesEnvio = {}
): Promise<boolean> {
  const r = await postarComRetry(corpo, opts);

  try {
    if (r.ok) await marcarEnviada(id);
    else await marcarFalha(id, r.permanente);
  } catch (err) {
    // Banco indisponível na hora de marcar: a mensagem continua pendente e o
    // varredor reavalia depois.
    log.error(erroSeguro(err), 'Falha ao atualizar estado de envio');
  }

  if (!r.ok) {
    log.warn(
      { mensagemId: id, status: r.status, permanente: r.permanente, erro: r.erro },
      'Envio pendente'
    );
    if (r.permanente) registrarDesistencia(id, r.status, config.enviosMaxTentativas, true);
  }
  return r.ok;
}

type Pendente = {
  id: number;
  payload: CorpoWhatsApp;
  tentativas: number;
  telefone: string;
  texto: string;
};

/**
 * Devolve um corpo que a Evolution aceita, reconstruindo o que for antigo.
 *
 * O `payload` é gravado uma vez e reenviado LITERAL pelo varredor. Isso é o que
 * se quer no dia a dia — reenvio fiel —, mas vira armadilha numa troca de
 * provedor: toda linha que estava pendente quando o projeto saiu da Meta tem o
 * corpo dela (`{messaging_product, to, type, text:{body}}`), e a Evolution
 * recusa isso com 400. A mensagem queimaria as seis tentativas e morreria, e o
 * alerta diria "desisti" sem dizer por quê.
 *
 * Não há adivinhação envolvida: a própria linha guarda `telefone` e `texto`, que
 * é tudo o que um corpo da Evolution tem. Então o payload velho é RECONSTRUÍDO,
 * não descartado — a pessoa recebe a mensagem que ficou presa.
 *
 * O teste é pela forma, e não pela presença de campo da Meta: o que importa é se
 * o corpo serve para a Evolution de hoje, e qualquer formato que não sirva cai
 * no mesmo tratamento.
 */
function corpoParaEnvio(item: Pendente): CorpoWhatsApp {
  const p = item.payload;
  const jaServe = typeof p?.number === 'string' && p.number !== '' && typeof p?.text === 'string';
  if (jaServe) return p;

  log.warn(
    { mensagemId: item.id, chaves: Object.keys(p ?? {}) },
    'payload fora do formato da Evolution; reconstruído a partir de telefone/texto'
  );
  return corpoTexto(item.telefone, item.texto);
}

/**
 * Reserva um lote de pendentes já incrementando `tentativas` e marcando
 * `ultimaTentativaEm`, em uma única instrução.
 *
 * Uma instrução só, e não um SELECT seguido de UPDATE: no SQLite a instrução é
 * atômica por si, então nenhum outro escritor consegue ver o lote entre a
 * escolha e a marcação. É o que o `FOR UPDATE SKIP LOCKED` do Postgres fazia
 * aqui - e a razão de não haver substituto é que não há o que substituir: o
 * SQLite tem UM escritor por banco, então duas varreduras concorrentes no mesmo
 * arquivo já são impossíveis por construção.
 *
 * O filtro é por `ultimaTentativaEm` com espera crescente. Antes ele olhava
 * `timestamp`, que é a hora da CRIAÇÃO e nunca muda: passados os 30 segundos
 * iniciais a linha ficava elegível em toda varredura, então as 6 tentativas se
 * gastavam em cinco minutos e a mensagem morria ali.
 *
 * ATENÇÃO À COMPARAÇÃO DE DATA - é o mesmo lugar que já derrubou o varredor uma
 * vez, por outro motivo. O Prisma grava data no SQLite como TEXTO ISO-8601 com
 * offset (`2026-08-27T19:57:00.604+00:00`), e `datetime('now')` devolve
 * `2026-08-27 19:57:00` - espaço em vez de `T`, sem milissegundo, sem offset.
 * Comparados como TEXTO, o `T` (0x54) é maior que o espaço (0x20), então TODA
 * pendente pareceria estar no futuro e nada seria reenviado nunca. Por isso as
 * duas pontas são convertidas para número com `unixepoch(..., 'subsec')`, que
 * entende o offset do texto gravado e devolve segundos com fração.
 *
 * `pow(2, tentativas)` é a espera dobrando; as funções matemáticas do SQLite
 * vêm compiladas no better-sqlite3. E `RETURNING` numa instrução `UPDATE` exige
 * SQLite >= 3.35 (o embutido aqui é 3.53).
 *
 * Nada disso aparece em teste com dublê em memória, que reimplementa a regra em
 * JS. Quem prova a SQL é o `npm run dev:verificar-banco`, contra o arquivo de
 * verdade.
 */
async function reservarLote(limite: number): Promise<Pendente[]> {
  // `new Date()` em vez de `datetime('now')`: o Prisma serializa o parâmetro no
  // MESMO formato em que grava as outras datas. Deixar o SQLite escrever a data
  // gravaria `2026-08-27 19:57:00` na coluna, e aí a comparação da próxima
  // varredura leria uma data sem offset e sem milissegundo.
  return prisma.$queryRaw<Pendente[]>`
    UPDATE "Mensagem"
       SET tentativas = tentativas + 1,
           "ultimaTentativaEm" = ${new Date()}
     WHERE id IN (
       SELECT id FROM "Mensagem"
        WHERE remetente = 'sistema'
          AND "enviadaEm" IS NULL
          AND payload IS NOT NULL
          AND tentativas < ${config.enviosMaxTentativas}
          AND unixepoch(coalesce("ultimaTentativaEm", "timestamp"), 'subsec')
              < unixepoch('now', 'subsec') - (${BACKOFF_BASE_SEGUNDOS} * pow(2, tentativas))
        ORDER BY "timestamp"
        LIMIT ${limite}
     )
     RETURNING id, payload, tentativas, telefone, texto`;
}

export async function varrerPendentes(limite = 20): Promise<number> {
  const lote = await reservarLote(limite);
  let entregues = 0;

  for (const item of lote) {
    const r = await postarComRetry(corpoParaEnvio(item));

    if (r.ok) {
      await marcarEnviada(item.id);
      entregues++;
      continue;
    }

    if (r.permanente) await marcarFalha(item.id, true);
    // Falha transitória: `tentativas` já foi incrementado na reserva.

    if (r.permanente || item.tentativas >= config.enviosMaxTentativas) {
      registrarDesistencia(item.id, r.status, item.tentativas, r.permanente);
    }
  }

  return entregues;
}

export function iniciarVarredor(): NodeJS.Timeout {
  const timer = setInterval(() => {
    varrerPendentes().catch((err) => log.error(erroSeguro(err), 'Varredor de pendentes falhou'));
  }, config.varredorIntervaloSegundos * 1_000);

  timer.unref(); // não segura o processo no shutdown
  return timer;
}
