// Rendu d'un match : monde (caméra, entités triées, effets, lumière) + HUD comic.
import { W, H, CY, VIEW_W, VIEW_H, BUMPERS, PORTALS, GOAL_H, PAL, TAU, clamp, lerp, easeOutBack, easeOutElastic } from './config.js';
import { drawHumanoid, drawKeeper, drawBall, drawToken, drawBumper, drawPortal, rrPath, TOKEN_INFO, shadeColor } from './art.js';
import { comicText } from './fx.js';

const OUT = PAL.outline;

export class Renderer {
  constructor(canvas) {
    this.canvas = canvas; this.ctx = canvas.getContext('2d', { alpha: false });
    this.sx = 1; this.ox = 0; this.oy = 0;
    this.vig = this._makeVignette();
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const cw = Math.floor(window.innerWidth * dpr), ch = Math.floor(window.innerHeight * dpr);
    if (this.canvas.width !== cw || this.canvas.height !== ch) { this.canvas.width = cw; this.canvas.height = ch; }
    this.sx = Math.min(cw / VIEW_W, ch / VIEW_H);
    this.ox = (cw - VIEW_W * this.sx) / 2; this.oy = (ch - VIEW_H * this.sx) / 2;
  }

  _makeVignette() {
    const c = document.createElement('canvas'); c.width = 320; c.height = 180;
    const x = c.getContext('2d');
    const g = x.createRadialGradient(160, 90, 60, 160, 90, 210);
    g.addColorStop(0, 'rgba(10,4,12,0)'); g.addColorStop(0.65, 'rgba(10,4,12,0.18)'); g.addColorStop(1, 'rgba(10,4,12,0.72)');
    x.fillStyle = g; x.fillRect(0, 0, 320, 180);
    return c;
  }

  // Prépare le contexte en coordonnées logiques 1600x900 (avec bandes noires si le ratio diffère).
  begin(bg = '#150d12') {
    const ctx = this.ctx;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = bg; ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(this.sx, 0, 0, this.sx, this.ox, this.oy);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, VIEW_W, VIEW_H); ctx.clip();
    return ctx;
  }
  end() {
    const ctx = this.ctx; ctx.restore();
    // bandes latérales opaques
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#0c070b';
    if (this.ox > 0) { ctx.fillRect(0, 0, this.ox, this.canvas.height); ctx.fillRect(this.canvas.width - this.ox, 0, this.ox, this.canvas.height); }
    if (this.oy > 0) { ctx.fillRect(0, 0, this.canvas.width, this.oy); ctx.fillRect(0, this.canvas.height - this.oy, this.canvas.width, this.oy); }
  }

  // ----------------------------------------------------------------- monde
  drawWorld(m, arena, fx, time) {
    const ctx = this.ctx, cam = m.cam;
    const sh = fx.shakeOffset();
    ctx.save();
    ctx.translate(VIEW_W / 2 + sh.x + cam.kx, VIEW_H / 2 + sh.y + cam.ky);
    ctx.rotate(sh.r); ctx.scale(cam.zoom, cam.zoom); ctx.translate(-cam.x, -cam.y);
    const hw = VIEW_W / 2 / cam.zoom + 60, hh = VIEW_H / 2 / cam.zoom + 60;
    const view = { x0: cam.x - hw, x1: cam.x + hw, y0: cam.y - hh, y1: cam.y + hh };

    arena.drawStands(ctx, view);
    let cheerSide = -1;
    if (m.phase === 'goal' && m.scoredTeam >= 0) cheerSide = m.teams[m.scoredTeam].attackDir > 0 ? 0 : 1;
    else if (m.phase === 'fulltime' && m.winner >= 0) cheerSide = m.teams[m.winner].attackDir > 0 ? 0 : 1;
    arena.drawCrowd(ctx, time, m.excite, view, cheerSide);
    arena.drawArena(ctx);
    this.drawFloorLights(ctx, m, time);
    fx.draw(ctx, 0, view);
    arena.drawPads(ctx, m.pads, time, m.teams.map((t) => t.def.main));
    for (const p of PORTALS) drawPortal(ctx, p.x, p.y, p.r, time, m.portalGlow);
    this.drawLauncher(ctx, m, time);
    // cages (arrière)
    for (const side of [0, 1]) {
      const team = m.teams.find((t) => (side === 0 ? t.attackDir > 0 : t.attackDir < 0)); // équipe qui défend ce côté
      arena.drawGoalBack(ctx, side, team.def, m.goalFlash[side]);
    }
    this.drawShadows(ctx, m);
    this.drawEntities(ctx, m, fx, time);
    fx.draw(ctx, 1, view);
    for (const side of [0, 1]) {
      const team = m.teams.find((t) => (side === 0 ? t.attackDir > 0 : t.attackDir < 0));
      arena.drawGoalFront(ctx, side, team.def, m.goalFlash[side], time);
    }
    arena.drawFront(ctx);
    // marqueurs par-dessus tout
    this.drawMarkers(ctx, m, time);
    // lumière additive
    ctx.globalCompositeOperation = 'lighter';
    this.drawGlow(ctx, m, fx, time);
    fx.draw(ctx, 2, view);
    ctx.globalCompositeOperation = 'source-over';
    ctx.restore();

    // ----- post
    ctx.globalAlpha = 1; ctx.drawImage(this.vig, 0, 0, VIEW_W, VIEW_H);
    if (fx.flash > 0.01) { ctx.globalAlpha = Math.min(1, fx.flash); ctx.fillStyle = fx.flashColor; ctx.fillRect(0, 0, VIEW_W, VIEW_H); ctx.globalAlpha = 1; }
    // alerte fin de période
    if (m.phase === 'play' && !m.overtime && m.clock < 10) {
      const a = (1 - m.clock / 10) * (0.12 + 0.1 * Math.sin(time * 8));
      ctx.fillStyle = `rgba(255,60,50,${Math.max(0, a)})`; ctx.fillRect(0, 0, VIEW_W, 14); ctx.fillRect(0, VIEW_H - 14, VIEW_W, 14); ctx.fillRect(0, 0, 14, VIEW_H); ctx.fillRect(VIEW_W - 14, 0, 14, VIEW_H);
    }
  }

  drawFloorLights(ctx, m, time) {
    ctx.save(); ctx.globalCompositeOperation = 'lighter';
    for (let i = 0; i < 3; i++) {
      const x = W * (0.5 + 0.38 * Math.sin(time * 0.23 + i * 2.1)), y = H * (0.5 + 0.2 * Math.cos(time * 0.31 + i * 1.7));
      const g = ctx.createRadialGradient(x, y, 10, x, y, 320);
      g.addColorStop(0, 'rgba(255,240,205,0.11)'); g.addColorStop(1, 'rgba(255,240,205,0)');
      ctx.fillStyle = g; ctx.save(); ctx.translate(x, y); ctx.scale(1, 0.7); ctx.translate(-x, -y); ctx.fillRect(x - 320, y - 320, 640, 640); ctx.restore();
    }
    ctx.restore();
  }

  drawLauncher(ctx, m, time) {
    const x = W / 2, y = CY;
    const arming = m.phase === 'kickoff' ? Math.min(1, m.phaseT / 1.2) : 0;
    for (let i = 0; i < 10; i++) {
      const a = i * TAU / 10 + time * (0.5 + arming * 6), on = arming > 0 ? (Math.sin(a * 3 - time * 20) > 0 ? 1 : 0.25) : 0.5;
      ctx.fillStyle = i % 2 ? `rgba(255,200,80,${on})` : `rgba(255,120,90,${on})`;
      ctx.beginPath(); ctx.arc(x + Math.cos(a) * 66, y + Math.sin(a) * 66 * 0.9, 5.5, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    }
    if (arming > 0) {
      const g = ctx.createRadialGradient(x, y, 4, x, y, 60); g.addColorStop(0, `rgba(255,240,180,${0.9 * arming})`); g.addColorStop(1, 'rgba(255,180,60,0)');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 60, 0, TAU); ctx.fill();
      // balle qui monte dans le puits
      if (m.ball.state === 'launcher') { const bz = 6 + arming * 14; ctx.save(); ctx.beginPath(); ctx.arc(x, y, 50, 0, TAU); ctx.clip(); drawBall(ctx, x, y - bz + 6, 15, time * 3, '#ffb35a', 0.6); ctx.restore(); }
    }
  }

  drawShadows(ctx, m) {
    ctx.fillStyle = 'rgba(8,6,12,0.38)';
    for (const p of m.players) {
      const k = 1 / (1 + p.z / 160), rx = (p.role === 'GK' ? p.r * 1.7 : p.r * 1.25) * k, ry = rx * 0.42;
      ctx.beginPath(); ctx.ellipse(p.x + (p.slideT > 0 ? p.slideDx * 26 : 0), p.y + 3, rx * (p.slideT > 0 || p.stun > 0 ? 1.7 : 1), ry, 0, 0, TAU); ctx.fill();
    }
    const b = m.ball;
    if (b.state === 'free' || b.holder) {
      const k = 1 / (1 + b.z / 120);
      ctx.fillStyle = `rgba(8,6,12,${0.42 * k + 0.1})`;
      ctx.beginPath(); ctx.ellipse(b.x, b.y + 4, 15 * k + 3, (15 * k + 3) * 0.45, 0, 0, TAU); ctx.fill();
    }
    for (const bm of BUMPERS) { ctx.fillStyle = 'rgba(8,6,12,0.35)'; ctx.beginPath(); ctx.ellipse(bm.x + 4, bm.y + 12, bm.r * 1.2, bm.r * 0.6, 0, 0, TAU); ctx.fill(); }
  }

  drawEntities(ctx, m, fx, time) {
    const list = [];
    for (const p of m.players) list.push({ y: p.y, k: 0, p });
    const b = m.ball;
    if (b.state === 'free' || b.holder) list.push({ y: b.holder ? b.y + 0.5 : b.y, k: 1 });
    BUMPERS.forEach((bm, i) => list.push({ y: bm.y + 14, k: 2, i }));
    for (const tk of m.tokens) list.push({ y: tk.y, k: 3, tk });
    list.sort((a, c) => a.y - c.y);
    for (const e of list) {
      if (e.k === 0) this.drawPlayer(ctx, m, e.p, time);
      else if (e.k === 1) this.drawBallEnt(ctx, m, time);
      else if (e.k === 2) drawBumper(ctx, BUMPERS[e.i].x, BUMPERS[e.i].y, BUMPERS[e.i].r, m.bumperPulse[e.i], time);
      else if (e.k === 3) {
        const tk = e.tk, bob = Math.sin(time * 4 + tk.x) * 5, fade = tk.life < 3 ? (Math.sin(time * 20) > 0 ? 1 : 0.3) : 1;
        ctx.fillStyle = 'rgba(8,6,12,0.3)'; ctx.beginPath(); ctx.ellipse(tk.x, tk.y + 6, 16, 6, 0, 0, TAU); ctx.fill();
        ctx.save(); ctx.translate(tk.x, tk.y - 30 - bob);
        const info = TOKEN_INFO[tk.type], g = ctx.createRadialGradient(0, 0, 4, 0, 0, 44); g.addColorStop(0, info.color + '99'); g.addColorStop(1, info.color + '00');
        ctx.fillStyle = g; ctx.fillRect(-44, -44, 88, 88);
        drawToken(ctx, tk.type, tk.t, fade); ctx.restore();
      }
    }
  }

  drawPlayer(ctx, m, p, time) {
    const team = m.teams[p.team], def = team.def;
    const sp = Math.hypot(p.vx, p.vy);
    const frozen = team.freeze > 0;
    let state = 'run';
    if (p.stun > 0 || frozen) state = 'stun'; else if (p.slideT > 0) state = 'slide'; else if (p.celebrate) state = 'celebrate'; else if (p.sad) state = 'sad'; else if (p.z > 6) state = 'jump';
    const pose = {
      t: time, phase: p.runPhase, run: clamp(sp / 320, 0, 1), flip: p.flip, hasBall: p.hasBall, charge: Math.min(1, p.chargeT / 0.7), state,
      sq: clamp(p.sq, -0.25, 0.25), stunT: frozen ? 1 : p.stun, blink: p.blink > 0,
    };
    ctx.save();
    ctx.translate(p.x, p.y - p.z);
    if (p.role === 'GK') {
      pose.flip = team.attackDir < 0; pose.reach = p.reach; pose.moveY = p.vy / 300; pose.jump = p.z > 5;
      if (state === 'stun') { ctx.rotate(0.0); }
      const sc = 0.92; ctx.scale(sc, sc);
      drawKeeper(ctx, def, pose);
    } else {
      if (p.hurtT > 0) p.hurtT -= 0.016;
      ctx.scale(1.14, 1.14);
      drawHumanoid(ctx, def, p.idx, pose, p.num);
    }
    // teinte gelée
    if (frozen) {
      ctx.globalAlpha = 0.5; ctx.fillStyle = '#bfe8ff'; ctx.beginPath(); ctx.ellipse(0, -50, p.role === 'GK' ? 60 : 28, p.role === 'GK' ? 70 : 54, 0, 0, TAU); ctx.fill(); ctx.globalAlpha = 1;
      ctx.strokeStyle = '#eaf8ff'; ctx.lineWidth = 3; for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(-20 + i * 10, -8); ctx.lineTo(-24 + i * 12, -60 - (i % 2) * 20); ctx.stroke(); }
    }
    // étoiles d'étourdissement
    if (p.stun > 0.2 && !frozen) {
      for (let i = 0; i < 3; i++) {
        const a = time * 6 + i * TAU / 3, x = Math.cos(a) * 24, y = -108 + Math.sin(a) * 7;
        ctx.save(); ctx.translate(x, y); ctx.rotate(time * 4); ctx.beginPath();
        for (let k = 0; k < 10; k++) { const rr = k % 2 ? 4 : 9, aa = -Math.PI / 2 + k * Math.PI / 5; k ? ctx.lineTo(Math.cos(aa) * rr, Math.sin(aa) * rr) : ctx.moveTo(Math.cos(aa) * rr, Math.sin(aa) * rr); }
        ctx.closePath(); ctx.fillStyle = PAL.mustardLight; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); ctx.restore();
      }
    }
    // auras de bonus
    if (p.speedT > 0 || p.powerT > 0) {
      ctx.globalAlpha = 0.6 + Math.sin(time * 12) * 0.2; ctx.strokeStyle = p.powerT > 0 ? '#ff7a59' : '#63d6c4'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.ellipse(0, -2, 30, 11, 0, 0, TAU); ctx.stroke(); ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  drawBallEnt(ctx, m, time) {
    const b = m.ball;
    // traînée
    const tr = b.trail;
    if (tr.length > 2) {
      for (let i = 0; i < tr.length; i++) {
        const q = tr[i], k = i / tr.length, s = clamp(q.s / 1400, 0, 1);
        if (s < 0.25) continue;
        ctx.globalAlpha = k * 0.42 * s; ctx.fillStyle = m.teamColorOf(b.lastTeam);
        ctx.beginPath(); ctx.arc(q.x, q.y - q.z, 15 * (0.35 + k * 0.65), 0, TAU); ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    const hot = b.heat > 0.55 ? (b.heat - 0.55) * 1.5 : 0;
    drawBall(ctx, b.x, b.y - b.z, b.r, b.rot, m.teamColorOf(b.lastTeam), hot);
  }

  drawMarkers(ctx, m, time) {
    for (const t of m.teams) {
      if (t.human < 0 || !t.ctrl) continue;
      const p = t.ctrl;
      if (m.phase === 'goal' || m.phase === 'halftime' || m.phase === 'fulltime' || m.phase === 'endhalf') continue;
      const col = t.def.light;
      // anneau au sol
      ctx.save(); ctx.translate(p.x, p.y + 3); ctx.scale(1, 0.45);
      ctx.strokeStyle = OUT; ctx.lineWidth = 9; ctx.beginPath(); ctx.arc(0, 0, 30, 0, TAU); ctx.stroke();
      ctx.strokeStyle = col; ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(0, 0, 30, 0, TAU); ctx.stroke(); ctx.restore();
      // flèche + étiquette joueur
      const by = p.y - p.z - 138 + Math.sin(time * 7) * 4;
      ctx.save(); ctx.translate(p.x, by);
      ctx.beginPath(); ctx.moveTo(-15, -18); ctx.lineTo(15, -18); ctx.lineTo(0, 0); ctx.closePath();
      ctx.fillStyle = col; ctx.fill(); ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.lineJoin = 'round'; ctx.stroke();
      const lab = m.mode2p ? `P${t.human + 1}` : 'J1';
      comicText(ctx, lab, 0, -32, 24, PAL.cream, OUT);
      ctx.restore();
      // jauge de charge
      if (p.chargeT > 0.12) {
        const k = Math.min(1, p.chargeT / 0.7);
        ctx.save(); ctx.translate(p.x, p.y - p.z - 118);
        rrPath(ctx, -30, 0, 60, 11, 5); ctx.fillStyle = 'rgba(10,6,12,0.75)'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
        rrPath(ctx, -28, 2, 56 * k, 7, 3); ctx.fillStyle = k > 0.85 ? '#ffe36a' : k > 0.5 ? PAL.mustard : PAL.salmon; ctx.fill();
        ctx.restore();
      }
      // flèche de visée quand on tient la balle
      if (p.hasBall) {
        const l = 70 + Math.min(1, p.chargeT / 0.7) * 60, a = Math.atan2(p.fy, p.fx);
        ctx.save(); ctx.translate(p.x, p.y + 2); ctx.scale(1, 0.55); ctx.rotate(a);
        ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.moveTo(44, -6); ctx.lineTo(l, -6); ctx.lineTo(l, -15); ctx.lineTo(l + 26, 0); ctx.lineTo(l, 15); ctx.lineTo(l, 6); ctx.lineTo(44, 6); ctx.closePath();
        ctx.fillStyle = col; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke(); ctx.restore(); ctx.globalAlpha = 1;
      }
    }
  }

  drawGlow(ctx, m, fx, time) {
    const b = m.ball;
    if (b.state === 'free' || b.holder) {
      const s = Math.hypot(b.vx, b.vy), k = clamp(s / 1400, 0, 1);
      const r = 46 + k * 60, g = ctx.createRadialGradient(b.x, b.y - b.z, 2, b.x, b.y - b.z, r);
      const c = m.teamColorOf(b.lastTeam);
      g.addColorStop(0, c + 'aa'); g.addColorStop(0.35, c + '44'); g.addColorStop(1, c + '00');
      ctx.globalAlpha = 0.35 + k * 0.6; ctx.fillStyle = g; ctx.fillRect(b.x - r, b.y - b.z - r, r * 2, r * 2); ctx.globalAlpha = 1;
    }
    for (const p of m.pads) {
      if (p.owner < 0 && p.flash <= 0) continue;
      const y = p.wall === 'top' ? 10 : H - 8, c = p.owner < 0 ? '#ffffff' : m.teams[p.owner].def.light;
      const g = ctx.createRadialGradient(p.x, y, 4, p.x, y, 110); g.addColorStop(0, c + '88'); g.addColorStop(1, c + '00');
      ctx.globalAlpha = 0.25 + p.flash * 0.7; ctx.fillStyle = g; ctx.fillRect(p.x - 110, y - 110, 220, 220); ctx.globalAlpha = 1;
    }
    for (const pt of PORTALS) {
      const g = ctx.createRadialGradient(pt.x, pt.y, 4, pt.x, pt.y, 90); g.addColorStop(0, 'rgba(150,200,255,0.5)'); g.addColorStop(1, 'rgba(150,200,255,0)');
      ctx.globalAlpha = 0.6 + Math.sin(time * 4) * 0.2 + m.portalGlow; ctx.fillStyle = g; ctx.fillRect(pt.x - 90, pt.y - 90, 180, 180); ctx.globalAlpha = 1;
    }
    for (const side of [0, 1]) if (m.goalFlash[side] > 0) {
      const gx = side === 0 ? -60 : W + 60, g = ctx.createRadialGradient(gx, CY, 10, gx, CY, 420);
      g.addColorStop(0, 'rgba(255,240,200,0.55)'); g.addColorStop(1, 'rgba(255,240,200,0)');
      ctx.globalAlpha = Math.min(0.8, m.goalFlash[side]); ctx.fillStyle = g; ctx.fillRect(gx - 420, CY - 420, 840, 840); ctx.globalAlpha = 1;
    }
  }

  // ----------------------------------------------------------------- HUD
  panel(ctx, x, y, w, h, skew, fill, stroke = OUT, lw = 5) {
    ctx.beginPath(); ctx.moveTo(x + skew, y); ctx.lineTo(x + w + skew, y); ctx.lineTo(x + w - skew, y + h); ctx.lineTo(x - skew, y + h); ctx.closePath();
    ctx.fillStyle = fill; ctx.fill(); ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.lineJoin = 'round'; ctx.stroke();
  }

  drawHUD(m, time, dt) {
    const ctx = this.ctx;
    const cx = VIEW_W / 2, top = 14;
    const tl = m.teams.find((t) => t.attackDir > 0), tr = m.teams.find((t) => t.attackDir < 0);   // gauche / droite à l'écran
    // ---- tableau de score
    const drawSide = (t, x, right) => {
      const def = t.def; t.scorePop = Math.max(0, (t.scorePop || 0) - dt * 2.2);
      ctx.save();
      this.panel(ctx, x, top + 8, 250, 76, 16, def.main);
      ctx.save(); ctx.beginPath(); ctx.moveTo(x + 16, top + 8); ctx.lineTo(x + 266, top + 8); ctx.lineTo(x + 234, top + 84); ctx.lineTo(x - 16, top + 84); ctx.closePath(); ctx.clip();
      ctx.fillStyle = def.dark; ctx.globalAlpha = 0.5; ctx.fillRect(x - 20, top + 56, 300, 40); ctx.globalAlpha = 0.9; ctx.fillStyle = def.accent; ctx.fillRect(right ? x - 20 : x + 200, top + 4, 70, 90); ctx.restore();
      ctx.font = '25px Bangers'; ctx.textAlign = right ? 'right' : 'left'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round';
      ctx.lineWidth = 5; ctx.strokeStyle = OUT; ctx.fillStyle = PAL.cream;
      const nx = right ? x + 240 : x + 18;
      ctx.strokeText(def.name, nx, top + 28); ctx.fillText(def.name, nx, top + 28);
      const pop = t.scorePop > 0 ? 1 + easeOutBack(t.scorePop) * 0.4 : 1;
      ctx.save(); ctx.translate(right ? x + 60 : x + 190, top + 58); ctx.scale(pop, pop);
      comicText(ctx, String(t.score), 0, 0, 58, PAL.cream, OUT);
      ctx.restore();
      // pastilles de but
      ctx.font = '18px "Lilita One"'; ctx.textAlign = right ? 'left' : 'right';
      ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.fillStyle = PAL.cream;
      const gx = right ? x + 118 : x + 132; ctx.strokeText(`${t.goals} but${t.goals > 1 ? 's' : ''}`, right ? x + 108 : x + 138, top + 66); ctx.fillText(`${t.goals} but${t.goals > 1 ? 's' : ''}`, right ? x + 108 : x + 138, top + 66);
      ctx.restore();
      // multiplicateur
      if (t.mult > 1) {
        const bx = right ? x + 200 : x + 50, by = top + 106, pulse = 1 + Math.sin(time * 9) * 0.08;
        ctx.save(); ctx.translate(bx, by); ctx.scale(pulse, pulse);
        this.panel(ctx, -46, -16, 92, 32, 8, PAL.mustard); comicText(ctx, 'BUT x2', 0, 1, 22, PAL.cream, OUT); ctx.restore();
      }
    };
    drawSide(tl, cx - 400 - 6, false);
    drawSide(tr, cx + 156, true);
    // chrono
    this.panel(ctx, cx - 126, top, 252, 92, 20, '#241a22', OUT, 6);
    this.panel(ctx, cx - 116, top + 8, 232, 76, 16, '#33252f', '#0f0a0e', 3);
    const clk = m.overtime ? 'MORT SUBITE' : this.fmt(m.clock);
    const low = !m.overtime && m.clock < 10 && m.phase === 'play';
    if (m.overtime) comicText(ctx, clk, cx, top + 44, 32, PAL.salmonLight, OUT); else comicText(ctx, clk, cx, top + 42, 56, low ? (Math.sin(time * 12) > 0 ? '#ff6a5a' : PAL.cream) : PAL.cream, OUT);
    ctx.font = '19px "Lilita One"'; ctx.textAlign = 'center'; ctx.fillStyle = PAL.mustardLight; ctx.strokeStyle = OUT; ctx.lineWidth = 4;
    const ht = m.overtime ? 'PROLONGATION' : `PÉRIODE ${m.half} / 2`; ctx.strokeText(ht, cx, top + 78); ctx.fillText(ht, cx, top + 78);
    // pads
    this.panel(ctx, cx - 88, top + 96, 176, 22, 8, 'rgba(24,16,22,0.9)', OUT, 3);
    for (let i = 0; i < m.pads.length; i++) {
      const p = m.pads[i], x = cx - 76 + i * 18, y = top + 107;
      ctx.beginPath(); ctx.arc(x + 9, y, 6.5, 0, TAU); ctx.fillStyle = p.owner < 0 ? '#3a2d36' : m.teams[p.owner].def.main; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      if (p.flash > 0) { ctx.fillStyle = `rgba(255,255,255,${p.flash})`; ctx.fill(); }
    }
    // ---- statuts joueurs humains (endurance + bonus)
    for (const t of m.teams) {
      if (t.human < 0 || !t.ctrl) continue;
      const p = t.ctrl, left = t === tl, x = left ? 30 : VIEW_W - 30 - 220, y = VIEW_H - 62;
      this.panel(ctx, x, y, 220, 34, 10, 'rgba(24,16,22,0.85)', OUT, 4);
      rrPath(ctx, x + 12, y + 10, 196 * 0.98, 14, 6); ctx.fillStyle = '#0f0a0e'; ctx.fill();
      rrPath(ctx, x + 12, y + 10, 196 * p.stamina, 14, 6); ctx.fillStyle = p.turboLock ? PAL.salmon : (p.stamina > 0.35 ? PAL.green : PAL.mustard); ctx.fill();
      ctx.font = '15px "Lilita One"'; ctx.textAlign = 'left'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 3;
      this.panel(ctx, x + 6, y - 26, 84, 20, 8, 'rgba(24,16,22,0.9)', OUT, 3); ctx.textBaseline = 'middle'; ctx.fillText('TURBO', x + 22, y - 15); ctx.textBaseline = 'alphabetic';
      let bxx = x + (left ? 232 : -14);
      const icons = []; if (p.speedT > 0) icons.push(['speed', p.speedT]); if (p.powerT > 0) icons.push(['power', p.powerT]);
      icons.forEach(([ty, tt], i) => { const ix = left ? x + 240 + i * 44 : x - 24 - i * 44; ctx.save(); ctx.translate(ix, y + 17); ctx.scale(0.7, 0.7); drawToken(ctx, ty, time); ctx.restore(); rrPath(ctx, ix - 12, y + 34, 24 * Math.min(1, tt / 8), 4, 2); ctx.fillStyle = TOKEN_INFO[ty].color; ctx.fill(); });
    }
    this.drawMinimap(ctx, m, time);
    this.drawAnnounce(ctx, m, time);
    this.drawPhaseOverlay(ctx, m, time);
    // aide contrôles
    if (m.hint > 0 && (m.phase === 'countdown' || m.phase === 'play' || m.phase === 'kickoff')) this.drawHint(ctx, m);
  }

  drawHint(ctx, m) {
    const a = Math.min(1, m.hint / 1.5);
    ctx.save(); ctx.globalAlpha = a;
    const lines = m.mode2p
      ? ['J1 : ZQSD/WASD · F tir/tacle · G lob/saut · H turbo', 'J2 : Flèches · K tir/tacle · L lob/saut · ; turbo']
      : ['Déplacement : ZQSD / WASD / Flèches  ·  Tir / Tacle : ESPACE ou F (maintenir = puissance)', 'Lob / Saut : G ou K  ·  Turbo : MAJ  ·  Changer de joueur : A/Q ou E  ·  Pause : ÉCHAP'];
    const w = 1000, x = (VIEW_W - w) / 2, y = VIEW_H - 128;
    this.panel(ctx, x, y, w, lines.length * 30 + 20, 14, 'rgba(24,16,22,0.88)', OUT, 4);
    ctx.font = '21px "Lilita One"'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = PAL.cream;
    lines.forEach((l, i) => ctx.fillText(l, VIEW_W / 2, y + 27 + i * 30));
    ctx.restore();
  }

  fmt(s) { s = Math.max(0, Math.ceil(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }

  drawMinimap(ctx, m, time) {
    const w = 250, h = w * H / W * 1.0, x = VIEW_W / 2 - w / 2, y = VIEW_H - h - 26;
    const sx = w / W, sy = h / H;
    ctx.save(); ctx.globalAlpha = 0.92;
    rrPath(ctx, x - 8, y - 8, w + 16, h + 16, 10); ctx.fillStyle = 'rgba(22,15,20,0.8)'; ctx.fill(); ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = 'rgba(88,117,137,0.55)'; ctx.fillRect(x, y, w, h);
    const tl = m.teams.find((t) => t.attackDir > 0), tr = m.teams.find((t) => t.attackDir < 0);
    ctx.fillStyle = tl.def.main; ctx.globalAlpha = 0.25; ctx.fillRect(x, y, w / 2, h); ctx.fillStyle = tr.def.main; ctx.fillRect(x + w / 2, y, w / 2, h); ctx.globalAlpha = 0.92;
    ctx.strokeStyle = 'rgba(246,239,223,0.6)'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(x + w / 2, y); ctx.lineTo(x + w / 2, y + h); ctx.stroke();
    ctx.strokeRect(x, y, w, h);
    ctx.fillStyle = tl.def.light; ctx.fillRect(x - 5, y + h / 2 - 12, 5, 24); ctx.fillStyle = tr.def.light; ctx.fillRect(x + w, y + h / 2 - 12, 5, 24);
    for (const b of BUMPERS) { ctx.fillStyle = '#ffd23f'; ctx.beginPath(); ctx.arc(x + b.x * sx, y + b.y * sy, 3, 0, TAU); ctx.fill(); }
    for (const p of PORTALS) { ctx.fillStyle = '#9adcff'; ctx.beginPath(); ctx.arc(x + p.x * sx, y + p.y * sy, 3.5, 0, TAU); ctx.fill(); }
    for (const p of m.players) {
      const c = m.teams[p.team].def; const ctrl = m.teams[p.team].ctrl === p;
      ctx.beginPath(); ctx.arc(x + p.x * sx, y + p.y * sy, p.role === 'GK' ? 4.5 : ctrl ? 4.5 : 3.5, 0, TAU); ctx.fillStyle = c.main; ctx.fill(); ctx.lineWidth = ctrl ? 2 : 1.4; ctx.strokeStyle = ctrl ? '#fff' : OUT; ctx.stroke();
    }
    for (const tk of m.tokens) { ctx.fillStyle = TOKEN_INFO[tk.type].color; ctx.fillRect(x + tk.x * sx - 2, y + tk.y * sy - 2, 4, 4); }
    const b = m.ball;
    if (b.state !== 'launcher') { ctx.beginPath(); ctx.arc(x + b.x * sx, y + b.y * sy, 4, 0, TAU); ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    // cadre de la caméra
    const c = m.cam, hw = VIEW_W / 2 / c.zoom, hh = VIEW_H / 2 / c.zoom;
    ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 1.5; ctx.strokeRect(x + (c.x - hw) * sx, y + (c.y - hh) * sy, hw * 2 * sx, hh * 2 * sy);
    ctx.restore();
  }

  drawAnnounce(ctx, m, time) {
    const a = m.announce; if (!a) return;
    const k = a.t / a.dur, pop = easeOutElastic(Math.min(1, a.t * 3.2)), out = k > 0.82 ? 1 - (k - 0.82) / 0.18 : 1;
    ctx.save(); ctx.translate(VIEW_W / 2, VIEW_H * 0.34); ctx.globalAlpha = Math.max(0, out);
    const big = a.text.length <= 4;
    // rayons de fond
    if (a.dur > 1.5 || big) {
      ctx.save(); ctx.rotate(time * 0.35); ctx.globalAlpha = 0.15 * out;
      for (let i = 0; i < 14; i++) { ctx.rotate(TAU / 14); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(900, -50); ctx.lineTo(900, 50); ctx.closePath(); ctx.fillStyle = i % 2 ? a.color : PAL.cream; ctx.fill(); }
      ctx.restore();
    }
    ctx.rotate(-0.06); ctx.scale(pop, pop);
    comicText(ctx, a.text, 0, 0, big ? 190 : 128, a.color, OUT);
    if (a.sub) { ctx.translate(0, big ? 120 : 92); comicText(ctx, a.sub, 0, 0, 44, PAL.cream, OUT, 'Lilita One', 0.06); }
    ctx.restore();
  }

  drawPhaseOverlay(ctx, m, time) {
    if (m.phase === 'intro') {
      const k = m.phaseT / 2.4, a = k < 0.15 ? k / 0.15 : k > 0.85 ? (1 - k) / 0.15 : 1;
      ctx.save(); ctx.globalAlpha = a; ctx.translate(VIEW_W / 2, VIEW_H * 0.3);
      const A = m.teams[0].def, B = m.teams[1].def, pop = easeOutBack(Math.min(1, m.phaseT * 2.5));
      ctx.scale(pop, pop);
      comicText(ctx, A.name, -330, 0, 74, A.light, OUT); comicText(ctx, 'VS', 0, 8, 96, PAL.cream, OUT); comicText(ctx, B.name, 330, 0, 74, B.light, OUT);
      ctx.restore();
    }
    if (m.phase === 'halftime' || m.phase === 'fulltime' || m.phase === 'endhalf') {
      ctx.fillStyle = 'rgba(15,8,14,0.35)'; ctx.fillRect(0, 0, VIEW_W, VIEW_H);
    }
    if (m.phase === 'fulltime') {
      ctx.save(); ctx.translate(VIEW_W / 2, VIEW_H * 0.62);
      const w = m.winner >= 0 ? m.teams[m.winner].def : null;
      comicText(ctx, w ? `${w.name} GAGNE !` : 'ÉGALITÉ', 0, 0, 96, w ? w.light : PAL.cream, OUT);
      comicText(ctx, `${m.teams[0].score} - ${m.teams[1].score}`, 0, 96, 84, PAL.cream, OUT);
      ctx.restore();
    }
    if (m.phase === 'halftime') {
      ctx.save(); ctx.translate(VIEW_W / 2, VIEW_H * 0.62);
      comicText(ctx, 'Changement de côté…', 0, 0, 48, PAL.cream, OUT, 'Lilita One', 0.06);
      ctx.restore();
    }
  }
}
