import { PrismaBetterSqlite3 } from '@prisma/adapter-better-sqlite3';
import { config } from '../config';
import { PrismaClient } from '../generated/prisma/client';
import { urlDoBanco } from './caminho';

/**
 * Conexão única com o SQLite, compartilhada por todo o processo.
 *
 * O banco é um ARQUIVO, não um servidor: não há rede, não há autenticação e não
 * há pool. Por isso as variáveis `DB_POOL_*` que existiam para o Postgres
 * sumiram - não havia nada para limitar. O que sobrou de "pool" é o
 * `DB_BUSY_TIMEOUT_MS`, e ele resolve um problema diferente: ver abaixo.
 *
 * O QUE ISTO IMPÕE AO DESENHO, e é a parte que não dá para esquecer: o SQLite
 * aceita UM escritor por banco. Dentro deste processo o adaptador serializa as
 * transações num mutex (ele segura o mutex do `BEGIN` até o commit), então duas
 * transações nunca se sobrepõem - e é isso que substituiu o
 * `pg_advisory_xact_lock` do handler e o `SELECT ... FOR UPDATE` do endpoint
 * interno. ENTRE PROCESSOS não há mutex nenhum: dois servidores apontados para o
 * mesmo arquivo brigam pelo lock de escrita e o segundo espera até o
 * `busy_timeout` estourar. Este serviço roda em uma instância só (ver
 * render.yaml, que monta um disco justamente por isso) - subir a segunda não é
 * questão de configuração, é troca de banco.
 */
const adaptador = new PrismaBetterSqlite3({
  // Caminho absoluto, resolvido contra a raiz do projeto. Ver db/caminho.ts para
  // por que não pode ser o caminho relativo cru do .env.
  url: urlDoBanco(config.databaseUrl),

  // `PRAGMA busy_timeout`: quanto esperar quando OUTRO processo está com o lock
  // de escrita, antes de devolver SQLITE_BUSY. Sem isto o padrão do
  // better-sqlite3 é 5s; o que importa é que não seja 0, porque aí um `npm run
  // retencao` rodando junto com o servidor faria a mensagem do usuário falhar em
  // vez de esperar alguns milissegundos.
  timeout: config.dbBusyTimeoutMs,
});

export const prisma = new PrismaClient({ adapter: adaptador });

/**
 * Liga o WAL. Chamar uma vez no boot, antes de atender.
 *
 * `journal_mode = WAL` fica GRAVADO no arquivo do banco, então na prática isto
 * só tem efeito na primeira execução. Vale rodar sempre porque é idempotente e
 * porque um banco recém-criado nasce em `journal_mode = delete`, onde escritor e
 * leitor se excluem: enquanto o webhook grava uma mensagem, um `sqlite3
 * banco.db` aberto para conferir dado (coisa que a documentação deste projeto
 * manda fazer) bloquearia a escrita. Com WAL, leitura e escrita convivem.
 *
 * `foreign_keys` NÃO é ligado aqui porque o better-sqlite3 já abre a conexão com
 * ele ligado - e a checagem existe para isso não virar uma suposição: sem FK, o
 * `onDelete: Cascade` do histórico de situação silenciosamente não acontece e a
 * retenção (LGPD) passa a deixar registro órfão.
 */
export async function prepararBanco(): Promise<void> {
  await prisma.$executeRawUnsafe('PRAGMA journal_mode = WAL');

  const [{ foreign_keys: fk }] =
    await prisma.$queryRawUnsafe<{ foreign_keys: bigint | number }[]>('PRAGMA foreign_keys');
  if (Number(fk) !== 1) {
    throw new Error(
      'PRAGMA foreign_keys está desligado nesta conexão. Sem ele o ON DELETE ' +
        'CASCADE do histórico de situação não roda e a retenção deixa registro órfão.'
    );
  }
}
