"""
Quem entra no painel — pelo terminal.

Existe porque o painel tem um problema de ovo e galinha: só administrador
administra acessos, e o único administrador que o sistema cria sozinho é o
**primeiro cadastro**, que já aconteceu. Se esse primeiro acesso foi criado
antes de existir papel, ele nasceu `operador` e ninguém no sistema consegue
promovê-lo pela tela. Este script é a chave de fenda para esse caso — e para
a senha esquecida, que por decisão de projeto nenhum administrador troca pela
API (trocar a senha de outro é poder entrar como ele).

    python scripts/acessos.py --listar
    python scripts/acessos.py --promover tassio.ljs@gmail.com
    python scripts/acessos.py --criar ana@escritorio.com --nome "Ana" --nova "..."
    python scripts/acessos.py --senha ana@escritorio.com --nova "..."

Roda dentro do container do backend, que é onde o `DATABASE_URL` aponta para o
Postgres:

    docker compose exec backend python scripts/acessos.py --listar
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import User
from app.services.auth_service import auth_service

SENHA_MINIMA = 8


async def _buscar(db, email: str) -> User:
    resultado = await db.execute(select(User).where(User.email == email))
    usuario = resultado.scalars().first()
    if usuario is None:
        raise SystemExit(f"Não existe acesso com o e-mail {email}.")
    return usuario


async def listar() -> None:
    async with AsyncSessionLocal() as db:
        resultado = await db.execute(select(User).order_by(User.data_criacao))
        usuarios = resultado.scalars().all()

    if not usuarios:
        print("Nenhum acesso cadastrado.")
        return

    largura = max(len(u.email) for u in usuarios)
    print(f"{'E-MAIL'.ljust(largura)}  {'PAPEL'.ljust(9)}  {'STATUS'.ljust(8)}  NOME")
    for u in usuarios:
        print(f"{u.email.ljust(largura)}  {u.papel.ljust(9)}  {u.status.ljust(8)}  {u.nome}")


async def definir_papel(email: str, papel: str) -> None:
    async with AsyncSessionLocal() as db:
        usuario = await _buscar(db, email)
        if usuario.papel == papel:
            print(f"{email} já é {papel}. Nada a fazer.")
            return
        usuario.papel = papel
        # Promover quem está inativo entrega privilégio a uma conta que não
        # entra: o papel mudaria e o login continuaria recusando.
        if papel == "admin" and usuario.status != "ativo":
            print(f"{email} estava {usuario.status!r}; reativado junto.")
            usuario.status = "ativo"
        await db.commit()
    print(f"{email} agora é {papel}.")


async def criar(email: str, nome: str, senha: str, papel: str) -> None:
    if len(senha) < SENHA_MINIMA:
        raise SystemExit(f"A senha precisa de pelo menos {SENHA_MINIMA} caracteres.")

    async with AsyncSessionLocal() as db:
        resultado = await db.execute(select(User).where(User.email == email))
        if resultado.scalars().first() is not None:
            raise SystemExit(f"Já existe acesso com o e-mail {email}.")

        db.add(
            User(
                email=email,
                nome=nome,
                senha_hash=auth_service.hash_password(senha),
                papel=papel,
                status="ativo",
            )
        )
        await db.commit()
    print(f"Acesso criado: {email} ({papel}).")


async def trocar_senha(email: str, nova: str) -> None:
    if len(nova) < SENHA_MINIMA:
        raise SystemExit(f"A senha precisa de pelo menos {SENHA_MINIMA} caracteres.")

    async with AsyncSessionLocal() as db:
        usuario = await _buscar(db, email)
        usuario.senha_hash = auth_service.hash_password(nova)
        await db.commit()
    print(f"Senha trocada para {email}.")


def main() -> None:
    p = argparse.ArgumentParser(description="Administra acessos ao painel.")
    p.add_argument("--listar", action="store_true", help="mostra todos os acessos")
    p.add_argument("--promover", metavar="EMAIL", help="torna o acesso administrador")
    p.add_argument("--rebaixar", metavar="EMAIL", help="torna o acesso operador")
    p.add_argument("--criar", metavar="EMAIL", help="cria um acesso novo")
    p.add_argument("--nome", help="nome de quem usa o acesso (com --criar)")
    p.add_argument("--papel", default="operador", choices=["admin", "operador"])
    p.add_argument("--senha", metavar="EMAIL", help="troca a senha deste acesso")
    p.add_argument("--nova", help="a senha nova (com --criar ou --senha)")

    args = p.parse_args()

    if args.listar:
        asyncio.run(listar())
    elif args.promover:
        asyncio.run(definir_papel(args.promover, "admin"))
    elif args.rebaixar:
        asyncio.run(definir_papel(args.rebaixar, "operador"))
    elif args.criar:
        if not args.nome or not args.nova:
            raise SystemExit("--criar exige --nome e --nova.")
        asyncio.run(criar(args.criar, args.nome, args.nova, args.papel))
    elif args.senha:
        if not args.nova:
            raise SystemExit("--senha exige --nova.")
        asyncio.run(trocar_senha(args.senha, args.nova))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
