"""Render a GitHub stats card for the current calendar year.

Commits in private repos only reach the API as an anonymous "restricted"
contribution count, so the commit total adds that to the public commits.
It requires "Include private contributions on my profile" to be enabled.

Usage: GITHUB_TOKEN=... python3 year_stats.py [output.svg]
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from html import escape

LOGIN = "Yusufmermi"
NAME = "Yusuf"

# tokyonight theme, matching the other cards in README.md
BG, TITLE, TEXT, ICON = "#0D1117", "#70a5fd", "#38bdae", "#bf91f3"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

ICONS = {
    "commit": '<circle cx="8" cy="8" r="3"/><path d="M0 8h5M11 8h5"/>',
    "grid": '<rect x="1" y="1" width="5.5" height="5.5" rx="1"/><rect x="9.5" y="1" width="5.5" height="5.5" rx="1"/>'
            '<rect x="1" y="9.5" width="5.5" height="5.5" rx="1"/><rect x="9.5" y="9.5" width="5.5" height="5.5" rx="1"/>',
    "calendar": '<rect x="1.5" y="3" width="13" height="11.5" rx="1.5"/><path d="M1.5 7h13M5 1v3.5M11 1v3.5"/>',
    "bolt": '<path d="M9.5 1 3 9h4.5L6.5 15 13 7H8.5z"/>',
}


def fetch(year, now):
    variables = {
        "login": LOGIN,
        "from": f"{year}-01-01T00:00:00Z",
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={
            "Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")

    c = data["data"]["user"]["contributionsCollection"]
    days = [
        d
        for w in c["contributionCalendar"]["weeks"]
        for d in w["contributionDays"]
        if d["date"].startswith(str(year))
    ]
    return {
        "commits": c["totalCommitContributions"] + c["restrictedContributionsCount"],
        "contributions": c["contributionCalendar"]["totalContributions"],
        "active_days": sum(1 for d in days if d["contributionCount"] > 0),
        "best_day": max((d["contributionCount"] for d in days), default=0),
    }


def render(year, stats, progress):
    rows = [
        ("commit", f"Total Commits ({year}):", stats["commits"]),
        ("grid", f"Total Contributions ({year}):", stats["contributions"]),
        ("calendar", f"Active Days ({year}):", stats["active_days"]),
        ("bolt", "Most in One Day:", stats["best_day"]),
    ]
    body = "".join(
        f'<g class="stagger" style="animation-delay:{450 + i * 150}ms" transform="translate(25,{72 + i * 28})">'
        f'<g class="icon" transform="translate(0,-12)">{ICONS[icon]}</g>'
        f'<text class="stat" x="25">{escape(label)}</text>'
        f'<text class="stat" x="245">{value:,}</text></g>'
        for i, (icon, label, value) in enumerate(rows)
    )
    circumference = 2 * 3.14159 * 40
    offset = circumference * (1 - progress)
    title = escape(f"{NAME}'s {year} on GitHub")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="467" height="195" viewBox="0 0 467 195" role="img" aria-label="{title}">
<title>{title}: {stats['commits']:,} commits</title>
<style>
.header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; animation: fadeIn .8s ease-in-out forwards; }}
.stat {{ font: 600 14px 'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif; fill: {TEXT}; }}
.icon {{ fill: none; stroke: {ICON}; stroke-width: 1.5; stroke-linejoin: round; stroke-linecap: round; }}
.stagger {{ opacity: 0; animation: fadeIn .3s ease-in-out forwards; }}
.year {{ font: 800 22px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
.pct {{ font: 600 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
.ring-bg {{ fill: none; stroke: {TITLE}; stroke-opacity: .2; stroke-width: 6; }}
.ring {{ fill: none; stroke: {TITLE}; stroke-width: 6; stroke-linecap: round;
  stroke-dasharray: {circumference:.2f}; stroke-dashoffset: {circumference:.2f};
  animation: ring 1s ease-in-out .3s forwards; }}
@keyframes ring {{ to {{ stroke-dashoffset: {offset:.2f}; }} }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
</style>
<rect x="0.5" y="0.5" rx="4.5" width="466" height="194" fill="{BG}"/>
<text class="header" x="25" y="35">{title}</text>
{body}
<g transform="translate(390,107)">
  <circle class="ring-bg" r="40"/>
  <circle class="ring" r="40" transform="rotate(-90)"/>
  <text class="year" text-anchor="middle" y="4">{year}</text>
  <text class="pct" text-anchor="middle" y="22">{progress:.0%}</text>
</g>
</svg>
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/year-stats.svg"
    now = datetime.now(timezone.utc)
    start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    stats = fetch(now.year, now)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(now.year, stats, (now - start) / (end - start)))
    print(stats)


if __name__ == "__main__":
    main()
