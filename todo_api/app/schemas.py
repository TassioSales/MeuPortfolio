from pydantic import BaseModel

class TaskBase(BaseModel):
    title: str
    description: str | None = None
    status: str

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

class Task(TaskBase):
    id: int