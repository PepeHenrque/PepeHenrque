"""Pinta a cobrinha gerada pelo Platane/snk.

Uso: python scripts/colorir_cobrinha.py arquivo.svg ESTILO [COMIDA] [VAZIO]
VAZIO (cor dos quadradinhos sem contribuição): um cinza neutro, ex. #4a4a4a (sem informar, fica o padrão)
COMIDA (cor dos quadradinhos de contribuição, do claro ao escuro):
  verde | laranja | azul | arco-iris   (sem informar, continua verde)
ESTILO:
  arco-iris  - cada pedaço de uma cor do arco-íris
  tema       - degradê do laranja (cabeça) ao azul (rabo), cores do perfil
  ciclo      - arco-íris que vai trocando de cor enquanto ela anda
  alternado  - cobrinha de uma cor e comida de outra (sempre opostas), mudando juntas devagar;
               quadradinhos vazios em cinza translúcido
  onda       - como "alternado", mas a cor da comida forma um degradê da esquerda para a direita
               que vai andando (cada coluna um pouco à frente); a barra de baixo vira um degradê contínuo
Só biblioteca padrão.
"""
import re
import sys

PALETAS = {
    "arco-iris": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "tema": ["#f0883e", "#e9965a", "#a68fb8", "#5e9ce8", "#0969da", "#0550ae"],
    "ciclo": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "alternado": ["#f0883e"],
    "onda": ["#f0883e"],
}
ABERTURA = 180      # quanto do círculo de cores o degradê ocupa da esquerda à direita (180 = meia volta)
VOLTA = 24          # segundos para passar por todas as cores (mudança contínua; a cada ~4 s já é outra cor)
VAZIO = "rgba(128,128,128,.22)"   # cinza translúcido: escuro no tema escuro, claro no tema claro


COMIDAS = {
    "verde": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "laranja": ["#ffd8b5", "#ffb07a", "#f0883e", "#bd561d"],
    "azul": ["#b6dcff", "#79b8ff", "#2f81f7", "#0550ae"],
    "arco-iris": ["#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
}


def colorir(svg, estilo, comida="verde", vazio=None):
    if vazio is None and estilo in ("alternado", "onda"):
        vazio = VAZIO
    if vazio:   # cinza neutro continua cinza quando a matiz gira
        svg = re.sub(r"--ce:[^;}]*", "--ce:" + vazio, svg, count=1)
        svg = re.sub(r"--c0:[^;}]*", "--c0:" + vazio, svg, count=1)
    for i, cor in enumerate(COMIDAS[comida], start=1):
        svg = re.sub(r"--c%d:[^;}]*" % i, "--c%d:%s" % (i, cor), svg, count=1)
    cores = PALETAS[estilo]
    n = len(set(re.findall(r'class="s s(\d+)"', svg))) or 4
    css = "".join(".s.s%d{fill:%s}" % (i, cores[min(len(cores) - 1, round(i * (len(cores) - 1) / max(1, n - 1)))])
                  for i in range(n))
    if estilo == "ciclo":
        # embrulha os pedaços num grupo e gira a matiz devagar: as cores "andam" pelo corpo
        css += ".arco{animation:arco 4s linear infinite}@keyframes arco{to{filter:hue-rotate(360deg)}}"
        primeiro = svg.index('<rect class="s s')
        ultimo = svg.rindex('class="s s')
        ultimo = svg.index("/>", ultimo) + 2
        svg = svg[:primeiro] + '<g class="arco">' + svg[primeiro:ultimo] + "</g>" + svg[ultimo:]
    if estilo == "alternado":
        # comida (quadradinhos + barra) e cobrinha giram a matiz juntas, mantendo a distância entre as cores
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

    def atraso(x):        # coluna mais à direita fica mais à frente no ciclo de cores
        return -(float(x) / largura) * (ABERTURA / 360) * VOLTA

    css += ".onda{animation:gira %ds linear infinite}@keyframes gira{to{filter:hue-rotate(360deg)}}" % VOLTA
    # 1) quadradinhos: um grupo por coluna, cada um com seu atraso
    a = svg.index('<rect class="c')
    b = svg.index('<rect class="u')
    pedacos = re.findall(r'<rect class="c[^"]*" x="([0-9.]+)"[^>]*/>', svg[a:b])
    elems = re.findall(r'<rect class="c[^>]*/>', svg[a:b])
    colunas, atual, x_atual = [], [], None
    for x, el in zip(pedacos, elems):
        if x != x_atual and atual:
            colunas.append((x_atual, atual))
            atual = []
        x_atual = x
        atual.append(el)
    colunas.append((x_atual, atual))
    grade = "".join('<g class="onda" style="animation-delay:%.2fs">%s</g>' % (atraso(x), "".join(els))
                    for x, els in colunas)
    # 2) barra: degradê fixo da esquerda para a direita, girando junto
    c = svg.index('<rect class="s s')
    barra = svg[b:c]
    paradas = "".join('<stop offset="%.2f" stop-color="%s"/>' % (i / 8, gira_cor(cor_barra, ABERTURA * i / 8))
                      for i in range(9))
    defs = ('<defs><linearGradient id="arco" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="%d" y2="0">%s'
            '</linearGradient></defs>' % (largura, paradas))
    css += ".u.u0,.u.u1,.u.u2,.u.u3{fill:url(#arco)}"
    # 3) cobrinha: uma cor só, oposta à cor do meio do degradê
    fim_s = svg.index("/>", svg.rindex('class="s s')) + 2
    cobra = svg[c:fim_s]
    import colorsys

    def matiz(hexcor):
        r, g, b = (int(hexcor[i:i + 2], 16) / 255 for i in (1, 3, 5))
        return colorsys.rgb_to_hsv(r, g, b)[0] * 360
    giro = (matiz(cor_barra) + ABERTURA / 2 + 180 - matiz(PALETAS["onda"][0])) % 360
    atraso_cobra = -(giro / 360) * VOLTA
    svg = (svg[:a] + defs + grade + '<g class="onda">' + barra + "</g>"
           + '<g class="onda" style="animation-delay:%.2fs">%s</g>' % (atraso_cobra, cobra) + svg[fim_s:])
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
        # grava num arquivo novo e troca pelo original: funciona mesmo se o original for de outro dono
        # (o Platane/snk roda em Docker como root)
        pasta = os.path.dirname(os.path.abspath(arq))
        fd, tmp = tempfile.mkstemp(dir=pasta, suffix=".svg")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(svg)
        os.chmod(tmp, 0o644)
        os.replace(tmp, arq)
        print("ok: cobrinha", estilo, "comendo", comida)
    except Exception as e:  # nunca derruba o workflow: no pior caso a cobrinha fica com a cor padrão
        print("aviso: não consegui colorir a cobrinha (%s: %s); ela fica com a cor padrão" % (type(e).__name__, e))


if __name__ == "__main__":
    main()
