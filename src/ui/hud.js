// Crisp overlay: side-panel scoreboard, vertical minimap, off-screen indicators, hints, menus & results.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF } from '../game/constants.js';
import { MULTS } from '../game/match.js';
import { TAU, clamp, easeOutCubic } from '../core/math.js';
import { drawText } from '../render/text.js';
import { t } from '../core/i18n.js';

const INK = '#070302';
const BONE = '#e8dcc6';
const DUST = '#a8957c';
const BLOOD = '#b3200f';

function panel(ctx, x, y, w, h, u, alpha = 0.78) {
  ctx.fillStyle = `rgba(12,8,6,${alpha})`;
  ctx.fillRect(x, y, w, h);
  ctx.fillStyle = 'rgba(90,70,55,0.5)';
  ctx.fillRect(x, y, w, 2 * u);
  ctx.fillRect(x, y + h - 2 * u, w, 2 * u);
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  for (const [rx, ry] of [[x + 8 * u, y + 8 * u], [x + w - 8 * u, y + 8 * u], [x + 8 * u, y + h - 8 * u], [x + w - 8 * u, y + h - 8 * u]]) {
    ctx.beginPath(); ctx.arc(rx, ry, 2.5 * u, 0, TAU); ctx.fill();
  }
}

const cond = (fill, u, extra = {}) => ({ font: 'Cond', weight: 700, fill, stroke: INK, strokeW: 4 * u, erosion: 0, ...extra });

export function drawHUD(ctx, match, cam, cw, ch, time, showHints) {
  const u = ch / 1080;
  const s = cw / cam.viewW;
  const fieldL = (0 - cam.view.x0) * s, fieldR = (W - cam.view.x0) * s;
  const pw = clamp(fieldL - 24 * u, 270 * u, 300 * u);

  // ---- Left panel: clock + scores ----
  const px = 16 * u, py = 16 * u;
  panel(ctx, px, py, pw, 250 * u, u);
  const clock = Math.max(0, match.clock);
  const mm = Math.floor(clock / 60), ss = Math.floor(clock % 60);
  const low = clock < 10.5 && match.phase === 'play';
  const clockCol = low && Math.sin(time * 12) > 0 ? '#e8321a' : BONE;
  drawText(ctx, `${mm}:${String(ss).padStart(2, '0')}`, px + pw / 2, py + 52 * u, 72 * u, { font: 'Display', fill: clockCol, stroke: INK, strokeW: 6 * u, erosion: 0 });
  drawText(ctx, match.half === 3 ? t('suddenDeath') : t('half', match.half), px + pw / 2, py + 100 * u, 24 * u, cond(DUST, u, { tracking: 3 * u }));
  match.teams.forEach((tm, i) => {
    const y = py + (140 + i * 58) * u;
    ctx.fillStyle = tm.def.mark;
    ctx.fillRect(px + 14 * u, y - 22 * u, 6 * u, 44 * u);
    if (tm.lastScore !== tm.score) { tm.scorePop = 1; tm.lastScore = tm.score; }
    tm.scorePop = Math.max(0, (tm.scorePop || 0) - 0.04);
    // Score in a fixed column on the left, name + status on the right.
    drawText(ctx, String(tm.score), px + 62 * u, y, (50 + tm.scorePop * 22) * u, { font: 'Display', fill: '#f4ead8', stroke: INK, strokeW: 5 * u, erosion: 0 });
    drawText(ctx, tm.def.name, px + 108 * u, y - 7 * u, 24 * u, cond(tm.def.ui, u), 1, 0, 'left');
    const tags = [];
    if (tm.mult > 0) tags.push(`x${MULTS[tm.mult]}`);
    if (tm.rageT > 0) tags.push(t('rage'));
    if (tm.freezeT > 0) tags.push(t('fettered'));
    if (tags.length) drawText(ctx, tags.join('  '), px + 108 * u, y + 16 * u, 20 * u, cond(i === 0 ? '#e0a060' : '#a8d8e8', u, { strokeW: 3 * u }), 1, 0, 'left');
  });
  // Which way am I attacking?
  const h0 = match.humans[0];
  if (h0 && match.phase !== 'fulltime') {
    const up = h0.team.dir < 0;
    const ax = px + pw / 2, ay = py + 250 * u + 26 * u;
    ctx.fillStyle = h0.team.def.mark;
    ctx.beginPath();
    if (up) { ctx.moveTo(ax, ay - 12 * u); ctx.lineTo(ax + 12 * u, ay + 6 * u); ctx.lineTo(ax - 12 * u, ay + 6 * u); } else { ctx.moveTo(ax, ay + 12 * u); ctx.lineTo(ax + 12 * u, ay - 6 * u); ctx.lineTo(ax - 12 * u, ay - 6 * u); }
    ctx.fill();
  }

  drawMinimap(ctx, match, cam, cw, ch, u, fieldR);
  drawOffscreen(ctx, match, cam, cw, ch, u);

  if (showHints && !match.demo && match.half === 1 && match.phase === 'play' && match.clock > match.halfLength - 8) {
    const a = clamp((match.clock - (match.halfLength - 8)) / 1.5, 0, 1);
    const lines = match.humans.length === 1 && match.humans[0].device.kind === 'merge' ? t('hintSolo') : t('hintMulti');
    const lh = 30 * u, bh = lines.length * lh + 20 * u;
    ctx.globalAlpha = a;
    ctx.fillStyle = 'rgba(8,5,4,0.8)';
    ctx.fillRect(cw / 2 - 470 * u, ch - bh - 16 * u, 940 * u, bh);
    lines.forEach((l, i) => drawText(ctx, l, cw / 2, ch - bh - 16 * u + 10 * u + lh * (i + 0.5), 23 * u, cond(BONE, u, { strokeW: 3 * u })));
    ctx.globalAlpha = 1;
  }
}

function drawMinimap(ctx, match, cam, cw, ch, u, fieldR) {
  const mh = 330 * u, mw = mh * (W / H);
  const mx = cw - mw - 28 * u, my = 28 * u;
  panel(ctx, mx - 12 * u, my - 12 * u, mw + 24 * u, mh + 24 * u, u, 0.72);
  ctx.strokeStyle = 'rgba(170,140,110,0.5)'; ctx.lineWidth = 1.5 * u;
  ctx.strokeRect(mx, my, mw, mh);
  ctx.beginPath(); ctx.moveTo(mx, my + mh / 2); ctx.lineTo(mx + mw, my + mh / 2); ctx.stroke();
  const sx = (x) => mx + (x / W) * mw, sy = (y) => my + (y / H) * mh;
  for (const tm of match.teams) {
    const gy = match.ownGoalY(tm);
    ctx.fillStyle = tm.def.mark;
    ctx.fillRect(sx(CX - GOAL_HALF), sy(gy) - 2.5 * u, (GOAL_HALF * 2 / W) * mw, 5 * u);
  }
  const v = cam.view;
  ctx.strokeStyle = 'rgba(255,240,220,0.25)';
  const y0 = clamp(v.y0, 0, H), y1 = clamp(v.y1, 0, H);
  ctx.strokeRect(mx + 1, sy(y0), mw - 2, sy(y1) - sy(y0));
  for (const p of match.players) {
    ctx.fillStyle = p.grounded ? 'rgba(110,100,95,0.8)' : p.team.def.mark;
    const r = (p.human ? 4.5 : 3.2) * u;
    ctx.beginPath(); ctx.arc(sx(p.x), sy(p.y), r, 0, TAU); ctx.fill();
    if (p.human) { ctx.strokeStyle = p.human.color; ctx.lineWidth = 2 * u; ctx.stroke(); }
  }
  const b = match.ball;
  ctx.fillStyle = b.electric > 0 ? '#9fe8ff' : '#ffffff';
  ctx.beginPath(); ctx.arc(sx(b.x), sy(b.y), 3.2 * u, 0, TAU); ctx.fill();
}

function drawOffscreen(ctx, match, cam, cw, ch, u) {
  const v = cam.view;
  const s = cw / cam.viewW;
  for (const h of match.humans) {
    const p = h.player;
    if (!p) continue;
    const px = (p.x - v.x0) * s, py = (p.y - 50 - v.y0) * s;
    if (px > 0 && px < cw && py > 0 && py < ch) continue;
    const cx = clamp(px, 40 * u, cw - 40 * u), cy = clamp(py, 40 * u, ch - 40 * u);
    const a = Math.atan2(py - cy, px - cx);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(a);
    ctx.fillStyle = INK;
    ctx.beginPath(); ctx.moveTo(26 * u, 0); ctx.lineTo(-12 * u, -17 * u); ctx.lineTo(-12 * u, 17 * u); ctx.fill();
    ctx.fillStyle = h.color;
    ctx.beginPath(); ctx.moveTo(20 * u, 0); ctx.lineTo(-8 * u, -12 * u); ctx.lineTo(-8 * u, 12 * u); ctx.fill();
    ctx.restore();
  }
}

// ---------------- Menus ----------------

export function drawLogo(ctx, cw, ch, time, y = 0.27, scale = 1) {
  const u = (ch / 1080) * scale;
  const cx = cw / 2, cy = ch * y;
  const glow = ctx.createRadialGradient(cx, cy, 10, cx, cy, 650 * u);
  glow.addColorStop(0, `rgba(200,60,15,${0.28 + Math.sin(time * 3) * 0.04})`);
  glow.addColorStop(1, 'rgba(120,20,5,0)');
  ctx.fillStyle = glow;
  ctx.fillRect(cx - 900 * u, cy - 400 * u, 1800 * u, 800 * u);
  drawText(ctx, 'STEEL', cx, cy - 90 * u, 170 * u, { font: 'Display', fill: '#d8d2c8', fill2: '#5a5550', stroke: INK, strokeW: 12 * u, erosion: 0.5, tracking: 14 * u }, 1, -0.02);
  drawText(ctx, 'CARNAGE', cx, cy + 80 * u, 210 * u, { font: 'Display', fill: '#e05a20', fill2: '#5a0c04', stroke: INK, strokeW: 14 * u, erosion: 0.5, drips: true, dripColor: '#6a0804', tracking: 6 * u }, 1, -0.02);
}

export function drawTitle(ctx, cw, ch, time) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(6,3,2,0.45)';
  ctx.fillRect(0, 0, cw, ch);
  drawLogo(ctx, cw, ch, time);
  drawText(ctx, t('tagline'), cw / 2, ch * 0.5, 36 * u, cond(DUST, u, { tracking: 6 * u, strokeW: 5 * u }));
  if (Math.sin(time * 4) > -0.4) drawText(ctx, t('pressStart'), cw / 2, ch * 0.74, 54 * u, { font: 'Display', fill: BONE, stroke: INK, strokeW: 6 * u, erosion: 0.3, tracking: 4 * u });
  drawText(ctx, t('titleHelp'), cw / 2, ch * 0.95, 24 * u, cond('#7d6c5a', u, { strokeW: 3 * u }));
}

export function drawMenu(ctx, cw, ch, time, menu) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(6,3,2,0.62)';
  ctx.fillRect(0, 0, cw, ch);
  drawLogo(ctx, cw, ch, time, 0.16, 0.55);
  const top = ch * 0.36;
  const rowH = 66 * u;
  const w = 880 * u, x = cw / 2 - w / 2;
  menu.items.forEach((it, i) => {
    const y = top + i * rowH;
    const sel = i === menu.index;
    if (sel) {
      ctx.fillStyle = 'rgba(140,20,8,0.55)';
      ctx.fillRect(x - 10 * u, y - rowH * 0.42, w + 20 * u, rowH * 0.84);
      ctx.fillStyle = BLOOD;
      ctx.fillRect(x - 10 * u, y - rowH * 0.42, 6 * u, rowH * 0.84);
    }
    const col = it.disabled ? '#5a4c40' : sel ? '#ffffff' : '#c4b29a';
    if (it.value !== undefined) {
      drawText(ctx, it.label, x + 20 * u, y, 38 * u, cond(col, u, { tracking: 2 * u }), 1, 0, 'left');
      drawText(ctx, sel ? `‹  ${it.value}  ›` : it.value, x + w - 20 * u, y, 38 * u, cond(sel ? '#f0c070' : BONE, u, { tracking: 2 * u }), 1, 0, 'right');
    } else if (it.big) {
      drawText(ctx, it.label, cw / 2, y, 52 * u, { font: 'Display', fill: sel ? '#ffffff' : '#d8c8b0', stroke: INK, strokeW: 6 * u, erosion: 0.25, tracking: 4 * u });
    } else {
      drawText(ctx, it.label, cw / 2, y, 38 * u, cond(col, u, { tracking: 2 * u }));
    }
  });
  if (menu.help) drawText(ctx, menu.help, cw / 2, ch * 0.94, 24 * u, cond('#8a7864', u, { strokeW: 3 * u }));
}

export function drawPause(ctx, cw, ch, time, menu) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(5,2,1,0.6)';
  ctx.fillRect(0, 0, cw, ch);
  drawText(ctx, t('pause'), cw / 2, ch * 0.3, 150 * u, { font: 'Display', fill: BONE, fill2: '#7a6a58', stroke: INK, strokeW: 10 * u, erosion: 0.45, tracking: 10 * u });
  menu.items.forEach((it, i) => {
    const sel = i === menu.index;
    drawText(ctx, sel ? `›  ${it.label}  ‹` : it.label, cw / 2, ch * 0.5 + i * 68 * u, 46 * u, cond(sel ? '#ffffff' : '#b09c84', u, { tracking: 3 * u, strokeW: 5 * u }));
  });
}

export function drawResults(ctx, cw, ch, time, match, menu, st) {
  const u = ch / 1080;
  const k = easeOutCubic(clamp(st / 0.6, 0, 1));
  ctx.fillStyle = `rgba(5,2,1,${0.75 * k})`;
  ctx.fillRect(0, 0, cw, ch);
  ctx.save();
  ctx.globalAlpha = k;
  ctx.translate(0, (1 - k) * 50 * u);
  const w = match.winner;
  drawText(ctx, w ? t('victory') : t('draw'), cw / 2, ch * 0.13, 150 * u,
    { font: 'Display', fill: '#f4ead8', fill2: w ? w.def.mark : '#8a7a68', stroke: INK, strokeW: 12 * u, erosion: 0.45, drips: true, tracking: 10 * u });
  if (w) drawText(ctx, w.def.name, cw / 2, ch * 0.25, 48 * u, cond(BONE, u, { tracking: 8 * u, strokeW: 5 * u }));
  const [A, B] = match.teams;
  const colW = 360 * u;
  drawText(ctx, String(A.score), cw / 2 - colW, ch * 0.37, 130 * u, { font: 'Display', fill: '#f4ead8', fill2: A.def.mark, stroke: INK, strokeW: 10 * u, erosion: 0.2 });
  drawText(ctx, String(B.score), cw / 2 + colW, ch * 0.37, 130 * u, { font: 'Display', fill: '#f4ead8', fill2: B.def.mark, stroke: INK, strokeW: 10 * u, erosion: 0.2 });
  drawText(ctx, A.def.name, cw / 2 - colW, ch * 0.46, 34 * u, cond(A.def.ui, u, { tracking: 4 * u }));
  drawText(ctx, B.def.name, cw / 2 + colW, ch * 0.46, 34 * u, cond(B.def.ui, u, { tracking: 4 * u }));
  const rows = [['statGoals', 'goals'], ['statKos', 'kos'], ['statTackles', 'tackles'], ['statShots', 'shots'], ['statStars', 'starsLit'], ['statCredits', 'credits']];
  rows.forEach(([label, key], i) => {
    const y = ch * 0.54 + i * 44 * u;
    ctx.fillStyle = i % 2 ? 'rgba(255,240,220,0.03)' : 'rgba(255,240,220,0.07)';
    ctx.fillRect(cw / 2 - colW - 120 * u, y - 20 * u, (colW + 120 * u) * 2, 40 * u);
    drawText(ctx, t(label), cw / 2, y, 28 * u, cond(DUST, u, { tracking: 3 * u, strokeW: 3 * u }));
    drawText(ctx, String(A[key]), cw / 2 - colW, y, 34 * u, cond('#ffffff', u));
    drawText(ctx, String(B[key]), cw / 2 + colW, y, 34 * u, cond('#ffffff', u));
  });
  menu.items.forEach((it, i) => {
    const sel = i === menu.index;
    drawText(ctx, sel ? `›  ${it.label}  ‹` : it.label, cw / 2 + (i - 0.5) * 420 * u, ch * 0.91, 46 * u, cond(sel ? '#f0c070' : '#b09c84', u, { tracking: 3 * u, strokeW: 5 * u }));
  });
  ctx.restore();
}
