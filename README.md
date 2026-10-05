# Sabio Market Intelligence Agent

Reads the major ad/marketing trades every morning, decides what matters *to Sabio*, and emails a short brief with
**what happened → why it matters → what we can activate this week**, plus a **narrative to push** and a
**drop-in slide pack** for the weekly client strategy decks.

## What it does
1. **Fetch** ~16 trade/app/CTV feeds (`config/sources.yaml`); one broken feed never kills a run.
2. **Remember** everything in SQLite: no repeats, and a rolling record of themes.
3. **Triage** every new article 0–10 against Sabio's priorities (`config/company.yaml`) through the reader's lens.
4. **Deep-read** the top stories: plain-English headline, so-what, a concrete activation play (audience/persona/app signal), a client-safe slide, and **claims to verify** before anything goes in front of a client.
5. **Synthesize**: the narrative of the week (argument, proof points, talk track, LinkedIn draft), theme momentum vs. prior weeks, a watchlist, and a "what the trades are missing" contrarian take.
6. **Deliver**: HTML email + `output/<date>_<profile>_slides.md|json`.

Every story above the relevance bar is included: the top few get the full write-up, the rest appear under "Also on the radar" with a one-line why-it-matters. Stories touching an active client (`config/audiences.yaml → clients`) always make the cut and are flagged.

## Run it
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python -m sabio_intel check-sources          # verify every feed URL first
python -m sabio_intel run --profile ben --no-send    # writes output/*.html preview
MI_TRANSPORT=smtp SMTP_USER=... SMTP_PASSWORD=... python -m sabio_intel run --profile ben
pytest
```
`.github/workflows/intel.yml` runs it 7am ET weekdays (add `ANTHROPIC_API_KEY`, `SMTP_USER`, `SMTP_PASSWORD` repo secrets). Gmail needs an app password.

## Company-wide rollout
Add a block under `profiles:` in `config/audiences.yaml`: same pipeline, different **lens**, cadence, length and sections
(sales = conversation openers; planning = audience/persona ideas; exec = competitive moves). Templates for sales,
planning and leadership are in the file, commented out. Next: per-person subscriptions, a shared Slack channel, and a team-level feedback loop.

## Before you rely on it
- Feed URLs were written from memory and **not tested** (no network in the build sandbox). Run `check-sources`.
- `bbring@sabio.inc` and the differentiator/competitor lists in `company.yaml` are placeholders: confirm, and confirm which claims are cleared for external use.
- Output is analysis from article summaries, not full articles; treat "claims to verify" seriously.

## Roadmap (highest-leverage first)
1. **Feedback loop**: 👍/👎 links in the email feed back into scoring so it learns what Ben actually uses.
2. **Deck integration**: render the slide pack straight into the weekly strategy deck template (pptx/Google Slides) and run the narrative through the `sabio-narrative` skill.
3. **Client radar**: per-client watch queries, auto-brief before each client call (pull calendar).
4. **Competitor tracker**: dedicated page/press monitoring for named competitors, with a weekly diff.
5. **Narrative bank**: persistent library of proof points/stats with source + date, searchable by the whole company.
6. **Full-text fetch** for top stories (paywall-aware) instead of RSS summaries.
7. **Slack/Teams delivery** and an "ask the agent" bot over the history.
