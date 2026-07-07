import json
from loguru import logger
from services.ai_service import ai_service

FALLBACK_ROADMAPS: dict[str, list[dict]] = {
    "cloud architect": [
        {"index": 0, "title": "SQL Fundamentals", "description": "Domine queries, joins e modelagem relacional.", "skills": ["SQL", "PostgreSQL"], "estimated_hours": 20, "resources": ["SQLZoo", "Mode Analytics"]},
        {"index": 1, "title": "Python para Dados", "description": "Python aplicado a análise e automação.", "skills": ["Python", "Pandas"], "estimated_hours": 40, "resources": ["Python.org", "Kaggle"]},
        {"index": 2, "title": "Cloud Architecture Basics", "description": "Conceitos de IaaS, PaaS, SaaS e redes.", "skills": ["AWS", "Networking"], "estimated_hours": 35, "resources": ["AWS Skill Builder"]},
        {"index": 3, "title": "Machine Learning Concepts", "description": "Fundamentos de ML para decisões orientadas a dados.", "skills": ["Scikit-learn", "ML Theory"], "estimated_hours": 30, "resources": ["fast.ai"]},
        {"index": 4, "title": "AWS Solutions Architect", "description": "Certificação AWS SAA-C03.", "skills": ["AWS", "Architecture"], "estimated_hours": 50, "resources": ["AWS Docs"]},
    ],
    "data engineer": [
        {"index": 0, "title": "SQL Avançado", "description": "Window functions, CTEs, otimização.", "skills": ["SQL", "PostgreSQL"], "estimated_hours": 25, "resources": ["StrataScratch"]},
        {"index": 1, "title": "Python & Pandas", "description": "Manipulação de dados em larga escala.", "skills": ["Python", "Pandas", "Polars"], "estimated_hours": 35, "resources": ["Real Python"]},
        {"index": 2, "title": "Spark & Big Data", "description": "Processamento distribuído com PySpark.", "skills": ["Spark"], "estimated_hours": 40, "resources": ["Databricks Academy"]},
        {"index": 3, "title": "Data Pipelines & Airflow", "description": "Orquestração de ETL com Apache Airflow.", "skills": ["Airflow", "dbt"], "estimated_hours": 30, "resources": ["Astronomer"]},
        {"index": 4, "title": "Data Warehouse & dbt", "description": "Modelagem dimensional e analytics engineering.", "skills": ["dbt", "Snowflake"], "estimated_hours": 30, "resources": ["dbt Learn"]},
    ],
}


async def generate_roadmap(
    current_role: str, target_role: str, experience_years: int, known_skills: list[str]
) -> list[dict]:
    target_lower = target_role.lower()
    for key, milestones in FALLBACK_ROADMAPS.items():
        if key in target_lower:
            return milestones

    prompt = f"""Crie um roadmap de carreira personalizado em JSON.

Perfil:
- Cargo atual: {current_role}
- Meta: {target_role}
- Anos de experiência: {experience_years}
- Skills conhecidas: {', '.join(known_skills) or 'nenhuma informada'}

Retorne APENAS um array JSON com exatamente 5 objetos:
[{{"index": 0, "title": "...", "description": "...", "skills": ["..."], "estimated_hours": 30, "resources": ["..."]}}]

Retorne SOMENTE o JSON, sem texto adicional."""

    try:
        raw = await ai_service.generate_text(prompt)
        raw = raw.strip().strip("```json").strip("```").strip()
        milestones = json.loads(raw)
        for i, m in enumerate(milestones):
            m["index"] = i
        return milestones
    except Exception as e:
        logger.error(f"Erro ao gerar roadmap via AI: {e}")
        return FALLBACK_ROADMAPS.get("cloud architect", [])


async def generate_and_save_roadmap(
    user_id: int,
    current_role: str,
    target_role: str,
    experience_years: int,
    known_skills: list[str],
) -> None:
    """Executado como BackgroundTask — não bloqueia a resposta do register."""
    from core.database import AsyncSessionLocal
    from models.career_path import CareerPath, MilestoneProgress

    try:
        milestones = await generate_roadmap(current_role, target_role, experience_years, known_skills)
        async with AsyncSessionLocal() as db:
            db.add(CareerPath(user_id=user_id, milestones=milestones))
            for i in range(len(milestones)):
                db.add(MilestoneProgress(user_id=user_id, milestone_index=i, status="not_started"))
            await db.commit()
        logger.info(f"Roadmap gerado para user_id={user_id}: {len(milestones)} milestones")
    except Exception as e:
        logger.error(f"Falha ao gerar roadmap para user_id={user_id}: {e}")
