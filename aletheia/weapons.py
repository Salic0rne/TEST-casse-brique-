"""Armes divines : 6 dieux x 3 modes (α β γ), + les « Théophanies » (bombes).

Chaque arme reçoit update(firing) à chaque image et gère ses projectiles / rayons.
Niveau de puissance lv = 0..5 (le « blindage » du vaisseau façon Super Aleste).
"""
import math
import random

import pygame

from . import palette as P
from .sprites import S, NROT
from .spritegen import rot_index
from .fx import (glow, Particle, K_FIRE, K_SPARK, K_GLOW, K_FLARE, K_RING, K_EMBER, K_STREAK, bolt_points,
                 draw_bolt, draw_bolt_tree)
from .util import TAU, clamp, angle_diff, gradient

PF_W, PF_H = 256, 270
GODS = ["zeus", "apollo", "artemis", "poseidon", "athena", "hephaestus"]
GOD_NAMES = {"zeus": "ZEUS", "apollo": "APOLLON", "artemis": "ARTÉMIS", "poseidon": "POSÉIDON",
             "athena": "ATHÉNA", "hephaestus": "HÉPHAÏSTOS"}
WEAPON_NAMES = {"zeus": "KERAUNOS", "apollo": "HÉLIOS", "artemis": "TOXA", "poseidon": "TRIAINA",
                "athena": "AIGIS", "hephaestus": "PYR"}
MODE_NAMES = {
    "zeus": ("CHAÎNE", "LANCE", "TEMPÊTE"),
    "apollo": ("RAYON", "ÉVENTAIL", "COURONNE"),
    "artemis": ("CHASSE", "VOLÉE", "LUNES"),
    "poseidon": ("TRIDENT", "MARÉE", "ABYSSE"),
    "athena": ("ORBITE", "PHALANGE", "JAVELOT"),
    "hephaestus": ("FORGE", "MORTIER", "MÉTÉORE"),
}
MODE_GREEK = ("α", "β", "γ")


def dps(lv):
    return 16 + 11 * lv


# ---------------------------------------------------------------------------
# Projectile générique du joueur
# ---------------------------------------------------------------------------
class Proj:
    __slots__ = ("w", "x", "y", "vx", "vy", "dmg", "r", "pierce", "life", "t", "spr", "frames", "rbase",
                 "alive", "hits", "cd", "col", "trail", "homing", "turn", "spd", "target", "kind", "data")

    def __init__(self, w, x, y, vx, vy, dmg, spr=None, r=3.0, pierce=False, life=90, frames=None,
                 rbase=-math.pi / 2, col=(255, 230, 170), trail=None, cd=8, kind=None):
        self.w = w
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.dmg = dmg
        self.spr = spr
        self.r = r
        self.pierce = pierce
        self.life = life
        self.t = 0
        self.frames = frames
        self.rbase = rbase
        self.alive = True
        self.hits = {} if pierce else None
        self.cd = cd
        self.col = col
        self.trail = trail
        self.homing = False
        self.turn = 0.0
        self.spd = math.hypot(vx, vy)
        self.target = None
        self.kind = kind
        self.data = None

    def update(self):
        self.t += 1
        self.move()
        if self.t > self.life or self.x < -20 or self.x > PF_W + 20 or self.y < -24 or self.y > PF_H + 20:
            self.alive = False
            self.on_end()
            return
        if self.trail and self.t % 2 == 0:
            self.w.fx.add(Particle(K_GLOW, self.x, self.y, 0, 0, 8, 2.5, 1, self.trail))
        self.collide()
        if not self.alive:
            self.on_end()

    def move(self):
        if self.homing:
            self.steer()
        self.x += self.vx
        self.y += self.vy

    def on_end(self):
        pass

    def steer(self):
        w = self.w
        tg = self.target
        if tg is None or tg.dead or tg.gone or not tg.targetable():
            tg = self.target = w.nearest_target(self.x, self.y, 260)
        if tg is not None:
            a = math.atan2(self.vy, self.vx)
            want = math.atan2(tg.y - self.y, tg.x - self.x)
            a += clamp(angle_diff(a, want), -self.turn, self.turn)
            self.vx = math.cos(a) * self.spd
            self.vy = math.sin(a) * self.spd

    def collide(self):
        w = self.w
        for e in w.targets:
            if e.dead or not e.collide(self.x, self.y, self.r):
                continue
            if self.pierce:
                last = self.hits.get(id(e))
                if last is not None and w.t - last < self.cd:
                    continue
                self.hits[id(e)] = w.t
                e.hit(self.dmg, self.x, self.y)
                self.on_hit(e)
            else:
                e.hit(self.dmg, self.x, self.y)
                self.on_hit(e)
                self.alive = False
                return

    def on_hit(self, e):
        pass

    def sprite(self):
        if self.frames is not None:
            return self.frames[rot_index(math.atan2(self.vy, self.vx), NROT, self.rbase)]
        return self.spr

    def draw(self, surf):
        spr = self.sprite()
        if spr is not None:
            surf.blit(spr.img, (int(self.x - spr.ox), int(self.y - spr.oy)))

    def draw_add(self, add):
        spr = self.sprite()
        if spr is not None and spr.halo is not None:
            add.blit(spr.halo, (int(self.x - spr.hox), int(self.y - spr.hoy)), special_flags=pygame.BLEND_ADD)


class Streak(Proj):
    """Trait de lumière (lasers d'Apollon) dessiné en lignes."""
    __slots__ = ()

    def draw(self, surf):
        pass

    def draw_add(self, add):
        x0, y0 = self.x, self.y
        x1, y1 = x0 - self.vx * 1.8, y0 - self.vy * 1.8
        pygame.draw.line(add, (120, 70, 10), (x0, y0), (x1, y1), 5)
        pygame.draw.line(add, (255, 190, 60), (x0, y0), (x1, y1), 3)
        pygame.draw.line(add, (255, 255, 230), (x0, y0), (x1, y1), 1)


class Flame(Proj):
    """Flamme de la forge : grossit et refroidit."""
    __slots__ = ()

    def move(self):
        self.vx *= 0.97
        self.vy *= 0.97
        self.x += self.vx
        self.y += self.vy
        self.r = 3 + self.t * 0.45

    def draw(self, surf):
        pass

    def draw_add(self, add):
        f = self.t / self.life
        r = 3 + self.t * 0.75
        c = gradient(P.FIRE, 0.04 + f * 0.85)
        g = glow(r, c, 0.45 * (1 - f) if f < 0.5 else 0.0)
        add.blit(g, (int(self.x - g.get_width() // 2), int(self.y - g.get_height() // 2)),
                 special_flags=pygame.BLEND_ADD)


class Shell(Proj):
    """Obus de mortier : explose au contact ou en fin de course."""
    __slots__ = ()

    def collide(self):
        for e in self.w.targets:
            if not e.dead and e.collide(self.x, self.y, self.r):
                self.alive = False
                return

    def on_end(self):
        w = self.w
        rad = self.data or 24
        w.area_damage(self.x, self.y, rad, self.dmg)
        w.fx.explosion(self.x, self.y, 0.8, smoke_on=False)
        w.fx.ring(self.x, self.y, 2, rad, 12, (255, 170, 80), 2)
        w.audio.play("fire_burst", self.x, 0.6, throttle=4)
        w.juice.shake(0.05)


class Meteor(Proj):
    __slots__ = ()

    def move(self):
        Proj.move(self)
        if self.t % 2 == 0:
            self.w.fx.add(Particle(K_FIRE, self.x + random.uniform(-3, 3), self.y + 4, random.uniform(-0.3, 0.3),
                                   0.8, 18, 4, 7, grad=P.FIRE))
        if self.t > 52 or self.y < 18:
            self.t = self.life + 1

    def on_end(self):
        w = self.w
        n = self.data or 6
        for i in range(n):
            a = i * TAU / n + random.random() * 0.2
            w.add_shot(Proj(w, self.x, self.y, math.cos(a) * 4.2, math.sin(a) * 4.2, self.dmg * 0.6, S["shell"], 4,
                            False, 40, trail=(255, 130, 40)))
        w.fx.explosion(self.x, self.y, 0.9, smoke_on=False)
        w.audio.play("fire_burst", self.x, 0.7, throttle=4)


class Tide(Proj):
    """Double hélice de la Marée."""
    __slots__ = ()

    def move(self):
        x0, ph, amp = self.data
        self.y += self.vy
        self.x = x0 + math.sin(ph + self.t * 0.22) * amp * min(1.0, self.t / 8)


class Wave(Proj):
    """Croissant du Trident : s'élargit en avançant."""
    __slots__ = ()

    def move(self):
        Proj.move(self)
        self.r = 5 + self.t * 0.12

    def draw_add(self, add):
        Proj.draw_add(self, add)
        if self.t > 10:
            k = min(1.0, (self.t - 10) / 30)
            a = math.atan2(self.vy, self.vx)
            px, py = -math.sin(a), math.cos(a)
            wdt = 4 + self.t * 0.14
            c = (int(30 * (1 - k * 0.5)), int(160 * (1 - k * 0.5)), int(150 * (1 - k * 0.5)))
            pygame.draw.line(add, c, (self.x - px * wdt, self.y - py * wdt), (self.x + px * wdt, self.y + py * wdt), 2)


class Abyss(Proj):
    """Orbe des profondeurs : se change en tourbillon au contact ou en fin de course."""
    __slots__ = ()

    def on_end(self):
        rad, tick = self.data
        self.w.add_shot(Vortex(self.w, self.x, self.y, rad, tick))
        self.w.audio.play("splash", self.x, 0.5, throttle=6)


class Vortex:
    """Tourbillon d'Abysse : dégâts de zone + absorbe les balles."""

    def __init__(self, w, x, y, rad, dmg_tick):
        self.w = w
        self.x = x
        self.y = y
        self.rad = rad
        self.dmg = dmg_tick
        self.t = 0
        self.life = 48
        self.alive = True

    def update(self):
        self.t += 1
        self.y += self.w.scroll * 0.5
        if self.t % 3 == 0:
            self.w.area_damage(self.x, self.y, self.rad, self.dmg, silent=True)
        if self.t % 4 == 0:
            self.w.bullets.cancel(False, self.x, self.y, self.rad * 0.7)
        if self.t >= self.life:
            self.alive = False

    def draw(self, surf):
        pass

    def draw_add(self, add):
        f = self.t / self.life
        k = math.sin(f * math.pi)
        r = self.rad * (0.6 + 0.4 * k)
        for i in range(10):
            a = self.t * 0.25 + i * TAU / 10
            rr = r * (0.3 + 0.7 * ((i * 37) % 10) / 10)
            x = self.x + math.cos(a + rr * 0.05) * rr
            y = self.y + math.sin(a + rr * 0.05) * rr * 0.8
            g = glow(3, (40 * k, 200 * k, 200 * k))
            add.blit(g, (int(x - 3), int(y - 3)), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(add, (20 * k, 110 * k, 120 * k), (int(self.x), int(self.y)), int(r), 2)
        g = glow(int(r * 0.8), (10 * k, 60 * k, 70 * k))
        add.blit(g, (int(self.x - g.get_width() // 2), int(self.y - g.get_height() // 2)),
                 special_flags=pygame.BLEND_ADD)


class Aegis:
    """Bouclier d'Athéna (orbite / phalange / javelot) : bloque les balles, blesse au contact."""

    def __init__(self, w, x, y):
        self.w = w
        self.x = x
        self.y = y
        self.alive = True
        self.t = 0
        self.vx = 0.0
        self.vy = 0.0
        self.returning = False
        self.thrown = False
        self.hits = {}

    def block(self, rad=6.5):
        w = self.w
        keep = []
        blocked = 0
        for b in w.bullets.list:
            dx, dy = b.x - self.x, b.y - self.y
            if dx * dx + dy * dy < (rad + b.r) ** 2:
                blocked += 1
                w.fx.hit(b.x, b.y, (255, 230, 150), 2)
            else:
                keep.append(b)
        if blocked:
            w.bullets.list = keep
            w.audio.play("block", self.x, 0.7, throttle=4)
            w.score.add(10 * blocked, popup=False)

    def contact(self, dmg, cd=6):
        w = self.w
        for e in w.targets:
            if not e.dead and e.collide(self.x, self.y, 6):
                last = self.hits.get(id(e))
                if last is None or w.t - last >= cd:
                    self.hits[id(e)] = w.t
                    e.hit(dmg, self.x, self.y)

    def draw(self, surf):
        spr = S["aegis"]
        spr.draw(surf, self.x, self.y)

    def draw_add(self, add):
        S["aegis"].draw_halo(add, self.x, self.y)


# ---------------------------------------------------------------------------
# Armes
# ---------------------------------------------------------------------------
class Weapon:
    god = "zeus"

    def __init__(self, w, player):
        self.w = w
        self.p = player
        self.mode = 0
        self.cool = 0
        self.t = 0
        self.objs = []

    @property
    def lv(self):
        return self.p.power

    def set_mode(self, m):
        self.stop()
        self.mode = m % 3
        self.objs = []

    def stop(self):
        pass

    def update(self, firing):
        self.t += 1
        if self.cool > 0:
            self.cool -= 1

    def draw(self, surf):
        for o in self.objs:
            o.draw(surf)

    def draw_add(self, add):
        for o in self.objs:
            o.draw_add(add)


class Zeus(Weapon):
    god = "zeus"

    def __init__(self, w, p):
        super().__init__(w, p)
        self.bolts = []   # (x0,y0,x1,y1,vie)
        self.beam_end = None

    def stop(self):
        self.w.audio.loop("zap_beam", False)
        self.beam_end = None

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        self.bolts = [(a, b, c, d, n - 1) for (a, b, c, d, n) in self.bolts if n > 1]
        nx, ny = p.x, p.y - 13
        if self.mode == 0:           # CHAÎNE
            if firing and self.cool <= 0:
                self.cool = 7
                rng_ = 100 + 10 * lv
                cands = [e for e in w.targets if e.y < p.y + 12 and not e.armored()
                         and (e.x - nx) ** 2 + (e.y - ny) ** 2 < rng_ * rng_]
                cands.sort(key=lambda e: (e.x - nx) ** 2 + (e.y - ny) ** 2)
                n1 = 1 + lv // 2
                prim = cands[:n1]
                if prim:
                    dmg = dps(lv) * 7 / 60 / len(prim) * 1.05
                    jumps = 1 if lv < 3 else 2
                    for e in prim:
                        self.bolts.append((nx, ny, e.x, e.y, 8))
                        e.hit(dmg, e.x, e.y + 4)
                        w.fx.hit(e.x, e.y, (170, 220, 255), 3)
                        src = e
                        done = {id(e)}
                        for _ in range(jumps):
                            nxt = None
                            bd = 55 * 55
                            for o in w.targets:
                                if id(o) in done or o.dead or o.armored():
                                    continue
                                d = (o.x - src.x) ** 2 + (o.y - src.y) ** 2
                                if d < bd:
                                    bd, nxt = d, o
                            if nxt is None:
                                break
                            done.add(id(nxt))
                            self.bolts.append((src.x, src.y, nxt.x, nxt.y, 8))
                            nxt.hit(dmg * 0.6, nxt.x, nxt.y)
                            src = nxt
                    w.audio.play("zap", nx, 0.8, throttle=6)
                else:
                    for _ in range(2):
                        a = -math.pi / 2 + random.uniform(-0.8, 0.8)
                        ln = random.uniform(16, 30)
                        self.bolts.append((nx, ny, nx + math.cos(a) * ln, ny + math.sin(a) * ln, 4))
        elif self.mode == 1:         # LANCE
            if firing:
                hw = 3 + lv * 0.6
                best, by = None, -20.0
                for e in w.targets:
                    yb = w.vline_hit(e, nx, hw, ny)
                    if yb is not None and yb > by:
                        best, by = e, yb
                self.beam_end = by if best else -10
                if best:
                    best.hit(dps(lv) * 1.3 / 60, nx, by, silent=(w.t % 5 != 0))
                    if w.t % 3 == 0:
                        w.fx.spark_burst(nx, by, 2, (170, 220, 255), 3, 10, 2.4, math.pi / 2)
                w.audio.loop("zap_beam", True, 0.8, nx)
            else:
                self.beam_end = None
                w.audio.loop("zap_beam", False)
        else:                        # TEMPÊTE
            if firing and self.cool <= 0:
                self.cool = 6
                R = 62 + 6 * lv
                cands = [e for e in w.targets if not e.armored() and (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < R * R]
                cands.sort(key=lambda e: (e.x - p.x) ** 2 + (e.y - p.y) ** 2)
                cands = cands[:2 + lv]
                if cands:
                    dmg = dps(lv) * 6 / 60 / max(2, len(cands)) * 1.45
                    for e in cands:
                        self.bolts.append((p.x, p.y, e.x, e.y, 4))
                        e.hit(dmg, e.x, e.y)
                    w.audio.play("zap", p.x, 0.6, throttle=8)
                else:
                    a = random.random() * TAU
                    self.bolts.append((p.x, p.y, p.x + math.cos(a) * R * 0.5, p.y + math.sin(a) * R * 0.5, 3))
                if lv >= 1:
                    n = w.bullets.cancel(False, p.x, p.y, 16 + 2 * lv)
                    if n:
                        w.audio.play("zap", p.x, 0.4, throttle=10)

    def draw_add(self, add):
        col = (110, 170, 255)
        for (x0, y0, x1, y1, n) in self.bolts:
            pts = bolt_points(x0, y0, x1, y1, 7)
            draw_bolt(add, pts, col, width=2 if n > 2 else 1)
        if self.mode == 1 and self.beam_end is not None:
            p = self.p
            nx, ny = p.x, p.y - 13
            hw = 3 + self.lv * 0.6
            ye = self.beam_end
            for k in range(2):
                pts = bolt_points(nx, ny, nx, ye, 3 + hw)
                draw_bolt(add, pts, col, width=int(hw))
            g = glow(int(6 + hw), (80, 140, 255), 0.6)
            add.blit(g, (int(nx - g.get_width() // 2), int(ye - g.get_height() // 2)), special_flags=pygame.BLEND_ADD)
            g = glow(8, (60, 100, 220), 0.5)
            add.blit(g, (int(nx - 8), int(ny - 8)), special_flags=pygame.BLEND_ADD)
        if self.mode == 2 and self.p.firing:
            p = self.p
            R = 62 + 6 * self.lv
            k = 0.5 + 0.5 * math.sin(self.t * 0.4)
            pygame.draw.circle(add, (int(20 + 20 * k), int(40 + 30 * k), int(90 + 40 * k)), (int(p.x), int(p.y)),
                               int(16 + 2 * self.lv), 1)
            pygame.draw.circle(add, (10, 20, 50), (int(p.x), int(p.y)), int(R), 1)


class Apollo(Weapon):
    god = "apollo"

    def __init__(self, w, p):
        super().__init__(w, p)
        self.beams = []    # (x0, y0, angle, length)

    def stop(self):
        self.w.audio.loop("laser_loop", False)
        self.beams = []

    def beam(self, x0, y0, ang, hw, dmg):
        """Rayon perçant : blesse tout ce qu'il traverse."""
        w = self.w
        dx, dy = math.cos(ang), math.sin(ang)
        length = 320
        for e in w.targets:
            if e.dead:
                continue
            ex, ey = e.x - x0, e.y - y0
            proj = ex * dx + ey * dy
            if proj < -4:
                continue
            perp = abs(ex * dy - ey * dx)
            if perp < e.RADIUS + hw or w.segment_hits_boxes(e, x0, y0, dx, dy, hw):
                if e.hit(dmg, e.x - dy * 0, e.y + 3, silent=(w.t % 6 != 0)) and w.t % 4 == 0:
                    w.fx.spark_burst(e.x, e.y + 4, 2, (255, 210, 120), 3, 10, 2.0, ang + math.pi)
        self.beams.append((x0, y0, ang, length, hw))

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        self.beams = []
        nx, ny = p.x, p.y - 13
        if self.mode == 0:          # RAYON
            if firing:
                hw = 2.5 + 0.7 * lv
                self.beam(nx, ny, -math.pi / 2, hw, dps(lv) / 60 * 0.95)
                w.audio.loop("laser_loop", True, 0.75, nx)
            else:
                w.audio.loop("laser_loop", False)
        elif self.mode == 1:        # ÉVENTAIL
            if firing and self.cool <= 0:
                self.cool = 6
                angs = [-10, 0, 10] if lv < 2 else [-20, -7, 7, 20] if lv < 4 else [-26, -13, 0, 13, 26]
                dmg = dps(lv) * 6 / 60 / len(angs) * 1.15
                for a in angs:
                    r = math.radians(a) - math.pi / 2
                    w.add_shot(Streak(w, nx, ny, math.cos(r) * 10, math.sin(r) * 10, dmg, None, 3, True, 40))
                w.audio.play("laser", nx, 0.5, throttle=6)
        else:                       # COURONNE
            if firing:
                amp = 0.55 + 0.05 * lv
                n = 1 if lv < 3 else 2
                s = math.sin(self.t * 0.06)
                hw = 2 + 0.4 * lv
                dmg = dps(lv) / 60 * 0.85 / n * (1.35 if n == 2 else 1.0)
                self.beam(nx, ny, -math.pi / 2 + s * amp, hw, dmg)
                if n == 2:
                    self.beam(nx, ny, -math.pi / 2 - s * amp, hw, dmg)
                w.audio.loop("laser_loop", True, 0.7, nx)
            else:
                w.audio.loop("laser_loop", False)

    def draw_add(self, add):
        t = self.t
        for (x0, y0, ang, ln, hw) in self.beams:
            dx, dy = math.cos(ang), math.sin(ang)
            x1, y1 = x0 + dx * ln, y0 + dy * ln
            fl = 1 + 0.25 * math.sin(t * 0.9)
            pygame.draw.line(add, (110, 50, 5), (x0, y0), (x1, y1), int(hw * 2 * fl + 6))
            pygame.draw.line(add, (230, 140, 30), (x0, y0), (x1, y1), int(hw * 2 * fl + 1))
            pygame.draw.line(add, (255, 240, 170), (x0, y0), (x1, y1), max(1, int(hw * fl)))
            pygame.draw.line(add, (255, 255, 255), (x0, y0), (x1, y1), 1)
            g = glow(int(7 + hw), (255, 170, 50), 0.8)
            add.blit(g, (int(x0 - g.get_width() // 2), int(y0 - g.get_height() // 2)), special_flags=pygame.BLEND_ADD)


class Artemis(Weapon):
    god = "artemis"

    def __init__(self, w, p):
        super().__init__(w, p)
        self.moon_t = 0

    def nmoons(self):
        lv = self.lv
        return 2 if lv < 3 else 3 if lv < 5 else 4

    def moon_pos(self, i, n):
        a = self.moon_t * 0.07 + i * TAU / n
        return self.p.x + math.cos(a) * 21, self.p.y + math.sin(a) * 17

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        nx, ny = p.x, p.y - 12
        self.moon_t += 1
        if self.mode == 0:          # CHASSE
            if firing and self.cool <= 0:
                self.cool = 9
                n = 2 + lv // 2
                spread = math.radians(20 + 5 * n)
                dmg = dps(lv) * 9 / 60 / n * 1.05
                for i in range(n):
                    a = -math.pi / 2 - spread + 2 * spread * (i + 0.5) / n
                    pr = Proj(w, nx, ny, math.cos(a) * 5.2, math.sin(a) * 5.2, dmg, None, 3, False, 100,
                              frames=S["arrow"], trail=(60, 120, 90))
                    pr.homing = True
                    pr.turn = 0.09
                    w.add_shot(pr)
                w.audio.play("arrow", nx, 0.7, throttle=8)
        elif self.mode == 1:        # VOLÉE
            if firing and self.cool <= 0:
                self.cool = 5
                n = 3 + lv
                spread = math.radians(24 + 5 * lv)
                dmg = dps(lv) * 5 / 60 / n * 1.25
                for i in range(n):
                    a = -math.pi / 2 - spread / 2 + spread * i / (n - 1)
                    w.add_shot(Proj(w, nx, ny, math.cos(a) * 8.5, math.sin(a) * 8.5, dmg, None, 3, False, 60,
                                    frames=S["arrow"]))
                w.audio.play("arrow", nx, 0.55, throttle=5)
        else:                       # LUNES
            n = self.nmoons()
            if firing and self.cool <= 0:
                self.cool = 14
                dmg = dps(lv) * 14 / 60 / n * 1.15
                for i in range(n):
                    mx, my = self.moon_pos(i, n)
                    pr = Proj(w, mx, my, 0, -6, dmg, None, 3, False, 90, frames=S["dart"], trail=(40, 90, 70))
                    pr.homing = True
                    pr.turn = 0.15
                    w.add_shot(pr)
                w.audio.play("arrow", p.x, 0.4, throttle=10)

    def draw(self, surf):
        if self.mode == 2:
            n = self.nmoons()
            for i in range(n):
                x, y = self.moon_pos(i, n)
                S["moon"].draw(surf, x, y)

    def draw_add(self, add):
        if self.mode == 2:
            n = self.nmoons()
            for i in range(n):
                x, y = self.moon_pos(i, n)
                S["moon"].draw_halo(add, x, y)


class Poseidon(Weapon):
    god = "poseidon"

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        nx, ny = p.x, p.y - 12
        if self.mode == 0:           # TRIDENT
            if firing and self.cool <= 0:
                self.cool = 11
                angs = [-14, 0, 14] if lv < 3 else [-28, -14, 0, 14, 28]
                dmg = dps(lv) * 11 / 60 / len(angs) * 1.3
                for a in angs:
                    r = math.radians(a) - math.pi / 2
                    w.add_shot(Wave(w, nx, ny, math.cos(r) * 4.8, math.sin(r) * 4.8, dmg, None, 6, True, 70,
                                    frames=S["wave"], cd=10))
                w.audio.play("wave", nx, 0.6, throttle=10)
        elif self.mode == 1:         # MARÉE
            if firing and self.cool <= 0:
                self.cool = 4
                dmg = dps(lv) * 4 / 60 / 2 * 1.0
                for ph in (0.0, math.pi):
                    pr = Tide(w, nx, ny, 0, -6.2, dmg, S["tide"], 4, True, 60, cd=12)
                    pr.data = (nx, ph, 12 + 2 * lv)
                    w.add_shot(pr)
                if self.t % 12 == 0:
                    w.audio.play("wave", nx, 0.35, throttle=12)
        else:                        # ABYSSE
            if firing and self.cool <= 0:
                self.cool = 20
                angs = [0] if lv < 3 else [-10, 10]
                for a in angs:
                    r = math.radians(a) - math.pi / 2
                    pr = Abyss(w, nx, ny, math.cos(r) * 3.2, math.sin(r) * 3.2, 0, S["abyss"], 5, False, 44)
                    pr.data = (20 + 3 * lv, dps(lv) * 20 / 60 / len(angs) * 1.45 / 16)
                    w.add_shot(pr)
                w.audio.play("wave", nx, 0.6, throttle=10)


class Athena(Weapon):
    god = "athena"

    def __init__(self, w, p):
        super().__init__(w, p)
        self.shields = []
        self.spear_cd = 0

    def set_mode(self, m):
        super().set_mode(m)
        self.shields = []

    def count(self):
        lv = self.lv
        if self.mode == 1:
            return 3 + lv // 2
        return 2 + lv // 2

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        if self.spear_cd > 0:
            self.spear_cd -= 1
        if self.mode in (0, 1):
            n = self.count()
            while len(self.shields) < n:
                self.shields.append(Aegis(w, p.x, p.y))
            self.shields = self.shields[:n]
            for i, s in enumerate(self.shields):
                if self.mode == 0:
                    a = self.t * 0.085 + i * TAU / n
                    tx, ty = p.x + math.cos(a) * 21, p.y + math.sin(a) * 21
                else:
                    span = 8 + 5 * n
                    tx = p.x - span + 2 * span * i / max(1, n - 1)
                    ty = p.y - 19 + abs(i - (n - 1) / 2) * 2.5
                s.x += (tx - s.x) * 0.5
                s.y += (ty - s.y) * 0.5
                s.block()
                s.contact(dps(lv) / 60 * 3.0)
            if firing and self.spear_cd <= 0 and (self.mode == 1 or lv >= 1):
                self.spear_cd = 12 if self.mode == 0 else 7
                dmg = dps(lv) * self.spear_cd / 60 / n * (0.7 if self.mode == 0 else 1.05)
                for s in self.shields:
                    w.add_shot(Proj(w, s.x, s.y - 5, 0, -8, dmg, S["spear"], 3, False, 50))
                w.audio.play("clang", p.x, 0.25, throttle=14)
        else:                        # JAVELOT
            nmax = 2 + lv // 2
            if firing and self.cool <= 0 and len(self.shields) < nmax:
                self.cool = 16
                s = Aegis(w, p.x, p.y - 12)
                s.thrown = True
                s.vy = -7.2
                s.vx = (len(self.shields) % 2 * 2 - 1) * 0.6
                self.shields.append(s)
                w.audio.play("clang", p.x, 0.5, throttle=6)
            keep = []
            for s in self.shields:
                s.t += 1
                if not s.returning:
                    s.vy += 0.24
                    s.x += s.vx
                    s.y += s.vy
                    if s.vy >= 0 or s.y < 10:
                        s.returning = True
                else:
                    a = math.atan2(p.y - s.y, p.x - s.x)
                    sp = min(9.0, 3 + s.t * 0.08)
                    s.x += math.cos(a) * sp
                    s.y += math.sin(a) * sp
                    if (s.x - p.x) ** 2 + (s.y - p.y) ** 2 < 100:
                        continue
                s.block()
                s.contact(dps(lv) * 16 / 60 * 0.45, cd=8)
                keep.append(s)
            self.shields = keep

    def draw(self, surf):
        for s in self.shields:
            s.draw(surf)

    def draw_add(self, add):
        for s in self.shields:
            s.draw_add(add)


class Hephaestus(Weapon):
    god = "hephaestus"

    def stop(self):
        self.w.audio.loop("flame_loop", False)

    def draw_add(self, add):
        Weapon.draw_add(self, add)
        if self.mode == 0 and self.p.firing and not self.p.dead:
            k = 0.8 + 0.2 * math.sin(self.t * 1.7)
            g = glow(10, (int(170 * k), int(80 * k), 10), 0.4)
            add.blit(g, (int(self.p.x - 10), int(self.p.y - 23)), special_flags=pygame.BLEND_ADD)

    def update(self, firing):
        super().update(firing)
        w, p, lv = self.w, self.p, self.lv
        nx, ny = p.x, p.y - 12
        if self.mode == 0:            # FORGE
            if firing:
                if self.cool <= 0:
                    self.cool = 2
                    spread = 0.18 + 0.025 * lv
                    dmg = dps(lv) * 2 / 60 / 3 * 1.45
                    for _ in range(3):
                        a = -math.pi / 2 + random.uniform(-spread, spread)
                        sp = random.uniform(5.2, 6.4)
                        w.add_shot(Flame(w, nx, ny, math.cos(a) * sp, math.sin(a) * sp, dmg, None, 3, True,
                                         17 + lv, cd=99))
                w.audio.loop("flame_loop", True, 0.8, nx)
            else:
                w.audio.loop("flame_loop", False)
        elif self.mode == 1:          # MORTIER
            if firing and self.cool <= 0:
                self.cool = 18
                angs = [0] if lv < 3 else [-8, 8] if lv < 5 else [-12, 0, 12]
                dmg = dps(lv) * 18 / 60 / len(angs) * 1.35
                for a in angs:
                    r = math.radians(a) - math.pi / 2
                    sh = Shell(w, nx, ny, math.cos(r) * 5, math.sin(r) * 5, dmg, S["shell"], 4, False, 42,
                               trail=(160, 80, 20))
                    sh.data = 20 + 3 * lv
                    w.add_shot(sh)
                w.audio.play("mortar", nx, 0.7, throttle=6)
        else:                         # MÉTÉORE
            if firing and self.cool <= 0:
                self.cool = 24
                dmg = dps(lv) * 24 / 60 * 0.55
                m = Meteor(w, nx, ny, 0, -3.8, dmg, S["meteor"], 7, True, 80, cd=10)
                m.data = 6 + lv
                w.add_shot(m)
                w.audio.play("mortar", nx, 0.8, throttle=6)


WEAPON_CLASSES = {"zeus": Zeus, "apollo": Apollo, "artemis": Artemis, "poseidon": Poseidon, "athena": Athena,
                  "hephaestus": Hephaestus}


# ---------------------------------------------------------------------------
# Théophanies (bombes)
# ---------------------------------------------------------------------------
class Bomb:
    DUR = 150

    def __init__(self, w, god):
        self.w = w
        self.god = god
        self.t = 0
        self.alive = True
        self.p = w.player
        self.x0, self.y0 = self.p.x, self.p.y
        self.strikes = []
        self.col = P.GOD_COLORS.get(god, (255, 255, 255)) if god else (255, 255, 255)
        w.bullets.cancel(True)
        w.juice.flash(self.col, 0.9, 0.05)
        w.juice.shake(0.6)
        w.juice.aberr(4)
        w.audio.play("bomb")
        w.fx.ring(self.x0, self.y0, 4, 200, 40, self.col, 5)
        w.fx.ring(self.x0, self.y0, 2, 140, 30, (255, 255, 255), 3, delay=4)

    def update(self):
        w = self.w
        self.t += 1
        t = self.t
        if t < 100:
            w.bullets.cancel(True)
        # dégâts continus
        if t % 3 == 0 and t < 130:
            for e in w.targets:
                e.hit(1.5 * 3 if not e.BOSSPART else 0.45 * 3, e.x, e.y, silent=True)
        g = self.god
        rnd = random.random
        if g == "zeus":
            if t % 7 == 1 and t < 110:
                tg = w.random_target()
                x = tg.x if tg and rnd() < 0.7 else rnd() * PF_W
                y = tg.y if tg and rnd() < 0.7 else rnd() * PF_H * 0.8
                self.strikes.append([x, y, 6])
                w.fx.explosion(x, y, 0.8, grad=P.PLASMA, smoke_on=False)
                w.juice.flash((180, 200, 255), 0.35, 0.1)
                w.audio.play("lightning", x, 0.8, throttle=6)
            if t == 2:
                w.audio.play("thunder")
        elif g == "apollo":
            if t % 2 == 0 and t < 120:
                for _ in range(3):
                    a = rnd() * TAU
                    w.fx.add(Particle(K_STREAK, self.p.x + math.cos(a) * 10, self.p.y + math.sin(a) * 10,
                                      math.cos(a) * 7, math.sin(a) * 7, 24, 4, 2, (255, 200, 80)))
        elif g == "artemis":
            if t % 2 == 0 and t < 100:
                for _ in range(2):
                    x = rnd() * PF_W
                    pr = Proj(w, x, -10, rnd() - 0.5, 7.5, 6, None, 3, False, 60, frames=S["arrow"],
                              rbase=-math.pi / 2)
                    pr.homing = True
                    pr.turn = 0.08
                    w.add_shot(pr)
        elif g == "poseidon":
            yw = PF_H - t * 2.4
            if t % 2 == 0 and yw > -20:
                for _ in range(6):
                    x = rnd() * PF_W
                    w.fx.add(Particle(K_GLOW, x, yw + rnd() * 10, (rnd() - 0.5) * 2, -2 - rnd() * 2, 22, 5, 1,
                                      (80, 230, 255)))
        elif g == "athena":
            pass
        elif g == "hephaestus":
            if t % 5 == 0 and t < 110:
                x = rnd() * PF_W
                w.fx.explosion(x, PF_H * (0.2 + rnd() * 0.7), 1.1)
                w.audio.play("explo_s", x, 0.6, throttle=4)
                for _ in range(4):
                    w.fx.add(Particle(K_FIRE, x, PF_H + 5, (rnd() - 0.5) * 2, -6 - rnd() * 5, 30, 5, 12,
                                      grad=P.FIRE, drag=0.97))
        else:
            if t < 60 and t % 10 == 0:
                w.fx.ring(self.p.x, self.p.y, 4, 160, 30, (255, 255, 255), 3)
        self.strikes = [[x, y, n - 1] for (x, y, n) in self.strikes if n > 1]
        if t >= self.DUR:
            self.alive = False

    def draw_add(self, add):
        t = self.t
        g = self.god
        k = max(0.0, 1 - t / self.DUR)
        if g == "zeus":
            for (x, y, n) in self.strikes:
                draw_bolt_tree(add, x + random.uniform(-20, 20), -10, x, y, (140, 180, 255), 14, 3)
        elif g == "apollo":
            p = self.p
            wdt = int(60 * math.sin(min(1.0, t / 20) * math.pi / 2) * k + 4)
            pygame.draw.rect(add, (int(120 * k), int(60 * k), 0), (int(p.x - wdt), 0, wdt * 2, int(p.y)))
            pygame.draw.rect(add, (int(255 * k), int(180 * k), int(60 * k)), (int(p.x - wdt * 0.6), 0,
                                                                                int(wdt * 1.2), int(p.y)))
            pygame.draw.rect(add, (int(255 * k), int(255 * k), int(220 * k)), (int(p.x - wdt * 0.25), 0,
                                                                                 max(1, int(wdt * 0.5)), int(p.y)))
            gg = glow(40, (int(200 * k), int(120 * k), int(20 * k)), 0.6 * k)
            add.blit(gg, (int(p.x - 40), int(p.y - 40)), special_flags=pygame.BLEND_ADD)
        elif g == "poseidon":
            yw = PF_H - t * 2.4
            if yw > -30:
                c = (int(30 * k), int(150 * k), int(190 * k))
                pygame.draw.rect(add, (int(8 * k), int(40 * k), int(60 * k)), (0, int(yw), PF_W, PF_H))
                pts = [(x, yw + math.sin(x * 0.08 + t * 0.3) * 6) for x in range(0, PF_W + 8, 8)]
                pygame.draw.lines(add, c, False, pts, 4)
                pygame.draw.lines(add, (int(200 * k), int(255 * k), int(255 * k)), False, pts, 1)
        elif g == "athena":
            p = self.p
            r = int(min(1.0, t / 30) * 150)
            c = (int(120 * k), int(100 * k), int(40 * k))
            pygame.draw.circle(add, c, (int(p.x), int(p.y)), r, 4)
            pygame.draw.circle(add, (int(60 * k), int(50 * k), int(20 * k)), (int(p.x), int(p.y)), max(1, r - 10), 2)
            gg = glow(min(90, r), (int(60 * k), int(50 * k), int(20 * k)))
            add.blit(gg, (int(p.x - gg.get_width() // 2), int(p.y - gg.get_height() // 2)), special_flags=pygame.BLEND_ADD)
        elif g == "artemis":
            gg = glow(30, (int(40 * k), int(80 * k), int(70 * k)), 0.4 * k)
            add.blit(gg, (PF_W // 2 - 30, 10), special_flags=pygame.BLEND_ADD)

    def draw(self, surf):
        if self.god == "athena" and self.t < 110:
            # la Gorgone sur l'égide pétrifie les ennemis : voile gris
            for e in self.w.targets:
                if not e.BOSSPART:
                    spr = e.sprite()
                    if spr is not None and self.t % 6 < 3:
                        spr.draw(surf, e.x, e.y, True)
