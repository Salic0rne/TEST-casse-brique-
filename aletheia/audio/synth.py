"""Primitives DSP (numpy pur) : oscillateurs anti-repliement, enveloppes, filtres FFT,
cordes pincées (Karplus-Strong), FM, synthèse additive, réverbération par convolution."""
import math

import numpy as np

SR = 44100
_RNG = np.random.default_rng(12345)


def ns(dur):
    return max(1, int(round(dur * SR)))


def tarr(n):
    return np.arange(n, dtype=np.float64) / SR


def rng(seed=None):
    return np.random.default_rng(seed) if seed is not None else _RNG


# ---------------------------------------------------------------------------
# Oscillateurs
# ---------------------------------------------------------------------------
def _freq_arr(freq, n):
    if np.isscalar(freq):
        return np.full(n, float(freq))
    f = np.asarray(freq, dtype=np.float64)
    if len(f) < n:
        f = np.concatenate([f, np.full(n - len(f), f[-1] if len(f) else 0.0)])
    return f[:n]


def _polyblep(t, dt):
    out = np.zeros_like(t)
    m = t < dt
    if m.any():
        x = t[m] / dt[m]
        out[m] = x + x - x * x - 1.0
    m = t > 1.0 - dt
    if m.any():
        x = (t[m] - 1.0) / dt[m]
        out[m] = x * x + x + x + 1.0
    return out


def osc(kind, freq, n, duty=0.5, ph0=0.0, seed=None):
    if kind == "noise":
        return rng(seed).uniform(-1, 1, n)
    f = _freq_arr(freq, n)
    dt = np.clip(f / SR, 1e-7, 0.49)
    ph = np.cumsum(dt) + ph0
    t = ph % 1.0
    if kind == "sine":
        return np.sin(2 * math.pi * ph)
    if kind == "tri":
        return 2.0 * np.abs(2.0 * t - 1.0) - 1.0
    if kind == "saw":
        return 2.0 * t - 1.0 - _polyblep(t, dt)
    if kind in ("square", "pulse"):
        y = np.where(t < duty, 1.0, -1.0)
        y += _polyblep(t, dt)
        y -= _polyblep((t - duty) % 1.0, dt)
        return y
    raise ValueError(kind)


def phase(freq, n, ph0=0.0):
    return np.cumsum(_freq_arr(freq, n) / SR) + ph0


def sweep(f0, f1, n, curve="exp"):
    t = np.linspace(0, 1, n)
    if curve == "exp":
        return f0 * (f1 / f0) ** t
    return f0 + (f1 - f0) * t


def expdrop(f0, f1, n, rate):
    """Fréquence qui chute exponentiellement de f0 vers f1 (rate en 1/s)."""
    return f1 + (f0 - f1) * np.exp(-tarr(n) * rate)


# ---------------------------------------------------------------------------
# Enveloppes
# ---------------------------------------------------------------------------
def env_exp(n, decay):
    return np.exp(-tarr(n) / max(1e-4, decay))


def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.1, gate=None):
    t = tarr(n)
    gate = max(0.0, (n / SR - r) if gate is None else gate)
    a = max(a, 1e-4)
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-np.maximum(t - a, 0) / max(1e-4, d / 3.0)))
    if gate < n / SR:
        gi = min(n - 1, int(gate * SR))
        gv = e[gi]
        rel = t >= gate
        e[rel] = gv * np.exp(-(t[rel] - gate) / max(1e-4, r / 4.0))
    return e


def fade_edges(x, fin=0.002, fout=0.01):
    n = len(x)
    a = min(n, ns(fin))
    b = min(n, ns(fout))
    if a > 0:
        x[:a] *= np.linspace(0, 1, a)
    if b > 0:
        x[-b:] *= np.linspace(1, 0, b)
    return x


# ---------------------------------------------------------------------------
# Filtres (domaine fréquentiel, phase nulle)
# ---------------------------------------------------------------------------
def _nfft(n):
    return 1 << int(math.ceil(math.log2(max(2, n))))


def fft_filter(x, H_fn, pad=0.05):
    n = len(x)
    N = _nfft(n + ns(pad))
    X = np.fft.rfft(x, N)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    X *= H_fn(f)
    return np.fft.irfft(X, N)[:n]


def lowpass(x, fc, order=2):
    return fft_filter(x, lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order)))


def highpass(x, fc, order=2):
    return fft_filter(x, lambda f: 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-3)) ** (2 * order)))


def bandpass(x, lo, hi, order=2):
    return fft_filter(x, lambda f: (1.0 / np.sqrt(1.0 + (f / hi) ** (2 * order)))
                      * (1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1e-3)) ** (2 * order))))


def peaks(x, bands):
    """bands: liste de (fréquence, gain linéaire, largeur relative) ajoutés en cloche (log-fréquence)."""
    def H(f):
        h = np.ones_like(f)
        lf = np.log2(np.maximum(f, 1.0))
        for fc, g, w in bands:
            h += (g - 1.0) * np.exp(-((lf - math.log2(fc)) / w) ** 2)
        return h
    return fft_filter(x, H)


def formant(x, formants):
    """Filtre vocalique : somme de bosses (freq, gain, largeur en octaves)."""
    def H(f):
        lf = np.log2(np.maximum(f, 1.0))
        h = np.zeros_like(f) + 0.04
        for fc, g, w in formants:
            h += g * np.exp(-((lf - math.log2(fc)) / w) ** 2)
        return h
    return fft_filter(x, H)


def sweep_lowpass(x, fc_curve, k=8, order=2):
    """Passe-bas à fréquence de coupure variable (fondu entre k versions filtrées)."""
    fc_curve = _freq_arr(fc_curve, len(x))
    lo, hi = max(20.0, fc_curve.min()), max(40.0, fc_curve.max())
    if hi / lo < 1.05:
        return lowpass(x, lo, order)
    cuts = lo * (hi / lo) ** np.linspace(0, 1, k)
    versions = np.stack([lowpass(x, c, order) for c in cuts])
    pos = np.interp(np.log(np.clip(fc_curve, lo, hi)), np.log(cuts), np.arange(k))
    i0 = np.clip(np.floor(pos).astype(np.int64), 0, k - 2)
    fr = pos - i0
    idx = np.arange(len(x))
    return versions[i0, idx] * (1 - fr) + versions[i0 + 1, idx] * fr


# ---------------------------------------------------------------------------
# Générateurs spéciaux
# ---------------------------------------------------------------------------
def pluck(freq, dur, bright=0.6, decay=0.996, seed=None):
    """Corde pincée Karplus-Strong vectorisée par périodes (lyre)."""
    n = ns(dur)
    N = max(2, int(round(SR / freq - 0.5)))
    r = rng(seed)
    burst = r.uniform(-1, 1, N)
    if bright < 1.0:
        k = max(1, int((1.0 - bright) * 6))
        for _ in range(k):
            burst = 0.5 * (burst + np.roll(burst, 1))
    out = np.zeros(n + N + 1)
    out[1:N + 1] = burst
    start = N + 1
    while start < len(out):
        end = min(start + N, len(out))
        out[start:end] = decay * 0.5 * (out[start - N:end - N] + out[start - N - 1:end - N - 1])
        start = end
    return out[1:n + 1]


def fm(fc, ratio, index, n, index_env=None, fb=0.0):
    t = tarr(n)
    ie = index if index_env is None else index * index_env
    mod = np.sin(2 * math.pi * fc * ratio * t) * ie
    return np.sin(2 * math.pi * fc * t + mod)


def additive(freq, n, harmonics=16, rolloff=1.0, decay=None, vib=None, amp_fn=None, detune=0.0, seed=None):
    """Synthèse additive par récurrence de Tchebychev : sin(kθ) = 2cosθ·sin((k-1)θ) - sin((k-2)θ).
    decay : décroissance par harmonique (harmonique k décroît k fois plus vite -> filtre naturel)."""
    f = _freq_arr(freq, n)
    if vib is not None:
        f = f * vib
    ph = np.cumsum(f / SR)
    if seed is not None:
        ph += rng(seed).random()
    theta = (2 * math.pi * (ph % 1.0)).astype(np.float32)
    s_cur = np.sin(theta)
    c2 = (2.0 * np.cos(theta)).astype(np.float32)
    s_prev = np.zeros(n, np.float32)
    y = np.zeros(n, np.float32)
    base = float(np.mean(f))
    E = None
    Ek = None
    if decay is not None:
        E = np.exp(-(np.arange(n, dtype=np.float32) / SR) * (decay * 0.6)).astype(np.float32)
        Ek = np.ones(n, np.float32)
    for k in range(1, harmonics + 1):
        if base * k > SR * 0.45:
            break
        a = 1.0 / (k ** rolloff)
        if amp_fn is not None:
            a *= amp_fn(base * k, k)
        if E is not None:
            Ek *= E
        if a >= 1e-4:
            if Ek is not None:
                y += (a * s_cur) * Ek
            else:
                y += a * s_cur
        s_next = c2 * s_cur - s_prev
        s_prev = s_cur
        s_cur = s_next
    return y.astype(np.float64)


def vibrato(n, rate=5.5, depth_cents=12.0, delay=0.15):
    t = np.arange(n, dtype=np.float32) / SR
    amt = np.clip((t - delay) / 0.25, 0, 1) * (depth_cents / 1200.0)
    return np.exp2(np.sin((2 * math.pi * rate) * t) * amt).astype(np.float64)


def crackle(n, rate=400.0, seed=None):
    """Amplitude aléatoire échantillonnée-bloquée (grésillement électrique)."""
    r = rng(seed)
    step = max(1, int(SR / rate))
    k = n // step + 2
    vals = r.random(k) ** 3
    return np.repeat(vals, step)[:n]


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / math.tanh(drive)


# ---------------------------------------------------------------------------
# Espace : réverbération et écho
# ---------------------------------------------------------------------------
def make_ir(dur=1.8, decay=0.42, seed=7, damp=5200.0, predelay=0.018, early=True):
    r = rng(seed)
    n = ns(dur)
    t = tarr(n)
    env = np.exp(-t / decay)
    L = r.normal(0, 1, n) * env
    R = r.normal(0, 1, n) * env
    # amortissement des aigus progressif : on mélange une version filtrée qui domine avec le temps
    Ld, Rd = lowpass(L, damp * 0.35), lowpass(R, damp * 0.35)
    mix = np.clip(t / (dur * 0.5), 0, 1)
    L = lowpass(L, damp) * (1 - mix) + Ld * mix
    R = lowpass(R, damp) * (1 - mix) + Rd * mix
    pd = ns(predelay)
    L = np.concatenate([np.zeros(pd), L])
    R = np.concatenate([np.zeros(pd), R])
    if early:
        for i, (dl, g) in enumerate(((0.011, 0.5), (0.019, 0.4), (0.027, 0.33), (0.041, 0.25))):
            k = ns(dl)
            if i % 2 == 0:
                L[k] += g * 3
            else:
                R[k] += g * 3
    norm = math.sqrt(float(np.sum(L * L) + np.sum(R * R)) / 2) or 1.0
    return L / norm, R / norm


def convolve(x, ir):
    n = len(x) + len(ir) - 1
    N = _nfft(n)
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n]


def _half(x):
    m = len(x) // 2
    return (x[0:2 * m:2] + x[1:2 * m:2]) * 0.5


def _double(y, n):
    return np.interp(np.arange(n) * 0.5, np.arange(len(y)), y)


def reverb_stereo(x_l, x_r, ir, half=True):
    """Convolution stéréo. half=True : calcul à demi-fréquence (la réverbération est sombre de toute façon)."""
    L, R = ir
    if not half or len(x_l) < 4096:
        return convolve(x_l, L), convolve(x_r, R)
    n_out = len(x_l) + len(L) - 1
    yl = convolve(_half(x_l), _half(L)) * 2.0
    yr = convolve(_half(x_r), _half(R)) * 2.0
    return _double(yl, n_out), _double(yr, n_out)


def echo(x, delay_s, feedback=0.4, taps=4, pingpong=True):
    """Écho multi-taps -> (gauche, droite), longueur étendue."""
    d = ns(delay_s)
    n = len(x) + d * taps
    L = np.zeros(n)
    R = np.zeros(n)
    g = 1.0
    for i in range(1, taps + 1):
        g *= feedback
        tgt = L if (i % 2 == 1 or not pingpong) else R
        tgt[i * d:i * d + len(x)] += x * g
        if not pingpong:
            R[i * d:i * d + len(x)] += x * g
    return L, R


def pan_gains(p):
    """p dans [-1, 1] -> gains gauche/droite (loi à puissance constante)."""
    a = (p + 1) * math.pi / 4
    return math.cos(a), math.sin(a)


def to_int16_stereo(L, R, peak=0.92):
    m = max(float(np.max(np.abs(L))) if len(L) else 0.0, float(np.max(np.abs(R))) if len(R) else 0.0, 1e-9)
    g = peak / m if m > peak else 1.0
    st = np.empty((len(L), 2), dtype=np.int16)
    st[:, 0] = np.clip(L * g * 32767, -32768, 32767)
    st[:, 1] = np.clip(R * g * 32767, -32768, 32767)
    return st


def mono(x, gain=1.0, pan=0.0, peak=None):
    gl, gr = pan_gains(pan)
    x = x * gain
    if peak is not None:
        m = float(np.max(np.abs(x))) or 1.0
        x = x * (peak / m)
    return x * gl * math.sqrt(2), x * gr * math.sqrt(2)


NOTE_BASE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_freq(name):
    """'A4' -> 440.0 ; 'C#5', 'Eb3'…"""
    return midi_freq(note_midi(name))


def note_midi(name):
    s = NOTE_BASE[name[0].upper()]
    i = 1
    while i < len(name) and name[i] in "#b":
        s += 1 if name[i] == "#" else -1
        i += 1
    octave = int(name[i:])
    return 12 * (octave + 1) + s


def midi_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)
