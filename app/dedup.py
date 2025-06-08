"""Deduplikacja ofert występujących na wielu portalach / w wielu miastach."""
from __future__ import annotations

import re


def _norm(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\(.*?\)", " ", text)  # usuń nawiasy
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _key(offer: dict) -> str:
    """Klucz tożsamości oferty: firma + tytuł (bez miasta/znaków)."""
    title = _norm(offer.get("title", ""))
    company = _norm(offer.get("company", ""))
    return f"{company}|{title}"


def dedup_offers(offers: list[dict]) -> list[dict]:
    """Scala duplikaty. Zachowuje pierwsze wystąpienie, ale zbiera wszystkie
    źródła (pole `sources`) oraz najbogatszy zestaw skilli i widełki."""
    merged: dict[str, dict] = {}
    order: list[str] = []
    for o in offers:
        key = _key(o)
        # Oferty bez tytułu lub bez firmy traktujemy jako unikalne (po URL).
        if not o.get("title") or not o.get("company"):
            key = "uniq|" + o.get("id", o.get("url", ""))
        if key not in merged:
            base = dict(o)
            base["sources"] = [o.get("source", "")]
            base["urls"] = {o.get("source", ""): o.get("url", "")}
            merged[key] = base
            order.append(key)
        else:
            ex = merged[key]
            src = o.get("source", "")
            if src and src not in ex["sources"]:
                ex["sources"].append(src)
                ex["urls"][src] = o.get("url", "")
            # Uzupełnij brakujące dane z duplikatu.
            if not ex.get("salary") and o.get("salary"):
                ex["salary"] = o["salary"]
            if len(o.get("skills", [])) > len(ex.get("skills", [])):
                ex["skills"] = o["skills"]
            ex["remote"] = ex.get("remote") or o.get("remote")
    return [merged[k] for k in order]
