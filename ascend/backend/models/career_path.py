from datetime import datetime, timezone
from sqlalchemy import ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class CareerPath(Base):
    __tablename__ = "career_paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    milestones: Mapped[list] = mapped_column(JSON, default=list)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    user: Mapped["User"] = relationship(back_populates="career_path")


class MilestoneProgress(Base):
    __tablename__ = "milestone_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    milestone_index: Mapped[int]
    status: Mapped[str] = mapped_column(default="not_started")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_minutes: Mapped[int] = mapped_column(default=0)
    user: Mapped["User"] = relationship(back_populates="progress")


class MentorshipSession(Base):
    __tablename__ = "mentorship_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mentor_name: Mapped[str]
    mentor_role: Mapped[str]
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    topic: Mapped[str]
    status: Mapped[str] = mapped_column(default="scheduled")
    user: Mapped["User"] = relationship(back_populates="mentorships")
