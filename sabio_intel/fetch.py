"""Collect articles from RSS feeds. Failures in one source never sink the run."""
import calendar
import re
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; SabioMarketIntel/1.0)"


def _clean(html: str, limit: int = 700) -> str:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _published(e) -> datetime:
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.fromtimestamp(calendar.timegm(t), timezone.utc) if t else datetime.now(timezone.utc)


def fetch_source(src: dict, max_age_hours: int, client: httpx.Client) -> list[dict]:
    r = client.get(src["url"], headers={"User-Agent": UA}, follow_redirects=True, timeout=20)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    out = []
    for e in feed.entries:
        pub = _published(e)
        if pub < cutoff:
            continue
        out.append({
            "source": src["name"], "title": _clean(e.get("title", ""), 300),
            "url": e.get("link", ""), "published": pub.isoformat(),
            "summary": _clean(e.get("summary") or (e.get("content") or [{}])[0].get("value", "")),
            "weight": src.get("weight", 1.0), "tags": src.get("tags", []),
        })
    return out


def fetch_all(sources: list[dict], max_age_hours: int = 48) -> tuple[list[dict], dict]:
    arts, status = [], {}
    with httpx.Client() as client:
        for src in sources:
            try:
                got = fetch_source(src, max_age_hours, client)
                arts += got
                status[src["name"]] = f"ok ({len(got)})"
            except Exception as exc:  # noqa: BLE001
                status[src["name"]] = f"FAILED: {type(exc).__name__}: {exc}"
                print(f"[fetch] {src['name']}: {exc}", file=sys.stderr)
    return arts, status
