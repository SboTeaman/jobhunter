"""Watcher nowych ofert.

Wczytuje zapisany profil CV (data/profile.json) oraz konfigurację wyszukiwania
(data/watch.json), uruchamia wyszukiwanie i raportuje TYLKO nowe oferty
(porównanie z data/seen.json). Nowe oferty trafiają do data/new_offers.log,
a jeśli skonfigurowano SMTP - również na e-mail.

Uruchamianie ręczne:
    python watch.py

Cykliczne (Windows, np. co godzinę) - Harmonogram zadań:
    Program:  C:\\...\\jobhunter\\.venv\\Scripts\\python.exe
    Argumenty: watch.py
    Rozpocznij w: C:\\...\\jobhunter

Przykładowy data/watch.json:
{
  "sources": ["justjoin", "nofluffjobs", "remoteok"],
  "query": "python",
  "min_score": 50,
  "remote_only": true,
  "location": "",
  "salary_min": 15000,
  "limit": 60
}
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

from app import config, notify, pipeline

DEFAULT_WATCH = {
    "sources": ["justjoin", "nofluffjobs", "remoteok", "weworkremotely"],
    "query": "",
    "min_score": 50,
    "remote_only": False,
    "location": "",
    "salary_min": 0,
    "limit": 60,
}


def _load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


async def main() -> None:
    profile = _load_json(config.PROFILE_PATH, None)
    if not profile:
        print("Brak profilu CV (data/profile.json). Wgraj CV w aplikacji webowej.")
        return

    watch = _load_json(config.WATCH_CONFIG_PATH, DEFAULT_WATCH)
    seen = set(_load_json(config.SEEN_PATH, []))

    result = await pipeline.run_search(
        profile,
        watch.get("sources", DEFAULT_WATCH["sources"]),
        query=watch.get("query", ""),
        min_score=watch.get("min_score", 50),
        remote_only=watch.get("remote_only", False),
        location=watch.get("location", ""),
        salary_min=watch.get("salary_min", 0),
        limit=watch.get("limit", 60),
    )

    new_offers = [o for o in result["offers"] if o["id"] not in seen]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not new_offers:
        print(f"[{ts}] Brak nowych ofert (sprawdzono {result['total_matched']} dopasowanych).")
    else:
        print(f"[{ts}] Nowych ofert: {len(new_offers)}")
        with config.NEW_OFFERS_LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {ts} - {len(new_offers)} nowych ===\n")
            f.write(notify.format_offers(new_offers) + "\n")
        if notify.email_configured():
            sent = notify.send_email(
                f"JobHunter: {len(new_offers)} nowych ofert", notify.format_offers(new_offers)
            )
            print("  E-mail wysłany." if sent else "  E-mail NIE wysłany.")
        else:
            print("  (SMTP nieskonfigurowany - tylko zapis do new_offers.log)")

    # Zaktualizuj zbiór widzianych ofert.
    all_ids = sorted(seen | {o["id"] for o in result["offers"]})
    config.SEEN_PATH.write_text(json.dumps(all_ids), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
