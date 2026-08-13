"""
Pergunta à Evolution de verdade se ela colabora com a tela de conexão.

Existe por um motivo específico: há um histórico de versões da Evolution
devolvendo `{"count": 0}` em `/instance/connect` — sem QR, sem código de
pareamento e sem erro —, com o QR aparecendo normalmente no Manager (issues
#2380 e #2385, relatadas nas versões 2.0.10 a 2.2.3). Os testes usam transporte
mockado e não têm como flagrar isso: eles provam que **nós** lemos a resposta
certa, não que a Evolution manda uma.

Rode antes de confiar na tela de conexão, e de novo depois de atualizar a
Evolution:

    python -m scripts.sondar_evolution

Não escreve nada e não pareia nada — só lê e conta o que viu.
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.services.whatsapp_service import ESTADOS


def _url(caminho: str) -> str:
    return f"{settings.evolution_api_url}{caminho}/{settings.evolution_instance_name}"


async def sondar() -> int:
    if not settings.evolution_api_key:
        print("EVOLUTION_API_KEY não configurada — não há o que sondar.")
        return 1

    print(f"Evolution: {settings.evolution_api_url}")
    print(f"Instância: {settings.evolution_instance_name}\n")

    cabecalhos = {"apikey": settings.evolution_api_key}
    async with httpx.AsyncClient(timeout=20.0, headers=cabecalhos) as cliente:
        try:
            estado = await cliente.get(_url("/instance/connectionState"))
        except httpx.HTTPError as e:
            print(f"✗ Não deu para falar com a Evolution: {e}")
            print("  A Evolution está no ar? O EVOLUTION_API_URL está certo?")
            return 1

        print(f"connectionState → HTTP {estado.status_code}")
        if estado.status_code >= 400:
            print(f"  corpo: {estado.text[:300]}")
            return 1

        bruto = (estado.json().get("instance") or {}).get("state")
        traduzido = ESTADOS.get(bruto, "desconhecido")
        print(f"  state={bruto!r} → {traduzido}")
        if traduzido == "desconhecido":
            print("  ⚠ palavra nova: acrescente-a em ESTADOS, no whatsapp_service")

        conectado = traduzido == "conectado"
        qr = await cliente.get(_url("/instance/connect"))
        print(f"\nconnect → HTTP {qr.status_code}")
        if qr.status_code >= 400:
            print(f"  corpo: {qr.text[:300]}")
            return 1

        dados = qr.json() or {}
        interno = dados.get("qrcode") or {}
        base64 = dados.get("base64") or interno.get("base64")
        codigo = dados.get("pairingCode") or interno.get("pairingCode")

        print(f"  chaves: {sorted(dados.keys())}")
        print(f"  base64: {'sim, ' + str(len(base64)) + ' caracteres' if base64 else 'não'}")
        print(f"  pairingCode: {codigo or 'não'}")

        if base64 or codigo:
            print("\n✓ A tela de conexão tem o que mostrar.")
            return 0

        if conectado:
            print(
                "\n✓ Sem QR porque o número já está conectado — é a resposta certa.\n"
                "  Para sondar o QR de verdade, desconecte a instância e rode de novo."
            )
            return 0

        print(
            "\n✗ Desconectada e mesmo assim sem QR e sem código.\n"
            "  É o sintoma das issues #2380 e #2385 da Evolution. A tela de\n"
            "  conexão não tem como funcionar nesta versão — vale checar se há\n"
            "  atualização antes de procurar outro caminho."
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(sondar()))
