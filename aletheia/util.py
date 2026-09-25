"""Petits utilitaires mathématiques."""
import math
import random

TAU = math.pi * 2


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def approach(v, target, step):
    if v < target:
        return min(v + step, target)
    return max(v - step, target)


def sign(v):
    return (v > 0) - (v < 0)


def angle_to(x1, y1, x2, y2):
    return math.atan2(y2 - y1, x2 - x1)


def dist2(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    return dx * dx + dy * dy


def vec(angle, speed):
    return math.cos(angle) * speed, math.sin(angle) * speed


def angle_diff(a, b):
    """Différence signée b - a ramenée dans [-pi, pi]."""
    d = (b - a) % TAU
    if d > math.pi:
        d -= TAU
    return d


def lerp_color(c1, c2, t):
    return (int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t))


def scale_color(c, k):
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def gradient(stops, t):
    """stops: liste de (t, couleur) triée ; renvoie la couleur interpolée."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        t1, c1 = stops[i]
        if t <= t1:
            t0, c0 = stops[i - 1]
            return lerp_color(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 1.0)
    return stops[-1][1]


# --- Easing ---------------------------------------------------------------
def ease_out_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in_cubic(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * t


def ease_in_out(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ease_out_back(t, s=1.7):
    t = clamp(t, 0.0, 1.0) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_elastic(t):
    t = clamp(t, 0.0, 1.0)
    if t in (0.0, 1.0):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (TAU / 3)) + 1


def rand_range(a, b):
    return a + random.random() * (b - a)


def chance(p):
    return random.random() < p


def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
            a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def catmull(points, t):
    """Spline Catmull-Rom passant par les points, t dans [0,1]."""
    n = len(points) - 1
    if n < 1:
        return points[0]
    t = clamp(t, 0.0, 1.0) * n
    i = min(int(t), n - 1)
    f = t - i
    p0 = points[max(i - 1, 0)]
    p1 = points[i]
    p2 = points[i + 1]
    p3 = points[min(i + 2, n)]
    f2, f3 = f * f, f * f * f
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * f + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * f2
               + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * f3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * f + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * f2
               + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * f3)
    return x, y
