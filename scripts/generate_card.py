"""Gera o cartão de estatísticas do perfil (github-stats.svg), 800x400, fundo branco.

Uso:
    python scripts/generate_card.py           # dados reais (precisa de GITHUB_TOKEN ou METRICS_TOKEN)
    python scripts/generate_card.py --mock    # dados de exemplo, para testar sem token
    python scripts/generate_card.py --mock --big   # valores grandes, para testar o layout

Só biblioteca padrão.
"""
import json
import math
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

USER = "PepeHenrque"
NAME = "Pedro Henrique"
OUT = "github-stats.svg"
TZ = timezone(timedelta(hours=-3))          # America/Sao_Paulo (sem horário de verão desde 2019)

W, H = 700, 420
PAD = 24
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
C_TEXT, C_MUTED, C_LINE, C_BORDER = "#1f2328", "#656d76", "#d8dee4", "#d0d7de"
C_BLUE, C_GREEN, C_ORANGE = "#0969da", "#1a7f37", "#e16f24"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


# --------------------------------------------------------------------------- dados
QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes { stargazerCount }
    }
    recent: repositories(first: 15, ownerAffiliations: [OWNER, COLLABORATOR],
                         orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes { name nameWithOwner primaryLanguage { name color } }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
      commitContributionsByRepository(maxRepositories: 10) {
        repository { name nameWithOwner }
        contributions { totalCount }
      }
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_real():
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Sem token: defina GITHUB_TOKEN/METRICS_TOKEN ou use --mock.")
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "pepe-card"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.loads(r.read())
    if payload.get("errors"):
        sys.exit("Erro da API: %s" % payload["errors"])
    u = payload["data"]["user"]
    cc = u["contributionsCollection"]
    days = [(date.fromisoformat(d["date"]), d["contributionCount"])
            for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    own = USER + "/" + USER
    repos = [(x["repository"]["name"], x["contributions"]["totalCount"])
             for x in cc["commitContributionsByRepository"] if x["repository"]["nameWithOwner"] != own]
    lang = None
    for n in u["recent"]["nodes"]:
        if n["nameWithOwner"] != own and n["primaryLanguage"]:
            lang = (n["primaryLanguage"]["name"], n["primaryLanguage"]["color"] or C_MUTED, n["name"])
            break
    return {
        "total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "days": days,
        "repos": sorted(repos, key=lambda t: -t[1])[:3],
        "lang": lang,
    }


def fetch_mock(big=False):
    today = datetime.now(TZ).date()
    start = today - timedelta(days=364)
    days = []
    for i in range(365):
        d = start + timedelta(days=i)
        t = i / 364
        base = 0 if t < 0.55 else (t - 0.55) * 9
        wave = max(0.0, math.sin(i / 9.0)) * base
        n = int(round(wave + (3 if i % 11 == 0 and t > 0.4 else 0)))
        days.append((d, n))
    # sequência atual de 3 dias, com um dia vazio antes
    days[-4] = (days[-4][0], 0)
    for k in (1, 2, 3):
        days[-k] = (days[-k][0], max(1, days[-k][1]))
    if big:
        return {"total": 12345, "commits": 12345, "reviews": 900, "prs": 4321, "issues": 987, "stars": 54321,
                "followers": 9999, "days": [(d, n * 9) for d, n in days],
                "repos": [("um-repositorio-com-nome-muito-muito-comprido", 4321), ("compiladores", 1200),
                          ("arduino-estacao-meteorologica", 640)],
                "lang": ("Jupyter Notebook", "#DA5B0B", "repositorio-com-nome-enorme-de-teste")}
    return {"total": 279, "commits": 222, "reviews": 0, "prs": 29, "issues": 3, "stars": 24, "followers": 12,
            "days": days, "repos": [("quantum-ai", 96), ("terraform-lab", 54), ("arduino-projetos", 31)],
            "lang": ("Python", "#3572A5", "quantum-ai")}


# --------------------------------------------------------------------------- cálculos
def streaks(days):
    today = datetime.now(TZ).date()
    days = [(d, n) for d, n in sorted(days) if d <= today]
    # atual: conta para trás a partir de hoje; se hoje ainda está em 0, começa de ontem
    cur, cur_start, cur_end = 0, None, None
    i = len(days) - 1
    if i >= 0 and days[i][1] == 0:
        i -= 1
    while i >= 0 and days[i][1] > 0:
        cur += 1
        cur_start = days[i][0]
        cur_end = cur_end or days[i][0]
        i -= 1
    best, best_rng, run, run_start = 0, (None, None), 0, None
    for d, n in days:
        if n > 0:
            run_start = run_start or d
            run += 1
            if run > best:
                best, best_rng = run, (run_start, d)
        else:
            run, run_start = 0, None
    return (cur, cur_start, cur_end), (best, *best_rng)


def rank(s):
    """mesma ideia do github-readme-stats: percentil a partir de CDFs ponderadas."""
    exp_cdf = lambda x: 1 - 2 ** (-x)
    log_cdf = lambda x: x / (1 + x)
    parts = [(2, exp_cdf(s["commits"] / 250)), (3, exp_cdf(s["prs"] / 50)), (1, exp_cdf(s["issues"] / 25)),
             (1, exp_cdf(s["reviews"] / 2)), (4, log_cdf(s["stars"] / 50)), (1, log_cdf(s["followers"] / 10))]
    pct = (1 - sum(w * c for w, c in parts) / sum(w for w, _ in parts)) * 100
    for lim, lvl in ((1, "S"), (12.5, "A+"), (25, "A"), (37.5, "A-"), (50, "B+"), (62.5, "B"), (75, "B-"),
                     (87.5, "C+"), (100, "C")):
        if pct <= lim:
            return lvl, pct
    return "C", pct


def weekly(days):
    days = sorted(days)[-364:]
    weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
    return [(w[0][0], sum(n for _, n in w)) for w in weeks]


# --------------------------------------------------------------------------- helpers de desenho
def fmt(n):
    return "{:,}".format(n).replace(",", ".")


def dt(d):
    return "%d %s" % (d.day, MESES[d.month - 1]) if d else "–"


def text_w(s, size, bold=False):
    """largura aproximada em px (fontes de sistema)."""
    k = 0.60 if bold else 0.56
    narrow = sum(1 for c in s if c in "iljtf.,:;|!'I ·")
    wide = sum(1 for c in s if c in "mwMW@%")
    return size * (k * (len(s) - narrow - wide) + 0.30 * narrow + 0.85 * wide)


def fit(s, size, max_w, bold=False):
    if text_w(s, size, bold) <= max_w:
        return s
    while s and text_w(s + "…", size, bold) > max_w:
        s = s[:-1]
    return s.rstrip("-_ ") + "…"


def T(x, y, s, size=13, color=C_TEXT, weight=400, anchor="start", cls=""):
    c = ' class="%s"' % cls if cls else ""
    return ('<text x="%g" y="%g" font-size="%g" fill="%s" font-weight="%d" text-anchor="%s"%s>%s</text>'
            % (x, y, size, color, weight, anchor, c, escape(s)))


# ícones 16x16 desenhados com traço (estilo Octicons)
def icon(name, x, y, color=C_MUTED):
    g = '<g transform="translate(%g %g)" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' % (x, y, color)
    body = {
        "contrib": '<rect x="2" y="2" width="5" height="5" rx="1"/><rect x="9" y="2" width="5" height="5" rx="1"/>'
                   '<rect x="2" y="9" width="5" height="5" rx="1"/><rect x="9" y="9" width="5" height="5" rx="1" fill="%s"/>' % color,
        "commit": '<circle cx="8" cy="8" r="3"/><path d="M1 8h4M11 8h4"/>',
        "pr": '<circle cx="4" cy="3.5" r="1.8"/><circle cx="4" cy="12.5" r="1.8"/><circle cx="12" cy="12.5" r="1.8"/>'
              '<path d="M4 5.3v5.4M12 10.7V6.5a2 2 0 0 0-2-2H7.5M9 3 7.5 4.5 9 6"/>',
        "issue": '<circle cx="8" cy="8" r="6.2"/><circle cx="8" cy="8" r="1" fill="%s"/>' % color,
        "star": '<path d="M8 1.8l1.9 3.9 4.2.6-3 3 .7 4.2L8 11.5l-3.8 2 .7-4.2-3-3 4.2-.6z"/>',
        "code": '<path d="M5.5 4 1.5 8l4 4M10.5 4l4 4-4 4"/>',
        "repo": '<path d="M3 13.5V3a1.5 1.5 0 0 1 1.5-1.5H13v10H4.5A1.5 1.5 0 0 0 3 13a1.5 1.5 0 0 0 1.5 1.5H13"/>',
        "trophy": '<path d="M4.5 2h7v4a3.5 3.5 0 0 1-7 0zM4.5 3.5H2v1a2.5 2.5 0 0 0 2.6 2.5M11.5 3.5H14v1a2.5 2.5 0 0 1-2.6 2.5M8 9.5v3M5.5 14h5"/>',
        "calendar": '<rect x="2" y="3" width="12" height="11" rx="1.5"/><path d="M2 6.5h12M5 1.5v3M11 1.5v3"/>',
    }[name]
    return g + body + "</g>"


FLAME = ('<path d="M8 1.2c.6 2.3 3.8 3.9 3.8 7.6A3.8 3.8 0 0 1 4.2 9c0-1.6.8-2.6 1.6-3.4.1 1.1.6 1.9 1.4 2.1'
         '-.4-2.4.1-4.6.8-6.5z" fill="%s"/><path d="M8 8.2c.3 1 1.6 1.6 1.6 3a1.6 1.6 0 0 1-3.2.1c0-.8.5-1.3 1-1.7'
         '.1.4.3.6.6.7-.1-.8 0-1.5 0-2.1z" fill="#fff3"/>' % C_ORANGE)


# --------------------------------------------------------------------------- SVG
def build(s):
    (cur, cs, ce), (best, bs, be) = streaks(s["days"])
    lvl, pct = rank(s)
    now = datetime.now(TZ)
    out = []
    add = out.append

    # ---- cabeçalho
    add('<g class="in d0">')
    add(T(PAD, 48, NAME, 22, C_TEXT, 600))
    add(T(PAD + text_w(NAME, 22, True) + 10, 48, "@" + USER, 15, C_MUTED))
    add('</g>')
    add('<path d="M%d 68H%d" stroke="%s"/>' % (PAD, W - PAD, C_LINE))

    # ---- métricas (coluna esquerda)
    LX, VX, ROW, Y0 = PAD, 200, 26, 100
    rows = [("contrib", "Contribuições (ano)", fmt(s["total"])),
            ("commit", "Commits (ano)", fmt(s["commits"])),
            ("pr", "Pull Requests", fmt(s["prs"])),
            ("issue", "Issues", fmt(s["issues"])),
            ("star", "Stars recebidas", fmt(s["stars"]))]
    add('<g class="in d1">')
    for i, (ic, label, val) in enumerate(rows):
        y = Y0 + i * ROW
        add(icon(ic, LX, y - 12))
        add(T(LX + 26, y, label, 14, C_MUTED))
        add(T(VX, y, val, 16, C_TEXT, 700))
    y = Y0 + 5 * ROW
    add(icon("code", LX, y - 12))
    add(T(LX + 26, y, "Linguagem recente", 14, C_MUTED))
    if s["lang"]:
        name, color, repo = s["lang"]
        add('<circle cx="%g" cy="%g" r="5" fill="%s"/>' % (VX + 5, y - 4.5, color))
        nm = fit(name, 15, 116, True)
        add(T(VX + 16, y, nm, 15, C_TEXT, 700))
        rx = VX + 16 + text_w(nm, 15, True) + 8
        if 336 - rx > 24:
            add(T(rx, y, fit(repo, 12, 336 - rx), 12, C_MUTED))
    else:
        add(T(VX, y, "–", 15, C_MUTED))
    add('</g>')
    add('<path d="M350 86V236" stroke="%s"/>' % C_LINE)

    # ---- coluna direita: nota | sequência atual | maior sequência (estilo streak-stats)
    CY, RR = 140, 34
    cols = (406, 518, 630)
    circ = 2 * math.pi * RR

    # nota
    RX = cols[0]
    fill = max(0.02, min(1.0, (100 - pct) / 100))
    add('<g class="in d2">')
    add('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="#eaeef2" stroke-width="7"/>' % (RX, CY, RR))
    add('<circle class="ring" cx="%g" cy="%g" r="%g" fill="none" stroke="%s" stroke-width="7" stroke-linecap="round"'
        ' stroke-dasharray="%.2f" style="--c:%.2f;--o:%.2f" stroke-dashoffset="%.2f" transform="rotate(-90 %g %g)"/>'
        % (RX, CY, RR, C_BLUE, circ, circ, circ * (1 - fill), circ * (1 - fill), RX, CY))
    add(T(RX, CY + 9, lvl, 25, C_TEXT, 700, "middle"))
    add(T(RX, CY + RR + 26, "Nota", 12, C_BLUE, 700, "middle"))
    add(T(RX, CY + RR + 44, "top %.0f%%" % max(1, pct), 11.5, C_MUTED, anchor="middle"))
    add('</g>')

    # sequência atual: anel laranja com a chama no topo
    SX = cols[1]
    add('<g class="in d3">')
    add('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="%s" stroke-width="5"/>' % (SX, CY, RR, C_ORANGE))
    add('<circle cx="%g" cy="%g" r="13" fill="#fff"/>' % (SX, CY - RR))          # abre espaço no anel
    add('<g transform="translate(%g %g) scale(1.5)"><g class="flame">%s</g></g>' % (SX - 12, CY - RR - 14, FLAME))
    add(T(SX, CY + 10, fmt(cur), 28, C_TEXT, 700, "middle"))
    add(T(SX, CY + RR + 26, "Sequência atual", 12, C_ORANGE, 700, "middle"))
    add(T(SX, CY + RR + 44, ("%s – %s" % (dt(cs), dt(ce))) if cur else "comece hoje", 11.5, C_MUTED, anchor="middle"))
    add('</g>')

    # maior sequência
    BX = cols[2]
    add('<g class="in d3">')
    add(T(BX, CY + 10, fmt(best), 28, C_TEXT, 700, "middle"))
    add(T(BX, CY + RR + 26, "Maior sequência", 12, C_TEXT, 600, "middle"))
    add(T(BX, CY + RR + 44, ("%s – %s" % (dt(bs), dt(be))) if best else "–", 11.5, C_MUTED, anchor="middle"))
    add('</g>')
    for x in ((cols[0] + cols[1]) / 2, (cols[1] + cols[2]) / 2):
        add('<path d="M%g 96V226" stroke="%s"/>' % (x, C_LINE))

    add('<path d="M%d 250H%d" stroke="%s"/>' % (PAD, W - PAD, C_LINE))

    # ---- onde estou contribuindo (esquerda)
    add('<g class="in d4">')
    add(icon("repo", PAD, 268))
    add(T(PAD + 24, 281, "Onde estou contribuindo", 14, C_TEXT, 700))
    top = max([n for _, n in s["repos"]] or [1])
    BW = 300 - PAD
    for i, (name, n) in enumerate(s["repos"]):
        y = 312 + i * 32
        num = fmt(n) + " commits"
        add(T(PAD, y, fit(name, 13, BW - text_w(num, 12) - 12), 13, C_TEXT, 600))
        add(T(PAD + BW, y, num, 12, C_MUTED, anchor="end"))
        add('<rect x="%d" y="%d" width="%d" height="6" rx="3" fill="#eaeef2"/>' % (PAD, y + 6, BW))
        add('<rect class="bar" style="animation-delay:%.2fs" x="%d" y="%d" width="%.1f" height="6" rx="3" fill="%s"/>'
            % (1.2 + i * 0.12, PAD, y + 6, max(6, BW * n / top), C_BLUE))
    if not s["repos"]:
        add(T(PAD, 312, "Nenhum commit no último ano", 13, C_MUTED))
    add('</g>')
    add('<path d="M324 266V392" stroke="%s"/>' % C_LINE)

    # ---- contribuições no último ano (direita): gráfico de área por semana
    weeks = weekly(s["days"])
    GX0, GX1, GY0, GY1 = 348, W - PAD, 302, 374
    add('<g class="in d5">')
    add(icon("calendar", GX0, 268))
    add(T(GX0 + 24, 281, "Contribuições no ano", 14, C_TEXT, 700))
    peak = max([n for _, n in weeks] or [1]) or 1
    add(T(GX1, 281, "pico %s/sem." % fmt(peak), 11.5, C_MUTED, anchor="end"))
    pts = []
    for i, (_, n) in enumerate(weeks):
        x = GX0 + (GX1 - GX0) * i / max(1, len(weeks) - 1)
        y = GY1 - (GY1 - GY0) * n / peak
        pts.append((x, y))
    # curva suave (Catmull-Rom -> Bézier), sem passar abaixo do eixo
    d = "M%.1f %.1f" % pts[0]
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(0, i - 1)], pts[i], pts[i + 1]
        p3 = pts[min(len(pts) - 1, i + 2)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(GY1, p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(GY1, p2[1] - (p3[1] - p1[1]) / 6))
        d += " C%.1f %.1f %.1f %.1f %.1f %.1f" % (c1 + c2 + p2)
    area = d + " L%.1f %d L%.1f %d Z" % (pts[-1][0], GY1, pts[0][0], GY1)
    add('<defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s" stop-opacity=".28"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient></defs>' % (C_GREEN, C_GREEN))
    add('<path d="M%d %dH%d" stroke="%s"/>' % (GX0, GY1, GX1, C_LINE))
    add('<path class="area" d="%s" fill="url(#ga)"/>' % area)
    add('<path class="line" d="%s" pathLength="1" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
        % (d, C_GREEN))
    lx, ly = pts[-1]
    add('<circle class="pulse" cx="%.1f" cy="%.1f" r="4" fill="%s"/>' % (lx, ly, C_GREEN))
    add('<circle cx="%.1f" cy="%.1f" r="3" fill="%s" stroke="#fff" stroke-width="1.5"/>' % (lx, ly, C_GREEN))
    # rótulos de mês (só quando o mês muda e há espaço)
    last_x = -99
    for i, (d0, _) in enumerate(weeks):
        if i == 0 or d0.month != weeks[i - 1][0].month:
            x = GX0 + (GX1 - GX0) * i / max(1, len(weeks) - 1)
            if x - last_x >= 24 and x <= GX1 - 12:
                add(T(x, GY1 + 15, MESES[d0.month - 1], 10.5, C_MUTED, anchor="middle" if i else "start"))
                last_x = x
    add('</g>')

    # ---- rodapé
    add(T(PAD, 406, "Atualizado em %s · America/Sao_Paulo" % now.strftime("%d/%m/%Y"), 10.5, "#8c959f"))

    css = """
text{font-family:%s}
.in{animation:in .6s cubic-bezier(.2,.7,.2,1) both}
.d0{animation-delay:.05s}.d1{animation-delay:.2s}.d2{animation-delay:.35s}.d3{animation-delay:.5s}
.d4{animation-delay:.65s}.d5{animation-delay:.8s}
@keyframes in{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.ring{animation:ring 1.3s cubic-bezier(.3,.7,.2,1) .5s both}
@keyframes ring{from{stroke-dashoffset:var(--c)}to{stroke-dashoffset:var(--o)}}
.bar{transform-box:fill-box;transform-origin:left center;animation:bar .9s cubic-bezier(.3,.7,.2,1) both}
@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.line{stroke-dasharray:1;animation:draw 1.5s ease-in-out 1s both}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
.area{animation:fade .8s ease 1.9s both}
@keyframes fade{from{opacity:0}to{opacity:1}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.2s ease-out 2.5s infinite;opacity:0}
@keyframes pulse{0%%{opacity:.5;transform:scale(1)}100%%{opacity:0;transform:scale(3)}}
.flame{transform-box:fill-box;transform-origin:50%% 100%%;animation:flame 1.6s ease-in-out infinite}
@keyframes flame{0%%,100%%{transform:scale(1) rotate(0)}30%%{transform:scale(1.06,.95) rotate(-3deg)}60%%{transform:scale(.96,1.05) rotate(3deg)}}
@media (prefers-reduced-motion:reduce){.in,.ring,.bar,.line,.area,.pulse,.flame{animation:none}}
""" % FONT

    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
            'aria-label="Estatísticas do GitHub de %s">\n<title>Estatísticas do GitHub de %s</title>\n'
            '<style>%s</style>\n'
            '<rect x=".5" y=".5" width="%d" height="%d" rx="8" fill="#fff" stroke="%s"/>\n%s\n</svg>\n'
            % (W, H, W, H, NAME, NAME, css, W - 1, H - 1, C_BORDER, "\n".join(out)))


def main():
    mock = "--mock" in sys.argv
    data = fetch_mock(big="--big" in sys.argv) if mock else fetch_real()
    out = OUT
    for a in sys.argv[1:]:
        if a.startswith("--out="):
            out = a.split("=", 1)[1]
    with open(out, "w", encoding="utf-8") as f:
        f.write(build(data))
    print("ok:", out)


if __name__ == "__main__":
    main()
