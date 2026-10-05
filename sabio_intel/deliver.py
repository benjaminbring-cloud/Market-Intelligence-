import os
import smtplib
import sys
from email.message import EmailMessage

from .config import OUTPUT_DIR


def send(to: str, subject: str, html: str, from_name: str, run_date: str, profile_key: str):
    """MI_TRANSPORT=smtp sends; anything else writes a preview file (safe default)."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    preview = OUTPUT_DIR / f"{run_date}_{profile_key}.html"
    preview.write_text(html)
    if os.environ.get("MI_TRANSPORT", "file") != "smtp":
        print(f"[deliver] preview written to {preview} (set MI_TRANSPORT=smtp to send)", file=sys.stderr)
        return
    user, pw = os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"]
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = f"{from_name} <{user}>", to, subject
    msg.set_content("Open in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        s.login(user, pw)
        s.send_message(msg)
    print(f"[deliver] sent to {to}", file=sys.stderr)
