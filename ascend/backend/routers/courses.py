from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.database import get_db, get_read_db
from core.security import get_current_user
from models.user import User
from models.career_path import CareerPath, MilestoneProgress
from models.course_progress import CourseEnrollment, CourseLessonProgress
from services import course_service
from services.courses_data import COURSES, _INDEX

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
async def list_courses(
    category: str | None = Query(None, description="Filtrar por categoria"),
    current_user: User = Depends(get_current_user),
):
    return {"courses": course_service.get_all(category=category)}


@router.get("/categories")
async def list_categories(current_user: User = Depends(get_current_user)):
    return {"categories": course_service.get_categories()}


@router.get("/recommended")
async def recommended_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    result = await db.execute(
        select(CareerPath).where(CareerPath.user_id == current_user.id)
    )
    career_path = result.scalars().first()

    if not career_path or not career_path.milestones:
        courses = course_service.get_all()[:8]
        return {"courses": courses, "source": "catalog"}

    # Find the current (not-started or in-progress) milestone
    prog_result = await db.execute(
        select(MilestoneProgress)
        .where(MilestoneProgress.user_id == current_user.id)
        .where(MilestoneProgress.status != "completed")
        .order_by(MilestoneProgress.milestone_index)
    )
    pending = prog_result.scalars().first()

    if pending is None:
        # All done — recommend advanced courses for next career step
        all_skills = []
        for m in career_path.milestones:
            all_skills.extend(m.get("skills", []))
        courses = course_service.get_for_skills(all_skills)
        return {"courses": courses[:8], "source": "completed"}

    milestone = career_path.milestones[pending.milestone_index]
    skills = milestone.get("skills", [])
    courses = course_service.get_for_skills(skills)

    return {
        "courses": courses[:8],
        "source": "milestone",
        "milestone_title": milestone.get("title", ""),
        "milestone_index": pending.milestone_index,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Trilha (cursos built-in)
# ─────────────────────────────────────────────────────────────────────────────

def _course_summary(course, enrolled_ids: set[str], progress_map: dict[str, int]) -> dict:
    total_lessons = sum(len(m.lessons) for m in course.modules)
    completed = progress_map.get(course.id, 0)
    return {
        "id": course.id,
        "title": course.title,
        "tagline": course.tagline,
        "description": course.description,
        "level": course.level,
        "category": course.category,
        "duration_hours": course.duration_hours,
        "skills": course.skills,
        "color": course.color,
        "module_count": len(course.modules),
        "lesson_count": total_lessons,
        "enrolled": course.id in enrolled_ids,
        "completed_lessons": completed,
        "progress_pct": round(completed * 100 / total_lessons) if total_lessons else 0,
    }


@router.get("/trilha")
async def list_builtin_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    enroll_result = await db.execute(
        select(CourseEnrollment.course_id).where(CourseEnrollment.user_id == current_user.id)
    )
    enrolled_ids = {row[0] for row in enroll_result.all()}

    prog_result = await db.execute(
        select(CourseLessonProgress.course_id)
        .where(CourseLessonProgress.user_id == current_user.id)
    )
    progress_map: dict[str, int] = {}
    for row in prog_result.all():
        progress_map[row[0]] = progress_map.get(row[0], 0) + 1

    return {
        "courses": [_course_summary(c, enrolled_ids, progress_map) for c in COURSES]
    }


@router.get("/trilha/{course_id}")
async def get_builtin_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    course = _INDEX.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    enroll_result = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == current_user.id,
            CourseEnrollment.course_id == course_id,
        )
    )
    enrolled = enroll_result.scalars().first() is not None

    prog_result = await db.execute(
        select(CourseLessonProgress.lesson_id).where(
            CourseLessonProgress.user_id == current_user.id,
            CourseLessonProgress.course_id == course_id,
        )
    )
    completed_lessons = {row[0] for row in prog_result.all()}

    course_dict = asdict(course)
    course_dict["enrolled"] = enrolled
    course_dict["completed_lessons"] = list(completed_lessons)
    return course_dict


@router.post("/trilha/{course_id}/enroll", status_code=201)
async def enroll_course(
    course_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if course_id not in _INDEX:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    existing = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.user_id == current_user.id,
            CourseEnrollment.course_id == course_id,
        )
    )
    if existing.scalars().first():
        return {"enrolled": True, "already_enrolled": True}

    db.add(CourseEnrollment(user_id=current_user.id, course_id=course_id))
    await db.commit()
    return {"enrolled": True, "already_enrolled": False}


@router.patch("/trilha/{course_id}/lessons/{lesson_id}/complete")
async def complete_lesson(
    course_id: str,
    lesson_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    course = _INDEX.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso não encontrado")

    all_lesson_ids = {l.id for m in course.modules for l in m.lessons}
    if lesson_id not in all_lesson_ids:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    existing = await db.execute(
        select(CourseLessonProgress).where(
            CourseLessonProgress.user_id == current_user.id,
            CourseLessonProgress.course_id == course_id,
            CourseLessonProgress.lesson_id == lesson_id,
        )
    )
    if not existing.scalars().first():
        db.add(CourseLessonProgress(
            user_id=current_user.id,
            course_id=course_id,
            lesson_id=lesson_id,
        ))
        await db.commit()

    # Return updated progress
    prog_result = await db.execute(
        select(CourseLessonProgress.lesson_id).where(
            CourseLessonProgress.user_id == current_user.id,
            CourseLessonProgress.course_id == course_id,
        )
    )
    completed = {row[0] for row in prog_result.all()}
    total = len(all_lesson_ids)
    return {
        "lesson_id": lesson_id,
        "completed_lessons": list(completed),
        "progress_pct": round(len(completed) * 100 / total) if total else 0,
    }
