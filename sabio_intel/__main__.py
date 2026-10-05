import argparse
import sys

from . import fetch
from .config import load


def main():
    p = argparse.ArgumentParser(prog="sabio_intel")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="fetch, score, and email")
    r.add_argument("--profile", default="ben")
    r.add_argument("--all", action="store_true", help="every profile whose cadence matches today")
    r.add_argument("--hours", type=int, default=48)
    r.add_argument("--no-send", action="store_true")
    sub.add_parser("check-sources", help="test every feed URL")
    a = p.parse_args()

    if a.cmd == "check-sources":
        _, status = fetch.fetch_all(load("sources")["sources"], max_age_hours=24 * 30)
        for k, v in status.items():
            print(f"{k:35} {v}")
        sys.exit(any(v.startswith("FAILED") for v in status.values()))

    from datetime import date
    from .llm import LLM
    from .pipeline import run
    llm = LLM()
    profiles = load("audiences")["profiles"]
    keys = [a.profile]
    if a.all:
        monday = date.today().weekday() == 0
        keys = [k for k, v in profiles.items() if v["cadence"] == "daily" or monday]
    for k in keys:
        run(k, llm, since_hours=a.hours if profiles[k]["cadence"] == "daily" else 24 * 7, send=not a.no_send)


main()
