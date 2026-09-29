"""
Testes da memória entre atendimentos.

Quem já foi atendido e volta não pode ouvir "seu caso é sobre o quê?" outra
vez: para o cliente parece que o escritório esqueceu, e para o escritório o
mesmo caso chega duas vezes.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import Caso, Lead, LeadDetails
from app.services.atendimento_context import (
    MENSAGENS_DE_CONTEXTO,
    com_nota,
    nota_de_atendimento_anterior,
)


def _db(lead=None, detalhes=None, total_mensagens=0, card=None, casos=()):
    """
    Sessão que responde às consultas na ordem em que são feitas.

    A ordem importa e é frágil de propósito: quem acrescentar uma consulta ao
    serviço vai ver este helper quebrar, que é melhor do que ver a nota sair
    com o campo errado.

    `card` é a tupla `(KanbanCard, nome_da_coluna)` que o `join` devolve.
    """
    respostas = []

    r_lead = MagicMock()
    r_lead.scalars.return_value.first.return_value = lead
    respostas.append(r_lead)

    if lead is not None:
        r_card = MagicMock()
        r_card.first.return_value = card
        respostas.append(r_card)

        r_casos = MagicMock()
        r_casos.scalars.return_value.all.return_value = list(casos)
        respostas.append(r_casos)

        r_det = MagicMock()
        r_det.scalars.return_value.first.return_value = detalhes
        respostas.append(r_det)

        r_total = MagicMock()
        r_total.scalar.return_value = total_mensagens
        respostas.append(r_total)

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=respostas)
    return db


def _caso(area="trabalhista", data=None):
    caso = MagicMock(spec=Caso)
    caso.area = area
    caso.data_abertura = data or datetime(2026, 8, 12, 14, 0)
    return caso


def _lead(**kwargs):
    lead = MagicMock(spec=Lead)
    lead.id = kwargs.get("id", "lead-1")
    lead.nome = kwargs.get("nome", "Tássio Sales")
    lead.status_funil = kwargs.get("status_funil", "qualificado")
    lead.data_criacao = kwargs.get("data_criacao", datetime(2026, 8, 10, 9, 0))
    return lead


class TestPrimeiroContato:
    async def test_numero_desconhecido_avisa_que_nao_sabe_o_nome(self):
        """
        **Este teste mudou de lado.** Ele exigia `None` para número
        desconhecido — "sem nota, o agente abre a triagem normalmente" —, e
        era exatamente essa lacuna que deixava o modelo inventar um nome.

        Num atendimento real o cliente abriu com dois áudios que o agente não
        conseguiu ouvir; sem nome nenhum à mão, o modelo passou a chamá-lo de
        "Rafael", onze vezes em meia hora. Ele se chama Lázaro.

        Agora a nota existe desde o primeiro contato, e o que ela carrega é a
        afirmação da ignorância: o sistema **não sabe** o nome desta pessoa.
        """
        from app.services.atendimento_context import AVISO_SEM_NOME

        nota = await nota_de_atendimento_anterior("5561999", "conv-1", _db())

        assert nota is not None
        assert AVISO_SEM_NOME in nota
        # E nada mais: não há atendimento anterior para contar.
        assert "atendimento registrado" not in nota


class TestRetorno:
    async def test_nota_traz_nome_situacao_e_a_instrucao(self):
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), total_mensagens=12)
        )

        assert "Tássio Sales" in nota
        assert "qualificado" in nota
        assert "10/08/2026" in nota
        assert "12" in nota
        # A instrução é o que muda o comportamento; sem ela a nota é decoração.
        assert "Não recomece a triagem do zero" in nota

    async def test_nota_se_identifica_como_sistema(self):
        """
        O modelo precisa saber que aquilo não veio do cliente.

        A nota entra no papel de usuário — é o único canal disponível sem
        alterar o system prompt, que é do dono do agente —, e sem o rótulo o
        agente responderia a ela como se fosse mensagem de quem está do outro
        lado.
        """
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), total_mensagens=3)
        )

        assert nota.startswith("[Nota do sistema")
        assert "não é mensagem do cliente" in nota

    async def test_leva_o_resumo_do_parecer_mas_nao_o_parecer_inteiro(self):
        """
        Só a primeira seção.

        O parecer traz teses, prazos e pontos fracos — material do advogado. Um
        agente com isso no contexto acaba repetindo tese para o cliente, que é
        exatamente o que o prompt de triagem proíbe.
        """
        detalhes = MagicMock(spec=LeadDetails)
        detalhes.analise_preliminar = (
            "## Resumo\nCliente relata demissão por justa causa em maio.\n\n"
            "## Área e possíveis teses\nReversão com base no art. 482 da CLT.\n\n"
            "## Pontos fracos\nPode haver faltas não cobertas por atestado."
        )

        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), detalhes=detalhes, total_mensagens=8)
        )

        assert "demissão por justa causa em maio" in nota
        assert "art. 482" not in nota
        assert "Pontos fracos" not in nota

    async def test_lead_sem_nome_nao_quebra(self):
        lead = _lead(nome=None)

        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=lead, total_mensagens=1)
        )

        # Antes dizia "sem nome registrado", que é uma constatação. Agora é
        # uma instrução — a diferença entre o modelo saber que falta o dado e
        # saber o que fazer com a falta.
        from app.services.atendimento_context import AVISO_SEM_NOME

        assert AVISO_SEM_NOME in nota


class TestMontagemDoHistorico:
    def test_nota_vai_na_frente_do_historico(self):
        historico = [{"role": "user", "content": "oi"}]

        resultado = com_nota(historico, "[Nota do sistema] já atendido")

        assert resultado[0]["content"].startswith("[Nota do sistema]")
        assert resultado[1] == historico[0]

    def test_sem_nota_o_historico_passa_intacto(self):
        historico = [{"role": "user", "content": "oi"}]

        assert com_nota(historico, None) is historico


class TestJanelaDeContexto:
    def test_janela_cobre_uma_triagem_inteira(self):
        """
        Eram 5 mensagens, e uma triagem passa disso no terceiro par de
        perguntas — o relato do caso saía da janela antes de a conversa
        terminar, e o agente esquecia o que estava apurando.
        """
        assert MENSAGENS_DE_CONTEXTO >= 20


class TestCardEmAndamento:
    """
    O agente precisa saber que o contato **já está no funil**.

    Isto é fato registrado, respondido por um `SELECT` em chave indexada — não
    é pergunta para o modelo. Gastar chamada de LLM para descobrir o que o
    banco responde em milissegundos seria pagar caro por uma resposta pior.
    """

    async def test_diz_em_que_coluna_o_card_esta(self):
        card = (MagicMock(), "Viabilidade")

        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), card=card)
        )

        assert "card no funil" in nota
        assert "Viabilidade" in nota

    async def test_sem_card_nao_inventa(self):
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), card=None)
        )

        assert "card no funil" not in nota

    async def test_lista_os_casos_ja_registrados(self):
        nota = await nota_de_atendimento_anterior(
            "5561999",
            "conv-1",
            _db(lead=_lead(), casos=[_caso("trabalhista"), _caso("familia")]),
        )

        assert "trabalhista" in nota
        assert "familia" in nota
        assert "12/08/2026" in nota

    async def test_assunto_diferente_e_caso_novo(self):
        """
        O contato pode voltar com **outro** assunto, e aí não é retomada.
        Sem esta instrução o agente trataria o divórcio como continuação da
        reclamação trabalhista, e os dois virariam um caso só.
        """
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), casos=[_caso("trabalhista")])
        )

        assert "caso novo" in nota
        assert "sem misturar" in nota

    async def test_sem_caso_registrado_nao_fala_de_caso(self):
        nota = await nota_de_atendimento_anterior(
            "5561999", "conv-1", _db(lead=_lead(), casos=[])
        )

        assert "Casos já registrados" not in nota


class TestContraOBancoDeVerdade:
    """
    Os casos acima usam mock, e mock responde o que o teste mandar.

    Este projeto já perdeu uma tarde com um teste que passava porque o mock
    devolvia relacionamento sem IO, enquanto o PostgreSQL estourava
    `greenlet_spawn`. Consulta nova com `join` merece uma passada no banco de
    verdade antes de virar produção.
    """

    @pytest.mark.asyncio
    async def test_a_consulta_do_card_roda_no_postgres(self):
        from app.db.database import AsyncSessionLocal
        from app.db.models import Agent, Caso, Conversation, KanbanCard, User
        from app.services.kanban_defaults import criar_colunas_padrao
        from sqlalchemy import select as _select
        from app.db.models import KanbanColumn

        async with AsyncSessionLocal() as db:
            db.add(
                User(
                    id="ctx-user",
                    email="ctx@example.com",
                    nome="Dono",
                    senha_hash="x",
                    status="ativo",
                )
            )
            await db.flush()
            db.add(
                Agent(
                    id="ctx-agent",
                    user_id="ctx-user",
                    nome="Triagem",
                    system_prompt="x",
                    temperatura=0.7,
                    max_tokens=1024,
                    status="ativo",
                )
            )
            conversa = Conversation(
                id="ctx-conv",
                agent_id="ctx-agent",
                phone_number="5561911111111",
                status="ativa",
            )
            db.add(conversa)
            lead = Lead(
                id="ctx-lead",
                phone_number="5561911111111",
                conversation_id="ctx-conv",
                nome="Marcos",
                status_funil="qualificado",
            )
            db.add(lead)
            await db.commit()

            await criar_colunas_padrao("ctx-agent", db)
            await db.commit()

            coluna = (
                await db.execute(
                    _select(KanbanColumn)
                    .where(KanbanColumn.agent_id == "ctx-agent")
                    .where(KanbanColumn.nome == "Viabilidade")
                )
            ).scalars().first()

            db.add(KanbanCard(column_id=coluna.id, lead_id="ctx-lead", ordem=1))
            db.add(
                Caso(
                    lead_id="ctx-lead",
                    area="trabalhista",
                    resumo="Justa causa sem prova",
                    data_abertura=datetime(2026, 8, 12, 14, 0),
                )
            )
            await db.commit()

            nota = await nota_de_atendimento_anterior(
                "5561911111111", "ctx-conv", db
            )

        assert "Viabilidade" in nota
        assert "trabalhista" in nota
        assert "caso novo" in nota
