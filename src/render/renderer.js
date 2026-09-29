// Scene renderer: floor, crowd, furniture, y-sorted sprites, particles, lights and the
// screen-space announcer, composed into the 2D scene canvas that the WebGL pass consumes.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, BUMPERS, ELECTRO, STAR_YS, RAMP_HALF } from '../game/constants.js';
import { drawFloor, drawCrowd, drawLights, barrelSprites, emitBarrelFire, starPath, LEDGE } from './arena.js';
import { drawPlayer, drawShadow, drawRing, drawBall, drawBallGlow } from './sprites.js';
import { fx, glowSprite } from './fx.js';
import { drawText } from './text.js';
import { TAU, rand, clamp, easeOutBack } from '../core/math.js';

const TEAM_RGB = ['242,100,30', '205,230,240'];
const list = [];
const byY = (a, b) => a.y - b.y;

export function renderScene(ctx, match, cam, cw, ch, time, dt) {
  const view = cam.view;
  const s = cw / cam.viewW;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#070504';
  ctx.fillRect(0, 0, cw, ch);
  ctx.setTransform(s, 0, 0, s, -(view.x0 + fx.shakeX) * s, -(view.y0 + fx.shakeY) * s);
  ctx.imageSmoothingEnabled = true;

  drawFloor(ctx, view);
  drawCrowd(ctx, view, time, match.excitement, dt);
  drawGoalPits(ctx, match, time);
  drawStars(ctx, match, time);
  drawRamps(ctx, match, time);
  drawElectro(ctx, match, time, dt);
  drawLauncher(ctx, match, time);
  drawTokens(ctx, match, time);

  for (const p of match.players) {
    if (p.y < view.y0 - 120 || p.y > view.y1 + 150) continue;
    drawShadow(ctx, p);
    if (p.human) {
      ctx.globalCompositeOperation = 'lighter';
      drawRing(ctx, p, p.human.color, 3.5, 0.7 + Math.sin(time * 8) * 0.2, 28);
      ctx.globalCompositeOperation = 'source-over';
      if (p.charging) drawCharge(ctx, p);
    } else {
      drawRing(ctx, p, `rgba(${TEAM_RGB[p.team.idx]},1)`, 2.5, p.grounded ? 0.15 : 0.55, 24);
    }
  }

  // Y-sorted sprites
  list.length = 0;
  for (const p of match.players) {
    if (p.y < view.y0 - 120 || p.y > view.y1 + 150) continue;
    list.push({ y: p.y, draw: (c) => drawPlayer(c, p, p.team.def, time, match.ball) });
  }
  for (let i = 0; i < BUMPERS.length; i++) {
    const b = BUMPERS[i];
    if (b.y < view.y0 - 100 || b.y > view.y1 + 100) continue;
    list.push({ y: b.y, draw: (c) => drawBumper(c, b, match.bumperFlash[i], time) });
  }
  for (const top of [true, false]) {
    const gy = top ? 0 : H;
    if (gy < view.y0 - 200 || gy > view.y1 + 200) continue;
    for (const side of [-1, 1]) list.push({ y: gy + (top ? -2 : 2), draw: (c) => drawPost(c, CX + side * GOAL_HALF, gy, match, time) });
    list.push({ y: gy + (top ? -1 : 3), draw: (c) => drawCrossbar(c, gy, match) });
  }
  barrelSprites(list, view, time);
  const b = match.ball;
  if (!b.owner && b.z > -5) list.push({ y: b.y, draw: (c) => drawBall(c, b) });
  list.sort(byY);
  for (const it of list) it.draw(ctx);

  emitBarrelFire(view, dt);
  fx.draw(ctx);
  drawLights(ctx, view, time);
  if (b.owner || b.z > -5) drawBallGlow(ctx, b, time);
  if (!b.owner) { b.drawX = undefined; b.drawY = undefined; }
  drawTeamAuras(ctx, match, time, dt);
  fx.drawTexts(ctx);
  drawOverheads(ctx, match, time, view);

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  drawAnnouncements(ctx, match, cw, ch, time);
}

function drawCharge(ctx, p) {
  const c = Math.min(1, p.chargeT / 0.45);
  ctx.strokeStyle = c >= 1 ? '#e8321a' : '#e8b83a';
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y + 2, 36, 16, 0, -Math.PI / 2, -Math.PI / 2 + c * TAU);
  ctx.stroke();
  if (p.aimX !== undefined) {
    ctx.strokeStyle = `rgba(255,210,130,${0.25 + c * 0.35})`;
    ctx.lineWidth = 3;
    ctx.setLineDash([10, 10]);
    const l = 150 + c * 170;
    ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.aimX * l, p.y + p.aimY * l); ctx.stroke();
    ctx.setLineDash([]);
  }
}

function defenderOf(match, gy) {
  return match.teams.find((tm) => match.ownGoalY(tm) === gy);
}

function drawGoalPits(ctx, match, time) {
  ctx.globalCompositeOperation = 'lighter';
  for (let side = 0; side < 2; side++) {
    const gy = side ? H : 0;
    const rgb = TEAM_RGB[defenderOf(match, gy).idx];
    const goal = match.phase === 'goal' && match.goalInfo && match.goalInfo.side === side;
    const a = goal ? 0.6 + Math.sin(time * 30) * 0.3 : 0.18 + Math.sin(time * 4 + side) * 0.05;
    const y0 = side ? H : -GOAL_DEPTH;
    const grd = ctx.createLinearGradient(0, gy, 0, gy + (side ? GOAL_DEPTH : -GOAL_DEPTH));
    grd.addColorStop(0, `rgba(${rgb},${a})`);
    grd.addColorStop(1, `rgba(${rgb},0)`);
    ctx.fillStyle = grd;
    ctx.fillRect(CX - GOAL_HALF, y0, GOAL_HALF * 2, GOAL_DEPTH);
    // flickering energy barrier across the mouth
    ctx.fillStyle = `rgba(${rgb},${0.25 + Math.random() * 0.15})`;
    ctx.fillRect(CX - GOAL_HALF, gy - 2, GOAL_HALF * 2, 4);
  }
  ctx.globalCompositeOperation = 'source-over';
}

function drawPost(ctx, x, gy, match, time) {
  const hgt = 120;
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.beginPath(); ctx.ellipse(x + 6, gy + 4, 18, 8, 0, 0, TAU); ctx.fill();
  ctx.fillStyle = '#070504';
  ctx.fillRect(x - 12, gy - hgt - 2, 24, hgt + 4);
  const g = ctx.createLinearGradient(x - 10, 0, x + 10, 0);
  g.addColorStop(0, '#1c1511'); g.addColorStop(0.35, '#5a4a3d'); g.addColorStop(1, '#16110d');
  ctx.fillStyle = g;
  ctx.fillRect(x - 10, gy - hgt, 20, hgt);
  ctx.fillStyle = 'rgba(110,40,15,0.6)';
  ctx.fillRect(x - 10, gy - 70, 20, 30);
  ctx.fillStyle = '#0a0706';
  for (let k = 0; k < 4; k++) ctx.fillRect(x - 10, gy - hgt + 12 + k * 26, 20, 3);
  const rgb = TEAM_RGB[defenderOf(match, gy).idx];
  ctx.fillStyle = `rgb(${rgb})`;
  ctx.fillRect(x - 6, gy - hgt - 6, 12, 5);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.45 + Math.sin(time * 6) * 0.15;
  ctx.drawImage(glowSprite(`rgba(${rgb},1)`, 64), x - 34, gy - hgt - 38, 68, 68);
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}

function drawCrossbar(ctx, gy, match) {
  const y = gy - 112;
  const bottom = gy === H;
  ctx.globalAlpha = bottom ? 0.75 : 1; // keep players readable behind the near crossbar
  ctx.fillStyle = '#070504';
  ctx.fillRect(CX - GOAL_HALF, y - 7, GOAL_HALF * 2, 14);
  ctx.fillStyle = '#4a3c31';
  ctx.fillRect(CX - GOAL_HALF, y - 5, GOAL_HALF * 2, 10);
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.fillRect(CX - GOAL_HALF, y + 1, GOAL_HALF * 2, 4);
  // chains hanging from the bar
  ctx.strokeStyle = 'rgba(60,52,46,0.8)';
  ctx.lineWidth = 2;
  for (let x = CX - GOAL_HALF + 25; x < CX + GOAL_HALF; x += 45) {
    ctx.beginPath(); ctx.moveTo(x, y + 5); ctx.lineTo(x + 2, y + 30); ctx.stroke();
  }
  ctx.globalAlpha = 1;
}

function drawBumper(ctx, b, flash, time) {
  const r = b.r;
  ctx.save();
  ctx.translate(b.x, b.y);
  ctx.fillStyle = 'rgba(0,0,0,0.55)';
  ctx.beginPath(); ctx.ellipse(6, 4, r + 12, (r + 12) * 0.55, 0, 0, TAU); ctx.fill();
  ctx.fillStyle = '#0a0706';
  ctx.beginPath(); ctx.ellipse(0, 0, r + 8, (r + 8) * 0.6, 0, 0, TAU); ctx.fill();
  ctx.fillStyle = '#3a2e25';
  ctx.beginPath(); ctx.ellipse(0, 0, r + 5, (r + 5) * 0.58, 0, 0, TAU); ctx.fill();
  const h = 24;
  const hot = flash > 0.1;
  ctx.fillStyle = hot ? '#9a6a3a' : '#6a5646';
  ctx.beginPath();
  ctx.ellipse(0, -h * 0.35, r, r * 0.95, 0, Math.PI, 0);
  ctx.ellipse(0, 0, r, r * 0.58, 0, 0, Math.PI);
  ctx.fill();
  ctx.fillStyle = hot ? '#b07a40' : '#2a2019';
  ctx.beginPath(); ctx.ellipse(6, -h * 0.2, r * 0.7, r * 0.6, 0, -0.2, Math.PI * 0.7); ctx.fill();
  ctx.fillStyle = 'rgba(160,80,30,0.45)';
  ctx.beginPath(); ctx.ellipse(-r * 0.35, -h - r * 0.25, r * 0.4, r * 0.22, -0.4, 0, TAU); ctx.fill();
  // spikes around the dome
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU + 0.2;
    const sx = Math.cos(a) * r * 0.85, sy = -h * 0.3 + Math.sin(a) * r * 0.55;
    const tx = Math.cos(a) * (r + 12), ty = -h * 0.3 + Math.sin(a) * (r * 0.55 + 8) - 6;
    ctx.fillStyle = '#0b0807';
    ctx.beginPath(); ctx.moveTo(sx - 3, sy); ctx.lineTo(tx, ty); ctx.lineTo(sx + 3, sy); ctx.fill();
    ctx.fillStyle = '#958b80';
    ctx.beginPath(); ctx.moveTo(sx - 1.5, sy); ctx.lineTo(tx, ty); ctx.lineTo(sx, sy); ctx.fill();
  }
  if (flash > 0.01) {
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = flash * 0.8;
    ctx.drawImage(glowSprite('rgba(255,160,80,1)', 128), -r * 2.3, -r * 2.6, r * 4.6, r * 4.6);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.restore();
}

function drawStars(ctx, match, time) {
  for (const wall of ['left', 'right']) {
    const row = match.stars[wall];
    const x = wall === 'left' ? -LEDGE / 2 : W + LEDGE / 2;
    for (let i = 0; i < STAR_YS.length; i++) {
      const own = row[i];
      const fl = match.starFlash[wall][i];
      if (own < 0 && fl <= 0) continue;
      const rgb = own >= 0 ? TEAM_RGB[own] : '255,255,255';
      const y = STAR_YS[i];
      const k = 1 + fl * 0.5;
      starPath(ctx, x, y, 15 * k, 6.5 * k);
      ctx.fillStyle = `rgb(${rgb})`;
      ctx.fill();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.45 + fl * 0.5 + Math.sin(time * 5 + i) * 0.08;
      ctx.drawImage(glowSprite(`rgba(${rgb},1)`, 64), x - 42, y - 42, 84, 84);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }
  }
}

function drawRamps(ctx, match, time) {
  const leader = match.teams.find((tm) => tm.mult > 0);
  const rgb = leader ? TEAM_RGB[leader.idx] : '120,100,80';
  for (let wi = 0; wi < 2; wi++) {
    const x = wi === 0 ? -LEDGE / 2 : W + LEDGE / 2;
    const fl = match.rampFlash[wi];
    for (let i = -3; i <= 3; i++) {
      const on = leader ? (Math.floor(time * 8) - i + 7) % 7 < 3 : false;
      ctx.fillStyle = on || fl > 0 ? `rgba(${rgb},0.95)` : 'rgba(70,58,48,0.9)';
      const y = CY + i * 26;
      ctx.beginPath();
      ctx.moveTo(x - 12, y - 6); ctx.lineTo(x, y + 4); ctx.lineTo(x + 12, y - 6); ctx.lineTo(x + 12, y); ctx.lineTo(x, y + 10); ctx.lineTo(x - 12, y);
      ctx.fill();
    }
    if (leader || fl > 0) {
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.3 + fl * 0.5;
      ctx.drawImage(glowSprite(`rgba(${rgb},1)`, 64), x - 60, CY - RAMP_HALF * 1.2, 120, RAMP_HALF * 2.4);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
    }
  }
}

function drawElectro(ctx, match, time, dt) {
  for (let i = 0; i < ELECTRO.length; i++) {
    const e = ELECTRO[i];
    const fl = match.electroFlash[i];
    ctx.fillStyle = '#0a0908';
    ctx.beginPath(); ctx.arc(e.x, e.y, e.r + 8, 0, TAU); ctx.fill();
    for (let k = 0; k < 4; k++) {
      ctx.strokeStyle = k % 2 ? '#5a4128' : '#8a6538';
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(e.x, e.y, e.r - 3 - k * 5, 0, TAU); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.25 + Math.sin(time * 7 + i) * 0.1 + fl * 0.6;
    ctx.drawImage(glowSprite('rgba(80,190,255,1)', 64), e.x - e.r * 2.3, e.y - e.r * 2.3, e.r * 4.6, e.r * 4.6);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    if (Math.random() < dt * (3 + fl * 30)) {
      const a = rand(0, TAU);
      fx.arc(e.x, e.y, 2, e.x + Math.cos(a) * rand(20, 50), e.y + Math.sin(a) * rand(14, 30), rand(0, 20), '#9fe8ff', 0.1);
    }
  }
}

function drawLauncher(ctx, match, time) {
  if (match.phase !== 'kickoff') return;
  const k = Math.min(1, match.phaseT / 2);
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.3 + k * 0.5;
  ctx.drawImage(glowSprite('rgba(255,60,20,1)', 64), CX - 80, CY - 80, 160, 160);
  ctx.strokeStyle = `rgba(255,110,50,${0.5 + k * 0.5})`;
  ctx.lineWidth = 4;
  for (let i = 0; i < 3; i++) {
    const a = time * 4 + (i * TAU) / 3;
    ctx.beginPath(); ctx.arc(CX, CY, 42, a, a + 0.8); ctx.stroke();
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}

const TOKEN_STYLE = {
  rage: { c: '220,60,25', label: 'R' },
  shock: { c: '90,200,255', label: 'E' },
  freeze: { c: '170,210,230', label: 'F' },
  medic: { c: '140,200,110', label: '+' },
  cash: { c: '220,180,60', label: '$' },
};

function drawTokens(ctx, match, time) {
  for (const tk of match.tokens) {
    const st = TOKEN_STYLE[tk.type];
    if (tk.life - tk.t < 3 && Math.sin(time * 20) > 0) continue;
    // Battered canister with a painted symbol.
    ctx.fillStyle = 'rgba(0,0,0,0.5)';
    ctx.beginPath(); ctx.ellipse(tk.x + 4, tk.y + 2, 18, 8, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = '#0a0706';
    ctx.fillRect(tk.x - 14, tk.y - 40, 28, 42);
    ctx.fillStyle = '#4a3c30';
    ctx.fillRect(tk.x - 12, tk.y - 38, 24, 38);
    ctx.fillStyle = `rgb(${st.c})`;
    ctx.fillRect(tk.x - 12, tk.y - 30, 24, 16);
    ctx.fillStyle = '#0c0806';
    ctx.font = '600 16px Cond, Impact, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(st.label, tk.x, tk.y - 21);
    ctx.fillStyle = '#2a211a';
    ctx.beginPath(); ctx.ellipse(tk.x, tk.y - 39, 12, 4, 0, 0, TAU); ctx.fill();
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.35 + Math.sin(time * 5) * 0.15;
    ctx.drawImage(glowSprite(`rgba(${st.c},1)`, 64), tk.x - 40, tk.y - 60, 80, 80);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
}

function drawTeamAuras(ctx, match, time, dt) {
  for (const tm of match.teams) {
    if (tm.rageT <= 0 && tm.freezeT <= 0) continue;
    const col = tm.rageT > 0 ? 'rgba(255,60,20,1)' : 'rgba(150,210,240,1)';
    ctx.globalCompositeOperation = 'lighter';
    for (const p of tm.players) {
      ctx.globalAlpha = 0.28 + Math.sin(time * 10 + p.idx) * 0.08;
      ctx.drawImage(glowSprite(col, 64), p.x - 40, p.y - 100, 80, 110);
      if (tm.rageT > 0 && Math.random() < dt * 8) fx.fire(p.x, p.y, 30, 1, 9, 10);
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
}

function drawOverheads(ctx, match, time, view) {
  for (const p of match.players) {
    if (p.y < view.y0 - 50 || p.y > view.y1 + 150) continue;
    const headY = p.y - p.z - 118;
    if (p.human) {
      const bob = Math.sin(time * 6) * 3;
      ctx.fillStyle = '#070504';
      ctx.beginPath(); ctx.moveTo(p.x - 12, headY - 16 + bob); ctx.lineTo(p.x + 12, headY - 16 + bob); ctx.lineTo(p.x, headY + 2 + bob); ctx.fill();
      ctx.fillStyle = p.human.color;
      ctx.beginPath(); ctx.moveTo(p.x - 8.5, headY - 14 + bob); ctx.lineTo(p.x + 8.5, headY - 14 + bob); ctx.lineTo(p.x, headY - 2 + bob); ctx.fill();
      drawText(ctx, `P${p.human.id + 1}`, p.x, headY - 28 + bob, 22, { font: 'Cond', weight: 700, fill: p.human.color, stroke: '#070504', strokeW: 4, erosion: 0 });
    }
    if ((p.hitImmune > 0 && p.health < 100) || p.state === 'ko') {
      const w = 40, h = 5;
      const x = p.x - w / 2, y = p.y - p.z - (p.grounded ? 44 : 104);
      ctx.fillStyle = 'rgba(0,0,0,0.8)';
      ctx.fillRect(x - 2, y - 2, w + 4, h + 4);
      const hp = clamp(p.health / 100, 0, 1);
      ctx.fillStyle = hp > 0.5 ? '#8a9a3a' : hp > 0.25 ? '#c8801c' : '#c01a10';
      ctx.fillRect(x, y, w * hp, h);
    }
  }
}

function drawAnnouncements(ctx, match, cw, ch, time) {
  const u = ch / 1080;
  const arr = match.announcements;
  if (!arr.length) return;
  const a = arr[arr.length - 1];
  const t = a.t;
  const inT = Math.min(1, t / 0.14);
  const out = t > a.dur - 0.25 ? (a.dur - t) / 0.25 : 1;
  const big = a.text.length <= 4;
  const size = (big ? 200 : a.text.length > 12 ? 104 : 140) * u;
  const sc = t < 0.14 ? 2.2 - 1.2 * easeOutBack(inT) : 1 + Math.max(0, 0.03 - (t - 0.14) * 0.04);
  const jitter = t < 0.25 ? rand(-5, 5) * u : 0;
  ctx.globalAlpha = clamp(out, 0, 1);
  const cy = ch * (big ? 0.4 : 0.3);
  drawText(ctx, a.text, cw / 2 + jitter, cy + jitter, size,
    { font: 'Display', fill: '#f4ead8', fill2: a.color, stroke: '#070302', strokeW: size * 0.07, erosion: 0.45, drips: !big && a.color !== '#ffffff' },
    sc, -0.02);
  if (a.sub) {
    drawText(ctx, a.sub, cw / 2, cy + size * 0.95, 44 * u,
      { font: 'Cond', weight: 700, fill: '#e8dcc6', stroke: '#070302', strokeW: 6 * u, erosion: 0.15, tracking: 3 * u });
  }
  ctx.globalAlpha = 1;
}
