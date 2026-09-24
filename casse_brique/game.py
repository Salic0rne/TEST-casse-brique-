"""Scène de jeu : simulation, collisions, bonus, combos, effets et interface."""

import math
import random

import pygame

from .config import (BALL_R, BALL_SPEED_HIT_STEP, BALL_SPEED_LEVEL_STEP, BALL_SPEED_MAX,
                     BALL_SPEED_START, BRICK_H, BRICK_W, COLS, EXTRA_LIFE_EVERY, GRID_LEFT,
                     GRID_TOP, HEIGHT, MAX_BALLS, MAX_LIVES, PADDLE_KEY_SPEED, PADDLE_W,
                     PADDLE_W_NARROW, PADDLE_W_WIDE, PF_BOTTOM, PF_CX, PF_H, PF_LEFT, PF_RIGHT,
                     PF_TOP, PF_W, PHYSICS_DT, PITCH_X, PITCH_Y, START_LIVES, WIDTH)
from .entities import Ball, Brick, Capsule, Laser, Paddle
from .levels import get_level, level_count, parse_cell
from .sprites import ARMOR, BOMB, HARD, MALUS, METAL, POWERUPS, PRISM
from .surf import blend_fill
from .ui import Menu, MenuItem, card, draw_bar
from .util import approach, clamp, ease_in_cubic, ease_out_back, hsv, lighten, mix, scale

TIMED = {"G": 18.0, "L": 14.0, "R": 12.0, "F": 9.0, "A": 15.0, "B": 15.0, "P": 11.0, "V": 10.0}
DROP_WEIGHTS = {"G": 14, "M": 13, "L": 11, "R": 9, "F": 7, "A": 9, "B": 8, "♥": 3, "P": 8, "V": 7}
COMBO_WORDS = [(6, "BIEN !"), (12, "SUPER !"), (20, "GÉNIAL !"), (30, "INCROYABLE !"),
               (45, "DÉMENTIEL !"), (65, "LÉGENDAIRE !")]
MULT_COLORS = [(225, 225, 245), (0, 230, 255), (80, 255, 120), (255, 230, 0), (255, 140, 0),
               (255, 60, 130), (220, 90, 255), (255, 255, 255)]
SHIELD_Y = PF_BOTTOM - 18
PF_DIM = (58, 52, 80)
PANEL_DIM = (118, 108, 140)
LEFT_PANEL = pygame.Rect(0, 0, PF_LEFT, HEIGHT)
RIGHT_PANEL = pygame.Rect(PF_RIGHT, 0, WIDTH - PF_RIGHT, HEIGHT)
PF_RECT = pygame.Rect(PF_LEFT, PF_TOP, PF_W, PF_H)


def fmt_score(n):
    return "{:,}".format(int(n)).replace(",", " ")


class GameScene:
    def __init__(self, app, level=0):
        self.app = app
        self.audio, self.fx, self.art = app.audio, app.fx, app.art
        self.font, self.parts, self.bg = app.font, app.particles, app.bg
        self.rng = random.Random()
        self.parts.clear()
        self.parts.on_event = self._particle_event
        self.fx.reset()
        self.score = 0
        self.shown_score = 0.0
        self.lives = START_LIVES
        self.next_life = EXTRA_LIFE_EVERY
        self.best_before = app.settings.best_score
        self.paddle = Paddle()
        self.balls, self.capsules, self.lasers, self.bricks = [], [], [], []
        self.grid = {}
        self.timers = []
        self.effects = {}
        self.chain = 0
        self.best_chain = 0
        self.speed_mult = 1.0
        self.time = 0.0
        self.acc = 0.0
        self.laser_cd = 0.0
        self.wall_flashes = []
        self.grid_flash = 0.0
        self.drops_since = 0
        self.recent_pickups = []
        self.glint_t = 0.0
        self.shine_t = 0.0
        self.paused = False
        self.stats = {"bricks": 0, "bonus": 0}
        self.new_record = False
        self.level_bonus = 0
        self.mouse_x = pygame.mouse.get_pos()[0]
        self.input_mode = "mouse"
        self.hud_bump = {"score": 0.0, "lives": 0.0, "combo": 0.0}
        self.pause_menu = Menu(app, [
            MenuItem("REPRENDRE", self.resume),
            MenuItem("RECOMMENCER", self.restart),
            MenuItem("MENU PRINCIPAL", self.quit_to_menu),
        ], PF_CX, 350, spacing=58, size=24, on_back=self.resume, width=420)
        self.over_menu = None
        self.prewarm_texts()
        self.load_level(level)

    # ================================================================== niveaux
    def load_level(self, index):
        self.level = index
        self.level_name, rows = get_level(index)
        self.bg.set_theme(index)
        self.theme = self.bg.theme
        self.bricks, self.grid = [], {}
        nrows = len(rows)
        for r, line in enumerate(rows):
            for c, ch in enumerate(line[:COLS]):
                cell = parse_cell(ch, r, nrows)
                if cell is None:
                    continue
                kind, hue, sat, hp = cell
                b = Brick(c, r, kind, hue, sat, hp)
                b.delay = 0.35 + r * 0.055 + abs(c - COLS // 2) * 0.03
                self.bricks.append(b)
                self.grid[(c, r)] = b
        self.art.prewarm_bricks({(b.kind, b.hue, b.sat, b.max_hp) for b in self.bricks})
        self.rows_seen = set()
        self.last_destroyed = None
        self.remaining = sum(1 for b in self.bricks if b.destructible)
        self.total = self.remaining
        self.capsules, self.lasers, self.timers = [], [], []
        self.effects = {}
        self.paddle.target_w = PADDLE_W
        self.paddle.visible = True
        self.chain = 0
        self.base_speed = min(BALL_SPEED_MAX - 220.0, BALL_SPEED_START + index * BALL_SPEED_LEVEL_STEP)
        self.reset_ball()
        self.set_state("intro")
        self.audio.set_track(index % 2)      # les deux morceaux alternent d'un niveau à l'autre
        self.audio.set_music_mode("intro")
        self.audio.play("whoosh")

    def prewarm_texts(self):
        """Rend d'avance les textes flottants fréquents (évite les à-coups en pleine action)."""
        for mult in range(1, 9):
            size = 13 if mult == 1 else 15 + min(6, mult)
            for base in (50, 120, 200):
                self.font.render("+%d" % (base * mult), size, MULT_COLORS[mult - 1], glow=0.8)
            self.font.render("COMBO ×%d" % mult, 16, (255, 220, 120))
        for color, name, _ in POWERUPS.values():
            self.font.render(name, 18, color)

    def reset_ball(self):
        b = Ball(self.paddle.x, self.paddle.top - BALL_R - 1, self.base_speed)
        b.stick_dx = self.rng.uniform(-12, 12)
        self.balls = [b]

    def set_state(self, s):
        self.state = s
        self.state_t = 0.0

    # ================================================================== entrées
    def on_action(self, action):
        if self.state == "gameover":
            if self.over_menu and self.state_t > 1.2:
                self.over_menu.on_action(action)
            return
        if self.paused:
            self.pause_menu.on_action(action)
            return
        if action in ("pause", "back"):
            self.pause()
        elif action == "confirm":
            self.press_fire()

    def on_event(self, e):
        if self.state == "gameover":
            if self.over_menu and self.state_t > 1.2:
                self.over_menu.on_event(e)
            return
        if self.paused:
            self.pause_menu.on_event(e)
            return
        if e.type == pygame.MOUSEMOTION:
            self.input_mode = "mouse"
            self.mouse_x = e.pos[0]
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.press_fire()
        elif e.type == pygame.WINDOWFOCUSLOST and self.state in ("play", "ready"):
            self.pause()

    def press_fire(self):
        if self.state in ("ready", "play") and any(b.stuck for b in self.balls if b.alive):
            self.launch()
        elif self.state == "play" and "L" in self.effects:
            self.shoot()

    def pause(self):
        if self.state in ("gameover",):
            return
        self.paused = True
        self.pause_menu.sel = 0
        self.audio.set_music_mode("pause")
        self.audio.play("select")

    def resume(self):
        self.paused = False
        self.audio.set_music_mode("game" if self.state == "play" else "intro")

    def restart(self):
        self.paused = False
        self.app.goto(lambda: GameScene(self.app, 0))

    def quit_to_menu(self):
        self.paused = False
        from .scenes import TitleScene
        self.app.goto(lambda: TitleScene(self.app))

    # ================================================================== actions
    def launch(self):
        p = self.paddle
        for b in self.balls:
            if not b.alive or not b.stuck:
                continue
            rel = b.stick_dx / (p.w / 2)
            ang = clamp(rel * 0.9 + clamp(p.vx / 3000.0, -0.3, 0.3), -1.0, 1.0)
            if abs(ang) < 0.06:
                ang = self.rng.choice((-1, 1)) * self.rng.uniform(0.1, 0.3)
            b.stuck = False
            b.set_angle(ang, b.speed * self.speed_mult)
            self.parts.ring(b.x, b.y, (160, 240, 255), 34, life=0.3, width=2)
            self.parts.sparks_burst(b.x, b.y, (150, 230, 255), 10, speed=(80, 260),
                                    angle=-math.pi / 2, spread=1.6, grav=200)
        self.audio.play("launch", pan=self.pan(p.x))
        if self.state == "ready":
            self.set_state("play")
            self.audio.set_music_mode("game")

    def shoot(self):
        if self.laser_cd > 0:
            return
        self.laser_cd = 0.2
        p = self.paddle
        for x in (p.left + 8, p.right - 8):
            self.lasers.append(Laser(x, p.top - 4))
            self.parts.blob(x, p.top - 4, (255, 60, 90), 26, life=0.12)
        self.audio.play("laser", 0.8, self.pan(p.x), min_gap=0.05)

    @staticmethod
    def pan(x):
        return clamp((x - PF_CX) / (PF_W / 2) * 0.75, -0.75, 0.75)

    def multiplier(self):
        return min(8, 1 + self.chain // 6)

    def add_score(self, pts):
        self.score += int(pts)
        self.hud_bump["score"] = 1.0
        while self.score >= self.next_life:
            self.next_life += EXTRA_LIFE_EVERY
            if self.lives < MAX_LIVES:
                self.lives += 1
                self.hud_bump["lives"] = 1.0
                self.audio.play("life")
                self.parts.text(PF_CX, 420, "VIE BONUS !", 26, (255, 90, 190), life=1.4, vy=-40)

    def schedule(self, delay, fn):
        self.timers.append([delay, fn])

    def _particle_event(self, name, x, y):
        if name == "firework":
            self.audio.play("firework", 0.7, self.pan(x), min_gap=0.05)

    # ================================================================== mise à jour
    def update(self, dt, scale_t):
        self.fx.shake_enabled = self.app.settings.shake
        if self.paused:
            self.pause_menu.update(dt)
            return
        if self.over_menu:
            self.over_menu.update(dt)
        wdt = dt * scale_t
        self.time += wdt
        self.state_t += dt
        for k in self.hud_bump:
            self.hud_bump[k] = max(0.0, self.hud_bump[k] - dt * 3.0)
        self.shown_score = approach(self.shown_score, self.score, 9.0, dt)
        if abs(self.shown_score - self.score) < 1:
            self.shown_score = self.score
        self.grid_flash = max(0.0, self.grid_flash - dt * 2.0)

        self.update_paddle(dt, wdt)
        self.update_state(dt, wdt)

        # simulation à pas fixe
        if wdt > 0:
            self.acc = min(self.acc + wdt, 0.1)
            while self.acc >= PHYSICS_DT:
                self.physics(PHYSICS_DT)
                self.acc -= PHYSICS_DT
        self.balls = [b for b in self.balls if b.alive]
        self.capsules = [c for c in self.capsules if c.alive]
        self.lasers = [l for l in self.lasers if l.alive]
        if self.remaining <= 0 and self.state in ("play", "ready"):
            self.level_cleared(self.last_destroyed)
        elif self.state == "play" and not self.balls:
            self.lose_life()

        # vitesse cible (bonus ralenti / malus accéléré)
        target = 0.68 if "R" in self.effects else 1.3 if "V" in self.effects else 1.0
        self.speed_mult = approach(self.speed_mult, target, 3.0, wdt)
        for b in self.balls:
            if not b.stuck:
                b.normalize(b.speed * self.speed_mult)
            b.squash = max(0.0, b.squash - wdt * 7.0)
            b.trail.append((b.x, b.y))
            if b.fire and not b.stuck and wdt > 0 and self.rng.random() < 2.0 / (1 + len(self.balls)):
                self.parts.blob(b.x + self.rng.uniform(-4, 4), b.y + self.rng.uniform(-4, 4),
                                (255, 150, 30), self.rng.uniform(14, 22), life=self.rng.uniform(0.25, 0.4),
                                vx=-b.vx * 0.08, vy=-b.vy * 0.08, rise=-80, fire=True)
            if b.stuck and "A" in self.effects and self.state == "play":
                b.stick_timer -= wdt
                if b.stick_timer <= 0:
                    self.launch()

        # minuteries (les rappels peuvent en programmer de nouvelles)
        if wdt > 0 and self.timers:
            current, self.timers = self.timers, []
            for tmr in current:
                tmr[0] -= wdt
                if tmr[0] <= 0:
                    tmr[1]()
                else:
                    self.timers.append(tmr)

        # effets temporaires
        for k in list(self.effects):
            self.effects[k] -= wdt
            if self.effects[k] <= 0:
                del self.effects[k]
                self.expire(k)
        self.laser_cd = max(0.0, self.laser_cd - wdt)
        if "L" in self.effects and self.state == "play" and self.fire_held():
            self.shoot()

        for b in self.bricks:
            if b.alive:
                b.update(wdt)
        self.parts.update(wdt)
        self.wall_flashes = [[x, y, t - dt, c] for x, y, t, c in self.wall_flashes if t - dt > 0]

        # reflets scintillants sur les briques
        self.glint_t -= wdt
        if self.glint_t <= 0 and self.bricks and self.state != "intro":
            self.glint_t = self.rng.uniform(0.05, 0.16)
            b = self.rng.choice(self.bricks)
            if b.alive:
                self.parts.glint(b.x + self.rng.uniform(4, BRICK_W - 4), b.y + self.rng.uniform(2, 8),
                                 self.rng.uniform(6, 11))

    def fire_held(self):
        keys = pygame.key.get_pressed()
        return keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0] or self.app.joy_fire

    def update_paddle(self, dt, wdt):
        p = self.paddle
        keys = pygame.key.get_pressed()
        left = keys[pygame.K_LEFT] or keys[pygame.K_q] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        axis = self.app.joy_axis
        if left or right or abs(axis) > 0.25:
            self.input_mode = "keys"
        old = p.x
        if self.input_mode == "keys":
            d = (1.0 if right else 0.0) - (1.0 if left else 0.0)
            if abs(axis) > 0.25:
                d = axis
            fast = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            target = d * PADDLE_KEY_SPEED * (1.4 if fast else 1.0)
            p.vx = approach(p.vx, target, 16.0, dt)
            p.x += p.vx * wdt
        else:
            p.x = float(self.mouse_x)
        half = p.w / 2
        p.x = clamp(p.x, PF_LEFT + half + 3, PF_RIGHT - half - 3)
        if self.input_mode != "keys" and dt > 0:
            p.vx = clamp((p.x - old) / dt, -3000.0, 3000.0)
        elif p.x in (PF_LEFT + half + 3, PF_RIGHT - half - 3):
            p.vx = 0.0
        p.update(wdt)
        if abs(p.vx) > 900 and p.visible:
            p.ghosts.append(p.x)
        elif p.ghosts:
            p.ghosts.popleft()

    def update_state(self, dt, wdt):
        s = self.state
        if s == "intro":
            for b in self.bricks:
                b.appear = clamp((self.state_t - b.delay) / 0.45, 0.0, 1.0)
                if b.appear > 0 and b.row not in self.rows_seen:
                    self.rows_seen.add(b.row)
                    self.audio.play("appear%d" % (b.row % 8), 0.7, min_gap=0.0)
            if self.state_t > 2.1 and all(b.appear >= 1.0 for b in self.bricks):
                self.set_state("ready")
                self.audio.play("ready")
        elif s == "dying":
            if self.state_t > 1.7:
                if self.lives > 0:
                    self.paddle.visible = True
                    self.paddle.target_w = PADDLE_W
                    self.parts.ring(self.paddle.x, self.paddle.y, (120, 240, 255), 90, life=0.5, width=3)
                    self.parts.sparks_burst(self.paddle.x, self.paddle.y, (140, 240, 255), 26,
                                            speed=(60, 300))
                    self.reset_ball()
                    self.set_state("ready")
                    self.audio.play("ready")
                    self.audio.set_music_mode("intro")
                else:
                    self.game_over()
        elif s == "clear":
            if self.state_t > 1.0:
                for b in self.balls:
                    self.parts.sparks_burst(b.x, b.y, (200, 240, 255), 20, speed=(60, 300))
                    self.parts.blob(b.x, b.y, (160, 220, 255), 60, life=0.4)
                self.balls = []
            if self.state_t > 1.5 and self.level_bonus:
                self.add_score(self.level_bonus)
                self.level_bonus = 0
                self.audio.play("powerup")
            if self.state_t > 4.0:
                self.fx.flash((255, 255, 255), 0.6)
                self.load_level(self.level + 1)
        elif s == "gameover":
            if self.over_menu is None and self.state_t > 1.2:
                self.over_menu = Menu(self.app, [
                    MenuItem("REJOUER", self.restart),
                    MenuItem("MENU PRINCIPAL", self.quit_to_menu),
                ], PF_CX, 520, spacing=56, size=24, width=420)

    # ================================================================== physique
    def physics(self, h):
        p = self.paddle
        for b in self.balls:
            if not b.alive:
                continue
            if b.stuck:
                b.x = p.x + b.stick_dx
                b.y = p.top - b.r - 1 + p.bounce
                continue
            b.x += b.vx * h
            b.y += b.vy * h
            self.collide_walls(b)
            self.collide_bricks(b)
            if b.vy > 0 and p.visible:
                self.collide_paddle(b)
            if "B" in self.effects and b.vy > 0 and b.y + b.r >= SHIELD_Y:
                b.y = SHIELD_Y - b.r
                b.vy = -abs(b.vy)
                b.fix_angle()
                self.audio.play("shield", 0.8, self.pan(b.x))
                self.parts.sparks_burst(b.x, SHIELD_Y, (120, 255, 230), 14, speed=(80, 300),
                                        angle=-math.pi / 2, spread=2.2)
                self.parts.ring(b.x, SHIELD_Y, (120, 255, 230), 40, life=0.3, width=2)
            if b.y - b.r > PF_BOTTOM + 6:
                b.alive = False
                self.ball_lost(b)

        for l in self.lasers:
            if not l.alive:
                continue
            l.y -= 1050 * h
            if l.y < PF_TOP + 4:
                l.alive = False
                self.parts.sparks_burst(l.x, PF_TOP + 4, (255, 90, 110), 6, speed=(60, 200))
                continue
            c = int((l.x - GRID_LEFT) // PITCH_X)
            r = int((l.y - GRID_TOP) // PITCH_Y)
            brick = self.grid.get((c, r))
            if brick and brick.alive and brick.x <= l.x <= brick.x + BRICK_W and \
                    brick.y <= l.y <= brick.y + BRICK_H:
                l.alive = False
                self.parts.sparks_burst(l.x, brick.y + BRICK_H, (255, 120, 140), 8, speed=(60, 240),
                                        angle=math.pi / 2, spread=2.5)
                self.damage(brick, 1, "laser", nx=0.0, ny=1.0)

        for cap in self.capsules:
            if not cap.alive:
                continue
            cap.t += h
            cap.y += cap.vy * h
            if p.visible and cap.y + 9 >= p.top and cap.y - 9 <= p.top + p.h and \
                    p.left - 20 <= cap.x <= p.right + 20:
                cap.alive = False
                self.collect(cap)
            elif cap.y > PF_BOTTOM + 20:
                cap.alive = False

    def collide_walls(self, b):
        r = b.r
        if b.x - r < PF_LEFT:
            b.x = PF_LEFT + r
            b.vx = abs(b.vx)
            self.wall_hit(b, PF_LEFT, b.y, 1, 0)
        elif b.x + r > PF_RIGHT:
            b.x = PF_RIGHT - r
            b.vx = -abs(b.vx)
            self.wall_hit(b, PF_RIGHT, b.y, -1, 0)
        if b.y - r < PF_TOP:
            b.y = PF_TOP + r
            b.vy = abs(b.vy)
            self.wall_hit(b, b.x, PF_TOP, 0, 1)

    def wall_hit(self, b, x, y, nx, ny):
        b.fix_angle()
        b.impact(nx, ny)
        self.audio.play("wall", 0.8, self.pan(x))
        col = self.theme.frame
        self.parts.sparks_burst(x, y, lighten(col, 0.4), 6, speed=(60, 220),
                                angle=math.atan2(ny, nx), spread=2.2, grav=300, width=1)
        self.wall_flashes.append([x, y, 0.4, col])

    def bricks_near(self, x, y, r):
        c0 = int((x - r - GRID_LEFT) // PITCH_X)
        c1 = int((x + r - GRID_LEFT) // PITCH_X)
        r0 = int((y - r - GRID_TOP) // PITCH_Y)
        r1 = int((y + r - GRID_TOP) // PITCH_Y)
        g = self.grid
        out = []
        for c in range(c0, c1 + 1):
            for rr in range(r0, r1 + 1):
                br = g.get((c, rr))
                if br is not None and br.alive:
                    out.append(br)
        return out

    def collide_bricks(self, b):
        near = self.bricks_near(b.x, b.y, b.r)
        if not near:
            return
        r = b.r
        hits = []
        for br in near:
            rx, ry = br.x, br.y
            rx2, ry2 = rx + BRICK_W, ry + BRICK_H
            cx = rx if b.x < rx else rx2 if b.x > rx2 else b.x
            cy = ry if b.y < ry else ry2 if b.y > ry2 else b.y
            dx, dy = b.x - cx, b.y - cy
            d2 = dx * dx + dy * dy
            if d2 >= r * r:
                continue
            if d2 > 1e-9:
                d = math.sqrt(d2)
                nx, ny, pen = dx / d, dy / d, r - d
                if cx in (rx, rx2) and cy in (ry, ry2):
                    # coin : si une voisine prolonge la face, on rebondit comme sur une face plane
                    sx = -1 if cx == rx else 1
                    sy = -1 if cy == ry else 1
                    side = self.grid.get((br.col + sx, br.row))
                    vert = self.grid.get((br.col, br.row + sy))
                    has_h = side is not None and side.alive
                    has_v = vert is not None and vert.alive
                    if has_h and not has_v:
                        nx, ny, pen = 0.0, float(sy), r - abs(dy)
                    elif has_v and not has_h:
                        nx, ny, pen = float(sx), 0.0, r - abs(dx)
            else:
                dl, dr_, dt_, db = b.x - rx, rx2 - b.x, b.y - ry, ry2 - b.y
                m = min(dl, dr_, dt_, db)
                if m == dt_:
                    nx, ny, pen = 0.0, -1.0, dt_ + r
                elif m == db:
                    nx, ny, pen = 0.0, 1.0, db + r
                elif m == dl:
                    nx, ny, pen = -1.0, 0.0, dl + r
                else:
                    nx, ny, pen = 1.0, 0.0, dr_ + r
            hits.append((br, nx, ny, pen))
        if not hits:
            return
        solid = []
        for br, nx, ny, pen in hits:
            approaching = b.vx * nx + b.vy * ny < 0
            if b.fire and br.destructible:
                self.damage(br, br.hp, "ball", b, nx, ny)
                continue
            if approaching:
                solid.append((br, nx, ny, pen))
        if not solid:
            return
        sx = sum(h[1] for h in solid)
        sy = sum(h[2] for h in solid)
        ln = math.hypot(sx, sy)
        if ln < 1e-6:
            sx, sy = solid[0][1], solid[0][2]
        else:
            sx, sy = sx / ln, sy / ln
        pen = max(h[3] for h in solid)
        vn = b.vx * sx + b.vy * sy
        if vn < 0:
            b.vx -= 2 * vn * sx
            b.vy -= 2 * vn * sy
        b.x += sx * pen
        b.y += sy * pen
        b.fix_angle()
        b.impact(sx, sy)
        b.speed = min(BALL_SPEED_MAX, b.speed + BALL_SPEED_HIT_STEP)
        for br, nx, ny, _ in solid:
            self.damage(br, 1, "ball", b, nx, ny)

    def collide_paddle(self, b):
        p = self.paddle
        top = p.top + p.bounce
        if b.y + b.r < top or b.y - b.r > top + p.h:
            return
        if b.x < p.left - b.r or b.x > p.right + b.r:
            return
        if b.y > top + p.h * 0.6:
            return
        rel = clamp((b.x - p.x) / (p.w / 2 + b.r * 0.5), -1.0, 1.0)
        ang = rel * math.radians(62) + clamp(p.vx / 2500.0, -0.2, 0.2)
        ang = clamp(ang, -math.radians(70), math.radians(70))
        b.set_angle(ang, b.speed * self.speed_mult)
        b.y = top - b.r - 0.5
        b.impact(0, -1)
        p.hit(0.7 + 0.3 * abs(rel))
        if self.chain >= 6:
            self.parts.text(p.x, p.top - 30, "COMBO ×%d" % self.multiplier(), 16, (255, 220, 120),
                            life=0.8, vy=-50)
        self.best_chain = max(self.best_chain, self.chain)
        self.chain = 0
        col = (120, 230, 255)
        self.parts.sparks_burst(b.x, top, col, 12, speed=(80, 320), angle=-math.pi / 2, spread=2.4,
                                grav=400, width=2)
        self.parts.ring(b.x, top, col, 30, life=0.28, width=2)
        self.parts.blob(b.x, top, col, 50, life=0.25)
        self.audio.play("paddle", 0.9, self.pan(b.x))
        if "A" in self.effects:
            b.stuck = True
            b.stick_dx = clamp(b.x - p.x, -p.w / 2 + 6, p.w / 2 - 6)
            b.stick_timer = 2.5
            b.vx = b.vy = 0.0
            self.audio.play("catch", 0.8, self.pan(b.x))

    # ================================================================== briques
    def damage(self, br, amount, source, ball=None, nx=0.0, ny=0.0):
        if not br.alive:
            return
        cx, cy = br.cx, br.cy
        if br.kind == METAL:
            br.flash = 1.0
            br.kick(-nx, -ny, 70)
            self.audio.play("metal", 0.7, self.pan(cx), min_gap=0.06)
            self.parts.sparks_burst(cx - nx * BRICK_W * 0.4, cy - ny * BRICK_H * 0.4, (230, 240, 255), 10,
                                    speed=(100, 380), angle=math.atan2(ny, nx), spread=2.4, width=1)
            return
        br.hp -= amount
        br.flash = 1.0
        br.kick(-nx or self.rng.uniform(-1, 1), -ny or self.rng.uniform(-1, 1), 90)
        if br.hp <= 0:
            self.destroy(br, source, ball)
        else:
            self.add_score(10)
            self.audio.play("hit", 0.8, self.pan(cx))
            self.parts.sparks_burst(cx, cy, lighten(br.color, 0.4), 10, speed=(80, 300), width=1)
            self.parts.shards_burst(cx, cy, BRICK_W, BRICK_H, br.color, n=3, force=0.6)

    def destroy(self, br, source, ball=None):
        br.alive = False
        self.grid.pop((br.col, br.row), None)
        self.remaining -= 1
        self.chain += 1
        self.best_chain = max(self.best_chain, self.chain)
        self.stats["bricks"] += 1
        mult = self.multiplier()
        pts = br.points * mult
        self.add_score(pts)
        cx, cy = br.cx, br.cy
        col = br.color if br.kind != PRISM else hsv(self.time * 0.5, 0.6, 1.0)
        big = br.kind in (HARD, ARMOR)
        size = 13 if mult == 1 else 15 + min(6, mult)
        # couleur du texte = couleur du multiplicateur (et cache de rendu borné)
        self.parts.text(cx, cy, "+%d" % pts, size, MULT_COLORS[mult - 1], life=0.8, vy=-70, glow=0.8)
        vx, vy = (ball.vx, ball.vy) if ball else (0.0, 0.0)
        self.parts.brick_break(cx, cy, BRICK_W, BRICK_H, col, 1.4 if big else 1.0, vx, vy)
        pan = self.pan(cx)
        self.audio.brick(self.chain - 1, pan)
        if ball is not None and ball.fire:
            self.audio.play("burn", 0.6, pan)
        self.fx.shake(0.1 if big else 0.05)
        if br.kind == PRISM:
            self.audio.play("prism", 0.9, pan)
            self.parts.confetti_burst(cx, cy, 30, 0.7)
            self.fx.flash((255, 255, 255), 0.15)
        # onde de choc sur les briques voisines
        for dc in (-2, -1, 0, 1, 2):
            for dr in (-2, -1, 0, 1, 2):
                nb = self.grid.get((br.col + dc, br.row + dr))
                if nb is not None and nb.alive:
                    d = math.hypot(dc, dr)
                    nb.kick(dc, dr, 110.0 / d)
        # paliers de combo
        for idx, (threshold, word) in enumerate(COMBO_WORDS):
            if self.chain == threshold:
                self.audio.play("combo%d" % min(3, idx))
                self.parts.text(PF_CX, 300, word, 34, hsv(self.time * 0.3, 0.7, 1.0), life=1.3, vy=-30,
                                skew=0.15)
                self.hud_bump["combo"] = 1.0
                self.fx.flash(self.theme.accent, 0.12)
                self.grid_flash = 1.0
        self.maybe_drop(br)
        self.last_destroyed = br
        if br.kind == BOMB:
            self.schedule(0.07, lambda b=br: self.explode(b))

    def explode(self, br):
        cx, cy = br.cx, br.cy
        self.parts.explosion(cx, cy)
        self.fx.shake(0.45)
        self.fx.flash((255, 150, 60), 0.35)
        self.fx.aberration(7)
        self.fx.freeze(0.045)
        self.grid_flash = 1.2
        self.audio.play("explosion", 1.0, self.pan(cx), min_gap=0.05)
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                nb = self.grid.get((br.col + dc, br.row + dr))
                if nb is not None and nb.alive and nb.destructible:
                    delay = 0.04 + 0.03 * (abs(dc) + abs(dr))
                    self.schedule(delay, lambda n=nb, d=(dc, dr): self.damage(n, 99, "bomb", None,
                                                                             -d[0], -d[1]))

    # ================================================================== bonus
    def maybe_drop(self, br):
        if br.kind == PRISM:
            self.spawn_capsule(br.cx, br.cy, self.pick_powerup(good=True))
            return
        if len(self.capsules) >= 3 or self.state != "play":
            return
        self.drops_since += 1
        chance = 0.11 + (0.3 if self.drops_since > 14 else 0.0)
        if self.rng.random() < chance:
            self.spawn_capsule(br.cx, br.cy, self.pick_powerup())

    def pick_powerup(self, good=False):
        pool = [(k, w) for k, w in DROP_WEIGHTS.items()
                if not (good and k in MALUS) and not (k == "♥" and self.lives >= MAX_LIVES)
                and not (k == "M" and len(self.balls) >= MAX_BALLS)]
        total = sum(w for _, w in pool)
        r = self.rng.uniform(0, total)
        for k, w in pool:
            r -= w
            if r <= 0:
                return k
        return pool[-1][0]

    def spawn_capsule(self, x, y, kind):
        self.drops_since = 0
        self.capsules.append(Capsule(x, y, kind))
        self.audio.play("spawn", 0.8, self.pan(x))
        self.parts.ring(x, y, POWERUPS[kind][0], 36, life=0.35, width=2)

    def collect(self, cap):
        k = cap.kind
        color, name, _ = POWERUPS[k]
        p = self.paddle
        self.stats["bonus"] += 1
        self.add_score(100)
        # plusieurs bonus attrapés coup sur coup : on empile leurs noms
        self.recent_pickups = [t for t in self.recent_pickups if self.time - t < 0.5] + [self.time]
        stack = len(self.recent_pickups) - 1
        self.parts.text(p.x, p.top - 34 - 24 * stack, name, 18, color, life=1.1, vy=-55)
        self.parts.ring(cap.x, p.y, color, 80, life=0.4, width=3)
        self.parts.sparks_burst(cap.x, p.top, lighten(color, 0.3), 24, speed=(100, 380),
                                angle=-math.pi / 2, spread=2.8, grav=350)
        self.parts.blob(cap.x, p.y, color, 90, life=0.35)
        p.flash = 1.0
        pan = self.pan(cap.x)
        if k in MALUS:
            self.audio.play("malus", 0.9, pan)
            self.fx.add_glitch(0.25)
        elif k == "♥":
            self.audio.play("life", 0.9, pan)
        else:
            self.audio.play("powerup", 0.9, pan)
        if k in TIMED:
            self.effects[k] = TIMED[k]
        if k == "G":
            self.effects.pop("P", None)
            p.target_w = PADDLE_W_WIDE
        elif k == "P":
            self.effects.pop("G", None)
            p.target_w = PADDLE_W_NARROW
        elif k == "R":
            self.effects.pop("V", None)
        elif k == "V":
            self.effects.pop("R", None)
        elif k == "F":
            for b in self.balls:
                b.fire = True
        elif k == "M":
            self.multiball()
        elif k == "♥":
            if self.lives < MAX_LIVES:
                self.lives += 1
                self.hud_bump["lives"] = 1.0

    def expire(self, k):
        if k in ("G", "P"):
            self.paddle.target_w = PADDLE_W
        elif k == "F":
            for b in self.balls:
                b.fire = False
        elif k == "A":
            if any(b.stuck for b in self.balls) and self.state == "play":
                self.launch()

    def multiball(self):
        new = []
        for b in self.balls:
            if not b.alive:
                continue
            if b.stuck:
                continue
            ang = math.atan2(b.vx, -b.vy)
            for d in (-0.38, 0.38):
                if len(self.balls) + len(new) >= MAX_BALLS:
                    break
                nb = Ball(b.x, b.y, b.speed)
                nb.stuck = False
                nb.fire = b.fire
                nb.set_angle(ang + d, b.speed * self.speed_mult)
                nb.fix_angle()
                new.append(nb)
                self.parts.ring(b.x, b.y, (0, 225, 255), 40, life=0.3, width=2)
        self.balls.extend(new)
        if not new and any(b.stuck for b in self.balls):
            self.launch()
            self.multiball()

    # ================================================================== événements majeurs
    def ball_lost(self, b):
        self.parts.sparks_burst(b.x, PF_BOTTOM - 4, (255, 60, 90), 22, speed=(100, 420),
                                angle=-math.pi / 2, spread=1.4, grav=600)
        self.parts.blob(b.x, PF_BOTTOM, (255, 40, 80), 90, life=0.4)
        if any(o.alive for o in self.balls if o is not b):
            self.audio.play("back", 0.7, self.pan(b.x))

    def lose_life(self):
        self.set_state("dying")
        self.lives -= 1
        self.best_chain = max(self.best_chain, self.chain)
        self.chain = 0
        self.effects = {}
        self.capsules, self.lasers = [], []
        p = self.paddle
        p.visible = False
        self.parts.shards_burst(p.x, p.y, p.w, p.h, (120, 230, 255), n=14, force=1.6)
        self.parts.shards_burst(p.x, p.y, p.w, p.h, (255, 60, 190), n=8, force=1.4)
        self.parts.sparks_burst(p.x, p.y, (255, 90, 120), 40, speed=(100, 600), life=(0.3, 0.9))
        self.parts.ring(p.x, p.y, (255, 60, 90), 140, life=0.6, width=5)
        self.parts.blob(p.x, p.y, (255, 50, 90), 160, life=0.6)
        self.fx.shake(0.75)
        self.fx.flash((255, 30, 60), 0.55)
        self.fx.aberration(10)
        self.fx.add_glitch(0.9)
        self.audio.play("lose")
        self.audio.set_music_mode("pause")
        self.hud_bump["lives"] = 1.0

    def level_cleared(self, last):
        self.set_state("clear")
        self.best_chain = max(self.best_chain, self.chain)
        self.level_chain = self.chain
        self.chain = 0
        self.fx.slowmo(0.22, 1.1)
        self.fx.flash((255, 255, 255), 0.75)
        self.fx.shake(0.4)
        self.fx.aberration(6)
        self.capsules, self.lasers = [], []
        self.effects = {}
        self.paddle.target_w = PADDLE_W
        self.level_bonus = 1000 * (self.level + 1) + 250 * self.lives
        lx, ly = (last.cx, last.cy) if last is not None else (PF_CX, 300)
        self.parts.confetti_burst(lx, ly, 80, 1.2)
        self.parts.firework(lx, ly, self.theme.accent)
        self.audio.play("clear")
        self.audio.set_music_mode("intro")
        s = self.app.settings
        s.best_level = max(s.best_level, self.level + 2)
        for i in range(7):
            x = PF_LEFT + 120 + self.rng.uniform(0, PF_W - 240)
            col = hsv(self.rng.random(), 0.75, 1.0)
            self.schedule(0.25 + i * 0.3, lambda x=x, c=col: self.parts.rocket(x, PF_BOTTOM, self.rng.uniform(150, 330), c))

    def game_over(self):
        self.set_state("gameover")
        s = self.app.settings
        self.new_record = self.score > s.best_score
        if self.new_record:
            s.best_score = self.score
            self.schedule(1.4, lambda: self.audio.play("record"))
            for i in range(10):
                x = PF_LEFT + 100 + self.rng.uniform(0, PF_W - 200)
                col = hsv(self.rng.random(), 0.75, 1.0)
                self.schedule(0.8 + i * 0.35, lambda x=x, c=col: self.parts.rocket(x, PF_BOTTOM, self.rng.uniform(120, 300), c))
        s.best_level = max(s.best_level, self.level + 1)
        s.save()
        self.audio.play("gameover")
        self.audio.set_music_mode("gameover")
        self.fx.add_glitch(0.6)

    # ================================================================== rendu
    def draw(self, canvas, glow):
        pulse = self.audio.beat_pulse()
        speed = 0.45 + min(1.6, self.chain * 0.035)
        self.bg.draw(canvas, glow, self.time, pulse=pulse, speed=speed, grid_boost=self.grid_flash * 0.6)
        blend_fill(canvas, PF_DIM, PF_RECT)
        glow.dim(PF_RECT, PF_DIM)
        for r in (LEFT_PANEL, RIGHT_PANEL):
            blend_fill(canvas, PANEL_DIM, r)
            glow.dim(r, (150, 150, 150))

        ox, oy = self.fx.offset
        glow.ox, glow.oy = ox, oy
        self.draw_frame(canvas, glow, ox, oy, pulse)
        self.draw_bricks(canvas, glow, ox, oy)
        if "B" in self.effects:
            self.draw_shield(canvas, glow, ox, oy)
        self.draw_capsules(canvas, glow, ox, oy)
        for l in self.lasers:
            canvas.blit(self.art.laser, (l.x - 3 + ox, l.y - 9 + oy))
            glow.rect(l.x - 3, l.y - 9, 6, 18, (160, 20, 50))
        self.parts.draw(canvas, glow, ox, oy)
        self.draw_paddle(canvas, glow, ox, oy)
        self.draw_balls(canvas, glow, ox, oy)
        self.parts.draw_texts(canvas, ox, oy)
        glow.ox = glow.oy = 0.0

        self.draw_hud(canvas, glow, pulse)
        self.draw_overlays(canvas, glow)

    def draw_frame(self, canvas, glow, ox, oy, pulse):
        th = self.theme
        col = th.frame
        if self.lives <= 1 and self.state not in ("gameover",):
            k = 0.5 + 0.5 * math.sin(self.time * 6.0)
            col = mix(col, (255, 40, 70), 0.6 + 0.4 * k)
        col = lighten(col, 0.15 * pulse)
        L, T, R, B = PF_LEFT - 2 + ox, PF_TOP - 2 + oy, PF_RIGHT + 1 + ox, HEIGHT + 10
        pts = [(L, B), (L, T), (R, T), (R, B)]
        pygame.draw.lines(canvas, scale(col, 0.85), False, pts, 4)
        pygame.draw.lines(canvas, lighten(col, 0.65), False, pts, 1)
        gcol = scale(col, 0.55 + 0.25 * pulse)
        glow.line((PF_LEFT - 2, HEIGHT), (PF_LEFT - 2, PF_TOP - 2), gcol, 2)
        glow.line((PF_LEFT - 2, PF_TOP - 2), (PF_RIGHT + 1, PF_TOP - 2), gcol, 2)
        glow.line((PF_RIGHT + 1, PF_TOP - 2), (PF_RIGHT + 1, HEIGHT), gcol, 2)
        for x, y in ((L, T), (R, T)):
            pygame.draw.rect(canvas, (255, 255, 255), (x - 3, y - 3, 7, 7))
            glow.rect(x - ox - 6, y - oy - 6, 12, 12, col)
        for x, y, t, c in self.wall_flashes:
            k = t / 0.4
            glow.blob(x, y, 70, scale(c, 0.9 * k))
            if x in (PF_LEFT, PF_RIGHT):
                xx = (PF_LEFT - 2 if x == PF_LEFT else PF_RIGHT + 1) + ox
                pygame.draw.line(canvas, lighten(c, 0.3 + 0.7 * k), (xx, y - 36 * k + oy),
                                 (xx, y + 36 * k + oy), 3)
            else:
                pygame.draw.line(canvas, lighten(c, 0.3 + 0.7 * k), (x - 36 * k + ox, PF_TOP - 2 + oy),
                                 (x + 36 * k + ox, PF_TOP - 2 + oy), 3)

    def draw_bricks(self, canvas, glow, ox, oy):
        art = self.art
        t = self.time
        # reflet diagonal qui balaie le mur toutes les 6 secondes
        cyc = t % 6.0
        sweep = PF_LEFT - 300 + cyc / 1.4 * (PF_W + 600) if cyc < 1.4 else None
        for b in self.bricks:
            if not b.alive:
                continue
            a = b.appear if self.state == "intro" else 1.0
            if a <= 0:
                continue
            dy = (1.0 - ease_out_back(a)) * -46 if a < 1 else 0.0
            x = b.x + b.ox + ox
            y = b.y + b.oy + oy + dy
            shimmer = 0.022 * math.sin(t * 1.7 + b.col * 0.55 + b.row * 0.85)
            dmg = b.max_hp - b.hp
            spr = art.brick(b.kind, b.hue + shimmer, b.sat, dmg, int(t * 14 + b.col * 2) % 24)
            if a < 1:
                spr.set_alpha(int(255 * a))
                canvas.blit(spr, (x, y))
                spr.set_alpha(255)
            else:
                canvas.blit(spr, (x, y))
            if b.flash > 0:
                f = art.brick_flash
                f.set_alpha(int(220 * b.flash))
                canvas.blit(f, (x, y))
                f.set_alpha(255)
            if sweep is not None and b.kind != BOMB:
                sx = sweep - (b.y - GRID_TOP) * 0.7
                if x - 50 < sx < x + BRICK_W:
                    canvas.set_clip(pygame.Rect(int(x), int(y), BRICK_W, BRICK_H))
                    canvas.blit(art.shine, (sx, y))
                    canvas.set_clip(None)
            # halo néon chatoyant
            if b.kind == METAL:
                gc = (70, 75, 95)
            elif b.kind == BOMB:
                k = 0.5 + 0.5 * math.sin(t * 7.0 + b.col)
                gc = scale((255, 110, 30), 0.35 + 0.35 * k)
                pulse_r = 26 + 10 * k
                canvas.blit(art.glow(int(pulse_r), (140, 50, 10)), (x + BRICK_W / 2 - pulse_r, y + BRICK_H / 2 - pulse_r),
                            special_flags=pygame.BLEND_RGB_ADD)
            elif b.kind == PRISM:
                gc = hsv(t * 0.6 + b.col * 0.05, 0.6, 0.6)
            else:
                gc = hsv(b.hue + shimmer * 3.0, b.sat, 0.36 + 0.1 * b.flash)
            glow.rect(b.x + b.ox, b.y + b.oy + dy, BRICK_W, BRICK_H, gc)

    def draw_shield(self, canvas, glow, ox, oy):
        rem = self.effects.get("B", 0)
        if rem < 2.5 and int(rem * 8) % 2 == 0:
            return
        t = self.time
        col = (110, 255, 230)
        pts = [(x + ox, SHIELD_Y + math.sin(x * 0.045 + t * 9.0) * 2.5 + oy)
               for x in range(PF_LEFT, PF_RIGHT + 1, 16)]
        pygame.draw.lines(canvas, scale(col, 0.6), False, pts, 5)
        pygame.draw.lines(canvas, lighten(col, 0.6), False, pts, 1)
        glow.rect(PF_LEFT, SHIELD_Y - 4, PF_W, 8, scale(col, 0.45))

    def draw_capsules(self, canvas, glow, ox, oy):
        for c in self.capsules:
            frames = self.art.capsules[c.kind]
            spr = frames[int(c.t * 14) % len(frames)]
            x = c.x + math.sin(c.t * 5.0) * 3
            canvas.blit(spr, (x - spr.get_width() / 2 + ox, c.y - spr.get_height() / 2 + oy))
            color = POWERUPS[c.kind][0]
            glow.rect(x - 22, c.y - 10, 44, 20, scale(color, 0.55))

    def draw_paddle(self, canvas, glow, ox, oy):
        p = self.paddle
        if not p.visible:
            return
        spr = self.art.paddle(p.w, laser="L" in self.effects)
        w = spr.get_width()
        by = p.top - 8 + p.bounce
        for i, gx in enumerate(p.ghosts):
            spr.set_alpha(30 + 20 * i)
            canvas.blit(spr, (gx - w / 2 + ox, by + oy))
        spr.set_alpha(255)
        canvas.blit(spr, (p.x - w / 2 + ox, by + oy))
        k = p.flash
        gcol = mix((0, 110, 150), (80, 150, 190), k)
        glow.rect(p.left, p.top + p.bounce, p.w, p.h, gcol)
        if k > 0.3:
            r = int(30 + 20 * k)
            canvas.blit(self.art.glow(r, (30, 70, 100)), (p.x - r + ox, p.y - r + p.bounce + oy),
                        special_flags=pygame.BLEND_RGB_ADD)
        if "A" in self.effects:
            col = (200, 110, 255)
            for _ in range(2):
                pts = [(p.left + 10 + ox, p.top + oy)]
                n = 7
                for i in range(1, n):
                    pts.append((p.left + 10 + (p.w - 20) * i / n + ox,
                                p.top - 6 - self.rng.uniform(0, 10) + oy))
                pts.append((p.right - 10 + ox, p.top + oy))
                pygame.draw.lines(canvas, col, False, pts, 1)
            glow.rect(p.left, p.top - 14, p.w, 12, (70, 30, 110))

    def trail_color(self):
        c = self.chain
        if c >= 20:
            return hsv(self.time * 0.8, 0.7, 1.0)
        if c >= 12:
            return (255, 210, 80)
        if c >= 6:
            return (255, 80, 210)
        return (110, 210, 255)

    def draw_balls(self, canvas, glow, ox, oy):
        art = self.art
        base = self.trail_color()
        for b in self.balls:
            fire = b.fire
            tc = (255, 120, 30) if fire else base
            tq = (tc[0] // 16 * 16, tc[1] // 16 * 16, tc[2] // 16 * 16)
            n = len(b.trail)
            step = 1 if len(self.balls) <= 3 else 2
            for i in range(n % step, n, step):
                tx, ty = b.trail[i]
                k = (i + 1) / n
                rr = int(3 + 9 * k)
                g = art.glow(rr, scale(tq, 0.15 + 0.55 * k * k))
                canvas.blit(g, (tx - rr + ox, ty - rr + oy), special_flags=pygame.BLEND_RGB_ADD)
            halo = art.glow(30, scale(tq, 0.75))
            canvas.blit(halo, (b.x - 30 + ox, b.y - 30 + oy), special_flags=pygame.BLEND_RGB_ADD)
            core = art.ball_fire if fire else art.ball
            if b.squash > 0.05:
                s = b.squash
                d = core.get_width()
                sq = pygame.transform.smoothscale(core, (max(4, int(d * (1 - 0.35 * s))), int(d * (1 + 0.3 * s))))
                sq = pygame.transform.rotate(sq, -math.degrees(b.squash_ang))
                canvas.blit(sq, (b.x - sq.get_width() / 2 + ox, b.y - sq.get_height() / 2 + oy))
            else:
                canvas.blit(core, (b.x - core.get_width() / 2 + ox, b.y - core.get_height() / 2 + oy))
            glow.blob(b.x, b.y, 34, scale(tc, 0.7))

    # ------------------------------------------------------------------ interface
    def draw_hud(self, canvas, glow, pulse):
        font = self.font
        th = self.theme
        acc = th.accent
        lab = lighten(acc, 0.1)
        # ---- panneau gauche
        cx = PF_LEFT // 2
        x0, cw = 12, PF_LEFT - 26
        for rect in ((x0, 12, cw, 62), (x0, 86, cw, 156), (x0, 254, cw, 150), (x0, 416, cw, 116),
                     (x0, 544, cw, 164)):
            card(canvas, glow, rect, acc)
        logo = font.render("PRISMA", 26, hsv(int(self.app.time * 2.4) / 24.0, 0.65, 1.0),
                           core=(255, 255, 255), skew=0.18)
        logo.draw(canvas, cx, 43)
        font.render("SCORE", 12, lab, spacing=2.2).draw(canvas, cx, 108)
        bump = self.hud_bump["score"]
        font.draw_chars(canvas, fmt_score(self.shown_score), 22 + int(3 * bump), (255, 255, 255),
                        cx, 138, core=(255, 255, 255))
        font.render("RECORD", 12, lab, spacing=2.2).draw(canvas, cx, 184)
        best = max(self.best_before, self.score)
        font.draw_chars(canvas, fmt_score(best), 16, lighten(acc, 0.4), cx, 212)

        font.render("COMBO", 12, lab, spacing=2.2).draw(canvas, cx, 276)
        mult = self.multiplier()
        mc = MULT_COLORS[mult - 1] if mult < 8 else hsv(int(self.app.time * 12) / 12.0, 0.6, 1.0)
        cb = self.hud_bump["combo"]
        font.draw_chars(canvas, "×%d" % mult, 40 + int(8 * cb), mc, cx, 320)
        prog = (self.chain % 6) / 6.0 if mult < 8 else 1.0
        draw_bar(canvas, glow, cx - 70, 356, 140, 8, prog, scale(mc, 0.6), mc)
        font.draw_chars(canvas, "%d BRIQUE%s" % (self.chain, "S" if self.chain > 1 else ""), 11,
                        (190, 190, 225), cx, 382)

        # visualiseur audio
        self.draw_visualizer(canvas, glow, 26, 432, cw - 28, 76, pulse)
        hints = ("SOURIS / ← →", "CLIC / ESPACE", "LANCER · TIRER", "P : PAUSE", "M : MUSIQUE")
        for i, h in enumerate(hints):
            font.render(h, 10, (170, 170, 210), glow=0.3, spacing=1.2).draw(canvas, cx, 572 + i * 27)

        # ---- panneau droit
        rx = PF_RIGHT + (WIDTH - PF_RIGHT) // 2
        x1 = PF_RIGHT + 14
        n_fx = len(self.effects)
        for rect in ((x1, 12, cw, 138), (x1, 162, cw, 84), (x1, 258, cw, 92),
                     (x1, 362, cw, 58 + max(1, n_fx) * 38)):
            card(canvas, glow, rect, acc)
        font.render("NIVEAU", 12, lab, spacing=2.2).draw(canvas, rx, 34)
        font.draw_chars(canvas, str(self.level + 1), 40, (255, 255, 255), rx, 78, core=(255, 255, 255))
        font.render(self.level_name, 11, lighten(acc, 0.35), spacing=1.4).draw(canvas, rx, 124)

        font.render("VIES", 12, lab, spacing=2.2).draw(canvas, rx, 182)
        lb = self.hud_bump["lives"]
        n = max(0, self.lives)
        for i in range(n):
            col_i, row_i = i % 4, i // 4
            per_row = min(4, n - row_i * 4)
            x = rx - (per_row - 1) * 20 + col_i * 40
            y = 212 + row_i * 20
            icon = self.art.life_icon
            canvas.blit(icon, (x - icon.get_width() // 2, y - 6 - lb * 4))
            glow.rect(x - 15, y - 4, 30, 8, (0, 90, 130))

        font.render("BRIQUES", 12, lab, spacing=2.2).draw(canvas, rx, 278)
        done = self.total - self.remaining
        draw_bar(canvas, glow, rx - 72, 298, 144, 10, done / max(1, self.total), scale(acc, 0.5),
                 lighten(acc, 0.2))
        font.draw_chars(canvas, "%d / %d" % (done, self.total), 11, (200, 200, 230), rx, 326)

        font.render("BONUS", 12, lab, spacing=2.2).draw(canvas, rx, 382)
        y = 414
        for k, rem in sorted(self.effects.items(), key=lambda kv: -kv[1]):
            color, name, _ = POWERUPS[k]
            frames = self.art.capsules[k]
            canvas.blit(frames[int(self.app.time * 10) % len(frames)], (x1 + 8, y - 10))
            font.render(name, 9, lighten(color, 0.35), glow=0.4, spacing=1.0).draw(canvas, x1 + 58, y - 4,
                                                                                    "midleft")
            frac = rem / TIMED.get(k, 10.0)
            blink = rem > 2.5 or int(rem * 8) % 2 == 0
            if blink:
                draw_bar(canvas, glow, x1 + 58, y + 6, cw - 68, 4, frac, scale(color, 0.5), color)
            y += 38
        if not self.effects:
            font.render("AUCUN", 10, (130, 130, 170), glow=0.2).draw(canvas, rx, y)

        font.render("MUSIQUE" if self.audio.music_volume > 0 else "MUSIQUE COUPÉE", 9,
                    (150, 150, 190), glow=0.3).draw(canvas, rx, 692)

    def draw_visualizer(self, canvas, glow, x, y, w, h, pulse):
        spec = self.audio.spectrum_frame()
        n = 14
        bw = w / n
        th = self.theme
        for i in range(n):
            if spec is not None and self.audio.music_volume > 0:
                v = float(spec[i])
            else:
                v = 0.15 + 0.2 * pulse * (1 - i / n) + 0.08 * math.sin(self.app.time * 3 + i)
            bh = max(2, int(h * v))
            col = mix(th.grid, th.accent, i / (n - 1))
            bx = int(x + i * bw)
            segs = bh // 5
            for s in range(segs):
                yy = y + h - (s + 1) * 5
                pygame.draw.rect(canvas, scale(col, 0.55 + 0.45 * s / max(1, h // 5)), (bx + 1, yy, int(bw) - 3, 3))
            glow.rect(bx + 1, y + h - bh, int(bw) - 3, bh, scale(col, 0.25))
        pygame.draw.line(canvas, scale(th.accent, 0.6), (x, y + h + 3), (x + w, y + h + 3), 1)

    def draw_overlays(self, canvas, glow):
        font = self.font
        th = self.theme
        s = self.state
        t = self.state_t
        if s in ("intro", "ready") and (s == "intro" or t < 1.2):
            total = 2.1 + (1.2 if s == "ready" else 0.0)
            tt = t if s == "intro" else t + 2.1
            k_in = ease_out_back(clamp(tt / 0.5, 0, 1))
            k_out = 1.0 - ease_in_cubic(clamp((tt - (total - 0.5)) / 0.5, 0, 1))
            alpha = int(255 * clamp(k_out, 0, 1))
            dx = (1 - k_in) * -300
            if alpha > 0:
                title = font.render("NIVEAU %d" % (self.level + 1), 48, th.accent, core=(255, 255, 255),
                                    skew=0.15, glow=1.2)
                if tt < 0.3:
                    j = int((0.3 - tt) * 30)
                    title.draw(canvas, PF_CX + dx - j, 330, alpha=alpha // 2)
                    title.draw(canvas, PF_CX + dx + j, 334, alpha=alpha // 2)
                title.draw(canvas, PF_CX + dx, 332, alpha=alpha)
                sub = font.render(self.level_name, 22, lighten(th.frame, 0.2), spacing=2.4)
                sub.draw(canvas, PF_CX - dx, 392, alpha=alpha)
        if s == "ready" and not self.paused:
            a = int(160 + 95 * math.sin(self.app.time * 5.0))
            font.render("CLIC OU ESPACE POUR LANCER", 14, (220, 220, 255), spacing=1.6).draw(
                canvas, PF_CX, 560, alpha=a)
        if s == "dying":
            k = clamp(t / 0.3, 0, 1) * clamp((1.7 - t) / 0.6, 0, 1)
            nt = font.render("VIE PERDUE", 40, (255, 50, 80), core=(255, 220, 220), skew=0.12, glow=1.3)
            jit = self.rng.uniform(-3, 3) if t < 0.6 else 0
            nt.draw(canvas, PF_CX + jit, 360, alpha=int(255 * k))
            if self.lives > 0:
                font.render("%d VIE%s RESTANTE%s" % (self.lives, "S" if self.lives > 1 else "",
                                                      "S" if self.lives > 1 else ""),
                            16, (255, 170, 190)).draw(canvas, PF_CX, 412, alpha=int(255 * k))
        if s == "clear":
            k = ease_out_back(clamp((t - 0.3) / 0.5, 0, 1))
            if t > 0.3:
                col = hsv(int(self.app.time * 6) / 16.0, 0.6, 1.0)
                nt = font.render("NIVEAU TERMINÉ !", 44, col, core=(255, 255, 255), skew=0.12, glow=1.2)
                nt.draw(canvas, PF_CX, 300 + (1 - k) * 60, alpha=int(255 * clamp((t - 0.3) * 3, 0, 1)))
            if t > 1.4:
                bonus = 1000 * (self.level + 1) + 250 * self.lives
                font.render("BONUS +%s" % fmt_score(bonus), 24, (255, 230, 120)).draw(
                    canvas, PF_CX, 370, alpha=int(255 * clamp((t - 1.4) * 3, 0, 1)))
            if t > 2.0:
                txt = "MODE INFINI DÉBLOQUÉ !" if self.level + 1 == level_count() else \
                    "COMBO FINAL : %d BRIQUES" % self.level_chain
                font.render(txt, 16, (200, 220, 255)).draw(canvas, PF_CX, 420,
                                                           alpha=int(255 * clamp((t - 2.0) * 3, 0, 1)))
        if self.paused:
            self.draw_pause(canvas, glow)
        if s == "gameover":
            self.draw_gameover(canvas, glow)

    def draw_pause(self, canvas, glow):
        dim = (52, 46, 68)
        blend_fill(canvas, dim, PF_RECT)
        glow.dim(PF_RECT, dim)
        font = self.font
        nt = font.render("PAUSE", 64, self.theme.accent, core=(255, 255, 255), skew=0.15, glow=1.3)
        nt.draw(canvas, PF_CX, 230 + math.sin(self.app.time * 2) * 4)
        self.pause_menu.accent = self.theme.accent
        self.pause_menu.draw(canvas, glow)
        font.render("M : MUSIQUE   ·   F11 : PLEIN ÉCRAN", 11, (170, 170, 210), glow=0.3).draw(
            canvas, PF_CX, 580)

    def draw_gameover(self, canvas, glow):
        t = self.state_t
        k = clamp(t / 0.8, 0, 1)
        v = int(255 - 150 * k)
        dim = (v, int(v * 0.85), int(v * 1.0))
        blend_fill(canvas, dim, PF_RECT)
        glow.dim(PF_RECT, dim)
        font = self.font
        go = font.render("GAME OVER", 72, (255, 40, 110), core=(255, 230, 240), skew=0.15, glow=1.4)
        y = 210 + (1 - ease_out_back(k)) * -120
        if self.rng.random() < 0.08:
            go.draw(canvas, PF_CX + self.rng.uniform(-10, 10), y, alpha=160)
        go.draw(canvas, PF_CX, y, alpha=int(255 * k))
        if t > 0.6:
            a = int(255 * clamp((t - 0.6) * 3, 0, 1))
            font.render("SCORE", 14, (200, 200, 240), spacing=2.2).draw(canvas, PF_CX, 300, alpha=a)
            font.draw_chars(canvas, fmt_score(self.score), 40, (255, 255, 255), PF_CX, 340, alpha=a,
                            core=(255, 255, 255))
            if self.new_record:
                col = hsv(int(self.app.time * 10) / 16.0, 0.65, 1.0)
                font.render("NOUVEAU RECORD !", 26, col, core=(255, 255, 255), skew=0.1).draw(
                    canvas, PF_CX, 396 + math.sin(self.app.time * 8) * 3, alpha=a)
            else:
                font.render("RECORD : %s" % fmt_score(self.app.settings.best_score), 16,
                            (200, 160, 255)).draw(canvas, PF_CX, 396, alpha=a)
            font.render("NIVEAU %d  ·  %d BRIQUES  ·  COMBO MAX %d" % (
                self.level + 1, self.stats["bricks"], self.best_chain), 12, (170, 170, 220), glow=0.3).draw(
                canvas, PF_CX, 446, alpha=a)
        if self.over_menu:
            self.over_menu.accent = (255, 60, 150)
            self.over_menu.draw(canvas, glow)
