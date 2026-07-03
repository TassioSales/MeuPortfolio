from pydantic import BaseModel
from datetime import datetime


class Milestone(BaseModel):
    index: int
    title: str
    description: str
    skills: list[str]
    estimated_hours: int
    resources: list[str] = []


class CareerPathResponse(BaseModel):
    milestones: list[Milestone]
    generated_at: datetime
    progress_pct: float
    current_milestone_index: int


class MilestoneUpdateRequest(BaseModel):
    status: str
    time_spent_minutes: int = 0


class MilestoneProgressResponse(BaseModel):
    milestone_index: int
    status: str
    time_spent_minutes: int
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
