"""Le vaisseau ALETHEIA.

Mécaniques Super Aleste : tir principal permanent + arme spéciale (6 dieux, 3 modes),
niveau de puissance 0..5 qui sert aussi de blindage (un impact coûte 2 niveaux, on ne meurt
qu'à 0), vitesse réglable sur 4 crans, puces « P » (ambroisie) pour monter de niveau.
"""
import math
import random

import pygame

from . import palette as P
from .sprites import S
from .fx import glow, Particle, K_GLOW, K_FLARE
from .weapons import (WEAPON_CLASSES, WEAPON_NAMES, MODE_NAMES, MODE_GREEK, Proj, Bomb)
from .util import clamp, approach

PF_W, PF_H = 256, 270
MAX_POWER = 5


class Player:
    SPEEDS = (1.35, 1.95, 2.6, 3.3)
    HIT_R = 1.7
    GRAZE_R = 14

    def __init__(self, w, lives=3):
        self.w = w
        self.x = PF_W / 2
        self.y = PF_H + 30
        self.speed_i = 1
        self.bank = 0.0
        self.power = 0
        self.chips = 0
        self.lives = lives
        self.bombs = 3
        self.god = None
        self.weapon = None
        self.mode = 0
        self.invuln = 0
        self.dead = False
        self.respawn = 0
        self.firing = False
        self.main_cd = 0
        self.control = False
        self.bomb = None
        self.t = 0
        self.moving_up = 0.0
        self.shot_alt = False
        self.ghosts = []
        self.last_dx = 0

    # --- état ---------------------------------------------------------------------
    def vulnerable(self):
        return not self.dead and self.invuln <= 0 and self.bomb is None and self.control and not self.w.cheat

    def chips_needed(self):
        return 3 + self.power // 2

    def add_chip(self, n=1):
        w = self.w
        for _ in range(n):
            if self.power >= MAX_POWER:
                w.score.add(1000, self.x, self.y - 16)
                continue
            self.chips += 1
            if self.chips >= self.chips_needed():
                self.chips = 0
                self.level_up()

    def level_up(self, n=1):
        w = self.w
        if self.power >= MAX_POWER:
            w.score.add(5000, self.x, self.y - 16)
            return
        self.power = min(MAX_POWER, self.power + n)
        w.popup(self.x, self.y - 22, "MAX !" if self.power == MAX_POWER else f"PUISSANCE {self.power}",
                (255, 230, 120))
        w.audio.play("powerup", self.x)
        w.fx.ring(self.x, self.y, 4, 30, 18, (255, 220, 120), 2)

    def set_weapon(self, god):
        w = self.w
        if god == self.god and self.weapon is not None:
            self.level_up()
            return
        if self.weapon is not None:
            self.weapon.stop()
        self.god = god
        self.weapon = WEAPON_CLASSES[god](w, self)
        self.weapon.set_mode(self.mode)
        w.audio.play("weapon", self.x)
        w.popup(self.x, self.y - 26, WEAPON_NAMES[god], P.GOD_COLORS[god])
        w.popup(self.x, self.y - 16, f"{MODE_GREEK[self.mode]} {MODE_NAMES[god][self.mode]}", (230, 230, 255), 50)
        w.fx.ring(self.x, self.y, 6, 40, 22, P.GOD_COLORS[god], 3)
        w.juice.flash(P.GOD_COLORS[god], 0.25, 0.05)
        w.hud_flash_weapon = 40

    def cycle_mode(self):
        w = self.w
        self.mode = (self.mode + 1) % 3
        if self.weapon is not None:
            self.weapon.set_mode(self.mode)
            w.popup(self.x, self.y - 20, f"{MODE_GREEK[self.mode]} {MODE_NAMES[self.god][self.mode]}",
                    P.GOD_COLORS[self.god], 45)
        else:
            w.popup(self.x, self.y - 20, f"MODE {MODE_GREEK[self.mode]}", (220, 220, 255), 40)
        w.audio.play("mode", self.x)
        w.hud_flash_weapon = 20

    # --- mise à jour ------------------------------------------------------------------
    def update(self, inp):
        w = self.w
        self.t += 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.bomb is not None:
            self.bomb.update()
            if not self.bomb.alive:
                self.bomb = None
                self.invuln = max(self.invuln, 30)
        if self.dead:
            self.firing = False
            if self.weapon is not None:
                self.weapon.update(False)
            self.respawn -= 1
            if self.respawn <= 0:
                self.revive()
            return
        dx = dy = 0.0
        if self.control:
            if inp["left"]:
                dx -= 1
            if inp["right"]:
                dx += 1
            if inp["up"]:
                dy -= 1
            if inp["down"]:
                dy += 1
            if inp.pressed("speed"):
                self.speed_i = (self.speed_i + 1) % 4
                w.audio.play("speed_up", self.x)
                w.popup(self.x, self.y + 20, "VITESSE " + str(self.speed_i + 1), (140, 230, 255), 30)
            if inp.pressed("speed_down"):
                self.speed_i = (self.speed_i - 1) % 4
                w.audio.play("speed_down", self.x)
                w.popup(self.x, self.y + 20, "VITESSE " + str(self.speed_i + 1), (140, 230, 255), 30)
            if inp.pressed("mode"):
                self.cycle_mode()
            if inp.pressed("bomb") and self.bombs > 0 and self.bomb is None:
                self.bombs -= 1
                self.bomb = Bomb(w, self.god)
            sp = self.SPEEDS[self.speed_i]
            if dx and dy:
                sp *= 0.7071
            self.x = clamp(self.x + dx * sp, 10, PF_W - 10)
            self.y = clamp(self.y + dy * sp, 16, PF_H - 12)
            self.firing = inp["fire"]
        else:
            self.firing = False
        self.last_dx = dx
        self.moving_up = approach(self.moving_up, 1.0 if dy < 0 else (-0.6 if dy > 0 else 0.0), 0.15)
        self.bank = approach(self.bank, dx * 2.0, 0.28)
        # traînée fantôme à grande vitesse
        if self.speed_i >= 3 and (dx or dy) and self.t % 3 == 0:
            self.ghosts.append([self.x, self.y, 10, self.frame_index()])
        self.ghosts = [[gx, gy, n - 1, fi] for (gx, gy, n, fi) in self.ghosts if n > 1]
        # tir principal
        if self.main_cd > 0:
            self.main_cd -= 1
        if self.firing and self.main_cd <= 0:
            self.fire_main()
        if self.weapon is not None:
            self.weapon.update(self.firing)
        # réacteurs
        if self.t % 2 == 0 and self.control:
            for sx in (-3.4, 3.4):
                w.fx.add(Particle(K_GLOW, self.x + sx + random.uniform(-0.5, 0.5), self.y + 14, 0,
                                  1.6 + self.speed_i * 0.4, 8, 2.2, 0.5, (70, 180, 255)))

    def fire_main(self):
        w = self.w
        self.main_cd = 4
        lv = self.power
        x, y = self.x, self.y - 9
        if lv < 2:
            guns = ((-5.9, 0, 0.0), (5.9, 0, 0.0))
        elif lv < 4:
            guns = ((-5.9, 0, 0.0), (5.9, 0, 0.0), (0, -5, 0.0))
        else:
            guns = ((-5.9, 0, 0.0), (5.9, 0, 0.0), (-2.2, -4, -0.05), (2.2, -4, 0.05))
        for gx, gy, a in guns:
            vx, vy = math.sin(a) * 9.5, -math.cos(a) * 9.5
            w.add_shot(Proj(w, x + gx, y + gy, vx, vy, 1.0, S["shot"], 3.2, False, 40))
        self.shot_alt = not self.shot_alt
        w.audio.play("shot" if self.shot_alt else "shot2", self.x, 1.0, throttle=3)
        for gx in (-5.9, 5.9):
            w.fx.add(Particle(K_FLARE, x + gx, y - 1, 0, 0, 3, 4, 2, (255, 220, 150)))

    # --- dégâts --------------------------------------------------------------------------
    def hurt(self):
        w = self.w
        if not self.vulnerable():
            return
        if self.power > 0:
            lost = min(2, self.power)
            self.power -= lost
            self.chips = 0
            self.invuln = 110
            w.bullets.cancel(False, self.x, self.y, 48)
            w.audio.play("armor", self.x)
            w.juice.shake(0.45)
            w.juice.flash((255, 60, 80), 0.45, 0.06)
            w.juice.aberr(3)
            w.juice.hitstop = 5
            w.fx.explosion(self.x, self.y, 0.7, grad=P.PLASMA, smoke_on=False)
            w.fx.ring(self.x, self.y, 4, 48, 20, (255, 120, 140), 3)
            w.popup(self.x, self.y - 22, "BLINDAGE -%d" % lost, (255, 110, 120), 50)
            w.score.break_chain(half=True)
            # l'ambroisie perdue s'éparpille : on peut en rattraper une partie
            for i in range(lost + 1):
                a = -math.pi / 2 + (i - lost / 2) * 0.7
                w.drop_items(self.x, self.y, "p", 1, vx=math.cos(a) * 2.2, vy=math.sin(a) * 2.2 - 1.0)
        else:
            self.die()

    def die(self):
        w = self.w
        self.dead = True
        self.respawn = 100
        self.firing = False
        w.audio.stop_loops()
        w.audio.play("die", self.x)
        w.juice.shake(0.9)
        w.juice.flash((255, 255, 255), 0.9, 0.04)
        w.juice.aberr(5)
        w.juice.hitstop = 8
        w.juice.slowmo = 40
        w.fx.explosion(self.x, self.y, 2.2, grad=P.PLASMA,
                       debris=w.fx.debris_from(S["player"][2].img, 9))
        w.fx.explosion(self.x, self.y, 1.2, delay=8)
        w.fx.ring(self.x, self.y, 5, 120, 40, (120, 220, 255), 4)
        w.bullets.cancel(False)
        w.score.break_chain()
        self.lives -= 1
        self.power = 0
        self.chips = 0
        w.on_player_death()

    def revive(self):
        w = self.w
        if self.lives < 0:
            return
        self.dead = False
        self.x = PF_W / 2
        self.y = PF_H + 20
        self.invuln = 200
        self.bombs = max(self.bombs, 3)
        self.control = False
        w.player_enter()
        # compensation : quelques puces d'ambroisie
        w.drop_items(PF_W / 2, PF_H * 0.55, "p", 3)

    # --- rendu ---------------------------------------------------------------------------------
    def frame_index(self):
        return int(round(clamp(self.bank, -2, 2))) + 2

    def visible(self):
        if self.dead:
            return False
        if self.invuln > 0 and self.bomb is None:
            return (self.invuln // 3) % 2 == 0
        return True

    def draw_shadow(self, surf):
        if self.dead or not self.w.bg.shadows:
            return
        spr = S["player"][self.frame_index()]
        spr.draw_shadow(surf, self.x + 12, self.y + 18)

    def draw(self, surf):
        if self.dead:
            return
        for (gx, gy, n, fi) in self.ghosts:
            img = S["player"][fi].flash
            img.set_alpha(18 * n)
            surf.blit(img, (int(gx - 14.5), int(gy - 15.5)))
            img.set_alpha(255)
        if not self.visible():
            return
        spr = S["player"][self.frame_index()]
        spr.draw(surf, self.x, self.y)
        if self.weapon is not None:
            self.weapon.draw(surf)
        # hitbox
        c = S["core"]
        c.draw(surf, self.x, self.y + 0.5)

    def draw_add(self, add):
        if self.weapon is not None and not self.dead:
            self.weapon.draw_add(add)
        if self.bomb is not None:
            self.bomb.draw_add(add)
        if self.dead:
            return
        spr = S["player"][self.frame_index()]
        if self.visible():
            spr.draw_halo(add, self.x, self.y)
        # flammes des réacteurs
        ln = 4 + self.speed_i * 1.3 + self.moving_up * 3 + random.random() * 2
        for sx in (-3.4, 3.4):
            x, y = self.x + sx, self.y + 13
            g = glow(int(3 + ln * 0.5), (40, 120, 255))
            add.blit(g, (int(x - g.get_width() // 2), int(y + ln * 0.4 - g.get_height() // 2)),
                     special_flags=pygame.BLEND_ADD)
            pygame.draw.line(add, (120, 220, 255), (x, y), (x, y + ln), 2)
            pygame.draw.line(add, (255, 255, 255), (x, y), (x, y + ln * 0.5), 1)
        if self.invuln > 0 and self.control:
            k = min(1.0, self.invuln / 60)
            r = 16 + math.sin(self.t * 0.3) * 1.5
            pygame.draw.circle(add, (int(40 * k), int(120 * k), int(160 * k)), (int(self.x), int(self.y)), int(r), 1)
