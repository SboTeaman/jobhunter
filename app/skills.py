"""Słownik technologii/umiejętności IT używany do dopasowywania CV <-> oferta.

Każdy wpis to (kanoniczna_nazwa, [aliasy...]). Dopasowanie jest bez wielkości
liter, z granicami słów, więc "go" nie złapie "google".
"""
from __future__ import annotations

import re

# (kanoniczna nazwa, lista wariantów do wyszukania w tekście)
_SKILLS: list[tuple[str, list[str]]] = [
    # Języki
    ("Python", ["python"]),
    ("JavaScript", ["javascript", "js", "es6", "ecmascript"]),
    ("TypeScript", ["typescript", "ts"]),
    ("Java", ["java"]),
    ("C#", ["c#", "csharp", ".net", "dotnet"]),
    ("C++", ["c++", "cpp"]),
    ("C", ["\\bc\\b"]),
    ("Go", ["golang", "\\bgo\\b"]),
    ("Rust", ["rust"]),
    ("PHP", ["php"]),
    ("Ruby", ["ruby"]),
    ("Kotlin", ["kotlin"]),
    ("Swift", ["swift"]),
    ("Scala", ["scala"]),
    ("R", ["\\br\\b"]),
    ("SQL", ["sql"]),
    ("Bash", ["bash", "shell scripting"]),
    # Frontend
    ("React", ["react", "react.js", "reactjs"]),
    ("Next.js", ["next.js", "nextjs"]),
    ("Vue", ["vue", "vue.js", "vuejs"]),
    ("Angular", ["angular", "angularjs"]),
    ("Svelte", ["svelte"]),
    ("Redux", ["redux"]),
    ("HTML", ["html", "html5"]),
    ("CSS", ["css", "css3"]),
    ("Sass", ["sass", "scss"]),
    ("Tailwind", ["tailwind"]),
    ("Webpack", ["webpack"]),
    ("Vite", ["vite"]),
    # Backend / frameworki
    ("Node.js", ["node.js", "nodejs", "node"]),
    ("Express", ["express", "express.js"]),
    ("NestJS", ["nestjs", "nest.js"]),
    ("Django", ["django"]),
    ("Flask", ["flask"]),
    ("FastAPI", ["fastapi"]),
    ("Spring", ["spring", "spring boot", "springboot"]),
    ("Laravel", ["laravel"]),
    ("Symfony", ["symfony"]),
    ("Rails", ["rails", "ruby on rails"]),
    ("ASP.NET", ["asp.net", "aspnet"]),
    ("GraphQL", ["graphql"]),
    ("REST", ["rest", "restful", "rest api"]),
    ("gRPC", ["grpc"]),
    # Bazy danych
    ("PostgreSQL", ["postgresql", "postgres"]),
    ("MySQL", ["mysql"]),
    ("MongoDB", ["mongodb", "mongo"]),
    ("Redis", ["redis"]),
    ("Elasticsearch", ["elasticsearch", "elastic search"]),
    ("Oracle", ["oracle db", "oracle database"]),
    ("SQLite", ["sqlite"]),
    ("Cassandra", ["cassandra"]),
    ("DynamoDB", ["dynamodb"]),
    ("Kafka", ["kafka"]),
    ("RabbitMQ", ["rabbitmq"]),
    # DevOps / chmura
    ("Docker", ["docker"]),
    ("Kubernetes", ["kubernetes", "k8s"]),
    ("AWS", ["aws", "amazon web services"]),
    ("Azure", ["azure"]),
    ("GCP", ["gcp", "google cloud"]),
    ("Terraform", ["terraform"]),
    ("Ansible", ["ansible"]),
    ("Jenkins", ["jenkins"]),
    ("GitLab CI", ["gitlab ci", "gitlab-ci"]),
    ("GitHub Actions", ["github actions"]),
    ("CI/CD", ["ci/cd", "cicd"]),
    ("Linux", ["linux"]),
    ("Nginx", ["nginx"]),
    ("Prometheus", ["prometheus"]),
    ("Grafana", ["grafana"]),
    # Data / ML
    ("Pandas", ["pandas"]),
    ("NumPy", ["numpy"]),
    ("PyTorch", ["pytorch"]),
    ("TensorFlow", ["tensorflow"]),
    ("scikit-learn", ["scikit-learn", "sklearn"]),
    ("Spark", ["spark", "pyspark"]),
    ("Airflow", ["airflow"]),
    ("Machine Learning", ["machine learning", "uczenie maszynowe"]),
    ("Deep Learning", ["deep learning"]),
    ("LLM", ["llm", "large language model"]),
    # Mobile
    ("Android", ["android"]),
    ("iOS", ["ios"]),
    ("Flutter", ["flutter"]),
    ("React Native", ["react native"]),
    # Narzędzia / metodyki
    ("Git", ["git"]),
    ("Jira", ["jira"]),
    ("Agile", ["agile", "scrum", "kanban"]),
    ("Microservices", ["microservices", "mikroserwisy", "microservice"]),
    ("Selenium", ["selenium"]),
    ("Cypress", ["cypress"]),
    ("Playwright", ["playwright"]),
    ("Jest", ["jest"]),
    ("Pytest", ["pytest"]),
]

# Prekompilowane regexy: kanoniczna nazwa -> wzorzec.
_PATTERNS: list[tuple[str, re.Pattern]] = []
for canonical, variants in _SKILLS:
    parts = []
    for v in variants:
        # Jeśli wariant zawiera już \b (np. "\\bgo\\b") - użyj go wprost.
        if "\\b" in v:
            parts.append(v)
        else:
            # Granica: znaki tworzące dłuższy token (np. C#, C++) - ale NIE kropka,
            # by "Docker." na końcu zdania wciąż się dopasował.
            parts.append(r"(?<![\w#+])" + re.escape(v) + r"(?![\w#+])")
    _PATTERNS.append((canonical, re.compile("|".join(parts), re.IGNORECASE)))


def extract_skills(text: str) -> set[str]:
    """Zwraca zbiór kanonicznych nazw technologii znalezionych w tekście."""
    if not text:
        return set()
    found: set[str] = set()
    for canonical, pattern in _PATTERNS:
        if pattern.search(text):
            found.add(canonical)
    return found


# Słowa kluczowe seniority -> waga liczbowa (0 = junior ... 3 = lead).
SENIORITY_KEYWORDS = {
    "intern": 0, "stażysta": 0, "praktykant": 0, "trainee": 0,
    "junior": 1, "młodszy": 1,
    "mid": 2, "regular": 2, "specjalista": 2,
    "senior": 3, "starszy": 3, "expert": 3, "ekspert": 3,
    "lead": 4, "principal": 4, "architect": 4, "architekt": 4, "staff": 4,
}
