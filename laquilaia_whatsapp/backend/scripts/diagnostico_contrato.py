"""
Por que o contrato não saiu para este cliente.

O gatilho do contrato depende de seis condições, e quando uma falha o efeito é
o mesmo: nada acontece. Sem este script, descobrir qual delas foi exige ler
log, consultar o banco e conhecer o código — o que na prática significa
perguntar a quem escreveu.

    python -m scripts.diagnostico_contrato --telefone 5561982970840
    python -m scripts.diagnostico_contrato --ultimo
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import (
    Caso,
    Contrato,
    Conversation,
    Lead,
    LeadDetails,
    ModeloDeContrato,
)
from app.services import coleta_service, gatilho_contrato


def _marca(ok: bool) -> str:
    return "✓" if ok else "✗"


async def diagnosticar(telefone: str = "", ultimo: bool = False) -> int:
    async with AsyncSessionLocal() as db:
        busca = select(Lead).order_by(Lead.data_criacao.desc())
        if telefone:
            so_digitos = "".join(c for c in telefone if c.isdigit())
            busca = busca.where(Lead.phone_number.ilike(f"%{so_digitos}%"))
        lead = (await db.execute(busca)).scalars().first()

        if lead is None:
            print("Nenhum lead encontrado" + (f" para {telefone}" if telefone else ""))
            return 1

        print(f"Lead: {lead.nome or '(sem nome)'}  ·  {lead.phone_number}")
        print(f"Funil: {lead.status_funil or '(vazio)'}")
        print()

        # ------------------------------------------------------ a corrente
        print("O que o gatilho exige:")

        ligado = settings.contrato_automatico
        print(f"  {_marca(ligado)} CONTRATO_AUTOMATICO ligado")
        if not ligado:
            print("      → ponha CONTRATO_AUTOMATICO=true no .env e recrie o backend")

        conversa = (
            await db.execute(
                select(Conversation).where(Conversation.id == lead.conversation_id)
            )
        ).scalars().first()
        ok_conversa = conversa is not None and conversa.status == "ativa"
        print(
            f"  {_marca(ok_conversa)} conversa ativa "
            f"(status: {getattr(conversa, 'status', '?')}, "
            f"fase: {getattr(conversa, 'fase', '?')})"
        )
        if conversa is not None and conversa.status == "pausada":
            print("      → um humano assumiu; o robô não fala por cima")

        detalhes = (
            await db.execute(
                select(LeadDetails).where(LeadDetails.lead_id == lead.id)
            )
        ).scalars().first()
        tem_parecer = bool(detalhes and detalhes.analise_preliminar)
        print(f"  {_marca(tem_parecer)} parecer gerado")
        if not tem_parecer:
            print("      → sem parecer não há caso, e sem caso o gatilho não dispara.")
            print(f"      → ANALISE_JURIDICA_ENABLED={settings.analise_juridica_enabled}")

        caso = (
            await db.execute(
                select(Caso)
                .where(Caso.lead_id == lead.id)
                .order_by(Caso.data_abertura.desc())
            )
        ).scalars().first()
        print(f"  {_marca(caso is not None)} caso arquivado", end="")
        if caso is not None:
            print(f" (área: {caso.area}, viabilidade: {caso.viabilidade})")
            if (caso.viabilidade or "") in gatilho_contrato.VETADOS:
                print("      → viabilidade abaixo do piso barra o contrato")
        else:
            print()
            if tem_parecer:
                # Caso mais insidioso: o parecer saiu e a ficha não foi lida.
                print("      → o parecer existe mas a `## Ficha` não foi lida.")
                print("        Veja o parecer no dossiê: a linha 'Área:' está lá?")

        modelo = (
            await db.execute(
                select(ModeloDeContrato).where(ModeloDeContrato.ativo.is_(True))
            )
        ).scalars().first()
        print(f"  {_marca(modelo is not None)} modelo de contrato ativo", end="")
        print(f" ({modelo.nome})" if modelo else "")
        if modelo is None:
            print("      → Contratos → Modelos → marque 'usar nos contratos novos'")

        contratos = (
            await db.execute(select(Contrato).where(Contrato.lead_id == lead.id))
        ).scalars().all()
        print(f"  {_marca(not contratos)} nenhum contrato ainda ({len(contratos)})")
        for c in contratos:
            print(f"      · {c.id[:8]} — {c.status}", end="")
            print(f", assinado em {c.data_assinatura}" if c.data_assinatura else "")

        # ------------------------------------------------------- veredito
        print()
        pode, motivo = await gatilho_contrato.pode_abrir_coleta(db, lead, caso)
        if pode:
            print("→ O gatilho ABRIRIA a coleta agora.")
        else:
            print(f"→ O gatilho NÃO abre: {motivo}")

        # ------------------------------------------------ dados coletados
        if conversa is not None and conversa.fase == coleta_service.FASE_COLETA:
            dados = await coleta_service.dados_do_lead(db, lead.id)
            faltam = coleta_service.o_que_falta(dados)
            print()
            if faltam:
                print(f"Coleta em andamento. Faltam: {', '.join(faltam)}")
            else:
                print("Coleta completa — o contrato sai na próxima mensagem.")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telefone", default="", help="filtra pelo número")
    parser.add_argument(
        "--ultimo", action="store_true", help="o lead mais recente (padrão)"
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(diagnosticar(args.telefone, args.ultimo)))
