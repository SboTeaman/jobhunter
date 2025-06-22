"""Testy modułu app/cv_quality.py."""
from app import cv_quality


_GOOD_CV = """
Jan Kowalski  |  jan@example.com  |  github.com/jan  |  +48 600 000 000

DOŚWIADCZENIE
2020-2024  Acme Corp, Senior Python Developer
  - Built distributed microservices handling 1M requests/day
  - Reduced deployment time by 40% using Docker and Kubernetes
  - Led team of 5 engineers

2018-2020  StartupX, Backend Developer
  - Developed REST APIs with FastAPI and PostgreSQL
  - Increased test coverage from 30% to 85%

WYKSZTAŁCENIE
2014-2018  Politechnika Warszawska, Informatyka, inż.

UMIEJĘTNOŚCI
Python, FastAPI, Django, Docker, Kubernetes, PostgreSQL, Redis, AWS, Git
"""

_POOR_CV = "I worked at a company. I helped with Python things. It was good."


def test_good_cv_scores_higher():
    good = cv_quality.analyze(_GOOD_CV)
    poor = cv_quality.analyze(_POOR_CV)
    assert good["score"] > poor["score"]


def test_score_range():
    result = cv_quality.analyze(_GOOD_CV)
    assert 0 <= result["score"] <= 100


def test_returns_checks_list():
    result = cv_quality.analyze(_GOOD_CV)
    assert isinstance(result["checks"], list)
    assert len(result["checks"]) >= 5


def test_each_check_has_required_fields():
    result = cv_quality.analyze(_GOOD_CV)
    for c in result["checks"]:
        assert "id" in c
        assert "passed" in c
        assert isinstance(c["passed"], bool)


def test_top_issues_not_passed():
    result = cv_quality.analyze(_POOR_CV)
    for issue in result["top_issues"]:
        assert issue["passed"] is False


def test_good_cv_detects_contact():
    result = cv_quality.analyze(_GOOD_CV)
    contact_check = next((c for c in result["checks"] if c["id"] == "has_contact"), None)
    assert contact_check is not None
    assert contact_check["passed"] is True


def test_good_cv_detects_metrics():
    result = cv_quality.analyze(_GOOD_CV)
    metrics_check = next((c for c in result["checks"] if c["id"] == "has_metrics"), None)
    assert metrics_check is not None
    assert metrics_check["passed"] is True


def test_poor_cv_missing_sections():
    result = cv_quality.analyze(_POOR_CV)
    section_checks = [c for c in result["checks"] if c["id"] in ("has_experience", "has_skills", "has_education")]
    failed = [c for c in section_checks if not c["passed"]]
    assert len(failed) >= 2


def test_empty_cv():
    result = cv_quality.analyze("")
    assert result["score"] < 30  # practically nothing passes
    assert len(result["top_issues"]) > 0


def test_word_count_returned():
    result = cv_quality.analyze(_GOOD_CV)
    assert result["word_count"] > 0
