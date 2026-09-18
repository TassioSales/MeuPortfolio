import { existsSync, mkdirSync } from 'node:fs';
import { dirname, isAbsolute, resolve } from 'node:path';

/**
 * Transforma o `DATABASE_URL` em um caminho de arquivo ABSOLUTO.
 *
 * Existe porque, com SQLite, o banco é um arquivo - e caminho relativo é
 * resolvido contra o DIRETÓRIO DE TRABALHO de quem chama. São pelo menos quatro
 * chamadores com diretórios diferentes: `npm run dev` (raiz), `node
 * dist/server.js` (raiz), o CLI do Prisma carregado pelo `prisma.config.ts`, e o
 * `npm run retencao` de um cron qualquer. Com `file:./dados/x.db` cru, dois
 * deles podem abrir arquivos DIFERENTES - e a falha não é um erro, é pior:
 * o segundo cria um banco vazio do lado e o servidor passa a atender sem os
 * dados, sem nada quebrar.
 *
 * A âncora é a RAIZ DO PROJETO (o diretório acima de `src/`), e não o
 * `process.cwd()`, exatamente para não depender de onde o comando foi rodado.
 *
 * Aceita também caminho absoluto (`file:/app/dados/x.db`, que é o que o
 * render.yaml usa) e `file::memory:`.
 */

/**
 * Raiz do projeto: o primeiro diretório ACIMA deste arquivo que tem um
 * `package.json`.
 *
 * Contar níveis com `resolve(__dirname, '../..')` não serve, e a razão é
 * concreta: este arquivo aparece em três profundidades diferentes.
 * `src/db/caminho.ts` em desenvolvimento, `dist/db/caminho.js` no build de
 * produção (o `rootDir` é `src`, então o `dist` espelha o conteúdo de `src`) e
 * `dist-test/src/db/caminho.js` no build de teste (que compila `src` E `test`,
 * então precisa manter os dois diretórios). Dois níveis acerta nos dois
 * primeiros e erra no terceiro - e o jeito que erra é o pior possível: aponta
 * para `dist-test/dados/`, cria o arquivo lá e o script falha com "a tabela não
 * existe", que faz procurar migração faltando em vez de caminho errado.
 */
function acharRaiz(): string {
  let dir = __dirname;

  for (;;) {
    if (existsSync(resolve(dir, 'package.json'))) return dir;
    const acima = dirname(dir);
    // Chegou na raiz do disco sem achar nada: melhor o diretório de trabalho do
    // que um caminho inventado.
    if (acima === dir) return process.cwd();
    dir = acima;
  }
}

const RAIZ = acharRaiz();

/** O que o SQLite entende como banco em memória, e não como nome de arquivo. */
export const EM_MEMORIA = ':memory:';

/**
 * Recusa URL de banco em REDE com uma mensagem que diz o que fazer.
 *
 * Sem isto, um `DATABASE_URL` de Postgres que sobrou de antes da migração para
 * SQLite não dá erro de configuração: ele é tratado como caminho relativo, e o
 * `mkdir` estoura com `ENOENT: no such file or directory, mkdir
 * '.../postgresql:/usuario:senha@localhost:5432'` - que não menciona banco, não
 * menciona SQLite, e por cima IMPRIME A SENHA no log.
 */
function recusarUrlDeServidor(bruto: string): void {
  const esquema = /^([a-z][a-z0-9+.-]*):\/\//i.exec(bruto)?.[1];
  if (esquema === undefined) return;

  throw new Error(
    `DATABASE_URL aponta para um servidor "${esquema}://", mas este projeto usa ` +
      'SQLite: o valor tem de ser um caminho de arquivo, como ' +
      'DATABASE_URL="file:./dados/whatsapp-suporte.db". ' +
      '(Se você está vindo da versão em Postgres, o banco antigo não é lido ' +
      'automaticamente - ver docs/WA Banco de dados.md.)'
  );
}

/**
 * Devolve o caminho do arquivo do banco a partir do valor do `DATABASE_URL`.
 *
 * Não valida a URL: quem falha alto por `DATABASE_URL` ausente é o config.ts.
 * Aqui um valor vazio devolve o padrão, para o CLI do Prisma conseguir rodar
 * `generate` (que não abre banco) sem exigir a variável.
 */
export function caminhoDoBanco(url: string | undefined): string {
  const bruto = (url ?? '').trim().replace(/^file:/, '');

  if (bruto === '') return resolve(RAIZ, 'dados/whatsapp-suporte.db');
  if (bruto === EM_MEMORIA) return EM_MEMORIA;

  recusarUrlDeServidor(bruto);

  return isAbsolute(bruto) ? bruto : resolve(RAIZ, bruto);
}

/**
 * Como `caminhoDoBanco`, mas já no formato `file:` que o Prisma espera - e
 * criando o diretório antes.
 *
 * O `mkdir` está aqui, e não só no runtime, porque o primeiro comando a tocar o
 * banco costuma ser o `prisma migrate deploy`: sem o diretório, ele falha com
 * "unable to open database file", que não diz que o problema é uma pasta que não
 * existe. Com um disco montado em produção (ver render.yaml) o diretório já
 * existe e o `recursive` faz disto um no-op.
 */
export function urlDoBanco(url: string | undefined): string {
  const caminho = caminhoDoBanco(url);
  if (caminho === EM_MEMORIA) return `file:${EM_MEMORIA}`;

  mkdirSync(dirname(caminho), { recursive: true });
  return `file:${caminho}`;
}
