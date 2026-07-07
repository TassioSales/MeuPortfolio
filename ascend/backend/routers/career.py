from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.career_path import CareerPath, MilestoneProgress
from schemas.career import CareerPathResponse, Milestone, MilestoneUpdateRequest, MilestoneProgressResponse
from services.roadmap_service import generate_roadmap

router = APIRouter(prefix="/career", tags=["career"])


async def _get_progress_pct(user_id: int, total: int, db: AsyncSession) -> tuple[float, int]:
    result = await db.execute(
        select(MilestoneProgress).where(MilestoneProgress.user_id == user_id)
    )
    rows = result.scalars().all()
    done = sum(1 for r in rows if r.status == "done")
    current = next((r.milestone_index for r in rows if r.status == "in_progress"), done)
    pct = (done / total * 100) if total else 0
    return pct, current


@router.get("/roadmap", response_model=CareerPathResponse)
async def get_roadmap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CareerPath).where(CareerPath.user_id == current_user.id))
    path = result.scalar_one_or_none()
    if not path:
        raise HTTPException(status_code=404, detail="Roadmap não encontrado")

    milestones = [Milestone(**m) for m in path.milestones]
    pct, current = await _get_progress_pct(current_user.id, len(milestones), db)
    return CareerPathResponse(
        milestones=milestones,
        generated_at=path.generated_at,
        progress_pct=pct,
        current_milestone_index=current,
    )


@router.post("/roadmap/generate")
async def regenerate_roadmap(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    milestones = await generate_roadmap(
        current_user.current_role,
        current_user.target_role,
        current_user.experience_years,
        current_user.known_skills,
    )
    result = await db.execute(select(CareerPath).where(CareerPath.user_id == current_user.id))
    path = result.scalar_one_or_none()
    if path:
        path.milestones = milestones
        path.generated_at = datetime.now(timezone.utc)
    else:
        db.add(CareerPath(user_id=current_user.id, milestones=milestones))
    await db.commit()
    return {"message": "Roadmap regenerado com sucesso", "milestones_count": len(milestones)}


@router.patch("/milestones/{index}")
async def update_milestone(
    index: int,
    data: MilestoneUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MilestoneProgress).where(
            MilestoneProgress.user_id == current_user.id,
            MilestoneProgress.milestone_index == index,
        )
    )
    prog = result.scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Milestone não encontrado")

    now = datetime.now(timezone.utc)
    if data.status == "in_progress" and not prog.started_at:
        prog.started_at = now
    if data.status == "done" and not prog.completed_at:
        prog.completed_at = now
    prog.status = data.status
    prog.time_spent_minutes += data.time_spent_minutes
    await db.commit()
    return {"message": "Progresso atualizado"}


@router.get("/progress", response_model=list[MilestoneProgressResponse])
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MilestoneProgress).where(MilestoneProgress.user_id == current_user.id)
    )
    return result.scalars().all()
