"""Bruitages procéduraux. Chaque fonction renvoie un signal mono ou un couple (L, R)."""
import math

import numpy as np

from .synth import (SR, ns, tarr, osc, env_exp, env_adsr, lowpass, highpass, bandpass, sweep_lowpass, pluck,
                    fm, additive, crackle, softclip, make_ir, reverb_stereo, echo, expdrop, sweep, rng, peaks,
                    formant, note_freq, fade_edges, vibrato)

REG = {}
_IR = {}


def sfx(name):
    def deco(fn):
        REG[name] = fn
        return fn
    return deco


def ir(kind="hall"):
    if kind not in _IR:
        if kind == "hall":
            _IR[kind] = make_ir(2.2, 0.55, seed=11, damp=4800)
        else:
            _IR[kind] = make_ir(0.9, 0.2, seed=5, damp=7000)
    return _IR[kind]


def wet(x, amount=0.3, kind="hall"):
    L, R = reverb_stereo(x, x, ir(kind))
    n = len(L)
    dry = np.zeros(n)
    dry[:len(x)] = x
    return dry + L * amount, dry + R * amount


def boom(n, f0=110, f1=38, rate=18, decay=0.25):
    return osc("sine", expdrop(f0, f1, n, rate), n) * env_exp(n, decay)


def noise_burst(n, fc0, fc1, decay, seed=None, hp=None):
    x = osc("noise", 0, n, seed=seed)
    x = sweep_lowpass(x, np.geomspace(fc0, fc1, n))
    if hp:
        x = highpass(x, hp)
    return x * env_exp(n, decay)


# ---------------------------------------------------------------------------
# Tirs du joueur
# ---------------------------------------------------------------------------
@sfx("shot")
def _shot():
    n = ns(0.075)
    f = expdrop(2400, 520, n, 45)
    y = osc("pulse", f, n, duty=0.25) * env_exp(n, 0.026) * 0.5
    y += osc("noise", 0, n, seed=1) * env_exp(n, 0.005) * 0.35
    return lowpass(y, 5200) * 0.55


@sfx("shot2")
def _shot2():
    n = ns(0.07)
    f = expdrop(2000, 480, n, 50)
    y = osc("pulse", f, n, duty=0.3) * env_exp(n, 0.024) * 0.5
    y += osc("noise", 0, n, seed=2) * env_exp(n, 0.004) * 0.35
    return lowpass(y, 5000) * 0.55


@sfx("zap")
def _zap():
    n = ns(0.2)
    x = osc("noise", 0, n, seed=3) * crackle(n, 520, seed=4)
    x = bandpass(x, 1400, 7000) * 1.6
    x += osc("saw", expdrop(3200, 900, n, 20), n) * 0.18
    x *= env_exp(n, 0.07)
    return softclip(x, 1.5) * 0.6


@sfx("zap_beam")
def _zap_beam():
    # boucle de 0,5 s pour la lance de foudre
    n = ns(0.5)
    x = osc("noise", 0, n, seed=5) * (0.35 + crackle(n, 300, seed=6))
    x = bandpass(x, 900, 6500)
    hum = osc("saw", 100, n) * 0.25 + osc("saw", 150, n) * 0.15
    x = x * 0.9 + lowpass(hum, 1500)
    return fade_edges(softclip(x, 1.3) * 0.5, 0.004, 0.004)


@sfx("laser_loop")
def _laser_loop():
    n = ns(0.5)
    t = tarr(n)
    y = osc("saw", 220, n) * 0.4 + osc("saw", 222, n) * 0.4 + osc("square", 110, n) * 0.25
    y *= 0.8 + 0.2 * np.sin(2 * math.pi * 30 * t)
    y = lowpass(y, 2600)
    y += bandpass(osc("noise", 0, n, seed=7), 3000, 8000) * 0.12
    return fade_edges(y * 0.45, 0.003, 0.003)


@sfx("laser")
def _laser():
    n = ns(0.16)
    f = expdrop(3600, 700, n, 22)
    y = osc("saw", f, n) * 0.5 + osc("square", f * 0.5, n, duty=0.3) * 0.3
    y = lowpass(y, 6000) * env_exp(n, 0.06)
    return y * 0.55


@sfx("arrow")
def _arrow():
    n = ns(0.16)
    x = osc("noise", 0, n, seed=8)
    x = sweep_lowpass(x, np.geomspace(1500, 9000, n)) - lowpass(x, 900)
    e = np.minimum(tarr(n) / 0.02, 1) * env_exp(n, 0.05)
    tw = pluck(740, 0.16, bright=0.9, decay=0.99, seed=9) * 0.5
    return (x * e * 0.8 + tw * env_exp(n, 0.08)) * 0.55


@sfx("wave")
def _wave():
    n = ns(0.26)
    t = tarr(n)
    f = sweep(280, 900, n) * (1 + 0.06 * np.sin(2 * math.pi * 26 * t))
    y = osc("sine", f, n) * env_adsr(n, 0.01, 0.1, 0.5, 0.1)
    y += osc("tri", f * 2, n) * 0.2 * env_exp(n, 0.06)
    b = np.zeros(n)
    r = rng(10)
    for _ in range(5):
        st = int(r.random() * n * 0.7)
        bn = ns(0.03)
        fb = 1200 + r.random() * 1800
        seg = osc("sine", sweep(fb, fb * 1.8, bn), bn) * env_exp(bn, 0.01)
        b[st:st + bn] += seg[:len(b[st:st + bn])] * 0.25
    return (y + b) * 0.5


@sfx("clang")
def _clang():
    n = ns(0.45)
    e = env_exp(n, 0.12)
    y = fm(620, 1.41, 3.0, n, env_exp(n, 0.05)) * e
    y += fm(1310, 2.76, 1.5, n, env_exp(n, 0.03)) * env_exp(n, 0.07) * 0.5
    y += osc("noise", 0, n, seed=11) * env_exp(n, 0.006) * 0.4
    return highpass(y, 300) * 0.5


@sfx("block")
def _block():
    n = ns(0.12)
    y = fm(1800, 1.5, 2.0, n, env_exp(n, 0.02)) * env_exp(n, 0.035)
    return highpass(y, 800) * 0.35


@sfx("flame_loop")
def _flame_loop():
    n = ns(0.6)
    x = osc("noise", 0, n, seed=12)
    body = lowpass(x, 900) * 2.2
    hiss = bandpass(x, 2500, 7000) * 0.35
    t = tarr(n)
    am = 0.75 + 0.25 * np.sin(2 * math.pi * 10 * t) * np.sin(2 * math.pi * 3.33 * t)
    y = (body + hiss) * am
    return fade_edges(softclip(y, 1.2) * 0.4, 0.004, 0.004)


@sfx("mortar")
def _mortar():
    n = ns(0.2)
    y = boom(n, 180, 60, 16, 0.08) * 0.9
    y += noise_burst(n, 3000, 400, 0.04, seed=13) * 0.5
    return y * 0.55


@sfx("fire_burst")
def _fire_burst():
    n = ns(0.35)
    y = noise_burst(n, 2500, 300, 0.12, seed=14)
    y += boom(n, 90, 40, 10, 0.12) * 0.6
    return softclip(y, 1.4) * 0.5


# ---------------------------------------------------------------------------
# Ennemis
# ---------------------------------------------------------------------------
@sfx("eshot")
def _eshot():
    n = ns(0.09)
    f = expdrop(1100, 320, n, 30)
    y = osc("square", f, n, duty=0.5) * env_exp(n, 0.035)
    return lowpass(y, 3000) * 0.28


@sfx("eshot2")
def _eshot2():
    n = ns(0.07)
    f = sweep(420, 900, n)
    y = osc("sine", f, n) * env_exp(n, 0.03)
    y += osc("tri", f * 1.5, n) * env_exp(n, 0.015) * 0.4
    return y * 0.33


@sfx("eshot_big")
def _eshot_big():
    n = ns(0.16)
    y = osc("tri", expdrop(300, 110, n, 18), n) * env_exp(n, 0.07)
    y += noise_burst(n, 2000, 300, 0.03, seed=15) * 0.4
    return y * 0.45


@sfx("charge")
def _charge():
    n = ns(0.9)
    t = tarr(n)
    f = 180 * (8.0 ** (t / 0.9))
    y = osc("saw", f, n) * 0.4 + osc("sine", f * 1.5, n) * 0.3
    y *= 0.6 + 0.4 * np.sin(2 * math.pi * (6 + 30 * t) * t)
    y = lowpass(y, 4500) * np.minimum(t / 0.6, 1.0) ** 1.5
    y = fade_edges(y, 0.01, 0.03)
    return y * 0.4


@sfx("beam")
def _beam():
    n = ns(0.9)
    t = tarr(n)
    y = osc("saw", 80, n) * 0.5 + osc("saw", 121, n) * 0.35 + osc("square", 40, n) * 0.3
    y += bandpass(osc("noise", 0, n, seed=16), 400, 4000) * 0.4
    y = softclip(lowpass(y, 1800) * 1.8, 1.5)
    e = np.minimum(t / 0.02, 1) * np.where(t > 0.6, np.exp(-(t - 0.6) / 0.1), 1.0)
    return y * e * 0.45


@sfx("roar")
def _roar():
    n = ns(1.6)
    t = tarr(n)
    f = 55 * (1 + 0.25 * np.sin(math.pi * t / 1.6)) * (1 + 0.02 * np.sin(2 * math.pi * 7 * t))
    y = osc("saw", f, n) * 0.5 + osc("saw", f * 1.498, n) * 0.4 + osc("square", f * 0.5, n) * 0.3
    y += bandpass(osc("noise", 0, n, seed=17), 300, 2500) * 0.5
    y = softclip(lowpass(y, 1400) * 2.0, 2.0)
    e = np.minimum(t / 0.3, 1) * np.exp(-np.maximum(t - 0.9, 0) / 0.25)
    L, R = wet(y * e * 0.5, 0.35)
    return L, R


@sfx("splash")
def _splash():
    n = ns(0.9)
    x = osc("noise", 0, n, seed=18)
    y = bandpass(x, 500, 4000) * env_adsr(n, 0.02, 0.2, 0.3, 0.5)
    y += boom(n, 70, 35, 6, 0.3) * 0.6
    return wet(y * 0.5, 0.25)


# ---------------------------------------------------------------------------
# Impacts & explosions
# ---------------------------------------------------------------------------
@sfx("hit")
def _hit():
    n = ns(0.035)
    y = highpass(osc("noise", 0, n, seed=19), 2500) * env_exp(n, 0.008)
    y += osc("sine", 2200, n) * env_exp(n, 0.01) * 0.3
    return y * 0.22


@sfx("tink")
def _tink():
    n = ns(0.12)
    y = fm(2400, 2.76, 1.2, n, env_exp(n, 0.02)) * env_exp(n, 0.03)
    return y * 0.22


@sfx("explo_s")
def _explo_s():
    n = ns(0.5)
    y = noise_burst(n, 5000, 350, 0.11, seed=20)
    y += boom(n, 140, 45, 16, 0.08) * 0.8
    y += osc("noise", 0, n, seed=21) * (crackle(n, 60, seed=22) > 0.5) * env_exp(n, 0.1) * 0.15
    return softclip(y * 1.2, 1.3) * 0.55


@sfx("explo_m")
def _explo_m():
    n = ns(0.95)
    y = noise_burst(n, 4200, 220, 0.2, seed=23) * 1.1
    y += boom(n, 120, 32, 10, 0.16) * 1.0
    cr = osc("noise", 0, n, seed=24) * (crackle(n, 45, seed=25) > 0.55) * env_exp(n, 0.25) * 0.2
    y += highpass(cr, 1500)
    L, R = wet(softclip(y * 1.2, 1.4) * 0.6, 0.18, "room")
    return L, R


@sfx("explo_l")
def _explo_l():
    n = ns(2.0)
    y = noise_burst(n, 3800, 120, 0.45, seed=26) * 1.2
    y += boom(n, 100, 28, 6, 0.4) * 1.2
    y += lowpass(osc("noise", 0, n, seed=27), 180) * env_exp(n, 0.7) * 1.5
    cr = osc("noise", 0, n, seed=28) * (crackle(n, 35, seed=29) > 0.6) * env_exp(n, 0.5) * 0.2
    y += highpass(cr, 1200)
    return wet(softclip(y, 1.6) * 0.6, 0.25)


@sfx("explo_boss")
def _explo_boss():
    n = ns(4.0)
    t = tarr(n)
    y = np.zeros(n)
    r = rng(30)
    for i in range(7):
        st = int((i * 0.28 + r.random() * 0.1) * SR)
        k = ns(1.4)
        seg = noise_burst(k, 3500, 150, 0.35, seed=31 + i) + boom(k, 110, 30, 7, 0.3)
        y[st:st + k] += seg[:len(y[st:st + k])] * (0.6 + 0.1 * i)
    y += lowpass(osc("noise", 0, n, seed=40), 120) * np.minimum(t / 0.5, 1) * np.exp(-t / 1.6) * 2.0
    y += boom(n, 60, 20, 2, 1.5) * 0.9
    return wet(softclip(y, 1.8) * 0.6, 0.3)


# ---------------------------------------------------------------------------
# Objets & interface
# ---------------------------------------------------------------------------
@sfx("pickup")
def _pickup():
    notes = [1318.5, 1661.2, 1975.5, 2637.0]
    seg = ns(0.045)
    y = np.zeros(seg * len(notes) + ns(0.12))
    for i, f in enumerate(notes):
        k = ns(0.12)
        s = osc("square", f, k, duty=0.25) * env_exp(k, 0.04) * (0.9 - i * 0.1)
        y[i * seg:i * seg + k] += s
    y = lowpass(y, 7000)
    return echo(y * 0.3, 0.09, 0.35, 3)


@sfx("powerup")
def _powerup():
    n = ns(0.9)
    t = tarr(n)
    f = 220 * (8 ** np.minimum(t / 0.35, 1))
    y = osc("saw", f, n) * 0.3 + osc("square", f * 1.5, n, duty=0.3) * 0.2
    y = lowpass(y, 5000) * env_adsr(n, 0.01, 0.3, 0.5, 0.3)
    for i, nt in enumerate(("D5", "F#5", "A5", "D6")):
        st = ns(0.3 + i * 0.06)
        k = n - st
        y[st:] += osc("tri", note_freq(nt), k) * env_exp(k, 0.3) * 0.25
    return wet(y * 0.6, 0.3)


@sfx("weapon")
def _weapon():
    n = ns(1.1)
    y = np.zeros(n)
    chord = ("A4", "C#5", "E5", "A5", "C#6")
    for i, nt in enumerate(chord):
        st = ns(i * 0.04)
        k = n - st
        s = pluck(note_freq(nt), k / SR, bright=0.8, decay=0.997, seed=50 + i)
        y[st:] += s * 0.4
    t = tarr(n)
    y += osc("saw", 110 * (4 ** np.minimum(t / 0.25, 1)), n) * env_exp(n, 0.15) * 0.25
    y = lowpass(y, 6000)
    return wet(y * 0.55, 0.35)


@sfx("coin")
def _coin():
    a, b = ns(0.05), ns(0.22)
    y = np.zeros(a + b)
    y[:a] = osc("square", 987.8, a, duty=0.5) * 0.5
    y[a:] = osc("square", 1318.5, b, duty=0.5) * env_exp(b, 0.07) * 0.5
    return lowpass(y, 4500) * 0.3


@sfx("oneup")
def _oneup():
    notes = ("C5", "E5", "G5", "C6", "E6", "G6")
    n = ns(1.6)
    y = np.zeros(n)
    for i, nt in enumerate(notes):
        st = ns(i * 0.07)
        s = pluck(note_freq(nt), (n - st) / SR, bright=0.85, decay=0.998, seed=60 + i)
        y[st:] += s * 0.5
    return wet(y * 0.6, 0.35)


@sfx("bomb")
def _bomb():
    n = ns(3.2)
    t = tarr(n)
    x = osc("noise", 0, n, seed=70)
    sw = sweep_lowpass(x, np.where(t < 0.35, 200 * (40 ** (t / 0.35)), 8000 * np.exp(-(t - 0.35) * 2.2) + 150))
    env = np.where(t < 0.35, (t / 0.35) ** 2, np.exp(-(t - 0.35) / 0.7))
    y = sw * env * 1.1
    k0 = ns(0.35)
    k = n - k0
    y[k0:] += boom(k, 90, 25, 4, 0.8) * 1.3
    # choeur (accord de ré mineur)
    ch = np.zeros(n)
    for nt in ("D3", "A3", "D4", "F4", "A4"):
        f = note_freq(nt)
        v = additive(f, n, 24, rolloff=1.0, vib=vibrato(n, 5, 10, 0.2), seed=int(f))
        ch += v
    ch = formant(ch, [(750, 1.0, 0.25), (1200, 0.6, 0.2), (2700, 0.25, 0.25)])
    ch *= np.clip((t - 0.3) / 0.25, 0, 1) * np.exp(-np.maximum(t - 0.7, 0) / 0.9)
    y += ch * 0.12
    return wet(softclip(y, 1.4) * 0.55, 0.4)


@sfx("armor")
def _armor():
    n = ns(0.8)
    y = fm(300, 1.73, 5.0, n, env_exp(n, 0.1)) * env_exp(n, 0.2) * 0.6
    y += noise_burst(n, 6000, 500, 0.08, seed=80) * 0.8
    k = ns(0.45)
    al = osc("square", sweep(880, 330, k), k, duty=0.5) * env_exp(k, 0.2) * 0.25
    y[ns(0.05):ns(0.05) + k] += lowpass(al, 3000)
    return wet(softclip(y, 1.5) * 0.55, 0.2, "room")


@sfx("die")
def _die():
    n = ns(2.4)
    y = noise_burst(n, 4000, 100, 0.5, seed=90) * 1.1
    y += boom(n, 120, 25, 5, 0.5) * 1.1
    t = tarr(n)
    y += osc("saw", 1400 * (0.05 ** np.minimum(t / 1.2, 1)), n) * env_exp(n, 0.5) * 0.25
    return wet(softclip(y, 1.6) * 0.55, 0.3)


@sfx("warning")
def _warning():
    cyc = 0.62
    n = ns(cyc * 3)
    t = tarr(n)
    ph = (t % cyc) / cyc
    f = np.where(ph < 0.5, 587.3, 440.0)
    y = osc("square", f, n, duty=0.5) * 0.35 + osc("saw", f * 0.5, n) * 0.25
    gate = np.where((ph % 0.5) < 0.42, 1.0, 0.0)
    gate = lowpass(gate, 60)
    y = softclip(lowpass(y, 2400) * gate * 1.5, 1.6)
    return wet(y * 0.5, 0.3)


@sfx("gong")
def _gong():
    n = ns(3.5)
    t = tarr(n)
    y = fm(98, 1.4, 3.0, n, env_exp(n, 0.5)) * env_exp(n, 1.2)
    y += fm(196 * 1.19, 1.0, 1.5, n, env_exp(n, 0.3)) * env_exp(n, 0.8) * 0.4
    y += fm(470, 2.3, 1.0, n, env_exp(n, 0.2)) * env_exp(n, 0.4) * 0.2
    y *= np.minimum(t / 0.01, 1)
    return wet(y * 0.5, 0.3)


@sfx("menu_move")
def _menu_move():
    n = ns(0.05)
    return lowpass(osc("square", 1250, n, duty=0.25) * env_exp(n, 0.02), 5000) * 0.28


@sfx("menu_ok")
def _menu_ok():
    y = np.zeros(ns(0.7))
    for i, nt in enumerate(("G5", "D6", "G6")):
        st = ns(i * 0.06)
        s = pluck(note_freq(nt), (len(y) - st) / SR, bright=0.9, decay=0.997, seed=100 + i)
        y[st:] += s * 0.45
    return wet(y * 0.55, 0.25)


@sfx("menu_back")
def _menu_back():
    a = ns(0.06)
    b = ns(0.14)
    y = np.zeros(a + b)
    y[:a] = osc("square", 587.3, a, duty=0.3) * 0.4
    y[a:] = osc("square", 440, b, duty=0.3) * env_exp(b, 0.05) * 0.4
    return lowpass(y, 4000) * 0.4


@sfx("mode")
def _mode():
    n = ns(0.16)
    y = highpass(osc("noise", 0, n, seed=110), 1500) * env_exp(n, 0.006) * 0.8
    k = ns(0.1)
    st = ns(0.03)
    y[st:st + k] += osc("square", sweep(700, 1500, k), k, duty=0.25) * env_exp(k, 0.04) * 0.4
    return lowpass(y, 6000) * 0.45


@sfx("speed_up")
def _speed_up():
    n = ns(0.12)
    return lowpass(osc("pulse", sweep(500, 1400, n), n, duty=0.25) * env_exp(n, 0.06), 5000) * 0.3


@sfx("speed_down")
def _speed_down():
    n = ns(0.12)
    return lowpass(osc("pulse", sweep(1400, 500, n), n, duty=0.25) * env_exp(n, 0.06), 5000) * 0.3


@sfx("graze")
def _graze():
    n = ns(0.05)
    y = highpass(osc("noise", 0, n, seed=120), 6000) * env_exp(n, 0.012)
    y += osc("sine", 4200, n) * env_exp(n, 0.015) * 0.3
    return y * 0.14


@sfx("tick")
def _tick():
    n = ns(0.04)
    return osc("square", 1760, n, duty=0.5) * env_exp(n, 0.012) * 0.18


@sfx("stage")
def _stage():
    n = ns(2.2)
    t = tarr(n)
    x = osc("noise", 0, n, seed=130)
    y = sweep_lowpass(x, 300 + 6000 * np.sin(np.clip(t / 1.4, 0, 1) * math.pi) ** 2) * 0.5
    y *= np.sin(np.clip(t / 1.6, 0, 1) * math.pi)
    for i, nt in enumerate(("D4", "A4", "D5", "E5", "F5", "A5")):
        st = ns(0.2 + i * 0.09)
        s = pluck(note_freq(nt), (n - st) / SR, bright=0.8, decay=0.998, seed=131 + i)
        y[st:] += s * 0.35
    return wet(y * 0.55, 0.4)


@sfx("clear")
def _clear():
    notes = [("D5", 0.0), ("F#5", 0.12), ("A5", 0.24), ("D6", 0.36), ("A5", 0.6), ("D6", 0.72)]
    n = ns(2.4)
    y = np.zeros(n)
    for i, (nt, st) in enumerate(notes):
        s0 = ns(st)
        s = pluck(note_freq(nt), (n - s0) / SR, bright=0.85, decay=0.998, seed=140 + i)
        y[s0:] += s * 0.4
        k = min(n - s0, ns(0.5))
        y[s0:s0 + k] += osc("pulse", note_freq(nt), k, duty=0.25) * env_exp(k, 0.15) * 0.12
    return wet(lowpass(y, 7000) * 0.6, 0.35)


@sfx("chain")
def _chain():
    n = ns(0.5)
    y = fm(1567, 3.5, 2.0, n, env_exp(n, 0.05)) * env_exp(n, 0.18)
    y += osc("sine", 1567 * 2, n) * env_exp(n, 0.08) * 0.3
    return echo(y * 0.25, 0.08, 0.3, 2)


@sfx("thunder")
def _thunder():
    n = ns(2.2)
    t = tarr(n)
    crack = highpass(osc("noise", 0, n, seed=150), 1200) * env_exp(n, 0.04) * 1.2
    rum = lowpass(osc("noise", 0, n, seed=151), 220) * 3.0
    am = 0.5 + 0.5 * lowpass(rng(152).random(n) ** 3, 8) * 4
    rum *= np.clip(am, 0, 2) * np.minimum(t / 0.05, 1) * np.exp(-t / 0.8)
    y = crack + rum + boom(n, 70, 25, 5, 0.4) * 0.7
    return wet(softclip(y, 1.4) * 0.6, 0.3)


@sfx("lightning")
def _lightning():
    n = ns(0.6)
    x = osc("noise", 0, n, seed=160) * (0.3 + crackle(n, 800, seed=161))
    y = bandpass(x, 1000, 9000) * env_exp(n, 0.15) * 1.2
    y += boom(n, 90, 30, 10, 0.2) * 0.8
    return wet(softclip(y, 1.5) * 0.55, 0.2, "room")


@sfx("shield_up")
def _shield_up():
    n = ns(0.6)
    t = tarr(n)
    f = 300 * (3 ** np.minimum(t / 0.4, 1))
    y = osc("sine", f, n) * 0.4 + osc("sine", f * 1.5, n) * 0.2
    y *= env_adsr(n, 0.02, 0.2, 0.6, 0.3)
    return wet(y * 0.5, 0.3)


@sfx("teleport")
def _teleport():
    n = ns(0.5)
    t = tarr(n)
    y = osc("sine", 200 + 1800 * t / 0.5 * (1 + 0.3 * np.sin(2 * math.pi * 40 * t)), n) * env_exp(n, 0.2)
    return wet(y * 0.35, 0.25)


@sfx("typing")
def _typing():
    n = ns(0.025)
    return osc("square", 2600, n, duty=0.5) * env_exp(n, 0.006) * 0.12


def build_all(progress=None):
    """Synthétise tous les bruitages -> dict nom -> (L, R) float."""
    out = {}
    names = list(REG.keys())
    for i, name in enumerate(names):
        r = REG[name]()
        if isinstance(r, tuple):
            L, R = r
        else:
            L = R = r
        out[name] = (np.asarray(L, dtype=np.float64), np.asarray(R, dtype=np.float64))
        if progress:
            progress((i + 1) / len(names))
    return out
