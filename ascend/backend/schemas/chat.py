from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class SimulationStartRequest(BaseModel):
    scenario: str = "client_requirements"


class SimulationRespondRequest(BaseModel):
    session_id: str
    user_message: str
    scenario: str = "client_requirements"
    history: list[ChatMessage] = []
