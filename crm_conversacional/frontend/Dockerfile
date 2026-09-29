# Imagem de desenvolvimento: o código é montado por volume no docker-compose,
# então o hot reload do Next continua funcionando dentro do container.
FROM node:20-alpine

WORKDIR /app

# Instala as dependências em camada própria para aproveitar o cache do Docker
# quando só o código-fonte muda.
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
