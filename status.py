"""Daily heartbeat: send pipeline stats to Telegram."""
import datetime
import os
import subprocess
from pathlib import Path

log = Path("state/brain-log.md")
lines = log.read_text(encoding="utf-8").strip().splitlines() if log.exists() else []
today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
runs = [l for l in lines if l.startswith(today)]
sent = sum(int(l.split("отправлено:")[1].split("|")[0]) for l in runs if "отправлено:" in l)
queue = Path("state/queue.json")
qlen = len(__import__("json").loads(queue.read_text(encoding="utf-8"))) if queue.exists() else 0
text = (f"☁️ Конвейер жив. За сегодня (UTC): прогонов мозга {len(runs)}, "
        f"проектов отправлено в дайджесты {sent}, в очереди сейчас {qlen}. "
        f"Тишина = не было достойного, фильтр бережёт ваши биды.")
out = Path("heartbeat.txt")
out.write_text(text, encoding="utf-8")
subprocess.run(["python3", "notify.py", "heartbeat.txt"], check=True)
