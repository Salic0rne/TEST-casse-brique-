"""Niveaux : 10 tableaux dessinés à la main puis génération procédurale infinie.

Légende (13 colonnes) :
    r o y g c b p m w   brique simple (rouge, orange, jaune, vert, cyan, bleu, violet, magenta, nacre)
    R O Y G C B P M W   brique renforcée (2 coups)
    #                   brique blindée (3 coups)
    @                   métal indestructible
    *                   brique explosive (réaction en chaîne)
    $                   prisme (libère toujours un bonus)
    .                   vide
"""

import math
import random

from .config import COLS
from .sprites import ARMOR, BOMB, HARD, METAL, NORMAL, PRISM

HUES = {
    "r": (0.985, 0.85), "o": (0.07, 0.9), "y": (0.14, 0.85), "g": (0.35, 0.8), "c": (0.5, 0.85),
    "b": (0.6, 0.8), "p": (0.76, 0.72), "m": (0.87, 0.78), "w": (0.62, 0.14),
}

LEVELS = [
    ("AUBE NÉON", [
        ".............",
        ".............",
        "mmmmmmmmmmmmm",
        "rrrrrr$rrrrrr",
        "ooooooooooooo",
        "yyyyyyyyyyyyy",
        "ggggggggggggg",
    ]),
    ("PYRAMIDE", [
        "......$......",
        ".....ppp.....",
        "....bbbbb....",
        "...ccccccc...",
        "..ggggggggg..",
        ".yyyyyyyyyyy.",
        "ooooooooooooo",
        "RRRRRRRRRRRRR",
    ]),
    ("ENVAHISSEUR", [
        "...g.....g...",
        "....g...g....",
        "...ggggggg...",
        "..gg*ggg*gg..",
        ".ggggggggggg.",
        ".g.ggggggg.g.",
        ".g.g.....g.g.",
        "....gg.gg....",
        ".............",
        ".WW..WWW..WW.",
    ]),
    ("CŒUR BATTANT", [
        "...mm...mm...",
        "..mRRm.mRRm..",
        ".mRRRRmRRRRm.",
        ".mRRRRRRRRRm.",
        ".mRRRR$RRRRm.",
        "..mRRRRRRRm..",
        "...mRRRRRm...",
        "....mRRRm....",
        ".....mRm.....",
        "......m......",
    ]),
    ("FORTERESSE", [
        "@@@@@.$.@@@@@",
        "@yyyy...yyyy@",
        "@yOOOOOOOOOy@",
        "@yO*ooooo*Oy@",
        "@yOo#####oOy@",
        "@yO*ooooo*Oy@",
        "@yOOOOOOOOOy@",
        "@yyyyyyyyyyy@",
        "@@@@@...@@@@@",
    ]),
    ("DAMIER EXPLOSIF", [
        "cmcmcmcmcmcmc",
        "mcmcmcmcmcmcm",
        "cmc*cmcmc*cmc",
        "mcmc*cmc*cmcm",
        "cmcmc*c*cmcmc",
        "mcmcmc*cmcmcm",
        "cmcmcmcmcmcmc",
        "BPBPBP$PBPBPB",
    ]),
    ("CHEVRONS", [
        "m...........m",
        "pm.........mp",
        "bpm.......mpb",
        "cbpm.....mpbc",
        "gcbpm...mpbcg",
        "ygcbpm.mpbcgy",
        "oygcbpmpbcgyo",
        "RRRRRR$RRRRRR",
        "@...@...@...@",
    ]),
    ("PRISME", [
        "......w......",
        ".....wWw.....",
        "....w$W$w....",
        "...rrrrrrr...",
        "..ooooooooo..",
        ".yyyyyyyyyyy.",
        "ggggggggggggg",
        "ccccccccccccc",
        "bbbbbbbbbbbbb",
        "ppppppppppppp",
    ]),
    ("CITÉ NÉON", [
        "......P......",
        ".....PPP.....",
        ".C...P#P...C.",
        "CCC..PPP..CCC",
        "C#C..P$P..C#C",
        "CCC.MMMMM.CCC",
        "C#C.M*M*M.C#C",
        "CCC.MMMMM.CCC",
        "yyyyyyyyyyyyy",
        "@.@.@.@.@.@.@",
    ]),
    ("SUPERNOVA", [
        ".....yyy.....",
        "...yyoooyy...",
        "..yooRRRooy..",
        ".yoRR***RRoy.",
        ".yoR**$**Roy.",
        ".yoRR***RRoy.",
        "..yooRRRooy..",
        "...yyoooyy...",
        ".....yyy.....",
        "#...#...#...#",
    ]),
]

PROC_NAMES = ["ÉCHO", "SPECTRE", "HÉLICE", "NÉBULEUSE", "MIRAGE", "CRISTAL", "PULSAR", "AURORE",
              "VORTEX", "ORBITE", "MATRICE", "QUASAR", "ÉCLIPSE", "PLASMA", "ZÉNITH"]


def level_count():
    return len(LEVELS)


def get_level(index):
    """Retourne (nom, lignes) du niveau `index` (0 = premier)."""
    if index < len(LEVELS):
        return LEVELS[index]
    return _generate(index)


def _generate(index):
    rng = random.Random(index * 7919 + 17)
    diff = min(1.0, (index - len(LEVELS) + 1) / 12.0)
    rows = rng.randint(7, 11)
    palette = rng.sample("roygcbpm", 4)
    style = rng.choice(("diamant", "anneaux", "bruit", "vagues", "bandes", "croix"))
    grid = [["." for _ in range(COLS)] for _ in range(rows)]
    cy = (rows - 1) / 2
    for r in range(rows):
        for c in range((COLS + 1) // 2):
            dx, dy = 6 - c, r - cy
            if style == "diamant":
                d = abs(dx) + abs(dy) * 1.3
                on = d <= 7.5 and int(d) % 4 != 3
                band = int(d / 2)
            elif style == "anneaux":
                d = (dx * dx + dy * dy * 2.2) ** 0.5
                on = int(d) % 3 != 2 and d < 8.5
                band = int(d)
            elif style == "bruit":
                on = rng.random() < 0.72
                band = r
            elif style == "vagues":
                on = abs(r - (cy + 2.5 * math.sin(c * 0.7 + index))) < 2.2 or r < 2
                band = r
            elif style == "bandes":
                on = r % 3 != 2
                band = r // 3
            else:
                on = abs(dx) <= 1 or abs(dy) <= 1 or (abs(dx) + r) % 4 == 0
                band = abs(dx) // 2
            if not on:
                continue
            ch = palette[band % len(palette)]
            roll = rng.random()
            if roll < 0.02 + 0.06 * diff:
                ch = "@"
            elif roll < 0.06 + 0.1 * diff:
                ch = "#"
            elif roll < 0.10 + 0.12 * diff:
                ch = "*"
            elif roll < 0.25 + 0.35 * diff:
                ch = ch.upper()
            grid[r][c] = grid[r][COLS - 1 - c] = ch
    # prismes garantis
    cells = [(r, c) for r in range(rows) for c in range(COLS) if grid[r][c] not in ".@"]
    for r, c in rng.sample(cells, min(2, len(cells))):
        grid[r][c] = "$"
    lines = ["".join(row) for row in grid]
    destructible = sum(ch not in ".@" for line in lines for ch in line)
    if destructible < 30:
        lines = [line.replace(".", palette[0]) if i % 2 == 0 else line for i, line in enumerate(lines)]
    lines = [".............", ] + lines if rows < 10 else lines
    name = "%s %d" % (PROC_NAMES[index % len(PROC_NAMES)], index + 1)
    return name, lines


def parse_cell(ch, row, rows):
    """Traduit un caractère en (type, teinte, saturation, points de vie) ou None."""
    if ch in ".  ":
        return None
    if ch == "@":
        return METAL, 0.6, 0.1, 1
    if ch == "*":
        return BOMB, 0.02, 0.9, 1
    if ch == "$":
        return PRISM, 0.0, 0.6, 1
    if ch == "#":
        return ARMOR, (row / max(1, rows)) * 0.8 + 0.5, 0.85, 3
    low = ch.lower()
    if low in HUES:
        hue, sat = HUES[low]
        if ch.isupper():
            return HARD, hue, sat, 2
        return NORMAL, hue, sat, 1
    return None
