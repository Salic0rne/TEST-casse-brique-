// Point d'entrée : initialisation, boucle principale, gestion des scènes et transitions.
import { VIEW_W, VIEW_H, TEAMS, PAL, clamp, easeOutCubic, pick, TAU } from './config.js';
import { Input } from './input.js';
import { AudioEngine } from './audio.js';
import { Music } from './music.js';
import { FX } from './fx.js';
import { Arena } from './arena.js';
import { Renderer } from './render.js';
import { Match } from './game.js';
import { TitleScene, SetupScene, OptionsScene, MatchScene, ResultScene } from './ui.js';

const nullAudio = new Proxy({}, { get: () => () => {} });
const OUT = PAL.outline;

class App {
  constructor() {
    this.canvas = document.getElementById('c');
    this.renderer = new Renderer(this.canvas);
    this.input = new Input();
    this.audio = new AudioEngine();
    this.music = new Music(this.audio);
    this.fx = new FX();
    this.arena = new Arena();
    this.settings = this.loadSettings();
    this.time = 0; this.scene = null; this.trans = null; this.attract = null; this.showFps = false; this.fps = 60;
    this.scenes = { title: TitleScene, setup: SetupScene, options: OptionsScene, match: MatchScene, result: ResultScene };
    this.bindMouse();
    const wake = () => { this.audio.init(); this.audio.resume(); this.applyAudio(); };
    for (const ev of ['keydown', 'mousedown', 'pointerdown', 'touchstart']) window.addEventListener(ev, wake, { passive: true });
    window.addEventListener('keydown', (e) => { if (e.code === 'F3') this.showFps = !this.showFps; });
    window.addEventListener('gamepadconnected', wake);
    try { this.audio.init(); } catch (e) { /* attend un geste */ }
    this.applyAudio();
  }

  loadSettings() {
    const d = { music: 0.6, sfx: 0.85, shake: true, replay: true, bloom: true, teamA: 0, teamB: 1, diff: 1, dur: 1 };
    try { return Object.assign(d, JSON.parse(localStorage.getItem('sba-settings') || '{}')); } catch (e) { return d; }
  }
  saveSettings() { try { localStorage.setItem('sba-settings', JSON.stringify(this.settings)); } catch (e) { /* ignore */ } }
  applyAudio() { this.audio.setVolumes(this.settings.music, this.settings.sfx); this.fx.shakeEnabled = this.settings.shake; this.renderer.bloom = this.settings.bloom !== false; }
  toggleFullscreen() { try { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); } catch (e) { /* ignore */ } }
  closeOverlay() { if (this.scene && this.scene.closeOverlay) this.scene.closeOverlay(); }

  bindMouse() {
    const m = this.input.mouse;
    const conv = (e) => { const r = this.renderer, dpr = window.devicePixelRatio || 1; m.x = (e.clientX * dpr - r.ox) / r.sx; m.y = (e.clientY * dpr - r.oy) / r.sx; };
    window.addEventListener('mousemove', (e) => { conv(e); m.moved = true; });
    window.addEventListener('mousedown', (e) => { conv(e); m.down = true; m.clicked = true; });
    window.addEventListener('mouseup', () => { m.down = false; });
  }

  // --- match d'attraction (IA contre IA) en fond des menus
  startAttract() {
    if (this.attract) return;
    const a = pick(TEAMS); let b = pick(TEAMS); while (b === a) b = pick(TEAMS);
    this.attractFx = new FX(); this.attractFx.shakeEnabled = false;
    this.arena.build(a, b);
    const m = new Match({ teamA: a, teamB: b, mode2p: false, attract: true, difficulty: 1, duration: 9999, audio: nullAudio, music: nullAudio, fx: this.attractFx, input: this.input });
    m.phase = 'kickoff'; m.phaseT = 0; m.hint = 0; m.launcherArmed = false;
    m.onSwap = null; this.attract = m;
  }
  stopAttract() { this.attract = null; }
  drawAttract(dim) {
    const r = this.renderer, ctx = r.ctx;
    if (!this.attract) this.startAttract();
    r.drawWorld(this.attract, this.arena, this.attractFx, this.time);
    ctx.fillStyle = `rgba(12,6,12,${dim})`; ctx.fillRect(0, 0, VIEW_W, VIEW_H);
  }

  // --- scènes
  go(name, args = {}) {
    if (this.trans && this.trans.phase === 'out') return;
    if (!this.scene) { this.enter(name, args); return; }
    this.trans = { phase: 'out', t: 0, next: [name, args] };
    this.audio.sfx('whoosh');
  }
  enter(name, args) {
    const S = this.scenes[name]; this.scene = new S(); this.sceneName = name; this.scene.enter(this, args);
  }

  frame(now) {
    const dt = Math.min(0.05, Math.max(0.0001, (now - (this.last || now)) / 1000)); this.last = now;
    this.fps += (1 / dt - this.fps) * 0.05;
    this.time += dt;
    // garde-fou performance : si le jeu tourne durablement sous ~38 fps, on allège (bloom off, foule réduite)
    if (!this.hq && !this.lowQuality) {
      this.slowT = this.fps < 38 && this.time > 4 ? (this.slowT || 0) + dt : 0;
      if (this.slowT > 3.5) { this.lowQuality = true; this.renderer.bloom = false; this.arena.low = true; }
    }
    this.input.poll(dt);
    // transition
    const tr = this.trans;
    if (tr) {
      tr.t += dt;
      const dur = 0.32;
      if (tr.phase === 'out' && tr.t >= dur) { this.enter(...tr.next); tr.phase = 'in'; tr.t = 0; }
      else if (tr.phase === 'in' && tr.t >= dur) this.trans = null;
    }
    if (!(this.scene instanceof MatchScene)) { this.audio.setCrowd(0.13); this.audio.updateCrowd(dt); this.audio.setRoll(0); }
    if (this.attract && !(this.scene instanceof MatchScene)) this.attract.update(dt);
    if (this.scene && !(tr && tr.phase === 'out' && tr.t > 0.3)) this.scene.update(dt);
    // rendu
    const r = this.renderer; r.resize();
    const ctx = r.begin();
    if (this.scene) this.scene.render(r, this.time);
    if (this.trans) this.drawTransition(ctx);
    if (this.showFps) { ctx.font = '22px "Lilita One"'; ctx.textAlign = 'left'; ctx.fillStyle = '#b6f26a'; ctx.strokeStyle = '#000'; ctx.lineWidth = 4; const s = `${this.fps.toFixed(0)} fps`; ctx.strokeText(s, 10, VIEW_H - 10); ctx.fillText(s, 10, VIEW_H - 10); }
    r.end();
    this.input.endFrame();
    requestAnimationFrame((n) => this.frame(n));
  }

  drawTransition(ctx) {
    const tr = this.trans, dur = 0.32;
    const p = clamp(tr.t / dur, 0, 1), cover = tr.phase === 'out' ? p : 1 - p;
    const N = 10, cols = [PAL.mustard, PAL.salmon, '#3a2733', PAL.pink, PAL.sage];
    for (let i = 0; i < N; i++) {
      const w = VIEW_W / N + 90, x = i * VIEW_W / N - 45;
      const k = clamp(cover * 1.7 - i * 0.07, 0, 1), h = easeOutCubic(k) * (VIEW_H + 60);
      if (h <= 1) continue;
      const fromTop = i % 2 === 0, y = fromTop ? -30 : VIEW_H + 30 - h;
      ctx.beginPath(); ctx.moveTo(x + 40, y); ctx.lineTo(x + w + 40, y); ctx.lineTo(x + w - 40, y + h); ctx.lineTo(x - 40, y + h); ctx.closePath();
      ctx.fillStyle = cols[i % cols.length]; ctx.fill(); ctx.lineWidth = 6; ctx.strokeStyle = OUT; ctx.stroke();
    }
  }
}

async function boot() {
  try { await Promise.all([document.fonts.load('40px Bangers'), document.fonts.load('40px "Lilita One"')]); } catch (e) { /* polices système */ }
  const app = new App(); window.__app = app;
  const q = new URLSearchParams(location.search);
  if (q.get('hq') || window.__HQ) app.hq = true;   // désactive le garde-fou de performance (captures, tests)
  app.go('title');
  if (q.get('test') === 'match') {
    app.go('match', { mode2p: false, teamA: TEAMS[+q.get('a') || 0], teamB: TEAMS[+q.get('b') || 1], difficulty: 1, duration: +q.get('dur') || 90 });
  }
  requestAnimationFrame((n) => app.frame(n));
}
window.__T = TEAMS;
boot();
