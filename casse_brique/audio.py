"""Audio 100 % procédural : effets sonores synthétisés et musique synthwave générée au lancement.

Aucun fichier audio : tout est calculé avec numpy (oscillateurs anti-repliement
PolyBLEP, filtres FFT, réverbération par convolution, écho ping-pong,
compression « sidechain »). La musique est découpée en trois pistes jouées en
parallèle, dont le mixage évolue selon la situation (menu, jeu, pause...).
"""

import math
import threading
import time

import numpy as np
import pygame

SR = 44100


# =========================================================================== synthèse

def _n(dur):
    return max(1, int(round(SR * dur)))


def _t(n):
    return np.arange(n, dtype=np.float64) / SR


def midi(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _phase(freq, n):
    if np.isscalar(freq):
        return float(freq) * _t(n)
    f = np.asarray(freq, dtype=np.float64)
    return np.concatenate(([0.0], np.cumsum(f[:-1]))) / SR


def _dt(freq, n):
    return np.broadcast_to(np.abs(np.asarray(freq, dtype=np.float64)) / SR, (n,))


def _blep(t, dt):
    y = np.zeros_like(t)
    m = t < dt
    if m.any():
        x = t[m] / dt[m]
        y[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    if m.any():
        x = (t[m] - 1.0) / dt[m]
        y[m] = x * x + x + x + 1.0
    return y


def sine(freq, n, ph0=0.0):
    return np.sin(2 * np.pi * (_phase(freq, n) + ph0))


def tri(freq, n, ph0=0.0):
    t = (_phase(freq, n) + ph0) % 1.0
    return 4.0 * np.abs(t - 0.5) - 1.0


def saw(freq, n, ph0=0.0):
    t = (_phase(freq, n) + ph0) % 1.0
    return 2.0 * t - 1.0 - _blep(t, _dt(freq, n))


def pulse(freq, n, pw=0.5, ph0=0.0):
    t = (_phase(freq, n) + ph0) % 1.0
    dt = _dt(freq, n)
    y = np.where(t < pw, 1.0, -1.0)
    # on retire la composante continue (2 * pw - 1) pour éviter les « bosses » basses
    return y + _blep(t, dt) - _blep((t + 1.0 - pw) % 1.0, dt) - (2.0 * pw - 1.0)


def noise(n, rng):
    return rng.uniform(-1.0, 1.0, n)


def env_exp(n, tau, attack=0.002):
    e = np.exp(-_t(n) / tau)
    a = min(n, _n(attack))
    if a > 1:
        e[:a] *= np.linspace(0.0, 1.0, a)
    return e


def env_adsr(n, a, d, s, r):
    """Enveloppe ADSR sur n échantillons, relâchement inclus à la fin."""
    e = np.full(n, s, dtype=np.float64)
    na, nd, nr = _n(a), _n(d), _n(r)
    na = min(na, n)
    e[:na] = np.linspace(0.0, 1.0, na)
    if na < n:
        k = min(nd, n - na)
        e[na:na + k] = 1.0 + (s - 1.0) * (1.0 - np.exp(-np.arange(k) / max(1, nd) * 4.0))
    nr = min(nr, n)
    e[n - nr:] *= np.linspace(1.0, 0.0, nr)
    return e


def sweep(f0, f1, n, curve=1.0):
    t = np.linspace(0.0, 1.0, n) ** curve
    return f0 * (f1 / f0) ** t


def _fast_len(n):
    return 1 << int(math.ceil(math.log2(max(2, n))))


def filt(x, lo=None, hi=None, order=2, circular=False):
    """Filtre passe-bas / passe-haut / passe-bande (réponse de Butterworth, via FFT)."""
    n = x.shape[0]
    size = n if circular else _fast_len(n + 2048)
    freqs = np.fft.rfftfreq(size, 1.0 / SR)
    h = np.ones_like(freqs)
    if hi:
        h /= np.sqrt(1.0 + (freqs / hi) ** (2 * order))
    if lo:
        h /= np.sqrt(1.0 + (lo / np.maximum(freqs, 1e-3)) ** (2 * order))
    if x.ndim == 2:
        spec = np.fft.rfft(x, size, axis=0) * h[:, None]
        return np.fft.irfft(spec, size, axis=0)[:n]
    return np.fft.irfft(np.fft.rfft(x, size) * h, size)[:n]


def stereo(x, pan=0.0):
    a = (pan + 1.0) * math.pi / 4.0
    return np.stack([x * math.cos(a), x * math.sin(a)], axis=-1)


def fade(x, fin=0.001, fout=0.006):
    n = x.shape[0]
    a, b = min(n, _n(fin)), min(n, _n(fout))
    ramp_in = np.linspace(0.0, 1.0, a)
    ramp_out = np.linspace(1.0, 0.0, b)
    if x.ndim == 2:
        x[:a] *= ramp_in[:, None]
        x[n - b:] *= ramp_out[:, None]
    else:
        x[:a] *= ramp_in
        x[n - b:] *= ramp_out
    return x


def normalize(x, peak=0.8):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 1e-9 else x


def echo(x, delay, feedback=0.35, taps=4):
    n = x.shape[0]
    d = _n(delay)
    out = np.concatenate([x, np.zeros((d * taps,) + x.shape[1:])])
    g = 1.0
    for k in range(1, taps + 1):
        g *= feedback
        out[k * d:k * d + n] += x * g
    return out


def reverb_ir(dur, rt60, rng, bright=4500.0):
    n = _n(dur)
    tau = rt60 / 6.91
    env = np.exp(-_t(n) / tau)
    ir = np.stack([noise(n, rng), noise(n, rng)], axis=-1) * env[:, None]
    ir = filt(ir, hi=bright, order=1)
    ir[: _n(0.012)] *= 0.2
    return ir / np.sqrt(np.sum(ir ** 2) / 2.0)


def convolve(x, ir, circular_len=None):
    """Convolution stéréo par FFT (circulaire pour les boucles musicales)."""
    if x.ndim == 1:
        x = np.stack([x, x], axis=-1)
    if circular_len:
        size = circular_len
    else:
        size = _fast_len(x.shape[0] + ir.shape[0])
    out = np.fft.irfft(np.fft.rfft(x, size, axis=0) * np.fft.rfft(ir, size, axis=0), size, axis=0)
    return out if circular_len else out[: x.shape[0] + ir.shape[0] - 1]


# =========================================================================== effets sonores

PENTA = [0, 2, 4, 7, 9]


def _brick_note(i):
    m = 67 + PENTA[i % 5] + 12 * (i // 5)
    f = midi(m)
    n = _n(0.5)
    rng = np.random.default_rng(100 + i)
    x = (sine(f, n) * env_exp(n, 0.32)
         + 0.5 * sine(f * 2.0, n) * env_exp(n, 0.16)
         + 0.22 * sine(f * 3.01, n) * env_exp(n, 0.09)
         + 0.12 * sine(f * 4.23, n) * env_exp(n, 0.05)
         + 0.35 * tri(f, n) * env_exp(n, 0.05))
    crack = filt(noise(n, rng), lo=1500, hi=6000) * env_exp(n, 0.012) * 0.9
    return x + crack


def build_sfx():
    rng = np.random.default_rng(1234)
    sfx = {}

    n = _n(0.24)
    f = sweep(560, 240, n, 0.25)
    x = sine(f, n) * env_exp(n, 0.08) + 0.35 * filt(pulse(f / 2, n, 0.3), hi=2200) * env_exp(n, 0.05)
    x += filt(noise(n, rng), lo=2500) * env_exp(n, 0.004) * 0.6
    sfx["paddle"] = (x, 0.75)

    n = _n(0.09)
    x = sine(1850, n) * env_exp(n, 0.02) + 0.5 * sine(2780, n) * env_exp(n, 0.012)
    x += filt(noise(n, rng), lo=3000) * env_exp(n, 0.005) * 0.7
    sfx["wall"] = (x, 0.42)

    for i in range(16):
        sfx["brick%d" % i] = (_brick_note(i), 0.62)

    n = _n(0.2)
    x = sum(a * sine(1250 * r, n) * env_exp(n, d) for r, a, d in
            ((1.0, 1.0, 0.12), (2.76, 0.6, 0.07), (5.4, 0.35, 0.04), (8.93, 0.2, 0.025)))
    x += filt(noise(n, rng), lo=4000) * env_exp(n, 0.006) * 0.8
    sfx["hit"] = (x, 0.5)

    n = _n(0.8)
    x = sum(a * sine(310 * r, n) * env_exp(n, d) for r, a, d in
            ((1.0, 1.0, 0.5), (1.51, 0.7, 0.35), (2.02, 0.5, 0.3), (2.73, 0.45, 0.22),
             (3.43, 0.3, 0.18), (4.1, 0.25, 0.12), (5.6, 0.2, 0.08)))
    x *= 1.0 + 0.3 * sine(37, n)
    x += filt(noise(n, rng), lo=2000) * env_exp(n, 0.01) * 1.2
    sfx["metal"] = (x, 0.55)

    n = _n(1.4)
    nz = np.stack([noise(n, rng), noise(n, rng)], axis=-1)
    bright = filt(nz, hi=5000) * env_exp(n, 0.07)[:, None]
    dark = filt(nz, hi=380, order=3) * env_exp(n, 0.5, attack=0.004)[:, None] * 2.2
    sub = sine(sweep(120, 34, n, 0.4), n) * env_exp(n, 0.42) * 1.3
    crack = np.zeros(n)
    idx = rng.integers(0, int(n * 0.7), 90)
    crack[idx] = rng.uniform(-1, 1, 90) * np.exp(-idx / (SR * 0.35))
    crack = filt(crack, lo=800, hi=7000)
    x = bright + dark + stereo(sub + crack * 3.0)
    sfx["explosion"] = (np.tanh(normalize(x, 1.0) * 1.6), 0.9)

    n = _n(0.32)
    x = np.zeros(n)
    for k, m in enumerate((88, 91, 95, 100)):
        s = _n(0.035) * k
        seg = n - s
        x[s:] += sine(midi(m), seg) * env_exp(seg, 0.04) * (1.0 - k * 0.12)
    sfx["spawn"] = (echo(x, 0.07, 0.3, 2), 0.35)

    notes = (72, 76, 79, 84, 88, 91)
    step = _n(0.05)
    n = step * len(notes) + _n(0.25)
    x = np.zeros(n)
    for k, m in enumerate(notes):
        seg = n - k * step
        x[k * step:] += filt(pulse(midi(m), seg, 0.25), hi=5000) * env_exp(seg, 0.08) * 0.6
    x += sine(sweep(400, 1800, n, 0.8), n) * env_adsr(n, 0.02, 0.1, 0.5, 0.1) * 0.35
    sfx["powerup"] = (echo(x, 0.09, 0.3, 3), 0.6)

    notes = (79, 74, 70, 65)
    step = _n(0.07)
    n = step * len(notes) + _n(0.2)
    x = np.zeros(n)
    for k, m in enumerate(notes):
        seg = n - k * step
        fr = midi(m) * (1 + 0.02 * sine(9, seg))
        x[k * step:] += filt(saw(fr, seg) + saw(fr * 1.01, seg), hi=2500) * env_exp(seg, 0.09) * 0.4
    sfx["malus"] = (x, 0.55)

    n = _n(0.16)
    f = sweep(2400, 380, n, 0.45)
    x = pulse(f, n, 0.25) * env_exp(n, 0.07) + filt(noise(n, rng), lo=5000) * env_exp(n, 0.02) * 0.4
    sfx["laser"] = (filt(x, hi=7000), 0.3)

    n = _n(0.36)
    nz = filt(noise(n, rng), lo=500, hi=4000)
    x = nz * env_adsr(n, 0.12, 0.1, 0.6, 0.2) * 0.8 + sine(sweep(220, 900, n, 0.7), n) * env_exp(n, 0.12) * 0.6
    sfx["launch"] = (x, 0.45)

    n = _n(1.1)
    f = sweep(760, 70, n, 0.7) * (1 + 0.04 * sine(8, n))
    x = filt(saw(f, n) + saw(f * 1.02, n), hi=2600) * env_adsr(n, 0.01, 0.2, 0.8, 0.4) * 0.5
    x += sine(sweep(90, 30, n, 0.5), n) * env_exp(n, 0.4) * 0.9
    sfx["lose"] = (x, 0.75)

    notes = (72, 76, 79, 84)
    step = _n(0.085)
    n = step * 4 + _n(1.5)
    x = np.zeros((n, 2))
    for k, m in enumerate(notes):
        seg = n - k * step
        x[k * step:] += stereo(filt(pulse(midi(m), seg, 0.3), hi=4500) * env_exp(seg, 0.12) * 0.5,
                               -0.3 + 0.2 * k)
    s = step * 4
    seg = n - s
    for m, p in ((72, -0.6), (76, 0.6), (79, -0.3), (84, 0.3), (60, 0.0)):
        for det in (-0.08, 0.08):
            x[s:] += stereo(filt(saw(midi(m + det), seg), hi=3500)
                            * env_adsr(seg, 0.02, 0.3, 0.6, 0.8) * 0.16, p + det * 3)
    sfx["clear"] = (x + convolve(x, reverb_ir(2.0, 1.8, rng), None)[:n] * 0.3, 0.8)

    notes = ((69, 0.32), (65, 0.32), (62, 0.32), (57, 1.2))
    n = _n(sum(d for _, d in notes) + 0.6)
    x = np.zeros(n)
    pos = 0
    for m, d in notes:
        seg = n - pos
        fr = midi(m) * (1 + 0.012 * sine(5, seg))
        x[pos:] += filt(saw(fr, seg) + saw(fr * 1.006, seg) + 0.6 * sine(fr / 2, seg), hi=1800) \
            * env_adsr(seg, 0.02, 0.2, 0.6, 0.3) * np.exp(-_t(seg) / (d * 1.8)) * 0.4
        pos += _n(d)
    sfx["gameover"] = (x, 0.75)

    n = _n(0.05)
    sfx["move"] = (filt(pulse(880, n, 0.5), hi=5000) * env_exp(n, 0.02), 0.25)
    n = _n(0.16)
    x = np.zeros(n)
    h = _n(0.055)
    x[:h] = pulse(660, h, 0.5) * env_exp(h, 0.03)
    x[h:] = pulse(1320, n - h, 0.5) * env_exp(n - h, 0.05)
    sfx["select"] = (filt(x, hi=6000), 0.3)
    x2 = np.zeros(n)
    x2[:h] = pulse(990, h, 0.5) * env_exp(h, 0.03)
    x2[h:] = pulse(495, n - h, 0.5) * env_exp(n - h, 0.05)
    sfx["back"] = (filt(x2, hi=6000), 0.3)

    for lvl in range(4):
        base = 72 + lvl * 3
        n = _n(0.7)
        x = np.zeros((n, 2))
        for k, iv in enumerate((0, 4, 7, 12, 16)):
            s = _n(0.03) * k
            seg = n - s
            x[s:] += stereo((sine(midi(base + iv), seg) + 0.4 * tri(midi(base + iv) * 2, seg))
                            * env_exp(seg, 0.25) * 0.3, -0.6 + 0.3 * k)
        sfx["combo%d" % lvl] = (echo(x, 0.11, 0.35, 3), 0.55)

    notes = (76, 79, 88, 84, 86, 91)
    step = _n(0.075)
    n = step * len(notes) + _n(0.3)
    x = np.zeros(n)
    for k, m in enumerate(notes):
        seg = n - k * step
        gate = np.zeros(seg)
        gate[: step if k < len(notes) - 1 else seg] = 1.0
        x[k * step:] += filt(pulse(midi(m), seg, 0.5), hi=6000) * env_exp(seg, 0.2) * gate * 0.5
    sfx["life"] = (x, 0.6)

    n = _n(0.35)
    x = filt(saw(110, n), hi=3000) * (0.5 + 0.5 * pulse(32, n, 0.5)) * env_exp(n, 0.12)
    x += filt(noise(n, rng), lo=3000) * env_exp(n, 0.06) * 0.6
    sfx["shield"] = (x, 0.5)

    n = _n(0.18)
    x = sine(sweep(300, 700, n, 0.6), n) * env_exp(n, 0.06) + filt(noise(n, rng), hi=600) * env_exp(n, 0.02)
    sfx["catch"] = (x, 0.45)

    n = _n(0.6)
    x = np.zeros((n, 2))
    for _ in range(34):
        s = int(rng.integers(0, _n(0.25)))
        seg = n - s
        f = rng.uniform(2200, 7500)
        x[s:] += stereo(sine(f, seg) * env_exp(seg, rng.uniform(0.02, 0.09)) * rng.uniform(0.3, 1.0),
                        rng.uniform(-0.9, 0.9))
    x += stereo(filt(noise(n, rng), lo=4000) * env_exp(n, 0.05) * 1.5)
    sfx["prism"] = (x, 0.55)

    for i in range(8):
        n = _n(0.07)
        sfx["appear%d" % i] = (sine(midi(79 + PENTA[i % 5] + 12 * (i // 5)), n) * env_exp(n, 0.025), 0.16)

    n = _n(0.5)
    x = np.zeros(n)
    h = _n(0.13)
    x[:] += sine(midi(76), n) * env_exp(n, 0.1) * 0.6
    x[h:] += sine(midi(83), n - h) * env_exp(n - h, 0.18) * 0.7
    sfx["ready"] = (echo(x, 0.12, 0.25, 2), 0.4)

    notes = (72, 76, 79, 84, 79, 84, 88, 91)
    step = _n(0.08)
    n = step * len(notes) + _n(0.6)
    x = np.zeros(n)
    for k, m in enumerate(notes):
        seg = n - k * step
        x[k * step:] += (filt(pulse(midi(m), seg, 0.25), hi=5000) * 0.5 + sine(midi(m + 12), seg) * 0.2) \
            * env_exp(seg, 0.1 if k < len(notes) - 1 else 0.5)
    sfx["record"] = (echo(x, 0.1, 0.35, 3), 0.6)

    n = _n(0.7)
    pop = filt(noise(n, rng), hi=1500) * env_exp(n, 0.05) * 1.5
    crack = np.zeros(n)
    idx = rng.integers(_n(0.05), n - 10, 60)
    crack[idx] = rng.uniform(-1, 1, 60)
    crack = filt(crack, lo=2000) * np.exp(-_t(n) / 0.3)
    sfx["firework"] = (pop + crack * 2, 0.4)

    n = _n(0.55)
    nz = noise(n, rng)
    x = filt(nz, lo=300, hi=3000) * env_adsr(n, 0.25, 0.1, 0.7, 0.25)
    sfx["whoosh"] = (x, 0.35)

    n = _n(0.3)
    x = filt(noise(n, rng), hi=1400) * env_exp(n, 0.1) * 1.5 + sine(sweep(200, 60, n), n) * env_exp(n, 0.1)
    sfx["burn"] = (x, 0.45)

    return sfx


# =========================================================================== musique

BPM = 100
PROG = ["Am", "F", "C", "G", "Am", "F", "C", "G", "F", "G", "Em", "Am", "F", "G", "Am", "E"]
BASS_ROOT = {"Am": 45, "F": 41, "C": 48, "G": 43, "Em": 40, "E": 40}
PAD = {"Am": (57, 60, 64), "F": (57, 60, 65), "C": (55, 60, 64), "G": (55, 59, 62),
       "Em": (55, 59, 64), "E": (56, 59, 64)}
ARP = {"Am": (69, 72, 76, 81), "F": (69, 72, 77, 81), "C": (67, 72, 76, 79), "G": (67, 71, 74, 79),
       "Em": (67, 71, 76, 79), "E": (68, 71, 76, 80)}
# mélodie de la seconde moitié : (mesure, double-croche, durée en doubles-croches, note)
LEAD = [
    (8, 0, 4, 69), (8, 4, 4, 72), (8, 8, 8, 76),
    (9, 0, 4, 74), (9, 4, 4, 71), (9, 8, 8, 67),
    (10, 0, 6, 76), (10, 6, 2, 74), (10, 8, 4, 71), (10, 12, 4, 67),
    (11, 0, 16, 69),
    (12, 0, 4, 72), (12, 4, 4, 76), (12, 8, 4, 77), (12, 12, 4, 76),
    (13, 0, 4, 74), (13, 4, 4, 79), (13, 8, 8, 74),
    (14, 0, 4, 76), (14, 4, 4, 72), (14, 8, 8, 69),
    (15, 0, 8, 68), (15, 8, 4, 71), (15, 12, 4, 76),
]
STEMS = ("base", "drums", "lead")


def generate_music(seed=7):
    """Retourne (pistes {nom: tableau (N, 2)}, spectre (images, bandes), durée d'une double-croche)."""
    rng = np.random.default_rng(seed)
    step = int(round(SR * 60.0 / BPM / 4.0))
    bar = step * 16
    total = bar * len(PROG)

    def place(buf, start, sig):
        start %= total
        n = sig.shape[0]
        end = start + n
        if end <= total:
            buf[start:end] += sig
        else:
            k = total - start
            buf[start:] += sig[:k]
            rest = sig[k:]
            while rest.shape[0] > 0:
                m = min(total, rest.shape[0])
                buf[:m] += rest[:m]
                rest = rest[m:]

    # -- basse
    bass_cache = {}

    def bass_note(m):
        if m not in bass_cache:
            n = step * 2
            f = midi(m)
            raw = saw(f, n) * 0.8 + sine(f / 2, n) * 0.6
            env = env_adsr(n, 0.004, 0.15, 0.55, 0.03)
            x = filt(raw, hi=520, order=2) + filt(raw, hi=2600) * env_exp(n, 0.045) * 0.7
            bass_cache[m] = x * env
        return bass_cache[m]

    bass = np.zeros(total)
    for b, ch in enumerate(PROG):
        root = BASS_ROOT[ch]
        for e in range(8):
            vel = 1.0 if e % 2 == 0 else 0.78
            place(bass, b * bar + e * 2 * step, bass_note(root + (12 if e % 2 else 0)) * vel)

    # -- nappes
    pad_cache = {}

    def pad_chord(ch):
        if ch not in pad_cache:
            n = bar + _n(0.6)
            x = np.zeros((n, 2))
            env = env_adsr(n, 0.35, 0.5, 0.85, 0.6)
            for m in PAD[ch]:
                for det, pan in ((-0.09, -0.7), (0.09, 0.7)):
                    x += stereo(saw(midi(m + det), n, ph0=rng.random()) * env, pan)
            x += stereo(sine(midi(PAD[ch][0] - 12), n) * env * 0.8)
            pad_cache[ch] = filt(x, hi=1900, order=2) * 0.16
        return pad_cache[ch]

    pads = np.zeros((total, 2))
    for b, ch in enumerate(PROG):
        place(pads, b * bar, pad_chord(ch))

    # -- arpège
    arp_cache = {}

    def arp_note(m):
        if m not in arp_cache:
            n = _n(0.16)
            x = filt(pulse(midi(m), n, 0.3), hi=3600) * env_exp(n, 0.06)
            arp_cache[m] = fade(x)
        return arp_cache[m]

    arp = np.zeros(total)
    for b, ch in enumerate(PROG):
        tones = ARP[ch]
        vol = 0.55 if b < 8 else 0.33
        for s in range(16):
            m = tones[s % 4] + (12 if (s // 4) % 4 == 3 and s % 4 == 3 else 0)
            accent = 1.0 if s % 4 == 0 else 0.72
            place(arp, b * bar + s * step, arp_note(m) * vol * accent)

    # -- mélodie
    lead = np.zeros(total)
    for b, s, d, m in LEAD:
        n = step * d + _n(0.18)
        f = midi(m)
        t = _t(n)
        vib = 1.0 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.18) / 0.2, 0, 1)
        raw = saw(f * vib, n) * 0.6 + pulse(f * vib * 1.003, n, 0.4) * 0.4
        x = filt(raw, hi=2400) * env_adsr(n, 0.015, 0.12, 0.72, 0.16) * 0.42
        place(lead, b * bar + s * step, x)

    # -- batterie
    n = _n(0.42)
    t = _t(n)
    kick = sine(45 + 120 * np.exp(-t / 0.032), n) * np.exp(-t / 0.26)
    kick += filt(noise(n, rng), lo=3000) * env_exp(n, 0.003) * 0.4
    kick = np.tanh(kick * 1.6) * 0.85
    n = _n(0.4)
    snare = sine(185, n) * env_exp(n, 0.07) * 0.5 + filt(noise(n, rng), lo=1400, hi=9000) * env_exp(n, 0.13)
    n = _n(0.09)
    hat = filt(noise(n, rng), lo=7500) * env_exp(n, 0.022) * 0.45
    n = _n(0.45)
    ohat = filt(noise(n, rng), lo=6500) * env_exp(n, 0.17) * 0.32
    n = _n(2.2)
    crash = filt(noise(n, rng), lo=4200) * env_exp(n, 0.85) * 0.34
    crash += filt(sum(pulse(f, n, 0.5) for f in (540, 800, 1050, 1340, 1680, 2100)), lo=5000) \
        * env_exp(n, 0.6) * 0.05

    def tom(f0):
        nn = _n(0.35)
        return sine(sweep(f0, f0 * 0.55, nn, 0.6), nn) * env_exp(nn, 0.2) * 0.8 \
            + filt(noise(nn, rng), hi=1500) * env_exp(nn, 0.03) * 0.3

    drums = np.zeros((total, 2))
    snares = np.zeros(total)
    for b in range(len(PROG)):
        second = b >= 8
        for s in range(16):
            pos = b * bar + s * step
            if s % 4 == 0 or (second and s == 14 and b % 2 == 1):
                place(drums, pos, stereo(kick))
            if s in (4, 12) and not (b == 15 and s == 12):
                place(snares, pos, snare)
            if s % 4 == 2:
                place(drums, pos, stereo(hat, 0.25))
            elif second and s % 2 == 1:
                place(drums, pos, stereo(hat * 0.45, 0.35))
            if s == 14 and b % 2 == 1:
                place(drums, pos, stereo(ohat, -0.2))
        if b in (0, 8):
            place(drums, b * bar, stereo(crash, -0.15))
    for k, f0 in enumerate((210, 175, 145, 120)):
        place(drums, 15 * bar + (12 + k) * step, stereo(tom(f0), 0.5 - k * 0.33))

    ir = reverb_ir(2.4, 2.2, rng)
    ir_short = reverb_ir(1.0, 0.9, rng, bright=6000)
    drums += stereo(snares, 0.05)
    drums += convolve(snares, ir_short, total) * 0.35

    # -- compression « sidechain » au rythme de la grosse caisse
    beat = step * 4
    tb = np.arange(beat) / SR
    duck = np.tile(1.0 - np.exp(-tb / 0.11), len(PROG) * 4)

    def side(x, depth):
        g = 1.0 - depth * (1.0 - duck)
        return x * (g[:, None] if x.ndim == 2 else g)

    # -- écho ping-pong de l'arpège et de la mélodie
    lead_dry = arp + lead
    lead_st = stereo(lead_dry)
    d = step * 3
    for k, (g, pan) in enumerate(((0.42, 0.9), (0.28, -0.9), (0.17, 0.9), (0.1, -0.9))):
        lead_st += stereo(np.roll(lead_dry, d * (k + 1)) * g, pan)

    base = side(pads, 0.6) + stereo(side(bass, 0.4) * 0.55)
    base += convolve(side(pads, 0.6), ir, total) * 0.35
    lead_st = side(lead_st, 0.35)
    lead_st += convolve(lead_st, ir, total) * 0.28
    base = filt(base, lo=28, order=1, circular=True)

    stems = {"base": base, "drums": drums, "lead": lead_st}
    mix_all = base + drums + lead_st
    k = 0.92 / max(1e-9, np.max(np.abs(mix_all)))
    for name in stems:
        stems[name] = (stems[name] * k).astype(np.float32)

    spectrum = _spectrum((mix_all * k).mean(axis=1))
    return stems, spectrum, step


def _spectrum(mono, fps=30, bands=14, size=2048):
    hop = int(SR / fps)
    frames = mono.shape[0] // hop
    pad = np.concatenate([mono, mono[:size]]).astype(np.float32)
    idx = np.arange(frames)[:, None] * hop + np.arange(size)[None, :]
    win = np.hanning(size).astype(np.float32)
    spec = np.abs(np.fft.rfft(pad[idx] * win, axis=1))
    freqs = np.fft.rfftfreq(size, 1.0 / SR)
    edges = np.geomspace(45, 11000, bands + 1)
    out = np.zeros((frames, bands), dtype=np.float32)
    for b in range(bands):
        m = (freqs >= edges[b]) & (freqs < edges[b + 1])
        out[:, b] = spec[:, m].mean(axis=1)
    out = 20 * np.log10(out + 1e-6)
    lo, hi = np.percentile(out, 8), np.percentile(out, 99.5)
    return np.clip((out - lo) / (hi - lo), 0, 1).astype(np.float32)


# =========================================================================== lecture

MIX_MODES = {
    "menu": {"base": 1.0, "drums": 0.55, "lead": 1.0},
    "intro": {"base": 1.0, "drums": 0.35, "lead": 0.9},
    "game": {"base": 1.0, "drums": 1.0, "lead": 1.0},
    "pause": {"base": 0.55, "drums": 0.0, "lead": 0.15},
    "gameover": {"base": 0.8, "drums": 0.0, "lead": 0.35},
    "silent": {"base": 0.0, "drums": 0.0, "lead": 0.0},
}


class Audio:
    def __init__(self, sfx_volume=0.8, music_volume=0.6):
        global SR
        self.sfx_volume = sfx_volume
        self.music_volume = music_volume
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self._last = {}
        self._fmt = None
        self._channels = 2
        self.music_ready = False
        self._music_result = None
        self._music_error = None
        self._music_channels = []
        self._music_sounds = []
        self._music_start = 0.0
        self._mix_target = dict(MIX_MODES["menu"])
        self._mix = {k: 0.0 for k in STEMS}
        self.spectrum = None
        self.step = 60.0 / BPM / 4.0
        self.loop_len = self.step * 16 * len(PROG)
        self._clock0 = time.perf_counter()
        if not self.enabled:
            return
        freq, fmt, channels = pygame.mixer.get_init()
        SR = freq
        self._fmt = fmt
        self._channels = channels
        pygame.mixer.set_num_channels(40)
        pygame.mixer.set_reserved(len(STEMS))
        for name, (x, peak) in build_sfx().items():
            self.sounds[name] = self._make_sound(fade(normalize(x, peak)))
        threading.Thread(target=self._music_worker, daemon=True).start()

    # ------------------------------------------------------------------ conversion
    def _make_sound(self, x):
        if x.ndim == 1:
            x = np.stack([x, x], axis=-1)
        if self._channels == 1:
            x = x.mean(axis=1)
        elif self._channels > 2:
            x = np.concatenate([x, np.zeros((x.shape[0], self._channels - 2))], axis=1)
        x = np.clip(x, -1.0, 1.0)
        fmt = self._fmt
        if fmt == -16:
            arr = (x * 32767).astype(np.int16)
        elif fmt == 16:
            arr = (x * 32767 + 32768).astype(np.uint16)
        elif fmt == -8:
            arr = (x * 127).astype(np.int8)
        elif fmt == 8:
            arr = (x * 127 + 128).astype(np.uint8)
        elif fmt == -32:
            arr = (x * 2147483647).astype(np.int32)
        else:
            arr = x.astype(np.float32)
        return pygame.sndarray.make_sound(np.ascontiguousarray(arr))

    # ------------------------------------------------------------------ effets
    def play(self, name, vol=1.0, pan=0.0, min_gap=0.03):
        if not self.enabled or self.sfx_volume <= 0:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = time.perf_counter()
        if now - self._last.get(name, 0.0) < min_gap:
            return
        self._last[name] = now
        # Sound.play() respecte les canaux réservés à la musique (contrairement à find_channel)
        ch = snd.play()
        if ch is None:
            return
        v = max(0.0, min(1.0, vol * self.sfx_volume))
        pan = max(-1.0, min(1.0, pan))
        ch.set_volume(v * min(1.0, 1.0 - pan), v * min(1.0, 1.0 + pan))

    def brick(self, index, pan=0.0, vol=1.0):
        self.play("brick%d" % max(0, min(15, index)), vol, pan, min_gap=0.02)

    # ------------------------------------------------------------------ musique
    def _music_worker(self):
        try:
            self._music_result = generate_music()
        except Exception as exc:  # la musique est facultative : le jeu reste jouable
            self._music_error = exc

    def set_music_mode(self, mode):
        self._mix_target = dict(MIX_MODES.get(mode, MIX_MODES["game"]))

    def music_time(self):
        """Position (s) dans la boucle musicale, ou horloge virtuelle si pas de musique."""
        if self.music_ready:
            return (time.perf_counter() - self._music_start) % self.loop_len
        return (time.perf_counter() - self._clock0) % self.loop_len

    def beat_pulse(self):
        """1 sur chaque temps puis décroissance rapide : pour faire pulser le décor."""
        beat = self.step * 4
        tb = self.music_time() % beat
        return math.exp(-tb / 0.16)

    def spectrum_frame(self):
        if self.spectrum is None:
            return None
        i = int(self.music_time() * 30) % self.spectrum.shape[0]
        return self.spectrum[i]

    def update(self, dt):
        if not self.enabled:
            return
        if not self.music_ready and self._music_result is not None:
            stems, spectrum, step = self._music_result
            self._music_result = None
            self._music_sounds = [self._make_sound(stems[name]) for name in STEMS]
            self.spectrum = spectrum
            self.step = step / SR
            self.loop_len = self.step * 16 * len(PROG)
            self._music_channels = [pygame.mixer.Channel(i) for i in range(len(STEMS))]
            for ch in self._music_channels:
                ch.set_volume(0.0)
            for ch, snd in zip(self._music_channels, self._music_sounds):
                ch.play(snd, loops=-1)
            self._music_start = time.perf_counter()
            self.music_ready = True
        if self.music_ready:
            k = 1.0 - math.exp(-dt * 3.0)
            for i, name in enumerate(STEMS):
                self._mix[name] += (self._mix_target[name] - self._mix[name]) * k
                self._music_channels[i].set_volume(max(0.0, self._mix[name] * self.music_volume))
