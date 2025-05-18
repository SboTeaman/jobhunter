# 🎯 JobHunter — wyszukiwarka ofert pracy IT dopasowanych do CV

Narzędzie webowe (działa lokalnie w przeglądarce): **wgrywasz CV → dostajesz listę
ofert IT posortowaną wg dopasowania → narzędzie pomaga aplikować** (generuje list
motywacyjny i prowadzi tracker aplikacji).

## Jak to działa

1. **Wgrywasz CV** (PDF / DOCX / TXT). Narzędzie wyciąga z niego technologie,
   poziom (junior/mid/senior…) i lata doświadczenia.
2. **Pobiera oferty** z wybranych portali równolegle.
3. **Dopasowuje i scoruje** każdą ofertę (0–100%) na podstawie pokrycia
   wymaganych technologii, seniority i innych czynników — z listą
   ✅ dopasowanych i ❌ brakujących umiejętności.
4. **Pomaga aplikować**: dla wybranej oferty generuje list motywacyjny
   (AI Claude jeśli masz klucz, inaczej z szablonu) i zapisuje aplikację
   w trackerze ze statusami (zapisana → wysłana → rozmowa → oferta/odrzucona).

## Źródła ofert

| Portal | Sposób | Niezawodność |
|---|---|---|
| JustJoin.it | publiczne API JSON | wysoka |
| NoFluffJobs | publiczne API | wysoka |
| RemoteOK | publiczne API JSON | wysoka |
| WeWorkRemotely | kanały RSS | wysoka |
| Pracuj.pl | scraping osadzonego JSON | **niska** (zabezpieczenia anty-bot) |
| TheProtocol | scraping `__NEXT_DATA__` | **niska** (zabezpieczenia anty-bot) |

> Pracuj.pl i TheProtocol nie mają publicznego API i mogą blokować automatyczne
> żądania — jeśli zwrócą 0 ofert, to normalne; pozostałe źródła działają dalej.
> Używaj zgodnie z regulaminami portali.

## Instalacja i uruchomienie (Windows / PowerShell)

```powershell
cd C:\Users\sbote\Desktop\scalper\jobhunter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Otwórz w przeglądarce: **http://127.0.0.1:8000**

## AI (opcjonalnie, tryb hybrydowy)

Dopasowanie ofert działa **lokalnie i za darmo**. AI (Claude) służy tylko do
pisania listów motywacyjnych. Aby włączyć:

```powershell
copy .env.example .env
# wpisz w .env swój ANTHROPIC_API_KEY
```

Bez klucza listy generowane są z szablonu (przełącznik „Użyj AI" w oknie aplikacji).

## Struktura

```
jobhunter/
├── run.py                 # start serwera
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py            # FastAPI: API + serwowanie UI
│   ├── config.py
│   ├── cv_parser.py       # CV (PDF/DOCX/TXT) -> profil
│   ├── skills.py          # słownik ~120 technologii IT
│   ├── matcher.py         # scoring ofert względem CV
│   ├── apply.py           # generowanie listu (szablon + Claude)
│   ├── db.py              # tracker aplikacji (SQLite)
│   └── sources/           # adaptery portali (1 plik = 1 portal)
└── static/                # interfejs webowy (HTML/CSS/JS)
```

## Pomysły na rozwój

- Filtr po widełkach / lokalizacji / trybie zdalnym.
- Eksport aplikacji do CSV.
- Powiadomienia o nowych ofertach (cron + e-mail).
- Sugestie „czego douczyć się" na podstawie najczęstszych brakujących skilli.
- Wykrywanie duplikatów tej samej oferty z różnych portali.
