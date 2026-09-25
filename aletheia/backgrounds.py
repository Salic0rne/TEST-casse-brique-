"""Décors procéduraux à parallaxe pour les six stades."""
import math
import random

import numpy as np
import pygame

from . import palette as P
from .spritegen import (L, forge, circle, ellipse, rect, line, polyline, arc, star, sym, move, fbm, box_blur,
                        arrays_to_surface, rgb_surface, dilate, erode, distance, Sprite, value_noise, TAU)
from .fx import glow, Particle, K_EMBER, K_GLOW, K_SMOKE

PF_W, PF_H = 256, 270
CACHE = {}


def ramp_map(v, stops):
    """v (w,h) dans [0,1] -> rgb via liste de (t, couleur)."""
    ts = np.array([s[0] for s in stops], np.float32)
    cs = np.array([s[1] for s in stops], np.float32)
    out = np.zeros(v.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(v, ts, cs[:, c])
    return out


def dither_quant(rgb, levels=24):
    """Légère quantification tramée pour garder un grain pixel-art."""
    w, h = rgb.shape[:2]
    bay = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 - 0.5)
    b = bay[np.arange(w) % 4][:, np.arange(h) % 4][..., None]
    step = 256.0 / levels
    return np.floor(rgb / step + 0.5 + b * 0.9) * step


def blob_mask(w, h, r, seed, rough=0.35, octaves=3):
    """Masque d'île / de nuage : cercle déformé par du bruit."""
    rng = np.random.default_rng(seed)
    n = fbm(w, h, 4, 4, octaves, seed=seed)
    xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = 1 - d + (n - 0.5) * rough * 2
    return v, v > 1 - r


def scorch_sprite(r):
    key = ("scorch", r)
    if key in CACHE:
        return CACHE[key]
    size = r * 2 + 5
    xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
    c = size / 2
    rng = np.random.default_rng(r)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (r + 1)
    n = rng.random((size, size)) * 0.3
    a = np.clip(1.1 - d - n, 0, 1) ** 0.8 * 170
    rgb = np.zeros((size, size, 3), np.float32)
    rgb[:] = (18, 10, 14)
    s = arrays_to_surface(rgb, a)
    CACHE[key] = s
    return s


class Scenery:
    __slots__ = ("spr", "x", "y", "layer", "spd", "img", "halo", "alpha", "add_img")

    def __init__(self, spr, x, y, layer="ground", spd=1.0, alpha=None):
        self.spr = spr
        self.x = x
        self.y = y
        self.layer = layer
        self.spd = spd
        self.img = spr.img if isinstance(spr, Sprite) else spr
        self.halo = spr.halo if isinstance(spr, Sprite) else None
        self.alpha = alpha


class Background:
    shadows = False
    raster = None      # (amplitude, fréquence, vitesse) pour la distorsion d'eau/chaleur

    def __init__(self, w, n):
        self.w = w
        self.n = n
        self.t = 0
        self.dist = 0.0
        self.scroll = 0.55
        self.target = 0.55
        self.rate = 0.01
        self.scen = []
        self.scorches = []
        self.flash = 0.0
        self.rng = random.Random(n * 77)
        self.build()

    def build(self):
        pass

    def set_speed(self, s, rate=0.01):
        self.target = s
        self.rate = rate

    def update(self):
        self.t += 1
        if self.scroll < self.target:
            self.scroll = min(self.target, self.scroll + self.rate)
        elif self.scroll > self.target:
            self.scroll = max(self.target, self.scroll - self.rate)
        self.dist += self.scroll
        for s in self.scen:
            s.y += self.scroll * s.spd
        self.scen = [s for s in self.scen if s.y - s.img.get_height() / 2 < PF_H + 40]
        for sc in self.scorches:
            sc[1] += self.scroll
        self.scorches = [s for s in self.scorches if s[1] < PF_H + 30]
        if self.flash > 0:
            self.flash = max(0.0, self.flash - 0.05)
        self.tick()

    def tick(self):
        pass

    def add(self, spr, x, y=None, layer="ground", spd=1.0, alpha=None):
        img = spr.img if isinstance(spr, Sprite) else spr
        if y is None:
            y = -img.get_height() / 2 - 2
        s = Scenery(spr, x, y, layer, spd, alpha)
        self.scen.append(s)
        return s

    def add_scorch(self, x, y, r):
        self.scorches.append([x, y, max(4, int(r))])

    def _draw_layer(self, f, layer):
        for s in self.scen:
            if s.layer == layer:
                img = s.img
                if s.alpha is not None:
                    img.set_alpha(s.alpha)
                f.blit(img, (int(s.x - img.get_width() / 2), int(s.y - img.get_height() / 2)))
                if s.alpha is not None:
                    img.set_alpha(255)

    def scroll_tile(self, f, tex, offset, x=0):
        h = tex.get_height()
        y = int(offset % h) - h
        while y < PF_H:
            f.blit(tex, (x, y))
            y += h

    # --- API de rendu ---
    def draw_far(self, f):
        f.fill((6, 4, 16))

    def draw_ground(self, f):
        self._draw_layer(f, "deep")
        self._draw_layer(f, "ground")
        for (x, y, r) in self.scorches:
            s = scorch_sprite(r)
            f.blit(s, (int(x - s.get_width() / 2), int(y - s.get_height() / 2)))

    def draw_mid(self, f):
        self._draw_layer(f, "mid")

    def draw_add(self, a):
        for s in self.scen:
            if s.halo is not None:
                a.blit(s.halo, (int(s.x - s.halo.get_width() / 2), int(s.y - s.halo.get_height() / 2)),
                       special_flags=pygame.BLEND_ADD)

    def draw_fore(self, f):
        self._draw_layer(f, "fore")


# ---------------------------------------------------------------------------
# Générateurs d'éléments de décor partagés
# ---------------------------------------------------------------------------
def temple_sprite(cols=4, rows=6, seed=0, ruined=0.0):
    """Temple grec vu de dessus : stylobate à degrés, péristyle (colonnes ombrées), toit à deux pans
    ou cella en ruine."""
    rng = random.Random(seed)
    w = 10 + cols * 6
    h = 10 + rows * 6
    hw, hh = w / 2, h / 2
    layers = [L([rect(-hw, -hh, hw, hh)], mat=P.MARBLE, bevel=1.5, base=0.6, veins=0.08),
              L([rect(-hw + 2, -hh + 2, hw - 2, hh - 2)], mat=P.STONE, bevel=1, base=0.5, noise=0.04)]
    cols_pts = []
    for i in range(cols):
        for j in range(rows):
            if 0 < i < cols - 1 and 0 < j < rows - 1:
                continue
            if rng.random() < ruined * 0.7:
                continue
            x = -hw + 5 + i * (w - 10) / max(1, cols - 1)
            y = -hh + 5 + j * (h - 10) / max(1, rows - 1)
            cols_pts.append((x, y))
    roofed = ruined < 0.3
    if not roofed:
        cx0, cx1, cy0, cy1 = -hw + 9, hw - 9, -hh + 10, hh - 9
        walls = [rect(cx0, cy0, cx1, cy0 + 1.8), rect(cx0, cy0, cx0 + 1.8, cy1), rect(cx1 - 1.8, cy0, cx1, cy1 - 6),
                 rect(cx0, cy1 - 1.8, cx1 - 7, cy1)]
        layers.append(L([move(r_, 1.2, 1.2) for r_ in walls], flat=(34, 30, 44), cast=False))
        layers.append(L(walls, mat=P.MARBLE, bevel=1, base=0.7))
        drums = [circle(rng.uniform(-hw + 4, hw - 4), rng.uniform(-hh + 4, hh - 4), 1.5, 8) for _ in range(3)]
        layers.append(L(drums, mat=P.MARBLE, profile="round", base=0.55))
    if cols_pts:
        layers.append(L([circle(x + 1.3, y + 1.4, 2.3, 10) for x, y in cols_pts], flat=(30, 26, 40), cast=False))
        layers.append(L([circle(x, y, 2.3, 10) for x, y in cols_pts], mat=P.MARBLE, profile="round", base=0.8,
                        spec=0.5))
    if roofed:
        rx0, rx1, ry0, ry1 = -hw + 8, hw - 8, -hh + 6, hh - 6
        layers.append(L([rect(rx0 + 1.5, ry0 + 1.5, rx1 + 1.5, ry1 + 1.5)], flat=(30, 26, 40), cast=False))
        layers.append(L([rect(rx0, ry0, 0, ry1)], mat=P.TERRACOTTA, bevel=1, base=0.32, grad=0.2, contrast=0.6))
        layers.append(L([rect(0, ry0, rx1, ry1)], mat=P.TERRACOTTA, bevel=1, base=0.74, grad=0.2, contrast=0.6))
        layers.append(L([rect(rx0, y, rx1, y + 0.6) for y in np.arange(ry0 + 2, ry1 - 1, 2.5)],
                        mat=P.TERRACOTTA, bevel=1, base=0.3, clip=True, cast=False))
        layers.append(L([rect(-0.7, ry0 - 1, 0.7, ry1 + 1)], mat=P.GOLD, bevel=1, spec=0.5))
        layers.append(L([[(rx0, ry0), (0, ry0 - 3), (rx1, ry0)], [(rx0, ry1), (0, ry1 + 3), (rx1, ry1)]],
                        mat=P.MARBLE, bevel=1, base=0.75))
    return forge(int(w + 6), int(h + 8), layers, halo=0, want_shadow=False)


def antenna_sprite():
    return forge(15, 15, [
        L([circle(0, 0, 5.8)], mat=P.STEEL, profile="round", spec=0.5),
        L([circle(0, 0, 3.4)], mat=P.DARKSTEEL, bevel=1, base=0.4),
        L([line(0, 0, 3, -3, 1.0)], mat=P.GOLD, bevel=1),
        L([circle(3, -3, 0.9)], emit=P.CYAN_E, glow=1.0),
    ], halo=3)


def column_top_sprite(r=4.5, broken=False):
    layers = [L([circle(0, 0, r + 1.2, 16)], mat=P.MARBLE, bevel=1, base=0.55),
              L([circle(0, 0, r, 16)], mat=P.MARBLE, profile="round", base=0.66, veins=0.1)]
    if broken:
        layers.append(L([[(-r, -1), (0, -2.5), (r, 0), (r, r), (-r, r)]], mat=P.STONE, bevel=1, clip=True))
    return forge(int(r * 2 + 6), int(r * 2 + 6), layers, halo=0)


def island_sprite(w, h, seed, rich=True):
    """Île égéenne : lagon turquoise, plage, maquis, falaises, et ruines grecques."""
    rng = random.Random(seed)
    v, m = blob_mask(w, h, 0.62, seed, 0.3)
    shallow = v > 0.22
    beach = m
    land = v > 0.5
    high = v > 0.72
    rgb = np.zeros((w, h, 3), np.float32)
    alpha = np.zeros((w, h), np.float32)
    # lagon
    lag = shallow & ~beach
    t = np.clip((v - 0.22) / 0.16, 0, 1)
    lag_col = ramp_map(t, [(0, (20, 90, 120)), (1, (70, 200, 190))])
    rgb[lag] = lag_col[lag]
    alpha[lag] = (np.clip(t, 0, 1) * 170 + 40)[lag]
    # plage
    n = fbm(w, h, 6, 6, 3, seed=seed + 1)
    sand = ramp_map(np.clip(n * 1.2, 0, 1), [(0, (196, 164, 110)), (0.5, (230, 206, 150)), (1, (250, 236, 190))])
    rgb[beach] = sand[beach]
    alpha[beach] = 255
    # terre : relief ombré par la hauteur
    hgt = np.clip((v - 0.5) / 0.4, 0, 1) + (n - 0.5) * 0.3
    hs = box_blur(hgt, 1)
    gx = np.gradient(hs, axis=0)
    gy = np.gradient(hs, axis=1)
    shade = np.clip(0.62 - (gx * 0.5 + gy * 0.8) * 6, 0, 1)
    veg = fbm(w, h, 8, 8, 3, seed=seed + 2)
    land_col = ramp_map(np.clip(shade * 0.8 + veg * 0.3, 0, 1),
                        [(0, (26, 36, 24)), (0.35, (58, 80, 40)), (0.6, (104, 124, 60)), (0.85, (150, 162, 92)),
                         (1, (200, 200, 140))])
    rock_col = ramp_map(np.clip(shade, 0, 1), [(0, (40, 34, 44)), (0.5, (120, 108, 108)), (1, (220, 210, 196))])
    rocky = high | (n > 0.62)
    lc = np.where(rocky[..., None], rock_col, land_col)
    rgb[land] = lc[land]
    rgb = dither_quant(rgb, 28)
    # contour sombre des terres
    edge = dilate(beach) & ~beach
    s = arrays_to_surface(rgb, alpha)
    # ruines
    if rich:
        n_t = rng.randint(1, 2)
        for i in range(n_t):
            tp = temple_sprite(rng.choice((3, 4)), rng.choice((5, 6)), seed + i, rng.choice((0.0, 0.6, 0.6)))
            for _ in range(20):
                x = rng.randint(tp.w // 2, w - tp.w // 2)
                y = rng.randint(tp.h // 2, h - tp.h // 2)
                if land[x, y] and land[min(w - 1, x + tp.w // 3), y] and land[max(0, x - tp.w // 3), y]:
                    s.blit(tp.img, (x - tp.w // 2, y - tp.h // 2))
                    break
        for _ in range(rng.randint(2, 5)):
            c = column_top_sprite(rng.choice((2.0, 2.6)), rng.random() < 0.5)
            x = rng.randint(6, w - 6)
            y = rng.randint(6, h - 6)
            if land[x, y]:
                s.blit(c.img, (x - c.w // 2, y - c.h // 2))
    return s


class _Glints:
    def __init__(self):
        self.pts = []

    def update(self, scroll, band=(0.0, 1.0), rate=3):
        rnd = random.random
        for _ in range(rate):
            y = PF_H * (band[0] + (band[1] - band[0]) * rnd())
            self.pts.append([rnd() * PF_W, y, 0, 10 + int(rnd() * 20)])
        for p in self.pts:
            p[1] += scroll
            p[2] += 1
        self.pts = [p for p in self.pts if p[2] < p[3]]

    def draw(self, a, col=(255, 230, 180)):
        for x, y, t, life in self.pts:
            k = math.sin(t / life * math.pi)
            c = (int(col[0] * k), int(col[1] * k), int(col[2] * k))
            a.fill(c, (int(x), int(y), 1, 1))
            if k > 0.7:
                a.fill((c[0] // 3, c[1] // 3, c[2] // 3), (int(x) - 1, int(y), 3, 1))


# ---------------------------------------------------------------------------
# STADE I — THALASSA : la mer de Poséidon au crépuscule
# ---------------------------------------------------------------------------
class Thalassa(Background):
    shadows = True

    def build(self):
        W, H = PF_W, 512
        depth = fbm(W, H, 3, 6, 4, seed=11)
        v2 = fbm(W, H, 8, 16, 3, seed=12)
        t = np.clip(depth * 0.85 + v2 * 0.25 - 0.05, 0, 1)
        base = ramp_map(t, [(0.0, (5, 14, 44)), (0.3, (8, 30, 76)), (0.55, (14, 54, 104)), (0.8, (22, 84, 128)),
                            (1.0, (38, 116, 150))])
        yy = np.arange(H, dtype=np.float32)[None, :]
        swell = np.sin(yy * 0.19 + fbm(W, H, 4, 8, 2, seed=15) * 7.0)
        base *= (1.0 + swell * 0.045)[..., None]
        self.deep = rgb_surface(dither_quant(base, 36))
        # crêtes de vagues : 4 couches qui scintillent en alternance
        self.wave_layers = []
        dens = fbm(W, 256, 4, 4, 3, seed=16)
        for k in range(4):
            rng = np.random.default_rng(100 + k)
            rgb = np.zeros((W, 256, 3), np.float32)
            a = np.zeros((W, 256), np.float32)
            n = 900
            xs = rng.integers(0, W, n)
            ys = rng.integers(0, 256, n)
            for x, y in zip(xs, ys):
                if rng.random() > np.clip((dens[x, y] - 0.36) * 3.2, 0.06, 1.0):
                    continue
                ln = int(rng.integers(2, 6))
                for i in range(ln):
                    xx = (x + i) % W
                    c = 1.0 - abs(i - ln / 2) / ln
                    rgb[xx, y] = (110 + 90 * c, 180 + 50 * c, 225)
                    a[xx, y] = max(a[xx, y], 60 + 110 * c)
                    yb = (y + 1) % 256
                    if a[xx, yb] == 0:
                        rgb[xx, yb] = (6, 26, 64)
                        a[xx, yb] = 90
            self.wave_layers.append(arrays_to_surface(rgb, a))
        self.statue = self.make_statue()
        self.islands = [island_sprite(112, 92, 100 + i, True) for i in range(3)] + \
                       [island_sprite(70, 60, 200 + i, True) for i in range(2)]
        self.rocks = [island_sprite(24, 20, 300 + i, False) for i in range(3)]
        self.clouds = [self.make_cloud(110, 70, 400 + i) for i in range(3)]
        self.glints = _Glints()
        self.next_rock = 60
        self.next_cloud = 100

    def make_statue(self):
        """Statue engloutie de Poséidon : silhouette floue vue à travers l'eau."""
        w, h = 200, 260
        s = pygame.Surface((w, h))
        s.fill((0, 0, 0))
        c = (255, 255, 255)
        pygame.draw.ellipse(s, c, (60, 40, 80, 96))
        pygame.draw.polygon(s, c, [(62, 110), (138, 110), (124, 170), (100, 200), (76, 170)])
        for i in range(7):
            x = 66 + i * 11
            pygame.draw.polygon(s, c, [(x, 46), (x + 5, 14 - (i % 2) * 8), (x + 10, 46)])
        pygame.draw.ellipse(s, c, (14, 146, 172, 44))
        pygame.draw.rect(s, c, (166, 30, 9, 230))
        for dx in (-20, 0, 20):
            pygame.draw.polygon(s, c, [(170 + dx - 5, 44), (170 + dx, 4), (170 + dx + 5, 44)])
        pygame.draw.rect(s, c, (146, 40, 50, 7))
        m = pygame.surfarray.array_red(s).astype(np.float32) / 255
        m = box_blur(box_blur(m, 2), 2)
        rgb = np.zeros((w, h, 3), np.float32)
        rgb[:] = (2, 10, 30)
        out = arrays_to_surface(rgb, m * 150)
        for (x, y) in ((86, 84), (114, 84)):
            g = glow(6, (40, 150, 170))
            out.blit(g, (x - 6, y - 6), special_flags=pygame.BLEND_RGB_ADD)
        return out

    def make_cloud(self, w, h, seed):
        v, m = blob_mask(w, h, 0.45, seed, 0.55, 4)
        n = fbm(w, h, 6, 6, 3, seed=seed + 5)
        a = np.clip((v - 0.35) / 0.5, 0, 1) * (0.6 + 0.4 * n) * 200
        rgb = ramp_map(np.clip(n + 0.1, 0, 1), [(0, (200, 170, 190)), (0.6, (250, 230, 220)), (1, (255, 250, 240))])
        img = arrays_to_surface(rgb, a)
        shadow = arrays_to_surface(np.zeros((w, h, 3), np.float32) + (0, 10, 30), a * 0.45)
        return img, shadow

    def tick(self):
        s = self.scroll
        self.glints.update(s, (0.05, 0.55), 3)
        self.next_rock -= s
        if self.next_rock <= 0:
            self.next_rock = self.rng.uniform(80, 200)
            self.add(self.rng.choice(self.rocks), self.rng.uniform(10, PF_W - 10))
        self.next_cloud -= s
        if self.next_cloud <= 0:
            self.next_cloud = self.rng.uniform(180, 320)
            img, sh = self.rng.choice(self.clouds)
            x = self.rng.uniform(0, PF_W)
            self.add(sh, x + 24, -60, "ground", 1.6)
            self.add(img, x, -80, "fore", 1.6, alpha=150)

    def spawn_island(self, i, x):
        return self.add(self.islands[i % len(self.islands)], x)

    def show_statue(self, x=128):
        self.add(self.statue, x, -140, "deep", 0.5)

    def draw_far(self, f):
        self.scroll_tile(f, self.deep, self.dist * 0.8)

    def draw_ground(self, f):
        self._draw_layer(f, "deep")
        # scintillement des crêtes : deux couches en fondu, décalées lentement (houle)
        ph = self.t * 0.035
        for k in range(4):
            a = math.sin(ph + k * math.pi / 2)
            if a <= 0:
                continue
            lay = self.wave_layers[k]
            lay.set_alpha(int(255 * a))
            off = self.dist + math.sin(self.t * 0.013 + k) * 2
            h = lay.get_height()
            y = int(off % h) - h
            xo = int(math.sin(self.t * 0.01 + k * 1.7) * 3)
            while y < PF_H:
                f.blit(lay, (xo, y))
                if xo:
                    f.blit(lay, (xo - PF_W if xo > 0 else xo + PF_W, y))
                y += h
            lay.set_alpha(255)
        self._draw_layer(f, "ground")
        for (x, y, r) in self.scorches:
            sc = scorch_sprite(r)
            f.blit(sc, (int(x - sc.get_width() / 2), int(y - sc.get_height() / 2)))

    def draw_add(self, a):
        Background.draw_add(self, a)
        self.glints.draw(a, (255, 210, 160))
        # halo du soleil couchant en haut de l'écran
        g = glow(90, (40, 20, 10))
        a.blit(g, (PF_W // 2 - 90, -120), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------------------
# Fabrique
# ---------------------------------------------------------------------------
def make(n, w):
    cls = {1: Thalassa}.get(n)
    if cls is None:
        from . import backgrounds2
        cls = backgrounds2.CLASSES[n]
    return cls(w, n)
