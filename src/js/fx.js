// Effets visuels : particules, textes comic flottants, secousse d'écran, flash, hit-stop.
import { PAL, TAU, rand, clamp, easeOutBack } from './config.js';

const MAX = 1600;

export class FX {
  constructor() {
    this.p = [];
    this.trauma = 0;
    this.flash = 0; this.flashColor = '#fff';
    this.hitstop = 0;
    this.shakeEnabled = true;
    this.t = 0;
  }

  clear() { this.p.length = 0; this.trauma = 0; this.flash = 0; this.hitstop = 0; }

  add(o) { if (this.p.length < MAX) this.p.push(o); return o; }

  shake(a) { this.trauma = Math.min(1, this.trauma + a); }
  doFlash(a, color = '#fff') { this.flash = Math.max(this.flash, a); this.flashColor = color; }
  stop(sec) { this.hitstop = Math.max(this.hitstop, sec); }

  // --- fabriques ---------------------------------------------------------
  sparks(x, y, z, n, color = PAL.mustardLight, speed = 500, spread = TAU, dir = 0) {
    for (let i = 0; i < n; i++) {
      const a = dir + (Math.random() - 0.5) * spread, s = speed * (0.35 + Math.random() * 0.75);
      this.add({ k: 'spark', x, y, z, vx: Math.cos(a) * s, vy: Math.sin(a) * s * 0.6, vz: rand(-50, 300), life: 0, max: rand(0.25, 0.6), size: rand(2.2, 4.5), color, g: 900, drag: 1.2, layer: 1 });
    }
  }
  dust(x, y, n = 6, size = 16, color = 'rgba(232,224,204,0.75)', spd = 90) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU, s = rand(0.3, 1) * spd;
      this.add({ k: 'dust', x, y, z: rand(0, 8), vx: Math.cos(a) * s, vy: Math.sin(a) * s * 0.5, vz: rand(20, 70), life: 0, max: rand(0.35, 0.7), size: size * rand(0.6, 1.2), color, g: -30, drag: 3, layer: 1 });
    }
  }
  smoke(x, y, z, n = 3, size = 26, color = 'rgba(240,235,224,0.6)', up = 120) {
    for (let i = 0; i < n; i++) this.add({ k: 'smoke', x: x + rand(-8, 8), y, z, vx: rand(-30, 30), vy: rand(-8, 8), vz: up * rand(0.6, 1.3), life: 0, max: rand(0.7, 1.4), size: size * rand(0.7, 1.3), color, g: -20, drag: 1.5, layer: 1 });
  }
  ring(x, y, z, color = '#fff', size = 90, life = 0.4, width = 6, ground = true) {
    this.add({ k: 'ring', x, y, z, vx: 0, vy: 0, vz: 0, life: 0, max: life, size, color, w: width, g: 0, drag: 0, layer: ground ? 0 : 1 });
  }
  star(x, y, z, color = PAL.mustardLight, size = 14) {
    this.add({ k: 'star', x, y, z, vx: rand(-160, 160), vy: rand(-60, 30), vz: rand(200, 420), life: 0, max: rand(0.5, 0.9), size, color, g: 1100, drag: 0.5, rot: rand(0, TAU), vr: rand(-8, 8), layer: 1 });
  }
  glow(x, y, z, color, size, life = 0.3) {
    this.add({ k: 'glow', x, y, z, vx: 0, vy: 0, vz: 0, life: 0, max: life, size, color, g: 0, drag: 0, layer: 2 });
  }
  confetti(x, y, n, colors, power = 500, z = 40) {
    for (let i = 0; i < n; i++) {
      const a = -Math.PI / 2 + (Math.random() - 0.5) * 1.6, s = rand(0.3, 1) * power;
      this.add({ k: 'confetti', x, y, z, vx: Math.cos(a) * s * 0.6, vy: rand(-140, 140), vz: -Math.sin(a) * s * 1.3, life: 0, max: rand(2.2, 3.8), size: rand(6, 11), color: colors[(Math.random() * colors.length) | 0], g: 520, drag: 1.6, rot: rand(0, TAU), vr: rand(-9, 9), layer: 1 });
    }
  }
  shard(x, y, z, color, n = 6, speed = 400) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU, s = rand(0.3, 1) * speed;
      this.add({ k: 'shard', x, y, z, vx: Math.cos(a) * s, vy: Math.sin(a) * s * 0.5, vz: rand(120, 480), life: 0, max: rand(0.5, 0.9), size: rand(5, 11), color, g: 1400, drag: 0.6, rot: rand(0, TAU), vr: rand(-14, 14), layer: 1 });
    }
  }
  scuff(x, y, dx, dy, len = 60) {
    this.add({ k: 'scuff', x, y, z: 0, vx: dx, vy: dy, life: 0, max: 4, size: len, color: 'rgba(15,20,26,0.35)', g: 0, drag: 0, layer: 0 });
  }
  speedLine(x, y, z, dx, dy, color = 'rgba(255,255,255,0.55)', len = 90) {
    this.add({ k: 'line', x, y, z, vx: -dx * 60, vy: -dy * 60, vz: 0, life: 0, max: 0.22, size: len, dx, dy, color, g: 0, drag: 0, layer: 1 });
  }
  ghost(fn, life = 0.3) { this.add({ k: 'ghost', x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0, life: 0, max: life, fn, g: 0, drag: 0, layer: 1 }); }

  text(str, x, y, opts = {}) {
    this.add({
      k: 'text', str, x, y, z: opts.z ?? 90, vx: 0, vy: 0, vz: opts.rise ?? 50, life: 0, max: opts.life ?? 1.0,
      size: opts.size ?? 44, color: opts.color ?? PAL.mustardLight, stroke: opts.stroke ?? PAL.outline, rot: opts.rot ?? rand(-0.15, 0.15),
      g: 0, drag: 0.8, layer: 1,
    });
  }

  // --- simulation ----------------------------------------------------------
  update(dt) {
    this.t += dt;
    this.trauma = Math.max(0, this.trauma - dt * 1.7);
    this.flash = Math.max(0, this.flash - dt * 3.2);
    const p = this.p;
    for (let i = p.length - 1; i >= 0; i--) {
      const q = p[i];
      q.life += dt;
      if (q.life >= q.max) { p[i] = p[p.length - 1]; p.pop(); continue; }
      if (q.k === 'ring' || q.k === 'glow' || q.k === 'ghost' || q.k === 'scuff') continue;
      const d = Math.exp(-q.drag * dt);
      q.vx *= d; q.vy *= d;
      q.vz -= q.g * dt;
      if (q.k === 'text') q.vz *= Math.exp(-3 * dt);
      q.x += q.vx * dt; q.y += q.vy * dt; q.z += q.vz * dt;
      if (q.rot !== undefined) q.rot += q.vr * dt;
      if (q.z < 0 && q.k !== 'dust' && q.k !== 'smoke') { q.z = 0; q.vz *= -0.35; q.vx *= 0.6; q.vy *= 0.6; if (q.k === 'confetti') { q.vr *= 0.3; } }
    }
  }

  shakeOffset() {
    if (!this.shakeEnabled) return { x: 0, y: 0, r: 0 };
    const s = this.trauma * this.trauma;
    return { x: (Math.random() - 0.5) * 46 * s, y: (Math.random() - 0.5) * 34 * s, r: (Math.random() - 0.5) * 0.03 * s };
  }

  // --- rendu ---------------------------------------------------------------
  // layer 0 : sol ; layer 1 : en l'air (trié avec les entités) ; layer 2 : lumière additive
  draw(ctx, layer, view) {
    const p = this.p;
    for (let i = 0; i < p.length; i++) {
      const q = p[i];
      if (q.layer !== layer) continue;
      if (view && (q.x < view.x0 - 100 || q.x > view.x1 + 100 || q.y < view.y0 - 200 || q.y > view.y1 + 100)) continue;
      const f = q.life / q.max, a = 1 - f;
      const sy = q.y - q.z;
      switch (q.k) {
        case 'spark': {
          ctx.strokeStyle = q.color; ctx.lineWidth = q.size * a + 0.5; ctx.lineCap = 'round';
          ctx.beginPath(); ctx.moveTo(q.x, sy); ctx.lineTo(q.x - q.vx * 0.045, sy - (q.vy - q.vz) * 0.045); ctx.stroke();
          break;
        }
        case 'dust': case 'smoke': {
          const r = q.size * (0.5 + f * (q.k === 'smoke' ? 1.6 : 1.1));
          ctx.globalAlpha = a * a * (q.k === 'smoke' ? 0.9 : 1);
          ctx.fillStyle = q.color; ctx.beginPath(); ctx.arc(q.x, sy, r, 0, TAU); ctx.fill();
          ctx.globalAlpha = 1; break;
        }
        case 'ring': {
          const r = q.size * (1 - Math.pow(1 - f, 3));
          ctx.globalAlpha = a; ctx.strokeStyle = q.color; ctx.lineWidth = q.w * a + 1;
          ctx.beginPath();
          if (layer === 0) ctx.ellipse(q.x, sy, r, r * 0.55, 0, 0, TAU); else ctx.arc(q.x, sy, r, 0, TAU);
          ctx.stroke(); ctx.globalAlpha = 1; break;
        }
        case 'star': {
          ctx.save(); ctx.translate(q.x, sy); ctx.rotate(q.rot); ctx.globalAlpha = Math.min(1, a * 2);
          this.starPath(ctx, q.size * (0.6 + a * 0.4));
          ctx.fillStyle = q.color; ctx.strokeStyle = PAL.outline; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.fill(); ctx.stroke();
          ctx.restore(); ctx.globalAlpha = 1; break;
        }
        case 'confetti': {
          ctx.save(); ctx.translate(q.x, sy); ctx.rotate(q.rot); ctx.scale(1, Math.sin(q.life * 9 + q.rot));
          ctx.globalAlpha = Math.min(1, a * 3); ctx.fillStyle = q.color; ctx.fillRect(-q.size / 2, -q.size / 4, q.size, q.size / 2);
          ctx.strokeStyle = PAL.outline; ctx.lineWidth = 1.2; ctx.strokeRect(-q.size / 2, -q.size / 4, q.size, q.size / 2);
          ctx.restore(); ctx.globalAlpha = 1; break;
        }
        case 'shard': {
          ctx.save(); ctx.translate(q.x, sy); ctx.rotate(q.rot); ctx.globalAlpha = Math.min(1, a * 2.5);
          ctx.beginPath(); ctx.moveTo(-q.size, 0); ctx.lineTo(0, -q.size * 0.5); ctx.lineTo(q.size, q.size * 0.2); ctx.closePath();
          ctx.fillStyle = q.color; ctx.strokeStyle = PAL.outline; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.fill(); ctx.stroke();
          ctx.restore(); ctx.globalAlpha = 1; break;
        }
        case 'glow': {
          const r = q.size * (0.6 + f * 0.6);
          const g = ctx.createRadialGradient(q.x, sy, 0, q.x, sy, r);
          g.addColorStop(0, q.color); g.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.globalAlpha = a; ctx.fillStyle = g; ctx.fillRect(q.x - r, sy - r, r * 2, r * 2); ctx.globalAlpha = 1; break;
        }
        case 'scuff': {
          ctx.globalAlpha = Math.min(1, a * 2); ctx.strokeStyle = q.color; ctx.lineWidth = 9; ctx.lineCap = 'round';
          ctx.beginPath(); ctx.moveTo(q.x, q.y); ctx.lineTo(q.x + q.vx * q.size, q.y + q.vy * q.size * 0.9); ctx.stroke(); ctx.globalAlpha = 1; break;
        }
        case 'line': {
          ctx.globalAlpha = a; ctx.strokeStyle = q.color; ctx.lineWidth = 3; ctx.lineCap = 'round';
          ctx.beginPath(); ctx.moveTo(q.x, sy); ctx.lineTo(q.x + q.dx * q.size * (1 - f * 0.4), sy + q.dy * q.size * (1 - f * 0.4)); ctx.stroke(); ctx.globalAlpha = 1; break;
        }
        case 'ghost': { ctx.globalAlpha = a * 0.5; q.fn(ctx, a); ctx.globalAlpha = 1; break; }
        case 'text': {
          const pop = easeOutBack(Math.min(1, f * 6)), sc = pop * (f > 0.75 ? 1 - (f - 0.75) * 2 : 1);
          ctx.save(); ctx.translate(q.x, sy); ctx.rotate(q.rot); ctx.scale(sc, sc);
          comicText(ctx, q.str, 0, 0, q.size, q.color, q.stroke);
          ctx.restore(); break;
        }
      }
    }
  }

  starPath(ctx, r) {
    ctx.beginPath();
    for (let i = 0; i < 10; i++) {
      const rr = i % 2 ? r * 0.45 : r, a = -Math.PI / 2 + i * Math.PI / 5;
      const x = Math.cos(a) * rr, y = Math.sin(a) * rr;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    }
    ctx.closePath();
  }
}

// Texte BD : contour épais + ombre extrudée.
export function comicText(ctx, str, x, y, size, fill = PAL.mustardLight, stroke = PAL.outline, font = 'Bangers', extrude = 0.09) {
  ctx.save();
  ctx.font = `${size}px ${font}, Impact, sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.lineJoin = 'round'; ctx.miterLimit = 2;
  const lw = Math.max(3, size * 0.16), ex = size * extrude;
  ctx.strokeStyle = stroke; ctx.lineWidth = lw;
  // extrusion
  ctx.fillStyle = stroke;
  for (let i = ex; i > 0; i -= 1) { ctx.strokeText(str, x + i * 0.6, y + i); }
  ctx.fillText(str, x + ex * 0.6, y + ex);
  ctx.strokeText(str, x, y);
  ctx.fillStyle = fill; ctx.fillText(str, x, y);
  // reflet haut
  ctx.globalCompositeOperation = 'source-atop';
  ctx.restore();
}
