from datetime import datetime, timezone
from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[str]
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class CourseLessonProgress(Base):
    __tablename__ = "course_lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "lesson_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[str]
    lesson_id: Mapped[str]
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
