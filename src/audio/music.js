// Procedural soundtrack: war drums + distorted guitar chugs + grinding bass + synth lead.
// A lookahead scheduler plays pattern-based sections whose layers follow the game intensity.
import { audio } from './audio.js';
import { rand } from '../core/math.js';

const midi = (n) => 440 * Math.pow(2, (n - 69) / 12);

// E phrygian flavoured riffs (E F G A B C D). -1 = rest, values are semitone offsets from E1 (MIDI 28).
const RIFFS = [
  [0, 0, -1, 0, 0, -1, 1, 0, 0, 0, -1, 0, 3, -1, 1, -1],
  [0, 0, 0, -1, 0, 0, 7, -1, 0, 0, 0, -1, 5, -1, 3, 1],
  [0, -1, 0, 0, 12, -1, 0, 0, 10, -1, 0, 0, 8, -1, 7, -1],
  [0, 0, -1, 0, 1, -1, 0, 0, 3, -1, 1, 0, -1, 0, 5, 3],
];
const LEADS = [
  [12, -1, -1, 15, -1, 13, -1, 12, -1, -1, 10, -1, 12, -1, -1, -1],
  [19, -1, 17, -1, 15, -1, 13, -1, 15, -1, -1, 12, -1, -1, -1, -1],
  [24, -1, 22, 20, -1, 19, -1, 17, 19, -1, 20, -1, 22, -1, 19, -1],
  [12, 13, 15, -1, 13, 12, -1, 10, 12, -1, -1, -1, 7, -1, 8, -1],
];
// Chord roots per bar for the song form (semitones from E).
const PROGRESSIONS = [[0, 0, 1, 0], [0, 0, 3, 1], [0, 5, 3, 1], [0, 1, 0, -2]];

class Music {
  constructor() {
    this.playing = false;
    this.mode = 'menu';
    this.intensity = 0.5;
    this.bpm = 132;
    this.step = 0;
    this.bar = 0;
    this.nextTime = 0;
    this.timer = null;
    this.riff = 0;
    this.lead = 0;
    this.prog = 0;
    this.fill = false;
  }

  start(mode = 'menu') {
    audio.init();
    if (!audio.ready) return;
    this.setMode(mode);
    if (this.playing) return;
    this.playing = true;
    const ctx = audio.ctx;
    this.out = ctx.createGain();
    this.out.gain.value = 0.85;
    this.out.connect(audio.duck);
    // Stereo feedback delay for lead/guitar tails
    this.delay = ctx.createDelay(1.5);
    this.delay.delayTime.value = (60 / this.bpm) * 0.75;
    const fb = ctx.createGain(); fb.gain.value = 0.35;
    const dl = ctx.createBiquadFilter(); dl.type = 'lowpass'; dl.frequency.value = 2500;
    this.delay.connect(dl).connect(fb).connect(this.delay);
    this.delayOut = ctx.createGain(); this.delayOut.gain.value = 0.5;
    dl.connect(this.delayOut).connect(this.out);
    this.rev = ctx.createGain(); this.rev.gain.value = 0.5;
    this.rev.connect(audio.reverbSend);
    // Global filter for "muffled" states (pause, halftime)
    this.nextTime = ctx.currentTime + 0.1;
    this.step = 0;
    this.bar = 0;
    this.timer = setInterval(() => this.schedule(), 25);
  }

  stop() {
    this.playing = false;
    clearInterval(this.timer);
    if (this.out) {
      const t = audio.now;
      this.out.gain.setTargetAtTime(0.0001, t, 0.2);
      const o = this.out;
      setTimeout(() => o.disconnect(), 1500);
    }
  }

  setMode(mode) {
    if (this.mode === mode) return;
    this.mode = mode;
    this.bpm = mode === 'menu' ? 104 : mode === 'results' ? 96 : 138;
    if (this.delay) this.delay.delayTime.setTargetAtTime((60 / this.bpm) * 0.75, audio.now, 0.1);
    this.fill = true;
  }

  setIntensity(v) {
    this.intensity = Math.max(0, Math.min(1, v));
  }

  schedule() {
    if (!this.playing || !audio.ctx) return;
    const ctx = audio.ctx;
    if (this.nextTime < ctx.currentTime - 0.2) this.nextTime = ctx.currentTime + 0.05; // resync after stall
    while (this.nextTime < ctx.currentTime + 0.12) {
      this.playStep(this.step, this.nextTime);
      const sixteenth = 60 / this.bpm / 4;
      // slight swing on off-beats for groove
      this.nextTime += sixteenth * (this.step % 2 === 0 ? 1.04 : 0.96);
      this.step++;
      if (this.step >= 16) {
        this.step = 0;
        this.bar++;
        if (this.bar % 4 === 0) this.newPhrase();
      }
    }
  }

  newPhrase() {
    this.riff = Math.floor(rand(0, RIFFS.length));
    this.lead = Math.floor(rand(0, LEADS.length));
    this.prog = Math.floor(rand(0, PROGRESSIONS.length));
  }

  playStep(s, t) {
    const I = this.intensity;
    const barInPhrase = this.bar % 4;
    const root = PROGRESSIONS[this.prog][barInPhrase];
    const lastBar = barInPhrase === 3;
    const mode = this.mode;

    if (mode === 'menu' || mode === 'results') {
      // Slow ritual: war toms, drone, sparse metallic hits.
      if (s === 0 || s === 6 || s === 10) this.tom(t, s === 0 ? 70 : 95, 0.9);
      if (s === 12 && barInPhrase % 2 === 1) this.tom(t, 120, 0.6);
      if (s === 0 && barInPhrase === 0) this.drone(t, 28 + root, (60 / this.bpm) * 16);
      if (s === 8) this.anvil(t, 0.25);
      if (s % 4 === 2) this.hat(t, 0.06);
      if (mode === 'menu' && (s === 0 || s === 3 || s === 8 || s === 11) && this.bar % 8 >= 4) this.guitar(t, root, 0.18, true);
      if (s === 0 && this.bar % 8 === 4) this.lead_(t, 40 + root + 12, (60 / this.bpm) * 3, 0.07);
      return;
    }

    if (mode === 'halftime') {
      if (s === 0 || s === 8) this.kick(t, 0.6);
      if (s === 0 && barInPhrase === 0) this.drone(t, 28 + root, (60 / this.bpm) * 16);
      if (s % 4 === 2) this.hat(t, 0.05);
      return;
    }

    // ---- In-game ----
    // Kick: four on the floor + syncopation at higher intensity
    if (s % 4 === 0) this.kick(t, 1);
    if (I > 0.55 && (s === 7 || s === 14)) this.kick(t, 0.7);
    // Snare/clap on 2 & 4
    if (s === 4 || s === 12) this.snare(t, 0.9);
    // Fill at end of phrase
    if ((lastBar || this.fill) && s >= 12) {
      this.snare(t, 0.4 + (s - 12) * 0.15);
      if (s % 2 === 0) this.tom(t, 150 - (s - 12) * 15, 0.7);
      if (s === 15) this.fill = false;
    }
    // Hats: 8ths, 16ths when intense
    if (s % 2 === 0) this.hat(t, s % 4 === 2 ? 0.12 : 0.07);
    else if (I > 0.35) this.hat(t, 0.04);
    // War toms (Fury Road drummers)
    if (I > 0.25 && (s === 3 || s === 6 || s === 11)) this.tom(t, s === 11 ? 85 : 110, 0.55);
    // Bass: grinding 16ths following the riff
    const r = RIFFS[this.riff][s];
    if (r >= 0) this.bass(t, 28 + root + r, 0.9);
    // Guitar chugs from intensity .3
    if (I > 0.3 && r >= 0 && (s % 2 === 0 || I > 0.7)) this.guitar(t, root + (r > 7 ? r - 12 : r), 0.22 + I * 0.12, s % 4 !== 0);
    // Lead from intensity .6
    if (I > 0.6) {
      const l = LEADS[this.lead][s];
      if (l >= 0) this.lead_(t, 52 + root + l, (60 / this.bpm / 4) * 1.8, 0.05 + (I - 0.6) * 0.1);
    }
    // Crash at phrase start
    if (s === 0 && barInPhrase === 0) this.crash(t, 0.35);
    // Riser in the final seconds
    if (I > 0.9 && s === 0) this.riser(t, (60 / this.bpm) * 4);
  }

  // ---------- instruments ----------
  kick(t, v) {
    const ctx = audio.ctx;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(160, t);
    o.frequency.exponentialRampToValueAtTime(42, t + 0.12);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(1.1 * v, t + 0.003);
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.38);
    const sh = ctx.createWaveShaper(); sh.curve = audio.makeCurve('soft', 3);
    o.connect(g).connect(sh).connect(this.out);
    o.start(t); o.stop(t + 0.42);
    audio.noise(this.out, t, 0.015, { type: 'highpass', f: 3000, gain: 0.25 * v });
  }

  snare(t, v) {
    const g = audio.ctx.createGain();
    g.gain.value = v;
    g.connect(this.out);
    g.connect(this.rev);
    audio.noise(g, t, 0.2, { type: 'highpass', f: 1300, gain: 0.45 });
    audio.noise(g, t, 0.08, { f: 3500, q: 0.8, gain: 0.3 });
    audio.tone(g, t, 0.1, { type: 'triangle', f: 220, f2: 160, gain: 0.4 });
    // Industrial metal clang layered on the snare
    audio.tone(g, t, 0.12, { f: 1650, gain: 0.04 });
  }

  tom(t, f, v) {
    const g = audio.ctx.createGain();
    g.gain.value = v;
    g.connect(this.out);
    g.connect(this.rev);
    audio.tone(g, t, 0.45, { f, f2: f * 0.55, gain: 0.8 });
    audio.noise(g, t, 0.05, { type: 'lowpass', f: 1200, gain: 0.3 });
  }

  hat(t, v) {
    audio.noise(this.out, t, 0.03 + v * 0.2, { type: 'highpass', f: 7500, gain: v * 1.4 });
  }

  crash(t, v) {
    const g = audio.ctx.createGain(); g.gain.value = v;
    g.connect(this.out); g.connect(this.rev);
    audio.noise(g, t, 1.4, { type: 'highpass', f: 5000, gain: 0.6, a: 0.003 });
    audio.noise(g, t, 0.9, { f: 2500, q: 0.5, gain: 0.3 });
  }

  anvil(t, v) {
    const g = audio.ctx.createGain(); g.gain.value = v;
    g.connect(this.out); g.connect(this.rev);
    audio.metal(g, t, 520, 0.9, 0.5);
  }

  bass(t, note, v) {
    const ctx = audio.ctx;
    const f = midi(note);
    const dur = 60 / this.bpm / 4 * 0.9;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.32 * v, t + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.Q.value = 6;
    lp.frequency.setValueAtTime(300 + this.intensity * 1600, t);
    lp.frequency.exponentialRampToValueAtTime(140, t + dur);
    const sh = ctx.createWaveShaper(); sh.curve = audio.distCurve;
    for (const det of [-9, 9]) {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = f;
      o.detune.value = det;
      o.connect(sh);
      o.start(t); o.stop(t + dur + 0.02);
    }
    const sub = ctx.createOscillator();
    sub.frequency.value = f;
    const sg = ctx.createGain(); sg.gain.value = 1.5;
    sub.connect(sg).connect(g);
    sub.start(t); sub.stop(t + dur + 0.02);
    sh.connect(lp).connect(g).connect(this.out);
  }

  guitar(t, semi, v, muted) {
    // Power chord (root, fifth, octave) on E2, heavy distortion into a "cabinet" filter.
    const ctx = audio.ctx;
    const base = 40 + semi;
    const dur = muted ? 0.11 : 0.34;
    const pre = ctx.createGain(); pre.gain.value = 3;
    const sh = ctx.createWaveShaper(); sh.curve = audio.crunchCurve; sh.oversample = '4x';
    const cab = ctx.createBiquadFilter(); cab.type = 'lowpass'; cab.frequency.value = muted ? 1600 : 3200; cab.Q.value = 1.2;
    const hp = ctx.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 90;
    const peak = ctx.createBiquadFilter(); peak.type = 'peaking'; peak.frequency.value = 800; peak.gain.value = -6;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(v, t + 0.004);
    g.gain.setValueAtTime(v, t + dur * 0.5);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    for (const [n, det] of [[base, -6], [base + 7, 5], [base + 12, -3]]) {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = midi(n);
      o.detune.value = det;
      o.connect(pre);
      o.start(t); o.stop(t + dur + 0.02);
    }
    pre.connect(sh).connect(hp).connect(peak).connect(cab).connect(g);
    g.connect(this.out);
    if (!muted) g.connect(this.delay);
  }

  lead_(t, note, dur, v) {
    const ctx = audio.ctx;
    const o = ctx.createOscillator(), o2 = ctx.createOscillator(), g = ctx.createGain();
    o.type = 'square'; o2.type = 'sawtooth';
    o.frequency.value = midi(note); o2.frequency.value = midi(note);
    o2.detune.value = 12;
    const vib = ctx.createOscillator(), vg = ctx.createGain();
    vib.frequency.value = 5.5; vg.gain.value = 0;
    vg.gain.setValueAtTime(0, t);
    vg.gain.linearRampToValueAtTime(12, t + dur);
    vib.connect(vg);
    vg.connect(o.detune); vg.connect(o2.detune);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2800; lp.Q.value = 3;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(v, t + 0.01);
    g.gain.setValueAtTime(v, t + dur * 0.7);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(lp); o2.connect(lp);
    lp.connect(g);
    g.connect(this.out); g.connect(this.delay); g.connect(this.rev);
    for (const x of [o, o2, vib]) { x.start(t); x.stop(t + dur + 0.05); }
  }

  drone(t, note, dur) {
    const ctx = audio.ctx;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(0.12, t + dur * 0.3);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.Q.value = 4;
    lp.frequency.setValueAtTime(200, t);
    lp.frequency.linearRampToValueAtTime(900, t + dur * 0.5);
    lp.frequency.linearRampToValueAtTime(200, t + dur);
    for (const [n, det] of [[note, -8], [note, 8], [note + 7, 0], [note + 12, 4]]) {
      const o = ctx.createOscillator();
      o.type = 'sawtooth';
      o.frequency.value = midi(n);
      o.detune.value = det;
      o.connect(lp);
      o.start(t); o.stop(t + dur + 0.05);
    }
    lp.connect(g);
    g.connect(this.out); g.connect(this.rev);
  }

  riser(t, dur) {
    audio.noise(this.out, t, dur, { f: 400, f2: 6000, q: 2, gain: 0.08, a: dur * 0.8 });
  }

  /** One-shot stinger for goals etc. */
  stinger(kind = 'goal') {
    if (!this.playing || !audio.ready) return;
    const t = audio.now + 0.02;
    if (kind === 'goal') {
      [0, 3, 7].forEach((s, i) => this.guitar(t + i * 0.12, s, 0.35, false));
      this.crash(t, 0.6);
      this.fill = true;
    } else if (kind === 'end') {
      this.guitar(t, 0, 0.4, false);
      this.guitar(t + 0.4, 1, 0.4, false);
      this.guitar(t + 0.8, 0, 0.5, false);
      this.crash(t + 0.8, 0.8);
    }
  }
}

export const music = new Music();
