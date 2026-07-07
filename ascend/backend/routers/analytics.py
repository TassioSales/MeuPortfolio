from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_read_db
from core.security import get_current_user
from models.user import User
from models.career_path import CareerPath, MilestoneProgress

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    path_result = await db.execute(select(CareerPath).where(CareerPath.user_id == current_user.id))
    path = path_result.scalar_one_or_none()

    prog_result = await db.execute(
        select(MilestoneProgress).where(MilestoneProgress.user_id == current_user.id)
    )
    rows = prog_result.scalars().all()

    milestones = path.milestones if path else []
    total = len(milestones)
    done_rows = [r for r in rows if r.status == "done"]
    done = len(done_rows)
    in_progress = sum(1 for r in rows if r.status == "in_progress")
    total_minutes = sum(r.time_spent_minutes for r in rows)

    avg_hours_per_ms = (total_minutes / 60 / done) if done else 0
    remaining = total - done
    estimated_hours_left = sum(
        milestones[i].get("estimated_hours", 30)
        for i in range(done, total)
        if i < len(milestones)
    )

    completion_date = None
    if avg_hours_per_ms > 0 and remaining > 0:
        weeks_left = estimated_hours_left / (avg_hours_per_ms * 2)
        days_left = int(weeks_left * 7)
        completion_date = (datetime.now(timezone.utc) + timedelta(days=days_left)).isoformat()

    return {
        "total_milestones": total,
        "completed": done,
        "in_progress": in_progress,
        "not_started": total - done - in_progress,
        "progress_pct": (done / total * 100) if total else 0,
        "total_hours_studied": round(total_minutes / 60, 1),
        "avg_hours_per_milestone": round(avg_hours_per_ms, 1),
        "estimated_hours_remaining": estimated_hours_left,
        "estimated_completion_date": completion_date,
        "current_role": current_user.current_role,
        "target_role": current_user.target_role,
    }
