"""Analiza luk kompetencyjnych - czego douczyć się na podstawie ofert."""
from __future__ import annotations

from collections import Counter


def skill_gaps(ranked_offers: list[dict], top: int = 10) -> list[dict]:
    """Zlicza najczęściej brakujące technologie w dopasowanych ofertach.

    Zwraca listę {"skill": str, "count": int} posortowaną malejąco - to
    podpowiedź, czego nauczyć się, by pasować do większej liczby ofert.
    """
    counter: Counter[str] = Counter()
    for o in ranked_offers:
        for s in o.get("missing_skills", []):
            counter[s] += 1
    return [{"skill": s, "count": c} for s, c in counter.most_common(top)]
