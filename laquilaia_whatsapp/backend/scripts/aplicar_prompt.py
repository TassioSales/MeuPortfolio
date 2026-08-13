"""
Escreve o prompt canônico de triagem no `system_prompt` de um agente.

O prompt do agente é editável pelo painel, e é para ser mesmo — quem atende
precisa poder experimentar sem esperar deploy. O que faltava era o caminho de
volta: depois de três experimentos, ninguém lembra qual era o texto bom, porque
o painel guarda um valor só e não guarda histórico.

Este script é esse caminho. Ele imprime o que vai trocar e pede confirmação,
porque sobrescrever o prompt de um agente em atendimento muda o que o próximo
cliente vai ouvir.

    python -m scripts.aplicar_prompt --listar
    python -m scripts.aplicar_prompt --agente <id>
    python -m scripts.aplicar_prompt --agente <id> --sim   # sem perguntar
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Agent
from app.prompts import PROMPT_TRIAGEM_JURIDICA


async def listar() -> None:
    async with AsyncSessionLocal() as db:
        agentes = (await db.execute(select(Agent))).scalars().all()

    if not agentes:
        print("Nenhum agente cadastrado.")
        return

    for a in agentes:
        atual = (a.system_prompt or "").strip()
        marca = "=" if atual == PROMPT_TRIAGEM_JURIDICA.strip() else " "
        print(f"[{marca}] {a.id}  {a.nome}  ({len(atual)} caracteres)")
    print("\n'=' marca os agentes que já estão com o prompt canônico.")


async def aplicar(agent_id: str, sem_perguntar: bool) -> int:
    async with AsyncSessionLocal() as db:
        agente = (
            await db.execute(select(Agent).where(Agent.id == agent_id))
        ).scalars().first()

        if agente is None:
            print(f"Agente {agent_id} não existe.", file=sys.stderr)
            return 1

        atual = (agente.system_prompt or "").strip()
        if atual == PROMPT_TRIAGEM_JURIDICA.strip():
            print(f"{agente.nome} já está com o prompt canônico. Nada a fazer.")
            return 0

        print(f"Agente:  {agente.nome} ({agente.id})")
        print(f"Atual:   {len(atual)} caracteres")
        print(f"Novo:    {len(PROMPT_TRIAGEM_JURIDICA.strip())} caracteres")

        if not sem_perguntar:
            # O prompt atual pode ser um ajuste fino que ninguém salvou em
            # outro lugar — mostrar antes de perder é o mínimo.
            print("\n--- primeiras linhas do prompt atual ---")
            print("\n".join(atual.split("\n")[:8]) or "(vazio)")
            print("---")
            if input("\nSobrescrever? [s/N] ").strip().lower() not in {"s", "sim"}:
                print("Cancelado.")
                return 1

        agente.system_prompt = PROMPT_TRIAGEM_JURIDICA.strip()
        await db.commit()

    print("Prompt aplicado.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listar", action="store_true", help="mostra os agentes")
    parser.add_argument("--agente", help="id do agente que recebe o prompt")
    parser.add_argument(
        "--sim", action="store_true", help="aplica sem pedir confirmação"
    )
    args = parser.parse_args()

    if args.listar:
        asyncio.run(listar())
        return 0

    if not args.agente:
        parser.print_help()
        return 1

    return asyncio.run(aplicar(args.agente, args.sim))


if __name__ == "__main__":
    raise SystemExit(main())
