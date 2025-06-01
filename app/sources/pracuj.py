"""Źródło: Pracuj.pl (best-effort - dane z osadzonego JSON na stronie wyników).

UWAGA: Pracuj.pl nie ma oficjalnego publicznego API i stosuje zabezpieczenia
anty-bot. Ten adapter próbuje wyciągnąć oferty z danych osadzonych w HTML
(window.__INITIAL_STATE__ / __NEXT_DATA__). Jeśli portal zmieni strukturę lub
zablokuje żądanie, adapter zwróci pustą listę (reszta narzędzia działa dalej).
"""
from __future__ import annotations

import json
import re

from .base import client, make_offer

SEARCH = "https://it.pracuj.pl/praca"


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    url = SEARCH
    if query:
        url = f"https://it.pracuj.pl/praca/{query.replace(' ', '%20')};kw"

    async with client() as c:
        try:
            r = await c.get(url)
            if r.status_code != 200:
                return []
            html = r.text
        except Exception:
            return []

    data = _extract_json(html)
    if not data:
        return []

    offers_raw = _find_offers(data)
    offers: list[dict] = []
    for it in offers_raw:
        title = it.get("jobTitle") or it.get("title") or ""
        company = it.get("companyName") or it.get("employer") or ""
        if not title:
            continue
        url_offer = it.get("offerAbsoluteUri") or it.get("url") or ""
        cities = it.get("offers", [{}])
        location = ""
        if isinstance(cities, list) and cities and isinstance(cities[0], dict):
            location = cities[0].get("displayWorkplace", "")
        salary = it.get("salaryDisplayText", "") or ""
        offers.append(
            make_offer(
                source="Pracuj.pl",
                title=title,
                company=company,
                location=location,
                remote="zdaln" in (location + title).lower(),
                salary=salary,
                url=url_offer,
                skills=it.get("technologies", []) if isinstance(it.get("technologies"), list) else [],
                description=title,
            )
        )
        if len(offers) >= limit:
            break
    return offers


def _extract_json(html: str) -> dict | None:
    for pattern in (
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        r'<script id="__NEXT_DATA__" type="application/json">(\{.*?\})</script>',
    ):
        m = re.search(pattern, html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                continue
    return None


def _find_offers(data, depth: int = 0) -> list[dict]:
    """Rekurencyjnie szuka listy ofert (klucze 'groupedOffers'/'offers')."""
    if depth > 8 or not isinstance(data, (dict, list)):
        return []
    if isinstance(data, dict):
        for key in ("groupedOffers", "offers", "jobOffers"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                if any(k in val[0] for k in ("jobTitle", "title", "offerAbsoluteUri")):
                    return val
        for v in data.values():
            found = _find_offers(v, depth + 1)
            if found:
                return found
    elif isinstance(data, list):
        for v in data:
            found = _find_offers(v, depth + 1)
            if found:
                return found
    return []
