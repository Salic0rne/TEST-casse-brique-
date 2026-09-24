"""Écran titre, options et aide."""

import math
import random

import pygame

from . import surf as S
from .config import HEIGHT, HORIZON, VERSION, WIDTH
from .sprites import ARMOR, BOMB, HARD, METAL, NORMAL, POWERUPS, PRISM
from .ui import Menu, MenuItem, corner_brackets
from .util import clamp, ease_out_cubic, hsv, lighten, scale

ACCENT = (255, 60, 200)
CYAN = (0, 230, 255)


class Logo:
    """Logo « PRISMA » en tubes néon parcourus par un arc-en-ciel animé."""

    def __init__(self, font, text="PRISMA", size=118):
        self.edge = font.render(text, size, (255, 255, 255), core=(255, 255, 255), core_ratio=0,
                                skew=0.2, glow=1.0, glow_radius=20, thick=13)
        self.core = font.render(text, size, (255, 255, 255), core=(255, 255, 255), core_ratio=0,
                                skew=0.2, glow=0, thick=4.5)
        w, h = self.edge.tube.get_size()
        self.w, self.h = w, h
        self.rainbow = S.rainbow_strip(w * 2, h, sat=0.78, cycles=2).convert()
        self.tmp_glow = pygame.Surface((w, h)).convert()

    def draw(self, canvas, cx, cy, t, alpha=255):
        w = self.w
        off = int(t * 110) % w
        px, py = self.edge.origin(cx, cy)
        self.tmp_glow.blit(self.rainbow, (0, 0), (off, 0, w, self.h))
        self.tmp_glow.blit(self.edge.glow, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if alpha < 255:
            v = alpha
            S.blend_fill(self.tmp_glow, (v, v, v))
        canvas.blit(self.tmp_glow, (px, py), special_flags=pygame.BLEND_RGB_ADD)
        tube = self.edge.tube.copy()
        tube.blit(self.rainbow, (0, 0), (off + 60, 0, w, self.h), special_flags=pygame.BLEND_RGB_MULT)
        if alpha < 255:
            tube.set_alpha(alpha)
        canvas.blit(tube, (px, py))
        self.core.draw(canvas, cx, cy, alpha=alpha)


class FloatingBrick:
    def __init__(self, rng, art, initial=False):
        self.rng = rng
        side = rng.choice((-1, 1))
        self.x = rng.uniform(40, 330) if side < 0 else rng.uniform(950, 1240)
        self.y = rng.uniform(80, HEIGHT + 40) if initial else HEIGHT + rng.uniform(20, 120)
        self.vy = -rng.uniform(14, 34)
        self.vx = rng.uniform(-6, 6)
        self.ang = rng.uniform(0, 360)
        self.va = rng.uniform(-30, 30)
        self.scale = rng.uniform(0.45, 0.85)
        kind = rng.choice((NORMAL, NORMAL, NORMAL, HARD, PRISM, METAL, BOMB))
        self.spr = art.brick(kind, rng.random(), 0.85, 0, rng.randrange(24))
        self.hue = rng.random()
        self.alive = True


class TitleScene:
    show_cursor = True

    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.rng = random.Random()
        app.bg.set_theme(0)
        app.audio.set_track(0)
        app.audio.set_music_mode("menu")
        app.particles.clear()
        app.fx.reset()
        self.mode = "main"
        self.logo = Logo(app.font)
        self.main_menu = Menu(app, [
            MenuItem("JOUER", self.play),
            MenuItem("OPTIONS", lambda: self.set_mode("options")),
            MenuItem("COMMANDES", lambda: self.set_mode("help")),
            MenuItem("QUITTER", app.quit),
        ], WIDTH // 2, 468, spacing=50, size=24, accent=ACCENT, width=380)
        s = app.settings
        self.options_menu = Menu(app, [
            MenuItem("MUSIQUE", adjust=lambda d: self.adjust_volume("music_volume", d),
                     value=lambda: "%d %%" % round(s.music_volume * 100)),
            MenuItem("EFFETS SONORES", adjust=lambda d: self.adjust_volume("sfx_volume", d),
                     value=lambda: "%d %%" % round(s.sfx_volume * 100)),
            MenuItem("EFFET CRT", adjust=lambda d: self.toggle("crt"), value=lambda: "OUI" if s.crt else "NON"),
            MenuItem("SECOUSSES", adjust=lambda d: self.toggle("shake"), value=lambda: "OUI" if s.shake else "NON"),
            MenuItem("PLEIN ÉCRAN", adjust=lambda d: app.toggle_fullscreen(),
                     value=lambda: "OUI" if s.fullscreen else "NON"),
            MenuItem("RETOUR", lambda: self.set_mode("main")),
        ], WIDTH // 2, 404, spacing=46, size=19, accent=CYAN, on_back=lambda: self.set_mode("main"),
            width=560)
        self.banner = S.hgradient(680, 40, [(0.0, (255, 255, 255)), (0.2, (64, 50, 92)),
                                            (0.8, (64, 50, 92)), (1.0, (255, 255, 255))]).convert()
        self.banner_line = S.hgradient(680, 1, [(0.0, (0, 0, 0)), (0.3, CYAN), (0.7, CYAN),
                                                (1.0, (0, 0, 0))]).convert()
        self.bricks = [FloatingBrick(self.rng, app.art, initial=True) for _ in range(9)]
        self.dust = [[self.rng.uniform(0, WIDTH), self.rng.uniform(HORIZON, HEIGHT), self.rng.uniform(10, 40),
                      self.rng.uniform(0, 6.28)] for _ in range(50)]

    # ------------------------------------------------------------------ navigation
    def set_mode(self, mode):
        self.mode = mode
        if mode == "options":
            self.options_menu.sel = 0
        self.app.settings.save()

    def play(self):
        from .game import GameScene
        self.app.goto(lambda: GameScene(self.app, 0))

    def adjust_volume(self, attr, d):
        s = self.app.settings
        v = clamp(round(getattr(s, attr) + d * 0.1, 1), 0.0, 1.0)
        setattr(s, attr, v)
        self.app.apply_volumes()

    def toggle(self, attr):
        s = self.app.settings
        setattr(s, attr, not getattr(s, attr))

    def current_menu(self):
        return self.options_menu if self.mode == "options" else self.main_menu

    def on_action(self, action):
        if self.mode == "help":
            if action in ("back", "confirm", "pause"):
                self.app.audio.play("back")
                self.set_mode("main")
            return
        if self.mode == "main" and action == "back":
            return
        self.current_menu().on_action(action)

    def on_event(self, e):
        if self.mode == "help":
            if e.type == pygame.MOUSEBUTTONDOWN:
                self.app.audio.play("back")
                self.set_mode("main")
            return
        self.current_menu().on_event(e)

    # ------------------------------------------------------------------ boucle
    def update(self, dt, scale_t):
        self.t += dt
        self.current_menu().update(dt)
        for b in self.bricks:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.ang += b.va * dt
            if b.y < 60 and b.alive:
                b.alive = False
                col = hsv(b.hue, 0.8, 1.0)
                self.app.particles.brick_break(b.x, b.y, 40, 16, col, 0.7)
        self.bricks = [b for b in self.bricks if b.alive]
        while len(self.bricks) < 9:
            self.bricks.append(FloatingBrick(self.rng, self.app.art))
        for d in self.dust:
            d[1] -= d[2] * dt
            if d[1] < HORIZON:
                d[0], d[1] = self.rng.uniform(0, WIDTH), HEIGHT + 5
        self.app.particles.update(dt)

    def draw(self, canvas, glow):
        app = self.app
        t = self.t
        pulse = app.audio.beat_pulse()
        app.bg.draw(canvas, glow, app.time, pulse=pulse, speed=0.6)
        for x, y, v, ph in self.dust:
            k = 0.5 + 0.5 * math.sin(app.time * 2 + ph)
            c = scale((255, 120, 230), 0.4 + 0.6 * k)
            canvas.fill(c, (x, y, 2, 2))
            glow.dot(x, y, scale(c, 0.5))
        for b in self.bricks:
            spr = pygame.transform.rotozoom(b.spr, b.ang, b.scale)
            canvas.blit(spr, (b.x - spr.get_width() / 2, b.y - spr.get_height() / 2))
            glow.blob(b.x, b.y, 30 * b.scale, scale(hsv(b.hue, 0.8, 1.0), 0.25))
        app.particles.draw(canvas, glow)

        if self.mode == "help":
            self.draw_help(canvas, glow)
            return

        # logo : allumage façon enseigne au néon puis flottement
        on = True
        if t < 1.1:
            on = self.rng.random() < min(0.95, 0.25 + t * 0.8)
        ly = 196 + math.sin(t * 1.3) * 6
        if on:
            self.logo.draw(canvas, WIDTH // 2, ly, app.time, alpha=255 if t > 1.1 else 200)
            glow.blob(WIDTH // 2, ly, 260, (40, 10, 50))
        sub_a = int(255 * clamp((t - 0.8) / 0.6, 0, 1))
        bx = WIDTH // 2 - 340
        canvas.blit(self.banner, (bx, 280), special_flags=pygame.BLEND_RGB_MULT)
        glow.dim((bx + 60, 280, 560, 40), (90, 90, 90))
        if sub_a > 0:
            canvas.blit(self.banner_line, (bx, 280), special_flags=pygame.BLEND_RGB_ADD)
            canvas.blit(self.banner_line, (bx, 319), special_flags=pygame.BLEND_RGB_ADD)
        app.font.render("CASSE-BRIQUE NÉON", 22, CYAN, core=(220, 255, 255), spacing=3.2).draw(
            canvas, WIDTH // 2, 300, alpha=sub_a)

        menu = self.current_menu()
        k = ease_out_cubic(clamp((t - 0.5) / 0.6, 0, 1))
        if self.mode == "options":
            panel = pygame.Rect(WIDTH // 2 - 320, 352, 640, 316)
        else:
            panel = pygame.Rect(WIDTH // 2 - 220, 424, 440, 196)
        dim = (58, 50, 80) if self.mode == "options" else (96, 86, 120)
        S.blend_fill(canvas, dim, panel)
        glow.dim(panel, (70, 70, 70) if self.mode == "options" else (120, 120, 120))
        corner_brackets(canvas, panel, scale(menu.accent, 0.9), 14, 2)
        if self.mode == "options":
            app.font.render("OPTIONS", 20, CYAN, spacing=3.0).draw(canvas, WIDTH // 2, 372)
        menu.top = (404 if self.mode == "options" else 468) + (1 - k) * 40
        menu.draw(canvas, glow, alpha=int(255 * k))

        s = app.settings
        foot = (180, 170, 220)
        app.font.render("RECORD  %s" % "{:,}".format(s.best_score).replace(",", " "), 14,
                        lighten(ACCENT, 0.3), spacing=1.6).draw(canvas, 40, 690, "midleft")
        app.font.render("NIVEAU MAX  %d" % s.best_level, 14, lighten(CYAN, 0.3), spacing=1.6).draw(
            canvas, WIDTH - 40, 690, "midright")
        hint = "HAUT / BAS  ·  ENTRÉE  ·  SOURIS" if self.mode == "main" else \
            "GAUCHE / DROITE : RÉGLER  ·  ÉCHAP : RETOUR"
        app.font.render(hint, 11, foot, glow=0.3, spacing=1.4).draw(canvas, WIDTH // 2, 690)
        app.font.render("VERSION " + VERSION, 11, (130, 120, 175), glow=0.2, spacing=1.6).draw(
            canvas, WIDTH - 40, 24, "midright")
        if app.audio.enabled and not app.audio.music_ready:
            dots = "." * (1 + int(app.time * 3) % 3)
            app.font.render("SYNTHÈSE DE LA MUSIQUE" + dots, 10, (190, 170, 240), glow=0.4).draw(
                canvas, 40, 24, "midleft")

    # ------------------------------------------------------------------ aide
    def draw_help(self, canvas, glow):
        app = self.app
        font = app.font
        panel = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
        S.blend_fill(canvas, (70, 62, 92), panel)
        glow.dim(panel, (90, 90, 90))
        corner_brackets(canvas, panel, ACCENT, 16, 2)
        font.render("COMMANDES", 30, ACCENT, core=(255, 255, 255), skew=0.12).draw(canvas, 340, 92)
        controls = [
            ("SOURIS / FLÈCHES / Q D", "DÉPLACER LA RAQUETTE"),
            ("MAJ + FLÈCHES", "DÉPLACEMENT RAPIDE"),
            ("CLIC / ESPACE", "LANCER · TIRER AU LASER"),
            ("P / ÉCHAP", "PAUSE"),
            ("M", "COUPER LA MUSIQUE"),
            ("F11", "PLEIN ÉCRAN"),
            ("MANETTE", "STICK · A · START"),
        ]
        for i, (k, v) in enumerate(controls):
            y = 150 + i * 40
            font.render(k, 13, CYAN, spacing=1.4).draw(canvas, 110, y, "midleft")
            font.render(v, 12, (220, 220, 245), glow=0.3, spacing=1.2).draw(canvas, 400, y, "midleft")

        font.render("BONUS", 30, CYAN, core=(255, 255, 255), skew=0.12).draw(canvas, 930, 92)
        for i, (k, (color, name, desc)) in enumerate(POWERUPS.items()):
            y = 146 + i * 38
            frames = app.art.capsules[k]
            canvas.blit(frames[int(app.time * 10 + i) % len(frames)], (700, y - 10))
            font.render(name, 12, lighten(color, 0.3), spacing=1.2).draw(canvas, 760, y - 5, "midleft")
            font.render(desc, 9, (190, 190, 220), glow=0.2, spacing=1.1).draw(canvas, 760, y + 10, "midleft")

        font.render("BRIQUES", 22, ACCENT, core=(255, 255, 255), skew=0.12).draw(canvas, 340, 470)
        kinds = [(NORMAL, "SIMPLE", 0), (HARD, "RENFORCÉE", 0), (ARMOR, "BLINDÉE", 0),
                 (METAL, "MÉTAL", 0), (BOMB, "EXPLOSIVE", 0), (PRISM, "PRISME", int(app.time * 12) % 24)]
        for i, (kind, name, ph) in enumerate(kinds):
            x = 120 + (i % 3) * 180
            y = 520 + (i // 3) * 66
            spr = app.art.brick(kind, 0.55 + i * 0.12, 0.85, 0, ph)
            canvas.blit(spr, (x, y - 12))
            font.render(name, 10, (210, 210, 240), glow=0.3).draw(canvas, x + 30, y + 26)
        tips = ["ENCHAÎNEZ LES BRIQUES SANS TOUCHER", "LA RAQUETTE POUR MULTIPLIER LES POINTS.",
                "LES BRIQUES EXPLOSIVES DÉCLENCHENT", "DES RÉACTIONS EN CHAÎNE !"]
        for i, tip in enumerate(tips):
            font.render(tip, 11, (230, 200, 255), glow=0.4, spacing=1.2).draw(canvas, 930, 530 + i * 24)
        a = int(170 + 85 * math.sin(app.time * 4))
        font.render("ÉCHAP / CLIC : RETOUR", 12, (200, 200, 240), spacing=1.6).draw(canvas, WIDTH // 2, 652,
                                                                                    alpha=a)
