from app import matcher


def _offer(**kw):
    base = {"id": "1", "source": "X", "title": "", "company": "", "location": "",
            "remote": False, "salary": "", "url": "", "skills": [], "description": ""}
    base.update(kw)
    return base


def test_perfect_skill_match_scores_high(sample_profile):
    offer = _offer(title="Python Developer", skills=["Python", "Django"])
    scored = matcher.score_offer(offer, sample_profile)
    assert scored["score"] >= 70
    assert set(scored["matched_skills"]) == {"Python", "Django"}
    assert scored["missing_skills"] == []


def test_missing_skills_reported(sample_profile):
    offer = _offer(title="Go Engineer", skills=["Go", "Kafka", "Python"])
    scored = matcher.score_offer(offer, sample_profile)
    assert "Python" in scored["matched_skills"]
    assert "Go" in scored["missing_skills"]
    assert "Kafka" in scored["missing_skills"]


def test_rank_filters_by_min_score(sample_profile):
    offers = [
        _offer(id="a", title="Python Developer", skills=["Python", "Django"]),
        _offer(id="b", title="COBOL Developer", skills=["COBOL"], description="mainframe"),
    ]
    ranked = matcher.rank_offers(offers, sample_profile, min_score=50)
    ids = [o["id"] for o in ranked]
    assert "a" in ids
    assert "b" not in ids


def test_rank_sorts_descending(sample_profile):
    offers = [
        _offer(id="low", title="x", skills=["Python", "Kafka", "Go", "Rust", "Scala"]),
        _offer(id="high", title="x", skills=["Python", "Django", "Docker"]),
    ]
    ranked = matcher.rank_offers(offers, sample_profile)
    assert ranked[0]["score"] >= ranked[-1]["score"]


def test_skills_detected_from_description_when_no_explicit(sample_profile):
    offer = _offer(title="Backend Engineer", description="Stack: Python, Docker, AWS")
    scored = matcher.score_offer(offer, sample_profile)
    assert "Python" in scored["matched_skills"]


def test_score_includes_kw_fields(sample_profile):
    offer = _offer(
        title="Senior Python Developer",
        skills=["Python", "Docker"],
        description="We need Python developer with Docker and Kubernetes experience.",
    )
    scored = matcher.score_offer(offer, sample_profile)
    assert "kw_score" in scored
    assert "kw_matched" in scored
    assert "kw_missing" in scored
    assert isinstance(scored["kw_score"], int)
    assert 0 <= scored["kw_score"] <= 100


def test_kw_missing_contains_unmatched_terms(sample_profile):
    offer = _offer(
        title="Go Developer",
        skills=["Go"],
        description="Expert Go developer with gRPC, Kafka, Terraform experience required.",
    )
    scored = matcher.score_offer(offer, sample_profile)
    missing_lower = [m.lower() for m in scored["kw_missing"]]
    assert "go" in missing_lower or "kafka" in missing_lower or "terraform" in missing_lower
