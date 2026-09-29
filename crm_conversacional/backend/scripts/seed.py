"""
Dados de exemplo para desenvolvimento.

Cria um usuário, um agente, algumas conversas e leads espalhados pelo funil,
para o painel ter o que mostrar sem precisar de uma instância do WhatsApp.

    python scripts/seed.py

É idempotente: rodar de novo não duplica nada.

Nunca rode isto em produção — a senha do usuário de exemplo é pública.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agent,
    Conversation,
    KanbanCard,
    KanbanColumn,
    Lead,
    LeadDetails,
    Message,
    User,
)
from app.services.auth_service import auth_service

# `example.com` é reservado pela RFC 2606 e nunca vai existir de verdade.
# Não use `.local` nem `.test`: o seed grava direto pelo SQLAlchemy e aceita,
# mas o `EmailStr` do schema recusa esses TLDs como de uso especial — o
# usuário era criado e depois não conseguia entrar pelo /auth/login (422).
DEMO_EMAIL = "demo@example.com"
DEMO_SENHA = "demo12345"

COLUNAS = [
    ("Novo Lead", "novo", "#3164ff"),
    ("Em Qualificação", "em_qualificacao", "#5598e7"),
    ("Lead Qualificado", "qualificado", "#16a34a"),
    ("Agendado", "agendado", "#eda100"),
    ("Arquivado", "arquivado", "#52514e"),
]

LEADS = [
    ("Maria Silva", "maria@example.com", "5561999990001", "qualificado", 88),
    ("João Souza", None, "5561999990002", "novo", 35),
    ("Ana Costa", "ana@example.com", "5561999990003", "em_qualificacao", 62),
    ("Pedro Lima", None, "5561999990004", "agendado", 91),
    ("Carla Dias", "carla@example.com", "5561999990005", "novo", 44),
    ("Rui Alves", None, "5561999990006", "arquivado", 12),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        existente = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = existente.scalars().first()

        if user is None:
            user = User(
                email=DEMO_EMAIL,
                nome="Usuário Demo",
                senha_hash=auth_service.hash_password(DEMO_SENHA),
                status="ativo",
            )
            db.add(user)
            await db.flush()
            print(f"✅ Usuário criado: {DEMO_EMAIL} / {DEMO_SENHA}")
        else:
            print(f"ℹ️ Usuário já existia: {DEMO_EMAIL}")

        agente_existente = await db.execute(
            select(Agent).where(Agent.user_id == user.id)
        )
        agent = agente_existente.scalars().first()

        if agent is None:
            agent = Agent(
                user_id=user.id,
                nome="Qualificador de leads",
                descricao="Atende e qualifica clientes no WhatsApp",
                system_prompt=(
                    "Você é um assistente de vendas. Faça perguntas para entender "
                    "a necessidade do cliente e qualifique o lead."
                ),
                temperatura=0.7,
                max_tokens=1024,
                status="ativo",
            )
            db.add(agent)
            await db.flush()
            print(f"✅ Agente criado: {agent.nome}")
        else:
            print(f"ℹ️ Agente já existia: {agent.nome}")

        colunas_existentes = await db.execute(
            select(KanbanColumn).where(KanbanColumn.agent_id == agent.id)
        )
        colunas = {c.nome: c for c in colunas_existentes.scalars().all()}

        for ordem, (nome, _status, cor) in enumerate(COLUNAS):
            if nome not in colunas:
                coluna = KanbanColumn(
                    agent_id=agent.id, nome=nome, ordem=ordem, cor_hex=cor
                )
                db.add(coluna)
                await db.flush()
                colunas[nome] = coluna

        coluna_por_status = {
            status: colunas[nome] for nome, status, _ in COLUNAS
        }
        print(f"✅ {len(colunas)} colunas do funil prontas")

        agora = datetime.utcnow()
        criados = 0

        for indice, (nome, email, telefone, status_funil, score) in enumerate(LEADS):
            ja_existe = await db.execute(
                select(Conversation).where(
                    (Conversation.agent_id == agent.id)
                    & (Conversation.phone_number == telefone)
                )
            )
            if ja_existe.scalars().first() is not None:
                continue

            # Espalha as conversas pelos últimos dias, para o gráfico de linha
            # ter variação em vez de uma barra única no dia de hoje.
            quando = agora - timedelta(days=indice % 5, hours=indice)

            conversa = Conversation(
                agent_id=agent.id,
                phone_number=telefone,
                status="ativa",
                data_inicio=quando,
                data_ultima_msg=quando,
            )
            db.add(conversa)
            await db.flush()

            db.add(
                Message(
                    conversation_id=conversa.id,
                    remetente="user",
                    conteudo="Olá, queria saber mais sobre o serviço.",
                    timestamp=quando,
                )
            )
            db.add(
                Message(
                    conversation_id=conversa.id,
                    remetente="assistant",
                    conteudo="Claro! Me conta um pouco sobre o que você precisa.",
                    timestamp=quando + timedelta(seconds=40),
                )
            )

            lead = Lead(
                conversation_id=conversa.id,
                phone_number=telefone,
                nome=nome,
                email=email,
                status_funil=status_funil,
                data_criacao=quando,
                data_atualizacao=quando,
            )
            db.add(lead)
            await db.flush()

            db.add(
                LeadDetails(
                    lead_id=lead.id,
                    score_qualificacao=score,
                    problemas_detectados="preço alto" if score < 50 else None,
                )
            )
            db.add(
                KanbanCard(
                    column_id=coluna_por_status[status_funil].id,
                    lead_id=lead.id,
                    ordem=indice,
                    data_movimentacao=quando,
                )
            )
            criados += 1

        await db.commit()
        print(f"✅ {criados} leads criados" if criados else "ℹ️ Leads já existiam")
        print("\n🎉 Pronto. Entre em http://localhost:3000 com:")
        print(f"   e-mail: {DEMO_EMAIL}")
        print(f"   senha:  {DEMO_SENHA}")


if __name__ == "__main__":
    asyncio.run(seed())
