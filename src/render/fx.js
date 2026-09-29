// Particles, decals, screen shake, hit-stop, flashes, shockwaves and floating text.
import { rand, pick, TAU, clamp, makeCanvas } from '../core/math.js';

const glowCache = new Map();
export function glowSprite(color, size = 64, hard = 0) {
  const key = color + size + hard;
  let c = glowCache.get(key);
  if (c) return c;
  c = makeCanvas(size, size);
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grd.addColorStop(0, color);
  grd.addColorStop(clamp(hard, 0, 0.9), color);
  grd.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  glowCache.set(key, c);
  return c;
}

const MAX = 2600;

class FX {
  constructor() {
    this.parts = [];
    this.decals = [];
    this.texts = [];
    this.trauma = 0;
    this.shakeX = 0;
    this.shakeY = 0;
    this.hitstop = 0;
    this.slowmo = 1;
    this.slowmoT = 0;
    this.flashColor = [1, 1, 1];
    this.flash = 0;
    this.ca = 0;
    this.shocks = [];
    this.time = 0;
  }

  reset() {
    this.parts.length = 0;
    this.texts.length = 0;
    this.shocks.length = 0;
    this.trauma = 0;
    this.hitstop = 0;
    this.slowmo = 1;
    this.flash = 0;
    this.ca = 0;
  }

  add(p) {
    if (this.parts.length >= MAX) this.parts.shift();
    p.age = 0;
    p.z ??= 0; p.vz ??= 0; p.vx ??= 0; p.vy ??= 0;
    p.drag ??= 1.5; p.grav ??= 0; p.size ??= 4; p.rot ??= 0; p.vr ??= 0;
    p.life ??= 0.5;
    this.parts.push(p);
    return p;
  }

  shake(amount) {
    this.trauma = Math.min(1.2, this.trauma + amount);
  }
  freeze(t) {
    this.hitstop = Math.max(this.hitstop, t);
  }
  slow(scale, time) {
    this.slowmo = scale;
    this.slowmoT = time;
  }
  doFlash(r, g, b, amount) {
    this.flashColor = [r, g, b];
    this.flash = Math.max(this.flash, amount);
  }
  aberrate(a) {
    this.ca = Math.max(this.ca, a);
  }
  shock(x, y, strength = 1) {
    this.shocks.push({ x, y, t: 0, s: strength });
  }
  text(x, y, str, color = '#fff', size = 34, life = 1.2) {
    this.texts.push({ x, y, z: 60, str, color, size, life, age: 0 });
  }
  decal(type, x, y, opts = {}) {
    this.decals.push({ type, x, y, ...opts });
  }

  // ---------- emitters ----------
  sparks(x, y, z, n = 12, speed = 400, dirX = 0, dirY = 0, spread = TAU) {
    const base = Math.atan2(dirY, dirX);
    for (let i = 0; i < n; i++) {
      const a = spread >= TAU ? rand(0, TAU) : base + rand(-spread / 2, spread / 2);
      const s = rand(0.3, 1) * speed;
      this.add({
        type: 'spark', x, y, z, vx: Math.cos(a) * s, vy: Math.sin(a) * s, vz: rand(50, 350),
        grav: 900, drag: 2.2, life: rand(0.25, 0.6), size: rand(1.5, 3),
        color: pick(['#fff6c0', '#ffd35a', '#ff9a2a']),
      });
    }
  }

  blood(x, y, z, n = 14, dirX = 0, dirY = 0, force = 1) {
    for (let i = 0; i < n; i++) {
      const a = Math.atan2(dirY, dirX) + rand(-0.9, 0.9);
      const s = rand(80, 380) * force;
      this.add({
        type: 'blood', x, y, z: z + rand(-8, 8), vx: Math.cos(a) * s + rand(-40, 40), vy: Math.sin(a) * s + rand(-40, 40),
        vz: rand(60, 300), grav: 1100, drag: 1, life: 2, size: rand(2, 5),
        color: pick(['#8a0d0d', '#a3120f', '#6b0909', '#b51c14']),
      });
    }
  }

  dust(x, y, n = 6, color = '#8a6a48', spread = 30) {
    for (let i = 0; i < n; i++) {
      this.add({
        type: 'dust', x: x + rand(-spread, spread) * 0.5, y: y + rand(-spread, spread) * 0.3, z: rand(0, 10),
        vx: rand(-60, 60), vy: rand(-30, 30), vz: rand(10, 60), drag: 3, life: rand(0.5, 1.0),
        size: rand(10, 22), grow: rand(20, 50), color, alpha: rand(0.25, 0.45),
      });
    }
  }

  smoke(x, y, z, n = 6, size = 26) {
    for (let i = 0; i < n; i++) {
      this.add({
        type: 'smoke', x: x + rand(-10, 10), y: y + rand(-6, 6), z: z + rand(0, 10),
        vx: rand(-25, 25), vy: rand(-20, 10), vz: rand(40, 110), drag: 0.8, life: rand(1, 2.2),
        size: rand(size * 0.6, size), grow: rand(20, 45), color: pick(['#1a1412', '#2a211c', '#130f0e']), alpha: rand(0.35, 0.6),
      });
    }
  }

  fire(x, y, z, n = 3, size = 16, spread = 8) {
    for (let i = 0; i < n; i++) {
      this.add({
        type: 'fire', x: x + rand(-spread, spread), y: y + rand(-spread, spread) * 0.5, z: z + rand(0, 6),
        vx: rand(-15, 15), vy: rand(-8, 8), vz: rand(70, 150), drag: 1.2, life: rand(0.35, 0.7),
        size: rand(size * 0.6, size),
      });
    }
  }

  embers(x, y, z, n = 2) {
    for (let i = 0; i < n; i++) {
      this.add({
        type: 'ember', x: x + rand(-10, 10), y, z: z + rand(0, 20), vx: rand(-40, 40), vy: rand(-20, 20), vz: rand(80, 200),
        drag: 0.6, grav: -20, life: rand(0.8, 1.8), size: rand(1.2, 2.4), color: pick(['#ffb347', '#ff7a1a', '#ffe08a']),
      });
    }
  }

  debris(x, y, z, n = 6, color = '#6b6258') {
    for (let i = 0; i < n; i++) {
      const a = rand(0, TAU), s = rand(80, 320);
      this.add({
        type: 'debris', x, y, z, vx: Math.cos(a) * s, vy: Math.sin(a) * s, vz: rand(150, 420), grav: 1300, drag: 0.8,
        life: rand(0.8, 1.6), size: rand(2, 5), rot: rand(0, TAU), vr: rand(-15, 15), color,
      });
    }
  }

  glow(x, y, z, size, color, life = 0.25) {
    this.add({ type: 'glow', x, y, z, size, color, life, drag: 0 });
  }

  ring(x, y, color = '#ffd27a', size = 120, life = 0.45, width = 6) {
    this.add({ type: 'ring', x, y, z: 0, size, color, life, width, drag: 0 });
  }

  arc(x1, y1, z1, x2, y2, z2, color = '#9ff6ff', life = 0.12) {
    this.add({ type: 'arc', x: x1, y: y1, z: z1, x2, y2, z2, color, life, drag: 0 });
  }

  explosion(x, y, big = 1) {
    this.glow(x, y, 20, 360 * big, 'rgba(255,190,90,1)', 0.35);
    this.glow(x, y, 20, 180 * big, 'rgba(255,255,230,1)', 0.18);
    for (let i = 0; i < 40 * big; i++) {
      const a = rand(0, TAU), s = rand(60, 420) * big;
      this.add({
        type: 'fire', x, y, z: rand(0, 30), vx: Math.cos(a) * s, vy: Math.sin(a) * s * 0.6, vz: rand(60, 380),
        drag: 2.6, life: rand(0.4, 0.9), size: rand(18, 38) * big,
      });
    }
    this.smoke(x, y, 20, 18 * big, 50 * big);
    this.sparks(x, y, 30, 50 * big, 800 * big);
    this.debris(x, y, 20, 14 * big);
    this.ring(x, y, '#ffcf7a', 420 * big, 0.6, 14);
    this.decal('scorch', x, y, { r: 90 * big });
  }

  // ---------- update ----------
  update(dt, realDt) {
    this.time += realDt;
    // Trauma-based shake (quadratic falloff feels punchy).
    this.trauma = Math.max(0, this.trauma - realDt * 1.6);
    const s = this.trauma * this.trauma * 26;
    this.shakeX = (Math.random() * 2 - 1) * s;
    this.shakeY = (Math.random() * 2 - 1) * s;
    this.flash = Math.max(0, this.flash - realDt * 3.2);
    this.ca = Math.max(0, this.ca - realDt * 2.5);
    if (this.slowmoT > 0) {
      this.slowmoT -= realDt;
      if (this.slowmoT <= 0) this.slowmo = 1;
    }
    for (const sh of this.shocks) sh.t += realDt;
    this.shocks = this.shocks.filter((sh) => sh.t < 0.9);

    const parts = this.parts;
    let w = 0;
    for (let i = 0; i < parts.length; i++) {
      const p = parts[i];
      p.age += dt;
      if (p.age >= p.life) continue;
      const k = Math.exp(-p.drag * dt);
      p.px = p.x; p.py = p.y - p.z;
      p.vx *= k; p.vy *= k;
      p.vz = p.vz * (p.type === 'fire' || p.type === 'smoke' ? k : 1) - p.grav * dt;
      p.x += p.vx * dt; p.y += p.vy * dt; p.z += p.vz * dt;
      p.rot += p.vr * dt;
      if (p.grow) p.size += p.grow * dt;
      if (p.z < 0 && p.grav > 0) {
        if (p.type === 'blood') {
          if (Math.random() < 0.6) this.decal('blood', p.x, p.y, { r: p.size * rand(0.8, 2.2) });
          continue;
        }
        p.z = 0;
        p.vz = -p.vz * 0.35;
        p.vx *= 0.6; p.vy *= 0.6;
      }
      parts[w++] = p;
    }
    parts.length = w;

    for (const t of this.texts) {
      t.age += realDt;
      t.z += realDt * 45;
    }
    this.texts = this.texts.filter((t) => t.age < t.life);
  }

  // ---------- draw (world space) ----------
  draw(ctx) {
    // Normal-blended first (dust, smoke, blood, debris), then additive.
    for (const p of this.parts) {
      const t = p.age / p.life;
      const sx = p.x, sy = p.y - p.z;
      switch (p.type) {
        case 'dust':
        case 'smoke': {
          const img = glowSprite(p.color, 64);
          ctx.globalAlpha = p.alpha * (1 - t) * Math.min(1, p.age * 10);
          ctx.drawImage(img, sx - p.size, sy - p.size, p.size * 2, p.size * 2);
          break;
        }
        case 'blood':
          ctx.globalAlpha = 1;
          ctx.fillStyle = p.color;
          ctx.beginPath();
          ctx.ellipse(sx, sy, p.size, p.size * 0.8, 0, 0, TAU);
          ctx.fill();
          break;
        case 'debris':
          ctx.globalAlpha = 1 - t * t;
          ctx.fillStyle = p.color;
          ctx.save();
          ctx.translate(sx, sy);
          ctx.rotate(p.rot);
          ctx.fillRect(-p.size, -p.size * 0.5, p.size * 2, p.size);
          ctx.restore();
          break;
      }
    }
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'lighter';
    for (const p of this.parts) {
      const t = p.age / p.life;
      const sx = p.x, sy = p.y - p.z;
      switch (p.type) {
        case 'spark': {
          ctx.globalAlpha = 1 - t;
          ctx.strokeStyle = p.color;
          ctx.lineWidth = p.size;
          ctx.beginPath();
          const px = p.px ?? sx, py = p.py ?? sy;
          ctx.moveTo(px - (sx - px) * 1.5, py - (sy - py) * 1.5);
          ctx.lineTo(sx, sy);
          ctx.stroke();
          break;
        }
        case 'ember': {
          ctx.globalAlpha = (1 - t) * (0.6 + 0.4 * Math.sin(p.age * 30 + p.x));
          ctx.fillStyle = p.color;
          ctx.fillRect(sx - p.size / 2, sy - p.size / 2, p.size, p.size);
          break;
        }
        case 'fire': {
          const col = t < 0.25 ? 'rgba(255,240,180,1)' : t < 0.55 ? 'rgba(255,150,40,1)' : 'rgba(200,50,10,1)';
          const img = glowSprite(col, 64, 0.15);
          const sz = p.size * (1 - t * 0.6);
          ctx.globalAlpha = (1 - t) * 0.85;
          ctx.drawImage(img, sx - sz, sy - sz, sz * 2, sz * 2);
          break;
        }
        case 'glow': {
          const img = glowSprite(p.color, 128);
          ctx.globalAlpha = (1 - t) * (1 - t);
          const sz = p.size * (0.6 + t * 0.6);
          ctx.drawImage(img, sx - sz / 2, sy - sz / 2, sz, sz);
          break;
        }
        case 'ring': {
          ctx.globalAlpha = (1 - t) * 0.9;
          ctx.strokeStyle = p.color;
          ctx.lineWidth = p.width * (1 - t) + 1;
          const r = p.size * (0.15 + 0.85 * Math.sqrt(t));
          ctx.beginPath();
          ctx.ellipse(p.x, p.y, r, r * 0.55, 0, 0, TAU);
          ctx.stroke();
          break;
        }
        case 'arc': {
          ctx.globalAlpha = 1 - t;
          const x1 = p.x, y1 = p.y - p.z, x2 = p.x2, y2 = p.y2 - p.z2;
          ctx.strokeStyle = p.color;
          for (let pass = 0; pass < 2; pass++) {
            ctx.lineWidth = pass === 0 ? 5 : 1.6;
            ctx.globalAlpha = (1 - t) * (pass === 0 ? 0.35 : 1);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            const segs = 7;
            const nx = -(y2 - y1), ny = x2 - x1;
            const nl = Math.hypot(nx, ny) || 1;
            for (let i = 1; i < segs; i++) {
              const f = i / segs;
              const off = rand(-1, 1) * 0.18 * nl;
              ctx.lineTo(x1 + (x2 - x1) * f + (nx / nl) * off, y1 + (y2 - y1) * f + (ny / nl) * off);
            }
            ctx.lineTo(x2, y2);
            ctx.stroke();
          }
          break;
        }
      }
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }

  drawTexts(ctx) {
    for (const t of this.texts) {
      const k = t.age / t.life;
      const pop = k < 0.12 ? 0.6 + (k / 0.12) * 0.6 : 1.2 - Math.min(0.2, (k - 0.12) * 2);
      ctx.save();
      ctx.translate(t.x, t.y - t.z);
      ctx.scale(pop, pop);
      ctx.globalAlpha = k > 0.7 ? 1 - (k - 0.7) / 0.3 : 1;
      ctx.font = `${t.size}px BlackOps, Impact, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.lineWidth = 6;
      ctx.strokeStyle = '#120806';
      ctx.lineJoin = 'round';
      ctx.strokeText(t.str, 0, 0);
      ctx.fillStyle = t.color;
      ctx.fillText(t.str, 0, 0);
      ctx.restore();
    }
    ctx.globalAlpha = 1;
  }
}

export const fx = new FX();
