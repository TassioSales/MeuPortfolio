import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from core.limiter import limiter
from core.security import get_current_user
from models.user import User
from services.ai_service import ai_service
from schemas.chat import SimulationRespondRequest

router = APIRouter(prefix="/simulation", tags=["simulation"])

SCENARIOS = {
    "client_requirements": "Você é um cliente difícil em uma reunião de levantamento de requisitos. Seja exigente mas realista.",
    "technical_interview": "Você é um entrevistador técnico senior avaliando o candidato para uma vaga de {target_role}.",
    "stakeholder_update": "Você é um stakeholder executivo que quer atualizações concisas do projeto.",
    "code_review": "Você é um senior dev fazendo code review do trabalho do usuário. Seja construtivo mas exigente.",
}


def _build_context(user: User) -> dict:
    return {
        "name": user.name,
        "current_role": user.current_role,
        "target_role": user.target_role,
        "progress_pct": 0,
        "next_milestone": "",
        "known_skills": user.known_skills,
    }


@router.post("/start")
@limiter.limit("10/minute")
async def start_simulation(
    request: Request,
    scenario: str = "client_requirements",
    current_user: User = Depends(get_current_user),
):
    session_id = str(uuid.uuid4())
    scenario_prompt = SCENARIOS.get(scenario, SCENARIOS["client_requirements"])
    scenario_prompt = scenario_prompt.replace("{target_role}", current_user.target_role)

    opening_prompt = (
        f"System: {scenario_prompt}\n"
        f"Contexto: O usuário ({current_user.name}) está praticando para se tornar {current_user.target_role}.\n"
        f"Inicie a simulação com uma situação desafiadora em português. Seja breve (2-3 linhas)."
    )

    async def gen():
        async for token in ai_service.stream_chat(
            [{"role": "user", "content": opening_prompt}],
            _build_context(current_user),
        ):
            yield f"data: {token}\n\n"
        yield f"data: [SESSION:{session_id}]\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})


@router.post("/respond")
@limiter.limit("20/minute")
async def respond_simulation(
    request: Request,
    req: SimulationRespondRequest,
    current_user: User = Depends(get_current_user),
):
    scenario_prompt = SCENARIOS.get(req.scenario, SCENARIOS["client_requirements"])
    scenario_prompt = scenario_prompt.replace("{target_role}", current_user.target_role)

    messages = [{"role": "system", "content": scenario_prompt}]
    for h in req.history:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": req.user_message})

    async def gen():
        async for token in ai_service.stream_chat(messages, _build_context(current_user)):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})
