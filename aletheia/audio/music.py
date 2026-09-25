"""Séquenceur « tracker » + instruments synthétisés.

Format d'une chanson (voir songs.py) :
  bpm, order (liste de patterns), patterns {nom: {canal: "notes…"}}, channels {canal: réglages}
Canal mélodique : jetons séparés par des espaces, 1 jeton = 1 double-croche :
  "D5" note, "D5!" accentuée, "D5?" douce, "." tenue, "-" silence, "|" ignoré.
Canal d'accords (chords=True) : "Dm", "Bb", "A7", "Fmaj7", "Esus4"…
Canal de batterie (drums=True) : 1 caractère = 1 pas (k kick, s snare, h hat, o open, c crash,
  p clap, t/m/n toms, a enclume, g gong, d doum, e tek, r cloche, x kick+hat, y snare+hat,
  z kick+crash, w kick+open, q snare+crash, . rien). Majuscule = accent.
"""
import math
import re

import numpy as np

from .synth import (SR, ns, tarr, osc, env_exp, env_adsr, lowpass, highpass, bandpass, pluck, fm, additive,
                    vibrato, softclip, make_ir, reverb_stereo, echo, pan_gains, midi_freq, note_midi, peaks,
                    rng, expdrop)

NOTE_RE = re.compile(r"^([A-Ga-g])([#b]?)(-?\d)([!?]?)$")
CHORD_RE = re.compile(r"^([A-G])([#b]?)(maj7|m7|m9|madd9|m|7|sus4|sus2|dim|aug|add9|6)?([!?]?)$")
CHORD_IV = {
    None: [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10], "maj7": [0, 4, 7, 11],
    "sus4": [0, 5, 7], "sus2": [0, 2, 7], "dim": [0, 3, 6], "aug": [0, 4, 8], "add9": [0, 4, 7, 14],
    "m9": [0, 3, 7, 10, 14], "madd9": [0, 3, 7, 14], "6": [0, 4, 7, 9],
}
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------
def _tail(dur, rel):
    return ns(dur + rel)


def v_lead(f, dur, vel, p):
    rel = p.get("rel", 0.12)
    n = _tail(dur, rel)
    vib = vibrato(n, 5.6, p.get("vib", 14), 0.18)
    det = p.get("detune", 0.006)
    y = (osc("saw", f * vib, n) + osc("saw", f * (1 + det) * vib, n) * 0.8
         + osc("saw", f * (1 - det) * vib, n) * 0.8) / 2.6
    y += osc("square", f * 0.5 * vib, n, duty=0.5) * p.get("sub", 0.2)
    e = env_adsr(n, p.get("a", 0.008), p.get("d", 0.15), p.get("s", 0.75), rel, dur)
    return y * e * vel


def v_aulos(f, dur, vel, p):
    """Aulos (double flûte grecque) : deux anches pulsées légèrement désaccordées + souffle."""
    rel = p.get("rel", 0.09)
    n = _tail(dur, rel)
    vib = vibrato(n, 6.2, p.get("vib", 22), 0.12)
    y = osc("pulse", f * vib, n, duty=0.34) * 0.6 + osc("pulse", f * 1.004 * vib, n, duty=0.22) * 0.4
    br = bandpass(osc("noise", 0, n, seed=int(f)), f * 1.5, min(f * 6, 12000)) * 0.18
    e = env_adsr(n, p.get("a", 0.025), 0.12, 0.85, rel, dur)
    return (y + br) * e * vel


def v_pulse(f, dur, vel, p):
    n = _tail(dur, p.get("rel", 0.05))
    y = osc("pulse", f, n, duty=p.get("duty", 0.25))
    e = env_exp(n, p.get("decay", 0.12)) * np.minimum(tarr(n) / 0.002, 1)
    return y * e * vel


def v_bass(f, dur, vel, p):
    rel = p.get("rel", 0.06)
    n = _tail(dur, rel)
    y = additive(f, n, harmonics=p.get("harm", 18), rolloff=1.0, decay=p.get("fdecay", 9.0), seed=int(f * 10))
    y = y * 0.55 + osc("sine", f, n) * p.get("sub", 0.5)
    e = env_adsr(n, 0.004, 0.2, p.get("s", 0.7), rel, dur)
    return softclip(y * e * 1.2, 1.2) * vel


def v_fmbass(f, dur, vel, p):
    rel = p.get("rel", 0.05)
    n = _tail(dur, rel)
    ie = env_exp(n, p.get("idecay", 0.09))
    y = fm(f, 1.0, p.get("index", 3.2), n, ie) * 0.7 + osc("sine", f * 0.5, n) * 0.4
    e = env_adsr(n, 0.003, 0.15, 0.8, rel, dur)
    return softclip(y * e * 1.3, 1.3) * vel


def v_choir(f, dur, vel, p):
    rel = p.get("rel", 0.5)
    n = _tail(dur, rel)
    vowel = p.get("vowel", "a")
    forms = {"a": [(800, 1.0), (1150, 0.5), (2800, 0.18)], "o": [(450, 1.0), (800, 0.45), (2830, 0.1)],
             "u": [(325, 1.0), (700, 0.25), (2530, 0.08)], "e": [(400, 1.0), (1600, 0.35), (2700, 0.2)]}[vowel]

    def amp(fr, k):
        a = 0.03
        for fc, g in forms:
            a += g * math.exp(-((math.log2(max(fr, 1)) - math.log2(fc)) / 0.28) ** 2)
        return a

    y = np.zeros(n)
    for i, det in enumerate((-0.004, 0.005)):
        vib = vibrato(n, 4.8 + i * 0.7, 9, 0.3)
        y += additive(f * (1 + det), n, harmonics=28, rolloff=0.5, vib=vib, amp_fn=amp, seed=int(f) + i)
    e = env_adsr(n, p.get("a", 0.35), 0.4, 0.85, rel, dur)
    return y * e * vel * 0.5


def v_strings(f, dur, vel, p):
    rel = p.get("rel", 0.35)
    n = _tail(dur, rel)
    y = np.zeros(n)
    for i, det in enumerate((-0.005, 0.0, 0.006)):
        vib = vibrato(n, 5.0 + i * 0.4, 8, 0.2)
        y += additive(f * (1 + det), n, harmonics=22, rolloff=1.05, vib=vib, seed=int(f * 3) + i)
    e = env_adsr(n, p.get("a", 0.18), 0.3, 0.9, rel, dur)
    return y * e * vel * 0.35


def v_brass(f, dur, vel, p):
    rel = p.get("rel", 0.15)
    n = _tail(dur, rel)
    e = env_adsr(n, p.get("a", 0.04), 0.25, 0.75, rel, dur)
    vib = vibrato(n, 5.2, 10, 0.25)
    ph = np.cumsum(f * vib / SR)
    y = np.zeros(n)
    for k in range(1, 20):
        if f * k > 11000:
            break
        y += np.sin(2 * math.pi * k * ph) * (1.0 / k) * e ** (1 + 0.35 * k)
    y2 = osc("saw", f * 1.003 * vib, n) * 0.15 * e ** 2.5
    return (y + y2) * vel * 0.8


def v_lyre(f, dur, vel, p):
    n = _tail(dur, p.get("rel", 1.2))
    y = pluck(f, n / SR, bright=p.get("bright", 0.75), decay=p.get("decay", 0.9975), seed=int(f * 7) % 9999)
    y += pluck(f * 2.001, n / SR, bright=0.9, decay=0.995, seed=int(f * 11) % 9999) * 0.15
    return y * vel * 0.9


def v_bell(f, dur, vel, p):
    n = _tail(dur, p.get("rel", 1.0))
    y = fm(f, 3.5, 2.2, n, env_exp(n, 0.3)) * env_exp(n, p.get("decay", 0.6))
    y += np.sin(2 * math.pi * f * 2 * tarr(n)) * env_exp(n, 0.25) * 0.25
    return y * vel * 0.6


def v_sub(f, dur, vel, p):
    rel = p.get("rel", 0.05)
    n = _tail(dur, rel)
    return osc("sine", f, n) * env_adsr(n, 0.005, 0.1, 0.9, rel, dur) * vel


def v_organ(f, dur, vel, p):
    rel = p.get("rel", 0.1)
    n = _tail(dur, rel)
    t = tarr(n)
    y = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.25), (6, 0.12), (8, 0.1)):
        y += np.sin(2 * math.pi * f * k * t) * a
    y *= 1 + 0.08 * np.sin(2 * math.pi * 6.5 * t)
    return y * env_adsr(n, 0.01, 0.1, 0.9, rel, dur) * vel * 0.35


INSTRUMENTS = {
    "lead": v_lead, "aulos": v_aulos, "pulse": v_pulse, "bass": v_bass, "fmbass": v_fmbass,
    "choir": v_choir, "strings": v_strings, "brass": v_brass, "lyre": v_lyre, "bell": v_bell, "sub": v_sub,
    "organ": v_organ,
}


# ---------------------------------------------------------------------------
# Batterie
# ---------------------------------------------------------------------------
_DRUMS = None


def _drums():
    global _DRUMS
    if _DRUMS is not None:
        return _DRUMS
    d = {}
    n = ns(0.45)
    k = osc("sine", expdrop(170, 44, n, 28), n) * env_exp(n, 0.2)
    k += highpass(osc("noise", 0, n, seed=1), 3000) * env_exp(n, 0.003) * 0.5
    d["k"] = softclip(k * 1.4, 1.5) * 0.95
    n = ns(0.3)
    s = bandpass(osc("noise", 0, n, seed=2), 1200, 8000) * env_exp(n, 0.09) * 0.9
    s += osc("tri", expdrop(240, 180, n, 30), n) * env_exp(n, 0.05) * 0.7
    d["s"] = softclip(s * 1.2, 1.3) * 0.7
    n = ns(0.06)
    d["h"] = highpass(osc("noise", 0, n, seed=3), 7500) * env_exp(n, 0.013) * 0.45
    n = ns(0.3)
    d["o"] = highpass(osc("noise", 0, n, seed=4), 6500) * env_exp(n, 0.09) * 0.35
    n = ns(1.8)
    c = highpass(osc("noise", 0, n, seed=5), 4000) * env_exp(n, 0.55) * 0.5
    c += fm(3100, 1.47, 2.0, n, env_exp(n, 0.4)) * env_exp(n, 0.5) * 0.08
    d["c"] = c
    n = ns(0.25)
    p = np.zeros(n)
    for i in range(3):
        st = ns(i * 0.011)
        seg = bandpass(osc("noise", 0, n - st, seed=10 + i), 900, 5000) * env_exp(n - st, 0.012 if i < 2 else 0.07)
        p[st:] += seg
    d["p"] = p * 0.6
    for key, (f0, f1) in (("t", (130, 80)), ("m", (170, 110)), ("n", (220, 150))):
        n = ns(0.4)
        d[key] = (osc("sine", expdrop(f0, f1, n, 12), n) * env_exp(n, 0.16)
                  + bandpass(osc("noise", 0, n, seed=20), 200, 2000) * env_exp(n, 0.02) * 0.3) * 0.8
    n = ns(0.7)
    a = fm(1180, 1.41, 3.0, n, env_exp(n, 0.05)) * env_exp(n, 0.22)
    a += fm(2650, 2.76, 1.5, n, env_exp(n, 0.03)) * env_exp(n, 0.12) * 0.5
    a += highpass(osc("noise", 0, n, seed=21), 2000) * env_exp(n, 0.004) * 0.6
    d["a"] = a * 0.45
    n = ns(3.0)
    g = fm(98, 1.4, 3.0, n, env_exp(n, 0.5)) * env_exp(n, 1.1)
    g += fm(233, 1.0, 1.5, n, env_exp(n, 0.3)) * env_exp(n, 0.7) * 0.35
    d["g"] = g * 0.5
    # tambour sur cadre (daf / tympanon) : doum grave et tek sec
    n = ns(0.5)
    d["d"] = (osc("sine", expdrop(110, 70, n, 9), n) * env_exp(n, 0.2)
              + bandpass(osc("noise", 0, n, seed=22), 100, 900) * env_exp(n, 0.03) * 0.5) * 0.85
    n = ns(0.15)
    d["e"] = (bandpass(osc("noise", 0, n, seed=23), 1500, 6000) * env_exp(n, 0.025)
              + osc("sine", 520, n) * env_exp(n, 0.02) * 0.3) * 0.55
    n = ns(0.2)
    d["r"] = fm(2400, 1.93, 1.2, n, env_exp(n, 0.05)) * env_exp(n, 0.08) * 0.2
    _DRUMS = d
    return d


DRUM_COMBOS = {"x": "kh", "y": "sh", "z": "kc", "w": "ko", "q": "sc"}


# ---------------------------------------------------------------------------
# Rendu d'une chanson
# ---------------------------------------------------------------------------
def parse_tokens(s):
    return [t for t in s.split() if t != "|"]


def parse_drums(s):
    return [c for c in s if c not in " |\n\t"]


def chord_notes(tok, octave=3):
    m = CHORD_RE.match(tok)
    if not m:
        raise ValueError("accord inconnu: " + tok)
    root = SEMI[m.group(1)] + (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)
    root_midi = 12 * (octave + 1) + root
    ivs = CHORD_IV[m.group(3)]
    notes = [root_midi + i for i in ivs]
    return notes, m.group(4)


def _events_melodic(tokens, chords=False):
    """-> liste (pas_début, nb_pas, [midi...], vélocité)."""
    ev = []
    cur = None
    for i, tok in enumerate(tokens):
        if tok == ".":
            if cur is not None:
                cur[1] += 1
            continue
        if cur is not None:
            ev.append(cur)
            cur = None
        if tok == "-":
            continue
        if chords:
            notes, acc = chord_notes(tok)
        else:
            m = NOTE_RE.match(tok)
            if not m:
                raise ValueError("note inconnue: " + tok)
            notes = [note_midi(m.group(1).upper() + m.group(2) + m.group(3))]
            acc = m.group(4)
        vel = 1.0 if acc == "!" else 0.55 if acc == "?" else 0.82
        cur = [i, 1, notes, vel]
    if cur is not None:
        ev.append(cur)
    return ev


class Renderer:
    def __init__(self, song):
        self.song = song
        self.cache = {}

    def voice(self, inst, params, midi, steps, vel, step_dur):
        key = (inst, midi, steps, round(vel, 2), tuple(sorted(params.items())))
        y = self.cache.get(key)
        if y is None:
            fn = INSTRUMENTS[inst]
            y = fn(midi_freq(midi), steps * step_dur * params.get("gate", 0.92), vel, params)
            self.cache[key] = y
        return y

    def render(self, progress=None, normalize=True):
        song = self.song
        bpm = song["bpm"]
        step = 60.0 / bpm / 4
        order = song["order"]
        pats = song["patterns"]
        chans = song["channels"]
        swing = song.get("swing", 0.0)
        # longueur de chaque pattern
        plen = {}
        for pn, pat in pats.items():
            L = 0
            for cn, s in pat.items():
                cfg = chans.get(cn, {})
                L = max(L, len(parse_drums(s)) if cfg.get("drums") else len(parse_tokens(s)))
            plen[pn] = L
        total_steps = sum(plen[p] for p in order)
        loop_n = ns(total_steps * step)
        tail = ns(4.0)
        N = loop_n + tail
        bufs = {cn: np.zeros(N, np.float32) for cn in chans}
        kick_steps = []
        R = rng(song.get("seed", 1))
        drums = _drums()
        pos = 0
        chord_track = []   # (pas_global, nb_pas, notes) pour les arpèges automatiques
        for pi, pn in enumerate(order):
            pat = pats[pn]
            for cn, s in pat.items():
                cfg = chans[cn]
                buf = bufs[cn]
                if cfg.get("drums"):
                    for i, c in enumerate(parse_drums(s)):
                        if c == ".":
                            continue
                        t0 = (pos + i) * step + (swing * step if (pos + i) % 2 == 1 else 0.0)
                        t0 += (R.random() - 0.5) * 0.004
                        st = max(0, int(t0 * SR))
                        combo = DRUM_COMBOS.get(c.lower(), c.lower())
                        for dc in combo:
                            smp = drums.get(dc)
                            if smp is None:
                                continue
                            g = 1.0 if c.isupper() else 0.78
                            end = min(N, st + len(smp))
                            buf[st:end] += smp[:end - st] * g
                            if dc.lower() == "k":
                                kick_steps.append(st)
                    continue
                toks = parse_tokens(s)
                evs = _events_melodic(toks, chords=cfg.get("chords", False))
                inst = cfg["inst"]
                params = cfg.get("params", {})
                octs = cfg.get("oct", 0)
                for (i0, nst, notes, vel) in evs:
                    if cfg.get("chords"):
                        chord_track.append((pos + i0, nst, notes, set(pat.keys())))
                        if cfg.get("voicing") == "bass":
                            notes = [notes[0] - 12]
                        else:
                            notes = [n_ + 12 * octs for n_ in notes]
                            if cfg.get("root", False):
                                notes = notes + [notes[0] - 12]
                    else:
                        notes = [n_ + 12 * octs for n_ in notes]
                    t0 = (pos + i0) * step + (swing * step if (pos + i0) % 2 == 1 else 0.0)
                    t0 += (R.random() - 0.5) * 0.003
                    st = max(0, int(t0 * SR))
                    vv = round(vel * (0.92 + R.random() * 0.08) / 0.05) * 0.05
                    for m_ in notes:
                        y = self.voice(inst, params, m_, nst, vv, step)
                        end = min(N, st + len(y))
                        buf[st:end] += y[:end - st]
            pos += plen[pn]
            if progress:
                progress(0.7 * (pi + 1) / len(order))
        # arpèges automatiques dérivés des accords
        for cn, cfg in chans.items():
            aa = cfg.get("autoarp")
            if not aa:
                continue
            buf = bufs[cn]
            pattern = aa.get("pattern", [0, 1, 2, 1])
            rate = aa.get("rate", 1)
            octv = aa.get("oct", 5)
            inst = cfg["inst"]
            params = cfg.get("params", {})
            k = 0
            for (s0, nst, notes, present) in chord_track:
                if cn not in present:
                    continue
                base = sorted(notes)
                ext = base + [n_ + 12 for n_ in base]
                shift = 12 * (octv - 3)
                for j in range(0, nst, rate):
                    idx = pattern[k % len(pattern)]
                    k += 1
                    if idx < 0:
                        continue
                    m_ = ext[idx % len(ext)] + shift
                    t0 = (s0 + j) * step
                    st = int(t0 * SR)
                    y = self.voice(inst, params, m_, rate, 0.8, step)
                    end = min(N, st + len(y))
                    buf[st:end] += y[:end - st]
        # mixage
        L = np.zeros(N, np.float32)
        Rr = np.zeros(N, np.float32)
        revL = np.zeros(N, np.float32)
        revR = np.zeros(N, np.float32)
        duck = None
        if kick_steps and any(c.get("duck") for c in chans.values()):
            duck = np.ones(N)
            dn = ns(0.22)
            shape = 1 - np.exp(-tarr(dn) / 0.06)
            for st in kick_steps:
                end = min(N, st + dn)
                duck[st:end] = np.minimum(duck[st:end], shape[:end - st])
        for ci, (cn, cfg) in enumerate(chans.items()):
            x = bufs[cn]
            if not np.any(x):
                continue
            if cfg.get("lp"):
                x = lowpass(x, cfg["lp"])
            if cfg.get("hp"):
                x = highpass(x, cfg["hp"])
            if cfg.get("eq"):
                x = peaks(x, cfg["eq"])
            if cfg.get("duck") and duck is not None:
                x = x * (1 - cfg["duck"] * (1 - duck))
            vol = cfg.get("vol", 0.5)
            gl, gr = pan_gains(cfg.get("pan", 0.0))
            xl, xr = x * vol * gl * 1.41, x * vol * gr * 1.41
            if cfg.get("echo"):
                steps_d, fb = cfg["echo"]
                el, er = echo(x * vol, steps_d * step, fb, 4, pingpong=True)
                L += el[:N] * 0.7
                Rr += er[:N] * 0.7
            L += xl
            Rr += xr
            rv = cfg.get("rev", 0.0)
            if rv:
                revL += xl * rv
                revR += xr * rv
            if progress:
                progress(0.7 + 0.2 * (ci + 1) / len(chans))
        if np.any(revL):
            ir = make_ir(song.get("rev_len", 2.4), song.get("rev_decay", 0.6), seed=3, damp=5000)
            wl, wr = reverb_stereo(revL, revR, ir)
            L += wl[:N]
            Rr += wr[:N]
        if song.get("loop", True):
            # boucle sans couture : la traîne revient au début
            L[:tail] += L[loop_n:loop_n + tail]
            Rr[:tail] += Rr[loop_n:loop_n + tail]
            L, Rr = L[:loop_n], Rr[:loop_n]
        else:
            amp = np.maximum(np.abs(L), np.abs(Rr))
            thr = amp.max() * 0.002
            idx = np.nonzero(amp > thr)[0]
            end = int(idx[-1]) + ns(0.05) if len(idx) else len(L)
            L, Rr = L[:end], Rr[:end]
            fl = min(len(L), ns(0.3))
            L[-fl:] *= np.linspace(1, 0, fl)
            Rr[-fl:] *= np.linspace(1, 0, fl)
        if not normalize:
            return L, Rr
        m = max(float(np.max(np.abs(L))), float(np.max(np.abs(Rr))), 1e-9)
        drive = song.get("drive", 1.1)
        L = softclip(L / m * drive, drive) * 0.9
        Rr = softclip(Rr / m * drive, drive) * 0.9
        if progress:
            progress(1.0)
        return L, Rr
