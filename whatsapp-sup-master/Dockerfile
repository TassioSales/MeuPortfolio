# syntax=docker/dockerfile:1

# Imagem de produção do bot.
#
# Duas etapas: a primeira compila (precisa de TypeScript, do CLI do Prisma e das
# dependências de desenvolvimento), a segunda carrega só o que roda. O que sai no
# fim não tem compilador nem código-fonte.

# ---------- etapa 1: build ----------
FROM node:24-slim AS build

WORKDIR /app

# Dependências antes do código: esta camada só é refeita quando o lockfile muda,
# e não a cada alteração em src/.
# `python3` e `make`/`g++` NÃO entram aqui de propósito: o `better-sqlite3` (que
# vem com o adaptador do Prisma) baixa um binário pronto para linux/x64 e só cai
# para compilar do zero se não houver. Se um dia o `npm ci` passar a compilar
# nesta etapa, o motivo é falta de binário para a plataforma da imagem - e a
# correção é instalar as ferramentas AQUI, na etapa de build, nunca na de
# runtime.
COPY package.json package-lock.json ./
RUN npm ci

# O cliente do Prisma é GERADO, não versionado (ver .gitignore). Sem este passo
# o `tsc` não encontra os tipos de @prisma/client.
COPY prisma.config.ts ./
COPY prisma ./prisma
RUN npx prisma generate

COPY tsconfig.json ./
COPY src ./src
COPY sql ./sql
RUN npm run build

# Reinstala sem as dependências de desenvolvimento, para copiar um node_modules
# já enxuto para a etapa seguinte.
RUN npm ci --omit=dev

# ---------- etapa 2: runtime ----------
FROM node:24-slim AS runtime

ENV NODE_ENV=production
WORKDIR /app

COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist

# `prisma migrate deploy` roda a partir desta imagem (ver render.yaml), então o
# schema, as migrações e o prisma.config.ts precisam vir junto.
COPY --from=build /app/prisma ./prisma
COPY --from=build /app/prisma.config.ts ./prisma.config.ts

# O prisma.config.ts importa `./src/db/caminho` para resolver o caminho do banco
# do mesmo jeito que o runtime resolve (ver o comentário lá). É o ÚNICO arquivo
# de `src/` que a imagem de runtime precisa: sem ele, `prisma migrate deploy`
# falha no deploy com "Cannot find module", depois de a imagem já ter sido
# construída com sucesso.
COPY --from=build /app/src/db/caminho.ts ./src/db/caminho.ts

# `npm run db:view` LÊ este arquivo em runtime. Sem ele na imagem, o passo que
# recria a view depois da migração falha por arquivo ausente.
COPY --from=build /app/sql ./sql

COPY package.json ./

# Diretório do banco, criado ANTES de trocar de usuário e com dono `node`.
#
# É onde o disco persistente é montado em produção (ver render.yaml). Existir na
# imagem serve a dois casos: rodar o contêiner sem volume nenhum (o banco fica
# na camada de escrita e some no próximo deploy - bom para experimentar, nunca
# para valer), e garantir que, COM volume montado, o ponto de montagem já
# pertença ao usuário que vai escrever nele. Sem isso o `node` não consegue criar
# o arquivo e o processo sobe para morrer na primeira mensagem.
RUN mkdir -p /app/dados && chown -R node:node /app/dados
VOLUME /app/dados

# Não roda como root. A imagem oficial do Node já traz o usuário `node`.
USER node

EXPOSE 3000

# Liveness. Bate no /health de propósito, e não no /ready: a pergunta aqui é "o
# processo está vivo?". Reiniciar o contêiner porque o banco está inacessível não
# conserta o disco - quem tira a instância de rotação nesse caso é o
# balanceador, e é ele que usa o /ready.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

# Sem init/tini de propósito: o server.ts já registra handler de SIGTERM (para
# de aceitar conexão, deixa as requisições em voo terminarem, fecha o arquivo do
# banco). Como o handler existe, o node rodando como PID 1 encerra limpo - e com
# SQLite fechar limpo importa mais: é o que faz o WAL ser incorporado ao arquivo
# em vez de ficar pendente.
CMD ["node", "dist/server.js"]

# ---------- etapa 3: painel ----------
#
# O painel de chamados (servidor-painel.mjs + activity-dashboard) roda como um
# SEGUNDO contêiner, ao lado do bot. Fora de contêiner os dois sobem juntos pelo
# `iniciar.mjs`, num processo só; aqui eles se separam porque no compose cada
# serviço tem o seu ciclo de vida, e derrubar o painel para reiniciar o bot (ou
# o contrário) não faz sentido nenhum.
#
# O que os liga é `BOT_HOST`: o painel repassa `/webhook` e `/internal/*` para
# `${BOT_HOST}:${BOT_PORT}` — no compose, o nome do serviço do bot na rede
# interna. Sem a variável ele usa 127.0.0.1 e o comportamento antigo continua
# valendo (ver o comentário em servidor-painel.mjs).
#
# Não há build aqui: os arquivos do painel são .mjs, executados como estão. A
# única dependência que ele importa de node_modules é o dotenv, e por isso a
# camada vem pronta da etapa de build, já sem devDependencies.
FROM node:24-slim AS painel

ENV NODE_ENV=production
WORKDIR /app

COPY --from=build /app/node_modules ./node_modules

COPY package.json ./
COPY servidor-painel.mjs painel-entra.mjs painel-metricas.mjs ./
COPY activity-dashboard ./activity-dashboard

USER node

EXPOSE 8511

# O painel serve a si mesmo em `/`; se ele responde, está de pé. O estado do bot
# é problema do healthcheck do bot — o painel sobe e fica útil (mostrando o erro
# de proxy) mesmo com o bot fora, o que é melhor que os dois reiniciando juntos.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://127.0.0.1:'+(process.env.PAINEL_PORT||8511)+'/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "servidor-painel.mjs"]
