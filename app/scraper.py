"""Scrapowanie oferty z dowolnego URL.

Kolejność prób:
1. Wykryj portal po domenie → użyj dedykowanego parsera.
2. Fallback: ogólny scraper (JSON-LD / meta tagi / heurystyki z HTML).
"""
from __future__ import annotations

import json as _json_mod
import re
from urllib.parse import urlparse

from .sources.base import client, make_offer
from .sources import justjoin, nofluffjobs


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Niedozwolony schemat URL: {parsed.scheme!r}")
    hostname = (parsed.hostname or "").lower()
    blocked = ("localhost", "127.0.0.1", "::1", "0.0.0.0")
    if hostname in blocked or hostname.startswith(("192.168.", "10.", "172.16.", "169.254.")):
        raise ValueError("Niedozwolony adres wewnętrzny.")


def _extract_json_object(html: str, marker: str) -> dict | None:
    pos = html.find(marker)
    if pos == -1:
        return None
    brace_start = html.find("{", pos)
    if brace_start == -1:
        return None
    try:
        obj, _ = _json_mod.JSONDecoder().raw_decode(html, brace_start)
        return obj
    except (ValueError, KeyError):
        return None


async def offer_from_url(url: str) -> dict:
    """Pobiera i parsuje ofertę z podanego URL. Rzuca wyjątek gdy się nie uda."""
    url = url.strip()
    _validate_url(url)
    domain = _domain(url)

    async with client() as c:
        r = await c.get(url)
        if r.status_code != 200:
            raise ValueError(f"HTTP {r.status_code} dla {url}")
        html = r.text

    if "justjoin.it" in domain:
        return justjoin.parse_offer_html(html, url)

    if "nofluffjobs.com" in domain:
        return _parse_nofluff(html, url)

    if "remoteok.com" in domain:
        return _parse_remoteok(html, url)

    if "pracuj.pl" in domain or "theprotocol.it" in domain:
        return _parse_next_data(html, url, domain)

    return _generic_scrape(html, url)


def _domain(url: str) -> str:
    m = re.search(r"https?://([^/]+)", url)
    return m.group(1).lower() if m else ""


# --- Parsery per portal ---

def _parse_nofluff(html: str, url: str) -> dict:
    """NoFluffJobs: dane w __NEXT_DATA__."""
    data = _extract_json_object(html, '__NEXT_DATA__')
    if not data:
        return _generic_scrape(html, url)
    posting = _deep_find(data, ("posting", "jobOffer", "offer")) or {}
    title = posting.get("title") or ""
    company = posting.get("name") or posting.get("companyName") or ""
    skills = [t.get("value", "") for t in (posting.get("tiles", {}) or {}).get("values", []) if isinstance(t, dict)]
    sal = posting.get("salary", {}) or {}
    salary = f"{sal.get('from', '')}-{sal.get('to', '')} {sal.get('currency', 'PLN')}".strip("-  ")
    return make_offer(source="NoFluffJobs", title=title, company=company,
                      url=url, skills=skills, salary=salary,
                      description=posting.get("requirements", ""))


def _parse_remoteok(html: str, url: str) -> dict:
    """RemoteOK: JSON osadzony w stronie."""
    for pat in [r'<script type="application/json"[^>]*>(.*?)</script>',
                r'"job":\s*(\{.*?\})']:
        m = re.search(pat, html, re.DOTALL)
        if m:
            try:
                d = _json_mod.loads(m.group(1))
                if isinstance(d, list):
                    d = d[0] if d else {}
                tags = d.get("tags", [])
                return make_offer(
                    source="RemoteOK", title=d.get("position", ""),
                    company=d.get("company", ""), url=url, skills=tags,
                    remote=True, description=d.get("description", ""))
            except Exception:
                pass
    return _generic_scrape(html, url)


def _parse_next_data(html: str, url: str, domain: str) -> dict:
    """Parsuje __NEXT_DATA__ dla pracuj.pl / theprotocol."""
    data = _extract_json_object(html, '__NEXT_DATA__')
    if not data:
        return _generic_scrape(html, url)
    offer = _deep_find(data, ("offer", "jobOffer", "posting")) or {}
    title = offer.get("title") or offer.get("jobTitle") or ""
    company = offer.get("companyName") or offer.get("employer") or ""
    if isinstance(company, dict):
        company = company.get("name", "")
    source = "Pracuj.pl" if "pracuj" in domain else "TheProtocol"
    return make_offer(source=source, title=title, company=company, url=url,
                      description=title)


def _generic_scrape(html: str, url: str) -> dict:
    """Fallback: JSON-LD, meta OG, tytuł strony."""
    # JSON-LD (schema.org JobPosting)
    for m in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
                         html, re.DOTALL | re.IGNORECASE):
        try:
            d = _json_mod.loads(m.group(1))
            if isinstance(d, list):
                d = next((x for x in d if x.get("@type") == "JobPosting"), None) or {}
            if d.get("@type") == "JobPosting":
                sal_obj = d.get("baseSalary", {}) or {}
                sal_val = sal_obj.get("value", {}) or {}
                salary = ""
                if sal_val.get("minValue") and sal_val.get("maxValue"):
                    salary = f"{sal_val['minValue']}-{sal_val['maxValue']} {sal_val.get('currency', '')}"
                skills = d.get("skills", [])
                if isinstance(skills, str):
                    skills = [s.strip() for s in skills.split(",")]
                return make_offer(
                    source=_domain(url),
                    title=d.get("title", ""),
                    company=(d.get("hiringOrganization") or {}).get("name", "")
                            if isinstance(d.get("hiringOrganization"), dict)
                            else str(d.get("hiringOrganization", "")),
                    location=(d.get("jobLocation") or {}).get("address", {}).get("addressLocality", "")
                              if isinstance(d.get("jobLocation"), dict) else "",
                    salary=salary, url=url, skills=skills,
                    description=re.sub(r"<[^>]+>", " ", d.get("description", "")),
                )
        except Exception:
            pass

    # Meta OG fallback.
    def meta(prop: str) -> str:
        m2 = re.search(rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]+)"', html)
        return m2.group(1) if m2 else ""

    title = meta("og:title") or meta("twitter:title") or _page_title(html)
    desc = meta("og:description") or meta("description") or ""
    company = meta("og:site_name") or ""
    return make_offer(source=_domain(url), title=title, company=company,
                      url=url, description=desc)


def _page_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def _deep_find(data, keys: tuple, depth: int = 0):
    if depth > 8 or not isinstance(data, (dict, list)):
        return None
    if isinstance(data, dict):
        for k in keys:
            if k in data and isinstance(data[k], dict):
                return data[k]
        for v in data.values():
            found = _deep_find(v, keys, depth + 1)
            if found:
                return found
    elif isinstance(data, list):
        for v in data:
            found = _deep_find(v, keys, depth + 1)
            if found:
                return found
    return None
