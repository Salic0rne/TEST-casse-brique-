"""Entités du jeu : briques, balles, raquette, capsules de bonus, tirs laser."""

import math
from collections import deque

from .config import (BALL_R, BRICK_H, BRICK_W, GRID_LEFT, GRID_TOP, PADDLE_H, PADDLE_W,
                     PADDLE_Y, PF_CX, PITCH_X, PITCH_Y)
from .sprites import METAL
from .util import hsv


class Brick:
    __slots__ = ("col", "row", "x", "y", "w", "h", "kind", "hp", "max_hp", "hue", "sat",
                 "alive", "flash", "ox", "oy", "vx", "vy", "appear", "delay", "points", "color")

    def __init__(self, col, row, kind, hue, sat, hp):
        self.col, self.row = col, row
        self.x = GRID_LEFT + col * PITCH_X
        self.y = GRID_TOP + row * PITCH_Y
        self.w, self.h = BRICK_W, BRICK_H
        self.kind = kind
        self.hp = self.max_hp = hp
        self.hue, self.sat = hue, sat
        self.alive = True
        self.flash = 0.0
        self.ox = self.oy = self.vx = self.vy = 0.0
        self.appear = 0.0
        self.delay = 0.0
        self.points = {1: 50, 2: 120, 3: 200}.get(hp, 50)
        self.color = hsv(hue, sat, 1.0) if kind != METAL else (200, 210, 235)

    @property
    def destructible(self):
        return self.kind != METAL

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def kick(self, dx, dy, force=60.0):
        """Petit choc visuel (ressort amorti)."""
        d = math.hypot(dx, dy) or 1.0
        self.vx += dx / d * force
        self.vy += dy / d * force

    def update(self, dt):
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt * 5.0)
        if self.ox or self.oy or self.vx or self.vy:
            k, c = 420.0, 16.0
            self.vx += (-k * self.ox - c * self.vx) * dt
            self.vy += (-k * self.oy - c * self.vy) * dt
            self.ox += self.vx * dt
            self.oy += self.vy * dt
            if abs(self.ox) < 0.05 and abs(self.oy) < 0.05 and abs(self.vx) < 0.5 and abs(self.vy) < 0.5:
                self.ox = self.oy = self.vx = self.vy = 0.0


class Ball:
    __slots__ = ("x", "y", "vx", "vy", "r", "speed", "stuck", "stick_dx", "stick_timer", "trail",
                 "alive", "squash", "squash_ang", "fire", "spin")

    def __init__(self, x, y, speed):
        self.x, self.y = x, y
        self.vx, self.vy = 0.0, -speed
        self.r = BALL_R
        self.speed = speed
        self.stuck = True
        self.stick_dx = 0.0
        self.stick_timer = 0.0
        self.trail = deque(maxlen=18)
        self.alive = True
        self.squash = 0.0
        self.squash_ang = 0.0
        self.fire = False
        self.spin = 0.0

    def set_angle(self, ang, speed):
        """Angle mesuré depuis la verticale (vers le haut), en radians."""
        self.vx = math.sin(ang) * speed
        self.vy = -math.cos(ang) * speed

    def normalize(self, speed):
        v = math.hypot(self.vx, self.vy)
        if v > 1e-6:
            k = speed / v
            self.vx *= k
            self.vy *= k
        else:
            self.vx, self.vy = 0.0, -speed

    def fix_angle(self):
        """Évite les trajectoires presque horizontales (balle « coincée » entre deux murs)."""
        v = math.hypot(self.vx, self.vy)
        if v < 1e-6:
            return
        min_vy = v * 0.28
        if abs(self.vy) < min_vy:
            sy = -1.0 if self.vy <= 0 else 1.0
            self.vy = sy * min_vy
            sx = -1.0 if self.vx < 0 else 1.0
            self.vx = sx * math.sqrt(max(0.0, v * v - min_vy * min_vy))

    def impact(self, nx, ny):
        self.squash = 1.0
        self.squash_ang = math.atan2(ny, nx)


class Paddle:
    def __init__(self):
        self.x = float(PF_CX)
        self.y = float(PADDLE_Y)
        self.w = float(PADDLE_W)
        self.target_w = float(PADDLE_W)
        self.h = PADDLE_H
        self.vx = 0.0
        self.bounce = 0.0
        self.bounce_v = 0.0
        self.flash = 0.0
        self.visible = True
        self.ghosts = deque(maxlen=5)

    @property
    def left(self):
        return self.x - self.w / 2

    @property
    def right(self):
        return self.x + self.w / 2

    @property
    def top(self):
        return self.y - self.h / 2

    def hit(self, strength=1.0):
        self.bounce_v += 160.0 * strength
        self.flash = 1.0

    def update(self, dt):
        self.w += (self.target_w - self.w) * (1.0 - math.exp(-dt * 10.0))
        k, c = 700.0, 22.0
        self.bounce_v += (-k * self.bounce - c * self.bounce_v) * dt
        self.bounce += self.bounce_v * dt
        self.flash = max(0.0, self.flash - dt * 4.0)


class Capsule:
    __slots__ = ("x", "y", "kind", "vy", "t", "alive")

    def __init__(self, x, y, kind):
        self.x, self.y, self.kind = x, y, kind
        self.vy = 150.0
        self.t = 0.0
        self.alive = True


class Laser:
    __slots__ = ("x", "y", "alive")

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.alive = True
