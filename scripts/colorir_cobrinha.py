"""Pinta a cobrinha gerada pelo Platane/snk.

Uso: python scripts/colorir_cobrinha.py arquivo.svg ESTILO [COMIDA]
COMIDA (cor dos quadradinhos de contribuição, do claro ao escuro):
  verde | laranja | azul | arco-iris   (sem informar, continua verde)
ESTILO:
  arco-iris  - cada pedaço de uma cor do arco-íris
  tema       - degradê do laranja (cabeça) ao azul (rabo), cores do perfil
  ciclo      - arco-íris que vai trocando de cor enquanto ela anda
  alternado  - cobrinha de uma cor e comida de outra (sempre opostas), trocando juntas de tempos em tempos
Só biblioteca padrão.
"""
import re
import sys

PALETAS = {
    "arco-iris": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "tema": ["#f0883e", "#e9965a", "#a68fb8", "#5e9ce8", "#0969da", "#0550ae"],
    "ciclo": ["#ff4d4d", "#ffa94d", "#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
    "alternado": ["#f0883e"],
}
PASSOS = 6          # quantas cores diferentes no ciclo (360° / 6 = 60° por troca)
SEGUNDOS = 4        # quanto tempo cada cor fica na tela


COMIDAS = {
    "verde": ["#9be9a8", "#40c463", "#30a14e", "#216e39"],
    "laranja": ["#ffd8b5", "#ffb07a", "#f0883e", "#bd561d"],
    "azul": ["#b6dcff", "#79b8ff", "#2f81f7", "#0550ae"],
    "arco-iris": ["#ffe14d", "#4dd97a", "#4dabff", "#9b6bff"],
}


def colorir(svg, estilo, comida="verde"):
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
        dur = PASSOS * SEGUNDOS
        quadros = []
        for k in range(PASSOS):
            ini = 100 * k / PASSOS
            fim = 100 * (k + 1) / PASSOS - 100 * 0.6 / dur   # 0,6 s de transição suave
            quadros.append("%.2f%%,%.2f%%{filter:hue-rotate(%ddeg)}" % (ini, fim, 360 * k // PASSOS))
        quadros.append("100%{filter:hue-rotate(360deg)}")
        css += (".gira{animation:gira %ds ease-in-out infinite}@keyframes gira{%s}" % (dur, "".join(quadros)))
        a = svg.index('<rect class="c')
        b = svg.index('<rect class="s s')
        fim_s = svg.index("/>", svg.rindex('class="s s')) + 2
        svg = (svg[:a] + '<g class="gira">' + svg[a:b] + '</g><g class="gira">' + svg[b:fim_s] + "</g>"
               + svg[fim_s:])
    return svg.replace("</style>", css + "</style>", 1)


if __name__ == "__main__":
    arq, estilo = sys.argv[1], sys.argv[2]
    comida = sys.argv[3] if len(sys.argv) > 3 else "verde"
    with open(arq, encoding="utf-8") as f:
        svg = f.read()
    with open(arq, "w", encoding="utf-8") as f:
        f.write(colorir(svg, estilo, comida))
    print("ok: cobrinha", estilo, "comendo", comida)
