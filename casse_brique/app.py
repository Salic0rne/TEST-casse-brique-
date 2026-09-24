"""Application : fenêtre, boucle principale, entrées, transitions et post-traitement."""

import os
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# mise à l'échelle lissée de la fenêtre (pygame.SCALED)
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")

import pygame  # noqa: E402

from .config import FPS, HEIGHT, TITLE, WIDTH  # noqa: E402

KEY_ACTIONS = {
    pygame.K_UP: "up", pygame.K_w: "up", pygame.K_z: "up",
    pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_LEFT: "left", pygame.K_q: "left", pygame.K_a: "left",
    pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_RETURN: "confirm", pygame.K_KP_ENTER: "confirm", pygame.K_SPACE: "confirm",
    pygame.K_ESCAPE: "back", pygame.K_BACKSPACE: "back",
    pygame.K_p: "pause",
}


def _make_icon():
    s = pygame.Surface((32, 32), pygame.SRCALPHA)
    for i, col in enumerate(((255, 60, 200), (255, 150, 40), (0, 230, 255))):
        pygame.draw.rect(s, col, (2, 3 + i * 7, 28, 5), border_radius=2)
    pygame.draw.circle(s, (255, 255, 255), (16, 26), 4)
    return s


class App:
    def __init__(self, headless=False):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 2, 512)
        except pygame.error:
            pass
        from .settings import Settings
        self.settings = Settings.load()
        self.headless = headless
        pygame.display.set_caption("%s — casse-brique néon" % TITLE)
        pygame.display.set_icon(_make_icon())
        self.screen = self._open_window(self.settings.fullscreen)
        pygame.mouse.set_visible(False)
        self.canvas = pygame.Surface((WIDTH, HEIGHT)).convert()
        self.clock = pygame.time.Clock()
        self.time = 0.0
        self.running = True
        self.show_fps = False
        self.joy_axis = 0.0
        self.joy_fire = False
        self._joy_nav = 0
        self.joysticks = {}
        self.mouse_idle = 99.0
        self.transition = None

        from .vfont import VectorFont
        self.font = VectorFont()
        self._loading_screen()

        from .audio import Audio
        from .background import Background
        from .particles import Particles
        from .post import GlowBuffer, Post, ScreenFX
        from .sprites import Art
        self.glow = GlowBuffer((WIDTH, HEIGHT))
        self.post = Post((WIDTH, HEIGHT))
        self.fx = ScreenFX()
        self.art = Art(self.font)
        self.bg = Background()
        self.particles = Particles(self.art, self.font)
        self.audio = Audio(self.settings.sfx_volume, self.settings.music_volume)

        from .scenes import TitleScene
        self.scene = TitleScene(self)

    # ------------------------------------------------------------------ fenêtre
    def _open_window(self, fullscreen):
        flags = pygame.SCALED
        if fullscreen:
            flags |= pygame.FULLSCREEN
        else:
            flags |= pygame.RESIZABLE
        try:
            return pygame.display.set_mode((WIDTH, HEIGHT), flags)
        except pygame.error:
            return pygame.display.set_mode((WIDTH, HEIGHT))

    def toggle_fullscreen(self):
        self.settings.fullscreen = not self.settings.fullscreen
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            self.screen = self._open_window(self.settings.fullscreen)
        self.settings.save()

    def _loading_screen(self):
        self.canvas.fill((6, 0, 18))
        nt = self.font.render("CHARGEMENT", 28, (255, 60, 200), core=(255, 255, 255), spacing=3.0)
        nt.draw(self.canvas, WIDTH // 2, HEIGHT // 2)
        self.font.render("SYNTHÈSE DES SONS ET DES TEXTURES", 12, (0, 230, 255), glow=0.5).draw(
            self.canvas, WIDTH // 2, HEIGHT // 2 + 44)
        self.screen.blit(self.canvas, (0, 0))
        pygame.display.flip()
        pygame.event.pump()

    def apply_volumes(self):
        self.audio.sfx_volume = self.settings.sfx_volume
        self.audio.music_volume = self.settings.music_volume

    # ------------------------------------------------------------------ scènes
    def goto(self, factory):
        if self.transition is None:
            self.transition = {"t": 0.0, "factory": factory, "done": False}
            self.audio.play("whoosh")

    def quit(self):
        self.settings.save()
        self.running = False

    # ------------------------------------------------------------------ entrées
    def _dispatch_action(self, action):
        if self.transition is None:
            self.scene.on_action(action)

    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.quit()
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_F11 or (e.key == pygame.K_RETURN and e.mod & pygame.KMOD_ALT):
                self.toggle_fullscreen()
                return
            if e.key == pygame.K_m:
                if self.settings.music_volume > 0:
                    self._music_backup = self.settings.music_volume
                    self.settings.music_volume = 0.0
                else:
                    self.settings.music_volume = getattr(self, "_music_backup", 0.6) or 0.6
                self.apply_volumes()
                self.settings.save()
                return
            if e.key == pygame.K_F3:
                self.show_fps = not self.show_fps
                return
            if e.key == pygame.K_F12:
                path = os.path.join(os.path.expanduser("~"), "prisma_%d.png" % int(time.time()))
                pygame.image.save(self.canvas, path)
                return
            action = KEY_ACTIONS.get(e.key)
            if action:
                self._dispatch_action(action)
        elif e.type == pygame.JOYDEVICEADDED:
            try:
                j = pygame.joystick.Joystick(e.device_index)
                self.joysticks[j.get_instance_id()] = j
            except pygame.error:
                pass
        elif e.type == pygame.JOYDEVICEREMOVED:
            self.joysticks.pop(e.instance_id, None)
        elif e.type == pygame.JOYAXISMOTION:
            if e.axis == 0:
                self.joy_axis = e.value if abs(e.value) > 0.2 else 0.0
            elif e.axis == 1:
                nav = -1 if e.value < -0.6 else 1 if e.value > 0.6 else 0
                if nav != self._joy_nav and nav != 0:
                    self._dispatch_action("up" if nav < 0 else "down")
                self._joy_nav = nav
        elif e.type == pygame.JOYHATMOTION:
            x, y = e.value
            if y:
                self._dispatch_action("up" if y > 0 else "down")
            elif x:
                self._dispatch_action("left" if x < 0 else "right")
            self.joy_axis = float(x) if x else 0.0
        elif e.type == pygame.JOYBUTTONDOWN:
            if e.button in (0, 2):
                self.joy_fire = True
                self._dispatch_action("confirm")
            elif e.button == 1:
                self._dispatch_action("back")
            elif e.button in (6, 7, 9):
                self._dispatch_action("pause")
        elif e.type == pygame.JOYBUTTONUP:
            if e.button in (0, 2):
                self.joy_fire = False
        if e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            self.mouse_idle = 0.0
        if self.transition is None and e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN,
                                                  pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL,
                                                  pygame.WINDOWFOCUSLOST):
            self.scene.on_event(e)

    # ------------------------------------------------------------------ boucle
    def step(self, dt, events=None):
        """Une image : entrées, mise à jour, rendu. `events` permet de piloter le jeu en test."""
        dt = min(dt, 1.0 / 20.0)
        self.time += dt
        self.mouse_idle += dt
        for e in (pygame.event.get() if events is None else events):
            self.handle_event(e)
        self.audio.update(dt)
        scale_t = self.fx.update(dt)
        self.bg.update(dt)
        self.scene.update(dt, scale_t)
        if self.transition:
            tr = self.transition
            tr["t"] += dt
            if tr["t"] >= 0.3 and not tr["done"]:
                tr["done"] = True
                self.scene = tr["factory"]()
            if tr["t"] >= 0.6:
                self.transition = None
        self.render()

    def render(self):
        canvas = self.canvas
        glow = self.glow
        glow.clear()
        glow.ox = glow.oy = 0.0
        self.scene.draw(canvas, glow)
        glow.composite(canvas)
        fx = self.fx
        if fx.chroma > 0.5:
            self.post.chromatic(canvas, fx.chroma)
        if fx.glitch > 0.02:
            self.post.glitch(canvas, fx.glitch)
        self.post.flash(canvas, fx.flash_color, fx.flash_k)
        if self.transition:
            t = self.transition["t"]
            k = t / 0.3 if t < 0.3 else 1.0 - (t - 0.3) / 0.3
            k = max(0.0, min(1.0, k))
            v = int(255 * (1.0 - k))
            canvas.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
            self.post.glitch(canvas, k * 0.6)
        self.post.crt_pass(canvas, self.settings.crt)
        if getattr(self.scene, "show_cursor", False) or getattr(self.scene, "paused", False) or \
                getattr(self.scene, "state", "") == "gameover":
            if self.mouse_idle < 3.0:
                self._draw_cursor(canvas)
        if self.show_fps:
            self.font.draw_chars(canvas, "%d FPS" % round(self.clock.get_fps()), 12, (120, 255, 120),
                                 WIDTH - 12, HEIGHT - 16, anchor="midright")
        self.screen.blit(canvas, (0, 0))
        pygame.display.flip()

    def _draw_cursor(self, canvas):
        x, y = pygame.mouse.get_pos()
        col = (255, 90, 220)
        pygame.draw.polygon(canvas, (40, 0, 40), [(x + 1, y + 1), (x + 15, y + 9), (x + 8, y + 10), (x + 5, y + 17)])
        pygame.draw.polygon(canvas, col, [(x, y), (x + 14, y + 8), (x + 7, y + 9), (x + 4, y + 16)])
        pygame.draw.polygon(canvas, (255, 255, 255), [(x, y), (x + 14, y + 8), (x + 7, y + 9), (x + 4, y + 16)], 1)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)
        self.settings.save()
        pygame.quit()


def main():
    try:
        App().run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
