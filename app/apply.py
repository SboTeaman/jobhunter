"""Pomoc w aplikowaniu: generowanie listu motywacyjnego (szablon + opcjonalnie AI)."""
from __future__ import annotations

import json as _json
import logging
from typing import TYPE_CHECKING

from . import config
from .cv_parser import SENIORITY_LABELS

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic

_anthropic_client: AsyncAnthropic | None = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic_client


def _template_letter(offer: dict, profile: dict) -> str:
    """List z szablonu - działa zawsze, bez AI."""
    matched = offer.get("matched_skills", [])
    company = offer.get("company") or "Państwa firmy"
    title = offer.get("title") or "oferowane stanowisko"
    sen = SENIORITY_LABELS.get(profile.get("seniority", 1), "")
    years = profile.get("years", 0)

    exp = f"{years} lat doświadczenia" if years else "doświadczenie komercyjne"
    skills_line = ", ".join(matched[:8]) if matched else ", ".join(profile.get("skills", [])[:8])

    return (
        f"Szanowni Państwo,\n\n"
        f"piszę w odpowiedzi na ofertę pracy na stanowisko {title} w {company}. "
        f"Jako {sen.lower()} programista z {exp} jestem przekonany, że moje "
        f"kompetencje dobrze odpowiadają Państwa wymaganiom.\n\n"
        f"W szczególności posługuję się technologiami istotnymi w tej roli: "
        f"{skills_line}. W dotychczasowej pracy wykorzystywałem je do "
        f"projektowania i utrzymania rozwiązań produkcyjnych, dbając o jakość "
        f"kodu i współpracę w zespole.\n\n"
        f"Chętnie opowiem więcej o moim doświadczeniu podczas rozmowy. "
        f"Dziękuję za poświęcony czas i pozostaję do dyspozycji.\n\n"
        f"Z poważaniem"
    )


async def generate_cover_letter(offer: dict, profile: dict, use_ai: bool = True) -> dict:
    """Zwraca {'letter': str, 'mode': 'ai'|'template', 'note': str}."""
    if use_ai and config.ANTHROPIC_API_KEY:
        try:
            letter = await _ai_letter(offer, profile)
            return {"letter": letter, "mode": "ai", "note": f"Wygenerowano przez {config.AI_MODEL}"}
        except Exception as e:  # noqa: BLE001
            tmpl = _template_letter(offer, profile)
            return {
                "letter": tmpl,
                "mode": "template",
                "note": f"AI niedostępne ({e}). Użyto szablonu.",
            }
    note = "Brak ANTHROPIC_API_KEY - użyto szablonu." if use_ai else "Tryb szablonu."
    return {"letter": _template_letter(offer, profile), "mode": "template", "note": note}


async def suggest_cv_improvements(offer: dict, profile: dict) -> dict:
    """Zwraca konkretne sugestie jak dostosować CV do tej oferty."""
    if not config.ANTHROPIC_API_KEY:
        return {"suggestions": _template_suggestions(offer, profile), "mode": "template"}
    try:
        suggestions = await _ai_suggestions(offer, profile)
        return {"suggestions": suggestions, "mode": "ai"}
    except Exception as e:
        return {"suggestions": _template_suggestions(offer, profile),
                "mode": "template", "note": str(e)}


def _template_suggestions(offer: dict, profile: dict) -> list[dict]:
    missing = offer.get("missing_skills", [])
    kw_missing = offer.get("kw_missing", [])[:8]
    suggestions = []
    if missing:
        suggestions.append({
            "priority": "high",
            "category": "Brakujące technologie",
            "action": f"Dodaj do sekcji Umiejętności: {', '.join(missing[:6])}. "
                      f"Jeśli masz z nimi jakiekolwiek doświadczenie, nawet poboczne, wymień je.",
        })
    if kw_missing:
        suggestions.append({
            "priority": "medium",
            "category": "Brakujące słowa kluczowe",
            "action": f"Użyj w opisach stanowisk słów: {', '.join(kw_missing[:6])}. "
                      f"ATS wyszukuje dokładne dopasowania fraz.",
        })
    off_sen = offer.get("_factors", {}).get("offer_seniority")
    my_sen = profile.get("seniority", 1)
    if off_sen is not None and off_sen > my_sen:
        suggestions.append({
            "priority": "medium",
            "category": "Poziom doświadczenia",
            "action": "Oferta oczekuje wyższego seniority niż Twoje CV sugeruje. "
                      "Podkreśl samodzielność, mentoring innych, decyzje architektoniczne.",
        })
    if not suggestions:
        suggestions.append({
            "priority": "low",
            "category": "Dobry match",
            "action": "CV dobrze pasuje do tej oferty. Upewnij się że tytuł stanowiska "
                      "w CV brzmi podobnie do tytułu w ofercie.",
        })
    return suggestions


def _parse_claude_json_array(raw: str, fallback):
    logger = logging.getLogger(__name__)
    try:
        decoder = _json.JSONDecoder()
        start = raw.index("[")
        result, _ = decoder.raw_decode(raw, start)
        if isinstance(result, list):
            return result
    except (ValueError, KeyError):
        logger.warning("Claude nie zwrócił poprawnego JSON array. Raw: %.200s", raw)
    return fallback


async def _ai_suggestions(offer: dict, profile: dict) -> list[dict]:
    client = _get_anthropic_client()
    prompt = (
        f"Jesteś ekspertem od rekrutacji IT. Przeanalizuj CV kandydata i ofertę pracy. "
        f"Podaj 4-6 konkretnych, zwięzłych sugestii jak zmodyfikować CV, by lepiej pasowało do tej oferty. "
        f"Każda sugestia: priority (high/medium/low), category (krótka nazwa), action (konkretny krok).\n"
        f"Odpowiedz TYLKO jako JSON array: [{{'priority':'...','category':'...','action':'...'}},...]\n\n"
        f"OFERTA: {offer.get('title')} @ {offer.get('company')}\n"
        f"Wymagane tech: {', '.join(offer.get('offer_skills', []))}\n"
        f"Brakujące w CV: {', '.join(offer.get('missing_skills', []))}\n"
        f"Brakujące słowa kluczowe: {', '.join(offer.get('kw_missing', [])[:10])}\n"
        f"Opis oferty: {offer.get('description', '')[:1000]}\n\n"
        f"CV (fragment): {profile.get('text', '')[:3000]}"
    )
    resp = await client.messages.create(
        model=config.AI_MODEL,
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
        timeout=30.0,
    )
    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return _parse_claude_json_array(raw, _template_suggestions(offer, profile))


async def _ai_letter(offer: dict, profile: dict) -> str:
    client = _get_anthropic_client()
    lang = profile.get("language", "pl")
    cv_excerpt = profile.get("text", "")[:6000]

    prompt = (
        f"Jesteś ekspertem od rekrutacji IT. Napisz zwięzły, konkretny i naturalny "
        f"list motywacyjny ({'po polsku' if lang == 'pl' else 'in English'}) "
        f"dopasowany do poniższej oferty i CV kandydata. "
        f"Maksymalnie 200 słów. Bez przesady i pustych frazesów, podkreśl realne "
        f"dopasowanie technologii. Nie wymyślaj doświadczeń, których nie ma w CV.\n\n"
        f"=== OFERTA ===\n"
        f"Stanowisko: {offer.get('title')}\n"
        f"Firma: {offer.get('company')}\n"
        f"Wymagane technologie: {', '.join(offer.get('offer_skills', []))}\n"
        f"Dopasowane do kandydata: {', '.join(offer.get('matched_skills', []))}\n"
        f"Opis: {offer.get('description', '')[:1500]}\n\n"
        f"=== CV KANDYDATA (fragment) ===\n{cv_excerpt}\n\n"
        f"Zwróć wyłącznie treść listu."
    )

    resp = await client.messages.create(
        model=config.AI_MODEL,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
        timeout=30.0,
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
