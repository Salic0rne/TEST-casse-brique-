// Dessin vectoriel procédural des personnages et accessoires (style cartoon : gros contours prune, aplats + cel-shading).
import { PAL, TAU, clamp, lerp } from './config.js';

const OUT = PAL.outline;

// ---------- helpers de forme ------------------------------------------------
export function rrPath(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

// Remplit + ombre cel (bas/droite) + lumière (haut/gauche) + contour. Le chemin doit déjà être défini par pathFn.
function cel(ctx, pathFn, bbox, fill, shade, light, lw = 3.5) {
  pathFn(); ctx.fillStyle = fill; ctx.fill();
  if (shade || light) {
    ctx.save(); pathFn(); ctx.clip();
    if (shade) { ctx.fillStyle = shade; ctx.globalAlpha = 0.55; ctx.beginPath(); ctx.ellipse(bbox.x + bbox.w * 0.78, bbox.y + bbox.h * 0.95, bbox.w * 0.75, bbox.h * 0.55, 0, 0, TAU); ctx.fill(); ctx.globalAlpha = 1; }
    if (light) { ctx.fillStyle = light; ctx.globalAlpha = 0.6; ctx.beginPath(); ctx.ellipse(bbox.x + bbox.w * 0.28, bbox.y + bbox.h * 0.16, bbox.w * 0.32, bbox.h * 0.13, -0.3, 0, TAU); ctx.fill(); ctx.globalAlpha = 1; }
    ctx.restore();
  }
  ctx.lineWidth = lw; ctx.strokeStyle = OUT; ctx.lineJoin = 'round'; pathFn(); ctx.stroke();
}
export function rrCel(ctx, x, y, w, h, r, fill, shade, light, lw = 3.5) {
  cel(ctx, () => rrPath(ctx, x, y, w, h, r), { x, y, w, h }, fill, shade, light, lw);
}
export function circCel(ctx, cx, cy, r, fill, shade, light, lw = 3.5) {
  cel(ctx, () => { ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); }, { x: cx - r, y: cy - r, w: r * 2, h: r * 2 }, fill, shade, light, lw);
}
export function polyCel(ctx, pts, fill, shade, light, lw = 3.5) {
  let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
  for (const [x, y] of pts) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  cel(ctx, () => { ctx.beginPath(); pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath(); }, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, fill, shade, light, lw);
}
// Membre : double trait (contour puis couleur) avec petit fléchi.
function limb(ctx, x0, y0, x1, y1, w, col, bx = 0, by = 0) {
  const mx = (x0 + x1) / 2 + bx, my = (y0 + y1) / 2 + by;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.strokeStyle = OUT; ctx.lineWidth = w + 7; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo(mx, my, x1, y1); ctx.stroke();
  ctx.strokeStyle = col; ctx.lineWidth = w; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.quadraticCurveTo(mx, my, x1, y1); ctx.stroke();
}
function line(ctx, x0, y0, x1, y1, w, col = OUT) { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke(); }
function shadeColor(hex, k) {
  const n = parseInt(hex.slice(1), 16); let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  if (k < 0) { r *= 1 + k; g *= 1 + k; b *= 1 + k; } else { r += (255 - r) * k; g += (255 - g) * k; b += (255 - b) * k; }
  return `rgb(${r | 0},${g | 0},${b | 0})`;
}
export { shadeColor };

// ---------- humanoïdes (joueurs de champ) ---------------------------------------
// pose: { t, phase, run(0..1), flip, hasBall, charge(0..1), state, sq, stunT, celebrate, blink, speedFx }
export function drawHumanoid(ctx, team, vi, pose, shirt) {
  const robot = team.kind === 'robot';
  const skin = team.skin[vi % team.skin.length], hair = team.hair[vi % team.hair.length], gear = team.headgear[vi % team.headgear.length];
  const main = team.main, dark = team.dark, light = team.light, acc = team.accent, accD = team.accentDark;
  const hipY = robot ? -52 : -37, torsoH = robot ? 38 : 35, shY = hipY - torsoH, headY = shY - (robot ? 22 : 21);
  const run = pose.run, ph = pose.phase, st = pose.state;

  ctx.save();
  ctx.scale(pose.flip ? -1 : 1, 1);
  if (pose.sq) ctx.scale(1 + pose.sq, 1 - pose.sq);

  // transformation d'état
  let bob = Math.abs(Math.sin(ph)) * 3.2 * run + Math.sin(pose.t * 3.1 + vi) * 1.2 * (1 - run);
  let lean = 0.12 * run;
  let legsMode = 'run';
  if (st === 'slide') { ctx.translate(-4, -8); ctx.rotate(-1.28); ctx.translate(0, 18); legsMode = 'slide'; bob = 0; lean = 0; }
  else if (st === 'stun') {
    const g = clamp((pose.stunT - 0.0) / 0.35, 0, 1); // 0 = se relève
    const ang = -1.5 * Math.min(1, g);
    ctx.translate(0, 0); ctx.rotate(ang); ctx.translate(-2 * g, 18 * g); legsMode = 'limp'; bob = 0; lean = 0;
  } else if (st === 'jump') { legsMode = 'jump'; bob = 0; }
  else if (st === 'celebrate') { legsMode = 'jump'; bob = 0; }
  ctx.translate(0, -bob);
  if (lean) { ctx.translate(0, hipY); ctx.rotate(lean); ctx.translate(0, -hipY); }
  if (st === 'sad') { ctx.translate(0, hipY); ctx.scale(1, 0.94); ctx.rotate(0.06); ctx.translate(0, -hipY); }

  const stride = 15 * run + 6;
  const legPose = (i) => {
    const p2 = ph + i * Math.PI;
    let fx, fy;
    if (legsMode === 'run') { fx = Math.sin(p2) * stride * (run > 0.05 ? 1 : 0) + (i ? 7 : -7) * (1 - run); fy = -Math.max(0, Math.cos(p2)) * 11 * run; }
    else if (legsMode === 'jump') { fx = (i ? 9 : -9); fy = -18 - i * 4; }
    else if (legsMode === 'slide') { fx = i ? 30 : 22; fy = i ? 6 : -6; }
    else { fx = i ? 14 : -10; fy = i ? -6 : 0; }
    return [fx, fy];
  };

  // bras arrière
  const armPose = (i) => {
    const p2 = ph + (1 - i) * Math.PI;
    let hx = 6 + Math.sin(p2) * 13 * run, hy = 30 - Math.abs(Math.cos(p2)) * 3 * run;
    if (pose.hasBall) { hx = 24 + i * 6; hy = 20 + i * 8; }
    if (pose.charge > 0 && i === 1) { hx = -22 - pose.charge * 8; hy = 10 - pose.charge * 6; }
    if (st === 'celebrate') { hx = 12 + i * 10; hy = -16 + Math.sin(pose.t * 14 + i * 2) * 6; }
    if (st === 'jump') { hx = 14 + i * 6; hy = -10; }
    if (st === 'slide') { hx = 14; hy = 14; }
    if (st === 'stun') { hx = -10 + i * 20; hy = 24 + Math.sin(pose.t * 9 + i) * 4; }
    if (st === 'sad') { hx = 2; hy = 34; }
    return [hx, hy];
  };
  const drawArm = (i) => {
    const sx = i ? 12 : -10, sy = shY + 8;
    const [hx, hy] = armPose(i);
    const ex = sx + hx, ey = sy + hy;
    limb(ctx, sx, sy, ex, ey, robot ? 10 : 13, robot ? PAL.steel : main, robot ? 0 : -3, 3);
    if (robot) { ctx.beginPath(); ctx.arc((sx + ex) / 2, (sy + ey) / 2, 5, 0, TAU); ctx.fillStyle = PAL.steelDark; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    // gros gant mécanique
    const gs = robot ? 0.9 : 1;
    ctx.save(); ctx.translate(ex, ey);
    rrCel(ctx, -10 * gs, -10 * gs, 22 * gs, 21 * gs, 7 * gs, acc, accD, PAL.cream, 3.2);
    line(ctx, -2 * gs, -8 * gs, -2 * gs, 6 * gs, 2, accD); line(ctx, 4 * gs, -8 * gs, 4 * gs, 6 * gs, 2, accD);
    rrCel(ctx, -12 * gs, -4 * gs, 8 * gs, 12 * gs, 3, PAL.steelDark, null, null, 2.5);
    ctx.restore();
  };
  drawArm(0);

  // jambes
  for (let i = 0; i < 2; i++) {
    const [fx, fy] = legPose(i);
    const hx = i ? 7 : -7, kneeBend = st === 'slide' ? -2 : 7;
    limb(ctx, hx, hipY, fx, fy - 5, robot ? 11 : 14, robot ? PAL.steel : (i ? dark : shadeColor(dark, -0.2)), kneeBend, 0);
    if (robot) { ctx.beginPath(); ctx.arc((hx + fx) / 2 + kneeBend * 0.5, (hipY + fy) / 2, 6, 0, TAU); ctx.fillStyle = PAL.steelDark; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke(); }
    // chaussure
    ctx.save(); ctx.translate(fx, fy);
    rrCel(ctx, -9, -8, 24, 13, 6, robot ? PAL.floorDark : '#5b4a4f', null, robot ? PAL.steelLight : '#8a7a7f', 3);
    ctx.fillStyle = acc; ctx.fillRect(-7, 3, 20, 3);
    ctx.restore();
  }

  // torse
  {
    const tw = robot ? 40 : 42, bw = robot ? 32 : 36;
    const pts = [[-tw / 2, shY], [tw / 2, shY], [bw / 2, hipY + 3], [-bw / 2, hipY + 3]];
    ctx.save(); ctx.translate(0, 0);
    ctx.beginPath(); ctx.moveTo(-tw / 2 + 4, shY); ctx.lineTo(tw / 2 - 4, shY); ctx.quadraticCurveTo(tw / 2, shY, tw / 2 - 1, shY + 6);
    ctx.lineTo(bw / 2, hipY - 2); ctx.quadraticCurveTo(bw / 2, hipY + 4, bw / 2 - 5, hipY + 4); ctx.lineTo(-bw / 2 + 5, hipY + 4);
    ctx.quadraticCurveTo(-bw / 2, hipY + 4, -bw / 2, hipY - 2); ctx.lineTo(-tw / 2 + 1, shY + 6); ctx.quadraticCurveTo(-tw / 2, shY, -tw / 2 + 4, shY);
    ctx.closePath();
    const pth = new Path2D(); ctx.save();
    ctx.fillStyle = main; ctx.fill();
    ctx.clip();
    // ombre
    ctx.fillStyle = dark; ctx.globalAlpha = 0.5; ctx.fillRect(4, shY, 30, torsoH + 8); ctx.globalAlpha = 1;
    // bande accent en biais
    ctx.fillStyle = acc; ctx.beginPath(); ctx.moveTo(-tw / 2, shY + 8); ctx.lineTo(-tw / 2 + 12, shY + 2); ctx.lineTo(tw / 2, shY + torsoH - 10); ctx.lineTo(tw / 2, shY + torsoH + 2); ctx.closePath();
    ctx.globalAlpha = 0.95; ctx.fill(); ctx.globalAlpha = 1;
    // ceinture
    ctx.fillStyle = shadeColor(dark, -0.25); ctx.fillRect(-tw / 2, hipY - 5, tw, 9);
    ctx.fillStyle = acc; ctx.fillRect(-4, hipY - 5, 8, 9);
    ctx.restore();
    ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.stroke();
    // numéro
    if (shirt !== undefined && shirt !== null) {
      ctx.font = '19px Bangers, Impact, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.strokeText(String(shirt), -2, shY + 15); ctx.fillStyle = PAL.cream; ctx.fillText(String(shirt), -2, shY + 15);
    }
    ctx.restore();
  }

  // épaulières (élément fort de la DA)
  for (const sx of [-15, 15]) {
    ctx.save(); ctx.translate(sx, shY + 5);
    rrCel(ctx, -9, -8, 19, 15, 7, acc, accD, PAL.cream, 3);
    ctx.restore();
  }

  // tête
  const hx = 3;
  drawHead(ctx, { robot, gear, skin, hair, main, dark, acc, accD, light }, hx, headY, pose, st);

  drawArm(1);
  ctx.restore();
}

function drawHead(ctx, s, hx, hy, pose, st) {
  const { robot, gear, skin, hair, main, dark, acc, accD } = s;
  const r = robot ? 17 : 19;
  // éléments derrière la tête
  if (gear === 'afro') { circCel(ctx, hx - 3, hy - 6, 26, hair, shadeColor(hair, 0.0), '#4a4a55', 3.5); }
  if (gear === 'ponytail') {
    const sw = Math.sin(pose.t * 9 + pose.phase) * 4 * (0.3 + pose.run) ;
    limb(ctx, hx - 10, hy - 6, hx - 30 - sw, hy + 10 + sw * 0.5, 10, hair, -8, 6);
  }
  if (robot) {
    // cou + tête dôme
    rrCel(ctx, hx - 6, hy + 8, 12, 10, 3, PAL.steelDark, null, null, 2.5);
    ctx.beginPath(); ctx.moveTo(hx - 19, hy + 10); ctx.quadraticCurveTo(hx - 21, hy - 20, hx, hy - 20); ctx.quadraticCurveTo(hx + 21, hy - 20, hx + 19, hy + 10);
    ctx.quadraticCurveTo(hx, hy + 14, hx - 19, hy + 10); ctx.closePath();
    ctx.fillStyle = PAL.steel; ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = PAL.steelDark; ctx.globalAlpha = 0.5; ctx.beginPath(); ctx.ellipse(hx + 16, hy + 12, 20, 20, 0, 0, TAU); ctx.fill(); ctx.globalAlpha = 0.7; ctx.fillStyle = PAL.steelLight; ctx.beginPath(); ctx.ellipse(hx - 8, hy - 14, 10, 4, -0.3, 0, TAU); ctx.fill(); ctx.restore();
    ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.stroke();
    // visière
    rrCel(ctx, hx - 2, hy - 7, 24, 11, 5, '#1c2430', null, null, 2.5);
    const blink = pose.blink ? 0.2 : 1;
    ctx.fillStyle = st === 'stun' ? '#ff6a6a' : acc; ctx.shadowColor = acc; ctx.shadowBlur = 8;
    rrPath(ctx, hx + 2, hy - 4, 17, 5 * blink + 1, 2.5); ctx.fill(); ctx.shadowBlur = 0;
    if (gear === 'botcap') {
      polyCel(ctx, [[hx - 18, hy - 12], [hx - 14, hy - 27], [hx + 4, hy - 31], [hx + 18, hy - 22], [hx + 34, hy - 14], [hx + 30, hy - 9], [hx + 10, hy - 12]], main, dark, s.light, 3.2);
      ctx.fillStyle = acc; ctx.beginPath(); ctx.arc(hx + 2, hy - 22, 4.5, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke();
    } else { line(ctx, hx - 4, hy - 20, hx - 8, hy - 32, 3); circCel(ctx, hx - 8, hy - 33, 3.5, acc, null, null, 2); }
    return;
  }
  // oreille + tête
  circCel(ctx, hx - 12, hy + 1, 5.5, skin, shadeColor(skin, -0.25), null, 2.5);
  circCel(ctx, hx, hy, r, skin, shadeColor(skin, -0.22), shadeColor(skin, 0.4), 3.5);
  // visage
  const ex = hx + 8, ey = hy - 1;
  const blink = pose.blink;
  for (let i = 0; i < 2; i++) {
    const x = ex + i * 10.5 - (i ? 1 : 0);
    if (st === 'stun') { line(ctx, x - 3.5, ey - 3.5, x + 3.5, ey + 3.5, 2.2); line(ctx, x + 3.5, ey - 3.5, x - 3.5, ey + 3.5, 2.2); continue; }
    if (st === 'celebrate') { ctx.strokeStyle = OUT; ctx.lineWidth = 2.6; ctx.beginPath(); ctx.arc(x, ey + 1, 4, Math.PI * 1.05, Math.PI * 1.95); ctx.stroke(); continue; }
    if (blink) { line(ctx, x - 3.5, ey, x + 3.5, ey, 2.4); continue; }
    ctx.fillStyle = '#fffdf6'; ctx.beginPath(); ctx.ellipse(x, ey, 4.4, 5.6, 0, 0, TAU); ctx.fill(); ctx.lineWidth = 1.8; ctx.strokeStyle = OUT; ctx.stroke();
    ctx.fillStyle = i === 0 && st === 'run' ? '#2a3a6b' : '#22314f'; ctx.beginPath(); ctx.arc(x + 1.4, ey + 0.5, 2.7, 0, TAU); ctx.fill();
  }
  // sourcils fâchés
  if (st !== 'celebrate' && st !== 'stun') {
    const sad = st === 'sad';
    for (let i = 0; i < 2; i++) { const x = ex + i * 10.5 - (i ? 1 : 0); line(ctx, x - 5, ey - (sad ? 12 : 8) - (sad ? 0 : (i ? 3 : -1)) , x + 4.5, ey - (sad ? 7 : 8) - (sad ? 0 : (i ? -1 : 3)), 3); }
  }
  // bouche
  ctx.strokeStyle = OUT; ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.beginPath();
  if (st === 'celebrate') { ctx.fillStyle = '#7a2a2a'; ctx.ellipse(hx + 12, hy + 10, 5.5, 4.5, 0, 0, TAU); ctx.fill(); ctx.stroke(); }
  else if (pose.charge > 0.2 || st === 'slide') { ctx.moveTo(hx + 7, hy + 10); ctx.lineTo(hx + 17, hy + 9); ctx.stroke(); line(ctx, hx + 9, hy + 10.5, hx + 9, hy + 13, 2); line(ctx, hx + 12, hy + 10.5, hx + 12, hy + 13, 2); }
  else if (st === 'sad') { ctx.moveTo(hx + 8, hy + 12); ctx.quadraticCurveTo(hx + 12, hy + 8, hx + 17, hy + 12); ctx.stroke(); }
  else { ctx.moveTo(hx + 8, hy + 10.5); ctx.quadraticCurveTo(hx + 12, hy + 12, hx + 17, hy + 9.5); ctx.stroke(); }
  // nez
  ctx.beginPath(); ctx.moveTo(hx + 19, hy + 2); ctx.lineTo(hx + 22, hy + 6); ctx.lineTo(hx + 18, hy + 6.5); ctx.strokeStyle = shadeColor(skin, -0.5); ctx.lineWidth = 2; ctx.stroke();

  // couvre-chef
  if (gear === 'cap') {
    ctx.beginPath(); ctx.moveTo(hx - 19, hy - 3); ctx.quadraticCurveTo(hx - 18, hy - 27, hx + 2, hy - 26); ctx.quadraticCurveTo(hx + 19, hy - 25, hx + 20, hy - 6); ctx.closePath();
    ctx.fillStyle = acc; ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = accD; ctx.globalAlpha = 0.45; ctx.beginPath(); ctx.ellipse(hx + 16, hy - 2, 16, 20, 0, 0, TAU); ctx.fill(); ctx.restore();
    ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.stroke();
    polyCel(ctx, [[hx + 8, hy - 8], [hx + 34, hy - 5], [hx + 32, hy - 1], [hx + 8, hy - 3]], acc, accD, null, 3);
    ctx.fillStyle = PAL.cream; ctx.beginPath(); ctx.arc(hx + 3, hy - 17, 3.2, 0, TAU); ctx.fill(); ctx.lineWidth = 1.5; ctx.strokeStyle = OUT; ctx.stroke();
    // mèche
    limb(ctx, hx - 15, hy - 3, hx - 20, hy + 12, 6, hair, -2, 0);
  } else if (gear === 'helmet') {
    ctx.beginPath(); ctx.moveTo(hx - 21, hy + 3); ctx.quadraticCurveTo(hx - 22, hy - 28, hx + 2, hy - 27); ctx.quadraticCurveTo(hx + 22, hy - 25, hx + 21, hy - 4); ctx.lineTo(hx - 21, hy + 3); ctx.closePath();
    ctx.fillStyle = main; ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = dark; ctx.globalAlpha = 0.5; ctx.beginPath(); ctx.ellipse(hx + 18, hy, 16, 26, 0, 0, TAU); ctx.fill(); ctx.globalAlpha = 0.6; ctx.fillStyle = s.light; ctx.beginPath(); ctx.ellipse(hx - 6, hy - 20, 9, 4, -0.4, 0, TAU); ctx.fill(); ctx.restore();
    ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.stroke();
    rrCel(ctx, hx - 20, hy - 12, 42, 7, 3, acc, accD, null, 2.5);
    line(ctx, hx - 2, hy - 27, hx - 2, hy - 12, 3, OUT);
  }
}

// ---------- gardiens : gros mécas ----------------------------------------------
// pose: { t, phase, flip, hasBall, reach:[dx,dy] (bras pod), stunT, jump, moveY }
export function drawKeeper(ctx, team, pose) {
  ctx.save();
  ctx.scale(pose.flip ? -1 : 1, 1);
  const kind = team.keeper;
  if (pose.sq) ctx.scale(1 + pose.sq, 1 - pose.sq);
  if (pose.state === 'stun') { ctx.rotate(Math.sin(pose.t * 20) * 0.06); }
  const fn = { box: keeperBox, bug: keeperBug, pod: keeperPod, crab: keeperCrab }[kind] || keeperBox;
  fn(ctx, team, pose);
  ctx.restore();
}

function footSlab(ctx, x, y, w = 34, h = 14) { rrCel(ctx, x - w / 2, y - h, w, h, 4, '#43393f', null, '#7d6f76', 3.2); }
function bolt(ctx, x, y, r = 5) { ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fillStyle = PAL.steel; ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke(); line(ctx, x - r * 0.6, y, x + r * 0.6, y, 1.6); }

function keeperBox(ctx, team, p) {
  const m = team.main, d = team.dark, l = team.light, a = team.accent;
  const ph = p.phase, run = Math.min(1, Math.abs(p.moveY || 0));
  const bob = Math.abs(Math.sin(ph)) * 4 * run + Math.sin(p.t * 2) * 1.5;
  // pattes arrière
  for (let i = 0; i < 2; i++) {
    const s = Math.sin(ph + i * Math.PI) * 16 * run, lift = Math.max(0, Math.cos(ph + i * Math.PI)) * 12 * run;
    const bx = i ? 26 : -22, hip = -62 - bob;
    limb(ctx, bx, hip, bx + s * 0.5 - 6, -34 - lift * 0.5, 22, i ? m : d, -8, 0);
    limb(ctx, bx + s * 0.5 - 6, -34 - lift * 0.5, bx + s, -14 - lift, 18, i ? l : m, 4, 0);
    bolt(ctx, bx + s * 0.5 - 6, -34 - lift * 0.5, 7);
    footSlab(ctx, bx + s + 4, -lift + 2, 38, 16);
  }
  // sacs sur le dos
  const sacks = [['#8a7a90', -46, -142, 26], ['#d1b070', -14, -152, 28], ['#6f5f75', -60, -122, 22], ['#c7a35c', 22, -150, 20]];
  for (const [c, x, y, r] of sacks) circCel(ctx, x, y - bob, r, c, shadeColor(c, -0.3), shadeColor(c, 0.35), 3.2);
  // caisson principal
  const y0 = -132 - bob;
  polyCel(ctx, [[-64, y0 + 10], [-44, y0], [46, y0], [66, y0 + 14], [66, y0 + 64], [-64, y0 + 64]], m, d, l, 4);
  // plaque avant (à droite)
  polyCel(ctx, [[18, y0 - 2], [66, y0 + 14], [66, y0 + 64], [18, y0 + 64]], shadeColor(m, 0.1), d, l, 3.5);
  // fenêtre à lames (s'ouvre quand la balle est prise)
  const open = p.hasBall ? 1 : 0;
  rrCel(ctx, 30, y0 + 14, 28, 38, 5, a, team.accentDark, null, 3);
  ctx.fillStyle = '#2b2f24'; rrPath(ctx, 34, y0 + 18, 20, 30, 3); ctx.fill();
  ctx.strokeStyle = '#4b5a3a'; ctx.lineWidth = 2.6;
  for (let i = 0; i < 5; i++) { const yy = y0 + 21 + i * 6 - open * 4; ctx.beginPath(); ctx.moveTo(35, yy); ctx.lineTo(53, yy); ctx.stroke(); }
  if (p.hasBall) { ctx.fillStyle = '#c9d1da'; ctx.beginPath(); ctx.arc(44, y0 + 33, 9, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); }
  // tuyau blanc
  rrCel(ctx, -58, y0 + 34, 76, 10, 5, '#f0f0e6', '#b8b8ac', null, 3);
  bolt(ctx, -44, y0 + 20, 4.5); bolt(ctx, -44, y0 + 54, 4.5);
  // museau/casque
  polyCel(ctx, [[-74, y0 + 26], [-62, y0 + 22], [-56, y0 + 50], [-74, y0 + 52]], a, team.accentDark, null, 3.2);
  line(ctx, -50, y0 + 6, -50, y0 + 60, 2.5, d);
}

function keeperBug(ctx, team, p) {
  const m = team.main, d = team.dark, l = team.light;
  const ph = p.phase, run = Math.min(1, Math.abs(p.moveY || 0));
  const bob = Math.sin(p.t * 2.4) * 2 + Math.abs(Math.sin(ph)) * 3 * run;
  // pattes
  const legs = [[-46, 0], [-8, 1], [30, 0], [62, 1]];
  legs.forEach(([bx, k], i) => {
    const s = Math.sin(ph + i * 1.6 + k * Math.PI) * 14 * run, lift = Math.max(0, Math.cos(ph + i * 1.6 + k * Math.PI)) * 12 * run;
    const col = k ? '#5e4b4f' : '#6f5a5e';
    const hx = bx, hy = -78 - bob;
    limb(ctx, hx, hy, hx - 16 + s * 0.4, -46 - lift * 0.4, 20, col, -10, 0);
    limb(ctx, hx - 16 + s * 0.4, -46 - lift * 0.4, hx - 6 + s, -8 - lift, 18, shadeColor(col, 0.1), 6, 0);
    bolt(ctx, hx - 16 + s * 0.4, -46 - lift * 0.4, 7);
    footSlab(ctx, hx - 4 + s, -lift + 3, 34, 15);
  });
  // carapace segmentée
  const segs = [[-96, 62, 64, 0.0], [-36, 58, 72, 0.02], [24, 56, 78, 0.05]];
  segs.forEach(([x, w, h, sk], i) => {
    const y = -138 - bob - i * 0 + (i === 0 ? 10 : i === 1 ? 0 : -2);
    polyCel(ctx, [[x, y + h * 0.35], [x + 14, y], [x + w, y - 2 + i * 2], [x + w + 6, y + h * 0.5], [x + w - 4, y + h], [x + 4, y + h - 6]], m, d, l, 4);
    line(ctx, x + 10, y + 8, x + w - 6, y + 6, 2.2, shadeColor(m, -0.3));
  });
  // écoutille ouverte avec lueur verte
  const hx = -30, hy = -172 - bob;
  ctx.save(); ctx.translate(hx, hy);
  rrCel(ctx, 0, 24, 46, 14, 3, '#3a6a3a', null, null, 3);
  ctx.fillStyle = PAL.green; rrPath(ctx, 5, 27, 36, 8, 2); ctx.fill();
  ctx.save(); ctx.translate(38, 26); ctx.rotate(-0.95 - Math.sin(p.t * 1.5) * 0.03);
  rrCel(ctx, -4, -30, 36, 30, 4, shadeColor(m, 0.05), d, l, 3.5);
  for (let i = 0; i < 4; i++) line(ctx, 2, -25 + i * 6, 26, -25 + i * 6, 2, d);
  ctx.restore(); ctx.restore();
  // tête / phare
  polyCel(ctx, [[86, -134 - bob], [122, -122 - bob], [130, -100 - bob], [118, -78 - bob], [90, -74 - bob], [84, -100 - bob]], m, d, l, 4);
  ctx.beginPath(); ctx.moveTo(108, -120 - bob); ctx.quadraticCurveTo(132, -112 - bob, 124, -92 - bob); ctx.lineTo(104, -96 - bob); ctx.closePath();
  ctx.fillStyle = '#ffe66a'; ctx.shadowColor = '#ffe66a'; ctx.shadowBlur = 16; ctx.fill(); ctx.shadowBlur = 0; ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
  line(ctx, 106, -108 - bob, 124, -104 - bob, 4, '#fff8c8');
  if (p.hasBall) { ctx.fillStyle = '#c9d1da'; ctx.beginPath(); ctx.arc(74, -92 - bob, 10, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); }
  // queue en pointe
  polyCel(ctx, [[-96, -110 - bob], [-140, -80], [-116, -84], [-96, -88]], d, null, null, 3.2);
}

function keeperPod(ctx, team, p) {
  const m = team.main, d = team.dark, l = team.light, a = team.accent;
  const ph = p.phase, run = Math.min(1, Math.abs(p.moveY || 0));
  const bob = Math.sin(p.t * 2.6) * 3 + (p.jump ? -10 : 0);
  // petits pieds
  for (let i = 0; i < 4; i++) {
    const bx = -32 + i * 21, s = Math.sin(ph + i * 1.7) * 6 * run, lift = Math.max(0, Math.cos(ph + i * 1.7)) * 6 * run;
    limb(ctx, bx, -34 - bob, bx + s, -12 - lift, 9, '#e7dff0', 0, 0);
    rrCel(ctx, bx + s - 11, -lift - 15, 24, 15, 6, i % 2 ? a : team.accentDark, null, '#c9b6ec', 3);
  }
  // bras longs (IK 2 segments) : suivent la balle
  const reach = p.reach || [60, -30];
  for (let i = 0; i < 2; i++) {
    const bx = i ? 42 : -34, by = -108 - bob;
    let tx = reach[0] * (i ? 1 : 0.6) + (i ? 20 : -40), ty = reach[1];
    tx = clamp(tx, -110, 130); ty = clamp(ty, -140, 60);
    const wig = Math.sin(p.t * 3 + i * 2) * 5;
    const dx = tx + wig, dy = ty - 20;
    const dist = Math.hypot(dx, dy) || 1, L = 70, Lc = Math.min(dist, L * 2 - 4);
    const ang = Math.atan2(dy, dx), h = Math.sqrt(Math.max(0, L * L - (Lc / 2) ** 2)) * (i ? -1 : -1);
    const ex = bx + Math.cos(ang) * Lc / 2 + Math.cos(ang + Math.PI / 2) * h * -1, ey = by + Math.sin(ang) * Lc / 2 + Math.sin(ang + Math.PI / 2) * h * -1;
    const hx = bx + Math.cos(ang) * Lc, hy = by + Math.sin(ang) * Lc;
    limb(ctx, bx, by, ex, ey, 19, '#efe5f2', 0, 0);
    ctx.beginPath(); ctx.arc(ex, ey, 11, 0, TAU); ctx.fillStyle = '#8c8298'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = OUT; ctx.stroke();
    limb(ctx, ex, ey, hx, hy, 16, '#efe5f2', 0, 0);
    // pince à 3 doigts
    ctx.save(); ctx.translate(hx, hy); ctx.rotate(ang);
    rrCel(ctx, -4, -9, 18, 18, 6, a, team.accentDark, null, 3);
    const open = p.hasBall ? 0.1 : 0.55 + Math.sin(p.t * 5 + i) * 0.1;
    for (let f = -1; f <= 1; f++) { ctx.save(); ctx.rotate(f * open); polyCel(ctx, [[12, -3], [34, -2 + f * 1], [34, 3 + f], [12, 4]], '#2a1f3a', null, null, 2.5); ctx.restore(); }
    ctx.restore();
  }
  // dôme rose
  circCel(ctx, 0, -86 - bob, 42, m, d, l, 4);
  circCel(ctx, -34, -74 - bob, 24, shadeColor(m, -0.15), d, null, 3.5);
  circCel(ctx, 34, -74 - bob, 26, shadeColor(m, -0.1), d, null, 3.5);
  circCel(ctx, 2, -100 - bob, 30, m, null, l, 3.5);
  for (const [x, y] of [[-8, -112], [10, -114], [26, -104], [-24, -102]]) { ctx.beginPath(); ctx.ellipse(x, y - bob, 4, 5, 0, 0, TAU); ctx.fillStyle = d; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); }
  // pare-chocs blanc
  rrCel(ctx, -54, -62 - bob, 108, 16, 6, '#e9eef0', '#aab4b9', '#ffffff', 3.5);
  rrCel(ctx, -58, -70 - bob, 26, 26, 6, 'rgba(233,238,240,0.0)', null, null, 3.5);
  rrCel(ctx, 32, -70 - bob, 26, 26, 6, 'rgba(233,238,240,0.0)', null, null, 3.5);
  // oeil unique
  ctx.fillStyle = '#fffdf6'; ctx.beginPath(); ctx.ellipse(28, -88 - bob, 9, 11, 0, 0, TAU); ctx.fill(); ctx.lineWidth = 2.5; ctx.strokeStyle = OUT; ctx.stroke();
  ctx.fillStyle = '#2a1f3a'; ctx.beginPath(); ctx.arc(31 + (reach[0] > 0 ? 2 : 0), -87 - bob + clamp(reach[1] / 40, -2, 2), 4.6, 0, TAU); ctx.fill();
  line(ctx, 18, -103 - bob, 38, -98 - bob, 3);
  if (p.hasBall) { ctx.fillStyle = '#c9d1da'; ctx.beginPath(); ctx.arc(52, -100 - bob, 10, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); }
}

function keeperCrab(ctx, team, p) {
  const m = '#e8b84a', d = '#a97a1e', l = '#ffe08a';
  const ph = p.phase, run = Math.min(1, Math.abs(p.moveY || 0));
  const bob = Math.sin(p.t * 3) * 2 + Math.abs(Math.sin(ph)) * 3 * run;
  // pattes-roues
  for (let i = 0; i < 4; i++) {
    const bx = -46 + i * 32 + (i > 1 ? 4 : 0), s = Math.sin(ph + i * 1.2) * 10 * run;
    limb(ctx, bx, -54 - bob, bx + s * 0.5, -30, 14, m, -6, 0);
    circCel(ctx, bx + s * 0.5, -22, 17, '#8f979f', '#5a6472', '#d4dbe2', 3.5);
    circCel(ctx, bx + s * 0.5, -22, 7, '#43393f', null, null, 2.5);
  }
  // plaques avant empilées
  for (let i = 0; i < 3; i++) polyCel(ctx, [[30 + i * 4, -66 - bob + i * 7], [84 + i * 6, -60 - bob + i * 7], [92 + i * 6, -52 - bob + i * 7], [26 + i * 4, -50 - bob + i * 7]], shadeColor(m, 0.15 - i * 0.1), d, l, 3.2);
  // corps
  polyCel(ctx, [[-58, -66 - bob], [-46, -112 - bob], [-16, -128 - bob], [26, -122 - bob], [48, -96 - bob], [52, -58 - bob], [-58, -52 - bob]], m, d, l, 4);
  // dôme + numéro
  polyCel(ctx, [[-30, -124 - bob], [-10, -142 - bob], [14, -138 - bob], [14, -122 - bob]], shadeColor(m, 0.1), d, l, 3.5);
  circCel(ctx, 0, -134 - bob, 6, '#43393f', null, null, 2);
  ctx.font = '38px Bangers, Impact, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.strokeStyle = OUT; ctx.lineWidth = 6; ctx.strokeText('3', -30, -96 - bob); ctx.fillStyle = PAL.cream; ctx.fillText('3', -30, -96 - bob);
  // bande + hublot
  rrCel(ctx, 4, -104 - bob, 40, 22, 6, '#1c2430', null, null, 3);
  ctx.fillStyle = team.accent; ctx.shadowColor = team.accent; ctx.shadowBlur = 8; rrPath(ctx, 9, -98 - bob, 30, 8, 3); ctx.fill(); ctx.shadowBlur = 0;
  if (p.hasBall) { ctx.fillStyle = '#c9d1da'; ctx.beginPath(); ctx.arc(60, -84 - bob, 10, 0, TAU); ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = OUT; ctx.stroke(); }
}

// ---------- balle d'acier ----------------------------------------------------------
export function drawBall(ctx, x, y, r, rot, glowColor, heat = 0) {
  ctx.save(); ctx.translate(x, y);
  const g = ctx.createRadialGradient(-r * 0.35, -r * 0.4, r * 0.1, 0, 0, r * 1.05);
  g.addColorStop(0, '#f4f8fb'); g.addColorStop(0.35, '#b6c1cc'); g.addColorStop(0.75, '#6d7b8c'); g.addColorStop(1, '#3d4858');
  ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fillStyle = g; ctx.fill();
  ctx.save(); ctx.clip();
  // bandes tournantes (montre la rotation)
  ctx.strokeStyle = 'rgba(30,38,52,0.55)'; ctx.lineWidth = 2.4;
  ctx.beginPath(); ctx.ellipse(0, 0, r * 0.95, r * 0.35, rot, 0, TAU); ctx.stroke();
  ctx.beginPath(); ctx.ellipse(0, 0, r * 0.35, r * 0.95, rot * 0.7 + 1, 0, TAU); ctx.stroke();
  if (heat > 0.05) { ctx.fillStyle = glowColor || '#ffb35a'; ctx.globalAlpha = heat * 0.5; ctx.fillRect(-r, -r, r * 2, r * 2); ctx.globalAlpha = 1; }
  ctx.restore();
  ctx.lineWidth = 3.4; ctx.strokeStyle = OUT; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.beginPath(); ctx.ellipse(-r * 0.36, -r * 0.42, r * 0.22, r * 0.14, -0.6, 0, TAU); ctx.fill();
  ctx.restore();
}

// ---------- jetons / power-ups -----------------------------------------------------
export const TOKEN_INFO = {
  coin: { color: '#ffd23f', dark: '#b8860b', label: '$' },
  speed: { color: '#63d6c4', dark: '#2b8a7c', label: '»' },
  power: { color: '#ff7a59', dark: '#a8371b', label: '!' },
  freeze: { color: '#9adcff', dark: '#3b7fb0', label: '*' },
};

export function drawToken(ctx, type, t, alpha = 1) {
  const info = TOKEN_INFO[type];
  ctx.save(); ctx.globalAlpha = alpha;
  if (type === 'coin') {
    const sx = Math.abs(Math.cos(t * 4));
    ctx.scale(Math.max(0.15, sx), 1);
    circCel(ctx, 0, 0, 15, info.color, info.dark, '#fff3a8', 3.5);
    ctx.beginPath(); ctx.arc(0, 0, 9.5, 0, TAU); ctx.lineWidth = 2; ctx.strokeStyle = info.dark; ctx.stroke();
    ctx.font = '17px Bangers, Impact'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = info.dark; ctx.fillText('$', 0, 1);
  } else {
    const s = 1 + Math.sin(t * 6) * 0.05;
    ctx.scale(s, s);
    // hexagone
    ctx.beginPath(); for (let i = 0; i < 6; i++) { const a = i * TAU / 6 + Math.PI / 6; const x = Math.cos(a) * 19, y = Math.sin(a) * 19; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.closePath();
    ctx.fillStyle = info.color; ctx.fill(); ctx.save(); ctx.clip(); ctx.fillStyle = info.dark; ctx.globalAlpha = alpha * 0.4; ctx.fillRect(-20, 2, 40, 20); ctx.restore();
    ctx.lineWidth = 3.5; ctx.strokeStyle = OUT; ctx.lineJoin = 'round'; ctx.stroke();
    ctx.strokeStyle = PAL.cream; ctx.fillStyle = PAL.cream; ctx.lineWidth = 3.5; ctx.lineCap = 'round';
    if (type === 'speed') { for (let i = 0; i < 2; i++) { ctx.beginPath(); ctx.moveTo(-8 + i * 8, -8); ctx.lineTo(-1 + i * 8, 0); ctx.lineTo(-8 + i * 8, 8); ctx.stroke(); } }
    else if (type === 'power') { ctx.beginPath(); ctx.moveTo(3, -11); ctx.lineTo(-7, 2); ctx.lineTo(0, 2); ctx.lineTo(-3, 11); ctx.lineTo(8, -3); ctx.lineTo(1, -3); ctx.closePath(); ctx.fill(); }
    else if (type === 'freeze') { for (let i = 0; i < 3; i++) { ctx.save(); ctx.rotate(i * TAU / 6); ctx.beginPath(); ctx.moveTo(-10, 0); ctx.lineTo(10, 0); ctx.stroke(); ctx.restore(); } }
  }
  ctx.restore();
}

// ---------- bumper dôme / portail / plot ------------------------------------------------
export function drawBumper(ctx, x, y, r, pulse, t) {
  ctx.save(); ctx.translate(x, y);
  const s = 1 + pulse * 0.22;
  // base
  ctx.beginPath(); ctx.ellipse(0, 6, r * 1.12, r * 0.62, 0, 0, TAU); ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.fill();
  ctx.scale(s, s * (1 - pulse * 0.1));
  rrCel(ctx, -r * 1.05, -8, r * 2.1, 20, 9, '#5a6472', '#2f3742', '#9aa3ad', 3.5);
  // dôme
  ctx.beginPath(); ctx.moveTo(-r, -2); ctx.bezierCurveTo(-r, -r * 1.9, r, -r * 1.9, r, -2); ctx.closePath();
  const g = ctx.createLinearGradient(-r, -r * 1.5, r, 0);
  const hot = pulse;
  g.addColorStop(0, hot > 0.1 ? '#fff6b0' : '#ffb0d0'); g.addColorStop(0.5, hot > 0.1 ? '#ffd23f' : '#ff7fb2'); g.addColorStop(1, hot > 0.1 ? '#e89a1e' : '#b34a86');
  ctx.fillStyle = g; ctx.fill(); ctx.lineWidth = 4; ctx.strokeStyle = OUT; ctx.stroke();
  ctx.fillStyle = 'rgba(255,255,255,0.75)'; ctx.beginPath(); ctx.ellipse(-r * 0.4, -r * 1.0, r * 0.28, r * 0.12, -0.5, 0, TAU); ctx.fill();
  // étoile centrale
  ctx.save(); ctx.translate(0, -r * 0.55); ctx.fillStyle = '#fff'; ctx.globalAlpha = 0.85; ctx.beginPath();
  for (let i = 0; i < 10; i++) { const rr = i % 2 ? r * 0.12 : r * 0.28, a = -Math.PI / 2 + i * Math.PI / 5; i ? ctx.lineTo(Math.cos(a) * rr, Math.sin(a) * rr) : ctx.moveTo(Math.cos(a) * rr, Math.sin(a) * rr); }
  ctx.closePath(); ctx.fill(); ctx.restore();
  ctx.restore();
}

export function drawPortal(ctx, x, y, r, t, cool) {
  ctx.save(); ctx.translate(x, y); ctx.scale(1, 0.62);
  const on = cool > 0 ? 1.4 : 1;
  ctx.beginPath(); ctx.arc(0, 0, r * 1.25, 0, TAU); ctx.fillStyle = '#20182a'; ctx.fill(); ctx.lineWidth = 5; ctx.strokeStyle = OUT; ctx.stroke();
  const g = ctx.createRadialGradient(0, 0, 2, 0, 0, r * 1.15);
  g.addColorStop(0, '#ffffff'); g.addColorStop(0.25, '#9adcff'); g.addColorStop(0.6, '#8a5cff'); g.addColorStop(1, '#3a1f7a');
  ctx.globalAlpha = 0.95; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill(); ctx.globalAlpha = 1;
  ctx.save(); ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.clip();
  ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 3; ctx.lineCap = 'round';
  for (let k = 0; k < 3; k++) {
    ctx.beginPath();
    for (let i = 0; i < 40; i++) { const a = i * 0.28 + t * 3 * on + k * TAU / 3, rr = (i / 40) * r; const px = Math.cos(a) * rr, py = Math.sin(a) * rr; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
    ctx.stroke();
  }
  ctx.restore();
  // chevrons autour
  for (let i = 0; i < 8; i++) { const a = i * TAU / 8 + t * 0.5; ctx.save(); ctx.rotate(a); ctx.translate(r * 1.14, 0); ctx.fillStyle = i % 2 ? PAL.mustard : '#2b181d'; ctx.beginPath(); ctx.moveTo(-5, -6); ctx.lineTo(6, 0); ctx.lineTo(-5, 6); ctx.closePath(); ctx.fill(); ctx.restore(); }
  ctx.restore();
}
