"""
A assinatura eletrônica do contrato, feita aqui dentro.

**O que ela vale.** É assinatura eletrônica simples/avançada, na classificação
da Lei 14.063/2020 — a mesma categoria do produto padrão dos serviços de
mercado, que também não são ICP-Brasil. Vale entre as partes que a aceitam, e
o que lhe dá peso é a trilha de prova, não o carimbo: quem, quando, de qual
endereço, em qual aparelho, e o hash do texto exato que estava na tela. É isso
que este módulo registra.

**O que segura a porta é o token, e só ele.** São 256 bits de
`secrets.token_urlsafe`, entregues no WhatsApp do próprio cliente e com prazo
de validade. Conferir CPF por cima disso pareceria mais seguro e não seria: o
CPF está impresso no contrato que a página mostra, então quem tem o link já
tem o CPF. Segundo fator que o próprio documento entrega não é segundo fator —
e cobrá-lo só faria alguém que digitou errado desistir de assinar.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from app.config import settings
from app.db.models import Contrato
from app.utils.logger import logger

# Prazo do link. Uma semana cobre "vou ler com calma no fim de semana" e não
# cobre "esse celular já é de outra pessoa".
DIAS_DE_VALIDADE = 7

# 32 bytes → 43 caracteres em base64url. Cabe folgado em String(64) e é
# inadivinhável por qualquer margem que importe.
BYTES_DO_TOKEN = 32

STATUS_GERADO = "gerado"
STATUS_ENVIADO = "enviado"
STATUS_ASSINADO = "assinado"
STATUS_CANCELADO = "cancelado"


# Teto do desenho. Um traço de dedo em PNG dá uns 10 KB; 300 é folga larga
# para um tablet de tela grande e continua sendo um teto — sem ele, a rota
# pública aceitaria qualquer coisa que caiba num POST e guardaria no banco.
LIMITE_DA_ASSINATURA = 300 * 1024

# Assinatura dos oito primeiros bytes de todo PNG.
_ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


def png_da_assinatura(data_url: Optional[str]) -> Optional[bytes]:
    """
    Converte o `data:image/png;base64,...` do `<canvas>` em bytes.

    Devolve `None` para qualquer coisa que não seja um PNG plausível. **Isto é
    entrada pública**, então nada aqui confia no formato: o prefixo é
    conferido, o tamanho é limitado e os bytes decodificados têm de começar
    com a assinatura do PNG. Guardar no banco o que o cliente mandou dizendo
    ser imagem é como se serve um upload malicioso.

    Recusa é silenciosa de propósito — o contrato vale sem o desenho, e
    derrubar uma assinatura legítima porque o `<canvas>` de um navegador
    exótico produziu algo diferente seria trocar o essencial pelo enfeite.
    """
    if not data_url or not isinstance(data_url, str):
        return None

    prefixo = "data:image/png;base64,"
    if not data_url.startswith(prefixo):
        logger.warning("⚠️ Assinatura desenhada em formato inesperado, ignorada")
        return None

    corpo = data_url[len(prefixo):]
    # O base64 cresce 4/3; o teto é aplicado antes de decodificar, para não
    # alocar 40 MB por causa de um POST de 30.
    if len(corpo) > LIMITE_DA_ASSINATURA * 4 // 3:
        logger.warning("⚠️ Assinatura desenhada grande demais, ignorada")
        return None

    try:
        import base64

        bruto = base64.b64decode(corpo, validate=True)
    except Exception:
        logger.warning("⚠️ Assinatura desenhada não é base64 válido, ignorada")
        return None

    if not bruto.startswith(_ASSINATURA_PNG) or len(bruto) > LIMITE_DA_ASSINATURA:
        logger.warning("⚠️ Assinatura desenhada não é um PNG, ignorada")
        return None

    return bruto


def novo_token() -> str:
    return secrets.token_urlsafe(BYTES_DO_TOKEN)


def hash_do_documento(corpo: str) -> str:
    """
    SHA-256 do texto assinado.

    Guardado no momento da assinatura, é o que permite provar depois que o
    documento não mudou — e o que denunciaria se tivesse mudado.
    """
    return hashlib.sha256(corpo.encode("utf-8")).hexdigest()


def link_de(token: str) -> str:
    """
    O endereço que o cliente abre.

    Sai do `FRONTEND_URL`, que é o endereço público do painel — o mesmo que o
    `subir.ps1` reescreve a cada túnel. Link montado com host interno chegaria
    ao celular do cliente apontando para `localhost`.
    """
    return f"{settings.frontend_url.rstrip('/')}/assinar/{token}"


def preparar_para_envio(contrato: Contrato, agora: Optional[datetime] = None) -> str:
    """
    Dá ao contrato um link vivo e devolve o endereço.

    Chamar de novo **renova**: o prazo volta a contar e o token anterior deixa
    de valer. É o que se quer quando o cliente diz "o link venceu" — e é a
    razão de o token não ser gerado junto com o contrato: link que nasce vivo
    é link que vence sem ninguém ter usado.
    """
    quando = agora or datetime.utcnow()
    contrato.token_assinatura = novo_token()
    contrato.token_expira_em = quando + timedelta(days=DIAS_DE_VALIDADE)
    contrato.link_assinatura = link_de(contrato.token_assinatura)
    if contrato.status == STATUS_GERADO:
        contrato.status = STATUS_ENVIADO
    contrato.data_envio = quando
    return contrato.link_assinatura


def expirado(contrato: Contrato, agora: Optional[datetime] = None) -> bool:
    if contrato.token_expira_em is None:
        return True
    return (agora or datetime.utcnow()) > contrato.token_expira_em


def ja_assinado(contrato: Contrato) -> bool:
    return contrato.data_assinatura is not None


def registrar_assinatura(
    contrato: Contrato,
    nome: str,
    ip: Optional[str],
    user_agent: Optional[str],
    agora: Optional[datetime] = None,
) -> None:
    """
    Grava a assinatura e a trilha que a sustenta.

    O `hash_documento` é calculado aqui, do `corpo` como ele está neste
    instante — não de uma cópia guardada antes. É esse valor que amarra a
    assinatura a este texto.
    """
    contrato.assinado_nome = nome.strip()
    contrato.assinado_ip = (ip or "")[:45] or None
    contrato.assinado_user_agent = (user_agent or "")[:500] or None
    contrato.hash_documento = hash_do_documento(contrato.corpo)
    contrato.data_assinatura = agora or datetime.utcnow()
    contrato.status = STATUS_ASSINADO
    # O token morre com a assinatura: o link não pode continuar abrindo um
    # formulário de assinar o que já está assinado.
    contrato.token_expira_em = contrato.data_assinatura

    logger.info(
        f"✍️ Contrato {contrato.id} assinado por '{contrato.assinado_nome}' "
        f"({contrato.assinado_ip}) — hash {contrato.hash_documento[:12]}…"
    )


def ip_do_pedido(request) -> Optional[str]:
    """
    O endereço de quem assinou.

    Atrás do túnel do Cloudflare — que é como isto roda hoje — o IP do socket
    é o do próprio túnel, igual para todo mundo. O `CF-Connecting-IP` é o que
    carrega o endereço real; o `X-Forwarded-For` é a alternativa genérica, e
    dele interessa o **primeiro** item, que é o cliente.

    Cabeçalho é dado do cliente e pode ser forjado. Isto é prova de contexto,
    não credencial: vale como indício num litígio, e nada aqui depende dele
    para autorizar coisa alguma.
    """
    cabecalhos = request.headers
    direto = cabecalhos.get("cf-connecting-ip")
    if direto:
        return direto.strip()

    encadeado = cabecalhos.get("x-forwarded-for")
    if encadeado:
        return encadeado.split(",")[0].strip()

    return request.client.host if request.client else None
