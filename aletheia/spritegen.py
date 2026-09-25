"""La Forge d'Héphaïstos : générateur de sprites pixel-art procéduraux.

Chaque sprite est décrit comme une pile de calques de polygones (modèle centré,
y vers le bas). Chaque calque reçoit un matériau (rampe de couleurs) et un
profil de relief ; la forge calcule un champ de distance -> hauteur -> normales,
éclaire depuis le haut-gauche, quantifie sur la rampe avec un tramage de Bayer,
projette de petites ombres portées entre calques, ajoute un contour sombre,
et produit un halo lumineux pour les parties émissives.
"""
import math

import numpy as np
import pygame

from . import palette as P

TAU = math.pi * 2

_L = np.array([-0.5, -0.72, 0.62], dtype=np.float32)
LIGHT = _L / np.linalg.norm(_L)

BAYER = ((np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0 - 0.5)


# ---------------------------------------------------------------------------
# Primitives géométriques (espace modèle)
# ---------------------------------------------------------------------------
def circle(cx, cy, r, n=None):
    n = n or max(12, int(r * 6))
    return [(cx + math.cos(i * TAU / n) * r, cy + math.sin(i * TAU / n) * r) for i in range(n)]


def ellipse(cx, cy, rx, ry, rot=0.0, n=None):
    n = n or max(12, int(max(rx, ry) * 6))
    c, s = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n):
        a = i * TAU / n
        x, y = math.cos(a) * rx, math.sin(a) * ry
        pts.append((cx + x * c - y * s, cy + x * s + y * c))
    return pts


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def line(x0, y0, x1, y1, w=1.0):
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / d * w / 2, dx / d * w / 2
    return [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]


def polyline(pts, w=1.0):
    """Liste de quads pour une ligne brisée épaisse."""
    return [line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], w) for i in range(len(pts) - 1)]


def arc(cx, cy, r0, r1, a0, a1, n=None):
    """Secteur d'anneau entre les angles a0 et a1 (radians)."""
    n = n or max(6, int(abs(a1 - a0) * r1 * 1.5))
    outer = [(cx + math.cos(a0 + (a1 - a0) * i / n) * r1, cy + math.sin(a0 + (a1 - a0) * i / n) * r1)
             for i in range(n + 1)]
    inner = [(cx + math.cos(a1 - (a1 - a0) * i / n) * r0, cy + math.sin(a1 - (a1 - a0) * i / n) * r0)
             for i in range(n + 1)]
    return outer + inner


def star(cx, cy, r0, r1, n, rot=0.0):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r0
        a = rot + i * math.pi / n - math.pi / 2
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def sym(half):
    """Contour symétrique à partir de la moitié droite (du haut vers le bas)."""
    return list(half) + [(-x, y) for (x, y) in reversed(half)]


def mirror(poly):
    return [(-x, y) for (x, y) in poly]


def move(poly, dx=0.0, dy=0.0, rot=0.0, sx=1.0, sy=1.0):
    c, s = math.cos(rot), math.sin(rot)
    return [(dx + (x * sx) * c - (y * sy) * s, dy + (x * sx) * s + (y * sy) * c) for (x, y) in poly]


# ---------------------------------------------------------------------------
# Bruit (textures)
# ---------------------------------------------------------------------------
def value_noise(w, h, gx, gy, rng):
    """Bruit de valeur périodique (tuilable), grille gx*gy, sortie (w,h) dans [0,1]."""
    g = rng.random((gx, gy)).astype(np.float32)
    xs = np.arange(w, dtype=np.float32) * gx / w
    ys = np.arange(h, dtype=np.float32) * gy / h
    x0 = np.floor(xs).astype(np.int32)
    y0 = np.floor(ys).astype(np.int32)
    fx = xs - x0
    fy = ys - y0
    x0 %= gx
    y0 %= gy
    x1 = (x0 + 1) % gx
    y1 = (y0 + 1) % gy
    sx = (fx * fx * (3 - 2 * fx))[:, None]
    sy = (fy * fy * (3 - 2 * fy))[None, :]
    v00 = g[x0[:, None], y0[None, :]]
    v10 = g[x1[:, None], y0[None, :]]
    v01 = g[x0[:, None], y1[None, :]]
    v11 = g[x1[:, None], y1[None, :]]
    a = v00 + (v10 - v00) * sx
    b = v01 + (v11 - v01) * sx
    return a + (b - a) * sy


def fbm(w, h, gx, gy, octaves=4, seed=0, persistence=0.5):
    rng = np.random.default_rng(seed)
    total = np.zeros((w, h), np.float32)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        total += value_noise(w, h, gx * (2 ** o), gy * (2 ** o), rng) * amp
        norm += amp
        amp *= persistence
    return total / norm


def box_blur(a, r):
    """Flou boîte séparable (axes 0 et 1) via sommes cumulées."""
    if r <= 0:
        return a
    extra = ((0, 0),) * (a.ndim - 2)
    p = np.pad(a, ((r + 1, r), (0, 0)) + extra)
    cs = np.cumsum(p, axis=0)
    a = (cs[2 * r + 1:] - cs[:-2 * r - 1]) / (2 * r + 1)
    p = np.pad(a, ((0, 0), (r + 1, r)) + extra)
    cs = np.cumsum(p, axis=1)
    return (cs[:, 2 * r + 1:] - cs[:, :-2 * r - 1]) / (2 * r + 1)


# ---------------------------------------------------------------------------
# Morphologie
# ---------------------------------------------------------------------------
def erode(m, diag=False):
    p = np.pad(m, 1, constant_values=False)
    r = p[1:-1, 1:-1] & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    if diag:
        r &= p[:-2, :-2] & p[2:, 2:] & p[:-2, 2:] & p[2:, :-2]
    return r


def dilate(m, diag=True):
    p = np.pad(m, 1, constant_values=False)
    r = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    if diag:
        r |= p[:-2, :-2] | p[2:, 2:] | p[:-2, 2:] | p[2:, :-2]
    return r


def distance(m, cap=64):
    d = np.zeros(m.shape, np.float32)
    cur = m.copy()
    for i in range(cap):
        if not cur.any():
            break
        d += cur
        cur = erode(cur, diag=(i % 2 == 1))
    return d


# ---------------------------------------------------------------------------
# Calques
# ---------------------------------------------------------------------------
def L(shapes, mat=None, emit=None, flat=None, bevel=2.0, profile="bevel", base=0.58, contrast=1.0,
      spec=0.3, cast=True, noise=0.0, glow=0.0, sub=None, mirror=False, dither=0.5, clip=False,
      rim=None, bump=1.0, grad=0.12, veins=0.0, erase=False, seed=1):
    return dict(shapes=shapes, mat=mat, emit=emit, flat=flat, bevel=bevel, profile=profile, base=base,
                contrast=contrast, spec=spec, cast=cast, noise=noise, glow=glow, sub=sub or [],
                mirror=mirror, dither=dither, clip=clip, rim=rim, bump=bump, grad=grad, veins=veins,
                erase=erase, seed=seed)


def raster(w, h, polys, subs, ax, ay, rot=0.0, sx=1.0, sy=1.0, ss=3, xform=None):
    surf = pygame.Surface((w * ss, h * ss))
    surf.fill((0, 0, 0))
    c, s = math.cos(rot), math.sin(rot)

    def tp(pt):
        x, y = pt
        if xform is not None:
            x, y = xform(x, y)
        x *= sx
        y *= sy
        return ((ax + x * c - y * s) * ss, (ay + x * s + y * c) * ss)

    for poly in polys:
        if len(poly) >= 3:
            pygame.draw.polygon(surf, (255, 255, 255), [tp(p) for p in poly])
    for poly in subs:
        if len(poly) >= 3:
            pygame.draw.polygon(surf, (0, 0, 0), [tp(p) for p in poly])
    arr = pygame.surfarray.array_red(surf).astype(np.float32)
    cov = arr.reshape(w, ss, h, ss).mean(axis=(1, 3))
    return cov > 127


def _shade(m, layer, light, rng):
    ramp = np.array(layer["mat"], np.float32)
    n = len(ramp)
    prof = layer["profile"]
    if prof == "flat":
        hgt = m.astype(np.float32)
        k = 1.2
    elif prof == "round":
        d = distance(m, 64)
        R = max(1.0, float(d.max()))
        t = np.clip(d / R, 0, 1)
        hgt = np.sqrt(np.clip(1 - (1 - t) ** 2, 0, 1))
        k = R * 0.85
    elif prof == "pillow":
        b = max(1.0, layer["bevel"])
        d = distance(m, int(math.ceil(b)) + 1)
        t = np.clip(d / b, 0, 1)
        hgt = t * t * (3 - 2 * t)
        k = b * 1.1
    else:  # bevel
        b = max(1.0, layer["bevel"])
        d = distance(m, int(math.ceil(b)) + 1)
        hgt = np.clip(d / b, 0, 1)
        k = b * 1.0
    hgt = hgt * m
    # lissage léger pour des normales propres
    hs = box_blur(hgt, 1) if prof != "flat" else box_blur(hgt, 1) * 0.9 + hgt * 0.1
    hs = np.where(m, hs, 0)
    p = np.pad(hs, 1, mode="edge")
    gx = (p[2:, 1:-1] - p[:-2, 1:-1]) * 0.5
    gy = (p[1:-1, 2:] - p[1:-1, :-2]) * 0.5
    k *= layer["bump"]
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(gx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv
    lx, ly, lz = light
    diff = np.clip(nx * lx + ny * ly + nz * lz, 0, 1)
    inten = layer["base"] + (diff - lz) * layer["contrast"]
    if layer["spec"]:
        hx, hy, hz = lx, ly, lz + 1.0
        hn = math.sqrt(hx * hx + hy * hy + hz * hz)
        sp = np.clip((nx * hx + ny * hy + nz * hz) / hn, 0, 1) ** 24
        inten += sp * layer["spec"]
    w, h = m.shape
    xs, ys = np.nonzero(m)
    if len(xs):
        x0, x1 = xs.min(), xs.max() + 1
        y0, y1 = ys.min(), ys.max() + 1
        gxr = (np.arange(w, dtype=np.float32) - x0) / max(1, x1 - x0)
        gyr = (np.arange(h, dtype=np.float32) - y0) / max(1, y1 - y0)
        inten += layer["grad"] * (0.5 - (gxr[:, None] * 0.35 + gyr[None, :] * 0.65))
    if layer["noise"]:
        inten += (rng.random((w, h)).astype(np.float32) - 0.5) * 2 * layer["noise"]
    if layer["veins"]:
        vn = fbm(w, h, 3, 3, 3, seed=layer["seed"])
        xx = np.arange(w, dtype=np.float32)[:, None]
        yy = np.arange(h, dtype=np.float32)[None, :]
        v = np.abs(np.sin(xx * 0.31 + yy * 0.17 + vn * 9.0))
        inten -= (v < 0.13) * layer["veins"]
    idx = inten * (n - 1)
    if layer["dither"]:
        bx = BAYER[np.arange(w) % 4][:, np.arange(h) % 4]
        idx = idx + bx * layer["dither"]
    idx = np.clip(np.floor(idx + 0.5), 0, n - 1).astype(np.int32)
    rgb = ramp[idx]
    if layer["rim"]:
        col, amt = layer["rim"]
        dd = distance(m, 2)
        edge = (dd == 1) & ((nx * lx + ny * ly) < -0.05)
        rgb[edge] = rgb[edge] * (1 - amt) + np.array(col, np.float32) * amt
    return rgb


def _shade_emit(m, col):
    d = distance(m, 8)
    wh = np.clip((d - 1) / 3.0, 0, 0.85)[..., None]
    c = np.array(col, np.float32)[None, None, :]
    return c + (255 - c) * wh


class Sprite:
    """Image + silhouette blanche (impact) + ombre + halo additif."""
    __slots__ = ("img", "flash", "shadow", "halo", "w", "h", "ox", "oy", "hox", "hoy", "mask")

    def __init__(self, img, flash=None, shadow=None, halo=None, ox=None, oy=None, hpad=0, mask=None):
        self.img = img
        self.flash = flash
        self.shadow = shadow
        self.halo = halo
        self.w, self.h = img.get_size()
        self.ox = self.w / 2 if ox is None else ox
        self.oy = self.h / 2 if oy is None else oy
        self.hox = self.ox + hpad
        self.hoy = self.oy + hpad
        self.mask = mask

    def draw(self, surf, x, y, flash=False):
        surf.blit(self.flash if (flash and self.flash) else self.img, (int(x - self.ox), int(y - self.oy)))

    def draw_halo(self, surf, x, y):
        if self.halo is not None:
            surf.blit(self.halo, (int(x - self.hox), int(y - self.hoy)), special_flags=pygame.BLEND_ADD)

    def draw_shadow(self, surf, x, y):
        if self.shadow is not None:
            surf.blit(self.shadow, (int(x - self.ox), int(y - self.oy)))


def arrays_to_surface(rgb, alpha):
    w, h = alpha.shape
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8))
    pa = pygame.surfarray.pixels_alpha(s)
    pa[:] = np.clip(alpha, 0, 255).astype(np.uint8)
    del pa
    return s


def rgb_surface(rgb):
    w, h = rgb.shape[:2]
    s = pygame.Surface((w, h))
    pygame.surfarray.blit_array(s, np.clip(rgb, 0, 255).astype(np.uint8))
    return s


def forge(w, h, layers, anchor=None, rot=0.0, sx=1.0, sy=1.0, outline=P.OUTLINE, light=None, halo=3,
          halo_gain=1.0, ss=3, xform=None, flash_col=(255, 250, 240), shadow_alpha=96, want_shadow=False,
          outline_diag=True, seed=7):
    ax, ay = anchor if anchor else (w / 2.0, h / 2.0)
    light = LIGHT if light is None else light
    rng = np.random.default_rng(seed)
    union = np.zeros((w, h), bool)
    rgb = np.zeros((w, h, 3), np.float32)
    glowmap = np.zeros((w, h, 3), np.float32)
    has_glow = False
    for layer in layers:
        polys = list(layer["shapes"])
        subs = list(layer["sub"])
        if layer["mirror"]:
            polys += [mirror(p) for p in layer["shapes"]]
            subs += [mirror(p) for p in layer["sub"]]
        m = raster(w, h, polys, subs, ax, ay, rot, sx, sy, ss, xform)
        if layer["erase"]:
            union &= ~m
            rgb[m] = 0
            glowmap[m] = 0
            continue
        if layer["clip"]:
            m &= union
        if not m.any():
            continue
        if layer["cast"] and union.any():
            sh = np.zeros_like(m)
            sh[1:, 1:] = m[:-1, :-1]
            sh &= union & ~m
            rgb[sh] *= 0.6
        if layer["emit"] is not None:
            col = _shade_emit(m, layer["emit"])
            if layer["glow"]:
                glowmap[m] += np.array(layer["emit"], np.float32) * layer["glow"]
                has_glow = True
        elif layer["flat"] is not None:
            col = np.broadcast_to(np.array(layer["flat"], np.float32), (w, h, 3))
        else:
            col = _shade(m, layer, light, rng)
        rgb[m] = col[m]
        union |= m
    alpha = union.astype(np.float32) * 255
    full = union
    if outline is not None:
        o = dilate(union, diag=outline_diag) & ~union
        rgb[o] = outline
        alpha[o] = 255
        full = union | o
    img = arrays_to_surface(rgb, alpha)
    fl = np.zeros((w, h, 3), np.float32)
    fl[:] = flash_col
    flash = arrays_to_surface(fl, full.astype(np.float32) * 255)
    shadow = None
    if want_shadow:
        shc = np.zeros((w, h, 3), np.float32)
        shc[:] = (8, 4, 24)
        shadow = arrays_to_surface(shc, full.astype(np.float32) * shadow_alpha)
    halo_s = None
    pad = 0
    if has_glow and halo > 0:
        pad = halo * 2
        g = np.pad(glowmap, ((pad, pad), (pad, pad), (0, 0)))
        g = box_blur(g, halo)
        g = box_blur(g, max(1, halo // 2))
        g = g * (1.6 * halo_gain)
        halo_s = rgb_surface(g)
    return Sprite(img, flash, shadow, halo_s, ax, ay, pad, mask=full)


def forge_rot(w, h, layers, n=16, **kw):
    """Série de sprites pour n orientations (0 = modèle tel quel, sens horaire)."""
    return [forge(w, h, layers, rot=i * TAU / n, **kw) for i in range(n)]


def rot_index(angle, n, base=math.pi / 2):
    """Index de rotation pour pointer dans la direction 'angle' (modèle orienté vers 'base')."""
    return int(round((angle - base) / TAU * n)) % n


# ---------------------------------------------------------------------------
# Sprites ASCII (icônes)
# ---------------------------------------------------------------------------
def ascii_sprite(rows, colors, outline=None):
    h = len(rows)
    w = max(len(r) for r in rows)
    rgb = np.zeros((w, h, 3), np.float32)
    alpha = np.zeros((w, h), np.float32)
    m = np.zeros((w, h), bool)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in colors:
                rgb[x, y] = colors[c]
                alpha[x, y] = 255
                m[x, y] = True
    if outline is not None:
        pad = 1
        rgb = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)))
        alpha = np.pad(alpha, pad)
        m = np.pad(m, pad)
        o = dilate(m) & ~m
        rgb[o] = outline
        alpha[o] = 255
    return arrays_to_surface(rgb, alpha)


def tint_surface(surf, color):
    s = surf.copy()
    s.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def silhouette(surf, color, alpha=255):
    s = surf.copy()
    s.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.fill(color + (0,), special_flags=pygame.BLEND_RGBA_ADD)
    if alpha != 255:
        s.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return s
