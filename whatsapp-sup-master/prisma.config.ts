import 'dotenv/config';
import { defineConfig } from 'prisma/config';
import { urlDoBanco } from './src/db/caminho';

/**
 * Configuração do Prisma CLI (generate, migrate, db).
 *
 * A partir do Prisma 7 a URL do banco não pode mais ficar no `schema.prisma`.
 * Aqui ela serve só às ferramentas de linha de comando; o servidor em execução
 * abre o arquivo pelo adaptador em `src/db/client.ts`.
 *
 * A URL NÃO vem do `env('DATABASE_URL')` cru, e a diferença importa: com SQLite o
 * valor é um CAMINHO DE ARQUIVO, e caminho relativo é resolvido contra o
 * diretório de trabalho de quem chama. `urlDoBanco` ancora na raiz do projeto,
 * que é o que garante que `prisma migrate deploy` e o servidor abram o MESMO
 * arquivo - e cria o diretório, porque sem ele o migrate falha com "unable to
 * open database file", que não diz que o problema é uma pasta ausente. Ver
 * src/db/caminho.ts.
 *
 * Sem `DATABASE_URL` definida, cai no caminho padrão em vez de estourar: é o que
 * deixa `prisma generate` (que não abre banco nenhum) rodar no CI sem a variável.
 */
export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: {
    path: 'prisma/migrations',
  },
  datasource: {
    url: urlDoBanco(process.env.DATABASE_URL),
  },
});
