"""SQLite store: dedupe, history, and the memory that powers trend detection."""
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone

from .config import DATA_DIR

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT, summary TEXT,
  published TEXT, fetched TEXT, source_weight REAL, tags TEXT
);
CREATE TABLE IF NOT EXISTS scores (
  article_id TEXT, profile TEXT, run_date TEXT, relevance INTEGER, payload TEXT,
  PRIMARY KEY (article_id, profile)
);
CREATE TABLE IF NOT EXISTS themes (
  run_date TEXT, profile TEXT, theme TEXT, article_ids TEXT
);
"""


def article_id(url: str, title: str) -> str:
    return hashlib.sha1((url or title).strip().lower().encode()).hexdigest()[:16]


def connect(path=None) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path or DATA_DIR / "intel.db")
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def upsert_articles(db, arts: list[dict]) -> list[dict]:
    """Insert new articles; return only the ones we hadn't seen."""
    new = []
    for a in arts:
        a["id"] = article_id(a["url"], a["title"])
        if db.execute("SELECT 1 FROM articles WHERE id=?", (a["id"],)).fetchone():
            continue
        db.execute(
            "INSERT INTO articles VALUES (?,?,?,?,?,?,?,?,?)",
            (a["id"], a["source"], a["title"], a["url"], a["summary"], a["published"],
             datetime.now(timezone.utc).isoformat(), a["weight"], json.dumps(a["tags"])),
        )
        new.append(a)
    db.commit()
    return new


def unscored(db, profile: str, since_hours: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    rows = db.execute(
        """SELECT * FROM articles a WHERE fetched >= ?
           AND NOT EXISTS (SELECT 1 FROM scores s WHERE s.article_id=a.id AND s.profile=?)""",
        (cutoff, profile)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["weight"] = d.pop("source_weight")
        d["tags"] = json.loads(d["tags"] or "[]")
        out.append(d)
    return out


def save_scores(db, profile: str, run_date: str, scored: list[dict]):
    for s in scored:
        db.execute("INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?)",
                   (s["id"], profile, run_date, s["relevance"], json.dumps(s)))
    db.commit()


def recent_scored(db, profile: str, days: int) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    rows = db.execute("""SELECT s.payload, a.title, a.url, a.source FROM scores s
        JOIN articles a ON a.id=s.article_id WHERE s.profile=? AND s.run_date>=?
        ORDER BY s.relevance DESC""", (profile, cutoff)).fetchall()
    out = []
    for r in rows:
        p = json.loads(r["payload"])
        p.update(title=r["title"], url=r["url"], source=r["source"])
        out.append(p)
    return out


def save_themes(db, run_date, profile, themes: list[dict]):
    for t in themes:
        db.execute("INSERT INTO themes VALUES (?,?,?,?)",
                   (run_date, profile, t["theme"], json.dumps(t.get("article_ids", []))))
    db.commit()


def theme_history(db, profile: str, weeks: int = 6) -> list[str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).date().isoformat()
    return [r["theme"] for r in db.execute(
        "SELECT theme FROM themes WHERE profile=? AND run_date>=? ORDER BY run_date", (profile, cutoff))]
