from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Course:
    id: int
    title: str
    platform: str
    url: str
    duration: str
    level: str
    skills: list[str]
    is_free: bool
    rating: float
    description: str
    category: str


COURSE_CATALOG: list[Course] = [
    # ── SQL / Banco de Dados ─────────────────────────────────────────
    Course(1, "SQL for Data Science", "Coursera (UC Davis)", "https://coursera.org/learn/sql-for-data-science",
           "16h", "Iniciante", ["SQL", "PostgreSQL"], True, 4.7,
           "Fundamentos de SQL para análise de dados com projetos práticos.", "Data"),
    Course(2, "Advanced SQL: MySQL for Ecommerce & Web Analytics", "Udemy", "https://udemy.com/course/advanced-sql-mysql-for-analytics-business-intelligence/",
           "10h", "Avançado", ["SQL", "MySQL", "Analytics"], False, 4.6,
           "Window functions, CTEs e otimização de queries para analytics.", "Data"),
    Course(3, "PostgreSQL: Up and Running", "LinkedIn Learning", "https://linkedin.com/learning/postgresql-up-and-running-2",
           "5h", "Intermediário", ["PostgreSQL"], False, 4.5,
           "Instalação, configuração e operações essenciais do PostgreSQL.", "Data"),

    # ── Python ──────────────────────────────────────────────────────
    Course(4, "Python for Everybody", "Coursera (Michigan)", "https://coursera.org/specializations/python",
           "32h", "Iniciante", ["Python"], True, 4.8,
           "Especialização completa: do zero à programação orientada a dados.", "Python"),
    Course(5, "Complete Python Bootcamp", "Udemy", "https://udemy.com/course/complete-python-bootcamp/",
           "22h", "Iniciante", ["Python", "OOP"], False, 4.7,
           "Python moderno com projetos reais — o curso mais popular do Udemy.", "Python"),
    Course(6, "Python Data Science Handbook", "YouTube (Jake VanderPlas)", "https://youtube.com/playlist?list=PLVZqlMpoM6kbMBBKEEHC7Tr3eME34XiKN",
           "12h", "Intermediário", ["Python", "Pandas", "NumPy"], True, 4.9,
           "Série gratuita baseada no livro Python Data Science Handbook.", "Python"),

    # ── Cloud (AWS) ──────────────────────────────────────────────────
    Course(7, "AWS Certified Solutions Architect – Associate", "AWS Skill Builder", "https://explore.skillbuilder.aws/learn/course/external/view/elearning/125/exam-readiness-aws-certified-solutions-architect-associate",
           "40h", "Intermediário", ["AWS", "Architecture", "Cloud"], True, 4.8,
           "Preparação oficial para o exame SAA-C03 da AWS.", "Cloud"),
    Course(8, "Ultimate AWS Certified Developer Associate", "Udemy (Stephane Maarek)", "https://udemy.com/course/aws-certified-developer-associate-dva-c01/",
           "32h", "Intermediário", ["AWS", "Lambda", "DynamoDB"], False, 4.7,
           "O guia mais completo para a certificação AWS Developer.", "Cloud"),
    Course(9, "Google Cloud Fundamentals: Core Infrastructure", "Coursera (Google)", "https://coursera.org/learn/gcp-fundamentals",
           "8h", "Iniciante", ["GCP", "Cloud"], True, 4.6,
           "Conceitos fundamentais de IaaS, PaaS e redes no Google Cloud.", "Cloud"),

    # ── Data Engineering ─────────────────────────────────────────────
    Course(10, "Data Engineering with Python", "DataCamp", "https://datacamp.com/tracks/data-engineer-with-python",
           "90h", "Intermediário", ["Python", "Airflow", "Spark"], False, 4.7,
           "Trilha completa de Data Engineering: pipelines, ETL e cloud.", "Data Engineering"),
    Course(11, "Apache Spark with Python – Big Data", "Udemy", "https://udemy.com/course/apache-spark-with-python-big-data-with-pyspark-and-spark/",
           "12h", "Intermediário", ["Spark", "PySpark", "Python"], False, 4.6,
           "Processamento distribuído em larga escala com PySpark.", "Data Engineering"),
    Course(12, "dbt (data build tool) Fundamentals", "dbt Learn", "https://courses.getdbt.com/courses/fundamentals",
           "5h", "Iniciante", ["dbt", "SQL", "Data Warehouse"], True, 4.9,
           "Curso oficial da dbt Labs — modelagem e transformação de dados.", "Data Engineering"),
    Course(13, "The Complete Hands-On Introduction to Apache Airflow", "Udemy", "https://udemy.com/course/the-complete-hands-on-course-to-master-apache-airflow/",
           "8h", "Iniciante", ["Airflow", "Python", "ETL"], False, 4.6,
           "Criação de DAGs, operadores e monitoramento de pipelines.", "Data Engineering"),

    # ── Machine Learning / AI ────────────────────────────────────────
    Course(14, "Machine Learning Specialization", "Coursera (Andrew Ng)", "https://coursera.org/specializations/machine-learning-introduction",
           "85h", "Iniciante", ["ML Theory", "Python", "Scikit-learn"], True, 4.9,
           "A referência mundial em ML — atualizado com ML moderno.", "ML/AI"),
    Course(15, "Practical Deep Learning for Coders", "fast.ai", "https://course.fast.ai/",
           "30h", "Intermediário", ["Deep Learning", "Python", "PyTorch"], True, 4.9,
           "Abordagem top-down: coloca modelos em produção desde a primeira aula.", "ML/AI"),
    Course(16, "LangChain & Vector Databases in Production", "Activeloop", "https://learn.activeloop.ai/courses/langchain",
           "10h", "Intermediário", ["LLM", "Python", "RAG"], True, 4.7,
           "Construa aplicações LLM com RAG, agentes e vector databases.", "ML/AI"),

    # ── DevOps / SRE ────────────────────────────────────────────────
    Course(17, "Docker and Kubernetes: The Complete Guide", "Udemy (Stephen Grider)", "https://udemy.com/course/docker-and-kubernetes-the-complete-guide/",
           "22h", "Intermediário", ["Docker", "Kubernetes"], False, 4.7,
           "Do zero ao deploy em produção com K8s — o mais completo do mercado.", "DevOps"),
    Course(18, "Terraform Fundamentals", "Google Cloud Skills Boost", "https://cloudskillsboost.google/course_templates/636",
           "8h", "Iniciante", ["Terraform", "IaC", "Cloud"], True, 4.6,
           "Infrastructure as Code com Terraform do zero.", "DevOps"),
    Course(19, "The Linux Command Line", "YouTube (freeCodeCamp)", "https://youtube.com/watch?v=ZtqBQ68cfJc",
           "6h", "Iniciante", ["Linux", "Bash"], True, 4.8,
           "Domínio do terminal Linux em 6 horas.", "DevOps"),

    # ── JavaScript / Frontend ────────────────────────────────────────
    Course(20, "The Complete JavaScript Course", "Udemy (Jonas Schmedtmann)", "https://udemy.com/course/the-complete-javascript-course/",
           "69h", "Iniciante", ["JavaScript", "ES6+"], False, 4.8,
           "O mais completo curso de JavaScript moderno: DOM, async, OOP e mais.", "Frontend"),
    Course(21, "Next.js & React – The Complete Guide", "Udemy (Maximilian Schwarzmüller)", "https://udemy.com/course/nextjs-react-the-complete-guide/",
           "25h", "Intermediário", ["React", "Next.js", "TypeScript"], False, 4.7,
           "App Router, Server Components e deploy com Next.js 14+.", "Frontend"),
    Course(22, "TypeScript: The Complete Developer's Guide", "Udemy (Stephen Grider)", "https://udemy.com/course/typescript-the-complete-developers-guide/",
           "27h", "Intermediário", ["TypeScript"], False, 4.6,
           "TypeScript estrito, generics avançados e integração com React.", "Frontend"),

    # ── Go ───────────────────────────────────────────────────────────
    Course(23, "Go: The Complete Developer's Guide", "Udemy", "https://udemy.com/course/go-the-complete-developers-guide/",
           "9h", "Iniciante", ["Go"], False, 4.6,
           "Fundamentos de Go: goroutines, channels e construção de APIs.", "Backend"),
    Course(24, "Building Microservices with Go", "YouTube (Nic Jackson)", "https://youtube.com/playlist?list=PLmD8u-IFdreyh6EUfevBcbiuCKzFk0EW_",
           "15h", "Avançado", ["Go", "Microservices", "gRPC"], True, 4.8,
           "Série completa de microserviços em Go com gRPC e Docker.", "Backend"),

    # ── System Design ────────────────────────────────────────────────
    Course(25, "System Design Interview – An Insider's Guide", "Educative", "https://educative.io/courses/grokking-the-system-design-interview",
           "20h", "Avançado", ["System Design", "Architecture"], False, 4.8,
           "Os 16 padrões mais cobrados em entrevistas de design de sistemas.", "Architecture"),
    Course(26, "Software Architecture & Design", "Udacity", "https://udacity.com/course/software-architecture-design--ud821",
           "16h", "Intermediário", ["Architecture", "Design Patterns"], True, 4.5,
           "Curso gratuito da Georgia Tech sobre arquitetura de software.", "Architecture"),

    # ── Git / Soft Skills ────────────────────────────────────────────
    Course(27, "Git & GitHub Crash Course", "YouTube (freeCodeCamp)", "https://youtube.com/watch?v=RGOj5yH7evk",
           "1h", "Iniciante", ["Git"], True, 4.9,
           "Git do zero ao trabalho em equipe em 1 hora.", "Tools"),
    Course(28, "Communication Skills for Engineers", "Coursera", "https://coursera.org/learn/presentation-skills",
           "8h", "Iniciante", ["Soft Skills"], True, 4.5,
           "Comunicação técnica eficaz para equipes de engenharia.", "Soft Skills"),

    # ── MLOps ────────────────────────────────────────────────────────
    Course(29, "MLOps Specialization", "Coursera (DeepLearning.AI)", "https://coursera.org/specializations/machine-learning-engineering-for-production-mlops",
           "120h", "Avançado", ["MLOps", "Docker", "Kubernetes", "Python"], False, 4.7,
           "Deploy, monitoramento e automação de modelos ML em produção.", "ML/AI"),
    Course(30, "Full Stack LLM Bootcamp", "The Full Stack", "https://fullstackdeeplearning.com/llm-bootcamp/",
           "10h", "Intermediário", ["LLM", "Python", "RAG", "Deployment"], True, 4.9,
           "Do protótipo ao produto LLM: prompting, RAG, agents e UX.", "ML/AI"),
]

_by_id: dict[int, Course] = {c.id: c for c in COURSE_CATALOG}


def get_all(category: str | None = None) -> list[dict]:
    courses = COURSE_CATALOG
    if category:
        courses = [c for c in courses if c.category.lower() == category.lower()]
    return [asdict(c) for c in courses]


def get_by_id(course_id: int) -> Course | None:
    return _by_id.get(course_id)


def get_for_skills(skills: list[str]) -> list[dict]:
    if not skills:
        return get_all()
    skills_lower = {s.lower() for s in skills}
    matched = [
        c for c in COURSE_CATALOG
        if any(skill.lower() in skills_lower for skill in c.skills)
    ]
    # fallback: return popular courses if nothing matches
    if not matched:
        matched = COURSE_CATALOG[:6]
    return [asdict(c) for c in matched]


def get_categories() -> list[str]:
    return sorted({c.category for c in COURSE_CATALOG})
