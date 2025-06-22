"""Testy warstwy API (TestClient). Pipeline wyszukiwania jest mockowany,
baza i profil wskazują na pliki tymczasowe - bez sieci i bez dotykania danych."""
import pytest
from fastapi.testclient import TestClient

from app import config, db, main


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Przekieruj bazę i profil na pliki tymczasowe.
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(config, "PROFILE_PATH", tmp_path / "profile.json")
    # Wyczyść stan globalny modułu między testami.
    main._PROFILE = None
    main._OFFER_CACHE.clear()

    async def fake_search(profile, sources, **kw):
        offer = {
            "id": "off1", "source": "JustJoin.it", "sources": ["JustJoin.it"],
            "title": "Senior Python Developer", "company": "Acme", "location": "Warszawa",
            "remote": True, "salary": "20000-25000 PLN", "url": "http://x",
            "skills": ["Python"], "description": "", "score": 88,
            "matched_skills": ["Python"], "missing_skills": ["Kafka"], "offer_skills": ["Python", "Kafka"],
        }
        return {"offers": [offer], "errors": {}, "skill_gaps": [{"skill": "Kafka", "count": 1}],
                "total_fetched": 1, "total_after_dedup": 1, "total_matched": 1}

    monkeypatch.setattr(main.pipeline, "run_search", fake_search)

    with TestClient(main.app) as c:
        yield c


def test_sources_endpoint(client):
    r = client.get("/api/sources")
    assert r.status_code == 200
    keys = [s["key"] for s in r.json()["sources"]]
    assert "justjoin" in keys and "nofluffjobs" in keys


def test_search_requires_cv(client):
    r = client.post("/api/search", json={"sources": ["justjoin"]})
    assert r.status_code == 400


def test_full_flow_upload_search_track(client):
    # 1. upload CV
    cv = b"Senior Python Developer, 6 lat doswiadczenia. Python, Django, Docker."
    r = client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    assert r.status_code == 200
    assert "Python" in r.json()["profile"]["skills"]

    # 2. search
    r = client.post("/api/search", json={"sources": ["justjoin"], "min_score": 0})
    assert r.status_code == 200
    data = r.json()
    assert data["total_matched"] == 1
    assert data["skill_gaps"][0]["skill"] == "Kafka"
    assert data["offers"][0]["id"] == "off1"

    # 3. cover letter (tryb szablonu - bez AI)
    r = client.post("/api/cover-letter", json={"offer_id": "off1", "use_ai": False})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "template"
    assert "Acme" in body["letter"]

    # 4. track
    r = client.post("/api/track", json={"offer_id": "off1", "status": "do_aplikacji"})
    assert r.status_code == 200
    assert r.json()["application"]["status"] == "do_aplikacji"

    # 5. tracker list
    r = client.get("/api/tracker")
    assert len(r.json()["applications"]) == 1

    # 6. update status
    app_id = "off1"
    r = client.patch(f"/api/tracker/{app_id}", json={"status": "wyslana"})
    assert r.json()["application"]["status"] == "wyslana"

    # 7. CSV export
    r = client.get("/api/tracker/export.csv")
    assert r.status_code == 200
    assert "Senior Python Developer" in r.text
    assert r.headers["content-type"].startswith("text/csv")

    # 8. delete
    r = client.delete(f"/api/tracker/{app_id}")
    assert r.json()["ok"] is True
    r = client.get("/api/tracker")
    assert len(r.json()["applications"]) == 0


def test_cover_letter_unknown_offer(client):
    cv = b"Python developer"
    client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    r = client.post("/api/cover-letter", json={"offer_id": "nope", "use_ai": False})
    assert r.status_code == 404


def test_cv_quality_returned_on_upload(client):
    cv = b"Senior Python Developer\n\nDoswiadczenie: Python, Docker 5 lat.\n\nWyksztalcenie: informatyka."
    r = client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    assert r.status_code == 200
    body = r.json()
    assert "quality" in body
    q = body["quality"]
    assert "score" in q
    assert 0 <= q["score"] <= 100
    assert "checks" in q


def test_cv_quality_endpoint(client):
    cv = b"Python developer with 3 years of experience."
    client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    r = client.get("/api/cv-quality")
    assert r.status_code == 200
    assert "score" in r.json()


def test_cv_quality_requires_cv(client):
    r = client.get("/api/cv-quality")
    assert r.status_code == 400


def test_config_endpoint(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    assert "ai_enabled" in r.json()


def test_preference_save_and_stats(client):
    cv = b"Python developer"
    client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    # run search to populate cache
    client.post("/api/search", json={"sources": ["justjoin"], "min_score": 0})
    # save a dislike
    r = client.post("/api/preference", json={"offer_id": "off1", "action": "dislike", "offer": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # stats
    r = client.get("/api/preferences/stats")
    assert r.status_code == 200
    stats = r.json()
    assert "disliked_skills" in stats or "total_disliked" in stats or "disliked" in stats


def test_recruiter_crud(client):
    rec = {"name": "Anna Nowak", "email": "anna@example.com", "company": "Acme",
           "phone": "", "linkedin": "", "notes": "VIP", "follow_up": "2026-07-01"}
    r = client.post("/api/recruiters", json=rec)
    assert r.status_code == 200
    rid = r.json()["recruiter"]["id"]
    # list
    r = client.get("/api/recruiters")
    assert any(rec["id"] == rid for rec in r.json()["recruiters"])
    # delete
    r = client.delete(f"/api/recruiters/{rid}")
    assert r.json()["ok"] is True
    r = client.get("/api/recruiters")
    assert not any(rec["id"] == rid for rec in r.json()["recruiters"])


def test_suggest_cv_requires_cv(client):
    r = client.post("/api/suggest-cv", json={"offer_id": "nope"})
    assert r.status_code == 400


def test_suggest_cv_unknown_offer(client):
    cv = b"Python developer"
    client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    r = client.post("/api/suggest-cv", json={"offer_id": "nonexistent"})
    assert r.status_code == 404


def test_tracker_notes_update(client):
    cv = b"Python developer"
    client.post("/api/upload-cv", files={"file": ("cv.txt", cv, "text/plain")})
    client.post("/api/search", json={"sources": ["justjoin"], "min_score": 0})
    client.post("/api/track", json={"offer_id": "off1", "status": "zapisana"})
    r = client.patch("/api/tracker/off1/notes", json={"notes": "Świetna firma!"})
    assert r.status_code == 200
    assert r.json()["application"]["notes"] == "Świetna firma!"
