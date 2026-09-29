"""
Real-time channel manager.

Um canal por agente: o dashboard acompanha um agente por vez, e agrupar por
agente evita abrir uma conexão por conversa.

O fluxo é **só do servidor para o cliente**. A versão anterior retransmitia o
que o cliente mandava, o que deixava qualquer conexão injetar conteúdo falso
no painel de todo mundo que estivesse no mesmo canal.
"""

from typing import Any, Dict, List

from fastapi import WebSocket

from app.utils.logger import logger


class ConnectionManager:
    """Keeps the open sockets grouped by agent."""

    def __init__(self) -> None:
        self._channels: Dict[str, List[WebSocket]] = {}

    async def connect(self, agent_id: str, websocket: WebSocket) -> None:
        """Accept the socket and register it on the agent's channel."""
        await websocket.accept()
        self._channels.setdefault(agent_id, []).append(websocket)
        logger.info(
            f"✅ WebSocket conectado: agente={agent_id} "
            f"({len(self._channels[agent_id])} no canal)"
        )

    def disconnect(self, agent_id: str, websocket: WebSocket) -> None:
        """Drop the socket; remove the channel once it is empty."""
        sockets = self._channels.get(agent_id)
        if not sockets:
            return

        if websocket in sockets:
            sockets.remove(websocket)
        if not sockets:
            del self._channels[agent_id]

        logger.info(f"❌ WebSocket desconectado: agente={agent_id}")

    async def broadcast(self, agent_id: str, event: Dict[str, Any]) -> int:
        """
        Send an event to everyone watching the agent.

        Sockets que falharem no envio já morreram: são removidos aqui, senão o
        canal acumularia conexões mortas até o processo reiniciar. Retorna
        quantos clientes receberam.
        """
        sockets = list(self._channels.get(agent_id, []))
        if not sockets:
            return 0

        entregues = 0
        for socket in sockets:
            try:
                await socket.send_json(event)
                entregues += 1
            except Exception as e:
                logger.warning(f"⚠️ Removendo socket morto do canal {agent_id}: {e}")
                self.disconnect(agent_id, socket)

        return entregues

    def connection_count(self, agent_id: str) -> int:
        """How many clients are currently watching this agent."""
        return len(self._channels.get(agent_id, []))


connection_manager = ConnectionManager()


# ========== EVENTOS ==========
#
# Os nomes são o contrato com o frontend (`hooks/useAgentEvents.ts`);
# mudá-los exige mudar os dois lados.

EVENT_LEAD_MOVED = "lead_moved"
EVENT_NEW_MESSAGE = "new_message"


async def notify_lead_moved(
    agent_id: str, lead_id: str, target_column_id: str, status_funil: str
) -> None:
    """Um lead mudou de etapa — o board precisa se atualizar."""
    await connection_manager.broadcast(
        agent_id,
        {
            "type": EVENT_LEAD_MOVED,
            "lead_id": lead_id,
            "column_id": target_column_id,
            "status_funil": status_funil,
        },
    )


async def notify_new_message(
    agent_id: str, conversation_id: str, phone_number: str
) -> None:
    """
    Chegou mensagem nova numa conversa do WhatsApp.

    O evento não carrega o conteúdo: quem estiver na tela busca o que precisa
    pela API, que já aplica a checagem de dono. Assim o socket não vira um
    caminho paralelo para vazar dados de conversa.
    """
    await connection_manager.broadcast(
        agent_id,
        {
            "type": EVENT_NEW_MESSAGE,
            "conversation_id": conversation_id,
            "phone_number": phone_number,
        },
    )
