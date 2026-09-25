"""Effets visuels : particules, explosions, ondes de choc, éclairs, popups, secousses."""
import math
import random

import numpy as np
import pygame

from . import palette as P
from .spritegen import rgb_surface, arrays_to_surface
from .util import gradient, TAU

# ---------------------------------------------------------------------------
# Caches de sprites lumineux
# ---------------------------------------------------------------------------
_glow_cache = {}
_smoke_cache = {}
_rot_cache = {}


def _q(c):
    return (int(c[0]) & 0xF8, int(c[1]) & 0xF8, int(c[2]) & 0xF8)


def glow(r, color, core=0.0):
    """Boule lumineuse additive (fond noir). core > 0 ajoute un noyau blanc."""
    r = max(1, int(r))
    color = _q(color)
    key = (r, color, core)
    s = _glow_cache.get(key)
    if s is None:
        size = r * 2 + 1
        xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / (r + 0.5)
        i = np.clip(1 - d, 0, 1) ** 1.7
        rgb = i[..., None] * np.array(color, np.float32)[None, None, :]
        if core:
            c = np.clip(1 - d * 2.4, 0, 1) ** 1.5 * 255 * core
            rgb += c[..., None]
        s = rgb_surface(rgb)
        if len(_glow_cache) > 3000:
            _glow_cache.clear()
        _glow_cache[key] = s
    return s


def smoke(r, alpha, tint=(40, 34, 48)):
    r = max(2, int(r))
    alpha = int(alpha) & 0xF0
    key = (r, alpha, tint)
    s = _smoke_cache.get(key)
    if s is None:
        size = r * 2 + 1
        xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
        d = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / (r + 0.5)
        a = np.clip(1 - d, 0, 1) ** 0.9 * alpha
        # léger relief : plus clair en haut à gauche
        shade = 1.0 + np.clip((r - xx) * 0.4 + (r - yy) * 0.6, -r, r) / (r * 3.0)
        rgb = np.array(tint, np.float32)[None, None, :] * shade[..., None]
        s = arrays_to_surface(rgb, a)
        if len(_smoke_cache) > 1500:
            _smoke_cache.clear()
        _smoke_cache[key] = s
    return s


def rotated(img, ang_deg, step=15):
    a = int(round(ang_deg / step)) * step % 360
    key = (id(img), a)
    s = _rot_cache.get(key)
    if s is None:
        s = pygame.transform.rotate(img, a)
        if len(_rot_cache) > 4000:
            _rot_cache.clear()
        _rot_cache[key] = s
    return s


# ---------------------------------------------------------------------------
# Particules
# ---------------------------------------------------------------------------
K_GLOW, K_FIRE, K_SPARK, K_SMOKE, K_DEBRIS, K_RING, K_TEXT, K_EMBER, K_STREAK, K_SPRITE, K_FLARE = range(11)


class Particle:
    __slots__ = ("k", "x", "y", "vx", "vy", "t", "life", "s0", "s1", "col", "grad", "drag", "g", "ang", "va",
                 "img", "trail", "add", "delay")

    def __init__(self, k, x, y, vx=0.0, vy=0.0, life=30, s0=4, s1=0, col=(255, 255, 255), grad=None,
                 drag=1.0, g=0.0, ang=0.0, va=0.0, img=None, trail=0, add=True, delay=0):
        self.k = k
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.t = 0
        self.life = max(1, life)
        self.s0 = s0
        self.s1 = s1
        self.col = col
        self.grad = grad
        self.drag = drag
        self.g = g
        self.ang = ang
        self.va = va
        self.img = img
        self.trail = trail
        self.add = add
        self.delay = delay


class FX:
    """Système de particules + recettes d'explosions."""
    MAX = 2600

    def __init__(self):
        self.parts = []
        self.scroll = 0.0   # vitesse de défilement du sol (pour les particules posées au sol)

    def clear(self):
        self.parts.clear()

    def add(self, p):
        if len(self.parts) < self.MAX:
            self.parts.append(p)
        return p

    # --- mise à jour -------------------------------------------------------
    def update(self):
        alive = []
        ap = alive.append
        rnd = random.random
        for p in self.parts:
            if p.delay > 0:
                p.delay -= 1
                ap(p)
                continue
            p.t += 1
            if p.t >= p.life:
                continue
            if p.drag != 1.0:
                p.vx *= p.drag
                p.vy *= p.drag
            p.vy += p.g
            p.x += p.vx
            p.y += p.vy
            if p.va:
                p.ang += p.va
            if p.trail and p.k == K_DEBRIS and p.t % 2 == 0 and p.t < p.life * 0.7:
                # traînée de feu des débris
                if len(self.parts) < self.MAX:
                    self.parts.append(Particle(K_FIRE, p.x, p.y, rnd() - 0.5, rnd() - 0.5, 10 + int(rnd() * 8),
                                               p.trail, 0.5, grad=P.FIRE))
            ap(p)
        self.parts = alive

    # --- rendu --------------------------------------------------------------
    def draw_add(self, surf):
        """Particules additives -> calque émissif."""
        blits = []
        badd = pygame.BLEND_ADD
        line = pygame.draw.line
        circ = pygame.draw.circle
        for p in self.parts:
            if p.delay > 0:
                continue
            k = p.k
            f = p.t / p.life
            if k == K_FIRE:
                r = p.s0 + (p.s1 - p.s0) * (1 - (1 - f) ** 2)
                c = gradient(p.grad or P.FIRE, f)
                if c[0] + c[1] + c[2] > 12:
                    g = glow(r, c, 0.0)
                    blits.append((g, (p.x - g.get_width() // 2, p.y - g.get_height() // 2), None, badd))
            elif k == K_GLOW or k == K_FLARE:
                r = p.s0 + (p.s1 - p.s0) * f
                fade = (1 - f) ** 1.3
                c = p.col
                g = glow(r, (c[0] * fade, c[1] * fade, c[2] * fade), 0.8 * fade if k == K_FLARE else 0.0)
                blits.append((g, (p.x - g.get_width() // 2, p.y - g.get_height() // 2), None, badd))
            elif k == K_SPARK:
                fade = 1 - f
                c = p.col
                cc = (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade))
                ln = p.s0
                line(surf, cc, (p.x, p.y), (p.x - p.vx * ln, p.y - p.vy * ln), 1)
            elif k == K_EMBER:
                fl = 0.6 + 0.4 * math.sin(p.t * 0.9 + p.ang)
                fade = (1 - f) * fl
                c = p.col
                surf.fill((int(c[0] * fade), int(c[1] * fade), int(c[2] * fade)),
                          (int(p.x), int(p.y), p.s0, p.s0), special_flags=badd)
            elif k == K_RING:
                ff = 1 - (1 - f) ** 3
                r = p.s0 + (p.s1 - p.s0) * ff
                fade = (1 - f) ** 1.5
                c = p.col
                wdt = max(1, int((p.ang or 3) * (1 - f) + 0.5))
                if r > wdt:
                    circ(surf, (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade)), (int(p.x), int(p.y)),
                         int(r), wdt)
            elif k == K_STREAK:
                fade = 1 - f
                c = p.col
                cc = (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade))
                line(surf, cc, (p.x, p.y), (p.x - p.vx * p.s0, p.y - p.vy * p.s0), max(1, int(p.s1)))
            elif k == K_SPRITE and p.add:
                if p.img is not None:
                    im = p.img
                    blits.append((im, (p.x - im.get_width() // 2, p.y - im.get_height() // 2), None, badd))
        if blits:
            surf.blits(blits, doreturn=False)

    def draw_normal(self, surf):
        """Particules opaques/alpha (fumée, débris, textes) -> image principale."""
        blits = []
        for p in self.parts:
            if p.delay > 0:
                continue
            k = p.k
            if k == K_SMOKE:
                f = p.t / p.life
                r = p.s0 + (p.s1 - p.s0) * (1 - (1 - f) ** 2)
                a = 150 * (1 - f) ** 1.2 * (min(1.0, p.t / 4.0))
                if a >= 16:
                    s = smoke(r, a, p.col)
                    blits.append((s, (p.x - s.get_width() // 2, p.y - s.get_height() // 2)))
            elif k == K_DEBRIS:
                im = rotated(p.img, p.ang)
                blits.append((im, (p.x - im.get_width() // 2, p.y - im.get_height() // 2)))
            elif k == K_TEXT:
                f = p.t / p.life
                if f > 0.72 and (p.t // 2) % 2 == 0:
                    continue
                im = p.img
                blits.append((im, (int(p.x - im.get_width() // 2), int(p.y - im.get_height() // 2))))
            elif k == K_SPRITE and not p.add:
                im = p.img
                blits.append((im, (p.x - im.get_width() // 2, p.y - im.get_height() // 2)))
        if blits:
            surf.blits(blits, doreturn=False)

    # --- recettes ---------------------------------------------------------------
    def spark_burst(self, x, y, n=6, col=(255, 230, 160), speed=3.0, life=14, spread=TAU, angle=0.0, ln=1.6):
        rnd = random.random
        for _ in range(n):
            a = angle + (rnd() - 0.5) * spread
            s = speed * (0.4 + rnd() * 0.8)
            self.add(Particle(K_SPARK, x, y, math.cos(a) * s, math.sin(a) * s, life + int(rnd() * life * 0.5),
                              ln, 0, col, drag=0.9))

    def hit(self, x, y, col=(255, 240, 200), n=3):
        rnd = random.random
        self.add(Particle(K_GLOW, x, y, 0, 0, 5, 5, 2, col))
        for _ in range(n):
            a = -math.pi / 2 + (rnd() - 0.5) * 2.4
            s = 1.5 + rnd() * 2.5
            self.add(Particle(K_SPARK, x, y, math.cos(a) * s, math.sin(a) * s, 6 + int(rnd() * 6), 1.5, 0, col,
                              drag=0.85))

    def ring(self, x, y, r0, r1, life, col=(255, 220, 160), width=3, delay=0):
        self.add(Particle(K_RING, x, y, 0, 0, life, r0, r1, col, ang=width, delay=delay))

    def flash(self, x, y, r, col=(255, 255, 255), life=8):
        self.add(Particle(K_FLARE, x, y, 0, 0, life, r, r * 0.6, col))

    def explosion(self, x, y, size=1.0, grad=None, debris=None, smoke_on=True, ring_col=None, sparks=True,
                  vx=0.0, vy=0.0, delay=0):
        """Explosion multi-couches. size ~ 0.5 (petite) .. 3 (énorme)."""
        rnd = random.random
        grad = grad or P.FIRE
        d0 = delay
        # flash central
        self.add(Particle(K_FLARE, x, y, vx * 0.5, vy * 0.5, int(6 + 4 * size), 10 * size, 4 * size,
                          gradient(grad, 0.1), delay=d0))
        # boules de feu
        n = int(5 + 7 * size)
        for i in range(n):
            a = rnd() * TAU
            dist = rnd() * 7 * size
            s = (0.3 + rnd() * 1.1) * (0.6 + size * 0.5)
            self.add(Particle(K_FIRE, x + math.cos(a) * dist * 0.4, y + math.sin(a) * dist * 0.4,
                              math.cos(a) * s + vx * 0.4, math.sin(a) * s + vy * 0.4,
                              int((14 + rnd() * 16) * (0.7 + size * 0.3)), (3 + rnd() * 4) * (0.7 + size * 0.4),
                              (6 + rnd() * 6) * (0.5 + size * 0.5), grad=grad, drag=0.9,
                              delay=d0 + int(rnd() * 5 * size)))
        # fumée
        if smoke_on:
            for i in range(int(2 + 4 * size)):
                a = rnd() * TAU
                s = rnd() * 0.8 * size
                self.add(Particle(K_SMOKE, x, y, math.cos(a) * s + vx * 0.3, math.sin(a) * s - 0.2 + vy * 0.3,
                                  int(30 + rnd() * 30 * size), 3 * size, (7 + rnd() * 6) * size, (38, 30, 46),
                                  drag=0.95, delay=d0 + 6 + int(rnd() * 6)))
        # étincelles
        if sparks:
            for i in range(int(6 + 10 * size)):
                a = rnd() * TAU
                s = (2 + rnd() * 4) * (0.7 + size * 0.35)
                self.add(Particle(K_SPARK, x, y, math.cos(a) * s, math.sin(a) * s, int(10 + rnd() * 18),
                                  1.8, 0, gradient(grad, 0.15 + rnd() * 0.2), drag=0.9, g=0.04, delay=d0))
        # onde de choc
        rc = ring_col or gradient(grad, 0.25)
        self.add(Particle(K_RING, x, y, 0, 0, int(14 + 8 * size), 2 * size, 22 * size, rc, ang=2 + size,
                          delay=d0))
        if size >= 1.5:
            self.add(Particle(K_RING, x, y, 0, 0, int(26 + 10 * size), 4 * size, 44 * size,
                              (rc[0] // 2, rc[1] // 2, rc[2] // 2), ang=2, delay=d0 + 3))
        # débris
        if debris:
            for img in debris:
                a = rnd() * TAU
                s = 1 + rnd() * 2.5 * (0.6 + size * 0.4)
                self.add(Particle(K_DEBRIS, x + (rnd() - 0.5) * 6, y + (rnd() - 0.5) * 6,
                                  math.cos(a) * s + vx * 0.5, math.sin(a) * s + vy * 0.5,
                                  int(28 + rnd() * 30), 0, 0, img=img, drag=0.97, g=0.03,
                                  ang=rnd() * 360, va=(rnd() - 0.5) * 24, trail=2.5, delay=d0))

    def embers(self, x, y, n=8, col=(255, 170, 60), spread=10, vy=-0.8):
        rnd = random.random
        for _ in range(n):
            self.add(Particle(K_EMBER, x + (rnd() - 0.5) * spread, y + (rnd() - 0.5) * spread,
                              (rnd() - 0.5) * 0.8, vy * (0.5 + rnd()), int(30 + rnd() * 40), 1, 0, col,
                              ang=rnd() * 6, drag=0.99))

    def text(self, x, y, img, life=40, vy=-0.6):
        self.add(Particle(K_TEXT, x, y, 0, vy, life, 0, 0, img=img, drag=0.96))

    def debris_from(self, img, n=6):
        """Découpe un sprite en morceaux pour les éclats."""
        w, h = img.get_size()
        pieces = []
        rnd = random.random
        for _ in range(n):
            pw = max(2, int(w * (0.18 + rnd() * 0.2)))
            ph = max(2, int(h * (0.18 + rnd() * 0.2)))
            px = int(rnd() * max(1, w - pw))
            py = int(rnd() * max(1, h - ph))
            piece = img.subsurface((px, py, pw, ph)).copy()
            pieces.append(piece)
        return pieces


# ---------------------------------------------------------------------------
# Éclairs procéduraux
# ---------------------------------------------------------------------------
def bolt_points(x0, y0, x1, y1, jag=6.0, segs=None, rnd=random.random):
    d = math.hypot(x1 - x0, y1 - y0)
    segs = segs or max(3, int(d / 9))
    nx, ny = (-(y1 - y0) / (d or 1), (x1 - x0) / (d or 1))
    pts = [(x0, y0)]
    for i in range(1, segs):
        t = i / segs
        off = (rnd() - 0.5) * 2 * jag * math.sin(t * math.pi) ** 0.5
        pts.append((x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off))
    pts.append((x1, y1))
    return pts


def draw_bolt(surf, pts, col=(120, 180, 255), core=(255, 255, 255), width=3):
    """Éclair sur un calque additif : halo coloré + cœur blanc."""
    if len(pts) < 2:
        return
    dim = (col[0] // 3, col[1] // 3, col[2] // 3)
    pygame.draw.lines(surf, dim, False, pts, width + 2)
    pygame.draw.lines(surf, col, False, pts, width)
    pygame.draw.lines(surf, core, False, pts, 1)


def draw_bolt_tree(surf, x0, y0, x1, y1, col, jag=7, width=2, branches=2, depth=0):
    pts = bolt_points(x0, y0, x1, y1, jag)
    draw_bolt(surf, pts, col, width=width)
    if depth < 2:
        for _ in range(branches):
            i = random.randrange(1, len(pts))
            bx, by = pts[i]
            a = math.atan2(y1 - y0, x1 - x0) + (random.random() - 0.5) * 1.6
            ln = math.hypot(x1 - x0, y1 - y0) * (0.2 + random.random() * 0.3)
            draw_bolt_tree(surf, bx, by, bx + math.cos(a) * ln, by + math.sin(a) * ln, col, jag * 0.6,
                           max(1, width - 1), 1, depth + 1)


# ---------------------------------------------------------------------------
# « Jus » : secousses, flashs, hitstop, ralenti, aberration chromatique
# ---------------------------------------------------------------------------
class Juice:
    def __init__(self):
        self.trauma = 0.0
        self.ox = 0
        self.oy = 0
        self.flash_col = (255, 255, 255)
        self.flash_a = 0.0
        self.flash_decay = 0.1
        self.hitstop = 0
        self.slowmo = 0
        self.chroma = 0.0
        self.enabled = True

    def shake(self, amount):
        self.trauma = min(1.0, self.trauma + amount)

    def flash(self, col=(255, 255, 255), alpha=0.8, decay=0.08):
        if alpha >= self.flash_a:
            self.flash_col = col
            self.flash_a = alpha
            self.flash_decay = decay

    def aberr(self, amount):
        self.chroma = max(self.chroma, amount)

    def update(self):
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - 0.022)
        amt = self.trauma * self.trauma * 7.0 if self.enabled else 0.0
        self.ox = int(round((random.random() * 2 - 1) * amt))
        self.oy = int(round((random.random() * 2 - 1) * amt))
        if self.flash_a > 0:
            self.flash_a = max(0.0, self.flash_a - self.flash_decay)
        if self.chroma > 0:
            self.chroma = max(0.0, self.chroma - 0.12)
