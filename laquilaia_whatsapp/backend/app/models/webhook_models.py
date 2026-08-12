"""Pydantic models for Evolution API webhooks."""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class InstanceDataModel(BaseModel):
    """Instance data from Evolution API."""
    instanceName: str
    owner: str
    profilePicUrl: Optional[str] = None
    profileStatus: Optional[str] = None
    profileName: Optional[str] = None
    onWhatsapp: bool = False


class SenderModel(BaseModel):
    """Sender information."""
    id: str
    pushName: Optional[str] = None
    profilePicUrl: Optional[str] = None


class MessageModel(BaseModel):
    """Message data from Evolution webhook."""
    # Opcionais porque eventos que não são de mensagem (connection.update,
    # qrcode.updated...) chegam sem esses campos — exigi-los faria o webhook
    # devolver 422 para tráfego legítimo da Evolution API.
    messageTimestamp: Optional[int] = None
    messageType: Optional[str] = None
    messageBody: Optional[str] = None
    # Onde a Evolution v2 põe o texto de verdade. Verificado contra a v2.3.7
    # com WhatsApp pareado: mensagem simples chega como
    # `message: {"conversation": "oi"}`, e mensagem com citação ou link como
    # `extendedTextMessage: {"text": "..."}`. O `messageBody` acima não existe
    # nesse formato — era por isso que toda mensagem real virava
    # "[non-text message]" e era descartada.
    conversation: Optional[str] = None
    extendedTextMessage: Optional[dict] = None
    mimetype: Optional[str] = None
    fileName: Optional[str] = None
    caption: Optional[str] = None
    media: Optional[str] = None

    @property
    def texto(self) -> Optional[str]:
        """O texto da mensagem, venha de onde vier."""
        if self.conversation:
            return self.conversation
        if self.extendedTextMessage:
            return self.extendedTextMessage.get("text")
        return self.messageBody


# Tipos que o orquestrador sabe tratar. `conversation` é o texto simples da
# Evolution v2; `extendedTextMessage` é o texto com citação ou prévia de link;
# `textMessage` é o nome que este projeto assumia antes de ver um payload real,
# mantido porque os testes e as ferramentas internas o usam.
TIPOS_DE_TEXTO = {"conversation", "extendedTextMessage", "textMessage"}


class DataModel(BaseModel):
    """Data payload from Evolution webhook."""
    # Ver nota em MessageModel: cada tipo de evento traz um `data` diferente.
    key: dict = Field(default_factory=dict, description="Message key (id, remoteJid, fromMe, etc)")
    pushName: Optional[str] = None
    instanceData: Optional[InstanceDataModel] = None
    message: MessageModel = Field(default_factory=MessageModel)
    # Na Evolution v2 o tipo é irmão de `message`, não filho. Declarado só
    # dentro de MessageModel, ficava sempre None e o filtro de tipo do router
    # descartava tudo.
    messageType: Optional[str] = None
    owner: Optional[str] = None
    senderKeyDistributionMessage: Optional[dict] = None

    @property
    def tipo(self) -> Optional[str]:
        """O tipo da mensagem, nos dois níveis em que ele pode aparecer."""
        return self.messageType or self.message.messageType

    @property
    def e_texto(self) -> bool:
        return self.tipo in TIPOS_DE_TEXTO


class WebhookPayload(BaseModel):
    """Complete Evolution API webhook payload."""
    event: str = Field(..., description="Event type (messages.upsert, connection.update, etc)")
    data: DataModel
    server_url: Optional[str] = None
    dateTime: Optional[str] = None


class WhatsAppMessageOut(BaseModel):
    """Message to send via WhatsApp."""
    number: str = Field(..., description="Phone number without +55")
    textMessage: str = Field(..., description="Message text to send")
    quotedMessageId: Optional[str] = None


class WhatsAppResponse(BaseModel):
    """Response from Evolution API when sending message."""
    success: bool
    message: Optional[str] = None
    messageId: Optional[str] = None
    timestamp: Optional[datetime] = None
