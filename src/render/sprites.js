// Procedural pseudo-3D fighters. A skeleton is posed in 3D, rotated to the facing angle and
// projected obliquely (x, y - z). Parts are drawn back-to-front with directional shading,
// a thin dark silhouette, asymmetric armour, team rags and accumulated blood.
import { TAU, clamp, lerp } from '../core/math.js';
import { glowSprite } from './fx.js';
import { BALL_R } from '../game/constants.js';

const S = 1.2; // model → world scale

const shadeCache = new Map();
function sh(hex, k) {
  const key = hex + k;
  let v = shadeCache.get(key);
  if (v) return v;
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  if (k > 0) { r += (255 - r) * k; g += (255 - g) * k; b += (255 - b) * k; } else { r *= 1 + k; g *= 1 + k; b *= 1 + k; }
  v = `rgb(${r | 0},${g | 0},${b | 0})`;
  shadeCache.set(key, v);
  return v;
}

// Reused buffers to keep the per-frame garbage low.
const J = {};
const P = {};
const JOINTS = ['pelvis', 'waist', 'chest', 'neck', 'head', 'hipL', 'hipR', 'kneeL', 'kneeR', 'footL', 'footR', 'shL', 'shR', 'elL', 'elR', 'haL', 'haR', 'rag'];
for (const k of JOINTS) { J[k] = [0, 0, 0]; P[k] = { x: 0, y: 0, d: 0 }; }
const set = (k, x, y, z) => { const j = J[k]; j[0] = x; j[1] = y; j[2] = z; };

/** Poses the skeleton (local space: x right, y forward, z up). Returns [pitch, roll]. */
function pose(p, time) {
  const a = p.anim;
  const run = clamp(a.speed, 0, 1.2);
  const ph = a.phase;
  const st = p.state;
  let pitch = 0, roll = 0;
  const bob = Math.abs(Math.sin(ph)) * 2.4 * run;

  if (st === 'down' || st === 'ko') {
    const k = clamp(a.stateT / 0.22, 0, 1);
    const tw = st === 'ko' && a.stateT < 1.2 ? Math.sin(time * 34) * 1.6 : 0;
    set('pelvis', 0, 4, lerp(34, 6, k)); set('waist', 0, lerp(2, -6, k), lerp(44, 7, k)); set('chest', 0, lerp(0, -17, k), lerp(56, 8, k));
    set('neck', 0, lerp(0, -24, k), lerp(62, 8, k)); set('head', 0, lerp(0, -31, k), lerp(69, 8, k));
    set('hipL', -6, 4, 6); set('hipR', 6, 4, 6);
    set('kneeL', -9, 17, 10); set('kneeR', 8, 16, 14 + tw);
    set('footL', -11, 31, 4); set('footR', 10, 29, 6);
    set('shL', -15, -17, 9); set('shR', 15, -17, 9);
    set('elL', -25, -11, 5); set('elR', 24, -9, 6 + tw);
    set('haL', -32, -20, 4); set('haR', 31, -2, 5);
    set('rag', 0, 12, 5);
    return [pitch, roll];
  }

  if (st === 'slide') {
    set('pelvis', 0, 0, 12); set('waist', 0, -6, 18); set('chest', 0, -12, 26); set('neck', 0, -15, 32); set('head', 0, -18, 38);
    set('hipL', -6, 0, 12); set('hipR', 6, 0, 12);
    set('kneeL', -7, 16, 13); set('kneeR', 7, 12, 18);
    set('footL', -7, 32, 5); set('footR', 7, 26, 9);
    set('shL', -15, -13, 28); set('shR', 15, -13, 28);
    set('elL', -20, -20, 16); set('elR', 20, -4, 25);
    set('haL', -21, -27, 4); set('haR', 18, 10, 22);
    set('rag', 0, -6, 6);
    return [pitch, roll];
  }

  // Standing family
  const lean = run * 2;
  set('pelvis', 0, 0, 36 + bob);
  set('waist', 0, lean * 0.5, 45 + bob);
  set('chest', 0, lean, 55 + bob);
  set('neck', 0, lean * 1.2, 62 + bob);
  set('head', 0, lean * 1.3 + 1, 69 + bob);
  set('hipL', -7, 0, 36 + bob); set('hipR', 7, 0, 36 + bob);
  set('shL', -16, lean, 59 + bob); set('shR', 15, lean, 59 + bob);
  pitch = 0.15 * Math.min(1, run);

  for (let side = -1; side <= 1; side += 2) {
    const off = side < 0 ? 0 : Math.PI;
    const sw = Math.sin(ph + off) * 15 * run;
    const lift = Math.max(0, Math.cos(ph + off)) * 11 * run;
    set(side < 0 ? 'footL' : 'footR', side * 7.5, sw, lift + 2.5);
    set(side < 0 ? 'kneeL' : 'kneeR', side * 7.8, sw * 0.45 + 5 * run + 2, 19 + lift * 0.6 + bob * 0.5);
    const asw = -Math.sin(ph + off) * 13 * run;
    set(side < 0 ? 'haL' : 'haR', side * 18.5, asw + 2, 37 + Math.abs(asw) * 0.4 + bob);
    set(side < 0 ? 'elL' : 'elR', side * 20, asw * 0.4 - 3, 48 + bob);
  }
  set('rag', 0, 5 - run * 6, 22 + bob + Math.sin(ph * 2) * 2 * run);

  if (st === 'jump') {
    set('kneeL', -8, 10, 24); set('kneeR', 8, 8, 28);
    set('footL', -8, 0, 11); set('footR', 8, -2, 15);
    set('haL', -15, 6, 92); set('haR', 15, 6, 92);
    set('elL', -17, 2, 76); set('elR', 17, 2, 76);
  } else if (st === 'dive') {
    // Roll toward the dive direction (given in world x).
    const rx = -Math.sin(p.facing);
    roll = -a.diveDir * Math.sign(rx || 1) * 1.35 * clamp(a.stateT / 0.12, 0, 1);
    set('haL', -11, 4, 92); set('haR', 11, 4, 92);
    set('elL', -14, 2, 76); set('elR', 14, 2, 76);
  } else if (st === 'stun') {
    pitch = Math.sin(time * 9) * 0.12; roll = Math.cos(time * 7) * 0.12;
    set('haL', -17, 4, 28); set('haR', 17, 4, 28);
  } else if (st === 'celebrate') {
    const b = Math.abs(Math.sin(time * 9)) * 7;
    for (const k of ['pelvis', 'waist', 'chest', 'neck', 'head', 'hipL', 'hipR', 'shL', 'shR', 'rag']) J[k][2] += b;
    set('haL', -19, 3, 96 + b); set('haR', 19, 3, 96 + b);
    set('elL', -21, 2, 79 + b); set('elR', 21, 2, 79 + b);
  } else if (st === 'throw') {
    const k = Math.sin(clamp(a.stateT / 0.22, 0, 1) * Math.PI * 0.5);
    set('haR', lerp(14, 4, k), lerp(-16, 24, k), lerp(68, 54, k));
    set('elR', 17, lerp(-9, 9, k), 61);
    set('haL', -14, lerp(12, -9, k), 46);
    pitch = 0.1 + 0.22 * k;
  }

  if (p.hasBall && st !== 'throw') {
    if (a.charge > 0) {
      const c = a.charge;
      set('haR', lerp(9, 15, c), lerp(16, -16, c), lerp(52, 70, c));
      set('elR', 18, lerp(7, -7, c), lerp(52, 63, c));
      set('haL', -9, 16, 51); set('elL', -17, 7, 49);
      pitch = 0.1 - c * 0.15;
    } else {
      set('haL', -7, 15, 49); set('haR', 7, 15, 49);
      set('elL', -17, 6, 49); set('elR', 17, 6, 49);
    }
  }
  return [pitch, roll];
}

// [a, b, width, material]
const SEGS = [
  ['hipL', 'kneeL', 10.5, 'pants'], ['kneeL', 'footL', 9, 'greave'],
  ['hipR', 'kneeR', 10.5, 'pants'], ['kneeR', 'footR', 9, 'greave'],
  ['pelvis', 'waist', 16, 'leather'],
  ['waist', 'chest', 19, 'plate'],
  ['shL', 'shR', 12, 'leather'],
  ['chest', 'neck', 8, 'skin'],
  ['shL', 'elL', 8.5, 'skin'], ['elL', 'haL', 7.8, 'bracer'],
  ['shR', 'elR', 8.5, 'skin'], ['elR', 'haR', 7.8, 'bracer'],
  ['pelvis', 'rag', 9, 'rag'],
];
const items = SEGS.map(([a, b, w, m]) => ({ kind: 'seg', a, b, w: w * S, m, d: 0 }));
const ragItem = items[items.length - 1];
const extras = [
  { kind: 'boot', a: 'footL' }, { kind: 'boot', a: 'footR' },
  { kind: 'pauldron', a: 'shL' }, { kind: 'strap', a: 'shR' },
  { kind: 'head', a: 'head' }, { kind: 'hand', a: 'haL' }, { kind: 'hand', a: 'haR' },
].map((e) => ({ ...e, d: 0 }));
const ballItem = { kind: 'ball', a: null, d: 0 };
const ballPos = { x: 0, y: 0, d: 0 };
const drawList = [];
const byDepth = (u, v) => u.d - v.d;

export function drawShadow(ctx, p) {
  const k = 1 / (1 + p.z * 0.012);
  const lying = p.state === 'down' || p.state === 'ko' || p.state === 'slide';
  ctx.globalAlpha = 0.5 * k;
  ctx.fillStyle = '#000';
  ctx.beginPath();
  ctx.ellipse(p.x + 5, p.y + 3, (lying ? 36 : 22) * k, (lying ? 15 : 10) * k, lying ? p.facing : 0, 0, TAU);
  ctx.fill();
  ctx.globalAlpha = 1;
}

export function drawRing(ctx, p, color, width = 2, alpha = 0.6, r = 25) {
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y + 2, r, r * 0.45, 0, 0, TAU);
  ctx.stroke();
  ctx.globalAlpha = 1;
}

export function drawPlayer(ctx, p, team, time, ball) {
  const [pitch, roll] = pose(p, time);
  const f = p.facing;
  const fx = Math.cos(f), fy = Math.sin(f);
  const rx = -fy, ry = fx;
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const cr = Math.cos(roll), sr = Math.sin(roll);
  const flash = p.hitFlash > 0;
  const shocked = p.shockT > 0 && Math.sin(time * 60) > 0;

  for (const k of JOINTS) {
    const j = J[k];
    const x = j[0], y = j[1], z = j[2];
    const y1 = y * cp + z * sp, z1 = -y * sp + z * cp;
    const x2 = x * cr + z1 * sr, z2 = -x * sr + z1 * cr;
    const wx = (x2 * rx + y1 * fx) * S, wy = (x2 * ry + y1 * fy) * S;
    const o = P[k];
    o.x = p.x + wx; o.y = p.y + wy - (z2 * S + p.z); o.d = wy + z2 * 0.01;
  }

  const mat = team.__mat || (team.__mat = {
    pants: team.pants, greave: team.metal, leather: team.leather, plate: team.metal,
    skin: team.skin, bracer: team.metalDark, rag: team.mark,
  });

  drawList.length = 0;
  for (const it of items) { it.d = (P[it.a].d + P[it.b].d) / 2; drawList.push(it); }
  for (const e of extras) { e.d = P[e.a].d + (e.kind === 'head' ? 2 : e.kind === 'pauldron' ? 1.2 : 0.4); drawList.push(e); }
  ragItem.d = P.pelvis.d - 0.5 + (fy > 0 ? 1 : 0);
  let hasBallPos = false;
  if (p.hasBall && ball) {
    const c = p.anim.charge > 0 || p.state === 'throw' ? P.haR : null;
    ballPos.x = (c ? c.x : (P.haL.x + P.haR.x) / 2) + fx * 4;
    ballPos.y = (c ? c.y : (P.haL.y + P.haR.y) / 2) + fy * 2;
    ballPos.d = (c ? c.d : (P.haL.d + P.haR.d) / 2) + 3;
    ballItem.a = ballPos;
    ballItem.d = ballPos.d;
    drawList.push(ballItem);
    hasBallPos = true;
  }
  drawList.sort(byDepth);

  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  // Thin silhouette pass for readability on the sand.
  ctx.strokeStyle = shocked ? '#bff4ff' : 'rgba(8,5,4,0.9)';
  ctx.fillStyle = ctx.strokeStyle;
  const OUT = 2.6;
  for (const it of drawList) {
    if (it.kind === 'seg') {
      const a = P[it.a], b = P[it.b];
      ctx.lineWidth = it.w + OUT;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    } else {
      const a = it.kind === 'ball' ? it.a : P[it.a];
      const r = it.kind === 'head' ? 7.6 * S : it.kind === 'pauldron' ? 10 * S : it.kind === 'boot' ? 5.6 * S : it.kind === 'ball' ? BALL_R : it.kind === 'strap' ? 4.5 * S : 4.2 * S;
      ctx.beginPath(); ctx.arc(a.x, a.y, r + OUT / 2, 0, TAU); ctx.fill();
    }
  }

  const wounds = p.wounds || 0;
  for (const it of drawList) {
    switch (it.kind) {
      case 'seg': {
        const a = P[it.a], b = P[it.b];
        const base = mat[it.m];
        ctx.strokeStyle = flash ? '#f0e8e0' : base;
        ctx.lineWidth = it.w;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        if (flash) break;
        // Shadowed lower-right side, then a narrow key light top-left.
        ctx.strokeStyle = sh(base, -0.45);
        ctx.lineWidth = it.w * 0.38;
        ctx.beginPath(); ctx.moveTo(a.x + it.w * 0.28, a.y + it.w * 0.18); ctx.lineTo(b.x + it.w * 0.28, b.y + it.w * 0.18); ctx.stroke();
        const metal = it.m === 'plate' || it.m === 'greave' || it.m === 'bracer';
        ctx.strokeStyle = sh(base, metal ? 0.35 : 0.16);
        ctx.lineWidth = it.w * (metal ? 0.16 : 0.22);
        ctx.beginPath(); ctx.moveTo(a.x - it.w * 0.26, a.y - it.w * 0.2); ctx.lineTo(b.x - it.w * 0.26, b.y - it.w * 0.2); ctx.stroke();
        if (it.m === 'plate') {
          // Team war-paint slash across the chest plate + rivets.
          const mx = lerp(a.x, b.x, 0.55), my = lerp(a.y, b.y, 0.55);
          ctx.strokeStyle = team.mark;
          ctx.lineWidth = 3.4;
          ctx.beginPath(); ctx.moveTo(mx - rx * 9 - 2, my - ry * 4 - 4); ctx.lineTo(mx + rx * 9 + 2, my + ry * 4 + 3); ctx.stroke();
          ctx.fillStyle = sh(team.metal, -0.55);
          const qx = lerp(a.x, b.x, 0.15), qy = lerp(a.y, b.y, 0.15);
          ctx.fillRect(qx - rx * 7 - 1, qy - 1, 2.2, 2.2);
          ctx.fillRect(qx + rx * 7 - 1, qy - 1, 2.2, 2.2);
          if (wounds > 1) {
            ctx.fillStyle = 'rgba(110,8,6,0.85)';
            ctx.beginPath(); ctx.ellipse(mx + rx * 3, my + 3, 3 + wounds, 2 + wounds * 0.6, 0.4, 0, TAU); ctx.fill();
          }
        } else if (it.m === 'skin' && wounds > 0 && it.a !== 'chest') {
          ctx.strokeStyle = 'rgba(120,10,6,0.8)';
          ctx.lineWidth = Math.min(it.w * 0.6, 1.5 + wounds * 0.8);
          ctx.beginPath(); ctx.moveTo(lerp(a.x, b.x, 0.3), lerp(a.y, b.y, 0.3)); ctx.lineTo(lerp(a.x, b.x, 0.3 + wounds * 0.08), lerp(a.y, b.y, 0.3 + wounds * 0.08)); ctx.stroke();
        } else if (it.m === 'rag') {
          ctx.strokeStyle = sh(team.mark, -0.4);
          ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.moveTo(lerp(a.x, b.x, 0.5) - 3, lerp(a.y, b.y, 0.5)); ctx.lineTo(b.x - 2, b.y + 2); ctx.stroke();
        }
        break;
      }
      case 'boot': {
        const a = P[it.a];
        ctx.fillStyle = flash ? '#f0e8e0' : team.boot;
        ctx.beginPath(); ctx.arc(a.x, a.y, 5.3 * S, 0, TAU); ctx.fill();
        ctx.fillStyle = sh(team.metal, 0.1);
        ctx.fillRect(a.x - 3, a.y - 3.5, 6, 2);
        break;
      }
      case 'hand': {
        const a = P[it.a];
        ctx.fillStyle = flash ? '#f0e8e0' : '#241a14';
        ctx.beginPath(); ctx.arc(a.x, a.y, 4 * S, 0, TAU); ctx.fill();
        ctx.fillStyle = '#8a8076';
        ctx.fillRect(a.x - 2.5, a.y - 4.5, 1.6, 2.4); ctx.fillRect(a.x + 0.8, a.y - 4.5, 1.6, 2.4);
        break;
      }
      case 'pauldron': {
        const a = P[it.a];
        const r = 9.5 * S;
        ctx.fillStyle = flash ? '#f0e8e0' : team.metal;
        ctx.beginPath(); ctx.ellipse(a.x, a.y, r, r * 0.85, -0.3, 0, TAU); ctx.fill();
        if (flash) break;
        ctx.fillStyle = sh(team.metal, -0.5);
        ctx.beginPath(); ctx.ellipse(a.x + 2.5, a.y + 2.5, r * 0.8, r * 0.55, -0.3, 0, Math.PI); ctx.fill();
        ctx.fillStyle = team.mark;
        ctx.beginPath(); ctx.ellipse(a.x - 1, a.y - 1, r * 0.55, r * 0.35, -0.3, 0, TAU); ctx.fill();
        ctx.fillStyle = sh(team.metal, 0.35);
        ctx.beginPath(); ctx.ellipse(a.x - r * 0.4, a.y - r * 0.45, r * 0.35, r * 0.18, -0.5, 0, TAU); ctx.fill();
        for (let i = 0; i < 3; i++) {
          const ang = -Math.PI / 2 - 0.9 + i * 0.55;
          const bx = a.x + Math.cos(ang) * r * 0.6, by = a.y + Math.sin(ang) * r * 0.6;
          ctx.fillStyle = '#0c0907';
          ctx.beginPath(); ctx.moveTo(bx - 2.6, by + 1); ctx.lineTo(bx + Math.cos(ang) * 11, by + Math.sin(ang) * 11); ctx.lineTo(bx + 2.6, by + 1); ctx.fill();
          ctx.fillStyle = '#b3aba2';
          ctx.beginPath(); ctx.moveTo(bx - 1.2, by + 0.5); ctx.lineTo(bx + Math.cos(ang) * 9.5, by + Math.sin(ang) * 9.5); ctx.lineTo(bx + 0.6, by + 0.5); ctx.fill();
        }
        break;
      }
      case 'strap': {
        const a = P[it.a];
        ctx.fillStyle = flash ? '#f0e8e0' : team.leather;
        ctx.beginPath(); ctx.arc(a.x, a.y, 4.3 * S, 0, TAU); ctx.fill();
        ctx.strokeStyle = '#6d655c'; ctx.lineWidth = 1.4;
        ctx.beginPath(); ctx.arc(a.x, a.y, 3 * S, 0.3, 2.6); ctx.stroke();
        break;
      }
      case 'head':
        drawHead(ctx, P.head, team, fx, fy, rx, ry, flash, wounds);
        break;
      case 'ball':
        drawBallSphere(ctx, it.a.x, it.a.y, ball);
        break;
    }
  }
  if (hasBallPos) { ball.drawX = ballPos.x; ball.drawY = ballPos.y; }
}

function drawHead(ctx, a, team, fx, fy, rx, ry, flash, wounds) {
  const r = 7.2 * S;
  const facing = fy; // > 0 : face toward the camera
  const faceX = a.x + fx * r * 0.5, faceY = a.y + fy * r * 0.3 + 1;
  if (team.mask === 'welder') {
    // Rusted welder helmet with a glowing slit.
    ctx.fillStyle = flash ? '#f0e8e0' : '#4a3a2e';
    ctx.beginPath(); ctx.ellipse(a.x, a.y, r, r * 1.05, 0, 0, TAU); ctx.fill();
    if (flash) return;
    ctx.fillStyle = '#2a1f18';
    ctx.beginPath(); ctx.ellipse(a.x + 2, a.y + 2, r * 0.8, r * 0.75, 0, 0, Math.PI); ctx.fill();
    ctx.fillStyle = 'rgba(150,70,30,0.6)';
    ctx.beginPath(); ctx.ellipse(a.x - r * 0.35, a.y - r * 0.4, r * 0.35, r * 0.25, -0.4, 0, TAU); ctx.fill();
    if (facing > -0.5) {
      const w = r * (0.55 + Math.abs(fy) * 0.45);
      ctx.fillStyle = '#120c09';
      ctx.fillRect(faceX - w, faceY - 3.5, w * 2, 5);
      ctx.fillStyle = team.glow;
      ctx.fillRect(faceX - w * 0.85, faceY - 2.2, w * 1.7, 2);
      ctx.fillStyle = '#1b130f';
      ctx.fillRect(faceX - 3, faceY + 3, 6, 4);
    }
    ctx.fillStyle = '#8a7e72';
    for (let i = -1; i <= 1; i++) {
      ctx.beginPath(); ctx.arc(a.x + fx * i * 3.5, a.y - r * 0.85 + fy * i * 2, 1.6, 0, TAU); ctx.fill();
    }
  } else {
    // War Boy: shaved chalk-white skull, black eye sockets, stitched grin.
    ctx.fillStyle = flash ? '#f0e8e0' : '#dcd6cc';
    ctx.beginPath(); ctx.ellipse(a.x, a.y, r * 0.95, r * 1.05, 0, 0, TAU); ctx.fill();
    if (flash) return;
    ctx.fillStyle = 'rgba(90,80,70,0.55)';
    ctx.beginPath(); ctx.ellipse(a.x + 2, a.y + 2.5, r * 0.75, r * 0.7, 0, 0, Math.PI); ctx.fill();
    if (facing > -0.5) {
      const ex = rx * 2.8 * S, ey = ry * 1.2;
      const er = 2.3 * S * clamp(facing + 0.6, 0.35, 1);
      ctx.fillStyle = '#080606';
      ctx.beginPath(); ctx.ellipse(faceX - ex, faceY - 2.5 - ey, er * 1.2, er, 0, 0, TAU); ctx.fill();
      ctx.beginPath(); ctx.ellipse(faceX + ex, faceY - 2.5 + ey, er * 1.2, er, 0, 0, TAU); ctx.fill();
      ctx.strokeStyle = '#1a1512'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(faceX - 4, faceY + 3.5); ctx.lineTo(faceX + 4, faceY + 3.5); ctx.stroke();
      for (let i = -3; i <= 3; i += 2) { ctx.beginPath(); ctx.moveTo(faceX + i, faceY + 2); ctx.lineTo(faceX + i, faceY + 5); ctx.stroke(); }
    } else {
      ctx.strokeStyle = 'rgba(120,40,30,0.7)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(a.x - 3, a.y - 3); ctx.lineTo(a.x + 3, a.y + 2); ctx.stroke();
    }
  }
  if (wounds > 2) {
    ctx.fillStyle = 'rgba(120,8,6,0.8)';
    ctx.beginPath(); ctx.ellipse(a.x - 2, a.y - 3, 2.5, 3.5, 0.3, 0, TAU); ctx.fill();
  }
}

export function drawBallSphere(ctx, x, y, ball) {
  const r = BALL_R;
  const electric = ball && ball.electric > 0;
  ctx.fillStyle = electric ? '#bfefff' : '#6d6f72';
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  ctx.fillStyle = electric ? '#3aa8d8' : '#2c2e31';
  ctx.beginPath(); ctx.arc(x + 1.5, y + 1.5, r * 0.8, 0, Math.PI); ctx.fill();
  ctx.fillStyle = electric ? '#ffffff' : '#c8cacc';
  ctx.beginPath(); ctx.arc(x - r * 0.35, y - r * 0.4, r * 0.3, 0, TAU); ctx.fill();
  ctx.strokeStyle = 'rgba(15,15,18,0.8)';
  ctx.lineWidth = 1.3;
  const spin = ball ? ball.spin : 0;
  ctx.beginPath(); ctx.ellipse(x, y, r * 0.95, r * Math.abs(Math.cos(spin)) * 0.95 + 0.5, 0, 0, TAU); ctx.stroke();
}

export function drawBall(ctx, ball) {
  const k = 1 / (1 + ball.z * 0.01);
  ctx.globalAlpha = 0.55 * k;
  ctx.fillStyle = '#000';
  ctx.beginPath(); ctx.ellipse(ball.x + 3, ball.y + 2, BALL_R * 1.2 * k, BALL_R * 0.6 * k, 0, 0, TAU); ctx.fill();
  ctx.globalAlpha = 1;
  const x = ball.x, y = ball.y - ball.z;
  const tr = ball.trail;
  if (tr.length > 1 && Math.hypot(ball.vx, ball.vy) > 280) {
    ctx.globalCompositeOperation = 'lighter';
    const col = ball.electric > 0 ? '120,220,255' : '255,200,140';
    ctx.lineCap = 'round';
    for (let i = 1; i < tr.length; i++) {
      const t = i / tr.length;
      ctx.strokeStyle = `rgba(${col},${(t * 0.45).toFixed(2)})`;
      ctx.lineWidth = BALL_R * 1.5 * t;
      ctx.beginPath(); ctx.moveTo(tr[i - 1].x, tr[i - 1].y); ctx.lineTo(tr[i].x, tr[i].y); ctx.stroke();
    }
    ctx.globalCompositeOperation = 'source-over';
  }
  ctx.fillStyle = '#070505';
  ctx.beginPath(); ctx.arc(x, y, BALL_R + 1.6, 0, TAU); ctx.fill();
  drawBallSphere(ctx, x, y, ball);
}

export function drawBallGlow(ctx, ball, time) {
  const x = ball.drawX ?? ball.x, y = ball.drawY ?? ball.y - ball.z;
  ctx.globalCompositeOperation = 'lighter';
  if (ball.electric > 0) {
    const s = 110 + Math.sin(time * 40) * 20;
    ctx.globalAlpha = 0.65;
    ctx.drawImage(glowSprite('rgba(90,200,255,1)', 128), x - s / 2, y - s / 2, s, s);
  } else {
    ctx.globalAlpha = 0.22;
    ctx.drawImage(glowSprite('rgba(255,220,180,1)', 64), x - 26, y - 26, 52, 52);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}
