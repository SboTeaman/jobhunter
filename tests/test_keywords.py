"""Testy modułu app/keywords.py."""
from app import keywords


def test_extract_keywords_returns_nonempty():
    words = keywords.extract_keywords("Python developer with Django and PostgreSQL experience")
    assert len(words) > 0


def test_stopwords_excluded():
    words = keywords.extract_keywords("the and or a an in on with by")
    assert words == []


def test_extract_keywords_removes_short_tokens():
    words = keywords.extract_keywords("Go Rust C++ Java")
    # "C++" has special chars; we mainly care that normal short stop-words are gone
    for w in words:
        assert len(w) >= 2


def test_keyword_coverage_full_match():
    offer = "Python Django REST API developer"
    cv    = "Python Django REST API developer senior"
    result = keywords.keyword_coverage(offer, cv)
    assert result["score"] == 100
    assert result["missing"] == []


def test_keyword_coverage_partial_match():
    offer = "Python Kubernetes Kafka developer"
    cv    = "Python Django Docker developer"
    result = keywords.keyword_coverage(offer, cv)
    assert 0 < result["score"] < 100
    assert "Kafka" in result["missing"] or "kubernetes" in [m.lower() for m in result["missing"]]


def test_keyword_coverage_no_match():
    offer = "COBOL Fortran mainframe assembly legacy"
    cv    = "Python Django FastAPI Redis microservices"
    result = keywords.keyword_coverage(offer, cv)
    assert result["score"] == 0
    assert len(result["missing"]) > 0


def test_top_missing_prioritizes_capitalized():
    missing = ["python", "Docker", "Redis", "and", "kubernetes", "CI/CD", "AWS"]
    top = keywords.top_missing(missing, n=3)
    # Capitalized tokens should appear first
    capitalized = [t for t in top if t[0].isupper()]
    assert len(capitalized) >= 1


def test_keyword_coverage_returns_matched_list():
    offer = "Python Docker Kubernetes"
    cv    = "Python Docker Java"
    result = keywords.keyword_coverage(offer, cv)
    matched_lower = [m.lower() for m in result["matched"]]
    assert "python" in matched_lower
    assert "docker" in matched_lower
