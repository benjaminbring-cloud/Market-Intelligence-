import html
import json
from datetime import date

e = html.escape


def _story(s: dict, n: int) -> str:
    flag = f' <span style="background:#fde68a;padding:1px 6px;border-radius:4px;font-size:11px">CLIENT: {e(s["client"])}</span>' if s.get("client") else ""
    verify = ""
    if s.get("claims_to_verify"):
        verify = f'<div style="font-size:12px;color:#92400e;margin-top:6px">Verify before client use: {e("; ".join(s["claims_to_verify"]))}</div>'
    return f"""
<div style="margin:0 0 22px;padding:0 0 18px;border-bottom:1px solid #e5e7eb">
  <div style="font-size:12px;color:#6b7280">{n}. {e(s['source'])} · {e(s.get('category',''))} · relevance {s['relevance']}/10{flag}</div>
  <div style="font-size:17px;font-weight:700;margin:4px 0"><a href="{e(s['url'])}" style="color:#111;text-decoration:none">{e(s.get('headline', s['title']))}</a></div>
  <div style="font-size:14px;line-height:1.5;color:#374151">{e(s.get('why_it_matters',''))}</div>
  <div style="font-size:14px;line-height:1.5;margin-top:8px;background:#ecfdf5;border-left:3px solid #10b981;padding:8px 10px"><b>Activate:</b> {e(s.get('activation',''))}</div>{verify}
</div>"""


def email_html(profile: dict, stories: list[dict], synth: dict, run_date: str, status: dict) -> str:
    secs = profile.get("sections", [])
    parts = [f'<div style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:680px;margin:auto;color:#111">',
             f'<h2 style="margin:0">Sabio Market Intel</h2><div style="color:#6b7280;font-size:13px;margin-bottom:18px">{e(run_date)} · for {e(profile["name"])}</div>']
    nar = synth.get("narrative_of_the_week")
    if "narrative_of_the_week" in secs and nar:
        parts.append(f"""<div style="background:#111827;color:#fff;padding:16px 18px;border-radius:8px;margin-bottom:22px">
<div style="font-size:11px;letter-spacing:.08em;opacity:.7">THE NARRATIVE TO PUSH</div>
<div style="font-size:19px;font-weight:700;margin:6px 0">{e(nar['headline'])}</div>
<div style="font-size:14px;line-height:1.5;opacity:.92">{e(nar['argument'])}</div>
<div style="font-size:13px;margin-top:10px;opacity:.85"><b>Talk track:</b> {e(nar.get('talk_track',''))}</div></div>""")
    if "headline" in secs:
        parts.append('<h3 style="margin:0 0 12px">What matters</h3>')
        parts += [_story(s, i + 1) for i, s in enumerate(stories)]
    if "deck_slides" in secs:
        parts.append('<h3>Deck-ready (also saved as a slide pack)</h3><ul style="font-size:14px">')
        for s in stories[:4]:
            d = s.get("deck_slide")
            if d:
                parts.append(f"<li><b>{e(d['title'])}</b> — {e(d.get('so_what',''))}</li>")
        parts.append("</ul>")
    if nar and "narrative_of_the_week" in secs:
        parts.append(f'<h3>LinkedIn draft</h3><div style="font-size:14px;background:#f3f4f6;padding:10px;border-radius:6px;white-space:pre-wrap">{e(nar.get("linkedin_post",""))}</div>')
    if synth.get("contrarian_take"):
        parts.append(f'<h3>What the trades are missing</h3><p style="font-size:14px">{e(synth["contrarian_take"])}</p>')
    if "watchlist" in secs and synth.get("watchlist"):
        parts.append("<h3>Watchlist</h3><ul style='font-size:14px'>" + "".join(f"<li>{e(w)}</li>" for w in synth["watchlist"]) + "</ul>")
    bad = [k for k, v in status.items() if v.startswith("FAILED")]
    if bad:
        parts.append(f'<div style="font-size:11px;color:#9ca3af;margin-top:20px">Sources unavailable this run: {e(", ".join(bad))}</div>')
    parts.append("</div>")
    return "".join(parts)


def deck_markdown(stories: list[dict], synth: dict, run_date: str) -> str:
    out = [f"# Market Intel slide pack — {run_date}", "",
           "_Drop-in content for the weekly client strategy deck. Verify flagged claims before client use._", ""]
    nar = synth.get("narrative_of_the_week")
    if nar:
        out += ["## Slide: Market narrative", f"**{nar['headline']}**", "", nar["argument"], ""]
        out += [f"- {p}" for p in nar.get("proof_points", [])] + [""]
    for i, s in enumerate(stories, 1):
        d = s.get("deck_slide")
        if not d:
            continue
        out += [f"## Slide {i}: {d['title']}"] + [f"- {b}" for b in d.get("bullets", [])]
        out += [f"\n**So what:** {d.get('so_what','')}", f"_Source: {s['source']} — {s['url']}_",
                f"_Our play: {s.get('activation','')}_", ""]
        if s.get("claims_to_verify"):
            out += [f"_Verify: {'; '.join(s['claims_to_verify'])}_", ""]
    return "\n".join(out)


def deck_json(stories: list[dict], synth: dict, run_date: str) -> str:
    return json.dumps({"date": run_date, "narrative": synth.get("narrative_of_the_week"),
                       "slides": [{"source": s["source"], "url": s["url"], **s["deck_slide"]}
                                  for s in stories if s.get("deck_slide")]}, indent=2)
