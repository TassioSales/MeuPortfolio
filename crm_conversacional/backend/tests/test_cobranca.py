"""
Cobrar quem recebeu o contrato e não assinou.

O dono descreveu o buraco: contrato enviado e nunca assinado tem três
explicações com a mesma aparência no painel — desistiu, travou numa cláusula,
ou nem abriu o link. A cobrança existe para descobrir qual.

O que estes testes travam, e cada um tem um motivo que não é hipótese:

1. **Não cobrar quem já assinou** — óbvio, e é o primeiro que quebraria numa
   refatoração do filtro.
2. **Não cobrar contrato nunca enviado.** Pedir assinatura de um documento que
   a pessoa não recebeu é constrangedor.
3. **Não cobrar por cima de conversa em atendimento humano.**
4. **Não cobrar quem acabou de escrever.** A pessoa está falando com a gente;
   cortar com "assina aí" é o movimento errado.
5. **Falha de envio não gasta a tentativa.** Senão a cobrança termina sem que
   ninguém tenha sido cobrado.
6. **Link vencido é renovado antes de sair.** Cobrar com endereço morto
   apareceria como "o cliente diz que o link não abre" — que ninguém liga à
   configuração dos intervalos.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Contrato, Conversation, Lead, LeadTimeline, Message
from app.services import assinatura_service, cobranca_service

INTERVALOS = settings.cobranca_intervalos

# Antigo o bastante para vencer **qualquer** um dos prazos, inclusive o da
# terceira tentativa. Um valor fixo menor faria os testes de segunda e terceira
# cobrança passarem por acidente — ou falharem, que foi o que aconteceu.
BEM_VENCIDO = max(INTERVALOS) + 1000


async def _cenario(
    sufixo: str,
    *,
    enviado_ha_minutos: int = BEM_VENCIDO,
    status_contrato: str = "enviado",
    status_conversa: str = "ativa",
    cobrancas: int = 0,
    assinado: bool = False,
    com_token: bool = True,
    expirado: bool = False,
    cliente_falou_ha_minutos: int = None,
) -> str:
    """Um contrato num estado específico. Devolve o id do contrato."""
    agora = datetime.utcnow()
    enviado_em = agora - timedelta(minutes=enviado_ha_minutos)

    async with AsyncSessionLocal() as db:
        db.add(Agent(id=f"ag-{sufixo}", nome="Ag", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"5561{sufixo}", status=status_conversa))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Maria Aparecida", phone_number=f"5561{sufixo}",
                    status_funil="qualificado"))
        await db.flush()

        if cliente_falou_ha_minutos is not None:
            db.add(Message(
                conversation_id=f"cv-{sufixo}", remetente="user",
                conteudo="uma dúvida",
                timestamp=agora - timedelta(minutes=cliente_falou_ha_minutos),
            ))

        token = assinatura_service.novo_token() if com_token else None
        db.add(Contrato(
            id=f"k-{sufixo}", lead_id=f"lead-{sufixo}", corpo="# CONTRATO\nTexto.",
            status=status_contrato,
            token_assinatura=token,
            token_expira_em=(
                (agora - timedelta(hours=1)) if expirado
                else (agora + timedelta(days=7)) if com_token else None
            ),
            link_assinatura=f"http://x/assinar/{token}" if token else None,
            data_envio=enviado_em if status_contrato != "gerado" else None,
            data_assinatura=agora if assinado else None,
            assinado_nome="Maria Aparecida" if assinado else None,
            cobrancas_enviadas=cobrancas,
        ))
        await db.commit()
    return f"k-{sufixo}"


def _evolution_ok():
    return patch(
        "app.services.whatsapp_service.whatsapp_service.send_message",
        new=AsyncMock(return_value={"success": True}),
    )


async def _rodar() -> dict:
    async with AsyncSessionLocal() as db:
        return await cobranca_service.processar(db)


async def _contrato(contrato_id: str) -> Contrato:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(Contrato).where(Contrato.id == contrato_id))
        ).scalars().first()


# ------------------------------------------------------------ quem entra

class TestQuemEntraNaCobranca:
    @pytest.mark.asyncio
    async def test_cobra_contrato_enviado_e_esquecido(self):
        contrato_id = await _cenario("q1")

        with _evolution_ok() as enviar:
            resultado = await _rodar()

        assert resultado["enviadas"] == 1
        assert enviar.await_count == 1
        c = await _contrato(contrato_id)
        assert c.cobrancas_enviadas == 1 and c.ultima_cobranca_em is not None

    @pytest.mark.asyncio
    async def test_nao_cobra_quem_ja_assinou(self):
        await _cenario("q2", assinado=True, status_contrato="assinado")

        with _evolution_ok() as enviar:
            assert (await _rodar())["enviadas"] == 0
        assert enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_nao_cobra_contrato_nunca_enviado(self):
        """Pedir assinatura de documento que a pessoa não recebeu."""
        await _cenario("q3", status_contrato="gerado", com_token=False)

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 0

    @pytest.mark.asyncio
    async def test_nao_cobra_por_cima_de_atendimento_humano(self):
        """Robô cobrando enquanto gente atende é pior que silêncio."""
        await _cenario("q4", status_conversa="pausada")

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 0

    @pytest.mark.asyncio
    async def test_nao_cobra_antes_do_prazo(self):
        await _cenario("q5", enviado_ha_minutos=INTERVALOS[0] - 10)

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 0

    @pytest.mark.asyncio
    async def test_para_depois_da_cota(self):
        """Insistir uma quarta vez é o que faz alguém bloquear o número."""
        await _cenario("q6", cobrancas=len(INTERVALOS))

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 0


# ------------------------------------------- o cliente respondendo no meio

class TestClienteRespondendo:
    @pytest.mark.asyncio
    async def test_nao_corta_quem_acabou_de_escrever(self):
        """
        A pessoa está falando com a gente agora. Cortar a conversa com
        "assina aí" é exatamente o movimento errado.
        """
        await _cenario("r1", cliente_falou_ha_minutos=5)

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 0

    @pytest.mark.asyncio
    async def test_volta_a_cobrar_quando_a_conversa_esfria(self):
        """
        O relógio passa a contar da fala dela — a cobrança não some para
        sempre só porque a pessoa respondeu uma vez.
        """
        await _cenario("r2", cliente_falou_ha_minutos=INTERVALOS[0] + 60)

        with _evolution_ok():
            assert (await _rodar())["enviadas"] == 1


# ------------------------------------------------------------ o que sai

class TestOQueSai:
    @pytest.mark.asyncio
    async def test_a_primeira_manda_o_link_de_novo(self):
        contrato_id = await _cenario("s1")
        c = await _contrato(contrato_id)

        with _evolution_ok() as enviar:
            await _rodar()

        texto = enviar.await_args.kwargs["message_text"]
        assert c.link_assinatura in texto
        assert "Maria" in texto

    @pytest.mark.asyncio
    async def test_a_segunda_pergunta_o_motivo(self):
        """
        O que o dono pediu: "tem que perguntar por que não assinou, se
        desistiu". Pergunta aberta — "você vai assinar?" recebe silêncio.
        """
        await _cenario("s2", cobrancas=1)

        with _evolution_ok() as enviar:
            await _rodar()

        texto = enviar.await_args.kwargs["message_text"]
        assert "dúvida" in texto and "prefere não seguir" in texto

    @pytest.mark.asyncio
    async def test_a_ultima_da_a_saida_e_nao_insiste(self):
        await _cenario("s3", cobrancas=len(INTERVALOS) - 1)

        with _evolution_ok() as enviar:
            await _rodar()

        texto = enviar.await_args.kwargs["message_text"]
        assert "não vou insistir" in texto.lower()

    @pytest.mark.asyncio
    async def test_grava_a_mensagem_na_conversa_e_na_trilha(self):
        """Cobrança que não aparece na transcrição é cobrança que ninguém audita."""
        await _cenario("s4")

        with _evolution_ok():
            await _rodar()

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()
            trilha = (await db.execute(select(LeadTimeline))).scalars().all()

        assert len(msgs) == 1 and msgs[0].remetente == "sistema"
        assert len(trilha) == 1 and "Cobrança" in trilha[0].motivo


# ---------------------------------------------------------------- falhas

class TestFalhas:
    @pytest.mark.asyncio
    async def test_falha_de_envio_nao_gasta_a_tentativa(self):
        """
        Senão a cobrança termina sem que ninguém tenha sido cobrado — e o
        contrato fica marcado como cobrado três vezes.
        """
        contrato_id = await _cenario("f1")

        with patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": False}),
        ):
            resultado = await _rodar()

        assert resultado["falhas"] == 1 and resultado["enviadas"] == 0
        c = await _contrato(contrato_id)
        assert c.cobrancas_enviadas == 0

        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()
        assert msgs == []

    @pytest.mark.asyncio
    async def test_link_vencido_e_renovado_antes_de_sair(self):
        """
        Com os intervalos padrão isto não acontece (4 dias de cobrança contra
        7 de validade). Basta alguém alargar um intervalo no `.env` para a
        cobrança passar a mandar endereço morto — e o defeito apareceria como
        "o cliente diz que o link não abre".
        """
        contrato_id = await _cenario("f2", expirado=True)
        antes = await _contrato(contrato_id)

        with _evolution_ok() as enviar:
            resultado = await _rodar()

        assert resultado["links_renovados"] == 1
        depois = await _contrato(contrato_id)
        assert depois.token_assinatura != antes.token_assinatura
        assert not assinatura_service.expirado(depois)
        # E o link novo é o que foi mandado, não o morto.
        assert depois.link_assinatura in enviar.await_args.kwargs["message_text"]

    @pytest.mark.asyncio
    async def test_renovar_nao_reinicia_a_contagem(self):
        """Senão a renovação viraria cobrança perpétua."""
        contrato_id = await _cenario("f3", expirado=True, cobrancas=1)

        with _evolution_ok():
            await _rodar()

        c = await _contrato(contrato_id)
        assert c.cobrancas_enviadas == 2

    @pytest.mark.asyncio
    async def test_desligada_nao_faz_nada(self):
        await _cenario("f4")

        with patch.object(settings, "cobranca_habilitada", False):
            resultado = await cobranca_service.rodada()

        assert resultado.get("desligada") is True

    @pytest.mark.asyncio
    async def test_fora_do_horario_espera(self):
        """Mensagem automática às 3h queima a reputação do número."""
        await _cenario("f5")

        with patch("app.services.cobranca_service.dentro_do_horario", return_value=False):
            resultado = await cobranca_service.rodada()

        assert resultado.get("fora_do_horario") is True

    @pytest.mark.asyncio
    async def test_erro_na_rodada_nao_derruba_o_agendador(self):
        with patch(
            "app.services.cobranca_service.processar",
            new=AsyncMock(side_effect=Exception("banco caiu")),
        ):
            resultado = await cobranca_service.rodada()

        assert "erro" in resultado and resultado["enviadas"] == 0


class TestNaoAtropelaOFollowup:
    @pytest.mark.asyncio
    async def test_a_cobranca_nao_vira_alvo_do_followup_de_conversa(self):
        """
        Os dois serviços não podem cutucar a mesma pessoa. O follow-up de
        conversa só pega conversas cuja última mensagem é do agente
        (`assistant`); a cobrança grava como `sistema` justamente por isso.
        """
        from app.services import followup_service

        await _cenario("n1")
        with _evolution_ok():
            await _rodar()

        async with AsyncSessionLocal() as db:
            devidas = await followup_service.conversas_para_cutucar(
                db, datetime.utcnow() + timedelta(days=30)
            )

        assert devidas == []
