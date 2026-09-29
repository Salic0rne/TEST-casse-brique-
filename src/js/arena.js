// Décor de l'arène : pré-rendu (sol, murs, tribunes, filets) + éléments dynamiques (foule, pads lumineux, cages, lanceur).
import { W, H, CY, GOAL_H, GOAL_D, GOAL_TOP, WALL_FACE, PAL, PADS, TAU, clamp } from './config.js';
import { rrPath, shadeColor } from './art.js';

const S = 1.25;                       // définition du pré-rendu
const X0 = -360, X1 = W + 360;
const ST_Y0 = -520, ST_Y1 = -WALL_FACE + 30;   // tribunes
const AR_Y0 = -WALL_FACE - 40, AR_Y1 = H + 12; // mur du fond + sol
const FR_Y0 = H - 6, FR_Y1 = H + 300;          // mur proche + silhouettes
const OUT = PAL.outline;

function mkCanvas(x0, y0, x1, y1) {
  const c = document.createElement('canvas');
  c.width = Math.ceil((x1 - x0) * S); c.height = Math.ceil((y1 - y0) * S);
  const ctx = c.getContext('2d');
  ctx.scale(S, S); ctx.translate(-x0, -y0);
  return { c, ctx, x0, y0, w: x1 - x0, h: y1 - y0 };
}

function mulberry(seed) { return () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const ADS = ['GEARHEAD', 'BOLT-COLA', 'NUTZ&CO', 'OIL RUSH', 'MEGAWATT', 'RUSTY\'S', 'TURBO-X', 'SCRAPLY'];

export class Arena {
  constructor() {
    this.stands = null; this.arena = null; this.front = null;
    this.crowd = [];
  }

  build(tL, tR) {
    this.tL = tL; this.tR = tR;
    this._buildStands(tL, tR);
    this._buildArena(tL, tR);
    this._buildFront(tL, tR);
    this._buildCrowd(tL, tR);
  }

  // ---------------------------------------------------------------- tribunes
  _buildStands(tL, tR) {
    const s = (this.stands = mkCanvas(X0, ST_Y0, X1, ST_Y1)), ctx = s.ctx, rnd = mulberry(11);
    const g = ctx.createLinearGradient(0, ST_Y0, 0, ST_Y1);
    g.addColorStop(0, '#120c14'); g.addColorStop(1, '#2b1c28');
    ctx.fillStyle = g; ctx.fillRect(X0, ST_Y0, X1 - X0, ST_Y1 - ST_Y0);
    // gradins
    const tiers = 8;
    for (let i = 0; i < tiers; i++) {
      const y = -WALL_FACE - 6 - i * 50;
      const k = i / tiers;
      ctx.fillStyle = i % 2 ? shadeColor('#3a2733', -0.1 - k * 0.5) : shadeColor('#45303b', -0.1 - k * 0.5);
      ctx.fillRect(X0, y - 50, X1 - X0, 52);
      ctx.fillStyle = shadeColor('#6b4a58', -0.2 - k * 0.6); ctx.fillRect(X0, y - 50, X1 - X0, 5);
      ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.fillRect(X0, y + 1, X1 - X0, 4);
      // sièges
      for (let x = X0 + 10; x < X1; x += 22) { ctx.fillStyle = `rgba(0,0,0,${0.15 + rnd() * 0.15})`; ctx.fillRect(x, y - 10, 14, 8); }
    }
    // escaliers
    for (let x = X0 + 160; x < X1; x += 420) { ctx.fillStyle = 'rgba(15,10,18,0.55)'; ctx.fillRect(x, ST_Y0, 34, ST_Y1 - ST_Y0); ctx.fillStyle = 'rgba(232,184,74,0.35)'; ctx.fillRect(x, ST_Y0, 3, ST_Y1 - ST_Y0); ctx.fillRect(x + 31, ST_Y0, 3, ST_Y1 - ST_Y0); }
    // banderoles
    const banners = [[0.12, tL], [0.32, tR], [0.5, null], [0.68, tL], [0.88, tR]];
    for (const [f, t] of banners) {
      const bx = W * f, by = -WALL_FACE - 240;
      ctx.fillStyle = OUT; ctx.fillRect(bx - 42, by - 6, 84, 140);
      const col = t ? t.main : PAL.mustard;
      ctx.beginPath(); ctx.moveTo(bx - 38, by); ctx.lineTo(bx + 38, by); ctx.lineTo(bx + 38, by + 118); ctx.lineTo(bx, by + 132); ctx.lineTo(bx - 38, by + 118); ctx.closePath();
      ctx.fillStyle = col; ctx.fill(); ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.fillStyle = t ? t.accent : PAL.salmon; ctx.beginPath(); ctx.arc(bx, by + 52, 20, 0, TAU); ctx.fill(); ctx.stroke();
      ctx.font = '30px Bangers, Impact'; ctx.textAlign = 'center'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 5;
      const txt = t ? t.short : 'SB'; ctx.strokeText(txt, bx, by + 104); ctx.fillText(txt, bx, by + 104);
    }
    // projecteurs
    for (const f of [0.05, 0.27, 0.5, 0.73, 0.95]) {
      const lx = W * f, ly = ST_Y0 + 60;
      ctx.fillStyle = OUT; ctx.fillRect(lx - 4, ly, 8, 260);
      const gg = ctx.createRadialGradient(lx, ly, 4, lx, ly, 150); gg.addColorStop(0, 'rgba(255,240,200,0.55)'); gg.addColorStop(1, 'rgba(255,240,200,0)');
      ctx.fillStyle = gg; ctx.fillRect(lx - 150, ly - 150, 300, 300);
      rrPath(ctx, lx - 34, ly - 12, 68, 24, 6); ctx.fillStyle = '#2b2530'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      for (let i = 0; i < 4; i++) { ctx.fillStyle = '#fff6d0'; ctx.beginPath(); ctx.arc(lx - 22 + i * 14.6, ly, 5, 0, TAU); ctx.fill(); }
    }
  }

  // ---------------------------------------------------------------- arène
  _buildArena(tL, tR) {
    const a = (this.arena = mkCanvas(X0, AR_Y0, X1, AR_Y1)), ctx = a.ctx, rnd = mulberry(5);

    // ---- fond des côtés (au-delà des buts)
    ctx.fillStyle = '#1b1218'; ctx.fillRect(X0, 0, X1 - X0, H + 12);
    for (const side of [-1, 1]) {
      const x = side < 0 ? X0 : W + 74;
      for (let i = 0; i < 9; i++) { ctx.fillStyle = i % 2 ? '#2a1d26' : '#33232e'; ctx.fillRect(side < 0 ? X0 + i * 30 : W + 74 + i * 30, 0, 30, H + 12); }
    }

    // ---- sol
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, W, H); ctx.clip();
    const T = 95;
    for (let ty = 0; ty < H; ty += T) for (let tx = 0; tx < W; tx += T) {
      const v = (rnd() - 0.5) * 0.09;
      ctx.fillStyle = shadeColor(PAL.floor, v); ctx.fillRect(tx, ty, T, T);
      ctx.fillStyle = 'rgba(255,255,255,0.07)'; ctx.fillRect(tx, ty, T, 3); ctx.fillRect(tx, ty, 3, T);
      ctx.fillStyle = 'rgba(0,0,0,0.20)'; ctx.fillRect(tx, ty + T - 3, T, 3); ctx.fillRect(tx + T - 3, ty, 3, T);
      for (const [rx, ry] of [[9, 9], [T - 9, 9], [9, T - 9], [T - 9, T - 9]]) { ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.beginPath(); ctx.arc(tx + rx, ty + ry + 1, 3, 0, TAU); ctx.fill(); ctx.fillStyle = 'rgba(214,226,236,0.45)'; ctx.beginPath(); ctx.arc(tx + rx, ty + ry, 2.4, 0, TAU); ctx.fill(); }
      // plaque losangée sur une tuile sur trois
      if ((tx / T + ty / T) % 3 === 0) {
        ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 2;
        for (let k = 14; k < T - 10; k += 14) { ctx.beginPath(); ctx.moveTo(tx + 12, ty + k); ctx.lineTo(tx + k, ty + 12); ctx.stroke(); }
      }
    }
    // taches et rayures
    for (let i = 0; i < 90; i++) {
      const x = rnd() * W, y = rnd() * H;
      if (rnd() < 0.5) { ctx.fillStyle = `rgba(10,14,20,${0.05 + rnd() * 0.08})`; ctx.beginPath(); ctx.ellipse(x, y, 20 + rnd() * 50, 8 + rnd() * 20, rnd() * 3, 0, TAU); ctx.fill(); }
      else { ctx.strokeStyle = `rgba(230,240,250,${0.06 + rnd() * 0.08})`; ctx.lineWidth = 1.5 + rnd() * 1.5; ctx.beginPath(); const l = 20 + rnd() * 60, an = rnd() * 3.14; ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(an) * l, y + Math.sin(an) * l * 0.3); ctx.stroke(); }
    }
    // zones d'équipes
    ctx.fillStyle = tL.main; ctx.globalAlpha = 0.13; ctx.fillRect(0, 0, W / 2, H);
    ctx.fillStyle = tR.main; ctx.fillRect(W / 2, 0, W / 2, H); ctx.globalAlpha = 1;
    // surfaces de but
    for (const side of [-1, 1]) {
      const t = side < 0 ? tL : tR, gx = side < 0 ? 0 : W;
      ctx.save(); ctx.beginPath(); ctx.arc(gx, CY, 260, 0, TAU); ctx.clip();
      ctx.fillStyle = t.main; ctx.globalAlpha = 0.22; ctx.fillRect(gx - 270, CY - 270, 540, 540); ctx.globalAlpha = 1;
      ctx.strokeStyle = 'rgba(0,0,0,0.13)'; ctx.lineWidth = 10;
      for (let i = -30; i < 40; i++) { ctx.beginPath(); ctx.moveTo(gx - 300 + i * 26, CY - 300); ctx.lineTo(gx - 100 + i * 26, CY + 300); ctx.stroke(); }
      ctx.restore();
      ctx.strokeStyle = PAL.cream; ctx.lineWidth = 7; ctx.globalAlpha = 0.85; ctx.beginPath(); ctx.arc(gx, CY, 260, 0, TAU); ctx.stroke();
      ctx.setLineDash([22, 16]); ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(gx, CY, 290, 0, TAU); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
    }
    // bandes de danger le long des murs
    for (const [y0, y1] of [[0, 24], [H - 24, H]]) {
      ctx.save(); ctx.beginPath(); ctx.rect(0, y0, W, y1 - y0); ctx.clip();
      ctx.fillStyle = 'rgba(15,10,14,0.55)'; ctx.fillRect(0, y0, W, y1 - y0);
      ctx.fillStyle = 'rgba(232,184,74,0.7)';
      for (let x = -40; x < W + 40; x += 44) { ctx.beginPath(); ctx.moveTo(x, y1); ctx.lineTo(x + 22, y1); ctx.lineTo(x + 22 + 24, y0); ctx.lineTo(x + 24, y0); ctx.closePath(); ctx.fill(); }
      ctx.restore();
    }
    // ligne médiane, cercle central
    ctx.strokeStyle = PAL.cream; ctx.globalAlpha = 0.9; ctx.lineWidth = 8;
    ctx.beginPath(); ctx.moveTo(W / 2, 24); ctx.lineTo(W / 2, H - 24); ctx.stroke();
    ctx.beginPath(); ctx.arc(W / 2, CY, 150, 0, TAU); ctx.stroke();
    ctx.lineWidth = 4; ctx.setLineDash([16, 14]); ctx.beginPath(); ctx.arc(W / 2, CY, 182, 0, TAU); ctx.stroke(); ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    // chevrons directionnels
    for (const side of [-1, 1]) {
      const t = side < 0 ? tL : tR;
      for (let i = 0; i < 3; i++) {
        const cx = side < 0 ? W * (0.15 + i * 0.075) : W * (0.85 - i * 0.075), dirx = side < 0 ? 1 : -1;
        ctx.fillStyle = t.main; ctx.globalAlpha = 0.5 - i * 0.1;
        ctx.beginPath(); ctx.moveTo(cx - 24 * dirx, CY - 52); ctx.lineTo(cx + 6 * dirx, CY - 52); ctx.lineTo(cx + 34 * dirx, CY); ctx.lineTo(cx + 6 * dirx, CY + 52); ctx.lineTo(cx - 24 * dirx, CY + 52); ctx.lineTo(cx + 4 * dirx, CY); ctx.closePath(); ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    // trou du lanceur
    ctx.beginPath(); ctx.arc(W / 2, CY, 52, 0, TAU); ctx.fillStyle = '#12181f'; ctx.fill(); ctx.lineWidth = 8; ctx.strokeStyle = PAL.mustard; ctx.stroke();
    ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.beginPath(); ctx.arc(W / 2, CY, 58, 0, TAU); ctx.stroke();
    // ombres portées des murs + occlusion ambiante
    let g = ctx.createLinearGradient(0, 0, 0, 90); g.addColorStop(0, 'rgba(6,8,12,0.65)'); g.addColorStop(1, 'rgba(6,8,12,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, 90);
    g = ctx.createLinearGradient(0, H, 0, H - 60); g.addColorStop(0, 'rgba(6,8,12,0.5)'); g.addColorStop(1, 'rgba(6,8,12,0)');
    ctx.fillStyle = g; ctx.fillRect(0, H - 60, W, 60);
    g = ctx.createLinearGradient(0, 0, 90, 0); g.addColorStop(0, 'rgba(6,8,12,0.55)'); g.addColorStop(1, 'rgba(6,8,12,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, 90, H);
    g = ctx.createLinearGradient(W, 0, W - 90, 0); g.addColorStop(0, 'rgba(6,8,12,0.55)'); g.addColorStop(1, 'rgba(6,8,12,0)'); ctx.fillStyle = g; ctx.fillRect(W - 90, 0, 90, H);
    ctx.restore();

    // ---- murs d'extrémité (avec ouverture de but)
    for (const side of [-1, 1]) {
      ctx.save();
      if (side > 0) { ctx.translate(W, 0); ctx.scale(-1, 1); }
      const t = side < 0 ? tL : tR;
      // recul du filet (sol)
      const gy0 = CY - GOAL_H / 2, gy1 = CY + GOAL_H / 2;
      const wallX = -76;
      // dalle du mur
      ctx.fillStyle = OUT; ctx.fillRect(wallX - 4, -WALL_FACE - 4, 84, H + WALL_FACE + 12);
      ctx.fillStyle = '#7d8790'; ctx.fillRect(wallX, -WALL_FACE, 76, H + WALL_FACE + 6);
      ctx.fillStyle = '#a0a9b1'; ctx.fillRect(wallX, -WALL_FACE, 18, H + WALL_FACE + 6);
      ctx.fillStyle = '#5a636d'; ctx.fillRect(-14, -WALL_FACE, 14, H + WALL_FACE + 6);
      for (let y = -WALL_FACE + 40; y < H; y += 80) { ctx.fillStyle = 'rgba(0,0,0,0.22)'; ctx.fillRect(wallX + 22, y, 44, 3); for (const rx of [wallX + 30, wallX + 58]) { ctx.fillStyle = 'rgba(230,236,242,0.6)'; ctx.beginPath(); ctx.arc(rx, y + 14, 3, 0, TAU); ctx.fill(); } }
      // bande couleur équipe
      ctx.fillStyle = t.main; ctx.fillRect(wallX + 20, -WALL_FACE, 44, H + WALL_FACE + 6); ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.fillRect(wallX + 46, -WALL_FACE, 18, H + WALL_FACE + 6);
      for (let y = -WALL_FACE + 10; y < H; y += 44) { ctx.fillStyle = t.accent; ctx.fillRect(wallX + 28, y, 28, 10); }
      // ouverture du but : creuse le mur
      ctx.clearRect(-GOAL_D - 40, gy0 - 130, GOAL_D + 60, GOAL_H + 130);
      // sol du but
      const rg = ctx.createLinearGradient(-GOAL_D, 0, 0, 0); rg.addColorStop(0, shadeColor(t.dark, -0.6)); rg.addColorStop(1, shadeColor(t.dark, -0.25));
      ctx.fillStyle = rg; ctx.fillRect(-GOAL_D, gy0, GOAL_D, GOAL_H);
      ctx.strokeStyle = 'rgba(246,239,223,0.35)'; ctx.lineWidth = 1.6;
      for (let x = -GOAL_D; x <= 0; x += 16) { ctx.beginPath(); ctx.moveTo(x, gy0); ctx.lineTo(x, gy1); ctx.stroke(); }
      for (let y = gy0; y <= gy1; y += 16) { ctx.beginPath(); ctx.moveTo(-GOAL_D, y); ctx.lineTo(0, y); ctx.stroke(); }
      // mur du fond du but (plan vertical vu de tranche) + filet latéral lointain
      ctx.fillStyle = shadeColor(t.dark, -0.55); ctx.fillRect(-GOAL_D - 14, gy0 - GOAL_TOP, 14, GOAL_H + GOAL_TOP);
      ctx.fillStyle = shadeColor(t.dark, -0.5); ctx.fillRect(-GOAL_D, gy0 - GOAL_TOP, GOAL_D, GOAL_TOP);
      ctx.strokeStyle = 'rgba(246,239,223,0.42)'; ctx.lineWidth = 1.6;
      for (let x = -GOAL_D; x <= 0; x += 14) { ctx.beginPath(); ctx.moveTo(x, gy0 - GOAL_TOP); ctx.lineTo(x, gy0); ctx.stroke(); }
      for (let y = gy0 - GOAL_TOP; y <= gy0; y += 14) { ctx.beginPath(); ctx.moveTo(-GOAL_D, y); ctx.lineTo(0, y); ctx.stroke(); }
      ctx.strokeStyle = OUT; ctx.lineWidth = 3.5; ctx.strokeRect(-GOAL_D, gy0 - GOAL_TOP, GOAL_D, GOAL_H + GOAL_TOP);
      ctx.restore();
    }

    // ---- mur du fond (face vers le terrain)
    const wx0 = -76, wx1 = W + 76;
    ctx.fillStyle = OUT; ctx.fillRect(wx0, -WALL_FACE - 4, wx1 - wx0, WALL_FACE + 6);
    ctx.fillStyle = '#bfc5c9'; ctx.fillRect(wx0, -WALL_FACE, wx1 - wx0, 14);      // dessus
    ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.fillRect(wx0, -WALL_FACE + 12, wx1 - wx0, 4);
    ctx.fillStyle = '#7b8791'; ctx.fillRect(wx0, -WALL_FACE + 16, wx1 - wx0, WALL_FACE - 16);
    // panneaux pub
    const pw = 190;
    for (let i = 0, x = wx0 + 6; x < wx1 - 20; i++, x += pw) {
      const cols = [tL.main, PAL.mustard, tR.main, PAL.steel, PAL.sage];
      const col = cols[i % cols.length];
      rrPath(ctx, x, -WALL_FACE + 22, pw - 12, 34, 5); ctx.fillStyle = col; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.save(); rrPath(ctx, x, -WALL_FACE + 22, pw - 12, 34, 5); ctx.clip(); ctx.fillStyle = 'rgba(0,0,0,0.16)'; for (let k = 0; k < 8; k++) { ctx.beginPath(); ctx.moveTo(x + k * 30, -WALL_FACE + 56); ctx.lineTo(x + k * 30 + 14, -WALL_FACE + 56); ctx.lineTo(x + k * 30 + 34, -WALL_FACE + 22); ctx.lineTo(x + k * 30 + 20, -WALL_FACE + 22); ctx.fill(); } ctx.restore();
      ctx.font = '26px Bangers, Impact'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 5; ctx.lineJoin = 'round';
      ctx.strokeText(ADS[i % ADS.length], x + (pw - 12) / 2, -WALL_FACE + 40); ctx.fillText(ADS[i % ADS.length], x + (pw - 12) / 2, -WALL_FACE + 40);
    }
    // logements des pads (dessinés en dynamique par-dessus)
    for (const p of PADS) if (p.wall === 'top') { rrPath(ctx, p.x - p.w / 2 - 6, -WALL_FACE + 18, p.w + 12, 42, 7); ctx.fillStyle = '#20262d'; ctx.fill(); ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    ctx.fillStyle = '#4d5760'; ctx.fillRect(wx0, -12, wx1 - wx0, 12);
    ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.fillRect(wx0, -12, wx1 - wx0, 3);
    for (let x = wx0 + 20; x < wx1; x += 60) { ctx.fillStyle = 'rgba(214,226,236,0.5)'; ctx.beginPath(); ctx.arc(x, -6, 2.6, 0, TAU); ctx.fill(); }
  }

  // ---------------------------------------------------------------- mur proche + silhouettes
  _buildFront(tL, tR) {
    const f = (this.front = mkCanvas(X0, FR_Y0, X1, FR_Y1)), ctx = f.ctx, rnd = mulberry(23);
    const wx0 = -76, wx1 = W + 76;
    // dessus du mur (lèvre)
    ctx.fillStyle = OUT; ctx.fillRect(wx0, H - 4, wx1 - wx0, 100);
    ctx.fillStyle = '#c9cfd3'; ctx.fillRect(wx0, H, wx1 - wx0, 20);
    ctx.fillStyle = 'rgba(255,255,255,0.4)'; ctx.fillRect(wx0, H, wx1 - wx0, 4);
    ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.fillRect(wx0, H + 17, wx1 - wx0, 3);
    // face avant
    ctx.fillStyle = '#5f6a74'; ctx.fillRect(wx0, H + 20, wx1 - wx0, 62);
    const pw = 190;
    for (let i = 0, x = wx0 + 96; x < wx1 - 20; i++, x += pw) {
      const cols = [PAL.steel, tR.main, PAL.mustard, tL.main, PAL.pink];
      rrPath(ctx, x, H + 30, pw - 12, 34, 5); ctx.fillStyle = cols[i % cols.length]; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      ctx.font = '26px Bangers, Impact'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = PAL.cream; ctx.strokeStyle = OUT; ctx.lineWidth = 5; ctx.lineJoin = 'round';
      const t = ADS[(i + 3) % ADS.length]; ctx.strokeText(t, x + (pw - 12) / 2, H + 48); ctx.fillText(t, x + (pw - 12) / 2, H + 48);
    }
    ctx.fillStyle = '#39424b'; ctx.fillRect(wx0, H + 70, wx1 - wx0, 12);
    ctx.fillStyle = OUT; ctx.fillRect(wx0, H + 80, wx1 - wx0, 4);
    // côtés : murs d'extrémité prolongés vers le bas
    // silhouettes de spectateurs au premier plan
    const g = ctx.createLinearGradient(0, H + 84, 0, FR_Y1); g.addColorStop(0, '#1a1017'); g.addColorStop(1, '#0c070b');
    ctx.fillStyle = g; ctx.fillRect(X0, H + 84, X1 - X0, FR_Y1 - H - 84);
    for (let row = 0; row < 3; row++) {
      for (let x = X0 - 20 + (row % 2) * 24; x < X1 + 20; x += 48 + rnd() * 10) {
        const y = H + 118 + row * 46 + rnd() * 8, r = 14 + rnd() * 4 + row * 2;
        const c = rnd() < 0.2 ? '#3a2233' : rnd() < 0.5 ? '#2a1a26' : '#22151f';
        ctx.fillStyle = c; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
        rrPath(ctx, x - r * 1.2, y + r * 0.8, r * 2.4, 60, 12); ctx.fill();
        if (rnd() < 0.3) { ctx.fillStyle = 'rgba(232,184,74,0.35)'; ctx.beginPath(); ctx.arc(x + r * 0.5, y - r * 0.5, r * 0.5, 0, TAU); ctx.fill(); }   // contre-jour
        ctx.strokeStyle = 'rgba(255,214,150,0.18)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, r, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke();
      }
    }
  }

  // ---------------------------------------------------------------- foule
  _buildCrowd(tL, tR) {
    const rnd = mulberry(99);
    const neutral = [PAL.salmon, PAL.sage, PAL.mustard, PAL.pink, PAL.steel, PAL.cream, '#9d7ad6', '#63d6c4'];
    this.crowd = [];
    const rows = 5;
    for (let r = 0; r < rows; r++) {
      for (let x = X0 + 10 + (r % 2) * 20; x < X1; x += 38 + rnd() * 8) {
        const inSide = x < W / 2 ? tL : tR;
        const useTeam = rnd() < 0.42;
        const col = useTeam ? inSide.main : neutral[(rnd() * neutral.length) | 0];
        const skinPool = [PAL.skin1, PAL.skin2, PAL.skin3, PAL.skin4, PAL.steel];
        const robot = rnd() < 0.22;
        this.crowd.push({
          x, y: -WALL_FACE - 14 - r * 46 + (rnd() - 0.5) * 6, row: r, col, acc: useTeam ? inSide.accent : PAL.mustard,
          skin: robot ? PAL.steel : skinPool[(rnd() * skinPool.length) | 0], robot, ph: rnd() * TAU, sp: 4 + rnd() * 5,
          hat: rnd() < 0.3 ? (rnd() < 0.5 ? 'cap' : 'flag') : rnd() < 0.15 ? 'afro' : '', side: x < W / 2 ? 0 : 1, arm: rnd(),
        });
      }
    }
  }

  // ---------------------------------------------------------------- rendu
  drawStands(ctx, view) {
    const s = this.stands;
    ctx.drawImage(s.c, s.x0, s.y0, s.w, s.h);
  }

  drawCrowd(ctx, t, excite, view, scoredSide) {
    const list = this.crowd;
    for (let i = list.length - 1; i >= 0; i--) {
      const c = list[i];
      if (c.x < view.x0 - 40 || c.x > view.x1 + 40 || c.y < view.y0 - 60 || c.y > view.y1) continue;
      if (this.low && (c.row > 2 || (i & 1))) continue;
      const cheer = scoredSide === c.side ? Math.min(1.4, excite + 0.5) : excite * (scoredSide >= 0 ? 0.45 : 1);
      const amp = 2 + cheer * 11, bob = Math.abs(Math.sin(t * c.sp * (0.5 + cheer * 0.6) + c.ph)) * amp;
      const y = c.y - bob;
      ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.lineJoin = 'round';
      // bras levés
      const armsUp = cheer > 0.35 + c.arm * 0.5;
      ctx.lineCap = 'round';
      ctx.save(); ctx.translate(c.x, 0);
      if (armsUp) { const w = Math.sin(t * 10 + c.ph) * 6; for (const sx of [-1, 1]) { ctx.strokeStyle = OUT; ctx.lineWidth = 10; ctx.beginPath(); ctx.moveTo(sx * 9, y - 6); ctx.lineTo(sx * 15, y - 34 + w * sx); ctx.stroke(); ctx.strokeStyle = c.col; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(sx * 9, y - 6); ctx.lineTo(sx * 15, y - 34 + w * sx); ctx.stroke(); ctx.fillStyle = c.skin; ctx.beginPath(); ctx.arc(sx * 15, y - 36 + w * sx, 4.5, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); } }
      // corps
      rrPath(ctx, -12, y - 12, 24, 26, 8); ctx.fillStyle = c.col; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      // tête
      if (c.robot) { rrPath(ctx, -10, y - 32, 20, 20, 6); ctx.fillStyle = c.skin; ctx.fill(); ctx.stroke(); ctx.fillStyle = c.acc; ctx.fillRect(-7, y - 24, 14, 5); }
      else { ctx.beginPath(); ctx.arc(0, y - 21, 10.5, 0, TAU); ctx.fillStyle = c.skin; ctx.fill(); ctx.stroke(); ctx.fillStyle = OUT; ctx.fillRect(-5, y - 23, 3, 3); ctx.fillRect(3, y - 23, 3, 3); if (cheer > 0.4) { ctx.beginPath(); ctx.ellipse(0, y - 15, 3.5, 2.5 + cheer * 1.5, 0, 0, TAU); ctx.fill(); } }
      if (c.hat === 'cap') { ctx.beginPath(); ctx.arc(0, y - 24, 10.5, Math.PI, TAU); ctx.fillStyle = c.acc; ctx.fill(); ctx.stroke(); ctx.fillRect(2, y - 25, 14, 4); }
      else if (c.hat === 'afro') { ctx.beginPath(); ctx.arc(0, y - 28, 12, 0, TAU); ctx.fillStyle = '#231512'; ctx.fill(); ctx.stroke(); }
      else if (c.hat === 'flag') { ctx.strokeStyle = OUT; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(12, y - 10); ctx.lineTo(12, y - 52); ctx.stroke(); ctx.fillStyle = c.acc; ctx.beginPath(); const fw = Math.sin(t * 7 + c.ph) * 4; ctx.moveTo(12, y - 52); ctx.lineTo(34, y - 46 + fw); ctx.lineTo(12, y - 38); ctx.closePath(); ctx.fill(); ctx.stroke(); }
      ctx.restore();
      // flashs d'appareils photo dans les tribunes pendant les grands moments
      if (cheer > 0.9 && ((Math.floor(t * 7) + i * 13) % 29 === 0)) {
        const fl = 1 - ((t * 7) % 1);
        ctx.save(); ctx.translate(c.x, y - 34); ctx.globalAlpha = fl; ctx.fillStyle = '#fff';
        ctx.beginPath(); for (let k = 0; k < 8; k++) { const rr = k % 2 ? 4 : 15, a = k * Math.PI / 4; k ? ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
        ctx.closePath(); ctx.fill(); ctx.restore();
      }
    }
  }

  drawArena(ctx) { const a = this.arena; ctx.drawImage(a.c, a.x0, a.y0, a.w, a.h); }
  drawFront(ctx) { const f = this.front; ctx.drawImage(f.c, f.x0, f.y0, f.w, f.h); }

  // pads lumineux : sur le mur du fond + bandes au sol
  drawPads(ctx, pads, t, teamColors) {
    for (const p of pads) {
      const col = p.owner < 0 ? null : teamColors[p.owner];
      const fl = p.flash;
      if (p.wall === 'top') {
        rrPath(ctx, p.x - p.w / 2, -WALL_FACE + 22, p.w, 34, 5);
        ctx.fillStyle = col ? col : '#39424b'; ctx.fill();
        if (fl > 0) { ctx.fillStyle = `rgba(255,255,255,${fl})`; ctx.fill(); }
        ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      }
      // bande au sol
      const y = p.wall === 'top' ? 0 : H - 16;
      rrPath(ctx, p.x - p.w / 2, y, p.w, 16, 4);
      ctx.fillStyle = col ? col : 'rgba(20,26,34,0.75)'; ctx.fill();
      if (fl > 0) { ctx.fillStyle = `rgba(255,255,255,${fl})`; ctx.fill(); }
      ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
      // étoile
      ctx.save(); ctx.translate(p.x, y + 8); ctx.beginPath();
      for (let i = 0; i < 10; i++) { const r = i % 2 ? 3.2 : 7.5, a = -Math.PI / 2 + i * Math.PI / 5; i ? ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r) : ctx.moveTo(Math.cos(a) * r, Math.sin(a) * r); }
      ctx.closePath(); ctx.fillStyle = col ? '#fff' : 'rgba(255,255,255,0.35)'; ctx.fill(); ctx.restore();
    }
  }

  // Éléments arrière de la cage (avant les joueurs) : filet latéral lointain + montants arrière + traverse haute
  drawGoalBack(ctx, side, team, glow) {
    ctx.save();
    if (side > 0) { ctx.translate(W, 0); ctx.scale(-1, 1); }
    const gy0 = CY - GOAL_H / 2, gy1 = CY + GOAL_H / 2;
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    // barre arrière + montants arrière
    const pole = (x, y, h, w) => { ctx.strokeStyle = OUT; ctx.lineWidth = w + 5; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y - h); ctx.stroke(); ctx.strokeStyle = PAL.cream; ctx.lineWidth = w; ctx.stroke(); };
    pole(-GOAL_D, gy0, GOAL_TOP, 7); pole(-GOAL_D, gy1, GOAL_TOP, 7);
    // rails hauts + barre du fond
    const bar = (x0, y0, x1, y1, w) => { ctx.strokeStyle = OUT; ctx.lineWidth = w + 5; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); ctx.strokeStyle = PAL.cream; ctx.lineWidth = w; ctx.stroke(); };
    bar(-GOAL_D, gy0 - GOAL_TOP, 0, gy0 - GOAL_TOP, 7);
    bar(-GOAL_D, gy0 - GOAL_TOP, -GOAL_D, gy1 - GOAL_TOP, 7);
    if (glow > 0) {
      ctx.globalCompositeOperation = 'lighter';
      const g = ctx.createRadialGradient(-GOAL_D / 2, CY, 10, -GOAL_D / 2, CY, 300); g.addColorStop(0, team.light); g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.globalAlpha = glow * 0.85; ctx.fillStyle = g; ctx.fillRect(-GOAL_D - 200, CY - 320, 600, 640); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    }
    ctx.restore();
  }

  // Éléments avant de la cage (après les joueurs) : montants avant, traverse, filet latéral proche
  drawGoalFront(ctx, side, team, flash, t) {
    ctx.save();
    if (side > 0) { ctx.translate(W, 0); ctx.scale(-1, 1); }
    const gy0 = CY - GOAL_H / 2, gy1 = CY + GOAL_H / 2;
    ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    // filet latéral proche (translucide)
    ctx.save(); ctx.beginPath(); ctx.rect(-GOAL_D, gy1 - GOAL_TOP, GOAL_D, GOAL_TOP); ctx.clip();
    ctx.fillStyle = 'rgba(20,14,24,0.30)'; ctx.fillRect(-GOAL_D, gy1 - GOAL_TOP, GOAL_D, GOAL_TOP);
    ctx.strokeStyle = 'rgba(246,239,223,0.42)'; ctx.lineWidth = 1.6;
    for (let x = -GOAL_D; x <= 0; x += 14) { ctx.beginPath(); ctx.moveTo(x, gy1 - GOAL_TOP); ctx.lineTo(x, gy1); ctx.stroke(); }
    for (let y = gy1 - GOAL_TOP; y <= gy1; y += 14) { ctx.beginPath(); ctx.moveTo(-GOAL_D, y); ctx.lineTo(0, y); ctx.stroke(); }
    ctx.restore();
    const bar = (x0, y0, x1, y1, w, col = PAL.cream) => { ctx.strokeStyle = OUT; ctx.lineWidth = w + 6; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); ctx.strokeStyle = col; ctx.lineWidth = w; ctx.stroke(); };
    // rail haut proche
    bar(-GOAL_D, gy1 - GOAL_TOP, 0, gy1 - GOAL_TOP, 7);
    // montant avant lointain, traverse, montant avant proche
    bar(0, gy0, 0, gy0 - GOAL_TOP, 9, PAL.mustard);
    bar(0, gy0 - GOAL_TOP, 0, gy1 - GOAL_TOP, 9, flash > 0 ? '#ffffff' : PAL.mustard);
    bar(0, gy1, 0, gy1 - GOAL_TOP, 9, PAL.mustard);
    // rayures de danger sur la traverse et pieds
    ctx.fillStyle = OUT; for (const y of [gy0, gy1]) { ctx.beginPath(); ctx.ellipse(0, y, 12, 7, 0, 0, TAU); ctx.fill(); ctx.fillStyle = team.accent; ctx.beginPath(); ctx.ellipse(0, y - 1, 8, 4.4, 0, 0, TAU); ctx.fill(); ctx.fillStyle = OUT; }
    // voyant lumineux
    const ly = gy0 - GOAL_TOP - 4;
    ctx.beginPath(); ctx.arc(0, ly, 8, 0, TAU); ctx.fillStyle = flash > 0 && Math.floor(t * 10) % 2 ? '#fff' : team.main; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.restore();
  }
}
