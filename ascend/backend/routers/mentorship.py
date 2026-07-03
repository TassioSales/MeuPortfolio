from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db, get_read_db
from core.security import get_current_user
from models.user import User
from models.career_path import MentorshipSession
from services.mentor_service import get_all, get_by_id

router = APIRouter(prefix="/mentorship", tags=["mentorship"])


@router.get("/mentors")
async def list_mentors():
    return get_all()


@router.get("/slots")
async def list_slots():
    now = datetime.now(timezone.utc)
    slots = []
    for days_ahead in range(1, 8):
        for hour in [9, 14, 16]:
            slot_dt = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
            slots.append({"datetime": slot_dt.isoformat(), "available": True})
    return slots[:10]


@router.post("/book")
async def book_session(
    mentor_id: int,
    scheduled_at: str,
    topic: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mentor = get_by_id(mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor não encontrado")

    session = MentorshipSession(
        user_id=current_user.id,
        mentor_name=mentor.name,
        mentor_role=mentor.role,
        scheduled_at=datetime.fromisoformat(scheduled_at),
        topic=topic,
        status="scheduled",
    )
    db.add(session)
    await db.commit()
    return {"message": f"Sessão com {mentor.name} agendada com sucesso!"}


@router.get("/my-sessions")
async def my_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    result = await db.execute(
        select(MentorshipSession)
        .where(MentorshipSession.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "mentor_name": s.mentor_name,
            "mentor_role": s.mentor_role,
            "scheduled_at": s.scheduled_at.isoformat(),
            "topic": s.topic,
            "status": s.status,
        }
        for s in sessions
    ]
