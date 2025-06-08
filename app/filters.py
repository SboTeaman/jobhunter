"""Filtrowanie ofert wg lokalizacji, trybu zdalnego i minimalnych widełek."""
from __future__ import annotations

from .salary import to_monthly_pln


def apply_filters(
    offers: list[dict],
    *,
    remote_only: bool = False,
    location: str = "",
    salary_min: int = 0,
) -> list[dict]:
    """Filtruje listę ofert. Oferta bez porównywalnych widełek NIE jest odrzucana
    przez `salary_min` (brak danych != za mało)."""
    loc = location.strip().lower()
    out: list[dict] = []
    for o in offers:
        if remote_only and not o.get("remote"):
            continue
        if loc and loc not in (o.get("location", "") + " " + o.get("title", "")).lower():
            if not (o.get("remote") and loc in ("remote", "zdalnie", "zdalna")):
                continue
        if salary_min > 0:
            monthly = to_monthly_pln(o.get("salary", ""))
            if monthly is not None and monthly < salary_min:
                continue
        out.append(o)
    return out
