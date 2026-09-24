"""Système de particules : étincelles, éclats, ondes de choc, feux d'artifice, textes flottants..."""

import math
import random

import pygame

from .util import clamp, ease_out_back, ease_out_cubic, hsv, lighten, mix, scale

TAU = math.tau


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "width", "grav", "drag", "stretch")

    def __init__(self, x, y, vx, vy, life, color, width=2, grav=500.0, drag=1.8, stretch=0.035):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.width, self.grav, self.drag, self.stretch = color, width, grav, drag, stretch


class Shard:
    __slots__ = ("x", "y", "vx", "vy", "rot", "vr", "life", "max", "color", "hi", "shape")

    def __init__(self, x, y, vx, vy, life, color, shape, vr):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.rot, self.vr = random.uniform(0, TAU), vr
        self.life = self.max = life
        self.color, self.shape = color, shape
        self.hi = lighten(color, 0.6)


class Blob:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "color", "radius", "grow", "rise", "fire")

    def __init__(self, x, y, vx, vy, life, color, radius, grow=0.0, rise=0.0, fire=False):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max = life
        self.color, self.radius, self.grow, self.rise, self.fire = color, radius, grow, rise, fire


class Ring:
    __slots__ = ("x", "y", "life", "max", "color", "radius", "width")

    def __init__(self, x, y, life, color, radius, width):
        self.x, self.y, self.life, self.max = x, y, life, life
        self.color, self.radius, self.width = color, radius, width


class Text:
    __slots__ = ("x", "y", "vy", "life", "max", "nt", "delay")

    def __init__(self, x, y, vy, life, nt, delay=0.0):
        self.x, self.y, self.vy, self.life, self.max, self.nt, self.delay = x, y, vy, life, life, nt, delay


class Smoke:
    __slots__ = ("x", "y", "vx", "vy", "life", "max", "radius", "color")

    def __init__(self, x, y, vx, vy, life, radius, color):
        self.x, self.y, self.vx, self.vy, self.life, self.max = x, y, vx, vy, life, life
        self.radius, self.color = radius, color


class Confetti:
    __slots__ = ("x", "y", "vx", "vy", "rot", "vr", "flip", "vf", "life", "max", "color", "w", "h")

    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.rot, self.vr = random.uniform(0, TAU), random.uniform(-8, 8)
        self.flip, self.vf = random.uniform(0, TAU), random.uniform(6, 14)
        self.life = self.max = life
        self.color = color
        self.w, self.h = random.uniform(5, 9), random.uniform(3, 5)


class Rocket:
    __slots__ = ("x", "y", "vx", "vy", "life", "color")

    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y, self.vx, self.vy, self.life, self.color = x, y, vx, vy, life, color


class Glint:
    __slots__ = ("x", "y", "life", "max", "size")

    def __init__(self, x, y, life, size):
        self.x, self.y, self.life, self.max, self.size = x, y, life, life, size


class Particles:
    MAX_SPARKS = 1000

    def __init__(self, art, font):
        self.art = art
        self.font = font
        self.rng = random.Random()
        self.on_event = None   # rappel (nom, x, y) pour les sons des feux d'artifice
        self.clear()

    def clear(self):
        self.sparks, self.shards, self.blobs, self.rings = [], [], [], []
        self.texts, self.smokes, self.confetti, self.rockets, self.glints = [], [], [], [], []

    def count(self):
        return (len(self.sparks) + len(self.shards) + len(self.blobs) + len(self.rings)
                + len(self.texts) + len(self.smokes) + len(self.confetti) + len(self.rockets))

    # ------------------------------------------------------------------ émetteurs
    def sparks_burst(self, x, y, color, n, speed=(120, 420), angle=None, spread=TAU,
                     life=(0.25, 0.65), grav=500.0, width=2, drag=1.8, stretch=0.035):
        room = self.MAX_SPARKS - len(self.sparks)
        if room <= 0:
            return
        load = len(self.sparks) / self.MAX_SPARKS
        n = min(room, max(1, int(n * (1.0 - 0.75 * load))))
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, TAU) if angle is None else angle + r.uniform(-spread / 2, spread / 2)
            v = r.uniform(*speed)
            c = color if r.random() < 0.7 else lighten(color, 0.6)
            self.sparks.append(Spark(x, y, math.cos(a) * v, math.sin(a) * v, r.uniform(*life), c,
                                     width, grav, drag, stretch))

    def shards_burst(self, x, y, w, h, color, n=8, force=1.0, vx0=0.0, vy0=0.0):
        r = self.rng
        if len(self.shards) > 220:
            n = max(1, n // 3)
        for _ in range(n):
            px, py = x + r.uniform(-w / 2, w / 2), y + r.uniform(-h / 2, h / 2)
            a = math.atan2(py - y + r.uniform(-4, 4), px - x + r.uniform(-4, 4))
            v = r.uniform(80, 300) * force
            k = r.randint(3, 4)
            size = r.uniform(3, 8)
            shape = [(size * r.uniform(0.5, 1.0), i * TAU / k + r.uniform(-0.4, 0.4)) for i in range(k)]
            col = mix(color, (255, 255, 255), r.uniform(0.0, 0.35))
            self.shards.append(Shard(px, py, math.cos(a) * v + vx0, math.sin(a) * v - 120 * force + vy0,
                                     r.uniform(0.5, 1.0), col, shape, r.uniform(-12, 12)))

    def blob(self, x, y, color, radius, life=0.4, vx=0.0, vy=0.0, grow=0.0, rise=0.0, fire=False):
        if len(self.blobs) < 500:
            self.blobs.append(Blob(x, y, vx, vy, life, color, radius, grow, rise, fire))

    def ring(self, x, y, color, radius, life=0.45, width=4):
        self.rings.append(Ring(x, y, life, color, radius, width))

    def smoke(self, x, y, n=8, color=(40, 10, 60), spread=30, life=(0.8, 1.6)):
        r = self.rng
        for _ in range(n):
            a = r.uniform(0, TAU)
            v = r.uniform(10, 60)
            self.smokes.append(Smoke(x + r.uniform(-spread, spread), y + r.uniform(-spread, spread),
                                     math.cos(a) * v, math.sin(a) * v - 25, r.uniform(*life),
                                     r.uniform(14, 30), color))

    def text(self, x, y, s, size, color, life=0.9, vy=-60, delay=0.0, **kw):
        nt = self.font.render(s, size, color, **kw)
        self.texts.append(Text(x, y, vy, life, nt, delay))

    def confetti_burst(self, x, y, n=60, power=1.0):
        r = self.rng
        for _ in range(n):
            a = r.uniform(-math.pi, 0)
            v = r.uniform(150, 520) * power
            self.confetti.append(Confetti(x, y, math.cos(a) * v, math.sin(a) * v, r.uniform(1.6, 3.2),
                                          hsv(r.random(), 0.8, 1.0)))

    def rocket(self, x, y, target_y, color):
        vy = -math.sqrt(2 * 520 * max(40, y - target_y))
        self.rockets.append(Rocket(x, y, self.rng.uniform(-40, 40), vy, 0.0, color))

    def glint(self, x, y, size=8):
        if len(self.glints) < 40:
            self.glints.append(Glint(x, y, 0.45, size))

    # ------------------------------------------------------------------ effets composés
    def brick_break(self, x, y, w, h, color, power=1.0, vx=0.0, vy=0.0):
        self.shards_burst(x, y, w, h, color, n=int(7 * power) + 3, force=power, vx0=vx * 0.15, vy0=vy * 0.15)
        self.sparks_burst(x, y, lighten(color, 0.3), int(14 * power) + 4, speed=(120, 460 * power))
        self.blob(x, y, color, 60, life=0.3, grow=50)
        self.ring(x, y, lighten(color, 0.4), 46 * power, life=0.35, width=3)

    def explosion(self, x, y, radius=110, color=(255, 150, 40)):
        r = self.rng
        self.blob(x, y, (150, 130, 100), radius * 1.05, life=0.4, grow=70)
        self.blob(x, y, scale(color, 0.7), radius * 2.0, life=0.8, grow=60)
        self.ring(x, y, (255, 230, 160), radius * 1.6, life=0.5, width=8)
        self.ring(x, y, color, radius * 2.4, life=0.8, width=4)
        self.sparks_burst(x, y, (255, 200, 90), 55, speed=(200, 900), life=(0.3, 0.9), grav=300, width=3)
        self.sparks_burst(x, y, (255, 90, 30), 30, speed=(100, 500), life=(0.4, 1.1), grav=200)
        for _ in range(12):
            a = r.uniform(0, TAU)
            v = r.uniform(30, 180)
            self.blob(x + math.cos(a) * 10, y + math.sin(a) * 10, (255, 120, 20), r.uniform(26, 46),
                      life=r.uniform(0.5, 1.0), vx=math.cos(a) * v, vy=math.sin(a) * v, rise=-60, fire=True)
        self.smoke(x, y, n=10, spread=radius * 0.4)
        self.shards_burst(x, y, 60, 30, (255, 170, 60), n=10, force=1.8)

    def firework(self, x, y, color):
        self.sparks_burst(x, y, color, 70, speed=(60, 380), life=(0.8, 1.6), grav=160, drag=1.2, width=2)
        self.sparks_burst(x, y, (255, 255, 255), 20, speed=(40, 200), life=(0.4, 0.9), grav=120)
        self.blob(x, y, color, 120, life=0.6, grow=40)
        self.ring(x, y, lighten(color, 0.5), 90, life=0.6, width=3)

    # ------------------------------------------------------------------ simulation
    def update(self, dt):
        if dt <= 0:
            return
        keep = []
        for p in self.sparks:
            p.life -= dt
            if p.life > 0:
                d = math.exp(-p.drag * dt)
                p.vx *= d
                p.vy = p.vy * d + p.grav * dt
                p.x += p.vx * dt
                p.y += p.vy * dt
                keep.append(p)
        self.sparks = keep

        keep = []
        for p in self.shards:
            p.life -= dt
            if p.life > 0 and p.y < 780:
                p.vy += 950 * dt
                p.vx *= math.exp(-0.8 * dt)
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.rot += p.vr * dt
                keep.append(p)
        self.shards = keep

        keep = []
        for p in self.blobs:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.vx *= math.exp(-2.5 * dt)
                p.vy = p.vy * math.exp(-2.5 * dt) + p.rise * dt
                p.radius += p.grow * dt
                keep.append(p)
        self.blobs = keep

        self.rings = [p for p in self.rings if self._dec(p, dt)]

        keep = []
        for p in self.texts:
            if p.delay > 0:
                p.delay -= dt
                keep.append(p)
                continue
            p.life -= dt
            if p.life > 0:
                p.y += p.vy * dt
                p.vy *= math.exp(-2.0 * dt)
                keep.append(p)
        self.texts = keep

        keep = []
        for p in self.smokes:
            p.life -= dt
            if p.life > 0:
                p.x += p.vx * dt
                p.y += p.vy * dt
                p.radius += 18 * dt
                keep.append(p)
        self.smokes = keep

        keep = []
        for p in self.confetti:
            p.life -= dt
            if p.life > 0 and p.y < 760:
                p.vx *= math.exp(-1.6 * dt)
                p.vy = p.vy * math.exp(-1.6 * dt) + 420 * dt
                p.x += p.vx * dt + math.sin(p.flip * 0.5) * 20 * dt
                p.y += p.vy * dt
                p.rot += p.vr * dt
                p.flip += p.vf * dt
                keep.append(p)
        self.confetti = keep

        keep = []
        for p in self.rockets:
            p.life += dt
            p.vy += 520 * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if self.rng.random() < 0.8:
                self.sparks.append(Spark(p.x, p.y, self.rng.uniform(-30, 30), self.rng.uniform(20, 80),
                                         0.35, lighten(p.color, 0.4), 2, 200.0, 2.0))
            if p.vy >= -40:
                self.firework(p.x, p.y, p.color)
                if self.on_event:
                    self.on_event("firework", p.x, p.y)
            else:
                keep.append(p)
        self.rockets = keep

        self.glints = [p for p in self.glints if self._dec(p, dt)]

    @staticmethod
    def _dec(p, dt):
        p.life -= dt
        return p.life > 0

    # ------------------------------------------------------------------ rendu
    def draw(self, canvas, glow, ox=0.0, oy=0.0):
        art = self.art
        for p in self.smokes:
            k = p.life / p.max
            spr = art.disc(int(p.radius / 4) * 4 + 4, p.color, 200)
            spr.set_alpha(int(170 * k))
            canvas.blit(spr, (p.x - spr.get_width() / 2 + ox, p.y - spr.get_height() / 2 + oy))
            spr.set_alpha(255)

        for p in self.blobs:
            k = p.life / p.max
            if p.fire:
                col = _fire_color(1 - k)
                glow.blob(p.x, p.y, p.radius * (0.6 + 0.4 * k), scale(col, k * 0.5))
                if k > 0.35:
                    rr = int(p.radius * 0.22 * k) + 1
                    pygame.draw.circle(canvas, col, (p.x + ox, p.y + oy), rr)
            else:
                glow.blob(p.x, p.y, p.radius, scale(p.color, k * 0.6))

        for p in self.rings:
            k = p.life / p.max
            t = 1 - k
            rad = p.radius * ease_out_cubic(t) + 2
            wdt = max(1, int(p.width * k + 0.5))
            col = scale(p.color, 0.4 + 0.6 * k)
            pygame.draw.circle(canvas, col, (p.x + ox, p.y + oy), rad, wdt)
            glow.blob(p.x, p.y, rad * 0.4, scale(p.color, 0.12 * k))

        cos, sin = math.cos, math.sin
        poly, aal = pygame.draw.polygon, pygame.draw.aaline
        for p in self.shards:
            k = p.life / p.max
            px, py, rot = p.x + ox, p.y + oy, p.rot
            pts = [(px + cos(a + rot) * rr, py + sin(a + rot) * rr) for rr, a in p.shape]
            if k > 0.3:
                poly(canvas, p.color, pts)
                aal(canvas, p.hi, pts[0], pts[1])
            else:
                m = k / 0.3
                c = p.color
                poly(canvas, (int(c[0] * m), int(c[1] * m), int(c[2] * m)), pts)

        # boucle la plus chaude : tout est « déroulé » pour limiter les appels Python
        dl = pygame.draw.line
        gs, ginv, gox, goy = glow.surf, glow.inv, glow.ox, glow.oy
        add = pygame.BLEND_RGB_ADD
        for p in self.sparks:
            k = p.life / p.max
            r, g, b = p.color
            m = 0.25 + 0.75 * k
            s = p.stretch
            x, y = p.x + ox, p.y + oy
            dl(canvas, (int(r * m), int(g * m), int(b * m)), (x, y), (x - p.vx * s, y - p.vy * s),
               p.width if k > 0.4 else 1)
            h = 0.5 * k
            gs.fill((int(r * h), int(g * h), int(b * h)),
                    (int((p.x + gox) * ginv), int((p.y + goy) * ginv), 1, 1), special_flags=add)

        for p in self.confetti:
            k = min(1.0, p.life / 0.5)
            fw = p.w * abs(math.cos(p.flip))
            c, s = math.cos(p.rot), math.sin(p.rot)
            hw, hh = fw / 2, p.h / 2
            pts = [(p.x + ox + c * dx - s * dy, p.y + oy + s * dx + c * dy)
                   for dx, dy in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
            col = scale(p.color, (0.55 + 0.45 * abs(math.cos(p.flip))) * k)
            pygame.draw.polygon(canvas, col, pts)

        for p in self.rockets:
            pygame.draw.circle(canvas, (255, 255, 255), (p.x + ox, p.y + oy), 2)
            glow.blob(p.x, p.y, 18, scale(p.color, 0.8))

        for p in self.glints:
            k = math.sin(math.pi * p.life / p.max)
            r = max(3, int(p.size * k))
            spr = art.sparkle(r, (255, 255, 255))
            canvas.blit(spr, (p.x - r + ox, p.y - r + oy), special_flags=pygame.BLEND_RGB_ADD)

    def draw_texts(self, canvas, ox=0.0, oy=0.0):
        for p in self.texts:
            if p.delay > 0:
                continue
            k = p.life / p.max
            age = p.max - p.life
            pop = ease_out_back(min(1.0, age / 0.18))
            a = 255 if k > 0.35 else int(255 * k / 0.35)
            p.nt.draw(canvas, p.x + ox, p.y + oy + (1 - pop) * 14, "center", alpha=a,
                      glow=clamp(1.3 - age * 1.5, 0.35, 1.0))


def _fire_color(t):
    """Blanc → jaune → orange → rouge → braise."""
    stops = ((255, 250, 220), (255, 220, 80), (255, 130, 20), (220, 40, 10), (90, 10, 20))
    t = clamp(t, 0.0, 0.999) * (len(stops) - 1)
    i = int(t)
    return mix(stops[i], stops[i + 1], t - i)
