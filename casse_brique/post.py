"""Post-traitement : bloom basse résolution, CRT, aberration chromatique, glitch, secousses."""

import math
import random

import numpy as np
import pygame

from .util import clamp


class GlowBuffer:
    """Tampon de lumière en basse résolution, flouté puis ajouté à l'image (bloom néon).

    Les objets lumineux y dessinent une version simplifiée d'eux-mêmes ; la
    composition finale est un simple flou multi-échelle + addition.
    """

    def __init__(self, size, scale=4):
        self.scale = scale
        self.inv = 1.0 / scale
        w, h = size
        self.size = size
        self.sw, self.sh = w // scale, h // scale
        self.surf = pygame.Surface((self.sw, self.sh)).convert()
        self.half = pygame.Surface((self.sw // 2, self.sh // 2)).convert()
        self.quarter = pygame.Surface((self.sw // 4, self.sh // 4)).convert()
        self.tmp = pygame.Surface((self.sw, self.sh)).convert()
        self.acc = pygame.Surface((self.sw, self.sh)).convert()
        self.full = pygame.Surface(size).convert()
        self.ox = 0.0
        self.oy = 0.0
        self._dots = {}

    def clear(self):
        self.surf.fill((0, 0, 0))

    def rect(self, x, y, w, h, color):
        s = self.inv
        x += self.ox
        y += self.oy
        r = (int(x * s), int(y * s), max(1, int(w * s + 0.999)), max(1, int(h * s + 0.999)))
        self.surf.fill(color, r, special_flags=pygame.BLEND_RGB_ADD)

    def dot(self, x, y, color, size=1):
        s = self.inv
        self.surf.fill(color, (int((x + self.ox) * s), int((y + self.oy) * s), size, size),
                       special_flags=pygame.BLEND_RGB_ADD)

    def line(self, p1, p2, color, width=1):
        s = self.inv
        pygame.draw.line(self.surf, color, ((p1[0] + self.ox) * s, (p1[1] + self.oy) * s),
                         ((p2[0] + self.ox) * s, (p2[1] + self.oy) * s), width)

    def blob(self, x, y, radius, color):
        """Tache lumineuse douce (radius en pixels plein écran)."""
        if color[0] < 3 and color[1] < 3 and color[2] < 3:
            return
        r = max(1, min(160, int(radius * self.inv)))
        spr = self._dots.get(r)
        if spr is None:
            from .surf import radial_glow
            spr = radial_glow(r, (255, 255, 255), power=1.6).convert()
            self._dots[r] = spr
        tinted = spr.copy()
        tinted.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        s = self.inv
        self.surf.blit(tinted, (int((x + self.ox) * s) - r, int((y + self.oy) * s) - r),
                       special_flags=pygame.BLEND_RGB_ADD)

    def blit(self, sprite, x, y):
        s = self.inv
        self.surf.blit(sprite, (int((x + self.ox) * s), int((y + self.oy) * s)),
                       special_flags=pygame.BLEND_RGB_ADD)

    def dim(self, rect, color):
        """Assombrit une zone du tampon (ex. : la vitre de l'aire de jeu)."""
        s = self.inv
        self.surf.fill(color, (int(rect[0] * s), int(rect[1] * s), int(rect[2] * s + 0.999),
                               int(rect[3] * s + 0.999)), special_flags=pygame.BLEND_RGB_MULT)

    def composite(self, target, strength=1.0):
        sw, sh = self.sw, self.sh
        pygame.transform.smoothscale(self.surf, (sw // 2, sh // 2), self.half)
        pygame.transform.smoothscale(self.half, (sw // 4, sh // 4), self.quarter)
        pygame.transform.smoothscale(self.half, (sw, sh), self.acc)
        pygame.transform.smoothscale(self.quarter, (sw, sh), self.tmp)
        self.acc.blit(self.tmp, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.surf.fill((110, 110, 110), special_flags=pygame.BLEND_RGB_MULT)
        self.acc.blit(self.surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        if strength < 0.99:
            v = int(255 * clamp(strength, 0, 1))
            self.acc.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        pygame.transform.smoothscale(self.acc, self.size, self.full)
        target.blit(self.full, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def make_crt_overlay(size, scan_strength=0.16, vignette=0.55):
    """Calque multiplicatif : lignes de balayage + vignettage."""
    w, h = size
    x = (np.arange(w) - w / 2) / (w / 2)
    y = (np.arange(h) - h / 2) / (h / 2)
    d = np.sqrt(x[:, None] ** 2 * 0.8 + y[None, :] ** 2)
    vig = 1.0 - vignette * np.clip(d - 0.55, 0, 1) ** 1.6
    scan = np.ones(h)
    scan[2::3] = 1.0 - scan_strength
    f = np.clip(vig * scan[None, :], 0, 1) * 255
    arr = np.repeat(f[:, :, None], 3, axis=2).astype(np.uint8)
    surf = pygame.Surface(size).convert()
    pygame.surfarray.blit_array(surf, arr)
    return surf


def make_vignette_only(size, vignette=0.45):
    return make_crt_overlay(size, scan_strength=0.0, vignette=vignette)


class Post:
    """Effets plein écran appliqués sur le canevas final."""

    def __init__(self, size):
        self.size = size
        self.tmp_r = pygame.Surface(size).convert()
        self.tmp_b = pygame.Surface(size).convert()
        self.crt = make_crt_overlay(size)
        self.vignette = make_vignette_only(size)
        self.rng = random.Random()

    def chromatic(self, canvas, amount):
        a = int(round(amount))
        if a < 1:
            return
        self.tmp_r.blit(canvas, (0, 0))
        self.tmp_r.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_MULT)
        self.tmp_b.blit(canvas, (0, 0))
        self.tmp_b.fill((0, 0, 255), special_flags=pygame.BLEND_RGB_MULT)
        canvas.fill((0, 255, 0), special_flags=pygame.BLEND_RGB_MULT)
        canvas.blit(self.tmp_r, (-a, 0), special_flags=pygame.BLEND_RGB_ADD)
        canvas.blit(self.tmp_b, (a, int(a * 0.4)), special_flags=pygame.BLEND_RGB_ADD)

    def glitch(self, canvas, amount):
        if amount <= 0.02:
            return
        w, h = self.size
        rng = self.rng
        for _ in range(int(2 + amount * 12)):
            sh = rng.randint(3, int(8 + 40 * amount))
            y = rng.randint(0, h - sh)
            dx = int(rng.uniform(-1, 1) * 60 * amount)
            if dx == 0:
                continue
            strip = canvas.subsurface((0, y, w, sh)).copy()
            if rng.random() < 0.4:
                strip.fill(rng.choice(((255, 60, 200), (0, 255, 255), (255, 255, 255))),
                           special_flags=pygame.BLEND_RGB_MULT)
            canvas.blit(strip, (dx, y))

    def flash(self, canvas, color, k):
        if k <= 0.01:
            return
        c = (int(color[0] * k), int(color[1] * k), int(color[2] * k))
        canvas.fill(c, special_flags=pygame.BLEND_RGB_ADD)

    def crt_pass(self, canvas, crt=True):
        canvas.blit(self.crt if crt else self.vignette, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


class ScreenFX:
    """État des effets de « juice » : secousses, flash, ralenti, arrêt sur image..."""

    def __init__(self):
        self.trauma = 0.0
        self.flash_color = (255, 255, 255)
        self.flash_k = 0.0
        self.chroma = 0.0
        self.glitch = 0.0
        self.hitstop = 0.0
        self.slowmo_scale = 1.0
        self.slowmo_timer = 0.0
        self.time = 0.0
        self.shake_enabled = True
        self.offset = (0.0, 0.0)

    def reset(self):
        self.trauma = self.flash_k = self.chroma = self.glitch = self.hitstop = 0.0
        self.slowmo_scale, self.slowmo_timer = 1.0, 0.0
        self.offset = (0.0, 0.0)

    def shake(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def flash(self, color, k):
        if k >= self.flash_k:
            self.flash_color = color
        self.flash_k = min(1.0, max(self.flash_k, k))

    def aberration(self, amount):
        self.chroma = max(self.chroma, amount)

    def add_glitch(self, amount):
        self.glitch = max(self.glitch, amount)

    def freeze(self, duration):
        self.hitstop = max(self.hitstop, duration)

    def slowmo(self, scale, duration):
        self.slowmo_scale = scale
        self.slowmo_timer = duration

    def update(self, dt):
        """dt réel ; retourne l'échelle de temps pour la simulation."""
        self.time += dt
        self.trauma = max(0.0, self.trauma - dt * 1.5)
        self.flash_k = max(0.0, self.flash_k - dt * 3.2)
        self.chroma = max(0.0, self.chroma - dt * 14.0)
        self.glitch = max(0.0, self.glitch - dt * 2.2)
        if self.trauma > 0 and self.shake_enabled:
            k = self.trauma * self.trauma * 16.0
            t = self.time
            self.offset = (k * (math.sin(t * 71.3) * 0.6 + math.sin(t * 29.1 + 1.3) * 0.4),
                           k * (math.sin(t * 63.7 + 2.1) * 0.6 + math.sin(t * 37.9) * 0.4))
        else:
            self.offset = (0.0, 0.0)
        if self.hitstop > 0:
            self.hitstop -= dt
            return 0.0
        if self.slowmo_timer > 0:
            self.slowmo_timer -= dt
            if self.slowmo_timer <= 0:
                self.slowmo_scale = 1.0
            return self.slowmo_scale
        return 1.0
