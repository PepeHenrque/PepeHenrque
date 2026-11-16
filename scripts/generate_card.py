import os
import json
import urllib.request
from datetime import datetime

USERNAME = "PepeHenrque"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

def fetch_events():
    headers = {"User-Agent": "PepeCard"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    try:
        req = urllib.request.Request(f"https://api.github.com/users/{USERNAME}/events/public", headers=headers)
        with urllib.request.urlopen(req) as resp:
            events = json.loads(resp.read().decode("utf-8"))
            repo_counts = {}
            recent_lang = "TypeScript"
            for e in events:
                rname = e.get("repo", {}).get("name", "")
                if rname and rname != f"{USERNAME}/{USERNAME}":
                    repo_counts[rname] = repo_counts.get(rname, 0) + 1
            top_repo = max(repo_counts.items(), key=lambda x: x[1])[0] if repo_counts else ""
            # Get language from top repo
            if top_repo:
                try:
                    req2 = urllib.request.Request(f"https://api.github.com/repos/{top_repo}/languages", headers=headers)
                    with urllib.request.urlopen(req2) as resp2:
                        langs = json.loads(resp2.read().decode("utf-8"))
                        if langs:
                            recent_lang = max(langs.items(), key=lambda x: x[1])[0]
                except:
                    pass
            return top_repo.split("/")[-1] if "/" in top_repo else top_repo, recent_lang
    except Exception as e:
        print("Events error:", e)
    return "apts", "TypeScript"

def get_stats():
    stars, commits, prs, issues, contributed = 28, 224, 29, 0, 31
    days = []

    if TOKEN:
        gql = """query($login:String!){user(login:$login){
            repositoriesContributedTo(first:1,contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
            pullRequests(first:1){totalCount}
            issues(first:1){totalCount}
            contributionsCollection{
                totalCommitContributions restrictedContributionsCount
                contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}
            }
            repositories(first:100,ownerAffiliations:OWNER,isFork:false){nodes{stargazerCount}}
        }}"""
        try:
            data = json.dumps({"query": gql, "variables": {"login": USERNAME}}).encode()
            req = urllib.request.Request("https://api.github.com/graphql", data=data, headers={
                "User-Agent": "PepeCard", "Content-Type": "application/json",
                "Authorization": f"Bearer {TOKEN}"
            })
            with urllib.request.urlopen(req) as resp:
                u = json.loads(resp.read())["data"]["user"]
                c = u["contributionsCollection"]
                commits = c["totalCommitContributions"] + c["restrictedContributionsCount"]
                prs = u["pullRequests"]["totalCount"]
                issues = u["issues"]["totalCount"]
                contributed = u["repositoriesContributedTo"]["totalCount"]
                stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
                for w in c["contributionCalendar"]["weeks"]:
                    for d in w["contributionDays"]:
                        days.append(d["contributionCount"])
        except Exception as e:
            print("GQL error:", e)

    if not days:
        days = [0]*300 + [1, 2, 0, 5, 12, 25, 45, 60, 40, 30, 85, 140, 160]

    # Rank
    sc = commits*2 + prs*3 + issues*1 + stars*4 + contributed*3
    if sc >= 1000: rank = "S"
    elif sc >= 500: rank = "A+"
    elif sc >= 250: rank = "A"
    elif sc >= 100: rank = "B+"
    elif sc >= 50: rank = "B"
    else: rank = "B-"

    # Streak
    total_c = sum(days)
    cur, lon, t = 0, 0, 0
    for v in days:
        if v > 0:
            t += 1
            if t > lon: lon = t
        else:
            t = 0
    for v in reversed(days):
        if v > 0: cur += 1
        elif cur > 0: break
    cur = max(cur, 0)
    lon = max(lon, cur)

    # Sparkline: aggregate to 40 points
    step = max(1, len(days) // 40)
    pts = []
    for i in range(0, len(days), step):
        pts.append(sum(days[i:i+step]))
    pts = pts[-40:]

    top_repo, recent_lang = fetch_events()

    return {
        "stars": stars, "commits": commits, "prs": prs, "issues": issues,
        "contributed": contributed, "rank": rank,
        "total": total_c, "cur_streak": cur, "lon_streak": lon,
        "pts": pts, "top_repo": top_repo, "recent_lang": recent_lang
    }

def make_svg(d):
    # --- Graph path (smooth cubic bezier) ---
    pts = d["pts"]
    mx = max(pts) if pts and max(pts) > 0 else 1
    gx, gy, gw, gh = 18, 278, 459, 68
    st = gw / max(1, len(pts)-1)
    coords = [(gx + i*st, gy - (v/mx)*gh) for i, v in enumerate(pts)]
    
    path = f"M{coords[0][0]:.1f},{coords[0][1]:.1f}"
    for i in range(1, len(coords)):
        p, c = coords[i-1], coords[i]
        mx1 = p[0] + (c[0]-p[0])/2
        path += f" C{mx1:.1f},{p[1]:.1f},{mx1:.1f},{c[1]:.1f},{c[0]:.1f},{c[1]:.1f}"
    fill_path = f"{path} L{coords[-1][0]:.1f},{gy} L{coords[0][0]:.1f},{gy} Z"

    # --- Rank gauge arc ---
    # SVG circle arc: r=20, circumference=125.66
    circ = 125.66
    # Score percentage (rough)
    sc = d["commits"]*2 + d["prs"]*3 + d["issues"]*1 + d["stars"]*4 + d["contributed"]*3
    pct = min(sc / 800, 1.0)  # normalize to 800 as "S" threshold
    filled = circ * pct
    gap = circ - filled

    # --- Contribution squares (16 blocks) ---
    greens = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
    blocks = ""
    for i in range(16):
        color = greens[min(4, max(1, (i % 4) + 1))]
        bx = 310 + i * 11
        blocks += f'<rect x="{bx}" y="13" width="8" height="8" rx="2" fill="{color}"/>'

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="360" viewBox="0 0 495 360">
  <style>
    @keyframes draw {{ from {{ stroke-dashoffset: 800 }} to {{ stroke-dashoffset: 0 }} }}
    @keyframes fill-up {{ from {{ opacity: 0 }} to {{ opacity: 1 }} }}
    @keyframes gauge {{ from {{ stroke-dashoffset: {circ:.1f} }} to {{ stroke-dashoffset: {gap:.1f} }} }}
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif; }}
  </style>

  <!-- Background -->
  <rect x="0.5" y="0.5" width="494" height="359" rx="6" fill="#fff" stroke="#d0d7de"/>

  <!-- === TOP BAR: Name + Squares === -->
  <text x="18" y="27" fill="#0969da" font-weight="700" font-size="16">Pedro Henrique</text>
  <text x="155" y="27" fill="#656d76" font-weight="400" font-size="12">@PepeHenrque</text>
  {blocks}
  <text x="486" y="27" fill="#656d76" font-size="10" text-anchor="end">{d['contributed']} repos</text>

  <!-- Divider -->
  <line x1="18" y1="38" x2="477" y2="38" stroke="#d8dee4" stroke-width="0.6"/>

  <!-- === BADGES: Active Repo + Recent Lang === -->
  <rect x="18" y="46" width="180" height="20" rx="10" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.6"/>
  <text x="30" y="60" fill="#656d76" font-size="11">📦 Active: <tspan fill="#24292f" font-weight="600">{d['top_repo']}</tspan></text>

  <rect x="206" y="46" width="160" height="20" rx="10" fill="#f6f8fa" stroke="#d0d7de" stroke-width="0.6"/>
  <text x="218" y="60" fill="#656d76" font-size="11">🔵 Recent: <tspan fill="#24292f" font-weight="600">{d['recent_lang']}</tspan></text>

  <!-- === LEFT COLUMN: Stats === -->
  <!-- Stars -->
  <g transform="translate(18, 86)">
    <circle cx="7" cy="7" r="7" fill="#faf0c8"/>
    <text x="7" y="10.5" fill="#9a6700" font-size="9" text-anchor="middle" font-weight="700">★</text>
    <text x="20" y="11" fill="#656d76" font-size="13">Stars</text>
    <text x="75" y="11" fill="#24292f" font-size="13" font-weight="600">{d['stars']}</text>
  </g>

  <!-- Commits -->
  <g transform="translate(18, 112)">
    <circle cx="7" cy="7" r="7" fill="#ddf4ff"/>
    <text x="7" y="11" fill="#0969da" font-size="9" text-anchor="middle" font-weight="700">⊙</text>
    <text x="20" y="11" fill="#656d76" font-size="13">Commits</text>
    <text x="90" y="11" fill="#24292f" font-size="13" font-weight="600">{d['commits']}</text>
  </g>

  <!-- PRs -->
  <g transform="translate(18, 138)">
    <circle cx="7" cy="7" r="7" fill="#dafbe1"/>
    <text x="7" y="11" fill="#1a7f37" font-size="9" text-anchor="middle" font-weight="700">⑂</text>
    <text x="20" y="11" fill="#656d76" font-size="13">Pull Requests</text>
    <text x="120" y="11" fill="#24292f" font-size="13" font-weight="600">{d['prs']}</text>
  </g>

  <!-- Issues -->
  <g transform="translate(18, 164)">
    <circle cx="7" cy="7" r="7" fill="#ffebe9"/>
    <text x="7" y="11" fill="#cf222e" font-size="9" text-anchor="middle" font-weight="700">!</text>
    <text x="20" y="11" fill="#656d76" font-size="13">Issues</text>
    <text x="75" y="11" fill="#24292f" font-size="13" font-weight="600">{d['issues']}</text>
  </g>

  <!-- === CENTER: Streak === -->
  <!-- Vertical divider -->
  <line x1="165" y1="80" x2="165" y2="185" stroke="#d8dee4" stroke-width="0.6"/>

  <g transform="translate(220, 85)">
    <text x="0" y="12" fill="#656d76" font-size="11" font-weight="500">TOTAL</text>
    <text x="0" y="35" fill="#24292f" font-size="22" font-weight="700">{d['total']}</text>

    <text x="80" y="12" fill="#cf222e" font-size="11" font-weight="600">CURRENT STREAK 🔥</text>
    <text x="80" y="35" fill="#cf222e" font-size="22" font-weight="700">{d['cur_streak']} <tspan font-size="13" fill="#656d76">days</tspan></text>

    <text x="0" y="70" fill="#656d76" font-size="11" font-weight="500">LONGEST</text>
    <text x="0" y="90" fill="#24292f" font-size="18" font-weight="600">{d['lon_streak']} <tspan font-size="12" fill="#656d76">days</tspan></text>
  </g>

  <!-- === RIGHT: Rank Gauge === -->
  <line x1="415" y1="80" x2="415" y2="185" stroke="#d8dee4" stroke-width="0.6"/>

  <g transform="translate(452, 130)">
    <!-- Background ring -->
    <circle cx="0" cy="0" r="20" fill="none" stroke="#e8f1ff" stroke-width="4"/>
    <!-- Animated gauge -->
    <circle cx="0" cy="0" r="20" fill="none" stroke="#0969da" stroke-width="4"
            stroke-dasharray="{circ:.1f}" stroke-dashoffset="{gap:.1f}"
            stroke-linecap="round" transform="rotate(-90)">
      <animate attributeName="stroke-dashoffset" from="{circ:.1f}" to="{gap:.1f}" dur="1.5s" fill="freeze"/>
    </circle>
    <text x="0" y="7" fill="#24292f" font-size="18" font-weight="800" text-anchor="middle">{d['rank']}</text>
    <text x="0" y="33" fill="#656d76" font-size="9" font-weight="600" text-anchor="middle">RANK</text>
  </g>

  <!-- === Divider before graph === -->
  <line x1="18" y1="195" x2="477" y2="195" stroke="#d8dee4" stroke-width="0.6"/>

  <!-- === BOTTOM: Contribution Graph === -->
  <text x="18" y="212" fill="#656d76" font-size="10" font-weight="600" letter-spacing="0.5">CONTRIBUTIONS OVER TIME</text>

  <!-- Graph fill (animated) -->
  <path d="{fill_path}" fill="#2da44e" opacity="0.12">
    <animate attributeName="opacity" from="0" to="0.12" dur="1.8s" fill="freeze"/>
  </path>

  <!-- Graph line (animated draw) -->
  <path d="{path}" fill="none" stroke="#1a7f37" stroke-width="2" stroke-linecap="round"
        stroke-dasharray="800" stroke-dashoffset="800">
    <animate attributeName="stroke-dashoffset" from="800" to="0" dur="2s" fill="freeze"/>
  </path>

  <!-- Dot at last point -->
  <circle cx="{coords[-1][0]:.1f}" cy="{coords[-1][1]:.1f}" r="3" fill="#1a7f37">
    <animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="1.8s" fill="freeze"/>
  </circle>
  <circle cx="{coords[-1][0]:.1f}" cy="{coords[-1][1]:.1f}" r="6" fill="#1a7f37" opacity="0">
    <animate attributeName="opacity" values="0;0.3;0" dur="2s" begin="2s" repeatCount="indefinite"/>
    <animate attributeName="r" values="3;8;3" dur="2s" begin="2s" repeatCount="indefinite"/>
  </circle>

  <!-- === Footer === -->
  <line x1="18" y1="290" x2="477" y2="290" stroke="#d8dee4" stroke-width="0.4"/>
  <text x="248" y="306" fill="#afb8c1" font-size="9" text-anchor="middle">Auto-generated daily · github.com/PepeHenrque</text>
</svg>'''
    return svg

if __name__ == "__main__":
    d = get_stats()
    svg = make_svg(d)
    with open("github-stats.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Done! Card generated.")
