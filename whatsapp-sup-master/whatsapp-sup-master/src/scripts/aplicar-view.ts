import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { prisma } from '../db/client';

/**
 * Aplica `sql/view_chamados_para_cards.sql`.
 *
 * Existe porque `prisma migrate` não gerencia view: sem este passo, todo banco
 * novo nasce sem ela e a plataforma de cards não tem o que consultar.
 *
 * O QUE MUDOU COM O SQLITE, e é bom saber antes de procurar: a metade deste
 * script que reaplicava GRANT foi embora. SQLite não tem usuário nem papel - o
 * controle de acesso é a permissão do ARQUIVO no sistema de arquivos, tudo ou
 * nada. Quem antes lia só a view com um usuário somente-leitura hoje precisa de
 * outra abordagem: consumir a rota `/internal/chamados` (que já minimiza os
 * campos e exige token) ou receber uma CÓPIA do arquivo aberta em modo
 * `readonly`. A view continua valendo como contrato de leitura - ela define
 * QUAIS colunas o consumidor vê, e `telefone` deliberadamente não é uma delas -
 * mas ela não é mais uma fronteira de permissão.
 *
 * Idempotente de propósito: pode rodar depois de toda migração, sempre. Migração
 * que mexe em coluna usada pela view precisa da view recriada, e é isso que o
 * `DROP` daqui garante.
 *
 * Uso:
 *   npm run db:view
 */

const CAMINHO_SQL = resolve(__dirname, '../../sql/view_chamados_para_cards.sql');

/**
 * Nome da view, usado no `DROP` que antecede o arquivo.
 *
 * Fica aqui e não no .sql porque o SQLite não tem `CREATE OR REPLACE VIEW`, e
 * cada instrução tem de ir separada: o driver prepara UMA por chamada, então um
 * arquivo com `DROP; CREATE;` estouraria em vez de rodar as duas.
 */
const NOME_VIEW = 'chamados_para_cards';

export async function aplicarView(): Promise<void> {
  const sql = readFileSync(CAMINHO_SQL, 'utf8');

  await prisma.$executeRawUnsafe(`DROP VIEW IF EXISTS "${NOME_VIEW}"`);
  await prisma.$executeRawUnsafe(sql);

  console.log(`View ${NOME_VIEW} aplicada.`);
}

if (require.main === module) {
  aplicarView()
    .then(() => prisma.$disconnect())
    .then(() => process.exit(0))
    .catch(async (err) => {
      console.error('Falha ao aplicar a view:', err instanceof Error ? err.message : err);
      await prisma.$disconnect().catch(() => {});
      process.exit(1);
    });
}
