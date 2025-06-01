"""Wspólne narzędzia dla źródeł ofert."""
from __future__ import annotations

import hashlib

import httpx

from ..config import HTTP_TIMEOUT, USER_AGENT


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "pl,en;q=0.9"},
        follow_redirects=True,
    )


def make_offer(
    *,
    source: str,
    title: str,
    company: str = "",
    location: str = "",
    remote: bool = False,
    salary: str = "",
    url: str = "",
    skills: list[str] | None = None,
    description: str = "",
    published: str = "",
) -> dict:
    """Tworzy znormalizowaną ofertę o stałym schemacie."""
    raw_id = f"{source}|{url or title + company}"
    offer_id = hashlib.md5(raw_id.encode("utf-8")).hexdigest()[:16]
    return {
        "id": offer_id,
        "source": source,
        "title": (title or "").strip(),
        "company": (company or "").strip(),
        "location": (location or "").strip(),
        "remote": bool(remote),
        "salary": (salary or "").strip(),
        "url": (url or "").strip(),
        "skills": skills or [],
        "description": (description or "").strip(),
        "published": published or "",
    }
