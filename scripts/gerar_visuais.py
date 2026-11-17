"""Gera os títulos de seção e os cartões de projeto do README, em versão escura e clara.

Uso:
    python scripts/gerar_visuais.py              # grava em dist/
    python scripts/gerar_visuais.py --out=pasta

- Títulos: a lista SECOES abaixo (λ sobre, λ projetos, ...).
- Projetos: os repositórios FIXADOS no seu perfil do GitHub (se não houver nenhum, os 4 em que você
  mexeu por último). Os cartões são gerados e a seção "λ projetos" do README.md é reescrita sozinha,
  entre os marcadores <!-- projetos:inicio --> e <!-- projetos:fim -->.
  Sem token (ou se a busca falhar), não mexe nos projetos nem no README.
Só biblioteca padrão.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parent.parent
MONO = "ui-monospace,SFMono-Regular,'Cascadia Code',Menlo,Consolas,'Liberation Mono',monospace"
W = 800

TEMAS = {
    "dark": dict(card="#161b22", borda="#30363d", texto="#e6edf3", fraco="#8b949e", linha="#30363d",
                 azul="#58a6ff", laranja="#f0883e"),
    "light": dict(card="#ffffff", borda="#d0d7de", texto="#1f2328", fraco="#656d76", linha="#d8dee4",
                  azul="#0969da", laranja="#e16f24"),
}

# arquivo -> título que aparece depois do λ
SECOES = {
    "sobre": "sobre",
    "projetos": "projetos",
    "estudando": "estudando",
    "stack": "stack",
    "contribuicoes": "contribuições",
    "contato": "contato",
}


def mono_w(s, tam):
    return len(s) * tam * 0.6          # fonte monoespaçada: ~0.6 da altura por caractere


def caber(s, tam, max_w):
    if mono_w(s, tam) <= max_w:
        return s
    n = max(1, int(max_w / (tam * 0.6)) - 1)
    return s[:n].rstrip(" ,-") + "…"


def T(x, y, s, tam, cor, peso=400, ancora="start"):
    return ('<text x="%g" y="%g" font-size="%g" fill="%s" font-weight="%d" text-anchor="%s">%s</text>'
            % (x, y, tam, cor, peso, ancora, escape(s)))


# --------------------------------------------------------------------------- títulos de seção
def titulo(texto, c):
    H = 44
    tx = 30
    fim = tx + mono_w(texto, 20) + 6
    linha0 = fim + 24
    css = ("text{font-family:%s}"
           ".cur{animation:pisca 1.1s steps(1) infinite}"
           "@keyframes pisca{50%%{opacity:0}}"
           ".corre{animation:corre 6s ease-in-out infinite}"
           "@keyframes corre{0%%{transform:translateX(0)}50%%{transform:translateX(%dpx)}100%%{transform:translateX(0)}}"
           "@media (prefers-reduced-motion:reduce){.cur,.corre{animation:none}}"
           % (MONO, W - 2 - linha0 - 70))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
            '<style>%s</style>'
            '%s%s'
            '<rect class="cur" x="%g" y="13" width="10" height="20" rx="1" fill="%s"/>'
            '<path d="M%g 23H%d" stroke="%s"/>'
            '<rect class="corre" x="%g" y="22" width="70" height="2" rx="1" fill="%s"/>'
            '</svg>'
            % (W, H, W, H, escape(texto), css,
               T(2, 30, "λ", 22, c["laranja"], 700), T(tx, 30, texto, 20, c["azul"], 700),
               fim, c["laranja"], linha0, W - 2, c["linha"], linha0, c["azul"]))


# --------------------------------------------------------------------------- cartões de projeto
USUARIO = "PepeHenrque"
CAMPOS = ("nameWithOwner name description url primaryLanguage { name color } "
          "repositoryTopics(first: 4) { nodes { topic { name } } }")
QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: REPOSITORY) { nodes { ... on Repository { %s } } }
    repositories(first: 10, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: PUSHED_AT, direction: DESC}) { nodes { %s } }
  }
}
""" % (CAMPOS, CAMPOS)


def buscar_projetos():
    """repositórios fixados no perfil; se não houver, os 4 mais recentes. None se a busca falhar."""
    token = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    body = json.dumps({"query": QUERY, "variables": {"login": USUARIO}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": "pepe-readme"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            u = json.loads(r.read())["data"]["user"]
    except Exception as e:
        print("aviso: não consegui buscar os repositórios (%s); projetos e README ficam como estão" % e)
        return None
    fixados = [n for n in u["pinnedItems"]["nodes"] if n]
    if fixados:
        return fixados
    perfil = "%s/%s" % (USUARIO, USUARIO)
    return [n for n in u["repositories"]["nodes"] if n and n["nameWithOwner"] != perfil][:4]


def quebrar(texto, tam, max_w, max_linhas=2):
    linhas, atual = [], ""
    for p in texto.split():
        teste = (atual + " " + p).strip()
        if mono_w(teste, tam) <= max_w:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    linhas.append(atual)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas - 1] + [caber(" ".join(linhas[max_linhas - 1:]), tam, max_w)]
    return linhas


def cartao(info, c):
    CW, CH = 400, 132
    nome = info["name"]
    desc = info.get("description") or "sem descrição ainda"
    lang = info.get("primaryLanguage") or {}
    topicos = [t["topic"]["name"] for t in (info.get("repositoryTopics") or {}).get("nodes", [])]
    css = ("text{font-family:%s}"
           ".cresce{transform-box:fill-box;transform-origin:left center;animation:cresce .9s cubic-bezier(.3,.7,.2,1) .3s both}"
           "@keyframes cresce{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
           "@media (prefers-reduced-motion:reduce){.cresce{animation:none}}" % MONO)
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
         % (CW, CH, CW, CH, escape(nome)), "<style>%s</style>" % css,
         '<rect x=".5" y=".5" width="%d" height="%d" rx="8" fill="%s" stroke="%s"/>' % (CW - 1, CH - 1, c["card"], c["borda"])]
    direita = CW - 18
    if lang.get("name"):
        ln = caber(lang["name"], 12, 110)
        s.append(T(direita, 32, ln, 12, c["fraco"], 400, "end"))
        s.append('<circle cx="%g" cy="28" r="5" fill="%s"/>' % (direita - mono_w(ln, 12) - 10, lang.get("color") or c["fraco"]))
        direita -= mono_w(ln, 12) + 24
    s.append(T(18, 32, "λ", 15, c["laranja"], 700))
    s.append(T(36, 32, caber(nome, 15, direita - 44), 15, c["azul"], 700))
    for i, l in enumerate(quebrar(desc, 13, CW - 36)):
        s.append(T(18, 62 + i * 20, l, 13, c["texto"]))
    if topicos:
        s.append(T(18, CH - 22, caber("# " + " · ".join(topicos), 12, CW - 36), 12, c["fraco"]))
    s.append('<rect class="cresce" x="1" y="%d" width="64" height="2.5" rx="1.2" fill="%s"/>' % (CH - 3, c["laranja"]))
    s.append("</svg>")
    return "".join(s)


BASE = "https://raw.githubusercontent.com/%s/%s/output/" % (USUARIO, USUARIO)


def slug(info):
    return info["nameWithOwner"].replace("/", "-").lower()


def bloco_readme(projetos):
    linhas = ['<p align="center">']
    for info in projetos:
        linhas.append('<a href="%s"><picture>\n'
                      '  <source media="(prefers-color-scheme: dark)" srcset="%sprojeto-%s-dark.svg">\n'
                      '  <img src="%sprojeto-%s-light.svg" alt="%s" width="49%%">\n</picture></a>'
                      % (info["url"], BASE, slug(info), BASE, slug(info), escape(info["name"])))
    linhas.append("</p>")
    return "\n".join(linhas)


def atualizar_readme(projetos):
    arq = RAIZ / "README.md"
    txt = arq.read_text(encoding="utf-8")
    ini, fim = "<!-- projetos:inicio -->", "<!-- projetos:fim -->"
    if ini not in txt or fim not in txt:
        print("aviso: marcadores de projetos não encontrados no README; nada alterado")
        return
    antes, resto = txt.split(ini, 1)
    _, depois = resto.split(fim, 1)
    novo = antes + ini + "\n" + bloco_readme(projetos) + "\n" + fim + depois
    if novo != txt:
        arq.write_text(novo, encoding="utf-8")
        print("README: seção de projetos atualizada")
    else:
        print("README: projetos sem mudança")


def main():
    out = RAIZ / "dist"
    for a in sys.argv[1:]:
        if a.startswith("--out="):
            out = Path(a.split("=", 1)[1])
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for tema, c in TEMAS.items():
        for arq, txt in SECOES.items():
            (out / ("secao-%s-%s.svg" % (arq, tema))).write_text(titulo(txt, c), encoding="utf-8")
            n += 1
    projetos = buscar_projetos()
    if projetos:
        for tema, c in TEMAS.items():
            for info in projetos:
                (out / ("projeto-%s-%s.svg" % (slug(info), tema))).write_text(cartao(info, c), encoding="utf-8")
                n += 1
        if "--sem-readme" not in sys.argv:
            atualizar_readme(projetos)
    print("ok: %d arquivos em %s" % (n, out))


if __name__ == "__main__":
    main()
