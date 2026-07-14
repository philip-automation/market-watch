"""Forward fresh platform emails (Fiverr/Upwork/Freelancer) from Gmail to Telegram.

Env: GMAIL_USER, GMAIL_APP_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
State: state/mail_seen.json (processed Message-IDs)
"""
import email
import email.header
import imaplib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

USER = os.environ.get("GMAIL_USER", "")
PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
if not USER or not PASSWORD:
    print("mailwatch: no credentials, skipping")
    raise SystemExit(0)

STATE = Path("state")
SEEN_FILE = STATE / "mail_seen.json"
seen = set(json.loads(SEEN_FILE.read_text(encoding="utf-8"))) if SEEN_FILE.exists() else set()

SKIP_SUBJECT = re.compile(
    r"might interest you|recommended for you|jobs for you|projects matching|digest|newsletter|"
    r"weekly|tips for|webinar|promotion|% off|survey", re.I)

PLATFORMS = {
    "fiverr.com": "FIVERR",
    "upwork.com": "UPWORK",
    "freelancer.com": "FREELANCER",
}


def decode(s):
    if not s:
        return ""
    parts = email.header.decode_header(s)
    out = ""
    for text, enc in parts:
        out += text.decode(enc or "utf-8", "replace") if isinstance(text, bytes) else text
    return out


def body_snippet(msg, limit=350):
    def text_of(part):
        try:
            payload = part.get_payload(decode=True)
            return payload.decode(part.get_content_charset() or "utf-8", "replace")
        except Exception:
            return ""
    text = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                text = text_of(part)
                break
    else:
        text = text_of(msg)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def tg(text):
    Path("mailmsg.txt").write_text(text, encoding="utf-8")
    subprocess.run(["python3", "notify.py", "mailmsg.txt"], check=True)


def main():
    box = imaplib.IMAP4_SSL("imap.gmail.com")
    box.login(USER, PASSWORD)
    box.select("INBOX", readonly=True)
    since = (datetime.utcnow() - timedelta(days=2)).strftime("%d-%b-%Y")
    forwarded = 0
    for domain, label in PLATFORMS.items():
        ok, data = box.search(None, f'(SINCE "{since}" FROM "{domain}")')
        if ok != "OK" or not data or not data[0]:
            continue
        for num in data[0].split()[-15:]:
            ok, fetched = box.fetch(num, "(BODY.PEEK[])")
            if ok != "OK":
                continue
            msg = email.message_from_bytes(fetched[0][1])
            mid = msg.get("Message-ID", "").strip() or f"{label}-{num.decode()}"
            if mid in seen:
                continue
            seen.add(mid)
            subject = decode(msg.get("Subject"))
            if SKIP_SUBJECT.search(subject or ""):
                continue
            snippet = body_snippet(msg)
            esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            tg(f"📬 <b>{label}</b>\n<b>{esc(subject)}</b>\n{esc(snippet)}\n\n"
               f"Открой ноутбук и скажи Claude «проверь почту» - ответ будет готов.")
            forwarded += 1
            if forwarded >= 5:
                break
    box.logout()
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-3000:]), encoding="utf-8")
    print(f"mailwatch: forwarded {forwarded}")


if __name__ == "__main__":
    main()
