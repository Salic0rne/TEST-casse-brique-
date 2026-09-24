"""Petits utilitaires : maths, interpolations, couleurs."""

import colorsys
import math


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def approach(value, target, rate, dt):
    """Rapproche `value` de `target` de façon exponentielle (indépendant du framerate)."""
    return target + (value - target) * math.exp(-rate * dt)


# --------------------------------------------------------------------------- easing

def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t


def ease_in_out_sine(t):
    t = clamp(t, 0.0, 1.0)
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def ease_out_back(t, s=1.70158):
    t = clamp(t, 0.0, 1.0) - 1.0
    return t * t * ((s + 1.0) * t + s) + 1.0


def ease_out_elastic(t):
    t = clamp(t, 0.0, 1.0)
    if t in (0.0, 1.0):
        return t
    return 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * (2.0 * math.pi) / 3.0) + 1.0


def ease_out_bounce(t):
    t = clamp(t, 0.0, 1.0)
    n1, d1 = 7.5625, 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


# --------------------------------------------------------------------------- couleurs

def hsv(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s, 0.0, 1.0), clamp(v, 0.0, 1.0))
    return (int(r * 255), int(g * 255), int(b * 255))


def rgb_to_hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)


def mix(c1, c2, t):
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def scale(c, k):
    return (
        int(clamp(c[0] * k, 0, 255)),
        int(clamp(c[1] * k, 0, 255)),
        int(clamp(c[2] * k, 0, 255)),
    )


def lighten(c, k):
    """Mélange vers le blanc (k = 0 : inchangé, k = 1 : blanc)."""
    return mix(c, (255, 255, 255), clamp(k, 0.0, 1.0))


def darken(c, k):
    """Mélange vers le noir (k = 0 : inchangé, k = 1 : noir)."""
    return mix(c, (0, 0, 0), clamp(k, 0.0, 1.0))


def gradient3(c1, c2, c3, t):
    """Dégradé à trois couleurs, t dans [0, 1]."""
    if t < 0.5:
        return mix(c1, c2, t * 2.0)
    return mix(c2, c3, (t - 0.5) * 2.0)


def quantize(c, step=16):
    return (c[0] // step * step, c[1] // step * step, c[2] // step * step)
