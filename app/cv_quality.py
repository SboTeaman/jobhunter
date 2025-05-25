"""Analiza jakości CV — feedback podobny do Jobscan/Teal (30+ checków).

Zwraca wynik 0-100 oraz listę konkretnych uwag z priorytetem.
"""
from __future__ import annotations

import re

# Słabe czasowniki (pasywne, ogólne) — lepiej zastąpić mocniejszymi.
_WEAK_VERBS = {
    "worked", "helped", "assisted", "did", "made", "handled", "used",
    "pracowałem", "pracowałam", "pomagałem", "pomagałam", "robiłem", "robiłam",
    "zajmowałem", "zajmowałam", "brałem", "brałam", "uczestniczyłem",
}

_STRONG_VERBS = [
    "built", "developed", "designed", "led", "created", "implemented",
    "optimized", "reduced", "increased", "delivered", "architected",
    "automated", "migrated", "scaled", "zbudował", "zaprojektował",
    "wdrożył", "zoptymalizował", "zwiększył", "zredukował", "kierował",
    "stworzył", "zautomatyzował", "dostarczył", "wprowadził",
]

# Sekcje których szukamy w CV.
_SECTIONS = {
    "experience": [
        "experience", "work history", "employment", "doświadczenie",
        "historia zatrudnienia", "praca zawodowa",
    ],
    "education": [
        "education", "studies", "degree", "wykształcenie", "studia",
        "uczelnia", "university", "akademia",
    ],
    "skills": [
        "skills", "technologies", "tech stack", "umiejętności",
        "technologie", "kompetencje",
    ],
    "contact": [
        "@", "github.com", "linkedin.com", "tel:", "+48", "phone", "email",
    ],
}

# Metryki liczbowe (%, liczby + jednostki).
_METRIC_RE = re.compile(
    r"\d+\s*(%|x|X|k\b|mln|tys|ms\b|s\b|h\b|users?|klientów|requests?|deployments?|releases?)"
)


def analyze(cv_text: str) -> dict:
    """Zwraca:
      - score: 0-100
      - checks: lista {id, label, passed, priority, tip}
    """
    text = cv_text or ""
    lower = text.lower()
    checks: list[dict] = []

    def add(id_: str, label: str, passed: bool, priority: str, tip: str) -> None:
        checks.append({"id": id_, "label": label, "passed": passed,
                       "priority": priority, "tip": tip})

    # --- Sekcje ---
    add("has_experience", "Sekcja doświadczenia",
        any(w in lower for w in _SECTIONS["experience"]),
        "high", "Dodaj sekcję 'Doświadczenie zawodowe' / 'Work Experience'.")

    add("has_education", "Sekcja wykształcenia",
        any(w in lower for w in _SECTIONS["education"]),
        "medium", "Dodaj sekcję 'Wykształcenie' / 'Education'.")

    add("has_skills", "Sekcja umiejętności",
        any(w in lower for w in _SECTIONS["skills"]),
        "high", "Dodaj sekcję 'Umiejętności' / 'Skills' z listą technologii.")

    add("has_contact", "Dane kontaktowe (e-mail lub telefon)",
        any(w in lower for w in _SECTIONS["contact"]),
        "high", "Upewnij się, że CV zawiera e-mail i/lub telefon.")

    add("has_github", "Link do GitHub / portfolio",
        "github" in lower or "portfolio" in lower or "gitlab" in lower,
        "medium", "Dodaj link do GitHub lub portfolio — ważne dla ról tech.")

    add("has_linkedin", "Link do LinkedIn",
        "linkedin" in lower,
        "low", "LinkedIn zwiększa wiarygodność — dodaj link do profilu.")

    # --- Długość ---
    word_count = len(text.split())
    add("length_ok", f"Odpowiednia długość ({word_count} słów)",
        300 <= word_count <= 1200,
        "medium",
        "CV za krótkie — rozwiń opisy stanowisk." if word_count < 300
        else "CV za długie (>1200 słów) — skróć do 1-2 stron." if word_count > 1200
        else "")

    # --- Metryki i liczby ---
    metrics = _METRIC_RE.findall(text)
    add("has_metrics", f"Mierzalne wyniki ({len(metrics)} znalezionych)",
        len(metrics) >= 2,
        "high",
        "Dodaj liczby: 'zredukowałem czas ładowania o 40%', "
        "'obsługiwałem 10k requestów/s'. ATS i rekruterzy to doceniają.")

    # --- Czasowniki akcji ---
    strong_count = sum(1 for v in _STRONG_VERBS if v in lower)
    weak_found = [v for v in _WEAK_VERBS if re.search(r"\b" + v + r"\b", lower)]
    add("strong_verbs", f"Mocne czasowniki akcji ({strong_count} znalezionych)",
        strong_count >= 3,
        "medium",
        "Użyj mocnych czasowników: 'zbudował', 'wdrożył', 'zoptymalizował' "
        "zamiast 'pracował', 'pomagał', 'zajmował się'.")

    if weak_found:
        add("no_weak_verbs", f"Słabe czasowniki ({', '.join(weak_found[:3])})",
            False, "medium",
            f"Zastąp słabe czasowniki: {', '.join(weak_found[:3])} → "
            "developed, implemented, optimized.")
    else:
        add("no_weak_verbs", "Brak słabych czasowników", True, "medium", "")

    # --- Formatowanie i czytelność ---
    has_bullet = "•" in text or "·" in text or text.count("-  ") > 2 or text.count("* ") > 2
    add("has_bullets", "Listy / punkty (czytelna struktura)",
        has_bullet,
        "low", "Używaj punktorów do opisów obowiązków — ułatwia skanowanie.")

    add("no_photo_mention", "Brak wzmianki o zdjęciu",
        "photo" not in lower and "zdjęcie" not in lower,
        "low", "Nie wspominaj o zdjęciu — w CV dla IT jest zbędne.")

    add("no_references", "Brak 'referencje na żądanie'",
        "references available" not in lower and "referencje na żądanie" not in lower,
        "low", "Fraza 'referencje na żądanie' jest przestarzała — usuń ją.")

    # --- Wynik ---
    weights = {"high": 3, "medium": 2, "low": 1}
    total_weight = sum(weights[c["priority"]] for c in checks)
    passed_weight = sum(weights[c["priority"]] for c in checks if c["passed"])
    score = round(passed_weight / total_weight * 100) if total_weight else 0

    failed = [c for c in checks if not c["passed"]]
    failed.sort(key=lambda c: weights[c["priority"]], reverse=True)

    return {
        "score": score,
        "checks": checks,
        "top_issues": failed[:5],
        "word_count": word_count,
        "metrics_found": len(metrics),
        "strong_verbs_found": strong_count,
    }
