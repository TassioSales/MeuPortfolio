"""
A IA abrindo a coleta e emitindo o contrato sozinha.

Este é o recurso mais perigoso do produto: ele manda um documento com
honorários para uma pessoa real sem ninguém do escritório clicar. Os testes
aqui existem menos para provar que funciona e mais para provar **que ele não
dispara quando não deve**.

O que cada barreira impede, e por que ela está lá:

- **Desligado por padrão** — ligado, o próximo lead real recebe um contrato
  sem o dono ter escolhido a hora.
- **Viabilidade abaixo do piso** — o escritório recusaria o caso; mandar
  contrato é constrangedor e cria expectativa.
- **Conversa pausada** — um humano assumiu. Um robô anunciando "vamos aceitar
  seu caso" por cima do atendimento de gente é pior que silêncio.
- **Sem modelo ativo** — o contrato sairia sem cláusula e sem honorários.
- **Já tem contrato** — dois contratos com honorários no mesmo WhatsApp é o
  pior desfecho possível deste recurso.
- **Evolution recusou** — sem entrega, sem fase nova e sem contrato: um
  contrato marcado como enviado que ninguém recebeu entra na fila de cobrança
  e cobra alguém por um documento que ela nunca viu.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.config import settings
from app.db.models import (
    Agent,
    Caso,
    ConfiguracaoEscritorio,
    Contrato,
    Conversation,
    Lead,
    Message,
    ModeloDeContrato,
)
from app.db.database import AsyncSessionLocal
from app.services import coleta_service, gatilho_contrato

CORPO = "# CONTRATO\n{{cliente.nome}}, CPF {{cliente.cpf}}, {{cliente.cidade}}/{{cliente.uf}}."


async def _cenario(
    sufixo: str,
    *,
    viabilidade: str = "acima_do_piso",
    status_conversa: str = "ativa",
    fase: str = "triagem",
    com_modelo: bool = True,
    com_contrato: bool = False,
    status_funil: str = "qualificado",
    com_caso: bool = True,
    dados_completos: bool = False,
) -> tuple:
    """Devolve (lead_id, conversation_id)."""
    async with AsyncSessionLocal() as db:
        db.add(ConfiguracaoEscritorio(id="unica", nome="Sales Advocacia",
                                      cidade="Brasília"))
        db.add(Agent(id=f"ag-{sufixo}", nome="Ag", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"5561{sufixo}", status=status_conversa,
                            fase=fase))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome="Maria Aparecida da Silva", phone_number=f"5561{sufixo}",
                    status_funil=status_funil))
        await db.flush()

        if com_caso:
            db.add(Caso(id=f"caso-{sufixo}", lead_id=f"lead-{sufixo}",
                        area="trabalhista", resumo="Verbas",
                        viabilidade=viabilidade))
        if com_modelo:
            db.add(ModeloDeContrato(id=f"m-{sufixo}", nome=f"Modelo {sufixo}",
                                    corpo=CORPO, ativo=True))
        if com_contrato:
            db.add(Contrato(id=f"k-{sufixo}", lead_id=f"lead-{sufixo}",
                            corpo="antigo", status="enviado"))
        if dados_completos:
            await coleta_service.gravar(db, f"lead-{sufixo}", {
                "cpf": "12345678901", "endereco": "Q 312 Conj A",
                "cidade": "Gama", "uf": "DF",
            })
        await db.commit()
    return f"lead-{sufixo}", f"cv-{sufixo}"


def _ligado():
    return patch.object(settings, "contrato_automatico", True)


def _evolution_ok():
    return patch(
        "app.services.whatsapp_service.whatsapp_service.send_message",
        new=AsyncMock(return_value={"success": True}),
    )


async def _abrir(lead_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalars().first()
        caso = (
            await db.execute(select(Caso).where(Caso.lead_id == lead_id))
        ).scalars().first()
        aberto = await gatilho_contrato.abrir_coleta(db, lead, caso)
        await db.commit()
    return aberto


async def _fase(conversation_id: str) -> str:
    async with AsyncSessionLocal() as db:
        c = (
            await db.execute(select(Conversation).where(Conversation.id == conversation_id))
        ).scalars().first()
        return c.fase


# ------------------------------------------------------- abrir a coleta

class TestAbrirColeta:
    @pytest.mark.asyncio
    async def test_abre_e_anuncia_que_o_caso_foi_aceito(self):
        lead_id, conversa_id = await _cenario("a1")

        with _ligado(), _evolution_ok() as enviar:
            assert await _abrir(lead_id) is True

        assert await _fase(conversa_id) == "coleta"
        texto = enviar.await_args.kwargs["message_text"]
        assert "aceitar" in texto and "CPF" in texto
        assert "Maria" in texto

    @pytest.mark.asyncio
    async def test_desligado_nao_faz_nada(self):
        """A barreira que importa mais: ligar é decisão do dono, não default."""
        lead_id, conversa_id = await _cenario("a2")

        with _evolution_ok() as enviar:  # sem _ligado()
            assert await _abrir(lead_id) is False

        assert await _fase(conversa_id) == "triagem"
        assert enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_viabilidade_abaixo_do_piso_barra(self):
        lead_id, conversa_id = await _cenario("a3", viabilidade="abaixo_do_piso")

        with _ligado(), _evolution_ok():
            assert await _abrir(lead_id) is False
        assert await _fase(conversa_id) == "triagem"

    @pytest.mark.asyncio
    async def test_indeterminado_nao_barra(self):
        """
        Parecer sem porte não é caso inviável, é caso que ninguém dimensionou —
        a mesma distinção que o funil já faz. Barrar aqui faria o gatilho não
        disparar quase nunca.
        """
        lead_id, _ = await _cenario("a4", viabilidade="indeterminado")

        with _ligado(), _evolution_ok():
            assert await _abrir(lead_id) is True

    @pytest.mark.asyncio
    async def test_conversa_pausada_barra(self):
        """Um humano assumiu."""
        lead_id, _ = await _cenario("a5", status_conversa="pausada")

        with _ligado(), _evolution_ok() as enviar:
            assert await _abrir(lead_id) is False
        assert enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_sem_modelo_ativo_barra(self):
        """O contrato sairia sem cláusula e sem honorários."""
        lead_id, _ = await _cenario("a6", com_modelo=False)

        with _ligado(), _evolution_ok():
            assert await _abrir(lead_id) is False

    @pytest.mark.asyncio
    async def test_lead_ja_com_contrato_barra(self):
        lead_id, _ = await _cenario("a7", com_contrato=True)

        with _ligado(), _evolution_ok():
            assert await _abrir(lead_id) is False

    @pytest.mark.asyncio
    async def test_nao_qualificado_barra(self):
        lead_id, _ = await _cenario("a8", status_funil="nao_qualificado")

        with _ligado(), _evolution_ok():
            assert await _abrir(lead_id) is False

    @pytest.mark.asyncio
    async def test_nao_reabre_conversa_ja_em_coleta(self):
        lead_id, _ = await _cenario("a9", fase="coleta")

        with _ligado(), _evolution_ok() as enviar:
            assert await _abrir(lead_id) is False
        assert enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_evolution_recusando_nao_vira_a_fase(self):
        """
        Senão o agente entraria em coleta em silêncio, e o cliente receberia,
        do nada, uma pergunta sobre CPF sem nunca ter sido avisado de que o
        caso foi aceito.
        """
        lead_id, conversa_id = await _cenario("a10")

        with _ligado(), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": False}),
        ):
            assert await _abrir(lead_id) is False

        assert await _fase(conversa_id) == "triagem"
        async with AsyncSessionLocal() as db:
            msgs = (await db.execute(select(Message))).scalars().all()
        assert msgs == []


# --------------------------------------------------- emitir o contrato

async def _emitir(lead_id: str):
    async with AsyncSessionLocal() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalars().first()
        resultado = await gatilho_contrato.talvez_emitir(db, lead)
        await db.commit()
    return resultado


class TestEmitir:
    @pytest.mark.asyncio
    async def test_dados_completos_geram_e_enviam_sozinhos(self):
        lead_id, conversa_id = await _cenario("e1", fase="coleta", dados_completos=True)

        with _ligado(), _evolution_ok() as enviar:
            contrato_id = await _emitir(lead_id)

        assert contrato_id is not None
        assert await _fase(conversa_id) == "contratado"

        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Contrato))).scalars().first()

        # O contrato saiu preenchido com o que a agente coletou.
        assert "Maria Aparecida da Silva" in c.corpo
        assert "123.456.789-01" in c.corpo
        assert "Gama/DF" in c.corpo
        assert "{{" not in c.corpo
        # E o link foi junto na mensagem.
        assert c.link_assinatura in enviar.await_args.kwargs["message_text"]

    @pytest.mark.asyncio
    async def test_dados_incompletos_nao_emitem(self):
        lead_id, conversa_id = await _cenario("e2", fase="coleta")

        with _ligado(), _evolution_ok() as enviar:
            assert await _emitir(lead_id) is None
        assert enviar.await_count == 0
        assert await _fase(conversa_id) == "coleta"

    @pytest.mark.asyncio
    async def test_nao_emite_duas_vezes(self):
        """
        Dois contratos com honorários no mesmo WhatsApp é o pior desfecho
        possível deste recurso. O cliente pode confirmar o endereço duas vezes.
        """
        lead_id, _ = await _cenario("e3", fase="coleta", dados_completos=True)

        with _ligado(), _evolution_ok():
            primeiro = await _emitir(lead_id)
            segundo = await _emitir(lead_id)

        assert primeiro is not None and segundo is None
        async with AsyncSessionLocal() as db:
            contratos = (await db.execute(select(Contrato))).scalars().all()
        assert len(contratos) == 1

    @pytest.mark.asyncio
    async def test_desligado_nao_emite(self):
        lead_id, _ = await _cenario("e4", fase="coleta", dados_completos=True)

        with _evolution_ok() as enviar:
            assert await _emitir(lead_id) is None
        assert enviar.await_count == 0

    @pytest.mark.asyncio
    async def test_evolution_recusando_nao_deixa_contrato_fantasma(self):
        """
        Contrato marcado como enviado que ninguém recebeu entra na fila de
        cobrança e cobra alguém por um documento que ela nunca viu.
        """
        lead_id, conversa_id = await _cenario("e5", fase="coleta", dados_completos=True)

        with _ligado(), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": False}),
        ):
            assert await _emitir(lead_id) is None

        async with AsyncSessionLocal() as db:
            contratos = (await db.execute(select(Contrato))).scalars().all()
            msgs = (await db.execute(select(Message))).scalars().all()
        assert contratos == [] and msgs == []
        assert await _fase(conversa_id) == "coleta"
