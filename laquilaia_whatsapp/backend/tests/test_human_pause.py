"""
Testes da pausa humana (Fase 16).

O ponto crítico é o orquestrador: com a conversa pausada a mensagem do cliente
ainda é registrada, mas a IA não responde — senão operador e agente falariam
ao mesmo tempo com o cliente.
"""
from tests.conftest import criar_acesso

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Message, User
from app.services.message_orchestrator import orchestrator
from app.utils.exceptions import ValidationException

client = TestClient(app)


def _login(suffix: str) -> dict:
    creds = {
        "email": f"pause-{suffix}@example.com",
        "nome": "Pause User",
        "senha": "SenhaSegura123!",
    }
    criar_acesso(client, creds["email"], creds["senha"], creds.get("nome", "Teste"))
    r = client.post(
        "/api/v1/auth/login", json={"email": creds["email"], "senha": creds["senha"]}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed(agent_id: str, user_id: str, conv_id: str) -> None:
    async with AsyncSessionLocal() as db:
        db.add(
            User(id=user_id, email=f"{user_id}@x.com", nome="Dono",
                 senha_hash="x", status="ativo")
        )
        await db.flush()
        db.add(
            Agent(id=agent_id, user_id=user_id, nome="Agente",
                  system_prompt="p", temperatura=0.7, max_tokens=1024, status="ativo")
        )
        await db.flush()
        db.add(
            Conversation(id=conv_id, agent_id=agent_id,
                         phone_number="5561900001111", status="ativa")
        )
        await db.commit()


class TestOrchestratorRespectsPause:
    @pytest.mark.asyncio
    async def test_paused_conversation_does_not_call_the_model(self):
        await _seed("ag-pause", "user-pause", "conv-pause")

        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.id == "conv-pause")
            )).scalars().first()
            conv.status = "pausada"
            await db.commit()

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            async with AsyncSessionLocal() as db:
                result = await orchestrator.process_incoming_message(
                    "ag-pause", "5561900001111", "Oi", db
                )

        assert result["paused"] is True
        assert result["response"] is None
        # O que realmente importa: nada de chamada paga ao Claude.
        mock_llm.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_paused_conversation_still_records_the_message(self):
        await _seed("ag-rec", "user-rec", "conv-rec")

        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.id == "conv-rec")
            )).scalars().first()
            conv.status = "pausada"
            await db.commit()

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ):
            async with AsyncSessionLocal() as db:
                await orchestrator.process_incoming_message(
                    "ag-rec", "5561900001111", "Preciso de ajuda", db
                )

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(
                select(Message).where(Message.conversation_id == "conv-rec")
            )).scalars().all()

        # A mensagem do cliente não pode se perder: o operador precisa vê-la.
        assert len(msgs) == 1
        assert msgs[0].remetente == "user"
        assert msgs[0].conteudo == "Preciso de ajuda"

    @pytest.mark.asyncio
    async def test_active_conversation_still_answers(self):
        await _seed("ag-act", "user-act", "conv-act")

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm, patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
        ) as mock_wa:
            mock_llm.return_value = ("Claro!", {"input_tokens": 1, "output_tokens": 1,
                                                "total_tokens": 2})
            mock_wa.return_value = {"success": True, "message_id": "m1"}

            async with AsyncSessionLocal() as db:
                result = await orchestrator.process_incoming_message(
                    "ag-act", "5561900001111", "Oi", db
                )

        assert result.get("paused") is None
        mock_llm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_o_cliente_recebe_a_resposta_antes_do_parecer(self):
        """
        A ordem entre enviar e qualificar é de produto, não de arrumação.

        A qualificação dispara o parecer jurídico, que é uma segunda chamada ao
        modelo: 2 minutos no Opus 5, medido contra a API real. Qualificando
        primeiro, o cliente esperava esses 2 minutos por uma mensagem de
        fechamento — e o parecer é um texto que ele nunca vai ler.
        """
        await _seed("ag-ordem", "user-ordem", "conv-ordem")
        ordem = []

        async def envio(*args, **kwargs):
            ordem.append("envio")
            return {"success": True, "message_id": "m1"}

        async def qualificacao(*args, **kwargs):
            ordem.append("qualificacao")
            return {"success": False}

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm, patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=envio,
        ), patch(
            "app.services.lead_processor.lead_processor.process_response",
            new=qualificacao,
        ):
            mock_llm.return_value = (
                "Pronto, o advogado te procura.",
                {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            )

            async with AsyncSessionLocal() as db:
                await orchestrator.process_incoming_message(
                    "ag-ordem", "5561900001111", "obrigado", db
                )

        assert ordem == ["envio", "qualificacao"]


class TestPauseEndpoints:
    def _agent_and_conversation(self, headers: dict) -> str:
        agent_id = client.post(
            "/api/v1/agents", headers=headers,
            json={"nome": "A", "system_prompt": "p", "temperatura": 0.7,
                  "max_tokens": 1024},
        ).json()["id"]

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = ("oi", {"input_tokens": 1, "output_tokens": 1,
                                            "total_tokens": 2})
            r = client.post(
                f"/api/v1/agents/{agent_id}/chat", headers=headers,
                json={"message": "Oi"},
            )
        return r.json()["conversation_id"]

    def test_pause_then_resume(self):
        headers = _login("endpoints")
        conv_id = self._agent_and_conversation(headers)

        pausa = client.post(f"/api/v1/conversations/{conv_id}/pause", headers=headers)
        assert pausa.status_code == 200
        assert pausa.json()["ia_ativa"] is False

        retoma = client.post(f"/api/v1/conversations/{conv_id}/resume", headers=headers)
        assert retoma.status_code == 200
        assert retoma.json()["ia_ativa"] is True

    def test_status_reflects_the_pause(self):
        headers = _login("status")
        conv_id = self._agent_and_conversation(headers)

        client.post(f"/api/v1/conversations/{conv_id}/pause", headers=headers)
        body = client.get(
            f"/api/v1/conversations/{conv_id}/status", headers=headers
        ).json()

        assert body["status"] == "pausada"
        assert body["ia_ativa"] is False

    def test_requires_authentication(self):
        r = client.post("/api/v1/conversations/qualquer/pause")

        assert r.status_code in (401, 403)

    def test_cannot_pause_another_users_conversation(self):
        dono = _login("dono")
        conv_id = self._agent_and_conversation(dono)
        intruso = _login("intruso")

        r = client.post(f"/api/v1/conversations/{conv_id}/pause", headers=intruso)

        assert r.status_code == 404

    def test_unknown_conversation_is_404(self):
        headers = _login("desconhecida")

        r = client.post("/api/v1/conversations/nao-existe/pause", headers=headers)

        assert r.status_code == 404


class TestListagemDeConversas:
    """
    Sem listagem, os endpoints de pausa eram inalcançáveis pelo painel: os três
    recebem um `conversation_id` que o operador não tinha por onde descobrir.
    """

    async def _conversa_real(self, agent_id: str, telefone: str, nome_lead: str | None):
        """Cria uma conversa como as que chegam do WhatsApp, com mensagens."""
        from datetime import datetime, timedelta

        from app.db.models import Lead

        conv_id = f"conv-{telefone}"
        async with AsyncSessionLocal() as db:
            db.add(
                Conversation(
                    id=conv_id,
                    agent_id=agent_id,
                    phone_number=telefone,
                    status="ativa",
                    data_ultima_msg=datetime.utcnow(),
                )
            )
            await db.flush()
            db.add(
                Message(
                    conversation_id=conv_id,
                    remetente="user",
                    conteudo="Primeira",
                    timestamp=datetime.utcnow() - timedelta(minutes=2),
                )
            )
            db.add(
                Message(
                    conversation_id=conv_id,
                    remetente="assistant",
                    conteudo="Resposta da IA",
                    timestamp=datetime.utcnow() - timedelta(minutes=1),
                )
            )
            if nome_lead:
                db.add(
                    Lead(
                        phone_number=telefone,
                        conversation_id=conv_id,
                        nome=nome_lead,
                        status_funil="qualificado",
                    )
                )
            await db.commit()
        return conv_id

    def _agente(self, headers: dict) -> str:
        return client.post(
            "/api/v1/agents",
            headers=headers,
            json={"nome": "A", "system_prompt": "p", "temperatura": 0.7,
                  "max_tokens": 1024},
        ).json()["id"]

    async def test_lista_traz_nome_do_lead_e_ultima_mensagem(self):
        headers = _login("lista")
        agent_id = self._agente(headers)
        await self._conversa_real(agent_id, "5561900002222", "Maria Silva")

        r = client.get(f"/api/v1/agents/{agent_id}/conversations", headers=headers)

        assert r.status_code == 200
        item = r.json()[0]
        assert item["lead_nome"] == "Maria Silva"
        assert item["total_mensagens"] == 2
        assert item["ultima_mensagem"] == "Resposta da IA"
        assert item["ultimo_remetente"] == "assistant"
        assert item["ia_ativa"] is True

    async def test_conversa_do_playground_fica_de_fora(self):
        """
        O playground é o desenvolvedor testando o prompt, não um cliente
        esperando atendimento — misturá-lo na fila do operador seria ruído.
        """
        headers = _login("playground")
        agent_id = self._agente(headers)

        # Cria a conversa do playground pelo caminho normal.
        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
        ) as mock_llm:
            mock_llm.return_value = ("oi", {"input_tokens": 1, "output_tokens": 1,
                                            "total_tokens": 2})
            client.post(
                f"/api/v1/agents/{agent_id}/chat", headers=headers,
                json={"message": "Oi"},
            )

        await self._conversa_real(agent_id, "5561900003333", "Cliente Real")

        corpo = client.get(
            f"/api/v1/agents/{agent_id}/conversations", headers=headers
        ).json()

        assert [c["phone_number"] for c in corpo] == ["5561900003333"]

    async def test_lista_ordena_da_mais_recente_para_a_mais_antiga(self):
        from datetime import datetime, timedelta

        headers = _login("ordem")
        agent_id = self._agente(headers)
        antiga = await self._conversa_real(agent_id, "5561900004444", "Antiga")
        recente = await self._conversa_real(agent_id, "5561900005555", "Recente")

        async with AsyncSessionLocal() as db:
            conv = (await db.execute(
                select(Conversation).where(Conversation.id == antiga)
            )).scalars().first()
            conv.data_ultima_msg = datetime.utcnow() - timedelta(days=2)
            await db.commit()

        corpo = client.get(
            f"/api/v1/agents/{agent_id}/conversations", headers=headers
        ).json()

        assert [c["id"] for c in corpo] == [recente, antiga]

    async def test_lead_ausente_nao_quebra_a_lista(self):
        """Conversa sem lead ainda extraído aparece, só sem nome."""
        headers = _login("sem-lead")
        agent_id = self._agente(headers)
        await self._conversa_real(agent_id, "5561900006666", None)

        item = client.get(
            f"/api/v1/agents/{agent_id}/conversations", headers=headers
        ).json()[0]

        assert item["lead_nome"] is None
        assert item["phone_number"] == "5561900006666"

    async def test_lista_de_agente_alheio_e_404(self):
        dono = _login("dono-lista")
        agent_id = self._agente(dono)
        await self._conversa_real(agent_id, "5561900007777", "X")
        intruso = _login("intruso-lista")

        r = client.get(f"/api/v1/agents/{agent_id}/conversations", headers=intruso)

        assert r.status_code == 404

    def test_lista_exige_autenticacao(self):
        r = client.get("/api/v1/agents/qualquer/conversations")

        assert r.status_code in (401, 403)


class TestMensagensDaConversa:
    """O operador precisa ler o que já foi dito antes de assumir."""

    async def _conversa_com_mensagens(self, headers: dict) -> str:
        from datetime import datetime, timedelta

        agent_id = client.post(
            "/api/v1/agents", headers=headers,
            json={"nome": "A", "system_prompt": "p", "temperatura": 0.7,
                  "max_tokens": 1024},
        ).json()["id"]

        conv_id = f"conv-msgs-{agent_id[:8]}"
        base = datetime.utcnow()
        async with AsyncSessionLocal() as db:
            db.add(
                Conversation(id=conv_id, agent_id=agent_id,
                             phone_number="5561900008888", status="ativa")
            )
            await db.flush()
            # Inseridas fora de ordem de propósito: a ordenação é do banco.
            db.add(Message(conversation_id=conv_id, remetente="assistant",
                           conteudo="Segunda", timestamp=base))
            db.add(Message(conversation_id=conv_id, remetente="user",
                           conteudo="Primeira", timestamp=base - timedelta(minutes=5)))
            await db.commit()
        return conv_id

    async def test_transcricao_vem_da_mais_antiga_para_a_mais_recente(self):
        headers = _login("msgs")
        conv_id = await self._conversa_com_mensagens(headers)

        corpo = client.get(
            f"/api/v1/conversations/{conv_id}/messages", headers=headers
        ).json()

        assert [m["conteudo"] for m in corpo["messages"]] == ["Primeira", "Segunda"]

    async def test_traz_o_estado_da_automacao_junto(self):
        """
        Evita uma segunda chamada só para o botão saber se mostra "pausar" ou
        "retomar".
        """
        headers = _login("msgs-estado")
        conv_id = await self._conversa_com_mensagens(headers)
        client.post(f"/api/v1/conversations/{conv_id}/pause", headers=headers)

        corpo = client.get(
            f"/api/v1/conversations/{conv_id}/messages", headers=headers
        ).json()

        assert corpo["status"] == "pausada"
        assert corpo["ia_ativa"] is False

    async def test_mensagens_de_conversa_alheia_sao_404(self):
        dono = _login("dono-msgs")
        conv_id = await self._conversa_com_mensagens(dono)
        intruso = _login("intruso-msgs")

        r = client.get(
            f"/api/v1/conversations/{conv_id}/messages", headers=intruso
        )

        assert r.status_code == 404

    def test_mensagens_exigem_autenticacao(self):
        r = client.get("/api/v1/conversations/qualquer/messages")

        assert r.status_code in (401, 403)


class TestOperadorResponde:
    """
    O operador escrevendo ao cliente pelo painel.

    Antes disto, assumir a conversa parava a IA e mais nada: para responder, a
    pessoa abria o WhatsApp no celular, e a mensagem nunca entrava na
    transcrição. Quem lesse o atendimento depois via a conversa com um buraco.
    """

    def _preparar(self, sufixo: str):
        headers = _login(sufixo)
        agent_id = client.post(
            "/api/v1/agents",
            headers=headers,
            json={"nome": "A", "system_prompt": "p", "temperatura": 0.7, "max_tokens": 1024},
        ).json()["id"]
        return headers, agent_id

    async def _conversa(self, agent_id: str, conv_id: str, status: str):
        async with AsyncSessionLocal() as db:
            db.add(
                Conversation(
                    id=conv_id,
                    agent_id=agent_id,
                    phone_number=f"5561{conv_id[-6:]}",
                    status=status,
                )
            )
            await db.commit()

    @pytest.mark.asyncio
    async def test_com_a_ia_ativa_recusa_com_409(self):
        """
        Não é erro de digitação: é o operador falando por cima do agente. Os
        dois responderiam à mesma pergunta, e o cliente receberia duas versões
        da mesma resposta — pior que demorar.
        """
        headers, agent_id = self._preparar("op-409")
        await self._conversa(agent_id, "conv-op409", "ativa")

        r = client.post(
            "/api/v1/conversations/conv-op409/mensagens",
            json={"conteudo": "Oi, aqui é a Dra. Helena."},
            headers=headers,
        )

        assert r.status_code == 409
        assert "Assuma a conversa" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_pausada_envia_e_grava_na_transcricao(self):
        headers, agent_id = self._preparar("op-ok")
        await self._conversa(agent_id, "conv-opok", "pausada")

        with patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
        ) as envio:
            envio.return_value = {"success": True, "message_id": "m1"}

            r = client.post(
                "/api/v1/conversations/conv-opok/mensagens",
                json={"conteudo": "Bom dia, seu caso está comigo."},
                headers=headers,
            )

        assert r.status_code == 201
        assert r.json()["remetente"] == "operador"
        envio.assert_awaited_once()

        transcricao = client.get(
            "/api/v1/conversations/conv-opok/messages", headers=headers
        ).json()
        assert transcricao["messages"][-1]["conteudo"] == "Bom dia, seu caso está comigo."

    @pytest.mark.asyncio
    async def test_envio_recusado_nao_grava_mensagem(self):
        """
        Gravar o que a Evolution recusou faria a transcrição mentir: o
        escritório leria uma resposta que o cliente nunca recebeu.
        """
        headers, agent_id = self._preparar("op-falha")
        await self._conversa(agent_id, "conv-opfalha", "pausada")

        with patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
            side_effect=ValidationException("Evolution fora do ar"),
        ):
            r = client.post(
                "/api/v1/conversations/conv-opfalha/mensagens",
                json={"conteudo": "teste"},
                headers=headers,
            )

        assert r.status_code == 502

        transcricao = client.get(
            "/api/v1/conversations/conv-opfalha/messages", headers=headers
        ).json()
        assert transcricao["messages"] == []

    @pytest.mark.asyncio
    async def test_conversa_de_outro_dono_e_404(self):
        headers, agent_id = self._preparar("op-dono")
        await self._conversa(agent_id, "conv-opdono", "pausada")
        alheio = _login("op-alheio")

        r = client.post(
            "/api/v1/conversations/conv-opdono/mensagens",
            json={"conteudo": "oi"},
            headers=alheio,
        )

        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_mensagem_vazia_e_recusada(self):
        headers, agent_id = self._preparar("op-vazio")
        await self._conversa(agent_id, "conv-opvazio", "pausada")

        r = client.post(
            "/api/v1/conversations/conv-opvazio/mensagens",
            json={"conteudo": ""},
            headers=headers,
        )

        assert r.status_code == 422


class TestHistoricoParaOModelo:
    async def test_a_fala_do_operador_nao_vira_pergunta_do_cliente(self):
        """
        O mapeamento era `"assistant" if remetente == "assistant" else "user"`.
        Com ele, a mensagem escrita à mão pelo operador entraria no histórico
        como se fosse o cliente: o modelo leria a própria resposta do
        escritório como pergunta e responderia a ela — o atendimento
        conversando sozinho.
        """
        from unittest.mock import MagicMock

        from app.services.memory_service import memory_service

        def _msg(remetente, conteudo):
            m = MagicMock()
            m.remetente = remetente
            m.conteudo = conteudo
            return m

        db = AsyncMock()
        resultado = MagicMock()
        # A query ordena do mais recente para o mais antigo.
        resultado.scalars.return_value.all.return_value = [
            _msg("operador", "Bom dia, seu caso está comigo."),
            _msg("user", "tem alguém aí?"),
        ]
        db.execute = AsyncMock(return_value=resultado)

        historico = await memory_service._fetch_from_db("conv-1", db, limit=10)

        assert [m["role"] for m in historico] == ["user", "assistant"]
