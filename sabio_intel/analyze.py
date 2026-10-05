"""Three passes: triage (cheap, wide) -> deep analysis (top stories) -> synthesis (narrative + themes)."""
import json

from .config import load

BATCH = 25


def company_brief(company: dict, clients: list[dict]) -> str:
    c = company
    lines = [
        f"COMPANY: {c['company']['name']} — {c['company']['one_liner'].strip()}",
        "DIFFERENTIATORS: " + "; ".join(c["company"]["differentiators"]),
        "BUYERS: " + ", ".join(c["company"]["buyers"]),
        "COMPETITORS/ADJACENT: " + ", ".join(c["company"]["competitors_and_adjacent"]),
        "WHAT MATTERS (in priority order):\n- " + "\n- ".join(c["priorities"]),
        "IGNORE unless unusually relevant: " + "; ".join(c["ignore"]),
        "SAMPLE AUDIENCES: " + "; ".join(c["audiences"]["examples"]),
        f"NARRATIVE THESIS: {c['narrative']['thesis'].strip()}",
        f"TONE: {c['narrative']['tone']}. Avoid: {', '.join(c['narrative']['avoid'])}",
    ]
    if clients:
        lines.append("ACTIVE CLIENTS (flag any story touching these): " +
                     "; ".join(f"{x['name']} ({x.get('category', '')})" for x in clients))
    return "\n".join(lines)


TRIAGE_SYS = """You are the market-intelligence triage analyst for the company below.
Score each article 0-10 for how much it matters to this company's business, pitches and clients.
Be harsh: most articles are 0-3. 8+ means the team would want to hear about it today.
Return ONLY JSON: [{"i": <index>, "relevance": <0-10>, "category": "<short label>", "client": "<client name or null>"}]

""" 


def triage(llm, brief: str, lens: str, arts: list[dict]) -> list[dict]:
    scored = []
    for k in range(0, len(arts), BATCH):
        chunk = arts[k:k + BATCH]
        listing = "\n".join(
            f"[{i}] ({a['source']}) {a['title']} — {a['summary'][:300]}" for i, a in enumerate(chunk))
        res = llm.json(TRIAGE_SYS + brief + f"\n\nREADER LENS: {lens.strip()}", listing, max_tokens=3000)
        by_i = {r["i"]: r for r in res}
        for i, a in enumerate(chunk):
            r = by_i.get(i, {})
            rel = float(r.get("relevance", 0))
            # light source-credibility nudge, capped so it can't promote junk
            a = {**a, "relevance": round(min(10, rel * (0.9 + 0.1 * a["weight"])), 1),
                 "category": r.get("category", ""), "client": r.get("client")}
            scored.append(a)
    return scored


DEEP_SYS = """You are a senior strategist at the company below writing for a busy executive.
For EACH story, produce an actionable read. Be specific to the company's capabilities; no generic advice.
Return ONLY JSON: [{
 "i": <index>,
 "headline": "<rewrite in plain English, <=14 words, insight first>",
 "why_it_matters": "<2 sentences max: the so-what for us and our buyers>",
 "activation": "<one concrete play we can run THIS WEEK: an audience to build, a pitch angle, an outreach, a client to call. Name the persona/apps where relevant>",
 "deck_slide": {"title": "<slide title as a claim>", "bullets": ["<=3 short bullets, client-safe, no confidential info>"], "so_what": "<one line>"},
 "confidence": "<high|medium|low — based on how solid the source report is>",
 "claims_to_verify": ["<any stat or claim you'd check before putting in front of a client>"]
}]
Only use facts in the supplied text. If the article doesn't support a claim, don't make it.

"""


def deep(llm, brief: str, lens: str, top: list[dict]) -> list[dict]:
    listing = "\n\n".join(
        f"[{i}] ({a['source']}, {a['published'][:10]}) {a['title']}\n{a['summary']}\nURL: {a['url']}"
        for i, a in enumerate(top))
    res = llm.json(DEEP_SYS + brief + f"\n\nREADER LENS: {lens.strip()}", listing, max_tokens=7000)
    by_i = {r["i"]: r for r in res}
    return [{**a, **{k: v for k, v in by_i.get(i, {}).items() if k != "i"}} for i, a in enumerate(top)]


SYNTH_SYS = """You are the head of narrative strategy for the company below. From this period's top stories,
and the themes we've already flagged in recent weeks, produce ONLY JSON:
{
 "narrative_of_the_week": {
   "headline": "<the one market story we should be telling, as a sentence a CMO would repeat>",
   "argument": "<3-4 sentences: what's changing, why app-based audiences are the answer, evidence from the stories>",
   "proof_points": ["<2-3, each tied to a supplied story index like [2]>"],
   "linkedin_post": "<120 words max, first person plural, no hype words, ends with a question>",
   "talk_track": "<30-second spoken version for a sales call>"
 },
 "themes": [{"theme": "<short label>", "article_indices": [<ints>], "momentum": "<new|building|fading>"}],
 "watchlist": ["<2-4 things not yet actionable but worth tracking, with what would trigger action>"],
 "contrarian_take": "<one thing the trades are getting wrong or missing, 1-2 sentences>"
}
Prior themes are context: mark a theme "building" if it recurs, "new" if not seen before.

"""


def synthesize(llm, brief: str, lens: str, stories: list[dict], past_themes: list[str]) -> dict:
    listing = "\n".join(f"[{i}] {s['headline'] if 'headline' in s else s['title']} — {s.get('why_it_matters', s['summary'][:200])}"
                        for i, s in enumerate(stories))
    user = listing + "\n\nPRIOR THEMES (last 6 weeks): " + (json.dumps(past_themes) if past_themes else "none yet")
    return llm.json(SYNTH_SYS + brief + f"\n\nREADER LENS: {lens.strip()}", user, max_tokens=3500)
