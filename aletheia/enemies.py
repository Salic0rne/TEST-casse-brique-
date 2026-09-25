"""Bestiaire : les automates des dieux corrompus."""
import math
import random

import pygame

from . import palette as P
from .entities import Enemy, wait, move_to, follow, drift, PF_W, PF_H
from .sprites import S, NTUR
from .spritegen import rot_index
from .fx import glow, Particle, K_GLOW, K_FIRE, K_SPARK, K_RING, K_FLARE, bolt_points, draw_bolt
from .util import TAU, ease_out_cubic, ease_in_cubic, ease_in_out, clamp, angle_diff


def seg_dist(px, py, x0, y0, x1, y1):
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy or 1e-6
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / L2))
    cx, cy = x0 + dx * t, y0 + dy * t
    return math.hypot(px - cx, py - cy)


# ---------------------------------------------------------------------------
# Dangers continus (rayons, arcs)
# ---------------------------------------------------------------------------
class Hazard:
    """Rayon ennemi : phase d'avertissement (trait clignotant) puis rayon actif."""

    def __init__(self, w, x0, y0, x1, y1, width=8, warn=40, life=40, col=(255, 80, 200), owner=None,
                 kind="beam", track=None):
        self.w = w
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.width = width
        self.warn = warn
        self.life = life
        self.col = col
        self.owner = owner
        self.kind = kind
        self.track = track     # fonction -> (x0, y0, x1, y1)
        self.t = 0
        self.alive = True
        if warn > 0:
            w.audio.play("charge", x0, 0.5, throttle=10)

    @property
    def active(self):
        return self.t >= self.warn

    def update(self):
        self.t += 1
        if self.owner is not None and (self.owner.dead or self.owner.gone):
            self.alive = False
            return
        if self.track is not None:
            self.x0, self.y0, self.x1, self.y1 = self.track()
        if self.t == self.warn:
            if self.kind == "bolt":
                self.w.audio.play("lightning", self.x1, 0.9)
                self.w.juice.flash((170, 190, 255), 0.25, 0.08)
                self.w.juice.shake(0.2)
            else:
                self.w.audio.play("beam", self.x0, 0.8, throttle=6)
                self.w.juice.shake(0.15)
        if self.t >= self.warn + self.life:
            self.alive = False

    def hits(self, px, py, r):
        if not self.active:
            return False
        k = 0.7 if self.t - self.warn < 4 else 1.0
        return seg_dist(px, py, self.x0, self.y0, self.x1, self.y1) < self.width * 0.5 * k + r

    def draw_add(self, add):
        c = self.col
        if not self.active:
            if (self.t // 3) % 2 == 0:
                k = 0.3 + 0.5 * self.t / max(1, self.warn)
                pygame.draw.line(add, (int(c[0] * k), int(c[1] * k), int(c[2] * k)), (self.x0, self.y0),
                                 (self.x1, self.y1), 1)
            return
        f = (self.t - self.warn) / max(1, self.life)
        fade = 1.0 if f < 0.75 else max(0.0, (1 - f) / 0.25)
        if self.kind == "bolt":
            pts = bolt_points(self.x0, self.y0, self.x1, self.y1, 10)
            draw_bolt(add, pts, (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade)), width=max(1, int(self.width * 0.5)))
            return
        wdt = self.width * (0.85 + 0.15 * math.sin(self.t * 1.3)) * (min(1.0, (self.t - self.warn + 1) / 4))
        pygame.draw.line(add, (int(c[0] * 0.35 * fade), int(c[1] * 0.35 * fade), int(c[2] * 0.35 * fade)),
                         (self.x0, self.y0), (self.x1, self.y1), max(1, int(wdt + 6)))
        pygame.draw.line(add, (int(c[0] * fade), int(c[1] * fade), int(c[2] * fade)), (self.x0, self.y0),
                         (self.x1, self.y1), max(1, int(wdt)))
        pygame.draw.line(add, (int(255 * fade), int(255 * fade), int(255 * fade)), (self.x0, self.y0),
                         (self.x1, self.y1), max(1, int(wdt * 0.35)))


# ---------------------------------------------------------------------------
# Ennemis orientables : sprite choisi selon la direction du mouvement
# ---------------------------------------------------------------------------
class Rotor(Enemy):
    ROT = None

    def update(self):
        px, py = self.x, self.y
        Enemy.update(self)
        dx, dy = self.x - px, self.y - py - (self.w.scroll if self.GROUND else 0)
        if dx * dx + dy * dy > 0.04:
            want = math.atan2(dy, dx)
            self.face += clamp(angle_diff(self.face, want), -0.25, 0.25)

    def sprite(self):
        if self.ROT:
            return S[self.ROT][rot_index(self.face, NTUR)]
        return Enemy.sprite(self)


# ---------------------------------------------------------------------------
# Petits ennemis
# ---------------------------------------------------------------------------
class Myrmex(Rotor):
    """Drone-fourmi : vole en escadrilles."""
    HP = 2
    SCORE = 100
    RADIUS = 7
    EXPLO = 0.55
    ROT = "myrmex_r"

    def setup(self, path=None, dur=120, vx=0.0, vy=1.7, sine=0.0, freq=0.05, fire=None, dive=None, speed=2.4,
              **kw):
        self.path = path
        self.dur = dur
        self.v = (vx, vy)
        self.sine = sine
        self.freq = freq
        self.fire_at = fire
        self.dive = dive
        self.speed = speed

    def behave(self):
        if self.path:
            yield from follow(self, self.path, self.dur)
            self.vx, self.vy = math.cos(self.face) * self.speed, math.sin(self.face) * self.speed
            while True:
                yield
        elif self.dive is not None:
            yield from move_to(self, self.x, self.dive, 40, ease_out_cubic)
            yield from wait(12)
            a = self.aim()
            self.vx, self.vy = math.cos(a) * self.speed, math.sin(a) * self.speed
            while True:
                yield
        else:
            bx = self.x
            ph = random.random() * TAU
            self.vy = self.v[1]
            while True:
                bx += self.v[0]
                if self.sine:
                    self.x = bx + math.sin(self.t * self.freq + ph) * self.sine
                else:
                    self.x = bx
                yield

    def update(self):
        Rotor.update(self)
        if self.fire_at is not None and self.t == self.fire_at and self.can_fire():
            self.w.bullets.aimed(self.x, self.y, 2.0, 1, 0, "s", "pink")
            self.w.audio.play("eshot", self.x, 0.6, throttle=3)


class Harpy(Rotor):
    """Harpie : fond en piqué, décoche une gerbe à mi-course."""
    HP = 5
    SCORE = 200
    RADIUS = 8
    EXPLO = 0.65
    ROT = "harpy_r"

    def setup(self, path=None, dur=150, shots=3, fire_t=None, col="pink", **kw):
        self.path = path or [(self.x, self.y), (self.x, 120), (PF_W - self.x, 260)]
        self.dur = dur
        self.shots = shots
        self.fire_t = fire_t if fire_t is not None else int(dur * 0.4)
        self.col = col

    def behave(self):
        yield from follow(self, self.path, self.dur)
        self.vx, self.vy = math.cos(self.face) * 2.5, math.sin(self.face) * 2.5
        while True:
            yield

    def update(self):
        Rotor.update(self)
        if self.t == self.fire_t and self.can_fire():
            n = self.w.bullets.dens(self.shots)
            self.w.bullets.aimed(self.x, self.y, 2.2, n, 0.5, "rice", self.col)
            self.w.audio.play("eshot2", self.x, 0.7)


class Stymphalian(Enemy):
    """Oiseau du Stymphale : s'arrête et lâche un éventail de plumes d'airain."""
    HP = 14
    SCORE = 500
    RADIUS = 10
    SPRITE = "stymph"
    EXPLO = 0.85
    COINS = 2

    def setup(self, tx=None, ty=70, stay=110, volleys=2, exit=(0, 2.5), **kw):
        self.tx = self.x if tx is None else tx
        self.ty = ty
        self.stay = stay
        self.volleys = volleys
        self.exit = exit

    def behave(self):
        yield from move_to(self, self.tx, self.ty, 50, ease_out_cubic)
        for v in range(self.volleys):
            yield from wait(24)
            if self.can_fire():
                n = self.w.bullets.dens(7)
                a = self.aim()
                self.w.bullets.arc(self.x, self.y + 6, a, n, 1.2, 2.3, "feather")
                self.w.audio.play("eshot2", self.x)
                self.flash = 2
            yield from wait(self.stay // max(1, self.volleys) - 24)
        self.vx, self.vy = self.exit
        while True:
            self.vy += 0.03
            yield


class Pithos(Enemy):
    """Jarre de Pandore : dérive, et libère ses maux quand on la brise."""
    HP = 6
    SCORE = 150
    RADIUS = 7
    SPRITE = "pithos"
    EXPLO = 0.6

    def setup(self, vy=0.7, vx=0.0, burst=8, **kw):
        self.vy = vy
        self.vx = vx
        self.burst = burst

    def behave(self):
        ph = random.random() * TAU
        while True:
            self.x += math.sin(self.t * 0.04 + ph) * 0.3
            yield

    def on_death(self):
        w = self.w
        if self.y < PF_H - 60:
            n = w.bullets.dens(self.burst)
            w.bullets.ring(self.x, self.y, n, 1.6, "m", "violet", offset=random.random())
            w.fx.ring(self.x, self.y, 2, 24, 14, (200, 90, 255), 2)


class Hermes(Enemy):
    """Messager d'Hermès : traverse l'écran et porte des présents divins."""
    HP = 8
    SCORE = 500
    RADIUS = 8
    SPRITE = "hermes"
    EXPLO = 0.7
    BODY = False

    def setup(self, side=1, y0=60, speed=1.1, amp=18, **kw):
        self.side = side
        self.y0 = y0
        self.speed = speed
        self.amp = amp
        if self.drop is None:
            self.drop = "orb"

    def behave(self):
        self.vx = self.speed * self.side
        while True:
            self.y = self.y0 + math.sin(self.t * 0.05) * self.amp
            yield

    def draw_add(self, add):
        Enemy.draw_add(self, add)
        if (self.t // 4) % 2 == 0:
            for sx in (-9, 9):
                g = glow(2, (200, 255, 255))
                add.blit(g, (int(self.x + sx - 2), int(self.y - 2)), special_flags=pygame.BLEND_ADD)


class Siren(Enemy):
    """Sirène : lyre émettrice, anneaux de balles à trous."""
    HP = 36
    SCORE = 1500
    RADIUS = 10
    SPRITE = "siren"
    EXPLO = 1.0
    COINS = 4
    PCHIPS = 1

    def setup(self, tx=None, ty=64, rings=4, **kw):
        self.tx = self.x if tx is None else tx
        self.ty = ty
        self.rings = rings

    def behave(self):
        yield from move_to(self, self.tx, self.ty, 60, ease_out_cubic)
        rot = 0.0
        for i in range(self.rings):
            yield from wait(40)
            if self.can_fire():
                n = self.w.bullets.dens(18)
                rot += 0.17
                for k in range(n):
                    if k % 6 in (0,):
                        continue
                    a = rot + k * TAU / n
                    self.w.bullets.fire(self.x, self.y + 4, a, 1.5, "m", "pink")
                self.w.fx.ring(self.x, self.y + 4, 4, 30, 16, (255, 90, 200), 2)
                self.w.audio.play("eshot_big", self.x)
        yield from wait(30)
        self.vy = -0.5
        while True:
            self.vy -= 0.03
            yield


class AspisPart(Enemy):
    """Bouclier d'un hoplite : bloque les tirs venant d'en bas."""
    HP = 22
    SCORE = 100
    RADIUS = 8
    SPRITE = "aspis"
    EXPLO = 0.5
    BODY = False

    def setup(self, owner=None, **kw):
        self.owner = owner

    def behave(self):
        while True:
            o = self.owner
            if o is None or o.dead or o.gone:
                self.die()
                return
            self.x, self.y = o.x, o.y + 9
            yield

    def update(self):
        Enemy.update(self)
        self.gone = self.owner is not None and self.owner.gone


class Hoplite(Enemy):
    """Hoplite de la phalange : avance derrière son aspis marquée du lambda."""
    HP = 12
    SCORE = 600
    RADIUS = 8
    SPRITE = "hoplite"
    EXPLO = 0.75
    COINS = 2

    def setup(self, vy=0.8, **kw):
        self.speed = vy
        self.shield = AspisPart(self.w, self.x, self.y + 9, owner=self)
        self.w.spawn(self.shield)

    def behave(self):
        self.vy = self.speed
        k = 0
        while True:
            k += 1
            p = self.w.player
            self.vx = clamp((p.x - self.x) * 0.01, -0.5, 0.5)
            if k % 70 == 40 and self.can_fire():
                n = self.w.bullets.dens(3)
                self.w.bullets.aimed(self.x, self.y + 12, 2.1, n, 0.35, "rice", "orange")
                self.w.audio.play("eshot", self.x)
            yield


class Asteroid(Enemy):
    """Rocher pétrifié : se fragmente."""
    SCORE = 120
    EXPLO = 0.7
    SIZES = {"s": (6, 5.5, 100), "m": (18, 9.0, 250), "l": (45, 14.0, 600)}

    def setup(self, size="m", vx=0.0, vy=1.0, **kw):
        self.size = size
        hp, r, sc = self.SIZES[size]
        self.hp = self.max_hp = hp
        self.RADIUS = r
        self.SCORE = sc
        self.EXPLO = {"s": 0.5, "m": 0.8, "l": 1.2}[size]
        self.vx, self.vy = vx, vy
        self.var = random.randrange(2)
        self.spin = random.uniform(-0.12, 0.12)
        self.ang = random.random() * 8

    def behave(self):
        while True:
            self.ang += self.spin
            yield

    def sprite(self):
        return S[f"rock_{self.size}"][self.var][int(self.ang) % 8]

    def on_death(self):
        w = self.w
        nxt = {"l": "m", "m": "s"}.get(self.size)
        if nxt:
            for i in (-1, 1):
                a = math.atan2(self.vy, self.vx) + i * 0.6
                sp = math.hypot(self.vx, self.vy) + 0.4
                w.spawn(Asteroid(w, self.x + i * 4, self.y, size=nxt, vx=math.cos(a) * sp, vy=math.sin(a) * sp))
        w.fx.explosion(self.x, self.y, 0.4, grad=[(0.0, (255, 255, 240)), (0.3, (200, 190, 170)),
                                                   (0.7, (90, 80, 80)), (1.0, (0, 0, 0))], smoke_on=True)


class SerpentSeg(Enemy):
    HP = 999
    SCORE = 50
    RADIUS = 5
    SPRITE = "serpent_seg"
    EXPLO = 0.5
    ARMOR = True
    BOSSPART = True

    def setup(self, head=None, idx=0, tail=False, **kw):
        self.head = head
        self.idx = idx
        if tail:
            self.SPRITE = "serpent_tail"

    def behave(self):
        while True:
            yield

    def update(self):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        h = self.head
        k = (self.idx + 1) * 5
        if len(h.trail) > k:
            self.x, self.y = h.trail[-k]
        self.gone = h.gone


class Serpent(Rotor):
    """Serpent d'airain : un mur mouvant d'anneaux invulnérables, seule la tête est vulnérable."""
    HP = 40
    SCORE = 2500
    RADIUS = 7
    ROT = None
    EXPLO = 1.0
    COINS = 5
    PCHIPS = 1

    def setup(self, path=None, dur=420, segs=10, **kw):
        self.path = path or [(self.x, -20), (60, 80), (200, 140), (60, 200), (128, 300)]
        self.dur = dur
        self.trail = []
        self.segs = []
        for i in range(segs):
            s = SerpentSeg(self.w, self.x, self.y, head=self, idx=i, tail=(i == segs - 1))
            self.segs.append(s)
            self.w.spawn(s)

    def behave(self):
        for _ in follow(self, self.path, self.dur):
            if self.t % 50 == 25 and self.can_fire():
                self.w.bullets.aimed(self.x, self.y, 2.2, self.w.bullets.dens(3), 0.4, "m", "green")
                self.w.audio.play("eshot", self.x, 0.7)
            yield
        self.vx, self.vy = math.cos(self.face) * 2.0, math.sin(self.face) * 2.0
        while True:
            yield

    def update(self):
        Rotor.update(self)
        self.trail.append((self.x, self.y))
        if len(self.trail) > 400:
            del self.trail[:100]

    def sprite(self):
        return S["serpent_head"][rot_index(self.face, NTUR)]

    def on_death(self):
        w = self.w
        for i, s in enumerate(self.segs):
            if not s.dead:
                s.dead = True
                w.fx.explosion(s.x, s.y, 0.6, delay=i * 4)
                w.score.add(50, popup=False)
        w.audio.play("explo_m", self.x)


class Shade(Enemy):
    """Ombre du Tartare : ne se matérialise que par intermittence."""
    HP = 10
    SCORE = 400
    RADIUS = 8
    SPRITE = "shade"
    EXPLO = 0.7
    BODY = True

    def setup(self, vy=0.5, **kw):
        self.vy = vy
        self.phase = random.randrange(150)
        self.base_x = self.x

    def solid(self):
        return (self.t + self.phase) % 150 < 95

    def targetable(self):
        return self.onscreen and self.solid()

    def behave(self):
        while True:
            self.x = self.base_x + math.sin((self.t + self.phase) * 0.03) * 30
            if (self.t + self.phase) % 150 == 50 and self.can_fire():
                n = self.w.bullets.dens(4)
                self.w.bullets.aimed(self.x, self.y, 1.4, n, 0.8, "l", "green", wave=0.02)
                self.w.audio.play("eshot2", self.x, 0.6)
            yield

    def draw(self, surf):
        k = (self.t + self.phase) % 150
        spr = self.sprite()
        if k < 95:
            a = 255 if k > 10 else int(25 * k)
            if k > 85:
                a = int(255 * (95 - k) / 10)
        else:
            a = 40 if (self.t // 2) % 2 else 0
        img = spr.flash if self.flash > 0 else spr.img
        img.set_alpha(a)
        surf.blit(img, (int(self.x - spr.ox), int(self.y - spr.oy)))
        img.set_alpha(255)

    def draw_add(self, add):
        if self.solid():
            Enemy.draw_add(self, add)


class Erinys(Rotor):
    """Érinye : fonce sur sa proie après un bref avertissement."""
    HP = 8
    SCORE = 350
    RADIUS = 8
    ROT = "erinys_r"
    EXPLO = 0.7

    def setup(self, ty=60, **kw):
        self.ty = ty
        self.dashing = False

    def behave(self):
        yield from move_to(self, self.x, self.ty, 40, ease_out_cubic)
        self.face = self.aim()
        for i in range(24):
            self.face = self.aim()
            yield
        a = self.aim()
        self.dashing = True
        self.w.audio.play("eshot2", self.x, 0.8)
        if self.can_fire():
            self.w.bullets.aimed(self.x, self.y, 1.8, self.w.bullets.dens(3), 0.6, "rice", "red")
        sp = 1.0
        while True:
            sp = min(6.5, sp + 0.35)
            self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
            if self.t % 2 == 0:
                self.w.fx.add(Particle(K_GLOW, self.x, self.y, 0, 0, 12, 6, 2, (160, 20, 40)))
            yield

    def draw_add(self, add):
        Rotor.draw_add(self, add)
        if not self.dashing and self.t > 40 and (self.t // 3) % 2:
            a = self.aim()
            pygame.draw.line(add, (90, 10, 20), (self.x, self.y),
                             (self.x + math.cos(a) * 60, self.y + math.sin(a) * 60), 1)


class Eagle(Rotor):
    """Aigle de Zeus : décoche des aiguilles-éclairs."""
    HP = 22
    SCORE = 900
    RADIUS = 10
    ROT = "eagle_r"
    EXPLO = 0.95
    COINS = 3

    def setup(self, path=None, dur=240, **kw):
        self.path = path or [(self.x, -20), (self.x, 80), (PF_W - self.x, 120), (PF_W - self.x, -30)]
        self.dur = dur

    def behave(self):
        for _ in follow(self, self.path, self.dur):
            if self.t % 45 == 30 and self.can_fire():
                self.w.bullets.aimed(self.x, self.y, 3.0, self.w.bullets.dens(3), 0.25, "needle", "blue")
                self.w.audio.play("zap", self.x, 0.5, throttle=6)
            yield
        self.vx, self.vy = math.cos(self.face) * 2.5, math.sin(self.face) * 2.5
        while True:
            yield


class LavaDrone(Enemy):
    """Drone de lave : jaillit du magma et crache des gerbes de feu."""
    HP = 10
    SCORE = 350
    RADIUS = 7
    SPRITE = "lavadrone"
    EXPLO = 0.7
    KILL_SFX = "fire_burst"

    def setup(self, tx=None, ty=90, **kw):
        self.tx = self.x if tx is None else tx
        self.ty = ty

    def behave(self):
        yield from move_to(self, self.tx, self.ty, 45, ease_out_cubic)
        for i in range(2):
            yield from wait(35)
            if self.can_fire():
                n = self.w.bullets.dens(10)
                self.w.bullets.ring(self.x, self.y, n, 1.7, "m", "orange", offset=random.random())
                self.w.audio.play("fire_burst", self.x, 0.6)
        yield from wait(20)
        self.vy = 1.0
        while True:
            self.vy += 0.04
            if self.t % 3 == 0:
                self.w.fx.add(Particle(K_FIRE, self.x, self.y, 0, -0.3, 14, 3, 6, grad=P.FIRE))
            yield

    def update(self):
        Enemy.update(self)
        if self.t % 4 == 0:
            self.w.fx.embers(self.x, self.y, 1, spread=8)


# ---------------------------------------------------------------------------
# Ennemis au sol (défilent avec le décor)
# ---------------------------------------------------------------------------
class Turret(Enemy):
    GROUND = True
    BODY = False
    BASE = "cyclops_base"
    TUR = "cyclops_tur"

    def setup(self, rate=100, burst=3, speed=2.2, col="pink", kind="m", delay=None, **kw):
        self.rate = rate
        self.burst = burst
        self.speed = speed
        self.col = col
        self.kind = kind
        self.aim_a = math.pi / 2
        self.cool = random.randrange(30, 60) if delay is None else delay
        self.charge = 0

    def behave(self):
        while True:
            p = self.w.player
            want = math.atan2(p.y - self.y, p.x - self.x)
            self.aim_a += clamp(angle_diff(self.aim_a, want), -0.06, 0.06)
            self.cool -= 1
            if self.cool <= 20:
                self.charge = 20 - self.cool
            if self.cool <= 0:
                self.cool = int(self.rate / self.w.diff["rate"])
                self.charge = 0
                if self.can_fire():
                    yield from self.shoot()
            yield

    def shoot(self):
        for i in range(self.burst):
            if self.dead:
                return
            mx, my = self.x + math.cos(self.aim_a) * 8, self.y + math.sin(self.aim_a) * 8
            self.w.bullets.fire(mx, my, self.aim_a, self.speed, self.kind, self.col)
            self.w.fx.add(Particle(K_FLARE, mx, my, 0, 0, 4, 5, 2, (255, 150, 200)))
            self.w.audio.play("eshot", self.x, 0.6, throttle=3)
            yield from wait(6)

    def draw(self, surf):
        S[self.BASE].draw(surf, self.x, self.y, self.flash > 0)
        S[self.TUR][rot_index(self.aim_a, NTUR)].draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        S[self.BASE].draw_halo(add, self.x, self.y)
        S[self.TUR][rot_index(self.aim_a, NTUR)].draw_halo(add, self.x, self.y)
        if self.charge > 0:
            k = self.charge / 20
            g = glow(int(3 + 5 * k), (int(255 * k), int(60 * k), int(120 * k)), 0.5 * k)
            add.blit(g, (int(self.x + math.cos(self.aim_a) * 3 - g.get_width() // 2),
                         int(self.y + math.sin(self.aim_a) * 3 - g.get_height() // 2)), special_flags=pygame.BLEND_ADD)

    def image(self):
        return S[self.BASE].img


class Cyclops(Turret):
    """Tourelle cyclope : l'œil rougeoie avant la rafale."""
    HP = 16
    SCORE = 800
    RADIUS = 9
    EXPLO = 0.9
    COINS = 2


class WallGun(Turret):
    """Tourelle murale du Labyrinthe : éventails."""
    HP = 20
    SCORE = 700
    RADIUS = 9
    EXPLO = 0.85
    BASE = "wallgun_base"
    TUR = "wallgun_tur"
    COINS = 2

    def shoot(self):
        n = self.w.bullets.dens(5)
        self.w.bullets.arc(self.x, self.y, self.aim_a, n, 0.9, 1.9, "rice", "violet")
        self.w.audio.play("eshot2", self.x, 0.7)
        yield


class Centaur(Enemy):
    """Kentauros : char-archer qui patrouille au sol."""
    HP = 18
    SCORE = 900
    RADIUS = 9
    GROUND = True
    BODY = False
    EXPLO = 0.95
    COINS = 2

    def setup(self, vx=0.4, vy=0.3, **kw):
        self.vx = vx
        self.vy = vy
        self.aim_a = math.pi / 2
        self.cool = 60

    def behave(self):
        while True:
            p = self.w.player
            want = math.atan2(p.y - self.y, p.x - self.x)
            self.aim_a += clamp(angle_diff(self.aim_a, want), -0.05, 0.05)
            if self.x < 20 or self.x > PF_W - 20:
                self.vx = -self.vx
            self.cool -= 1
            if self.cool <= 0:
                self.cool = int(90 / self.w.diff["rate"])
                if self.can_fire():
                    n = self.w.bullets.dens(3)
                    self.w.bullets.arc(self.x, self.y, self.aim_a, n, 0.3, 2.6, "arrow", "orange")
                    self.w.audio.play("arrow", self.x, 0.5, throttle=4)
            yield

    def draw(self, surf):
        base = S["centaur_base"]
        base.draw(surf, self.x, self.y, self.flash > 0)
        S["centaur_tur"][rot_index(self.aim_a, NTUR)].draw(surf, self.x, self.y - 1, self.flash > 0)

    def draw_shadow(self, surf):
        pass

    def image(self):
        return S["centaur_base"].img


class GorgonEye(Enemy):
    """Œil de la Gorgone : rayon pétrifiant télégraphié."""
    HP = 24
    SCORE = 1200
    RADIUS = 9
    SPRITE = "gorgon_eye"
    EXPLO = 0.9
    COINS = 3

    def setup(self, vy=0.5, ground=False, period=150, **kw):
        self.vy = vy
        self.period = period
        self.beam = None
        if ground:
            self.GROUND = True
            self.BODY = False

    def behave(self):
        k = random.randrange(40)
        while True:
            k += 1
            if k % int(self.period / self.w.diff["rate"]) == 60 and self.can_fire():
                a = self.aim()
                x1, y1 = self.x + math.cos(a) * 400, self.y + math.sin(a) * 400
                self.beam = Hazard(self.w, self.x, self.y, x1, y1, 7, 45, 30, (90, 255, 150), owner=self)
                self.w.hazards.append(self.beam)
            if self.beam is not None:
                bm = self.beam
                ang = math.atan2(bm.y1 - bm.y0, bm.x1 - bm.x0)
                bm.x0, bm.y0 = self.x, self.y
                bm.x1, bm.y1 = self.x + math.cos(ang) * 400, self.y + math.sin(ang) * 400
                if not bm.alive:
                    self.beam = None
            yield


class Pylon(Enemy):
    """Pylône de l'Olympe : relié à un jumeau par un arc électrique."""
    HP = 30
    SCORE = 1000
    RADIUS = 8
    SPRITE = "pylon"
    GROUND = True
    BODY = False
    EXPLO = 0.9
    COINS = 2

    def setup(self, twin=None, period=120, **kw):
        self.twin = twin
        self.period = period
        self.arc = None

    def behave(self):
        k = 0
        while True:
            k += 1
            tw = self.twin
            if tw is not None and not tw.dead and k % self.period == 30 and self.onscreen:
                self.arc = Hazard(self.w, self.x, self.y - 7, tw.x, tw.y - 7, 6, 36, 44, (140, 190, 255), owner=self,
                                  kind="bolt", track=lambda: (self.x, self.y - 7, self.twin.x, self.twin.y - 7))
                self.w.hazards.append(self.arc)
            if self.arc is not None and (tw is None or tw.dead):
                self.arc.alive = False
                self.arc = None
            yield


class Bull(Enemy):
    """Taureau d'airain : charge en ligne droite après avoir gratté le sol."""
    HP = 14
    SCORE = 500
    RADIUS = 9
    SPRITE = "bull"
    EXPLO = 0.8
    COINS = 1

    def setup(self, ty=50, **kw):
        self.ty = ty

    def behave(self):
        yield from move_to(self, self.x, self.ty, 40, ease_out_cubic)
        for i in range(30):
            self.x += (-1) ** i * 0.8
            yield
        self.w.audio.play("roar", self.x, 0.35, throttle=30)
        sp = 0.5
        while True:
            sp = min(5.5, sp + 0.25)
            self.vy = sp
            if self.t % 3 == 0:
                self.w.fx.add(Particle(K_GLOW, self.x, self.y - 8, 0, -1, 10, 5, 1, (160, 60, 20)))
            yield


class HammerBot(Enemy):
    """Automate-forgeron : frappe l'enclune et projette des anneaux de scories."""
    HP = 26
    SCORE = 1100
    RADIUS = 9
    SPRITE = "hammerbot"
    GROUND = True
    BODY = False
    EXPLO = 1.0
    COINS = 3

    def setup(self, vx=0.3, **kw):
        self.vx = vx

    def behave(self):
        k = random.randrange(60)
        while True:
            k += 1
            if self.x < 24 or self.x > PF_W - 24:
                self.vx = -self.vx
            if k % int(110 / self.w.diff["rate"]) == 0 and self.can_fire():
                n = self.w.bullets.dens(12)
                self.w.bullets.ring(self.x, self.y, n, 1.5, "s", "orange", offset=random.random())
                self.w.fx.ring(self.x, self.y, 3, 22, 12, (255, 160, 60), 2)
                self.w.fx.spark_burst(self.x, self.y, 10, (255, 200, 120), 3.5, 14)
                self.w.audio.play("clang", self.x, 0.6)
                self.flash = 3
            yield


class Trireme(Enemy):
    """Trirème de guerre : bordées latérales et canons de pont."""
    HP = 90
    SCORE = 3000
    RADIUS = 14
    SPRITE = "trireme"
    EXPLO = 1.6
    COINS = 8
    PCHIPS = 2
    KILL_SFX = "explo_m"

    def setup(self, ty=70, stay=420, **kw):
        self.ty = ty
        self.stay = stay
        self.hitboxes = [(0, -10, 7, 16), (0, 12, 6, 14)]
        self.cannons = [math.pi / 2, math.pi / 2]

    def behave(self):
        yield from move_to(self, self.x, self.ty, 120, ease_out_cubic)
        k = 0
        while k < self.stay:
            k += 1
            p = self.w.player
            for i, cy in enumerate((-14, 14)):
                want = math.atan2(p.y - (self.y + cy), p.x - self.x)
                self.cannons[i] += clamp(angle_diff(self.cannons[i], want), -0.05, 0.05)
            if k % int(80 / self.w.diff["rate"]) == 40 and self.can_fire():
                # bordée : rangées de balles de chaque flanc
                for side in (-1, 1):
                    for j in range(self.w.bullets.dens(5)):
                        y = self.y - 16 + j * 8
                        a = math.pi / 2 - side * (math.pi / 2 - 0.5)
                        self.w.bullets.fire(self.x + side * 10, y, a, 1.6, "s", "orange")
                self.w.audio.play("eshot_big", self.x)
            if k % int(55 / self.w.diff["rate"]) == 20 and self.can_fire():
                for i, cy in enumerate((-14, 14)):
                    self.w.bullets.fire(self.x, self.y + cy, self.cannons[i], 2.4, "m", "pink")
                self.w.audio.play("eshot", self.x, 0.7)
            yield
        self.vy = 0.2
        while True:
            self.vy = min(1.4, self.vy + 0.01)
            yield

    def draw(self, surf):
        Enemy.draw(self, surf)
        for i, cy in enumerate((-14, 14)):
            S["cyclops_tur"][rot_index(self.cannons[i], NTUR)].draw(surf, self.x, self.y + cy, self.flash > 0)

    def draw_add(self, add):
        Enemy.draw_add(self, add)
        for i, cy in enumerate((-14, 14)):
            S["cyclops_tur"][rot_index(self.cannons[i], NTUR)].draw_halo(add, self.x, self.y + cy)
        # rames-propulseurs
        if (self.t // 3) % 2 == 0:
            for side in (-1, 1):
                for y in range(-18, 20, 5):
                    g = glow(2, (255, 140, 60))
                    add.blit(g, (int(self.x + side * 12 - 2), int(self.y + y + 2.4 - 2)), special_flags=pygame.BLEND_ADD)


ENEMY_TYPES = {
    "myrmex": Myrmex, "harpy": Harpy, "stymph": Stymphalian, "pithos": Pithos, "hermes": Hermes,
    "siren": Siren, "hoplite": Hoplite, "rock": Asteroid, "serpent": Serpent, "shade": Shade, "erinys": Erinys,
    "eagle": Eagle, "lava": LavaDrone, "cyclops": Cyclops, "wallgun": WallGun, "centaur": Centaur,
    "gorgon": GorgonEye, "pylon": Pylon, "bull": Bull, "hammer": HammerBot, "trireme": Trireme,
}
