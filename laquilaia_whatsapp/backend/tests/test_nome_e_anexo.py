"""
Dois defeitos vistos num atendimento real, no mesmo dia.

O cliente abriu a conversa com dois áudios. O agente **não conseguiu
transcrevê-los** — e mesmo assim respondeu *"Entendo, é uma situação bem chata
mesmo, ficar recebendo menos do que o combinado"*, inventando o conteúdo de um
áudio que nunca ouviu. Sem nome à mão, passou a chamar o cliente de "Rafael", e
fez isso **onze vezes** ao longo de meia hora. Ele se chama Lázaro.

As duas coisas têm a mesma raiz: o sistema entregava ao modelo um vazio em vez
de dizer que era um vazio. Um modelo aceita não saber quando lhe dizem que não
sabe; não aceita quando lhe entregam um buraco para preencher.
"""

import pytest
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Agent, Conversation, Lead
from app.services.atendimento_context import (
    AVISO_SEM_NOME,
    nota_de_atendimento_anterior,
)
from app.services.message_orchestrator import MessageOrchestrator, orchestrator

TELEFONE = "556195258442"


async def _cenario(sufixo: str, nome: str = "") -> str:
    async with AsyncSessionLocal() as db:
        db.add(Agent(id=f"ag-{sufixo}", nome="Ag", system_prompt="p",
                     temperatura=0.4, max_tokens=1024, status="ativo"))
        await db.flush()
        db.add(Conversation(id=f"cv-{sufixo}", agent_id=f"ag-{sufixo}",
                            phone_number=f"{TELEFONE}{sufixo}", status="ativa"))
        await db.flush()
        db.add(Lead(id=f"lead-{sufixo}", conversation_id=f"cv-{sufixo}",
                    nome=nome or None, phone_number=f"{TELEFONE}{sufixo}"))
        await db.commit()
    return f"{TELEFONE}{sufixo}"


class TestONomeInventado:
    @pytest.mark.asyncio
    async def test_primeiro_contato_avisa_que_o_nome_e_desconhecido(self):
        """
        A lacuna por onde "Rafael" entrou: sem lead, não havia nota nenhuma, e
        o modelo preenchia o vazio.
        """
        async with AsyncSessionLocal() as db:
            nota = await nota_de_atendimento_anterior(
                "5561000000000", "cv-inexistente", db
            )

        assert nota is not None, "primeiro contato ficava sem nota"
        assert AVISO_SEM_NOME in nota

    @pytest.mark.asyncio
    async def test_lead_sem_nome_tambem_avisa(self):
        telefone = await _cenario("n1")

        async with AsyncSessionLocal() as db:
            nota = await nota_de_atendimento_anterior(telefone, "cv-n1", db)

        assert AVISO_SEM_NOME in nota

    @pytest.mark.asyncio
    async def test_com_nome_o_sistema_afirma_qual_e(self):
        """
        Não basta não avisar: o sistema diz o nome e manda usar **esse**. Um
        modelo que já escolheu um nome tende a mantê-lo por coerência com o
        que ele mesmo disse antes.
        """
        telefone = await _cenario("n2", nome="Lázaro da Silva")

        async with AsyncSessionLocal() as db:
            nota = await nota_de_atendimento_anterior(telefone, "cv-n2", db)

        assert "Lázaro da Silva" in nota
        assert "por nenhum outro" in nota
        assert AVISO_SEM_NOME not in nota

    def test_o_prompt_tambem_proibe(self):
        """
        Cinto e suspensório. A nota é a trava dura; o prompt explica o porquê,
        e é o que o modelo lê antes de qualquer mensagem.
        """
        from app.prompts import PROMPT_TRIAGEM_JURIDICA

        assert "Nunca invente um nome" in PROMPT_TRIAGEM_JURIDICA


class TestOAnexoQueNaoFoiLido:
    def test_a_nota_do_anexo_nao_e_fala_do_agente(self):
        """
        A versão anterior dizia "Não consigo ouvir áudios por aqui. Pode me
        escrever o que você falou?" — primeira pessoa, do agente — mas era
        anexada ao turno do **cliente**. O modelo lia o próprio cliente
        dizendo que não conseguia ouvir áudios.
        """
        for tipo, nota in MessageOrchestrator.PEDIDO_DE_TEXTO.items():
            assert nota.startswith("[Nota do sistema:"), tipo
            assert nota.endswith("]"), tipo
            # Nada de primeira pessoa do agente.
            assert "Não consigo" not in nota.split("Diga que")[0], tipo

    def test_a_nota_afirma_a_ignorancia(self):
        """
        "NÃO foi transcrito" é diferente de "não consigo ouvir": o primeiro é
        fato sobre o que o modelo tem em mãos, o segundo é uma frase para ele
        repetir. Só o primeiro impede a invenção.
        """
        audio = MessageOrchestrator.PEDIDO_DE_TEXTO["audio"]
        assert "NÃO foi transcrito" in audio
        assert "não tem acesso" in audio
        assert "não responda como se tivesse ouvido" in audio.lower()

    @pytest.mark.asyncio
    async def test_audio_sem_transcricao_vira_mensagem_com_a_nota(self):
        async with AsyncSessionLocal() as db:
            agente = Agent(id="ag-a1", nome="Ag", system_prompt="p",
                           temperatura=0.4, max_tokens=1024, status="ativo",
                           anexos_habilitados=False)
            db.add(agente)
            await db.commit()

            anexo, texto = await orchestrator._preparar_anexo(
                agente, "audio", {"id": "x"}, ""
            )

        assert anexo is None
        assert "[o cliente enviou um áudio]" in texto
        assert "[Nota do sistema:" in texto
