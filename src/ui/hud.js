// Crisp overlay: scoreboard, minimap, off-screen indicators, control hints, menus & results.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, TEAMS, DIFFICULTIES } from '../game/constants.js';
import { TAU, clamp, easeOutCubic } from '../core/math.js';

const MULTS = ['', 'x1.5', 'x2'];

function plate(ctx, x, y, w, h, u, fill = '#1c1512') {
  const g = ctx.createLinearGradient(0, y, 0, y + h);
  g.addColorStop(0, '#4a3a30'); g.addColorStop(0.08, fill); g.addColorStop(1, '#0c0807');
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.beginPath();
  ctx.moveTo(x + 14 * u + 6 * u, y + 6 * u); ctx.lineTo(x + w - 14 * u + 6 * u, y + 6 * u); ctx.lineTo(x + w + 6 * u, y + h / 2 + 6 * u);
  ctx.lineTo(x + w - 14 * u + 6 * u, y + h + 6 * u); ctx.lineTo(x + 14 * u + 6 * u, y + h + 6 * u); ctx.lineTo(x + 6 * u, y + h / 2 + 6 * u); ctx.fill();
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.moveTo(x + 14 * u, y); ctx.lineTo(x + w - 14 * u, y); ctx.lineTo(x + w, y + h / 2);
  ctx.lineTo(x + w - 14 * u, y + h); ctx.lineTo(x + 14 * u, y + h); ctx.lineTo(x, y + h / 2); ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = '#7a6452'; ctx.lineWidth = 2 * u; ctx.stroke();
  for (const [rx, ry] of [[x + 20 * u, y + 8 * u], [x + w - 20 * u, y + 8 * u], [x + 20 * u, y + h - 8 * u], [x + w - 20 * u, y + h - 8 * u]]) {
    ctx.fillStyle = '#0a0706'; ctx.beginPath(); ctx.arc(rx, ry, 3 * u, 0, TAU); ctx.fill();
    ctx.fillStyle = '#a08a74'; ctx.beginPath(); ctx.arc(rx - 0.8 * u, ry - 0.8 * u, 1.3 * u, 0, TAU); ctx.fill();
  }
}

function text(ctx, str, x, y, size, color, font = 'Bebas', align = 'center', stroke = 5) {
  ctx.font = `${size}px ${font}, Impact, sans-serif`;
  ctx.textAlign = align;
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  if (stroke) { ctx.lineWidth = stroke; ctx.strokeStyle = '#0a0504'; ctx.strokeText(str, x, y); }
  ctx.fillStyle = color;
  ctx.fillText(str, x, y);
}

export function drawHUD(ctx, match, cam, cw, ch, time) {
  const u = ch / 1080;
  const [A, B] = match.teams;
  // Left team on screen is whichever defends the left goal.
  const left = A.dir > 0 ? A : B, right = left === A ? B : A;

  // ---- Scoreboard ----
  const sw = 760 * u, sh = 96 * u, sx = cw / 2 - sw / 2, sy = 18 * u;
  plate(ctx, sx, sy, sw, sh, u);
  const clock = Math.max(0, match.clock);
  const mm = Math.floor(clock / 60), ss = Math.floor(clock % 60);
  const low = clock < 10.5 && match.phase === 'play';
  const clockCol = low ? (Math.sin(time * 12) > 0 ? '#ff3a1a' : '#ffd36a') : '#f2e6d0';
  text(ctx, `${mm}:${String(ss).padStart(2, '0')}`, cw / 2, sy + sh * 0.44, 62 * u, clockCol, 'Bebas', 'center', 6 * u);
  text(ctx, match.half === 3 ? 'MORT SUBITE' : `MI-TEMPS ${match.half}`, cw / 2, sy + sh * 0.84, 20 * u, '#b8a48c', 'Bebas', 'center', 3 * u);
  for (const [t, side] of [[left, -1], [right, 1]]) {
    const def = t.def;
    const cx = cw / 2 + side * 230 * u;
    // Team colour bar
    ctx.fillStyle = def.armor;
    ctx.fillRect(cx - 130 * u, sy + 10 * u, 260 * u, 6 * u);
    text(ctx, def.name, cx + side * 20 * u, sy + 38 * u, 30 * u, def.armorLight, 'Bebas', 'center', 4 * u);
    const pop = t.scorePop ? Math.max(0, t.scorePop) : 0;
    text(ctx, String(t.score), cx - side * 110 * u, sy + sh * 0.5, (70 + pop * 30) * u, '#ffffff', 'BlackOps', 'center', 7 * u);
    if (t.lastScore !== t.score) { t.scorePop = 1; t.lastScore = t.score; }
    t.scorePop = Math.max(0, (t.scorePop || 0) - 0.05);
    // Multiplier + effects
    let bx = cx + side * 20 * u - 60 * u;
    if (t.mult > 0) {
      ctx.fillStyle = def.glow;
      ctx.fillRect(bx, sy + 58 * u, 50 * u, 24 * u);
      text(ctx, MULTS[t.mult], bx + 25 * u, sy + 71 * u, 24 * u, '#140906', 'Bebas', 'center', 0);
      bx += 58 * u;
    }
    if (t.rageT > 0) { ctx.fillStyle = '#e02a10'; ctx.fillRect(bx, sy + 58 * u, 64 * u, 24 * u); text(ctx, 'RAGE', bx + 32 * u, sy + 71 * u, 22 * u, '#fff', 'Bebas', 'center', 0); bx += 72 * u; }
    if (t.freezeT > 0) { ctx.fillStyle = '#7ec8ee'; ctx.fillRect(bx, sy + 58 * u, 70 * u, 24 * u); text(ctx, 'ENTRAVE', bx + 35 * u, sy + 71 * u, 22 * u, '#08141a', 'Bebas', 'center', 0); }
  }

  drawMinimap(ctx, match, cam, cw, ch, u, left);
  drawOffscreen(ctx, match, cam, cw, ch, u, time);

  if (!match.demo && match.half === 1 && match.clock > match.halfLength - 12 && match.phase === 'play') {
    const a = clamp((match.clock - (match.halfLength - 12)) / 2, 0, 1);
    ctx.globalAlpha = a;
    const lines = controlsHint(match);
    lines.forEach((l, i) => text(ctx, l, 28 * u, ch - (30 + (lines.length - 1 - i) * 30) * u, 26 * u, '#e8dccb', 'Bebas', 'left', 4 * u));
    ctx.globalAlpha = 1;
  }
}

function controlsHint(match) {
  const hs = match.humans;
  if (hs.length === 1 && hs[0].device.kind === 'merge') {
    return ['DÉPLACER : ZQSD / WASD / FLÈCHES', 'ESPACE / J : PASSE-TIR (MAINTENIR = PUISSANCE)  •  SANS BALLE : TACLE', 'K / SHIFT : LOB  •  SANS BALLE : SAUT      L / TAB : CHANGER DE JOUEUR'];
  }
  return ['MANETTE : A = PASSE-TIR / TACLE   B = LOB / SAUT   LB-RB = CHANGER',
    'J1 CLAVIER : ZQSD + ESPACE / SHIFT / TAB   —   J2 CLAVIER : FLÈCHES + PAVÉ 0 / . / ENTRÉE'];
}

function drawMinimap(ctx, match, cam, cw, ch, u, left) {
  const mw = 300 * u, mh = mw * (H / W);
  const mx = cw / 2 - mw / 2, my = ch - mh - 20 * u;
  ctx.fillStyle = 'rgba(10,6,4,0.62)';
  ctx.fillRect(mx - 6 * u, my - 6 * u, mw + 12 * u, mh + 12 * u);
  ctx.strokeStyle = 'rgba(160,130,100,0.6)'; ctx.lineWidth = 1.5 * u;
  ctx.strokeRect(mx, my, mw, mh);
  ctx.beginPath(); ctx.moveTo(mx + mw / 2, my); ctx.lineTo(mx + mw / 2, my + mh); ctx.stroke();
  const sx = (x) => mx + (x / W) * mw, sy = (y) => my + (y / H) * mh;
  // goals
  for (const t of match.teams) {
    const gx = match.ownGoalX(t);
    ctx.fillStyle = t.def.glow;
    ctx.fillRect(sx(gx) - 3 * u, sy(CY - GOAL_HALF), 6 * u, (GOAL_HALF * 2 / H) * mh);
  }
  // camera frame
  const v = cam.view;
  ctx.strokeStyle = 'rgba(255,255,255,0.25)';
  ctx.strokeRect(sx(clamp(v.x0, 0, W)), sy(clamp(v.y0, 0, H)), (Math.min(W, v.x1) - Math.max(0, v.x0)) / W * mw, (Math.min(H, v.y1) - Math.max(0, v.y0)) / H * mh);
  for (const p of match.players) {
    ctx.fillStyle = p.grounded ? 'rgba(120,120,120,0.8)' : p.team.def.armorLight;
    const r = (p.human ? 5 : 3.5) * u;
    ctx.beginPath(); ctx.arc(sx(p.x), sy(p.y), r, 0, TAU); ctx.fill();
    if (p.human) { ctx.strokeStyle = p.human.color; ctx.lineWidth = 2 * u; ctx.stroke(); }
  }
  const b = match.ball;
  ctx.fillStyle = b.electric > 0 ? '#7ff6ff' : '#ffffff';
  ctx.beginPath(); ctx.arc(sx(b.x), sy(b.y), 3.5 * u, 0, TAU); ctx.fill();
}

function drawOffscreen(ctx, match, cam, cw, ch, u, time) {
  const v = cam.view;
  const s = cw / cam.viewW;
  for (const h of match.humans) {
    const p = h.player;
    if (!p) continue;
    const px = (p.x - v.x0) * s, py = (p.y - 40 - v.y0) * s;
    if (px > 0 && px < cw && py > 0 && py < ch) continue;
    const cx = clamp(px, 40 * u, cw - 40 * u), cy = clamp(py, 140 * u, ch - 40 * u);
    const a = Math.atan2(py - cy, px - cx);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(a);
    ctx.fillStyle = h.color;
    ctx.beginPath(); ctx.moveTo(22 * u, 0); ctx.lineTo(-10 * u, -14 * u); ctx.lineTo(-10 * u, 14 * u); ctx.fill();
    ctx.restore();
  }
}

// ---------------- Menus ----------------

export function drawLogo(ctx, cw, ch, time, y = 0.26, scale = 1) {
  const u = ch / 1080 * scale;
  const cx = cw / 2, cy = ch * y;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(-0.04);
  const size = 170 * u;
  ctx.font = `${size}px BlackOps, Impact, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  // Fire glow behind
  const glow = ctx.createRadialGradient(0, 0, 10, 0, 0, 700 * u);
  glow.addColorStop(0, `rgba(255,110,30,${0.35 + Math.sin(time * 3) * 0.05})`);
  glow.addColorStop(1, 'rgba(255,60,10,0)');
  ctx.fillStyle = glow;
  ctx.fillRect(-900 * u, -300 * u, 1800 * u, 600 * u);
  for (const [str, dy, sz] of [['STEEL', -70, 1], ['CARNAGE', 80, 1.12]]) {
    ctx.font = `${size * sz}px BlackOps, Impact, sans-serif`;
    ctx.lineWidth = 22 * u;
    ctx.strokeStyle = '#0a0302';
    ctx.strokeText(str, 0, dy * u);
    const g = ctx.createLinearGradient(0, dy * u - size * 0.45, 0, dy * u + size * 0.45);
    if (str === 'STEEL') {
      g.addColorStop(0, '#ffffff'); g.addColorStop(0.45, '#b9c0c6'); g.addColorStop(0.55, '#5c646b'); g.addColorStop(1, '#c9d0d6');
    } else {
      g.addColorStop(0, '#ffe7a0'); g.addColorStop(0.4, '#ff8a1f'); g.addColorStop(0.7, '#c2260c'); g.addColorStop(1, '#5a0c04');
    }
    ctx.fillStyle = g;
    ctx.fillText(str, 0, dy * u);
  }
  // Scratches
  ctx.globalCompositeOperation = 'destination-out';
  ctx.strokeStyle = 'rgba(0,0,0,0.6)';
  ctx.lineWidth = 2 * u;
  for (let i = 0; i < 14; i++) {
    const x = ((i * 137) % 900 - 450) * u, yy = ((i * 71) % 260 - 130) * u;
    ctx.beginPath(); ctx.moveTo(x, yy); ctx.lineTo(x + 60 * u, yy + 12 * u); ctx.stroke();
  }
  ctx.globalCompositeOperation = 'source-over';
  ctx.restore();
}

export function drawTitle(ctx, cw, ch, time) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(8,4,3,0.35)';
  ctx.fillRect(0, 0, cw, ch);
  drawLogo(ctx, cw, ch, time);
  text(ctx, 'LE SPORT LE PLUS BRUTAL DES TERRES DÉSOLÉES', cw / 2, ch * 0.45, 40 * u, '#e7d6bd', 'Bebas', 'center', 5 * u);
  if (Math.sin(time * 4) > -0.3) text(ctx, 'APPUIE SUR ENTRÉE / START', cw / 2, ch * 0.72, 56 * u, '#ffd36a', 'BlackOps', 'center', 7 * u);
  text(ctx, 'F11 : PLEIN ÉCRAN   •   M : MUSIQUE', cw / 2, ch * 0.95, 24 * u, '#8f7c68', 'Bebas', 'center', 3 * u);
}

export function drawMenu(ctx, cw, ch, time, menu) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(8,4,3,0.55)';
  ctx.fillRect(0, 0, cw, ch);
  drawLogo(ctx, cw, ch, time, 0.17, 0.62);
  const items = menu.items;
  const top = ch * 0.36;
  const rowH = 74 * u;
  items.forEach((it, i) => {
    const y = top + i * rowH;
    const sel = i === menu.index;
    const w = 860 * u, x = cw / 2 - w / 2;
    if (sel) {
      const pulse = 0.6 + Math.sin(time * 8) * 0.2;
      ctx.fillStyle = `rgba(200,70,20,${0.35 * pulse + 0.2})`;
      ctx.beginPath();
      ctx.moveTo(x, y - rowH * 0.42); ctx.lineTo(x + w, y - rowH * 0.42); ctx.lineTo(x + w - 20 * u, y + rowH * 0.42); ctx.lineTo(x - 20 * u, y + rowH * 0.42); ctx.fill();
      ctx.fillStyle = '#ff7a1a';
      ctx.fillRect(x - 20 * u, y - rowH * 0.42, 8 * u, rowH * 0.84);
    }
    const col = it.disabled ? '#6a5a4c' : sel ? '#ffffff' : '#cbb89f';
    if (it.value !== undefined) {
      text(ctx, it.label, x + 30 * u, y, 42 * u, col, 'Bebas', 'left', 5 * u);
      const v = it.value;
      text(ctx, sel ? `◄  ${v}  ►` : v, x + w - 30 * u, y, 42 * u, sel ? '#ffd36a' : '#e8dccb', 'Bebas', 'right', 5 * u);
    } else {
      text(ctx, it.label, cw / 2, y, (it.big ? 56 : 44) * u, it.big && sel ? '#ffd36a' : col, it.big ? 'BlackOps' : 'Bebas', 'center', 6 * u);
    }
  });
  if (menu.help) text(ctx, menu.help, cw / 2, ch * 0.93, 26 * u, '#a8927a', 'Bebas', 'center', 3 * u);
}

export function drawPause(ctx, cw, ch, time, menu) {
  const u = ch / 1080;
  ctx.fillStyle = 'rgba(6,3,2,0.62)';
  ctx.fillRect(0, 0, cw, ch);
  text(ctx, 'PAUSE', cw / 2, ch * 0.3, 140 * u, '#ffd36a', 'BlackOps', 'center', 12 * u);
  menu.items.forEach((it, i) => {
    const sel = i === menu.index;
    text(ctx, sel ? `►  ${it.label}  ◄` : it.label, cw / 2, ch * 0.48 + i * 70 * u, 50 * u, sel ? '#ffffff' : '#bba68c', 'Bebas', 'center', 6 * u);
  });
}

export function drawResults(ctx, cw, ch, time, match, menu, t) {
  const u = ch / 1080;
  const k = easeOutCubic(clamp(t / 0.6, 0, 1));
  ctx.fillStyle = `rgba(6,3,2,${0.7 * k})`;
  ctx.fillRect(0, 0, cw, ch);
  ctx.save();
  ctx.translate(0, (1 - k) * 60 * u);
  ctx.globalAlpha = k;
  const w = match.winner;
  text(ctx, w ? 'VICTOIRE' : 'MATCH NUL', cw / 2, ch * 0.14, 130 * u, w ? w.def.glow : '#e8dccb', 'BlackOps', 'center', 12 * u);
  if (w) text(ctx, w.def.name, cw / 2, ch * 0.24, 54 * u, '#ffffff', 'Bebas', 'center', 6 * u);
  const [A, B] = match.teams;
  const colW = 380 * u;
  text(ctx, `${A.score}`, cw / 2 - colW, ch * 0.36, 120 * u, A.def.armorLight, 'BlackOps', 'center', 10 * u);
  text(ctx, `${B.score}`, cw / 2 + colW, ch * 0.36, 120 * u, B.def.armorLight, 'BlackOps', 'center', 10 * u);
  text(ctx, A.def.name, cw / 2 - colW, ch * 0.45, 40 * u, '#e8dccb', 'Bebas', 'center', 5 * u);
  text(ctx, B.def.name, cw / 2 + colW, ch * 0.45, 40 * u, '#e8dccb', 'Bebas', 'center', 5 * u);
  text(ctx, '—', cw / 2, ch * 0.36, 90 * u, '#8a7560', 'BlackOps', 'center', 8 * u);
  const rows = [
    ['BUTS', 'goals'], ['K.O. INFLIGÉS', 'kos'], ['TACLES', 'tackles'], ['TIRS', 'shots'], ['ÉTOILES ALLUMÉES', 'starsLit'], ['CRÉDITS RAMASSÉS', 'credits'],
  ];
  rows.forEach(([label, key], i) => {
    const y = ch * 0.53 + i * 44 * u;
    ctx.fillStyle = i % 2 ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.07)';
    ctx.fillRect(cw / 2 - colW - 120 * u, y - 20 * u, (colW + 120 * u) * 2, 40 * u);
    text(ctx, label, cw / 2, y, 32 * u, '#b8a48c', 'Bebas', 'center', 3 * u);
    text(ctx, String(A[key]), cw / 2 - colW, y, 36 * u, '#ffffff', 'Bebas', 'center', 4 * u);
    text(ctx, String(B[key]), cw / 2 + colW, y, 36 * u, '#ffffff', 'Bebas', 'center', 4 * u);
  });
  menu.items.forEach((it, i) => {
    const sel = i === menu.index;
    text(ctx, sel ? `►  ${it.label}  ◄` : it.label, cw / 2 + (i - 0.5) * 420 * u, ch * 0.9, 50 * u, sel ? '#ffd36a' : '#bba68c', 'Bebas', 'center', 6 * u);
  });
  ctx.restore();
}
