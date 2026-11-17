"""Pinta a cobrinha gerada pelo Platane/snk com tema Hora de Aventura (Lady Íris + Finn, Jake e BMO).

Uso: python scripts/colorir_cobrinha.py arquivo.svg ESTILO [COMIDA] [VAZIO]
VAZIO (cor dos quadradinhos sem contribuição): um cinza neutro, ex. #4a4a4a (sem informar, fica o padrão)
COMIDA (cor dos quadradinhos de contribuição, do claro ao escuro):
  verde | laranja | azul | arco-iris | doces   (sem informar, continua verde)
ESTILO:
  lady-iris  - Lady Íris devorando os commits + Finn, Jake e BMO assistindo no canto
  arco-iris  - cada pedaço de uma cor do arco-íris
  tema       - degradê do laranja (cabeça) ao azul (rabo), cores do perfil
  ciclo      - arco-íris que vai trocando de cor enquanto ela anda
  alternado  - cobrinha de uma cor e comida de outra (sempre opostas), mudando juntas devagar
  onda       - degradê da esquerda para a direita que vai andando
Só biblioteca padrão.
"""
import re
import sys

PALETAS = {
    "lady-iris": ["#ffffff", "#ff85c0", "#ffd666", "#73d13d", "#40a9ff", "#b37feb"],
    "arco-iris": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "tema": ["#f0883e", "#e9965a", "#a68fb8", "#5e9ce8", "#0969da", "#0550ae"],
    "ciclo": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "alternado": ["#f0883e"],
    "onda": ["#f0883e"],
}
ABERTURA = 180
VOLTA = 24
VAZIO = "rgba(128,128,128,.22)"

COMIDAS = {
    "verde": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "laranja": ["#ffd8b5", "#ffb07a", "#f0883e", "#bd561d"],
    "azul": ["#b6dcff", "#79b8ff", "#2f81f7", "#0550ae"],
    "arco-iris": ["#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "doces": ["#ffcce6", "#ff80bf", "#ff3399", "#cc0066"],
}


def injetar_cabeca_lady_iris(svg):
    """Substitui o rect da cabeça (s s0) por um <svg> aninhado com a Lady Íris sem interferir no transform CSS."""
    padrao_s0 = re.compile(r'<rect class="s s0"([^>]*?)(?:/>|>(.*?)</rect>)', re.DOTALL)
    match = padrao_s0.search(svg)
    if not match:
        return svg

    atributos = match.group(1)
    animacoes = match.group(2) or ""

    # Usa <svg> aninhado com overflow="visible": ele aceita x, y, width, height exatamente como <rect>
    # e deixa o transform: translate(...) do CSS livre para mover a cabeça pelo gráfico!
    cabeca_svg = f"""<svg class="s s0"{atributos} overflow="visible">
      {animacoes}
      <!-- Crina Rosa e Lilás -->
      <rect x="-2" y="1" width="3" height="10" rx="1" fill="#ff66b2" />
      <rect x="-4" y="3" width="3" height="6" rx="1" fill="#b37feb" />
      <!-- Cabeça Branca com contorno suave para destacar no tema claro e escuro -->
      <rect x="0" y="1" width="12" height="10" rx="2" fill="#ffffff" stroke="#d9d9d9" stroke-width="0.6" />
      <!-- Focinho -->
      <rect x="10" y="4" width="4" height="6" rx="1" fill="#fff0f6" stroke="#d9d9d9" stroke-width="0.5" />
      <!-- Chifre Dourado -->
      <polygon points="8,1 13,-4 11,2" fill="#ffd700" stroke="#d48806" stroke-width="0.4" />
      <!-- Olho com brilho -->
      <rect x="7" y="4" width="2" height="2" fill="#1a1a1a" />
      <rect x="7" y="4" width="1" height="1" fill="#ffffff" />
      <!-- Bochecha corada -->
      <rect x="6" y="7" width="2" height="1" fill="#ff85c0" />
    </svg>"""

    return svg[:match.start()] + cabeca_svg + svg[match.end():]


def injetar_trio_ooo(svg):
    """Adiciona BMO, Jake e Finn em pixel art animada no canto inferior esquerdo do SVG."""
    vb_match = re.search(r'viewBox="([^"]+)"', svg)
    if vb_match:
        parts = [float(p) for p in vb_match.group(1).split()]
        altura_total = parts[3]
    else:
        altura_total = 192.0

    # Posiciona na base inferior esquerda (espaço vazio ao lado da barra de progresso/legenda)
    pos_y = max(130.0, altura_total - 33.0)

    trio_svg = f"""
    <g id="trio-ooo" transform="translate(16, {pos_y})" shape-rendering="crispEdges">
      <!-- BMO -->
      <g class="ooo-bmo">
        <rect x="0" y="10" width="12" height="14" fill="#63c5b4" />
        <rect x="1" y="10" width="10" height="1" fill="#8ce0d2" />
        <rect x="2" y="12" width="8" height="6" fill="#d9f7be" />
        <rect x="3" y="14" width="1" height="1" fill="#1a1a1a" />
        <rect x="8" y="14" width="1" height="1" fill="#1a1a1a" />
        <rect x="5" y="16" width="2" height="1" fill="#1a1a1a" />
        <rect x="3" y="20" width="2" height="2" fill="#fadb14" />
        <rect x="7" y="19" width="2" height="1" fill="#ff4d4f" />
        <rect x="8" y="21" width="1" height="1" fill="#1890ff" />
        <rect x="3" y="24" width="2" height="4" fill="#3a8f80" />
        <rect x="7" y="24" width="2" height="4" fill="#3a8f80" />
      </g>

      <!-- JAKE -->
      <g class="ooo-jake" transform="translate(18, 0)">
        <rect x="0" y="10" width="14" height="13" fill="#f7b519" />
        <rect x="-2" y="12" width="2" height="5" fill="#e09b00" />
        <rect x="14" y="12" width="2" height="5" fill="#e09b00" />
        <rect x="2" y="12" width="4" height="4" fill="#1a1a1a" />
        <rect x="3" y="12" width="2" height="2" fill="#ffffff" />
        <rect x="8" y="12" width="4" height="4" fill="#1a1a1a" />
        <rect x="9" y="12" width="2" height="2" fill="#ffffff" />
        <rect x="5" y="16" width="4" height="2" fill="#e09b00" />
        <rect x="6" y="15" width="2" height="1" fill="#1a1a1a" />
        <rect x="2" y="23" width="2" height="5" fill="#f7b519" />
        <rect x="10" y="23" width="2" height="5" fill="#f7b519" />
      </g>

      <!-- FINN -->
      <g class="ooo-finn" transform="translate(38, 0)">
        <!-- Mochila Verde -->
        <rect x="-2" y="12" width="3" height="8" fill="#3b8c30" />
        <!-- Chapéu Branco com contorno sutil para aparecer no fundo claro -->
        <rect x="1" y="1" width="2" height="3" fill="#ffffff" stroke="#bfbfbf" stroke-width="0.4" />
        <rect x="9" y="1" width="2" height="3" fill="#ffffff" stroke="#bfbfbf" stroke-width="0.4" />
        <rect x="1" y="4" width="10" height="8" fill="#ffffff" stroke="#bfbfbf" stroke-width="0.4" />
        <!-- Rosto -->
        <rect x="3" y="6" width="6" height="4" fill="#ffcca8" />
        <rect x="4" y="7" width="1" height="1" fill="#1a1a1a" />
        <rect x="7" y="7" width="1" height="1" fill="#1a1a1a" />
        <!-- Camisa Azul -->
        <rect x="1" y="12" width="10" height="7" fill="#2ba6cb" />
        <!-- Shorts Azul Escuro -->
        <rect x="1" y="19" width="10" height="3" fill="#1b5299" />
        <!-- Pernas e Botas -->
        <rect x="2" y="22" width="2" height="4" fill="#ffcca8" />
        <rect x="8" y="22" width="2" height="4" fill="#ffcca8" />
        <rect x="2" y="26" width="3" height="2" fill="#222222" />
        <rect x="8" y="26" width="3" height="2" fill="#222222" />
      </g>
    </g>
    """

    return svg.replace("</svg>", trio_svg + "\n</svg>", 1)


def colorir(svg, estilo, comida="verde", vazio=None):
    if vazio is None and estilo in ("alternado", "onda"):
        vazio = VAZIO
    if vazio:
        svg = re.sub(r"--ce:[^;}]*", "--ce:" + vazio, svg, count=1)
        svg = re.sub(r"--c0:[^;}]*", "--c0:" + vazio, svg, count=1)
    for i, cor in enumerate(COMIDAS[comida], start=1):
        svg = re.sub(r"--c%d:[^;}]*" % i, "--c%d:%s" % (i, cor), svg, count=1)

    cores = PALETAS[estilo]
    n = len(set(re.findall(r'class="s s(\d+)"', svg))) or 4
    css = "".join(
        ".s.s%d{fill:%s}" % (i, cores[min(len(cores) - 1, round(i * (len(cores) - 1) / max(1, n - 1)))])
        for i in range(n)
    )

    if estilo == "lady-iris":
        css += (
            "@keyframes ooo-hop{0%,100%{transform:translateY(0)}50%{transform:translateY(-2px)}}"
            ".ooo-bmo{animation:ooo-hop 0.8s infinite}"
            ".ooo-jake{animation:ooo-hop 1.2s 0.2s infinite}"
            ".ooo-finn{animation:ooo-hop 1.0s 0.4s infinite}"
        )
        svg = injetar_cabeca_lady_iris(svg)
        svg = injetar_trio_ooo(svg)

    if estilo == "ciclo":
        css += ".arco{animation:arco 4s linear infinite}@keyframes arco{to{filter:hue-rotate(360deg)}}"
        primeiro = svg.index('<rect class="s s')
        ultimo = svg.rindex('class="s s')
        ultimo = svg.index("/>", ultimo) + 2
        svg = svg[:primeiro] + '<g class="arco">' + svg[primeiro:ultimo] + "</g>" + svg[ultimo:]

    if estilo == "alternado":
        css += ".gira{animation:gira %ds linear infinite}@keyframes gira{to{filter:hue-rotate(360deg)}}" % VOLTA
        a = svg.index('<rect class="c')
        b = svg.index('<rect class="s s')
        fim_s = svg.index("/>", svg.rindex('class="s s')) + 2
        svg = (svg[:a] + '<g class="gira">' + svg[a:b] + '</g><g class="gira">' + svg[b:fim_s] + "</g>"
               + svg[fim_s:])

    if estilo == "onda":
        svg, css = onda(svg, css, COMIDAS[comida][2])

    return svg.replace("</style>", css + "</style>", 1)


def gira_cor(hexcor, graus):
    """mesma conta do filtro CSS hue-rotate(), para o degradê da barra bater com as colunas."""
    import math
    r, g, b = (int(hexcor[i:i + 2], 16) for i in (1, 3, 5))
    a = math.radians(graus)
    c, s = math.cos(a), math.sin(a)
    m = [[.213 + c * .787 - s * .213, .715 - c * .715 - s * .715, .072 - c * .072 + s * .928],
         [.213 - c * .213 + s * .143, .715 + c * .285 + s * .140, .072 - c * .072 - s * .283],
         [.213 - c * .213 - s * .787, .715 - c * .715 + s * .715, .072 + c * .928 + s * .072]]
    v = [max(0, min(255, round(m[i][0] * r + m[i][1] * g + m[i][2] * b))) for i in range(3)]
    return "#%02x%02x%02x" % tuple(v)


def onda(svg, css, cor_barra):
    largura = max(float(x) for x in re.findall(r'<rect class="c[^"]*" x="([0-9.]+)"', svg)) + 14

    def atraso(x):
        return -(float(x) / largura) * (ABERTURA / 360) * VOLTA

    css += ".onda{animation:gira %ds linear infinite}@keyframes gira{to{filter:hue-rotate(360deg)}}" % VOLTA
    a = svg.index('<rect class="c')
    b = svg.index('<rect class="u')
  pedacos = re.findall(r'<rect class="c[^"]" x="([0-9.]+)"[^>]/>', svg[a:b])
elems = re.findall(r'<rect class="c[^>]*/>', svg[a:b])
colunas, atual, x_atual = [], [], None
for x, el in zip(pedacos, elems):
if x != x_atual and atual:
colunas.append((x_atual, atual))
atual = []
x_atual = x
atual.append(el)
colunas.append((x_atual, atual))
grade = "".join('%s' % (atraso(x), "".join(els))
for x, els in colunas)
c = svg.index('<rect class="s s')
barra = svg[b:c]
paradas = "".join('' % (i / 8, gira_cor(cor_barra, ABERTURA * i / 8))
for i in range(9))
defs = ('%s'
'' % (largura, paradas))
css += ".u.u0,.u.u1,.u.u2,.u.u3{fill:url(#arco)}"
fim_s = svg.index("/>", svg.rindex('class="s s')) + 2
cobra = svg[c:fim_s]
import colorsys
def matiz(hexcor):
r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
return colorsys.rgb_to_hsv(r, g, b)[0] * 360
giro = (matiz(cor_barra) + ABERTURA / 2 + 180 - matiz(PALETAS["onda"][0])) % 360
atraso_cobra = -(giro / 360) * VOLTA
svg = (svg[:a] + defs + grade + '' + barra + ""
+ '%s' % (atraso_cobra, cobra) + svg[fim_s:])
return svg, css
def main():
import os
import tempfile
arq, estilo = sys.argv[1], sys.argv[2]
comida = sys.argv[3] if len(sys.argv) > 3 else "verde"
vazio = sys.argv[4] if len(sys.argv) > 4 else None
try:
with open(arq, encoding="utf-8") as f:
svg = colorir(f.read(), estilo, comida, vazio)
pasta = os.path.dirname(os.path.abspath(arq))
fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".svg")
with os.fdopen(fd, "w", encoding="utf-8") as f:
f.write(svg)
os.chmod(tmp, 0o644)
os.replace(tmp, arq)
print("ok: cobrinha", estilo, "comendo", comida)
except Exception as e:
print("aviso: não consegui colorir a cobrinha (%s: %s); ela fica com a cor padrão" % (type(e).name, e))
if name == "main":
main()
