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
    messageType: Optional[str] = None  # "textMessage", "imageMessage", ...
    messageBody: Optional[str] = None
    mimetype: Optional[str] = None
    fileName: Optional[str] = None
    caption: Optional[str] = None
    media: Optional[str] = None


class DataModel(BaseModel):
    """Data payload from Evolution webhook."""
    # Ver nota em MessageModel: cada tipo de evento traz um `data` diferente.
    key: dict = Field(default_factory=dict, description="Message key (id, remoteJid, fromMe, etc)")
    pushName: Optional[str] = None
    instanceData: Optional[InstanceDataModel] = None
    message: MessageModel = Field(default_factory=MessageModel)
    owner: Optional[str] = None
    senderKeyDistributionMessage: Optional[dict] = None


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
