// Scènes de menu (dessinées en canvas dans le même style cartoon) : titre, sélection, options, match/pause, résultats.
import { VIEW_W, VIEW_H, PAL, TEAMS, DIFFICULTY, DURATIONS, TAU, clamp, lerp, easeOutBack, easeOutCubic, pick, randi } from './config.js';
import { drawHumanoid, drawKeeper, rrPath, shadeColor } from './art.js';
import { comicText } from './fx.js';
import { Match } from './game.js';

const OUT = PAL.outline;
const nullAudio = new Proxy({}, { get: () => () => {} });

// ---------------------------------------------------------------- widgets
export function skewPanel(ctx, x, y, w, h, skew, fill, lw = 5) {
  ctx.beginPath(); ctx.moveTo(x + skew, y); ctx.lineTo(x + w + skew, y); ctx.lineTo(x + w - skew, y + h); ctx.lineTo(x - skew, y + h); ctx.closePath();
  ctx.fillStyle = fill; ctx.fill(); ctx.lineWidth = lw; ctx.strokeStyle = OUT; ctx.lineJoin = 'round'; ctx.stroke();
}

function button(ctx, label, cx, cy, w, h, sel, time, rects, idx, sub) {
  const wob = sel ? Math.sin(time * 8) * 0.012 : 0, sc = sel ? 1.07 : 1;
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(wob - (sel ? 0.015 : 0)); ctx.scale(sc, sc);
  // ombre dure
  skewPanel(ctx, -w / 2 + 7, -h / 2 + 8, w, h, 22, OUT, 0.1);
  skewPanel(ctx, -w / 2, -h / 2, w, h, 22, sel ? PAL.mustard : PAL.cream, 5);
  ctx.save(); ctx.beginPath(); ctx.moveTo(-w / 2 + 22, -h / 2); ctx.lineTo(w / 2 + 22, -h / 2); ctx.lineTo(w / 2 - 22, h / 2); ctx.lineTo(-w / 2 - 22, h / 2); ctx.closePath(); ctx.clip();
  ctx.fillStyle = sel ? PAL.mustardDark : '#c8bfa9'; ctx.globalAlpha = 0.5; ctx.fillRect(-w, h * 0.12, w * 2, h); ctx.restore();
  comicText(ctx, label, 0, sub ? -8 : 0, sub ? 40 : 46, sel ? PAL.cream : '#4a3038', sel ? OUT : 'rgba(0,0,0,0)', 'Bangers', sel ? 0.09 : 0);
  if (!sel) { ctx.font = '46px Bangers'; }
  if (sub) { ctx.font = '19px "Lilita One"'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = sel ? '#5a3a10' : '#7a6a60'; ctx.fillText(sub, 0, 24); }
  ctx.restore();
  if (rects) rects[idx] = { x: cx - w / 2, y: cy - h / 2, w, h };
}

export class Menu {
  constructor(n) { this.n = n; this.sel = 0; this.rects = []; }
  // retourne { ok, dx } pour la frame
  update(app, opts = {}) {
    const nav = app.input.nav, m = app.input.mouse, out = { ok: false, dx: 0, changed: false };
    const old = this.sel;
    if (nav.up) this.sel = (this.sel + this.n - 1) % this.n;
    if (nav.down) this.sel = (this.sel + 1) % this.n;
    if (m.moved) { for (let i = 0; i < this.rects.length; i++) { const r = this.rects[i]; if (r && m.x > r.x && m.x < r.x + r.w && m.y > r.y && m.y < r.y + r.h) this.sel = i; } }
    if (m.clicked) { const r = this.rects[this.sel]; if (r && m.x > r.x && m.x < r.x + r.w && m.y > r.y && m.y < r.y + r.h) out.ok = true; }
    if (nav.ok) out.ok = true;
    if (nav.left) out.dx = -1; if (nav.right) out.dx = 1;
    if (m.clicked && opts.sliders) { /* clic sur les flèches gérés par la scène */ }
    if (this.sel !== old) { app.audio.sfx('ui-move'); out.changed = true; }
    return out;
  }
}

function menuBackdrop(app, r, dim = 0.55) {
  const ctx = r.ctx;
  app.drawAttract(dim);
}

function titleLogo(ctx, time, x, y, s = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.rotate(-0.045);
  const bob = Math.sin(time * 1.6) * 5;
  ctx.translate(0, bob);
  // rayons
  ctx.save(); ctx.rotate(time * 0.1); ctx.globalAlpha = 0.14;
  for (let i = 0; i < 16; i++) { ctx.rotate(TAU / 16); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(760, -32); ctx.lineTo(760, 32); ctx.closePath(); ctx.fillStyle = i % 2 ? PAL.mustard : PAL.salmon; ctx.fill(); }
  ctx.restore();
  comicText(ctx, 'STEEL BALL', 0, -34, 150, PAL.mustardLight, OUT, 'Bangers', 0.11);
  comicText(ctx, 'ARENA', 0, 96, 172, PAL.salmon, OUT, 'Bangers', 0.11);
  // balle d'acier logo
  ctx.save(); ctx.translate(292, 106); ctx.rotate(time * 1.4);
  const g = ctx.createRadialGradient(-14, -16, 4, 0, 0, 44); g.addColorStop(0, '#fff'); g.addColorStop(0.4, '#b6c1cc'); g.addColorStop(1, '#3d4858');
  ctx.beginPath(); ctx.arc(0, 0, 44, 0, TAU); ctx.fillStyle = g; ctx.fill(); ctx.lineWidth = 6; ctx.strokeStyle = OUT; ctx.stroke();
  ctx.lineWidth = 3.5; ctx.strokeStyle = 'rgba(30,38,52,0.6)'; ctx.beginPath(); ctx.ellipse(0, 0, 40, 14, 0, 0, TAU); ctx.stroke(); ctx.beginPath(); ctx.ellipse(0, 0, 14, 40, 0, 0, TAU); ctx.stroke();
  ctx.restore();
  ctx.restore();
}

// ---------------------------------------------------------------- Titre
export class TitleScene {
  enter(app) {
    this.app = app; this.menu = new Menu(4); this.t = 0;
    app.startAttract(); app.music.play('menu');
  }
  update(dt) {
    const app = this.app; this.t += dt;
    const r = this.menu.update(app);
    if (r.ok) {
      app.audio.sfx('ui-ok');
      if (this.menu.sel === 0) app.go('setup', { mode2p: false });
      else if (this.menu.sel === 1) app.go('setup', { mode2p: true });
      else if (this.menu.sel === 2) app.go('options', { from: 'title' });
      else if (this.menu.sel === 3) { try { window.close(); } catch (e) { /* navigateur */ } }
    }
  }
  render(r, time) {
    const ctx = r.ctx, app = this.app;
    menuBackdrop(app, r, 0.5);
    // bandeau sombre latéral pour lisibilité
    const g = ctx.createLinearGradient(0, 0, 0, VIEW_H); g.addColorStop(0, 'rgba(12,6,12,0.55)'); g.addColorStop(0.5, 'rgba(12,6,12,0.1)'); g.addColorStop(1, 'rgba(12,6,12,0.7)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    const pop = easeOutBack(Math.min(1, this.t * 1.6));
    titleLogo(ctx, time, VIEW_W / 2 - 20, 210, 0.86 * pop);
    const labels = ['1 JOUEUR', '2 JOUEURS', 'OPTIONS', 'QUITTER'];
    const subs = ['Contre l\'ordinateur', 'Duel en local', 'Sons, écran, contrôles', null];
    labels.forEach((l, i) => {
      const k = easeOutCubic(clamp(this.t * 2 - i * 0.15, 0, 1));
      button(ctx, l, VIEW_W / 2 - (1 - k) * 700, 480 + i * 92, 430, 74, this.menu.sel === i, time, this.menu.rects, i, subs[i]);
    });
    ctx.font = '20px "Lilita One"'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(246,239,223,0.75)'; ctx.strokeStyle = OUT; ctx.lineWidth = 4;
    const foot = '↑↓ choisir · ENTRÉE valider · F11 plein écran';
    ctx.strokeText(foot, VIEW_W / 2, VIEW_H - 22); ctx.fillText(foot, VIEW_W / 2, VIEW_H - 22);
  }
}

// ---------------------------------------------------------------- Sélection des équipes
function statBar(ctx, x, y, w, v, col) {
  for (let i = 0; i < 5; i++) { rrPath(ctx, x + i * (w / 5), y, w / 5 - 4, 12, 3); ctx.fillStyle = i < v ? col : 'rgba(0,0,0,0.35)'; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke(); }
}

function teamCard(ctx, def, x, y, w, h, time, label, active) {
  ctx.save(); ctx.translate(x, y);
  ctx.save(); ctx.translate(8, 10); skewPanel(ctx, 0, 0, w, h, 20, OUT, 0.1); ctx.restore();
  skewPanel(ctx, 0, 0, w, h, 20, shadeColor(def.main, -0.1), 6);
  ctx.save(); ctx.beginPath(); ctx.moveTo(20, 0); ctx.lineTo(w + 20, 0); ctx.lineTo(w - 20, h); ctx.lineTo(-20, h); ctx.closePath(); ctx.clip();
  ctx.fillStyle = def.dark; ctx.globalAlpha = 0.45; ctx.fillRect(-30, h * 0.62, w + 60, h); ctx.globalAlpha = 0.16; ctx.fillStyle = '#fff';
  for (let i = 0; i < 12; i++) { ctx.beginPath(); ctx.moveTo(-30 + i * 70, h); ctx.lineTo(10 + i * 70, h); ctx.lineTo(100 + i * 70, 0); ctx.lineTo(60 + i * 70, 0); ctx.fill(); }
  ctx.restore();
  // personnages
  ctx.save(); ctx.translate(w * 0.32, h * 0.66); ctx.scale(1.75, 1.75);
  ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.beginPath(); ctx.ellipse(0, 4, 34, 11, 0, 0, TAU); ctx.fill();
  drawHumanoid(ctx, def, 0, { t: time, phase: time * 2, run: 0, flip: false, hasBall: false, charge: 0, state: 'run', sq: 0, stunT: 0, blink: false }, 4);
  ctx.restore();
  ctx.save(); ctx.translate(w * 0.72, h * 0.72); ctx.scale(0.95, 0.95);
  ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.beginPath(); ctx.ellipse(0, 4, 70, 14, 0, 0, TAU); ctx.fill();
  drawKeeper(ctx, def, { t: time, phase: time * 1.5, flip: true, hasBall: false, reach: [Math.sin(time) * 50 + 20, -30], moveY: 0, sq: 0, state: 'run' });
  ctx.restore();
  ctx.save(); ctx.translate(w / 2, 46); comicText(ctx, def.name, 0, 0, 58, PAL.cream, OUT); ctx.restore();
  ctx.font = '19px "Lilita One"'; ctx.textAlign = 'center'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 4; ctx.strokeText(def.tag, w / 2, 84); ctx.fillText(def.tag, w / 2, 84);
  // stats
  ctx.textAlign = 'left'; ctx.font = '17px "Lilita One"';
  [['VITESSE', def.stats.speed], ['PUISSANCE', def.stats.power], ['DÉFENSE', def.stats.defense]].forEach(([n, v], i) => {
    const yy = h - 92 + i * 27; ctx.fillStyle = PAL.cream; ctx.strokeText(n, 24, yy + 11); ctx.fillText(n, 24, yy + 11); statBar(ctx, 132, yy, 140, v, def.accent);
  });
  // étiquette joueur
  skewPanel(ctx, 24, -20, 120, 34, 10, active ? PAL.mustard : PAL.cream, 4);
  comicText(ctx, label, 84, -3, 26, active ? PAL.cream : '#4a3038', active ? OUT : 'rgba(0,0,0,0)', 'Bangers', active ? 0.08 : 0);
  ctx.restore();
}

export class SetupScene {
  enter(app, args) {
    this.app = app; this.mode2p = !!args.mode2p; this.t = 0;
    const s = app.settings;
    this.cfg = { teamA: s.teamA ?? 0, teamB: s.teamB ?? 1, diff: s.diff ?? 1, dur: s.dur ?? 1 };
    if (this.cfg.teamA === this.cfg.teamB) this.cfg.teamB = (this.cfg.teamA + 1) % TEAMS.length;
    this.menu = new Menu(this.mode2p ? 4 : 5);
    app.startAttract();
  }
  rows() {
    const r = [['ÉQUIPE J1', TEAMS[this.cfg.teamA].name], [this.mode2p ? 'ÉQUIPE J2' : 'ADVERSAIRE', TEAMS[this.cfg.teamB].name]];
    if (!this.mode2p) r.push(['DIFFICULTÉ', DIFFICULTY[this.cfg.diff].name]);
    r.push(['DURÉE PÉRIODE', DURATIONS[this.cfg.dur] + ' s']);
    r.push(['COUP D\'ENVOI !', null]);
    return r;
  }
  update(dt) {
    const app = this.app; this.t += dt;
    const n = this.rows().length; this.menu.n = n;
    const res = this.menu.update(app);
    const kinds = this.mode2p ? ['a', 'b', 'dur', 'go'] : ['a', 'b', 'diff', 'dur', 'go'];
    const kind = kinds[this.menu.sel];
    if (res.dx && kind !== 'go') {
      app.audio.sfx('ui-tick');
      const c = this.cfg, d = res.dx, N = TEAMS.length;
      if (kind === 'a') { c.teamA = (c.teamA + d + N) % N; if (c.teamA === c.teamB && this.mode2p) c.teamB = (c.teamB + d + N) % N; }
      else if (kind === 'b') { c.teamB = (c.teamB + d + N) % N; }
      else if (kind === 'diff') c.diff = clamp(c.diff + d, 0, DIFFICULTY.length - 1);
      else if (kind === 'dur') c.dur = clamp(c.dur + d, 0, DURATIONS.length - 1);
    }
    if (res.ok) {
      if (kind === 'go') {
        const s = app.settings; Object.assign(s, this.cfg); app.saveSettings();
        app.audio.sfx('ui-ok');
        app.go('match', { mode2p: this.mode2p, teamA: TEAMS[this.cfg.teamA], teamB: TEAMS[this.cfg.teamB], difficulty: this.cfg.diff, duration: DURATIONS[this.cfg.dur] });
      } else { this.menu.sel = Math.min(n - 1, this.menu.sel + 1); app.audio.sfx('ui-move'); }
    }
    if (app.input.nav.back) { app.audio.sfx('ui-back'); app.go('title'); }
  }
  render(r, time) {
    const ctx = r.ctx, app = this.app;
    menuBackdrop(app, r, 0.72);
    const k = easeOutCubic(clamp(this.t * 2.2, 0, 1));
    ctx.save(); ctx.translate(VIEW_W / 2, 66); comicText(ctx, this.mode2p ? 'DUEL LOCAL' : 'MATCH RAPIDE', 0, 0, 84, PAL.mustardLight, OUT); ctx.restore();
    const A = TEAMS[this.cfg.teamA], B = TEAMS[this.cfg.teamB];
    const sel = this.menu.sel;
    ctx.save(); ctx.translate(-(1 - k) * 600, 0); teamCard(ctx, A, 90, 160, 470, 390, time, 'J1', sel === 0); ctx.restore();
    ctx.save(); ctx.translate((1 - k) * 600, 0); teamCard(ctx, B, VIEW_W - 90 - 470, 160, 470, 390, time, this.mode2p ? 'J2' : 'CPU', sel === 1); ctx.restore();
    ctx.save(); ctx.translate(VIEW_W / 2, 350); ctx.rotate(-0.08); comicText(ctx, 'VS', 0, 0, 130, PAL.cream, OUT); ctx.restore();
    // lignes d'options
    const rows = this.rows(); const y0 = 592, h = 46;
    rows.forEach(([lab, val], i) => {
      const isSel = sel === i, y = y0 + i * (h + 6);
      if (val === null) { button(ctx, lab, VIEW_W / 2, 838, 440, 62, isSel, time, this.menu.rects, i); return; }
      const w = 640, x = VIEW_W / 2 - w / 2;
      ctx.save(); ctx.translate(x + w / 2, y + h / 2); if (isSel) ctx.scale(1.03, 1.03);
      skewPanel(ctx, -w / 2 + 5, -h / 2 + 6, w, h, 16, OUT, 0.1);
      skewPanel(ctx, -w / 2, -h / 2, w, h, 16, isSel ? PAL.mustard : PAL.cream, 5);
      ctx.font = '26px "Lilita One"'; ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; ctx.fillStyle = isSel ? PAL.cream : '#6a4a54'; ctx.strokeStyle = OUT; ctx.lineWidth = isSel ? 5 : 0;
      if (isSel) ctx.strokeText(lab, -w / 2 + 34, 2); ctx.fillText(lab, -w / 2 + 34, 2);
      ctx.textAlign = 'center'; ctx.font = '34px Bangers'; ctx.fillStyle = isSel ? PAL.cream : '#4a3038'; if (isSel) ctx.strokeText(val, w * 0.2, 2); ctx.fillText(val, w * 0.2, 2);
      if (isSel) { ctx.fillStyle = OUT; const ax = w * 0.2 - 150 - Math.sin(time * 8) * 4, bx = w * 0.2 + 150 + Math.sin(time * 8) * 4; ctx.beginPath(); ctx.moveTo(ax - 10, 0); ctx.lineTo(ax + 6, -12); ctx.lineTo(ax + 6, 12); ctx.fill(); ctx.beginPath(); ctx.moveTo(bx + 10, 0); ctx.lineTo(bx - 6, -12); ctx.lineTo(bx - 6, 12); ctx.fill(); }
      ctx.restore();
      this.menu.rects[i] = { x, y, w, h };
    });
    ctx.font = '19px "Lilita One"'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(246,239,223,0.8)'; ctx.strokeStyle = OUT; ctx.lineWidth = 4;
    const foot = '↑↓ ligne · ←→ modifier · ENTRÉE valider · ÉCHAP retour'; ctx.strokeText(foot, VIEW_W / 2, VIEW_H - 8); ctx.fillText(foot, VIEW_W / 2, VIEW_H - 8);
  }
}

// ---------------------------------------------------------------- Options
export class OptionsScene {
  enter(app, args) { this.app = app; this.from = args.from || 'title'; this.menu = new Menu(5); this.t = 0; this.overlay = !!args.overlay; }
  update(dt) {
    const app = this.app, s = app.settings; this.t += dt;
    const r = this.menu.update(app);
    const sel = this.menu.sel, d = r.dx;
    if (d) {
      if (sel === 0) { s.music = clamp(Math.round((s.music + d * 0.1) * 10) / 10, 0, 1); app.applyAudio(); app.audio.sfx('ui-tick'); }
      if (sel === 1) { s.sfx = clamp(Math.round((s.sfx + d * 0.1) * 10) / 10, 0, 1); app.applyAudio(); app.audio.sfx('bumper'); }
      if (sel === 2) { s.shake = !s.shake; app.applyAudio(); app.audio.sfx('ui-tick'); }
      if (sel === 3) { app.toggleFullscreen(); }
    }
    if (r.ok) {
      if (sel === 2) { s.shake = !s.shake; app.applyAudio(); app.audio.sfx('ui-tick'); }
      else if (sel === 3) app.toggleFullscreen();
      else if (sel === 4) this.exit();
    }
    if (app.input.nav.back) this.exit();
  }
  exit() { this.app.saveSettings(); this.app.audio.sfx('ui-back'); if (this.overlay) this.app.closeOverlay(); else this.app.go(this.from); }
  render(r, time) {
    const ctx = r.ctx, app = this.app, s = app.settings;
    if (!this.overlay) menuBackdrop(app, r, 0.78);
    ctx.save(); ctx.translate(VIEW_W / 2, 100); comicText(ctx, 'OPTIONS', 0, 0, 100, PAL.mustardLight, OUT); ctx.restore();
    const rows = [['MUSIQUE', s.music], ['EFFETS SONORES', s.sfx], ['SECOUSSES D\'ÉCRAN', s.shake ? 'OUI' : 'NON'], ['PLEIN ÉCRAN', document.fullscreenElement ? 'OUI' : 'NON'], ['RETOUR', null]];
    rows.forEach(([lab, v], i) => {
      const isSel = this.menu.sel === i, y = 250 + i * 90;
      if (v === null) { button(ctx, lab, VIEW_W / 2, y + 20, 380, 68, isSel, time, this.menu.rects, i); return; }
      const w = 760, h = 64, x = VIEW_W / 2 - w / 2;
      ctx.save(); ctx.translate(VIEW_W / 2, y + h / 2); if (isSel) ctx.scale(1.03, 1.03);
      skewPanel(ctx, -w / 2 + 5, -h / 2 + 6, w, h, 18, OUT, 0.1);
      skewPanel(ctx, -w / 2, -h / 2, w, h, 18, isSel ? PAL.mustard : PAL.cream, 5);
      ctx.font = '28px "Lilita One"'; ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; ctx.fillStyle = isSel ? PAL.cream : '#6a4a54'; ctx.strokeStyle = OUT; ctx.lineWidth = 5;
      if (isSel) ctx.strokeText(lab, -w / 2 + 40, 2); ctx.fillText(lab, -w / 2 + 40, 2);
      if (typeof v === 'number') {
        const bx = 40, bw = 280;
        for (let k = 0; k < 10; k++) { rrPath(ctx, bx + k * (bw / 10), -14, bw / 10 - 5, 28, 4); ctx.fillStyle = k < Math.round(v * 10) ? (isSel ? PAL.cream : PAL.salmon) : 'rgba(0,0,0,0.25)'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke(); }
      } else { ctx.textAlign = 'center'; ctx.font = '38px Bangers'; ctx.fillStyle = isSel ? PAL.cream : '#4a3038'; if (isSel) ctx.strokeText(v, 200, 2); ctx.fillText(v, 200, 2); }
      ctx.restore();
      this.menu.rects[i] = { x, y, w, h };
    });
    ctx.font = '19px "Lilita One"'; ctx.textAlign = 'center'; ctx.fillStyle = 'rgba(246,239,223,0.8)'; ctx.strokeStyle = OUT; ctx.lineWidth = 4;
    const foot = '←→ régler · ENTRÉE valider · ÉCHAP retour'; ctx.strokeText(foot, VIEW_W / 2, VIEW_H - 24); ctx.fillText(foot, VIEW_W / 2, VIEW_H - 24);
  }
}

// ---------------------------------------------------------------- Match
export class MatchScene {
  enter(app, cfg) {
    this.app = app; this.cfg = cfg; this.paused = false; this.sub = null; this.menu = new Menu(4);
    app.stopAttract();
    app.input.mode2p = cfg.mode2p;
    app.fx.clear(); app.fx.shakeEnabled = app.settings.shake;
    this.buildArena(cfg.teamA, cfg.teamB);
    this.m = new Match({
      teamA: cfg.teamA, teamB: cfg.teamB, mode2p: cfg.mode2p, difficulty: cfg.difficulty, duration: cfg.duration,
      audio: app.audio, music: app.music, fx: app.fx, input: app.input, onEnd: (res) => this.finish(res),
    });
    this.m.onSwap = () => { const l = this.m.teams.find((t) => t.attackDir > 0).def, r = this.m.teams.find((t) => t.attackDir < 0).def; this.buildArena(l, r); };
    app.music.stop(0.4);
    app.audio.sfx('whistle', { dur: 0.35 }); app.music.jingle('intro');
    this.ended = false; this.wasHidden = false;
  }
  buildArena(l, r) { this.app.arena.build(l, r); }
  finish(res) { if (this.ended) return; this.ended = true; this.app.go('result', { res, cfg: this.cfg }); }
  update(dt) {
    const app = this.app, nav = app.input.nav;
    if (this.sub) { this.sub.update(dt); return; }
    if (this.paused) {
      const r = this.menu.update(app);
      if (r.ok) this.pickPause(this.menu.sel);
      if (nav.pause || nav.back) { this.resume(); }
      return;
    }
    if (nav.pause && !['fulltime'].includes(this.m.phase)) { this.paused = true; this.menu.sel = 0; app.audio.sfx('ui-back'); app.audio.duckMusic(0.35, 0.01); app.music.setIntensity(0.1); return; }
    if (document.hidden) { this.paused = true; return; }
    this.m.update(dt);
  }
  resume() { this.paused = false; this.app.audio.sfx('ui-ok'); this.app.music.setIntensity(0.5); this.app.audio.duckMusic(1, 0.01); }
  pickPause(i) {
    const app = this.app; app.audio.sfx('ui-ok');
    if (i === 0) this.resume();
    else if (i === 1) { this.sub = new OptionsScene(); this.sub.enter(app, { overlay: true, from: 'pause' }); app.overlay = this; }
    else if (i === 2) { app.audio.duckMusic(1, 0.01); app.go('match', this.cfg); }
    else if (i === 3) { app.audio.duckMusic(1, 0.01); app.go('title'); }
  }
  closeOverlay() { this.sub = null; }
  render(r, time) {
    const ctx = r.ctx, m = this.m, app = this.app;
    r.drawWorld(m, app.arena, app.fx, time);
    r.drawHUD(m, time, 1 / 60);
    if (this.paused && !this.sub) {
      ctx.fillStyle = 'rgba(12,6,12,0.68)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H);
      ctx.save(); ctx.translate(VIEW_W / 2, 210); comicText(ctx, 'PAUSE', 0, 0, 130, PAL.mustardLight, OUT); ctx.restore();
      ['REPRENDRE', 'OPTIONS', 'RECOMMENCER', 'QUITTER LE MATCH'].forEach((l, i) => button(ctx, l, VIEW_W / 2, 380 + i * 96, 480, 74, this.menu.sel === i, time, this.menu.rects, i));
    }
    if (this.sub) { ctx.fillStyle = 'rgba(12,6,12,0.85)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H); this.sub.render(r, time); }
  }
}

// ---------------------------------------------------------------- Résultats
export class ResultScene {
  enter(app, args) {
    this.app = app; this.res = args.res; this.cfg = args.cfg; this.menu = new Menu(2); this.t = 0;
    app.startAttract();
    const w = this.res.winner;
    app.music.stop(0.2);
    app.music.jingle(w < 0 ? 'draw' : (w === 0 || app.input.mode2p ? 'win' : 'lose'));
    app.audio.sfx('crowd-cheer');
    this.confetti = [];
    if (w >= 0) app.fx2 = app.fx;
  }
  update(dt) {
    const app = this.app; this.t += dt;
    const r = this.menu.update(app);
    if (r.ok) {
      app.audio.sfx('ui-ok');
      if (this.menu.sel === 0) app.go('match', this.cfg); else app.go('title');
    }
  }
  render(r, time) {
    const ctx = r.ctx, app = this.app, res = this.res;
    menuBackdrop(app, r, 0.8);
    const w = res.winner, k = easeOutCubic(clamp(this.t * 1.6, 0, 1));
    ctx.save(); ctx.translate(VIEW_W / 2, 96); ctx.scale(k, k);
    comicText(ctx, w < 0 ? 'MATCH NUL' : 'VICTOIRE', 0, 0, 120, w < 0 ? PAL.cream : res.defs[w].light, OUT); ctx.restore();
    if (w >= 0) { ctx.save(); ctx.translate(VIEW_W / 2, 170); comicText(ctx, res.defs[w].name, 0, 0, 56, PAL.cream, OUT, 'Lilita One', 0.07); ctx.restore(); }
    // cartes
    [0, 1].forEach((i) => {
      const def = res.defs[i], win = w === i, x = i === 0 ? 150 : VIEW_W - 150 - 520;
      ctx.save(); ctx.translate(x, 230 + (1 - k) * 60);
      skewPanel(ctx, 6, 8, 520, 470, 20, OUT, 0.1);
      skewPanel(ctx, 0, 0, 520, 470, 20, shadeColor(def.main, -0.1), 6);
      ctx.save(); ctx.translate(112, 330); ctx.scale(1.65, 1.65);
      ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.beginPath(); ctx.ellipse(0, 4, 34, 11, 0, 0, TAU); ctx.fill();
      const st = w < 0 ? 'run' : win ? 'celebrate' : 'sad';
      drawHumanoid(ctx, def, i, { t: time, phase: 0, run: 0, flip: i === 1, hasBall: false, charge: 0, state: st, sq: 0, stunT: 0, blink: false }, 4);
      ctx.restore();
      ctx.save(); ctx.translate(260, 50); comicText(ctx, def.name, 0, 0, 52, PAL.cream, OUT); ctx.restore();
      ctx.save(); ctx.translate(400, 150); comicText(ctx, String(res.scores[i]), 0, 0, 120, PAL.cream, OUT); ctx.restore();
      ctx.font = '20px "Lilita One"'; ctx.textAlign = 'left'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 4;
      const st2 = res.stats[i];
      const rows = [['Buts', res.goals[i]], ['Tirs cadrés', st2.shots], ['Tacles réussis', st2.tackles], ['Arrêts', st2.saves], ['Pads allumés', st2.pads], ['Pièces', st2.coins]];
      rows.forEach(([n, v], j) => { const yy = 234 + j * 34, xx = 250; ctx.textAlign = 'left'; ctx.strokeText(n, xx - 30, yy); ctx.fillText(n, xx - 30, yy); ctx.textAlign = 'right'; ctx.strokeText(String(v), xx + 250, yy); ctx.fillText(String(v), xx + 250, yy); });
      ctx.restore();
    });
    ['REVANCHE', 'MENU PRINCIPAL'].forEach((l, i) => button(ctx, l, VIEW_W / 2 + (i ? 200 : -200), 800, 360, 70, this.menu.sel === i, time, this.menu.rects, i));
  }
}
