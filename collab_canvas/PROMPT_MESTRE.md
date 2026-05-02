# Prompt Mestre: CollabCanvas (Mural Multiplayer em Tempo Real)

*Copie e cole este prompt para iniciarmos a construção do projeto passo a passo.*

---

**[COPIE A PARTIR DAQUI]**

Você vai atuar como um Desenvolvedor Full-Stack Senior especializado em Sistemas de Tempo Real e Arquiteturas Escaláveis. Nosso objetivo é construir o "**CollabCanvas**", uma recriação da famosa experiência do r/place do Reddit. O projeto consiste em um mural de pixel art de tamanho fixo (ex: 100x100 pixels) onde múltiplos usuários conectados simultaneamente podem desenhar em tempo real.

### 🎯 Arquitetura e Tech Stack Escolhida
*   **Backend:** Go (Golang) utilizando o pacote `gorilla/websocket` para lidar com conexões persistentes e alta concorrência de eventos.
*   **Frontend:** Next.js (React) utilizando a API do `HTML5 Canvas` para garantir alta performance de renderização visual (sem os gargalos de performance do DOM). Estilização via TailwindCSS.
*   **Estado:** Inicialmente, o estado do Canvas será mantido na memória do servidor Go (usando Mutexes para evitar *race conditions*).

### 🚀 Funcionalidades Core (Escopo da V1)
1.  **Sincronização Inicial Eficiente:** Quando o cliente entra na página, o servidor envia o estado completo da matriz de pixels de forma compacta.
2.  **Desenho Simultâneo:** Ao clicar no canvas com uma cor selecionada, o cliente envia uma mensagem WS `{"action": "draw", "x": 10, "y": 20, "color": "#ff0000"}`.
3.  **Broadcast Imediato:** O servidor valida o pixel, atualiza o estado em memória e propaga o evento de mudança para **todos** os outros clientes, que renderizam a mudança imediatamente no Canvas.
4.  **Mecânica de Cooldown:** Para o jogo ter estratégia e não virar bagunça, cada jogador só pode pintar 1 pixel a cada 3 segundos. O frontend deve exibir um timer circular animado bloqueando novos cliques.
5.  **Presença de Usuários:** Um contador ao vivo mostrando o número de conexões ativas na sala.

### 🛠️ Passos de Implementação

Por favor, gere os comandos e o código estruturado seguindo esta exata ordem de fases. Inicie o desenvolvimento perguntando se estou pronto para o Passo 1.

**Fase 1: Setup do Motor Backend (Go)**
1. Criação do módulo Go e servidor HTTP/WebSocket.
2. Estruturação da matriz 2D de pixels protegida por `sync.RWMutex`.
3. Lógica do Hub: registro de clientes e broadcast.

**Fase 2: Comunicação de Eventos**
1. Parse das mensagens JSON de entrada.
2. Lógica de atualização de estado e proteção contra entradas inválidas (out-of-bounds).
3. Lógica de Cooldown associada a um ID de cliente/sessão.

**Fase 3: Setup do Frontend (Next.js)**
1. Inicialização do Next.js com TailwindCSS.
2. Criação da UI ao redor: Seletor de Cores, Contador de Usuários e Timer de Cooldown. 
3. *Design Aesthetic*: O tema deve ser um dark-mode premium, com neon glow suave e interface minimalista inspirada em jogos web modernos.

**Fase 4: A Mágica do Canvas**
1. Componente de Board utilizando `<canvas>`.
2. Lógica para converter o clique do mouse (coordenadas do viewport) para a escala da matriz (coordenadas de grade).
3. Conexão do WebSocket (reconectar automaticamente em caso de queda) e desenho nativo via Context2D (`ctx.fillStyle` e `ctx.fillRect`).

**Regras de Código:**
*   Documente funções críticas em Go, especialmente onde houver controle de concorrência.
*   Crie abstrações limpas no React (ex: um hook customizado `useWebSocketBoard`).
*   Priorize um visual moderno e "wow factor" no frontend.

Pode iniciar a Fase 1!

**[FIM DA CÓPIA]**
