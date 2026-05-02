# Backend Go

Servidor HTTP/WebSocket do CollabCanvas.

## Fase 1

Comandos equivalentes ao setup inicial:

```powershell
go mod init collabcanvas/backend
go get github.com/gorilla/websocket
go run ./cmd/server
```

Endpoints:

- `GET /healthz`: healthcheck simples.
- `GET /ws`: conexão WebSocket do mural.

Mensagens atuais do servidor:

- `init`: estado inicial completo do board em memória.
- `presence`: quantidade de usuários conectados.
- `draw`: pixel atualizado e propagado a todos os clientes.
- `cooldown`: cliente tentou pintar antes dos 3 segundos.
- `error`: entrada inválida.

## Fase 2

Mensagem de desenho enviada pelo cliente:

```json
{"action":"draw","x":10,"y":20,"color":"#ff0000"}
```

Validações atuais:

- `x` e `y` precisam estar dentro do board `100x100`.
- `color` precisa estar em hexadecimal `#rrggbb`.
- cada conexão WebSocket pode pintar 1 pixel a cada 3 segundos.
