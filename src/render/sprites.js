// Procedural pseudo-3D characters: a small skeleton is posed in 3D, rotated to the facing
// angle, projected obliquely (x, y - z) and drawn as outlined, shaded capsules.
import { TAU, clamp, lerp } from '../core/math.js';
import { glowSprite } from './fx.js';
import { BALL_R } from '../game/constants.js';

const S = 1.34; // model → world scale

function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  if (k > 0) { r += (255 - r) * k; g += (255 - g) * k; b += (255 - b) * k; } else { r *= 1 + k; g *= 1 + k; b *= 1 + k; }
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}
const shadeCache = new Map();
function sh(hex, k) {
  const key = hex + k;
  let v = shadeCache.get(key);
  if (!v) { v = shade(hex, k); shadeCache.set(key, v); }
  return v;
}

/** Builds joint positions (local space: x right, y forward, z up) for the current state. */
function pose(p, time) {
  const a = p.anim;
  const run = clamp(a.speed, 0, 1);
  const ph = a.phase;
  const J = {};
  let pitch = 0, roll = 0;
  const bob = Math.abs(Math.sin(ph)) * 2.2 * run;
  const st = p.state;

  if (st === 'down' || st === 'ko') {
    // Lying on the back, head toward -y.
    const t = clamp(a.stateT / 0.25, 0, 1);
    const twitch = st === 'ko' ? Math.sin(time * 30) * (a.stateT < 1 ? 1.5 : 0) : 0;
    J.pelvis = [0, 2, lerp(28, 6, t)];
    J.chest = [0, lerp(0, -14, t), lerp(46, 7, t)];
    J.head = [0, lerp(0, -25, t), lerp(61, 8, t)];
    J.hipL = [-6, 2, J.pelvis[2]]; J.hipR = [6, 2, J.pelvis[2]];
    J.kneeL = [-8, 13, 9]; J.kneeR = [7, 12, 12 + twitch];
    J.footL = [-10, 24, 3]; J.footR = [9, 22, 5];
    J.shL = [-12, J.chest[1] - 2, J.chest[2] + 1]; J.shR = [12, J.chest[1] - 2, J.chest[2] + 1];
    J.elL = [-20, -10, 4]; J.elR = [20, -8, 5 + twitch];
    J.haL = [-26, -18, 3]; J.haR = [26, -2, 4];
    return { J, pitch, roll };
  }

  if (st === 'slide') {
    J.pelvis = [0, 0, 11];
    J.chest = [0, -11, 22];
    J.head = [0, -16, 32];
    J.hipL = [-6, 0, 11]; J.hipR = [6, 0, 11];
    J.kneeL = [-7, 13, 12]; J.kneeR = [7, 10, 16];
    J.footL = [-7, 27, 5]; J.footR = [7, 22, 8];
    J.shL = [-12, -12, 26]; J.shR = [12, -12, 26];
    J.elL = [-17, -18, 14]; J.elR = [17, -4, 22];
    J.haL = [-18, -24, 4]; J.haR = [16, 8, 20];
    return { J, pitch, roll };
  }

  // Standing family
  J.pelvis = [0, 0, 30 + bob];
  J.chest = [0, 1.5 * run, 47 + bob];
  J.head = [0, 2.5 * run, 61 + bob];
  J.hipL = [-6, 0, 30 + bob]; J.hipR = [6, 0, 30 + bob];
  J.shL = [-15.5, J.chest[1], 50 + bob]; J.shR = [15.5, J.chest[1], 50 + bob];
  pitch = 0.16 * run;

  const legs = (side, off) => {
    const sw = Math.sin(ph + off) * 12 * run;
    const lift = Math.max(0, Math.cos(ph + off)) * 9 * run;
    const x = side * 7.2;
    J[side < 0 ? 'footL' : 'footR'] = [x * 1.1, sw, lift + 2];
    J[side < 0 ? 'kneeL' : 'kneeR'] = [x * 1.05, sw * 0.45 + 4 * run + 1.5, 16 + lift * 0.6 + bob * 0.5];
  };
  legs(-1, 0);
  legs(1, Math.PI);
  const arms = (side, off) => {
    const sw = -Math.sin(ph + off) * 11 * run;
    const x = side * 17;
    J[side < 0 ? 'haL' : 'haR'] = [x * 1.05, sw, 32 + Math.abs(sw) * 0.4 + bob];
    J[side < 0 ? 'elL' : 'elR'] = [x * 1.13, sw * 0.4 - 3, 41 + bob];
  };
  arms(-1, 0);
  arms(1, Math.PI);

  if (st === 'jump') {
    J.kneeL = [-7, 8, 20]; J.kneeR = [7, 6, 24];
    J.footL = [-7, 0, 9]; J.footR = [7, -2, 13];
    J.haL = [-14, 6, 78]; J.haR = [14, 6, 78];
    J.elL = [-15, 2, 64]; J.elR = [15, 2, 64];
  } else if (st === 'dive') {
    roll = a.diveDir * 1.35 * clamp(a.stateT / 0.12, 0, 1);
    J.haL = [-10, 4, 78]; J.haR = [10, 4, 78];
    J.elL = [-12, 2, 64]; J.elR = [12, 2, 64];
  } else if (st === 'stun') {
    const w = Math.sin(time * 9) * 0.12;
    pitch = w; roll = Math.cos(time * 7) * 0.12;
    J.haL = [-14, 4, 24]; J.haR = [14, 4, 24];
  } else if (st === 'celebrate') {
    const b = Math.abs(Math.sin(time * 10)) * 6;
    for (const k of ['pelvis', 'chest', 'head', 'hipL', 'hipR', 'shL', 'shR']) J[k] = [J[k][0], J[k][1], J[k][2] + b];
    J.haL = [-16, 3, 84 + b]; J.haR = [16, 3, 84 + b];
    J.elL = [-17, 2, 68 + b]; J.elR = [17, 2, 68 + b];
  } else if (st === 'throw') {
    const t = clamp(a.stateT / 0.22, 0, 1);
    const k = Math.sin(t * Math.PI * 0.5);
    J.haR = [lerp(12, 4, k), lerp(-14, 20, k), lerp(58, 46, k)];
    J.elR = [14, lerp(-8, 8, k), 52];
    J.haL = [-12, lerp(10, -8, k), 40];
    pitch = 0.1 + 0.2 * k;
  }

  if (p.hasBall && st !== 'throw') {
    if (a.charge > 0) {
      const c = a.charge;
      J.haR = [lerp(8, 13, c), lerp(14, -14, c), lerp(44, 60, c)];
      J.elR = [15, lerp(6, -6, c), lerp(44, 54, c)];
      J.haL = [-8, 14, 44];
      J.elL = [-14, 6, 42];
      pitch = 0.1 - c * 0.15;
    } else {
      J.haL = [-6, 13, 42]; J.haR = [6, 13, 42];
      J.elL = [-14, 5, 42]; J.elR = [14, 5, 42];
    }
  }
  return { J, pitch, roll };
}

const SEGS = [
  // [a, b, width, colorKey]
  ['hipL', 'kneeL', 10.5, 'cloth'], ['kneeL', 'footL', 9, 'boot'],
  ['hipR', 'kneeR', 10.5, 'cloth'], ['kneeR', 'footR', 9, 'boot'],
  ['pelvis', 'chest', 19, 'armor'],
  ['shL', 'shR', 13, 'yoke'],
  ['shL', 'elL', 7.5, 'skin'], ['elL', 'haL', 7, 'glove'],
  ['shR', 'elR', 7.5, 'skin'], ['elR', 'haR', 7, 'glove'],
];

export function drawShadow(ctx, p) {
  const z = p.z;
  const k = 1 / (1 + z * 0.012);
  const lying = p.state === 'down' || p.state === 'ko' || p.state === 'slide';
  ctx.globalAlpha = 0.45 * k;
  ctx.fillStyle = '#000';
  ctx.beginPath();
  ctx.ellipse(p.x + 4, p.y + 3, (lying ? 34 : 24) * k, (lying ? 16 : 11) * k, lying ? p.facing : 0, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
}

export function drawRing(ctx, p, color, width = 3, alpha = 0.8, r = 26) {
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y + 2, r, r * 0.5, 0, 0, TAU);
  ctx.stroke();
  ctx.globalAlpha = 1;
}

export function drawPlayer(ctx, p, team, time, ball) {
  const { J, pitch, roll } = pose(p, time);
  const f = p.facing;
  const fx = Math.cos(f), fy = Math.sin(f);
  const rx = -fy, ry = fx;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const cr = Math.cos(roll), sr = Math.sin(roll);
  const flash = p.hitFlash > 0;
  const shocked = p.shockT > 0;

  // Project all joints.
  const P = {};
  for (const k in J) {
    let [x, y, z] = J[k];
    // pitch (lean forward around the x axis, pivot at feet)
    const y1 = y * cp + z * sp, z1 = -y * sp + z * cp;
    // roll (around forward axis)
    const x2 = x * cr + z1 * sr, z2 = -x * sr + z1 * cr;
    const wx = (x2 * rx + y1 * fx) * S, wy = (x2 * ry + y1 * fy) * S;
    P[k] = { x: p.x + wx, y: p.y + wy - (z2 * S + p.z), d: wy + z2 * 0.01 };
  }

  const col = {
    cloth: team.pants, boot: '#2a1f19', armor: team.armor, yoke: team.armorDark, skin: team.skin, glove: '#2a1d16',
  };

  // Gather drawables with depth.
  const items = SEGS.map(([a, b, w, c]) => ({ kind: 'seg', a: P[a], b: P[b], w: w * S, c: col[c], d: (P[a].d + P[b].d) / 2 }));
  items.push({ kind: 'boot', a: P.footL, d: P.footL.d + 0.5 });
  items.push({ kind: 'boot', a: P.footR, d: P.footR.d + 0.5 });
  items.push({ kind: 'knee', a: P.kneeL, d: P.kneeL.d + 0.3 });
  items.push({ kind: 'knee', a: P.kneeR, d: P.kneeR.d + 0.3 });
  items.push({ kind: 'pad', a: P.shL, d: P.shL.d + 1 });
  items.push({ kind: 'pad', a: P.shR, d: P.shR.d + 1 });
  items.push({ kind: 'head', a: P.head, d: P.head.d + 2 });
  items.push({ kind: 'hand', a: P.haL, d: P.haL.d + 0.2 });
  items.push({ kind: 'hand', a: P.haR, d: P.haR.d + 0.2 });
  let ballPos = null;
  if (p.hasBall && ball) {
    const c = p.anim.charge > 0 || p.state === 'throw' ? P.haR : { x: (P.haL.x + P.haR.x) / 2, y: (P.haL.y + P.haR.y) / 2, d: (P.haL.d + P.haR.d) / 2 };
    ballPos = { x: c.x + fx * 4, y: c.y + fy * 2, d: c.d + 3 };
    items.push({ kind: 'ball', a: ballPos, d: ballPos.d });
  }
  items.sort((u, v) => u.d - v.d);

  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const OUT = 4.2;
  const outline = shocked && Math.sin(time * 60) > 0 ? '#bff8ff' : '#0b0706';

  // Outline pass (unified silhouette).
  ctx.strokeStyle = outline;
  ctx.fillStyle = outline;
  for (const it of items) {
    const a = it.a;
    if (it.kind === 'seg') {
      ctx.lineWidth = it.w + OUT;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(it.b.x, it.b.y); ctx.stroke();
    } else {
      const r = it.kind === 'head' ? 9.5 * S : it.kind === 'pad' ? 8.5 * S : it.kind === 'boot' ? 5.8 * S : it.kind === 'ball' ? BALL_R : it.kind === 'knee' ? 4.6 * S : 4.3 * S;
      ctx.beginPath(); ctx.arc(a.x, a.y, r + OUT / 2, 0, TAU); ctx.fill();
    }
  }

  // Fill pass.
  for (const it of items) {
    const a = it.a;
    switch (it.kind) {
      case 'seg': {
        const c = flash ? '#ffffff' : it.c;
        ctx.strokeStyle = c;
        ctx.lineWidth = it.w;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(it.b.x, it.b.y); ctx.stroke();
        if (!flash) {
          ctx.strokeStyle = sh(it.c, 0.28);
          ctx.lineWidth = it.w * 0.32;
          ctx.beginPath(); ctx.moveTo(a.x - it.w * 0.2, a.y - it.w * 0.18); ctx.lineTo(it.b.x - it.w * 0.2, it.b.y - it.w * 0.18); ctx.stroke();
        }
        if (it.c === team.armor && !flash) {
          // Chest plate details: belt, straps and team emblem stripe.
          ctx.strokeStyle = team.armorDark;
          ctx.lineWidth = 3;
          const mx = lerp(a.x, it.b.x, 0.25), my = lerp(a.y, it.b.y, 0.25);
          ctx.beginPath(); ctx.moveTo(mx - rx * 11, my - ry * 5); ctx.lineTo(mx + rx * 11, my + ry * 5); ctx.stroke();
          ctx.strokeStyle = team.accent;
          ctx.lineWidth = 2.5;
          const nx = lerp(a.x, it.b.x, 0.7), ny = lerp(a.y, it.b.y, 0.7);
          ctx.beginPath(); ctx.moveTo(nx - rx * 9, ny - ry * 4 - 2); ctx.lineTo(nx + rx * 9, ny + ry * 4 - 2); ctx.stroke();
        }
        break;
      }
      case 'boot':
        ctx.fillStyle = flash ? '#fff' : '#241a15';
        ctx.beginPath(); ctx.arc(a.x, a.y, 5.2 * S, 0, TAU); ctx.fill();
        ctx.fillStyle = '#6a5a4a';
        ctx.beginPath(); ctx.arc(a.x - 1.5, a.y - 1.5, 1.6 * S, 0, TAU); ctx.fill();
        break;
      case 'knee':
        ctx.fillStyle = flash ? '#fff' : team.armorLight;
        ctx.beginPath(); ctx.arc(a.x, a.y, 4.2 * S, 0, TAU); ctx.fill();
        ctx.fillStyle = team.armorDark;
        ctx.beginPath(); ctx.arc(a.x + 1, a.y + 1, 1.8 * S, 0, TAU); ctx.fill();
        break;
      case 'hand':
        ctx.fillStyle = flash ? '#fff' : '#3a2a20';
        ctx.beginPath(); ctx.arc(a.x, a.y, 4 * S, 0, TAU); ctx.fill();
        break;
      case 'pad': {
        const r = 8.2 * S;
        const g = ctx.createRadialGradient(a.x - r * 0.35, a.y - r * 0.4, 1, a.x, a.y, r);
        g.addColorStop(0, flash ? '#fff' : team.armorLight);
        g.addColorStop(1, flash ? '#fff' : team.armorDark);
        ctx.fillStyle = g;
        ctx.beginPath(); ctx.arc(a.x, a.y, r, 0, TAU); ctx.fill();
        // spikes
        ctx.fillStyle = '#d9d2c8';
        for (let i = 0; i < 3; i++) {
          const ang = -Math.PI / 2 + (i - 1) * 0.7;
          const bx = a.x + Math.cos(ang) * r * 0.6, by = a.y + Math.sin(ang) * r * 0.6;
          ctx.beginPath();
          ctx.moveTo(bx - 2.2, by + 1); ctx.lineTo(bx + Math.cos(ang) * 8, by + Math.sin(ang) * 8); ctx.lineTo(bx + 2.2, by + 1);
          ctx.fill();
        }
        break;
      }
      case 'head':
        drawHead(ctx, a, team, fx, fy, rx, flash, p);
        break;
      case 'ball':
        drawBallSphere(ctx, a.x, a.y, ball);
        break;
    }
  }
  if (ballPos && ball) { ball.drawX = ballPos.x; ball.drawY = ballPos.y; }
  return P;
}

function drawHead(ctx, a, team, fx, fy, rx, flash, p) {
  const r = 9.2 * S;
  const g = ctx.createRadialGradient(a.x - r * 0.3, a.y - r * 0.45, 1, a.x, a.y, r);
  const helm = team.crest === 'skull' ? '#39434a' : '#3b2a22';
  g.addColorStop(0, flash ? '#fff' : sh(helm, 0.45));
  g.addColorStop(1, flash ? '#fff' : sh(helm, -0.3));
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(a.x, a.y, r, 0, TAU); ctx.fill();

  const front = fy; // >0 facing camera
  const faceX = a.x + fx * r * 0.55, faceY = a.y + fy * r * 0.35 + 1;
  if (team.crest === 'skull') {
    // Bone-white skull mask on the face side.
    if (front > -0.55) {
      ctx.fillStyle = flash ? '#fff' : team.crestColor;
      ctx.beginPath(); ctx.ellipse(faceX, faceY, r * (0.55 + 0.25 * Math.abs(fy)), r * 0.72, 0, 0, TAU); ctx.fill();
      ctx.fillStyle = '#0a0a0c';
      const ex = rx * 3.6 * S, ey = -fx * 0 + 0;
      ctx.beginPath(); ctx.arc(faceX - ex, faceY - 2 + ey, 2.4 * S * Math.max(0.3, front + 0.5), 0, TAU); ctx.fill();
      ctx.beginPath(); ctx.arc(faceX + ex, faceY - 2 - ey, 2.4 * S * Math.max(0.3, front + 0.5), 0, TAU); ctx.fill();
      // glowing eyes
      ctx.fillStyle = team.accent;
      ctx.beginPath(); ctx.arc(faceX - ex, faceY - 2, 1.1 * S, 0, TAU); ctx.arc(faceX + ex, faceY - 2, 1.1 * S, 0, TAU); ctx.fill();
      ctx.strokeStyle = '#0a0a0c'; ctx.lineWidth = 1.2;
      for (let i = -2; i <= 2; i++) {
        ctx.beginPath(); ctx.moveTo(faceX + rx * i * 1.6, faceY + 3); ctx.lineTo(faceX + rx * i * 1.6, faceY + 6); ctx.stroke();
      }
    }
    // Back fins
    ctx.fillStyle = '#9aa5ab';
    ctx.beginPath();
    ctx.moveTo(a.x - fx * r * 0.2 - 2, a.y - r * 0.8);
    ctx.lineTo(a.x - fx * r * 1.2, a.y - r * 1.25 - fy * 3);
    ctx.lineTo(a.x - fx * r * 0.2 + 2, a.y - r * 0.5);
    ctx.fill();
  } else {
    // Welded goggles + red mohawk crest.
    if (front > -0.55) {
      ctx.fillStyle = '#16100c';
      ctx.fillRect(faceX - 7 * S * (0.4 + Math.abs(fy) * 0.6), faceY - 4, 14 * S * (0.4 + Math.abs(fy) * 0.6), 5);
      ctx.fillStyle = team.accent;
      const ex = rx * 3.3 * S;
      ctx.beginPath(); ctx.arc(faceX - ex, faceY - 1.6, 1.9 * S, 0, TAU); ctx.arc(faceX + ex, faceY - 1.6, 1.9 * S, 0, TAU); ctx.fill();
      // jaw grille
      ctx.strokeStyle = '#8b8178'; ctx.lineWidth = 1.2;
      for (let i = -1; i <= 1; i++) {
        ctx.beginPath(); ctx.moveTo(faceX + rx * i * 2.6 - 0.5, faceY + 3); ctx.lineTo(faceX + rx * i * 2.6, faceY + 7); ctx.stroke();
      }
    }
    ctx.fillStyle = flash ? '#fff' : team.crestColor;
    for (let i = -2; i <= 2; i++) {
      const t = i / 2;
      const bx = a.x + fx * t * r * 0.8, by = a.y - r * 0.75 + fy * t * r * 0.5;
      ctx.beginPath();
      ctx.moveTo(bx - 3, by + 3);
      ctx.lineTo(bx - fx * 2, by - 10 + Math.abs(t) * 3);
      ctx.lineTo(bx + 3, by + 3);
      ctx.fill();
    }
  }
}

export function drawBallSphere(ctx, x, y, ball) {
  const r = BALL_R;
  const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, 1, x, y, r);
  if (ball && ball.electric > 0) {
    g.addColorStop(0, '#ffffff'); g.addColorStop(0.5, '#9ff6ff'); g.addColorStop(1, '#1b6d8a');
  } else {
    g.addColorStop(0, '#ffffff'); g.addColorStop(0.35, '#c9ccd0'); g.addColorStop(0.8, '#5d6166'); g.addColorStop(1, '#2a2c30');
  }
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  ctx.strokeStyle = 'rgba(20,20,24,0.8)';
  ctx.lineWidth = 1.4;
  const spin = ball ? ball.spin : 0;
  ctx.beginPath(); ctx.ellipse(x, y, r * 0.95, r * Math.abs(Math.cos(spin)) * 0.95 + 0.5, 0, 0, TAU); ctx.stroke();
}

export function drawBall(ctx, ball, time) {
  // Shadow
  const k = 1 / (1 + ball.z * 0.01);
  ctx.globalAlpha = 0.5 * k;
  ctx.fillStyle = '#000';
  ctx.beginPath(); ctx.ellipse(ball.x + 3, ball.y + 2, BALL_R * 1.2 * k, BALL_R * 0.6 * k, 0, 0, TAU); ctx.fill();
  ctx.globalAlpha = 1;
  const x = ball.x, y = ball.y - ball.z;
  // Trail
  const sp = Math.hypot(ball.vx, ball.vy);
  if (ball.trail.length > 1 && sp > 250) {
    ctx.globalCompositeOperation = 'lighter';
    const col = ball.electric > 0 ? '120,240,255' : ball.lastTeam === 0 ? '255,150,50' : ball.lastTeam === 1 ? '80,210,255' : '255,240,200';
    for (let i = 1; i < ball.trail.length; i++) {
      const a = ball.trail[i - 1], b = ball.trail[i];
      const t = i / ball.trail.length;
      ctx.strokeStyle = `rgba(${col},${t * 0.55})`;
      ctx.lineWidth = BALL_R * 1.6 * t;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.fillStyle = '#0b0706';
  ctx.beginPath(); ctx.arc(x, y, BALL_R + 2, 0, TAU); ctx.fill();
  drawBallSphere(ctx, x, y, ball);
}

export function drawBallGlow(ctx, ball, time) {
  const x = ball.drawX ?? ball.x, y = ball.drawY ?? ball.y - ball.z;
  ctx.globalCompositeOperation = 'lighter';
  if (ball.electric > 0) {
    const img = glowSprite('rgba(90,220,255,1)', 128);
    const s = 120 + Math.sin(time * 40) * 20;
    ctx.globalAlpha = 0.7;
    ctx.drawImage(img, x - s / 2, y - s / 2, s, s);
  } else {
    const img = glowSprite('rgba(255,230,190,1)', 64);
    ctx.globalAlpha = 0.25;
    ctx.drawImage(img, x - 30, y - 30, 60, 60);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}
