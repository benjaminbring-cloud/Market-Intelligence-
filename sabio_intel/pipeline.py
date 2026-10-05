from datetime import date

from . import analyze, deliver, fetch, render, store
from .config import OUTPUT_DIR, load


def run(profile_key: str, llm, since_hours: int = 48, send: bool = True, articles: list[dict] | None = None,
        min_relevance: float = 5.0):
    sources, company, aud = load("sources")["sources"], load("company"), load("audiences")
    profile = aud["profiles"][profile_key]
    brief = analyze.company_brief(company, aud.get("clients") or [])
    run_date = date.today().isoformat()
    db = store.connect()

    status = {}
    if articles is None:
        articles, status = fetch.fetch_all(sources, since_hours)
    store.upsert_articles(db, articles)
    todo = store.unscored(db, profile_key, since_hours)
    print(f"[run] {len(articles)} fetched, {len(todo)} to score for {profile_key}")

    scored = analyze.triage(llm, brief, profile["lens"], todo)
    store.save_scores(db, profile_key, run_date, scored)

    # Daily emails look at the last 24-48h; weekly look back 7d across everything scored.
    window = 7 if profile["cadence"] == "weekly" else 2
    pool = [s for s in store.recent_scored(db, profile_key, window) if s["relevance"] >= min_relevance]
    pool = sorted(pool, key=lambda s: -s["relevance"])
    # Everything that clears the bar is included. top_n is how many get the FULL write-up;
    # the rest get a one-line summary. max_stories is only a runaway-cost safety ceiling.
    pool = pool[:profile.get("max_stories", 40)]
    if not pool:
        print("[run] nothing cleared the bar; no email sent")
        return None
    featured_n = profile["top_n"]
    featured = pool[:featured_n] + [s for s in pool[featured_n:] if s.get("client")]
    rest = [s for s in pool if s not in featured]

    stories = analyze.deep(llm, brief, profile["lens"], featured)
    radar = analyze.brief_pass(llm, brief, profile["lens"], rest) if rest else []
    synth = analyze.synthesize(llm, brief, profile["lens"], stories, store.theme_history(db, profile_key))
    themes = [{"theme": t["theme"], "article_ids": [stories[i]["id"] for i in t.get("article_indices", []) if i < len(stories)]}
              for t in synth.get("themes", [])]
    store.save_themes(db, run_date, profile_key, themes)

    html = render.email_html(profile, stories, synth, run_date, status, radar)
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / f"{run_date}_{profile_key}_slides.md").write_text(render.deck_markdown(stories, synth, run_date))
    (OUTPUT_DIR / f"{run_date}_{profile_key}_slides.json").write_text(render.deck_json(stories, synth, run_date))
    if send:
        deliver.send(profile["email"], f"Sabio Intel: {stories[0].get('headline', stories[0]['title'])}",
                     html, aud["delivery"]["from_name"], run_date, profile_key)
    return {"stories": stories, "synth": synth}
