"""Décor synthwave animé : ciel dégradé, soleil rayé, montagnes filaires, grille infinie."""

import math
import random

import pygame

from . import surf as S
from .config import HEIGHT, HORIZON, WIDTH
from .util import clamp, lighten, mix, scale


class Theme:
    def __init__(self, name, sky, sun, grid, floor, mountain, ridge, frame, accent, nebula):
        self.name = name
        self.sky = sky            # arrêts du dégradé du ciel
        self.sun = sun            # (haut, milieu, bas)
        self.grid = grid
        self.floor = floor        # (horizon, bas)
        self.mountain = mountain  # (sombre, clair)
        self.ridge = ridge
        self.frame = frame        # cadre de l'aire de jeu
        self.accent = accent
        self.nebula = nebula      # couleurs des nébuleuses


THEMES = [
    Theme("COUCHANT",
          [(0.0, (5, 0, 22)), (0.5, (48, 4, 84)), (0.85, (150, 20, 120)), (1.0, (255, 70, 140))],
          ((255, 240, 110), (255, 120, 70), (255, 20, 150)),
          (255, 50, 210), ((70, 0, 70), (6, 0, 18)), ((20, 0, 40), (70, 10, 100)),
          (255, 90, 230), (0, 235, 255), (255, 60, 200), [(120, 0, 160), (0, 60, 160)]),
    Theme("CYBER",
          [(0.0, (0, 2, 18)), (0.5, (0, 25, 70)), (0.85, (0, 90, 150)), (1.0, (40, 220, 255))],
          ((200, 255, 255), (0, 200, 255), (90, 60, 255)),
          (0, 220, 255), ((0, 40, 80), (0, 4, 16)), ((0, 10, 30), (10, 50, 110)),
          (0, 240, 255), (255, 50, 200), (0, 230, 255), [(0, 80, 160), (80, 0, 160)]),
    Theme("TOXIQUE",
          [(0.0, (0, 10, 6)), (0.5, (5, 40, 25)), (0.85, (20, 110, 50)), (1.0, (170, 255, 60))],
          ((250, 255, 150), (150, 255, 60), (0, 190, 120)),
          (80, 255, 90), ((10, 60, 20), (0, 10, 4)), ((0, 25, 10), (20, 80, 40)),
          (120, 255, 100), (255, 230, 0), (100, 255, 90), [(0, 120, 60), (60, 120, 0)]),
    Theme("PASSION",
          [(0.0, (14, 0, 12)), (0.5, (70, 0, 40)), (0.85, (180, 10, 70)), (1.0, (255, 90, 120))],
          ((255, 220, 200), (255, 80, 120), (200, 0, 90)),
          (255, 60, 120), ((80, 0, 40), (12, 0, 8)), ((35, 0, 20), (110, 10, 60)),
          (255, 110, 170), (255, 210, 60), (255, 80, 150), [(160, 0, 70), (120, 0, 140)]),
    Theme("INFERNO",
          [(0.0, (12, 0, 0)), (0.5, (60, 5, 0)), (0.85, (170, 40, 0)), (1.0, (255, 150, 30))],
          ((255, 250, 180), (255, 150, 0), (230, 20, 0)),
          (255, 110, 20), ((90, 20, 0), (14, 2, 0)), ((30, 5, 0), (100, 25, 5)),
          (255, 140, 40), (255, 60, 90), (255, 130, 30), [(150, 30, 0), (130, 0, 40)]),
    Theme("GLACIER",
          [(0.0, (0, 4, 16)), (0.5, (10, 40, 80)), (0.85, (60, 140, 190)), (1.0, (210, 250, 255))],
          ((255, 255, 255), (170, 240, 255), (80, 150, 255)),
          (150, 230, 255), ((20, 60, 100), (2, 6, 20)), ((5, 20, 45), (40, 90, 140)),
          (200, 250, 255), (120, 160, 255), (170, 240, 255), [(40, 100, 160), (80, 60, 160)]),
    Theme("VAPEUR",
          [(0.0, (20, 10, 40)), (0.5, (90, 50, 130)), (0.85, (230, 120, 190)), (1.0, (255, 200, 210))],
          ((255, 250, 170), (255, 150, 200), (130, 200, 255)),
          (255, 120, 230), ((70, 40, 110), (15, 8, 30)), ((40, 20, 70), (120, 70, 150)),
          (120, 255, 240), (120, 255, 240), (255, 140, 230), [(160, 60, 160), (40, 120, 160)]),
    Theme("PRISME",
          [(0.0, (6, 0, 20)), (0.5, (40, 0, 90)), (0.85, (110, 30, 200)), (1.0, (200, 120, 255))],
          ((255, 255, 255), (220, 140, 255), (120, 60, 255)),
          (190, 110, 255), ((50, 0, 90), (6, 0, 18)), ((25, 0, 50), (80, 30, 140)),
          (220, 150, 255), (255, 255, 120), (200, 120, 255), [(120, 0, 200), (0, 120, 200)]),
    Theme("MINUIT",
          [(0.0, (0, 0, 10)), (0.5, (8, 8, 50)), (0.85, (40, 20, 120)), (1.0, (255, 60, 180))],
          ((255, 200, 255), (200, 80, 255), (60, 40, 200)),
          (120, 80, 255), ((30, 10, 80), (2, 0, 12)), ((8, 4, 30), (40, 20, 90)),
          (160, 120, 255), (255, 60, 180), (140, 100, 255), [(40, 0, 120), (120, 0, 100)]),
    Theme("SUPERNOVA",
          [(0.0, (8, 0, 16)), (0.5, (60, 10, 60)), (0.85, (200, 90, 40)), (1.0, (255, 230, 140))],
          ((255, 255, 230), (255, 210, 90), (255, 90, 60)),
          (255, 200, 80), ((90, 40, 20), (10, 2, 10)), ((30, 5, 30), (110, 50, 60)),
          (255, 220, 120), (255, 80, 255), (255, 210, 90), [(160, 60, 0), (120, 0, 140)]),
]


def _ridge(rng, x0, x1, base_y, height, rough, n=7):
    """Ligne de crête par déplacement du point milieu."""
    pts = [(x0, base_y), (x1, base_y)]
    amp = height
    for _ in range(n):
        new = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            mx = (ax + bx) / 2
            my = (ay + by) / 2 - rng.uniform(-0.35, 1.0) * amp
            new += [(mx, min(base_y, my)), (bx, by)]
        pts = new
        amp *= rough
    return pts


class Background:
    def __init__(self, size=(WIDTH, HEIGHT)):
        self.w, self.h = size
        self.sun_c = (WIDTH // 2, HORIZON - 64)
        self.sun_r = 170
        self._cache = {}
        self.theme_index = -1
        self.theme = THEMES[0]
        rng = random.Random(99)
        self.stars = []
        while len(self.stars) < 70:
            x, y = rng.uniform(0, self.w), rng.uniform(4, HORIZON - 140)
            if math.hypot(x - self.sun_c[0], y - self.sun_c[1]) < self.sun_r + 30:
                continue
            self.stars.append([x, y, rng.uniform(0, 6.28), rng.uniform(1.0, 4.0),
                               rng.uniform(0.4, 1.0), rng.random() < 0.18])
        self.shooting = []
        self.next_shoot = 2.0
        self.rng = random.Random()
        self.set_theme(0)

    # ------------------------------------------------------------------ construction
    def set_theme(self, index):
        index %= len(THEMES)
        if index == self.theme_index:
            return
        self.theme_index = index
        self.theme = THEMES[index]
        if index not in self._cache:
            self._cache[index] = self._build(self.theme, index)
        (self.full, self.nosun, self.floor, self.haze, self.horizon_glow,
         self.star_sprite) = self._cache[index]

    def _build(self, th, seed):
        w = self.w
        rng = random.Random(1000 + seed)
        sky = S.vgradient(w, HORIZON, th.sky).convert()
        # nébuleuses
        for i in range(6):
            col = scale(th.nebula[i % len(th.nebula)], 0.35)
            r = rng.randint(140, 260)
            blob = S.radial_glow(r, col, power=1.8)
            sky.blit(blob, (rng.randint(-100, w - 100) - r // 2, rng.randint(-120, HORIZON - 260)),
                     special_flags=pygame.BLEND_RGB_ADD)
        # étoiles fixes
        for _ in range(260):
            x, y = rng.randrange(w), rng.randrange(0, HORIZON - 90)
            b = rng.randint(50, 170)
            sky.fill((b, b, min(255, b + 30)), (x, y, 1, 1), special_flags=pygame.BLEND_RGB_ADD)
        # halo du soleil
        cx, cy = self.sun_c
        halo = S.radial_glow(460, scale(th.sun[1], 0.55), power=2.0)
        sky.blit(halo, (cx - 460, cy - 460), special_flags=pygame.BLEND_RGB_ADD)
        halo2 = S.radial_glow(260, scale(th.sun[0], 0.35), power=1.6)
        sky.blit(halo2, (cx - 260, cy - 260), special_flags=pygame.BLEND_RGB_ADD)

        far = self._mountains(th, rng, 0, w, HORIZON, 120, far=True)
        near_l = self._mountains(th, rng, -40, 470, HORIZON, 95, far=False)
        near_r = self._mountains(th, rng, 810, w + 40, HORIZON, 95, far=False)

        sun = self._sun_disc(th)
        full = sky.copy()
        nosun = sky.copy()
        for target in (full, nosun):
            target.blit(far[0], (0, 0))
            target.blit(far[1], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        full.blit(sun, (cx - self.sun_r, cy - self.sun_r))
        for target in (full, nosun):
            for layer, glow in (near_l, near_r):
                target.blit(layer, (0, 0))
                target.blit(glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        floor = S.vgradient(w, self.h - HORIZON, [(0.0, th.floor[0]), (0.35, mix(th.floor[0], th.floor[1], 0.6)),
                                                  (1.0, th.floor[1])]).convert()
        haze = pygame.Surface((w, 70), pygame.SRCALPHA, 32)
        hc = th.sky[-1][1]
        for y in range(70):
            a = int(235 * (1 - y / 70) ** 1.7)
            pygame.draw.line(haze, (*mix(hc, th.floor[0], 0.35), a), (0, y), (w, y))
        haze = haze.convert_alpha()
        hg = pygame.Surface((w, 24), 0, 32)
        for y in range(24):
            k = (1 - abs(y - 12) / 12) ** 2.5
            pygame.draw.line(hg, scale(lighten(th.grid, 0.4), k), (0, y), (w, y))
        hg = hg.convert()
        star = S.sparkle(9, lighten(th.accent, 0.6)).convert()
        return full, nosun, floor, haze, hg, star

    def _mountains(self, th, rng, x0, x1, base_y, height, far):
        """Retourne (couche alpha, lueur additive) pour une chaîne de montagnes filaires."""
        w = self.w
        glow = pygame.Surface((w, base_y), 0, 32)
        pts = _ridge(rng, x0, x1, base_y, height * (0.55 if far else 1.0), 0.55)
        if far:
            pts = [(x, base_y - (base_y - y) * 0.9 - 6) for x, y in pts]
        dark, light = th.mountain
        body_col = mix(dark, light, 0.55 if far else 0.0)
        poly = [(x0, base_y)] + pts + [(x1, base_y)]
        top = clamp((base_y - height * 1.3) / base_y, 0.01, 0.98)
        layer = S.vgradient(w, base_y, [(0.0, lighten(body_col, 0.3)), (top, lighten(body_col, 0.3)),
                                        (1.0, scale(body_col, 0.55))], alpha=True)
        mask = pygame.Surface((w, base_y), pygame.SRCALPHA, 32)
        pygame.draw.polygon(mask, (255, 255, 255, 255), poly)
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        ridge_col = scale(th.ridge, 0.45 if far else 1.0)
        wire_col = scale(th.ridge, 0.16 if far else 0.32)
        # fil de fer : lignes de pente
        step = max(1, len(pts) // (26 if far else 18))
        cx = (x0 + x1) / 2
        for i in range(0, len(pts), step):
            x, y = pts[i]
            if base_y - y < 6:
                continue
            bx = x + (x - cx) * 0.18
            pygame.draw.aaline(layer, (*wire_col, 255), (x, y), (bx, base_y))
        for k in (0.35, 0.65):
            row = [(x, y + (base_y - y) * k) for x, y in pts]
            pygame.draw.aalines(layer, (*wire_col, 255), False, row)
        pygame.draw.lines(layer, (*ridge_col, 255), False, pts, 2)
        pygame.draw.lines(glow, scale(ridge_col, 0.9), False, pts, 5)
        glow = S.blur(glow, 8)
        return layer.convert_alpha(), glow.convert()

    def _sun_disc(self, th):
        r = self.sun_r
        grad = S.vgradient(r * 2, r * 2, [(0.0, th.sun[0]), (0.45, th.sun[1]), (1.0, th.sun[2])],
                           alpha=True)
        mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA, 32)
        pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
        grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return grad.convert_alpha()

    # ------------------------------------------------------------------ animation
    def update(self, dt):
        self.next_shoot -= dt
        if self.next_shoot <= 0:
            self.next_shoot = self.rng.uniform(2.5, 7.0)
            d = self.rng.choice((-1, 1))
            self.shooting.append([self.rng.uniform(150, self.w - 150), self.rng.uniform(20, 180),
                                  d * self.rng.uniform(520, 760), self.rng.uniform(180, 300), 0.0,
                                  self.rng.uniform(0.5, 0.9)])
        for s in self.shooting:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] += dt
        self.shooting = [s for s in self.shooting if s[4] < s[5]]

    def draw(self, canvas, glow, t, pulse=0.0, speed=0.55, grid_boost=0.0):
        th = self.theme
        canvas.blit(self.full, (0, 0))
        self._draw_sun_stripes(canvas, t)
        # étoiles scintillantes
        for x, y, ph, sp, b, big in self.stars:
            k = b * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(t * sp + ph)))
            v = int(255 * k)
            if big:
                spr = self.star_sprite
                if k > 0.6:
                    canvas.blit(spr, (x - 9, y - 9), special_flags=pygame.BLEND_RGB_ADD)
                canvas.fill((v, v, v), (x, y, 2, 2))
            else:
                canvas.fill((v, v, min(255, v + 20)), (x, y, 1, 1))
        for sx, sy, vx, vy, age, life in self.shooting:
            k = math.sin(math.pi * age / life)
            head = (sx, sy)
            for i in range(4):
                a = (i + 1) * 0.035
                b = i * 0.035
                col = scale((255, 240, 255), k * (1 - i / 4))
                pygame.draw.line(canvas, col, (sx - vx * b, sy - vy * b), (sx - vx * a, sy - vy * a),
                                 2 if i == 0 else 1)
            glow.blob(head[0], head[1], 14, scale(th.accent, 0.7 * k))

        # soleil dans le tampon de lumière (pulsation au rythme)
        glow.blob(self.sun_c[0], self.sun_c[1] - 40, 150 + 30 * pulse, scale(th.sun[1], 0.28 + 0.25 * pulse))
        self._draw_floor(canvas, glow, t, pulse, speed, grid_boost)

    def _draw_sun_stripes(self, canvas, t):
        cx, cy = self.sun_c
        r = self.sun_r
        y0 = cy - r * 0.05
        y1 = HORIZON
        spacing = 17.0
        phase = (t * 10.0) % spacing
        y = y0 + phase - spacing
        while y < y1:
            if y >= y0:
                k = (y - y0) / (cy + r - y0)
                th = 1.0 + 9.0 * k
                dy = y - cy
                if abs(dy) < r:
                    half = math.sqrt(r * r - dy * dy)
                    rect = pygame.Rect(int(cx - half) - 1, int(y), int(half * 2) + 2, max(1, int(th)))
                    rect.h = min(rect.h, HORIZON - rect.y)
                    if rect.h > 0:
                        canvas.blit(self.nosun, rect.topleft, rect)
            y += spacing

    def _draw_floor(self, canvas, glow, t, pulse, speed, boost):
        th = self.theme
        w, h = self.w, self.h
        canvas.blit(self.floor, (0, HORIZON))
        k_base = clamp(0.62 + 0.3 * pulse + boost, 0, 1.6)
        col_hi = lighten(th.grid, 0.15)
        K = h - HORIZON
        cx = w / 2
        off = (t * speed) % 1.0
        # lignes horizontales (profondeur)
        for i in range(34):
            z = i + 1.0 - off
            if z < 0.95:
                continue
            y = HORIZON + K / z
            if y > h:
                continue
            f = clamp(1.25 - z / 16.0, 0.08, 1.0) * k_base
            col = scale(col_hi, f)
            pygame.draw.line(canvas, col, (0, y), (w, y), 2 if z < 3 else 1)
            if z < 12:
                glow.line((0, y), (w, y), scale(th.grid, 0.35 * f))
        # lignes fuyantes
        for k in range(-42, 43):
            xb = cx + k * 88
            xt = cx + k * 88 / 40.0
            col = scale(col_hi, 0.8 * k_base)
            pygame.draw.line(canvas, col, (xt, HORIZON + K / 40.0), (xb, h), 1)
            if abs(k) < 10:
                glow.line((cx + k * 88 / 8.0, HORIZON + K / 8.0), (xb, h), scale(th.grid, 0.22 * k_base))
        canvas.blit(self.haze, (0, HORIZON))
        canvas.blit(self.horizon_glow, (0, HORIZON - 12), special_flags=pygame.BLEND_RGB_ADD)
        glow.rect(0, HORIZON - 4, w, 8, scale(th.grid, 0.5 + 0.3 * pulse))
