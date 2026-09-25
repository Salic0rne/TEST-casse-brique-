"""Boss des stades II (Daidalos, Minotauros) et III (Graiai, Méduse)."""
import math
import random

import pygame

from . import palette as P
from .bosses import Boss, Part, bs, BS
from .entities import Enemy, wait, move_to, PF_W, PF_H
from .enemies import Hazard, Eagle
from .sprites import S, NTUR
from .spritegen import (L, forge, forge_rot, circle, ellipse, rect, line, polyline, arc, star, sym, mirror, move,
                        rot_index)
from .fx import glow, Particle, K_GLOW, K_FIRE, K_SPARK, K_RING, K_FLARE, rotated
from .util import TAU, clamp, ease_out_cubic, ease_in_out, ease_in_cubic, angle_diff


# ===========================================================================
# STADE II — DAIDALOS : l'automate ailé de Dédale (gardien)
# ===========================================================================
def _daidalos_core():
    return forge(55, 55, [
        L([star(0, 0, 18, 22, 16)], mat=P.BRONZE, bevel=2, spec=0.3),
        L([circle(0, 0, 17)], mat=P.DARKSTEEL, bevel=2, base=0.5),
        L([circle(0, 0, 13)], mat=P.GOLD, bevel=2, spec=0.5),
        L([star(0, 0, 7, 10, 8, rot=0.3)], mat=P.BRONZE, bevel=1),
        L([circle(0, 0, 6)], mat=P.MAGENTA, profile="round", spec=0.8),
        L([circle(-1.5, -1.5, 2.5)], emit=(255, 170, 230), glow=1.4),
        L([circle(math.cos(a) * 15, math.sin(a) * 15, 1.2) for a in (0.4, 2.0, 3.6, 5.2)], emit=P.RED_E, glow=0.8),
    ], halo=4, want_shadow=True)


def _daidalos_wing(pose):
    """Aile droite (pose 0..2 : battement)."""
    feathers = []
    base_a = -0.5 + pose * 0.18
    for i in range(7):
        a = base_a + i * 0.17
        ln = 46 - abs(i - 2.5) * 3.5
        tip = (math.cos(a) * ln, math.sin(a) * ln)
        n = (-math.sin(a) * 3.6, math.cos(a) * 3.6)
        feathers.append([(0, 0), (tip[0] * 0.5 + n[0], tip[1] * 0.5 + n[1]), tip, (tip[0] * 0.5 - n[0] * 0.3,
                                                                                  tip[1] * 0.5 - n[1] * 0.3)])
    return forge(105, 105, [
        L(feathers, mat=P.MARBLE, bevel=1.5, base=0.66, rim=(P.GOLD_E, 0.5)),
        L([line(0, 0, math.cos(base_a + i * 0.17) * 36, math.sin(base_a + i * 0.17) * 36, 0.9) for i in range(7)],
          mat=P.GOLD, bevel=1),
        L([circle(0, 0, 7)], mat=P.BRONZE, profile="round"),
        L([circle(0, 0, 3)], emit=(255, 180, 80), glow=1.0),
    ], anchor=(52, 52), halo=3, want_shadow=True)


class DaidalosWing(Part):
    HP = 130
    SCORE = 5000
    RADIUS = 16
    EXPLO = 1.2
    counts = True

    def setup(self, owner=None, side=1, **kw):
        Part.setup(self, owner=owner)
        self.side = side
        self.poses = [bs(f"dwing{p}", lambda p=p: _daidalos_wing(p)) for p in range(3)]
        if side < 0:
            self.poses = [bs(f"dwingL{p}", lambda p=p: self._mirror(p)) for p in range(3)]

    def _mirror(self, p):
        from .spritegen import Sprite
        spr = bs(f"dwing{p}", lambda: _daidalos_wing(p))
        img = pygame.transform.flip(spr.img, True, False)
        fl = pygame.transform.flip(spr.flash, True, False)
        sh = pygame.transform.flip(spr.shadow, True, False) if spr.shadow else None
        ha = pygame.transform.flip(spr.halo, True, False) if spr.halo else None
        return Sprite(img, fl, sh, ha, spr.w - spr.ox, spr.oy, spr.hox - spr.ox)

    def pose(self):
        return int(1 + math.sin(self.owner.t * 0.12 + (0 if self.side > 0 else 0.5)) * 1.4 + 0.5) % 3

    def update(self):
        Part.update(self)
        self.x = self.owner.x + self.side * 22
        self.y = self.owner.y - 2
        self.hitboxes = [(self.side * 22, 4, 21, 12)]

    def sprite(self):
        return self.poses[self.pose()]

    def image(self):
        return self.poses[1].img


class Daidalos(Boss):
    NAME = "ΔΑΙΔΑΛΟΣ · L'AUTOMATE"
    CARD = ("ΔΑΙΔΑΛΟΣ", "LES AILES D'ICARE")
    HP = 320
    SCORE = 20000
    RADIUS = 16
    MID = True
    EXPLO = 2.0

    def setup(self, **kw):
        self.spr = bs("daidalos", _daidalos_core)
        self.wings = [self.add_part(DaidalosWing(self.w, self.x, self.y, owner=self, side=s)) for s in (-1, 1)]

    def sprite(self):
        return self.spr

    def ARMOR_NOW(self):
        return any(not wg.dead for wg in self.wings) and self.t < 60 * 30

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 70, 110, ease_out_cubic)
        self.entered_fight = True
        k = 0
        rot = 0.0
        while k < 60 * 50:
            k += 1
            wings = sum(1 for wg in self.wings if not wg.dead)
            sp = 1.0 if wings else 1.8
            self.x = PF_W / 2 + math.sin(k * 0.013 * sp) * 64
            self.y = 70 + math.sin(k * 0.027 * sp) * 16
            for wg in self.wings:
                if not wg.dead and (k + (40 if wg.side < 0 else 0)) % int(80 / w.diff["rate"]) == 0 and self.can_fire():
                    a = math.pi / 2 + wg.side * 0.5
                    w.bullets.arc(wg.x + wg.side * 14, wg.y + 6, a, w.bullets.dens(6), 1.0, 2.1, "feather")
                    w.audio.play("eshot2", wg.x, 0.7)
            if k % int(6 / w.diff["rate"] + 0.5) == 0 and self.can_fire():
                rot += 0.19 if wings else 0.27
                n = 2 if wings else 4
                for j in range(n):
                    w.bullets.fire(self.x, self.y, rot + j * TAU / n, 1.6 if wings else 2.0, "s", "pink")
            if not wings and k % int(70 / w.diff["rate"]) == 0 and self.can_fire():
                self.ring(self.x, self.y, 16, 1.4, "m", "violet", off=k * 0.07)
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
# STADE II — MINOTAUROS
# ===========================================================================
def _mino_body():
    return forge(141, 111, [
        L([[(-66, -34), (66, -34), (60, 6), (40, 18), (-40, 18), (-60, 6)]], mat=P.BRONZE, bevel=3, base=0.5),
        L([rect(-64, -30, 64, -24), rect(-52, 4, 52, 9)], mat=P.GOLD, bevel=1, clip=True, cast=False),
        L([circle(-50, -12, 10), circle(50, -12, 10)], mat=P.DARKSTEEL, profile="round", spec=0.4),
        L([circle(-50, -12, 4), circle(50, -12, 4)], emit=(255, 110, 40), glow=1.0),
        L([sym([(0, -38), (17, -36), (26, -22), (28, -4), (22, 16), (15, 32), (8, 44), (0, 46)])], mat=P.BRONZE,
          bevel=3.5, spec=0.35),
        L([sym([(0, -34), (9, -32), (12, -18), (8, -8), (0, -6)])], mat=P.GOLD, bevel=1.5, spec=0.5),
        L(polyline([(-5, -26), (0, -14), (5, -26)], 1.4) + [line(0, -30, 0, -12, 1.2)], mat=P.RED, bevel=1),
        L([ellipse(0, 34, 13, 10)], mat=P.BRONZE, bevel=2, base=0.42),
        L([ellipse(-5, 38, 2.4, 1.8), ellipse(5, 38, 2.4, 1.8)], flat=(20, 8, 8)),
        L([arc(0, 42, 4, 5.6, 0.2, math.pi - 0.2)], mat=P.GOLD, bevel=1, spec=0.6),
        L([ellipse(12, 4, 4.2, 2.6, 0.35), ellipse(-12, 4, 4.2, 2.6, -0.35)], emit=P.RED_E, glow=1.4),
    ], halo=4, want_shadow=True)


def _mino_horn():
    return forge(49, 49, [
        L([[(-4, 10), (6, 2), (14, -8), (18, -18), (22, -20), (20, -8), (12, 6), (2, 16)]], mat=P.MARBLE,
          profile="round", base=0.66, spec=0.5),
        L([circle(20, -19, 2.2)], emit=(255, 80, 60), glow=1.2),
    ], halo=3, want_shadow=True)


def _labrys():
    return forge(45, 45, [
        L([line(0, -19, 0, 19, 2.6)], mat=P.BRONZE, bevel=1),
        L([[(2, -14), (15, -20), (19, -8), (15, 4), (2, -2)]], mat=P.STEEL, bevel=2, mirror=True, spec=0.6),
        L([arc(0, -8, 14, 17.5, -0.9, 0.5), arc(0, -8, 14, 17.5, math.pi - 0.5, math.pi + 0.9)], mat=P.GOLD, bevel=1),
    ], halo=0)


class MinoHorn(Part):
    OWNER_DRAWS = True
    HP = 260
    SCORE = 8000
    RADIUS = 12
    EXPLO = 1.2
    counts = True

    def setup(self, owner=None, side=1, **kw):
        Part.setup(self, owner=owner)
        self.side = side
        base = bs("mino_horn", _mino_horn)
        if side > 0:
            self.spr = base
        else:
            from .spritegen import Sprite
            self.spr = bs("mino_hornL", lambda: Sprite(pygame.transform.flip(base.img, True, False),
                                                        pygame.transform.flip(base.flash, True, False),
                                                        pygame.transform.flip(base.shadow, True, False),
                                                        pygame.transform.flip(base.halo, True, False),
                                                        base.w - base.ox, base.oy, base.hox - base.ox))

    def update(self):
        Part.update(self)
        self.x = self.owner.x + self.side * 34
        self.y = self.owner.y - 26
        self.hitboxes = [(self.side * 8, -4, 10, 12)]

    def tip(self):
        return self.x + self.side * 20, self.y - 19


class Labrys(Enemy):
    """Hache à double tranchant lancée : aller-retour en tournoyant."""
    HP = 9999
    RADIUS = 13
    BOSSPART = True
    ARMOR = True
    BODY = True

    def setup(self, owner=None, tx=128, ty=200, **kw):
        self.owner = owner
        self.tx, self.ty = tx, ty
        self.ang = 0.0
        self.spr = bs("labrys", _labrys)

    def targetable(self):
        return False

    def behave(self):
        w = self.w
        x0, y0 = self.x, self.y
        for i in range(70):
            t = ease_out_cubic(i / 70)
            self.x = x0 + (self.tx - x0) * t
            self.y = y0 + (self.ty - y0) * t
            if i % 6 == 0 and self.can_fire():
                w.bullets.ring(self.x, self.y, w.bullets.dens(6), 1.1, "s", "orange", offset=self.ang)
            yield
        for i in range(80):
            o = self.owner
            if o is None or o.dead:
                break
            a = math.atan2(o.y - self.y, o.x - self.x)
            sp = min(6.0, 1 + i * 0.1)
            self.x += math.cos(a) * sp
            self.y += math.sin(a) * sp
            if (o.x - self.x) ** 2 + (o.y - self.y) ** 2 < 400:
                break
            yield
        self.dead = True

    def update(self):
        Enemy.update(self)
        self.ang += 24
        self.gone = False
        if self.t % 3 == 0:
            self.w.fx.add(Particle(K_GLOW, self.x, self.y, 0, 0, 10, 8, 2, (120, 100, 80)))

    def draw(self, surf):
        img = rotated(self.spr.img, self.ang, 15)
        surf.blit(img, (int(self.x - img.get_width() / 2), int(self.y - img.get_height() / 2)))

    def draw_add(self, add):
        pass


class Minotauros(Boss):
    NAME = "ΜΙΝΩΤΑΥΡΟΣ · MINOTAURE"
    CARD = ("ΜΙΝΩΤΑΥΡΟΣ", "LE TAUREAU DU DÉDALE")
    HP = 2100
    RADIUS = 22

    def setup(self, **kw):
        self.spr = bs("mino", _mino_body)
        self.horns = [self.add_part(MinoHorn(self.w, self.x, self.y, owner=self, side=s)) for s in (-1, 1)]
        self.hitboxes = [(0, 6, 22, 30), (0, -20, 50, 12)]
        self.labrys = None
        self.charging = False
        self.beams = []

    def sprite(self):
        return self.spr

    def death_span(self):
        return (40, 30)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 60, 150, ease_out_cubic)
        w.audio.play("roar")
        w.juice.shake(0.5)
        self.entered_fight = True
        while True:
            f = self.hp / self.max_hp
            yield from self.horn_lasers()
            yield from self.breath(3)
            if f < 0.75:
                yield from self.throw_labrys()
            if f < 0.5:
                yield from self.charge()
                yield from self.charge()
            if f < 0.3:
                yield from self.frenzy()

    def home(self, frames=60):
        yield from move_to(self, PF_W / 2 + random.uniform(-40, 40), 60, frames, ease_in_out)

    def horn_lasers(self):
        w = self.w
        horns = [h for h in self.horns if not h.dead]
        if not horns:
            yield from self.breath(2)
            return
        for h in horns:
            def track(h=h, s=[0.0]):
                tx, ty = h.tip()
                s[0] += 0.012
                a = math.pi / 2 - h.side * (0.9 - min(0.9, s[0] * 1.6))
                return tx, ty, tx + math.cos(a) * 400, ty + math.sin(a) * 400
            hz = Hazard(w, 0, 0, 0, 0, 8, 50, 90, (255, 70, 90), owner=h, track=track)
            hz.x0, hz.y0, hz.x1, hz.y1 = track()
            w.hazards.append(hz)
        for i in range(140):
            if i % 20 == 10 and self.can_fire():
                self.spread(self.x, self.y + 40, 3, 0.4, 2.2, "m", "orange")
            yield

    def breath(self, n):
        w = self.w
        for r in range(n):
            yield from wait(24)
            if self.can_fire():
                for side in (-5, 5):
                    self.spread(self.x + side, self.y + 40, 7, 1.1, 1.9, "rice", "pink")
                w.fx.add(Particle(K_GLOW, self.x, self.y + 42, 0, 1, 20, 8, 16, (120, 100, 110)))
                w.audio.play("eshot_big", self.x)

    def throw_labrys(self):
        w = self.w
        p = w.player
        self.labrys = Labrys(w, self.x + 40, self.y + 10, owner=self, tx=p.x, ty=min(PF_H - 40, p.y))
        w.spawn(self.labrys)
        w.audio.play("clang", self.x)
        for i in range(90):
            if i % 30 == 15 and self.can_fire():
                self.ring(self.x, self.y + 20, 14, 1.3, "m", "pink", off=i * 0.1)
            yield

    def charge(self):
        w = self.w
        p = w.player
        tx = p.x
        yield from move_to(self, tx, 40, 30, ease_in_out)
        # avertissement : trait vertical
        hz = Hazard(w, tx, 60, tx, PF_H, 46, 46, 1, (255, 60, 60))
        w.hazards.append(hz)
        w.audio.play("roar", tx, 0.8)
        yield from wait(44)
        self.charging = True
        for i in range(22):
            self.y += 7.0
            if i % 3 == 0:
                w.fx.add(Particle(K_GLOW, self.x, self.y - 30, 0, -2, 16, 12, 4, (150, 80, 40)))
            yield
        self.charging = False
        w.juice.shake(0.7)
        w.audio.play("explo_m", self.x)
        w.fx.ring(self.x, self.y + 30, 6, 90, 30, (255, 170, 90), 4)
        yield from wait(10)
        # onde de choc : couronne lente, à distance respectable du joueur
        self.ring(self.x, self.y + 10, 16, 1.2, "m", "orange")
        if w.diff["density"] > 1.0:
            self.ring(self.x, self.y + 10, 8, 0.9, "l", "pink", off=0.2)
        yield from wait(20)
        yield from move_to(self, PF_W / 2, 60, 70, ease_in_out)

    def frenzy(self):
        w = self.w
        rot = 0.0
        for i in range(300):
            self.x = PF_W / 2 + math.sin(i * 0.03) * 50
            if i % 4 == 0 and self.can_fire():
                rot += 0.23
                for j in range(3):
                    w.bullets.fire(self.x, self.y + 30, rot + j * TAU / 3, 1.8, "rice", "violet")
            if i % 50 == 25:
                self.spread(self.x, self.y + 40, 5, 0.6, 2.6, "l", "red")
                w.audio.play("eshot_big", self.x)
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        if self.charging:
            g = glow(40, (140, 30, 20), 0.3)
            add.blit(g, (int(self.x - 40), int(self.y - 30)), special_flags=pygame.BLEND_ADD)


# ===========================================================================
# STADE III — LES GRAIAI : trois sœurs, un seul œil
# ===========================================================================
def _graia():
    return forge(41, 47, [
        L([sym([(0, -20), (9, -17), (14, -6), (16, 10), (18, 21), (0, 18)])], mat=P.STONE, bevel=2.5, noise=0.06,
          base=0.5),
        L([sym([(0, -15), (6, -13), (9, -4), (7, 5), (0, 8)])], mat=P.EBONY, bevel=1.5),
        L([ellipse(0, -3, 5, 6)], mat=P.BONE, profile="round", base=0.55),
        L([ellipse(-2, -4, 1.4, 1.0), ellipse(2, -4, 1.4, 1.0)], flat=(10, 6, 12)),
        L(polyline([(-14, 8), (-20, 16), (-17, 22)], 1.6) + polyline([(14, 8), (20, 16), (17, 22)], 1.6), mat=P.BONE,
          bevel=1),
    ], halo=0, want_shadow=True)


class Graia(Part):
    HP = 170
    SCORE = 6000
    RADIUS = 14
    EXPLO = 1.2
    counts = True

    def setup(self, owner=None, idx=0, **kw):
        Part.setup(self, owner=owner)
        self.idx = idx
        self.spr = bs("graia", _graia)

    def has_eye(self):
        return self.owner.eye_holder is self

    def targetable(self):
        return self.onscreen and not self.owner.dying

    def armored(self):
        return not self.has_eye()

    def hit(self, dmg, x=None, y=None, silent=False):
        if not self.has_eye():
            if x is not None and self.w.t % 5 == 0:
                self.w.fx.hit(x, y, (200, 200, 220), 2)
                self.w.audio.play("tink", x, 0.5, throttle=6)
            return False
        return Part.hit(self, dmg, x, y, silent)

    def update(self):
        Part.update(self)
        o = self.owner
        a = o.t * 0.01 + self.idx * TAU / 3
        self.x = o.x + math.cos(a) * 58
        self.y = o.y + math.sin(a) * 30


class Graiai(Boss):
    NAME = "ΓΡΑΙΑΙ · LES GRÉES"
    CARD = ("ΓΡΑΙΑΙ", "TROIS SŒURS, UN SEUL ŒIL")
    HP = 1
    SCORE = 25000
    MID = True
    RADIUS = 1
    EXPLO = 2.0
    BODY = False

    def setup(self, **kw):
        self.sisters = [self.add_part(Graia(self.w, self.x, self.y, owner=self, idx=i)) for i in range(3)]
        self.eye_holder = self.sisters[0]
        self.eye_pos = [self.x, self.y]
        self.eye_from = None
        self.eye_t = 0

    def targetable(self):
        return False

    def hp_frac(self):
        tot = sum(max(0, s.hp) for s in self.sisters if not s.dead)
        return tot / sum(s.max_hp for s in self.sisters)

    def death_span(self):
        return (60, 30)

    def part_died(self, p):
        alive = [s for s in self.sisters if not s.dead]
        if not alive:
            self.die()
        elif self.eye_holder is p:
            self.pass_eye(alive)

    def pass_eye(self, alive=None):
        alive = alive or [s for s in self.sisters if not s.dead]
        choices = [s for s in alive if s is not self.eye_holder] or alive
        self.eye_from = (self.eye_pos[0], self.eye_pos[1])
        self.eye_holder = random.choice(choices)
        self.eye_t = 0
        self.w.audio.play("teleport", self.eye_pos[0], 0.6)

    def update(self):
        Boss.update(self)
        if self.dying:
            return
        h = self.eye_holder
        if h is not None:
            self.eye_t += 1
            tx, ty = h.x, h.y - 4
            if self.eye_from is not None and self.eye_t < 30:
                k = ease_in_out(self.eye_t / 30)
                self.eye_pos = [self.eye_from[0] + (tx - self.eye_from[0]) * k,
                                self.eye_from[1] + (ty - self.eye_from[1]) * k - math.sin(k * math.pi) * 30]
            else:
                self.eye_pos = [tx, ty]

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 90, 120, ease_out_cubic)
        self.entered_fight = True
        k = 0
        while True:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.01) * 20
            alive = [s for s in self.sisters if not s.dead]
            if not alive:
                return
            h = self.eye_holder
            if k % 240 == 0:
                self.pass_eye()
            ex, ey = self.eye_pos
            if self.eye_t > 30 and k % int(48 / w.diff["rate"]) == 0 and self.can_fire():
                self.spread(ex, ey, 5, 0.6, 2.4, "needle", "green")
                w.audio.play("eshot2", ex)
            if self.eye_t == 60 and self.can_fire():
                a = self.aim_from(ex, ey)
                hz = Hazard(w, ex, ey, ex + math.cos(a) * 400, ey + math.sin(a) * 400, 9, 40, 30, (90, 255, 150),
                            owner=h)
                w.hazards.append(hz)
            for s in alive:
                if s is not h and (k + s.idx * 20) % int(70 / w.diff["rate"]) == 0 and self.can_fire():
                    self.ring(s.x, s.y, 10, 1.1, "m", "violet", off=k * 0.05)
            yield

    def draw(self, surf):
        if self.dying:
            return
        ex, ey = self.eye_pos
        pygame.draw.circle(surf, (230, 255, 240), (int(ex), int(ey)), 4)
        pygame.draw.circle(surf, (20, 120, 60), (int(ex), int(ey)), 2)

    def draw_add(self, add):
        if self.dying:
            return
        ex, ey = self.eye_pos
        k = 0.8 + 0.2 * math.sin(self.t * 0.3)
        g = glow(12, (int(60 * k), int(230 * k), int(140 * k)), 0.7)
        add.blit(g, (int(ex - 12), int(ey - 12)), special_flags=pygame.BLEND_ADD)
        for s in self.sisters:
            if not s.dead and s is not self.eye_holder:
                pygame.draw.circle(add, (20, 40, 30), (int(s.x), int(s.y - 4)), 3)


# ===========================================================================
# STADE III — MÉDUSE
# ===========================================================================
def _medusa_face():
    return forge(121, 101, [
        # ailes d'or (les Gorgones sont ailées)
        L([[(20, -20), (40, -38), (58, -40), (54, -28), (60, -22), (50, -14), (54, -6), (36, -2), (22, 4)]],
          mat=P.GOLD, bevel=2, mirror=True, spec=0.4),
        L([line(26, -16, 52, -34, 1.0), line(28, -10, 52, -20, 1.0)], mat=P.BRONZE, bevel=1, mirror=True),
        L([ellipse(0, 0, 30, 38)], mat=P.MARBLE, profile="round", base=0.6, veins=0.12),
        L([rect(-30, -30, 30, -22)], mat=P.BRONZE, bevel=1.5, clip=True, cast=False),
        L([circle(0, -26, 4)], emit=P.GREEN_E, glow=1.2),
        L([ellipse(-12, -2, 8, 6), ellipse(12, -2, 8, 6)], mat=P.EBONY, bevel=1.5),
        L([ellipse(-12, -2, 4.4, 3.8), ellipse(12, -2, 4.4, 3.8)], emit=P.GREEN_E, glow=1.8),
        L([sym([(0, -8), (2.5, 8), (0, 10)])], mat=P.MARBLE, bevel=1, base=0.5),
        L([ellipse(0, 22, 11, 5)], mat=P.EBONY, bevel=1),
        L([[(-8 + i * 3.2, 19), (-6.8 + i * 3.2, 23.5), (-5.6 + i * 3.2, 19)] for i in range(5)], flat=(240, 236, 220)),
        L(polyline([(-24, 6), (-18, 14), (-22, 26)], 1.0) + polyline([(20, 10), (26, 22)], 1.0), mat=P.STONE, bevel=1,
          clip=True, cast=False),
    ], halo=5, want_shadow=True)


class MedusaSnake(Part):
    HP = 110
    SCORE = 3000
    RADIUS = 7
    EXPLO = 0.9
    counts = False
    NSEG = 7

    def setup(self, owner=None, ang=0.0, idx=0, **kw):
        Part.setup(self, owner=owner)
        self.ang = ang
        self.idx = idx
        self.pts = []
        self.aim_a = ang
        self.anchor = (0, 0)

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
        ax, ay = o.x + math.cos(self.ang) * 30, o.y + math.sin(self.ang) * 34 - 4
        self.anchor = (ax, ay)
        pts = []
        amp = 0.35 if not o.enraged else 0.55
        a = self.ang
        x, y = ax, ay
        for i in range(self.NSEG):
            a = self.ang + math.sin(o.t * 0.06 + self.idx * 0.9 + i * 0.6) * amp * (i / self.NSEG)
            x += math.cos(a) * 7
            y += math.sin(a) * 7
            pts.append((x, y))
        self.pts = pts
        self.x, self.y = pts[-1]
        p = self.w.player
        want = math.atan2(p.y - self.y, p.x - self.x)
        self.aim_a += clamp(angle_diff(self.aim_a, want), -0.1, 0.1)

    def draw(self, surf):
        seg = S["serpent_seg"]
        for (x, y) in self.pts[:-1]:
            seg.draw(surf, x, y, self.flash > 0)
        S["serpent_head"][rot_index(self.aim_a, NTUR)].draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        S["serpent_head"][rot_index(self.aim_a, NTUR)].draw_halo(add, self.x, self.y)

    def image(self):
        return S["serpent_head"][0].img


class Medusa(Boss):
    NAME = "ΜΕΔΟΥΣΑ · MÉDUSE"
    CARD = ("ΜΕΔΟΥΣΑ", "LA GORGONE AU REGARD DE PIERRE")
    HP = 2400
    RADIUS = 26

    def setup(self, **kw):
        self.spr = bs("medusa", _medusa_face)
        self.snakes = []
        for i in range(8):
            a = -math.pi / 2 + (i - 3.5) * 0.42
            if i >= 4:
                a += 0.0
            self.snakes.append(self.add_part(MedusaSnake(self.w, self.x, self.y, owner=self, ang=a, idx=i)))
        self.hitboxes = [(0, 0, 24, 32)]
        self.enraged = False
        self.gaze = None

    def sprite(self):
        return self.spr

    def death_span(self):
        return (34, 36)

    def eyes(self):
        return (self.x - 12, self.y - 2), (self.x + 12, self.y - 2)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 74, 160, ease_out_cubic)
        w.audio.play("roar", self.x, 0.8)
        self.entered_fight = True
        while True:
            f = self.hp / self.max_hp
            self.enraged = f < 0.35
            yield from self.snake_volleys()
            yield from self.gaze_attack()
            if f < 0.7:
                yield from self.hair_spiral()
            if f < 0.35:
                yield from self.cross_lasers()

    def drift(self, k):
        self.x = PF_W / 2 + math.sin(self.t * 0.012) * 40
        self.y = 74 + math.sin(self.t * 0.02) * 10

    def snake_volleys(self):
        w = self.w
        alive = [s for s in self.snakes if not s.dead]
        for k in range(200):
            self.drift(k)
            if alive and k % 10 == 0 and self.can_fire():
                s = alive[(k // 10) % len(alive)]
                if not s.dead:
                    w.bullets.fire(s.x, s.y, s.aim_a, 2.3, "rice", "green")
                    w.bullets.fire(s.x, s.y, s.aim_a + 0.2, 2.1, "rice", "green")
            if k % 60 == 30 and self.can_fire():
                self.spread(self.x, self.y + 22, 5, 0.9, 1.6, "l", "violet")
                w.audio.play("eshot_big", self.x)
            yield

    def gaze_attack(self):
        """Regard pétrifiant : large rayon balayant."""
        w = self.w
        (lx, ly), (rx, ry) = self.eyes()
        a0 = math.pi / 2 + 0.9 * random.choice((-1, 1))

        def track(s=[0]):
            s[0] += 1
            (lx, ly), (rx, ry) = self.eyes()
            cx, cy = (lx + rx) / 2, ly
            a = a0 - (a0 - math.pi / 2) * 2 * min(1.0, max(0.0, (s[0] - 50) / 100))
            return cx, cy, cx + math.cos(a) * 420, cy + math.sin(a) * 420
        hz = Hazard(w, 0, 0, 0, 0, 22, 50, 100, (90, 255, 150), owner=self, track=track)
        hz.x0, hz.y0, hz.x1, hz.y1 = track()
        w.hazards.append(hz)
        w.audio.play("charge", self.x)
        for k in range(160):
            self.drift(k)
            if k > 50 and k % 12 == 0 and self.can_fire():
                self.ring(self.x, self.y, 10, 1.0, "l", "white", off=k * 0.1)
            yield

    def hair_spiral(self):
        w = self.w
        rot = 0.0
        for k in range(240):
            self.drift(k)
            if k % 5 == 0 and self.can_fire():
                rot += 0.12
                for s in self.snakes:
                    if not s.dead:
                        a = math.atan2(s.y - self.y, s.x - self.x) + math.sin(rot) * 0.6
                        w.bullets.fire(s.x, s.y, a, 1.7, "s", "green")
            if k % 40 == 0:
                w.audio.play("eshot", self.x, 0.6)
            yield

    def cross_lasers(self):
        w = self.w
        for side in (-1, 1):
            def track(side=side, s=[0]):
                s[0] += 1
                (lx, ly), (rx, ry) = self.eyes()
                ex, ey = (lx, ly) if side < 0 else (rx, ry)
                a = math.pi / 2 + side * (0.8 - min(1.6, max(0.0, (s[0] - 45) / 70)))
                return ex, ey, ex + math.cos(a) * 420, ey + math.sin(a) * 420
            hz = Hazard(w, 0, 0, 0, 0, 10, 45, 110, (120, 255, 160), owner=self, track=track)
            hz.x0, hz.y0, hz.x1, hz.y1 = track()
            w.hazards.append(hz)
        for k in range(170):
            self.drift(k)
            if k % 16 == 0 and self.can_fire():
                self.spread(self.x, self.y + 22, 3, 0.5, 2.5, "m", "pink")
            yield

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        (lx, ly), (rx, ry) = self.eyes()
        k = 0.6 + 0.4 * math.sin(self.t * 0.2)
        for ex, ey in ((lx, ly), (rx, ry)):
            g = glow(7, (int(40 * k), int(200 * k), int(110 * k)), 0.6 * k)
            add.blit(g, (int(ex - 7), int(ey - 7)), special_flags=pygame.BLEND_ADD)
