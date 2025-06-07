"""Normalizacja widełek do przybliżonej miesięcznej kwoty w PLN (do filtrowania).

UWAGA: kursy walut są przybliżone i zaszyte na stałe - służą tylko do
porównań przy filtrowaniu, nie do prezentacji dokładnych kwot.
"""
from __future__ import annotations

import re

# Przybliżone kursy (PLN za 1 jednostkę waluty).
_FX = {"PLN": 1.0, "EUR": 4.3, "USD": 4.0, "GBP": 5.0, "CHF": 4.5}
# Przelicznik jednostek na miesiąc.
_UNIT_MULT = {"/h": 168, "/dzień": 21, "/mc": 1, "": 1}

_RE = re.compile(
    r"(\d[\d\s]*)\s*-\s*(\d[\d\s]*)\s*([A-Z]{3})\s*(/h|/mc|/dzień)?",
)


def to_monthly_pln(salary: str) -> int | None:
    """Zwraca przybliżoną dolną granicę miesięcznych widełek w PLN albo None."""
    if not salary:
        return None
    m = _RE.search(salary)
    if not m:
        return None
    lo = int(m.group(1).replace(" ", ""))
    cur = m.group(3)
    unit = m.group(4) or ""
    fx = _FX.get(cur)
    if fx is None:
        return None
    return round(lo * fx * _UNIT_MULT.get(unit, 1))
