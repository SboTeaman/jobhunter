"""Źródło: NoFluffJobs (publiczne API joboffers/main, paginowane)."""
from __future__ import annotations

from .base import client, make_offer

# Endpoint wymaga parametrów waluty/okresu; zwraca {"postings": [...]}.
BASE = (
    "https://nofluffjobs.com/api/joboffers/main"
    "?salaryCurrency=PLN&salaryPeriod=month&region=pl"
)


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    url = f"{BASE}&pageTo=1&pageSize={max(limit, 30)}"
    if query:
        url += f"&criteria=keyword%3D{query.replace(' ', '%20')}"

    async with client() as c:
        try:
            r = await c.get(url, headers={"Accept": "application/json"})
            if r.status_code != 200:
                return []
            data = r.json()
        except Exception:
            return []

    postings = data.get("postings", []) if isinstance(data, dict) else []
    q = query.lower()
    offers: list[dict] = []
    for p in postings:
        title = p.get("title") or ""          # stanowisko
        company = p.get("name") or ""         # nazwa firmy
        if not title:
            continue

        # Lokalizacja
        loc = p.get("location", {}) or {}
        places = loc.get("places", []) or []
        cities = [pl.get("city", "") for pl in places if pl.get("city")]
        remote = bool(p.get("fullyRemote")) or loc.get("fullyRemote", False)

        # Technologie / skille
        skills: list[str] = []
        tech = p.get("technology")
        if isinstance(tech, str) and tech:
            skills.append(tech)
        elif isinstance(tech, list):
            skills.extend([t for t in tech if isinstance(t, str)])
        tiles = p.get("tiles", {}) or {}
        for t in tiles.get("values", []) or []:
            if isinstance(t, dict) and t.get("value"):
                skills.append(t["value"])

        # Seniority (lista lub string) - dokładamy do tytułu na potrzeby matchera,
        # ale tylko jeśli nie powtarza tego, co już jest w tytule.
        sen = p.get("seniority")
        sen_txt = " ".join(sen) if isinstance(sen, list) else (sen or "")
        if sen_txt and sen_txt.lower() in title.lower():
            sen_txt = ""

        # Widełki
        salary_obj = p.get("salary", {}) or {}
        salary = ""
        if salary_obj.get("from") and salary_obj.get("to"):
            salary = f"{salary_obj['from']}-{salary_obj['to']} {salary_obj.get('currency', 'PLN')}"

        seo = p.get("url") or p.get("id", "")
        offer_url = f"https://nofluffjobs.com/pl/job/{seo}" if seo else "https://nofluffjobs.com"

        if q and q not in (title + " " + company + " " + " ".join(skills)).lower():
            continue

        offers.append(
            make_offer(
                source="NoFluffJobs",
                title=f"{sen_txt} {title}".strip(),
                company=company,
                location=", ".join(cities),
                remote=remote,
                salary=salary,
                url=offer_url,
                skills=[s for s in skills if s],
                description=p.get("category", ""),
                published=str(p.get("posted", "")),
            )
        )
        if len(offers) >= limit:
            break
    return offers
