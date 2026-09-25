"""Boss des stades IV (Kyklopes, Talos), V (Charon, Kerberos) et VI (Nikè, Zeus-Ω)."""
import math
import random

import pygame

from . import palette as P
from .bosses import Boss, Part, bs
from .entities import move_to, PF_W, PF_H
from .enemies import Hazard, Eagle
from .spritegen import (L, forge, circle, ellipse, rect, line, polyline, arc, sym, Sprite)
from .fx import glow, Particle, K_FIRE, bolt_points, draw_bolt
from .util import TAU, clamp, ease_out_cubic, ease_in_cubic


def flipped(name, base):
    return bs(name, lambda: Sprite(pygame.transform.flip(base.img, True, False),
                                   pygame.transform.flip(base.flash, True, False),
                                   pygame.transform.flip(base.shadow, True, False) if base.shadow else None,
                                   pygame.transform.flip(base.halo, True, False) if base.halo else None,
                                   base.w - base.ox, base.oy, base.hox - base.ox))


# ===========================================================================
# STADE IV — KYKLOPES (gardiens) : Brontès, Stéropès, Argès
# ===========================================================================
def _kyk_platform():
    return forge(171, 67, [
        L([[(-82, -18), (82, -18), (76, 22), (-76, 22)]], mat=P.OBSIDIAN, bevel=3, noise=0.05),
        L([rect(-78, -14, 78, -9), rect(-72, 14, 72, 18)], mat=P.BRONZE, bevel=1, clip=True, cast=False),
        L(polyline([(-70, 6), (-40, 2), (-12, 8), (20, 0), (50, 6), (72, 2)], 1.8), emit=(255, 110, 30), glow=1.0),
        L([rect(-16, -10, 16, 4), rect(-22, -4, 22, 0)], mat=P.DARKSTEEL, bevel=2, spec=0.5),
    ], halo=4, want_shadow=True)


def _kyk_head(col):
    return forge(41, 41, [
        L([circle(0, 0, 16)], mat=P.BRONZE, profile="round", spec=0.4),
        L([sym([(0, -17), (6, -15), (4, -6), (0, -5)])], mat=P.GOLD, bevel=1),
        L([ellipse(0, 3, 10, 8)], mat=P.MARBLE, profile="round", base=0.66),
        L([circle(0, 3, 5)], emit=col, glow=1.6),
        L([ellipse(0, 3, 1.6, 4)], flat=(10, 8, 12)),
        L([arc(0, 3, 10, 12.5, math.pi + 0.3, TAU - 0.3)], mat=P.DARKSTEEL, bevel=1),
    ], halo=4, want_shadow=True)


def _hammer():
    return forge(25, 41, [
        L([rect(-2, -18, 2, 8)], mat=P.BRONZE, bevel=1),
        L([rect(-10, 6, 10, 18)], mat=P.DARKSTEEL, bevel=2, spec=0.5),
        L([rect(-10, 15, 10, 18)], emit=(255, 140, 50), glow=0.6),
    ], halo=2)


class KykHead(Part):
    OWNER_DRAWS = True
    HP = 170
    SCORE = 6000
    RADIUS = 14
    EXPLO = 1.2
    counts = True
    NAMES = ("brontes", "steropes", "arges")
    COLS = ((110, 170, 255), (255, 240, 150), (255, 150, 60))

    def setup(self, owner=None, idx=0, **kw):
        Part.setup(self, owner=owner, dx=(idx - 1) * 56, dy=-8)
        self.idx = idx
        self.spr = bs(f"kyk{idx}", lambda: _kyk_head(self.COLS[idx]))
        self.ham = 0.0

    def draw(self, surf):
        Part.draw(self, surf)
        hy = self.y + 18 - self.ham * 16
        S_ = bs("hammer", _hammer)
        S_.draw(surf, self.x + 20, hy)


class Kyklopes(Boss):
    NAME = "ΚΥΚΛΩΠΕΣ · LES CYCLOPES"
    CARD = ("ΚΥΚΛΩΠΕΣ", "BRONTÈS · STÉROPÈS · ARGÈS")
    HP = 1
    SCORE = 25000
    MID = True
    RADIUS = 1
    BODY = False
    EXPLO = 2.2

    def setup(self, **kw):
        self.spr = bs("kyk_plat", _kyk_platform)
        self.heads = [self.add_part(KykHead(self.w, self.x, self.y, owner=self, idx=i)) for i in range(3)]

    def targetable(self):
        return False

    def hp_frac(self):
        return sum(max(0, h.hp) for h in self.heads if not h.dead) / sum(h.max_hp for h in self.heads)

    def part_died(self, p):
        if all(h.dead for h in self.heads):
            self.die()

    def death_span(self):
        return (70, 16)

    def sprite(self):
        return self.spr

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 58, 120, ease_out_cubic)
        self.entered_fight = True
        k = 0
        while True:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.01) * 26
            for h in self.heads:
                if h.dead:
                    continue
                ph = (k + h.idx * 50) % int(150 / w.diff["rate"])
                h.ham = min(1.0, ph / 40) if ph < 40 else max(0.0, 1 - (ph - 40) / 4)
                if ph == 44 and self.can_fire():
                    # coup de marteau sur l'enclume
                    w.juice.shake(0.25)
                    w.audio.play("clang", h.x, 0.8)
                    w.fx.spark_burst(h.x + 20, h.y + 30, 12, (255, 200, 120), 4, 16)
                    self.ring(h.x + 20, h.y + 30, 12, 1.5, "s", "orange", off=k * 0.1)
                if h.idx == 0 and k % int(90 / w.diff["rate"]) == 30 and self.can_fire():
                    self.ring(h.x, h.y + 4, 18, 1.3, "m", "blue", off=k * 0.05)
                    w.audio.play("eshot_big", h.x)
                if h.idx == 1 and k % int(40 / w.diff["rate"]) == 10 and self.can_fire():
                    self.spread(h.x, h.y + 4, 3, 0.3, 3.0, "needle", "gold")
                    w.audio.play("zap", h.x, 0.5, throttle=6)
                if h.idx == 2 and k % int(170 / w.diff["rate"]) == 80 and self.can_fire():
                    a = self.aim_from(h.x, h.y)
                    w.hazards.append(Hazard(w, h.x, h.y + 4, h.x + math.cos(a) * 400, h.y + math.sin(a) * 400,
                                            10, 45, 36, (255, 160, 70), owner=h))
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y + 8, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y + 8)


# ===========================================================================
# STADE IV — TALOS, le géant de bronze
# ===========================================================================
def _talos_body():
    return forge(231, 131, [
        L([[(-110, -40), (-60, -56), (60, -56), (110, -40), (100, 10), (60, 30), (-60, 30), (-100, 10)]],
          mat=P.BRONZE, bevel=4, spec=0.35, base=0.5),
        L([circle(x, y, 2.2) for x in (-90, -70, 70, 90) for y in (-36, -20, -4)], mat=P.GOLD, profile="round"),
        L([rect(-100, -44, 100, -38)], mat=P.GOLD, bevel=1, clip=True, cast=False),
        L([[(-40, -10), (40, -10), (32, 34), (-32, 34)]], mat=P.BRONZE, bevel=3, base=0.42),
        L([rect(-24, 0, 24, 26)], mat=P.DARKSTEEL, bevel=2),
        L([rect(-22 + i * 6, 2, -19 + i * 6, 24) for i in range(8)], mat=P.BRONZE, bevel=1, base=0.5),
        L([sym([(0, -62), (16, -58), (22, -44), (20, -26), (12, -16), (0, -12)])], mat=P.BRONZE, bevel=3, spec=0.4),
        L([sym([(0, -66), (3, -64), (3, -40), (0, -38)])], mat=P.RED, bevel=1),
        L([rect(-16, -46, 16, -40)], mat=P.EBONY, bevel=1),
        L([ellipse(-8, -43, 4.5, 2.2), ellipse(8, -43, 4.5, 2.2)], emit=(255, 200, 90), glow=1.6),
        L(polyline([(0, -12), (-6, 10), (4, 30), (-2, 50)], 1.4), emit=(255, 190, 60), glow=0.8),
    ], halo=5, want_shadow=True)


def _talos_fist():
    return forge(57, 51, [
        L([rect(-10, -24, 10, -8)], mat=P.BRONZE, bevel=2),
        L([[(-22, -10), (22, -10), (24, 14), (16, 22), (-16, 22), (-24, 14)]], mat=P.BRONZE, bevel=3, spec=0.4),
        L([rect(-20 + i * 10.5, 14, -12 + i * 10.5, 22) for i in range(4)], mat=P.BRONZE, bevel=1.5, base=0.66),
        L([line(-18, 2, 18, 2, 1.2)], emit=(255, 170, 60), glow=0.8),
    ], halo=3, want_shadow=True)


def _furnace_open():
    return forge(51, 31, [
        L([rect(-22, -12, 22, 12)], emit=(255, 150, 40), glow=1.4),
        L([ellipse(0, 0, 14, 8)], emit=(255, 230, 140), glow=1.4),
        L([circle(0, 0, 4)], emit=(255, 255, 240), glow=1.0),
    ], outline=(40, 10, 6), halo=5)


class TalosFist(Part):
    OWNER_DRAWS = True
    HP = 380
    SCORE = 8000
    RADIUS = 18
    EXPLO = 1.5
    counts = True
    BODY = True

    def setup(self, owner=None, side=1, **kw):
        Part.setup(self, owner=owner)
        self.side = side
        base = bs("tfist", _talos_fist)
        self.spr = base if side > 0 else flipped("tfistL", base)
        self.home = (side * 88, 38)
        self.slam = None
        self.shadow_r = 0

    def update(self):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.flash_cd > 0:
            self.flash_cd -= 1
        o = self.owner
        if o.dead:
            self.dead = True
            return
        if self.brain is not None:
            try:
                next(self.brain)
            except StopIteration:
                self.brain = None
        if self.slam is None:
            hx, hy = o.x + self.home[0], o.y + self.home[1] + math.sin(o.t * 0.05 + self.side) * 4
            self.x += (hx - self.x) * 0.12
            self.y += (hy - self.y) * 0.12
        self.hitboxes = [(0, 4, 20, 16)]

    def behave(self):
        while True:
            if self.slam is not None:
                yield from self.do_slam(*self.slam)
                self.slam = None
            yield

    def do_slam(self, tx, ty):
        w = self.w
        # survol
        for i in range(30):
            self.x += (tx - self.x) * 0.15
            self.y += (40 - self.y) * 0.15
            self.shadow_r = int(6 + i * 0.6)
            yield
        for i in range(22):
            self.shadow_r = 24
            yield
        # chute
        while self.y < ty:
            self.y += 11
            yield
        self.shadow_r = 0
        w.juice.shake(0.6)
        w.audio.play("explo_m", self.x)
        w.fx.ring(self.x, self.y + 16, 6, 70, 26, (255, 180, 100), 4)
        w.fx.spark_burst(self.x, self.y + 16, 14, (255, 200, 120), 5, 18)
        if self.can_fire() or self.y > PF_H - 50:
            w.bullets.ring(self.x, min(self.y + 10, PF_H - 30), w.bullets.dens(16), 1.6, "m", "orange",
                           offset=random.random())
        for i in range(24):
            yield
        for i in range(40):
            self.y -= 4
            yield

    def draw_add(self, add):
        Part.draw_add(self, add)
        if self.shadow_r:
            tx = self.x
            pygame.draw.circle(add, (90, 20, 10), (int(tx), int(self.owner.slam_y)), self.shadow_r, 2)


class Talos(Boss):
    NAME = "ΤΑΛΩΣ · LE GÉANT DE BRONZE"
    CARD = ("ΤΑΛΩΣ", "LE GÉANT DE BRONZE")
    HP = 2100
    RADIUS = 20

    def setup(self, **kw):
        self.spr = bs("talos", _talos_body)
        self.furn = bs("furnace", _furnace_open)
        self.fists = [self.add_part(TalosFist(self.w, self.x, self.y, owner=self, side=s)) for s in (-1, 1)]
        self.open = False
        self.hitboxes = [(0, 12, 24, 14)]
        self.slam_y = 200

    def ARMOR_NOW(self):
        return not self.open

    def sprite(self):
        return self.spr

    def death_span(self):
        return (90, 40)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 70, 170, ease_out_cubic)
        w.audio.play("roar", self.x)
        w.juice.shake(0.6)
        self.entered_fight = True
        while True:
            f = self.hp / self.max_hp
            yield from self.slams(2 if f > 0.5 else 3)
            yield from self.eye_beams()
            yield from self.furnace(1.0 if f > 0.4 else 1.5)

    def drift(self):
        self.x = PF_W / 2 + math.sin(self.t * 0.01) * 16
        self.y = 70 + math.sin(self.t * 0.02) * 3

    def collide(self, x, y, r):
        # corps de bronze (les tirs ricochent) ; le cœur n'est touchable que fourneau ouvert
        if self.open:
            return abs(x - self.x) < 24 + r and abs(y - (self.y + 12)) < 14 + r
        return abs(x - self.x) < 60 + r and abs(y - (self.y - 10)) < 36 + r

    def slams(self, n):
        w = self.w
        fists = [fi for fi in self.fists if not fi.dead]
        if not fists:
            yield from self.furnace(1.2)
            return
        for i in range(n):
            fi = fists[i % len(fists)]
            if fi.dead:
                continue
            p = w.player
            self.slam_y = min(PF_H - 40, p.y)
            fi.slam = (p.x, self.slam_y - 16)
            for k in range(70):
                self.drift()
                if k % 20 == 10 and self.can_fire():
                    self.spread(self.x, self.y + 20, 3, 0.4, 2.2, "m", "pink")
                yield
        for k in range(50):
            self.drift()
            yield

    def eye_beams(self):
        w = self.w
        for side in (-1, 1):
            def track(side=side, s=[0]):
                s[0] += 1
                ex, ey = self.x + side * 8, self.y - 43
                a = math.pi / 2 + side * (0.9 - min(1.8, max(0.0, (s[0] - 40) / 60)))
                return ex, ey, ex + math.cos(a) * 420, ey + math.sin(a) * 420
            hz = Hazard(w, 0, 0, 0, 0, 9, 40, 90, (255, 200, 90), owner=self, track=track)
            hz.x0, hz.y0, hz.x1, hz.y1 = track()
            w.hazards.append(hz)
        for k in range(140):
            self.drift()
            yield

    def furnace(self, k_):
        w = self.w
        self.open = True
        w.audio.play("fire_burst", self.x)
        n = int(220 * k_)
        for k in range(n):
            self.drift()
            fx, fy = self.x, self.y + 12
            if k % 3 == 0 and self.can_fire():
                a = math.pi / 2 + math.sin(k * 0.05) * 0.8 + random.uniform(-0.15, 0.15)
                w.bullets.fire(fx, fy, a, random.uniform(1.4, 2.4), "l", "orange")
            if k % 7 == 0:
                w.fx.add(Particle(K_FIRE, fx + random.uniform(-10, 10), fy, random.uniform(-0.5, 0.5), 1.2, 22, 5, 10,
                                  grad=P.FIRE))
            if k % 45 == 20 and self.can_fire():
                # pluie de scories
                for _ in range(w.bullets.dens(5)):
                    w.bullets.fire(random.uniform(10, PF_W - 10), -6, math.pi / 2 + random.uniform(-0.2, 0.2),
                                   random.uniform(1.2, 2.0), "s", "red")
            if k % 30 == 0:
                w.audio.play("fire_burst", fx, 0.5, throttle=10)
            yield
        self.open = False
        for k in range(40):
            self.drift()
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0 and self.open)
        if self.open:
            self.furn.draw(surf, self.x, self.y + 13)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        if self.open:
            self.furn.draw_halo(add, self.x, self.y + 13)


# ===========================================================================
# STADE V — CHARON, le passeur
# ===========================================================================
def _charon():
    return forge(71, 121, [
        L([sym([(0, -56), (10, -50), (18, -30), (20, 0), (18, 30), (10, 48), (0, 58)])], mat=P.EBONY, bevel=3,
          base=0.55, rim=(P.GREEN_E, 0.4)),
        L([sym([(0, -48), (7, -44), (13, -26), (14, 0), (12, 28), (6, 42), (0, 48)])], mat=P.OBSIDIAN, bevel=2,
          base=0.45),
        L([rect(-14, y, 14, y + 1.2) for y in range(-36, 40, 8)], mat=P.BRONZE, bevel=1, clip=True, cast=False),
        L([ellipse(0, 54, 6, 5)], mat=P.BONE, profile="round"),
        L([circle(-2, 55, 1), circle(2, 55, 1)], emit=P.GREEN_E, glow=1.2),
        L([sym([(0, -50), (7, -46), (9, -36), (6, -28), (0, -26)])], mat=P.PURPLE, bevel=2, base=0.4),
        L([ellipse(0, -40, 4, 5)], mat=P.BONE, profile="round", base=0.5),
        L([circle(-1.6, -41, 0.9), circle(1.6, -41, 0.9)], emit=P.GREEN_E, glow=1.4),
        L([line(8, -40, 26, 30, 1.6)], mat=P.BRONZE, bevel=1),
        L([circle(26, 30, 3.4)], emit=(120, 255, 170), glow=1.8),
    ], halo=5, want_shadow=True)


class Charon(Boss):
    NAME = "ΧΑΡΩΝ · LE PASSEUR"
    CARD = ("ΧΑΡΩΝ", "LE PASSEUR DU STYX")
    HP = 950
    SCORE = 25000
    MID = True
    RADIUS = 16
    EXPLO = 2.0

    def setup(self, **kw):
        self.spr = bs("charon", _charon)
        self.hitboxes = [(0, 0, 14, 44)]

    def sprite(self):
        return self.spr

    def death_span(self):
        return (16, 44)

    def lantern(self):
        return self.x + 26, self.y + 30

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 70, 130, ease_out_cubic)
        self.entered_fight = True
        k = 0
        while k < 60 * 50:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.011) * 70
            self.y = 70 + math.sin(k * 0.017) * 12
            lx, ly = self.lantern()
            if k % int(100 / w.diff["rate"]) == 20 and self.can_fire():
                # âmes : s'échappent, flottent, puis fondent sur le joueur
                n = w.bullets.dens(8)
                for i in range(n):
                    a = i * TAU / n + k * 0.01
                    w.bullets.fire(lx, ly, a, 1.2, "l", "green", acc=-0.03, minspd=0.0, delay=0, retarget=0)
                for b in w.bullets.list[-n:]:
                    b.delay = 0
                w.audio.play("teleport", lx, 0.6)
                self.souls = w.bullets.list[-n:]
                self.soul_t = 0
            if getattr(self, "souls", None):
                self.soul_t += 1
                if self.soul_t == 50:
                    p = w.player
                    for b in self.souls:
                        if b.alive:
                            a = math.atan2(p.y - b.y, p.x - b.x)
                            b.ang = a
                            b.spd = 2.2 * w.diff["bspeed"]
                            b.acc = 0.0
                            b.curve = True
                    self.souls = None
            if k % int(70 / w.diff["rate"]) == 45 and self.can_fire():
                for side in (-1, 1):
                    w.bullets.arc(self.x + side * 16, self.y, math.pi / 2 + side * 0.9, w.bullets.dens(7), 1.2, 1.9,
                                  "rice", "violet")
                w.audio.play("eshot2", self.x)
            if k % int(120 / w.diff["rate"]) == 90 and self.can_fire():
                self.ring(self.x, self.y + 50, 16, 1.4, "m", "gold", off=k * 0.1)
                w.audio.play("coin", self.x, 0.8)
            yield
        self.entered_fight = False
        yield from move_to(self, self.x, -120, 90, ease_in_cubic)
        self.dead = True
        self.gone = True

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        lx, ly = self.lantern()
        k = 0.7 + 0.3 * math.sin(self.t * 0.2)
        g = glow(14, (int(40 * k), int(140 * k), int(80 * k)), 0.5)
        add.blit(g, (int(lx - 14), int(ly - 14)), special_flags=pygame.BLEND_ADD)


# ===========================================================================
# STADE V — KERBEROS
# ===========================================================================
def _kerb_body():
    spine = [[(-3, y), (0, y - 7), (3, y)] for y in range(-40, 2, 7)]
    collar = []
    for i in range(11):
        a = math.pi * (0.12 + 0.76 * i / 10)
        cx, cy = math.cos(a) * 38, 4 + math.sin(a) * 30
        nx, ny = math.cos(a), math.sin(a)
        collar.append([(cx - ny * 3, cy + nx * 3), (cx + nx * 9, cy + ny * 9), (cx + ny * 3, cy - nx * 3)])
    claws = []
    for sx in (-1, 1):
        for i in range(3):
            x = sx * (46 + i * 4)
            claws.append([(x - 1.2, 44), (x, 50), (x + 1.2, 44)])
    return forge(181, 131, [
        L(polyline([(0, -44), (10, -54), (4, -62), (-8, -60)], 3.2), mat=P.VERDIGRIS, bevel=1.5),
        L([circle(-8, -60, 3.5)], mat=P.VERDIGRIS, profile="round"),
        L([[(-56, 14), (-40, 18), (-40, 40), (-54, 46), (-62, 30)], [(56, 14), (40, 18), (40, 40), (54, 46), (62, 30)]],
          mat=P.OBSIDIAN, bevel=2, rim=(P.RED_E, 0.4)),
        L(claws, mat=P.BONE, bevel=1, cast=False),
        L([ellipse(0, -10, 48, 36)], mat=P.OBSIDIAN, profile="round", base=0.5, spec=0.3, rim=(P.RED_E, 0.45)),
        L([ellipse(-30, 6, 18, 13, 0.3), ellipse(30, 6, 18, 13, -0.3)], mat=P.BRONZE, bevel=2, spec=0.4),
        L(spine, mat=P.BRONZE, bevel=1),
        L(collar, mat=P.STEEL, bevel=1, spec=0.5),
        L([arc(0, 4, 30, 35, math.pi * 0.1, math.pi * 0.9)], mat=P.GOLD, bevel=1.5, spec=0.5),
        L([ellipse(0, 4, 11, 9)], mat=P.EBONY, bevel=1.5),
        L(polyline([(-6, -2), (-2, 4), (-6, 10)], 1.2) + polyline([(5, -3), (2, 5), (6, 11)], 1.2) +
          [circle(0, 4, 3.2)], emit=(255, 70, 40), glow=1.4),
    ], halo=5, want_shadow=True)


def _kerb_head(col):
    mane = [[(math.cos(a) * 15, -6 + math.sin(a) * 13), (math.cos(a) * 23, -6 + math.sin(a) * 20),
             (math.cos(a + 0.2) * 15, -6 + math.sin(a + 0.2) * 13)] for a in [math.pi * (1.05 + i * 0.1) for i in range(10)]]
    return forge(61, 67, [
        L(mane, mat=P.OBSIDIAN, bevel=1, rim=(col, 0.5)),
        L([ellipse(-14, -18, 5, 10, -0.35), ellipse(14, -18, 5, 10, 0.35)], mat=P.OBSIDIAN, bevel=1.5),
        L([sym([(0, -22), (12, -20), (19, -8), (18, 8), (12, 22), (7, 30), (0, 31)])], mat=P.OBSIDIAN, bevel=3,
          spec=0.4),
        L([sym([(0, -18), (6, -16), (8, -2), (0, 1)])], mat=P.BRONZE, bevel=1.5),
        L([ellipse(0, 23, 8, 7)], emit=col, glow=1.6),
        L([[(5, 17), (7.5, 26), (3.5, 22)], [(-5, 17), (-7.5, 26), (-3.5, 22)]], flat=(245, 236, 216)),
        L([ellipse(-9, 3, 3.4, 2.1, 0.35), ellipse(9, 3, 3.4, 2.1, -0.35)], emit=col, glow=1.8),
    ], halo=5, want_shadow=True)


class KerbHead(Part):
    OWNER_DRAWS = True
    HP = 460
    SCORE = 10000
    RADIUS = 14
    EXPLO = 1.5
    counts = True
    KINDS = ("fire", "bolt", "ice")
    COLS = ((255, 130, 40), (120, 170, 255), (220, 230, 255))

    def setup(self, owner=None, idx=0, **kw):
        Part.setup(self, owner=owner)
        self.idx = idx
        self.kind = self.KINDS[idx]
        self.spr = bs(f"kerb{idx}", lambda: _kerb_head(self.COLS[idx]))
        self.base_dx = (idx - 1) * 50
        self.hitboxes = [(0, 4, 16, 20)]

    def update(self):
        Part.update(self)
        o = self.owner
        self.x = o.x + self.base_dx + math.sin(o.t * 0.05 + self.idx * 2) * 5
        self.y = o.y + 40 - abs(self.idx - 1) * 10 + math.sin(o.t * 0.07 + self.idx) * 4

    def mouth(self):
        return self.x, self.y + 24


class Kerberos(Boss):
    NAME = "ΚΕΡΒΕΡΟΣ · CERBÈRE"
    CARD = ("ΚΕΡΒΕΡΟΣ", "LE GARDIEN DES ENFERS")
    HP = 1150
    RADIUS = 24

    def setup(self, **kw):
        self.spr = bs("kerb", _kerb_body)
        self.heads = [self.add_part(KerbHead(self.w, self.x, self.y, owner=self, idx=i)) for i in range(3)]
        self.hitboxes = [(0, -4, 50, 26)]

    def ARMOR_NOW(self):
        return any(not h.dead for h in self.heads)

    def sprite(self):
        return self.spr

    def death_span(self):
        return (56, 36)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 52, 170, ease_out_cubic)
        w.audio.play("roar", self.x)
        w.audio.play("roar", self.x, 0.6)
        w.juice.shake(0.6)
        self.entered_fight = True
        k = 0
        while True:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.009) * 34
            self.y = 52 + math.sin(k * 0.021) * 6
            heads = [h for h in self.heads if not h.dead]
            rate = w.diff["rate"] * (1.0 + (3 - len(heads)) * 0.25)
            for h in heads:
                mx, my = h.mouth()
                if h.kind == "fire" and k % int(90 / rate) < 24 and k % 3 == 0 and self.can_fire():
                    a = self.aim_from(mx, my) + random.uniform(-0.35, 0.35)
                    w.bullets.fire(mx, my, a, random.uniform(1.6, 2.6), "l", "orange")
                    if k % 12 == 0:
                        w.audio.play("fire_burst", mx, 0.5, throttle=8)
                if h.kind == "bolt" and k % int(110 / rate) == 55 and self.can_fire():
                    p = w.player
                    for dx in (-30, 0, 30):
                        x = clamp(p.x + dx, 10, PF_W - 10)
                        w.hazards.append(Hazard(w, mx, my, x, PF_H + 10, 7, 36, 16, (140, 180, 255), owner=h,
                                                kind="bolt"))
                if h.kind == "bolt" and k % int(40 / rate) == 5 and self.can_fire():
                    self.spread(mx, my, 3, 0.25, 3.1, "needle", "blue")
                if h.kind == "ice" and k % int(80 / rate) == 40 and self.can_fire():
                    n = w.bullets.dens(12)
                    for i in range(n):
                        a = i * TAU / n + k * 0.03
                        w.bullets.fire(mx, my, a, 2.4, "needle", "violet", acc=-0.06, minspd=0.0, delay=0)
                    for b in w.bullets.list[-n:]:
                        b.retarget = 2.6
                        b.delay = 0
                    self.ice = (w.bullets.list[-n:], 0)
                    w.audio.play("eshot2", mx)
            ice = getattr(self, "ice", None)
            if ice:
                bl, t = ice
                t += 1
                if t == 36:
                    p = w.player
                    for b in bl:
                        a = math.atan2(p.y - b.y, p.x - b.x)
                        b.ang = a
                        b.spd = 2.6 * w.diff["bspeed"]
                        b.acc = 0.0
                    self.ice = None
                else:
                    self.ice = (bl, t)
            if not heads:
                # le cœur exposé : hurlement et spirales
                if k % 4 == 0 and self.can_fire():
                    for j in range(3):
                        a = k * 0.07 + j * TAU / 3
                        w.bullets.fire(self.x, self.y + 8, a, 1.7, "rice", ("red", "blue", "violet")[j])
                if k % 80 == 0:
                    self.ring(self.x, self.y + 8, 24, 1.5, "m", "red", off=k * 0.01)
                    w.fx.ring(self.x, self.y + 8, 8, 120, 30, (255, 80, 80), 3)
                    w.audio.play("roar", self.x, 0.6, throttle=40)
                    w.juice.shake(0.3)
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        if not self.ARMOR_NOW():
            k = 0.6 + 0.4 * math.sin(self.t * 0.25)
            g = glow(18, (int(180 * k), int(30 * k), int(20 * k)), 0.6 * k)
            add.blit(g, (int(self.x - 18), int(self.y - 10)), special_flags=pygame.BLEND_ADD)


# ===========================================================================
# STADE VI — NIKÈ, la Victoire ailée (gardienne)
# ===========================================================================
def _nike():
    feathers = []
    for i in range(6):
        a = -0.35 + i * 0.16
        ln = 34 - abs(i - 2) * 2
        tip = (math.cos(a) * ln + 6, math.sin(a) * ln - 4)
        feathers.append([(6, -4), (tip[0] * 0.6, tip[1] * 0.6 + 3), tip, (tip[0] * 0.6 + 2, tip[1] * 0.6 - 3)])
    return forge(91, 71, [
        L(feathers, mat=P.GOLD, bevel=1.5, mirror=True, spec=0.5),
        L([sym([(0, -22), (6, -18), (8, -6), (10, 12), (14, 28), (0, 30)])], mat=P.MARBLE, bevel=2, base=0.68,
          veins=0.1),
        L([circle(0, -18, 5)], mat=P.MARBLE, profile="round", base=0.7),
        L([arc(0, -18, 4.5, 6.5, math.pi * 0.9, math.pi * 2.1)], mat=P.OLIVE, bevel=1),
        L([line(-12, -30, 14, 32, 1.4)], mat=P.GOLD, bevel=1),
        L([sym([(0, -34), (2.2, -28), (0, -26)])], mat=P.STEEL, bevel=1, clip=False),
        L([circle(0, -2, 2.4)], emit=(255, 240, 170), glow=1.4),
    ], halo=4, want_shadow=True)


class Nike(Boss):
    NAME = "ΝΙΚΗ · LA VICTOIRE"
    CARD = ("ΝΙΚΗ", "LA VICTOIRE AILÉE")
    HP = 1050
    SCORE = 25000
    MID = True
    RADIUS = 16
    EXPLO = 2.0

    def setup(self, **kw):
        self.spr = bs("nike", _nike)
        self.hitboxes = [(0, 0, 12, 24), (0, -2, 34, 8)]

    def sprite(self):
        return self.spr

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 70, 110, ease_out_cubic)
        self.entered_fight = True
        k = 0
        while k < 60 * 50:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.02) * 80
            self.y = 70 + math.sin(k * 0.04) * 26
            if k % int(60 / w.diff["rate"]) == 0 and self.can_fire():
                for side in (-1, 1):
                    w.bullets.arc(self.x + side * 24, self.y, math.pi / 2 + side * 0.4, w.bullets.dens(5), 0.8, 2.0,
                                  "feather")
                w.audio.play("eshot2", self.x)
            if k % int(90 / w.diff["rate"]) == 45 and self.can_fire():
                self.spread(self.x, self.y + 20, 1, 0, 4.2, "needle", "gold")
                self.spread(self.x, self.y + 20, 2, 0.12, 3.8, "needle", "gold")
                w.audio.play("arrow", self.x)
            if k % int(130 / w.diff["rate"]) == 100 and self.can_fire():
                self.ring(self.x, self.y, 14, 1.3, "star", "gold", off=k * 0.1)
                w.audio.play("eshot_big", self.x)
            yield
        self.entered_fight = False
        yield from move_to(self, self.x, -90, 80, ease_in_cubic)
        self.dead = True
        self.gone = True

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)


# ===========================================================================
# STADE VI — ZEUS-Ω
# ===========================================================================
def _zeus_face():
    curls = []
    for i in range(9):
        a = math.pi * 0.08 + i * math.pi * 0.105
        curls.append(circle(math.cos(a) * 42, 6 + math.sin(a) * 50, 8))
    hair = []
    for i in range(9):
        a = -math.pi * 0.08 - i * math.pi * 0.105
        hair.append(circle(math.cos(a) * 44, -4 + math.sin(a) * 40, 9))
    rays = []
    for i in range(13):
        a = math.pi * (1.08 + i * 0.07)
        w_ = 0.06
        rays.append([(math.cos(a - w_) * 40, -6 + math.sin(a - w_) * 44), (math.cos(a) * 70, -6 + math.sin(a) * 74),
                     (math.cos(a + w_) * 40, -6 + math.sin(a + w_) * 44)])
    tips = [circle(math.cos(math.pi * (1.08 + i * 0.07)) * 70, -6 + math.sin(math.pi * (1.08 + i * 0.07)) * 74, 1.6)
            for i in range(0, 13, 2)]
    return forge(171, 151, [
        L(rays, mat=P.GOLD, bevel=1, spec=0.6),
        L(tips, emit=(190, 220, 255), glow=1.2),
        L(hair, mat=P.GOLD, profile="round", spec=0.4),
        L(curls, mat=P.GOLD, profile="round", spec=0.4, base=0.55),
        L([ellipse(0, -2, 38, 46)], mat=P.MARBLE, profile="round", base=0.64, veins=0.1),
        L([[(-30, -14), (-6, -8), (-6, -4), (-32, -8)], [(30, -14), (6, -8), (6, -4), (32, -8)]], mat=P.MARBLE,
          bevel=1.5, base=0.45),
        L([ellipse(-16, 0, 8, 5), ellipse(16, 0, 8, 5)], mat=P.EBONY, bevel=1.5),
        L([ellipse(-16, 0, 5, 3.2), ellipse(16, 0, 5, 3.2)], emit=(170, 210, 255), glow=2.0),
        L([sym([(0, -6), (4, 14), (0, 17)])], mat=P.MARBLE, bevel=1.5, base=0.5),
        L([sym([(0, 20), (16, 22), (26, 34), (22, 50), (10, 62), (0, 66)])], mat=P.GOLD, bevel=2, spec=0.4),
        L([ellipse(0, 26, 10, 3)], mat=P.EBONY, bevel=1, clip=True, cast=False),
        L([line(-20 + i * 8, 34, -18 + i * 8, 58, 1.2) for i in range(6)], mat=P.BRONZE, bevel=1, clip=True,
          cast=False),
        L([circle(0, -58, 5)], emit=(200, 230, 255), glow=1.6),
    ], halo=6, want_shadow=True)


def _zeus_hand():
    return forge(61, 61, [
        L(polyline([(8, -26), (-4, -6), (6, -2), (-8, 26)], 4), emit=(170, 200, 255), glow=0.7),
        L([ellipse(0, 4, 16, 13)], mat=P.MARBLE, profile="round", base=0.62),
        L([ellipse(-11 + i * 7.3, -6, 3.2, 6) for i in range(4)], mat=P.MARBLE, profile="round", base=0.7),
        L([rect(-14, 12, 14, 18)], mat=P.GOLD, bevel=1.5),
    ], halo=5, want_shadow=True)


class ZeusHand(Part):
    OWNER_DRAWS = True
    HP = 480
    SCORE = 10000
    RADIUS = 16
    EXPLO = 1.5
    counts = True

    def setup(self, owner=None, side=1, **kw):
        Part.setup(self, owner=owner)
        self.side = side
        base = bs("zhand", _zeus_hand)
        self.spr = base if side > 0 else flipped("zhandL", base)
        self.hitboxes = [(0, 2, 16, 14)]
        self.raise_ = 0.0

    def update(self):
        Part.update(self)
        o = self.owner
        self.x = o.x + self.side * (86 + math.sin(o.t * 0.03 + self.side) * 6)
        self.y = o.y + 40 - self.raise_ * 26 + math.sin(o.t * 0.05 + self.side * 1.3) * 5

    def bolt_tip(self):
        return self.x + 6 * self.side, self.y - 26


class Zeus(Boss):
    NAME = "ΖΕΥΣ-Ω · LE ROI DES DIEUX"
    CARD = ("ΖΕΥΣ-Ω", "LE ROI DES DIEUX")
    HP = 3400
    SCORE = 300000
    RADIUS = 30
    MUSIC = "final"

    def setup(self, **kw):
        self.spr = bs("zeus", _zeus_face)
        self.hands = [self.add_part(ZeusHand(self.w, self.x, self.y, owner=self, side=s)) for s in (-1, 1)]
        self.hitboxes = [(0, 0, 30, 40)]
        self.cracks = []
        self.storm = False

    def sprite(self):
        return self.spr

    def death_span(self):
        return (60, 60)

    def eyes(self):
        return (self.x - 16, self.y), (self.x + 16, self.y)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 64, 200, ease_out_cubic)
        w.audio.play("thunder")
        w.juice.flash((200, 220, 255), 0.8, 0.03)
        w.juice.shake(0.7)
        self.entered_fight = True
        while True:
            f = self.hp / self.max_hp
            if f > 0.66:
                yield from self.p1()
            elif f > 0.33:
                yield from self.p2()
            else:
                if not self.storm:
                    self.storm = True
                    w.audio.play("thunder")
                    w.audio.play("roar", self.x)
                    w.juice.flash((255, 255, 255), 1.0, 0.03)
                    w.banner("ΚΕΡΑΥΝΟΣ !", (170, 210, 255), 100)
                yield from self.p3()

    def drift(self, amp=40):
        self.x = PF_W / 2 + math.sin(self.t * 0.011) * amp
        self.y = 64 + math.sin(self.t * 0.023) * 8
        if self.hp / self.max_hp < 0.66 and len(self.cracks) < 1:
            self.cracks.append([(random.uniform(-20, 20), random.uniform(-20, 30)) for _ in range(5)])
        if self.hp / self.max_hp < 0.33 and len(self.cracks) < 3:
            self.cracks.append([(random.uniform(-26, 26), random.uniform(-30, 40)) for _ in range(6)])

    def bolts(self, n=3, spread=36):
        """Les mains lèvent la foudre : frappes verticales télégraphiées."""
        w = self.w
        p = w.player
        hands = [h for h in self.hands if not h.dead]
        for h in hands:
            h.raise_ = 1.0
        xs = [clamp(p.x + (i - (n - 1) / 2) * spread + random.uniform(-6, 6), 8, PF_W - 8) for i in range(n)]
        for x in xs:
            # la foudre tombe des nuées d'orage, au geste des mains divines
            w.hazards.append(Hazard(w, x, -10, x, PF_H + 10, 12, 44, 18, (160, 190, 255), kind="bolt"))
        return hands

    def p1(self):
        w = self.w
        for rep in range(2):
            hands = self.bolts(3, 40)
            for k in range(70):
                self.drift()
                if k % 24 == 12 and self.can_fire():
                    self.ring(self.x, self.y + 20, 20, 1.4, "m", "gold", off=self.t * 0.02)
                    w.audio.play("eshot_big", self.x)
                if k == 30:
                    for h in hands:
                        h.raise_ = 0.0
                yield
        for k in range(120):
            self.drift()
            if k % 6 == 0 and self.can_fire():
                for h in self.hands:
                    if not h.dead:
                        tx, ty = h.bolt_tip()
                        w.bullets.fire(tx, ty + 30, self.aim_from(tx, ty) + math.sin(k * 0.1) * 0.5, 2.2, "needle",
                                       "blue")
            yield

    def p2(self):
        w = self.w
        # aigles convoqués
        for side in (-1, 1):
            e = Eagle(w, PF_W / 2 + side * 140, -20, path=[(PF_W / 2 + side * 140, -20), (PF_W / 2 + side * 60, 110),
                                                           (PF_W / 2 - side * 60, 150), (PF_W / 2 - side * 140, -30)],
                      dur=260)
            w.spawn(e)
        for side in (-1, 1):
            def track(side=side, s=[0]):
                s[0] += 1
                (lx, ly), (rx, ry) = self.eyes()
                ex, ey = (lx, ly) if side < 0 else (rx, ry)
                a = math.pi / 2 - side * 0.9 + side * min(1.8, max(0.0, (s[0] - 45) / 55))
                return ex, ey, ex + math.cos(a) * 420, ey + math.sin(a) * 420
            hz = Hazard(w, 0, 0, 0, 0, 10, 45, 100, (170, 210, 255), owner=self, track=track)
            hz.x0, hz.y0, hz.x1, hz.y1 = track()
            w.hazards.append(hz)
        for k in range(170):
            self.drift(30)
            if k % 30 == 15 and self.can_fire():
                for h in self.hands:
                    if not h.dead:
                        self.spread(h.x, h.y, 7, 1.0, 1.9, "rice", "gold")
                w.audio.play("eshot2", self.x)
            yield
        hands = self.bolts(4, 30)
        for k in range(80):
            self.drift(30)
            if k == 30:
                for h in hands:
                    h.raise_ = 0.0
            yield

    def p3(self):
        w = self.w
        rot = 0.0
        for k in range(300):
            self.drift(56)
            (lx, ly), (rx, ry) = self.eyes()
            mx, my = self.x, self.y + 30
            if k % 3 == 0 and self.can_fire():
                rot += 0.17
                w.bullets.fire(mx, my, rot, 1.8, "rice", "gold")
                w.bullets.fire(mx, my, rot + math.pi, 1.8, "rice", "gold")
                w.bullets.fire(mx, my, -rot * 0.7 + 1.0, 1.4, "s", "blue")
            if k % 70 == 35:
                self.bolts(2, 70)
            if k % 70 == 60:
                for h in self.hands:
                    h.raise_ = 0.0
            if k % 45 == 0 and self.can_fire():
                self.spread(mx, my, 5, 0.5, 2.8, "l", "violet")
                w.audio.play("eshot_big", mx)
            if k % 25 == 0:
                w.bg.flash = 0.6
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)
        # fissures d'où suinte l'ichor doré
        for cr in self.cracks:
            pts = [(self.x + dx, self.y + dy) for dx, dy in cr]
            pygame.draw.lines(surf, (40, 20, 10), False, pts, 2)
            pygame.draw.lines(surf, (255, 210, 90), False, pts, 1)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        (lx, ly), (rx, ry) = self.eyes()
        k = 0.7 + 0.3 * math.sin(self.t * 0.15)
        for ex, ey in ((lx, ly), (rx, ry)):
            g = glow(9, (int(90 * k), int(140 * k), int(255 * k)), 0.6)
            add.blit(g, (int(ex - 9), int(ey - 9)), special_flags=pygame.BLEND_ADD)
        if self.storm:
            for h in self.hands:
                if not h.dead and random.random() < 0.3:
                    tx, ty = h.bolt_tip()
                    pts = bolt_points(tx, ty, tx + random.uniform(-30, 30), ty - random.uniform(10, 40), 6)
                    draw_bolt(add, pts, (120, 160, 255), width=1)
