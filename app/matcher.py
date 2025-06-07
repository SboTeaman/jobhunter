"""Dopasowanie i scoring ofert względem profilu CV (logika lokalna, bez AI)."""
from __future__ import annotations

from . import keywords as kw_mod
from . import skills as skills_mod


def _offer_skills(offer: dict) -> set[str]:
    """Skille oferty: te podane przez portal + wykryte w opisie/tytule."""
    explicit = {s for s in offer.get("skills", []) if s}
    # Niektóre portale dają skille jako wolny tekst - znormalizuj przez słownik.
    text = " ".join(
        [offer.get("title", ""), offer.get("description", ""), " ".join(explicit)]
    )
    detected = skills_mod.extract_skills(text)
    return detected | skills_mod.extract_skills(" ".join(explicit))


def _seniority_of_offer(offer: dict) -> int | None:
    text = (offer.get("title", "") + " " + offer.get("seniority", "")).lower()
    best = None
    for kw, level in skills_mod.SENIORITY_KEYWORDS.items():
        if kw in text:
            best = level if best is None else max(best, level)
    return best


def score_offer(offer: dict, profile: dict) -> dict:
    """Liczy wynik dopasowania 0-100 + rozbija na czynniki i braki."""
    profile_skills = set(profile.get("skills", []))
    off_skills = _offer_skills(offer)

    matched = sorted(off_skills & profile_skills)
    missing = sorted(off_skills - profile_skills)

    # Pokrycie wymaganych technologii (główny czynnik).
    if off_skills:
        coverage = len(matched) / len(off_skills)
    else:
        coverage = 0.0
    skill_points = coverage * 70  # max 70 pkt

    # Bonus za liczbę dopasowanych skilli (nagradza bogate dopasowania).
    overlap_points = min(len(matched), 10) / 10 * 15  # max 15 pkt

    # Dopasowanie seniority (max 15 pkt).
    off_sen = _seniority_of_offer(offer)
    my_sen = profile.get("seniority", 1)
    if off_sen is None:
        seniority_points = 10  # brak informacji - neutralnie
    else:
        diff = abs(off_sen - my_sen)
        seniority_points = max(0, 15 - diff * 6)

    score = round(skill_points + overlap_points + seniority_points)
    score = max(0, min(100, score))

    # Pełna analiza słów kluczowych (wszystkie słowa z opisu, nie tylko słownik).
    offer_full_text = " ".join([
        offer.get("title", ""), offer.get("description", ""),
        " ".join(offer.get("skills", [])),
    ])
    cv_text = profile.get("text", "")
    kw_result = kw_mod.keyword_coverage(offer_full_text, cv_text)

    return {
        **offer,
        "score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "offer_skills": sorted(off_skills),
        "kw_matched": kw_result["matched"],
        "kw_missing": kw_mod.top_missing(kw_result["missing"]),
        "kw_score": kw_result["score"],
        "_factors": {
            "coverage": round(coverage * 100),
            "matched_count": len(matched),
            "offer_seniority": off_sen,
            "kw_coverage": kw_result["score"],
        },
    }


def rank_offers(offers: list[dict], profile: dict, min_score: int = 0) -> list[dict]:
    scored = [score_offer(o, profile) for o in offers]
    scored = [o for o in scored if o["score"] >= min_score]
    scored.sort(key=lambda o: o["score"], reverse=True)
    return scored
