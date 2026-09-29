// Moteur audio 100 % synthétisé (WebAudio) : bus, réverbération, foule, et une bibliothèque de SFX.
import { clamp, rand } from './config.js';

const NOTE = (n) => 440 * Math.pow(2, (n - 69) / 12);

export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.vol = { music: 0.6, sfx: 0.85 };
    this.last = {};
    this.voices = 0;
    this.ready = false;
  }

  init() {
    if (this.ctx) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    const ctx = (this.ctx = new AC({ latencyHint: 'interactive' }));
    this.master = ctx.createGain();
    this.master.gain.value = 0.9;
    this.limiter = ctx.createDynamicsCompressor();
    this.limiter.threshold.value = -10; this.limiter.knee.value = 12; this.limiter.ratio.value = 6;
    this.limiter.attack.value = 0.004; this.limiter.release.value = 0.18;
    this.master.connect(this.limiter); this.limiter.connect(ctx.destination);

    this.sfxBus = ctx.createGain(); this.sfxBus.gain.value = this.vol.sfx; this.sfxBus.connect(this.master);
    this.musicBus = ctx.createGain(); this.musicBus.gain.value = this.vol.music * 0.7; this.musicBus.connect(this.master);
    this.musicDuck = ctx.createGain(); this.musicDuck.gain.value = 1; this.musicDuck.connect(this.musicBus);

    // Réverbération : impulsion bruitée qui décroît (salle métallique)
    this.reverb = ctx.createConvolver();
    this.reverb.buffer = this._impulse(1.9, 2.6);
    this.revSend = ctx.createGain(); this.revSend.gain.value = 0.7;
    this.revSend.connect(this.reverb); this.reverb.connect(this.sfxBus);
    this.musicRev = ctx.createConvolver(); this.musicRev.buffer = this._impulse(2.6, 2.2);
    this.musicRevSend = ctx.createGain(); this.musicRevSend.gain.value = 0.5;
    this.musicRevSend.connect(this.musicRev); this.musicRev.connect(this.musicBus);

    // Buffer de bruit blanc / rose
    const len = ctx.sampleRate * 3;
    this.noiseBuf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = this.noiseBuf.getChannelData(0);
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < len; i++) {
      const w = Math.random() * 2 - 1;
      b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
      d[i] = (w * 0.5 + (b0 + b1 + b2 + w * 0.1848) * 0.11);
    }
    this._initCrowd();
    this.ready = true;
  }

  resume() { if (this.ctx && this.ctx.state !== 'running') this.ctx.resume(); }

  setVolumes(music, sfx) {
    this.vol.music = music; this.vol.sfx = sfx;
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    this.musicBus.gain.setTargetAtTime(music * 0.7, t, 0.05);
    this.sfxBus.gain.setTargetAtTime(sfx, t, 0.05);
  }

  _impulse(seconds, decay) {
    const ctx = this.ctx, rate = ctx.sampleRate, len = Math.floor(rate * seconds);
    const buf = ctx.createBuffer(2, len, rate);
    for (let c = 0; c < 2; c++) {
      const d = buf.getChannelData(c);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, decay);
    }
    return buf;
  }

  get now() { return this.ctx ? this.ctx.currentTime : 0; }

  // ---- briques de base -------------------------------------------------
  _out(o) {
    const ctx = this.ctx;
    const dest = o.dest || this.sfxBus;
    let node = null;
    if (o.pan) { node = ctx.createStereoPanner(); node.pan.value = clamp(o.pan, -1, 1); node.connect(dest); if (o.rev) this._sendRev(node, o.rev, o.music); return node; }
    if (o.rev) { node = ctx.createGain(); node.connect(dest); this._sendRev(node, o.rev, o.music); return node; }
    return dest;
  }
  _sendRev(node, amt, music) { const g = this.ctx.createGain(); g.gain.value = amt; node.connect(g); g.connect(music ? this.musicRevSend : this.revSend); }

  tone(o) {
    if (!this.ctx) return null;
    const ctx = this.ctx, t = (o.at ?? ctx.currentTime) + (o.when || 0);
    const dur = o.dur ?? 0.2, a = o.a ?? 0.004, vol = (o.vol ?? 0.3);
    const osc = ctx.createOscillator();
    osc.type = o.type || 'sine';
    osc.frequency.setValueAtTime(o.f || 440, t);
    if (o.f1 && o.f1 !== o.f) osc.frequency.exponentialRampToValueAtTime(Math.max(1, o.f1), t + (o.slide ?? dur));
    if (o.detune) osc.detune.value = o.detune;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + a);
    if (o.hold) g.gain.setValueAtTime(vol, t + a + o.hold);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    let last = osc;
    if (o.lp) {
      const f = ctx.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = o.q || 0.8;
      f.frequency.setValueAtTime(o.lp, t); if (o.lp1) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.lp1), t + dur);
      last.connect(f); last = f;
    }
    if (o.hp) { const f = ctx.createBiquadFilter(); f.type = 'highpass'; f.frequency.value = o.hp; last.connect(f); last = f; }
    if (o.vib) {
      const l = ctx.createOscillator(); l.frequency.value = o.vib.rate; const lg = ctx.createGain(); lg.gain.value = o.vib.depth;
      l.connect(lg); lg.connect(osc.frequency); l.start(t); l.stop(t + dur + 0.05);
    }
    last.connect(g); g.connect(this._out(o));
    osc.start(t); osc.stop(t + dur + 0.05);
    this._track(osc);
    return osc;
  }

  noise(o) {
    if (!this.ctx) return null;
    const ctx = this.ctx, t = (o.at ?? ctx.currentTime) + (o.when || 0);
    const dur = o.dur ?? 0.2, a = o.a ?? 0.003, vol = o.vol ?? 0.3;
    const src = ctx.createBufferSource(); src.buffer = this.noiseBuf; src.loop = true;
    const off = Math.random() * 2; src.playbackRate.value = o.rate || 1;
    const f = ctx.createBiquadFilter(); f.type = o.ftype || 'bandpass'; f.Q.value = o.q ?? 0.9;
    f.frequency.setValueAtTime(o.f || 1000, t);
    if (o.f1) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.f1), t + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vol, t + a);
    if (o.hold) g.gain.setValueAtTime(vol, t + a + o.hold);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f); f.connect(g); g.connect(this._out(o));
    src.start(t, off); src.stop(t + dur + 0.05);
    this._track(src);
    return src;
  }

  _track(node) { this.voices++; node.onended = () => { this.voices--; }; }

  _throttle(name, ms) {
    const n = performance.now();
    if (this.last[name] && n - this.last[name] < ms) return false;
    this.last[name] = n; return true;
  }

  // ---- foule -----------------------------------------------------------
  _initCrowd() {
    const ctx = this.ctx;
    const mk = (f, q) => {
      const src = ctx.createBufferSource(); src.buffer = this.noiseBuf; src.loop = true; src.playbackRate.value = 0.8 + Math.random() * 0.4;
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f; bp.Q.value = q;
      const g = ctx.createGain(); g.gain.value = 0;
      src.connect(bp); bp.connect(g); g.connect(this.sfxBus); src.start();
      return { g, bp };
    };
    this.crowd = { low: mk(420, 0.6), mid: mk(900, 0.9), hi: mk(1800, 1.4) };
    this.crowdLevel = 0.3; this.crowdSwellT = 0;
    // murmures : modulation lente
    const lfo = ctx.createOscillator(); lfo.frequency.value = 0.23;
    const lg = ctx.createGain(); lg.gain.value = 120; lfo.connect(lg); lg.connect(this.crowd.mid.bp.frequency); lfo.start();
    const lfo2 = ctx.createOscillator(); lfo2.frequency.value = 0.37;
    const lg2 = ctx.createGain(); lg2.gain.value = 260; lfo2.connect(lg2); lg2.connect(this.crowd.hi.bp.frequency); lfo2.start();
  }

  setCrowd(level) { this.crowdLevel = clamp(level, 0, 1); }

  swell(amount, seconds) { this.crowdSwell = amount; this.crowdSwellT = seconds; this.crowdSwellMax = seconds; }

  updateCrowd(dt) {
    if (!this.ctx || !this.crowd) return;
    let extra = 0;
    if (this.crowdSwellT > 0) { this.crowdSwellT -= dt; const k = Math.max(0, this.crowdSwellT / this.crowdSwellMax); extra = this.crowdSwell * Math.min(1, k * 2.2) * Math.min(1, (1 - k) * 12 + 0.2); }
    const lv = this.crowdLevel + extra, t = this.ctx.currentTime;
    this.crowd.low.g.gain.setTargetAtTime(0.03 + lv * 0.10, t, 0.12);
    this.crowd.mid.g.gain.setTargetAtTime(0.02 + lv * 0.13, t, 0.12);
    this.crowd.hi.g.gain.setTargetAtTime(0.006 + lv * 0.10, t, 0.12);
    this.crowd.mid.bp.frequency.value; // (modulé par LFO)
  }

  muteCrowd(on) { this.crowdMuted = on; }

  // ---- bibliothèque de SFX ---------------------------------------------
  sfx(name, o = {}) {
    if (!this.ctx || this.ctx.state !== 'running') return;
    if (this.voices > 70) return;
    const p = o.pan || 0, v = o.vol ?? 1;
    switch (name) {
      case 'ui-move': this.tone({ type: 'square', f: 520, f1: 640, dur: 0.06, vol: 0.09, lp: 2600 }); break;
      case 'ui-ok': this.tone({ type: 'square', f: 440, dur: 0.07, vol: 0.1, lp: 3000 }); this.tone({ type: 'square', f: 660, dur: 0.12, vol: 0.1, when: 0.06, lp: 3000, rev: 0.3 }); this.tone({ type: 'square', f: 880, dur: 0.16, vol: 0.08, when: 0.11, lp: 3000, rev: 0.3 }); break;
      case 'ui-back': this.tone({ type: 'square', f: 400, f1: 250, dur: 0.12, vol: 0.09, lp: 2000 }); break;
      case 'ui-tick': this.tone({ type: 'triangle', f: 900, dur: 0.04, vol: 0.08 }); break;

      case 'beep': this.tone({ type: 'square', f: 660, dur: 0.22, vol: 0.16, lp: 3200, rev: 0.25 }); this.tone({ type: 'sine', f: 330, dur: 0.22, vol: 0.2 }); break;
      case 'go':
        this.tone({ type: 'sawtooth', f: 880, dur: 0.6, vol: 0.16, lp: 5000, lp1: 800, rev: 0.4 });
        this.tone({ type: 'square', f: 1320, dur: 0.5, vol: 0.09, lp: 4000, rev: 0.4 });
        this.tone({ type: 'sine', f: 220, f1: 110, dur: 0.5, vol: 0.3 }); break;
      case 'whistle': {
        const d = o.dur || 0.5;
        this.tone({ type: 'sine', f: 2650, f1: 2750, dur: d, a: 0.02, hold: d * 0.6, vol: 0.14 * v, vib: { rate: 34, depth: 120 }, rev: 0.4 });
        this.tone({ type: 'sine', f: 3900, dur: d, a: 0.02, hold: d * 0.5, vol: 0.05 * v, vib: { rate: 29, depth: 160 } });
        this.noise({ f: 4200, q: 1.4, dur: d, hold: d * 0.5, vol: 0.05 * v });
        break;
      }
      case 'buzzer':
        this.tone({ type: 'sawtooth', f: 110, dur: 1.5, vol: 0.28, hold: 1.2, lp: 900, rev: 0.4 });
        this.tone({ type: 'square', f: 165, dur: 1.5, vol: 0.14, hold: 1.2, lp: 900 }); break;

      case 'throw': {
        const k = clamp(o.power ?? 0.5, 0, 1);
        this.noise({ f: 900 + k * 800, f1: 300, q: 0.7, dur: 0.16 + k * 0.1, vol: (0.18 + k * 0.14) * v, pan: p });
        this.tone({ type: 'sine', f: 240 + k * 120, f1: 70, dur: 0.14, vol: (0.3 + k * 0.2) * v, pan: p });
        this.tone({ type: 'triangle', f: 1400 + k * 800, f1: 500, dur: 0.06, vol: 0.08 * v, pan: p });
        break;
      }
      case 'lob':
        this.noise({ f: 500, f1: 1800, q: 1.2, dur: 0.3, vol: 0.14 * v, pan: p });
        this.tone({ type: 'sine', f: 180, f1: 480, dur: 0.22, vol: 0.28 * v, pan: p });
        this.tone({ type: 'triangle', f: 900, f1: 1500, dur: 0.14, vol: 0.06 * v, pan: p });
        break;
      case 'catch':
        this.tone({ type: 'triangle', f: 310, f1: 150, dur: 0.12, vol: 0.34 * v, pan: p });
        this.noise({ f: 2200, q: 1, dur: 0.05, vol: 0.14 * v, pan: p });
        this.tone({ type: 'sine', f: 1760, dur: 0.18, vol: 0.05 * v, pan: p, rev: 0.4 });
        break;
      case 'deflect':
        this.clang(620 + rand(-40, 40), 0.22 * v, p, 0.3);
        this.noise({ f: 1600, q: 1, dur: 0.06, vol: 0.16 * v, pan: p });
        break;
      case 'save':
        this.tone({ type: 'sine', f: 140, f1: 55, dur: 0.24, vol: 0.5 * v, pan: p });
        this.clang(480, 0.24 * v, p, 0.45);
        this.noise({ f: 800, f1: 300, q: 0.6, dur: 0.18, vol: 0.2 * v, pan: p });
        break;
      case 'wall': {
        const k = clamp(o.power ?? 0.5, 0, 1);
        if (!this._throttle('wall', 45)) break;
        this.clang(210 + k * 70 + rand(-15, 15), (0.09 + k * 0.28) * v, p, 0.22 + k * 0.22);
        this.tone({ type: 'sine', f: 120, f1: 60, dur: 0.12, vol: (0.12 + k * 0.3) * v, pan: p });
        this.noise({ f: 3200, q: 1.2, dur: 0.03, vol: 0.12 * k * v, pan: p });
        break;
      }
      case 'post':
        this.clang(880, 0.3 * v, p, 0.9); this.clang(1320, 0.12 * v, p, 0.7);
        this.tone({ type: 'sine', f: 100, f1: 50, dur: 0.15, vol: 0.3 * v, pan: p });
        break;
      case 'net':
        this.noise({ f: 700, f1: 200, q: 0.5, dur: 0.4, vol: 0.25 * v, pan: p, ftype: 'lowpass' });
        this.tone({ type: 'sine', f: 90, f1: 45, dur: 0.22, vol: 0.3 * v, pan: p });
        break;
      case 'bumper': {
        const f = 240 + Math.random() * 60;
        this.tone({ type: 'sine', f, f1: f * 4, slide: 0.06, dur: 0.22, vol: 0.34 * v, pan: p, rev: 0.3 });
        this.tone({ type: 'square', f: f * 2, f1: f * 6, slide: 0.05, dur: 0.1, vol: 0.06 * v, pan: p, lp: 3000 });
        this.noise({ f: 2400, q: 1.2, dur: 0.05, vol: 0.13 * v, pan: p });
        break;
      }
      case 'pad': {
        const base = o.note ?? 72;
        this.tone({ type: 'triangle', f: NOTE(base), dur: 0.25, vol: 0.22 * v, pan: p, rev: 0.5 });
        this.tone({ type: 'triangle', f: NOTE(base + 4), dur: 0.25, vol: 0.2 * v, when: 0.06, pan: p, rev: 0.5 });
        this.tone({ type: 'triangle', f: NOTE(base + 7), dur: 0.4, vol: 0.2 * v, when: 0.12, pan: p, rev: 0.5 });
        this.tone({ type: 'sine', f: NOTE(base + 19), dur: 0.5, vol: 0.06 * v, when: 0.12, pan: p, rev: 0.6 });
        break;
      }
      case 'star-rush':
        [0, 4, 7, 12, 16, 19, 24].forEach((n, i) => {
          this.tone({ type: 'square', f: NOTE(64 + n), dur: 0.22, vol: 0.12, when: i * 0.055, lp: 4000, rev: 0.5 });
          this.tone({ type: 'sawtooth', f: NOTE(52 + n), dur: 0.26, vol: 0.08, when: i * 0.055, lp: 1800 });
        });
        this.noise({ f: 300, f1: 6000, q: 0.8, dur: 0.6, vol: 0.18 });
        break;
      case 'warp':
        this.tone({ type: 'sine', f: 300, f1: 2400, dur: 0.35, vol: 0.2 * v, pan: p, rev: 0.6 });
        this.tone({ type: 'sine', f: 2000, f1: 200, dur: 0.4, vol: 0.18 * v, when: 0.12, pan: -p, rev: 0.6 });
        this.noise({ f: 800, f1: 5000, q: 2.5, dur: 0.4, vol: 0.14 * v, pan: p });
        break;
      case 'launcher-charge':
        this.tone({ type: 'sawtooth', f: 90, f1: 520, dur: 1.0, vol: 0.16, lp: 900, lp1: 3000, rev: 0.3 });
        this.noise({ f: 2500, q: 0.7, dur: 1.0, vol: 0.13, a: 0.4 });
        break;
      case 'launch':
        this.tone({ type: 'sine', f: 200, f1: 45, dur: 0.4, vol: 0.6 });
        this.noise({ f: 300, f1: 6000, q: 0.6, dur: 0.6, vol: 0.4, a: 0.01, rev: 0.4 });
        this.tone({ type: 'sawtooth', f: 200, f1: 1600, slide: 0.35, dur: 0.5, vol: 0.14, lp: 3200, rev: 0.4 });
        this.clang(300, 0.25, 0, 0.6);
        break;
      case 'steam': this.noise({ f: 5000, q: 0.4, ftype: 'highpass', dur: 0.5, vol: 0.12, a: 0.02, pan: p }); break;

      case 'slide':
        this.noise({ f: 2600, f1: 700, q: 0.8, dur: 0.35, vol: 0.22 * v, pan: p, a: 0.02 });
        this.tone({ type: 'sine', f: 150, f1: 80, dur: 0.25, vol: 0.14 * v, pan: p });
        break;
      case 'hit': {
        const k = clamp(o.power ?? 0.6, 0, 1);
        this.tone({ type: 'sine', f: 150, f1: 38, dur: 0.3, vol: (0.5 + k * 0.3) * v, pan: p });
        this.noise({ f: 1400, f1: 300, q: 0.6, dur: 0.22, vol: (0.3 + k * 0.2) * v, pan: p });
        this.tone({ type: 'square', f: 260, f1: 90, dur: 0.09, vol: 0.14 * v, pan: p, lp: 1400 });
        this.clang(300 + rand(0, 60), 0.12 * v, p, 0.3);
        if (k > 0.7) { this.tone({ type: 'sine', f: 70, f1: 30, dur: 0.6, vol: 0.5 * v, pan: p }); this.noise({ f: 600, f1: 100, q: 0.5, dur: 0.5, vol: 0.2, ftype: 'lowpass', pan: p }); }
        break;
      }
      case 'stun':
        for (let i = 0; i < 4; i++) this.tone({ type: 'triangle', f: 880 - i * 90, dur: 0.14, vol: 0.09 * v, when: 0.1 + i * 0.09, pan: p, rev: 0.3 });
        break;
      case 'jump':
        this.tone({ type: 'sine', f: 220, f1: 520, dur: 0.16, vol: 0.18 * v, pan: p });
        this.noise({ f: 1500, f1: 3000, q: 1, dur: 0.1, vol: 0.06 * v, pan: p });
        break;
      case 'land':
        this.tone({ type: 'sine', f: 110, f1: 55, dur: 0.12, vol: 0.2 * v, pan: p });
        this.noise({ f: 700, f1: 300, q: 0.7, dur: 0.1, vol: 0.12 * v, pan: p });
        break;
      case 'step':
        if (!this._throttle('step' + (o.id || 0), 130)) break;
        this.noise({ f: 300 + Math.random() * 250, q: 1.2, dur: 0.05, vol: 0.05 * v, pan: p });
        break;
      case 'turbo':
        this.noise({ f: 700, f1: 3200, q: 0.9, dur: 0.28, vol: 0.14 * v, pan: p, a: 0.03 });
        this.tone({ type: 'sawtooth', f: 110, f1: 300, dur: 0.24, vol: 0.06 * v, pan: p, lp: 1200 });
        break;
      case 'bounce':
        if (!this._throttle('bounce', 60)) break;
        this.tone({ type: 'sine', f: 190 + (o.power || 0) * 60, f1: 90, dur: 0.1, vol: (0.1 + (o.power || 0) * 0.24) * v, pan: p });
        this.noise({ f: 1800, q: 1, dur: 0.03, vol: 0.06 * v, pan: p });
        break;

      case 'coin':
        this.tone({ type: 'square', f: NOTE(83), dur: 0.08, vol: 0.12 * v, lp: 5000, pan: p });
        this.tone({ type: 'square', f: NOTE(88), dur: 0.35, vol: 0.12 * v, when: 0.07, lp: 5000, pan: p, rev: 0.4 });
        this.tone({ type: 'sine', f: NOTE(100), dur: 0.3, vol: 0.05, when: 0.07, pan: p, rev: 0.5 });
        break;
      case 'powerup':
        [0, 4, 7, 12, 16].forEach((n, i) => {
          this.tone({ type: 'square', f: NOTE(67 + n), dur: 0.14, vol: 0.11, when: i * 0.06, lp: 4000, pan: p, rev: 0.4 });
        });
        this.tone({ type: 'sawtooth', f: NOTE(55), f1: NOTE(67), dur: 0.4, vol: 0.1, lp: 1500, pan: p });
        break;
      case 'freeze':
        for (let i = 0; i < 6; i++) this.tone({ type: 'sine', f: 2000 + Math.random() * 3000, dur: 0.5, vol: 0.06, when: Math.random() * 0.25, rev: 0.7 });
        this.noise({ f: 6000, f1: 2500, q: 2, dur: 0.6, vol: 0.2, rev: 0.6 });
        this.tone({ type: 'sine', f: 800, f1: 100, dur: 0.6, vol: 0.2, rev: 0.5 });
        break;
      case 'charge-tick': this.tone({ type: 'triangle', f: 1200 + (o.k || 0) * 1200, dur: 0.03, vol: 0.05 }); break;

      case 'goal': {
        // klaxon de stade + sirène + rugissement de foule
        this.tone({ type: 'sawtooth', f: 233, dur: 1.5, vol: 0.2, hold: 1.0, lp: 1800, rev: 0.4 });
        this.tone({ type: 'sawtooth', f: 349, dur: 1.5, vol: 0.16, hold: 1.0, lp: 1800, rev: 0.4, detune: 8 });
        this.tone({ type: 'square', f: 466, dur: 1.4, vol: 0.06, hold: 1.0, lp: 2400 });
        for (let i = 0; i < 6; i++) this.tone({ type: 'square', f: i % 2 ? 660 : 880, dur: 0.16, vol: 0.09, when: 0.25 + i * 0.17, lp: 3000, rev: 0.3 });
        this.tone({ type: 'sine', f: 55, f1: 40, dur: 1.2, vol: 0.55 });
        this.noise({ f: 200, f1: 8000, q: 0.5, dur: 1.2, vol: 0.28, a: 0.05, rev: 0.5 });
        this.swell(0.9, 4.5);
        break;
      }
      case 'crowd-ooh': this.swell(0.35, 1.6); break;
      case 'crowd-cheer': this.swell(0.6, 2.4); break;
      case 'sting-bad':
        [0, -1, -3, -6].forEach((n, i) => this.tone({ type: 'sawtooth', f: NOTE(60 + n), dur: 0.3, vol: 0.09, when: i * 0.16, lp: 1200 }));
        break;
      case 'camera': this.noise({ f: 5000, q: 2, dur: 0.02, vol: 0.05, pan: p }); break;
      case 'whoosh': this.noise({ f: 400, f1: 3000, q: 0.8, dur: 0.5, vol: 0.2 * v, a: 0.15 }); break;
      case 'confetti':
        this.noise({ f: 800, f1: 300, q: 0.7, dur: 0.15, vol: 0.3 }); this.tone({ type: 'sine', f: 90, dur: 0.12, vol: 0.4 });
        this.noise({ f: 6000, q: 0.6, ftype: 'highpass', dur: 0.8, vol: 0.06, when: 0.05 });
        break;
      case 'bigtext': this.tone({ type: 'sine', f: 90, f1: 40, dur: 0.5, vol: 0.5 }); this.noise({ f: 200, f1: 900, q: 0.6, dur: 0.3, vol: 0.2 }); break;
    }
  }

  clang(base, vol, pan, dur) {
    const ratios = [1, 2.76, 5.4, 8.93], gains = [1, 0.55, 0.3, 0.16];
    ratios.forEach((r, i) => this.tone({ type: 'sine', f: base * r, dur: dur * (1 - i * 0.18), vol: vol * gains[i] * 0.6, pan, rev: 0.25 }));
  }

  // Son continu de charge du tir (montée en tonalité).
  startCharge() {
    if (!this.ctx) return null;
    const ctx = this.ctx, t = ctx.currentTime;
    const osc = ctx.createOscillator(); osc.type = 'sawtooth'; osc.frequency.value = 120;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 500; lp.Q.value = 4;
    const g = ctx.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.05, t + 0.05);
    osc.connect(lp); lp.connect(g); g.connect(this.sfxBus); osc.start(t);
    const self = this;
    return {
      set(k) { const tt = ctx.currentTime; osc.frequency.setTargetAtTime(120 + k * 380, tt, 0.03); lp.frequency.setTargetAtTime(500 + k * 3000, tt, 0.03); g.gain.setTargetAtTime(0.04 + k * 0.05, tt, 0.03); },
      stop() { const tt = ctx.currentTime; g.gain.cancelScheduledValues(tt); g.gain.setTargetAtTime(0.0001, tt, 0.02); osc.stop(tt + 0.15); },
    };
  }

  duckMusic(to, seconds) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime, g = this.musicDuck.gain;
    g.cancelScheduledValues(t); g.setTargetAtTime(to, t, 0.03); g.setTargetAtTime(1, t + seconds, 0.4);
  }
}
