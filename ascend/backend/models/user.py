from datetime import datetime, timezone
from sqlalchemy import String, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100))
    current_role: Mapped[str] = mapped_column(String(100))
    target_role: Mapped[str] = mapped_column(String(100))
    experience_years: Mapped[int] = mapped_column(default=0)
    known_skills: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    career_path: Mapped["CareerPath"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    progress: Mapped[list["MilestoneProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    mentorships: Mapped[list["MentorshipSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
