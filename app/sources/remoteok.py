"""Źródło: RemoteOK (publiczne API JSON, oferty zdalne)."""
from __future__ import annotations

from .base import client, make_offer

API_URL = "https://remoteok.com/api"


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    async with client() as c:
        try:
            r = await c.get(API_URL)
            if r.status_code != 200:
                return []
            data = r.json()
        except Exception:
            return []

    if not isinstance(data, list):
        return []

    q = query.lower()
    offers: list[dict] = []
    for it in data:
        # Pierwszy element to nota prawna - pomiń wpisy bez 'position'.
        if not isinstance(it, dict) or not it.get("position"):
            continue
        title = it.get("position", "")
        company = it.get("company", "")
        tags = it.get("tags", []) or []

        salary = ""
        if it.get("salary_min") and it.get("salary_max"):
            salary = f"${it['salary_min']}-${it['salary_max']}"

        if q and q not in (title + " " + company + " " + " ".join(tags)).lower():
            continue

        offers.append(
            make_offer(
                source="RemoteOK",
                title=title,
                company=company,
                location=it.get("location", "") or "Remote",
                remote=True,
                salary=salary,
                url=it.get("url", "") or it.get("apply_url", ""),
                skills=tags,
                description=it.get("description", ""),
                published=it.get("date", ""),
            )
        )
        if len(offers) >= limit:
            break
    return offers
