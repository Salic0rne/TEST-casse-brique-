"""Bibliothèque de sprites : modèles procéduraux passés à la Forge.

Conventions : le joueur regarde vers le haut (-y), les ennemis vers le bas (+y).
"""
import math

import numpy as np
import pygame

from . import palette as P
from .spritegen import (L, forge, forge_rot, circle, ellipse, rect, line, polyline, arc, star, sym, mirror,
                        move, ascii_sprite, arrays_to_surface, rgb_surface, Sprite, dilate, fbm, TAU)

S = {}          # nom -> Sprite ou liste de Sprites
NROT = 32       # orientations des projectiles allongés
NTUR = 16       # orientations des tourelles


# ---------------------------------------------------------------------------
# Joueur : l'intercepteur ALETHEIA (marbre, or, verrière cyan, ailes de Hermès)
# ---------------------------------------------------------------------------
def player_layers():
    wing = [(3, -2), (7, 1.2), (11.4, 5.6), (12.4, 9.2), (11.4, 11.4), (10.4, 10.0), (9.4, 11.6), (8.4, 9.8),
            (7.3, 10.9), (6.3, 8.8), (3.6, 7.6)]
    return [
        L([wing], mat=P.MARBLE, bevel=1.5, mirror=True, rim=(P.CYAN_E, 0.5), base=0.62),
        L([line(3.8, -0.8, 11.8, 6.4, 1.4)], mat=P.GOLD, bevel=1, mirror=True),
        L([[(10.6, 3.0), (12.6, 2.0), (13.2, 9.4), (11.6, 10.2)]], mat=P.GOLD, bevel=1, mirror=True),
        L([rect(5.3, -5.8, 6.6, 2)], mat=P.STEEL, bevel=1, mirror=True),
        L([sym([(0, -14.5), (1.6, -11), (2.6, -7), (3.6, -2), (4.2, 3), (3.8, 8), (2.6, 11.2), (0, 12.2)])],
          mat=P.MARBLE, bevel=2, rim=(P.CYAN_E, 0.45), veins=0.1, base=0.64),
        L([sym([(0, -2.5), (0.9, -1), (0.9, 8.5), (0, 10.5)])], mat=P.GOLD, bevel=1, profile="round"),
        L([[(1.6, -9.5), (3.3, -6.5), (3.4, -2.8), (2.3, -3.8)]], mat=P.GOLD, bevel=1, mirror=True),
        L([ellipse(0, -6.4, 1.7, 3.3)], mat=P.GLASS, profile="round", spec=0.6),
        L([ellipse(3.4, 9.2, 1.5, 2.6)], mat=P.STEEL, profile="round", mirror=True),
        L([ellipse(3.4, 11.6, 1.0, 0.9)], emit=P.CYAN_E, glow=1.0, mirror=True),
        L([rect(11.7, 8.2, 12.9, 9.4)], emit=P.CYAN_E, glow=0.8, mirror=True),
        L([rect(-0.5, -12.6, 0.5, -11.4)], emit=P.CYAN_E, glow=0.5),
    ]


def build_player():
    frames = []
    for b in (-2, -1, 0, 1, 2):
        def xf(x, y, b=b):
            if b == 0:
                return x, y
            k = (1 - 0.13 * abs(b)) if x * b > 0 else (1 - 0.05 * abs(b))
            return x * k + b * 0.35 * (1 - min(1.0, abs(x) / 12)), y
        light = None
        if b:
            lv = np.array([-0.5 + 0.18 * b, -0.72, 0.62], np.float32)
            light = lv / np.linalg.norm(lv)
        frames.append(forge(29, 31, player_layers(), xform=xf, halo=3, light=light, want_shadow=True,
                            shadow_alpha=80))
    S["player"] = frames
    # icône de vie (mini vaisseau)
    S["life_icon"] = forge(15, 16, player_layers(), sx=0.5, sy=0.5, halo=0)


# ---------------------------------------------------------------------------
# Projectiles du joueur
# ---------------------------------------------------------------------------
def build_player_shots():
    S["shot"] = forge(5, 13, [
        L([ellipse(0, 0, 1.6, 5.5)], emit=(255, 210, 120), glow=0.6),
        L([ellipse(0, -0.5, 0.7, 4.2)], emit=(255, 255, 235)),
    ], outline=None, halo=2)
    S["shot_s"] = forge(5, 9, [
        L([ellipse(0, 0, 1.3, 3.5)], emit=(255, 200, 110), glow=0.6),
        L([ellipse(0, -0.4, 0.6, 2.5)], emit=(255, 255, 235)),
    ], outline=None, halo=2)
    # flèche d'Artémis (orientée vers le haut, 32 directions)
    arrow_layers = [
        L([line(0, 6, 0, -3, 1.7)], emit=(190, 255, 220), glow=1.0),
        L([sym([(0, -7), (2.4, -2.6), (0, -3.6)])], emit=(240, 255, 245), glow=1.0),
        L([[(0, 3.5), (2.2, 6.2), (1.6, 7.2), (0, 5.6)]], emit=(130, 230, 190), mirror=True, glow=0.6),
    ]
    S["arrow"] = [forge(15, 15, arrow_layers, rot=i * TAU / NROT, outline=None, halo=2) for i in range(NROT)]
    # dard de lune
    S["dart"] = [forge(9, 9, [L([ellipse(0, 0, 0.9, 3.2)], emit=(210, 255, 230), glow=0.8)],
                       rot=i * TAU / NROT, outline=None, halo=2) for i in range(NROT)]
    # croissant de vague (Poséidon)
    S["wave"] = [forge(19, 19, [
        L([arc(0, 3, 5.5, 7.8, math.pi + 0.45, TAU - 0.45)], emit=(60, 240, 210), glow=0.7),
        L([arc(0, 3, 6.4, 7.2, math.pi + 0.6, TAU - 0.6)], emit=(220, 255, 250)),
    ], rot=i * TAU / NROT, outline=None, halo=3) for i in range(NROT)]
    S["tide"] = forge(9, 9, [L([circle(0, 0, 3)], emit=(60, 230, 220), glow=0.8),
                             L([circle(-0.5, -0.5, 1.4)], emit=(230, 255, 255))], outline=None, halo=3)
    S["abyss"] = forge(15, 15, [L([circle(0, 0, 5.5)], emit=(30, 150, 200), glow=0.8),
                                L([circle(0, 0, 3.8)], emit=(40, 230, 220)),
                                L([circle(-1, -1, 1.6)], emit=(240, 255, 255))], outline=None, halo=4)
    # bouclier d'Athéna (disque doré à la chouette)
    S["aegis"] = forge(13, 13, [
        L([circle(0, 0, 5.4)], mat=P.GOLD, profile="round", spec=0.5),
        L([circle(0, 0, 3.4)], mat=P.BRONZE, profile="round", base=0.5),
        L([circle(-1.1, -0.5, 0.9), circle(1.1, -0.5, 0.9)], emit=(255, 240, 150), glow=0.8),
        L([sym([(0, 0.4), (0.5, 1.4), (0, 2.0)])], flat=P.GOLD[4]),
    ], halo=2)
    S["spear"] = forge(5, 13, [L([line(0, 5, 0, -3, 1.1)], emit=(250, 230, 150), glow=0.5),
                                L([sym([(0, -6), (1.4, -2.6), (0, -3.2)])], emit=(255, 255, 230), glow=0.5)],
                       outline=None, halo=2)
    # obus / météore d'Héphaïstos
    S["shell"] = forge(9, 11, [L([ellipse(0, 0, 2.6, 3.6)], mat=P.BRONZE, profile="round"),
                               L([ellipse(0, -1.6, 1.4, 1.4)], emit=(255, 170, 60), glow=0.8)], halo=3)
    S["meteor"] = forge(17, 17, [L([circle(0, 0, 6.2)], emit=(255, 110, 30), glow=1.0),
                                 L([circle(-0.6, -0.8, 4.4)], emit=(255, 200, 90)),
                                 L([circle(-1.2, -1.4, 2.2)], emit=(255, 255, 220))], outline=None, halo=4)
    # lune d'Artémis (satellite)
    S["moon"] = forge(15, 15, [
        L([circle(0, 0, 5.8)], mat=P.ICE, profile="round", spec=0.5, sub=[circle(2.8, -1.8, 5.0)]),
        L([circle(-3.2, 1.5, 0.8)], emit=(210, 255, 230), glow=1.0),
    ], halo=3)
    S["muzzle"] = forge(9, 9, [L([star(0, 0, 1.2, 4.2, 4)], emit=(255, 240, 190), glow=1.0)], outline=None,
                        halo=2)


# ---------------------------------------------------------------------------
# Projectiles ennemis (couleurs chaudes, cœur blanc, contour sombre : lisibilité maximale)
# ---------------------------------------------------------------------------
BCOL = {
    "pink": (255, 58, 170), "orange": (255, 140, 30), "violet": (170, 90, 255), "red": (255, 50, 50),
    "gold": (255, 215, 90), "green": (80, 255, 150), "blue": (90, 170, 255), "white": (230, 230, 255),
}


def orb_bullet(r, col):
    size = int(r * 2 + 3)
    c = (size - 1) / 2
    xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    rgb = np.zeros((size, size, 3), np.float32)
    alpha = np.zeros((size, size), np.float32)
    col = np.array(col, np.float32)
    dark = col * 0.28
    rim = d <= r + 0.5
    rgb[rim] = dark
    alpha[rim] = 255
    body = d <= r - 0.5
    rgb[body] = col
    mid = d <= r * 0.62
    rgb[mid] = col * 0.45 + 255 * 0.55
    core = d <= max(0.6, r * 0.34)
    rgb[core] = (255, 255, 255)
    # reflet
    hl = (np.abs(xx - (c - r * 0.35)) < 0.8) & (np.abs(yy - (c - r * 0.35)) < 0.8) & body
    rgb[hl] = (255, 255, 255)
    halo = np.clip(1 - (d - r) / 2.2, 0, 1) * (d > r + 0.5) * 110
    alpha = np.maximum(alpha, halo)
    rgb[(d > r + 0.5)] = col
    return Sprite(arrays_to_surface(rgb, alpha))


def ring_bullet(r, col):
    size = int(r * 2 + 3)
    c = (size - 1) / 2
    xx, yy = np.mgrid[0:size, 0:size].astype(np.float32)
    d = np.sqrt((xx - c) ** 2 + (yy - c) ** 2)
    rgb = np.zeros((size, size, 3), np.float32)
    alpha = np.zeros((size, size), np.float32)
    colv = np.array(col, np.float32)
    band = (d <= r + 0.5) & (d >= r - 1.8)
    rgb[band] = colv
    alpha[band] = 255
    inner = (d <= r - 0.3) & (d >= r - 1.1)
    rgb[inner] = colv * 0.4 + 153
    edge = ((d > r + 0.5) & (d <= r + 1.4)) | ((d < r - 1.8) & (d >= r - 2.6))
    rgb[edge] = colv * 0.25
    alpha[edge] = 255
    return Sprite(arrays_to_surface(rgb, alpha))


def rice_frames(col, rx=4.2, ry=1.9):
    colv = tuple(int(v) for v in col)
    light = tuple(int(v * 0.4 + 153) for v in col)
    layers = [L([ellipse(0, 0, ry, rx)], flat=colv), L([ellipse(0, -0.4, ry * 0.45, rx * 0.62)], flat=light),
              L([ellipse(0, -0.6, 0.35, rx * 0.35)], flat=(255, 255, 255))]
    w = int(rx * 2 + 5)
    return [forge(w, w, layers, rot=i * TAU / NROT, outline=tuple(int(v * 0.25) for v in col), halo=0, ss=4)
            for i in range(NROT)]


def feather_frames():
    layers = [
        L([sym([(0, -6.5), (1.9, -3), (2.1, 1.5), (1.0, 5), (0, 6.5)])], mat=P.BRONZE, bevel=1),
        L([line(0, -6, 0, 6, 0.8)], emit=(255, 80, 60)),
    ]
    return [forge(15, 15, layers, rot=i * TAU / NROT, outline=(60, 10, 20), halo=0, ss=4) for i in range(NROT)]


def arrowhead_frames(col):
    colv = tuple(int(v) for v in col)
    layers = [L([line(0, -4, 0, 3, 1.0)], flat=(230, 200, 150)),
              L([sym([(0, 6.5), (2.2, 2.2), (0, 3.2)])], flat=colv),
              L([sym([(0, 5.8), (0.8, 3.4), (0, 3.8)])], flat=(255, 255, 255))]
    return [forge(15, 15, layers, rot=i * TAU / NROT, outline=(40, 10, 10), halo=0, ss=4) for i in range(NROT)]


def star_frames(col, r=5.0):
    colv = tuple(int(v) for v in col)
    out = []
    for i in range(8):
        a = i * (math.pi / 4) / 8
        layers = [L([star(0, 0, r * 0.45, r, 8, rot=a)], flat=colv),
                  L([star(0, 0, r * 0.3, r * 0.62, 8, rot=a)], flat=tuple(int(v * 0.4 + 153) for v in col)),
                  L([circle(0, 0, r * 0.28)], flat=(255, 255, 255))]
        out.append(forge(int(r * 2 + 5), int(r * 2 + 5), layers, outline=tuple(int(v * 0.25) for v in col),
                         halo=0, ss=4))
    return out


def build_bullets():
    for name, col in BCOL.items():
        S[f"b_s_{name}"] = orb_bullet(2.2, col)
        S[f"b_m_{name}"] = orb_bullet(3.2, col)
        S[f"b_l_{name}"] = orb_bullet(4.6, col)
        S[f"b_xl_{name}"] = orb_bullet(7.0, col)
        S[f"b_ring_{name}"] = ring_bullet(4.5, col)
    for name in ("pink", "orange", "violet", "green", "blue", "gold", "red"):
        S[f"b_rice_{name}"] = rice_frames(BCOL[name])
        S[f"b_needle_{name}"] = rice_frames(BCOL[name], rx=6.0, ry=1.3)
    S["b_feather"] = feather_frames()
    S["b_arrow"] = arrowhead_frames(BCOL["orange"])
    for name in ("gold", "pink", "violet", "green", "orange"):
        S[f"b_star_{name}"] = star_frames(BCOL[name])


# ---------------------------------------------------------------------------
# Icônes des dieux (ASCII 11x11)
# ---------------------------------------------------------------------------
ICONS = {
    "zeus": ["....##.....", "...##......", "..##.......", ".######....", "....##.....", "...##......",
             "..######...", ".....##....", "....##.....", "...##......", "..#........"],
    "apollo": ["....#.#....", ".#...#...#.", "..#.###.#..", "...#####...", "#.#######.#", ".#########.",
               "#.#######.#", "...#####...", "..#.###.#..", ".#...#...#.", "....#.#...."],
    "artemis": ["..##.......", "...##..#...", "....##.##..", ".....#..##.", "#########.#", ".....#..##.",
                "....##.##..", "...##..#...", "..##.......", "...........", "..........."],
    "poseidon": ["#...#...#..", "#...#...#..", "#.#.#.#.#..", "##..#..##..", ".#######...", "....#......",
                 "....#......", "....#......", "....#......", "....#......", "....#......"],
    "athena": ["..#######..", ".#.......#.", "#..##.##..#", "#.#..#..#.#", "#..##.##..#", "#....#....#",
               "#...#.#...#", ".#.......#.", "..#.....#..", "...#...#...", "....###...."],
    "hephaestus": ["#######....", "#######....", "#######....", "...##......", "...##......", "...##......",
                   "...##......", "...##...#..", "...##..###.", "...##.#####", "...........",],
}
GODS = ["zeus", "apollo", "artemis", "poseidon", "athena", "hephaestus"]


def icon_surface(god, col=None, outline=P.OUTLINE):
    col = col or P.GOD_COLORS[god]
    return ascii_sprite(ICONS[god], {"#": col}, outline=outline)


# ---------------------------------------------------------------------------
# Objets à ramasser
# ---------------------------------------------------------------------------
def build_items():
    S["orb"] = {}
    for g in GODS:
        col = P.GOD_COLORS[g]
        ramp = [tuple(int(c * k) for c in col) for k in (0.15, 0.3, 0.5, 0.72, 0.9, 1.0)]
        ramp[-1] = tuple(min(255, int(c * 0.5 + 128)) for c in col)
        base = forge(19, 19, [
            L([circle(0, 0, 7.5)], mat=ramp, profile="round", spec=0.8, base=0.5, contrast=1.1),
            L([arc(0, 0, 7.6, 8.6, -2.6, -0.5)], emit=(255, 255, 255), glow=0.6),
        ], halo=3)
        img = base.img.copy()
        ic = icon_surface(g, (255, 255, 255), outline=tuple(int(c * 0.25) for c in col))
        img.blit(ic, (19 // 2 - ic.get_width() // 2, 19 // 2 - ic.get_height() // 2))
        S["orb"][g] = Sprite(img, base.flash, None, base.halo, base.ox, base.oy, 6)
    S["pchip"] = forge(11, 13, [
        L([ellipse(0, 0, 4.4, 5.4)], mat=P.GOLD, profile="round", spec=0.7),
        L([ellipse(0, 0, 3.0, 4.0)], emit=(255, 170, 40), glow=0.8),
    ], halo=2)
    pimg = S["pchip"].img
    pmask = ["###.", "#..#", "###.", "#...", "#..."]
    for y, row in enumerate(pmask):
        for x, c in enumerate(row):
            if c == "#":
                pimg.set_at((4 + x, 4 + y), (255, 255, 240))
    # drachme (4 étapes de rotation)
    S["coin"] = []
    for k in (1.0, 0.7, 0.3, 0.7):
        S["coin"].append(forge(9, 9, [
            L([ellipse(0, 0, 3.6 * k + 0.4, 3.6)], mat=P.GOLD, profile="round", spec=0.6),
            L([ellipse(0, 0, 2.2 * k + 0.2, 2.2)], mat=P.GOLD, bevel=1, base=0.45),
        ], halo=0))
    S["bomb_item"] = forge(15, 15, [
        L([circle(0, 0, 6.2)], mat=P.ICE, profile="round", spec=0.8),
        L([polyline([(1.5, -4.5), (-1.5, -0.5), (1.5, 0.5), (-1.5, 4.8)], 1.4)[i] for i in range(3)],
          emit=(255, 255, 200), glow=1.0),
    ], halo=3)
    S["oneup"] = forge(17, 15, [
        L([arc(0, 1, 4.5, 6.5, math.pi * 0.75, math.pi * 2.25)], mat=P.OLIVE, bevel=1),
        L([ellipse(-5.2, -2.5, 1.2, 2.2, 0.5), ellipse(5.2, -2.5, 1.2, 2.2, -0.5), ellipse(-6.2, 1.5, 1.2, 2.2, 0.1),
           ellipse(6.2, 1.5, 1.2, 2.2, -0.1), ellipse(-3.5, 5.5, 1.2, 2.2, -0.9), ellipse(3.5, 5.5, 1.2, 2.2, 0.9)],
          mat=P.OLIVE, profile="round"),
        L([circle(0, 6.5, 1.4)], mat=P.GOLD, profile="round"),
        L([rect(-0.6, -1.5, 0.6, 1.5), rect(-1.5, -0.6, 1.5, 0.6)], emit=(255, 240, 150), glow=0.8),
    ], halo=2)


# ---------------------------------------------------------------------------
# Ennemis
# ---------------------------------------------------------------------------
def build_enemies():
    # --- Myrmex : drone-fourmi de bronze -------------------------------------------
    myrmex_layers = [
        L(polyline([(1.5, 1.2), (5, 3.3), (6.8, 7)], 1.0) + polyline([(1.8, 0.2), (6, -0.3), (7.8, 2.2)], 1.0)
          + polyline([(1.4, -0.8), (5, -3.4), (7.2, -2.2)], 1.0), mat=P.DARKSTEEL, bevel=1, mirror=True),
        L([ellipse(3.2, -1.8, 3.0, 1.2, 0.45)], mat=P.PURPLE, profile="round", mirror=True, base=0.6),
        L([ellipse(0, -4.6, 3.5, 4.2)], mat=P.BRONZE, profile="round", spec=0.4),
        L([ellipse(0, -5.2, 1.1, 2.6)], mat=P.GOLD, bevel=1),
        L([ellipse(0, 0.4, 2.2, 2.0)], mat=P.BRONZE, profile="round"),
        L([ellipse(0, 4.4, 2.8, 2.5)], mat=P.BRONZE, profile="round", spec=0.4),
        L([[(0.9, 6.2), (2.6, 7.8), (1.6, 8.6), (0.3, 7.2)]], mat=P.GOLD, bevel=1, mirror=True),
        L([circle(1.3, 5.0, 0.8)], emit=P.RED_E, glow=1.0, mirror=True),
    ]
    S["myrmex"] = forge(19, 19, myrmex_layers, want_shadow=True, halo=2)
    S["myrmex_r"] = forge_rot(19, 19, myrmex_layers, NTUR, want_shadow=True, halo=2)
    # --- Harpie ------------------------------------------------------------------------
    wing = [(1.8, -3), (6.5, -5.4), (10.8, -3.8), (11.8, -1.4), (9.6, -0.6), (10.6, 1.4), (7.8, 1.2), (8.6, 3.2),
            (5, 2.2), (2, 1.5)]
    harpy_layers = [
        L([wing], mat=P.BRONZE, bevel=1.5, mirror=True),
        L([line(3, -2.4, 10, -2.4, 1.0), line(3, -0.2, 8.8, 1.2, 0.9)], mat=P.GOLD, bevel=1, mirror=True),
        L([ellipse(0, -0.5, 2.8, 5.0)], mat=P.BRONZE, profile="round"),
        L([ellipse(0, -3.6, 1.6, 2.6)], mat=P.MAGENTA, profile="round", base=0.45),
        L([ellipse(0, 3.4, 2.3, 2.7)], mat=P.MARBLE, profile="round", base=0.62),
        L([circle(0.9, 3.8, 0.6)], emit=P.RED_E, glow=1.0, mirror=True),
        L(polyline([(1, 5.5), (1.8, 8.2)], 0.9), mat=P.STEEL, bevel=1, mirror=True),
    ]
    S["harpy"] = forge(25, 19, harpy_layers, want_shadow=True, halo=2)
    S["harpy_r"] = forge_rot(25, 25, harpy_layers, NTUR, want_shadow=True, halo=2)
    # --- Oiseau du Stymphale ---------------------------------------------------------------
    blades = [[(2, -2.5), (12.2, -7), (11, -4.8)], [(2.2, -0.8), (12.5, -2.2), (10.8, -0.6)],
              [(2.2, 0.8), (11.2, 2.6), (9.6, 3.2)]]
    S["stymph"] = forge(27, 23, [
        L([[(0.5, -5), (1.5, -10.5), (0, -8.5)], [(1.8, -4.8), (3.8, -9.6), (1.2, -7.6)]], mat=P.STEEL, bevel=1,
          mirror=True),
        L(blades, mat=P.STEEL, bevel=1.2, mirror=True, rim=(P.RED_E, 0.35)),
        L([line(2.5, -2, 11, -5.8, 0.7), line(2.5, 0, 11.4, -1.6, 0.7)], mat=P.GOLD, bevel=1, mirror=True),
        L([ellipse(0, -0.5, 3.0, 5.6)], mat=P.DARKSTEEL, profile="round", spec=0.4),
        L([circle(0, 4.6, 2.6)], mat=P.STEEL, profile="round"),
        L([sym([(0, 10.5), (1.3, 6.4), (0, 6.0)])], mat=P.GOLD, bevel=1),
        L([circle(1.2, 4.6, 0.8)], emit=P.RED_E, glow=1.0, mirror=True),
    ], want_shadow=True, halo=2)
    # --- Cyclope (tourelle au sol) --------------------------------------------------------
    oct_ = [(math.cos(i * TAU / 8 + TAU / 16) * 8.6, math.sin(i * TAU / 8 + TAU / 16) * 8.6) for i in range(8)]
    S["cyclops_base"] = forge(21, 21, [
        L([oct_], mat=P.DARKSTEEL, bevel=2),
        L([circle(0, 0, 6.4)], mat=P.BRONZE, bevel=1.5, sub=[circle(0, 0, 5.2)]),
        L([rect(-0.6, -8.4, 0.6, -6.8), rect(-0.6, 6.8, 0.6, 8.4), rect(6.8, -0.6, 8.4, 0.6), rect(-8.4, -0.6, -6.8, 0.6)],
          emit=(255, 120, 60), glow=0.5),
    ], halo=2)
    tur = [
        L([rect(-2.6, 2, -1.2, 9), rect(1.2, 2, 2.6, 9)], mat=P.STEEL, bevel=1),
        L([circle(0, 0, 5.0)], mat=P.BRONZE, profile="round", spec=0.5),
        L([ellipse(0, 1.6, 3.0, 2.4)], mat=P.MARBLE, profile="round", base=0.66),
        L([circle(0, 2.1, 1.3)], emit=P.RED_E, glow=1.2),
    ]
    S["cyclops_tur"] = forge_rot(21, 21, tur, NTUR, halo=2)
    # --- Pithos (amphore-mine de Pandore) -----------------------------------------------------
    body = sym([(0, -8.2), (1.4, -8.2), (1.4, -6.6), (2.3, -5.6), (4.6, -3), (5.1, 0), (4.3, 4), (2.6, 6.4),
                (1.6, 7.4), (2.2, 8.3), (0, 8.3)])
    S["pithos"] = forge(15, 19, [
        L([line(1.4, -6.4, 4.2, -6.2, 1.0), line(4.2, -6.2, 4.6, -3.2, 1.0)], mat=P.TERRACOTTA, bevel=1,
          mirror=True),
        L([body], mat=P.TERRACOTTA, profile="round", spec=0.3),
        L([rect(-6, -1.4, 6, 1.6)], mat=P.EBONY, bevel=1, clip=True),
        L([rect(-6, 3.2, 6, 3.9), rect(-6, -4.4, 6, -3.8)], mat=P.EBONY, bevel=1, clip=True, cast=False),
        L(polyline([(-1.2, -2.6), (0.4, -0.2), (-0.6, 1.8), (1.0, 3.6)], 0.9), emit=P.MAGENTA_E, glow=1.2),
    ], want_shadow=True, halo=3)
    # --- Messager d'Hermès (porteur d'objets) ----------------------------------------------
    hw = [(3.5, -1.5), (6.5, -4.6), (9.8, -5.2), (8.6, -3.4), (10.4, -3.0), (8.8, -1.4), (10.0, -0.4), (7.6, 0.4),
          (4.2, 1.2)]
    S["hermes"] = forge(23, 17, [
        L([hw], mat=P.MARBLE, bevel=1.2, mirror=True, base=0.66),
        L([ellipse(0, 0, 5.0, 4.0)], mat=P.GOLD, profile="round", spec=0.6),
        L([ellipse(0, 0.2, 2.6, 2.2)], emit=P.CYAN_E, glow=1.0),
        L([rect(-1.2, 3.6, 1.2, 5.4)], mat=P.STEEL, bevel=1),
    ], want_shadow=True, halo=3)
    # --- Sirène (émetteur en forme de lyre) ---------------------------------------------------
    S["siren"] = forge(23, 25, [
        L([arc(0, 0, 6.4, 8.4, -math.pi * 0.05, math.pi * 1.05)], mat=P.GOLD, bevel=1.5),
        L([rect(-9, -9, 9, -7.2)], mat=P.GOLD, bevel=1),
        L([line(-7.4, -8, -7.4, 0, 1.6), line(7.4, -8, 7.4, 0, 1.6)], mat=P.GOLD, bevel=1),
        L([line(x, -7.2, x, 4, 0.6) for x in (-3, -1, 1, 3)], emit=P.MAGENTA_E, glow=0.6),
        L([circle(0, 4.2, 3.4)], mat=P.MAGENTA, profile="round", spec=0.7),
        L([circle(-0.8, 3.4, 1.2)], emit=(255, 220, 250), glow=1.0),
    ], want_shadow=True, halo=3)
    # --- Hoplite (casque corinthien + bouclier) -------------------------------------------------
    S["hoplite"] = forge(21, 21, [
        L([sym([(0, -9), (2.8, -8.2), (4.6, -5), (5, -1), (4, 3), (2, 5), (0, 5.5)])], mat=P.BRONZE, bevel=2,
          spec=0.4),
        L([sym([(0, -10.5), (0.9, -9), (0.9, 2), (0, 3.5)])], mat=P.RED, profile="round"),
        L([[(0.6, 0.5), (2.6, -0.5), (2.2, 4), (0.6, 4.6)]], mat=P.EBONY, bevel=1, mirror=True),
        L([rect(0.8, 1.2, 2.0, 2.0)], emit=P.RED_E, glow=1.0, mirror=True),
    ], want_shadow=True, halo=2)
    S["aspis"] = forge(19, 19, [
        L([circle(0, 0, 8.0)], mat=P.GOLD, profile="round", spec=0.5),
        L([circle(0, 0, 6.2)], mat=P.BRONZE, bevel=1, base=0.55),
        L(polyline([(-3.4, 3.6), (0, -3.8), (3.4, 3.6)], 1.8), mat=P.RED, bevel=1),
    ], halo=0)
    # --- Trirème ------------------------------------------------------------------------------
    hull = sym([(0, 27), (3, 22), (6.2, 14), (7.4, 0), (6.8, -14), (5.2, -22), (3, -25.5), (0, -26.5)])
    oars = []
    for y in range(-18, 20, 5):
        oars.append(line(6.6, y, 11.5, y + 2.2, 1.0))
    S["trireme"] = forge(35, 61, [
        L(oars, mat=P.DARKSTEEL, bevel=1, mirror=True),
        L([hull], mat=P.BRONZE, bevel=2.5, spec=0.3),
        L([sym([(0, 23), (4.2, 12), (5.2, 0), (4.8, -13), (3.4, -21), (0, -23)])], mat=P.OBSIDIAN, bevel=1.5,
          base=0.6),
        L([sym([(0, 30), (1.6, 26.5), (2.8, 23.5), (0, 24.6)])], mat=P.GOLD, bevel=1),
        L([rect(-11.5, -7, 11.5, 1.5)], mat=P.MARBLE, bevel=1.2, base=0.66),
        L([rect(-11.5, -4.6, 11.5, -3.2), rect(-11.5, -1.8, 11.5, -0.6)], mat=P.RED, bevel=1, clip=True,
          cast=False),
        L([circle(0, -2.8, 2.6)], mat=P.GOLD, profile="round", spec=0.5),
        L([ellipse(3.0, 19.5, 1.4, 1.0)], mat=P.MARBLE, profile="round", mirror=True),
        L([circle(3.0, 19.6, 0.5)], emit=P.RED_E, glow=0.8, mirror=True),
        L([circle(11.8, y + 2.4, 0.7) for y in range(-18, 20, 5)], emit=(255, 150, 60), glow=0.8, mirror=True),
    ], want_shadow=True, halo=2)
    # --- Astéroïdes (pétrifiés) -------------------------------------------------------------------
    rng = np.random.default_rng(42)
    for size, r in (("s", 6.5), ("m", 10.5), ("l", 16.0)):
        variants = []
        for v in range(2):
            pts = []
            n = 14
            offs = rng.uniform(0.78, 1.08, n)
            for i in range(n):
                a = i * TAU / n
                pts.append((math.cos(a) * r * offs[i], math.sin(a) * r * offs[i]))
            craters = [circle(rng.uniform(-r * 0.5, r * 0.5), rng.uniform(-r * 0.5, r * 0.5),
                              rng.uniform(r * 0.12, r * 0.25)) for _ in range(3)]
            w = int(r * 2 + 6)
            frames = []
            for k in range(8):
                layers = [
                    L([pts], mat=P.STONE, profile="round", noise=0.07, spec=0.15, seed=v + k),
                    L(craters, mat=P.STONE, bevel=1.5, base=0.34, contrast=-0.6, clip=True, cast=False),
                ]
                frames.append(forge(w, w, layers, rot=k * TAU / 8, halo=0))
            variants.append(frames)
        S[f"rock_{size}"] = variants
    # --- Serpent (tête + anneaux) --------------------------------------------------------------
    head = [
        L([sym([(0, 8.6), (2.4, 6.8), (4.4, 2), (4.6, -2.6), (3.2, -6), (0, -7)])], mat=P.VERDIGRIS, bevel=2,
          spec=0.4),
        L([sym([(0, 7.6), (1.4, 5.6), (1.6, -1), (0, -3.4)])], mat=P.GOLD, bevel=1),
        L([[(1.4, 7.8), (2.2, 10.4), (1.0, 8.6)]], flat=(250, 244, 230), mirror=True),
        L([ellipse(2.8, 2.6, 1.2, 1.6, 0.4)], emit=P.RED_E, glow=1.2, mirror=True),
    ]
    S["serpent_head"] = forge_rot(21, 21, head, NTUR, want_shadow=False, halo=2)
    S["serpent_seg"] = forge(13, 13, [
        L([circle(0, 0, 5.2)], mat=P.VERDIGRIS, profile="round", spec=0.4),
        L([circle(0, 0, 3.2)], mat=P.GOLD, bevel=1, base=0.5),
        L([circle(0, 0, 1.2)], emit=(120, 255, 170), glow=0.8),
    ], halo=2)
    S["serpent_tail"] = forge(9, 9, [L([circle(0, 0, 3.2)], mat=P.VERDIGRIS, profile="round")], halo=0)
    # --- Ombre (spectre du Tartare) --------------------------------------------------------------
    S["shade"] = forge(21, 25, [
        L([sym([(0, -10), (3.6, -8.6), (5.4, -4), (6.6, 3), (8.4, 10.6), (5, 8.6), (3.8, 11.4), (1.6, 9),
                (0, 11.6)])], mat=P.ICE, bevel=2, base=0.5),
        L([sym([(0, -7.4), (2.5, -6.4), (3.2, -3), (2.4, 0.5), (0, 1.4)])], mat=P.EBONY, bevel=1),
        L([ellipse(0, -3.2, 2.0, 2.4)], mat=P.BONE, profile="round", base=0.64),
        L([circle(0.9, -3.4, 0.6)], emit=P.GREEN_E, glow=1.4, mirror=True),
    ], halo=3)
    # --- Érinye (furie ailée) --------------------------------------------------------------------
    bw = [(2, -3), (6, -6.5), (10.5, -6), (9, -3.5), (11, -2), (8.6, -0.5), (9.4, 1.8), (6, 0.6), (2.4, 2)]
    erinys_layers = [
        L([bw], mat=P.OBSIDIAN, bevel=1.2, mirror=True, rim=(P.RED_E, 0.6)),
        L(polyline([(2.5, -2), (6, -5.4), (9.8, -5.4)], 0.6) + polyline([(2.5, 0), (7.6, -1.2)], 0.6),
          emit=(255, 60, 60), glow=0.5, mirror=True),
        L([ellipse(0, 0, 2.6, 5.4)], mat=P.OBSIDIAN, profile="round", spec=0.4),
        L([ellipse(0, 3.6, 2.0, 2.2)], mat=P.BONE, profile="round", base=0.55),
        L(polyline([(0.8, 1.6), (2.6, -1), (3.6, 0.6)], 0.7) + polyline([(-0.4, 1.4), (-1.8, -1.8)], 0.7),
          mat=P.VERDIGRIS, bevel=1),
        L([circle(0.8, 3.8, 0.55)], emit=P.RED_E, glow=1.4, mirror=True),
    ]
    S["erinys"] = forge(25, 21, erinys_layers, halo=2)
    S["erinys_r"] = forge_rot(25, 25, erinys_layers, NTUR, halo=2)
    # --- Aigle de Zeus ----------------------------------------------------------------------------
    ew = [(2, -2.6), (6, -5.6), (11, -6.4), (14.2, -5), (12.4, -3.8), (13.8, -2.6), (11.6, -1.6), (12.6, 0),
          (9.6, 0), (10, 1.8), (6.4, 1), (2.4, 2.6)]
    eagle_layers = [
        L([ew], mat=P.GOLD, bevel=1.5, mirror=True, spec=0.4),
        L(polyline([(3, -1.6), (7, -3.6), (8.6, -2), (12.4, -4.4)], 0.7), emit=(170, 220, 255), glow=0.9,
          mirror=True),
        L([sym([(0, -9.8), (2.2, -7), (3.2, -1), (2.6, 3), (0, 4.4)])], mat=P.BRONZE, bevel=1.5),
        L([sym([(0, -11.5), (1.6, -9.6), (1.6, -7.4), (0, -8)])], mat=P.BRONZE, bevel=1),
        L([circle(0, 5.4, 2.4)], mat=P.MARBLE, profile="round", base=0.64),
        L([sym([(0, 10), (1.1, 6.6), (0, 6.8)])], mat=P.GOLD, bevel=1),
        L([circle(1.1, 5.2, 0.55)], emit=(120, 200, 255), glow=1.2, mirror=True),
    ]
    S["eagle"] = forge(33, 25, eagle_layers, want_shadow=True, halo=2)
    S["eagle_r"] = forge_rot(33, 33, eagle_layers, NTUR, want_shadow=True, halo=2)
    # --- Drone de lave -----------------------------------------------------------------------------
    S["lavadrone"] = forge(17, 17, [
        L([circle(0, 0, 6.6)], mat=P.OBSIDIAN, profile="round", noise=0.08, spec=0.3),
        L(polyline([(-4.5, -2), (-1.5, -0.6), (0.4, -3.8)], 0.9) + polyline([(-1.5, -0.6), (0.8, 2.4), (4, 1.6)], 0.9)
          + polyline([(0.8, 2.4), (-0.6, 5.2)], 0.8), emit=(255, 130, 40), glow=1.2),
        L([circle(0, 0, 1.6)], emit=(255, 220, 120), glow=1.0),
    ], halo=3)
    # --- Kentauros (char-archer) --------------------------------------------------------------------
    S["centaur_base"] = forge(23, 27, [
        L([rect(4.2, -10.5, 8.4, -3.5), rect(4.2, 3.5, 8.4, 10.5)], mat=P.DARKSTEEL, bevel=1.5, mirror=True),
        L([rect(4.6, -10, 8, -9.2), rect(4.6, -7, 8, -6.2), rect(4.6, 4, 8, 4.8), rect(4.6, 7, 8, 7.8)],
          mat=P.STEEL, bevel=1, mirror=True, clip=True, cast=False),
        L([sym([(0, -11.5), (4.2, -9.5), (5, 0), (4.2, 9.5), (0, 11.5)])], mat=P.BRONZE, bevel=2),
        L([sym([(0, 9), (2.6, 7), (2.8, 3), (0, 2)])], mat=P.OBSIDIAN, bevel=1),
    ], want_shadow=True, halo=0)
    ctur = [
        L([arc(0, 1.5, 5.4, 6.6, math.pi * 0.15, math.pi * 0.85)], mat=P.GOLD, bevel=1),
        L([line(-5.2, 3.6, 5.2, 3.6, 0.5)], emit=(255, 200, 120)),
        L([circle(0, -0.5, 3.4)], mat=P.MARBLE, profile="round", base=0.62),
        L([circle(0, 0.8, 1.4)], mat=P.BRONZE, profile="round"),
        L([rect(-0.5, 2.2, 0.5, 7.4)], mat=P.STEEL, bevel=1),
    ]
    S["centaur_tur"] = forge_rot(19, 19, ctur, NTUR, halo=0)
    # --- Œil de la Gorgone (tourelle de pierre) --------------------------------------------------------
    S["gorgon_eye"] = forge(19, 19, [
        L([circle(0, 0, 8.0)], mat=P.STONE, profile="round", noise=0.06),
        L([ellipse(0, 0.5, 5.8, 3.8)], mat=P.MARBLE, profile="round", base=0.6),
        L([circle(0, 0.6, 2.6)], emit=P.GREEN_E, glow=1.2),
        L([ellipse(0, 0.6, 0.7, 2.0)], flat=(10, 30, 20)),
        L(polyline([(-5, -5.5), (-2.4, -4.4), (0, -5.8), (2.4, -4.4), (5, -5.5)], 1.2), mat=P.VERDIGRIS, bevel=1),
    ], want_shadow=True, halo=3)
    # --- Pylône foudroyant (Olympe) ----------------------------------------------------------------------
    S["pylon"] = forge(17, 21, [
        L([rect(-7, 6.5, 7, 9.5)], mat=P.MARBLE, bevel=1.5, base=0.64),
        L([rect(-4.4, -5, 4.4, 7)], mat=P.MARBLE, bevel=1, base=0.6),
        L([rect(x - 0.4, -5, x + 0.4, 7) for x in (-2.8, -0.9, 0.9, 2.8)], mat=P.MARBLE, bevel=1, base=0.4,
          clip=True, cast=False),
        L([rect(-6.4, -8.5, 6.4, -5.2)], mat=P.GOLD, bevel=1),
        L([circle(0, -6.8, 2.6)], emit=(140, 200, 255), glow=1.4),
    ], want_shadow=True, halo=3)
    # --- Tourelle murale (Labyrinthe) -------------------------------------------------------------------
    S["wallgun_base"] = forge(19, 19, [
        L([rect(-8, -8, 8, 8)], mat=P.DARKSTEEL, bevel=2),
        L([rect(-6, -6, 6, 6)], mat=P.GOLD, bevel=1, sub=[rect(-4.6, -4.6, 4.6, 4.6)]),
    ], halo=0)
    wg = [
        L([rect(-1.2, 1, 1.2, 9)], mat=P.STEEL, bevel=1),
        L([circle(0, 0, 4.2)], mat=P.STEEL, profile="round", spec=0.5),
        L([circle(0, 0, 1.6)], emit=P.MAGENTA_E, glow=1.2),
    ]
    S["wallgun_tur"] = forge_rot(21, 21, wg, NTUR, halo=2)
    # --- Taureau d'airain (drone chargeur du labyrinthe) -------------------------------------------------
    S["bull"] = forge(23, 23, [
        L([arc(0, -1, 7.5, 9.5, math.pi * 0.62, math.pi * 1.1)], mat=P.MARBLE, bevel=1, base=0.66),
        L([arc(0, -1, 7.5, 9.5, -math.pi * 0.1, math.pi * 0.38)], mat=P.MARBLE, bevel=1, base=0.66),
        L([sym([(0, -7), (4.4, -5.6), (5.4, 0), (4, 5.4), (2, 8.6), (0, 9.2)])], mat=P.BRONZE, bevel=2, spec=0.4),
        L([ellipse(0, 6.6, 2.2, 1.6)], mat=P.BRONZE, bevel=1, base=0.4),
        L([circle(0.9, 6.8, 0.5)], flat=(20, 10, 10), mirror=True),
        L([ellipse(2.6, 1.2, 1.2, 0.8, 0.5)], emit=(255, 90, 40), glow=1.2, mirror=True),
    ], want_shadow=True, halo=2)
    # --- Forgeron automate (Héphaïstos) : marteau-pilon mobile ------------------------------------------
    S["hammerbot"] = forge(23, 23, [
        L([rect(-9, -2, 9, 2)], mat=P.DARKSTEEL, bevel=1),
        L([circle(0, 0, 6.4)], mat=P.BRONZE, profile="round", spec=0.4),
        L([rect(-3.6, 4, 3.6, 9.5)], mat=P.STEEL, bevel=1.5),
        L([rect(-3, 8.2, 3, 9.2)], emit=(255, 150, 60), glow=0.8),
        L([circle(0, -0.5, 2.0)], emit=(255, 120, 40), glow=1.2),
    ], want_shadow=True, halo=2)


def build_misc():
    """Petits éléments d'UI et d'effets."""
    # halo de hitbox du joueur
    S["core"] = forge(7, 7, [L([circle(0, 0, 2.2)], emit=(255, 255, 255), glow=1.0)], outline=(20, 200, 255),
                      halo=2)
    # marqueur de ciblage (verrouillage)
    S["lock"] = forge(15, 15, [L([arc(0, 0, 5.4, 6.6, a, a + 1.0) for a in (0.3, 1.87, 3.44, 5.01)],
                                 emit=(120, 255, 200), glow=0.6)], outline=None, halo=2)


BUILDERS = [build_player, build_player_shots, build_bullets, build_items, build_enemies, build_misc]


def build(progress=None):
    for i, b in enumerate(BUILDERS):
        b()
        if progress:
            progress((i + 1) / len(BUILDERS))
    return S
