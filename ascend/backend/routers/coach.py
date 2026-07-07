from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db, get_read_db
from core.limiter import limiter
from core.security import get_current_user
from models.user import User
from models.career_path import CareerPath, MilestoneProgress
from models.chat import ChatMessage
from schemas.chat import ChatRequest
from services.ai_service import ai_service

router = APIRouter(prefix="/coach", tags=["coach"])


async def _build_user_context(user: User, db: AsyncSession) -> dict:
    path_result = await db.execute(select(CareerPath).where(CareerPath.user_id == user.id))
    path = path_result.scalar_one_or_none()

    prog_result = await db.execute(
        select(MilestoneProgress).where(MilestoneProgress.user_id == user.id)
    )
    progress_rows = prog_result.scalars().all()

    milestones = path.milestones if path else []
    done = sum(1 for p in progress_rows if p.status == "done")
    pct = (done / len(milestones) * 100) if milestones else 0
    next_ms = milestones[done]["title"] if done < len(milestones) else "Roadmap completo!"

    return {
        "name": user.name,
        "current_role": user.current_role,
        "target_role": user.target_role,
        "progress_pct": pct,
        "next_milestone": next_ms,
        "known_skills": user.known_skills,
    }


@router.post("/chat")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_context = await _build_user_context(current_user, db)
    messages = [m.model_dump() for m in req.messages]

    from core.database import AsyncSessionLocal

    # persist user message synchronously before streaming
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    if last_user:
        db.add(ChatMessage(user_id=current_user.id, role="user", content=last_user["content"]))
        await db.commit()

    user_id = current_user.id
    accumulated: list[str] = []

    async def event_generator():
        async for token in ai_service.stream_chat(messages, user_context):
            accumulated.append(token)
            yield f"data: {token}\n\n"

        # persist assistant response in its own session after stream completes
        full_reply = "".join(accumulated)
        if full_reply:
            async with AsyncSessionLocal() as save_db:
                save_db.add(ChatMessage(user_id=user_id, role="assistant", content=full_reply))
                await save_db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/chat/history")
async def chat_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in messages
    ]
