"""
Põe um rascunho de contrato no banco, para a tela não abrir vazia.

Nasce **inativo**: nenhum contrato sai dele antes de alguém ler, preencher o
percentual de honorários e ativar. Ver `app/prompts/modelo_contrato_base.py`
sobre por que o percentual é lacuna.

    python -m scripts.semear_modelo_contrato
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import ModeloDeContrato
from app.prompts.modelo_contrato_base import MODELO_BASE, NOME_BASE
from app.services import contrato_service


async def semear() -> int:
    desconhecidas = contrato_service.variaveis_desconhecidas(MODELO_BASE)
    if desconhecidas:
        # Falha aqui, não na tela do advogado: uma lacuna escrita errada no
        # rascunho viraria um espaço em branco no contrato do cliente.
        print(f"❌ O rascunho usa variáveis inexistentes: {', '.join(desconhecidas)}")
        return 1

    async with AsyncSessionLocal() as db:
        ja = await db.execute(
            select(ModeloDeContrato).where(ModeloDeContrato.nome == NOME_BASE)
        )
        if ja.scalars().first() is not None:
            print(f"✓ '{NOME_BASE}' já existe — nada a fazer.")
            return 0

        db.add(ModeloDeContrato(nome=NOME_BASE, corpo=MODELO_BASE, ativo=False))
        await db.commit()

    print(f"✓ Rascunho '{NOME_BASE}' criado, inativo.")
    print("  Abra Contratos → Modelos, preencha o percentual de honorários e ative.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(semear()))
