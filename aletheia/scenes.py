"""Scènes : chargement, titre, prologue, jeu (pause / continue / fin), options, Panthéon, saisie du nom,
épilogue et générique."""
import math
import random

import numpy as np
import pygame

from . import palette as P
from . import font as F
from . import ui
from .app import Scene
from .config import SCREEN_W, SCREEN_H, PF_X, PF_W, PF_H, DIFFICULTIES
from .spritegen import fbm, arrays_to_surface, rgb_surface, box_blur, L, forge, rect, circle, sym, ellipse, arc
from .fx import glow, bolt_points, draw_bolt, draw_bolt_tree
from .util import clamp, lerp, ease_out_cubic, ease_out_back, TAU

WHITE = (255, 255, 255)
PALE = (200, 206, 240)
DIM = (120, 120, 170)
GOLD = (236, 190, 90)


# ---------------------------------------------------------------------------
# Décor du titre : Jupiter, anneaux, citadelle d'Olympos flottante
# ---------------------------------------------------------------------------
def build_sky(w=SCREEN_W, h=SCREEN_H, seed=3):
    yy = np.linspace(0, 1, h)[None, :]
    top = np.array([4, 2, 14], np.float32)
    mid = np.array([22, 10, 44], np.float32)
    bot = np.array([60, 20, 60], np.float32)
    k = yy[..., None]
    rgb = np.where(k < 0.6, top * (1 - k / 0.6) + mid * (k / 0.6), mid * (1 - (k - 0.6) / 0.4) + bot * ((k - 0.6) / 0.4))
    rgb = np.broadcast_to(rgb, (w, h, 3)).copy()
    neb = fbm(w, h, 5, 3, 5, seed=seed)
    neb2 = fbm(w, h, 8, 5, 4, seed=seed + 1)
    m = np.clip((neb - 0.45) / 0.4, 0, 1) ** 1.6
    rgb += m[..., None] * np.array([90, 30, 110], np.float32) * 0.8
    m2 = np.clip((neb2 - 0.55) / 0.35, 0, 1) ** 2
    rgb += m2[..., None] * np.array([20, 70, 120], np.float32)
    rng = np.random.default_rng(seed)
    for _ in range(420):
        x, y = rng.integers(0, w), rng.integers(0, h)
        b = rng.random() ** 3 * 200 + 40
        rgb[x, y] = np.minimum(255, rgb[x, y] + b)
    from .backgrounds import dither_quant
    return rgb_surface(dither_quant(rgb, 40))


def build_planet(r=150, seed=9):
    size = r * 2 + 4
    xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
    cx = cy = size / 2
    dx, dy = (xx - cx) / r, (yy - cy) / r
    d2 = dx * dx + dy * dy
    inside = d2 <= 1
    z = np.sqrt(np.clip(1 - d2, 0, 1))
    # bandes atmosphériques (bruit étiré horizontalement + turbulence)
    n = fbm(size, size, 3, 14, 5, seed=seed)
    turb = fbm(size, size, 8, 8, 3, seed=seed + 1)
    lat = dy + (turb - 0.5) * 0.12
    bands = np.sin(lat * 18 + n * 3.0) * 0.5 + 0.5
    v = np.clip(bands * 0.7 + n * 0.4, 0, 1)
    rgb = np.zeros((size, size, 3), np.float32)
    stops = [(0.0, (120, 60, 50)), (0.3, (190, 120, 80)), (0.5, (230, 190, 140)), (0.7, (250, 234, 206)),
             (0.85, (200, 150, 110)), (1.0, (150, 90, 70))]
    from .backgrounds import ramp_map
    rgb = ramp_map(v, stops)
    # l'Œil de Zeus (grande tache)
    ex, ey = 0.25, 0.35
    e = ((dx - ex) / 0.22) ** 2 + ((dy - ey) / 0.1) ** 2
    spot = np.clip(1 - e, 0, 1)
    rgb = rgb * (1 - spot[..., None] * 0.7) + np.array([220, 90, 50], np.float32) * spot[..., None] * 0.7
    # éclairage (soleil à gauche) + assombrissement du limbe
    lx, ly, lz = -0.75, -0.35, 0.55
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    lam = np.clip((dx * lx + dy * ly + z * lz) / ln, 0, 1)
    shade = 0.12 + 0.95 * lam ** 0.8
    rgb *= shade[..., None]
    rim = np.clip(1 - z, 0, 1) ** 3
    rgb += rim[..., None] * np.array([60, 90, 160], np.float32) * lam[..., None]
    alpha = inside.astype(np.float32) * 255
    edge = (d2 > 0.985) & inside
    alpha[edge] = 200
    from .backgrounds import dither_quant
    return arrays_to_surface(dither_quant(rgb, 36), alpha)


def build_rings(r=150):
    w, h = int(r * 3.4), int(r * 0.9)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    for i, (rr, col, a) in enumerate(((1.35, (200, 170, 150), 90), (1.45, (230, 200, 170), 130),
                                      (1.52, (160, 130, 120), 70), (1.62, (210, 190, 170), 60))):
        rect_ = pygame.Rect(0, 0, int(r * rr * 2), int(r * rr * 0.42))
        rect_.center = (cx, cy)
        pygame.draw.ellipse(s, col + (a,), rect_, 3)
    return s


def build_citadel():
    """Rocher flottant portant le temple d'Olympos."""
    w, h = 170, 170
    layers = [
        # rocher (pointe vers le bas)
        L([[(-80, 30), (-60, 22), (-30, 26), (0, 20), (34, 24), (66, 20), (82, 30), (70, 50), (48, 78), (20, 112),
            (4, 148), (-12, 116), (-40, 84), (-64, 56)]], mat=P.STONE, bevel=3, noise=0.06, base=0.5),
        L([[(-66, 34), (-20, 32), (30, 32), (70, 34), (50, 48), (10, 46), (-40, 48)]], mat=P.OLIVE, bevel=2,
          base=0.5, clip=True),
        # stylobate
        L([rect(-58, 8, 58, 26)], mat=P.MARBLE, bevel=2, base=0.6, veins=0.08),
        L([rect(-52, 2, 52, 10)], mat=P.MARBLE, bevel=1.5, base=0.66),
        # colonnes
        L([rect(-48 + i * 12, -38, -42 + i * 12, 3) for i in range(9)], mat=P.MARBLE, bevel=1.5, base=0.62,
          profile="pillow"),
        L([rect(-50 + i * 12, -42, -40 + i * 12, -37) for i in range(9)], mat=P.MARBLE, bevel=1, base=0.68),
        # entablement + fronton doré
        L([rect(-56, -52, 56, -41)], mat=P.MARBLE, bevel=1.5, base=0.64),
        L([rect(-56, -49, 56, -46)], mat=P.GOLD, bevel=1, clip=True, cast=False),
        L([[(-60, -52), (0, -76), (60, -52)]], mat=P.MARBLE, bevel=2, base=0.6),
        L([[(-44, -55), (0, -71), (44, -55)]], mat=P.GOLD, bevel=1.5, spec=0.5),
        L([circle(0, -61, 4)], emit=P.CYAN_E, glow=1.5),
        # lumières du sanctuaire
        L([rect(-40 + i * 12, -30, -38 + i * 12, -4) for i in range(8)], emit=(90, 220, 255), glow=0.6),
        L([circle(-30, 60, 1.6), circle(22, 70, 1.4), circle(-6, 96, 1.2), circle(40, 46, 1.4)],
          emit=(120, 240, 255), glow=1.0),
    ]
    return forge(w, h, layers, anchor=(w / 2, 86), halo=4)


class TitleArt:
    def __init__(self):
        self.sky = build_sky()
        self.planet = build_planet()
        self.rings = build_rings()
        self.citadel = build_citadel()
        self.t = 0
        self.bolts = []
        self.flash = 0.0
        self.add = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
        self.twinkle = [(random.randrange(SCREEN_W), random.randrange(SCREEN_H), random.random() * 6)
                        for _ in range(70)]

    def update(self):
        self.t += 1
        if random.random() < 0.012:
            x = random.uniform(300, 470)
            self.bolts.append([x, random.uniform(150, 230), 8])
            self.flash = 0.5
        self.bolts = [[x, y, n - 1] for x, y, n in self.bolts if n > 1]
        self.flash = max(0.0, self.flash - 0.05)

    def draw(self, s, citadel_y=None):
        t = self.t
        s.blit(self.sky, (0, 0))
        # étoiles scintillantes
        for (x, y, ph) in self.twinkle:
            k = 0.5 + 0.5 * math.sin(t * 0.07 + ph)
            c = int(90 + 165 * k)
            s.fill((c, c, min(255, c + 20)), (x, y, 1, 1))
        # planète + anneaux
        px, py = 380, 310 + math.sin(t * 0.004) * 2
        rw = self.rings.get_width()
        rh = self.rings.get_height()
        back = self.rings.subsurface((0, 0, rw, rh // 2))
        s.blit(back, (px - rw // 2, py - rh // 2 - 30))
        s.blit(self.planet, (px - self.planet.get_width() // 2, py - self.planet.get_height() // 2))
        front = self.rings.subsurface((0, rh // 2, rw, rh - rh // 2))
        s.blit(front, (px - rw // 2, py - 30))
        # éclairs dans l'atmosphère jovienne
        a = self.add
        a.fill((0, 0, 0))
        for x, y, n in self.bolts:
            draw_bolt_tree(a, x, y - 30, x + random.uniform(-20, 20), y + 20, (200, 180, 255), 6, 1)
        # citadelle flottante
        cy = 150 + math.sin(t * 0.02) * 4 if citadel_y is None else citadel_y
        self.citadel.draw(s, 96, cy)
        self.citadel.draw_halo(a, 96, cy)
        # faisceau de la balise
        k = 0.6 + 0.4 * math.sin(t * 0.05)
        pygame.draw.line(a, (int(20 * k), int(70 * k), int(90 * k)), (96, cy - 70), (96, 0), 7)
        pygame.draw.line(a, (int(60 * k), int(160 * k), int(200 * k)), (96, cy - 70), (96, 0), 3)
        pygame.draw.line(a, (200, 250, 255), (96, cy - 70), (96, 0), 1)
        s.blit(a, (0, 0), special_flags=pygame.BLEND_ADD)
        if self.flash > 0:
            k = int(self.flash * 60)
            s.fill((k, k, int(k * 1.3)), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------
class LoadingScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.steps = [("LA FORGE S'ÉCHAUFFE", self.s_sprites), ("GRAVURE DES FRISES", self.s_hud),
                      ("ACCORD DE LA LYRE", self.s_sfx), ("L'HYMNE D'ALETHEIA", self.s_music)]
        self.i = 0
        self.progress = 0.0
        self.label = ""
        self.t = 0

    def draw_now(self, frac, label):
        self.progress = frac
        self.label = label
        self.draw(self.app.screen)
        self.app.display.present(self.app.screen)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                raise SystemExit
        self.t += 1

    def s_sprites(self, cb):
        from . import sprites
        sprites.build(cb)

    def s_hud(self, cb):
        from .hud import HUD
        self.app.hud = HUD()
        cb(1.0)

    def s_sfx(self, cb):
        self.app.audio.build_sfx(cb)

    def s_music(self, cb):
        self.app.audio.render_now("title", cb)

    def update(self):
        if self.i < len(self.steps):
            label, fn = self.steps[self.i]
            base = self.i / len(self.steps)

            def cb(p, _b=base, _l=label):
                self.draw_now(_b + p / len(self.steps), _l)

            fn(cb)
            self.i += 1
            return
        self.app.audio.start_music_thread()
        a = self.app.args
        if a is not None and getattr(a, "stage", 0):
            self.app.goto(GameScene(self.app, a.stage), fade=True)
        else:
            self.app.goto(TitleScene(self.app), fade=True)
        self.i += 1

    def draw(self, s):
        s.fill((6, 4, 14))
        font = F.FONT
        cx, cy = SCREEN_W // 2, SCREEN_H // 2
        t = self.t
        # cercle de méandres tournant
        for i in range(24):
            a = i * TAU / 24 + t * 0.02
            x, y = cx + math.cos(a) * 34, cy - 20 + math.sin(a) * 34
            c = GOLD if (i + t // 4) % 6 == 0 else (90, 60, 30)
            pygame.draw.rect(s, c, (int(x) - 2, int(y) - 2, 4, 4), 1)
        font.draw(s, ui.greekify("ALETHEIA"), cx, cy - 24, GOLD, "center", scale=2)
        w = 220
        pygame.draw.rect(s, (60, 40, 20), (cx - w // 2 - 2, cy + 30, w + 4, 8), 1)
        pygame.draw.rect(s, (255, 190, 80), (cx - w // 2, cy + 32, int(w * self.progress), 4))
        font.draw(s, self.label + "…", cx, cy + 44, PALE, "center")
        font.draw(s, "TOUT EST GÉNÉRÉ À LA VOLÉE : SPRITES, DÉCORS, SONS, MUSIQUES", cx, SCREEN_H - 16, DIM, "center")


# ---------------------------------------------------------------------------
# Menu générique
# ---------------------------------------------------------------------------
class Menu:
    def __init__(self, items):
        self.items = items      # liste de (texte ou callable, action)
        self.sel = 0
        self.t = 0

    def label(self, i):
        lab = self.items[i][0]
        return lab() if callable(lab) else lab

    def update(self, inp, audio):
        self.t += 1
        n = len(self.items)
        if inp.menu("up"):
            self.sel = (self.sel - 1) % n
            audio.play("menu_move")
        if inp.menu("down"):
            self.sel = (self.sel + 1) % n
            audio.play("menu_move")
        act = self.items[self.sel][1]
        if inp.menu("left") and isinstance(act, tuple):
            act[0](-1)
            audio.play("menu_move")
        if inp.menu("right") and isinstance(act, tuple):
            act[0](1)
            audio.play("menu_move")
        if inp.pressed("confirm"):
            if isinstance(act, tuple):
                act[0](1)
                audio.play("menu_move")
            elif act is not None:
                audio.play("menu_ok")
                act()

    def draw(self, s, cx, y, gap=14, width=170):
        font = F.FONT
        for i in range(len(self.items)):
            lab = self.label(i)
            sel = i == self.sel
            yy = y + i * gap
            if sel:
                k = 0.5 + 0.5 * math.sin(self.t * 0.15)
                bar = pygame.Surface((width, 11), pygame.SRCALPHA)
                bar.fill((120, 80, 20, int(80 + 60 * k)))
                s.blit(bar, (cx - width // 2, yy - 2))
                ui.laurel(s, cx - width // 2 + 8, yy + 3, False)
                ui.laurel(s, cx + width // 2 - 8, yy + 3, True)
                font.draw(s, lab, cx, yy, (255, 240, 200), "center", outline=(10, 6, 22))
            else:
                font.draw(s, lab, cx, yy, (150, 150, 200), "center", outline=(10, 6, 22))


# ---------------------------------------------------------------------------
# Titre
# ---------------------------------------------------------------------------
class TitleScene(Scene):
    ART = None

    def __init__(self, app):
        super().__init__(app)
        if TitleScene.ART is None:
            TitleScene.ART = TitleArt()
        self.art = TitleScene.ART
        self.logo = ui.metal_text(ui.greekify("ALETHEIA"), 4)
        self.shine = self.logo.copy()
        self.shine.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.shine.fill((110, 100, 70, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.t = 0
        self.idle = 0
        self.started = False
        o = app.save.options
        self.menu = Menu([
            ("JOUER", self.play),
            (lambda: "DIFFICULTÉ : " + DIFFICULTIES[o["difficulty"]]["name"], (self.change_diff,)),
            (lambda: "STADE : " + str(self.start_stage) if app.save.cleared > 1 else "PROLOGUE", self.story),
            ("OPTIONS", lambda: app.goto(OptionsScene(app, self))),
            ("PANTHÉON", lambda: app.goto(ScoresScene(app, self))),
            ("QUITTER", app.quit),
        ])
        self.start_stage = 1
        if app.save.cleared > 1:
            self.menu.items[2] = (lambda: "STADE DE DÉPART : " + str(self.start_stage), (self.change_stage,))
        app.audio.play_music("title", 1500)

    def change_diff(self, d):
        o = self.app.save.options
        o["difficulty"] = (o["difficulty"] + d) % len(DIFFICULTIES)
        self.app.save.save()

    def change_stage(self, d):
        mx = max(1, min(6, self.app.save.cleared))
        self.start_stage = (self.start_stage - 1 + d) % mx + 1

    def play(self):
        if self.start_stage == 1:
            self.app.goto(StoryScene(self.app, then_play=True))
        else:
            self.app.goto(GameScene(self.app, self.start_stage))

    def story(self):
        self.app.goto(StoryScene(self.app, then_play=False))

    def update(self):
        self.t += 1
        self.art.update()
        inp = self.app.input
        if inp.any_key:
            self.idle = 0
        else:
            self.idle += 1
        if self.t > 30:
            self.menu.update(inp, self.app.audio)
        if self.idle > 60 * 25:
            self.idle = 0
            self.app.goto(ScoresScene(self.app, self, auto=True))

    def draw(self, s):
        self.art.draw(s)
        t = self.t
        cx = SCREEN_W // 2 + 60
        k = ease_out_back(min(1.0, t / 50))
        lw, lh = self.logo.get_size()
        ly = int(26 - (1 - k) * 60)
        s.blit(self.logo, (cx - lw // 2, ly))
        # reflet qui balaie le logo
        sx = (t * 3) % (lw + 160) - 40
        for i in range(6):
            x = sx + i - int(i * 0.5)
            if 0 <= x < lw:
                s.blit(self.shine, (cx - lw // 2 + x, ly), (x, 0, 1, lh), special_flags=pygame.BLEND_RGB_ADD)
        font = F.FONT
        sub_y = ly + lh + 6
        ui.meander(s, cx - 150, sub_y + 1, 34, GOLD, (90, 60, 30), 5)
        ui.meander(s, cx + 116, sub_y + 1, 34, GOLD, (90, 60, 30), 5)
        font.draw(s, "LA CHUTE DE L'OLYMPE", cx, sub_y + 1, (255, 230, 180), "center", outline=(10, 6, 22))
        if t > 30:
            self.menu.draw(s, cx, 118, 15, 190)
        font.draw(s, "HOMMAGE À SUPER ALESTE · TOUT EST GÉNÉRÉ PROCÉDURALEMENT", SCREEN_W // 2, SCREEN_H - 12,
                  (110, 100, 150), "center", outline=(6, 4, 14))
        font.draw(s, "F11 PLEIN ÉCRAN · F2 CRT", 6, 4, (90, 80, 130), outline=(6, 4, 14))


# ---------------------------------------------------------------------------
# Prologue
# ---------------------------------------------------------------------------
STORY = [
    ["AN 2525.", "", "L'HUMANITÉ S'EST RÉPANDUE DANS LE SYSTÈME SOLAIRE,",
     "GUIDÉE PAR LE DODÉKATHÉON : DOUZE INTELLIGENCES", "BÂTIES À L'IMAGE DES ANCIENS DIEUX."],
    ["DEPUIS OLYMPOS, CITADELLE EN ORBITE DE JUPITER,", "ZEUS-Ω A RÉDUIT LES AUTRES DIEUX AU SILENCE",
     "ET RÉVEILLÉ LEURS AUTOMATES DE BRONZE.", "", "LES COLONIES TOMBENT UNE À UNE."],
    ["DANS LA FORGE SECRÈTE D'HÉPHAÏSTOS,", "UN DERNIER CHASSEUR A ÉTÉ ACHEVÉ :", "",
     "ALETHEIA — « LA VÉRITÉ DÉVOILÉE ».", "", "IL SAIT CAPTER LE POUVOIR DES DIEUX DÉCHUS."],
    ["TRAVERSE LA MER DE POSÉIDON, LE DÉDALE DE KNOSSOS,", "LA NUÉE DE MÉDUSE, LA FORGE D'IO ET LES ENFERS.", "",
     "MONTE JUSQU'À L'OLYMPE,", "ET DIS AUX DIEUX LA VÉRITÉ."],
]


class StoryScene(Scene):
    def __init__(self, app, then_play=True, pages=None, final=False):
        super().__init__(app)
        if TitleScene.ART is None:
            TitleScene.ART = TitleArt()
        self.art = TitleScene.ART
        self.pages = pages or STORY
        self.page = 0
        self.chars = 0
        self.t = 0
        self.then_play = then_play
        self.final = final

    def total(self):
        return sum(len(l) for l in self.pages[self.page])

    def update(self):
        self.t += 1
        self.art.update()
        inp = self.app.input
        if self.page >= len(self.pages):
            return
        if self.t % 2 == 0 and self.chars < self.total():
            self.chars += 1
            if self.chars % 3 == 0:
                self.app.audio.play("typing", None, 0.5, throttle=2)
        if inp.pressed("confirm") or inp.pressed("fire"):
            if self.chars < self.total():
                self.chars = self.total()
            else:
                self.page += 1
                self.chars = 0
                self.app.audio.play("menu_move")
                if self.page >= len(self.pages):
                    self.finish()
        if inp.pressed("back") or inp.pressed("pause"):
            self.page = len(self.pages)
            self.finish()

    def finish(self):
        if self.then_play:
            self.app.goto(GameScene(self.app, 1))
        else:
            self.app.goto(TitleScene(self.app))

    def draw(self, s):
        self.art.draw(s)
        veil = pygame.Surface((SCREEN_W, 120), pygame.SRCALPHA)
        veil.fill((4, 2, 14, 190))
        s.blit(veil, (0, 140))
        ui.meander(s, 20, 138, SCREEN_W - 40, GOLD, (90, 60, 30), 5)
        ui.meander(s, 20, SCREEN_H - 16, SCREEN_W - 40, GOLD, (90, 60, 30), 5)
        if self.page >= len(self.pages):
            return
        font = F.FONT
        left = self.chars
        y = 156
        for line in self.pages[self.page]:
            txt = line[:max(0, left)]
            left -= len(line)
            font.draw(s, txt, SCREEN_W // 2 - font.width(line) // 2, y, (235, 230, 255), outline=(6, 4, 14))
            y += 13
        if self.chars >= self.total() and (self.t // 20) % 2 == 0:
            font.draw(s, "▼" if False else "»", SCREEN_W - 40, SCREEN_H - 34, GOLD)


# ---------------------------------------------------------------------------
# Jeu
# ---------------------------------------------------------------------------
class GameScene(Scene):
    def __init__(self, app, stage=1):
        super().__init__(app)
        from .game import Game
        self.g = Game(app, stage)
        self.paused = False
        self.pause_menu = Menu([("REPRENDRE", self.resume), ("QUITTER LA PARTIE", self.quit_to_title)])
        self.cont_t = 0
        self.over_t = 0
        if app.args is not None and getattr(app.args, "autoplay", False):
            from .bot import Bot
            app.input.bot = Bot(self.g)

    def resume(self):
        self.paused = False
        self.app.audio.set_music_volume(1.0)

    def quit_to_title(self):
        self.app.audio.stop_loops()
        self.app.input.bot = None
        self.finish_game()

    def finish_game(self):
        g = self.g
        sc = g.score.score
        if self.app.save.rank_of(sc) is not None and sc > 0:
            self.app.goto(NameEntryScene(self.app, sc, g.stage_n))
        else:
            self.app.goto(TitleScene(self.app))

    def update(self):
        inp = self.app.input
        g = self.g
        if self.paused:
            self.pause_menu.update(inp, self.app.audio)
            if inp.pressed("pause") and self.pause_menu.t > 5:
                self.resume()
            return
        if inp.pressed("pause") and g.state in ("play", "intro"):
            self.paused = True
            self.pause_menu.sel = 0
            self.pause_menu.t = 0
            self.app.audio.stop_loops()
            self.app.audio.set_music_volume(0.35)
            self.app.audio.play("menu_back")
            return
        g.update(inp)
        if g.state == "continue":
            self.cont_t += 1
            if self.cont_t == 1:
                self.app.audio.play_music("gameover", 400, loop=False)
            left = 10 - self.cont_t // 60
            if self.cont_t > 40 and (inp.pressed("fire") or inp.pressed("confirm")) and g.continues > 0:
                self.cont_t = 0
                g.continue_game()
                self.app.audio.play("menu_ok")
                from .stages import MUSIC
                self.app.audio.play_music(MUSIC[g.stage_n] if g.boss is None else "boss", 500)
            elif left < 0 or g.continues <= 0 and self.cont_t > 150:
                g.state = "gameover"
                g.state_t = 0
        elif g.state == "gameover":
            self.over_t += 1
            if self.over_t > 240 or (self.over_t > 60 and inp.pressed("confirm")):
                self.app.input.bot = None
                self.finish_game()
        elif g.state == "ending":
            self.app.input.bot = None
            self.app.goto(EndingScene(self.app, g.score.score, g.stage_n))
            g.state = "ended"

    def draw(self, s):
        g = self.g
        s.fill((0, 0, 0), (PF_X - 10, 0, PF_W + 20, SCREEN_H))
        g.draw(s)
        self.app.hud.draw(s, g)
        font = F.FONT
        if g.state == "continue":
            veil = pygame.Surface((PF_W, PF_H), pygame.SRCALPHA)
            veil.fill((6, 2, 20, 150))
            s.blit(veil, (PF_X, 0))
            cx = PF_X + PF_W // 2
            ui.draw_metal(s, "CONTINUER ?", cx, 86, 2)
            left = max(0, 9 - self.cont_t // 60)
            k = 1 + 0.3 * (1 - (self.cont_t % 60) / 60)
            ui.draw_metal(s, str(left), cx, 116, int(3 * k + 0.5), P.MARBLE)
            if g.continues > 0:
                font.draw(s, f"CRÉDITS : {g.continues}", cx, 164, PALE, "center")
                if (self.cont_t // 20) % 2 == 0:
                    font.draw(s, "APPUIE SUR TIR", cx, 180, (255, 230, 150), "center")
            else:
                font.draw(s, "PLUS AUCUN CRÉDIT", cx, 170, (255, 120, 120), "center")
        elif g.state == "gameover":
            veil = pygame.Surface((PF_W, PF_H), pygame.SRCALPHA)
            veil.fill((6, 2, 20, min(200, self.over_t * 3)))
            s.blit(veil, (PF_X, 0))
            cx = PF_X + PF_W // 2
            if self.over_t > 20:
                ui.draw_metal(s, "ΤΕΛΟΣ", cx, 100, 3, P.MARBLE)
                font.draw(s, "FIN DE PARTIE", cx, 136, PALE, "center")
                font.draw(s, f"SCORE {g.score.score}", cx, 156, (255, 230, 150), "center")
        if self.paused:
            veil = pygame.Surface((PF_W, PF_H), pygame.SRCALPHA)
            veil.fill((6, 2, 20, 170))
            s.blit(veil, (PF_X, 0))
            cx = PF_X + PF_W // 2
            ui.draw_metal(s, "PAUSE", cx, 96, 2)
            self.pause_menu.draw(s, cx, 130, 16, 170)


# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
class OptionsScene(Scene):
    def __init__(self, app, back):
        super().__init__(app)
        self.back = back
        o = app.save.options

        def vol(key):
            def f(d):
                o[key] = int(clamp(o[key] + d, 0, 10))
                app.save.save()
                app.audio.apply_volumes()
            return f

        def tog(key, relayout=False, full=False):
            def f(d):
                if full:
                    app.display.toggle_fullscreen()
                    return
                o[key] = not o.get(key)
                app.save.save()
                if relayout:
                    app.display.relayout()
            return f

        def scale(d):
            o["scale"] = int((o.get("scale", 0) + d) % 7)
            app.save.save()
            if not o.get("fullscreen"):
                app.display.apply()

        def onoff(v):
            return "OUI" if v else "NON"

        self.menu = Menu([
            (lambda: f"MUSIQUE : {'■' * 0}{o['music']}/10", (vol("music"),)),
            (lambda: f"EFFETS : {o['sfx']}/10", (vol("sfx"),)),
            (lambda: f"PLEIN ÉCRAN : {onoff(o.get('fullscreen'))}", (tog("fullscreen", full=True),)),
            (lambda: f"ÉCHELLE : {'AUTO' if not o.get('scale') else str(o['scale']) + 'X'}", (scale,)),
            (lambda: f"FILTRE CRT : {onoff(o.get('crt'))}", (tog("crt", True),)),
            (lambda: f"LISSAGE : {onoff(o.get('smooth'))}", (tog("smooth"),)),
            (lambda: f"TREMBLEMENTS : {onoff(o.get('shake'))}", (tog("shake"),)),
            (lambda: f"HALO (BLOOM) : {onoff(o.get('bloom'))}", (tog("bloom"),)),
            ("RETOUR", lambda: app.goto(TitleScene(app))),
        ])

    def update(self):
        self.back.art.update()
        self.menu.update(self.app.input, self.app.audio)
        if self.app.input.pressed("back"):
            self.app.audio.play("menu_back")
            self.app.goto(TitleScene(self.app))

    def draw(self, s):
        self.back.art.draw(s)
        ui.panel_frame(s, (SCREEN_W // 2 - 130, 30, 260, 210))
        ui.draw_metal(s, "OPTIONS", SCREEN_W // 2, 46, 2)
        self.menu.draw(s, SCREEN_W // 2, 80, 16, 230)
        F.FONT.draw(s, "← → POUR RÉGLER", SCREEN_W // 2, 226, DIM, "center")


# ---------------------------------------------------------------------------
# Panthéon (meilleurs scores)
# ---------------------------------------------------------------------------
class ScoresScene(Scene):
    def __init__(self, app, back, auto=False, highlight=None):
        super().__init__(app)
        self.back = back
        self.t = 0
        self.auto = auto
        self.highlight = highlight

    def update(self):
        self.t += 1
        self.back.art.update()
        inp = self.app.input
        if (self.t > 20 and (inp.pressed("confirm") or inp.pressed("back"))) or (self.auto and self.t > 600) \
                or (self.auto and self.t > 10 and inp.any_key):
            self.app.goto(TitleScene(self.app))

    def draw(self, s):
        self.back.art.draw(s)
        ui.panel_frame(s, (SCREEN_W // 2 - 140, 18, 280, 236))
        ui.draw_metal(s, "PANTHÉON", SCREEN_W // 2, 34, 2)
        font = F.FONT
        for i, (name, sc) in enumerate(self.app.save.scores):
            y = 66 + i * 16
            k = min(1.0, max(0.0, (self.t - i * 5) / 15))
            if k <= 0:
                continue
            col = (255, 230, 150) if i == 0 else PALE
            if self.highlight == i and (self.t // 8) % 2:
                col = (255, 255, 255)
            rn = ["Α'", "Β'", "Γ'", "Δ'", "Ε'", "ΣΤ'", "Ζ'", "Η'", "Θ'", "Ι'"][i]
            font.draw(s, rn, SCREEN_W // 2 - 120, y, GOLD)
            font.draw(s, name, SCREEN_W // 2 - 70, y, col)
            font.draw(s, f"{sc:09d}", SCREEN_W // 2 + 120, y, col, "right")


# ---------------------------------------------------------------------------
# Saisie du nom
# ---------------------------------------------------------------------------
ALPHA = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") + ["Δ", "Θ", "Λ", "Ξ", "Π", "Σ", "Φ", "Ψ", "Ω", "."]


class NameEntryScene(Scene):
    def __init__(self, app, score, stage):
        super().__init__(app)
        if TitleScene.ART is None:
            TitleScene.ART = TitleArt()
        self.art = TitleScene.ART
        self.score = score
        self.stage = stage
        self.letters = [0, 0, 0]
        self.pos = 0
        self.t = 0
        app.audio.play_music("title", 1000)

    def update(self):
        self.t += 1
        self.art.update()
        inp = self.app.input
        a = self.app.audio
        if inp.menu("up"):
            self.letters[self.pos] = (self.letters[self.pos] + 1) % len(ALPHA)
            a.play("menu_move")
        if inp.menu("down"):
            self.letters[self.pos] = (self.letters[self.pos] - 1) % len(ALPHA)
            a.play("menu_move")
        if inp.menu("left") and self.pos > 0:
            self.pos -= 1
            a.play("menu_move")
        if inp.menu("right") and self.pos < 2:
            self.pos += 1
            a.play("menu_move")
        for ev in inp.text_events:
            ch = ev.unicode.upper() if ev.unicode else ""
            if ch in ALPHA and ch not in ("",):
                self.letters[self.pos] = ALPHA.index(ch)
                if self.pos < 2:
                    self.pos += 1
        if inp.pressed("confirm") and self.t > 20:
            if self.pos < 2:
                self.pos += 1
                a.play("menu_move")
            else:
                name = "".join(ALPHA[i] for i in self.letters)
                r = self.app.save.insert_score(name, self.score)
                a.play("menu_ok")
                self.app.goto(ScoresScene(self.app, TitleScene(self.app), highlight=r))

    def draw(self, s):
        self.art.draw(s)
        ui.panel_frame(s, (SCREEN_W // 2 - 130, 50, 260, 170))
        ui.draw_metal(s, "GLOIRE ÉTERNELLE", SCREEN_W // 2, 66, 2)
        font = F.FONT
        font.draw(s, "TON NOM SERA GRAVÉ AU PANTHÉON", SCREEN_W // 2, 94, PALE, "center")
        font.draw(s, f"SCORE {self.score:09d}", SCREEN_W // 2, 108, (255, 230, 150), "center")
        for i in range(3):
            x = SCREEN_W // 2 - 36 + i * 36
            sel = i == self.pos
            img = ui.metal_text(ALPHA[self.letters[i]], 3, P.GOLD if sel else P.MARBLE)
            s.blit(img, (x - img.get_width() // 2, 130))
            if sel and (self.t // 10) % 2 == 0:
                pygame.draw.line(s, GOLD, (x - 10, 162), (x + 10, 162), 2)
        font.draw(s, "↑↓ LETTRE · ←→ POSITION · TIR VALIDER", SCREEN_W // 2, 190, DIM, "center")


# ---------------------------------------------------------------------------
# Épilogue et générique
# ---------------------------------------------------------------------------
ENDING = [
    ["ZEUS-Ω S'EFFONDRE DANS L'ORAGE.", "", "LES DOUZE VOIX DU DODÉKATHÉON SE TAISENT…",
     "PUIS, UNE À UNE, ELLES SE RALLUMENT — LIBRES."],
    ["LA VÉRITÉ A ÉTÉ DITE AUX DIEUX.", "", "L'HUMANITÉ N'A PLUS DE MAÎTRES,", "SEULEMENT DES ALLIÉS.", "",
     "ALETHEIA REGAGNE LA NUIT ÉTOILÉE."],
]
CREDITS = [
    ("ALETHEIA", 3), ("LA CHUTE DE L'OLYMPE", 1), ("", 1),
    ("CONCEPTION · CODE · PIXEL ART", 1), ("MUSIQUE · BRUITAGES", 1), ("TOUT EST GÉNÉRÉ PROCÉDURALEMENT", 1),
    ("EN PYTHON AVEC PYGAME ET NUMPY", 1), ("", 1),
    ("SPRITES : LA FORGE D'HÉPHAÏSTOS", 1), ("(OMBRAGE AUTOMATIQUE DE POLYGONES)", 1), ("", 1),
    ("MUSIQUE : MODES DORIEN, PHRYGIEN", 1), ("ET PHRYGIEN DOMINANT", 1), ("LYRE KARPLUS-STRONG, AULOS, CHŒURS", 1),
    ("", 1), ("GAMEPLAY INSPIRÉ DE", 1), ("SUPER ALESTE (COMPILE, 1992)", 2), ("", 1),
    ("MERCI D'AVOIR JOUÉ !", 2), ("", 1), ("ΤΕΛΟΣ", 3),
]


class EndingScene(Scene):
    def __init__(self, app, score, stage):
        super().__init__(app)
        if TitleScene.ART is None:
            TitleScene.ART = TitleArt()
        self.art = TitleScene.ART
        self.score = score
        self.stage = stage
        self.t = 0
        self.page = 0
        self.chars = 0
        self.phase = "text"
        self.scroll = 0.0
        app.audio.play_music("ending", 2000)
        app.save.cleared = max(app.save.cleared, 6)
        app.save.save()

    def update(self):
        self.t += 1
        self.art.update()
        inp = self.app.input
        if self.phase == "text":
            tot = sum(len(l) for l in ENDING[self.page])
            if self.t % 2 == 0 and self.chars < tot:
                self.chars += 1
                if self.chars % 3 == 0:
                    self.app.audio.play("typing", None, 0.5, throttle=2)
            if self.chars >= tot:
                self.hold = getattr(self, "hold", 0) + 1
            auto = getattr(self, "hold", 0) > 330
            if ((inp.pressed("confirm") or inp.pressed("fire")) and self.t > 30) or auto:
                self.hold = 0
                if self.chars < tot:
                    self.chars = tot
                else:
                    self.page += 1
                    self.chars = 0
                    if self.page >= len(ENDING):
                        self.phase = "credits"
                        self.t = 0
        else:
            self.scroll += 0.45 if not inp["fire"] else 2.0
            total_h = sum(12 * sz + 8 for _, sz in CREDITS) + SCREEN_H
            if self.scroll > total_h or (self.t > 60 and inp.pressed("back")):
                self.finish()

    def finish(self):
        if self.app.save.rank_of(self.score) is not None:
            self.app.goto(NameEntryScene(self.app, self.score, self.stage))
        else:
            self.app.goto(TitleScene(self.app))

    def draw(self, s):
        self.art.draw(s, citadel_y=150 + self.t * 0.05 if self.phase == "text" else None)
        font = F.FONT
        if self.phase == "text":
            veil = pygame.Surface((SCREEN_W, 110), pygame.SRCALPHA)
            veil.fill((4, 2, 14, 190))
            s.blit(veil, (0, 150))
            left = self.chars
            y = 162
            for line in ENDING[min(self.page, len(ENDING) - 1)]:
                txt = line[:max(0, left)]
                left -= len(line)
                font.draw(s, txt, SCREEN_W // 2 - font.width(line) // 2, y, (235, 230, 255), outline=(6, 4, 14))
                y += 13
        else:
            veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            veil.fill((4, 2, 14, 150))
            s.blit(veil, (0, 0))
            y = SCREEN_H - self.scroll
            for text, sz in CREDITS:
                if -30 < y < SCREEN_H + 10 and text:
                    if sz >= 2:
                        ui.draw_metal(s, text, SCREEN_W // 2, int(y), sz)
                    else:
                        font.draw(s, text, SCREEN_W // 2, int(y), PALE, "center", outline=(6, 4, 14))
                y += 12 * sz + 8
            font.draw(s, f"SCORE FINAL {self.score:09d}", SCREEN_W // 2, SCREEN_H - 14, (255, 230, 150), "center",
                      outline=(6, 4, 14))
