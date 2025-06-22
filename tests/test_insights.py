from app.insights import skill_gaps


def test_counts_missing_skills():
    offers = [
        {"missing_skills": ["Kafka", "Go"]},
        {"missing_skills": ["Kafka", "Rust"]},
        {"missing_skills": ["Kafka"]},
    ]
    gaps = skill_gaps(offers)
    assert gaps[0] == {"skill": "Kafka", "count": 3}
    skills = {g["skill"] for g in gaps}
    assert {"Go", "Rust"} <= skills


def test_top_limit():
    offers = [{"missing_skills": [f"S{i}" for i in range(20)]}]
    gaps = skill_gaps(offers, top=5)
    assert len(gaps) == 5


def test_empty():
    assert skill_gaps([]) == []
