"""
O histórico que vai como contexto para o modelo.

Este arquivo já testou um cache read-through no Redis — inclusive a
invalidação, que ele mesmo chamava antes de reler. O cache saiu (ver
`memory_service`), e com ele os casos que provavam que os métodos existiam.
O que decide se o agente lembra do turno anterior está em
`test_webhook.py::test_segunda_mensagem_enxerga_a_primeira`, que olha o que
chega ao modelo no segundo turno.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
from app.services.memory_service import MemoryService
from app.db.models import Message
from sqlalchemy.ext.asyncio import AsyncSession


def _db_devolvendo(mensagens):
    """Um `AsyncSession` falso que devolve estas mensagens.

    Ordenadas por timestamp decrescente, como a consulta real faz — confiar na
    ordem em que o teste as escreveu esconderia o `reversed` do serviço.
    """
    db = AsyncMock(spec=AsyncSession)
    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = sorted(
        mensagens, key=lambda m: m.timestamp, reverse=True
    )
    db.execute = AsyncMock(return_value=resultado)
    return db


class TestHistoricoDaConversa:
    @pytest.mark.asyncio
    async def test_conversa_nova_devolve_lista_vazia(self):
        historico = await MemoryService().get_conversation_history(
            "conv-vazia", _db_devolvendo([])
        )

        assert historico == []

    @pytest.mark.asyncio
    async def test_mensagens_vem_da_mais_antiga_para_a_mais_recente(self):
        # A consulta ordena DESC para que o LIMIT pegue as *últimas*
        # mensagens; o modelo precisa lê-las na ordem em que aconteceram.
        agora = datetime.utcnow()
        mensagens = [
            Message(
                id="msg-1",
                conversation_id="conv-ordem",
                remetente="user",
                conteudo="Primeira",
                timestamp=agora,
            ),
            Message(
                id="msg-2",
                conversation_id="conv-ordem",
                remetente="assistant",
                conteudo="Segunda",
                timestamp=agora + timedelta(seconds=1),
            ),
            Message(
                id="msg-3",
                conversation_id="conv-ordem",
                remetente="user",
                conteudo="Terceira",
                timestamp=agora + timedelta(seconds=2),
            ),
        ]

        historico = await MemoryService().get_conversation_history(
            "conv-ordem", _db_devolvendo(mensagens)
        )

        assert [m["content"] for m in historico] == [
            "Primeira",
            "Segunda",
            "Terceira",
        ]

    @pytest.mark.asyncio
    async def test_o_operador_entra_como_escritorio_e_nao_como_cliente(self):
        # Cliente é `user`; todo o resto é o escritório falando. Com a
        # comparação ao contrário, a mensagem digitada à mão pelo operador
        # entrava como se fosse do cliente e o modelo respondia à própria
        # resposta do escritório — o atendimento conversando sozinho.
        agora = datetime.utcnow()
        mensagens = [
            Message(
                id="msg-1",
                conversation_id="conv-papeis",
                remetente="user",
                conteudo="Fui demitido",
                timestamp=agora,
            ),
            Message(
                id="msg-2",
                conversation_id="conv-papeis",
                remetente="assistant",
                conteudo="Em que mês?",
                timestamp=agora + timedelta(seconds=1),
            ),
            Message(
                id="msg-3",
                conversation_id="conv-papeis",
                remetente="operador",
                conteudo="Aqui é o Dr. Tássio, assumo daqui",
                timestamp=agora + timedelta(seconds=2),
            ),
        ]

        historico = await MemoryService().get_conversation_history(
            "conv-papeis", _db_devolvendo(mensagens)
        )

        assert [m["role"] for m in historico] == ["user", "assistant", "assistant"]

    @pytest.mark.asyncio
    async def test_falha_no_banco_nao_passa_despercebida(self):
        from app.utils.exceptions import ValidationException

        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock(side_effect=RuntimeError("conexão caiu"))

        with pytest.raises(ValidationException):
            await MemoryService().get_conversation_history("conv-erro", db)
