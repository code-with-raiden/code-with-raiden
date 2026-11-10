#!/usr/bin/env python3
"""Render the animated SVG cards for the profile README.

    python scripts/render_readme_cards.py           # animated cards -> cards/
    STATIC=1 python scripts/render_readme_cards.py  # end frames    -> cards-static/

Inputs
  data/contributions.json   written by scripts/fetch_contributions.py
  fonts/serif-400.woff      optional, Instrument Serif subset (embedded as base64)
  fonts/sans-400.woff       optional, Geist subset (embedded as base64)
  assets/portrait.txt       optional, ASCII portrait printed into the hero

Everything here is plain standard library Python.
"""
import base64
import datetime as dt
import json
import os
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
FONTS = ROOT / "fonts"
PORTRAIT = ROOT / "assets" / "portrait.txt"
STATIC = os.environ.get("STATIC") == "1"
OUT = ROOT / ("cards-static" if STATIC else "cards")

# ---------------------------------------------------------------- content
# Edit these. README.md links to the same card files, so keep names in sync.
PROFILE = {
    "name": "Raiden",
    "role": "Fullstack engineer",
    "line": "I build small tools and ship them in public.",
}

TILES = [
    {"label": "BUILD", "title": "Projects", "value": 12, "sub": "repos shipped", "color": "blue"},
    {"label": "BRAND", "title": "Brand", "value": 3, "sub": "sites live", "color": "red"},
    {"label": "LEARN", "title": "Writing", "value": 8, "sub": "posts", "color": "yellow"},
]

REPOS = [
    {"name": "code-with-raiden", "desc": "Profile README, rendered as animated SVG.", "lang": "Python", "color": "blue"},
    {"name": "raiden-api", "desc": "Example project card. Replace with a real repo.", "lang": "TypeScript", "color": "red"},
]

# ---------------------------------------------------------------- style
P = {
    "paper": "#F4F1EA",
    "ink": "#1A1A1A",
    "muted": "#6B675E",
    "rule": "#D8D3C7",
    "bar": "#CFC8B8",
    "blue": "#2F5BEA",
    "red": "#D9432B",
    "yellow": "#F2B705",
}
SERIF = "'Instrument Serif', Georgia, serif"
SANS = "'Geist', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

BASE_CSS = """
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes swing{0%{opacity:0;transform:translateY(40px) rotate(-6deg) scale(.92)}60%{opacity:1;transform:translateY(-6px) rotate(1.5deg) scale(1.03)}100%{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
@keyframes pop{0%{opacity:0;transform:scale(.4)}70%{opacity:1;transform:scale(1.15)}100%{opacity:1;transform:scale(1)}}
@keyframes shine{0%,55%{transform:translateX(-120px)}100%{transform:translateX(320px)}}
@keyframes ring{0%{opacity:.7;transform:scale(1)}100%{opacity:0;transform:scale(2.8)}}
@keyframes nudge{0%,100%{transform:translateX(0)}50%{transform:translateX(4px)}}
.rise{animation:rise .8s cubic-bezier(.2,.7,.2,1) both}
.fade{animation:fade .6s ease both}
.swing{animation:swing .9s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box;transform-origin:center}
.grow{animation:grow .8s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box;transform-origin:bottom}
.pop{animation:pop .5s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:center}
.shine{animation:shine 4.5s ease-in-out infinite}
.ring{animation:ring 2.4s ease-out infinite;transform-box:fill-box;transform-origin:center}
.nudge{animation:nudge 1.6s ease-in-out infinite}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ---------------------------------------------------------------- helpers
def A(cls, delay=0.0):
    """Animation attributes. Empty in STATIC mode so the final frame shows."""
    if STATIC:
        return ""
    return f' class="{cls}" style="animation-delay:{delay:.2f}s"'


def font_faces():
    faces = []
    for family, filename in [("Instrument Serif", "serif-400.woff"), ("Geist", "sans-400.woff")]:
        path = FONTS / filename
        if path.exists():
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            faces.append(
                f"@font-face{{font-family:'{family}';"
                f"src:url(data:font/woff;base64,{b64}) format('woff')}}"
            )
    return "".join(faces)


def svg(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}"><style>{font_faces()}{BASE_CSS}</style>{body}</svg>\n'
    )


def bg(w, h, rx):
    return f'<rect width="{w}" height="{h}" rx="{rx}" fill="{P["paper"]}" stroke="{P["rule"]}"/>'


def latest_date(days):
    if days:
        return dt.date.fromisoformat(max(d["date"] for d in days))
    return dt.date.today()


def streaks(days, end):
    """Return (current streak, longest streak) in days."""
    counts = {d["date"]: d["count"] for d in days}
    longest = run = 0
    prev = None
    for ds in sorted(counts):
        day = dt.date.fromisoformat(ds)
        if counts[ds] > 0:
            run = run + 1 if prev is not None and (day - prev).days == 1 else 1
            longest = max(longest, run)
        else:
            run = 0
        prev = day

    current = 0
    day = end
    if counts.get(day.isoformat(), 0) == 0:  # today may not have activity yet
        day -= dt.timedelta(days=1)
    while counts.get(day.isoformat(), 0) > 0:
        current += 1
        day -= dt.timedelta(days=1)
    return current, longest


def count_up(value, x, y, size, fill, t0):
    """Number that counts up from 0 using one SMIL <set> frame per value.

    CSS cannot change text, so each value is its own <text> that is shown
    for one step. Large numbers skip the count and just appear.
    """
    attrs = (f'x="{x}" y="{y}" font-family="{SERIF}" font-size="{size}" '
             f'fill="{fill}"')
    if STATIC or not isinstance(value, int) or value > 40:
        return f"<text {attrs}>{value}</text>"
    step = 0.07
    frames = []
    for k in range(value + 1):
        mode = "freeze" if k == value else "remove"
        begin = t0 + k * step
        frames.append(
            f'<text {attrs} visibility="hidden">{k}'
            f'<set attributeName="visibility" to="visible" '
            f'begin="{begin:.2f}s" dur="{step}s" fill="{mode}"/></text>'
        )
    return "".join(frames)


# ---------------------------------------------------------------- cards
def hero_svg():
    w, h = 880, 300
    body = [bg(w, h, 18)]
    body.append(
        f'<g{A("rise", 0.1)}>'
        f'<text x="48" y="118" font-family="{SERIF}" font-size="84" fill="{P["ink"]}">'
        f'{escape(PROFILE["name"])}</text></g>'
    )
    body.append(
        f'<g{A("fade", 0.5)}>'
        f'<circle cx="52" cy="158" r="5" fill="{P["blue"]}"/>'
        f'<circle cx="52" cy="158" r="5" fill="{P["blue"]}"{A("ring", 0.8)}/>'
        f'<text x="68" y="164" font-family="{SANS}" font-size="18" letter-spacing="1" '
        f'fill="{P["muted"]}">{escape(PROFILE["role"])}</text>'
        f'<text x="48" y="206" font-family="{SANS}" font-size="20" fill="{P["ink"]}">'
        f'{escape(PROFILE["line"])}</text></g>'
    )
    if PORTRAIT.exists():
        rows = PORTRAIT.read_text(encoding="utf-8").splitlines()
        lh = min(5.0, (h - 24) / max(len(rows), 1))
        for i, row in enumerate(rows):
            y = 12 + (i + 1) * lh
            body.append(
                f'<text x="600" y="{y:.2f}" font-family="{MONO}" font-size="{lh:.2f}" '
                f'fill="{P["ink"]}" xml:space="preserve"{A("fade", 0.4 + i * 0.018)}>'
                f"{escape(row)}</text>"
            )
    return svg(w, h, "".join(body))


def tile_svg(t, i):
    w, h = 300, 180
    col = P[t["color"]]
    t0 = 1.2 + i * 0.15  # count-up starts once the tile has swung in
    defs = (
        "<defs>"
        '<clipPath id="clip"><rect width="300" height="180" rx="14"/></clipPath>'
        '<linearGradient id="shine" x1="0" x2="1">'
        '<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        '<stop offset=".5" stop-color="#fff" stop-opacity=".6"/>'
        '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        "</linearGradient></defs>"
    )
    inner = (
        bg(w, h, 14)
        + f'<rect width="{w}" height="6" fill="{col}"/>'
        + f'<text x="24" y="40" font-family="{MONO}" font-size="12" letter-spacing="2" fill="{col}">'
        + f'{escape(t["label"])}</text>'
        + f'<text x="24" y="74" font-family="{SERIF}" font-size="30" fill="{P["ink"]}">'
        + f'{escape(t["title"])}</text>'
        + count_up(t["value"], 24, 138, 58, P["ink"], t0)
        + f'<text x="24" y="162" font-family="{SANS}" font-size="14" fill="{P["muted"]}">'
        + f'{escape(t["sub"])}</text>'
        + f'<circle cx="276" cy="30" r="5" fill="{col}"{A("ring", t0)}/>'
        + f'<text x="270" y="152" font-family="{SANS}" font-size="22" fill="{col}" '
        + f'text-anchor="end"{A("nudge")}>→</text>'
        + f'<g clip-path="url(#clip)"><rect width="90" height="{h}" fill="url(#shine)"'
        + f'{A("shine", 1.2 + i * 0.4)}/></g>'
    )
    return svg(w, h, f'{defs}<g{A("swing", 0.9 + i * 0.15)}>{inner}</g>')


def activity_svg(data):
    days = data["days"]
    w, h = 880, 330
    end = latest_date(days)

    # last 12 calendar months, oldest first
    keys = []
    y, m = end.year, end.month
    for _ in range(12):
        keys.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    keys.reverse()

    totals = {}
    for d in days:
        k = d["date"][:7]
        totals[k] = totals.get(k, 0) + d["count"]
    vals = [totals.get(f"{y:04d}-{m:02d}", 0) for y, m in keys]
    peak = max(vals) or 1
    best = vals.index(max(vals)) if max(vals) > 0 else -1

    year_days = [d for d in days
                 if dt.date.fromisoformat(d["date"]) > end - dt.timedelta(days=365)]
    active = sum(1 for d in year_days if d["count"] > 0)
    current, longest = streaks(days, end)
    busiest = max(days, key=lambda d: d["count"], default=None)

    stats = [
        (f"{sum(vals):,}", "contributions, 12 months"),
        (str(active), "active days"),
        (str(current), "day streak"),
        (str(longest), "longest streak"),
    ]
    body = [bg(w, h, 18)]
    for i, (num, label) in enumerate(stats):
        x = 48 + i * 205
        body.append(
            f'<g{A("rise", 0.2 + i * 0.1)}>'
            f'<text x="{x}" y="70" font-family="{SERIF}" font-size="44" fill="{P["ink"]}">{num}</text>'
            f'<text x="{x}" y="94" font-family="{SANS}" font-size="13" fill="{P["muted"]}">{label}</text>'
            "</g>"
        )

    base, max_h, bar_w, step = 270, 120, 40, 68
    for i, (y, m) in enumerate(keys):
        v = vals[i]
        bh = max(2.0, v / peak * max_h) if v else 2.0
        x = 48 + i * step
        color = P["blue"] if i == best else P["bar"]
        body.append(
            f'<rect x="{x}" y="{base - bh:.1f}" width="{bar_w}" height="{bh:.1f}" rx="4" '
            f'fill="{color}"{A("grow", 0.6 + i * 0.06)}/>'
        )
        label = dt.date(y, m, 1).strftime("%b")
        body.append(
            f'<text x="{x + bar_w / 2}" y="{base + 20}" text-anchor="middle" '
            f'font-family="{SANS}" font-size="12" fill="{P["muted"]}">{label}</text>'
        )
        if i == best:
            body.append(
                f'<text x="{x + bar_w / 2}" y="{base - bh - 8:.1f}" text-anchor="middle" '
                f'font-family="{SANS}" font-size="13" fill="{P["blue"]}"{A("pop", 1.4)}>{v:,}</text>'
            )

    if busiest and busiest["count"]:
        body.append(
            f'<text x="48" y="{base + 50}" font-family="{SANS}" font-size="13" fill="{P["muted"]}">'
            f'Busiest day: {escape(busiest["date"])}, {busiest["count"]} contributions</text>'
        )
    return svg(w, h, "".join(body))


def graph_svg(data):
    days = data["days"]
    w, h = 880, 150
    end = latest_date(days)
    start = end - dt.timedelta(days=370)
    first = start - dt.timedelta(days=(start.weekday() + 1) % 7)  # align to Sunday
    counts = {d["date"]: d["count"] for d in days}
    peak = max(counts.values(), default=0) or 1
    cell, step, x0, y0 = 12, 16, 16, 14

    body = [bg(w, h, 14)]
    day = first
    while day <= end:
        col = (day - first).days // 7
        row = (day.weekday() + 1) % 7  # Sunday = 0
        c = counts.get(day.isoformat(), 0)
        x, y = x0 + col * step, y0 + row * step
        if c == 0:
            body.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{P["rule"]}"/>')
        else:
            q = c / peak
            opacity = 0.3 if q < 0.25 else 0.5 if q < 0.5 else 0.75 if q < 0.75 else 1
            body.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
                f'fill="{P["blue"]}" fill-opacity="{opacity}"{A("pop", 0.2 + col * 0.025)}/>'
            )
        day += dt.timedelta(days=1)

    total = sum(counts.values())
    body.append(
        f'<text x="16" y="{y0 + 7 * step + 12}" font-family="{SANS}" font-size="13" '
        f'fill="{P["muted"]}">{total:,} contributions in the last year</text>'
    )
    return svg(w, h, "".join(body))


def repo_svg(r):
    w, h = 430, 120
    col = P[r["color"]]
    desc = r["desc"] if len(r["desc"]) <= 58 else r["desc"][:55] + "…"
    body = [
        bg(w, h, 14),
        f'<rect width="6" height="{h}" fill="{col}"/>',
        f'<g{A("rise", 0.1)}>'
        f'<text x="28" y="48" font-family="{SERIF}" font-size="28" fill="{P["ink"]}">'
        f'{escape(r["name"])}</text>'
        f'<text x="28" y="78" font-family="{SANS}" font-size="14" fill="{P["muted"]}">'
        f'{escape(desc)}</text>'
        f'<circle cx="28" cy="102" r="5" fill="{col}"/>'
        f'<text x="40" y="106" font-family="{SANS}" font-size="13" fill="{P["muted"]}">'
        f'{escape(r["lang"])}</text></g>',
    ]
    return svg(w, h, "".join(body))


def slug(name):
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


# ---------------------------------------------------------------- main
def main():
    data = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"days": []}

    files = {
        "hero.svg": hero_svg(),
        "activity.svg": activity_svg(data),
        "graph.svg": graph_svg(data),
    }
    for i, t in enumerate(TILES):
        files[f"{t['label'].lower()}.svg"] = tile_svg(t, i)
    for r in REPOS:
        files[f"repo-{slug(r['name'])}.svg"] = repo_svg(r)

    OUT.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")

    mode = "static end frames" if STATIC else "animated"
    print(f"Wrote {len(files)} {mode} cards to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
