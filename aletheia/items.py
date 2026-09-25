"""Objets : ambroisie (P), orbes divins cycliques, drachmes, foudre (bombe), couronne de laurier (1UP),
étincelles d'or (balles annulées)."""
import math
import random

import pygame

from . import palette as P
from .sprites import S, GODS
from .fx import glow, Particle, K_GLOW, K_SPARK, K_FLARE, K_RING

PF_W, PF_H = 256, 270


class Item:
    __slots__ = ("w", "x", "y", "vx", "vy", "kind", "god", "gi", "t", "alive", "magnet", "life")

    def __init__(self, w, x, y, kind, god=None, vx=None, vy=None):
        self.w = w
        self.x = x
        self.y = y
        self.kind = kind
        self.t = 0
        self.alive = True
        self.magnet = False
        self.life = 60 * 14
        if kind == "orb":
            self.gi = GODS.index(god) if god in GODS else random.randrange(len(GODS))
            self.god = GODS[self.gi]
            self.vx = random.choice((-0.5, 0.5)) if vx is None else vx
            self.vy = -1.2 if vy is None else vy
        elif kind == "spark":
            a = random.random() * math.tau
            self.vx = math.cos(a) * 1.5
            self.vy = math.sin(a) * 1.5
            self.gi = 0
            self.god = None
        else:
            self.gi = 0
            self.god = None
            self.vx = random.uniform(-1.2, 1.2) if vx is None else vx
            self.vy = random.uniform(-2.4, -1.2) if vy is None else vy

    def update(self):
        w = self.w
        p = w.player
        self.t += 1
        k = self.kind
        if k == "orb":
            # dérive lente et rebonds latéraux, façon Compile ; le dieu change régulièrement
            self.vy = min(0.42, self.vy + 0.04)
            self.x += self.vx
            self.y += self.vy + w.scroll * 0.3
            if self.x < 12 or self.x > PF_W - 12:
                self.vx = -self.vx
                self.x = max(12, min(PF_W - 12, self.x))
            if self.t > 40 and self.t % 120 == 0:
                self.gi = (self.gi + 1) % len(GODS)
                self.god = GODS[self.gi]
                w.fx.ring(self.x, self.y, 4, 16, 12, P.GOD_COLORS[self.god], 2)
                w.audio.play("tick", self.x, 0.6, throttle=2)
            if self.y > PF_H + 12:
                self.alive = False
        else:
            if not p.dead:
                d2 = (p.x - self.x) ** 2 + (p.y - self.y) ** 2
                if k == "spark" and self.t > 12:
                    self.magnet = True
                elif d2 < 44 * 44 or (p.y < 78 and p.control) or p.bomb is not None:
                    self.magnet = True
            if self.magnet and not p.dead:
                a = math.atan2(p.y - self.y, p.x - self.x)
                sp = min(9.0, 2.5 + self.t * 0.08)
                self.vx += (math.cos(a) * sp - self.vx) * 0.25
                self.vy += (math.sin(a) * sp - self.vy) * 0.25
            else:
                self.vx *= 0.96
                self.vy = min(1.1, self.vy + 0.06)
                if k == "spark":
                    self.vx *= 0.9
                    self.vy *= 0.9
            self.x += self.vx
            self.y += self.vy
            if self.y > PF_H + 12 or self.t > self.life:
                self.alive = False
        # ramassage
        if not p.dead and p.control:
            rr = 14 if k != "orb" else 13
            if (p.x - self.x) ** 2 + (p.y - self.y) ** 2 < rr * rr:
                self.collect()

    def collect(self):
        w = self.w
        p = w.player
        self.alive = False
        k = self.kind
        if k == "p":
            p.add_chip()
            w.audio.play("pickup", self.x, 0.8)
            w.fx.add(Particle(K_FLARE, self.x, self.y, 0, 0, 8, 6, 2, (255, 190, 70)))
            w.score.add(50, popup=False)
        elif k == "orb":
            p.set_weapon(self.god)
        elif k == "coin":
            pts = w.score.add(100, self.x, self.y, popup=False)
            w.score.coins += 1
            w.audio.play("coin", self.x, 0.7, throttle=2)
            w.fx.add(Particle(K_FLARE, self.x, self.y, 0, -0.5, 7, 4, 1, (255, 230, 120)))
            w.popup_tiny(self.x, self.y - 6, str(pts), (255, 230, 140))
        elif k == "bomb":
            p.bombs = min(6, p.bombs + 1)
            w.audio.play("powerup", self.x)
            w.popup(self.x, self.y - 14, "THÉOPHANIE +1", (160, 210, 255))
        elif k == "oneup":
            p.lives += 1
            w.audio.play("oneup")
            w.popup(self.x, self.y - 14, "VIE +1 !", (170, 255, 150), 60)
            w.fx.ring(self.x, self.y, 4, 60, 30, (170, 255, 150), 3)
        elif k == "spark":
            w.score.add(20, popup=False)
            w.audio.play("coin", self.x, 0.25, throttle=4)

    def draw(self, surf):
        k = self.kind
        if k == "orb":
            spr = S["orb"][self.god]
            bob = math.sin(self.t * 0.12) * 1.5
            spr.draw(surf, self.x, self.y + bob)
            if self.t > 40 and self.t % 120 > 96 and (self.t // 3) % 2:
                spr.draw(surf, self.x, self.y + bob, True)
        elif k == "p":
            spr = S["pchip"]
            spr.draw(surf, self.x, self.y)
        elif k == "coin":
            spr = S["coin"][(self.t // 4) % 4]
            spr.draw(surf, self.x, self.y)
        elif k == "bomb":
            S["bomb_item"].draw(surf, self.x, self.y)
        elif k == "oneup":
            S["oneup"].draw(surf, self.x, self.y + math.sin(self.t * 0.1) * 1.5)

    def draw_add(self, add):
        k = self.kind
        if k == "spark":
            g = glow(3, (255, 210, 90), 0.6)
            add.blit(g, (int(self.x - 3), int(self.y - 3)), special_flags=pygame.BLEND_ADD)
        elif k == "orb":
            spr = S["orb"][self.god]
            spr.draw_halo(add, self.x, self.y)
            c = P.GOD_COLORS[self.god]
            r = 11 + math.sin(self.t * 0.15) * 1.5
            pygame.draw.circle(add, (c[0] // 4, c[1] // 4, c[2] // 4), (int(self.x), int(self.y)), int(r), 1)
        elif k == "p":
            S["pchip"].draw_halo(add, self.x, self.y)
        elif k == "oneup":
            S["oneup"].draw_halo(add, self.x, self.y)
        elif k == "bomb":
            S["bomb_item"].draw_halo(add, self.x, self.y)
