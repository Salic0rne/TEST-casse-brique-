"""Police vectorielle « tube néon » dessinée à la main (aucun fichier de police requis).

Chaque glyphe est une liste de polylignes sur une grille de 4 x 6 unités
(y vers le bas). Le rendu superpose un halo flouté (additif), un tube coloré
et un cœur clair, avec suréchantillonnage pour l'anticrénelage.
"""

from collections import OrderedDict

import pygame

from . import surf as S

GLYPHS = {
    "A": [[(0, 6), (0, 1.5), (1.5, 0), (2.5, 0), (4, 1.5), (4, 6)], [(0, 3.6), (4, 3.6)]],
    "B": [[(0, 3), (2.8, 3), (3.6, 2.2), (3.6, 0.8), (2.8, 0), (0, 0), (0, 6), (3, 6),
           (4, 5), (4, 4), (3, 3), (2.8, 3)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6), (2.5, 6), (4, 4.5), (4, 1.5), (2.5, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.2), (2.2, 3.2)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "J": [[(1.5, 0), (4, 0), (4, 5), (3, 6), (1, 6), (0, 5), (0, 4)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (1, 3), (0, 3)], [(1, 3), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2.5, 3.2), (5, 0), (5, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2.2), (3, 3.2), (0, 3.2)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)],
          [(2.4, 4.4), (4.2, 6.2)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2.2), (3, 3.2), (0, 3.2)], [(2, 3.2), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6),
           (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1.2, 6), (2.5, 2.6), (3.8, 6), (5, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    "Œ": [[(3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6)], [(3, 0), (3, 6)], [(3, 0), (6, 0)],
          [(3, 6), (6, 6)], [(3, 3), (5.4, 3)]],
    "0": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)],
          [(3.1, 1.5), (0.9, 4.5)]],
    "1": [[(0.8, 1.2), (2, 0), (2, 6)], [(0.8, 6), (3.2, 6)]],
    "2": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2.2), (0, 6), (4, 6)]],
    "3": [[(0, 0), (4, 0), (2, 2.6), (3, 2.6), (4, 3.6), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "4": [[(3, 6), (3, 0), (0, 4.2), (4, 4.2)]],
    "5": [[(4, 0), (0, 0), (0, 2.6), (3, 2.6), (4, 3.6), (4, 5), (3, 6), (0, 6)]],
    "6": [[(3.5, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3.8), (3, 2.8), (0, 2.8)]],
    "7": [[(0, 0), (4, 0), (1.4, 6)]],
    "8": [[(1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 4), (0, 5),
           (1, 6), (3, 6), (4, 5), (4, 4), (3, 3)]],
    "9": [[(0.5, 6), (3, 6), (4, 5), (4, 1), (3, 0), (1, 0), (0, 1), (0, 2.2), (1, 3.2), (4, 3.2)]],
    "!": [[(0, 0), (0, 4.0)], [(0, 5.4), (0, 6)]],
    "?": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (2, 3.4), (2, 4.1)], [(2, 5.4), (2, 6)]],
    ".": [[(0, 5.4), (0, 6)]],
    ",": [[(0.5, 5.3), (0, 6.8)]],
    ":": [[(0, 1.6), (0, 2.2)], [(0, 5.4), (0, 6)]],
    ";": [[(0.5, 1.6), (0.5, 2.2)], [(0.5, 5.3), (0, 6.8)]],
    "-": [[(0, 3), (2.4, 3)]],
    "+": [[(0, 3), (3, 3)], [(1.5, 1.5), (1.5, 4.5)]],
    "×": [[(0, 1.8), (2.6, 4.4)], [(2.6, 1.8), (0, 4.4)]],
    "/": [[(0, 6), (3, 0)]],
    "'": [[(0, 0), (0, 1.6)]],
    "%": [[(0, 6), (4, 0)], [(0.2, 0.2), (1.3, 0.2), (1.3, 1.3), (0.2, 1.3), (0.2, 0.2)],
          [(2.7, 4.7), (3.8, 4.7), (3.8, 5.8), (2.7, 5.8), (2.7, 4.7)]],
    "<": [[(3, 0.6), (0, 3), (3, 5.4)]],
    ">": [[(0, 0.6), (3, 3), (0, 5.4)]],
    "(": [[(1.5, 0), (0.3, 1.2), (0.3, 4.8), (1.5, 6)]],
    ")": [[(0, 0), (1.2, 1.2), (1.2, 4.8), (0, 6)]],
    "[": [[(1.5, 0), (0, 0), (0, 6), (1.5, 6)]],
    "]": [[(0, 0), (1.5, 0), (1.5, 6), (0, 6)]],
    "=": [[(0, 2), (3, 2)], [(0, 4), (3, 4)]],
    "_": [[(0, 6), (4, 6)]],
    "·": [[(0, 2.7), (0, 3.3)]],
    "←": [[(4, 3), (0, 3)], [(1.6, 1.4), (0, 3), (1.6, 4.6)]],
    "→": [[(0, 3), (4, 3)], [(2.4, 1.4), (4, 3), (2.4, 4.6)]],
    "↑": [[(2, 6), (2, 0)], [(0.4, 1.6), (2, 0), (3.6, 1.6)]],
    "↓": [[(2, 0), (2, 6)], [(0.4, 4.4), (2, 6), (3.6, 4.4)]],
    "—": [[(0, 3), (5, 3)]],
    "♥": [[(2, 6), (0.2, 3.6), (0, 2.6), (0, 1.4), (0.9, 0.4), (2, 0.9), (3.1, 0.4), (4, 1.4),
           (4, 2.6), (3.8, 3.6), (2, 6)]],
    "★": [[(2.0, 0.0), (2.6, 2.1), (4.0, 2.2), (2.9, 3.6), (3.3, 6.0), (2.0, 4.7), (0.7, 6.0),
           (1.1, 3.6), (0.0, 2.2), (1.4, 2.1), (2.0, 0.0)]],
}

_ACUTE = [[(1.5, -0.5), (2.6, -1.8)]]
_GRAVE = [[(1.4, -1.8), (2.5, -0.5)]]
_CIRC = [[(0.9, -0.5), (2, -1.7), (3.1, -0.5)]]
_DIAER = [[(1.1, -1.3), (1.1, -0.9)], [(2.9, -1.3), (2.9, -0.9)]]
_CEDIL = [[(2, 6), (2.3, 7.0), (1.2, 7.6)]]

ACCENTED = {
    "É": ("E", _ACUTE), "È": ("E", _GRAVE), "Ê": ("E", _CIRC), "Ë": ("E", _DIAER),
    "À": ("A", _GRAVE), "Â": ("A", _CIRC), "Ä": ("A", _DIAER),
    "Î": ("I", _CIRC), "Ï": ("I", _DIAER),
    "Ô": ("O", _CIRC), "Ö": ("O", _DIAER),
    "Ù": ("U", _GRAVE), "Û": ("U", _CIRC), "Ü": ("U", _DIAER),
    "Ç": ("C", _CEDIL), "Ÿ": ("Y", _DIAER),
}

SPACE_ADVANCE = 2.6
TOP_UNITS = 2.2       # place réservée au-dessus (accents)
BOTTOM_UNITS = 1.8    # place réservée en dessous (cédille, virgule)


def _glyph(ch):
    if ch in GLYPHS:
        return GLYPHS[ch], []
    if ch in ACCENTED:
        base, acc = ACCENTED[ch]
        return GLYPHS[base], acc
    return GLYPHS["?"], []


def _layout(text, spacing):
    """Retourne (polylignes en unités, largeur en unités)."""
    x = 0.0
    strokes = []
    last_adv = 0.0
    for ch in text.upper():
        if ch == " ":
            x += SPACE_ADVANCE
            last_adv = 0.0
            continue
        polys, accents = _glyph(ch)
        xs = [p[0] for poly in polys for p in poly]
        minx, maxx = min(xs), max(xs)
        gw = maxx - minx
        for poly in polys:
            strokes.append([(px - minx + x, py) for px, py in poly])
        for poly in accents:
            strokes.append([(px - 2.0 + gw / 2.0 + x, py) for px, py in poly])
        x += gw + spacing
        last_adv = spacing
    return strokes, max(0.0, x - last_adv)


class NeonText:
    """Texte pré-rendu : halo additif + tube coloré."""

    __slots__ = ("tube", "glow", "ox", "oy", "w", "h")

    def __init__(self, tube, glow, ox, oy, w, h):
        self.tube = tube
        self.glow = glow
        self.ox = ox      # position de la boîte des majuscules dans la surface
        self.oy = oy
        self.w = w        # taille de la boîte des majuscules
        self.h = h

    def origin(self, x, y, anchor="center"):
        """Coin haut-gauche de la surface pour ancrer la boîte des majuscules en (x, y)."""
        if anchor == "center":
            bx, by = x - self.w / 2, y - self.h / 2
        elif anchor == "midleft":
            bx, by = x, y - self.h / 2
        elif anchor == "midright":
            bx, by = x - self.w, y - self.h / 2
        elif anchor == "topleft":
            bx, by = x, y
        elif anchor == "topright":
            bx, by = x - self.w, y
        elif anchor == "midtop":
            bx, by = x - self.w / 2, y
        elif anchor == "midbottom":
            bx, by = x - self.w / 2, y - self.h
        else:
            raise ValueError(anchor)
        return int(bx - self.ox), int(by - self.oy)

    def draw(self, target, x, y, anchor="center", alpha=255, glow=1.0):
        px, py = self.origin(x, y, anchor)
        if self.glow is not None and glow > 0 and alpha > 0:
            g = self.glow
            k = glow * alpha / 255.0
            if k < 0.99:
                g = S.intensity(g, k)
            target.blit(g, (px, py), special_flags=pygame.BLEND_RGB_ADD)
        if alpha >= 255:
            target.blit(self.tube, (px, py))
        elif alpha > 0:
            self.tube.set_alpha(int(alpha))
            target.blit(self.tube, (px, py))
            self.tube.set_alpha(255)


class VectorFont:
    def __init__(self, cache_size=400):
        self._cache = OrderedDict()
        self._cache_size = cache_size

    def measure(self, text, size, spacing=1.3):
        _, w = _layout(text, spacing)
        return w * size / 6.0

    def render(self, text, size, color, core=None, thick=None, glow=1.0, glow_radius=None,
               spacing=1.3, skew=0.0, core_ratio=0.42, supersample=2):
        key = (text, size, color, core, thick, glow, glow_radius, spacing, skew, core_ratio)
        hit = self._cache.get(key)
        if hit is not None:
            self._cache.move_to_end(key)
            return hit
        nt = self._render(text, size, color, core, thick, glow, glow_radius, spacing, skew,
                          core_ratio, supersample)
        self._cache[key] = nt
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return nt

    def _render(self, text, size, color, core, thick, glow, glow_radius, spacing, skew,
                core_ratio, ss):
        u = size / 6.0
        t = thick if thick is not None else max(1.6, size * 0.11)
        if core is None:
            core = tuple(min(255, c + (255 - c) * 7 // 10) for c in color)
        gr = glow_radius if glow_radius is not None else max(3, int(size * 0.22))
        strokes, wu = _layout(text, spacing)
        pad = int(gr * 1.6 + t) + 2
        skew_px = abs(skew) * (6 + TOP_UNITS) * u
        w = int(wu * u + skew_px + 2 * pad) + 2
        h = int((6 + TOP_UNITS + BOTTOM_UNITS) * u + 2 * pad) + 2
        ox = pad + (skew_px if skew < 0 else 0)
        oy = pad + TOP_UNITS * u

        def to_px(p, k):
            x = ox + (p[0] + (6 - p[1]) * skew) * u
            y = oy + p[1] * u
            return (x * k, y * k)

        big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA, 32)
        for poly in strokes:
            S.thick_polyline(big, color, [to_px(p, ss) for p in poly], t * ss)
        if core_ratio > 0:
            for poly in strokes:
                S.thick_polyline(big, core, [to_px(p, ss) for p in poly], t * core_ratio * ss)
        tube = pygame.transform.smoothscale(big, (w, h))
        if pygame.display.get_surface() is not None:
            tube = tube.convert_alpha()

        glow_surf = None
        if glow > 0:
            g = pygame.Surface((w, h), 0, 32)
            gcol = tuple(min(255, int(c * glow)) for c in color)
            for poly in strokes:
                S.thick_polyline(g, gcol, [to_px(p, 1) for p in poly], t * 1.8)
            glow_surf = S.blur(g, gr)
            if pygame.display.get_surface() is not None:
                glow_surf = glow_surf.convert()
        return NeonText(tube, glow_surf, ox, oy, wu * u, 6 * u)

    def draw(self, target, text, size, color, x, y, anchor="center", alpha=255, **kw):
        nt = self.render(text, size, color, **kw)
        nt.draw(target, x, y, anchor, alpha)
        return nt

    def draw_chars(self, target, text, size, color, x, y, anchor="center", spacing=1.3, alpha=255, **kw):
        """Texte composé caractère par caractère (idéal pour les nombres qui changent sans cesse)."""
        u = size / 6.0
        items = []
        pos = 0.0
        for ch in text:
            if ch == " ":
                pos += SPACE_ADVANCE * u
                continue
            nt = self.render(ch, size, color, spacing=spacing, **kw)
            items.append((nt, pos))
            pos += nt.w + spacing * u
        total = max(0.0, pos - spacing * u)
        if anchor == "center":
            x0 = x - total / 2
        elif anchor == "midright":
            x0 = x - total
        else:
            x0 = x
        for nt, off in items:
            nt.draw(target, x0 + off, y, "midleft", alpha)
        return total
