"""Wspólne fixture'y i dane testowe (bez sieci - wszystko mockowane/lokalne)."""
from __future__ import annotations

import pytest

SAMPLE_CV = """
Jan Kowalski — Senior Python Developer

Doświadczenie: 6 lat doświadczenia komercyjnego w wytwarzaniu oprogramowania.
Umiejętności: Python, Django, FastAPI, PostgreSQL, Docker, Kubernetes, AWS,
REST, Git, Redis. Wykształcenie: informatyka. Język: polski.
"""


@pytest.fixture
def sample_cv_bytes() -> bytes:
    return SAMPLE_CV.encode("utf-8")


@pytest.fixture
def sample_profile():
    return {
        "filename": "cv.txt",
        "skills": ["Python", "Django", "FastAPI", "PostgreSQL", "Docker", "AWS", "Git"],
        "years": 6,
        "seniority": 3,
        "language": "pl",
        "text": SAMPLE_CV,
    }


# Fragment HTML strony oferty JustJoin (zaescape'owany JSON w strumieniu RSC),
# odwzorowujący realną strukturę użytą przez parser. Realna strona ma te dane
# w jednej linii, więc fixture też (bez wewnętrznych znaków nowej linii).
JJ_HTML = (
    r'<script>self.__next_f.push([1,"...'
    r'\"companyName\":\"Reef Technologies\",\"companyUrl\":\"https://x\",'
    r'\"body\":\"$46\",\"city\":\"Warszawa\",'
    r'\"workplaceType\":{\"label\":\"remote\",\"value\":\"remote\"},'
    r'\"requiredSkills\":[{\"id\":\"Backend\",\"name\":\"Backend\",\"level\":4},'
    r'{\"id\":\"Python\",\"name\":\"Python\",\"level\":4},'
    r'{\"id\":\"Docker\",\"name\":\"Docker\",\"level\":3}],'
    r'\"employmentTypes\":[{\"currency\":\"GBP\",\"from\":36.6,\"fromPln\":null,\"to\":56.9,\"toPln\":null,\"type\":\"b2b\",\"unit\":\"hour\"},'
    r'{\"currency\":\"PLN\",\"from\":180,\"fromPln\":null,\"to\":280,\"toPln\":null,\"type\":\"b2b\",\"unit\":\"hour\"}]..."])</script>'
)

JJ_URL = "https://justjoin.it/job-offer/reef-technologies-senior-python-backend-engineer-warszawa"


@pytest.fixture
def jj_html() -> str:
    return JJ_HTML


@pytest.fixture
def jj_url() -> str:
    return JJ_URL
