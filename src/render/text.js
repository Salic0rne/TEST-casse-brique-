// Distressed, cached text rendering: condensed type, eroded by a grunge mask, optional blood drips.
// Results are cached canvases, so animated titles only cost a drawImage per frame.
import { makeCanvas, rand, hash, TAU } from '../core/math.js';

let grunge = null;
function grungeMask() {
  if (grunge) return grunge;
  grunge = makeCanvas(512, 256);
  const g = grunge.getContext('2d');
  for (let i = 0; i < 2600; i++) {
    g.fillStyle = `rgba(0,0,0,${rand(0.2, 1)})`;
    const s = rand(0.8, 3.2);
    g.fillRect(rand(0, 512), rand(0, 256), s, s * rand(0.5, 1.5));
  }
  g.strokeStyle = 'rgba(0,0,0,0.9)';
  for (let i = 0; i < 70; i++) {
    g.lineWidth = rand(0.6, 2);
    const x = rand(0, 512), y = rand(0, 256), a = rand(-0.4, 0.4);
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * rand(20, 90), y + Math.sin(a) * rand(4, 20)); g.stroke();
  }
  for (let i = 0; i < 40; i++) {
    g.fillStyle = `rgba(0,0,0,${rand(0.3, 0.8)})`;
    g.beginPath(); g.arc(rand(0, 512), rand(0, 256), rand(3, 10), 0, TAU); g.fill();
  }
  return grunge;
}

const cache = new Map();

/**
 * opts: { font: 'Display'|'Cond', weight, fill, fill2, stroke, strokeW, erosion (0..1), drips (bool), tracking }
 */
export function textImage(str, size, opts = {}) {
  const key = str + '|' + size + '|' + JSON.stringify(opts);
  let img = cache.get(key);
  if (img) return img;
  if (cache.size > 300) cache.clear();
  const font = `${opts.weight || ''} ${Math.round(size)}px ${opts.font || 'Display'}, Impact, sans-serif`;
  const probe = makeCanvas(4, 4).getContext('2d');
  probe.font = font;
  const tracking = opts.tracking || 0;
  const w = Math.ceil(probe.measureText(str).width + tracking * str.length + size * 0.4);
  const h = Math.ceil(size * (opts.drips ? 1.9 : 1.45));
  const c = makeCanvas(w, h);
  const g = c.getContext('2d');
  g.font = font;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.lineJoin = 'round';
  if ('letterSpacing' in g) g.letterSpacing = `${tracking}px`;
  const cx = w / 2, cy = size * 0.72;
  if (opts.stroke) {
    g.lineWidth = opts.strokeW || size * 0.08;
    g.strokeStyle = opts.stroke;
    g.strokeText(str, cx, cy);
  }
  if (opts.fill2) {
    const grd = g.createLinearGradient(0, cy - size / 2, 0, cy + size / 2);
    grd.addColorStop(0, opts.fill || '#fff');
    grd.addColorStop(1, opts.fill2);
    g.fillStyle = grd;
  } else g.fillStyle = opts.fill || '#fff';
  g.fillText(str, cx, cy);
  if (opts.drips) {
    // Blood dripping from the letters.
    g.fillStyle = opts.dripColor || '#7a0a06';
    const n = Math.max(3, Math.floor(w / (size * 0.35)));
    for (let i = 0; i < n; i++) {
      const x = size * 0.3 + hash(i, str.length, 3) * (w - size * 0.6);
      const len = size * (0.1 + hash(i, 7, str.length) * 0.32);
      const y0 = cy + size * 0.3;
      const ww = size * (0.03 + hash(i, 2, 5) * 0.04);
      g.fillRect(x - ww / 2, y0, ww, len);
      g.beginPath(); g.arc(x, y0 + len, ww * 0.9, 0, TAU); g.fill();
    }
  }
  const er = opts.erosion ?? 0.35;
  if (er > 0) {
    const m = grungeMask();
    g.globalCompositeOperation = 'destination-out';
    g.globalAlpha = er;
    const ox = hash(str.length, size | 0, 1) * 200;
    const sc = Math.max(0.6, size / 140);
    for (let x = -ox; x < w; x += 512 * sc) for (let y = 0; y < h; y += 256 * sc) g.drawImage(m, x, y, 512 * sc, 256 * sc);
    g.globalAlpha = 1;
    g.globalCompositeOperation = 'source-over';
  }
  img = { c, w, h, cy };
  cache.set(key, img);
  return img;
}

/** Draws cached text centred at (x, y) with optional scale / rotation. */
export function drawText(ctx, str, x, y, size, opts = {}, scale = 1, rot = 0, align = 'center') {
  const img = textImage(str, size, opts);
  ctx.save();
  ctx.translate(x, y);
  if (rot) ctx.rotate(rot);
  if (scale !== 1) ctx.scale(scale, scale);
  const ox = align === 'left' ? -size * 0.2 : align === 'right' ? -img.w + size * 0.2 : -img.w / 2;
  ctx.drawImage(img.c, ox, -img.cy);
  ctx.restore();
  return img;
}
