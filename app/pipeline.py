"""Wspólny pipeline wyszukiwania: fetch -> dedup -> filtry -> scoring -> luki.

Używany przez API (main.py) oraz watcher (watch.py), żeby logika była jedna.
"""
from __future__ import annotations

from . import insights, matcher
from .dedup import dedup_offers
from .filters import apply_filters
from .sources import fetch_all


async def run_search(
    profile: dict,
    sources: list[str],
    *,
    query: str = "",
    min_score: int = 0,
    remote_only: bool = False,
    location: str = "",
    salary_min: int = 0,
    limit: int = 60,
) -> dict:
    fetched = await fetch_all(sources, query=query, limit=limit)
    deduped = dedup_offers(fetched["offers"])
    filtered = apply_filters(
        deduped, remote_only=remote_only, location=location, salary_min=salary_min
    )
    ranked = matcher.rank_offers(filtered, profile, min_score=min_score)
    return {
        "offers": ranked,
        "errors": fetched["errors"],
        "skill_gaps": insights.skill_gaps(ranked),
        "total_fetched": len(fetched["offers"]),
        "total_after_dedup": len(deduped),
        "total_matched": len(ranked),
    }
