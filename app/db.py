"""Baza danych SQLite: tracker aplikacji, CRM rekruterów, preferencje."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .config import DB_PATH

# Rozszerzone etapy rekrutacji (z datami).
STATUSES = [
    "zapisana", "do_aplikacji", "wyslana",
    "screening", "technical", "hr", "oferta", "odrzucona",
]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id           TEXT PRIMARY KEY,
                source       TEXT,
                title        TEXT,
                company      TEXT,
                url          TEXT,
                score        INTEGER,
                status       TEXT DEFAULT 'zapisana',
                notes        TEXT DEFAULT '',
                cover_letter TEXT DEFAULT '',
                stage_dates  TEXT DEFAULT '{}',
                created_at   TEXT,
                updated_at   TEXT
            )
        """)
        # Nowa kolumna stage_dates — migracja bezpieczna dla istniejących baz.
        try:
            conn.execute("ALTER TABLE applications ADD COLUMN stage_dates TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS recruiters (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                email       TEXT,
                phone       TEXT,
                company     TEXT,
                linkedin    TEXT,
                notes       TEXT DEFAULT '',
                follow_up   TEXT,
                created_at  TEXT,
                updated_at  TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                offer_id    TEXT PRIMARY KEY,
                action      TEXT NOT NULL,
                title       TEXT,
                company     TEXT,
                skills      TEXT DEFAULT '[]',
                created_at  TEXT
            )
        """)


# ─── Applications ───────────────────────────────────────────────────────────

def save_application(offer: dict, status: str = "zapisana", cover_letter: str = "") -> dict:
    now = _now()
    stage_dates = json.dumps({status: now} if status != "zapisana" else {})
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO applications
              (id, source, title, company, url, score, status, cover_letter,
               stage_dates, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                cover_letter=CASE WHEN excluded.cover_letter!=''
                    THEN excluded.cover_letter ELSE applications.cover_letter END,
                updated_at=excluded.updated_at
            """,
            (offer.get("id"), offer.get("source"), offer.get("title"),
             offer.get("company"), offer.get("url"), offer.get("score", 0),
             status, cover_letter, stage_dates, now, now),
        )
    return get_application(offer.get("id"))


def get_application(app_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id=?", (app_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["stage_dates"] = json.loads(d.get("stage_dates") or "{}")
        except Exception:
            d["stage_dates"] = {}
        return d


def list_applications() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY updated_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["stage_dates"] = json.loads(d.get("stage_dates") or "{}")
        except Exception:
            d["stage_dates"] = {}
        result.append(d)
    return result


def update_status(app_id: str, status: str, note: str = "") -> dict | None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id=?", (app_id,)
        ).fetchone()
        if not row:
            return None
        app = dict(row)
        dates = app.get("stage_dates") or {}
        if isinstance(dates, str):
            dates = json.loads(dates)
        dates[status] = now
        conn.execute(
            "UPDATE applications SET status=?, stage_dates=?, updated_at=? WHERE id=?",
            (status, json.dumps(dates), now, app_id),
        )
        if note:
            conn.execute(
                "UPDATE applications SET notes=notes||'\n'||? WHERE id=?",
                (f"[{now[:10]}] {note}", app_id),
            )
    return get_application(app_id)


def update_notes(app_id: str, notes: str) -> dict | None:
    with _conn() as conn:
        conn.execute(
            "UPDATE applications SET notes=?, updated_at=? WHERE id=?",
            (notes, _now(), app_id),
        )
    return get_application(app_id)


def delete_application(app_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM applications WHERE id=?", (app_id,))


# ─── Recruiters CRM ─────────────────────────────────────────────────────────

def list_recruiters() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM recruiters ORDER BY follow_up ASC, updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def save_recruiter(data: dict) -> dict:
    now = _now()
    rid = data.get("id")
    with _conn() as conn:
        if rid:
            conn.execute(
                """UPDATE recruiters SET name=?,email=?,phone=?,company=?,
                   linkedin=?,notes=?,follow_up=?,updated_at=? WHERE id=?""",
                (data.get("name"), data.get("email"), data.get("phone"),
                 data.get("company"), data.get("linkedin"), data.get("notes"),
                 data.get("follow_up"), now, rid),
            )
        else:
            cur = conn.execute(
                """INSERT INTO recruiters
                   (name,email,phone,company,linkedin,notes,follow_up,created_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (data.get("name",""), data.get("email",""), data.get("phone",""),
                 data.get("company",""), data.get("linkedin",""),
                 data.get("notes",""), data.get("follow_up"), now, now),
            )
            rid = cur.lastrowid
    with _conn() as conn:
        row = conn.execute("SELECT * FROM recruiters WHERE id=?", (rid,)).fetchone()
        return dict(row) if row else {}


def delete_recruiter(rid: int) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM recruiters WHERE id=?", (rid,))


# ─── Preferences ────────────────────────────────────────────────────────────

def save_preference(offer_id: str, action: str, offer: dict) -> None:
    """action: 'like' | 'dislike'"""
    with _conn() as conn:
        conn.execute(
            """INSERT INTO preferences (offer_id,action,title,company,skills,created_at)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(offer_id) DO UPDATE SET action=excluded.action""",
            (offer_id, action, offer.get("title",""), offer.get("company",""),
             json.dumps(offer.get("skills",[])), _now()),
        )


def get_preference(offer_id: str) -> str | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT action FROM preferences WHERE offer_id=?", (offer_id,)
        ).fetchone()
        return row["action"] if row else None


def disliked_ids() -> set[str]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT offer_id FROM preferences WHERE action='dislike'"
        ).fetchall()
        return {r["offer_id"] for r in rows}


def get_preferences_batch(offer_ids: list[str]) -> dict[str, str]:
    if not offer_ids:
        return {}
    placeholders = ",".join("?" * len(offer_ids))
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT offer_id, action FROM preferences WHERE offer_id IN ({placeholders})",
            offer_ids,
        ).fetchall()
    return {r["offer_id"]: r["action"] for r in rows}


def preference_stats() -> dict:
    """Zwraca najczęściej lubiane/ignorowane technologie (do personalizacji)."""
    with _conn() as conn:
        rows = conn.execute("SELECT action, skills FROM preferences").fetchall()
    from collections import Counter
    liked: Counter = Counter()
    disliked: Counter = Counter()
    for r in rows:
        try:
            skills = json.loads(r["skills"] or "[]")
        except Exception:
            skills = []
        for s in skills:
            (liked if r["action"] == "like" else disliked)[s] += 1
    return {
        "liked_skills": [{"skill": k, "count": v} for k, v in liked.most_common(10)],
        "disliked_skills": [{"skill": k, "count": v} for k, v in disliked.most_common(10)],
    }
