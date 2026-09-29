// Scene renderer: composes floor, crowd, furniture, y-sorted sprites, particles, lights and
// screen-space announcer text into the 2D scene canvas that the WebGL post pass consumes.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, BUMPERS, ELECTRO, STAR_XS, RAMP_HALF, TEAMS } from '../game/constants.js';
import { drawFloor, drawCrowd, drawLights, barrelSprites, emitBarrelFire, starPath, TOP_WALL } from './arena.js';
import { drawPlayer, drawShadow, drawRing, drawBall, drawBallGlow } from './sprites.js';
import { fx, glowSprite } from './fx.js';
import { TAU, rand, clamp, easeOutBack } from '../core/math.js';

const TEAM_RGB = ['255,130,40', '60,200,255'];

export function renderScene(ctx, match, cam, cw, ch, time) {
  const view = cam.view;
  const s = cw / cam.viewW;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = '#07040a';
  ctx.fillRect(0, 0, cw, ch);
  ctx.setTransform(s, 0, 0, s, -(view.x0 + fx.shakeX) * s, -(view.y0 + fx.shakeY) * s);
  ctx.imageSmoothingEnabled = true;

  drawFloor(ctx, view);
  drawCrowd(ctx, view, time, match.excitement);
  drawGoalPits(ctx, match, time);
  drawStars(ctx, match, time);
  drawRamps(ctx, match, time);
  drawElectro(ctx, match, time);
  drawLauncher(ctx, match, time);
  drawTokens(ctx, match, time);

  // Shadows & rings under players
  for (const p of match.players) {
    drawShadow(ctx, p);
    const tr = TEAM_RGB[p.team.idx];
    if (p.human) {
      const pulse = 0.75 + Math.sin(time * 8) * 0.25;
      ctx.globalCompositeOperation = 'lighter';
      drawRing(ctx, p, p.human.color, 5, pulse, 30);
      ctx.globalCompositeOperation = 'source-over';
      if (p.charging) {
        const c = Math.min(1, p.chargeT / 0.45);
        ctx.strokeStyle = c >= 1 ? '#ff3a1a' : '#ffd23a';
        ctx.lineWidth = 6;
        ctx.beginPath();
        ctx.ellipse(p.x, p.y + 2, 38, 19, 0, -Math.PI / 2, -Math.PI / 2 + c * TAU);
        ctx.stroke();
        // Aim line
        if (p.aimX !== undefined) {
          ctx.globalCompositeOperation = 'lighter';
          ctx.strokeStyle = `rgba(255,220,120,${0.25 + c * 0.35})`;
          ctx.lineWidth = 3;
          ctx.setLineDash([10, 10]);
          ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.aimX * (140 + c * 160), p.y + p.aimY * (140 + c * 160)); ctx.stroke();
          ctx.setLineDash([]);
          ctx.globalCompositeOperation = 'source-over';
        }
      }
    } else {
      drawRing(ctx, p, `rgba(${tr},1)`, 2.5, p.grounded ? 0.25 : 0.6, 25);
    }
    if (p.hasBall) {
      ctx.globalCompositeOperation = 'lighter';
      drawRing(ctx, p, '#ffffff', 2, 0.35 + Math.sin(time * 12) * 0.2, 34);
      ctx.globalCompositeOperation = 'source-over';
    }
  }

  // Y-sorted sprites
  const list = [];
  for (const p of match.players) list.push({ y: p.y, draw: (c) => drawPlayer(c, p, p.team.def, time, match.ball) });
  BUMPERS.forEach((b, i) => list.push({ y: b.y, draw: (c) => drawBumper(c, b, match.bumperFlash[i], time) }));
  for (const side of [0, 1]) for (const top of [true, false]) {
    const x = side ? W : 0, y = top ? CY - GOAL_HALF : CY + GOAL_HALF;
    list.push({ y: y + (top ? -1 : 1), draw: (c) => drawGoalPost(c, x, y, top, side, match, time) });
  }
  barrelSprites(list, time);
  const b = match.ball;
  if (!b.owner && b.z > -5) list.push({ y: b.y, draw: (c) => drawBall(c, b, time) });
  list.sort((a, d) => a.y - d.y);
  for (const it of list) it.draw(ctx);

  if (match.phase !== 'pause') emitBarrelFire(view);
  fx.draw(ctx);
  drawLights(ctx, view, time);
  if (!b.owner && b.z <= -5) { /* inside launcher */ } else drawBallGlow(ctx, b, time);
  if (!b.owner) { b.drawX = undefined; b.drawY = undefined; }
  drawTeamAuras(ctx, match, time);
  fx.drawTexts(ctx);
  drawOverheads(ctx, match, time);

  // Screen space
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  drawAnnouncements(ctx, match, cw, ch, time);
}

function drawGoalPits(ctx, match, time) {
  ctx.globalCompositeOperation = 'lighter';
  for (const side of [0, 1]) {
    const x = side ? W : 0;
    const defender = match.teams.find((t) => match.ownGoalX(t) === x);
    const rgb = TEAM_RGB[defender.idx];
    const goal = match.phase === 'goal' && match.goalInfo && match.goalInfo.side === side;
    const a = goal ? 0.7 + Math.sin(time * 30) * 0.3 : 0.28 + Math.sin(time * 4 + side) * 0.08;
    const g = ctx.createLinearGradient(x, 0, x + (side ? GOAL_DEPTH : -GOAL_DEPTH), 0);
    g.addColorStop(0, `rgba(${rgb},${a})`);
    g.addColorStop(1, `rgba(${rgb},0)`);
    ctx.fillStyle = g;
    ctx.fillRect(side ? x : x - GOAL_DEPTH, CY - GOAL_HALF, GOAL_DEPTH, GOAL_HALF * 2);
    // Energy barrier scanlines across the mouth
    ctx.strokeStyle = `rgba(${rgb},${0.35 + Math.random() * 0.2})`;
    ctx.lineWidth = 2;
    for (let i = 0; i < 5; i++) {
      const yy = CY - GOAL_HALF + ((time * 120 + i * 50) % (GOAL_HALF * 2));
      ctx.beginPath(); ctx.moveTo(x - 6, yy); ctx.lineTo(x + 6, yy); ctx.stroke();
    }
    ctx.fillStyle = `rgba(${rgb},0.5)`;
    ctx.fillRect(x - 2, CY - GOAL_HALF, 4, GOAL_HALF * 2);
  }
  ctx.globalCompositeOperation = 'source-over';
}

function drawGoalPost(ctx, x, y, top, side, match, time) {
  const hgt = 118;
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.beginPath(); ctx.ellipse(x + 6, y + 4, 20, 9, 0, 0, TAU); ctx.fill();
  const g = ctx.createLinearGradient(x - 13, 0, x + 13, 0);
  g.addColorStop(0, '#221812'); g.addColorStop(0.4, '#6a5a4c'); g.addColorStop(1, '#1b1410');
  ctx.fillStyle = '#0b0706';
  ctx.fillRect(x - 15, y - hgt - 2, 30, hgt + 4);
  ctx.fillStyle = g;
  ctx.fillRect(x - 13, y - hgt, 26, hgt);
  // hazard bands
  for (let k = 0; k < 4; k++) {
    ctx.fillStyle = k % 2 ? '#15100c' : '#d2a01c';
    ctx.fillRect(x - 13, y - 30 - k * 12, 26, 12);
  }
  // top light
  const defender = match.teams.find((t) => match.ownGoalX(t) === x);
  const col = TEAM_RGB[defender.idx];
  ctx.fillStyle = `rgb(${col})`;
  ctx.beginPath(); ctx.arc(x, y - hgt - 4, 8, 0, TAU); ctx.fill();
  ctx.globalCompositeOperation = 'lighter';
  const gl = glowSprite(`rgba(${col},1)`, 64);
  ctx.globalAlpha = 0.6 + Math.sin(time * 6) * 0.2;
  ctx.drawImage(gl, x - 40, y - hgt - 44, 80, 80);
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
  if (top) {
    // Crossbar to the opposite post (drawn with the far post so players overlap it).
    ctx.strokeStyle = '#0b0706'; ctx.lineWidth = 12;
    ctx.beginPath(); ctx.moveTo(x, y - hgt + 10); ctx.lineTo(x, y + GOAL_HALF * 2 - hgt + 10); ctx.stroke();
    ctx.strokeStyle = '#5a4b3f'; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(x, y - hgt + 10); ctx.lineTo(x, y + GOAL_HALF * 2 - hgt + 10); ctx.stroke();
    ctx.globalCompositeOperation = 'lighter';
    ctx.strokeStyle = `rgba(${col},0.5)`; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x, y - hgt + 10); ctx.lineTo(x, y + GOAL_HALF * 2 - hgt + 10); ctx.stroke();
    ctx.globalCompositeOperation = 'source-over';
  }
}

function drawBumper(ctx, b, flash, time) {
  const r = b.r;
  ctx.save();
  ctx.translate(b.x, b.y);
  ctx.fillStyle = '#0b0706';
  ctx.beginPath(); ctx.ellipse(0, 0, r + 8, (r + 8) * 0.62, 0, 0, TAU); ctx.fill();
  ctx.fillStyle = '#4a3c32';
  ctx.beginPath(); ctx.ellipse(0, 0, r + 5, (r + 5) * 0.6, 0, 0, TAU); ctx.fill();
  // dome
  const h = 26;
  const g = ctx.createRadialGradient(-r * 0.35, -h - r * 0.2, 2, 0, -h * 0.4, r * 1.1);
  const hot = flash;
  g.addColorStop(0, hot > 0.1 ? '#fff6d8' : '#d8d0c4');
  g.addColorStop(0.35, hot > 0.1 ? '#ffb24a' : '#8a7f74');
  g.addColorStop(1, '#2a221c');
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(0, -h * 0.35, r, r * 0.95, 0, Math.PI, 0);
  ctx.ellipse(0, 0, r, r * 0.6, 0, 0, Math.PI);
  ctx.fill();
  ctx.strokeStyle = '#0b0706'; ctx.lineWidth = 2.5; ctx.stroke();
  // rim lights
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * TAU + time * 0.8;
    const lx = Math.cos(a) * (r + 1), ly = Math.sin(a) * (r + 1) * 0.6;
    if (ly < -2) continue;
    const on = flash > 0.05 || (Math.floor(time * 6) + i) % 3 === 0;
    ctx.fillStyle = on ? '#ffcf5a' : '#4a3a20';
    ctx.beginPath(); ctx.arc(lx, ly, 3, 0, TAU); ctx.fill();
  }
  if (flash > 0.01) {
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = flash;
    const gl = glowSprite('rgba(255,190,90,1)', 128);
    ctx.drawImage(gl, -r * 2.5, -r * 2.8, r * 5, r * 5);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.restore();
}

function drawStars(ctx, match, time) {
  for (const wall of ['top', 'bottom']) {
    const row = match.stars[wall];
    const y = wall === 'top' ? -TOP_WALL / 2 - 6 : H + 22;
    const sc = wall === 'top' ? 1 : 0.8;
    STAR_XS.forEach((sx, i) => {
      const own = row[i];
      const fl = match.starFlash[wall][i];
      if (own < 0 && fl <= 0) return;
      const rgb = own >= 0 ? TEAM_RGB[own] : '255,255,255';
      ctx.save();
      ctx.translate(sx, y);
      const k = sc * (1 + fl * 0.6);
      ctx.scale(k, k);
      starPath(ctx, 0, 0, 18, 8);
      ctx.fillStyle = `rgb(${rgb})`;
      ctx.fill();
      starPath(ctx, -1, -1, 9, 4);
      ctx.fillStyle = 'rgba(255,255,255,0.8)';
      ctx.fill();
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.5 + fl * 0.5 + Math.sin(time * 5 + i) * 0.1;
      ctx.drawImage(glowSprite(`rgba(${rgb},1)`, 64), -45, -45, 90, 90);
      ctx.restore();
    });
  }
}

function drawRamps(ctx, match, time) {
  for (const [wi, top] of [[0, true], [1, false]]) {
    const y = top ? -TOP_WALL / 2 - 6 : H + 22;
    const leader = match.teams.find((t) => t.mult > 0);
    const rgb = leader ? TEAM_RGB[leader.idx] : '200,180,150';
    const fl = match.rampFlash[wi];
    ctx.save();
    ctx.translate(CX, y);
    // chevrons
    for (let i = -3; i <= 3; i++) {
      const on = leader ? (Math.floor(time * 8) - i + 7) % 7 < 3 : false;
      ctx.fillStyle = on || fl > 0 ? `rgba(${rgb},${0.9})` : 'rgba(80,70,60,0.8)';
      const x = i * 24;
      ctx.beginPath();
      ctx.moveTo(x - 6, -12); ctx.lineTo(x + 4, 0); ctx.lineTo(x - 6, 12); ctx.lineTo(x - 1, 12); ctx.lineTo(x + 9, 0); ctx.lineTo(x - 1, -12);
      ctx.fill();
    }
    ctx.font = '18px Bebas, Impact, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = leader ? `rgb(${rgb})` : '#8a7a6a';
    ctx.fillText(leader ? `x${[1, 1.5, 2][leader.mult]}` : 'x1.5', 0, top ? -20 : 32);
    if (leader || fl > 0) {
      ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = 0.35 + fl * 0.5;
      ctx.drawImage(glowSprite(`rgba(${rgb},1)`, 64), -RAMP_HALF * 1.3, -60, RAMP_HALF * 2.6, 120);
    }
    ctx.restore();
  }
}

function drawElectro(ctx, match, time) {
  const b = match.ball;
  ELECTRO.forEach((e, i) => {
    const fl = match.electroFlash[i];
    ctx.save();
    ctx.translate(e.x, e.y);
    // coil
    ctx.fillStyle = '#0d0d0d';
    ctx.beginPath(); ctx.arc(0, 0, e.r, 0, TAU); ctx.fill();
    for (let k = 0; k < 4; k++) {
      ctx.strokeStyle = k % 2 ? '#7a5a2a' : '#b88a3a';
      ctx.lineWidth = 3;
      ctx.beginPath(); ctx.arc(0, 0, e.r - 4 - k * 5, 0, TAU); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'lighter';
    const pulse = 0.35 + Math.sin(time * 7 + i) * 0.15 + fl * 0.6;
    ctx.globalAlpha = pulse;
    ctx.drawImage(glowSprite('rgba(80,210,255,1)', 64), -e.r * 2.4, -e.r * 2.4, e.r * 4.8, e.r * 4.8);
    ctx.globalAlpha = 1;
    ctx.restore();
    ctx.globalCompositeOperation = 'source-over';
    if (Math.random() < 0.06 + fl * 0.5) {
      const a = rand(0, TAU);
      fx.arc(e.x, e.y, 2, e.x + Math.cos(a) * rand(20, 50), e.y + Math.sin(a) * rand(14, 30), rand(0, 20), '#9ff6ff', 0.1);
    }
  });
}

function drawLauncher(ctx, match, time) {
  if (match.phase !== 'kickoff') return;
  const t = match.phaseT;
  ctx.save();
  ctx.translate(CX, CY);
  ctx.globalCompositeOperation = 'lighter';
  const k = Math.min(1, t / 2);
  ctx.globalAlpha = 0.4 + k * 0.5;
  ctx.drawImage(glowSprite('rgba(255,70,30,1)', 64), -90, -90, 180, 180);
  ctx.strokeStyle = `rgba(255,120,60,${0.5 + k * 0.5})`;
  ctx.lineWidth = 4;
  for (let i = 0; i < 3; i++) {
    const a = time * 4 + (i * TAU) / 3;
    ctx.beginPath(); ctx.arc(0, 0, 44, a, a + 0.8); ctx.stroke();
  }
  ctx.restore();
  ctx.globalCompositeOperation = 'source-over';
  ctx.globalAlpha = 1;
}

const TOKEN_STYLE = {
  rage: { c: '255,70,30', label: 'R' },
  shock: { c: '90,230,255', label: 'E' },
  freeze: { c: '170,220,255', label: 'F' },
  medic: { c: '110,255,140', label: '+' },
  cash: { c: '255,210,60', label: '$' },
};

function drawTokens(ctx, match, time) {
  for (const tk of match.tokens) {
    const st = TOKEN_STYLE[tk.type];
    const blink = tk.life - tk.t < 3 && Math.sin(time * 20) > 0;
    if (blink) continue;
    const hover = 20 + Math.sin(time * 4 + tk.x) * 5;
    ctx.fillStyle = 'rgba(0,0,0,0.4)';
    ctx.beginPath(); ctx.ellipse(tk.x, tk.y, 16, 7, 0, 0, TAU); ctx.fill();
    const w = Math.abs(Math.cos(time * 3 + tk.y)) * 16 + 3;
    ctx.fillStyle = '#0b0706';
    ctx.beginPath(); ctx.ellipse(tk.x, tk.y - hover, w + 3, 19, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = `rgb(${st.c})`;
    ctx.beginPath(); ctx.ellipse(tk.x, tk.y - hover, w, 16, 0, 0, TAU); ctx.fill();
    ctx.fillStyle = '#140a06';
    ctx.font = '22px BlackOps, Impact, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    if (w > 9) ctx.fillText(st.label, tk.x, tk.y - hover + 1);
    ctx.globalCompositeOperation = 'lighter';
    ctx.globalAlpha = 0.6;
    ctx.drawImage(glowSprite(`rgba(${st.c},1)`, 64), tk.x - 45, tk.y - hover - 45, 90, 90);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
  }
}

function drawTeamAuras(ctx, match, time) {
  ctx.globalCompositeOperation = 'lighter';
  for (const t of match.teams) {
    if (t.rageT <= 0 && t.freezeT <= 0) continue;
    const col = t.rageT > 0 ? 'rgba(255,60,20,1)' : 'rgba(150,220,255,1)';
    for (const p of t.players) {
      ctx.globalAlpha = 0.35 + Math.sin(time * 10 + p.idx) * 0.1;
      ctx.drawImage(glowSprite(col, 64), p.x - 45, p.y - 90, 90, 110);
      if (t.rageT > 0 && Math.random() < 0.15) fx.fire(p.x, p.y, 20, 1, 10, 10);
    }
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}

function drawOverheads(ctx, match, time) {
  for (const p of match.players) {
    const headY = p.y - p.z - 112;
    if (p.human) {
      const bob = Math.sin(time * 6) * 4;
      ctx.fillStyle = '#0b0706';
      ctx.beginPath(); ctx.moveTo(p.x - 14, headY - 18 + bob); ctx.lineTo(p.x + 14, headY - 18 + bob); ctx.lineTo(p.x, headY + 2 + bob); ctx.fill();
      ctx.fillStyle = p.human.color;
      ctx.beginPath(); ctx.moveTo(p.x - 10, headY - 16 + bob); ctx.lineTo(p.x + 10, headY - 16 + bob); ctx.lineTo(p.x, headY - 2 + bob); ctx.fill();
      ctx.font = '20px Bebas, Impact, sans-serif';
      ctx.textAlign = 'center';
      ctx.lineWidth = 4; ctx.strokeStyle = '#0b0706';
      ctx.strokeText(`P${p.human.id + 1}`, p.x, headY - 24 + bob);
      ctx.fillText(`P${p.human.id + 1}`, p.x, headY - 24 + bob);
    }
    if ((p.hitImmune > 0 && !p.human) || p.health < 35 || p.state === 'ko') {
      const w = 44, h = 6;
      const x = p.x - w / 2, y = p.y - p.z - (p.grounded ? 44 : 100);
      ctx.fillStyle = 'rgba(0,0,0,0.75)';
      ctx.fillRect(x - 2, y - 2, w + 4, h + 4);
      const hp = clamp(p.health / 100, 0, 1);
      ctx.fillStyle = hp > 0.5 ? '#9bd13a' : hp > 0.25 ? '#e8a21c' : '#e22a1a';
      ctx.fillRect(x, y, w * hp, h);
    }
    if (p.state === 'ko' || (p.state === 'stun')) {
      // Orbiting stars/skulls
      for (let i = 0; i < 3; i++) {
        const a = time * 5 + (i * TAU) / 3;
        const sx = p.x + Math.cos(a) * 20, sy = p.y - p.z - (p.state === 'ko' ? 30 : 80) + Math.sin(a) * 7;
        starPath(ctx, sx, sy, 6, 2.6);
        ctx.fillStyle = '#ffe36a';
        ctx.fill();
      }
    }
  }
}

function drawAnnouncements(ctx, match, cw, ch, time) {
  const u = ch / 1080;
  const list = match.announcements;
  if (!list.length) return;
  const a = list[list.length - 1];
  const t = a.t;
  const inT = Math.min(1, t / 0.16);
  const out = t > a.dur - 0.25 ? (a.dur - t) / 0.25 : 1;
  const sc = t < 0.16 ? 2.6 - 1.6 * easeOutBack(inT) : 1 + Math.max(0, 0.04 - (t - 0.16) * 0.05);
  const big = a.text.length <= 3;
  const size = (big ? 190 : a.text.length > 12 ? 92 : 124) * u;
  const cx = cw / 2, cy = ch * (big ? 0.42 : 0.3);
  ctx.save();
  ctx.globalAlpha = clamp(out, 0, 1);
  ctx.translate(cx + (t < 0.3 ? rand(-6, 6) * u : 0), cy + (t < 0.3 ? rand(-6, 6) * u : 0));
  ctx.scale(sc, sc);
  ctx.rotate(-0.035);
  // Torn banner behind text
  if (!big) {
    ctx.font = `${size}px BlackOps, Impact, sans-serif`;
    const w = ctx.measureText(a.text).width + 120 * u;
    ctx.fillStyle = 'rgba(12,4,2,0.82)';
    ctx.beginPath();
    ctx.moveTo(-w / 2, -size * 0.62);
    for (let x = -w / 2; x <= w / 2; x += 26 * u) ctx.lineTo(x, -size * 0.62 + ((x * 13) % 7) * u);
    ctx.lineTo(w / 2 + 20 * u, size * 0.5);
    for (let x = w / 2; x >= -w / 2; x -= 26 * u) ctx.lineTo(x, size * 0.55 + ((x * 7) % 9) * u);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = a.color;
    ctx.fillRect(-w / 2, size * 0.5, w, 6 * u);
  }
  ctx.font = `${size}px BlackOps, Impact, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  ctx.lineWidth = 14 * u;
  ctx.strokeStyle = '#0a0302';
  ctx.strokeText(a.text, 0, 0);
  const g = ctx.createLinearGradient(0, -size / 2, 0, size / 2);
  g.addColorStop(0, '#ffffff');
  g.addColorStop(0.45, a.color);
  g.addColorStop(1, shadeDark(a.color));
  ctx.fillStyle = g;
  ctx.fillText(a.text, 0, 0);
  if (a.sub) {
    ctx.font = `${40 * u}px Bebas, Impact, sans-serif`;
    ctx.lineWidth = 6 * u;
    ctx.strokeText(a.sub, 0, size * 0.78);
    ctx.fillStyle = '#f2e6d0';
    ctx.fillText(a.sub, 0, size * 0.78);
  }
  ctx.restore();
}

function shadeDark(c) {
  if (c[0] !== '#' || c.length !== 7) return '#401008';
  const n = parseInt(c.slice(1), 16);
  const r = ((n >> 16) & 255) * 0.35, g = ((n >> 8) & 255) * 0.35, b = (n & 255) * 0.35;
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}
