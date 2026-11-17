"""Jogo de blocos deitado, jogado com as minhas contribuições.

Uso: python scripts/gerar_blocos.py cobrinha.svg blocos.svg
- cobrinha.svg: o arquivo gerado pelo Platane/snk (só para ler quais dias tiveram contribuição);
- blocos.svg: a animação gerada.

Como funciona:
- O tabuleiro é o gráfico de contribuições deitado: 7 linhas (dias) e uma coluna por semana.
- Cada contribuição, em ordem de data, vira uma peça de 4 quadradinhos. A peça entra pela direita e
  desliza para a esquerda até encostar (a "gravidade" puxa para a esquerda).
- Um jogador automático escolhe a melhor posição e rotação de cada peça.
- Quando uma coluna fica completa (7 quadradinhos), ela pisca e é limpa; o que está à direita anda.
- A barra embaixo enche conforme as contribuições viram peças (vazia no começo, cheia na última).
Só biblioteca padrão.
"""
import math
import os
import re
import sys
import tempfile

MAX_PECAS = 60          # usa as contribuições mais recentes (para a animação não ficar longa demais)
VELOCIDADE = 0.011      # segundos por coluna deslizada
QUEDA_MIN = 0.16        # tempo mínimo de cada deslize
ENTRE = 0.06            # intervalo entre uma peça e a próxima
PISCA = 0.36            # tempo da coluna completa piscando
ANDA = 0.16             # tempo do bloco andando depois da limpeza
FIM = 1.8               # tempo mostrando "FIM DE JOGO" depois da última peça, antes de explodir
EXPLODE = 0.9           # duração da explosão final
RESPIRA = 0.8           # pausa depois da explosão, antes de recomeçar
SOME = EXPLODE + RESPIRA
VOLTA_COR = 24          # segundos para as cores darem uma volta
COLUNAS_POR_NIVEL = 5   # sobe um nível a cada tantas colunas limpas (e as peças ficam mais rápidas)
PONTOS = {1: 100, 2: 300, 3: 500, 4: 800}   # pontos por limpeza (vezes o nível), como no jogo clássico
COMBOS = {2: "DUPLA!", 3: "TRIPLA!", 4: "QUÁDRUPLA!"}
VAZIO = "rgba(128,128,128,.22)"
TEXTO = "#8b949e"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

# as 7 peças de 4 quadradinhos (cada uma com suas rotações)
FORMAS = {
    "I": [(0, 0), (1, 0), (2, 0), (3, 0)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(0, 0), (1, 0), (2, 0), (1, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
}
CORES = {"I": "#2f81f7", "O": "#e3b341", "T": "#a371f7", "S": "#3fb950",
         "Z": "#f85149", "J": "#58a6ff", "L": "#f0883e"}


def rotacoes(forma):
    vistas, saida = set(), []
    pts = forma
    for _ in range(4):
        mx, my = min(x for x, _ in pts), min(y for _, y in pts)
        norm = tuple(sorted((x - mx, y - my) for x, y in pts))
        if norm not in vistas:
            vistas.add(norm)
            saida.append(list(norm))
        pts = [(y, -x) for x, y in pts]
    return saida


ROT = {k: rotacoes(v) for k, v in FORMAS.items()}


def ler_grade(svg):
    celulas = re.findall(r'<rect class="(c(?: c[0-9a-z]+)?)" x="([0-9.]+)" y="([0-9.]+)"', svg)
    com_cor = {m.group(1) for m in re.finditer(r"\.c\.(c[0-9a-z]+)\{fill:var\(--c[1-4]\)", svg)}
    vivas, todas = [], set()
    for cls, x, y in celulas:
        pos = (int(float(x)) // 16, int(float(y)) // 16)
        todas.add(pos)
        if " " in cls and cls.split()[1] in com_cor:
            vivas.append(pos)
    if not todas:
        raise ValueError("não achei o gráfico de contribuições no arquivo")
    vivas.sort()                              # ordem de data: semana, depois dia
    return max(c for c, _ in todas) + 1, max(r for _, r in todas) + 1, vivas


def simular(cols, linhas, contribs):
    """devolve a lista de peças com tempos e as limpezas, já com o jogador automático."""
    ocup = {}                                  # (x, y) -> id da célula
    celulas = []                               # cada célula: {"tipo", "eventos": [(t, x, y, opacidade)]}
    limpezas = []                              # (tempo, colunas limpas de uma vez, posições) de cada limpeza
    jogadas = []                               # (início, duração, posições finais, distância, tipo) de cada peça
    total_colunas = 0
    barra = []                                 # (tempo, fração da barra)
    t = 0.3
    for n, (semana, dia) in enumerate(contribs):
        tipo = "IOTSZJL"[(semana * 7 + dia * 3 + n) % 7]
        melhor = None
        for forma in ROT[tipo]:
            alt = max(y for _, y in forma) + 1
            for y0 in range(0, linhas - alt + 1):
                # entra pela direita e desliza para a esquerda até encostar
                x0 = cols
                if any((x0 + x - 1, y0 + y) in ocup for x, y in forma):
                    continue
                while x0 > 0 and not any((x0 - 1 + x, y0 + y) in ocup for x, y in forma):
                    x0 -= 1
                pos = [(x0 + x, y0 + y) for x, y in forma]
                if max(x for x, _ in pos) >= cols:
                    continue
                teste = set(ocup) | set(pos)
                cheias = [cx for cx in range(cols) if all((cx, yy) in teste for yy in range(linhas))]
                resto = {(x - sum(1 for c in cheias if c < x), y) for x, y in teste if x not in cheias}
                ext = [max([x + 1 for x, yy in resto if yy == y] or [0]) for y in range(linhas)]
                buracos = sum(1 for y in range(linhas) for x in range(ext[y]) if (x, y) not in resto)
                irreg = sum(abs(ext[i] - ext[i + 1]) for i in range(linhas - 1))
                # pesos clássicos de jogador automático: soma das alturas, linhas, buracos e irregularidade
                nota = len(cheias) * 7.6 - sum(ext) * 5.1 - buracos * 3.6 - irreg * 1.8 - max(ext) * 0.5
                if melhor is None or nota > melhor[0]:
                    melhor = (nota, pos)
        barra.append((t, (n + 1) / len(contribs)))     # enche conforme as peças são jogadas
        if melhor is None:                     # não cabe mais: limpa o tabuleiro e segue
            for cid in set(ocup.values()):
                celulas[cid]["eventos"].append((t, None, None, 1))
                celulas[cid]["eventos"].append((t + 0.4, None, None, 0))
            ocup.clear()
            t += 0.5
            continue
        pos = melhor[1]
        dist = cols - min(x for x, _ in pos)
        nivel = 1 + total_colunas // COLUNAS_POR_NIVEL
        dur = max(QUEDA_MIN * 0.6, dist * VELOCIDADE * (0.85 ** (nivel - 1)))
        ids = []
        for x, y in pos:
            cid = len(celulas)
            celulas.append({"tipo": tipo, "eventos": [(0, x + dist, y, 0), (t - 0.001, x + dist, y, 0),
                                                       (t, x + dist, y, 1), (t + dur, x, y, 1)]})
            ocup[(x, y)] = cid
            ids.append(cid)
        jogadas.append((t, dur, pos, dist, tipo))
        t += dur
        cheias = [cx for cx in range(cols) if all((cx, yy) in ocup for yy in range(linhas))]
        if cheias:
            limpezas.append((t, len(cheias), [(cx, yy) for cx in cheias for yy in range(linhas)]))
            total_colunas += len(cheias)
            for cx in cheias:
                for yy in range(linhas):
                    cid = ocup.pop((cx, yy))
                    ev = celulas[cid]["eventos"]
                    x, y = ev[-1][1], ev[-1][2]
                    ev += [(t, x, y, 1), (t + PISCA * .25, x, y, .2), (t + PISCA * .5, x, y, 1),
                           (t + PISCA * .75, x, y, .2), (t + PISCA, x, y, 0)]
            t += PISCA
            novo = {}
            for (x, y), cid in sorted(ocup.items()):
                desloca = sum(1 for c in cheias if c < x)
                if desloca:
                    ev = celulas[cid]["eventos"]
                    ev += [(t, x, y, 1), (t + ANDA, x - desloca, y, 1)]
                novo[(x - desloca, y)] = cid
            ocup = novo
            t += ANDA
        t += ENTRE
    simular.jogadas = jogadas
    return celulas, limpezas, barra, t


def gira_cor(hexcor, graus):
    r, g, b = (int(hexcor[i:i + 2], 16) for i in (1, 3, 5))
    a = math.radians(graus)
    c, s = math.cos(a), math.sin(a)
    m = [[.213 + c * .787 - s * .213, .715 - c * .715 - s * .715, .072 - c * .072 + s * .928],
         [.213 - c * .213 + s * .143, .715 + c * .285 + s * .140, .072 - c * .072 - s * .283],
         [.213 - c * .213 - s * .787, .715 - c * .715 + s * .715, .072 + c * .928 + s * .072]]
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(m[i][0] * r + m[i][1] * g + m[i][2] * b))) for i in range(3))


def gerar(svg_cobrinha):
    cols, linhas, contribs = ler_grade(svg_cobrinha)
    contribs = contribs[-MAX_PECAS:]
    celulas, limpezas, barra, t_fim = simular(cols, linhas, contribs)
    dur = t_fim + FIM + SOME

    def pct(t):
        return "%.3f%%" % (100 * min(t, dur) / dur)

    css = ["text{font-family:%s}" % MONO,
           ".cor{animation:cor %ds linear infinite}@keyframes cor{to{filter:hue-rotate(360deg)}}" % VOLTA_COR,
           ".q{animation-duration:%.2fs;animation-iteration-count:infinite;animation-timing-function:linear}" % dur]
    finais = [[e for e in c["eventos"] if e[1] is not None][-1] for c in celulas if c["eventos"][-1][3] > 0]
    centro = ((sum(e[1] for e in finais) / len(finais), sum(e[2] for e in finais) / len(finais))
              if finais else (3, linhas / 2))
    css.append(".q{transform-box:fill-box;transform-origin:center}")
    css.append("@keyframes clarao{0%%,%s{opacity:0}%s{opacity:.35}%s,100%%{opacity:0}}"
               ".clarao{opacity:0;animation:clarao %.2fs linear infinite}"
               % (pct(t_fim + FIM), pct(t_fim + FIM + 0.08), pct(t_fim + FIM + 0.45), dur))
    pecas_svg = []
    for i, cel in enumerate(celulas):
        ev = list(cel["eventos"])
        # posições que faltam (eventos de "limpar tudo" não mudam a posição)
        x = y = None
        cheio = []
        for (tt, ex, ey, op) in ev:
            if ex is None:
                ex, ey = x, y
            x, y = ex, ey
            cheio.append((tt, ex, ey, op))
        ultimo = cheio[-1]
        if ultimo[3] > 0:                      # ainda está no tabuleiro no fim: explode
            ux, uy = ultimo[1], ultimo[2]
            dx, dy = ux - centro[0], uy - centro[1]
            ang = math.atan2(dy, dx) + (((i * 7919) % 100) / 100 - .5) * 1.2
            forca = 4 + ((i * 104729) % 100) / 100 * 8                  # em quadradinhos
            fx, fy = ux + math.cos(ang) * forca, uy + math.sin(ang) * forca - 1.2
            giro = ((i * 6151) % 540) - 270
            cheio += [(t_fim + FIM, ux, uy, 1, 0, 1),
                      (t_fim + FIM + 0.06, ux, uy, 1, 0, 1.25),
                      (t_fim + FIM + EXPLODE, fx, fy, 0, giro, 0.2)]
        quadros = []
        for item in sorted(cheio, key=lambda e: e[0]):
            tt, ex, ey, op = item[:4]
            rot, esc = (item[4], item[5]) if len(item) > 4 else (0, 1)
            quadros.append("%s{transform:translate(%.1fpx,%.1fpx) rotate(%ddeg) scale(%g);opacity:%g}"
                           % (pct(tt), 8 + ex * 16, 8 + ey * 16, rot, esc, op))
        f = cheio[-1]
        quadros.append("100%%{transform:translate(%.1fpx,%.1fpx) rotate(%ddeg) scale(%g);opacity:0}"
                       % (8 + f[1] * 16, 8 + f[2] * 16, f[4] if len(f) > 4 else 0, f[5] if len(f) > 4 else 1))
        css.append("@keyframes q%d{%s}.q%d{animation-name:q%d}" % (i, "".join(quadros), i, i))
        pecas_svg.append('<rect class="q q%d" width="12" height="12" rx="2.5" fill="%s" opacity="0"/>'
                         % (i, CORES[cel["tipo"]]))

    W, Hb = cols * 16 + 16, linhas * 16 + 16
    base_y = Hb + 32
    # barra da linha do tempo (enche conforme as contribuições entram)
    passos = ["0%{transform:scaleX(0)}"]
    for tt, frac in barra:
        passos.append("%s{transform:scaleX(%.4f)}" % (pct(tt), frac))
    passos.append("%s{transform:scaleX(%.4f)}" % (pct(t_fim + FIM), barra[-1][1] if barra else 0))
    passos.append("%s,100%%{transform:scaleX(0)}" % pct(t_fim + FIM + EXPLODE))
    css.append(".barra{transform-box:fill-box;transform-origin:0 0;animation:barra %.2fs linear infinite}"
               "@keyframes barra{%s}" % (dur, "".join(passos)))
    paradas = "".join('<stop offset="%.2f" stop-color="%s"/>' % (i / 6, gira_cor("#2f81f7", 300 * i / 6))
                      for i in range(7))
    barra_svg = ('<defs><linearGradient id="gb" gradientUnits="userSpaceOnUse" x1="8" x2="%d">%s</linearGradient></defs>'
                 '<rect x="8" y="%d" width="%d" height="8" rx="4" fill="%s"/>'
                 '<rect class="barra" x="8" y="%d" width="%d" height="8" rx="4" fill="url(#gb)"/>'
                 % (W - 8, paradas, Hb + 2, W - 16, VAZIO, Hb + 2, W - 16))

    # placar: nível, pontos e colunas, atualizado a cada limpeza
    rotulos = []
    marcos = [(0.0, 0, 1, 0)]                  # (tempo, colunas, nível, pontos)
    colunas = pontos = 0
    for (tt, qtd, _) in limpezas:
        nivel = 1 + colunas // COLUNAS_POR_NIVEL
        pontos += PONTOS.get(qtd, 800) * nivel
        colunas += qtd
        marcos.append((tt + PISCA, colunas, 1 + colunas // COLUNAS_POR_NIVEL, pontos))
    for k, (ini, colunas, nivel, pontos) in enumerate(marcos):
        fim = marcos[k + 1][0] if k + 1 < len(marcos) else t_fim + FIM + SOME
        css.append("@keyframes l%d{0%%,%s{opacity:0}%s,%s{opacity:1}%s,100%%{opacity:0}}"
                   ".l%d{opacity:0;animation:l%d %.2fs steps(1,end) infinite}"
                   % (k, pct(max(0, ini - 0.001)), pct(ini), pct(fim - 0.001), pct(fim), k, k, dur))
        rotulos.append('<text class="l%d" x="%d" y="%d" font-size="11" fill="%s" text-anchor="end">'
                       'nível %d · %s pts · %d colunas</text>'
                       % (k, W - 8, base_y, TEXTO, nivel, "{:,}".format(pontos).replace(",", "."), colunas))

    # faíscas: cada quadradinho de uma coluna limpa solta uma faísca que voa e some
    faiscas = []
    for j, (tt, qtd, pos) in enumerate(limpezas):
        for m, (cx, cy) in enumerate(pos):
            n = j * 97 + m
            ang = (n * 137.5) % 360
            dist = 14 + (n * 53) % 26
            x0, y0 = 8 + cx * 16 + 4, 8 + cy * 16 + 4
            x1 = x0 + math.cos(math.radians(ang)) * dist
            y1 = y0 + math.sin(math.radians(ang)) * dist
            t0 = tt + PISCA * .5
            css.append("@keyframes f%d_%d{0%%,%s{transform:translate(%.1fpx,%.1fpx) scale(1);opacity:0}"
                       "%s{transform:translate(%.1fpx,%.1fpx) scale(1);opacity:1}"
                       "%s,100%%{transform:translate(%.1fpx,%.1fpx) scale(.2);opacity:0}}"
                       ".f%d_%d{opacity:0;animation:f%d_%d %.2fs ease-out infinite}"
                       % (j, m, pct(t0 - 0.001), x0, y0, pct(t0), x0, y0, pct(t0 + 0.55), x1, y1,
                          j, m, j, m, dur))
            faiscas.append('<rect class="f%d_%d" width="4" height="4" rx="1" fill="#ffffff"/>' % (j, m))

    # comemoração quando limpa 2, 3 ou 4 colunas de uma vez
    combos = []
    for j, (tt, qtd, pos) in enumerate(limpezas):
        if qtd < 2:
            continue
        cx = 8 + (sum(c for c, _ in pos) / len(pos)) * 16 + 6
        cx = max(90, min(W - 90, cx + 150))      # um pouco à direita do bloco, sem cobrir as peças
        css.append("@keyframes c%d{0%%,%s{opacity:0;transform:translateY(6px) scale(.6)}"
                   "%s{opacity:1;transform:translateY(0) scale(1.15)}%s{opacity:1;transform:translateY(-2px) scale(1)}"
                   "%s,100%%{opacity:0;transform:translateY(-10px) scale(1)}}"
                   ".c%d{opacity:0;transform-box:fill-box;transform-origin:center;animation:c%d %.2fs linear infinite}"
                   % (j, pct(tt), pct(tt + 0.15), pct(tt + 0.9), pct(tt + 1.3), j, j, dur))
        combos.append('<text class="c%d" x="%.0f" y="%d" font-size="%d" font-weight="800" fill="#ffffff" '
                      'stroke="#0d1117" stroke-width="3" paint-order="stroke" text-anchor="middle">%s</text>'
                      % (j, cx, 8 + linhas * 8 + 6, 16 + 2 * qtd, COMBOS[qtd]))


    # rastro de velocidade: uma faixa apagada atrás de cada peça enquanto ela desliza
    rastros = []
    for j, (t0, d0, pos, dist, tipo) in enumerate(getattr(simular, "jogadas", [])):
        ys = [y for _, y in pos]
        x_fim = max(x for x, _ in pos) + 1
        y0, y1 = min(ys), max(ys) + 1
        largura = 3 * 16
        css.append("@keyframes r%d{0%%,%s{opacity:0;transform:translateX(%dpx)}"
                   "%s{opacity:.5;transform:translateX(%dpx)}"
                   "%s{opacity:.42;transform:translateX(0)}%s,100%%{opacity:0;transform:translateX(0)}}"
                   ".r%d{opacity:0;animation:r%d %.2fs linear infinite}"
                   % (j, pct(t0), dist * 16, pct(t0 + 0.01), dist * 16, pct(t0 + d0), pct(t0 + d0 + 0.15),
                      j, j, dur))
        rastros.append('<rect class="r%d" x="%d" y="%d" width="%d" height="%d" rx="3" fill="url(#rastro%s)"/>'
                       % (j, 8 + x_fim * 16 - 4, 8 + y0 * 16, largura, (y1 - y0) * 16 - 4, tipo))
    grad_rastro = "".join('<linearGradient id="rastro%s"><stop offset="0" stop-color="%s"/>'
                          '<stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>' % (k, c, c)
                          for k, c in CORES.items())

    # tremor do tabuleiro nas limpezas de 3 ou 4 colunas
    passos_tremor = ["0%{transform:translate(0,0)}"]
    for (tt, qtd, _) in limpezas:
        if qtd >= 3:
            forca = 2 if qtd == 3 else 3.5
            for k, (dx, dy) in enumerate(((-1, 1), (1, -1), (-1, -1), (1, 1), (0, 0))):
                passos_tremor.append("%s{transform:translate(%gpx,%gpx)}" % (pct(tt + 0.04 * (k + 1)),
                                                                          dx * forca, dy * forca))
    css.append("@keyframes treme{%s}.treme{animation:treme %.2fs linear infinite}" % ("".join(passos_tremor), dur))

    # tela de fim de jogo antes da explosão
    pontos_fim = marcos[-1][3]
    css.append("@keyframes fimjogo{0%%,%s{opacity:0;transform:scale(.7)}%s{opacity:1;transform:scale(1.08)}"
               "%s{opacity:1;transform:scale(1)}%s,100%%{opacity:0;transform:scale(1.3)}}"
               ".fimjogo{opacity:0;transform-box:fill-box;transform-origin:center;animation:fimjogo %.2fs linear infinite}"
               % (pct(t_fim + 0.15), pct(t_fim + 0.35), pct(t_fim + FIM - 0.1), pct(t_fim + FIM + 0.15), dur))
    meio = 8 + linhas * 8
    fim_jogo = ('<g class="fimjogo"><text x="%d" y="%d" font-size="22" font-weight="800" fill="#ffffff" stroke="#0d1117" '
                'stroke-width="4" paint-order="stroke" text-anchor="middle">FIM DE JOGO</text>'
                '<text x="%d" y="%d" font-size="13" font-weight="700" fill="#ffffff" stroke="#0d1117" stroke-width="3" '
                'paint-order="stroke" text-anchor="middle">%s pontos</text></g>'
                % (W // 2, meio + 2, W // 2, meio + 22, "{:,}".format(pontos_fim).replace(",", ".")))

    legenda = ('<text x="8" y="%d" font-size="11" fill="%s">cada contribuição minha vira uma peça · '
               'coluna completa é limpa</text>' % (base_y, TEXTO))
    if not contribs:                           # ano sem contribuições: nada de "fim de jogo" piscando
        fim_jogo = ""
        rotulos = []
        legenda = ('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="middle">'
                   'nenhuma contribuição no último ano ainda: a primeira vira a primeira peça</text>'
                   % (W // 2, 8 + linhas * 8 + 4, TEXTO))
    fundo = "".join('<rect x="%d" y="%d" width="12" height="12" rx="2.5"/>' % (8 + c * 16, 8 + r * 16)
                    for c in range(cols) for r in range(linhas))
    # as contribuições reais aparecem no fundo; quando a peça dela nasce, o quadradinho acende e some
    origem = []
    for k, ((semana, dia), (tt, _)) in enumerate(zip(contribs, barra)):
        css.append("@keyframes o%d{0%%,%s{opacity:.55;transform:scale(1)}%s{opacity:1;transform:scale(1.35)}"
                   "%s,%s{opacity:0;transform:scale(1)}%s,100%%{opacity:.55}}"
                   ".o%d{transform-box:fill-box;transform-origin:center;animation:o%d %.2fs linear infinite}"
                   % (k, pct(max(0, tt - 0.12)), pct(tt), pct(tt + 0.25), pct(t_fim + FIM + SOME * .5),
                      pct(t_fim + FIM + SOME), k, k, dur))
        cor = gira_cor("#2f81f7", 300 * semana / max(1, cols - 1))
        origem.append('<rect class="o%d" x="%d" y="%d" width="12" height="12" rx="2.5" fill="%s"/>'
                      % (k, 8 + semana * 16, 8 + dia * 16, cor))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
            'aria-label="Jogo de blocos jogado com as contribuições do Pedro">'
            '<style>%s</style><defs><clipPath id="tab"><rect x="0" y="0" width="%d" height="%d"/></clipPath></defs>'
            '<defs>%s</defs>'
            '<g class="treme"><g fill="%s">%s</g><g class="cor">%s<g clip-path="url(#tab)">%s%s</g></g></g>'
            '<g class="cor">%s</g>'
            '<rect class="clarao" x="4" y="4" width="%d" height="%d" rx="6" fill="#ffffff"/>%s%s%s%s%s</svg>'
            % (W, base_y + 8, W, base_y + 8, "".join(css), W - 4, Hb, grad_rastro, VAZIO, fundo, "".join(origem),
               "".join(rastros), "".join(pecas_svg), barra_svg, W - 8, Hb - 4, "".join(faiscas), "".join(combos),
               fim_jogo, legenda, "".join(rotulos)))


def main():
    origem, destino = sys.argv[1], sys.argv[2]
    try:
        with open(origem, encoding="utf-8") as f:
            svg = gerar(f.read())
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(destino)), suffix=".svg")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(svg)
        os.chmod(tmp, 0o644)
        os.replace(tmp, destino)
        print("ok: blocos em", destino)
    except Exception as e:   # nunca derruba o workflow
        print("aviso: não consegui gerar os blocos (%s: %s)" % (type(e).__name__, e))


if __name__ == "__main__":
    main()
