"""Police bitmap maison 5x7 (+ accents français, lettres grecques) et petite police 3x5.

Chaque glyphe est une mini image ASCII. La cellule fait 11 lignes :
2 lignes d'accent au-dessus, 7 lignes de corps, 2 lignes de jambage.
"""
import numpy as np
import pygame

_G = r"""
A
.###.
#...#
#...#
#####
#...#
#...#
#...#
B
####.
#...#
#...#
####.
#...#
#...#
####.
C
.###.
#...#
#....
#....
#....
#...#
.###.
D
####.
#...#
#...#
#...#
#...#
#...#
####.
E
#####
#....
#....
####.
#....
#....
#####
F
#####
#....
#....
####.
#....
#....
#....
G
.###.
#...#
#....
#.###
#...#
#...#
.####
H
#...#
#...#
#...#
#####
#...#
#...#
#...#
I
###
.#.
.#.
.#.
.#.
.#.
###
J
..###
...#.
...#.
...#.
...#.
#..#.
.##..
K
#...#
#..#.
#.#..
##...
#.#..
#..#.
#...#
L
#....
#....
#....
#....
#....
#....
#####
M
#...#
##.##
#.#.#
#.#.#
#...#
#...#
#...#
N
#...#
##..#
#.#.#
#..##
#...#
#...#
#...#
O
.###.
#...#
#...#
#...#
#...#
#...#
.###.
P
####.
#...#
#...#
####.
#....
#....
#....
Q
.###.
#...#
#...#
#...#
#.#.#
#..#.
.##.#
R
####.
#...#
#...#
####.
#.#..
#..#.
#...#
S
.####
#....
#....
.###.
....#
....#
####.
T
#####
..#..
..#..
..#..
..#..
..#..
..#..
U
#...#
#...#
#...#
#...#
#...#
#...#
.###.
V
#...#
#...#
#...#
#...#
#...#
.#.#.
..#..
W
#...#
#...#
#...#
#.#.#
#.#.#
##.##
#...#
X
#...#
#...#
.#.#.
..#..
.#.#.
#...#
#...#
Y
#...#
#...#
.#.#.
..#..
..#..
..#..
..#..
Z
#####
....#
...#.
..#..
.#...
#....
#####
0
.###.
#...#
#..##
#.#.#
##..#
#...#
.###.
1
..#..
.##..
..#..
..#..
..#..
..#..
.###.
2
.###.
#...#
....#
...#.
..#..
.#...
#####
3
#####
...#.
..#..
...#.
....#
#...#
.###.
4
...#.
..##.
.#.#.
#..#.
#####
...#.
...#.
5
#####
#....
####.
....#
....#
#...#
.###.
6
..##.
.#...
#....
####.
#...#
#...#
.###.
7
#####
....#
...#.
..#..
.#...
.#...
.#...
8
.###.
#...#
#...#
.###.
#...#
#...#
.###.
9
.###.
#...#
#...#
.####
....#
...#.
.##..
!
#
#
#
#
#
.
#
?
.###.
#...#
....#
...#.
..#..
.....
..#..
'
#
#
.
.
.
.
.
"
#.#
#.#
...
...
...
...
...
-
....
....
....
####
....
....
....
+
.....
..#..
..#..
#####
..#..
..#..
.....
/
....#
....#
...#.
..#..
.#...
#....
#....
(
..#
.#.
#..
#..
#..
.#.
..#
)
#..
.#.
..#
..#
..#
.#.
#..
:
.
#
.
.
.
#
.
;
..
.#
..
..
..
.#
#.
,
..
..
..
..
..
.#
#.
.
.
.
.
.
.
.
#
%
##..#
##..#
...#.
..#..
.#...
#..##
#..##
*
.....
#.#.#
.###.
#####
.###.
#.#.#
.....
=
....
....
####
....
####
....
....
<
...#
..#.
.#..
#...
.#..
..#.
...#
>
#...
.#..
..#.
...#
..#.
.#..
#...
_
.....
.....
.....
.....
.....
.....
#####
×
.....
#...#
.#.#.
..#..
.#.#.
#...#
.....
[
###
#..
#..
#..
#..
#..
###
]
###
..#
..#
..#
..#
..#
###
&
.##..
#..#.
#.#..
.#...
#.#.#
#..#.
.##.#
@
.###.
#...#
#.###
#.#.#
#.###
#....
.###.
#
.#.#.
#####
.#.#.
.#.#.
.#.#.
#####
.#.#.
→
.....
..#..
...#.
#####
...#.
..#..
.....
←
.....
..#..
.#...
#####
.#...
..#..
.....
↑
..#..
.###.
#.#.#
..#..
..#..
..#..
.....
↓
.....
..#..
..#..
..#..
#.#.#
.###.
..#..
·
.
.
.
#
.
.
.
Γ
#####
#....
#....
#....
#....
#....
#....
Δ
..#..
..#..
.#.#.
.#.#.
#...#
#...#
#####
Θ
.###.
#...#
#...#
#.#.#
#...#
#...#
.###.
Λ
..#..
..#..
.#.#.
.#.#.
#...#
#...#
#...#
Ξ
#####
.....
.....
.###.
.....
.....
#####
Π
#####
#...#
#...#
#...#
#...#
#...#
#...#
Σ
#####
#....
.#...
..#..
.#...
#....
#####
Φ
..#..
.###.
#.#.#
#.#.#
#.#.#
.###.
..#..
Ψ
#.#.#
#.#.#
#.#.#
.###.
..#..
..#..
..#..
Ω
.###.
#...#
#...#
#...#
.#.#.
.#.#.
##.##
α
.....
.....
.##.#
#..#.
#..#.
#..#.
.##.#
β
.##..
#..#.
#.#..
#..#.
#..#.
###..
#....
#....
.....
γ
.....
.....
#...#
#...#
.#.#.
..#..
.#.#.
..#..
.....
♥
.....
.#.#.
#####
#####
.###.
..#..
.....
★
..#..
..#..
#####
.###.
.#.#.
#...#
.....
"""

ACCENTS = {
    "acute": ["...#.", "..#.."],
    "grave": [".#...", "..#.."],
    "circ": ["..#..", ".#.#."],
    "diaer": [".....", ".#.#."],
}
COMPOSED = {
    "É": ("E", "acute"), "È": ("E", "grave"), "Ê": ("E", "circ"), "Ë": ("E", "diaer"),
    "À": ("A", "grave"), "Â": ("A", "circ"), "Ä": ("A", "diaer"),
    "Î": ("I", "circ"), "Ï": ("I", "diaer"), "Ô": ("O", "circ"), "Ö": ("O", "diaer"),
    "Û": ("U", "circ"), "Ù": ("U", "grave"), "Ü": ("U", "diaer"),
}
# Lettres grecques majuscules identiques aux latines
GREEK_ALIAS = {
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "’": "'", "«": "<", "»": ">",
    "–": "-", "—": "-",
}
LATIN_LOWER = "abcdefghijklmnopqrstuvwxyzéèêëàâäîïôöûùüç"

CELL_H = 11
BODY_TOP = 2


def _parse():
    lines = _G.strip("\n").split("\n")
    glyphs = {}
    i = 0
    while i < len(lines):
        ch = lines[i]
        i += 1
        rows = []
        while i < len(lines) and len(lines[i]) > 0 and set(lines[i]) <= set(".#") and (
                not rows or len(lines[i]) == len(rows[0])):
            # un glyphe d'une colonne ('.') doit être distingué d'une ligne '.' : on se base sur la largeur
            rows.append(lines[i])
            i += 1
            if len(rows) == 9:
                break
            if len(rows) == 7 and ch not in ("β", "γ"):
                break
        glyphs[ch] = rows
    return glyphs


def _to_cell(rows, accent=None, cedilla=False):
    w = len(rows[0])
    cell = [["."] * w for _ in range(CELL_H)]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == "#":
                cell[BODY_TOP + y][x] = "#"
    if accent:
        pat = ACCENTS[accent]
        if w == 3:
            pat = [p[1:4] for p in pat]
        for y, r in enumerate(pat):
            for x, c in enumerate(r[:w]):
                if c == "#":
                    cell[y][x] = "#"
    if cedilla:
        for y, r in enumerate(["..#..", ".##.."]):
            for x, c in enumerate(r[:w]):
                if c == "#":
                    cell[BODY_TOP + 7 + y][x] = "#"
    arr = np.zeros((w, CELL_H), dtype=bool)
    for y in range(CELL_H):
        for x in range(w):
            arr[x, y] = cell[y][x] == "#"
    return arr


def _build_masks():
    raw = _parse()
    masks = {ch: _to_cell(rows) for ch, rows in raw.items()}
    for ch, (base, acc) in COMPOSED.items():
        masks[ch] = _to_cell(raw[base], accent=acc)
    masks["Ç"] = _to_cell(raw["C"], cedilla=True)
    masks[" "] = np.zeros((3, CELL_H), dtype=bool)
    return masks


def normalize(text):
    out = []
    for c in text:
        if c in LATIN_LOWER:
            c = c.upper()
        c = GREEK_ALIAS.get(c, c)
        out.append(c)
    return "".join(out)


class BitmapFont:
    def __init__(self):
        self.masks = _build_masks()
        self.spacing = 1
        self.cache = {}

    def text_mask(self, text):
        text = normalize(text)
        parts = [self.masks.get(c, self.masks["?"]) for c in text]
        if not parts:
            return np.zeros((1, CELL_H), dtype=bool)
        w = sum(p.shape[0] for p in parts) + self.spacing * (len(parts) - 1)
        m = np.zeros((max(w, 1), CELL_H), dtype=bool)
        x = 0
        for p in parts:
            m[x:x + p.shape[0], :] = p
            x += p.shape[0] + self.spacing
        return m

    def width(self, text, scale=1):
        text = normalize(text)
        if not text:
            return 0
        w = sum(self.masks.get(c, self.masks["?"]).shape[0] for c in text) + self.spacing * (len(text) - 1)
        return w * scale

    def render(self, text, color=(255, 255, 255), outline=None, shadow=None, scale=1, grad=None):
        """Rend un texte. grad = (couleur_haut, couleur_bas) pour un dégradé vertical."""
        key = (text, color, outline, shadow, scale, grad)
        surf = self.cache.get(key)
        if surf is not None:
            return surf
        m = self.text_mask(text)
        if scale != 1:
            m = np.repeat(np.repeat(m, scale, axis=0), scale, axis=1)
        pad = 1 if (outline or shadow) else 0
        sh = 1 if shadow else 0
        w, h = m.shape[0] + pad * 2 + sh * scale, m.shape[1] + pad * 2 + sh * scale
        rgb = np.zeros((w, h, 3), np.uint8)
        alpha = np.zeros((w, h), np.uint8)
        full = np.zeros((w, h), dtype=bool)
        full[pad:pad + m.shape[0], pad:pad + m.shape[1]] = m
        if shadow:
            s = np.zeros_like(full)
            s[scale:, scale:] = full[:-scale, :-scale]
            s &= ~full
            rgb[s] = shadow
            alpha[s] = 255
        if outline:
            d = full.copy()
            d[1:, :] |= full[:-1, :]
            d[:-1, :] |= full[1:, :]
            d[:, 1:] |= full[:, :-1]
            d[:, :-1] |= full[:, 1:]
            d[1:, 1:] |= full[:-1, :-1]
            d[:-1, :-1] |= full[1:, 1:]
            d[1:, :-1] |= full[:-1, 1:]
            d[:-1, 1:] |= full[1:, :-1]
            o = d & ~full
            rgb[o] = outline
            alpha[o] = 255
        if grad:
            top, bot = grad
            ys = np.arange(h)
            body0 = pad + BODY_TOP * scale
            body1 = pad + (BODY_TOP + 7) * scale
            t = np.clip((ys - body0) / max(1, body1 - body0 - 1), 0, 1)
            col = (np.array(top)[None, :] * (1 - t[:, None]) + np.array(bot)[None, :] * t[:, None]).astype(np.uint8)
            cols = np.broadcast_to(col[None, :, :], (w, h, 3))
            rgb[full] = cols[full]
        else:
            rgb[full] = color
        alpha[full] = 255
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.blit_array(surf, rgb)
        pa = pygame.surfarray.pixels_alpha(surf)
        pa[:] = alpha
        del pa
        if len(self.cache) > 1500:
            self.cache.clear()
        self.cache[key] = surf
        return surf

    def draw(self, surf, text, x, y, color=(255, 255, 255), align="left", outline=None, shadow=None,
             scale=1, grad=None):
        """Dessine le texte ; (x, y) = coin haut-gauche du corps des lettres."""
        img = self.render(text, color, outline, shadow, scale, grad)
        pad = 1 if (outline or shadow) else 0
        if align == "center":
            x -= self.width(text, scale) // 2
        elif align == "right":
            x -= self.width(text, scale)
        surf.blit(img, (int(x) - pad, int(y) - BODY_TOP * scale - pad))
        return img


# --- Petite police de chiffres 3x5 (popups de score) -----------------------
_TINY = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", ".#.", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    "×": ["...", "#.#", ".#.", "#.#", "..."],
    "x": ["...", "#.#", ".#.", "#.#", "..."],
    "+": ["...", ".#.", "###", ".#.", "..."],
    "-": ["...", "...", "###", "...", "..."],
    " ": ["...", "...", "...", "...", "..."],
}


class TinyFont:
    def __init__(self):
        self.cache = {}

    def render(self, text, color=(255, 255, 255), outline=(0, 0, 0)):
        key = (text, color, outline)
        s = self.cache.get(key)
        if s is not None:
            return s
        w = len(text) * 4 - 1 + 2
        h = 7
        m = np.zeros((w, h), dtype=bool)
        for i, c in enumerate(text):
            g = _TINY.get(c, _TINY[" "])
            for y, row in enumerate(g):
                for x, ch in enumerate(row):
                    if ch == "#":
                        m[1 + i * 4 + x, 1 + y] = True
        rgb = np.zeros((w, h, 3), np.uint8)
        alpha = np.zeros((w, h), np.uint8)
        if outline:
            d = m.copy()
            d[1:, :] |= m[:-1, :]
            d[:-1, :] |= m[1:, :]
            d[:, 1:] |= m[:, :-1]
            d[:, :-1] |= m[:, 1:]
            o = d & ~m
            rgb[o] = outline
            alpha[o] = 255
        rgb[m] = color
        alpha[m] = 255
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.blit_array(s, rgb)
        pa = pygame.surfarray.pixels_alpha(s)
        pa[:] = alpha
        del pa
        if len(self.cache) > 800:
            self.cache.clear()
        self.cache[key] = s
        return s


FONT = None
TINY = None


def init():
    global FONT, TINY
    FONT = BitmapFont()
    TINY = TinyFont()
    return FONT
