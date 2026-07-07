from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MentorProfile:
    id: int
    name: str
    role: str
    specialty: str
    avatar: str
    bio: str
    rating: float
    sessions_done: int


MENTOR_CATALOG: list[MentorProfile] = [
    MentorProfile(1, "Ana Ribeiro", "Cloud Architect @ AWS", "Cloud", "AR",
                  "8 anos construindo arquiteturas cloud-native na AWS. Especialista em migração e FinOps.",
                  4.9, 312),
    MentorProfile(2, "Carlos Lima", "Data Engineer @ Nubank", "Data", "CL",
                  "Ex-Itaú, hoje no Nubank. Domina Spark, dbt e pipelines em escala de petabytes.",
                  4.8, 198),
    MentorProfile(3, "Sofia Mendes", "ML Engineer @ Google", "ML/AI", "SM",
                  "PhD em ML pela USP. Trabalha com LLMs e MLOps no Google Brain.",
                  5.0, 87),
    MentorProfile(4, "Pedro Costa", "Senior SRE @ Itaú", "DevOps", "PC",
                  "Garante 99.99% de uptime para sistemas críticos do maior banco privado do Brasil.",
                  4.7, 241),
]

_index: dict[int, MentorProfile] = {m.id: m for m in MENTOR_CATALOG}


def get_all() -> list[dict]:
    return [asdict(m) for m in MENTOR_CATALOG]


def get_by_id(mentor_id: int) -> MentorProfile | None:
    return _index.get(mentor_id)
