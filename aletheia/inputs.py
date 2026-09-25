"""Entrées clavier + manette unifiées en actions."""
import pygame

KEYMAP = {
    "up": (pygame.K_UP, pygame.K_w),
    "down": (pygame.K_DOWN, pygame.K_s),
    "left": (pygame.K_LEFT, pygame.K_a),
    "right": (pygame.K_RIGHT, pygame.K_d),
    "fire": (pygame.K_z, pygame.K_j, pygame.K_SPACE),
    "mode": (pygame.K_x, pygame.K_k),
    "bomb": (pygame.K_c, pygame.K_l),
    "speed": (pygame.K_v, pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_i),
    "speed_down": (pygame.K_b, pygame.K_LCTRL, pygame.K_u),
    "pause": (pygame.K_ESCAPE, pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER),
    "confirm": (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_z, pygame.K_j, pygame.K_SPACE),
    "back": (pygame.K_ESCAPE, pygame.K_x, pygame.K_k, pygame.K_BACKSPACE),
}

# Manette type Xbox (SDL) : A=0 B=1 X=2 Y=3 LB=4 RB=5 Back=6 Start=7
PADMAP = {
    "fire": (0,),
    "bomb": (1,),
    "mode": (2,),
    "speed": (3, 5),
    "speed_down": (4,),
    "pause": (7,),
    "confirm": (0, 7),
    "back": (1, 6),
}

ACTIONS = tuple(KEYMAP.keys())


class Input:
    def __init__(self):
        self.held = {a: False for a in ACTIONS}
        self.prev = dict(self.held)
        self.pressed_set = set()
        self.repeat = {}
        self.pads = []
        self.bot = None          # pilote automatique (tests)
        self.any_key = False
        self.text_events = []
        self._init_pads()

    def _init_pads(self):
        try:
            pygame.joystick.init()
            self.pads = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            for p in self.pads:
                p.init()
        except pygame.error:
            self.pads = []

    def event(self, ev):
        if ev.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self._init_pads()
        if ev.type in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN):
            self.any_key = True
        if ev.type == pygame.KEYDOWN:
            self.text_events.append(ev)

    def update(self):
        keys = pygame.key.get_pressed()
        now = {}
        for a, ks in KEYMAP.items():
            now[a] = any(keys[k] for k in ks)
        for p in self.pads:
            try:
                nb = p.get_numbuttons()
                for a, bs in PADMAP.items():
                    if any(b < nb and p.get_button(b) for b in bs):
                        now[a] = True
                if p.get_numaxes() >= 2:
                    ax, ay = p.get_axis(0), p.get_axis(1)
                    if ax < -0.45:
                        now["left"] = True
                    if ax > 0.45:
                        now["right"] = True
                    if ay < -0.45:
                        now["up"] = True
                    if ay > 0.45:
                        now["down"] = True
                if p.get_numhats() > 0:
                    hx, hy = p.get_hat(0)
                    if hx < 0:
                        now["left"] = True
                    if hx > 0:
                        now["right"] = True
                    if hy > 0:
                        now["up"] = True
                    if hy < 0:
                        now["down"] = True
                if p.get_numaxes() >= 6:
                    # gâchettes analogiques : RT = tir
                    if p.get_axis(5) > 0.5:
                        now["fire"] = True
            except pygame.error:
                pass
        if self.bot is not None:
            for a, v in self.bot.actions().items():
                now[a] = now.get(a, False) or v
        self.prev = self.held
        self.held = now
        self.pressed_set = {a for a in ACTIONS if now[a] and not self.prev.get(a)}
        # répétition pour les menus
        for a in ("up", "down", "left", "right"):
            if now[a]:
                self.repeat[a] = self.repeat.get(a, 0) + 1
            else:
                self.repeat[a] = 0

    def end_frame(self):
        self.any_key = False
        self.text_events.clear()

    def pressed(self, a):
        return a in self.pressed_set

    def menu(self, a):
        """Appui avec répétition automatique (navigation des menus)."""
        r = self.repeat.get(a, 0)
        return r == 1 or (r > 18 and (r - 18) % 5 == 0)

    def __getitem__(self, a):
        return self.held.get(a, False)
