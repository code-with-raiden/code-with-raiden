#!/usr/bin/env python3
"""Download the last year of contribution counts into data/contributions.json.

    GH_USER=code-with-raiden python scripts/fetch_contributions.py

GitHub renders the contribution calendar as HTML. Each day is a <td> with
data-date and an id, and a <tool-tip> for that id gives the count.
If nothing parses, the script exits without overwriting the old data.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "code-with-raiden")
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"


def fetch(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-cards"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse(html):
    # cell id -> date
    cell_dates = {}
    for tag in re.findall(r"<td\b[^>]*>", html):
        date = re.search(r'data-date="([^"]+)"', tag)
        cid = re.search(r'\sid="([^"]+)"', tag)
        if date and cid:
            cell_dates[cid.group(1)] = date.group(1)

    # date -> count, read from the tooltip for each cell
    counts = {}
    for cid, body in re.findall(r'<tool-tip\b[^>]*\sfor="([^"]+)"[^>]*>(.*?)</tool-tip>', html, re.S):
        if cid not in cell_dates:
            continue
        text = re.sub(r"<[^>]+>", "", body).strip()
        m = re.match(r"([\d,]+) contribution", text)
        counts[cell_dates[cid]] = int(m.group(1).replace(",", "")) if m else 0

    return [{"date": d, "count": counts.get(d, 0)} for d in sorted(set(cell_dates.values()))]


def main():
    days = parse(fetch(USER))
    if not days:
        sys.exit("No contribution cells found. Leaving the existing data in place.")

    payload = {
        "user": USER,
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "total": sum(d["count"] for d in days),
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"{len(days)} days, {payload['total']} contributions -> {OUT.relative_to(OUT.parent.parent)}")


if __name__ == "__main__":
    main()
