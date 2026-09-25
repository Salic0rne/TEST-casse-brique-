"""Décors des stades II à VI : Labyrinthos, Gorgoneion, Hephaisteion, Tartaros, Olympos."""
import math
import random

import numpy as np
import pygame

from . import palette as P
from . import clouds
from .backgrounds import (Background, ramp_map, dither_quant, blob_mask, temple_sprite, column_top_sprite,
                          PF_W, PF_H)
from .spritegen import (fbm, rgb_surface, opaque_surface, arrays_to_surface, box_blur, dilate, erode, L, forge,
                        circle, rect, line, polyline, sym, _shade, LIGHT, TAU)
from .fx import glow, Particle, K_SMOKE


def blur_wrap(a, r):
    """Flou boîte périodique (texture tuilable sans couture)."""
    if r <= 0:
        return a
    p = np.pad(a, ((r, r), (r, r)) + ((0, 0),) * (a.ndim - 2), mode="wrap")
    return box_blur(p, r)[r:-r, r:-r]


def shade_wrap(mask, ramp, **kw):
    """Ombrage d'un masque tuilable verticalement (évite la couture en haut/bas)."""
    ext = np.concatenate([mask[:, -20:], mask, mask[:, :20]], axis=1)
    return mask_to_surface(ext, ramp, **kw)[:, 20:-20]


def stars_layer(n, seed, spd):
    rng = random.Random(seed)
    return [[rng.random() * PF_W, rng.random() * PF_H, spd * rng.uniform(0.7, 1.3), rng.random()] for _ in range(n)]


def draw_stars(f, stars, scroll, t, col=(255, 255, 255)):
    for s in stars:
        s[1] += scroll * s[2]
        if s[1] > PF_H:
            s[1] -= PF_H
            s[0] = random.random() * PF_W
        k = 0.55 + 0.45 * math.sin(t * 0.05 + s[3] * 20)
        b = s[2] * 0.6 + 0.3
        c = (int(col[0] * k * min(1, b)), int(col[1] * k * min(1, b)), int(col[2] * k * min(1, b)))
        f.fill(c, (int(s[0]), int(s[1]), 1, 1))


def soft_blob(w, h, col, alpha, seed, rough=0.5):
    v, m = blob_mask(w, h, 0.45, seed, rough, 4)
    a = np.clip((v - 0.35) / 0.5, 0, 1) ** 1.2 * alpha
    rgb = np.zeros((w, h, 3), np.float32)
    rgb[:] = col
    return arrays_to_surface(rgb, a)


def girder(w=PF_W, h=10):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((16, 16, 30, 170))
    pygame.draw.line(s, (60, 64, 96, 190), (0, 1), (w, 1))
    pygame.draw.line(s, (6, 6, 12, 200), (0, h - 1), (w, h - 1))
    for x in range(0, w, 16):
        pygame.draw.line(s, (40, 42, 70, 170), (x, 2), (x + 8, h - 2))
        s.fill((150, 110, 50, 200), (x + 3, 3, 1, 1))
    return s


def mask_to_surface(mask, ramp, bevel=2.0, base=0.58, spec=0.3, noise=0.0, seed=1, profile="bevel"):
    layer = L([], mat=ramp, bevel=bevel, base=base, spec=spec, noise=noise, profile=profile, dither=0.4)
    rgb = _shade(mask, layer, LIGHT, np.random.default_rng(seed))
    return rgb


# ---------------------------------------------------------------------------
# STADE II — LABYRINTHOS : station-dédale en orbite de Crète
# ---------------------------------------------------------------------------
def torus_maze(cols, rows, seed, braid=0.35):
    """Labyrinthe par parcours en profondeur, torique verticalement (texture sans raccord)."""
    rng = random.Random(seed)
    right = [[True] * rows for _ in range(cols)]    # mur entre (c,r) et (c+1,r)
    down = [[True] * rows for _ in range(cols)]     # mur entre (c,r) et (c,r+1 mod rows)
    seen = [[False] * rows for _ in range(cols)]
    stack = [(0, 0)]
    seen[0][0] = True
    while stack:
        c, r = stack[-1]
        nb = []
        if c > 0 and not seen[c - 1][r]:
            nb.append((c - 1, r, "L"))
        if c < cols - 1 and not seen[c + 1][r]:
            nb.append((c + 1, r, "R"))
        if not seen[c][(r - 1) % rows]:
            nb.append((c, (r - 1) % rows, "U"))
        if not seen[c][(r + 1) % rows]:
            nb.append((c, (r + 1) % rows, "D"))
        if not nb:
            stack.pop()
            continue
        nc, nr, d = rng.choice(nb)
        if d == "L":
            right[nc][r] = False
        elif d == "R":
            right[c][r] = False
        elif d == "U":
            down[c][nr] = False
        else:
            down[c][r] = False
        seen[nc][nr] = True
        stack.append((nc, nr))
    for c in range(cols):
        for r in range(rows):
            if rng.random() < braid:
                right[c][r] = False
            if rng.random() < braid:
                down[c][r] = False
    return right, down


class Labyrinthos(Background):
    shadows = True

    def build(self):
        W, H = PF_W, 512
        rng = np.random.default_rng(21)
        tile = 32
        xx, yy = np.mgrid[0:W, 0:H]
        tx, ty = xx % tile, yy % tile
        tid = (xx // tile) + (yy // tile) * (W // tile)
        tb = rng.random((W // tile) * (H // tile))[tid] * 0.1
        n = fbm(W, H, 8, 16, 3, seed=21)
        v = 0.3 + tb + (n - 0.5) * 0.08
        v = v + ((tx == 0) | (ty == 0)) * 0.1 - ((tx == tile - 1) | (ty == tile - 1)) * 0.12
        floor = ramp_map(np.clip(v, 0, 1), [(0, (6, 6, 16)), (0.3, (20, 22, 42)), (0.5, (38, 42, 68)),
                                            (1, (92, 100, 140))])
        self.floor = rgb_surface(dither_quant(floor, 40))
        self.glow_tex = opaque_surface((W, H))
        self.glow_tex.fill((0, 0, 0))
        prng = random.Random(22)
        for cx in range(0, W, tile):
            for cy in range(0, H, tile):
                r = prng.random()
                if r < 0.22:
                    # glyphe du labyrinthe (spirale carrée) incrusté d'or
                    gold = (126, 90, 38)
                    for k, m_ in enumerate((5, 9, 13)):
                        rr = pygame.Rect(cx + m_, cy + m_, tile - 2 * m_, tile - 2 * m_)
                        if rr.w <= 2:
                            break
                        pygame.draw.rect(self.floor, (8, 8, 18), rr.move(1, 1), 1)
                        pygame.draw.rect(self.floor, gold, rr, 1)
                        gap = (rr.x + rr.w // 2 - 1, rr.y) if k % 2 == 0 else (rr.x + rr.w // 2 - 1, rr.bottom - 1)
                        pygame.draw.rect(self.floor, (30, 32, 54), (gap[0], gap[1], 3, 1))
                elif r < 0.36:
                    pygame.draw.rect(self.floor, (14, 14, 26), (cx + 6, cy + 6, tile - 12, tile - 12))
                    for gy in range(cy + 8, cy + tile - 8, 3):
                        pygame.draw.line(self.floor, (30, 32, 52), (cx + 7, gy), (cx + tile - 8, gy))
                elif r < 0.46:
                    pygame.draw.line(self.glow_tex, (10, 60, 80), (cx + 2, cy + tile // 2), (cx + tile - 3, cy + tile // 2))
                    pygame.draw.circle(self.glow_tex, (30, 120, 150), (cx + tile // 2, cy + tile // 2), 2)
        # murs du dédale
        cols, rows, cell = 4, 8, 64
        right, down = torus_maze(cols, rows, 23, braid=0.12)
        ms = opaque_surface((W, H))
        ms.fill((0, 0, 0))
        wt = 13
        for c in range(cols):
            for r in range(rows):
                x0, y0 = c * cell, r * cell
                if c < cols - 1 and right[c][r]:
                    pygame.draw.rect(ms, (255, 255, 255), (x0 + cell - wt // 2, y0 - wt // 2, wt, cell + wt))
                if down[c][r]:
                    yb = (y0 + cell) % H
                    pygame.draw.rect(ms, (255, 255, 255), (x0 - wt // 2, yb - wt // 2, cell + wt, wt))
                    if yb - wt // 2 < 0:
                        pygame.draw.rect(ms, (255, 255, 255), (x0 - wt // 2, H - wt // 2, cell + wt, wt))
        mask = pygame.surfarray.array_red(ms) > 127
        # ombrage périodique : on travaille sur une version étendue pour éviter les coutures
        ext = np.concatenate([mask[:, -16:], mask, mask[:, :16]], axis=1)
        rgb = mask_to_surface(ext, P.STEEL, bevel=4.0, base=0.55, spec=0.4, seed=24)[:, 16:-16]
        # liseré doré au sommet des murs
        top = erode(erode(erode(erode(erode(mask)))))
        rgb[top] = rgb[top] * 0.35 + np.array(P.GOLD[3], np.float32) * 0.65
        alpha = mask.astype(np.float32) * 255
        sh = np.roll(np.roll(mask, 6, axis=0), 8, axis=1) & ~mask
        rgb[sh] = (4, 2, 12)
        alpha[sh] = 150
        out = dilate(mask) & ~mask & ~sh
        rgb[out] = P.OUTLINE
        alpha[out] = 255
        self.walls = arrays_to_surface(rgb, alpha)
        # lumières d'alerte aux intersections
        self.lights = []
        for c in range(1, cols):
            for r in range(rows):
                if prng.random() < 0.5:
                    self.lights.append((c * cell, r * cell, prng.random() * 6))
        self.next_vent = 40
        self.girder = girder()
        self.next_girder = 260

    def tick(self):
        w = self.w
        fx = getattr(w, "fx", None)
        self.next_girder -= self.scroll
        if self.next_girder <= 0:
            self.next_girder = self.rng.uniform(380, 620)
            self.add(self.girder, PF_W / 2, -10, "fore", 1.6)
        self.next_vent -= 1
        if fx is not None and self.next_vent <= 0:
            self.next_vent = random.randint(30, 90)
            x = random.uniform(20, PF_W - 20)
            for i in range(4):
                fx.add(Particle(K_SMOKE, x + random.uniform(-3, 3), -4 + random.uniform(0, 30), random.uniform(-0.2, 0.2),
                                self.scroll + random.uniform(-0.4, 0.1), 50, 3, 12, (60, 64, 90), drag=0.98,
                                delay=i * 3))

    def draw_far(self, f):
        self.scroll_tile(f, self.floor, self.dist)

    def draw_ground(self, f):
        self.scroll_tile(f, self.walls, self.dist)
        Background.draw_ground(self, f)

    def draw_add(self, a):
        h = self.glow_tex.get_height()
        y = int(self.dist % h) - h
        while y < PF_H:
            a.blit(self.glow_tex, (0, y), special_flags=pygame.BLEND_ADD)
            y += h
        t = self.t
        for (x, y0, ph) in self.lights:
            y = (y0 + self.dist) % h
            if y > PF_H + 8:
                y -= h
            k = max(0.0, math.sin(t * 0.08 + ph))
            if k > 0.05:
                g = glow(6, (int(200 * k), int(20 * k), int(30 * k)), 0.3 * k)
                a.blit(g, (int(x - 6), int(y - 6)), special_flags=pygame.BLEND_ADD)
        Background.draw_add(self, a)


# ---------------------------------------------------------------------------
# STADE III — GORGONEION : la nuée de Méduse
# ---------------------------------------------------------------------------
def petrified_statue():
    """Hoplite pétrifié géant dérivant dans la nuée."""
    w, h = 120, 170
    layers = [
        L([line(40, -70, -30, 80, 5)], mat=P.STONE, bevel=2, noise=0.08),
        L([sym([(0, -58), (12, -54), (16, -40), (26, -30), (30, 0), (22, 40), (14, 76), (0, 80)])], mat=P.STONE,
          bevel=3, noise=0.09, base=0.52),
        L([sym([(0, -78), (9, -74), (12, -60), (8, -50), (0, -48)])], mat=P.STONE, profile="round", noise=0.08),
        L([sym([(0, -84), (2, -80), (2, -58), (0, -54)])], mat=P.STONE, bevel=1, base=0.4),
        L([circle(-30, 4, 26)], mat=P.STONE, profile="round", noise=0.08, base=0.5),
        L([circle(-30, 4, 19)], mat=P.STONE, bevel=2, base=0.42, noise=0.06),
        L(polyline([(-44, -8), (-30, 4), (-20, -12), (-8, 2)], 1.2) + polyline([(10, -30), (4, 0), (14, 30)], 1.2),
          emit=(60, 230, 140), glow=1.0),
    ]
    return forge(w, h, layers, halo=4)


class Gorgoneion(Background):
    def build(self):
        W, H = PF_W, 512
        n1 = fbm(W, H, 3, 6, 5, seed=31)
        n2 = fbm(W, H, 5, 10, 4, seed=32)
        rgb = np.zeros((W, H, 3), np.float32)
        rgb[:] = (5, 4, 14)
        g = np.clip((n1 - 0.42) / 0.4, 0, 1) ** 1.6
        rgb += g[..., None] * np.array([18, 110, 80], np.float32)
        pu = np.clip((n2 - 0.48) / 0.4, 0, 1) ** 1.7
        rgb += pu[..., None] * np.array([110, 40, 140], np.float32)
        rng = np.random.default_rng(33)
        for _ in range(260):
            x, y = rng.integers(0, W), rng.integers(0, H)
            rgb[x, y] += rng.random() ** 2 * 180 + 30
        self.neb = rgb_surface(dither_quant(np.clip(rgb, 0, 255), 40))
        n3 = fbm(W, H, 4, 8, 4, seed=34)
        wa = np.clip((n3 - 0.55) / 0.3, 0, 1) ** 1.3 * 110
        wc = ramp_map(n3, [(0, (40, 160, 110)), (1, (150, 90, 200))])
        self.wisps = arrays_to_surface(wc, wa)
        self.stars1 = stars_layer(40, 35, 0.35)
        self.stars2 = stars_layer(25, 36, 0.8)
        from .sprites import S
        self.debris = []
        for key in ("rock_s", "rock_m", "rock_l"):
            for var in S[key]:
                img = var[0].img.copy()
                img.fill((120, 120, 130, 255), special_flags=pygame.BLEND_RGBA_MULT)
                self.debris.append(img)
        self.statue = petrified_statue()
        self.next_deb = 30
        self.fore = []
        for img in self.debris[-4:]:
            big = pygame.transform.scale(img, (img.get_width() * 2, img.get_height() * 2))
            big.fill((20, 14, 30, 170), special_flags=pygame.BLEND_RGBA_MULT)
            self.fore.append(big)
        self.next_fore = 200

    def tick(self):
        self.next_fore -= self.scroll
        if self.next_fore <= 0:
            self.next_fore = self.rng.uniform(260, 520)
            img = self.rng.choice(self.fore)
            x = self.rng.choice((self.rng.uniform(-10, 30), self.rng.uniform(PF_W - 30, PF_W + 10)))
            self.add(img, x, -40, "fore", 2.2)
        self.next_deb -= self.scroll
        if self.next_deb <= 0:
            self.next_deb = self.rng.uniform(40, 110)
            img = self.rng.choice(self.debris)
            self.add(img, self.rng.uniform(0, PF_W), None, "deep", self.rng.uniform(0.5, 0.8))

    def show_statue(self, x=150):
        self.add(self.statue, x, -90, "deep", 0.7)

    def draw_far(self, f):
        self.scroll_tile(f, self.neb, self.dist * 0.25)
        draw_stars(f, self.stars1, self.scroll * 0.3, self.t, (200, 230, 255))
        self.scroll_tile(f, self.wisps, self.dist * 0.55)
        draw_stars(f, self.stars2, self.scroll * 0.8, self.t)


# ---------------------------------------------------------------------------
# STADE IV — HEPHAISTEION : la forge sur Io
# ---------------------------------------------------------------------------
def forge_building(seed):
    rng = random.Random(seed)
    w = rng.choice((44, 52, 60))
    h = rng.choice((40, 48))
    hw, hh = w / 2, h / 2
    layers = [
        L([rect(-hw, -hh, hw, hh)], mat=P.OBSIDIAN, bevel=2, base=0.5, noise=0.05),
        L([rect(-hw + 4, -hh + 4, 0, hh - 4)], mat=P.BRONZE, bevel=1.5, base=0.38, contrast=0.6),
        L([rect(0, -hh + 4, hw - 4, hh - 4)], mat=P.BRONZE, bevel=1.5, base=0.66, contrast=0.6),
        L([rect(-0.8, -hh + 3, 0.8, hh - 3)], mat=P.GOLD, bevel=1),
        L([circle(-hw + 9, -hh + 9, 5.5), circle(hw - 9, hh - 9, 4.5)], mat=P.DARKSTEEL, profile="round"),
        L([circle(-hw + 9, -hh + 9, 3.2), circle(hw - 9, hh - 9, 2.6)], emit=(255, 120, 30), glow=1.2),
    ]
    spr = forge(int(w + 6), int(h + 6), layers, halo=4, want_shadow=True)
    chimneys = [(-hw + 9, -hh + 9), (hw - 9, hh - 9)]
    return spr, chimneys


class Hephaisteion(Background):
    shadows = True

    def build(self):
        W, H = PF_W, 512
        rock = fbm(W, H, 6, 12, 5, seed=41)
        ridge = 1 - np.abs(fbm(W, H, 3, 6, 4, seed=43) * 2 - 1)
        lava = np.clip((ridge - 0.925) / 0.05, 0, 1)
        crust = np.clip((ridge - 0.85) / 0.075, 0, 1) * (1 - lava)
        cracks = (np.abs(fbm(W, H, 12, 24, 2, seed=42) - 0.5) < 0.018)
        base = ramp_map(rock, [(0, (6, 4, 10)), (0.4, (22, 16, 22)), (0.7, (44, 32, 36)), (1, (78, 60, 56))])
        base[cracks] *= 0.45
        lava_col = ramp_map(lava, [(0, (110, 18, 8)), (0.5, (210, 70, 16)), (0.85, (255, 150, 50)),
                                   (1, (255, 214, 120))])
        base = base * (1 - crust[..., None] * 0.55) + np.array([70, 16, 8], np.float32) * crust[..., None] * 0.55
        m = lava > 0.02
        base[m] = lava_col[m]
        self.ground = rgb_surface(dither_quant(base, 40))
        # lueur de lave animée (4 phases)
        self.lava_glow = []
        for k in range(4):
            fl = fbm(W, H, 8, 16, 3, seed=50 + k)
            e = (np.clip((ridge - 0.86) / 0.12, 0, 1) ** 1.5) * (0.55 + 0.6 * fl)
            e = blur_wrap(e, 2)
            rgb = e[..., None] * np.array([150, 50, 12], np.float32)
            self.lava_glow.append(rgb_surface(rgb))
        self.buildings = [forge_building(60 + i) for i in range(3)]
        self.chimneys = []     # (scenery, dx, dy)
        self.next_b = 80

    def tick(self):
        self.next_b -= self.scroll
        if self.next_b <= 0:
            self.next_b = self.rng.uniform(110, 220)
            spr, ch = self.rng.choice(self.buildings)
            sc = self.add(spr, self.rng.uniform(30, PF_W - 30))
            for (dx, dy) in ch:
                self.chimneys.append((sc, dx, dy))
        self.chimneys = [c for c in self.chimneys if c[0].y < PF_H + 40]
        fx = getattr(self.w, "fx", None)
        if fx is not None:
            if self.t % 3 == 0:
                fx.embers(random.uniform(0, PF_W), PF_H + 2, 1, spread=4, vy=-1.1)
            for (sc, dx, dy) in self.chimneys:
                if random.random() < 0.18:
                    x, y = sc.x + dx, sc.y + dy
                    fx.add(Particle(K_SMOKE, x, y, random.uniform(-0.2, 0.2), self.scroll - 0.5, 60, 3, 13,
                                    (40, 30, 34), drag=0.985))
                    if random.random() < 0.4:
                        fx.embers(x, y, 1, spread=3, vy=-0.8)

    def draw_far(self, f):
        self.scroll_tile(f, self.ground, self.dist)
        if self.w is not None and getattr(self.w, "post", None) is not None:
            self.w.post.raster_wave(f, self.t, amp=1.2, freq=0.09, speed=0.12)

    def draw_add(self, a):
        k = (self.t // 10) % 4
        tex = self.lava_glow[k]
        h = tex.get_height()
        y = int(self.dist % h) - h
        while y < PF_H:
            a.blit(tex, (0, y), special_flags=pygame.BLEND_ADD)
            y += h
        Background.draw_add(self, a)


# ---------------------------------------------------------------------------
# STADE V — TARTAROS : les Enfers au bord du trou noir
# ---------------------------------------------------------------------------
class Tartaros(Background):
    def build(self):
        W, H = PF_W, 512
        # disque d'accrétion (face) puis projeté en ellipse, 24 orientations
        S_ = 240
        xx, yy = np.mgrid[0:S_, 0:S_].astype(np.float32)
        c = S_ / 2
        dx, dy = xx - c, yy - c
        r = np.sqrt(dx * dx + dy * dy) / c
        ang = np.arctan2(dy, dx)
        spiral = np.sin(ang * 3 + np.log(np.maximum(r, 0.05)) * 9) * 0.5 + 0.5
        n = fbm(S_, S_, 6, 6, 4, seed=51)
        inten = np.clip(1 - np.abs(r - 0.62) / 0.36, 0, 1) ** 1.3 * (0.55 + 0.45 * spiral) * (0.7 + 0.5 * n)
        inten *= (r > 0.26)
        col = ramp_map(np.clip(inten, 0, 1), [(0, (0, 0, 0)), (0.3, (90, 20, 60)), (0.6, (230, 90, 40)),
                                               (0.85, (255, 200, 120)), (1, (255, 250, 230))])
        face = rgb_surface(col)
        self.disk = []
        for i in range(24):
            rot = pygame.transform.rotate(face, i * 15)
            rw, rh = rot.get_size()
            self.disk.append(pygame.transform.smoothscale(rot, (int(rw * 1.25), int(rh * 0.36))))
        # vallée de pierre et Styx (texture avec vide transparent)
        yy2 = np.arange(H, dtype=np.float32)
        cx = 128 + 44 * np.sin(yy2 / H * TAU) + 18 * np.sin(yy2 / H * TAU * 2 + 1.0)
        halfw = 74 + 10 * np.sin(yy2 / H * TAU * 3)
        xs = np.arange(W, dtype=np.float32)[:, None]
        edge_n = (fbm(W, H, 16, 32, 3, seed=52) - 0.5) * 22
        d = np.abs(xs - cx[None, :]) + edge_n
        land = d < halfw[None, :]
        rn = fbm(W, H, 8, 16, 4, seed=53)
        rock = ramp_map(rn, [(0, (8, 6, 14)), (0.5, (26, 20, 36)), (0.8, (48, 40, 60)), (1, (80, 70, 96))])
        rgb = shade_wrap(land, [(10, 8, 18), (22, 18, 32), (36, 30, 50), (56, 48, 74), (84, 74, 104),
                                (120, 110, 140)], bevel=4, base=0.5, noise=0.05, seed=54)
        rgb = rgb * 0.5 + rock * 0.5
        river_w = 12 + 4 * np.sin(yy2 / H * TAU * 4)
        rd = np.abs(xs - cx[None, :])
        river = rd < river_w[None, :]
        bank = (rd < river_w[None, :] + 3) & ~river
        rgb[bank] = (30, 60, 70)
        rv = ramp_map(np.clip(1 - rd / river_w[None, :], 0, 1), [(0, (10, 60, 70)), (1, (40, 170, 170))])
        rgb[river] = rv[river]
        alpha = land.astype(np.float32) * 255
        outl = dilate(land) & ~land
        rgb[outl] = (2, 0, 6)
        alpha[outl] = 255
        self.valley = arrays_to_surface(dither_quant(rgb, 40), alpha)
        # flot des âmes : texture de reflets masquée par la rivière
        fl = fbm(W, H, 6, 24, 3, seed=55)
        fe = np.clip((fl - 0.55) / 0.2, 0, 1)
        self.flow = rgb_surface(fe[..., None] * np.array([60, 200, 190], np.float32))
        rm = np.zeros((W, H, 3), np.float32)
        rm[river] = 255
        self.river_mask = rgb_surface(rm)
        self.tmp = opaque_surface((PF_W, PF_H))
        self.stars1 = stars_layer(50, 57, 0.15)
        self.souls = []
        self.mists = [soft_blob(140, 80, (60, 40, 90), 70, 70 + i) for i in range(3)]
        self.next_mist = 120

    def tick(self):
        self.next_mist -= self.scroll
        if self.next_mist <= 0:
            self.next_mist = self.rng.uniform(220, 400)
            self.add(self.rng.choice(self.mists), self.rng.uniform(0, PF_W), -50, "fore", 1.4)
        if random.random() < 0.35:
            self.souls.append([random.uniform(0, PF_W), PF_H + 4, random.uniform(-0.2, 0.2), random.uniform(0.4, 1.0),
                               random.random() * 6])
        for s in self.souls:
            s[0] += s[2] + math.sin(self.t * 0.05 + s[4]) * 0.2
            s[1] -= s[3]
        self.souls = [s for s in self.souls if s[1] > -6]

    def draw_far(self, f):
        f.fill((2, 0, 6))
        draw_stars(f, self.stars1, self.scroll * 0.15, self.t, (180, 160, 220))
        i = (self.t // 6) % 24
        d = self.disk[i]
        cx, cy = PF_W // 2, 70
        f.blit(d, (cx - d.get_width() // 2, cy - d.get_height() // 2), special_flags=pygame.BLEND_ADD)
        pygame.draw.ellipse(f, (0, 0, 0), (cx - 26, cy - 12, 52, 24))
        pygame.draw.ellipse(f, (255, 200, 150), (cx - 28, cy - 14, 56, 28), 1)

    def draw_ground(self, f):
        self.scroll_tile(f, self.valley, self.dist)
        Background.draw_ground(self, f)

    def draw_add(self, a):
        tmp = self.tmp
        h = self.flow.get_height()
        off = self.dist * 1.0 + self.t * 0.6
        y = int(off % h) - h
        while y < PF_H:
            tmp.blit(self.flow, (0, y))
            y += h
        y = int(self.dist % h) - h
        while y < PF_H:
            tmp.blit(self.river_mask, (0, y), special_flags=pygame.BLEND_MULT)
            y += h
        a.blit(tmp, (0, 0), special_flags=pygame.BLEND_ADD)
        for s in self.souls:
            k = 0.5 + 0.5 * math.sin(self.t * 0.1 + s[4])
            g = glow(3, (int(60 * k), int(140 * k), int(150 * k)))
            a.blit(g, (int(s[0] - 3), int(s[1] - 3)), special_flags=pygame.BLEND_ADD)
        Background.draw_add(self, a)


# ---------------------------------------------------------------------------
# STADE VI — OLYMPOS : au-dessus des nuées de Jupiter
# ---------------------------------------------------------------------------
def tholos_sprite(seed=0, r=16):
    n = 10
    cols = [circle(math.cos(i * TAU / n) * (r - 3), math.sin(i * TAU / n) * (r - 3), 1.9, 10) for i in range(n)]
    shadows = [circle(math.cos(i * TAU / n) * (r - 3) + 1.2, math.sin(i * TAU / n) * (r - 3) + 1.3, 1.9, 10)
               for i in range(n)]
    layers = [
        L([circle(0, 0, r + 3)], mat=P.MARBLE, bevel=1.5, base=0.62),
        L([circle(0, 0, r)], mat=P.MARBLE, bevel=1, base=0.5),
        L(shadows, flat=(40, 34, 50), cast=False),
        L(cols, mat=P.MARBLE, profile="round", base=0.8, spec=0.5),
        L([circle(0, 0, r - 7)], mat=P.GOLD, profile="round", spec=0.6),
        L([circle(-1, -1, 1.8)], emit=(255, 240, 180), glow=1.0),
    ]
    return forge(int(r * 2 + 10), int(r * 2 + 10), layers, halo=3, want_shadow=True)


def sky_island(seed, w=100, h=80, kind="temple"):
    v, m = blob_mask(w, h, 0.6, seed, 0.25)
    rgb = mask_to_surface(m, P.OLIVE, bevel=4, base=0.55, noise=0.05, seed=seed)
    plaza = (v > 0.66) & (v < 0.76)
    rgb[plaza] = rgb[plaza] * 0.3 + np.array(P.MARBLE[4], np.float32) * 0.7
    rim = m & ~erode(erode(m))
    rgb[rim] = np.array(P.MARBLE[3], np.float32)
    alpha = m.astype(np.float32) * 255
    o = dilate(m) & ~m
    rgb[o] = P.OUTLINE
    alpha[o] = 255
    s = arrays_to_surface(dither_quant(rgb, 40), alpha)
    rng = random.Random(seed)
    if kind == "temple":
        tp = temple_sprite(4, 6, seed, 0.0)
        s.blit(tp.img, (w // 2 - tp.w // 2, h // 2 - tp.h // 2))
    else:
        th = tholos_sprite(seed)
        s.blit(th.img, (w // 2 - th.w // 2, h // 2 - th.h // 2))
    for _ in range(4):
        c = column_top_sprite(2.2, rng.random() < 0.3)
        x, y = rng.randint(8, w - 8), rng.randint(8, h - 8)
        if m[x, y]:
            s.blit(c.img, (x - c.w // 2, y - c.h // 2))
    shadow = arrays_to_surface(np.zeros((w, h, 3), np.float32) + (30, 20, 50), alpha * 0.35)
    return s, shadow


class Olympos(Background):
    shadows = True

    def build(self):
        W, H = PF_W, 512
        # Jupiter, loin en contrebas : bandes nuageuses tourbillonnaires sous une brume violette
        n = fbm(W, H, 4, 8, 5, seed=61)
        warp = fbm(W, H, 3, 6, 3, seed=63)
        yy = np.arange(H, dtype=np.float32)[None, :]
        xx = np.arange(W, dtype=np.float32)[:, None]
        bands = np.sin(yy * (TAU * 6 / H) + warp * 5.5 + np.sin(xx * (TAU / W)) * 0.5)
        t = np.clip(0.5 + 0.33 * bands + (n - 0.5) * 0.7, 0, 1)
        deep = ramp_map(t, [(0, (24, 16, 46)), (0.3, (46, 30, 70)), (0.55, (84, 50, 80)), (0.75, (124, 80, 88)),
                            (0.9, (156, 108, 102)), (1, (182, 136, 120))])
        self.deep = rgb_surface(dither_quant(deep, 36))
        # deux bancs de cumulus : bas (voilé par la brume) et moyen (éclairé, ombre portée, éclairs internes)
        self.low = clouds.bank(PF_W, 640, 91, clouds.OLYMP, clusters=34, size=(30, 64), alpha_max=0.82,
                               haze=(92, 70, 132), haze_k=0.45, mist=0.35)
        self.mid = clouds.bank(PF_W, 768, 92, clouds.OLYMP, clusters=12, size=(64, 118), alpha_max=0.95,
                               shadow_col=(26, 14, 50), shadow_k=0.5, glow_col=(150, 175, 255))
        self.ltmp = opaque_surface((145, 145))
        self.islands = [sky_island(70 + i, 132, 104, "temple" if i % 2 == 0 else "tholos") for i in range(4)]
        self.next_i = 90
        self.wisps = [clouds.wisp(160, 60, 80 + i) for i in range(3)]
        self.next_wisp = 150
        self.rays = clouds.Rays(PF_W, PF_H, (-60, -90), 17, (255, 214, 150), gain=0.2)
        self.flash_t = 0
        self.flash_x = PF_W / 2
        self.flash_y = PF_H / 3
        self.storm = False
        self.storm_k = 0.0
        self.dark = opaque_surface((PF_W, PF_H))

    def tick(self):
        self.next_i -= self.scroll
        if self.next_i <= 0:
            self.next_i = self.rng.uniform(170, 280)
            img, sh = self.rng.choice(self.islands)
            x = self.rng.uniform(40, PF_W - 40)
            self.add(sh, x + 22, -70, "ground", 1.0)
            self.add(img, x, -80, "ground", 1.0)
        self.next_wisp -= self.scroll
        if self.next_wisp <= 0:
            self.next_wisp = self.rng.uniform(240, 420)
            x = self.rng.choice((self.rng.uniform(-30, 50), self.rng.uniform(PF_W - 50, PF_W + 30)))
            self.add(self.rng.choice(self.wisps), x, -40, "fore", 1.9)
        if self.storm:
            self.storm_k = min(1.0, self.storm_k + 0.005)
        if random.random() < 0.006 + 0.02 * self.storm_k:
            self.flash = 0.8
            self.flash_x = random.uniform(20, PF_W - 20)
            self.flash_y = random.uniform(40, PF_H - 40)
            if getattr(self.w, "audio", None) is not None:
                self.w.audio.play("thunder", self.flash_x, 0.35, throttle=60)

    def drift(self):
        return self.t * 0.07          # le vent pousse lentement le banc moyen

    def draw_far(self, f):
        self.scroll_tile(f, self.deep, self.dist * 0.3)
        if self.flash > 0:
            k = int(self.flash * 90)
            g = glow(60, (k, k, int(k * 1.2)))
            f.blit(g, (int(self.flash_x - 60), int(self.flash_y - 60)), special_flags=pygame.BLEND_ADD)
        d = self.drift()
        clouds.blit_torus(f, self.low["img"], -d * 0.4, self.dist * 0.45)
        clouds.blit_torus(f, self.mid["shadow"], d, self.dist * 0.8)
        clouds.blit_torus(f, self.mid["img"], d, self.dist * 0.8)
        if self.storm_k > 0:
            k = self.storm_k * (1 - self.flash * 0.6)
            self.dark.fill((int(255 - 150 * k), int(255 - 160 * k), int(255 - 110 * k)))
            f.blit(self.dark, (0, 0), special_flags=pygame.BLEND_MULT)
            if self.flash > 0.3:
                pts = [(self.flash_x, 0)]
                x = self.flash_x
                for yy in range(20, int(self.flash_y), 20):
                    x += random.uniform(-12, 12)
                    pts.append((x, yy))
                if len(pts) > 1:
                    pygame.draw.lines(f, (200, 210, 255), False, pts, 1)

    def draw_add(self, a):
        k = 1 - self.storm_k
        if k > 0.05:
            # rayons du soleil entre les cumulus (s'éteignent quand l'orage de Zeus se lève)
            self.rays.draw(a, self.t, k, int(math.sin(self.t * 0.004) * 8))
        if self.flash > 0.05:
            # l'éclair illumine les nuées de l'intérieur (bleuté, épais au cœur des cumulus)
            R = 72
            x0, y0 = int(self.flash_x) - R, int(self.flash_y) - R
            tmp = self.ltmp
            tmp.fill((0, 0, 0))
            clouds.blit_torus(tmp, self.mid["glow"], self.drift() - x0, self.dist * 0.8 - y0)
            tmp.blit(glow(R, (255, 255, 255)), (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            v = int(255 * min(1.0, self.flash))
            tmp.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            a.blit(tmp, (x0, y0), special_flags=pygame.BLEND_ADD)
        Background.draw_add(self, a)


CLASSES = {2: Labyrinthos, 3: Gorgoneion, 4: Hephaisteion, 5: Tartaros, 6: Olympos}
