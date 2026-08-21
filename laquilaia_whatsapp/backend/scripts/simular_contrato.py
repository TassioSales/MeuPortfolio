"""
Deixa o sistema pronto para gerar um contrato de ponta a ponta.

Serve para **simular**, não para configurar o escritório de verdade. Ele faz
duas coisas:

1. Preenche a configuração do escritório — **só os campos vazios**. O que você
   já tiver digitado no painel fica como está: um script de teste que
   sobrescreve dado real é um jeito rápido de perder dado real.
2. Cria um modelo de contrato **de exemplo**, ativo, com o percentual de
   honorários preenchido.

Sobre o percentual: ele existe aqui porque o dono pediu, para poder testar o
fluxo inteiro sem ter de decidir o número antes da hora. É um valor de
exemplo, editável no painel, num modelo cujo nome diz "exemplo" — não um
default escondido do software. O rascunho sem percentual continua existindo em
`scripts.semear_modelo_contrato`, e é ele que serve para valer.

    python -m scripts.simular_contrato
"""

import asyncio
import sys

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import ConfiguracaoEscritorio, ModeloDeContrato
from app.prompts.modelo_contrato_base import MODELO_BASE
from app.services import contrato_service

NOME_DO_EXEMPLO = "Honorários advocatícios (exemplo)"

# Percentual de exemplo. É o que o escritório concorrente anuncia no
# atendimento dele; serve para o fluxo rodar, não como recomendação.
PERCENTUAL = "30% (trinta por cento)"

ESCRITORIO_DE_EXEMPLO = {
    "nome": "Sales & Associados Advocacia",
    "cnpj": "12.345.678/0001-90",
    "oab_responsavel": "DF 54321",
    "fundador": "Tássio Lucian Sales",
    "endereco": "SCS Quadra 2, Bloco C, sala 405, Asa Sul",
    "cidade": "Brasília",
    "email": "contato@salesadvocacia.com.br",
    "telefone": "(61) 3333-4444",
    "horario_atendimento": "Seg a sex, 9h às 18h",
}


def _com_percentual(corpo: str) -> str:
    """Troca a lacuna de honorários do rascunho pelo valor de exemplo."""
    return corpo.replace(
        "o percentual de ____ (____________ por cento)",
        f"o percentual de {PERCENTUAL}",
    )


async def simular() -> int:
    corpo = _com_percentual(MODELO_BASE)

    desconhecidas = contrato_service.variaveis_desconhecidas(corpo)
    if desconhecidas:
        print(f"❌ O exemplo usa variáveis inexistentes: {', '.join(desconhecidas)}")
        return 1

    if "____________ por cento" in corpo:
        # A troca depende do texto exato do rascunho. Se ele mudar e ninguém
        # ajustar aqui, o "exemplo pronto" sairia com o percentual em branco —
        # e a simulação testaria outra coisa sem avisar.
        print("❌ Não achei a lacuna de honorários no rascunho. Ajuste o script.")
        return 1

    async with AsyncSessionLocal() as db:
        config = (
            await db.execute(select(ConfiguracaoEscritorio))
        ).scalars().first()
        if config is None:
            config = ConfiguracaoEscritorio(id="unica")
            db.add(config)

        preenchidos, mantidos = [], []
        for campo, valor in ESCRITORIO_DE_EXEMPLO.items():
            atual = getattr(config, campo, None)
            if atual and str(atual).strip():
                mantidos.append(campo)
            else:
                setattr(config, campo, valor)
                preenchidos.append(campo)

        existente = (
            await db.execute(
                select(ModeloDeContrato).where(ModeloDeContrato.nome == NOME_DO_EXEMPLO)
            )
        ).scalars().first()

        if existente is None:
            modelo = ModeloDeContrato(nome=NOME_DO_EXEMPLO, corpo=corpo, ativo=True)
            db.add(modelo)
            await db.flush()
        else:
            modelo = existente
            modelo.corpo = corpo
            modelo.ativo = True

        # Só um ativo por vez, a mesma regra do painel.
        outros = (
            await db.execute(
                select(ModeloDeContrato).where(ModeloDeContrato.id != modelo.id)
            )
        ).scalars().all()
        desativados = [o.nome for o in outros if o.ativo]
        for o in outros:
            o.ativo = False

        await db.commit()

    print(f"✓ Escritório preenchido: {', '.join(preenchidos) or 'nada (já estava tudo)'}")
    if mantidos:
        print(f"  Mantidos como estavam: {', '.join(mantidos)}")
    print(f"✓ Modelo '{NOME_DO_EXEMPLO}' ativo, com honorários de {PERCENTUAL}.")
    if desativados:
        print(f"  Desativado: {', '.join(desativados)}")
    print()
    print("  Agora: Kanban → abra um card → seção Contrato → Gerar contrato.")
    print("  O percentual é exemplo. Edite em Contratos → Modelos antes de usar")
    print("  com cliente de verdade.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(simular()))
