"""
Hora de Brasília, para o que gente lê.

O banco guarda UTC — é o certo, e não muda. Mas "assinado em 21/08/2026 às
04:34" num comprovante é hora errada para quem assinou às 01:34 em Brasília, e
comprovante com hora errada é comprovante que a outra parte contesta.

A conversão fica aqui, e não espalhada: o mesmo fuso do follow-up, lido da
mesma configuração.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from app.config import settings


def em_brasilia(quando: Optional[datetime], com_fuso: bool = True) -> Optional[str]:
    """
    `datetime` em UTC vira "21/08/2026 às 01:34 (America/Sao_Paulo)".

    Sem `tzinfo`, assume UTC: é o que o `datetime.utcnow()` do resto do
    sistema produz. Assumir a hora local do servidor daria resultado diferente
    conforme a máquina onde o container roda.
    """
    if quando is None:
        return None

    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)

    local = quando.astimezone(ZoneInfo(settings.followup_fuso))
    texto = local.strftime("%d/%m/%Y às %H:%M")
    return f"{texto} ({settings.followup_fuso})" if com_fuso else texto
