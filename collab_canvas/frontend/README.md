# Frontend Next.js

Cliente web do CollabCanvas com Next.js, TailwindCSS e HTML5 Canvas.

## Fase 3 e 4

Comandos equivalentes ao setup:

```powershell
npm install
npm run dev
```

Por padrao o cliente tenta conectar em `ws://localhost:8080/ws`.
Para alterar:

```powershell
$env:NEXT_PUBLIC_WS_URL="ws://localhost:8080/ws"
npm run dev
```
