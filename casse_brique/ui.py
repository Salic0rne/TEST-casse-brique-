"""Éléments d'interface : menus néon navigables au clavier, à la souris et à la manette."""

import math

import pygame

from .surf import blend_fill
from .util import clamp, ease_out_cubic, lighten, scale


class MenuItem:
    def __init__(self, label, action=None, adjust=None, value=None):
        self.label = label      # texte fixe
        self.action = action    # appelé sur « valider »
        self.adjust = adjust    # appelé avec -1 / +1 (gauche / droite)
        self.value = value      # fonction retournant le texte de la valeur


class Menu:
    def __init__(self, app, items, cx, top, spacing=54, size=24, accent=(255, 60, 200),
                 on_back=None, width=460):
        self.app = app
        self.items = items
        self.cx, self.top = cx, top
        self.spacing, self.size = spacing, size
        self.accent = accent
        self.on_back = on_back
        self.width = width
        self.sel = 0
        self.anim = [0.0] * len(items)
        self.rects = []
        self.t = 0.0
        self.enabled = True

    # ------------------------------------------------------------------ entrées
    def move(self, d):
        self.sel = (self.sel + d) % len(self.items)
        self.app.audio.play("move")

    def activate(self):
        item = self.items[self.sel]
        if item.action:
            self.app.audio.play("select")
            item.action()
        elif item.adjust:
            item.adjust(1)
            self.app.audio.play("move")

    def on_action(self, action):
        if not self.enabled:
            return
        if action == "up":
            self.move(-1)
        elif action == "down":
            self.move(1)
        elif action in ("left", "right"):
            item = self.items[self.sel]
            if item.adjust:
                item.adjust(-1 if action == "left" else 1)
                self.app.audio.play("move")
        elif action == "confirm":
            self.activate()
        elif action in ("back", "pause") and self.on_back:
            self.app.audio.play("back")
            self.on_back()

    def on_event(self, e):
        if not self.enabled:
            return
        if e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(e.pos) and i != self.sel:
                    self.sel = i
                    self.app.audio.play("move")
        elif e.type == pygame.MOUSEBUTTONDOWN:
            for i, r in enumerate(self.rects):
                if r.collidepoint(e.pos):
                    self.sel = i
                    item = self.items[i]
                    if e.button == 1:
                        if item.adjust and not item.action:
                            d = -1 if e.pos[0] < r.centerx else 1
                            item.adjust(d)
                            self.app.audio.play("move")
                        else:
                            self.activate()
                    elif e.button == 3 and item.adjust:
                        item.adjust(-1)
                        self.app.audio.play("move")
        elif e.type == pygame.MOUSEWHEEL:
            self.move(-1 if e.y > 0 else 1)

    # ------------------------------------------------------------------ rendu
    def update(self, dt):
        self.t += dt
        for i in range(len(self.anim)):
            target = 1.0 if i == self.sel else 0.0
            self.anim[i] += (target - self.anim[i]) * (1.0 - math.exp(-dt * 14.0))

    def draw(self, canvas, glow, alpha=255):
        font = self.app.font
        self.rects = []
        acc = self.accent
        for i, item in enumerate(self.items):
            y = self.top + i * self.spacing
            k = self.anim[i]
            sel = i == self.sel
            text = item.label
            v = item.value() if item.value else ""
            if v:
                text = "%s   %s" % (item.label, ("< %s >" % v) if sel else v)
            self.rects.append(pygame.Rect(self.cx - self.width // 2, y - self.spacing // 2,
                                          self.width, self.spacing))
            if k > 0.02:
                w = self.width * ease_out_cubic(k)
                x0 = self.cx - w / 2
                band = pygame.Rect(int(x0), int(y - self.size * 0.95), int(w), int(self.size * 1.9))
                blend_fill(canvas, scale(acc, 0.11 * k), band, pygame.BLEND_RGB_ADD)
                pygame.draw.line(canvas, scale(acc, k), band.topleft, band.topright, 1)
                pygame.draw.line(canvas, scale(acc, k), band.bottomleft, band.bottomright, 1)
                glow.rect(band.x, band.y, band.w, band.h, scale(acc, 0.22 * k))
            if sel:
                nt = font.render(text, self.size, lighten(acc, 0.5), core=(255, 255, 255), glow=0.9)
                off = 16 + 5 * math.sin(self.t * 7.0)
                chev = font.render(">", self.size * 0.8, acc, glow=1.0)
                chev.draw(canvas, self.cx - nt.w / 2 - off - 14, y, "center", alpha)
                chev2 = font.render("<", self.size * 0.8, acc, glow=1.0)
                chev2.draw(canvas, self.cx + nt.w / 2 + off + 14, y, "center", alpha)
            else:
                nt = font.render(text, self.size, (150, 150, 200), core=(205, 205, 235), glow=0.35)
            nt.draw(canvas, self.cx, y, "center", alpha)


_BARS = {}


def _bar_surface(w, h, c1, c2):
    key = (w, h, c1, c2)
    surf = _BARS.get(key)
    if surf is None:
        if len(_BARS) > 200:
            _BARS.clear()
        surf = pygame.Surface((w, h)).convert()
        for i in range(w):
            t = i / max(1, w - 1)
            col = (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t),
                   int(c1[2] + (c2[2] - c1[2]) * t))
            pygame.draw.line(surf, col, (i, 0), (i, h - 1))
        pygame.draw.line(surf, (255, 255, 255), (1, 0), (w - 2, 0))
        _BARS[key] = surf
    return surf


def draw_bar(canvas, glow, x, y, w, h, frac, c1, c2, back=(30, 20, 50)):
    """Jauge néon horizontale (dégradé pré-calculé)."""
    frac = clamp(frac, 0.0, 1.0)
    pygame.draw.rect(canvas, back, (x, y, w, h), border_radius=h // 2)
    fw = int(w * frac)
    if fw > 0:
        canvas.blit(_bar_surface(w, max(1, h - 2), c1, c2), (x, y + 1), (0, 0, fw, max(1, h - 2)))
        glow.rect(x, y, fw, h, scale(c2, 0.45))
    pygame.draw.rect(canvas, lighten(back, 0.35), (x, y, w, h), 1, border_radius=h // 2)


def card(canvas, glow, rect, accent, dim=(52, 46, 72)):
    """Carte de verre sombre avec liseré néon (lisibilité du HUD sur le décor)."""
    rect = pygame.Rect(rect)
    blend_fill(canvas, dim, rect)
    glow.dim(rect, (80, 80, 80))
    pygame.draw.rect(canvas, scale(accent, 0.3), rect, 1)
    corner_brackets(canvas, rect, scale(accent, 0.95), 9, 2)


def corner_brackets(canvas, rect, color, size=10, width=2):
    x, y, w, h = rect
    for cx, cy, dx, dy in ((x, y, 1, 1), (x + w, y, -1, 1), (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        pygame.draw.line(canvas, color, (cx, cy), (cx + dx * size, cy), width)
        pygame.draw.line(canvas, color, (cx, cy), (cx, cy + dy * size), width)
