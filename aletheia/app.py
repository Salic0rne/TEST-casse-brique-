"""Application : fenêtre (mise à l'échelle entière, plein écran, filtre CRT), boucle principale,
chargement procédural, transitions entre scènes."""
import math
import os
import sys
import time

import pygame

from . import config as C
from .config import SCREEN_W, SCREEN_H, FPS, PF_W, PF_H, Save
from . import font as F


class Display:
    def __init__(self, save, headless=False):
        self.save = save
        self.headless = headless
        self.window = None
        self.scaled = None
        self.scan = None
        self.k = 1
        self.apply()

    def auto_scale(self):
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, AttributeError, IndexError):
            dw, dh = 1920, 1080
        return max(1, min((dw - 60) // SCREEN_W, (dh - 110) // SCREEN_H))

    def apply(self):
        o = self.save.options
        if self.headless:
            self.window = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        elif o.get("fullscreen"):
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            s = o.get("scale") or self.auto_scale()
            self.window = pygame.display.set_mode((SCREEN_W * s, SCREEN_H * s), pygame.RESIZABLE)
        pygame.display.set_caption("ALETHEIA — La Chute de l'Olympe")
        self.relayout()

    def relayout(self):
        W, H = self.window.get_size()
        k = max(1, min(W // SCREEN_W, H // SCREEN_H))
        self.k = k
        self.dw, self.dh = SCREEN_W * k, SCREEN_H * k
        self.dx, self.dy = (W - self.dw) // 2, (H - self.dh) // 2
        self.scaled = pygame.Surface((self.dw, self.dh)).convert() if k > 1 else None
        self.scan = self.make_scanlines(k) if (self.save.options.get("crt") and k >= 2) else None
        self.window.fill((0, 0, 0))

    def make_scanlines(self, k):
        s = pygame.Surface((self.dw, self.dh)).convert()
        s.fill((255, 255, 255))
        dark = {2: 200, 3: 170}.get(k, 150)
        for y in range(k - 1, self.dh, k):
            s.fill((dark, dark, dark), (0, y, self.dw, 1))
        if k >= 3:
            tints = ((255, 238, 238), (238, 255, 238), (238, 238, 255))
            tint = pygame.Surface((self.dw, self.dh)).convert()
            for x in range(self.dw):
                tint.fill(tints[x % 3], (x, 0, 1, self.dh))
            s.blit(tint, (0, 0), special_flags=pygame.BLEND_MULT)
        return s

    def toggle_fullscreen(self):
        self.save.options["fullscreen"] = not self.save.options.get("fullscreen")
        self.save.save()
        self.apply()

    def present(self, frame):
        if self.k == 1:
            self.window.blit(frame, (self.dx, self.dy))
        else:
            if self.save.options.get("smooth"):
                pygame.transform.smoothscale(frame, (self.dw, self.dh), self.scaled)
            else:
                pygame.transform.scale(frame, (self.dw, self.dh), self.scaled)
            if self.scan is not None:
                self.scaled.blit(self.scan, (0, 0), special_flags=pygame.BLEND_MULT)
            self.window.blit(self.scaled, (self.dx, self.dy))
        pygame.display.flip()


class Scene:
    def __init__(self, app):
        self.app = app

    def update(self):
        pass

    def draw(self, screen):
        pass


class App:
    def __init__(self, args):
        self.args = args
        headless = bool(os.environ.get("SDL_VIDEODRIVER") == "dummy")
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        mute = getattr(args, "mute", False)
        if not mute:
            try:
                pygame.mixer.pre_init(44100, -16, 2, 512)
            except pygame.error:
                pass
        pygame.init()
        if not mute and pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(44100, -16, 2, 512)
            except pygame.error:
                mute = True
        self.save = Save()
        self.display = Display(self.save, headless)
        self.screen = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
        self.clock = pygame.time.Clock()
        from .inputs import Input
        from .audio.manager import Audio
        from .post import Post
        self.input = Input()
        self.audio = Audio(self.save, enabled=not mute)
        F.init()
        self.post = Post(PF_W, PF_H)
        self.running = True
        self.frame_n = 0
        self.fade = 0.0
        self.fade_dir = 0
        self.next_scene = None
        self.show_fps = bool(getattr(args, "fps", False))
        self.hud = None
        from .scenes import LoadingScene
        self.scene = LoadingScene(self)

    # --- transitions ------------------------------------------------------------
    def goto(self, scene, fade=True):
        if fade:
            self.next_scene = scene
            self.fade_dir = 1
        else:
            self.scene = scene
            self.next_scene = None

    def pump(self):
        for ev in pygame.event.get():
            self.handle_event(ev)

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F11 or (ev.key == pygame.K_RETURN and (ev.mod & pygame.KMOD_ALT)):
                self.display.toggle_fullscreen()
                return
            if ev.key == pygame.K_F2:
                self.save.options["crt"] = not self.save.options.get("crt")
                self.save.save()
                self.display.relayout()
                return
            if ev.key == pygame.K_F3:
                self.show_fps = not self.show_fps
                return
        elif ev.type == pygame.VIDEORESIZE:
            if not self.save.options.get("fullscreen"):
                self.display.relayout()
        self.input.event(ev)

    def run(self):
        max_frames = getattr(self.args, "frames", 0) or 0
        while self.running:
            self.pump()
            self.input.update()
            self.scene.update()
            self.scene.draw(self.screen)
            self.draw_fade()
            if self.show_fps:
                F.FONT.draw(self.screen, f"{self.clock.get_fps():4.1f}", SCREEN_W - 4, 2, (120, 255, 120), "right",
                            outline=(0, 0, 0))
            self.display.present(self.screen)
            self.audio.update()
            self.input.end_frame()
            self.frame_n += 1
            if getattr(self.args, "shots", None):
                self.maybe_screenshot()
            if max_frames and self.frame_n >= max_frames:
                self.running = False
            if not getattr(self.args, "turbo", False):
                self.clock.tick(FPS)
            else:
                self.clock.tick()
        self.save.save()
        pygame.quit()

    def draw_fade(self):
        if self.fade_dir == 1:
            self.fade = min(1.0, self.fade + 1 / 14)
            if self.fade >= 1.0:
                if self.next_scene is not None:
                    self.scene = self.next_scene
                    self.next_scene = None
                self.fade_dir = -1
        elif self.fade_dir == -1:
            self.fade = max(0.0, self.fade - 1 / 14)
            if self.fade <= 0:
                self.fade_dir = 0
        if self.fade > 0:
            k = int(255 * (1 - self.fade))
            self.screen.fill((k, k, k), special_flags=pygame.BLEND_MULT)

    def maybe_screenshot(self):
        every = getattr(self.args, "shot_every", 300) or 300
        if self.frame_n % every == 0:
            d = self.args.shots
            os.makedirs(d, exist_ok=True)
            pygame.image.save(self.screen, os.path.join(d, f"f{self.frame_n:06d}.png"))

    def quit(self):
        self.running = False
