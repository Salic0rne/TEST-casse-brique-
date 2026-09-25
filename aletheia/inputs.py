"""Entrées clavier + manette unifiées en actions.

Les lettres sont lues par *position physique* (scancodes USB/SDL) : la même disposition
fonctionne en QWERTY (WASD + Z X C V) comme en AZERTY (ZQSD + W X C V) ou QWERTZ.
Les libellés affichés s'adaptent à la disposition détectée.
"""
import locale

import pygame

# Scancodes SDL (positions physiques, disposition QWERTY de référence)
SC = {"A": 4, "B": 5, "C": 6, "D": 7, "I": 12, "J": 13, "K": 14, "L": 15, "P": 19, "S": 22, "U": 24,
      "V": 25, "W": 26, "X": 27, "Z": 29}

# action -> (scancodes physiques, keycodes indépendants de la disposition)
BINDINGS = {
    "up": ((SC["W"],), (pygame.K_UP,)),
    "down": ((SC["S"],), (pygame.K_DOWN,)),
    "left": ((SC["A"],), (pygame.K_LEFT,)),
    "right": ((SC["D"],), (pygame.K_RIGHT,)),
    "fire": ((SC["Z"], SC["J"]), (pygame.K_SPACE,)),
    "mode": ((SC["X"], SC["K"]), ()),
    "bomb": ((SC["C"], SC["L"]), ()),
    "speed": ((SC["V"], SC["I"]), (pygame.K_LSHIFT, pygame.K_RSHIFT)),
    "speed_down": ((SC["B"], SC["U"]), (pygame.K_LCTRL, pygame.K_RCTRL)),
    "pause": ((SC["P"],), (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER)),
    "confirm": ((SC["Z"], SC["J"]), (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)),
    "back": ((SC["X"], SC["K"]), (pygame.K_ESCAPE, pygame.K_BACKSPACE)),
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

ACTIONS = tuple(BINDINGS.keys())

# libellés des touches physiques selon la disposition
LAYOUT_LABELS = {
    "qwerty": {"fire": "Z", "mode": "X", "bomb": "C", "speed": "V", "move": "WASD"},
    "azerty": {"fire": "W", "mode": "X", "bomb": "C", "speed": "V", "move": "ZQSD"},
    "qwertz": {"fire": "Y", "mode": "X", "bomb": "C", "speed": "V", "move": "WASD"},
}


def guess_layout():
    try:
        loc = (locale.getlocale()[0] or locale.getdefaultlocale()[0] or "").lower()
    except (ValueError, TypeError):
        loc = ""
    if loc.startswith(("fr_fr", "fr_be", "french_france", "french_belgium")):
        return "azerty"
    if loc.startswith(("de_", "german", "cs_", "sk_", "hu_", "pl_")):
        return "qwertz"
    return "qwerty"


class Input:
    def __init__(self):
        self.held = {a: False for a in ACTIONS}
        self.prev = dict(self.held)
        self.pressed_set = set()
        self.repeat = {}
        self.pads = []
        self.bot = None          # pilote automatique (démo, tests)
        self.any_key = False
        self.text_events = []
        self.scan_down = set()
        self.layout = guess_layout()
        self._init_pads()

    @property
    def labels(self):
        return LAYOUT_LABELS[self.layout]

    def _init_pads(self):
        try:
            pygame.joystick.init()
            self.pads = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            for p in self.pads:
                p.init()
        except pygame.error:
            self.pads = []

    def event(self, ev):
        t = ev.type
        if t in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
            self._init_pads()
        if t in (pygame.KEYDOWN, pygame.JOYBUTTONDOWN):
            self.any_key = True
        if t == pygame.KEYDOWN:
            self.text_events.append(ev)
            sc = getattr(ev, "scancode", None)
            if sc is not None:
                self.scan_down.add(sc)
                # détection de la disposition : quelle lettre produit la touche « Z » physique ?
                if sc == SC["Z"]:
                    if ev.key == pygame.K_w:
                        self.layout = "azerty"
                    elif ev.key == pygame.K_y:
                        self.layout = "qwertz"
                    elif ev.key == pygame.K_z:
                        self.layout = "qwerty"
        elif t == pygame.KEYUP:
            sc = getattr(ev, "scancode", None)
            if sc is not None:
                self.scan_down.discard(sc)
        elif t in (getattr(pygame, "WINDOWFOCUSLOST", -1), getattr(pygame, "WINDOWMINIMIZED", -1)):
            self.scan_down.clear()

    def update(self):
        keys = pygame.key.get_pressed()
        now = {}
        sd = self.scan_down
        for a, (scans, codes) in BINDINGS.items():
            v = any(s in sd for s in scans)
            if not v:
                for k in codes:
                    if keys[k]:
                        v = True
                        break
            now[a] = v
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
                    # gâchette droite analogique = tir
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
