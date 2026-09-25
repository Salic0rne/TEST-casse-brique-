"""Éléments d'interface à la grecque : texte métallique, frises (méandres), colonnes ioniques, cadres."""
import math

import numpy as np
import pygame

from . import palette as P
from . import font as F
from .spritegen import _shade, L, arrays_to_surface, dilate, LIGHT, forge, rect, circle, ellipse
from .util import clamp

_cache = {}


def metal_text(text, scale=2, ramp=None, outline=(10, 6, 22), bevel=1.5, glow_col=None):
    """Texte en relief métallique (or par défaut) à partir de la police bitmap."""
    ramp = ramp or P.GOLD
    key = (text, scale, tuple(map(tuple, ramp)), outline, bevel)
    if key in _cache:
        return _cache[key]
    m = F.FONT.text_mask(text)
    if scale != 1:
        m = np.repeat(np.repeat(m, scale, axis=0), scale, axis=1)
    pad = 2
    m = np.pad(m, pad)
    layer = L([], mat=ramp, bevel=bevel, base=0.6, contrast=1.15, spec=0.45, grad=0.35, dither=0.35)
    rgb = _shade(m, layer, LIGHT, np.random.default_rng(1))
    alpha = m.astype(np.float32) * 255
    if outline is not None:
        o = dilate(m) & ~m
        rgb[o] = outline
        alpha[o] = 255
        o2 = dilate(m | o) & ~(m | o)
        rgb[o2] = (outline[0] // 2, outline[1] // 2, outline[2] // 2)
        alpha[o2] = 140
    s = arrays_to_surface(rgb, alpha)
    _cache[key] = s
    return s


def draw_metal(surf, text, x, y, scale=2, ramp=None, align="center"):
    img = metal_text(text, scale, ramp)
    if align == "center":
        x -= img.get_width() // 2
    elif align == "right":
        x -= img.get_width()
    surf.blit(img, (int(x), int(y - (F.BODY_TOP * scale) - 2)))
    return img


def greekify(text):
    """ALETHEIA -> ΛLΣTHΣIΛ (typographie « faux grec »)."""
    return text.upper().replace("A", "Λ").replace("E", "Σ")


def meander(surf, x0, y, width, col=(200, 150, 60), dark=(80, 50, 20), size=6):
    """Frise de méandres (clé grecque) horizontale."""
    s = size
    x = x0
    pygame.draw.line(surf, col, (x0, y - 1), (x0 + width - 1, y - 1))
    pygame.draw.line(surf, col, (x0, y + s + 1), (x0 + width - 1, y + s + 1))
    while x + s <= x0 + width:
        pts = [(x, y + s), (x, y), (x + s - 1, y), (x + s - 1, y + s - 2), (x + 2, y + s - 2), (x + 2, y + 2),
               (x + s - 3, y + 2)]
        pygame.draw.lines(surf, col, False, pts)
        pygame.draw.line(surf, dark, (x + 1, y + s), (x + s, y + s))
        x += s + 1


def meander_v(surf, x, y0, height, col=(200, 150, 60), size=6):
    s = size
    y = y0
    while y + s <= y0 + height:
        pts = [(x + s, y), (x, y), (x, y + s - 1), (x + s - 2, y + s - 1), (x + s - 2, y + 2), (x + 2, y + 2),
               (x + 2, y + s - 3)]
        pygame.draw.lines(surf, col, False, pts)
        y += s + 1


def column_surface(h, w=13):
    """Colonne ionique verticale (fût cannelé + chapiteau à volutes + base)."""
    key = ("col", h, w)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((w + 8, h), pygame.SRCALPHA)
    # fût cannelé
    ramp = P.MARBLE
    for x in range(w):
        t = x / (w - 1)
        k = 0.35 + 0.65 * math.sin(t * math.pi) ** 0.7 - 0.25 * t
        if x % 3 == 0:
            k -= 0.22
        idx = int(clamp(k * 5.2, 0, 5))
        pygame.draw.line(s, ramp[idx], (4 + x, 14), (4 + x, h - 12))
    pygame.draw.line(s, P.OUTLINE, (3, 14), (3, h - 12))
    pygame.draw.line(s, P.OUTLINE, (4 + w, 14), (4 + w, h - 12))
    # chapiteau
    cap = forge(w + 8, 16, [
        L([rect(-(w + 6) / 2, -2.5, (w + 6) / 2, 2.0)], mat=P.MARBLE, bevel=1, base=0.62),
        L([circle(-(w + 1) / 2 + 1.5, 1.5, 3.2), circle((w + 1) / 2 - 1.5, 1.5, 3.2)], mat=P.MARBLE, profile="round",
          base=0.66),
        L([circle(-(w + 1) / 2 + 1.5, 1.5, 1.0), circle((w + 1) / 2 - 1.5, 1.5, 1.0)], mat=P.GOLD, profile="round"),
        L([rect(-(w + 7) / 2, -6.5, (w + 7) / 2, -3.2)], mat=P.MARBLE, bevel=1, base=0.7),
    ], halo=0)
    s.blit(cap.img, (0, 0))
    base = forge(w + 8, 13, [
        L([rect(-(w + 6) / 2, 1.5, (w + 6) / 2, 5.5)], mat=P.MARBLE, bevel=1, base=0.6),
        L([ellipse(0, -1.0, (w + 3) / 2, 2.2)], mat=P.MARBLE, profile="round", base=0.66),
    ], halo=0)
    s.blit(base.img, (0, h - 13))
    _cache[key] = s
    return s


def panel_frame(surf, rect_, col=(200, 150, 60), fill=(8, 6, 24, 210)):
    x, y, w, h = rect_
    p = pygame.Surface((w, h), pygame.SRCALPHA)
    p.fill(fill)
    surf.blit(p, (x, y))
    pygame.draw.rect(surf, col, (x, y, w, h), 1)
    pygame.draw.rect(surf, (col[0] // 3, col[1] // 3, col[2] // 3), (x + 2, y + 2, w - 4, h - 4), 1)
    for (cx, cy) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        pygame.draw.rect(surf, col, (cx - 1, cy - 1, 3, 3))


def laurel(surf, x, y, flip=False, col=(150, 170, 80), n=5):
    """Petite branche de laurier."""
    d = -1 if flip else 1
    for i in range(n):
        px = x + d * i * 3
        py = y - i * 1
        pygame.draw.ellipse(surf, col, (px - 1, py - 3, 3, 4))
        pygame.draw.ellipse(surf, col, (px - 1, py + 1, 3, 4))
    pygame.draw.line(surf, (110, 120, 60), (x, y + 1), (x + d * (n - 1) * 3, y + 1 - (n - 1)))


# ---------------------------------------------------------------------------
# Logo monumental : lettres lapidaires (façon inscription grecque) ciselées dans l'or
# ---------------------------------------------------------------------------
def _glyph_polys(ch, x0, h=28.0, sw=5.0):
    """Polygones d'une lettre de 20 unités de large, empattements compris."""
    R = lambda a, b, c, d: rect(x0 + a, b, x0 + c, d)
    serif = 1.6
    if ch == "Λ":
        return [[(x0 + 0, h), (x0 + 8.3, 0), (x0 + 11.7, 0), (x0 + 20, h), (x0 + 15, h), (x0 + 10, 7),
                 (x0 + 5, h)], R(-2, h - serif, 7, h), R(13, h - serif, 22, h)]
    if ch == "L":
        return [R(1, 0, 1 + sw, h), R(1, h - sw, 19, h), R(-1, 0, 3 + sw, serif), R(17.5, h - sw - 3, 19, h)]
    if ch == "Σ":
        return [R(0, 0, 19, sw), R(0, h - sw, 19, h),
                [(x0 + 0, 0), (x0 + 6.5, 0), (x0 + 13.5, h / 2), (x0 + 6.5, h), (x0 + 0, h), (x0 + 7, h / 2)],
                R(17.4, 0, 19, sw + 3), R(17.4, h - sw - 3, 19, h)]
    if ch == "T":
        return [R(0, 0, 20, sw), R(7.5, 0, 12.5, h), R(5, h - serif, 15, h), R(0, 0, 1.6, sw + 3),
                R(18.4, 0, 20, sw + 3)]
    if ch == "H":
        return [R(1, 0, 1 + sw, h), R(14, 0, 14 + sw, h), R(1 + sw, 11.5, 14, 16.5), R(-1, 0, 3 + sw, serif),
                R(-1, h - serif, 3 + sw, h), R(12, 0, 16 + sw, serif), R(12, h - serif, 16 + sw, h)]
    if ch == "I":
        return [R(7.5, 0, 12.5, h), R(4, 0, 16, serif), R(4, h - serif, 16, h)]
    return []


def logo_surface(text="ΛLΣTHΣIΛ"):
    key = ("logo", text)
    if key in _cache:
        return _cache[key]
    adv = 24.0
    polys = []
    for i, ch in enumerate(text):
        polys += _glyph_polys(ch, i * adv)
    w = int(len(text) * adv) + 10
    h = 40
    layers = [
        L(polys, mat=P.GOLD, bevel=2.6, base=0.62, contrast=1.2, spec=0.55, grad=0.4, dither=0.3),
    ]
    spr = forge(w, h, layers, anchor=(6, 6), outline=P.OUTLINE, halo=0, ss=4)
    img = spr.img
    # seconde ombre douce sous le logo
    sh = img.copy()
    sh.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    sh.fill((6, 2, 14, 0), special_flags=pygame.BLEND_RGBA_ADD)
    sh.fill((255, 255, 255, 150), special_flags=pygame.BLEND_RGBA_MULT)
    out = pygame.Surface((w + 3, h + 3), pygame.SRCALPHA)
    out.blit(sh, (3, 3))
    out.blit(img, (0, 0))
    _cache[key] = out
    _cache[("logo_letters", text)] = img
    return out


def logo_shine(text="ΛLΣTHΣIΛ"):
    """Masque additif (lettres seules) pour le reflet qui balaie le logo."""
    logo_surface(text)
    img = _cache[("logo_letters", text)]
    a = pygame.surfarray.array_alpha(img).astype(np.float32) / 255.0
    rgb = a[..., None] * np.array([120, 105, 70], np.float32)[None, None, :]
    s = pygame.Surface(img.get_size())
    pygame.surfarray.blit_array(s, rgb.astype(np.uint8))
    return s
