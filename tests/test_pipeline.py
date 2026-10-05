import json
from datetime import datetime, timezone

from sabio_intel import pipeline, llm as llm_mod


class FakeLLM:
    def json(self, system, user, max_tokens=0):
        if system.startswith("You are the market-intelligence triage"):
            n = user.count("\n") + 1
            return [{"i": i, "relevance": 9 if i == 0 else 1, "category": "identity",
                     "client": "eBay" if i == 0 else None} for i in range(n)]
        if "senior strategist" in system:
            return [{"i": 0, "headline": "Cookies die again", "why_it_matters": "Signal loss.",
                     "activation": "Build a resale-app audience.",
                     "deck_slide": {"title": "Signal loss is permanent", "bullets": ["a"], "so_what": "app audiences win"},
                     "claims_to_verify": ["80% stat"]}]
        return {"narrative_of_the_week": {"headline": "H", "argument": "A", "proof_points": ["[0]"],
                                          "linkedin_post": "post?", "talk_track": "tt"},
                "themes": [{"theme": "signal loss", "article_indices": [0], "momentum": "new"}],
                "watchlist": ["w"], "contrarian_take": "c"}


def arts():
    now = datetime.now(timezone.utc).isoformat()
    return [{"source": "AdExchanger", "title": "Chrome cookies", "url": "http://x/1", "published": now,
             "summary": "s", "weight": 1.3, "tags": []},
            {"source": "Adweek", "title": "Award news", "url": "http://x/2", "published": now,
             "summary": "s", "weight": 1.1, "tags": []}]


def test_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr("sabio_intel.store.DATA_DIR", tmp_path)
    monkeypatch.setattr("sabio_intel.pipeline.OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("sabio_intel.deliver.OUTPUT_DIR", tmp_path)
    res = pipeline.run("ben", FakeLLM(), articles=arts())
    assert res["stories"][0]["client"] == "eBay"
    assert len(res["stories"]) == 1           # low-relevance story filtered
    assert "Activate" in next(tmp_path.glob("*_ben.html")).read_text()
    slides = json.loads(next(tmp_path.glob("*_slides.json")).read_text())
    assert slides["slides"][0]["title"] == "Signal loss is permanent"
    # second run: already-seen articles are not re-scored
    again = pipeline.run("ben", FakeLLM(), articles=arts())
    assert again["stories"]                    # still in the 2-day window, but nothing re-triaged


def test_parse_json_handles_fences():
    assert llm_mod.parse_json('```json\n[{"a":1}]\n```') == [{"a": 1}]
    assert llm_mod.parse_json('Here: {"a":1}') == {"a": 1}
