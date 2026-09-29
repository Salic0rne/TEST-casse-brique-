// Séquenceur de musique générative : morceaux data-driven joués avec des synthés WebAudio.
// Couches dynamiques (intensité 0..1) : hats, percussions, arpèges, lead. Sidechain sur le kick.

const NOTE = (n) => 440 * Math.pow(2, (n - 69) / 12);

// PRNG déterministe pour que les mélodies générées soient toujours les mêmes.
function mulberry(seed) { return () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const MINOR = [0, 3, 7, 10], MAJOR = [0, 4, 7, 11], M7 = [0, 3, 7, 10], SUS = [0, 5, 7, 10], DOM = [0, 4, 7, 10];

function makeLead(seed, scale, base, bars, density) {
  const rnd = mulberry(seed), notes = [];
  let idx = Math.floor(scale.length / 2);
  for (let bar = 0; bar < bars; bar++) {
    let s = 0;
    while (s < 16) {
      const r = rnd();
      if (r < density) {
        idx = Math.max(0, Math.min(scale.length - 1, idx + Math.floor(rnd() * 5) - 2));
        const len = rnd() < 0.3 ? 4 : rnd() < 0.5 ? 2 : 1;
        notes.push({ s: bar * 16 + s, n: base + scale[idx] + (rnd() < 0.12 ? 12 : 0), len });
        s += len;
      } else s += 1;
    }
  }
  return notes;
}

const TRACKS = {
  // Match : électro-funk énergique, La mineur
  match: {
    bpm: 128, swing: 0.03, key: 45,
    chords: [
      { r: 0, q: MINOR }, { r: 0, q: MINOR }, { r: -4, q: MAJOR }, { r: -2, q: MAJOR },
      { r: 0, q: MINOR }, { r: 0, q: MINOR }, { r: -4, q: MAJOR }, { r: -5, q: DOM },
    ],
    kick: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0],
    kickFill: [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1],
    snare: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    ghost: [0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0],
    hat: [0.5, 0.15, 0.8, 0.15, 0.5, 0.15, 0.8, 0.2, 0.5, 0.15, 0.8, 0.15, 0.5, 0.2, 0.8, 0.3],
    open: [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    bass: [
      [0, -1, -1, 0, -1, -1, 0, -1, 12, -1, 0, -1, -1, 7, -1, 10],
      [0, -1, 0, -1, 12, -1, 0, -1, 0, -1, -1, 7, 0, -1, 12, -1],
    ],
    stab: [0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0],
    arpBase: 69, lead: { seed: 7, scale: [0, 3, 5, 7, 10, 12, 15], base: 69, bars: 4, density: 0.42 },
    leadType: 'square', padVol: 0.05,
  },
  // Match 2 : plus sombre / industriel, Ré mineur, un peu plus rapide
  match2: {
    bpm: 134, swing: 0, key: 38,
    chords: [
      { r: 0, q: MINOR }, { r: 0, q: MINOR }, { r: 3, q: MAJOR }, { r: 3, q: MAJOR },
      { r: 5, q: MINOR }, { r: 5, q: MINOR }, { r: -2, q: MAJOR }, { r: -3, q: DOM },
    ],
    kick: [1, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 0, 1, 0],
    kickFill: [1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1],
    snare: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
    ghost: [0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
    hat: [0.7, 0.2, 0.4, 0.2, 0.7, 0.2, 0.4, 0.3, 0.7, 0.2, 0.4, 0.2, 0.7, 0.3, 0.4, 0.4],
    open: [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    bass: [
      [0, 0, -1, 0, -1, 0, 12, -1, 0, -1, 0, 0, -1, 7, -1, 5],
      [0, -1, 0, 12, -1, 0, -1, 7, 0, -1, 0, -1, 10, -1, 12, -1],
    ],
    stab: [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
    arpBase: 62, lead: { seed: 21, scale: [0, 2, 3, 5, 7, 8, 10, 12], base: 62, bars: 4, density: 0.36 },
    leadType: 'sawtooth', padVol: 0.06,
  },
  // Menu : groove chill, plus lent
  menu: {
    bpm: 100, swing: 0.16, key: 41,
    chords: [
      { r: 0, q: M7 }, { r: 0, q: M7 }, { r: -4, q: MAJOR }, { r: -4, q: MAJOR },
      { r: -2, q: M7 }, { r: -2, q: M7 }, { r: -3, q: DOM }, { r: -3, q: DOM },
    ],
    kick: [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
    kickFill: [1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1],
    snare: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
    ghost: [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0],
    hat: [0.5, 0, 0.3, 0, 0.5, 0, 0.3, 0, 0.5, 0, 0.3, 0, 0.5, 0, 0.3, 0.2],
    open: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    bass: [
      [0, -1, -1, 0, -1, -1, 7, -1, 0, -1, -1, 5, -1, 0, -1, -1],
      [0, -1, -1, -1, 0, -1, 12, -1, -1, 7, -1, -1, 0, -1, 3, -1],
    ],
    stab: [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0],
    arpBase: 65, lead: { seed: 3, scale: [0, 2, 3, 5, 7, 9, 10, 12], base: 65, bars: 8, density: 0.28 },
    leadType: 'triangle', padVol: 0.08,
  },
};

export class Music {
  constructor(audio) {
    this.a = audio;
    this.track = null; this.name = null;
    this.intensity = 0.4; this.tempoMul = 1;
    this.timer = null; this.playing = false;
    this.step = 0; this.bar = 0;
  }

  _ensureBuses() {
    const a = this.a, ctx = a.ctx;
    if (this.drumBus) return;
    this.fade = ctx.createGain(); this.fade.gain.value = 1; this.fade.connect(a.musicDuck);
    this.drumBus = ctx.createGain(); this.drumBus.connect(this.fade);
    this.sideBus = ctx.createGain(); this.sideBus.connect(this.fade);
    // delay noté (croche pointée) pour lead / stabs
    this.delay = ctx.createDelay(1.5); this.delay.delayTime.value = 0.35;
    this.fb = ctx.createGain(); this.fb.gain.value = 0.36;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2400;
    this.delaySend = ctx.createGain(); this.delaySend.gain.value = 1;
    this.delaySend.connect(this.delay); this.delay.connect(lp); lp.connect(this.fb); this.fb.connect(this.delay);
    lp.connect(this.fade);
  }

  play(name, { fadeIn = 0.4 } = {}) {
    const a = this.a; if (!a.ctx) return;
    if (this.name === name && this.playing) return;
    this._ensureBuses();
    this.stop(0.25, true);
    const tr = TRACKS[name]; if (!tr) return;
    this.track = tr; this.name = name;
    if (!tr._lead) tr._lead = makeLead(tr.lead.seed, tr.lead.scale, tr.lead.base, tr.lead.bars, tr.lead.density);
    this.step = 0; this.bar = 0; this.playing = true;
    const ctx = a.ctx, t = ctx.currentTime;
    this.fade.gain.cancelScheduledValues(t); this.fade.gain.setValueAtTime(0.0001, t); this.fade.gain.linearRampToValueAtTime(1, t + fadeIn);
    this.nextTime = t + 0.08;
    this.delay.delayTime.value = (60 / tr.bpm) * 0.75;
    clearInterval(this.timer);
    this.timer = setInterval(() => this._tick(), 25);
  }

  stop(fade = 0.6, immediate = false) {
    const a = this.a; if (!a.ctx || !this.fade) return;
    const t = a.ctx.currentTime;
    this.fade.gain.cancelScheduledValues(t); this.fade.gain.setValueAtTime(this.fade.gain.value, t); this.fade.gain.linearRampToValueAtTime(0.0001, t + fade);
    this.playing = false; this.name = null;
    clearInterval(this.timer); this.timer = null;
  }

  setIntensity(v) { this.intensity = Math.max(0, Math.min(1, v)); }
  setTempo(m) { this.tempoMul = m; }

  _tick() {
    const a = this.a, tr = this.track; if (!tr || !a.ctx) return;
    const ctx = a.ctx;
    if (ctx.state !== 'running') { this.nextTime = ctx.currentTime + 0.1; return; }
    let guard = 0;
    while (this.nextTime < ctx.currentTime + 0.14 && guard++ < 16) {
      this._schedule(this.step, this.nextTime, tr);
      const base = 60 / (tr.bpm * this.tempoMul) / 4;
      const sw = (this.step % 2 === 0 ? 1 + tr.swing : 1 - tr.swing);
      this.nextTime += base * sw * 1;
      this.step++;
    }
  }

  _schedule(step, t, tr) {
    const s = step % 16, bar = Math.floor(step / 16), barIdx = bar % tr.chords.length;
    const chord = tr.chords[barIdx], key = tr.key, I = this.intensity;
    const sd = 60 / (tr.bpm * this.tempoMul) / 4;
    const isFill = barIdx === tr.chords.length - 1;
    const isMenu = this.name === 'menu';
    const a = this.a;

    // --- batterie
    const kickPat = isFill ? tr.kickFill : tr.kick;
    if (kickPat[s]) {
      this._kick(t, isMenu ? 0.7 : 1);
      // sidechain : les couches harmoniques "respirent" avec le kick
      const g = this.sideBus.gain; g.cancelScheduledValues(t); g.setValueAtTime(isMenu ? 0.6 : 0.3, t); g.linearRampToValueAtTime(1, t + sd * 2.2);
    }
    if (tr.snare[s]) this._snare(t, 1);
    else if (tr.ghost[s] && (I > 0.25 || isMenu) && bar % 2 === 1) this._snare(t, 0.28, true);
    const h = tr.hat[s];
    if (h > 0 && (I > 0.05 || isMenu)) { if (h >= 0.5 || I > 0.3) this._hat(t, h * (0.6 + I * 0.5), false); }
    if (tr.open[s] && (I > 0.35 || isMenu)) this._hat(t, 0.55, true);
    if (I > 0.7 && s % 4 === 2 && !isMenu) this._clap(t, 0.5);
    if (isFill && s >= 12 && !isMenu) this._tom(t, 200 - (s - 12) * 25, 0.5);
    if (bar % 8 === 0 && s === 0 && bar > 0 && !isMenu) this._crash(t);

    // --- basse
    const bp = tr.bass[Math.floor(bar / 2) % tr.bass.length];
    const bn = bp[s];
    if (bn >= 0) this._bass(t, key + chord.r + bn, sd * (isMenu ? 2.2 : 1.7), isMenu ? 0.32 : 0.42);

    // --- accords (stabs)
    if (tr.stab[s] && (I > 0.15 || isMenu)) this._stab(t, key + 12 + chord.r, chord.q, sd * 2.2, isMenu ? 0.05 : 0.07);

    // --- nappe
    if (s === 0 && tr.padVol) this._pad(t, key + 24 + chord.r, chord.q, sd * 16, tr.padVol);

    // --- arpège (intensité)
    if ((I > 0.55 || isMenu) && (isMenu ? s % 2 === 0 : true)) {
      const ct = chord.q, pat = [0, 1, 2, 3, 2, 1, 2, 3];
      const n = tr.arpBase + chord.r + ct[pat[s % 8] % ct.length] + (s % 8 > 5 ? 12 : 0);
      this._pluck(t, n, sd * 1.5, isMenu ? 0.06 : 0.045 * Math.min(1, I + 0.2));
    }

    // --- lead
    const lead = tr._lead, leadLen = tr.lead.bars * 16;
    const showLead = isMenu ? bar % 8 >= 2 : (I > 0.3 && (bar % 4 >= 2 || I > 0.7));
    if (showLead) {
      const pos = step % leadLen;
      for (const n of lead) if (n.s === pos) this._lead(t, n.n + chord.r * 0, sd * n.len * 0.95, isMenu ? 0.07 : 0.085, tr.leadType);
    }
  }

  // ---- voix -----------------------------------------------------------
  _kick(t, v = 1) {
    const a = this.a, d = this.drumBus;
    a.tone({ at: t, type: 'sine', f: 165, f1: 44, slide: 0.11, dur: 0.34, vol: 0.85 * v, a: 0.001, dest: d, music: true });
    a.tone({ at: t, type: 'triangle', f: 90, f1: 40, dur: 0.12, vol: 0.28 * v, a: 0.001, dest: d, music: true });
    a.noise({ at: t, f: 3500, q: 1, dur: 0.012, vol: 0.2 * v, a: 0.0005, dest: d, music: true });
  }
  _snare(t, v = 1, ghost = false) {
    const a = this.a, d = this.drumBus;
    a.noise({ at: t, f: 2100, q: 0.7, dur: ghost ? 0.07 : 0.2, vol: 0.34 * v, dest: d, music: true, rev: ghost ? 0 : 0.18 });
    a.tone({ at: t, type: 'triangle', f: 210, f1: 140, dur: 0.11, vol: 0.32 * v, dest: d, music: true });
    if (!ghost) a.noise({ at: t, f: 6000, q: 0.5, ftype: 'highpass', dur: 0.14, vol: 0.14, dest: d, music: true });
  }
  _clap(t, v = 1) {
    const a = this.a, d = this.drumBus;
    for (let i = 0; i < 3; i++) a.noise({ at: t + i * 0.011, f: 1300, q: 1.1, dur: i === 2 ? 0.16 : 0.03, vol: 0.2 * v, dest: d, music: true, rev: 0.25 });
  }
  _hat(t, v, open) {
    const a = this.a, d = this.drumBus;
    a.noise({ at: t, f: 9000, q: 0.6, ftype: 'highpass', dur: open ? 0.2 : 0.045, vol: (open ? 0.1 : 0.12) * v, dest: d, music: true, a: 0.001 });
  }
  _tom(t, f, v) {
    const a = this.a;
    a.tone({ at: t, type: 'sine', f, f1: f * 0.55, dur: 0.22, vol: 0.4 * v, dest: this.drumBus, music: true });
  }
  _crash(t) { this.a.noise({ at: t, f: 7000, q: 0.5, ftype: 'highpass', dur: 1.4, vol: 0.14, dest: this.drumBus, music: true, rev: 0.4 }); }

  _bass(t, midi, dur, vol) {
    const a = this.a, f = NOTE(midi);
    a.tone({ at: t, type: 'sawtooth', f, dur, vol, a: 0.004, lp: 1400, lp1: 220, q: 5, dest: this.sideBus, music: true });
    a.tone({ at: t, type: 'square', f: f / 2, dur, vol: vol * 0.7, a: 0.004, lp: 400, dest: this.sideBus, music: true });
  }
  _stab(t, root, q, dur, vol) {
    const a = this.a;
    for (const iv of q) {
      const f = NOTE(root + iv);
      a.tone({ at: t, type: 'sawtooth', f, dur, vol, a: 0.004, lp: 3800, lp1: 500, q: 2, detune: -6, dest: this.sideBus, music: true, rev: 0.3 });
      a.tone({ at: t, type: 'sawtooth', f, dur, vol: vol * 0.8, a: 0.004, lp: 3800, lp1: 500, q: 2, detune: 7, dest: this.sideBus, music: true });
    }
  }
  _pad(t, root, q, dur, vol) {
    const a = this.a;
    for (const iv of q) {
      a.tone({ at: t, type: 'sawtooth', f: NOTE(root + iv), dur: dur * 1.02, vol, a: dur * 0.3, hold: dur * 0.4, lp: 1100, q: 0.6, detune: (Math.random() - 0.5) * 12, dest: this.sideBus, music: true, rev: 0.6 });
    }
  }
  _pluck(t, midi, dur, vol) {
    const a = this.a;
    a.tone({ at: t, type: 'triangle', f: NOTE(midi + 12), dur: dur * 1.2, vol, a: 0.002, lp: 4500, lp1: 900, dest: this.sideBus, music: true, rev: 0.35 });
    a.tone({ at: t, type: 'square', f: NOTE(midi + 12), dur: dur, vol: vol * 0.35, a: 0.002, lp: 2500, lp1: 700, dest: this.sideBus, music: true });
  }
  _lead(t, midi, dur, vol, type) {
    const a = this.a, f = NOTE(midi);
    const o = { at: t, type, f, dur: Math.max(dur, 0.09), vol, a: 0.01, lp: 3600, lp1: 1600, q: 2, vib: { rate: 5.5, depth: 5 }, dest: this.sideBus, music: true, rev: 0.4 };
    a.tone(o);
    a.tone({ ...o, type: 'sawtooth', vol: vol * 0.45, detune: 9, vib: null });
    // écho : via sortie retardée (bus delay)
    a.tone({ at: t, type: 'sine', f: f * 2, dur: dur * 0.8, vol: vol * 0.2, dest: this.delaySend, music: true });
  }

  // ---- jingles (un seul coup, par-dessus le mix) ------------------------
  jingle(name) {
    const a = this.a; if (!a.ctx) return;
    this._ensureBuses();
    const t = a.ctx.currentTime + 0.05, d = this.fade;
    const T = (n, when, dur, vol = 0.14, type = 'sawtooth') => a.tone({ at: t, when, type, f: NOTE(n), dur, vol, lp: 3200, lp1: 1200, dest: a.musicDuck, music: true, rev: 0.4, detune: (Math.random() - 0.5) * 10 });
    if (name === 'win') {
      const seq = [[60, 0, 0.18], [64, 0.16, 0.18], [67, 0.32, 0.18], [72, 0.48, 0.5], [67, 0.9, 0.16], [72, 1.06, 0.16], [76, 1.22, 0.9]];
      for (const [n, w, du] of seq) { T(n, w, du); T(n + 7, w, du, 0.08); T(n - 12, w, du, 0.1, 'square'); }
      [0, 4, 7].forEach((iv) => T(72 + iv, 1.22, 1.4, 0.07));
      a.noise({ at: t, when: 1.22, f: 7000, q: 0.5, ftype: 'highpass', dur: 1.5, vol: 0.12, dest: a.musicDuck, music: true, rev: 0.5 });
    } else if (name === 'lose') {
      [[64, 0, 0.35], [62, 0.35, 0.35], [60, 0.7, 0.35], [57, 1.05, 1.1]].forEach(([n, w, du]) => { T(n, w, du, 0.12, 'triangle'); T(n - 12, w, du, 0.1, 'square'); });
    } else if (name === 'draw') {
      [[62, 0, 0.3], [65, 0.3, 0.3], [62, 0.6, 0.9]].forEach(([n, w, du]) => { T(n, w, du, 0.12, 'triangle'); });
    } else if (name === 'halftime') {
      [[69, 0, 0.14], [72, 0.14, 0.14], [76, 0.28, 0.4], [72, 0.6, 0.14], [69, 0.74, 0.5]].forEach(([n, w, du]) => { T(n, w, du, 0.11, 'square'); });
    } else if (name === 'intro') {
      [[57, 0, 0.12], [57, 0.14, 0.12], [64, 0.28, 0.12], [69, 0.42, 0.7]].forEach(([n, w, du]) => { T(n, w, du, 0.13); T(n - 12, w, du, 0.14, 'square'); });
    }
  }
}
