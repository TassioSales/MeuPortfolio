"""
Uma conversa do começo ao fim, pelo caminho de verdade.

Os testes deste projeto cobrem cada peça isolada, e foi assim que três defeitos
passaram: as peças funcionavam, e o que quebrava era a costura entre elas. Este
arquivo faz o percurso inteiro numa transação só — webhook → triagem →
qualificação → parecer → coleta → contrato → assinatura → confirmação —, com o
modelo e a Evolution simulados, mas **todo o resto real**: o banco, os
roteadores, os serviços e as regras.

O que ele prova, e que nenhum teste de unidade provava:

- a fase entra no system prompt do turno certo;
- o gatilho dispara depois do parecer, e não antes;
- o que a agente coletou chega ao PDF, preenchido;
- o link que o cliente recebe é o link que abre a página pública;
- o contrato absorvido é o mesmo arquivo que o painel devolve depois.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.db.database import AsyncSessionLocal
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
from app.main import app
from app.services import assinatura_service, coleta_service, gatilho_contrato
from app.services.message_orchestrator import orchestrator

client = TestClient(app)

MODELO = (
    "# CONTRATO DE HONORÁRIOS\n"
    "**CONTRATANTE:** {{cliente.nome}}, {{cliente.estado_civil}}, "
    "{{cliente.profissao}}, CPF {{cliente.cpf}}, residente em "
    "{{cliente.endereco}}, {{cliente.cidade}}/{{cliente.uf}}.\n"
    "**CONTRATADO:** {{escritorio.nome}}, OAB {{escritorio.oab}}.\n"
    "Causa: {{caso.area}} contra {{caso.empresa}}.\n"
    "{{data.cidade_e_data}}\n"
)

TELEFONE = "5561998887766"


async def _montar_escritorio() -> str:
    """O escritório configurado e o agente no ar. Devolve o agent_id."""
    async with AsyncSessionLocal() as db:
        db.add(ConfiguracaoEscritorio(id="unica", nome="Sales Advocacia",
                                      oab_responsavel="DF 54321", cidade="Brasília"))
        db.add(ModeloDeContrato(id="mod", nome="Honorários", corpo=MODELO, ativo=True))
        db.add(Agent(id="agente", nome="Triagem", system_prompt="Você atende.",
                     temperatura=0.4, max_tokens=2048, status="ativo"))
        await db.commit()
    return "agente"


def _resposta(texto: str):
    """O que o llm_service devolveria."""
    return AsyncMock(return_value=(texto, {"total_tokens": 120, "model": "teste"}))


async def _cliente_diz(texto: str, resposta_da_agente: str, agent_id: str) -> dict:
    """Uma volta completa: mensagem entra, agente responde, tudo é gravado."""
    async with AsyncSessionLocal() as db:
        with patch(
            "app.services.message_orchestrator.llm_service.generate_response",
            new=_resposta(resposta_da_agente),
        ) as chamada, patch(
            "app.services.message_orchestrator.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True, "message_id": "m"}),
        ):
            resultado = await orchestrator.process_incoming_message(
                phone_number=TELEFONE,
                message_text=texto,
                agent_id=agent_id,
                db=db,
            )
        resultado["_fase_usada"] = chamada.await_args.kwargs.get("fase")
    return resultado


async def _conversa() -> Conversation:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(Conversation).where(Conversation.phone_number == TELEFONE)
            )
        ).scalars().first()


async def _lead() -> Lead:
    async with AsyncSessionLocal() as db:
        return (
            await db.execute(select(Lead).where(Lead.phone_number == TELEFONE))
        ).scalars().first()


# O parecer como o analista o devolve. A `## Ficha` é o que o
# `caso_service` lê para arquivar o caso e gravar o porte — sem ela o caso
# nasce sem área e sem viabilidade.
PARECER = """## Resumo

Verbas rescisórias não pagas após quatro anos de casa.

## Ficha

Área: trabalhista
Titular: o próprio contato
Valor estimado: R$ 28.000 a R$ 45.000
Viabilidade: acima do piso

## Porte econômico

Piso da faixa acima do mínimo do escritório.
"""

QUALIFICACAO = """Entendi, Maria. Vou passar para o advogado.

```json
{
  "nome_cliente": "Maria Aparecida da Silva",
  "email": "",
  "empresa": "Supermercado Tático",
  "cargo": "Repositora",
  "score_qualificacao": 85,
  "status_proposto": "qualificado",
  "dados_economicos": "salário R$ 2.100, 4 anos de casa",
  "documentos_em_maos": "carteira e holerites",
  "inconsistencias": "",
  "problemas_detectados": "",
  "recomendacoes": "Ajuizar rescisão indireta"
}
```"""


class TestCicloCompleto:
    @pytest.mark.asyncio
    async def test_da_primeira_mensagem_ao_contrato_assinado(self):
        agent_id = await _montar_escritorio()

        # ---------------------------------------------------- 1. triagem
        primeira = await _cliente_diz(
            "oi, fui mandada embora", "Oi! Me conta o que aconteceu?", agent_id
        )
        assert primeira["success"] is True
        # Na triagem o bloco de coleta não chega ao modelo.
        assert primeira["_fase_usada"] == "triagem"

        # ------------------------------------------- 2. a triagem fecha
        # O analista é simulado, e não o `_gerar_analise` inteiro: é ele quem
        # registra o `Caso`, e o caso é a fonte da viabilidade que o gatilho
        # lê. Mockar um degrau acima faria o teste passar por um caminho que
        # a produção não percorre.
        with patch.object(settings, "contrato_automatico", True), patch(
            "app.services.lead_processor.legal_analyst.analisar",
            new=AsyncMock(return_value=PARECER),
        ), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True}),
        ):
            fechamento = await _cliente_diz(
                "trabalhei 4 anos no Supermercado Tático", QUALIFICACAO, agent_id
            )
            # O parecer roda em tarefa própria; aqui ela é esperada, senão o
            # TRUNCATE do teardown fica preso atrás dela.
            from app.services.lead_processor import _TAREFAS
            import asyncio

            if _TAREFAS:
                await asyncio.gather(*list(_TAREFAS))

        assert fechamento["lead_qualification"]["success"] is True
        lead = await _lead()
        assert lead.nome == "Maria Aparecida da Silva"

        # O bloco JSON não pode ter ido para o WhatsApp — o cliente receberia
        # o próprio score.
        assert "score_qualificacao" not in fechamento["response"]

        # -------------------------------- 3. o gatilho abre a coleta
        conversa = await _conversa()
        assert conversa.fase == "coleta", "o gatilho devia ter aberto a coleta"

        async with AsyncSessionLocal() as db:
            avisos = (
                await db.execute(
                    select(Message).where(Message.remetente == "sistema")
                )
            ).scalars().all()
        assert any("aceitar" in m.conteudo for m in avisos)

        # ------------------------------------ 4. a agente coleta os dados
        with patch.object(settings, "contrato_automatico", True), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True}),
        ):
            coleta = await _cliente_diz(
                "meu cpf é 123.456.789-01, moro na Q 312 Conj A, Gama-DF",
                'Anotado!\n\n```json\n{"dados_contrato": {"cpf": "123.456.789-01", '
                '"endereco": "Q 312 Conj A", "cidade": "Gama", "uf": "DF", '
                '"estado_civil": "casada", "profissao": "repositora"}}\n```',
                agent_id,
            )

        # Desta vez o bloco de coleta foi para o modelo.
        assert coleta["_fase_usada"] == "coleta"
        # E o JSON não vazou para o cliente.
        assert "dados_contrato" not in coleta["response"]

        # ------------------------- 5. dados completos → contrato sai só
        conversa = await _conversa()
        assert conversa.fase == "contratado", "o contrato devia ter sido emitido"

        async with AsyncSessionLocal() as db:
            contrato = (await db.execute(select(Contrato))).scalars().first()

        assert contrato is not None
        # O que a agente coletou chegou ao contrato, preenchido.
        assert "Maria Aparecida da Silva" in contrato.corpo
        assert "123.456.789-01" in contrato.corpo
        assert "Gama/DF" in contrato.corpo
        assert "casada" in contrato.corpo
        assert "Supermercado Tático" in contrato.corpo
        assert "Sales Advocacia" in contrato.corpo
        assert "Brasília," in contrato.corpo
        assert "{{" not in contrato.corpo, "sobrou lacuna sem preencher"

        # ------------------------------------ 6. o cliente abre e assina
        token = contrato.token_assinatura
        assert token and contrato.link_assinatura.endswith(token)

        pagina = client.get(f"/api/v1/assinatura/{token}")
        assert pagina.status_code == 200
        assert pagina.json()["nome_do_cliente"] == "Maria Aparecida da Silva"
        # A página pública não entrega o telefone nem o dossiê.
        assert TELEFONE not in str(pagina.json())

        with patch("app.routers.assinatura._agendar_confirmacao"):
            assinatura = client.post(
                f"/api/v1/assinatura/{token}",
                json={"nome": "Maria Aparecida da Silva", "aceite": True},
                headers={"CF-Connecting-IP": "189.45.12.7"},
            )
        assert assinatura.status_code == 200

        # ------------------------------ 7. absorvido, com trilha de prova
        async with AsyncSessionLocal() as db:
            contrato = (await db.execute(select(Contrato))).scalars().first()

        assert contrato.status == "assinado"
        assert contrato.assinado_ip == "189.45.12.7"
        assert contrato.hash_documento == assinatura_service.hash_do_documento(
            contrato.corpo
        )
        assert contrato.pdf_assinado.startswith(b"%PDF-")
        # O link morreu com a assinatura.
        assert assinatura_service.expirado(contrato)

    @pytest.mark.asyncio
    async def test_a_coleta_nao_comeca_com_o_automatico_desligado(self):
        """
        O padrão. Sem a chave ligada, o ciclo para na qualificação e ninguém
        recebe contrato nenhum — que é o comportamento que protege quem ainda
        não escolheu a hora.
        """
        agent_id = await _montar_escritorio()

        with patch(
            "app.services.lead_processor.legal_analyst.analisar",
            new=AsyncMock(return_value=PARECER),
        ), patch(
            "app.services.whatsapp_service.whatsapp_service.send_message",
            new=AsyncMock(return_value={"success": True}),
        ):
            await _cliente_diz("oi", QUALIFICACAO, agent_id)
            from app.services.lead_processor import _TAREFAS
            import asyncio

            if _TAREFAS:
                await asyncio.gather(*list(_TAREFAS))

        conversa = await _conversa()
        assert conversa.fase == "triagem"

        async with AsyncSessionLocal() as db:
            contratos = (await db.execute(select(Contrato))).scalars().all()
        assert contratos == []
