#!/usr/bin/env python3
"""Collect AI/tech headlines from configured feeds and dump Markdown summaries with Korean translations."""
import json
import logging
import hashlib
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import xml.etree.ElementTree as ET
from googletrans import Translator

BASE_DIR = Path(__file__).resolve().parent.parent
FEEDS_FILE = BASE_DIR / "feeds.json"
DAILY_DIR = BASE_DIR / "daily"
MONTHLY_DIR = BASE_DIR / "monthly"
STATE_DIR = BASE_DIR / "state"
LOGS_DIR = BASE_DIR / "logs"
MAX_ENTRIES_PER_FEED = 10
KEYWORD_LIMIT = 6
STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "using",
    "through",
    "into",
    "about",
    "via",
    "new",
    "ai",
    "artificial",
    "intelligence",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
TRANSLATOR = Translator()


def ensure_dirs() -> None:
    for folder in (DAILY_DIR, MONTHLY_DIR, STATE_DIR, LOGS_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def load_feeds() -> List[Dict]:
    if not FEEDS_FILE.exists():
        logging.warning("feeds.json is missing, nothing to crawl")
        return []
    return json.loads(FEEDS_FILE.read_text())


def parse_rss(content: str) -> List[Dict]:
    root = ET.fromstring(content)
    items: List[Dict] = []
    for item in root.findall(".//item"):
        title = item.findtext("title")
        link = item.findtext("link")
        published = item.findtext("pubDate")
        if not title or not link:
            continue
        items.append({"title": title.strip(), "link": link.strip(), "pubDate": published or ""})
    return items


def fetch_feed(feed: Dict) -> Tuple[List[Dict], List[str]]:
    errors: List[str] = []
    entries: List[Dict] = []
    try:
        resp = requests.get(feed["url"], timeout=10)
        resp.raise_for_status()
        parsed = parse_rss(resp.text)
        entries = parsed[:MAX_ENTRIES_PER_FEED]
        logging.info("Fetched %d entries from %s", len(entries), feed["id"])
    except Exception as exc:  # pragma: no cover
        logging.error("Failed to fetch %s: %s", feed["url"], exc)
        errors.append(str(exc))
    return entries, errors


def hash_entry(feed_id: str, link: str) -> str:
    return hashlib.sha256(f"{feed_id}|{link}".encode()).hexdigest()


def translate_text(text: str) -> str:
    try:
        translated = TRANSLATOR.translate(text, dest="ko")
        ko_text = translated.text
        return f"{ko_text} ({text})"
    except Exception as exc:  # pragma: no cover
        logging.warning("Translation failed for %s: %s", text, exc)
        return text


def extract_keywords(titles: List[str], limit: int = KEYWORD_LIMIT) -> List[str]:
    counter = Counter()
    representative: Dict[str, str] = {}
    for title in titles:
        for raw in re.findall(r"[A-Za-z0-9+#]{2,}", title):
            normalized = raw.strip("#+").lower()
            if not normalized or normalized in STOPWORDS or normalized.isdigit():
                continue
            counter[normalized] += 1
            if normalized not in representative:
                representative[normalized] = raw
    keywords: List[str] = []
    for term, _ in counter.most_common(limit):
        keywords.append(representative.get(term, term))
    return keywords


def load_state(year_month: str) -> Dict:
    state_file = STATE_DIR / f"{year_month}.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"seen": [], "updated": ""}


def save_state(year_month: str, state: Dict) -> None:
    state_file = STATE_DIR / f"{year_month}.json"
    state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_log(year_month: str, lines: List[str]) -> None:
    log_file = LOGS_DIR / f"{year_month}.log"
    now = datetime.utcnow().isoformat() + "Z"
    with log_file.open("a", encoding="utf-8") as handle:
        for line in lines:
            handle.write(f"{now} - {line}\n")


def summarize_entries(headlines: List[Dict]) -> str:
    if not headlines:
        return "현재 새로운 항목이 없습니다."
    bullets: List[str] = []
    for entry in headlines:
        translated = translate_text(entry["title"])
        bullets.append(
            f"- {translated} \u2013 {entry['source']} ({entry['link']})"
        )
    return "\n".join(bullets)


def build_markdown(date: datetime, headlines: List[Dict], errors: List[str], keywords: List[str]) -> str:
    lines = [f"# AI Briefing · {date:%Y-%m-%d}", "", "## Today", "", summarize_entries(headlines)]
    if keywords:
        lines.extend(["", "## Keywords"])
        lines.extend(f"- {translate_text(keyword)}" for keyword in keywords)
    if errors:
        lines.extend(["", "## Errors / Missing Feeds"])
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines)


def append_monthly(date: datetime, headlines: List[Dict]) -> None:
    path = MONTHLY_DIR / f"{date:%Y-%m}.md"
    header = f"# {date:%Y-%m} AI Briefing Summary\n\n"
    append_line = f"- {date:%Y-%m-%d}: {len(headlines)} new entries"
    if not path.exists():
        path.write_text(header, encoding="utf-8")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{append_line}\n")


def save_daily(date: datetime, markdown: str) -> None:
    path = DAILY_DIR / f"{date:%Y-%m-%d}.md"
    path.write_text(markdown, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    feeds = load_feeds()
    today = datetime.utcnow()
    year_month = today.strftime("%Y-%m")
    state = load_state(year_month)
    seen = set(state.get("seen", []))

    headlines: List[Dict] = []
    errors: List[str] = []

    for feed in feeds:
        entries, fetch_errors = fetch_feed(feed)
        errors.extend(fetch_errors)
        for entry in entries:
            entry_id = hash_entry(feed["id"], entry["link"])
            if entry_id in seen:
                continue
            seen.add(entry_id)
            headlines.append({
                "title": entry["title"],
                "link": entry["link"],
                "source": feed["title"],
                "region": feed.get("region", "")
            })

    keywords = extract_keywords([entry["title"] for entry in headlines])
    markdown = build_markdown(today, headlines, errors, keywords)
    save_daily(today, markdown)
    append_monthly(today, headlines)

    state["seen"] = sorted(seen)
    state["updated"] = today.isoformat() + "Z"
    save_state(year_month, state)

    if errors:
        append_log(year_month, errors)

    logging.info("Collected %d new headlines", len(headlines))


if __name__ == "__main__":
    main()
