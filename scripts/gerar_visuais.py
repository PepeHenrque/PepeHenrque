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
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

TEMAS = {
    "dark": dict(card="#161b22", borda="#30363d", texto="#e6edf3", fraco="#8b949e", linha="#30363d",
                 azul="#58a6ff", laranja="#f0883e"),
    "light": dict(card="#ffffff", borda="#d0d7de", texto="#1f2328", fraco="#656d76", linha="#d8dee4",
                  azul="#0969da", laranja="#e16f24"),
}

# arquivo -> título que aparece depois do λ
SECOES = {
    "tecnologias": "Tecnologias",
    "estatisticas": "Estatísticas",
    "contribuicoes": "Contribuições",
    "projetos": "Projetos",
}
NOME = "Pedro Henrique"


def mono_w(s, tam):
    return len(s) * tam * 0.6          # fonte monoespaçada: ~0.6 da altura por caractere


# larguras (em "em") de Arial/Helvetica em negrito; dão uma boa estimativa para a fonte do GitHub
LARG = dict(zip("abcdefghijklmnopqrstuvwxyz",
                [.556, .611, .556, .611, .556, .333, .611, .611, .278, .278, .556, .278, .889, .611, .611, .611,
                 .611, .389, .556, .333, .611, .556, .778, .556, .556, .5]))
LARG.update(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                [.722, .722, .722, .722, .667, .611, .778, .722, .278, .556, .722, .611, .833, .722, .778, .667,
                 .778, .722, .667, .611, .722, .667, .944, .667, .667, .611]))
LARG.update({c: LARG[b] for c, b in zip("áàâãéêíóôõúçÁÉÍÓÚÇ", "aaaaeeiooouc" + "AEIOUC")})
LARG.update({" ": .278, "-": .333, ".": .278})


def sans_w(s, tam):
    return tam * sum(LARG.get(ch, .6) for ch in s)


def caber(s, tam, max_w):
    if mono_w(s, tam) <= max_w:
        return s
    n = max(1, int(max_w / (tam * 0.6)) - 1)
    return s[:n].rstrip(" ,-") + "…"


def T(x, y, s, tam, cor, peso=400, ancora="start"):
    return ('<text x="%g" y="%g" font-size="%g" fill="%s" font-weight="%d" text-anchor="%s">%s</text>'
            % (x, y, tam, cor, peso, ancora, escape(s)))


# --------------------------------------------------------------------------- títulos de seção
def titulo(texto, c, tam=21, lambda_=True, H=44):
    tx = 30 if lambda_ else 2
    base = round(H * 0.68)
    fim = tx + sans_w(texto, tam) + round(tam * 0.45)
    x0 = fim + 24
    comp = W - 2 - x0
    ch = round(tam * 0.95)
    css = (".t{font-family:%s}.l{font-family:%s}"
           ".cur{animation:pisca 1.1s steps(1) infinite}"
           "@keyframes pisca{50%%{opacity:0}}"
           ".brilho{stroke-dasharray:80 %d;animation:corre 5s linear infinite}"
           "@keyframes corre{from{stroke-dashoffset:80}to{stroke-dashoffset:-%d}}"
           % (SANS, MONO, comp, comp))
    lam = ('<text class="l" x="2" y="%d" font-size="22" fill="%s" font-weight="700">λ</text>' % (base, c["laranja"])
           if lambda_ else "")
    meio = base - tam * 0.35
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
            '<style>%s</style>%s'
            '<text class="t" x="%g" y="%d" font-size="%g" fill="%s" font-weight="600">%s</text>'
            '<rect class="cur" x="%g" y="%g" width="%g" height="%d" rx="1" fill="%s"/>'
            '<line x1="%g" y1="%g" x2="%d" y2="%g" stroke="%s" stroke-width="1.5"/>'
            '<line class="brilho" x1="%g" y1="%g" x2="%d" y2="%g" stroke="%s" stroke-width="2" stroke-linecap="round"/>'
            '</svg>'
            % (W, H, W, H, escape(texto), css, lam, tx, base, tam, c["texto"], escape(texto),
               fim, base - ch * 0.85, max(10, tam * 0.48), ch, c["laranja"],
               x0, meio, W - 2, meio, c["linha"], x0, meio, W - 2, meio, c["laranja"]))


# --------------------------------------------------------------------------- cartões de projeto
USUARIO = "PepeHenrque"
CAMPOS = ("nameWithOwner name description url primaryLanguage { name color } "
          "repositoryTopics(first: 4) { nodes { topic { name } } } "
          'r1: object(expression: "HEAD:README.md") { ... on Blob { text } } '
          'r2: object(expression: "HEAD:readme.md") { ... on Blob { text } }')
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
    if not fixados:
        perfil = "%s/%s" % (USUARIO, USUARIO)
        fixados = [n for n in u["repositories"]["nodes"] if n and n["nameWithOwner"] != perfil][:4]
    for n in fixados:
        if not n.get("description"):
            texto = (n.get("r1") or n.get("r2") or {}).get("text") or ""
            n["description"] = descricao_do_readme(texto, n["name"])
        n.pop("r1", None)
        n.pop("r2", None)
    return fixados


def descricao_do_readme(texto, nome):
    """primeira frase de texto corrido do README (pula títulos, imagens, badges, HTML, código)."""
    import re
    dentro_codigo = False
    for linha in texto.splitlines():
        l = linha.strip()
        if l.startswith("```"):
            dentro_codigo = not dentro_codigo
            continue
        if dentro_codigo or not l or l[0] in "#<>|![-*=_" or l[0].isdigit() and l[1:2] in ".)":
            continue
        l = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", l)          # imagens
        l = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", l)      # links -> texto
        l = re.sub(r"<[^>]+>", "", l)                          # HTML
        l = re.sub(r"[*_`]", "", l).strip()
        if len(l) < 15 or l.lower() == nome.lower():
            continue
        frase = re.split(r"(?<=[.!?])\s", l)[0]
        return frase
    return ""


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
    import math
    RR = 8
    PERIM = 2 * ((CW - 2) + (CH - 2)) - 8 * RR + 2 * math.pi * RR   # contorno do retângulo arredondado
    SEG = 70
    nome = info["name"]
    desc = info.get("description") or "sem descrição ainda"
    lang = info.get("primaryLanguage") or {}
    topicos = [t["topic"]["name"] for t in (info.get("repositoryTopics") or {}).get("nodes", [])]
    css = ("text{font-family:%s}"
           ".volta{stroke-dasharray:%.1f %.1f;animation:volta 7s linear infinite}"
           "@keyframes volta{from{stroke-dashoffset:0}to{stroke-dashoffset:-%.1f}}"
           % (MONO, SEG, PERIM - SEG, PERIM))
    s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="%s">'
         % (CW, CH, CW, CH, escape(nome)), "<style>%s</style>" % css,
         '<rect x=".5" y=".5" width="%d" height="%d" rx="8" fill="%s" stroke="%s"/>' % (CW - 1, CH - 1, c["card"], c["borda"])]
    direita = CW - 18
    if lang.get("name"):
        ln = caber(lang["name"], 12, 150)
        s.append(T(direita, 32, ln, 12, c["fraco"], 400, "end"))
        s.append('<circle cx="%g" cy="28" r="5" fill="%s"/>' % (direita - mono_w(ln, 12) - 10, lang.get("color") or c["fraco"]))
        direita -= mono_w(ln, 12) + 24
    s.append(T(18, 32, "λ", 15, c["laranja"], 700))
    s.append(T(36, 32, caber(nome, 15, direita - 44), 15, c["azul"], 700))
    for i, l in enumerate(quebrar(desc, 13, CW - 36)):
        s.append(T(18, 62 + i * 20, l, 13, c["texto"]))
    if topicos:
        s.append(T(18, CH - 22, caber("# " + " · ".join(topicos), 12, CW - 36), 12, c["fraco"]))
    s.append('<rect class="volta" x="1" y="1" width="%d" height="%d" rx="8" fill="none" stroke="%s" stroke-width="2"'
             ' stroke-linecap="round"/>' % (CW - 2, CH - 2, c["laranja"]))
    s.append("</svg>")
    return "".join(s)


BASE = "https://raw.githubusercontent.com/%s/%s/output/" % (USUARIO, USUARIO)


ESTILO = "8"   # mude se alterar o desenho dos cartões, para o GitHub não mostrar a versão antiga


def versao(info):
    """muda sempre que o conteúdo do cartão muda (descrição, linguagem, tópicos), furando o cache do GitHub."""
    import hashlib
    chave = json.dumps([ESTILO, info.get("description"), info.get("primaryLanguage"),
                        info.get("repositoryTopics")], sort_keys=True)
    return hashlib.sha1(chave.encode()).hexdigest()[:8]


def slug(info):
    return info["nameWithOwner"].replace("/", "-").lower()


def bloco_readme(projetos):
    linhas = ['<p align="left">']
    for info in projetos:
        linhas.append('<a href="%s"><picture>\n'
                      '  <source media="(prefers-color-scheme: dark)" srcset="%sprojeto-%s-dark.svg?v=%s">\n'
                      '  <img src="%sprojeto-%s-light.svg?v=%s" alt="%s" width="49%%">\n</picture></a>'
                      % (info["url"], BASE, slug(info), versao(info), BASE, slug(info), versao(info),
                         escape(info["name"])))
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
        (out / ("nome-%s.svg" % tema)).write_text(titulo(NOME, c, tam=30, lambda_=False, H=54), encoding="utf-8")
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
