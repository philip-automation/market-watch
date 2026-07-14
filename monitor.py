"""Freelancer.com project monitor (cloud edition) -> queues candidates in state/queue.json.

Tokens come from environment variables (GitHub Secrets):
FREELANCER_TOKEN, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

STATE = Path(__file__).resolve().parent / "state"
STATE.mkdir(exist_ok=True)
SEEN_FILE = STATE / "seen_projects.json"
QUEUE_FILE = STATE / "queue.json"

FL_API = "https://www.freelancer.com/api/projects/0.1/projects/active/"
TOKEN = os.environ["FREELANCER_TOKEN"]

QUERIES = [
    "web scraping", "data extraction", "ai chatbot", "gpt integration",
    "python automation", "google sheets automation", "excel automation",
    "telegram bot", "chatgpt api", "pdf extraction", "api integration",
    "python script",
]
MIN_BUDGET_USD = 55
MAX_BIDS = 20


def http_json(url, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(url, headers={"freelancer-oauth-v1": TOKEN})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def interesting(project):
    upgrades = project.get("upgrades") or {}
    if (upgrades.get("qualified") or upgrades.get("pf_only") or upgrades.get("nonpublic")
            or upgrades.get("enterprise") or upgrades.get("non_compete")):
        return False
    bids = (project.get("bid_stats") or {}).get("bid_count") or 0
    if bids > MAX_BIDS:
        return False
    budget = project.get("budget") or {}
    top = budget.get("maximum") or budget.get("minimum") or 0
    usd_rate = (project.get("currency") or {}).get("exchange_rate") or 1
    if top and top * usd_rate < MIN_BUDGET_USD:
        return False
    return True


def main():
    seen = set(load(SEEN_FILE, []))
    first_run = not seen
    queue = load(QUEUE_FILE, [])
    queued_ids = {item.get("id") for item in queue}
    for query in QUERIES:
        try:
            projects = (http_json(FL_API, {
                "query": query, "limit": 40, "sort_field": "time_updated",
                "compact": "true", "full_description": "true",
            }).get("result") or {}).get("projects") or []
        except Exception as e:
            print(f"[{query}] fetch error: {e}")
            continue
        for p in projects:
            pid = p.get("id")
            if not pid or pid in seen:
                continue
            seen.add(pid)
            if first_run or pid in queued_ids or not interesting(p):
                continue
            budget = p.get("budget") or {}
            queue.append({
                "id": pid,
                "title": p.get("title"),
                "budget_min": budget.get("minimum"),
                "budget_max": budget.get("maximum"),
                "currency": (p.get("currency") or {}).get("code"),
                "usd_rate": (p.get("currency") or {}).get("exchange_rate") or 1,
                "bids": (p.get("bid_stats") or {}).get("bid_count") or 0,
                "url": "https://www.freelancer.com/projects/" + str(p.get("seo_url") or pid),
                "desc": ((p.get("description") or p.get("preview_description") or "").strip())[:1500],
                "query": query,
                "found_at": time.strftime("%Y-%m-%d %H:%M"),
            })
    SEEN_FILE.write_text(json.dumps(sorted(seen)[-8000:]), encoding="utf-8")
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"queue size: {len(queue)}")


if __name__ == "__main__":
    main()
