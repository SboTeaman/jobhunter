"""Wysyłka powiadomień e-mail (opcjonalna - tylko gdy skonfigurowano SMTP)."""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText

from . import config


def email_configured() -> bool:
    return bool(config.SMTP_HOST and config.SMTP_USER and config.NOTIFY_EMAIL_TO)


def send_email(subject: str, body: str) -> bool:
    """Wysyła e-mail. Zwraca True przy sukcesie, False gdy brak konfiguracji/błąd."""
    if not email_configured():
        return False
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.SMTP_USER
    msg["To"] = config.NOTIFY_EMAIL_TO
    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as s:
            s.starttls()
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
            s.sendmail(config.SMTP_USER, [config.NOTIFY_EMAIL_TO], msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[notify] Nie udało się wysłać e-maila: {e}")
        return False


def format_offers(offers: list[dict]) -> str:
    lines = [f"Znaleziono {len(offers)} nowych dopasowanych ofert:\n"]
    for o in offers:
        lines.append(
            f"[{o.get('score', '?')}%] {o.get('title')} — {o.get('company')} "
            f"({o.get('source')})\n  {o.get('url')}"
        )
    return "\n".join(lines)
