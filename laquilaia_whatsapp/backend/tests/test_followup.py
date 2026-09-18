"""
Cutucar quem sumiu, e desistir na hora certa.

O sintoma: o agente pergunta o salário, a pessoa não responde, e a conversa
fica ali para sempre. O lead ocupa a primeira coluna do funil
indefinidamente, e ninguém sabe se desistiu ou se só não viu — as duas coisas
têm a mesma aparência no painel.

Três grupos de caso, e o segundo é o que impede o produto de virar spam:
quando cutucar, quando **não** cutucar, e o que acontece quando a cota acaba.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Lead, LeadTimeline, Message, User
from app.services import followup_service
from app.services.followup_service import (
    TEXTO_DE_ENCERRAMENTO,
    conversas_para_cutucar,
    dentro_do_horario,
    processar,
    texto_do_followup,
)

PERGUNTA = "Qual era o seu salário registrado na carteira?"


async def _cenario(
    sufixo: str,
    *,
    quem_falou_por_ultimo: str = "assistant",
    minutos_atras: int = 60,
    status: str = "ativa",
    followups: int = 0,
    ultimo_followup_min: int | None = None,
    com_lead: bool = True,
    texto: str = PERGUNTA,
    fase: str = "triagem",
) -> str:
    quando = datetime.utcnow() - timedelta(minutes=minutos_atras)
    async with AsyncSessionLocal() as db:
        db.add(User(id=f"u-{sufixo}", email=f"{sufixo}@x.com", nome="Dono",
                    senha_hash="h", status="ativo", papel="admin"))
        await db.flush()
        db.add(Agent(id=f"ag-{sufixo}", user_id=f"u-{sufixo}", nome="Triagem",
                     system_prompt="p", temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(
            Conversation(
                id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                phone_number=f"5561{abs(hash(sufixo)) % 100000000:08d}",
                status=status, followups_enviados=followups,
                ultimo_followup_em=(
                    datetime.utcnow() - timedelta(minutes=ultimo_followup_min)
                    if ultimo_followup_min is not None
                    else None
                ),
                fase=fase,
            )
        )
        await db.flush()

        db.add(Message(conversation_id=f"cv-{sufixo}", remetente="user",
                       conteudo="oi", timestamp=quando - timedelta(minutes=5)))
        db.add(Message(conversation_id=f"cv-{sufixo}", remetente=quem_falou_por_ultimo,
                       conteudo=texto, timestamp=quando))

        if com_lead:
            db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                        nome="Marina Silva", phone_number=f"5561{sufixo}",
                        status_funil="em_qualificacao"))
        await db.commit()
    return f"cv-{sufixo}"


def _envio_ok():
    return patch(
        "app.services.whatsapp_service.whatsapp_service.send_message",
        new_callable=AsyncMock,
        return_value={"success": True, "message_id": "m1"},
    )


async def _conversa(conv_id: str) -> Conversation:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(Conversation).where(Conversation.id == conv_id))
        ).scalars().first()


class TestQuandoCutucar:
    @pytest.mark.asyncio
    async def test_silencio_do_cliente_vence_o_prazo(self):
        await _cenario("a1", minutos_atras=60)

        async with AsyncSessionLocal() as db:
            devidas = await conversas_para_cutucar(db)

        assert [c.id for c, _, _ in devidas] == ["cv-a1"]

    @pytest.mark.asyncio
    async def test_silencio_curto_ainda_nao_conta(self):
        """Quinze minutos é o piso; cinco é a pessoa terminando de digitar."""
        await _cenario("a2", minutos_atras=5)

        async with AsyncSessionLocal() as db:
            assert await conversas_para_cutucar(db) == []

    @pytest.mark.asyncio
    async def test_o_relogio_da_segunda_tentativa_conta_do_primeiro_followup(self):
        """
        Sem isto, as três tentativas sairiam todas juntas assim que o primeiro
        prazo vencesse — três mensagens em sequência, que é exatamente o que
        faz a pessoa bloquear o número.
        """
        # Mensagem de 10h atrás, mas o follow-up 1 saiu há 10 minutos.
        await _cenario("a3", minutos_atras=600, followups=1, ultimo_followup_min=10)

        async with AsyncSessionLocal() as db:
            assert await conversas_para_cutucar(db) == []

        # Passadas as 2h do segundo intervalo, aí sim.
        await _cenario("a3b", minutos_atras=600, followups=1, ultimo_followup_min=180)
        async with AsyncSessionLocal() as db:
            assert [c.id for c, _, _ in await conversas_para_cutucar(db)] == ["cv-a3b"]


class TestQuandoNaoCutucar:
    @pytest.mark.asyncio
    async def test_quem_deve_resposta_e_o_escritorio(self):
        """
        Última mensagem do cliente: quem está devendo é o escritório. Isso é o
        alerta de pendência, não follow-up — cutucar aqui seria cobrar a
        pessoa por um silêncio que é nosso.
        """
        await _cenario("b1", quem_falou_por_ultimo="user", minutos_atras=600)

        async with AsyncSessionLocal() as db:
            assert await conversas_para_cutucar(db) == []

    @pytest.mark.asyncio
    async def test_conversa_assumida_por_gente_fica_de_fora(self):
        """Robô cutucando por cima do atendimento de gente é pior que silêncio."""
        await _cenario("b2", status="pausada", minutos_atras=600)

        async with AsyncSessionLocal() as db:
            assert await conversas_para_cutucar(db) == []

    @pytest.mark.asyncio
    async def test_conversa_encerrada_nao_volta(self):
        await _cenario("b3", status="encerrada", minutos_atras=600)

        async with AsyncSessionLocal() as db:
            assert await conversas_para_cutucar(db) == []

    def test_fora_do_horario_ninguem_recebe_mensagem(self):
        """
        Mensagem automática às 3h da manhã queima a reputação do número, e o
        WhatsApp não perdoa denúncia de spam.
        """
        from zoneinfo import ZoneInfo

        fuso = ZoneInfo(settings.followup_fuso)
        assert not dentro_do_horario(datetime(2026, 8, 19, 3, 0, tzinfo=fuso))
        assert not dentro_do_horario(datetime(2026, 8, 19, 22, 0, tzinfo=fuso))
        assert dentro_do_horario(datetime(2026, 8, 19, 10, 0, tzinfo=fuso))


class TestDespedidaNaoEPergunta:
    """
    O defeito que o dono viu em produção.

    O agente encerrou com "Por nada, Diego. Fique tranquilo, o advogado vai te
    procurar ainda hoje", e quinze minutos depois o follow-up devolveu a
    própria despedida como se fosse pergunta:

        "Oi, Diego! Ficou faltando só isto aqui: Por nada, Diego. Fique
        tranquilo, o advogado vai te procurar ainda hoje..."

    Sem sentido, e errado no mérito: quem devia a próxima ação era o
    escritório, não o cliente.
    """

    DESPEDIDA = (
        "Por nada, Diego. Fique tranquilo, o advogado vai te procurar ainda "
        "hoje por causa da urgência. Qualquer novidade sobre o bloqueio, pode "
        "me avisar aqui."
    )

    @pytest.mark.asyncio
    async def test_a_despedida_do_diego_nao_vira_followup(self):
        await _cenario("d1", minutos_atras=60, texto=self.DESPEDIDA)

        async with AsyncSessionLocal() as db:
            assert await followup_service.conversas_para_cutucar(db) == []

    @pytest.mark.asyncio
    async def test_pergunta_de_verdade_continua_valendo(self):
        """A correção não pode desligar o recurso."""
        await _cenario("d2", minutos_atras=60)

        async with AsyncSessionLocal() as db:
            devidas = await followup_service.conversas_para_cutucar(db)
        assert len(devidas) == 1

    def test_o_criterio_e_a_interrogacao(self):
        assert followup_service.tem_pergunta_pendente(self.DESPEDIDA) is False
        assert followup_service.tem_pergunta_pendente(PERGUNTA) is True
        assert followup_service.tem_pergunta_pendente(None) is False

    @pytest.mark.asyncio
    async def test_conversa_em_coleta_nao_e_do_followup(self):
        """
        Em coleta a agente está perguntando os dados e a conversa anda; em
        `contratado` quem cobra é o `cobranca_service`. Dois serviços cutucando
        a mesma pessoa é o caminho para ela bloquear o número.
        """
        await _cenario("d3", minutos_atras=60, fase="coleta")

        async with AsyncSessionLocal() as db:
            assert await followup_service.conversas_para_cutucar(db) == []


class TestOTexto:
    def test_repete_a_pergunta_em_vez_de_perguntar_se_esta_ai(self):
        """
        "Oi, ainda está aí?" é o que todo robô manda. Repetir a pergunta é o
        que uma pessoa faria, custa zero chamada de modelo, e a resposta vem
        porque a pessoa lembra do que era.
        """
        texto = texto_do_followup(PERGUNTA, 1, "Marina Silva")

        assert PERGUNTA in texto
        assert "Marina" in texto
        assert "ainda está aí" not in texto.lower()

    def test_sem_nome_nao_inventa_tratamento(self):
        texto = texto_do_followup(PERGUNTA, 1, None)

        assert texto.startswith("Oi!")

    def test_a_ultima_tentativa_avisa_que_e_a_ultima(self):
        """
        Dar a saída explícita é mais honesto que sumir — e quem ainda tem
        interesse costuma responder justamente aí.
        """
        texto = texto_do_followup(PERGUNTA, 3, "Marina")

        assert "última" in texto.lower()
        assert PERGUNTA in texto


class TestARodada:
    @pytest.mark.asyncio
    async def test_manda_e_conta_a_tentativa(self):
        await _cenario("c1", minutos_atras=60)

        with _envio_ok() as envio:
            async with AsyncSessionLocal() as db:
                resultado = await processar(db)

        assert resultado["enviados"] == 1
        assert PERGUNTA in envio.call_args.kwargs["message_text"]
        assert (await _conversa("cv-c1")).followups_enviados == 1

    @pytest.mark.asyncio
    async def test_o_followup_entra_na_transcricao(self):
        """
        Quem ler a conversa depois precisa ver que o escritório insistiu — e
        o próprio agente precisa, para não repetir a pergunta uma quarta vez
        no próximo turno.
        """
        await _cenario("c2", minutos_atras=60)

        with _envio_ok():
            async with AsyncSessionLocal() as db:
                await processar(db)

        async with AsyncSessionLocal() as db:
            mensagens = (
                await db.execute(
                    select(Message).where(Message.conversation_id == "cv-c2")
                )
            ).scalars().all()

        assert any(PERGUNTA in m.conteudo and "Ficou faltando" in m.conteudo
                   for m in mensagens)

    @pytest.mark.asyncio
    async def test_esgotadas_as_tentativas_encerra(self):
        await _cenario("c3", minutos_atras=6000,
                       followups=len(settings.followup_intervalos),
                       ultimo_followup_min=6000)

        with _envio_ok() as envio:
            async with AsyncSessionLocal() as db:
                resultado = await processar(db)

        assert resultado["encerrados"] == 1
        assert TEXTO_DE_ENCERRAMENTO in envio.call_args.kwargs["message_text"]
        assert (await _conversa("cv-c3")).status == "encerrada"

    @pytest.mark.asyncio
    async def test_o_encerramento_fica_na_trilha_do_lead(self):
        await _cenario("c4", minutos_atras=6000,
                       followups=len(settings.followup_intervalos),
                       ultimo_followup_min=6000)

        with _envio_ok():
            async with AsyncSessionLocal() as db:
                await processar(db)

        async with AsyncSessionLocal() as db:
            trilha = (
                await db.execute(
                    select(LeadTimeline).where(LeadTimeline.lead_id == "lead-c4")
                )
            ).scalars().all()

        assert any("falta de retorno" in (t.motivo or "") for t in trilha)

    @pytest.mark.asyncio
    async def test_falha_de_envio_nao_gasta_a_tentativa(self):
        """
        A pessoa não recebeu nada. Queimar a cota faria a conversa ser
        encerrada sem que ninguém tenha falado com ela — e a Evolution cai
        com frequência suficiente para isso importar.
        """
        await _cenario("c5", minutos_atras=60)

        with patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
            return_value={"success": False},
        ):
            async with AsyncSessionLocal() as db:
                resultado = await processar(db)

        assert resultado == {"enviados": 0, "encerrados": 0, "falhas": 1}
        assert (await _conversa("cv-c5")).followups_enviados == 0

    @pytest.mark.asyncio
    async def test_conversa_sem_lead_nao_quebra(self):
        """Contato que nunca chegou a virar lead ainda é gente esperando."""
        await _cenario("c6", minutos_atras=60, com_lead=False)

        with _envio_ok():
            async with AsyncSessionLocal() as db:
                resultado = await processar(db)

        assert resultado["enviados"] == 1

    @pytest.mark.asyncio
    async def test_desligado_por_configuracao_nao_manda_nada(self):
        await _cenario("c7", minutos_atras=60)
        original = settings.followup_habilitado
        settings.followup_habilitado = False
        try:
            resultado = await followup_service.rodada()
        finally:
            settings.followup_habilitado = original

        assert resultado["desligado"] is True
        assert (await _conversa("cv-c7")).followups_enviados == 0


class TestOZeramento:
    """
    A contagem é de silêncio **seguido**, não de cutucadas na vida toda.

    Sem o zeramento, quem some, volta e some de novo seria encerrado na
    primeira ausência seguinte — como se nunca tivesse respondido. E a pessoa
    que voltou é justamente a que tem interesse.
    """

    @pytest.mark.asyncio
    async def test_responder_zera_a_contagem(self):
        await _cenario("d1", minutos_atras=600, followups=2, ultimo_followup_min=600)

        with patch(
            "app.services.llm_service.llm_service.generate_response",
            new_callable=AsyncMock,
            return_value=("Entendi, obrigado.", {"input_tokens": 1, "output_tokens": 1,
                                                 "total_tokens": 2}),
        ), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new_callable=AsyncMock,
            return_value={"success": True, "message_id": "m1"},
        ), patch(
            "app.services.lead_processor.lead_processor.process_response",
            new_callable=AsyncMock,
            return_value={"success": False},
        ):
            from app.services.message_orchestrator import orchestrator

            async with AsyncSessionLocal() as db:
                conversa = await _conversa("cv-d1")
                await orchestrator.process_incoming_message(
                    "ag-d1", conversa.phone_number, "Desculpa, eu ganhava 2.100", db
                )

        depois = await _conversa("cv-d1")
        assert depois.followups_enviados == 0
        assert depois.ultimo_followup_em is None
