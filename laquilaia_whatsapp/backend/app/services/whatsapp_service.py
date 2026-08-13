"""WhatsApp service for Evolution API integration."""

from app.config import settings
from app.utils.logger import logger
from app.utils.exceptions import ValidationException
import httpx
from typing import Optional, Dict, Any


# O vocabulário da Evolution traduzido para o do painel.
#
# "open" não quer dizer nada para quem administra o escritório, e prender a
# tela ao vocabulário da Evolution significa mexer no front no dia em que ela
# mudar de palavra.
ESTADOS = {
    "open": "conectado",
    "connecting": "conectando",
    "close": "desconectado",
}


def _com_prefixo_de_imagem(base64: Optional[str]) -> Optional[str]:
    """
    Garante o `data:image/png;base64,` que a tag `<img>` exige.

    A Evolution já devolveu das duas formas — com e sem o prefixo — e sem ele
    a imagem simplesmente não aparece, sem erro nenhum no console.
    """
    if not base64:
        return None
    return base64 if base64.startswith("data:") else f"data:image/png;base64,{base64}"


class WhatsAppService:
    """Service for sending messages via Evolution API."""

    def __init__(self):
        """Initialize WhatsApp service."""
        self.api_url = settings.evolution_api_url
        self.api_key = settings.evolution_api_key
        self.instance_name = settings.evolution_instance_name
        self.timeout = 30

    async def send_message(
        self,
        phone_number: str,
        message_text: str,
        quoted_message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send message via WhatsApp using Evolution API.

        Args:
            phone_number: Phone number (with or without +55)
            message_text: Message content
            quoted_message_id: Optional message ID to quote

        Returns:
            Dict with success status and message ID

        Raises:
            ValidationException: If API call fails
        """
        try:
            # O número vai como a Evolution o entrega, com DDI.
            #
            # Havia um `if clean_phone.startswith("55"): clean_phone[2:]` aqui,
            # que arrancava o código do país. Mas o `remoteJid` do webhook chega
            # como `556196298484@s.whatsapp.net` — com DDI —, e é esse o
            # identificador do contato no WhatsApp: responder para
            # `6196298484` é responder para outra pessoa, ou para ninguém.
            # De quebra, a regra mutilava números de DDD 55 (Santa Maria/RS)
            # enviados sem DDI.
            clean_phone = phone_number.replace("+", "").replace(" ", "")

            # `text`, e não `textMessage`.
            #
            # A Evolution v2 respondeu, palavra por palavra:
            # `instance requires property "text"`. O nome antigo é da v1, e
            # com ele toda resposta morria em 400 — depois de já ter gasto a
            # chamada ao LLM e gravado a conversa.
            payload = {
                "number": clean_phone,
                "text": message_text,
            }

            if quoted_message_id:
                payload["quotedMessageId"] = quoted_message_id

            # Build URL
            url = (
                f"{self.api_url}/message/sendText/{self.instance_name}"
            )

            # Headers
            headers = {
                "apikey": self.api_key,
                "Content-Type": "application/json",
            }

            # Send request
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)

            # Check response
            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(
                    f"✅ WhatsApp message sent to {clean_phone} "
                    f"(message_id: {data.get('messageId', 'N/A')})"
                )
                return {
                    "success": True,
                    "message_id": data.get("messageId"),
                    "phone": clean_phone,
                }
            else:
                logger.error(
                    f"❌ Failed to send WhatsApp message: {response.status_code} "
                    f"- {response.text}"
                )
                raise ValidationException(
                    f"Failed to send message: {response.status_code}"
                )

        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp message: {e}")
            raise ValidationException(f"Error sending message: {str(e)}")

    async def estado_da_conexao(self) -> Dict[str, Any]:
        """
        Se o número está conectado, conectando ou fora.

        A Evolution devolve `open`, `connecting` ou `close` em
        `instance.state`. Traduzimos aqui porque "open" não quer dizer nada
        para quem administra o escritório, e porque o dia em que a Evolution
        mudar o vocabulário o painel não deve mudar junto.

        Nunca levanta: a tela de conexão precisa dizer *alguma coisa* quando a
        Evolution está fora do ar, e "não deu para falar com a Evolution" é
        informação melhor que uma tela de erro genérica.
        """
        url = f"{self.api_url}/instance/connectionState/{self.instance_name}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resposta = await client.get(url, headers={"apikey": self.api_key})
        except httpx.HTTPError as e:
            logger.error(f"❌ Não foi possível falar com a Evolution: {e}")
            return {"estado": "indisponivel", "detalhe": str(e)}

        if resposta.status_code == 404:
            # 404 não é "a Evolution caiu" — ela respondeu. É a instância que
            # não existe lá dentro, o que acontece toda vez que o container é
            # recriado sem volume: o serviço sobe limpo e a instância pareada
            # se perde junto. Tratar como indisponível manda procurar o
            # problema no serviço, quando o que falta é criar a instância.
            logger.warning(
                f"⚠️ A instância '{self.instance_name}' não existe na Evolution"
            )
            return {"estado": "inexistente", "detalhe": None}

        if resposta.status_code >= 400:
            logger.error(
                f"❌ connectionState devolveu {resposta.status_code}: "
                f"{resposta.text[:200]}"
            )
            return {
                "estado": "indisponivel",
                "detalhe": f"HTTP {resposta.status_code}",
            }

        bruto = (resposta.json().get("instance") or {}).get("state")
        return {
            "estado": ESTADOS.get(bruto, "desconhecido"),
            "detalhe": None if bruto in ESTADOS else f"state={bruto!r}",
        }

    async def qrcode(self) -> Dict[str, Any]:
        """
        O QR para parear o número, e o código de pareamento quando houver.

        `GET /instance/connect/{instancia}` devolve o QR **só quando a
        instância está desconectada**: com o número já conectado ela responde
        sem `base64` nenhum, e isso não é erro — é a resposta certa para "já
        está pareado".

        Há um histórico de versões da Evolution devolvendo `{"count": 0}` sem
        QR e sem código (issues #2380 e #2385, nas 2.0.10 a 2.2.3). Por isso o
        retorno distingue "não veio QR" de "falhou": a tela precisa saber a
        diferença entre reconectar e avisar que o endpoint não colabora nesta
        versão.
        """
        url = f"{self.api_url}/instance/connect/{self.instance_name}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resposta = await client.get(url, headers={"apikey": self.api_key})
        except httpx.HTTPError as e:
            logger.error(f"❌ Não foi possível pedir o QR à Evolution: {e}")
            return {"qrcode": None, "codigo": None, "detalhe": str(e)}

        if resposta.status_code >= 400:
            return {
                "qrcode": None,
                "codigo": None,
                "detalhe": f"HTTP {resposta.status_code}",
            }

        dados = resposta.json() or {}
        # A Evolution já variou entre `base64` na raiz e dentro de `qrcode`.
        # Aceitar os dois é uma linha; descobrir em produção que mudou custa
        # uma noite.
        interno = dados.get("qrcode") or {}
        base64 = dados.get("base64") or interno.get("base64")
        codigo = dados.get("pairingCode") or interno.get("pairingCode")

        return {
            "qrcode": _com_prefixo_de_imagem(base64),
            "codigo": codigo,
            "detalhe": None if (base64 or codigo) else "a Evolution respondeu sem QR",
        }

    async def desconectar(self) -> Dict[str, Any]:
        """
        Despareia o número, mantendo a instância.

        É o `logout` da Evolution, e **não** o `delete`: a instância continua
        existindo, com o webhook e as configurações. O que sai é a sessão do
        celular — para religar, basta ler o QR de novo. O `delete` apagaria a
        instância inteira, e aí seria preciso recriá-la e reconfigurar o
        webhook antes de qualquer pareamento.

        Nunca levanta, pela mesma razão dos outros métodos: a tela precisa
        dizer o que aconteceu, e "não deu para falar com a Evolution" é
        informação melhor que uma tela de erro genérica.
        """
        url = f"{self.api_url}/instance/logout/{self.instance_name}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resposta = await client.delete(url, headers={"apikey": self.api_key})
        except httpx.HTTPError as e:
            logger.error(f"❌ Não foi possível desconectar o número: {e}")
            return {"desconectado": False, "detalhe": str(e)}

        if resposta.status_code == 404:
            # Instância inexistente: não há sessão para encerrar, e o estado
            # final é o que o pedido queria. Tratar como falha faria a tela
            # pedir para tentar de novo, para sempre.
            logger.warning(
                f"⚠️ A instância '{self.instance_name}' não existe na Evolution"
            )
            return {"desconectado": True, "detalhe": "a instância não existia"}

        if resposta.status_code >= 400:
            logger.error(
                f"❌ A Evolution recusou o logout: {resposta.status_code} — "
                f"{resposta.text[:200]}"
            )
            return {
                "desconectado": False,
                "detalhe": f"HTTP {resposta.status_code}",
            }

        logger.info(f"🔌 Número desconectado da instância '{self.instance_name}'")
        return {"desconectado": True, "detalhe": None}

    async def baixar_midia(self, key: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        O conteúdo de um anexo, em base64.

        O webhook avisa que chegou uma imagem, mas não a manda: o arquivo fica
        criptografado no servidor do WhatsApp, e quem tem a chave para abri-lo
        é a Evolution — daí a segunda chamada.

        `None` quando não deu, e nunca levanta: um anexo que não baixou é uma
        mensagem sem anexo, e o atendimento continua. Levantar aqui derrubaria
        a resposta ao cliente por causa de uma foto.

        Devolve `{"base64", "mimetype", "nome", "tamanho"}`.
        """
        url = f"{self.api_url}/chat/getBase64FromMediaMessage/{self.instance_name}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Timeout maior que o dos outros: aqui o que trafega é o
                # arquivo, e um PDF de contrato não chega em três segundos.
                resposta = await client.post(
                    url,
                    json={"message": {"key": key}, "convertToMp4": False},
                    headers={"apikey": self.api_key, "Content-Type": "application/json"},
                )
        except httpx.HTTPError as e:
            logger.error(f"❌ Falha de rede ao baixar o anexo: {e}")
            return None

        if resposta.status_code >= 400:
            logger.error(
                f"❌ A Evolution recusou o download do anexo: "
                f"{resposta.status_code} — {resposta.text[:200]}"
            )
            return None

        dados = resposta.json() or {}
        base64 = dados.get("base64")
        if not base64:
            logger.warning("⚠️ A Evolution respondeu sem base64 no anexo")
            return None

        return {
            "base64": base64,
            "mimetype": dados.get("mimetype") or "application/octet-stream",
            "nome": dados.get("fileName"),
            "tamanho": dados.get("size"),
        }

    async def health_check(self) -> bool:
        """
        Check Evolution API health.

        Returns:
            True if API is accessible, False otherwise
        """
        try:
            url = f"{self.api_url}/instance/info/{self.instance_name}"
            headers = {"apikey": self.api_key}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            is_healthy = response.status_code in [200, 401]  # 401 also means API is up
            logger.info(f"🔍 Evolution API health: {'✅ OK' if is_healthy else '❌ Down'}")
            return is_healthy

        except Exception as e:
            logger.error(f"❌ Evolution API health check failed: {e}")
            return False


whatsapp_service = WhatsAppService()
