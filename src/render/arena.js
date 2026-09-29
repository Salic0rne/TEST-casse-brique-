// Arena: baked rusted-steel floor (with persistent decals), walls, crowd, and animated furniture.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, BUMPERS, ELECTRO, STAR_XS, RAMP_HALF, RAMP_DEPTH, TEAMS } from '../game/constants.js';
import { rand, pick, TAU, fbm, hash, makeCanvas, clamp } from '../core/math.js';
import { fx, glowSprite } from './fx.js';

export const PAD_X = 300;
export const PAD_TOP = 330;
export const PAD_BOTTOM = 260;
const TOP_WALL = 96; // visible height of the top wall face

let floor, fctx;
let crowd = [];
let crowdSprites = [];
export const barrels = [
  { x: -95, y: -150 }, { x: W + 95, y: -150 }, { x: -95, y: H + 70 }, { x: W + 95, y: H + 70 },
  { x: CX - 520, y: -150 }, { x: CX + 520, y: -150 }, { x: -95, y: CY - 330 }, { x: -95, y: CY + 330 },
  { x: W + 95, y: CY - 330 }, { x: W + 95, y: CY + 330 },
];
// Torches held up in the crowd — flickering light sources.
const torches = [];

export function arenaBounds() {
  return { x0: -PAD_X, y0: -PAD_TOP, x1: W + PAD_X, y1: H + PAD_BOTTOM };
}

export function buildArena() {
  floor = makeCanvas(W + PAD_X * 2, H + PAD_TOP + PAD_BOTTOM);
  fctx = floor.getContext('2d');
  const g = fctx;
  g.save();
  g.translate(PAD_X, PAD_TOP);

  // --- outer ground (dirt / stands base) ---
  g.fillStyle = '#140d0a';
  g.fillRect(-PAD_X, -PAD_TOP, floor.width, floor.height);

  // --- field base: riveted steel plates ---
  const PL = 160;
  for (let py = 0; py < H; py += PL / 2) {
    for (let px = 0; px < W; px += PL) {
      const off = (py / (PL / 2)) % 2 ? PL / 2 : 0;
      const x = px - off, y = py;
      const v = hash(px, py, 3);
      const r = 58 + v * 16, gg = 44 + v * 10, b = 36 + v * 8;
      g.fillStyle = `rgb(${r | 0},${gg | 0},${b | 0})`;
      g.fillRect(x, y, PL, PL / 2);
      // bevel
      g.fillStyle = 'rgba(255,220,180,0.06)';
      g.fillRect(x, y, PL, 2);
      g.fillStyle = 'rgba(0,0,0,0.45)';
      g.fillRect(x, y + PL / 2 - 2, PL, 2);
      g.fillRect(x + PL - 2, y, 2, PL / 2);
      // rivets
      for (const [rx, ry] of [[8, 8], [PL - 8, 8], [8, PL / 2 - 8], [PL - 8, PL / 2 - 8]]) {
        g.fillStyle = '#1d1512';
        g.beginPath(); g.arc(x + rx, y + ry, 3.2, 0, TAU); g.fill();
        g.fillStyle = 'rgba(255,210,160,0.25)';
        g.beginPath(); g.arc(x + rx - 0.8, y + ry - 0.8, 1.4, 0, TAU); g.fill();
      }
      // tread pattern on some plates
      if (v > 0.72) {
        g.strokeStyle = 'rgba(0,0,0,0.18)';
        g.lineWidth = 3;
        for (let i = 0; i < 6; i++) for (let j = 0; j < 3; j++) {
          const cx = x + 20 + i * 24, cy = y + 16 + j * 24;
          g.beginPath();
          if ((i + j) % 2) { g.moveTo(cx - 6, cy - 3); g.lineTo(cx + 6, cy + 3); } else { g.moveTo(cx - 6, cy + 3); g.lineTo(cx + 6, cy - 3); }
          g.stroke();
        }
      }
    }
  }

  // --- rust & grime from low-res fbm noise, scaled up ---
  const NS = 6;
  const nw = Math.ceil(W / NS), nh = Math.ceil(H / NS);
  const nc = makeCanvas(nw, nh);
  const nctx = nc.getContext('2d');
  const img = nctx.createImageData(nw, nh);
  for (let y = 0; y < nh; y++) {
    for (let x = 0; x < nw; x++) {
      const i = (y * nw + x) * 4;
      const rust = fbm(x * 0.035, y * 0.035, 4, 1);
      const grime = fbm(x * 0.012, y * 0.012, 3, 7);
      const edge = Math.min(x, y, nw - x, nh - y) / 40; // dirt accumulates at walls
      let a = 0, r = 0, gg = 0, b = 0;
      if (rust > 0.56) { r = 150; gg = 64; b = 22; a = (rust - 0.56) * 2.2; }
      const dark = clamp((0.62 - grime) * 1.1 + (1 - clamp(edge, 0, 1)) * 0.35, 0, 0.7);
      // blend: rust over dark grime
      const da = dark;
      const outA = a + da * (1 - a);
      if (outA > 0) {
        r = (r * a + 20 * da * (1 - a)) / outA;
        gg = (gg * a + 14 * da * (1 - a)) / outA;
        b = (b * a + 10 * da * (1 - a)) / outA;
      }
      img.data[i] = r; img.data[i + 1] = gg; img.data[i + 2] = b; img.data[i + 3] = clamp(outA, 0, 0.85) * 255;
    }
  }
  nctx.putImageData(img, 0, 0);
  g.imageSmoothingEnabled = true;
  g.drawImage(nc, 0, 0, W, H);

  // sand drifts along walls
  const sand = (x0, y0, x1, y1) => {
    const grd = g.createLinearGradient(x0, y0, x1, y1);
    grd.addColorStop(0, 'rgba(150,110,70,0.45)');
    grd.addColorStop(1, 'rgba(150,110,70,0)');
    g.fillStyle = grd;
    g.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0) || W, Math.abs(y1 - y0) || H);
  };
  sand(0, 0, 0, 60); sand(0, H, 0, H - 60);
  for (let i = 0; i < 220; i++) {
    g.fillStyle = `rgba(${140 + rand(0, 40)},${100 + rand(0, 30)},${60 + rand(0, 20)},${rand(0.05, 0.18)})`;
    const x = rand(0, W), y = pick([rand(0, 90), rand(H - 90, H), rand(0, H)]);
    g.beginPath(); g.ellipse(x, y, rand(10, 60), rand(4, 18), rand(-0.3, 0.3), 0, TAU); g.fill();
  }

  // oil stains with iridescent sheen
  for (let i = 0; i < 12; i++) {
    const x = rand(80, W - 80), y = rand(60, H - 60), r = rand(20, 60);
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    grd.addColorStop(0, 'rgba(8,6,6,0.5)');
    grd.addColorStop(0.7, 'rgba(10,8,12,0.32)');
    grd.addColorStop(0.85, 'rgba(60,40,90,0.18)');
    grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd;
    g.beginPath(); g.ellipse(x, y, r, r * rand(0.5, 0.9), rand(0, TAU), 0, TAU); g.fill();
  }

  // cracks
  g.strokeStyle = 'rgba(0,0,0,0.5)';
  for (let i = 0; i < 40; i++) {
    let x = rand(0, W), y = rand(0, H), a = rand(0, TAU);
    g.lineWidth = rand(1, 2.5);
    g.beginPath(); g.moveTo(x, y);
    for (let s = 0; s < 8; s++) { a += rand(-0.7, 0.7); x += Math.cos(a) * rand(8, 22); y += Math.sin(a) * rand(8, 22); g.lineTo(x, y); }
    g.stroke();
  }

  // --- painted markings (worn) ---
  const paint = document.createElement('canvas');
  paint.width = W; paint.height = H;
  const p = paint.getContext('2d');
  p.strokeStyle = 'rgba(230,215,180,0.55)';
  p.lineWidth = 10;
  p.strokeRect(20, 20, W - 40, H - 40);
  p.beginPath(); p.moveTo(CX, 20); p.lineTo(CX, H - 20); p.stroke();
  p.beginPath(); p.arc(CX, CY, 170, 0, TAU); p.stroke();
  p.lineWidth = 8;
  for (const side of [0, 1]) {
    const gx = side ? W : 0, dir = side ? -1 : 1;
    p.beginPath();
    if (side) p.arc(gx, CY, 290, Math.PI / 2, Math.PI * 1.5); else p.arc(gx, CY, 290, -Math.PI / 2, Math.PI / 2);
    p.stroke();
    // hazard stripes in the goal crease
    p.save();
    p.beginPath();
    if (side) p.arc(gx, CY, 150, Math.PI / 2, Math.PI * 1.5); else p.arc(gx, CY, 150, -Math.PI / 2, Math.PI / 2);
    p.closePath();
    p.clip();
    for (let k = -300; k < 300; k += 36) {
      p.fillStyle = 'rgba(230,170,20,0.5)';
      p.beginPath();
      p.moveTo(gx + k * dir, CY - 200); p.lineTo(gx + (k + 18) * dir, CY - 200);
      p.lineTo(gx + (k + 18 + 200) * dir, CY + 200); p.lineTo(gx + (k + 200) * dir, CY + 200);
      p.fill();
    }
    p.restore();
    // skulls painted at center of each half
    p.save();
    p.translate(side ? W * 0.75 : W * 0.25, CY);
    p.globalAlpha = 0.16;
    drawSkullIcon(p, 110, '#e8dcc0');
    p.restore();
  }
  // Erode the paint with noise
  p.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 9000; i++) {
    p.fillStyle = `rgba(0,0,0,${rand(0.3, 1)})`;
    p.beginPath(); p.arc(rand(0, W), rand(0, H), rand(1, 7), 0, TAU); p.fill();
  }
  g.drawImage(paint, 0, 0);

  // center launcher hatch
  g.save();
  g.translate(CX, CY);
  g.fillStyle = '#1a1310';
  g.beginPath(); g.arc(0, 0, 58, 0, TAU); g.fill();
  const lg = g.createRadialGradient(0, 0, 10, 0, 0, 56);
  lg.addColorStop(0, '#50443c'); lg.addColorStop(1, '#231b16');
  g.fillStyle = lg;
  g.beginPath(); g.arc(0, 0, 50, 0, TAU); g.fill();
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * TAU;
    g.fillStyle = '#0e0a08';
    g.beginPath(); g.arc(Math.cos(a) * 42, Math.sin(a) * 42, 3.5, 0, TAU); g.fill();
  }
  g.strokeStyle = '#0c0907'; g.lineWidth = 4;
  for (let i = 0; i < 6; i++) {
    const a = (i / 6) * TAU;
    g.beginPath(); g.moveTo(0, 0); g.lineTo(Math.cos(a) * 34, Math.sin(a) * 34); g.stroke();
  }
  g.restore();

  // bumper & electro bases
  for (const b of BUMPERS) {
    g.fillStyle = 'rgba(0,0,0,0.5)';
    g.beginPath(); g.ellipse(b.x, b.y + 6, b.r + 16, (b.r + 16) * 0.75, 0, 0, TAU); g.fill();
    g.fillStyle = '#2b221d';
    g.beginPath(); g.ellipse(b.x, b.y, b.r + 12, (b.r + 12) * 0.7, 0, 0, TAU); g.fill();
  }
  for (const e of ELECTRO) {
    g.fillStyle = '#161616';
    g.beginPath(); g.arc(e.x, e.y, e.r + 22, 0, TAU); g.fill();
    for (let k = 0; k < 16; k++) {
      g.fillStyle = k % 2 ? '#d8a410' : '#141414';
      g.beginPath(); g.moveTo(e.x, e.y);
      g.arc(e.x, e.y, e.r + 20, (k / 16) * TAU, ((k + 1) / 16) * TAU); g.fill();
    }
    g.fillStyle = '#211d1b';
    g.beginPath(); g.arc(e.x, e.y, e.r + 6, 0, TAU); g.fill();
  }

  // --- lighting bake: floodlight pools and dark edges ---
  const pools = [[W * 0.25, CY], [W * 0.75, CY], [CX, CY]];
  g.globalCompositeOperation = 'multiply';
  const dark = g.createLinearGradient(0, -PAD_TOP, 0, H + PAD_BOTTOM);
  dark.addColorStop(0, '#6c5d56'); dark.addColorStop(0.3, '#ffffff'); dark.addColorStop(0.7, '#ffffff'); dark.addColorStop(1, '#6c5d56');
  g.fillStyle = dark;
  g.fillRect(-PAD_X, -PAD_TOP, floor.width, floor.height);
  g.globalCompositeOperation = 'lighter';
  for (const [x, y] of pools) {
    const grd = g.createRadialGradient(x, y, 0, x, y, 720);
    grd.addColorStop(0, 'rgba(70,52,34,0.35)');
    grd.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grd;
    g.fillRect(x - 720, y - 720, 1440, 1440);
  }
  g.globalCompositeOperation = 'source-over';

  // --- goals (pits) ---
  for (const side of [0, 1]) {
    const x0 = side ? W : -GOAL_DEPTH - 10;
    g.fillStyle = '#060404';
    g.fillRect(x0, CY - GOAL_HALF, GOAL_DEPTH + 10, GOAL_HALF * 2);
    // grating
    g.strokeStyle = '#2a211c';
    g.lineWidth = 3;
    for (let yy = CY - GOAL_HALF; yy <= CY + GOAL_HALF; yy += 16) {
      g.beginPath(); g.moveTo(x0, yy); g.lineTo(x0 + GOAL_DEPTH + 10, yy); g.stroke();
    }
    for (let xx = x0; xx <= x0 + GOAL_DEPTH + 10; xx += 16) {
      g.beginPath(); g.moveTo(xx, CY - GOAL_HALF); g.lineTo(xx, CY + GOAL_HALF); g.stroke();
    }
  }

  // --- side walls (seen from above) ---
  for (const side of [0, 1]) {
    const x = side ? W : -54;
    for (const [y0, y1] of [[-TOP_WALL, CY - GOAL_HALF], [CY + GOAL_HALF, H + 40]]) {
      drawWallTop(g, x, y0, 54, y1 - y0, true);
    }
  }
  // bottom ledge
  drawWallTop(g, -54, H, W + 108, 44, false);
  // top wall face
  drawTopWall(g);

  // --- stands ground ---
  g.fillStyle = '#0f0a08';
  g.fillRect(-PAD_X, -PAD_TOP, floor.width, PAD_TOP - TOP_WALL - 22);
  g.fillRect(-PAD_X, H + 44, floor.width, PAD_BOTTOM);
  g.fillRect(-PAD_X, -PAD_TOP, PAD_X - 90, floor.height);
  g.fillRect(W + 90, -PAD_TOP, PAD_X, floor.height);
  // terraces
  for (let yy = -PAD_TOP + 10; yy < -TOP_WALL - 30; yy += 28) {
    g.fillStyle = 'rgba(80,60,48,0.25)'; g.fillRect(-PAD_X, yy, floor.width, 3);
  }
  for (let yy = H + 60; yy < H + PAD_BOTTOM; yy += 28) {
    g.fillStyle = 'rgba(80,60,48,0.25)'; g.fillRect(-PAD_X, yy, floor.width, 3);
  }
  // chain-link fence top of stands
  g.strokeStyle = 'rgba(120,110,100,0.25)';
  g.lineWidth = 1;
  for (let x = -PAD_X; x < W + PAD_X; x += 12) {
    g.beginPath(); g.moveTo(x, -TOP_WALL - 22); g.lineTo(x + 12, -TOP_WALL - 44); g.stroke();
    g.beginPath(); g.moveTo(x + 12, -TOP_WALL - 22); g.lineTo(x, -TOP_WALL - 44); g.stroke();
  }

  g.restore();
  buildCrowd();
}

function drawSkullIcon(p, s, col) {
  p.fillStyle = col;
  p.beginPath();
  p.arc(0, -s * 0.12, s * 0.42, 0, TAU);
  p.fill();
  p.fillRect(-s * 0.26, s * 0.1, s * 0.52, s * 0.3);
  p.globalCompositeOperation = 'destination-out';
  p.beginPath(); p.arc(-s * 0.16, -s * 0.1, s * 0.12, 0, TAU); p.arc(s * 0.16, -s * 0.1, s * 0.12, 0, TAU); p.fill();
  p.beginPath(); p.moveTo(0, s * 0.02); p.lineTo(-s * 0.06, s * 0.14); p.lineTo(s * 0.06, s * 0.14); p.fill();
  for (let i = -2; i <= 2; i++) p.fillRect(i * s * 0.09 - s * 0.02, s * 0.28, s * 0.04, s * 0.14);
  p.globalCompositeOperation = 'source-over';
  // crossed bones
  p.strokeStyle = col; p.lineWidth = s * 0.1; p.lineCap = 'round';
  p.beginPath(); p.moveTo(-s * 0.6, s * 0.35); p.lineTo(s * 0.6, s * 0.75); p.moveTo(s * 0.6, s * 0.35); p.lineTo(-s * 0.6, s * 0.75); p.stroke();
}

function drawWallTop(g, x, y, w, h, vertical) {
  const grd = vertical ? g.createLinearGradient(x, 0, x + w, 0) : g.createLinearGradient(0, y, 0, y + h);
  grd.addColorStop(0, '#3d3029'); grd.addColorStop(0.5, '#5a4638'); grd.addColorStop(1, '#2a1f19');
  g.fillStyle = grd;
  g.fillRect(x, y, w, h);
  // hazard stripe band
  g.save();
  g.beginPath(); g.rect(x, y, w, h); g.clip();
  const band = vertical ? { x: x + w * 0.3, y, w: w * 0.4, h } : { x, y: y + h * 0.3, w, h: h * 0.4 };
  g.fillStyle = '#16100c'; g.fillRect(band.x, band.y, band.w, band.h);
  g.fillStyle = 'rgba(214,160,20,0.8)';
  const L = vertical ? h : w;
  for (let k = -40; k < L + 40; k += 28) {
    g.beginPath();
    if (vertical) {
      g.moveTo(band.x, y + k); g.lineTo(band.x + band.w, y + k + band.w); g.lineTo(band.x + band.w, y + k + band.w + 13); g.lineTo(band.x, y + k + 13);
    } else {
      g.moveTo(x + k, band.y); g.lineTo(x + k + 13, band.y); g.lineTo(x + k + 13 + band.h, band.y + band.h); g.lineTo(x + k + band.h, band.y + band.h);
    }
    g.fill();
  }
  // grime
  for (let i = 0; i < (w * h) / 300; i++) {
    g.fillStyle = `rgba(${rand(0, 60)},${rand(0, 30)},0,${rand(0.05, 0.25)})`;
    g.fillRect(x + rand(0, w), y + rand(0, h), rand(2, 10), rand(2, 10));
  }
  g.restore();
  // spikes
  g.fillStyle = '#8c8279';
  const n = Math.floor((vertical ? h : w) / 46);
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n;
    const sx = vertical ? x + w / 2 : x + t * w, sy = vertical ? y + t * h : y + h / 2;
    g.fillStyle = '#1a1411';
    g.beginPath(); g.arc(sx, sy, 7, 0, TAU); g.fill();
    g.fillStyle = '#9d948a';
    g.beginPath(); g.arc(sx, sy, 5, 0, TAU); g.fill();
    g.fillStyle = '#e2dbd2';
    g.beginPath(); g.arc(sx - 1.5, sy - 1.5, 1.8, 0, TAU); g.fill();
  }
  g.strokeStyle = 'rgba(0,0,0,0.6)'; g.lineWidth = 2;
  g.strokeRect(x + 1, y + 1, w - 2, h - 2);
}

function drawTopWall(g) {
  const y0 = -TOP_WALL - 22;
  // top ledge
  const lg = g.createLinearGradient(0, y0, 0, y0 + 22);
  lg.addColorStop(0, '#6b5646'); lg.addColorStop(1, '#3b2e25');
  g.fillStyle = lg;
  g.fillRect(-54, y0, W + 108, 22);
  // face
  const fg = g.createLinearGradient(0, -TOP_WALL, 0, 0);
  fg.addColorStop(0, '#4a3b31'); fg.addColorStop(0.5, '#33271f'); fg.addColorStop(1, '#1a130f');
  g.fillStyle = fg;
  g.fillRect(-54, -TOP_WALL, W + 108, TOP_WALL);
  // panels
  for (let x = -54; x < W + 54; x += 120) {
    g.fillStyle = `rgba(${hash(x, 1) * 60 | 0},${hash(x, 2) * 25 | 0},0,0.18)`;
    g.fillRect(x + 3, -TOP_WALL + 4, 114, TOP_WALL - 8);
    g.fillStyle = 'rgba(0,0,0,0.5)';
    g.fillRect(x, -TOP_WALL, 3, TOP_WALL);
    for (const ry of [-TOP_WALL + 10, -12]) {
      for (const rx of [10, 110]) {
        g.fillStyle = '#16100d'; g.beginPath(); g.arc(x + rx, ry, 3, 0, TAU); g.fill();
        g.fillStyle = 'rgba(255,220,180,0.3)'; g.beginPath(); g.arc(x + rx - 1, ry - 1, 1.2, 0, TAU); g.fill();
      }
    }
    // rust streaks running down
    for (let k = 0; k < 3; k++) {
      const sx = x + rand(10, 110);
      const grd = g.createLinearGradient(0, -TOP_WALL, 0, -TOP_WALL + rand(30, 90));
      grd.addColorStop(0, 'rgba(150,60,20,0.5)'); grd.addColorStop(1, 'rgba(150,60,20,0)');
      g.fillStyle = grd;
      g.fillRect(sx, -TOP_WALL, rand(3, 9), 90);
    }
  }
  // hazard stripe at the base of the wall
  g.save();
  g.beginPath(); g.rect(-54, -16, W + 108, 12); g.clip();
  g.fillStyle = '#120c09'; g.fillRect(-54, -16, W + 108, 12);
  g.fillStyle = 'rgba(214,160,20,0.85)';
  for (let x = -60; x < W + 60; x += 26) { g.beginPath(); g.moveTo(x, -16); g.lineTo(x + 12, -16); g.lineTo(x + 24, -4); g.lineTo(x + 12, -4); g.fill(); }
  g.restore();
  // star sockets
  for (const sx of STAR_XS) drawStarSocket(g, sx, -TOP_WALL / 2 - 6);
  for (const sx of STAR_XS) drawStarSocket(g, sx, H + 22, 0.8);
  // ramp tunnels
  for (const top of [true, false]) {
    const y = top ? -TOP_WALL / 2 : H + 22;
    g.fillStyle = '#0a0706';
    g.fillRect(CX - RAMP_HALF, y - (top ? 36 : 18), RAMP_HALF * 2, top ? 60 : 36);
    g.strokeStyle = '#6a5a4c'; g.lineWidth = 4;
    g.strokeRect(CX - RAMP_HALF, y - (top ? 36 : 18), RAMP_HALF * 2, top ? 60 : 36);
  }
  // spikes along top ledge
  for (let x = -40; x < W + 50; x += 30) {
    g.fillStyle = '#1a1411';
    g.beginPath(); g.moveTo(x - 7, y0 + 6); g.lineTo(x, y0 - 22); g.lineTo(x + 7, y0 + 6); g.fill();
    g.fillStyle = '#a49b90';
    g.beginPath(); g.moveTo(x - 5, y0 + 4); g.lineTo(x, y0 - 18); g.lineTo(x + 2, y0 + 4); g.fill();
  }
}

function drawStarSocket(g, x, y, s = 1) {
  g.save();
  g.translate(x, y);
  g.scale(s, s);
  g.fillStyle = '#0d0907';
  g.beginPath(); g.arc(0, 0, 26, 0, TAU); g.fill();
  g.strokeStyle = '#7b6a5a'; g.lineWidth = 3;
  g.beginPath(); g.arc(0, 0, 26, 0, TAU); g.stroke();
  starPath(g, 0, 0, 18, 8);
  g.fillStyle = '#2a211c';
  g.fill();
  g.restore();
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

// ---------- crowd ----------
function makePerson(cloth, skin, pose) {
  const c = makeCanvas(28, 34);
  const g = c.getContext('2d');
  g.translate(14, 20);
  if (pose === 'back') {
    g.fillStyle = cloth;
    g.beginPath(); g.ellipse(0, 6, 11, 8, 0, 0, TAU); g.fill();
    g.fillStyle = '#1b120e';
    g.beginPath(); g.arc(0, -3, 6.5, 0, TAU); g.fill();
    return c;
  }
  if (pose === 'arms') {
    g.strokeStyle = skin; g.lineWidth = 3.5; g.lineCap = 'round';
    g.beginPath(); g.moveTo(-8, 2); g.lineTo(-12, -16); g.moveTo(8, 2); g.lineTo(12, -16); g.stroke();
  }
  g.fillStyle = cloth;
  g.beginPath(); g.ellipse(0, 7, 11, 8, 0, 0, TAU); g.fill();
  g.fillStyle = skin;
  g.beginPath(); g.arc(0, -3, 6, 0, TAU); g.fill();
  g.fillStyle = 'rgba(0,0,0,0.5)';
  g.fillRect(-4, -4, 8, 2);
  return c;
}

function buildCrowd() {
  crowd = [];
  torches.length = 0;
  const cloths = ['#4a3226', '#3a2c24', '#5b4030', '#2e2622', '#62352a', '#3c3a30', '#553b1e', '#2b3336'];
  const skins = ['#8a5c3c', '#b58660', '#6b4430', '#c79c7a'];
  crowdSprites = cloths.map((c, i) => ({
    front: makePerson(c, skins[i % 4], 'front'),
    arms: makePerson(c, skins[(i + 1) % 4], 'arms'),
    back: makePerson(c, skins[i % 4], 'back'),
  }));
  const add = (x, y, facing) => {
    if (Math.random() < 0.12) return;
    crowd.push({ x: x + rand(-5, 5), y: y + rand(-3, 3), v: Math.floor(rand(0, crowdSprites.length)), ph: rand(0, TAU), sp: rand(5, 9), facing, amp: rand(0.5, 1.3) });
    if (Math.random() < 0.012) torches.push({ x, y: y - 16, ph: rand(0, TAU) });
  };
  for (let y = -PAD_TOP + 30; y < -TOP_WALL - 50; y += 26) for (let x = -PAD_X + 10; x < W + PAD_X; x += 22) add(x, y, 'front');
  for (let y = H + 70; y < H + PAD_BOTTOM; y += 26) for (let x = -PAD_X + 10; x < W + PAD_X; x += 22) add(x, y, 'back');
  for (let y = -TOP_WALL; y < H + 50; y += 26) {
    for (let x = -PAD_X + 10; x < -110; x += 24) add(x, y, 'front');
    for (let x = W + 120; x < W + PAD_X; x += 24) add(x, y, 'front');
  }
  crowd.sort((a, b) => a.y - b.y);
}

export function drawFloor(ctx, view) {
  flushDecals();
  const sx = clamp(view.x0 + PAD_X, 0, floor.width), sy = clamp(view.y0 + PAD_TOP, 0, floor.height);
  const ex = clamp(view.x1 + PAD_X, 0, floor.width), ey = clamp(view.y1 + PAD_TOP, 0, floor.height);
  if (ex <= sx || ey <= sy) return;
  ctx.drawImage(floor, sx, sy, ex - sx, ey - sy, sx - PAD_X, sy - PAD_TOP, ex - sx, ey - sy);
}

export function drawCrowd(ctx, view, time, excitement) {
  const x0 = view.x0 - 30, x1 = view.x1 + 30, y0 = view.y0 - 40, y1 = view.y1 + 40;
  for (const p of crowd) {
    if (p.x < x0 || p.x > x1 || p.y < y0 || p.y > y1) continue;
    const bounce = Math.max(0, Math.sin(time * p.sp + p.ph)) * (1.5 + excitement * 6) * p.amp;
    const spr = crowdSprites[p.v];
    const img = p.facing === 'back' ? spr.back : excitement > 0.55 && Math.sin(p.ph * 3.1) > 0.1 - excitement * 0.3 ? spr.arms : spr.front;
    ctx.drawImage(img, p.x - 14, p.y - 20 - bounce);
  }
  // torch fires in the crowd
  for (const t of torches) {
    if (t.x < x0 || t.x > x1 || t.y < y0 || t.y > y1) continue;
    ctx.strokeStyle = '#3a2a1c'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(t.x, t.y + 14); ctx.lineTo(t.x, t.y - 8); ctx.stroke();
    if (Math.random() < 0.4) fx.fire(t.x, t.y + 8, 0, 1, 9, 2);
    if (Math.random() < 0.05) fx.embers(t.x, t.y + 8, 0, 1);
  }
}

/** Additive light sources baked into the scene each frame. */
export function drawLights(ctx, view, time) {
  ctx.globalCompositeOperation = 'lighter';
  const light = glowSprite('rgba(255,120,40,1)', 128);
  for (const b of barrels) {
    if (b.x < view.x0 - 300 || b.x > view.x1 + 300 || b.y < view.y0 - 300 || b.y > view.y1 + 300) continue;
    const f = 0.8 + Math.sin(time * 13 + b.x) * 0.08 + Math.sin(time * 29 + b.y) * 0.06;
    ctx.globalAlpha = 0.28 * f;
    const s = 460 * f;
    ctx.drawImage(light, b.x - s / 2, b.y - 40 - s / 2, s, s);
  }
  for (const t of torches) {
    if (t.x < view.x0 - 150 || t.x > view.x1 + 150 || t.y < view.y0 - 150 || t.y > view.y1 + 150) continue;
    ctx.globalAlpha = 0.18 + Math.sin(time * 17 + t.ph) * 0.05;
    ctx.drawImage(light, t.x - 90, t.y - 90, 180, 180);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = 'source-over';
}

export function barrelSprites(list, time) {
  for (const b of barrels) {
    list.push({
      y: b.y,
      draw: (ctx) => {
        ctx.save();
        ctx.translate(b.x, b.y);
        ctx.fillStyle = 'rgba(0,0,0,0.5)';
        ctx.beginPath(); ctx.ellipse(4, 2, 26, 11, 0, 0, TAU); ctx.fill();
        const grd = ctx.createLinearGradient(-20, 0, 20, 0);
        grd.addColorStop(0, '#2a1a12'); grd.addColorStop(0.4, '#7a3a1c'); grd.addColorStop(0.7, '#4a2414'); grd.addColorStop(1, '#1e120c');
        ctx.fillStyle = grd;
        ctx.fillRect(-20, -52, 40, 52);
        ctx.fillStyle = 'rgba(0,0,0,0.4)';
        ctx.fillRect(-20, -40, 40, 4); ctx.fillRect(-20, -16, 40, 4);
        ctx.fillStyle = '#12090a';
        ctx.beginPath(); ctx.ellipse(0, -52, 20, 8, 0, 0, TAU); ctx.fill();
        ctx.fillStyle = `rgba(255,${140 + Math.sin(time * 20 + b.x) * 40},40,0.9)`;
        ctx.beginPath(); ctx.ellipse(0, -52, 15, 5.5, 0, 0, TAU); ctx.fill();
        ctx.restore();
      },
    });
  }
}

export function emitBarrelFire(view) {
  for (const b of barrels) {
    if (b.x < view.x0 - 200 || b.x > view.x1 + 200 || b.y < view.y0 - 200 || b.y > view.y1 + 300) continue;
    fx.fire(b.x, b.y, 52, 2, 22, 10);
    if (Math.random() < 0.3) fx.embers(b.x, b.y, 60, 1);
    if (Math.random() < 0.08) fx.smoke(b.x, b.y, 90, 1, 30);
  }
}

// ---------- decals ----------
function flushDecals() {
  if (!fx.decals.length) return;
  const g = fctx;
  g.save();
  g.translate(PAD_X, PAD_TOP);
  for (const d of fx.decals) {
    if (d.type === 'blood') {
      g.fillStyle = `rgba(${90 + rand(0, 40)},${rand(4, 12)},${rand(4, 10)},${rand(0.55, 0.85)})`;
      g.beginPath(); g.ellipse(d.x, d.y, d.r, d.r * rand(0.5, 0.9), rand(0, TAU), 0, TAU); g.fill();
      if (Math.random() < 0.3) {
        g.beginPath(); g.ellipse(d.x + rand(-8, 8), d.y + rand(-6, 6), d.r * 0.5, d.r * 0.35, 0, 0, TAU); g.fill();
      }
    } else if (d.type === 'scorch') {
      const grd = g.createRadialGradient(d.x, d.y, 0, d.x, d.y, d.r);
      grd.addColorStop(0, 'rgba(0,0,0,0.75)'); grd.addColorStop(0.6, 'rgba(15,8,4,0.4)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = grd;
      g.beginPath(); g.ellipse(d.x, d.y, d.r, d.r * 0.7, 0, 0, TAU); g.fill();
    } else if (d.type === 'skid') {
      g.strokeStyle = 'rgba(12,8,6,0.35)';
      g.lineWidth = d.w || 10;
      g.lineCap = 'round';
      g.beginPath(); g.moveTo(d.x, d.y); g.lineTo(d.x2, d.y2); g.stroke();
    } else if (d.type === 'burn') {
      g.fillStyle = 'rgba(20,40,60,0.25)';
      g.beginPath(); g.arc(d.x, d.y, d.r, 0, TAU); g.fill();
    }
  }
  g.restore();
  fx.decals.length = 0;
}

export { TOP_WALL };
