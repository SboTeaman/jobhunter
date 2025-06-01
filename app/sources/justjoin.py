"""Źródło: JustJoin.it.

JustJoin zablokował dawne API JSON, ale:
  1. listę aktywnych ofert publikuje w oficjalnym sitemap (z robots.txt),
  2. każda strona oferty zawiera pełne dane (firma, technologie, widełki, lokalizacja)
     osadzone w strumieniu RSC Next.js (`self.__next_f`).

Adapter pobiera URL-e z sitemap, filtruje po słowie kluczowym (na slugu),
a następnie równolegle dociąga szczegóły z poszczególnych stron i parsuje je
funkcją `parse_offer_html` (czysta -> łatwa do testów jednostkowych).
"""
from __future__ import annotations

import asyncio
import re

from bs4 import BeautifulSoup

from .base import client, make_offer

SITEMAP_INDEX = "https://justjoin.it/sitemaps/active-jobs.xml"
DETAIL_CONCURRENCY = 8

_CITIES = {
    "warszawa", "krakow", "wroclaw", "poznan", "gdansk", "gdynia", "lodz",
    "katowice", "szczecin", "lublin", "bialystok", "remote", "poland",
    "rzeszow", "bydgoszcz", "gliwice", "sopot", "torun", "olsztyn",
}


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    async with client() as c:
        urls = await _collect_urls(c, query=query, want=limit)
        if not urls:
            return []

        sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

        async def one(url: str) -> dict:
            async with sem:
                try:
                    r = await c.get(url)
                    if r.status_code == 200:
                        return parse_offer_html(r.text, url)
                except Exception:
                    pass
                return _fallback_offer(url)  # gdy szczegóły niedostępne

        results = await asyncio.gather(*(one(u) for u in urls[:limit]))
    return [o for o in results if o]


async def _collect_urls(c, query: str, want: int) -> list[str]:
    """Zbiera URL-e ofert z sitemap, filtrując po słowie kluczowym na slugu."""
    try:
        idx = await c.get(SITEMAP_INDEX)
        if idx.status_code != 200:
            return []
        parts = [loc.text for loc in BeautifulSoup(idx.text, "xml").find_all("loc")]
    except Exception:
        return []

    q = query.lower()
    urls: list[str] = []
    for part in parts:
        try:
            r = await c.get(part)
        except Exception:
            continue
        if r.status_code != 200:
            continue
        for loc in BeautifulSoup(r.text, "xml").find_all("loc"):
            url = loc.text
            if "/job-offer/" not in url:
                continue
            if q and q not in url.lower():
                continue
            urls.append(url)
        if len(urls) >= want:
            break
    return urls


def parse_offer_html(html: str, url: str) -> dict:
    """Parsuje stronę oferty JustJoin -> znormalizowana oferta.

    Dane są w strumieniu RSC jako podwójnie zaescape'owany JSON, więc czytamy je
    celowanymi regexami. Czysta funkcja: bez I/O (testowalna na zapisanym HTML).
    """
    slug = _slug(url)
    company = _search(r'\\"companyName\\":\\"([^"\\]+)\\"', html)
    city = _search(r'\\"city\\":\\"([^"\\]+)\\"', html)

    workplace = _search(r'\\"workplaceType\\":\{\\"label\\":\\"([^"\\]+)\\"', html) or ""
    remote = "remote" in workplace.lower() or "remote" in slug.lower()

    skills = _required_skills(html)
    salary = _salary(html)
    title = _title(slug, company, skills)

    return make_offer(
        source="JustJoin.it",
        title=title,
        company=company,
        location=city or _city_from_slug(slug),
        remote=remote,
        salary=salary,
        url=url,
        skills=skills,
        description=(slug.replace("-", " ") + " " + " ".join(skills)),
    )


def _fallback_offer(url: str) -> dict:
    """Gdy nie udało się pobrać szczegółów - oferta na podstawie samego sluga."""
    slug = _slug(url)
    return make_offer(
        source="JustJoin.it",
        title=_title(slug, ""),
        company="",
        location=_city_from_slug(slug),
        remote="remote" in slug.lower(),
        url=url,
        description=slug.replace("-", " "),
    )


# obie ścieżki (parse + fallback) korzystają z _title


# --- helpery parsujące (czyste) ---
def _slug(url: str) -> str:
    return url.rsplit("/job-offer/", 1)[-1] if "/job-offer/" in url else url


def _search(pattern: str, html: str) -> str:
    m = re.search(pattern, html)
    return m.group(1) if m else ""


def _required_skills(html: str) -> list[str]:
    m = re.search(r'\\"requiredSkills\\":\[(.*?)\]', html)
    if not m:
        return []
    names = re.findall(r'\\"name\\":\\"([^"\\]+)\\"', m.group(1))
    return list(dict.fromkeys(names))  # unikalne, zachowując kolejność


def _salary(html: str) -> str:
    """Zwraca widełki, preferując oryginalną walutę PLN (z jednostką)."""
    entries = re.findall(
        r'\\"currency\\":\\"([A-Z]{3})\\",\\"from\\":([0-9.]+),'
        r'.*?\\"to\\":([0-9.]+),.*?\\"unit\\":\\"(\w+)\\"',
        html,
    )
    if not entries:
        return ""
    chosen = next((e for e in entries if e[0] == "PLN"), entries[0])
    cur, lo, hi, unit = chosen
    lo_n, hi_n = round(float(lo)), round(float(hi))
    unit_pl = {"hour": "/h", "month": "/mc", "day": "/dzień"}.get(unit, "")
    return f"{lo_n}-{hi_n} {cur}{unit_pl}"


def _title(slug: str, company: str, skills: list[str] | None = None) -> str:
    words = [w for w in slug.split("-") if w]
    # Slugi mają doklejone na końcu miasto i/lub pojedynczą technologię - obcinamy.
    skill_tokens = {s.split()[0].lower() for s in (skills or [])}
    while words and (words[-1].lower() in _CITIES or words[-1].lower() in skill_tokens):
        words.pop()
    title = " ".join(words)
    # Usuń nazwę firmy z początku tytułu (slug zaczyna się od firmy).
    if company:
        comp_norm = re.sub(r"[^a-z0-9 ]", "", company.lower())
        title_norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
        if title_norm.startswith(comp_norm):
            title = title[len(company):].strip(" -")
    return " ".join(w.capitalize() for w in title.split()) or slug


def _city_from_slug(slug: str) -> str:
    for w in reversed(slug.split("-")):
        if w.lower() in _CITIES:
            return w.capitalize()
    return ""
