"""Boss et gardiens : cadre commun (parties destructibles, phases, mort spectaculaire)
+ les boss du stade I (Skylla, Kétos)."""
import math
import random

import pygame

from . import palette as P
from .entities import Enemy, wait, move_to, PF_W, PF_H
from .sprites import S, NTUR
from .spritegen import (L, forge, circle, ellipse, line, arc, sym, rot_index)
from .fx import glow, Particle, K_GLOW
from .util import TAU, clamp, ease_out_cubic, ease_in_out, ease_in_cubic, angle_diff

BS = {}   # sprites de boss (construits à la demande)


def bs(name, builder):
    s = BS.get(name)
    if s is None:
        s = BS[name] = builder()
    return s


# ---------------------------------------------------------------------------
# Cadre
# ---------------------------------------------------------------------------
class Part(Enemy):
    """Partie de boss : suit son propriétaire, peut être blindée."""
    BOSSPART = True
    BODY = False
    EXPLO = 1.0
    KILL_SFX = "explo_m"

    def setup(self, owner=None, dx=0.0, dy=0.0, spr=None, hp=None, radius=None, armor=False, **kw):
        self.owner = owner
        self.dx = dx
        self.dy = dy
        self.spr = spr
        if hp is not None:
            self.hp = self.max_hp = hp
        if radius is not None:
            self.RADIUS = radius
        self.armor = armor
        self.rot = 0.0

    def behave(self):
        while True:
            yield

    def update(self):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.flash_cd > 0:
            self.flash_cd -= 1
        o = self.owner
        if o is not None:
            self.x = o.x + self.dx
            self.y = o.y + self.dy
            if o.dead:
                self.dead = True
        if self.brain is not None:
            try:
                next(self.brain)
            except StopIteration:
                self.brain = None

    def targetable(self):
        return self.onscreen and not (self.owner and getattr(self.owner, "dying", False))

    def armored(self):
        return self.armor

    def hit(self, dmg, x=None, y=None, silent=False):
        if self.armor:
            if x is not None and self.w.t % 4 == 0:
                self.w.fx.hit(x, y, (200, 200, 255), 2)
                self.w.audio.play("tink", x, 0.6, throttle=5)
            return False
        return Enemy.hit(self, dmg, x, y, silent)

    def sprite(self):
        return self.spr

    def on_death(self):
        w = self.w
        w.juice.hitstop = max(w.juice.hitstop, 4)
        w.juice.shake(0.35)
        w.juice.flash((255, 240, 220), 0.3, 0.08)
        w.fx.ring(self.x, self.y, 4, 60, 24, (255, 230, 180), 3)
        if self.owner is not None and hasattr(self.owner, "part_died"):
            self.owner.part_died(self)


class Boss(Enemy):
    BOSSPART = True
    BODY = True
    NAME = "BOSS"
    CARD = None
    HP = 2000
    SCORE = 100000
    EXPLO = 3.0
    RADIUS = 20
    MUSIC = "boss"
    MID = False

    def __init__(self, w, x=PF_W / 2, y=-60, **kw):
        self.parts = []
        self.dying = False
        self.dying_t = 0
        self.phase = 0
        self.entered_fight = False
        super().__init__(w, x, y, **kw)
        # le multiplicateur de difficulté renforce un peu les boss
        self.hp *= (0.85 + 0.15 * w.diff["density"])
        self.max_hp = self.hp

    def add_part(self, p):
        self.parts.append(p)
        self.w.spawn(p)
        return p

    def hp_frac(self):
        tot = max(0.0, self.hp)
        mx = self.max_hp
        for p in self.parts:
            if getattr(p, "counts", True):
                mx += p.max_hp
                if not p.dead:
                    tot += max(0.0, p.hp)
        return tot / mx if mx > 0 else 0.0

    def targetable(self):
        return self.onscreen and not self.dying and self.entered_fight

    def armored(self):
        return self.ARMOR_NOW()

    def ARMOR_NOW(self):
        return False

    def hit(self, dmg, x=None, y=None, silent=False):
        if self.ARMOR_NOW():
            if x is not None and self.w.t % 4 == 0:
                self.w.fx.hit(x, y, (200, 200, 255), 2)
                self.w.audio.play("tink", x, 0.6, throttle=5)
            return False
        return Enemy.hit(self, dmg, x, y, silent)

    def update(self):
        if self.dying:
            self.update_dying()
            return
        Enemy.update(self)
        self.gone = False

    def die(self, quiet=False):
        if self.dying or self.dead:
            return
        self.dying = True
        self.dying_t = 0
        self.brain = None
        w = self.w
        w.juice.slowmo = 50
        w.juice.flash((255, 255, 255), 0.7, 0.05)
        w.audio.stop_loops()
        w.bullets.cancel(True)
        for h in w.hazards:
            h.alive = False
        for p in self.parts:
            if not p.dead:
                p.dead = True
                w.fx.explosion(p.x, p.y, 1.0)

    def update_dying(self):
        w = self.w
        self.dying_t += 1
        t = self.dying_t
        self.x += math.sin(t * 0.9) * 0.8
        self.y += 0.15
        span = self.death_span()
        if t % 5 == 0:
            ox = random.uniform(-span[0], span[0])
            oy = random.uniform(-span[1], span[1])
            w.fx.explosion(self.x + ox, self.y + oy, random.uniform(0.7, 1.3),
                           grad=self.grad() if t % 10 == 0 else None)
            w.audio.play("explo_m" if t % 15 == 0 else "explo_s", self.x + ox)
            w.juice.shake(0.2)
            self.flash = 2
        if t % 20 == 0:
            w.bullets.cancel(True)
        n = 110 if not self.MID else 70
        if t >= n:
            self.dead = True
            w.fx.explosion(self.x, self.y, 3.2 if not self.MID else 2.2,
                           debris=w.fx.debris_from(self.image(), 12), ring_col=(255, 240, 200))
            w.fx.explosion(self.x, self.y, 2.0, delay=10, grad=self.grad())
            w.fx.ring(self.x, self.y, 10, 300, 60, (255, 255, 255), 6)
            w.audio.play("explo_boss")
            w.juice.shake(1.0)
            w.juice.flash((255, 250, 230), 1.0, 0.025)
            w.juice.aberr(6)
            w.bullets.cancel(True)
            w.score.kill(self)
            w.popup(self.x, self.y - 10, f"+{self.SCORE * w.score.mult}", (255, 240, 170), 90)
            w.drop_items(self.x, self.y, "p", 4 if not self.MID else 2)
            w.drop_coins(self.x, self.y, 24 if not self.MID else 12)
            if not self.MID:
                w.drop_items(self.x, self.y, "bomb", 1)
            self.on_defeat()

    def on_defeat(self):
        pass

    def death_span(self):
        return (30, 24)

    # utilitaires de tir
    def spread(self, x, y, n, spread, spd, kind="m", col="pink", a=None, **kw):
        a = self.aim_from(x, y) if a is None else a
        return self.w.bullets.arc(x, y, a, self.w.bullets.dens(n), spread, spd, kind, col, **kw)

    def aim_from(self, x, y):
        p = self.w.player
        return math.atan2(p.y - y, p.x - x)

    def ring(self, x, y, n, spd, kind="m", col="pink", off=0.0, **kw):
        return self.w.bullets.ring(x, y, self.w.bullets.dens(n), spd, kind, col, offset=off, **kw)


# ---------------------------------------------------------------------------
# STADE I — SKYLLA (gardienne) : six têtes de serpent autour d'un noyau
# ---------------------------------------------------------------------------
def _skylla_body():
    return forge(71, 55, [
        L([ellipse(0, 0, 33, 24)], mat=P.STONE, profile="round", noise=0.08, base=0.5),
        L([ellipse(0, -2, 24, 16)], mat=P.VERDIGRIS, bevel=2.5, spec=0.3),
        L([arc(0, -2, 17, 21, 0.2, math.pi - 0.2), arc(0, -2, 17, 21, math.pi + 0.2, TAU - 0.2)], mat=P.GOLD,
          bevel=1),
        L([circle(0, 0, 9)], mat=P.MAGENTA, profile="round", spec=0.7),
        L([circle(-2, -2, 4)], emit=(255, 150, 230), glow=1.2),
        L([circle(x, y, 1.6) for x, y in ((-26, 6), (26, 6), (-18, 16), (18, 16), (0, 20))], emit=P.RED_E, glow=0.8),
    ], halo=4, want_shadow=True)


class SkyllaHead(Part):
    HP = 34
    SCORE = 2000
    RADIUS = 8
    EXPLO = 0.9
    counts = True

    def setup(self, owner=None, ang=0.0, idx=0, **kw):
        Part.setup(self, owner=owner)
        self.ang = ang
        self.idx = idx
        self.ext = 0.0
        self.lunge = 0
        self.aim_a = math.pi / 2

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
        w = self.w
        p = w.player
        base_a = self.ang + math.sin(self.t * 0.03 + self.idx) * 0.25
        L_ = 30 + self.ext
        ax, ay = o.x + math.cos(self.ang) * 18, o.y + math.sin(self.ang) * 12
        self.anchor = (ax, ay)
        tx, ty = ax + math.cos(base_a) * L_, ay + math.sin(base_a) * L_
        if self.lunge > 0:
            self.lunge -= 1
            k = math.sin((1 - self.lunge / 40) * math.pi)
            self.ext = 26 * k
        else:
            self.ext *= 0.9
        self.x += (tx - self.x) * 0.2
        self.y += (ty - self.y) * 0.2
        want = math.atan2(p.y - self.y, p.x - self.x)
        self.aim_a += clamp(angle_diff(self.aim_a, want), -0.08, 0.08)
        if not o.dying and o.entered_fight:
            period = int(150 / w.diff["rate"])
            if (self.t + self.idx * 25) % period == 0 and self.can_fire():
                self.lunge = 40
            if self.lunge == 20 and self.can_fire():
                w.bullets.arc(self.x, self.y, self.aim_a, w.bullets.dens(3), 0.4, 2.3, "rice", "green")
                w.audio.play("eshot2", self.x, 0.7)

    def draw(self, surf):
        o = self.owner
        ax, ay = getattr(self, "anchor", (o.x, o.y))
        n = 5
        seg = S["serpent_seg"]
        for i in range(1, n):
            k = i / n
            mx = ax + (self.x - ax) * k + math.sin(k * math.pi) * 3
            my = ay + (self.y - ay) * k
            seg.draw(surf, mx, my, self.flash > 0)
        S["serpent_head"][rot_index(self.aim_a, NTUR)].draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        S["serpent_head"][rot_index(self.aim_a, NTUR)].draw_halo(add, self.x, self.y)

    def image(self):
        return S["serpent_head"][0].img


class Skylla(Boss):
    NAME = "ΣΚΥΛΛΑ · SKYLLA"
    CARD = ("ΣΚΥΛΛΑ", "LA DÉVOREUSE AUX SIX TÊTES")
    HP = 260
    SCORE = 20000
    RADIUS = 14
    MID = True
    EXPLO = 2.0

    def setup(self, **kw):
        self.spr = bs("skylla", _skylla_body)
        self.hitboxes = [(0, 0, 16, 11)]
        self.heads = []
        for i in range(6):
            a = math.pi / 2 + (i - 2.5) * 0.52
            h = self.add_part(SkyllaHead(self.w, self.x, self.y, owner=self, ang=a, idx=i))
            self.heads.append(h)
        self.timeout = 60 * 45

    def ARMOR_NOW(self):
        return sum(1 for h in self.heads if not h.dead) > 2

    def sprite(self):
        return self.spr

    def death_span(self):
        return (28, 18)

    def behave(self):
        w = self.w
        yield from move_to(self, PF_W / 2, 64, 120, ease_out_cubic)
        self.entered_fight = True
        rot = 0.0
        k = 0
        while True:
            k += 1
            self.x = PF_W / 2 + math.sin(k * 0.012) * 50
            self.y = 64 + math.sin(k * 0.021) * 8
            alive = sum(1 for h in self.heads if not h.dead)
            if alive <= 2 and k % int(8 / w.diff["rate"] + 0.5) == 0 and self.can_fire():
                rot += 0.23
                for j in range(2):
                    w.bullets.fire(self.x, self.y + 4, rot + j * math.pi, 1.7, "m", "pink")
                if k % 24 == 0:
                    w.audio.play("eshot", self.x, 0.5)
            if k % int(110 / w.diff["rate"]) == 60 and self.can_fire():
                self.ring(self.x, self.y, 14, 1.4, "l", "violet", off=k * 0.1)
                w.audio.play("eshot_big", self.x)
            if k > self.timeout:
                break
            yield
        # fuite
        self.entered_fight = False
        yield from move_to(self, self.x, -80, 90, ease_in_cubic)
        self.gone = True
        self.dead = True
        for h in self.heads:
            h.dead = True

    def draw(self, surf):
        self.spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        self.spr.draw_halo(add, self.x, self.y)
        if not self.ARMOR_NOW():
            k = 0.5 + 0.5 * math.sin(self.t * 0.2)
            g = glow(14, (int(120 * k), int(30 * k), int(100 * k)))
            add.blit(g, (int(self.x - 14), int(self.y - 14)), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------------------
# STADE I — KÉTOS : le monstre marin de Poséidon
# ---------------------------------------------------------------------------
def _ketos_head(open_=0.0):
    jaw = 3 + open_ * 7
    return forge(81, 81, [
        # nageoires latérales
        L([[(12, -14), (34, -24), (38, -16), (30, -6), (16, -2)]], mat=P.BRONZE, bevel=2, mirror=True),
        L([line(16, -10, 34, -20, 1.2), line(17, -6, 32, -12, 1.2)], mat=P.GOLD, bevel=1, mirror=True),
        # mâchoire inférieure
        L([sym([(0, 36 + jaw), (6, 34 + jaw), (12, 26 + jaw * 0.6), (14, 12), (8, 10), (0, 12)])],
          mat=P.VERDIGRIS, bevel=2),
        L([[(4 + i * 2.4, 31 + jaw - i * 3.2), (5.2 + i * 2.4, 27 + jaw - i * 3.2), (6.2 + i * 2.4, 31 + jaw - i * 3.2)]
           for i in range(4)], flat=(250, 244, 230), mirror=True),
        # gueule (lueur) visible quand ouverte
        L([sym([(0, 30 + jaw * 0.5), (7, 24), (8, 14), (0, 12)])], emit=(255, 80, 60) if open_ > 0.2 else (90, 20, 20),
          glow=1.4 * open_),
        # crâne
        L([sym([(0, -30), (8, -28), (15, -20), (18, -6), (16, 8), (11, 22), (6, 30), (0, 32)])], mat=P.VERDIGRIS,
          bevel=3, spec=0.4),
        L([sym([(0, -26), (4, -24), (6, -10), (5, 14), (0, 20)])], mat=P.GOLD, bevel=1.5, spec=0.5),
        L([[(9, -22), (13, -30), (14, -18)], [(14, -12), (20, -20), (18, -6)]], mat=P.GOLD, bevel=1, mirror=True),
        # yeux
        L([ellipse(10.5, 4, 2.6, 3.8, 0.3)], mat=P.EBONY, bevel=1, mirror=True),
        L([ellipse(10.5, 4.5, 1.5, 2.6, 0.3)], emit=P.RED_E, glow=1.4, mirror=True),
    ], halo=4, want_shadow=True)


def _ketos_seg(r):
    return forge(int(r * 2 + 8), int(r * 2 + 8), [
        L([[(r * 0.4, -r * 0.4), (r + 3, -r * 0.1), (r * 0.5, r * 0.5)]], mat=P.BRONZE, bevel=1, mirror=True),
        L([circle(0, 0, r)], mat=P.VERDIGRIS, profile="round", spec=0.35),
        L([circle(0, 0, r * 0.62)], mat=P.VERDIGRIS, bevel=1.5, base=0.5),
        L([sym([(0, -r * 0.9), (r * 0.25, 0), (0, r * 0.5)])], mat=P.GOLD, bevel=1),
    ], halo=0, want_shadow=True)


def _ketos_tail():
    return forge(41, 31, [
        L([[(0, -8), (8, -2), (18, 10), (16, 13), (6, 6), (0, 4)]], mat=P.BRONZE, bevel=1.5, mirror=True),
        L([line(2, -2, 15, 10, 1.0)], mat=P.GOLD, bevel=1, mirror=True),
        L([circle(0, -6, 5)], mat=P.VERDIGRIS, profile="round"),
    ], halo=0, want_shadow=True)


class KetosSeg(Part):
    HP = 9999
    RADIUS = 9
    BODY = True
    counts = False

    def setup(self, owner=None, idx=0, r=10, **kw):
        Part.setup(self, owner=owner)
        self.idx = idx
        self.r = r
        self.RADIUS = r * 0.9
        self.angle = math.pi / 2
        self.spr = bs(f"ketos_seg{r}", lambda: _ketos_seg(r))

    def targetable(self):
        return False

    def update(self):
        self.t += 1
        o = self.owner
        if o.dead:
            self.dead = True
            return
        k = (self.idx + 1) * 7
        tr = o.trail
        if len(tr) > k:
            nx, ny = tr[-k]
            if len(tr) > k + 2:
                px, py = tr[-k - 2]
                self.angle = math.atan2(ny - py, nx - px)
            self.x, self.y = nx, ny

    def draw_shadow(self, surf):
        if not self.owner.submerged:
            Enemy.draw_shadow(self, surf)

    def draw(self, surf):
        pass

    def draw_seg(self, surf):
        if self.owner.submerged:
            img = self.spr.img
            img.set_alpha(70)
            surf.blit(img, (int(self.x - self.spr.ox), int(self.y - self.spr.oy)))
            img.set_alpha(255)
        else:
            self.spr.draw(surf, self.x, self.y)

    def collide(self, x, y, r):
        if self.owner.submerged:
            return False
        return Enemy.collide(self, x, y, r)


class Ketos(Boss):
    NAME = "ΚΗΤΟΣ · KÉTOS"
    CARD = ("ΚΗΤΟΣ", "LE MONSTRE DES ABYSSES")
    HP = 1650
    SCORE = 100000
    RADIUS = 16

    def setup(self, **kw):
        self.heads = [bs("ketos_h0", lambda: _ketos_head(0.0)), bs("ketos_h1", lambda: _ketos_head(0.5)),
                      bs("ketos_h2", lambda: _ketos_head(1.0))]
        self.tail_spr = bs("ketos_tail", _ketos_tail)
        self.open = 0.0
        self.trail = []
        self.submerged = False
        self.segs = []
        n = 12
        for i in range(n):
            r = int(12 - i * 0.55)
            self.segs.append(self.add_part(KetosSeg(self.w, self.x, self.y, owner=self, idx=i, r=r)))
        self.hitboxes = [(0, 4, 14, 20)]
        self.want_open = 0.0

    def ARMOR_NOW(self):
        return self.submerged

    def sprite(self):
        i = 0 if self.open < 0.3 else 1 if self.open < 0.7 else 2
        return self.heads[i]

    def death_span(self):
        return (20, 26)

    def mouth(self):
        return self.x, self.y + 30

    def update(self):
        Boss.update(self)
        self.trail.append((self.x, self.y))
        if len(self.trail) > 300:
            del self.trail[:100]
        self.open += (self.want_open - self.open) * 0.15

    def behave(self):
        w = self.w
        # émergence
        self.submerged = True
        self.x, self.y = PF_W / 2, -70
        yield from move_to(self, PF_W / 2, 30, 60)
        w.audio.play("splash")
        w.audio.play("roar")
        w.juice.shake(0.5)
        for i in range(20):
            w.fx.add(Particle(K_GLOW, self.x + random.uniform(-30, 30), self.y + random.uniform(-10, 30),
                              random.uniform(-1, 1), random.uniform(-2, 0.5), 30, 6, 1, (120, 220, 255)))
        self.submerged = False
        yield from move_to(self, PF_W / 2, 70, 60, ease_out_cubic)
        self.entered_fight = True
        while True:
            f = self.hp / self.max_hp
            if f > 0.62:
                yield from self.phase1()
            elif f > 0.3:
                yield from self.phase2()
            else:
                yield from self.phase3()

    def sway(self, k, cx=PF_W / 2, cy=70, ax=70, ay=14):
        self.x = cx + math.sin(k * 0.017) * ax
        self.y = cy + math.sin(k * 0.031) * ay

    def phase1(self):
        w = self.w
        for k in range(360):
            self.sway(self.t)
            if k % int(70 / w.diff["rate"]) == 20 and self.can_fire():
                self.want_open = 1.0
            if k % int(70 / w.diff["rate"]) == 34 and self.can_fire():
                mx, my = self.mouth()
                self.spread(mx, my, 5, 0.8, 2.3, "l", "pink")
                self.spread(mx, my, 4, 0.6, 1.7, "m", "pink")
                w.audio.play("eshot_big", mx)
            if k % int(70 / w.diff["rate"]) == 50:
                self.want_open = 0.0
            if 150 <= k < 260 and k % 5 == 0 and self.can_fire():
                # jets d'eau tournoyants
                a = k * 0.09
                for s in (-1, 1):
                    w.bullets.fire(self.x + s * 16, self.y + 8, math.pi / 2 + s * math.sin(a) * 1.1, 2.2, "rice",
                                   "blue")
                if k % 15 == 0:
                    w.audio.play("wave", self.x, 0.5, throttle=8)
            if k % 120 == 100:
                for sgm in self.segs[2::3]:
                    if 0 < sgm.y < PF_H - 60:
                        w.bullets.fire(sgm.x, sgm.y, math.atan2(w.player.y - sgm.y, w.player.x - sgm.x), 1.8, "s",
                                       "violet")
            if self.hp / self.max_hp <= 0.62:
                return
            yield

    def phase2(self):
        w = self.w
        # plongée
        self.want_open = 0.0
        w.audio.play("splash", self.x)
        for i in range(30):
            w.fx.add(Particle(K_GLOW, self.x + random.uniform(-20, 20), self.y + random.uniform(-10, 10),
                              random.uniform(-1.5, 1.5), random.uniform(-2.5, 0), 26, 5, 1, (120, 220, 255)))
        self.submerged = True
        yield from move_to(self, self.x, self.y + 30, 30)
        side = random.choice((-1, 1))
        yield from move_to(self, PF_W / 2 - side * 170, 150, 50)
        # bulles d'avertissement le long de la trajectoire
        for i in range(40):
            if i % 3 == 0:
                x = PF_W / 2 + side * (i * 5 - 100)
                w.fx.ring(x, 150 + random.uniform(-10, 10), 2, 10, 16, (100, 200, 255), 1)
            yield
        # charge en surface
        self.submerged = False
        w.audio.play("roar", self.x)
        w.audio.play("splash", self.x)
        self.want_open = 1.0
        for i in range(60):
            self.x += side * 5.8
            self.y = 150 - math.sin(i / 60 * math.pi) * 70
            if i % 6 == 0 and self.can_fire():
                w.bullets.fire(self.x, self.y, math.pi / 2, 1.2, "m", "blue")
                w.bullets.fire(self.x, self.y, -math.pi / 2, 1.0, "m", "blue", acc=0.03, maxspd=2.0)
            yield
        self.want_open = 0.3
        yield from move_to(self, PF_W / 2, 70, 60, ease_in_out)
        # salves en couronne
        for r in range(3):
            if self.can_fire():
                mx, my = self.mouth()
                self.ring(mx, my, 20, 1.5, "m", "pink", off=r * 0.16)
                self.spread(mx, my, 3, 0.3, 2.8, "needle", "pink")
                w.audio.play("eshot_big", mx)
                self.want_open = 1.0
            yield from wait(35)
            self.want_open = 0.2
        yield from wait(30)

    def phase3(self):
        w = self.w
        self.want_open = 1.0
        rot = 0.0
        for k in range(600):
            t = self.t
            self.x = PF_W / 2 + math.sin(t * 0.02) * 60
            self.y = 76 + math.sin(t * 0.04) * 20
            mx, my = self.mouth()
            if k % 4 == 0 and self.can_fire():
                rot += 0.21
                for j in range(3):
                    w.bullets.fire(mx, my, rot + j * TAU / 3, 1.6, "rice", "pink")
                    w.bullets.fire(mx, my, -rot * 0.8 + j * TAU / 3 + 0.5, 1.3, "s", "blue")
            if k % int(90 / w.diff["rate"]) == 45 and self.can_fire():
                self.spread(mx, my, 7, 1.0, 2.6, "l", "violet")
                w.audio.play("eshot_big", mx)
            if k % 20 == 0:
                w.audio.play("eshot", mx, 0.5)
            yield

    def draw(self, surf):
        # queue puis anneaux (du plus loin au plus proche), puis la tête
        if self.segs:
            tr = self.trail
            k = (len(self.segs) + 1) * 7
            if len(tr) > k:
                tx, ty = tr[-k]
                img = self.tail_spr
                if self.submerged:
                    img.img.set_alpha(70)
                    surf.blit(img.img, (int(tx - img.ox), int(ty - img.oy)))
                    img.img.set_alpha(255)
                else:
                    img.draw(surf, tx, ty)
        for s in reversed(self.segs):
            if not s.dead:
                s.draw_seg(surf)
        spr = self.sprite()
        if self.submerged:
            spr.img.set_alpha(80)
            surf.blit(spr.img, (int(self.x - spr.ox), int(self.y - spr.oy)))
            spr.img.set_alpha(255)
        else:
            spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        if not self.submerged:
            self.sprite().draw_halo(add, self.x, self.y)
            if self.open > 0.4:
                mx, my = self.mouth()
                g = glow(int(8 + 6 * self.open), (int(160 * self.open), int(40 * self.open), 20), 0.5 * self.open)
                add.blit(g, (int(mx - g.get_width() // 2), int(my - 8 - g.get_height() // 2)),
                         special_flags=pygame.BLEND_ADD)
