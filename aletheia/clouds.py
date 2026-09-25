"""Forge des nuages : cumulus volumétriques en pixel art.

Un nuage est une grappe de demi-sphères (bourgeons « chou-fleur ») : champ de hauteur -> normales ->
éclairage solaire enveloppant, ombres propres entre les bourgeons (marche vers le soleil), liseré
argenté sur les bords fins tournés vers la lumière, quantification tramée (Bayer) sur une rampe.
Les bords sont effilochés et translucides (alpha tramé en quelques niveaux), entourés d'une brume
légère ; chaque nuage fournit son ombre portée floue et, pour les bancs, un masque lumineux
(éclairs à l'intérieur des nuées). Les bancs sont des textures toriques (tuilables dans les deux
sens) : couches de parallaxe qui défilent et dérivent au vent sans couture.
"""
import math
import random

import numpy as np
import pygame

from .spritegen import fbm, box_blur, arrays_to_surface, rgb_surface, BAYER, LIGHT, TAU

# rampes ombre -> lumière
DUSK = [(28, 26, 70), (50, 44, 102), (82, 66, 132), (124, 92, 152), (174, 120, 160), (218, 154, 162),
        (244, 190, 170), (255, 220, 192), (255, 242, 222)]
OLYMP = [(44, 32, 78), (72, 54, 108), (108, 82, 136), (152, 114, 156), (198, 152, 168), (232, 190, 182),
         (250, 218, 198), (255, 238, 220), (255, 250, 238)]

_LXY = math.hypot(float(LIGHT[0]), float(LIGHT[1]))
_DX, _DY = float(LIGHT[0]) / _LXY, float(LIGHT[1]) / _LXY   # direction du soleil dans le plan
_TAN = float(LIGHT[2]) / _LXY                               # pente d'un rayon solaire

CACHE = {}


def _bayer(w, h):
    return BAYER[np.arange(w) % 4][:, np.arange(h) % 4]


def _shift(a, dx, dy, wrap):
    """out[x, y] = a[x + dx, y + dy] ; repli sur les axes indiqués par wrap=(wx, wy), zéro sinon."""
    wx, wy = wrap
    w, h = a.shape
    if wx:
        a = np.roll(a, -dx, axis=0)
        dx = 0
    if wy:
        a = np.roll(a, -dy, axis=1)
        dy = 0
    if dx == 0 and dy == 0:
        return a
    out = np.zeros_like(a)
    if abs(dx) >= w or abs(dy) >= h:
        return out
    sx, tx = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
    sy, ty = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
    out[tx, ty] = a[sx, sy]
    return out


def _blur(a, r, wrap):
    if r <= 0:
        return a
    wx, wy = wrap
    px = r + 1 if wx else 0
    py = r + 1 if wy else 0
    if px or py:
        a = np.pad(a, ((px, px), (py, py)) + ((0, 0),) * (a.ndim - 2), mode="wrap")
    b = box_blur(a, r)
    if px:
        b = b[px:-px]
    if py:
        b = b[:, py:-py]
    return b


def _stamp(H, cx, cy, r, z, wrap):
    """Bourgeon : demi-sphère de rayon r posée à la hauteur z (union par maximum)."""
    if r < 0.8:
        return
    w, h = H.shape
    xs = np.arange(int(math.floor(cx - r)), int(cx + r) + 2)
    ys = np.arange(int(math.floor(cy - r)), int(cy + r) + 2)
    if wrap[0]:
        xi = xs % w
    else:
        xs = xs[(xs >= 0) & (xs < w)]
        xi = xs
    if wrap[1]:
        yi = ys % h
    else:
        ys = ys[(ys >= 0) & (ys < h)]
        yi = ys
    if not len(xs) or not len(ys):
        return
    dx = xs.astype(np.float32)[:, None] + 0.5 - cx
    dy = ys.astype(np.float32)[None, :] + 0.5 - cy
    d2 = dx * dx + dy * dy
    hh = np.where(d2 < r * r, np.sqrt(np.maximum(r * r - d2, 0.0)) + z, 0.0).astype(np.float32)
    ix = np.ix_(xi, yi)
    H[ix] = np.maximum(H[ix], hh)


def _cluster(rng, cx, cy, rx, ry, rbig, n, fringe=2, zk=0.9):
    """Bourgeons d'un cumulus vu de dessus : gros et hauts au centre, petits et bas vers les bords,
    plus une frange de petits bourgeons (bord en chou-fleur)."""
    puffs = []
    for _ in range(n):
        a = rng.uniform(0, TAU)
        t = rng.random() ** 0.75
        r = rbig * (1.0 - 0.55 * t) * rng.uniform(0.75, 1.15)
        z = rbig * zk * (1.0 - t) ** 1.3 * rng.uniform(0.5, 1.0)
        puffs.append((cx + math.cos(a) * rx * t, cy + math.sin(a) * ry * t, r, z))
    for (x, y, r, z) in list(puffs):
        for _ in range(fringe):
            a = rng.uniform(0, TAU)
            puffs.append((x + math.cos(a) * r * 0.92, y + math.sin(a) * r * 0.92, r * rng.uniform(0.26, 0.42),
                          z * 0.5))
    return puffs


def _formation(rng, H, cx, cy, s, wrap, kind=None):
    """Une formation nuageuse de taille s : tour (cumulus bourgeonnant), plaque (stratocumulus
    étiré) ou grappe (plusieurs cumulus serrés)."""
    kind = kind or rng.choice(("tower", "tower", "plate", "cluster"))
    ang = rng.uniform(-0.6, 0.6)
    if kind == "plate":
        rx, ry = s * 0.62, s * 0.26
        parts = [(0.0, 1.0)]
        zk = 0.5
    elif kind == "cluster":
        rx, ry = s * 0.5, s * 0.38
        parts = [(-0.55, 0.62), (0.1, 0.72), (0.6, 0.55)]
        zk = 0.9
    else:
        rx, ry = s * 0.46, s * 0.4
        parts = [(0.0, 1.0)]
        zk = 1.1
    for off, k in parts:
        x = cx + math.cos(ang) * off * rx
        y = cy + math.sin(ang) * off * rx * 0.6 + rng.uniform(-0.12, 0.12) * ry
        lrx, lry = rx * k * rng.uniform(0.85, 1.12), ry * k * rng.uniform(0.85, 1.12)
        rbig = min(lrx, lry) * 0.62
        for p in _cluster(rng, x, y, lrx, lry, rbig, int(8 + lrx * lry / 55), zk=zk):
            _stamp(H, *p, wrap=wrap)


def _shade(H, ramp, seed, wrap=(False, False), alpha_max=0.9, edge=2.6, haze=None, haze_k=0.0, bright=0.0,
           detail=1.0, levels=4, mist=0.3):
    """Champ de hauteur -> (rgb, alpha 0..255, hauteur lissée)."""
    w, h = H.shape
    ramp = np.asarray(ramp, np.float32)
    n = len(ramp)
    bay = _bayer(w, h)
    # micro-relief : bourgeonnement fin (bruit périodique -> reste tuilable)
    nz_ = fbm(w, h, max(2, w // 10), max(2, h // 10), 3, seed=seed)
    Hd = H + (nz_ - 0.5) * 5.0 * detail * np.clip(H / 3.0, 0, 1)
    Hs = _blur(Hd, 1, wrap)
    gx = (_shift(Hs, 1, 0, wrap) - _shift(Hs, -1, 0, wrap)) * 0.5
    gy = (_shift(Hs, 0, 1, wrap) - _shift(Hs, 0, -1, wrap)) * 0.5
    nx, ny = -gx * 0.9, -gy * 0.9
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    nx, ny, nz = nx * inv, ny * inv, inv
    lx, ly, lz = (float(v) for v in LIGHT)
    diff = np.clip((nx * lx + ny * ly + nz * lz + 0.45) / 1.45, 0, 1)
    # ombres propres : un bourgeon plus haut entre le point et le soleil l'assombrit
    occ = np.zeros_like(Hs)
    for s in range(2, 17, 2):
        sx, sy = int(round(_DX * s)), int(round(_DY * s))
        occ = np.maximum(occ, np.clip((_shift(Hs, sx, sy, wrap) - Hs - s * _TAN) / 5.0, 0, 1))
    # liseré argenté (bords fins face au soleil) + translucidité à contre-jour
    thin = np.clip(1.0 - Hd / 7.0, 0, 1)
    along = gx * _DX + gy * _DY          # > 0 : la hauteur monte vers le soleil (versant à l'ombre)
    rim = thin * np.clip(-along * 0.8, 0, 1)
    back = thin * np.clip(along * 0.8, 0, 1)
    inten = 0.16 + 0.22 * nz + diff * 0.74 * (1.0 - 0.7 * occ) + rim * 0.38 + back * 0.08 + bright
    core = np.clip((Hd - 0.3) / edge, 0, 1)
    # brume légère autour des bourgeons (teinte moyenne, très translucide)
    halo = np.clip(_blur((core > 0).astype(np.float32), 3, wrap) * 1.5, 0, 1) * mist
    inten = np.where(core > 0, inten, 0.6 + bright)
    idx = np.clip(inten, 0, 1) * (n - 1) + bay * 0.6
    rgb = ramp[np.clip(np.floor(idx + 0.5), 0, n - 1).astype(np.int32)]
    if haze is not None and haze_k > 0:
        rgb = rgb * (1.0 - haze_k) + np.asarray(haze, np.float32) * haze_k
    # alpha tramé en quelques niveaux : translucidité « pixel art »
    a = np.maximum(core, halo)
    a = np.clip(np.floor(a * levels + bay * 0.9 + 0.5), 0, levels) / levels
    return rgb, a * alpha_max * 255.0, Hs


def _border_fade(w, h, m=6):
    """Atténuation près des bords d'un sprite : jamais de coupure droite."""
    fx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / m, 0, 1)
    fy = np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / m, 0, 1)
    return fx[:, None] * fy[None, :]


def _shadow_surface(alpha, col, k, blur, wrap, off=(0, 0)):
    a = _blur(alpha / 255.0, blur, wrap)
    if off != (0, 0):
        a = _shift(a, -off[0], -off[1], wrap)
    rgb = np.zeros(a.shape + (3,), np.float32) + np.asarray(col, np.float32)
    return arrays_to_surface(rgb, a * 255.0 * k)


def cumulus(w, h, seed, ramp=DUSK, alpha_max=0.8, kind=None, shadow_col=(0, 8, 30), shadow_k=0.42,
            bright=0.0, mist=0.3):
    """Cumulus isolé vu de dessus -> (image, ombre portée), mis en cache."""
    key = ("cu", w, h, seed, id(ramp), alpha_max, kind, shadow_col, shadow_k, bright, mist)
    if key in CACHE:
        return CACHE[key]
    rng = random.Random(seed)
    H = np.zeros((w, h), np.float32)
    s = min(w / 1.45, h / 1.05)
    _formation(rng, H, w / 2, h / 2, s, (False, False), kind)
    rgb, a, _ = _shade(H, ramp, seed, alpha_max=alpha_max, bright=bright, mist=mist)
    a *= _border_fade(w, h)
    img = arrays_to_surface(rgb, a)
    sh = _shadow_surface(a, shadow_col, shadow_k, 3, (False, False))
    CACHE[key] = (img, sh)
    return img, sh


def wisp(w, h, seed, ramp=OLYMP, alpha_max=0.5):
    """Filament de brume (stratus) : bourgeons bas alignés, très translucide."""
    key = ("wisp", w, h, seed, id(ramp), alpha_max)
    if key in CACHE:
        return CACHE[key]
    rng = random.Random(seed)
    H = np.zeros((w, h), np.float32)
    ang = rng.uniform(-0.35, 0.35)
    for _ in range(int(w / 5)):
        t = rng.uniform(-0.4, 0.4)
        r = rng.uniform(4.0, 10.0) * (1.0 - abs(t) * 1.3)
        x = w / 2 + math.cos(ang) * t * w + rng.uniform(-3, 3)
        y = h / 2 + math.sin(ang) * t * w + rng.uniform(-h * 0.12, h * 0.12)
        _stamp(H, x, y, r, rng.uniform(0, 2), (False, False))
    rgb, a, _ = _shade(H, ramp, seed, alpha_max=alpha_max, edge=4.0, bright=0.12, detail=0.6, mist=0.45)
    a *= _border_fade(w, h, 10)
    img = arrays_to_surface(rgb, a)
    CACHE[key] = img
    return img


def bank(w, h, seed, ramp=OLYMP, clusters=14, size=(60, 110), alpha_max=0.92, haze=None, haze_k=0.0,
         shadow_col=None, shadow_k=0.45, shadow_off=(10, 14), glow_col=None, bright=0.0, gap=1.0, mist=0.3):
    """Banc de nuages torique (tuilable dans les deux sens) : formations distinctes séparées de
    trouées. Renvoie {'img', 'shadow' (option), 'glow' (option, RGB additif)}."""
    key = ("bank", w, h, seed, id(ramp), clusters, size, alpha_max, haze, haze_k, shadow_col, glow_col, bright,
           gap, mist)
    if key in CACHE:
        return CACHE[key]
    rng = random.Random(seed)
    wrap = (True, True)
    H = np.zeros((w, h), np.float32)
    centers = []
    tries = 0
    while len(centers) < clusters and tries < clusters * 40:
        tries += 1
        s = rng.uniform(*size)
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        ok = True
        for (cx, cy, cs) in centers:
            dx, dy = abs(x - cx), abs(y - cy)
            if math.hypot(min(dx, w - dx), min(dy, h - dy)) < (s + cs) * 0.42 * gap:
                ok = False
                break
        if ok:
            centers.append((x, y, s))
    for (x, y, s) in centers:
        _formation(rng, H, x, y, s, wrap)
    rgb, a, Hs = _shade(H, ramp, seed, wrap, alpha_max=alpha_max, haze=haze, haze_k=haze_k, bright=bright, mist=mist)
    out = {"img": arrays_to_surface(rgb, a)}
    if shadow_col is not None:
        out["shadow"] = _shadow_surface(a, shadow_col, shadow_k, 4, wrap, shadow_off)
    if glow_col is not None:
        thick = np.clip(0.3 + Hs / max(1.0, float(Hs.max())) * 1.4, 0, 1)
        g = (a / 255.0 * thick)[..., None] * np.asarray(glow_col, np.float32)[None, None, :]
        out["glow"] = rgb_surface(g)
    CACHE[key] = out
    return out


def blit_torus(dst, tex, ox, oy, area=None, flags=0):
    """Pave dst (ou la zone area=(x, y, w, h)) avec la texture torique décalée de (ox, oy)."""
    tw, th = tex.get_size()
    ax, ay, aw, ah = area or (0, 0, dst.get_width(), dst.get_height())
    x0 = ax + (int(ox) - ax) % tw - tw
    y0 = ay + (int(oy) - ay) % th - th
    y = y0
    while y < ay + ah:
        x = x0
        while x < ax + aw:
            dst.blit(tex, (x, y), None, flags)
            x += tw
        y += th


def _sun_rays(w, h, sun, seed, col, bands=8, gain=0.16, width=(0.012, 0.045)):
    """Rayons crépusculaires (valeurs RGB additives) : faisceaux doux qui divergent depuis un soleil hors
    champ, plus intenses près de la source."""
    rng = np.random.default_rng(seed)
    xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
    dx, dy = xx - sun[0], yy - sun[1]
    ang = np.arctan2(dy, dx)
    dist = np.sqrt(dx * dx + dy * dy)
    a0, a1 = float(ang.min()), float(ang.max())
    v = np.zeros((w, h), np.float32)
    for _ in range(bands):
        c = rng.uniform(a0, a1)
        wd = rng.uniform(*width)
        v += rng.uniform(0.45, 1.0) * np.exp(-((ang - c) / wd) ** 2)
    d0, d1 = float(dist.min()), float(dist.max())
    fall = np.clip(1.0 - (dist - d0) / max(1.0, d1 - d0) * 0.85, 0, 1) ** 1.4
    return (np.clip(v, 0, 1.2) * fall * gain)[..., None] * np.asarray(col, np.float32)[None, None, :]


class Rays:
    """Deux champs de rayons en fondu enchaîné lent (précalculé) : la lumière « respire » à travers
    les nuages. Une seule copie additive par image."""
    STEPS = 24

    def __init__(self, w, h, sun, seed, col, period=570, **kw):
        key = ("rays", w, h, sun, seed, col, period, tuple(sorted(kw.items())))
        if key not in CACHE:
            a, b = (_sun_rays(w, h, sun, seed + i, col, **kw) for i in range(2))
            frames = []
            for i in range(self.STEPS):
                f = 0.5 + 0.5 * math.sin(i / self.STEPS * TAU)
                frames.append(rgb_surface(np.clip(a * f + b * (1.0 - f), 0, 255)))
            CACHE[key] = frames
        self.frames = CACHE[key]
        self.period = period
        self.tmp = rgb_surface(np.zeros((w, h, 3), np.float32))

    def draw(self, add, t, k=1.0, dx=0):
        img = self.frames[int(t * self.STEPS / self.period) % self.STEPS]
        if k < 0.98:
            v = int(255 * k)
            if v < 4:
                return
            self.tmp.blit(img, (0, 0))
            self.tmp.fill((v, v, v), special_flags=pygame.BLEND_MULT)
            img = self.tmp
        add.blit(img, (dx, 0), special_flags=pygame.BLEND_ADD)
