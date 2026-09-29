// IA : joueurs de champ (attaque, passes, tacles, replis) et gardiens. Produit un objet "input" comme le ferait un joueur humain.
import { W, H, CY, GOAL_H, GRAVITY, BUMPERS, clamp, lerp, rand, dist } from './config.js';

function segDist(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
  let t = l2 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0; t = clamp(t, 0, 1);
  return Math.hypot(px - (ax + dx * t), py - (ay + dy * t));
}

function moveTo(inp, p, tx, ty, arrive = 20) {
  const dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy);
  if (d > arrive) { const k = Math.min(1, d / 70); inp.mx = dx / d * k; inp.my = dy / d * k; }
  return d;
}

function avoid(m, p, inp, radius = 120, strength = 1.2) {
  // répulsion des adversaires proches + bumpers
  let ax = 0, ay = 0;
  for (const q of m.players) {
    if (q === p || q.team === p.team) continue;
    const dx = p.x - q.x, dy = p.y - q.y, d = Math.hypot(dx, dy);
    if (d < radius && d > 1) { const k = (1 - d / radius) * strength; ax += dx / d * k; ay += dy / d * k; }
  }
  for (const b of BUMPERS) {
    const dx = p.x - b.x, dy = p.y - b.y, d = Math.hypot(dx, dy);
    if (d < b.r + 90 && d > 1) { const k = (1 - d / (b.r + 90)) * 1.6; ax += dx / d * k; ay += dy / d * k; }
  }
  if (p.y < 70) ay += 0.8; if (p.y > H - 70) ay -= 0.8;
  inp.mx += ax; inp.my += ay;
  const l = Math.hypot(inp.mx, inp.my); if (l > 1) { inp.mx /= l; inp.my /= l; }
}

function landing(b) {
  if (b.z <= 2 && Math.abs(b.vz) < 50) return { x: b.x + b.vx * 0.22, y: b.y + b.vy * 0.22, t: 0 };
  const t = Math.min(1.6, (b.vz + Math.sqrt(Math.max(0, b.vz * b.vz + 2 * GRAVITY * Math.max(0, b.z)))) / GRAVITY);
  return { x: clamp(b.x + b.vx * t * 0.88, 30, W - 30), y: clamp(b.y + b.vy * t * 0.88, 30, H - 30), t };
}

function bestMate(m, p, t, opps, dir) {
  let best = null, bs = -1e9;
  for (const q of t.players) {
    if (q === p || q.role === 'GK' || q.stun > 0) continue;
    const d = dist(p.x, p.y, q.x, q.y);
    if (d < 130 || d > 950) continue;
    const adv = (q.x - p.x) * dir;
    if (adv < -140) continue;
    let open = 1e9;
    for (const o of opps) { if (o.stun > 0) continue; const sd = segDist(o.x, o.y, p.x, p.y, q.x, q.y); if (sd < open) open = sd; }
    let free = 1e9; for (const o of opps) { const dd = dist(o.x, o.y, q.x, q.y); if (dd < free) free = dd; }
    const score = adv * 0.5 + Math.min(free, 300) * 0.9 + Math.min(open, 120) - d * 0.12;
    if (score > bs) { bs = score; best = { q, d, lob: open < 62, open }; }
  }
  return best;
}

function passCmd(p, mate) {
  const q = mate.q, tx = q.x + q.vx * 0.35, ty = q.y + q.vy * 0.35, dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy) || 1;
  const aim = { x: dx / d, y: dy / d };
  if (mate.lob) return { lob: true, aim, power: 0.6, speed: clamp(d / 0.78, 450, 1150) };
  const sp = clamp(d * 1.6 + 450, 700, 1350);
  return { lob: false, aim, power: clamp((sp - 680) / 740, 0.05, 1) };
}

export function thinkOutfield(m, p, dt) {
  const D = m.diff(p.team), t = m.teams[p.team], o = m.teams[1 - p.team], b = m.ball, inp = p.input, ai = p.ai, dir = t.attackDir;
  inp.mx = 0; inp.my = 0; inp.turbo = false;
  const goalX = dir > 0 ? W : 0, ownX = dir > 0 ? 0 : W;
  const opps = o.players, holder = b.holder;

  // --- charge d'un tir en cours
  if (ai.charging) {
    ai.chargeLeft -= dt; inp.a = true;
    inp.mx = ai.aim.x * 0.5; inp.my = ai.aim.y * 0.5;
    if (p.stun > 0 || !p.hasBall) { ai.charging = false; inp.a = false; }
    else if (ai.chargeLeft <= 0) { ai.charging = false; inp.a = false; inp.throw = { lob: false, aim: ai.aim, power: ai.power }; }
    return;
  }
  inp.a = false;
  if (p.returnHome) { m.idleInput(p); return; }

  if (p.hasBall) {
    ai.decideT -= dt;
    const dg = Math.hypot(goalX - p.x, CY - p.y);
    let nd = 1e9;
    for (const q of opps) { if (q.stun > 0) continue; const d = dist(p.x, p.y, q.x, q.y); if (d < nd) nd = d; }
    const pressured = nd < 100;
    if (ai.decideT <= 0 || pressured) {
      ai.decideT = D.think * (0.5 + Math.random());
      const aligned = (goalX - p.x) * dir > 0;
      const rangeOK = dg < 560 + Math.random() * 240;
      let blocked = false;
      for (const q of opps) { if (q.role === 'GK') continue; if (dist(p.x, p.y, q.x, q.y) < dg && segDist(q.x, q.y, p.x, p.y, goalX, CY) < 48) blocked = true; }
      const mate = bestMate(m, p, t, opps, dir);
      if (aligned && rangeOK && (!blocked || Math.random() < 0.3)) ai.plan = 'shoot';
      else if (mate && (pressured || Math.random() < 0.38 || (dg > 1000 && Math.random() < 0.5))) { ai.plan = 'pass'; ai.mate = mate; }
      else ai.plan = 'dribble';
      if (pressured && ai.plan === 'dribble') ai.plan = mate ? 'pass' : (aligned && dg < 900 ? 'shoot' : 'dribble'); ai.mate = ai.mate || mate;
    }
    if (ai.plan === 'shoot') {
      const gk = opps[0], ty = CY + (gk.y > CY + 10 ? -1 : gk.y < CY - 10 ? 1 : (Math.random() < 0.5 ? -1 : 1)) * rand(35, 80);
      let dx = goalX - p.x, dy = ty - p.y; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      const na = (Math.random() - 0.5) * 2 * D.aimNoise, c = Math.cos(na), s = Math.sin(na);
      ai.aim = { x: dx * c - dy * s, y: dx * s + dy * c };
      ai.charging = true; ai.chargeLeft = clamp(dg / 1400, 0.18, 0.5); ai.power = clamp(0.55 + dg / 1500, 0.6, 1);
      ai.plan = 'dribble'; ai.decideT = 0.5;
    } else if (ai.plan === 'pass' && ai.mate) {
      inp.throw = passCmd(p, ai.mate); ai.plan = 'dribble'; ai.decideT = 0.7; ai.mate = null;
    } else {
      // dribble vers la cage adverse, en évitant les adversaires
      moveTo(inp, p, goalX, CY + (p.y - CY) * 0.4, 5);
      avoid(m, p, inp, 170, 1.7);
      inp.turbo = nd > 190 && p.stamina > 0.35;
    }
    return;
  }

  const isChaser = t.chasers && (t.chasers[0] === p || (holder && holder.team !== p.team && t.chasers[1] === p));
  const home = m.homeFor(p);

  if (holder && holder.team === p.team) {
    // soutien
    let tx, ty;
    if (p.role === 'FWD') {
      tx = clamp(holder.x + dir * 230, 200, W - 200);
      ty = holder.y < CY ? holder.y + 230 : holder.y - 230;
      if (p.idx === 4) ty = holder.y < CY ? CY + 200 : CY - 200;
      ty = clamp(ty, 100, H - 100);
    } else { tx = lerp(home.x, holder.x - dir * 220, 0.5); ty = lerp(home.y, holder.y, 0.25); }
    const d = moveTo(inp, p, tx, ty, 30); avoid(m, p, inp, 110, 1);
    inp.turbo = d > 320 && p.stamina > 0.4;
    return;
  }

  if (holder) {
    // défense
    if (isChaser) {
      const tx = holder.x + holder.vx * 0.18, ty = holder.y + holder.vy * 0.18;
      const d = moveTo(inp, p, tx, ty, 6);
      inp.turbo = d > 130 && p.stamina > 0.25;
      const hx = holder.x - p.x, hy = holder.y - p.y, hd = Math.hypot(hx, hy) || 1;
      if (d < 105 && p.slideCd <= 0 && p.z <= 0.01 && Math.random() < D.tackle * 0.13 && (hx * p.fx + hy * p.fy) / hd > 0.2) {
        inp.aPressed = true; inp.mx = hx / hd; inp.my = hy / hd;
      }
    } else {
      const tx = holder.x + (ownX - holder.x) * (p.role === 'DEF' ? 0.5 : 0.25), ty = lerp(holder.y, home.y, 0.5);
      const d = moveTo(inp, p, tx, ty, 30); avoid(m, p, inp, 90, 0.8);
      inp.turbo = d > 350 && p.stamina > 0.5;
    }
    return;
  }

  // balle libre
  if (b.state !== 'free') { m.idleInput(p); return; }
  const L = landing(b);
  if (isChaser) {
    const d = moveTo(inp, p, L.x, L.y, 8);
    inp.turbo = d > 220 && p.stamina > 0.3;
    if (b.z > 65 && b.z < 200 && p.z <= 0.01 && dist(p.x, p.y, b.x, b.y) < 100 && Math.random() < 0.5) inp.bPressed = true;
  } else {
    const wt = p.role === 'DEF' ? 0.22 : 0.4;
    const tx = lerp(home.x, b.x, wt), ty = lerp(home.y, b.y, 0.25);
    const d = moveTo(inp, p, tx, ty, 40); avoid(m, p, inp, 90, 0.6);
    inp.turbo = d > 400 && p.stamina > 0.6;
  }
}

export function thinkKeeper(m, p, dt) {
  const D = m.diff(p.team), t = m.teams[p.team], o = m.teams[1 - p.team], b = m.ball, inp = p.input, ai = p.ai, dir = t.attackDir;
  const gx = dir > 0 ? 0 : W, inward = dir > 0 ? 1 : -1;
  inp.mx = 0; inp.my = 0; inp.turbo = false; inp.a = false;
  if (p.returnHome) { m.idleInput(p); return; }

  if (p.hasBall) {
    ai.holdT -= dt;
    if (ai.holdT <= 0) {
      const mate = bestMate(m, p, t, o.players, dir) || null;
      if (mate) { const c = passCmd(p, mate); c.lob = c.lob || mate.d > 520; if (c.lob) c.speed = clamp(mate.d / 0.78, 450, 1150); inp.throw = c; }
      else inp.throw = { lob: true, aim: { x: inward, y: (Math.random() - 0.5) * 0.6 }, power: 0.8, speed: 900 };
    }
    return;
  }

  const sp = Math.hypot(b.vx, b.vy);
  const towards = b.state === 'free' && b.vx * inward < -150;
  let yPred;
  if (towards && Math.abs(b.x - gx) < 1400) { const tt = Math.abs(b.x - gx) / Math.max(1, Math.abs(b.vx)); yPred = b.y + b.vy * tt; if (yPred < 0) yPred = -yPred; if (yPred > H) yPred = 2 * H - yPred; }
  else yPred = CY + (b.y - CY) * 0.42;
  ai.trackY += (yPred - ai.trackY) * Math.min(1, dt / Math.max(0.02, D.keeperReact));
  const ty = clamp(ai.trackY, CY - GOAL_H / 2 + 6, CY + GOAL_H / 2 - 6);
  let tx = gx + inward * (72 + Math.max(0, 1 - Math.abs(b.y - CY) / 320) * 24);
  const dBall = dist(p.x, p.y, b.x, b.y);
  const inZone = Math.abs(b.x - gx) < 330 && Math.abs(b.y - CY) < 280;
  let closer = false; for (const q of o.players) if (dist(q.x, q.y, b.x, b.y) < dBall - 40) closer = true;
  if (b.state === 'free' && !b.holder && inZone && b.z < 90 && !closer && sp < 520) {
    moveTo(inp, p, b.x, b.y, 10);
  } else {
    if (towards && sp > 650 && Math.abs(b.x - gx) < 700) tx += inward * 40;
    moveTo(inp, p, tx, ty, 6);
  }
  if (b.z > 70 && dBall < 170 && p.z <= 0.01 && Math.random() < 0.5) inp.bPressed = true;
  // bras/pince : regarde la balle
  p.reach = [(b.x - p.x) * inward * 0.5, (b.y - p.y) * 0.5 - 40];
}
