"""Opérations bas niveau sur les surfaces : flou, dégradés, halos, teintes."""

import math

import numpy as np
import pygame


# --------------------------------------------------------------------------- flou

def _box_axis(a, r, axis):
    """Flou boîte de rayon r le long d'un axe (sommes cumulées, bords à zéro)."""
    n = a.shape[axis]
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad), axis=axis)
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)


def _np_blur(surface, radius):
    r = max(1, int(round(radius * 0.55)))
    rgb = pygame.surfarray.array3d(surface).astype(np.float32)
    for _ in range(3):
        rgb = _box_axis(_box_axis(rgb, r, 0), r, 1)
    out = pygame.Surface(surface.get_size(), surface.get_flags() & pygame.SRCALPHA, 32)
    pygame.surfarray.blit_array(out, np.clip(rgb, 0, 255).astype(np.uint8))
    if surface.get_flags() & pygame.SRCALPHA:
        alpha = pygame.surfarray.array_alpha(surface).astype(np.float32)
        for _ in range(3):
            alpha = _box_axis(_box_axis(alpha, r, 0), r, 1)
        pa = pygame.surfarray.pixels_alpha(out)
        pa[...] = np.clip(alpha, 0, 255).astype(np.uint8)
        del pa
    return out


def blur(surface, radius):
    """Flou gaussien : natif avec pygame-ce, sinon approximation numpy."""
    radius = int(radius)
    if radius < 1:
        return surface.copy()
    native = getattr(pygame.transform, "gaussian_blur", None)
    if native is not None:
        try:
            return native(surface, radius)
        except (ValueError, pygame.error):
            pass
    return _np_blur(surface, radius)


# --------------------------------------------------------------------------- dégradés

def _interp_stops(n, stops):
    ts = [s[0] for s in stops]
    t = np.linspace(0.0, 1.0, n)
    return np.stack([np.interp(t, ts, [s[1][i] for s in stops]) for i in range(3)], axis=-1)


def vgradient(w, h, stops, alpha=False):
    """Dégradé vertical. `stops` = [(t, (r, g, b)), ...] avec t croissant dans [0, 1]."""
    col = _interp_stops(h, stops)
    arr = np.ascontiguousarray(np.broadcast_to(col[None, :, :], (w, h, 3))).astype(np.uint8)
    surf = pygame.Surface((w, h), pygame.SRCALPHA if alpha else 0, 32)
    pygame.surfarray.blit_array(surf, arr)
    if alpha:
        surf.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MAX)
    return surf


def hgradient(w, h, stops):
    """Dégradé horizontal (surface RGB)."""
    col = _interp_stops(w, stops)
    arr = np.ascontiguousarray(np.broadcast_to(col[:, None, :], (w, h, 3))).astype(np.uint8)
    surf = pygame.Surface((w, h), 0, 32)
    pygame.surfarray.blit_array(surf, arr)
    return surf


def _hsv_array(hue, sat, val):
    """Conversion HSV -> RGB vectorisée (teinte : tableau numpy dans [0, 1[)."""
    hh = (hue % 1.0) * 6.0
    i = np.floor(hh).astype(int) % 6
    f = hh - np.floor(hh)
    p = val * (1 - sat)
    q = val * (1 - sat * f)
    t = val * (1 - sat * (1 - f))
    v = np.full_like(hue, val)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1) * 255.0


def prism_body(w, h, h0, span=0.9, sat=0.8):
    """Dégradé arc-en-ciel horizontal avec modelé vertical (brique « prisme »)."""
    cols = _hsv_array(h0 + np.arange(w) / w * span, sat, 1.0)            # (w, 3)
    t = np.linspace(0.0, 1.0, h)
    light = np.clip(1.0 - t / 0.5, 0, 1)[None, :, None]                    # vers le blanc
    dark = np.clip((t - 0.5) / 0.5, 0, 1)[None, :, None]                   # vers le noir
    base = cols[:, None, :]
    arr = base + (255.0 - base) * 0.3 * light
    arr = arr * (1.0 - 0.4 * dark)
    surf = pygame.Surface((w, h), pygame.SRCALPHA, 32)
    pygame.surfarray.blit_array(surf, np.clip(arr, 0, 255).astype(np.uint8))
    surf.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MAX)
    return surf


def rainbow_strip(w, h, sat=0.85, val=1.0, cycles=1.0):
    """Bande arc-en-ciel horizontale qui boucle parfaitement (utile pour les défilements)."""
    col = _hsv_array(np.arange(w) / w * cycles, sat, val)
    arr = np.ascontiguousarray(np.broadcast_to(col[:, None, :], (w, h, 3))).astype(np.uint8)
    surf = pygame.Surface((w, h), 0, 32)
    pygame.surfarray.blit_array(surf, arr)
    return surf


# --------------------------------------------------------------------------- halos

def radial_glow(radius, color, power=2.2, strength=1.0):
    """Halo radial RGB sur fond noir, à dessiner en BLEND_RGB_ADD."""
    radius = max(1, int(radius))
    size = radius * 2
    c = np.arange(size) - radius + 0.5
    d = np.sqrt(c[:, None] ** 2 + c[None, :] ** 2) / radius
    f = np.clip(1.0 - d, 0.0, 1.0) ** power * strength
    arr = np.clip(f[:, :, None] * np.array(color, dtype=np.float32)[None, None, :], 0, 255)
    surf = pygame.Surface((size, size), 0, 32)
    pygame.surfarray.blit_array(surf, arr.astype(np.uint8))
    return surf


def sparkle(radius, color, strength=1.0):
    """Étincelle en croix (reflet d'étoile), additive."""
    radius = max(2, int(radius))
    size = radius * 2 + 1
    c = np.arange(size) - radius
    ax = np.abs(c)[:, None] / radius
    ay = np.abs(c)[None, :] / radius
    thin = 1.3 / radius
    cross = np.maximum(
        np.clip(1 - ax, 0, 1) ** 2.5 * np.exp(-(ay / thin) ** 2),
        np.clip(1 - ay, 0, 1) ** 2.5 * np.exp(-(ax / thin) ** 2),
    )
    dist = np.sqrt(ax ** 2 + ay ** 2)
    core = np.clip(1 - dist * 2.2, 0, 1) ** 2
    f = np.clip(cross + core, 0, 1) * strength
    arr = np.clip(f[:, :, None] * np.array(color, dtype=np.float32)[None, None, :], 0, 255)
    surf = pygame.Surface((size, size), 0, 32)
    pygame.surfarray.blit_array(surf, arr.astype(np.uint8))
    return surf


def soft_disc(radius, color, alpha=255):
    """Disque aux bords doux avec transparence (fumée, ombres)."""
    radius = max(1, int(radius))
    size = radius * 2
    c = np.arange(size) - radius + 0.5
    d = np.sqrt(c[:, None] ** 2 + c[None, :] ** 2) / radius
    a = np.clip(1.0 - d, 0.0, 1.0) ** 1.5 * alpha
    surf = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    surf.fill((*color, 0))
    pa = pygame.surfarray.pixels_alpha(surf)
    pa[...] = a.astype(np.uint8)
    del pa
    return surf


# --------------------------------------------------------------------------- divers

def round_mask(surf, radius):
    """Découpe une surface SRCALPHA en rectangle aux coins arrondis."""
    mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA, 32)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return surf


def intensity(surf, k):
    """Copie d'une surface additive avec une intensité réduite (k dans [0, 1])."""
    out = surf.copy()
    v = max(0, min(255, int(255 * k)))
    out.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return out


def tint(surf, color):
    out = surf.copy()
    out.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return out


def thick_polyline(surf, color, pts, width, closed=False):
    """Trait épais d'épaisseur constante avec jointures arrondies."""
    if len(pts) == 1:
        pygame.draw.circle(surf, color, pts[0], width / 2)
        return
    seq = list(pts) + ([pts[0]] if closed else [])
    hw = width / 2.0
    for (x1, y1), (x2, y2) in zip(seq, seq[1:]):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        nx, ny = -dy / length * hw, dx / length * hw
        pygame.draw.polygon(surf, color, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                                          (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)])
    if hw >= 1.0:
        for p in seq:
            pygame.draw.circle(surf, color, p, hw)
