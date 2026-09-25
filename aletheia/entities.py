"""Entités de base : ennemis (comportements en générateurs), balles ennemies, motifs de tir."""
import math
import random

import pygame

from .sprites import S, NROT, BCOL
from .spritegen import rot_index
from .fx import glow, Particle, K_GLOW
from .util import TAU, ease_in_out, catmull

PF_W, PF_H = 256, 270


# ---------------------------------------------------------------------------
# Helpers de comportement (à utiliser avec « yield from »)
# ---------------------------------------------------------------------------
def wait(n):
    for _ in range(int(n)):
        yield


def move_to(e, x, y, frames, ease=ease_in_out):
    e.vx = e.vy = 0.0
    x0, y0 = e.x, e.y
    frames = max(1, int(frames))
    for i in range(1, frames + 1):
        t = ease(i / frames)
        e.x = x0 + (x - x0) * t
        e.y = y0 + (y - y0) * t
        yield


def follow(e, pts, frames, ease=None):
    """Suit une spline Catmull-Rom passant par pts."""
    e.vx = e.vy = 0.0
    frames = max(1, int(frames))
    px, py = e.x, e.y
    for i in range(1, frames + 1):
        t = i / frames
        if ease:
            t = ease(t)
        x, y = catmull(pts, t)
        e.face = math.atan2(y - py, x - px) if (x != px or y != py) else getattr(e, "face", math.pi / 2)
        px, py = x, y
        e.x, e.y = x, y
        yield


def drift(e, vx, vy, frames=None):
    e.vx, e.vy = vx, vy
    n = 0
    while frames is None or n < frames:
        n += 1
        yield


# ---------------------------------------------------------------------------
# Ennemi de base
# ---------------------------------------------------------------------------
class Enemy:
    HP = 1
    SCORE = 100
    RADIUS = 7
    SPRITE = None
    GROUND = False
    EXPLO = 0.7          # taille d'explosion
    COINS = 0
    PCHIPS = 0
    ARMOR = False        # insensible (les tirs rebondissent)
    BODY = True          # collision avec le joueur
    SHADOW = True
    BOSSPART = False
    OWNER_DRAWS = False  # partie de boss dessinée par-dessus le corps
    KILL_SFX = "explo_s"

    def __init__(self, w, x, y, **kw):
        self.w = w
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.t = 0
        self.dead = False
        self.gone = False
        self.flash = 0
        self.flash_cd = 0
        self.entered = False
        self.face = math.pi / 2
        self.hp = self.HP * kw.pop("hpmul", 1.0)
        self.max_hp = self.hp
        self.hitboxes = None     # liste (dx, dy, hw, hh) ; sinon cercle RADIUS
        self.parent = None
        self.invuln = 0
        self.drop = kw.pop("drop", None)
        self.kw = kw
        self.brain = None
        self.setup(**kw)
        self.brain = self.behave()

    # --- à surcharger ---------------------------------------------------------
    def setup(self, **kw):
        pass

    def behave(self):
        yield from drift(self, 0, 1.2)

    def on_death(self):
        pass

    # --- cycle de vie -------------------------------------------------------------
    def update(self):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.flash_cd > 0:
            self.flash_cd -= 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.brain is not None:
            try:
                next(self.brain)
            except StopIteration:
                self.brain = None
        self.x += self.vx
        self.y += self.vy
        if self.GROUND:
            self.y += self.w.scroll
        m = 24 + self.RADIUS
        inside = -m < self.x < PF_W + m and -m < self.y < PF_H + m
        if inside and 0 <= self.x <= PF_W and 0 <= self.y <= PF_H:
            self.entered = True
        if self.entered and not inside and not self.BOSSPART:
            self.gone = True
        elif not self.entered and self.t > 900:
            self.gone = True

    @property
    def onscreen(self):
        return -4 < self.x < PF_W + 4 and -4 < self.y < PF_H + 4

    def collide(self, x, y, r):
        if self.hitboxes:
            for (dx, dy, hw, hh) in self.hitboxes:
                if abs(x - (self.x + dx)) < hw + r and abs(y - (self.y + dy)) < hh + r:
                    return True
            return False
        rr = self.RADIUS + r
        dx, dy = x - self.x, y - self.y
        return dx * dx + dy * dy < rr * rr

    def hit(self, dmg, x=None, y=None, silent=False):
        """Retourne True si des dégâts ont été infligés."""
        if self.dead:
            return False
        w = self.w
        if self.ARMOR or self.invuln > 0 or not self.targetable():
            if not silent and x is not None and w.t % 4 == 0:
                w.fx.hit(x, y, (200, 200, 255), 2)
                w.audio.play("tink", x, 0.6, throttle=5)
            return False
        self.hp -= dmg
        if self.flash_cd <= 0:
            self.flash = 2
            self.flash_cd = 7 if self.BOSSPART else 4
        w.score.touch()
        if self.BOSSPART:
            w.score.dmg_points(dmg)
        if not silent and x is not None:
            if random.random() < 0.35:
                w.fx.hit(x, y, (255, 230, 170), 2)
            w.audio.play("hit", x, 0.5, throttle=3)
        if self.hp <= 0:
            self.die()
        return True

    def targetable(self):
        return self.onscreen

    def armored(self):
        return self.ARMOR

    def die(self, quiet=False):
        if self.dead:
            return
        self.dead = True
        w = self.w
        w.score.kill(self)
        if not quiet:
            debris = w.fx.debris_from(self.image(), 4 if self.EXPLO < 1 else 7) if self.EXPLO >= 0.9 else None
            w.fx.explosion(self.x, self.y, self.EXPLO, debris=debris, vx=self.vx * 0.5,
                           vy=self.vy * 0.5 + (w.scroll if self.GROUND else 0))
            w.audio.play(self.KILL_SFX, self.x)
            w.juice.shake(0.06 + 0.1 * self.EXPLO)
            if self.GROUND:
                w.bg.add_scorch(self.x, self.y, self.RADIUS)
        # objets
        if self.COINS:
            w.drop_coins(self.x, self.y, self.COINS)
        if self.PCHIPS:
            w.drop_items(self.x, self.y, "p", self.PCHIPS)
        if self.drop:
            w.drop_items(self.x, self.y, self.drop, 1)
        self.on_death()

    # --- rendu ------------------------------------------------------------------------
    def image(self):
        spr = self.sprite()
        return spr.img if spr else pygame.Surface((4, 4))

    def sprite(self):
        s = self.SPRITE
        return S[s] if isinstance(s, str) else s

    def draw_shadow(self, surf):
        spr = self.sprite()
        if spr is not None and spr.shadow is not None and self.w.bg.shadows:
            spr.draw_shadow(surf, self.x + 9, self.y + 13)

    def draw(self, surf):
        spr = self.sprite()
        if spr is not None:
            spr.draw(surf, self.x, self.y, self.flash > 0)

    def draw_add(self, add):
        spr = self.sprite()
        if spr is not None and spr.halo is not None:
            spr.draw_halo(add, self.x, self.y)

    # --- tirs -----------------------------------------------------------------------------
    def aim(self):
        p = self.w.player
        return math.atan2(p.y - self.y, p.x - self.x)

    def can_fire(self):
        """Pas de tir hors écran ni trop près du bas (équité)."""
        return 6 < self.x < PF_W - 6 and 4 < self.y < PF_H - 50 and not self.w.player_dead_pause


# ---------------------------------------------------------------------------
# Balles ennemies
# ---------------------------------------------------------------------------
BULLET_R = {"s": 2.0, "m": 2.6, "l": 3.6, "xl": 5.6, "ring": 3.6, "rice": 1.9, "needle": 1.4, "feather": 2.0,
            "arrow": 1.8, "star": 3.0}
ORIENTED = {"rice", "needle", "feather", "arrow"}


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "r", "kind", "col", "frames", "spr", "ang", "spd", "acc", "maxspd",
                 "minspd", "turn", "t", "delay", "grazed", "alive", "wave", "retarget", "ri", "curve")

    def __init__(self, x, y, ang, spd, kind="m", col="pink", acc=0.0, maxspd=9.0, minspd=0.0, turn=0.0,
                 delay=0, retarget=0, wave=0.0):
        self.x = x
        self.y = y
        self.ang = ang
        self.spd = spd
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd
        self.kind = kind
        self.col = col
        self.r = BULLET_R.get(kind, 2.5)
        self.acc = acc
        self.maxspd = maxspd
        self.minspd = minspd
        self.turn = turn
        self.t = 0
        self.delay = delay
        self.grazed = False
        self.alive = True
        self.retarget = retarget
        self.wave = wave
        self.curve = bool(acc or turn or wave)
        if kind in ORIENTED:
            key = "b_feather" if kind == "feather" else "b_arrow" if kind == "arrow" else f"b_{kind}_{col}"
            self.frames = S.get(key) or S["b_rice_pink"]
            self.spr = None
            self.ri = rot_index(ang, NROT)
        elif kind == "star":
            self.frames = S.get(f"b_star_{col}") or S["b_star_gold"]
            self.spr = None
            self.ri = 0
        else:
            self.frames = None
            self.spr = S.get(f"b_{kind}_{col}") or S["b_m_pink"]
            self.ri = 0


class Bullets:
    def __init__(self, w):
        self.w = w
        self.list = []

    def clear(self):
        self.list.clear()

    def add(self, b):
        if len(self.list) < 900:
            self.list.append(b)
        return b

    def fire(self, x, y, ang, spd, kind="m", col="pink", **kw):
        w = self.w
        return self.add(Bullet(x, y, ang, spd * w.diff["bspeed"], kind, col, **kw))

    def aimed(self, x, y, spd, n=1, spread=0.0, kind="m", col="pink", offset=0.0, **kw):
        a = math.atan2(self.w.player.y - y, self.w.player.x - x) + offset
        return self.arc(x, y, a, n, spread, spd, kind, col, **kw)

    def arc(self, x, y, ang, n, spread, spd, kind="m", col="pink", **kw):
        out = []
        if n <= 1:
            out.append(self.fire(x, y, ang, spd, kind, col, **kw))
            return out
        for i in range(n):
            a = ang - spread / 2 + spread * i / (n - 1)
            out.append(self.fire(x, y, a, spd, kind, col, **kw))
        return out

    def ring(self, x, y, n, spd, kind="m", col="pink", offset=0.0, **kw):
        out = []
        for i in range(n):
            out.append(self.fire(x, y, offset + i * TAU / n, spd, kind, col, **kw))
        return out

    def dens(self, n):
        return max(1, int(round(n * self.w.diff["density"])))

    def update(self):
        w = self.w
        p = w.player
        alive = []
        ap = alive.append
        px, py = p.x, p.y
        hit_r = p.HIT_R
        graze_r = p.GRAZE_R
        can_hit = p.vulnerable()
        for b in self.list:
            b.t += 1
            if b.delay > 0:
                b.delay -= 1
                if b.delay == 0 and b.retarget:
                    a = math.atan2(py - b.y, px - b.x)
                    b.ang = a
                    b.spd = b.retarget
                    b.vx = math.cos(a) * b.spd
                    b.vy = math.sin(a) * b.spd
                    if b.frames is not None and b.kind != "star":
                        b.ri = rot_index(a, NROT)
                ap(b)
                continue
            if b.curve:
                if b.acc:
                    b.spd = min(b.maxspd, max(b.minspd, b.spd + b.acc))
                if b.turn:
                    b.ang += b.turn
                if b.wave:
                    b.ang += math.sin(b.t * 0.12) * b.wave
                b.vx = math.cos(b.ang) * b.spd
                b.vy = math.sin(b.ang) * b.spd
                if b.frames is not None and b.kind != "star":
                    b.ri = rot_index(b.ang, NROT)
            b.x += b.vx
            b.y += b.vy
            x, y = b.x, b.y
            if x < -24 or x > PF_W + 24 or y < -24 or y > PF_H + 24:
                if b.t > 20 or y > PF_H + 24:
                    continue
            dx = x - px
            dy = y - py
            d2 = dx * dx + dy * dy
            if d2 < 400:
                rr = b.r + hit_r
                if can_hit and d2 < rr * rr:
                    w.player_hit(b)
                    continue
                if not b.grazed and d2 < graze_r * graze_r and can_hit:
                    b.grazed = True
                    w.graze(b)
            ap(b)
        self.list = alive

    def draw(self, surf):
        blits = []
        for b in self.list:
            if b.frames is not None:
                if b.kind == "star":
                    spr = b.frames[(b.t // 3) % len(b.frames)]
                else:
                    spr = b.frames[b.ri]
            else:
                spr = b.spr
            blits.append((spr.img, (int(b.x - spr.ox), int(b.y - spr.oy))))
        if blits:
            surf.blits(blits, doreturn=False)

    def draw_add(self, add):
        """Petits halos pour les grosses balles (le bloom fait le reste)."""
        blits = []
        badd = pygame.BLEND_ADD
        for b in self.list:
            if b.kind in ("l", "xl", "ring", "star"):
                c = BCOL.get(b.col, (255, 80, 180))
                r = 7 if b.kind != "xl" else 11
                g = glow(r, (c[0] * 0.45, c[1] * 0.45, c[2] * 0.45))
                blits.append((g, (int(b.x - r), int(b.y - r)), None, badd))
        if blits:
            add.blits(blits, doreturn=False)

    def cancel(self, to_score=True, x=None, y=None, radius=None):
        """Annule des balles (bombe, mort d'un boss) -> étincelles d'or rapportant des points."""
        w = self.w
        keep = []
        n = 0
        for b in self.list:
            if radius is not None:
                dx, dy = b.x - x, b.y - y
                if dx * dx + dy * dy > radius * radius:
                    keep.append(b)
                    continue
            n += 1
            if to_score and n <= 220:
                w.spawn_spark(b.x, b.y)
            elif n <= 300:
                w.fx.add(Particle(K_GLOW, b.x, b.y, 0, 0, 10, 4, 1, (255, 200, 240)))
        self.list = keep
        return n
