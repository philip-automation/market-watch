"""Send a UTF-8 text file to Telegram. Usage: python3 notify.py <file>"""
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]
MAX = 4096


def send(text, parse_html=True):
    fields = {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}
    if parse_html:
        fields["parse_mode"] = "HTML"
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=urllib.parse.urlencode(fields).encode(),
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    text = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
    if not text:
        sys.exit("empty message file")
    for i in range(0, min(len(text), MAX * 3), MAX):
        chunk = text[i:i + MAX]
        try:
            send(chunk)
        except Exception:
            send(chunk, parse_html=False)
    print("sent")


if __name__ == "__main__":
    main()
