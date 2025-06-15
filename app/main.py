"""Serwer FastAPI — API + serwowanie interfejsu webowego."""
from __future__ import annotations

import csv
import io
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import apply, config, cv_parser, cv_quality, db, matcher, pipeline, scraper
from .sources import SOURCES
from .sources.base import make_offer

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_PROFILE: dict | None = None
_OFFER_CACHE: dict[str, dict] = {}


@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _PROFILE
    db.init_db()
    if config.PROFILE_PATH.exists():
        try:
            _PROFILE = json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Nie udało się wczytać profilu: %s", e)
            _PROFILE = None
    yield


app = FastAPI(title="JobHunter", version="2.0", lifespan=_lifespan)

# CORS — potrzebne dla rozszerzenia Chrome (origin: chrome-extension://...).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://[a-z]+|http://localhost(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _profile_summary(p: dict) -> dict:
    return {
        "filename": p.get("filename"),
        "skills": p.get("skills", []),
        "years": p.get("years", 0),
        "seniority": p.get("seniority", 1),
        "seniority_label": cv_parser.SENIORITY_LABELS.get(p.get("seniority", 1), ""),
        "language": p.get("language", "pl"),
        "char_count": p.get("char_count", 0),
    }


# ─── CV ─────────────────────────────────────────────────────────────────────

@app.get("/api/sources")
def get_sources() -> dict:
    return {"sources": [{"key": k, "label": v[0]} for k, v in SOURCES.items()]}


@app.get("/api/profile")
def get_profile() -> dict:
    if not _PROFILE:
        return {"profile": None}
    return {"profile": _profile_summary(_PROFILE)}


@app.post("/api/upload-cv")
async def upload_cv(file: UploadFile = File(...)) -> dict:
    global _PROFILE
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in config.ALLOWED_CV_EXTENSIONS:
        raise HTTPException(400, f"Niedozwolony typ pliku. Akceptowane: {sorted(config.ALLOWED_CV_EXTENSIONS)}")
    data = await file.read(config.MAX_CV_SIZE_BYTES + 1)
    if len(data) > config.MAX_CV_SIZE_BYTES:
        raise HTTPException(413, "Plik za duży (maks. 5 MB).")
    if not data:
        raise HTTPException(400, "Pusty plik.")
    safe_filename = Path(file.filename or "upload").name
    profile = cv_parser.build_profile(safe_filename, data)
    _PROFILE = profile
    config.PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    quality = cv_quality.analyze(profile.get("text", ""))
    return {"profile": _profile_summary(profile), "quality": quality}


@app.get("/api/cv-quality")
def get_cv_quality() -> dict:
    if not _PROFILE:
        raise HTTPException(400, "Najpierw wgraj CV.")
    return cv_quality.analyze(_PROFILE.get("text", ""))


# ─── Wyszukiwanie ────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    sources: list[str] = Field(default_factory=list, max_length=20)
    query: str = Field("", max_length=200)
    min_score: int = Field(0, ge=0, le=100)
    remote_only: bool = False
    location: str = Field("", max_length=100)
    salary_min: int = Field(0, ge=0)
    limit: int = Field(60, ge=1, le=200)


@app.post("/api/search")
async def search(req: SearchRequest) -> dict:
    if not _PROFILE:
        raise HTTPException(400, "Najpierw wgraj CV.")
    disliked = db.disliked_ids()
    result = await pipeline.run_search(
        _PROFILE, req.sources,
        query=req.query, min_score=req.min_score,
        remote_only=req.remote_only, location=req.location,
        salary_min=req.salary_min, limit=req.limit,
    )
    # Filtruj zignorowane oferty; dodaj info o preferencji.
    offer_ids = [o["id"] for o in result["offers"] if o.get("id") and o["id"] not in disliked]
    preferences = db.get_preferences_batch(offer_ids)
    offers = []
    for o in result["offers"]:
        if o.get("id") in disliked:
            continue
        o["preference"] = preferences.get(o.get("id", ""), "")
        _OFFER_CACHE[o["id"]] = o
        offers.append(o)
    result["offers"] = offers
    result["total_matched"] = len(offers)
    return result


# ─── Oferta z URL ────────────────────────────────────────────────────────────

class UrlRequest(BaseModel):
    url: str


@app.post("/api/offer-from-url")
async def offer_from_url(req: UrlRequest) -> dict:
    if not _PROFILE:
        raise HTTPException(400, "Najpierw wgraj CV.")
    try:
        offer = await scraper.offer_from_url(req.url)
    except Exception as e:
        raise HTTPException(400, f"Nie udało się pobrać oferty: {e}")
    scored = matcher.score_offer(offer, _PROFILE)
    _OFFER_CACHE[scored["id"]] = scored
    return {"offer": scored}


# ─── Scoring z rozszerzenia Chrome ───────────────────────────────────────────

@app.post("/api/score-offer")
async def score_offer_ext(offer: dict) -> dict:
    """Używane przez rozszerzenie Chrome: przyjmuje surowe dane oferty,
    zwraca wynik scoringu."""
    if not _PROFILE:
        raise HTTPException(400, "Brak profilu CV.")
    # Znormalizuj ofertę z rozszerzenia (może brakować niektórych pól).
    normalized = make_offer(
        source=offer.get("source", ""),
        title=offer.get("title", ""),
        company=offer.get("company", ""),
        url=offer.get("url", ""),
        skills=offer.get("skills", []),
        salary=offer.get("salary", ""),
        remote=offer.get("remote", False),
    )
    scored = matcher.score_offer(normalized, _PROFILE)
    _OFFER_CACHE[scored["id"]] = scored
    return {"offer": scored}


# ─── List motywacyjny + sugestie ─────────────────────────────────────────────

class CoverLetterRequest(BaseModel):
    offer_id: str
    use_ai: bool = True


@app.post("/api/cover-letter")
async def cover_letter(req: CoverLetterRequest) -> dict:
    if not _PROFILE:
        raise HTTPException(400, "Najpierw wgraj CV.")
    offer = _OFFER_CACHE.get(req.offer_id)
    if not offer:
        raise HTTPException(404, "Nie znaleziono oferty (odśwież wyszukiwanie).")
    return await apply.generate_cover_letter(offer, _PROFILE, use_ai=req.use_ai)


class SuggestRequest(BaseModel):
    offer_id: str


@app.post("/api/suggest-cv")
async def suggest_cv(req: SuggestRequest) -> dict:
    if not _PROFILE:
        raise HTTPException(400, "Najpierw wgraj CV.")
    offer = _OFFER_CACHE.get(req.offer_id)
    if not offer:
        raise HTTPException(404, "Nie znaleziono oferty.")
    return await apply.suggest_cv_improvements(offer, _PROFILE)


# ─── Tracker ─────────────────────────────────────────────────────────────────

class TrackRequest(BaseModel):
    offer_id: str
    status: str = "zapisana"
    cover_letter: str = ""


@app.post("/api/track")
def track(req: TrackRequest) -> dict:
    offer = _OFFER_CACHE.get(req.offer_id)
    if not offer:
        raise HTTPException(404, "Nie znaleziono oferty.")
    return {"application": db.save_application(offer, req.status, req.cover_letter)}


class TrackExtRequest(BaseModel):
    offer: dict
    status: str = "do_aplikacji"


@app.post("/api/track-ext")
def track_ext(req: TrackExtRequest) -> dict:
    """Używane przez rozszerzenie Chrome (oferta bez cache)."""
    _OFFER_CACHE[req.offer.get("id", "")] = req.offer
    return {"application": db.save_application(req.offer, req.status)}


@app.get("/api/tracker")
def tracker() -> dict:
    return {"applications": db.list_applications(), "statuses": db.STATUSES}


class StatusRequest(BaseModel):
    status: Literal["zapisana", "do_aplikacji", "wyslana", "screening", "technical", "hr", "oferta", "odrzucona"]
    note: str = Field("", max_length=1000)


@app.patch("/api/tracker/{app_id}")
def set_status(app_id: str, req: StatusRequest) -> dict:
    updated = db.update_status(app_id, req.status, req.note)
    if not updated:
        raise HTTPException(404, "Nie znaleziono aplikacji.")
    return {"application": updated}


class NotesRequest(BaseModel):
    notes: str


@app.patch("/api/tracker/{app_id}/notes")
def set_notes(app_id: str, req: NotesRequest) -> dict:
    updated = db.update_notes(app_id, req.notes)
    if not updated:
        raise HTTPException(404, "Nie znaleziono aplikacji.")
    return {"application": updated}


@app.delete("/api/tracker/{app_id}")
def remove(app_id: str) -> dict:
    db.delete_application(app_id)
    return {"ok": True}


@app.get("/api/tracker/export.csv")
def export_csv() -> StreamingResponse:
    apps = db.list_applications()
    buf = io.StringIO()
    cols = ["title", "company", "source", "url", "score", "status", "created_at", "updated_at"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for a in apps:
        writer.writerow(a)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aplikacje.csv"},
    )


# ─── Preferencje ─────────────────────────────────────────────────────────────

class PreferenceRequest(BaseModel):
    offer_id: str
    action: str  # 'like' | 'dislike'
    offer: dict = {}


@app.post("/api/preference")
def set_preference(req: PreferenceRequest) -> dict:
    offer = _OFFER_CACHE.get(req.offer_id) or req.offer
    db.save_preference(req.offer_id, req.action, offer)
    return {"ok": True, "stats": db.preference_stats()}


@app.get("/api/preferences/stats")
def preference_stats() -> dict:
    return db.preference_stats()


# ─── CRM rekruterów ──────────────────────────────────────────────────────────

class RecruiterRequest(BaseModel):
    id: int | None = None
    name: str
    email: str = ""
    phone: str = ""
    company: str = ""
    linkedin: str = ""
    notes: str = ""
    follow_up: str = ""


@app.get("/api/recruiters")
def list_recruiters() -> dict:
    return {"recruiters": db.list_recruiters()}


@app.post("/api/recruiters")
def save_recruiter(req: RecruiterRequest) -> dict:
    return {"recruiter": db.save_recruiter(req.model_dump())}


@app.delete("/api/recruiters/{rid}")
def delete_recruiter(rid: int) -> dict:
    db.delete_recruiter(rid)
    return {"ok": True}


# ─── Config ──────────────────────────────────────────────────────────────────

@app.get("/api/config")
def get_config() -> dict:
    return {"ai_enabled": bool(config.ANTHROPIC_API_KEY), "ai_model": config.AI_MODEL}


# ─── Frontend ────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
