"""Źródło: WeWorkRemotely (kanały RSS, oferty zdalne)."""
from __future__ import annotations

from bs4 import BeautifulSoup

from .base import client, make_offer

# Kategorie programistyczne / devops / sysadmin.
FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
]


async def fetch(query: str = "", limit: int = 60) -> list[dict]:
    q = query.lower()
    offers: list[dict] = []
    async with client() as c:
        for feed in FEEDS:
            try:
                r = await c.get(feed)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "xml")
            except Exception:
                continue

            for item in soup.find_all("item"):
                raw_title = item.title.text if item.title else ""
                # Format zwykle: "Company: Job Title"
                if ":" in raw_title:
                    company, _, title = raw_title.partition(":")
                else:
                    company, title = "", raw_title
                title = title.strip()
                company = company.strip()
                link = item.link.text if item.link else ""
                desc = item.description.text if item.description else ""

                if q and q not in raw_title.lower():
                    continue

                offers.append(
                    make_offer(
                        source="WeWorkRemotely",
                        title=title or raw_title,
                        company=company,
                        location="Remote",
                        remote=True,
                        url=link,
                        description=BeautifulSoup(desc, "html.parser").get_text(" "),
                        published=item.pubDate.text if item.pubDate else "",
                    )
                )
                if len(offers) >= limit:
                    return offers
    return offers
