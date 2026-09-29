// Fully procedural audio engine: master bus, arena reverb, synthesized SFX and crowd.
import { rand, clamp } from '../core/math.js';

class AudioEngine {
  constructor() {
    this.ctx = null;
    this.ready = false;
    this.musicVol = 0.55;
    this.sfxVol = 0.75;
    this.lastPlay = new Map();
  }

  init() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC({ latencyHint: 'interactive' }));

    this.master = ctx.createGain();
    this.master.gain.value = 0.8;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -14;
    comp.knee.value = 10;
    comp.ratio.value = 5;
    comp.attack.value = 0.003;
    comp.release.value = 0.18;
    // Soft clipper after the compressor: glues everything and keeps peaks round.
    const clip = ctx.createWaveShaper();
    clip.curve = this.makeCurve('soft', 1.2);
    this.master.connect(comp).connect(clip).connect(ctx.destination);

    this.musicBus = ctx.createGain();
    this.musicBus.gain.value = this.musicVol;
    this.musicBus.connect(this.master);
    // Music is ducked under big impacts.
    this.duck = ctx.createGain();
    this.duck.connect(this.musicBus);

    this.sfxBus = ctx.createGain();
    this.sfxBus.gain.value = this.sfxVol;
    this.sfxBus.connect(this.master);

    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this.makeImpulse(2.8, 2.6);
    this.reverbSend = ctx.createGain();
    this.reverbSend.gain.value = 0.9;
    this.reverbSend.connect(this.reverb).connect(this.master);

    this.noiseBuf = this.makeNoise('white', 2);
    this.pinkBuf = this.makeNoise('pink', 4);
    this.brownBuf = this.makeNoise('brown', 4);
    this.distCurve = this.makeCurve('hard', 30);
    this.crunchCurve = this.makeCurve('hard', 80);

    this.startCrowd();
    this.ready = true;
  }

  get now() {
    return this.ctx ? this.ctx.currentTime : 0;
  }

  makeCurve(type, amount) {
    const n = 2048, c = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1;
      if (type === 'soft') c[i] = Math.tanh(x * amount) / Math.tanh(amount);
      else c[i] = ((1 + amount) * x) / (1 + amount * Math.abs(x));
    }
    return c;
  }

  makeNoise(kind, seconds) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, last = 0;
      for (let i = 0; i < len; i++) {
        const w = Math.random() * 2 - 1;
        if (kind === 'white') d[i] = w;
        else if (kind === 'pink') {
          b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759;
          b2 = 0.969 * b2 + w * 0.153852; b3 = 0.8665 * b3 + w * 0.3104856;
          b4 = 0.55 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.016898;
          d[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11;
          b6 = w * 0.115926;
        } else {
          last = (last + 0.02 * w) / 1.02;
          d[i] = last * 3.5;
        }
      }
    }
    return buf;
  }

  makeImpulse(seconds, decay) {
    const ctx = this.ctx;
    const len = Math.floor(ctx.sampleRate * seconds);
    const buf = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) {
        const t = i / len;
        // Early metallic reflections + dense diffuse tail.
        const early = i < ctx.sampleRate * 0.08 && Math.random() < 0.004 ? (Math.random() * 2 - 1) * 1.5 : 0;
        d[i] = ((Math.random() * 2 - 1) * Math.pow(1 - t, decay) + early) * 0.5;
      }
    }
    return buf;
  }

  setMusicVolume(v) {
    this.musicVol = v;
    if (this.musicBus) this.musicBus.gain.setTargetAtTime(v, this.now, 0.05);
  }

  /** Temporarily lowers the music under a big event. */
  duckMusic(amount = 0.4, time = 0.6) {
    if (!this.ctx) return;
    const g = this.duck.gain, t = this.now;
    g.cancelScheduledValues(t);
    g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(1 - amount, t + 0.03);
    g.setTargetAtTime(1, t + time * 0.4, time * 0.5);
  }

  // ---------- building blocks ----------
  out(pan = 0, reverb = 0.2) {
    const ctx = this.ctx;
    const g = ctx.createGain();
    const p = ctx.createStereoPanner();
    p.pan.value = clamp(pan, -1, 1);
    g.connect(p).connect(this.sfxBus);
    if (reverb > 0) {
      const s = ctx.createGain();
      s.gain.value = reverb;
      p.connect(s).connect(this.reverbSend);
    }
    return g;
  }

  env(param, t, a, peak, d, sustain = 0.0001) {
    param.cancelScheduledValues(t);
    param.setValueAtTime(0.0001, t);
    param.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t + a);
    param.exponentialRampToValueAtTime(Math.max(sustain, 0.0001), t + a + d);
  }

  noise(dest, t, dur, { buf, type = 'bandpass', f = 1000, f2 = null, q = 1, gain = 1, a = 0.002, rate = 1 } = {}) {
    const ctx = this.ctx;
    const src = ctx.createBufferSource();
    src.buffer = buf || this.noiseBuf;
    src.playbackRate.value = rate;
    src.loop = true;
    const filt = ctx.createBiquadFilter();
    filt.type = type;
    filt.frequency.setValueAtTime(f, t);
    if (f2) filt.frequency.exponentialRampToValueAtTime(f2, t + dur);
    filt.Q.value = q;
    const g = ctx.createGain();
    this.env(g.gain, t, a, gain, dur);
    src.connect(filt).connect(g).connect(dest);
    src.start(t, Math.random() * 1.5);
    src.stop(t + a + dur + 0.05);
    return { src, filt, g };
  }

  tone(dest, t, dur, { type = 'sine', f = 440, f2 = null, gain = 0.5, a = 0.002, curve = 'exp', detune = 0 } = {}) {
    const ctx = this.ctx;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(f, t);
    o.detune.value = detune;
    if (f2) {
      if (curve === 'exp') o.frequency.exponentialRampToValueAtTime(f2, t + dur);
      else o.frequency.linearRampToValueAtTime(f2, t + dur);
    }
    const g = ctx.createGain();
    this.env(g.gain, t, a, gain, dur);
    o.connect(g).connect(dest);
    o.start(t);
    o.stop(t + a + dur + 0.05);
    return { o, g };
  }

  shaper(dest, curve) {
    const ws = this.ctx.createWaveShaper();
    ws.curve = curve || this.distCurve;
    ws.oversample = '2x';
    ws.connect(dest);
    return ws;
  }

  /** Rate limiter so a burst of events doesn't turn into mush. */
  gate(key, minGap) {
    const t = performance.now();
    if (t - (this.lastPlay.get(key) || 0) < minGap * 1000) return false;
    this.lastPlay.set(key, t);
    return true;
  }

  // ---------- SFX ----------
  play(name, opts = {}) {
    if (!this.ready || this.ctx.state !== 'running') return;
    const fn = this['sfx_' + name];
    if (fn) fn.call(this, opts);
  }

  sfx_hit({ power = 1, pan = 0 } = {}) {
    if (!this.gate('hit', 0.04)) return;
    const t = this.now, o = this.out(pan, 0.25);
    o.gain.value = 0.9 * clamp(power, 0.4, 1.4);
    // Sub thump
    this.tone(o, t, 0.22, { f: 140, f2: 38, gain: 1.1 });
    // Crunch: distorted band noise
    const crunch = this.shaper(o, this.crunchCurve);
    this.noise(crunch, t, 0.12, { f: 1400, f2: 500, q: 0.8, gain: 0.35 });
    // Bone crack clicks
    for (let i = 0; i < 3; i++) {
      this.noise(o, t + 0.01 + i * rand(0.008, 0.022), 0.02, { type: 'highpass', f: 2500, gain: 0.5 * power });
    }
    // Armour rattle
    this.metal(o, t + 0.005, rand(420, 700), 0.25, 0.18);
    this.duckMusic(0.25 * power, 0.35);
  }

  sfx_ko({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.45);
    this.tone(o, t, 0.5, { f: 110, f2: 28, gain: 1.2 });
    const crunch = this.shaper(o, this.crunchCurve);
    this.noise(crunch, t, 0.3, { f: 900, f2: 180, q: 0.6, gain: 0.45 });
    this.metal(o, t, 260, 0.6, 0.35);
    this.crowdReact(0.9, 'ooh');
    this.duckMusic(0.5, 0.8);
  }

  metal(dest, t, f, dur, gain) {
    const ratios = [1, 2.76, 5.4, 8.93, 13.34];
    ratios.forEach((r, i) => {
      this.tone(dest, t, dur / (1 + i * 0.6), { f: f * r * rand(0.99, 1.01), gain: gain / (1 + i * 0.8), type: 'sine' });
    });
  }

  sfx_clank({ power = 1, pan = 0 } = {}) {
    if (!this.gate('clank', 0.05)) return;
    const t = this.now, o = this.out(pan, 0.35);
    o.gain.value = clamp(power, 0.2, 1);
    this.metal(o, t, rand(380, 620), 0.5, 0.45);
    this.noise(o, t, 0.03, { type: 'highpass', f: 3000, gain: 0.8 });
    this.tone(o, t, 0.08, { f: 90, f2: 50, gain: 0.5 });
  }

  sfx_bumper({ pan = 0 } = {}) {
    if (!this.gate('bumper', 0.06)) return;
    const t = this.now, o = this.out(pan, 0.4);
    const ctx = this.ctx;
    // FM "boing" with metallic ring
    const car = ctx.createOscillator(), mod = ctx.createOscillator(), mg = ctx.createGain(), g = ctx.createGain();
    car.frequency.setValueAtTime(420, t);
    car.frequency.exponentialRampToValueAtTime(180, t + 0.35);
    mod.frequency.setValueAtTime(630, t);
    mod.frequency.exponentialRampToValueAtTime(260, t + 0.35);
    mg.gain.setValueAtTime(600, t);
    mg.gain.exponentialRampToValueAtTime(10, t + 0.4);
    this.env(g.gain, t, 0.002, 0.5, 0.45);
    mod.connect(mg).connect(car.frequency);
    car.connect(g).connect(o);
    car.start(t); mod.start(t); car.stop(t + 0.6); mod.stop(t + 0.6);
    this.metal(o, t, 880, 0.4, 0.15);
  }

  sfx_throw({ power = 1, pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.15);
    this.noise(o, t, 0.22 + power * 0.1, { f: 500, f2: 2600 + power * 1500, q: 1.5, gain: 0.35 + power * 0.25, a: 0.02 });
    this.tone(o, t, 0.08, { f: 200, f2: 90, gain: 0.25 });
  }

  sfx_lob({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.2);
    this.noise(o, t, 0.45, { f: 300, f2: 1400, q: 2, gain: 0.35, a: 0.05 });
    this.tone(o, t, 0.1, { f: 160, f2: 70, gain: 0.3 });
  }

  sfx_catch({ pan = 0 } = {}) {
    if (!this.gate('catch', 0.05)) return;
    const t = this.now, o = this.out(pan, 0.1);
    this.noise(o, t, 0.06, { type: 'lowpass', f: 1200, gain: 0.7 });
    this.tone(o, t, 0.09, { f: 180, f2: 80, gain: 0.5 });
    this.metal(o, t, 1300, 0.08, 0.06);
  }

  sfx_slide({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.15);
    const n = this.noise(o, t, 0.42, { f: 1800, f2: 700, q: 1.2, gain: 0.35, a: 0.01 });
    // Grit: amplitude jitter
    const lfo = this.ctx.createOscillator(), lg = this.ctx.createGain();
    lfo.frequency.value = 38; lg.gain.value = 0.15;
    lfo.connect(lg).connect(n.g.gain);
    lfo.start(t); lfo.stop(t + 0.5);
    this.noise(o, t, 0.3, { buf: this.brownBuf, type: 'lowpass', f: 400, gain: 0.5 });
  }

  sfx_jump({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.05);
    this.noise(o, t, 0.12, { buf: this.pinkBuf, type: 'bandpass', f: 500, f2: 900, q: 2, gain: 0.3 });
  }

  sfx_land({ pan = 0 } = {}) {
    if (!this.gate('land', 0.08)) return;
    const t = this.now, o = this.out(pan, 0.05);
    this.noise(o, t, 0.08, { type: 'lowpass', f: 500, gain: 0.35 });
  }

  sfx_zap({ pan = 0, long = false } = {}) {
    if (!this.gate('zap', 0.08)) return;
    const t = this.now, o = this.out(pan, 0.3);
    const dur = long ? 0.9 : 0.35;
    const buzz = this.shaper(o, this.distCurve);
    const ctx = this.ctx;
    const saw = ctx.createOscillator(), g = ctx.createGain();
    saw.type = 'sawtooth';
    saw.frequency.setValueAtTime(95, t);
    const lfo = ctx.createOscillator(), lg = ctx.createGain();
    lfo.type = 'square'; lfo.frequency.value = 23; lg.gain.value = 60;
    lfo.connect(lg).connect(saw.frequency);
    this.env(g.gain, t, 0.005, 0.18, dur);
    saw.connect(g).connect(buzz);
    saw.start(t); lfo.start(t); saw.stop(t + dur + 0.1); lfo.stop(t + dur + 0.1);
    for (let i = 0; i < (long ? 14 : 6); i++) {
      this.noise(o, t + rand(0, dur), rand(0.01, 0.04), { type: 'highpass', f: rand(2500, 6000), gain: rand(0.3, 0.7) });
    }
  }

  sfx_electrify({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.4);
    this.tone(o, t, 0.5, { type: 'sawtooth', f: 200, f2: 1800, gain: 0.12 });
    this.tone(o, t, 0.5, { type: 'square', f: 203, f2: 1810, gain: 0.08 });
    this.sfx_zap({ pan });
  }

  sfx_star({ pan = 0, team = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.4);
    const base = team === 0 ? 660 : 587;
    [0, 4, 7, 12].forEach((s, i) => {
      this.tone(o, t + i * 0.045, 0.18, { type: 'square', f: base * Math.pow(2, s / 12), gain: 0.09 });
    });
    this.metal(o, t, 1500, 0.4, 0.08);
  }

  sfx_starbonus() {
    const t = this.now, o = this.out(0, 0.5);
    for (let i = 0; i < 10; i++) {
      this.tone(o, t + i * 0.06, 0.25, { type: 'square', f: 440 * Math.pow(2, [0, 3, 7, 10, 12, 15, 19, 22, 24, 27][i] / 12), gain: 0.08 });
    }
    this.crowdReact(0.8, 'cheer');
  }

  sfx_multiplier() {
    const t = this.now, o = this.out(0, 0.5);
    this.tone(o, t, 0.7, { type: 'sawtooth', f: 110, f2: 880, gain: 0.15 });
    this.tone(o, t, 0.7, { type: 'sawtooth', f: 111, f2: 890, gain: 0.15, detune: 12 });
    [0, 7, 12, 19].forEach((s, i) => this.tone(o, t + 0.5 + i * 0.07, 0.3, { type: 'square', f: 440 * Math.pow(2, s / 12), gain: 0.07 }));
  }

  sfx_token() {
    const t = this.now, o = this.out(0, 0.3);
    [0, 12, 7, 19].forEach((s, i) => this.tone(o, t + i * 0.05, 0.22, { type: 'triangle', f: 880 * Math.pow(2, s / 12), gain: 0.25 }));
    this.metal(o, t, 2000, 0.3, 0.06);
  }

  sfx_powerdown() {
    const t = this.now, o = this.out(0, 0.3);
    this.tone(o, t, 0.6, { type: 'sawtooth', f: 800, f2: 60, gain: 0.15 });
  }

  sfx_beep({ high = false } = {}) {
    const t = this.now, o = this.out(0, 0.3);
    const f = high ? 1320 : 660;
    this.tone(o, t, high ? 0.5 : 0.18, { type: 'square', f, gain: 0.12 });
    this.tone(o, t, high ? 0.5 : 0.18, { type: 'square', f: f * 1.005, gain: 0.12 });
    this.metal(o, t, f / 2, 0.2, 0.05);
  }

  sfx_launch() {
    const t = this.now, o = this.out(0, 0.5);
    // Pneumatic cannon: hiss + boom + rising whistle
    this.noise(o, t, 0.4, { f: 3000, f2: 800, q: 0.7, gain: 0.5 });
    this.tone(o, t, 0.4, { f: 90, f2: 30, gain: 1 });
    this.noise(this.shaper(o), t, 0.2, { buf: this.brownBuf, type: 'lowpass', f: 300, gain: 0.8 });
    this.tone(o, t + 0.05, 0.6, { type: 'sine', f: 600, f2: 1600, gain: 0.08 });
    this.crowdReact(0.5, 'cheer');
  }

  sfx_whistle({ long = false } = {}) {
    const t = this.now, o = this.out(0, 0.4);
    const ctx = this.ctx;
    const reps = long ? 3 : 1;
    for (let r = 0; r < reps; r++) {
      const st = t + r * 0.32;
      const dur = long && r === reps - 1 ? 0.7 : 0.22;
      const osc = ctx.createOscillator(), g = ctx.createGain();
      osc.frequency.value = 2900;
      const lfo = ctx.createOscillator(), lg = ctx.createGain();
      lfo.frequency.value = 32; lg.gain.value = 140;
      lfo.connect(lg).connect(osc.frequency);
      g.gain.setValueAtTime(0.0001, st);
      g.gain.exponentialRampToValueAtTime(0.22, st + 0.02);
      g.gain.setValueAtTime(0.22, st + dur);
      g.gain.exponentialRampToValueAtTime(0.0001, st + dur + 0.05);
      osc.connect(g).connect(o);
      osc.start(st); lfo.start(st); osc.stop(st + dur + 0.1); lfo.stop(st + dur + 0.1);
      this.noise(o, st, dur, { f: 3000, q: 3, gain: 0.05 });
    }
  }

  sfx_explosion({ big = true, pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.6);
    const d = this.shaper(o, this.crunchCurve);
    this.noise(d, t, big ? 1.6 : 0.6, { buf: this.brownBuf, type: 'lowpass', f: 2000, f2: 60, q: 0.5, gain: 0.5 });
    this.tone(o, t, big ? 1.1 : 0.4, { f: 70, f2: 22, gain: 0.9 });
    this.noise(o, t, 0.5, { f: 1500, f2: 200, q: 0.4, gain: 0.5 });
    for (let i = 0; i < 8; i++) this.metal(o, t + rand(0.05, 0.8), rand(600, 1800), 0.3, 0.05);
    this.duckMusic(0.7, 1.5);
  }

  sfx_goal({ pan = 0 } = {}) {
    this.sfx_explosion({ big: true, pan });
    const t = this.now, o = this.out(0, 0.5);
    // Siren: two detuned saws wailing
    const ctx = this.ctx;
    for (const det of [0, 9]) {
      const s = ctx.createOscillator(), g = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
      s.type = 'sawtooth';
      s.frequency.value = 520;
      s.detune.value = det;
      lfo.frequency.value = 1.6;
      lg.gain.value = 240;
      lfo.connect(lg).connect(s.frequency);
      const f = ctx.createBiquadFilter();
      f.type = 'lowpass'; f.frequency.value = 2400;
      g.gain.setValueAtTime(0.0001, t + 0.15);
      g.gain.exponentialRampToValueAtTime(0.07, t + 0.3);
      g.gain.setValueAtTime(0.07, t + 2.2);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 2.8);
      s.connect(f).connect(g).connect(o);
      s.start(t); lfo.start(t); s.stop(t + 3); lfo.stop(t + 3);
    }
    this.crowdReact(1.4, 'cheer');
  }

  sfx_ui({ kind = 'move' } = {}) {
    const t = this.now, o = this.out(0, 0.15);
    if (kind === 'move') {
      this.tone(o, t, 0.06, { type: 'square', f: 440, gain: 0.06 });
      this.metal(o, t, 1100, 0.1, 0.05);
    } else if (kind === 'select') {
      this.tone(o, t, 0.25, { type: 'sawtooth', f: 220, f2: 880, gain: 0.1 });
      this.metal(o, t, 500, 0.35, 0.15);
      this.tone(o, t, 0.2, { f: 100, f2: 40, gain: 0.6 });
    } else {
      this.tone(o, t, 0.15, { type: 'square', f: 330, f2: 160, gain: 0.08 });
    }
  }

  sfx_flame({ pan = 0 } = {}) {
    const t = this.now, o = this.out(pan, 0.3);
    this.noise(o, t, 0.9, { buf: this.brownBuf, type: 'lowpass', f: 800, f2: 300, gain: 0.7, a: 0.05 });
    this.noise(o, t, 0.7, { f: 2500, f2: 900, q: 0.5, gain: 0.15, a: 0.05 });
  }

  // ---------- crowd ----------
  startCrowd() {
    const ctx = this.ctx;
    this.crowdGain = ctx.createGain();
    this.crowdGain.gain.value = 0.0;
    this.crowdGain.connect(this.master);
    const rev = ctx.createGain();
    rev.gain.value = 0.4;
    this.crowdGain.connect(rev).connect(this.reverbSend);
    // Crowd murmur: pink noise through vowel-ish formants, slowly modulated.
    const src = ctx.createBufferSource();
    src.buffer = this.pinkBuf;
    src.loop = true;
    const formants = [
      [420, 4, 0.9], [900, 5, 0.5], [2400, 6, 0.18],
    ];
    const sum = ctx.createGain();
    for (const [f, q, g] of formants) {
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = q;
      const gg = ctx.createGain(); gg.gain.value = g;
      src.connect(bp).connect(gg).connect(sum);
      const lfo = ctx.createOscillator(), lg = ctx.createGain();
      lfo.frequency.value = rand(0.1, 0.35);
      lg.gain.value = f * 0.12;
      lfo.connect(lg).connect(bp.frequency);
      lfo.start();
    }
    const trem = ctx.createGain();
    trem.gain.value = 0.8;
    const lfo = ctx.createOscillator(), lg = ctx.createGain();
    lfo.frequency.value = 0.23; lg.gain.value = 0.2;
    lfo.connect(lg).connect(trem.gain);
    lfo.start();
    sum.connect(trem).connect(this.crowdGain);
    src.start();
    this.crowdLevel = 0;
  }

  setCrowd(level) {
    if (!this.ready) return;
    level = clamp(level, 0, 1.5);
    if (Math.abs(level - this.crowdLevel) < 0.01) return;
    this.crowdLevel = level;
    this.crowdGain.gain.setTargetAtTime(0.08 + level * 0.35, this.now, 0.4);
  }

  crowdReact(amount = 1, kind = 'cheer') {
    if (!this.ready || !this.gate('crowd' + kind, 0.3)) return;
    const t = this.now, ctx = this.ctx;
    const o = ctx.createGain();
    o.connect(this.master);
    const rs = ctx.createGain(); rs.gain.value = 0.6; o.connect(rs).connect(this.reverbSend);
    const dur = kind === 'ooh' ? 1.3 : 2.4 * amount;
    const vowels = kind === 'ooh' ? [[350, 600], [700, 900]] : [[750, 1100], [1200, 1700], [2600, 2900]];
    for (const [f1, f2] of vowels) {
      const src = ctx.createBufferSource();
      src.buffer = this.pinkBuf; src.loop = true;
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass'; bp.Q.value = 3.5;
      bp.frequency.setValueAtTime(kind === 'ooh' ? f2 : f1, t);
      bp.frequency.linearRampToValueAtTime(kind === 'ooh' ? f1 : f2, t + dur * 0.5);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(0.5 * amount, t + (kind === 'ooh' ? 0.15 : 0.25));
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      src.connect(bp).connect(g).connect(o);
      src.start(t, Math.random() * 3);
      src.stop(t + dur + 0.1);
    }
  }
}

export const audio = new AudioEngine();
