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

# Dados **fictícios**, e assumidamente. Servem para o contrato sair completo
# num teste, não para ir a um cliente: o nome do escritório, o CNPJ e a OAB
# saem impressos no documento, e um contrato com CNPJ inventado não é um
# contrato. Antes de usar com gente, preencha os reais em Configurações →
# Escritório — o script não sobrescreve o que já estiver lá.
ESCRITORIO_DE_EXEMPLO = {
    "nome": "Escritório Modelo Advocacia (dados de teste)",
    "cnpj": "00.000.000/0001-00",
    "oab_responsavel": "DF 00.000",
    "fundador": "Advogado Responsável (a preencher)",
    "endereco": "Endereço do escritório, a preencher",
    "cidade": "Brasília",
    "email": "contato@exemplo.com.br",
    "telefone": "(61) 0000-0000",
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
    print("  ⚠️  O percentual e os dados do escritório são de TESTE.")
    print("      Antes de usar com cliente: Configurações → Escritório (dados")
    print("      reais) e Contratos → Modelos (percentual de honorários).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(simular()))
