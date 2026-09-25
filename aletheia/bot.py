"""Pilote automatique rudimentaire (démo et tests sans écran) : esquive par champ de répulsion."""
import math
import random

from .inputs import ACTIONS
from .enemies import seg_dist

PF_W, PF_H = 256, 270


class Bot:
    def __init__(self, g):
        self.g = g
        self.t = 0
        self.jx = 0.0

    def actions(self):
        g = self.g
        p = g.player
        self.t += 1
        act = {a: False for a in ACTIONS}
        act["fire"] = True
        act["confirm"] = self.t % 40 == 0
        if p.dead or not p.control:
            return act
        fx = fy = 0.0
        danger = 0.0
        for b in g.bullets.list:
            dx = p.x - (b.x + b.vx * 6)
            dy = p.y - (b.y + b.vy * 6)
            d2 = dx * dx + dy * dy
            if d2 < 55 * 55:
                wgt = 1.0 / max(d2, 9.0)
                fx += dx * wgt * 90
                fy += dy * wgt * 90
                danger = max(danger, 1.0 / max(d2, 1.0))
        for h in g.hazards:
            d = seg_dist(p.x, p.y, h.x0, h.y0, h.x1, h.y1)
            if d < 30:
                vx, vy = h.x1 - h.x0, h.y1 - h.y0
                ln = math.hypot(vx, vy) or 1
                nx, ny = -vy / ln, vx / ln
                side = 1 if (p.x - h.x0) * nx + (p.y - h.y0) * ny > 0 else -1
                fx += nx * side * 3
                fy += ny * side * 3
        for e in g.enemies:
            if e.BODY and not e.GROUND and not e.dead:
                dx, dy = p.x - e.x, p.y - e.y
                d2 = dx * dx + dy * dy
                r = e.RADIUS + 22
                if d2 < r * r:
                    fx += dx / max(1.0, math.sqrt(d2)) * 2
                    fy += dy / max(1.0, math.sqrt(d2)) * 2
        # cible : aligner sur l'ennemi le plus menaçant, ou ramasser des objets
        tx, ty = PF_W / 2 + math.sin(self.t * 0.01) * 60, 215
        best = None
        for e in g.targets:
            if e.y < p.y - 20 and (best is None or e.y > best.y):
                best = e
        if best is not None:
            tx = best.x
        for it in g.items:
            if it.kind in ("orb", "p", "bomb", "oneup") and it.y < p.y + 20 and abs(it.x - p.x) < 90:
                tx, ty = it.x, max(120, it.y)
                break
        mx = (tx - p.x) * 0.04 + fx
        my = (ty - p.y) * 0.03 + fy
        thr = 0.25
        act["left"] = mx < -thr
        act["right"] = mx > thr
        act["up"] = my < -thr
        act["down"] = my > thr
        if danger > 1 / 60.0 and p.bombs > 0 and p.power == 0 and random.random() < 0.05:
            act["bomb"] = True
        if self.t % 1200 == 600:
            act["mode"] = True
        if p.speed_i != 2 and self.t % 30 == 0:
            act["speed"] = True
        return act
