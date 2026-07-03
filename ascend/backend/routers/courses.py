from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_read_db
from core.security import get_current_user
from models.user import User
from models.career_path import CareerPath, MilestoneProgress
from services import course_service

from sqlalchemy import select

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
