"""Panneaux latéraux (HUD) : score, Kléos, stade, vies, théophanies, arme divine, puissance, vitesse."""
import math

import numpy as np
import pygame

from . import palette as P
from . import font as F
from . import ui
from .config import PF_X, PF_W, SCREEN_W, SCREEN_H
from .sprites import S, icon_surface
from .spritegen import fbm, rgb_surface
from .weapons import WEAPON_NAMES, MODE_NAMES, MODE_GREEK, GOD_NAMES
from .util import clamp

GOLD = (236, 190, 90)
GOLD_D = (120, 80, 30)
PALE = (200, 206, 240)
DIM = (120, 120, 170)


def build_panels():
    """Fond statique des deux panneaux (dégradé, texture, méandres, colonnes ioniques)."""
    s = pygame.Surface((SCREEN_W, SCREEN_H)).convert()
    w = PF_X
    n = fbm(SCREEN_W, SCREEN_H, 12, 8, 4, seed=5)
    yy = np.linspace(0, 1, SCREEN_H)[None, :]
    base = np.zeros((SCREEN_W, SCREEN_H, 3), np.float32)
    top = np.array([22, 14, 46], np.float32)
    bot = np.array([8, 5, 20], np.float32)
    base[:] = top * (1 - yy[..., None]) + bot * yy[..., None]
    base *= (0.85 + n * 0.3)[..., None]
    s.blit(rgb_surface(base), (0, 0))
    # motif de méandres en filigrane
    faint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for yv in range(8, SCREEN_H, 26):
        ui.meander(faint, 4, yv, w - 20, (60, 40, 90, 60), (30, 20, 50, 60), 5)
        ui.meander(faint, PF_X + PF_W + 16, yv, w - 20, (60, 40, 90, 60), (30, 20, 50, 60), 5)
    s.blit(faint, (0, 0))
    # frises dorées haut/bas
    for x0 in (0, PF_X + PF_W):
        ui.meander(s, x0 + 3, 3, w - 6, GOLD, GOLD_D, 5)
        ui.meander(s, x0 + 3, SCREEN_H - 10, w - 6, GOLD, GOLD_D, 5)
    # colonnes ioniques encadrant l'aire de jeu
    col = ui.column_surface(SCREEN_H, 11)
    s.blit(col, (PF_X - col.get_width() + 5, 0))
    s.blit(col, (PF_X + PF_W - 5, 0))
    return s


class HUD:
    def __init__(self):
        self.panels = build_panels()
        self.col = ui.column_surface(SCREEN_H, 11)
        self.icons = {g: icon_surface(g) for g in P.GOD_COLORS}
        self.big_icons = {}
        for g, ic in self.icons.items():
            self.big_icons[g] = pygame.transform.scale(ic, (ic.get_width() * 3, ic.get_height() * 3))
        self.bolt = icon_surface("zeus", (170, 210, 255))
        self.score_disp = 0
        self.t = 0

    def draw(self, screen, g):
        """g : objet Game."""
        self.t += 1
        t = self.t
        screen.blit(self.panels, (0, 0), (0, 0, PF_X, SCREEN_H))
        rx = PF_X + PF_W
        screen.blit(self.panels, (rx, 0), (rx, 0, SCREEN_W - rx, SCREEN_H))
        # les colonnes encadrent l'aire de jeu (et masquent ses bords pendant les secousses)
        screen.blit(self.col, (PF_X - self.col.get_width() + 5, 0))
        screen.blit(self.col, (PF_X + PF_W - 5, 0))
        font = F.FONT
        p = g.player
        sc = g.score
        # --- panneau gauche -------------------------------------------------------
        x0 = 8
        ui.draw_metal(screen, ui.greekify("ALETHEIA"), 50, 18, 1)
        font.draw(screen, "SCORE", x0, 34, DIM)
        self.score_disp += (sc.score - self.score_disp) * 0.25
        if abs(sc.score - self.score_disp) < 2:
            self.score_disp = sc.score
        font.draw(screen, f"{int(self.score_disp):09d}", x0, 44, (255, 246, 220), outline=(10, 6, 22),
                  grad=((255, 250, 230), (240, 180, 80)))
        font.draw(screen, "RECORD", x0, 58, DIM)
        hs = max(g.save.hiscore, sc.score)
        font.draw(screen, f"{hs:09d}", x0, 68, PALE)
        # Kléos
        yk = 88
        font.draw(screen, "KLÉOS", x0, yk, GOLD)
        m = sc.mult
        mc = (255, 220, 120) if m < 8 else ((255, 255, 255) if (t // 4) % 2 else (255, 200, 90))
        scale = 2
        txt = f"×{m}"
        font.draw(screen, txt, 90, yk - 3, mc, "right", outline=(10, 6, 22), scale=scale)
        bw = 84
        pygame.draw.rect(screen, (30, 20, 50), (x0, yk + 13, bw, 4))
        if sc.chain > 0:
            k = clamp(sc.timer / 125, 0, 1)
            pygame.draw.rect(screen, (255, 200, 90) if k > 0.3 else (255, 90, 90), (x0, yk + 13, int(bw * k), 4))
        pygame.draw.rect(screen, GOLD_D, (x0 - 1, yk + 12, bw + 2, 6), 1)
        font.draw(screen, f"CHAÎNE {sc.chain}", x0, yk + 21, DIM)
        if sc.pulse > 0 and (sc.pulse // 3) % 2:
            pygame.draw.rect(screen, (255, 230, 150), (x0 - 2, yk - 3, bw + 4, 34), 1)
        # vies / théophanies
        yl = 134
        font.draw(screen, "VIES", x0, yl, DIM)
        li = S["life_icon"].img
        for i in range(min(max(p.lives, 0), 6)):
            screen.blit(li, (x0 + i * 13 - 2, yl + 8))
        if p.lives > 6:
            font.draw(screen, f"+{p.lives - 6}", x0 + 80, yl + 12, PALE)
        font.draw(screen, "THÉOPHANIES", x0, yl + 28, DIM)
        for i in range(min(p.bombs, 6)):
            screen.blit(self.bolt, (x0 + i * 13, yl + 37))
        # stade
        from . import stages
        info = stages.INFO.get(g.stage_n)
        if info:
            ys = 196
            ui.meander(screen, x0, ys - 8, 88, (90, 60, 30), (50, 30, 15), 4)
            font.draw(screen, info["num"], x0, ys, GOLD)
            font.draw(screen, info["name"], x0, ys + 11, (255, 255, 255))
            font.draw(screen, info["sub_short"], x0, ys + 22, DIM)
        diff = g.diff["name"]
        font.draw(screen, diff, x0, 244, (150, 110, 170))
        # --- panneau droit ---------------------------------------------------------
        x1 = rx + 14
        font.draw(screen, "ARME DIVINE", x1, 18, DIM)
        if p.god:
            col = P.GOD_COLORS[p.god]
            spr = S["orb"][p.god]
            cx, cy = x1 + 14, 44
            gl = pygame.Surface((40, 40))
            gl.fill((0, 0, 0))
            from .fx import glow
            gg = glow(16, (col[0] // 3, col[1] // 3, col[2] // 3))
            screen.blit(gg, (cx - 16, cy - 16), special_flags=pygame.BLEND_ADD)
            spr.draw(screen, cx, cy)
            flash = g.hud_flash_weapon > 0 and (g.hud_flash_weapon // 3) % 2
            font.draw(screen, WEAPON_NAMES[p.god], x1 + 32, 34, (255, 255, 255) if flash else col,
                      outline=(10, 6, 22))
            font.draw(screen, GOD_NAMES[p.god], x1 + 32, 45, DIM)
            # modes
            ym = 64
            for i in range(3):
                sel = i == p.mode
                c = col if sel else (70, 70, 110)
                bx = x1 + i * 28
                pygame.draw.rect(screen, (20, 14, 40), (bx, ym, 25, 12))
                pygame.draw.rect(screen, c, (bx, ym, 25, 12), 1)
                font.draw(screen, MODE_GREEK[i], bx + 12, ym + 2, (255, 255, 255) if sel else (90, 90, 130), "center")
            font.draw(screen, MODE_NAMES[p.god][p.mode], x1, ym + 17, (240, 240, 255))
        else:
            font.draw(screen, "AUCUNE", x1, 36, (110, 110, 150))
            font.draw(screen, "ATTRAPE UN ORBE", x1, 50, (90, 90, 130))
            font.draw(screen, "DIVIN !", x1, 60, (90, 90, 130))
        # puissance / blindage
        yp = 104
        if p.power == 0 and not p.dead and (t // 12) % 2 == 0:
            font.draw(screen, "BLINDAGE CRITIQUE", x1, yp, (255, 90, 100))
        else:
            font.draw(screen, "PUISSANCE", x1, yp, DIM)
        for i in range(5):
            cx = x1 + 5 + i * 17
            cy = yp + 16
            on = i < p.power
            pts = [(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)]
            if on:
                c = (255, 214, 100) if p.power < 5 else ((255, 255, 255) if (t // 5 + i) % 5 == 0 else (255, 200, 80))
                pygame.draw.polygon(screen, c, pts)
                pygame.draw.polygon(screen, (255, 250, 220), [(cx, cy - 3), (cx + 2, cy - 1), (cx, cy)], 0)
            else:
                pygame.draw.polygon(screen, (40, 30, 60), pts)
            pygame.draw.polygon(screen, (10, 6, 22), pts, 1)
        need = p.chips_needed()
        k = p.chips / need if p.power < 5 else 1.0
        pygame.draw.rect(screen, (30, 20, 50), (x1, yp + 25, 86, 3))
        pygame.draw.rect(screen, (255, 160, 60), (x1, yp + 25, int(86 * k), 3))
        if p.power == 5:
            font.draw(screen, "MAX", x1 + 86, yp, (255, 230, 150) if (t // 8) % 2 else (255, 160, 60), "right")
        # vitesse
        yv = 146
        font.draw(screen, "VITESSE", x1, yv, DIM)
        for i in range(4):
            on = i <= p.speed_i
            c = (120, 220, 255) if on else (40, 40, 70)
            bx = x1 + i * 13
            pts = [(bx, yv + 10), (bx + 6, yv + 10), (bx + 10, yv + 15), (bx + 6, yv + 20), (bx, yv + 20),
                   (bx + 4, yv + 15)]
            pygame.draw.polygon(screen, c, pts)
            pygame.draw.polygon(screen, (10, 6, 22), pts, 1)
        font.draw(screen, str(p.speed_i + 1), x1 + 62, yv + 11, (200, 240, 255))
        # portrait divin (grand symbole)
        if p.god:
            big = self.big_icons[p.god]
            big.set_alpha(70 + int(30 * math.sin(t * 0.05)))
            screen.blit(big, (x1 + 44 - big.get_width() // 2, 178))
            big.set_alpha(255)
        # rappel des commandes
        yc = 216
        lab = g.app.input.labels
        for i, (k_, v_) in enumerate(((lab["fire"] + "/J", "TIR"), (lab["mode"] + "/K", "MODE"),
                                      (lab["bomb"] + "/L", "BOMBE"), (lab["speed"] + "/⇧", "VITESSE"))):
            font.draw(screen, k_.replace("⇧", "MAJ"), x1, yc + i * 10, (110, 100, 150))
            font.draw(screen, v_, x1 + 36, yc + i * 10, (150, 140, 190))
