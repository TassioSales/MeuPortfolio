"""
Cria usuario de demonstracao no banco.
Uso: python seed.py
"""
import asyncio
from sqlalchemy import select
from core.database import AsyncSessionLocal, create_tables
from core.security import hash_password
from models.user import User
from models.career_path import CareerPath, MilestoneProgress
from services.roadmap_service import generate_roadmap

DEMO_USER = {
    "email": "demo@trilha.app",
    "password": "demo123",
    "name": "Ashley Demo",
    "current_role": "Data Analyst",
    "target_role": "Cloud Architect",
    "experience_years": 2,
    "known_skills": ["Python", "SQL", "Git"],
}


async def seed():
    await create_tables()

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == DEMO_USER["email"]))
        if existing.scalar_one_or_none():
            print(f"Usuario demo ja existe: {DEMO_USER['email']}")
            return

        user = User(
            email=DEMO_USER["email"],
            hashed_password=hash_password(DEMO_USER["password"]),
            name=DEMO_USER["name"],
            current_role=DEMO_USER["current_role"],
            target_role=DEMO_USER["target_role"],
            experience_years=DEMO_USER["experience_years"],
            known_skills=DEMO_USER["known_skills"],
        )
        db.add(user)
        await db.flush()

        print("Gerando roadmap via IA (pode demorar alguns segundos)...")
        milestones = await generate_roadmap(
            DEMO_USER["current_role"],
            DEMO_USER["target_role"],
            DEMO_USER["experience_years"],
            DEMO_USER["known_skills"],
        )

        db.add(CareerPath(user_id=user.id, milestones=milestones))

        for i, ms in enumerate(milestones):
            status = "done" if i == 0 else "in_progress" if i == 1 else "not_started"
            db.add(MilestoneProgress(user_id=user.id, milestone_index=i, status=status))

        await db.commit()
        print(f"Usuario demo criado com sucesso!")
        print(f"  Email:  {DEMO_USER['email']}")
        print(f"  Senha:  {DEMO_USER['password']}")
        print(f"  Roadmap: {len(milestones)} milestones gerados")


if __name__ == "__main__":
    asyncio.run(seed())
