"""Fabrique de sprites (briques, raquette, balle, capsules), générés et mis en cache."""

import math
import random

import pygame

from . import surf as S
from .config import BALL_R, BRICK_H, BRICK_W, PADDLE_H
from .util import darken, hsv, lighten, mix

# Types de briques
NORMAL, HARD, ARMOR, METAL, BOMB, PRISM = range(6)

# Bonus : lettre, couleur, nom affiché, description
POWERUPS = {
    "G": ((70, 255, 130), "GRANDE RAQUETTE", "Raquette élargie"),
    "M": ((0, 225, 255), "MULTI-BALLE", "Chaque balle se divise en trois"),
    "L": ((255, 50, 80), "LASER", "Tir laser : ESPACE ou clic"),
    "R": ((80, 130, 255), "RALENTI", "Balles ralenties"),
    "F": ((255, 140, 20), "BOULE DE FEU", "Traverse les briques"),
    "A": ((190, 80, 255), "AIMANT", "La balle colle à la raquette"),
    "B": ((110, 255, 230), "BOUCLIER", "Barrière d'énergie sous la raquette"),
    "♥": ((255, 70, 170), "VIE +1", "Une vie supplémentaire"),
    "P": ((150, 150, 165), "MINI RAQUETTE", "Malus : raquette réduite"),
    "V": ((255, 225, 0), "ACCÉLÉRATION", "Malus : balles plus rapides"),
}
MALUS = {"P", "V"}


def _convert(surf, alpha=True):
    if pygame.display.get_surface() is None:
        return surf
    return surf.convert_alpha() if alpha else surf.convert()


class Art:
    """Toutes les ressources graphiques générées procéduralement."""

    def __init__(self, font):
        self.font = font
        self._bricks = {}
        self._glows = {}
        self._sparkles = {}
        self._paddles = {}
        self._discs = {}
        self._rng = random.Random(7)
        self.cracks = [self._make_cracks(BRICK_W, BRICK_H, stage, seed)
                       for stage, seed in ((1, 11), (2, 23))]
        self.brick_flash = self._make_flash(BRICK_W, BRICK_H)
        self.shine = self._make_shine(BRICK_H)
        self.ball = self._make_ball((255, 255, 255))
        self.ball_fire = self._make_ball((255, 200, 120))
        self.capsules = {k: self._make_capsule_frames(k) for k in POWERUPS}
        self.laser = self._make_laser()
        self.life_icon = self._make_life_icon()

    # ------------------------------------------------------------------ halos
    def glow(self, radius, color, power=2.2, strength=1.0):
        key = (int(radius), color, power, strength)
        g = self._glows.get(key)
        if g is None:
            if len(self._glows) > 2500:
                self._glows.clear()
            g = _convert(S.radial_glow(radius, color, power, strength), alpha=False)
            self._glows[key] = g
        return g

    def sparkle(self, radius, color):
        key = (int(radius), color)
        g = self._sparkles.get(key)
        if g is None:
            g = _convert(S.sparkle(radius, color), alpha=False)
            self._sparkles[key] = g
        return g

    def disc(self, radius, color, alpha=255):
        key = (int(radius), color, alpha)
        g = self._discs.get(key)
        if g is None:
            g = _convert(S.soft_disc(radius, color, alpha))
            self._discs[key] = g
        return g

    # ------------------------------------------------------------------ briques
    def brick(self, kind, hue, sat=0.85, dmg=0, phase=0):
        """Sprite de brique. La teinte est quantifiée pour le cache (reflets chatoyants)."""
        hq = int(round((hue % 1.0) * 96)) % 96
        key = (kind, hq, round(sat, 2), dmg, phase if kind == PRISM else 0)
        s = self._bricks.get(key)
        if s is None:
            s = self._make_brick(kind, hq / 96.0, sat, dmg, phase)
            self._bricks[key] = s
        return s

    def prewarm_bricks(self, specs):
        """Génère d'avance les variantes (reflets, dégâts) des briques d'un niveau."""
        for kind, hue, sat, max_hp in specs:
            if kind == PRISM:
                for ph in range(24):
                    self.brick(kind, hue, sat, 0, ph)
                continue
            offsets = (0,) if kind in (METAL, BOMB) else range(-3, 4)
            for d in offsets:
                for dmg in range(max_hp):
                    self.brick(kind, hue + d / 96.0, sat, dmg)

    def _body(self, w, h, top, mid, bottom, radius=5):
        body = S.vgradient(w, h, [(0.0, top), (0.45, mid), (1.0, bottom)], alpha=True)
        return S.round_mask(body, radius)

    def _gloss(self, surf, w, h, strength=120, inset=3):
        gh = max(2, int(h * 0.42))
        gloss = pygame.Surface((w - inset * 2, gh), pygame.SRCALPHA, 32)
        for y in range(gh):
            a = int(strength * (1.0 - y / gh) ** 1.4)
            pygame.draw.line(gloss, (255, 255, 255, a), (0, y), (w - inset * 2, y))
        S.round_mask(gloss, 4)
        surf.blit(gloss, (inset, 2))

    def _make_brick(self, kind, hue, sat, dmg, phase):
        w, h = BRICK_W, BRICK_H
        base = hsv(hue, sat, 1.0)
        if kind == NORMAL:
            s = self._body(w, h, lighten(base, 0.35), base, darken(base, 0.5))
            self._gloss(s, w, h)
            pygame.draw.line(s, (*lighten(base, 0.3), 150), (5, h - 3), (w - 6, h - 3))
            pygame.draw.rect(s, (*lighten(base, 0.65), 255), s.get_rect(), 1, border_radius=5)
            pygame.draw.line(s, (255, 255, 255, 230), (6, 3), (15, 3), 2)
        elif kind == HARD:
            frame = darken(base, 0.55)
            s = self._body(w, h, lighten(frame, 0.25), frame, darken(frame, 0.5))
            inner_col = base if dmg == 0 else darken(base, 0.35)
            inner = self._body(w - 10, h - 10, lighten(inner_col, 0.4), inner_col,
                               darken(inner_col, 0.35), radius=3)
            s.blit(inner, (5, 5))
            pygame.draw.line(s, (255, 255, 255, 200), (8, 7), (w - 9, 7), 1)
            for x in (3, w - 4):
                pygame.draw.circle(s, lighten(base, 0.6), (x, h // 2), 1)
            self._gloss(s, w, h, strength=70)
            pygame.draw.rect(s, (*lighten(base, 0.5), 255), s.get_rect(), 1, border_radius=5)
        elif kind == ARMOR:
            s = self._body(w, h, (200, 210, 235), (85, 90, 120), (35, 38, 60))
            core = base if dmg == 0 else darken(base, 0.25 * dmg + 0.1)
            pygame.draw.rect(s, darken(core, 0.6), (6, h // 2 - 4, w - 12, 8), border_radius=3)
            pygame.draw.rect(s, core, (8, h // 2 - 2, w - 16, 4), border_radius=2)
            pygame.draw.line(s, lighten(core, 0.7), (10, h // 2 - 1), (w - 11, h // 2 - 1))
            for x, y in ((4, 4), (w - 5, 4), (4, h - 5), (w - 5, h - 5)):
                pygame.draw.circle(s, (40, 40, 60), (x, y), 2)
                pygame.draw.circle(s, (230, 235, 255), (x - 0.5, y - 0.5), 1)
            self._gloss(s, w, h, strength=90)
            pygame.draw.rect(s, (230, 235, 255, 255), s.get_rect(), 1, border_radius=5)
        elif kind == METAL:
            s = S.vgradient(w, h, [(0.0, (245, 248, 255)), (0.3, (160, 170, 200)),
                                   (0.52, (60, 64, 88)), (0.7, (120, 128, 160)),
                                   (1.0, (205, 212, 238))], alpha=True)
            for i in range(-h, w, 7):
                pygame.draw.line(s, (255, 255, 255, 28), (i, h), (i + h, 0), 2)
            S.round_mask(s, 4)
            for x, y in ((5, 5), (w - 6, 5), (5, h - 6), (w - 6, h - 6)):
                pygame.draw.circle(s, (30, 32, 45), (x, y), 2)
                pygame.draw.circle(s, (255, 255, 255), (x - 0.6, y - 0.6), 1)
            pygame.draw.rect(s, (255, 255, 255, 255), s.get_rect(), 1, border_radius=4)
            pygame.draw.rect(s, (40, 40, 60, 255), s.get_rect().inflate(-2, -2), 1, border_radius=3)
        elif kind == BOMB:
            s = self._body(w, h, (170, 30, 40), (110, 10, 25), (45, 0, 10))
            stripe = pygame.Surface((w, h), pygame.SRCALPHA, 32)
            for i in range(-h, w + h, 10):
                pygame.draw.polygon(stripe, (255, 200, 0, 255),
                                    [(i, h), (i + 5, h), (i + 5 + h, 0), (i + h, 0)])
            clip = pygame.Surface((w, h), pygame.SRCALPHA, 32)
            pygame.draw.rect(clip, (255, 255, 255, 255), (0, 0, 12, h))
            pygame.draw.rect(clip, (255, 255, 255, 255), (w - 12, 0, 12, h))
            stripe.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            s.blit(stripe, (0, 0))
            S.round_mask(s, 5)
            cx, cy = w // 2, h // 2
            pygame.draw.circle(s, (60, 0, 0), (cx, cy), 8)
            pygame.draw.circle(s, (255, 120, 0), (cx, cy), 6)
            pygame.draw.circle(s, (255, 230, 120), (cx, cy), 3)
            self._gloss(s, w, h, strength=80)
            pygame.draw.rect(s, (255, 160, 60, 255), s.get_rect(), 1, border_radius=5)
        elif kind == PRISM:
            s = S.prism_body(w, h, phase / 24.0)
            S.round_mask(s, 5)
            self._gloss(s, w, h, strength=95)
            pygame.draw.rect(s, (255, 255, 255, 255), s.get_rect(), 1, border_radius=5)
            for px, py in ((12, 7), (40, 15), (50, 6)):
                pygame.draw.line(s, (255, 255, 255, 220), (px - 3, py), (px + 3, py))
                pygame.draw.line(s, (255, 255, 255, 220), (px, py - 3), (px, py + 3))
        else:
            raise ValueError(kind)
        if dmg > 0 and kind in (HARD, ARMOR):
            s.blit(self.cracks[min(dmg, 2) - 1], (0, 0))
        return _convert(s)

    def _make_cracks(self, w, h, stage, seed):
        rng = random.Random(seed)
        s = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        n = 2 if stage == 1 else 5
        for _ in range(n):
            x, y = rng.uniform(8, w - 8), rng.choice((0, h))
            ang = math.pi / 2 if y == 0 else -math.pi / 2
            ang += rng.uniform(-0.8, 0.8)
            pts = [(x, y)]
            for _ in range(rng.randint(3, 5)):
                ang += rng.uniform(-0.9, 0.9)
                x += math.cos(ang) * rng.uniform(4, 9)
                y += math.sin(ang) * rng.uniform(3, 6)
                pts.append((x, y))
            pygame.draw.lines(s, (255, 255, 255, 130), False, [(px + 1, py + 1) for px, py in pts], 1)
            pygame.draw.lines(s, (10, 0, 20, 230), False, pts, 2 if stage == 2 else 1)
        S.round_mask(s, 5)
        return _convert(s)

    def _make_flash(self, w, h):
        s = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        pygame.draw.rect(s, (255, 255, 255, 255), s.get_rect(), border_radius=5)
        return _convert(s)

    def _make_shine(self, h):
        """Reflet diagonal qui balaie les briques."""
        w = 26 + h
        s = pygame.Surface((w, h), pygame.SRCALPHA, 32)
        for i in range(26):
            a = int(170 * math.sin(math.pi * i / 25) ** 2)
            pygame.draw.line(s, (255, 255, 255, a), (i + h, 0), (i, h))
        return _convert(s)

    # ------------------------------------------------------------------ raquette
    def paddle(self, width, laser=False):
        width = max(24, int(round(width / 2.0)) * 2)
        key = (width, laser)
        s = self._paddles.get(key)
        if s is None:
            s = self._make_paddle(width, laser)
            self._paddles[key] = s
        return s

    def _make_paddle(self, w, laser):
        h = PADDLE_H
        s = pygame.Surface((w, h + 8), pygame.SRCALPHA, 32)
        body = S.vgradient(w, h, [(0.0, (235, 250, 255)), (0.35, (120, 150, 200)),
                                  (0.6, (40, 50, 95)), (1.0, (90, 110, 170))], alpha=True)
        S.round_mask(body, h // 2)
        cap_w = 16
        cap = S.vgradient(cap_w, h, [(0.0, (255, 190, 240)), (0.45, (255, 40, 170)),
                                     (1.0, (110, 0, 90))], alpha=True)
        body.blit(cap, (0, 0))
        body.blit(cap, (w - cap_w, 0))
        S.round_mask(body, h // 2)
        pygame.draw.line(body, (20, 10, 40), (cap_w, 2), (cap_w, h - 3), 2)
        pygame.draw.line(body, (20, 10, 40), (w - cap_w - 1, 2), (w - cap_w - 1, h - 3), 2)
        # bande d'énergie centrale
        pygame.draw.rect(body, (0, 120, 200), (cap_w + 4, h // 2 - 2, w - 2 * cap_w - 8, 5),
                         border_radius=2)
        pygame.draw.rect(body, (0, 240, 255), (cap_w + 5, h // 2 - 1, w - 2 * cap_w - 10, 3),
                         border_radius=1)
        pygame.draw.line(body, (230, 255, 255), (cap_w + 7, h // 2), (w - cap_w - 8, h // 2))
        pygame.draw.line(body, (255, 255, 255), (h // 2, 2), (w - h // 2, 2))
        pygame.draw.rect(body, (210, 250, 255), body.get_rect(), 1, border_radius=h // 2)
        s.blit(body, (0, 8))
        if laser:
            for x in (5, w - 11):
                pygame.draw.rect(s, (60, 0, 20), (x, 0, 6, 11), border_radius=2)
                pygame.draw.rect(s, (255, 40, 70), (x + 1, 1, 4, 9), border_radius=2)
                pygame.draw.line(s, (255, 220, 220), (x + 2, 1), (x + 2, 8))
        return _convert(s)

    # ------------------------------------------------------------------ balle
    def _make_ball(self, tint):
        r = BALL_R
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA, 32)
        c = r + 1
        for i in range(r, 0, -1):
            t = i / r
            col = mix((255, 255, 255), tint, t * 0.6)
            col = mix(col, (170, 200, 255), t ** 3 * 0.5)
            pygame.draw.circle(s, (*col, 255), (c, c), i)
        pygame.draw.circle(s, (255, 255, 255, 255), (c - 2, c - 3), 2)
        return _convert(s)

    # ------------------------------------------------------------------ capsules
    def _make_capsule_frames(self, kind, frames=8):
        color = POWERUPS[kind][0]
        w, h = 44, 20
        letter = self.font.render(kind, 11, (255, 255, 255), core=(255, 255, 255), thick=2.4,
                                  glow=0, spacing=1.0)
        out = []
        for f in range(frames):
            s = pygame.Surface((w, h), pygame.SRCALPHA, 32)
            band = f / frames
            body = S.vgradient(w, h, [(0.0, darken(color, 0.55)),
                                      (max(0.01, band * 0.8), lighten(color, 0.55)),
                                      (min(0.99, band * 0.8 + 0.2), color),
                                      (1.0, darken(color, 0.6))], alpha=True)
            S.round_mask(body, h // 2)
            s.blit(body, (0, 0))
            if kind in MALUS:
                for x in range(-h, w, 8):
                    pygame.draw.line(s, (20, 20, 20, 120), (x, h), (x + h, 0), 3)
                S.round_mask(s, h // 2)
            pygame.draw.ellipse(s, (0, 0, 0, 120), (w // 2 - 10, 2, 20, h - 4))
            letter.draw(s, w // 2, h // 2)
            pygame.draw.rect(s, (*lighten(color, 0.7), 255), s.get_rect(), 1, border_radius=h // 2)
            pygame.draw.line(s, (255, 255, 255, 180), (h // 2, 2), (w - h // 2, 2))
            out.append(_convert(s))
        return out

    def _make_life_icon(self):
        w, h = 32, 12
        s = S.vgradient(w, h, [(0.0, (235, 250, 255)), (0.4, (110, 140, 200)), (1.0, (40, 50, 100))],
                        alpha=True)
        cap = S.vgradient(8, h, [(0.0, (255, 190, 240)), (0.5, (255, 40, 170)), (1.0, (110, 0, 90))],
                          alpha=True)
        s.blit(cap, (0, 0))
        s.blit(cap, (w - 8, 0))
        pygame.draw.line(s, (0, 240, 255), (10, h // 2), (w - 11, h // 2), 2)
        S.round_mask(s, h // 2)
        pygame.draw.rect(s, (210, 250, 255, 255), s.get_rect(), 1, border_radius=h // 2)
        return _convert(s)

    def _make_laser(self):
        s = pygame.Surface((6, 18), pygame.SRCALPHA, 32)
        pygame.draw.rect(s, (255, 40, 80, 255), (0, 0, 6, 18), border_radius=3)
        pygame.draw.rect(s, (255, 230, 230, 255), (2, 1, 2, 16), border_radius=1)
        return _convert(s)
