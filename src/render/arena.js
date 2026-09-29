// Arena: baked floor (static, uploaded once), tiled decal layer (blood, scorch — only touched
// tiles are redrawn), pre-rendered crowd animation frames, walls and fire barrels.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, STAR_YS, RAMP_HALF } from '../game/constants.js';
import { rand, pick, TAU, fbm, hash, makeCanvas, clamp } from '../core/math.js';
import { fx, glowSprite } from './fx.js';

export const PAD_X = 330;
export const PAD_TOP = 380;
export const PAD_BOTTOM = 300;
export const TOP_WALL = 110; // visible height of the top wall face
export const LEDGE = 60; // side wall thickness

let floor, fctx;
const TILE = 512;
const decalTiles = new Map();
let crowdFrames = []; // [{left,right,top,bottom}] canvases per frame
let crowdFrame = 0, crowdClock = 0;
const torches = [];

export const barrels = [];
for (const y of [-40, H * 0.25, H * 0.5, H * 0.75, H + 20]) { barrels.push({ x: -LEDGE - 42, y }); barrels.push({ x: W + LEDGE + 42, y }); }

export function arenaBounds() {
  return { x0: -PAD_X, y0: -PAD_TOP, x1: W + PAD_X, y1: H + PAD_BOTTOM };
}

export function buildArena() {
  floor = makeCanvas(W + PAD_X * 2, H + PAD_TOP + PAD_BOTTOM);
  fctx = floor.getContext('2d');
  const g = fctx;
  g.save();
  g.translate(PAD_X, PAD_TOP);

  g.fillStyle = '#0d0907';
  g.fillRect(-PAD_X, -PAD_TOP, floor.width, floor.height);

  // --- field base: worn steel plates under sand ---
  g.fillStyle = '#3a3029';
  g.fillRect(0, 0, W, H);
  const PL = 200;
  for (let py = 0; py < H; py += PL) {
    for (let px = 0; px < W; px += PL) {
      const v = hash(px, py, 5);
      g.fillStyle = `rgba(${20 + v * 30 | 0},${14 + v * 20 | 0},${10 + v * 14 | 0},${0.25 + v * 0.2})`;
      g.fillRect(px, py, PL, PL);
      g.fillStyle = 'rgba(0,0,0,0.35)';
      g.fillRect(px, py, PL, 2);
      g.fillRect(px, py, 2, PL);
      g.fillStyle = 'rgba(255,220,180,0.035)';
      g.fillRect(px + 2, py + 2, PL - 4, 1);
      for (const [rx, ry] of [[10, 10], [PL - 10, 10], [10, PL - 10], [PL - 10, PL - 10]]) {
        g.fillStyle = 'rgba(0,0,0,0.5)';
        g.beginPath(); g.arc(px + rx, py + ry, 2.6, 0, TAU); g.fill();
      }
    }
  }

  // --- sand, rust and grime: per-pixel fbm at reduced resolution ---
  const NS = 3;
  const nw = Math.ceil(W / NS), nh = Math.ceil(H / NS);
  const nc = makeCanvas(nw, nh);
  const nctx = nc.getContext('2d');
  const img = nctx.createImageData(nw, nh);
  const d = img.data;
  for (let y = 0; y < nh; y++) {
    for (let x = 0; x < nw; x++) {
      const i = (y * nw + x) * 4;
      const sand = fbm(x * 0.012, y * 0.012, 4, 3);
      const rust = fbm(x * 0.03, y * 0.03, 3, 11);
      const grain = hash(x, y, 9);
      const edge = clamp(Math.min(x, nw - x) / 60, 0, 1); // sand piles against the walls
      let sa = clamp((sand - 0.42) * 2.2 + (1 - edge) * 0.55, 0, 0.9);
      let r = 160, gg = 124, b = 86;
      if (rust > 0.6) { const k = (rust - 0.6) * 2.5; r = r * (1 - k) + 96 * k; gg = gg * (1 - k) + 40 * k; b = b * (1 - k) + 18 * k; sa = Math.max(sa, k * 0.6); }
      const dark = clamp((0.42 - sand) * 0.8, 0, 0.25);
      const gr = (grain - 0.5) * 26;
      d[i] = r * (1 - dark) + gr; d[i + 1] = gg * (1 - dark) + gr; d[i + 2] = b * (1 - dark) + gr;
      d[i + 3] = (0.4 + sa * 0.6) * 255;
    }
  }
  nctx.putImageData(img, 0, 0);
  g.imageSmoothingEnabled = true;
  g.drawImage(nc, 0, 0, W, H);

  // scattered stones, bolts and scrap
  for (let i = 0; i < 700; i++) {
    const x = rand(0, W), y = rand(0, H), s = rand(1, 3.5);
    g.fillStyle = pick(['rgba(30,22,16,0.7)', 'rgba(90,70,50,0.6)', 'rgba(160,130,100,0.35)']);
    g.fillRect(x, y, s, s * rand(0.6, 1.4));
  }
  // tyre tracks and drag marks
  g.strokeStyle = 'rgba(20,14,10,0.18)';
  for (let i = 0; i < 10; i++) {
    let x = rand(0, W), y = rand(0, H), a = rand(0, TAU);
    g.lineWidth = rand(10, 22);
    g.beginPath(); g.moveTo(x, y);
    for (let s = 0; s < 14; s++) { a += rand(-0.2, 0.2); x += Math.cos(a) * 40; y += Math.sin(a) * 40; g.lineTo(x, y); }
    g.stroke();
  }
  // old dried blood & oil
  for (let i = 0; i < 18; i++) {
    const x = rand(60, W - 60), y = rand(60, H - 60), r = rand(12, 40);
    g.fillStyle = pick(['rgba(50,10,6,0.35)', 'rgba(10,8,6,0.4)']);
    g.beginPath(); g.ellipse(x, y, r, r * rand(0.4, 0.8), rand(0, TAU), 0, TAU); g.fill();
  }
  // cracks
  g.strokeStyle = 'rgba(0,0,0,0.45)';
  for (let i = 0; i < 50; i++) {
    let x = rand(0, W), y = rand(0, H), a = rand(0, TAU);
    g.lineWidth = rand(0.8, 2);
    g.beginPath(); g.moveTo(x, y);
    for (let s = 0; s < 8; s++) { a += rand(-0.7, 0.7); x += Math.cos(a) * rand(6, 18); y += Math.sin(a) * rand(6, 18); g.lineTo(x, y); }
    g.stroke();
  }

  // --- worn paint markings ---
  const paint = makeCanvas(W, H);
  const p = paint.getContext('2d');
  p.strokeStyle = 'rgba(210,196,170,0.5)';
  p.lineWidth = 9;
  p.strokeRect(24, 24, W - 48, H - 48);
  p.beginPath(); p.moveTo(24, CY); p.lineTo(W - 24, CY); p.stroke();
  p.beginPath(); p.arc(CX, CY, 180, 0, TAU); p.stroke();
  for (const top of [true, false]) {
    const gy = top ? 0 : H;
    p.beginPath();
    if (top) p.arc(CX, gy, 320, 0, Math.PI); else p.arc(CX, gy, 320, Math.PI, TAU);
    p.stroke();
    // blood-red goal crease
    p.fillStyle = 'rgba(120,20,12,0.45)';
    p.beginPath();
    if (top) p.arc(CX, gy, 170, 0, Math.PI); else p.arc(CX, gy, 170, Math.PI, TAU);
    p.fill();
  }
  // Big stencilled lettering in each half
  p.save();
  p.font = '150px Display, Impact, sans-serif';
  p.textAlign = 'center';
  p.textBaseline = 'middle';
  p.fillStyle = 'rgba(200,180,150,0.08)';
  p.translate(CX, H * 0.25); p.fillText('KILL', 0, 0);
  p.translate(0, H * 0.5); p.rotate(Math.PI); p.fillText('KILL', 0, 0);
  p.restore();
  p.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 16000; i++) {
    p.fillStyle = `rgba(0,0,0,${rand(0.3, 1)})`;
    p.fillRect(rand(0, W), rand(0, H), rand(1, 8), rand(1, 5));
  }
  g.drawImage(paint, 0, 0);

  // center launcher hatch
  g.save();
  g.translate(CX, CY);
  g.fillStyle = '#120d0a';
  g.beginPath(); g.arc(0, 0, 56, 0, TAU); g.fill();
  const lg = g.createRadialGradient(-10, -10, 5, 0, 0, 50);
  lg.addColorStop(0, '#4a4038'); lg.addColorStop(1, '#1d1612');
  g.fillStyle = lg;
  g.beginPath(); g.arc(0, 0, 48, 0, TAU); g.fill();
  g.strokeStyle = '#0a0706'; g.lineWidth = 4;
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * TAU;
    g.beginPath(); g.moveTo(Math.cos(a) * 12, Math.sin(a) * 12); g.lineTo(Math.cos(a) * 44, Math.sin(a) * 44); g.stroke();
  }
  g.restore();

  // --- floodlight pools (baked) ---
  g.globalCompositeOperation = 'multiply';
  const edgeDark = g.createLinearGradient(0, 0, W, 0);
  edgeDark.addColorStop(0, '#6a5d55'); edgeDark.addColorStop(0.18, '#ffffff'); edgeDark.addColorStop(0.82, '#ffffff'); edgeDark.addColorStop(1, '#6a5d55');
  g.fillStyle = edgeDark;
  g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = 'source-over';
  g.globalCompositeOperation = 'lighter';
  for (const y of [H * 0.12, H * 0.37, H * 0.63, H * 0.88]) {
    const grd = g.createRadialGradient(CX, y, 0, CX, y, 620);
    grd.addColorStop(0, 'rgba(60,44,30,0.4)');
    grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd;
    g.fillRect(CX - 620, y - 620, 1240, 1240);
  }
  g.globalCompositeOperation = 'source-over';

  // --- goal pits ---
  for (const top of [true, false]) {
    const y0 = top ? -GOAL_DEPTH : H;
    g.fillStyle = '#050303';
    g.fillRect(CX - GOAL_HALF, y0, GOAL_HALF * 2, GOAL_DEPTH);
    g.strokeStyle = '#231b16';
    g.lineWidth = 3;
    for (let x = CX - GOAL_HALF; x <= CX + GOAL_HALF; x += 18) { g.beginPath(); g.moveTo(x, y0); g.lineTo(x, y0 + GOAL_DEPTH); g.stroke(); }
    for (let y = y0; y <= y0 + GOAL_DEPTH; y += 18) { g.beginPath(); g.moveTo(CX - GOAL_HALF, y); g.lineTo(CX + GOAL_HALF, y); g.stroke(); }
  }

  // --- stands ground & terraces ---
  g.fillStyle = '#0c0807';
  g.fillRect(-PAD_X, -PAD_TOP, PAD_X - LEDGE, floor.height);
  g.fillRect(W + LEDGE, -PAD_TOP, PAD_X, floor.height);
  g.fillRect(-PAD_X, -PAD_TOP, floor.width, PAD_TOP - TOP_WALL - 26);
  g.fillRect(-PAD_X, H + 50, floor.width, PAD_BOTTOM);
  g.fillStyle = 'rgba(70,52,40,0.28)';
  for (let x = -PAD_X + 20; x < -LEDGE - 20; x += 30) { g.fillRect(x, -PAD_TOP, 3, floor.height); g.fillRect(W + 2 * LEDGE - x - LEDGE, -PAD_TOP, 3, floor.height); }

  // --- walls ---
  drawTopWall(g);
  for (const left of [true, false]) drawSideLedge(g, left);
  drawBottomLedge(g);

  g.restore();
  buildCrowd();
  decalTiles.clear();
}

function metalGrad(g, x0, y0, x1, y1) {
  const grd = g.createLinearGradient(x0, y0, x1, y1);
  grd.addColorStop(0, '#2b211b'); grd.addColorStop(0.45, '#4d3e33'); grd.addColorStop(1, '#1d1612');
  return grd;
}

function grime(g, x, y, w, h, n) {
  for (let i = 0; i < n; i++) {
    g.fillStyle = `rgba(${rand(40, 110) | 0},${rand(15, 40) | 0},${rand(5, 15) | 0},${rand(0.08, 0.3)})`;
    g.fillRect(x + rand(0, w), y + rand(0, h), rand(2, 14), rand(2, 30));
  }
}

function spikesAlong(g, x0, y0, x1, y1, step) {
  const len = Math.hypot(x1 - x0, y1 - y0);
  const n = Math.floor(len / step);
  for (let i = 0; i <= n; i++) {
    const t = i / Math.max(1, n);
    const x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t;
    g.fillStyle = '#0c0907';
    g.beginPath(); g.moveTo(x - 6, y + 4); g.lineTo(x + 1, y - 20); g.lineTo(x + 6, y + 4); g.fill();
    g.fillStyle = '#7d736a';
    g.beginPath(); g.moveTo(x - 3, y + 2); g.lineTo(x, y - 16); g.lineTo(x + 1.5, y + 2); g.fill();
  }
}

function drawSideLedge(g, left) {
  const x = left ? -LEDGE : W;
  const y0 = -TOP_WALL, y1 = H + 50;
  g.fillStyle = metalGrad(g, x, 0, x + LEDGE, 0);
  g.fillRect(x, y0, LEDGE, y1 - y0);
  grime(g, x, y0, LEDGE, y1 - y0, 500);
  // riveted seams
  for (let y = y0; y < y1; y += 90) {
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillRect(x, y, LEDGE, 3);
    for (const rx of [8, LEDGE - 8]) { g.fillStyle = '#120d0a'; g.beginPath(); g.arc(x + rx, y + 10, 2.5, 0, TAU); g.fill(); }
  }
  // inner lip facing the pitch
  g.fillStyle = 'rgba(0,0,0,0.5)';
  g.fillRect(left ? -6 : W, y0, 6, y1 - y0);
  // star sockets
  for (const sy of STAR_YS) drawStarSocket(g, left ? -LEDGE / 2 : W + LEDGE / 2, sy);
  // multiplier ramp slot
  const rx = left ? -LEDGE + 8 : W + 8;
  g.fillStyle = '#060404';
  g.fillRect(rx, CY - RAMP_HALF, LEDGE - 16, RAMP_HALF * 2);
  g.strokeStyle = '#5b4a3c'; g.lineWidth = 3;
  g.strokeRect(rx, CY - RAMP_HALF, LEDGE - 16, RAMP_HALF * 2);
  // spikes on the outer edge
  const ox = left ? -LEDGE + 4 : W + LEDGE - 4;
  spikesAlong(g, ox, y0 + 20, ox, y1 - 10, 44);
}

function drawTopWall(g) {
  // ledge top
  g.fillStyle = metalGrad(g, 0, -TOP_WALL - 26, 0, -TOP_WALL);
  g.fillRect(-LEDGE, -TOP_WALL - 26, W + LEDGE * 2, 26);
  // face
  const fgr = g.createLinearGradient(0, -TOP_WALL, 0, 0);
  fgr.addColorStop(0, '#3d3129'); fgr.addColorStop(0.6, '#261d17'); fgr.addColorStop(1, '#120d0a');
  g.fillStyle = fgr;
  g.fillRect(-LEDGE, -TOP_WALL, W + LEDGE * 2, TOP_WALL);
  for (let x = -LEDGE; x < W + LEDGE; x += 130) {
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillRect(x, -TOP_WALL, 3, TOP_WALL);
    for (let k = 0; k < 3; k++) {
      const sx = x + rand(10, 120);
      const grd = g.createLinearGradient(0, -TOP_WALL, 0, -TOP_WALL + rand(30, 100));
      grd.addColorStop(0, 'rgba(120,45,15,0.55)'); grd.addColorStop(1, 'rgba(120,45,15,0)');
      g.fillStyle = grd;
      g.fillRect(sx, -TOP_WALL, rand(3, 9), 100);
    }
  }
  grime(g, -LEDGE, -TOP_WALL, W + LEDGE * 2, TOP_WALL, 600);
  // painted warning band at the base
  g.fillStyle = 'rgba(110,20,10,0.6)';
  g.fillRect(-LEDGE, -20, W + LEDGE * 2, 10);
  // goal gate carved into the face
  g.fillStyle = '#040202';
  g.fillRect(CX - GOAL_HALF, -TOP_WALL + 12, GOAL_HALF * 2, TOP_WALL - 12);
  g.strokeStyle = '#1e1712'; g.lineWidth = 3;
  for (let x = CX - GOAL_HALF; x <= CX + GOAL_HALF; x += 16) { g.beginPath(); g.moveTo(x, -TOP_WALL + 12); g.lineTo(x, 0); g.stroke(); }
  spikesAlong(g, -LEDGE + 10, -TOP_WALL - 22, W + LEDGE - 10, -TOP_WALL - 22, 34);
}

function drawBottomLedge(g) {
  for (const [x0, x1] of [[-LEDGE, CX - GOAL_HALF], [CX + GOAL_HALF, W + LEDGE]]) {
    g.fillStyle = metalGrad(g, 0, H, 0, H + 50);
    g.fillRect(x0, H, x1 - x0, 50);
    grime(g, x0, H, x1 - x0, 50, 200);
    g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x0, H, x1 - x0, 5);
    spikesAlong(g, x0 + 12, H + 40, x1 - 12, H + 40, 38);
  }
}

function drawStarSocket(g, x, y) {
  g.fillStyle = '#080605';
  g.beginPath(); g.arc(x, y, 22, 0, TAU); g.fill();
  g.strokeStyle = '#4e4035'; g.lineWidth = 3;
  g.beginPath(); g.arc(x, y, 22, 0, TAU); g.stroke();
  starPath(g, x, y, 15, 6.5);
  g.fillStyle = '#211a15';
  g.fill();
}

export function starPath(g, x, y, R, r) {
  g.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const rr = i % 2 ? r : R;
    g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  g.closePath();
}

// ---------- crowd: pre-rendered frames ----------
const CROWD_FRAMES = 4;
function buildCrowd() {
  torches.length = 0;
  const people = [];
  const add = (x, y, facing) => {
    if (Math.random() < 0.1) return;
    people.push({
      x: x + rand(-5, 5), y: y + rand(-3, 3), facing, ph: Math.floor(rand(0, CROWD_FRAMES)), amp: rand(1.5, 5),
      c: pick(['#2a201a', '#231b16', '#33271f', '#1c1714', '#3a2a1e', '#2b2622']), arms: Math.random() < 0.35,
      skin: pick(['#5a3e2c', '#6e4c36', '#3e2a1f', '#7a6a5c']), spike: Math.random() < 0.08,
    });
    if (Math.random() < 0.01) torches.push({ x, y: y - 14, ph: rand(0, TAU) });
  };
  for (let y = -PAD_TOP + 20; y < H + PAD_BOTTOM; y += 24) {
    for (let x = -PAD_X + 16; x < -LEDGE - 60; x += 22) add(x, y, 'side');
    for (let x = W + LEDGE + 60; x < W + PAD_X; x += 22) add(x, y, 'side');
  }
  for (let y = -PAD_TOP + 20; y < -TOP_WALL - 60; y += 24) for (let x = -LEDGE; x < W + LEDGE; x += 22) add(x, y, 'front');
  for (let y = H + 90; y < H + PAD_BOTTOM; y += 24) for (let x = -LEDGE; x < W + LEDGE; x += 22) add(x, y, 'back');
  people.sort((a, b) => a.y - b.y);

  const regions = {
    left: { x: -PAD_X, y: -PAD_TOP, w: PAD_X - LEDGE - 40, h: H + PAD_TOP + PAD_BOTTOM },
    right: { x: W + LEDGE + 40, y: -PAD_TOP, w: PAD_X - LEDGE - 40, h: H + PAD_TOP + PAD_BOTTOM },
    top: { x: -LEDGE - 40, y: -PAD_TOP, w: W + 2 * LEDGE + 80, h: PAD_TOP - TOP_WALL - 40 },
    bottom: { x: -LEDGE - 40, y: H + 60, w: W + 2 * LEDGE + 80, h: PAD_BOTTOM - 60 },
  };
  crowdFrames = [];
  for (let f = 0; f < CROWD_FRAMES; f++) {
    const frame = {};
    for (const [k, r] of Object.entries(regions)) {
      const c = makeCanvas(r.w, r.h);
      const g = c.getContext('2d');
      g.translate(-r.x, -r.y);
      for (const p of people) {
        if (p.x < r.x - 10 || p.x > r.x + r.w + 10 || p.y < r.y - 10 || p.y > r.y + r.h + 10) continue;
        const phase = ((f + p.ph) % CROWD_FRAMES) / CROWD_FRAMES;
        const bounce = Math.max(0, Math.sin(phase * TAU)) * p.amp;
        drawPerson(g, p, p.y - bounce, p.arms && phase < 0.5);
      }
      frame[k] = { c, r };
    }
    crowdFrames.push(frame);
  }
}

function drawPerson(g, p, y, armsUp) {
  const x = p.x;
  if (armsUp) {
    g.strokeStyle = p.skin; g.lineWidth = 3; g.lineCap = 'round';
    g.beginPath(); g.moveTo(x - 7, y + 2); g.lineTo(x - 10, y - 14); g.moveTo(x + 7, y + 2); g.lineTo(x + 11, y - 13); g.stroke();
  }
  g.fillStyle = p.c;
  g.beginPath(); g.ellipse(x, y + 7, 10, 7, 0, 0, TAU); g.fill();
  g.fillStyle = p.facing === 'back' ? '#140f0c' : p.skin;
  g.beginPath(); g.arc(x, y - 2, 5.5, 0, TAU); g.fill();
  // hoods, masks and spikes: faces mostly hidden
  g.fillStyle = 'rgba(10,8,6,0.75)';
  g.beginPath(); g.arc(x, y - 4, 5.8, Math.PI, TAU); g.fill();
  if (p.spike) { g.fillStyle = '#6b625a'; g.beginPath(); g.moveTo(x - 2, y - 8); g.lineTo(x, y - 17); g.lineTo(x + 2, y - 8); g.fill(); }
  // warm rim light from the fires
  g.fillStyle = 'rgba(255,140,60,0.18)';
  g.beginPath(); g.ellipse(x - 2, y + 3, 7, 3, 0, 0, Math.PI, true); g.fill();
}

export function drawCrowd(ctx, view, time, excitement, dt) {
  crowdClock += dt * (2 + excitement * 10);
  if (crowdClock >= 1) { crowdClock %= 1; crowdFrame = (crowdFrame + 1) % CROWD_FRAMES; }
  const frame = crowdFrames[crowdFrame];
  for (const k in frame) {
    const { c, r } = frame[k];
    const x0 = Math.max(r.x, view.x0), y0 = Math.max(r.y, view.y0);
    const x1 = Math.min(r.x + r.w, view.x1), y1 = Math.min(r.y + r.h, view.y1);
    if (x1 <= x0 || y1 <= y0) continue;
    ctx.drawImage(c, x0 - r.x, y0 - r.y, x1 - x0, y1 - y0, x0, y0, x1 - x0, y1 - y0);
  }
  for (const tch of torches) {
    if (tch.x < view.x0 - 20 || tch.x > view.x1 + 20 || tch.y < view.y0 - 40 || tch.y > view.y1 + 40) continue;
    ctx.strokeStyle = '#2a1e14'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(tch.x, tch.y + 14); ctx.lineTo(tch.x, tch.y - 8); ctx.stroke();
    if (Math.random() < dt * 20) fx.fire(tch.x, tch.y + 8, 0, 1, 9, 2);
  }
}

export function drawFloor(ctx, view) {
  const sx = clamp(view.x0 + PAD_X, 0, floor.width), sy = clamp(view.y0 + PAD_TOP, 0, floor.height);
  const ex = clamp(view.x1 + PAD_X, 0, floor.width), ey = clamp(view.y1 + PAD_TOP, 0, floor.height);
  if (ex <= sx || ey <= sy) return;
  ctx.drawImage(floor, sx, sy, ex - sx, ey - sy, sx - PAD_X, sy - PAD_TOP, ex - sx, ey - sy);
  flushDecals();
  // Decal tiles (only the ones that ever received a decal exist).
  const tx0 = Math.floor(view.x0 / TILE), tx1 = Math.floor(view.x1 / TILE);
  const ty0 = Math.floor(view.y0 / TILE), ty1 = Math.floor(view.y1 / TILE);
  for (let ty = ty0; ty <= ty1; ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      const tile = decalTiles.get(tx + ',' + ty);
      if (tile) ctx.drawImage(tile.c, tx * TILE, ty * TILE);
    }
  }
}

/** Additive light from the fire barrels and torches. */
export function drawLights(ctx, view, time) {
  ctx.globalCompositeOperation = 'lighter';
  const light = glowSprite('rgba(255,110,40,1)', 128);
  for (const b of barrels) {
    if (b.x < view.x0 - 300 || b.x > view.x1 + 300 || b.y < view.y0 - 300 || b.y > view.y1 + 300) continue;
    const f = 0.8 + Math.sin(time * 13 + b.y) * 0.08 + Math.sin(time * 29 + b.x) * 0.06;
    ctx.globalAlpha = 0.3 * f;
    const s = 520 * f;
    ctx.drawImage(light, b.x - s / 2, b.y - 50 - s / 2, s, s);
  }
  for (const tch of torches) {
    if (tch.x < view.x0 - 150 || tch.x > view.x1 + 150 || tch.y < view.y0 - 150 || tch.y > view.y1 + 150) continue;
    ctx.globalAlpha = 0.16 + Math.sin(time * 17 + tch.ph) * 0.05;
    ctx.drawImage(light, tch.x - 80, tch.y - 80, 160, 160);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}

export function barrelSprites(list, view, time) {
  for (const b of barrels) {
    if (b.x < view.x0 - 60 || b.x > view.x1 + 60 || b.y < view.y0 - 60 || b.y > view.y1 + 120) continue;
    list.push({ y: b.y, draw: (ctx) => drawBarrel(ctx, b, time) });
  }
}

function drawBarrel(ctx, b, time) {
  ctx.save();
  ctx.translate(b.x, b.y);
  ctx.fillStyle = 'rgba(0,0,0,0.5)';
  ctx.beginPath(); ctx.ellipse(4, 2, 26, 11, 0, 0, TAU); ctx.fill();
  const grd = ctx.createLinearGradient(-20, 0, 20, 0);
  grd.addColorStop(0, '#1a100b'); grd.addColorStop(0.4, '#5a2c16'); grd.addColorStop(0.7, '#3a1c0f'); grd.addColorStop(1, '#140c08');
  ctx.fillStyle = grd;
  ctx.fillRect(-20, -56, 40, 56);
  ctx.fillStyle = 'rgba(0,0,0,0.45)';
  ctx.fillRect(-20, -44, 40, 4); ctx.fillRect(-20, -18, 40, 4);
  ctx.fillStyle = '#0a0605';
  ctx.beginPath(); ctx.ellipse(0, -56, 20, 8, 0, 0, TAU); ctx.fill();
  ctx.fillStyle = `rgba(255,${120 + Math.sin(time * 20 + b.y) * 40},30,0.9)`;
  ctx.beginPath(); ctx.ellipse(0, -56, 15, 5.5, 0, 0, TAU); ctx.fill();
  ctx.restore();
}

export function emitBarrelFire(view, dt) {
  for (const b of barrels) {
    if (b.x < view.x0 - 200 || b.x > view.x1 + 200 || b.y < view.y0 - 200 || b.y > view.y1 + 300) continue;
    if (Math.random() < dt * 60) fx.fire(b.x, b.y, 56, 2, 22, 10);
    if (Math.random() < dt * 15) fx.embers(b.x, b.y, 64, 1);
    if (Math.random() < dt * 4) fx.smoke(b.x, b.y, 95, 1, 30);
  }
}

// ---------- decals (tiled) ----------
function tileFor(tx, ty) {
  const key = tx + ',' + ty;
  let t = decalTiles.get(key);
  if (!t) { const c = makeCanvas(TILE, TILE); t = { c, g: c.getContext('2d') }; decalTiles.set(key, t); }
  return t;
}

function stamp(x, y, r, draw) {
  const tx0 = Math.floor((x - r) / TILE), tx1 = Math.floor((x + r) / TILE);
  const ty0 = Math.floor((y - r) / TILE), ty1 = Math.floor((y + r) / TILE);
  for (let ty = ty0; ty <= ty1; ty++) {
    for (let tx = tx0; tx <= tx1; tx++) {
      const t = tileFor(tx, ty);
      t.g.save();
      t.g.translate(-tx * TILE, -ty * TILE);
      draw(t.g);
      t.g.restore();
    }
  }
}

function flushDecals() {
  if (!fx.decals.length) return;
  for (const d of fx.decals) {
    if (d.x < -GOAL_DEPTH || d.x > W + GOAL_DEPTH || d.y < -GOAL_DEPTH || d.y > H + GOAL_DEPTH) continue;
    switch (d.type) {
      case 'blood': {
        const col = `rgba(${70 + rand(0, 40) | 0},${rand(2, 8) | 0},${rand(2, 6) | 0},${rand(0.6, 0.9)})`;
        const rot = rand(0, TAU), sq = rand(0.5, 0.9);
        stamp(d.x, d.y, d.r * 1.5, (g) => {
          g.fillStyle = col;
          g.beginPath(); g.ellipse(d.x, d.y, d.r, d.r * sq, rot, 0, TAU); g.fill();
        });
        break;
      }
      case 'splat': {
        // Directional spray: a smeared impact plus droplets thrown along the hit direction.
        const ang = Math.atan2(d.dy || 0, d.dx || 1);
        const drops = [];
        for (let i = 0; i < 14; i++) {
          const a = ang + rand(-0.5, 0.5);
          const l = rand(0.4, 2.2) * d.r;
          drops.push({ x: d.x + Math.cos(a) * l, y: d.y + Math.sin(a) * l, r: rand(1, 4.5) * (1.3 - l / (2.4 * d.r)), a });
        }
        stamp(d.x, d.y, d.r * 2.6, (g) => {
          g.fillStyle = 'rgba(80,5,3,0.75)';
          g.beginPath(); g.ellipse(d.x, d.y, d.r * 0.8, d.r * 0.35, ang, 0, TAU); g.fill();
          g.fillStyle = 'rgba(95,8,4,0.85)';
          for (const p of drops) { g.beginPath(); g.ellipse(p.x, p.y, p.r * 1.6, p.r, p.a, 0, TAU); g.fill(); }
        });
        break;
      }
      case 'pool':
        stamp(d.x, d.y, d.r * 1.3, (g) => {
          const grd = g.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);
          grd.addColorStop(0, 'rgba(60,2,2,0.9)'); grd.addColorStop(0.75, 'rgba(80,6,4,0.8)'); grd.addColorStop(1, 'rgba(80,6,4,0)');
          g.fillStyle = grd;
          g.beginPath(); g.ellipse(d.x, d.y, d.r * 1.2, d.r * 0.8, rand(0, TAU), 0, TAU); g.fill();
        });
        break;
      case 'scorch':
        stamp(d.x, d.y, d.r, (g) => {
          const grd = g.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);
          grd.addColorStop(0, 'rgba(0,0,0,0.75)'); grd.addColorStop(0.6, 'rgba(15,8,4,0.4)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
          g.fillStyle = grd;
          g.beginPath(); g.ellipse(d.x, d.y, d.r, d.r * 0.7, 0, 0, TAU); g.fill();
        });
        break;
      case 'skid': {
        const r = Math.hypot(d.x2 - d.x, d.y2 - d.y);
        stamp((d.x + d.x2) / 2, (d.y + d.y2) / 2, r / 2 + 10, (g) => {
          g.strokeStyle = 'rgba(12,8,6,0.3)';
          g.lineWidth = d.w || 10;
          g.lineCap = 'round';
          g.beginPath(); g.moveTo(d.x, d.y); g.lineTo(d.x2, d.y2); g.stroke();
        });
        break;
      }
      case 'burn':
        stamp(d.x, d.y, d.r, (g) => {
          g.fillStyle = 'rgba(10,20,30,0.3)';
          g.beginPath(); g.arc(d.x, d.y, d.r, 0, TAU); g.fill();
        });
        break;
    }
  }
  fx.decals.length = 0;
}
