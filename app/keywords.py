"""Pełna analiza słów kluczowych oferty vs CV.

W przeciwieństwie do app/skills.py (słownik ~120 technologii), ten moduł wyciąga
WSZYSTKIE istotne słowa kluczowe z tekstu oferty (rzeczowniki, frazy techniczne,
certyfikaty, metodyki) i sprawdza pokrycie w CV — podobnie jak Jobscan.
"""
from __future__ import annotations

import re
from collections import Counter

# Stopwords PL + EN (najczęstsze słowa bez wartości informacyjnej).
_STOP = {
    # EN
    "a","an","the","and","or","but","in","on","at","to","for","of","with","by",
    "from","as","is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall",
    "not","no","nor","so","yet","both","either","each","few","more","most",
    "other","some","such","than","then","that","this","these","those","what",
    "which","who","whom","whose","when","where","why","how","all","any","both",
    "can","its","our","your","their","we","you","they","he","she","it","i",
    "us","me","him","her","them","my","his","her","its","our","your","their",
    "up","out","if","about","into","through","during","before","after","above",
    "below","between","under","again","further","once","here","there","only",
    "own","same","too","very","just","also","well","new","good","great","high",
    "strong","good","fast","large","small","based","using","working","within",
    "across","without","including","team","role","experience","work","job","you",
    "will","must","able","proven","track","record","looking","join","help","make",
    # PL
    "i","w","z","na","do","się","nie","to","że","jak","co","jest","są","was",
    "dla","po","przy","o","być","ze","ale","już","więcej","może","przez","jego",
    "jej","ich","nam","nasz","nasza","nasze","który","która","które","oraz",
    "czy","też","tego","tej","tej","to","ta","ten","jako","więc","bardzo","nowe",
    "swojej","swoich","swoje","swojego","pracy","doświadczenie","wiedza","znajomość",
    "umiejętności","mile","widziane","wymagania","oferujemy","poszukujemy","dołącz",
}

# Minimalna długość słowa kluczowego.
_MIN_LEN = 3


def extract_keywords(text: str) -> list[str]:
    """Wyciąga unikalne słowa kluczowe z tekstu oferty (bez stopwords)."""
    if not text:
        return []
    # Tokeny: słowa, cyfry+litery (np. "5G", "HTTP/2"), frazy z ukośnikiem.
    tokens = re.findall(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9][a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9+#./\-]*", text)
    seen: dict[str, str] = {}  # lower -> original (zachowaj oryginalną pisownię)
    for tok in tokens:
        if len(tok) < _MIN_LEN:
            continue
        low = tok.lower().strip("-./")
        if low in _STOP:
            continue
        # Preferuj wersję z wielką literą (np. "Python" nad "python").
        if low not in seen or tok[0].isupper():
            seen[low] = tok
    return list(seen.values())


def keyword_coverage(offer_text: str, cv_text: str) -> dict:
    """Zwraca:
      - matched: słowa z oferty obecne w CV
      - missing: słowa z oferty nieobecne w CV
      - score: % pokrycia (0-100)
    """
    offer_kws = extract_keywords(offer_text)
    if not offer_kws:
        return {"matched": [], "missing": [], "score": 0, "total": 0}

    cv_lower = cv_text.lower()
    matched, missing = [], []
    for kw in offer_kws:
        if re.search(r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)", cv_lower):
            matched.append(kw)
        else:
            missing.append(kw)

    score = round(len(matched) / len(offer_kws) * 100)
    return {
        "matched": matched,
        "missing": missing,
        "score": score,
        "total": len(offer_kws),
    }


def top_missing(missing: list[str], n: int = 15) -> list[str]:
    """Zwraca najważniejsze brakujące słowa kluczowe — krótsze sortuje wyżej
    (pojedyncze słowa techniczne są ważniejsze niż ogólne frazy)."""
    # Krótsze tokeny z wielkiej litery traktujemy jako ważniejsze (nazwy własne).
    def priority(w: str) -> tuple:
        return (0 if w[0].isupper() else 1, len(w))
    return sorted(missing, key=priority)[:n]
