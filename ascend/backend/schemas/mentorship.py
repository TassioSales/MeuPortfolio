from pydantic import BaseModel


class BookRequest(BaseModel):
    mentor_id: int
    scheduled_at: str
    topic: str
