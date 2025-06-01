"""Rejestr źródeł ofert pracy + równoległe pobieranie."""
from __future__ import annotations

import asyncio

from . import justjoin, nofluffjobs, remoteok, weworkremotely, pracuj, theprotocol

# Klucz -> (etykieta, funkcja fetch async)
SOURCES = {
    "justjoin": ("JustJoin.it", justjoin.fetch),
    "nofluffjobs": ("NoFluffJobs", nofluffjobs.fetch),
    "remoteok": ("RemoteOK", remoteok.fetch),
    "weworkremotely": ("WeWorkRemotely", weworkremotely.fetch),
    "pracuj": ("Pracuj.pl", pracuj.fetch),
    "theprotocol": ("TheProtocol", theprotocol.fetch),
}


async def fetch_all(keys: list[str], query: str = "", limit: int = 60) -> dict:
    """Pobiera oferty z wybranych źródeł równolegle.

    Zwraca: {"offers": [...], "errors": {źródło: komunikat}}
    """
    keys = [k for k in keys if k in SOURCES]
    tasks = [SOURCES[k][1](query=query, limit=limit) for k in keys]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    offers: list[dict] = []
    errors: dict[str, str] = {}
    for key, res in zip(keys, results):
        label = SOURCES[key][0]
        if isinstance(res, Exception):
            errors[label] = str(res) or res.__class__.__name__
        else:
            offers.extend(res)
    return {"offers": offers, "errors": errors}
