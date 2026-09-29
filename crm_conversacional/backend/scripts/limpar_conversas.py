"""
Apaga o histórico de atendimento para recomeçar os testes do zero.

**O que vai embora:** conversas, mensagens, leads, casos, dossiês, cards do
Kanban, linha do tempo, agendamentos, contratos (inclusive os assinados) e os
dados civis coletados.

**O que fica:** usuários e senhas, agentes e seus prompts, colunas do Kanban,
configuração do escritório, modelos de contrato e lançamentos de marketing. É
a configuração do escritório — apagá-la obrigaria a refazer tudo à mão antes
de poder testar de novo.

Isto é **irreversível** e não há cópia. Por isso pede confirmação digitada, e
por isso imprime antes o que vai apagar: um `--sim` distraído num banco de
produção destrói contrato assinado, que é documento.

    python -m scripts.limpar_conversas            # mostra e pergunta
    python -m scripts.limpar_conversas --sim      # sem perguntar
"""

import argparse
import asyncio
import sys

from sqlalchemy import func, select, text

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Agendamento,
    Caso,
    Contrato,
    Conversation,
    DadosDoContrato,
    KanbanCard,
    Lead,
    LeadDetails,
    LeadTimeline,
    Message,
)

# Ordem importa: filha antes de mãe. O `CASCADE` do Postgres resolveria, mas
# apagar explicitamente é o que deixa a lista acima ser lida e conferida —
# um `TRUNCATE ... CASCADE` em `conversations` levaria junto tabelas que
# ninguém listou aqui, e ninguém notaria.
TABELAS = [
    ("Mensagens", Message),
    ("Contratos", Contrato),
    ("Dados do contrato", DadosDoContrato),
    ("Agendamentos", Agendamento),
    ("Linha do tempo", LeadTimeline),
    ("Cards do Kanban", KanbanCard),
    ("Dossiês", LeadDetails),
    ("Casos", Caso),
    ("Leads", Lead),
    ("Conversas", Conversation),
]


async def contar() -> dict:
    async with AsyncSessionLocal() as db:
        contagens = {}
        for rotulo, modelo in TABELAS:
            total = (await db.execute(select(func.count(modelo.id)))).scalar()
            contagens[rotulo] = total or 0
        assinados = (
            await db.execute(
                select(func.count(Contrato.id)).where(
                    Contrato.data_assinatura.isnot(None)
                )
            )
        ).scalar() or 0
    return {"contagens": contagens, "assinados": assinados}


async def apagar() -> None:
    async with AsyncSessionLocal() as db:
        for rotulo, modelo in TABELAS:
            await db.execute(text(f"DELETE FROM {modelo.__tablename__}"))
        # As conversas voltam a zerar os contadores de follow-up junto, porque
        # a linha inteira some — nada a reiniciar.
        await db.commit()


async def principal(sem_perguntar: bool) -> int:
    estado = await contar()
    total = sum(estado["contagens"].values())

    if total == 0:
        print("Nada para apagar: o histórico já está vazio.")
        return 0

    print("Vai apagar:")
    for rotulo, quantos in estado["contagens"].items():
        if quantos:
            print(f"  {quantos:>6}  {rotulo}")

    if estado["assinados"]:
        # Contrato assinado é documento, com trilha de prova e PDF absorvido.
        # Merece um aviso próprio, não uma linha no meio da lista.
        print()
        print(f"  ⚠️  {estado['assinados']} contrato(s) ASSINADO(S) serão destruídos,")
        print("      com o PDF e a trilha de prova. Isso não tem volta.")

    print()
    print("Continuam intactos: usuários, agentes, colunas do Kanban,")
    print("configuração do escritório e modelos de contrato.")
    print()

    if not sem_perguntar:
        resposta = input("Digite APAGAR para confirmar: ").strip()
        if resposta != "APAGAR":
            print("Cancelado. Nada foi apagado.")
            return 1

    await apagar()
    print("✓ Histórico apagado. Pode recomeçar os testes.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sim", action="store_true", help="não pergunta antes de apagar"
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(principal(args.sim)))
