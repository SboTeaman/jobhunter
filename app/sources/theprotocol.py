"""Źródło: TheProtocol.it (best-effort - dane z __NEXT_DATA__).

UWAGA: jak Pracuj.pl - brak oficjalnego API, możliwe blokady anty-bot.
Adapter próbuje sparsować dane Next.js osadzone w stronie; przy niepowodzeniu
zwraca pustą listę.
"""
from __future__ import annotations

import json
import re

from .base import client, make_offer

SEARCH = "https://theprotocol.it/filtry/ai;sp"  # ogólny widok ofert


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    url = "https://theprotocol.it/praca"
    if query:
        url = f"https://theprotocol.it/szukaj/{query.replace(' ', '-')}"

    async with client() as c:
        try:
            r = await c.get(url)
            if r.status_code != 200:
                return []
            html = r.text
        except Exception:
            return []

    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(\{.*?\})</script>',
        html,
        re.DOTALL,
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except Exception:
        return []

    offers_raw = _find_offers(data)
    offers: list[dict] = []
    for it in offers_raw:
        title = it.get("title") or it.get("jobTitle") or ""
        if not title:
            continue
        company = it.get("employer") or it.get("companyName") or ""
        if isinstance(company, dict):
            company = company.get("name", "")
        url_offer = it.get("offerUrl") or it.get("url") or ""
        if url_offer and url_offer.startswith("/"):
            url_offer = "https://theprotocol.it" + url_offer
        wp = it.get("workplaces", []) or it.get("workModes", [])
        location = ", ".join(
            w.get("city", "") if isinstance(w, dict) else str(w) for w in wp
        ) if isinstance(wp, list) else ""
        techs = it.get("technologies", []) or it.get("requiredSkills", [])
        if isinstance(techs, list):
            techs = [t.get("name", "") if isinstance(t, dict) else str(t) for t in techs]
        else:
            techs = []
        offers.append(
            make_offer(
                source="TheProtocol",
                title=title,
                company=company,
                location=location,
                remote="zdaln" in (location + " " + json.dumps(wp, ensure_ascii=False)).lower(),
                url=url_offer,
                skills=[t for t in techs if t],
                description=title,
            )
        )
        if len(offers) >= limit:
            break
    return offers


def _find_offers(data, depth: int = 0) -> list[dict]:
    if depth > 9 or not isinstance(data, (dict, list)):
        return []
    if isinstance(data, dict):
        for key in ("offers", "jobOffers", "items", "data"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                if any(k in val[0] for k in ("title", "jobTitle", "offerUrl")):
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
