"""Post-traitement : bloom sur le calque émissif, vignette, flash, aberration chromatique,
distorsion raster (façon HDMA Super Nintendo)."""
import math

import numpy as np
import pygame

from .spritegen import arrays_to_surface


def make_vignette(w, h, strength=150, power=2.2, col=(6, 2, 16)):
    xx, yy = np.mgrid[0:w, 0:h].astype(np.float32)
    dx = (xx - w / 2) / (w / 2)
    dy = (yy - h / 2) / (h / 2)
    d = np.sqrt(dx * dx * 0.7 + dy * dy)
    a = np.clip(d - 0.55, 0, 1) ** power * strength / (0.45 ** power)
    rgb = np.zeros((w, h, 3), np.float32)
    rgb[:] = col
    return arrays_to_surface(rgb, np.clip(a, 0, strength))


class Post:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.vignette = make_vignette(w, h)
        self.tmp = pygame.Surface((w, h))
        self.red = pygame.Surface((w, h))
        self.cyan = pygame.Surface((w, h))
        self.q1 = (max(1, w // 4), max(1, h // 4))
        self.q2 = (max(1, w // 8), max(1, h // 8))
        self.bloom_gain = 1.0

    def bloom(self, frame, emissive, strength=1.0):
        small = pygame.transform.smoothscale(emissive, self.q1)
        tiny = pygame.transform.smoothscale(small, self.q2)
        k = int(max(0, min(255, 150 * strength * self.bloom_gain)))
        if k < 255:
            small.fill((k, k, k), special_flags=pygame.BLEND_MULT)
        k2 = int(max(0, min(255, 200 * strength * self.bloom_gain)))
        if k2 < 255:
            tiny.fill((k2, k2, k2), special_flags=pygame.BLEND_MULT)
        up = pygame.transform.smoothscale(small, (self.w, self.h))
        frame.blit(up, (0, 0), special_flags=pygame.BLEND_ADD)
        up2 = pygame.transform.smoothscale(tiny, (self.w, self.h))
        frame.blit(up2, (0, 0), special_flags=pygame.BLEND_ADD)

    def chroma(self, frame, amount):
        k = int(round(amount))
        if k <= 0:
            return
        self.red.blit(frame, (0, 0))
        self.red.fill((255, 0, 0), special_flags=pygame.BLEND_MULT)
        self.cyan.blit(frame, (0, 0))
        self.cyan.fill((0, 255, 255), special_flags=pygame.BLEND_MULT)
        frame.fill((0, 0, 0))
        frame.blit(self.red, (-k, 0), special_flags=pygame.BLEND_ADD)
        frame.blit(self.cyan, (k, 0), special_flags=pygame.BLEND_ADD)

    def flash(self, frame, col, alpha):
        if alpha <= 0.01:
            return
        a = int(min(1.0, alpha) * 255)
        c = (col[0] * a // 255, col[1] * a // 255, col[2] * a // 255)
        frame.fill(c, special_flags=pygame.BLEND_ADD)

    def raster_wave(self, surf, t, amp=2.0, freq=0.06, speed=0.08, y0=0, y1=None, rows=None):
        """Décale chaque ligne horizontalement (ondulation eau/chaleur)."""
        y1 = self.h if y1 is None else y1
        self.tmp.blit(surf, (0, 0))
        w = surf.get_width()
        for y in range(y0, y1):
            off = int(round(math.sin(y * freq + t * speed) * amp))
            if off:
                surf.blit(self.tmp, (off, y), (0, y, w, 1))
