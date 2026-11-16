import os
import json
import urllib.request
import re
from datetime import datetime

USERNAME = "PepeHenrque"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_url(url, headers=None):
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")

def get_stats():
    # If GITHUB_TOKEN is available, we use GraphQL
    if TOKEN:
        gql_query = """
        query($login: String!) {
          user(login: $login) {
            name
            login
            repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
              totalCount
            }
            pullRequests(first: 1) {
              totalCount
            }
            issues(first: 1) {
              totalCount
            }
            contributionsCollection {
              totalCommitContributions
              restrictedContributionsCount
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                  }
                }
              }
            }
            repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
              nodes {
                stargazerCount
              }
            }
          }
        }
        """
        data = json.dumps({"query": gql_query, "variables": {"login": USERNAME}}).encode("utf-8")
        req = urllib.request.Request("https://api.github.com/graphql", data=data, headers={
            "User-Agent": "GitHub-Stats-Generator",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}"
        })
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            user = res["data"]["user"]
            col = user["contributionsCollection"]
            commits = col["totalCommitContributions"] + col["restrictedContributionsCount"]
            prs = user["pullRequests"]["totalCount"]
            issues = user["issues"]["totalCount"]
            contributed = user["repositoriesContributedTo"]["totalCount"]
            stars = sum(r["stargazerCount"] for r in user["repositories"]["nodes"])
            name = user["name"] or USERNAME
            weeks = col["contributionCalendar"]["weeks"]
            day_counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
            return build_data(name, stars, commits, prs, issues, contributed, day_counts)

    # Fallback when running without token (scrape public user contribution profile)
    profile_html = fetch_url(f"https://github.com/users/{USERNAME}/contributions")
    # Extract counts from data-count or tooltips
    counts = [int(m) for m in re.findall(r'data-count="(\d+)"', profile_html)]
    if not counts:
        # fallback pattern if newer github markup
        counts = [int(m) for m in re.findall(r'(\d+)\s+contributions?', profile_html)]
    
    # Defaults based on current verified counts
    return build_data("Pedro Henrique", 28, 165, 29, 0, 4, counts or [1]*30)

def build_data(name, stars, commits, prs, issues, contributed, day_counts):
    score = (commits * 2) + (prs * 3) + (issues * 1) + (stars * 4) + (contributed * 5)
    if score >= 1000: rank = "S"
    elif score >= 500: rank = "A+"
    elif score >= 250: rank = "A"
    elif score >= 100: rank = "B+"
    elif score >= 50: rank = "B"
    else: rank = "B-"

    # 28 points for smooth line
    step = max(1, len(day_counts) // 28)
    points = []
    for i in range(0, len(day_counts), step):
        points.append(sum(day_counts[i:i+step]))
    points = points[-28:]
    if len(points) < 28:
        points = [0]*(28 - len(points)) + points

    return {
        "name": name,
        "stars": stars,
        "commits": commits,
        "prs": prs,
        "issues": issues,
        "contributed": contributed,
        "rank": rank,
        "sparkline": points
    }

def generate_svg(data, dark=False):
    if dark:
        bg = "#0d1117"
        border = "#30363d"
        title_color = "#58a6ff"
        text_primary = "#c9d1d9"
        text_muted = "#8b949e"
        badge_bg = "#161b22"
        badge_border = "#30363d"
        chart_line = "#238636"
        chart_fill = "rgba(35, 134, 54, 0.2)"
    else:
        bg = "#ffffff"
        border = "#e1e4e8"
        title_color = "#0366d6"
        text_primary = "#24292e"
        text_muted = "#586069"
        badge_bg = "#f6f8fa"
        badge_border = "#d1d5da"
        chart_line = "#2ea44f"
        chart_fill = "rgba(46, 164, 79, 0.15)"

    points = data["sparkline"]
    max_p = max(points) if points and max(points) > 0 else 1
    
    px_start = 380
    py_bottom = 152
    w_chart = 265
    h_chart = 75
    step = w_chart / max(1, len(points) - 1)
    
    coords = []
    for idx, val in enumerate(points):
        x = px_start + (idx * step)
        y = py_bottom - ((val / max_p) * h_chart)
        coords.append((x, y))
        
    line_d = f"M {coords[0][0]:.1f} {coords[0][1]:.1f} " + " ".join(f"L {x:.1f} {y:.1f}" for x, y in coords[1:])
    fill_d = f"{line_d} L {coords[-1][0]:.1f} {py_bottom} L {coords[0][0]:.1f} {py_bottom} Z"

    return f"""<svg width="680" height="195" viewBox="0 0 680 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .title {{ font: 600 17px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {title_color}; }}
      .label {{ font: 400 13px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {text_muted}; }}
      .value {{ font: 600 14px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {text_primary}; }}
      .rank-title {{ font: 600 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {text_muted}; }}
      .rank-value {{ font: 700 24px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {title_color}; }}
      .chart-title {{ font: 600 11px -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; fill: {text_muted}; }}
    </style>
  </defs>

  <rect x="0.5" y="0.5" width="679" height="194" rx="8" fill="{bg}" stroke="{border}"/>

  <g transform="translate(25, 34)">
    <text class="title">{data['name']}'s GitHub Stats</text>
  </g>

  <!-- Left Column -->
  <g transform="translate(25, 64)">
    <path d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z" fill="{title_color}"/>
    <text x="22" y="11" class="label">Total Stars Earned:</text>
    <text x="175" y="11" class="value">{data['stars']}</text>
  </g>

  <g transform="translate(25, 90)">
    <path d="M10.5 7.75a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM8 0a8 8 0 100 16A8 8 0 008 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0z" fill="{title_color}"/>
    <text x="22" y="11" class="label">Total Commits:</text>
    <text x="175" y="11" class="value">{data['commits']}</text>
  </g>

  <g transform="translate(25, 116)">
    <path d="M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5zm0 10a2.25 2.25 0 100 4.5 2.25 2.25 0 000-4.5z" fill="{title_color}"/>
    <text x="22" y="11" class="label">Total PRs:</text>
    <text x="175" y="11" class="value">{data['prs']}</text>
  </g>

  <g transform="translate(25, 142)">
    <path d="M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z" fill="{title_color}"/>
    <text x="22" y="11" class="label">Total Issues:</text>
    <text x="175" y="11" class="value">{data['issues']}</text>
  </g>

  <g transform="translate(25, 168)">
    <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1h-8a1 1 0 00-1 1v6.708A2.486 2.486 0 014.5 9h8V1.5z" fill="{title_color}"/>
    <text x="22" y="11" class="label">Contributed to:</text>
    <text x="175" y="11" class="value">{data['contributed']}</text>
  </g>

  <!-- Rank Badge -->
  <g transform="translate(265, 58)">
    <rect width="80" height="116" rx="6" fill="{badge_bg}" stroke="{badge_border}"/>
    <text x="40" y="34" text-anchor="middle" class="rank-title">RANK</text>
    <text x="40" y="80" text-anchor="middle" class="rank-value">{data['rank']}</text>
  </g>

  <!-- Chart Curve -->
  <g transform="translate(380, 48)">
    <text class="chart-title">CONTRIBUTIONS OVER TIME</text>
  </g>
  <path d="{fill_d}" fill="{chart_fill}"/>
  <path d="{line_d}" fill="none" stroke="{chart_line}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

if __name__ == "__main__":
    os.makedirs("dist", exist_ok=True)
    stats = get_stats()
    with open("dist/github-stats.svg", "w", encoding="utf-8") as f:
        f.write(generate_svg(stats, dark=False))
    with open("dist/github-stats-dark.svg", "w", encoding="utf-8") as f:
        f.write(generate_svg(stats, dark=True))
    print("Generated dist/github-stats.svg and dist/github-stats-dark.svg")
