"""Konfiguracja aplikacji - ładowana ze zmiennych środowiskowych / pliku .env."""
from __future__ import annotations

import os
from pathlib import Path

# Katalog na dane (profil CV, baza trackera).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tracker.db"
PROFILE_PATH = DATA_DIR / "profile.json"


def _load_dotenv() -> None:
    """Bardzo prosty loader .env (bez zewnętrznej zależności)."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-4-6").strip()

# Powiadomienia e-mail (opcjonalne) - używane przez watch.py.
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587") or "587")
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
NOTIFY_EMAIL_TO = os.environ.get("NOTIFY_EMAIL_TO", "").strip()

# Pliki używane przez watcher.
WATCH_CONFIG_PATH = DATA_DIR / "watch.json"
SEEN_PATH = DATA_DIR / "seen.json"
NEW_OFFERS_LOG = DATA_DIR / "new_offers.log"

# Domyślny User-Agent dla zapytań HTTP (część portali blokuje brak UA).
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 JobHunter/1.0"
)

HTTP_TIMEOUT = 20.0

MAX_CV_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
ALLOWED_CV_EXTENSIONS: frozenset = frozenset({".pdf", ".docx", ".txt", ".md"})
CV_TEXT_MAX_CHARS: int = int(os.environ.get("CV_TEXT_MAX_CHARS", "20000"))
