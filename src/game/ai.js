// Team + player AI: role assignment (chaser / presser / cover), carriers that run, pass, shoot,
// go for stars and ramps, defenders that mark and slide, and a goalkeeper that reads shots.
import { FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, BALL_GRAVITY, BALL_R, STAR_XS, DIFFICULTIES, PLAYER_SPEED, RAMP_HALF } from './constants.js';
import { clamp, rand, chance, segDist, angleDiff, pick } from '../core/math.js';

const MATE_DIFF = { ...DIFFICULTIES[1], aggro: 0.55 };

export function predictBall(b, maxT = 1.6, step = 1 / 30) {
  const out = [];
  let x = b.x, y = b.y, z = Math.max(0, b.z), vx = b.vx, vy = b.vy, vz = b.vz;
  for (let t = 0; t <= maxT; t += step) {
    out.push({ t, x, y, z });
    x += vx * step; y += vy * step;
    if (z > 0 || vz > 0) {
      vz -= BALL_GRAVITY * step;
      z += vz * step;
      if (z <= 0) { z = 0; vz = vz < -120 ? -vz * 0.52 : 0; }
    }
    if (z <= 0) { const k = Math.exp(-1.1 * step); vx *= k; vy *= k; }
    if (y < BALL_R) { y = BALL_R; vy = -vy * 0.8; }
    if (y > H - BALL_R) { y = H - BALL_R; vy = -vy * 0.8; }
    if (x < BALL_R) { x = BALL_R; vx = -vx * 0.8; }
    if (x > W - BALL_R) { x = W - BALL_R; vx = -vx * 0.8; }
  }
  return out;
}

function intercept(p, path, speed) {
  for (const s of path) {
    if (s.z > 75) continue;
    const d = Math.hypot(s.x - p.x, s.y - p.y) - 26;
    if (d <= speed * s.t) return { t: s.t, x: s.x, y: s.y };
  }
  const last = path[path.length - 1];
  return { t: path.length ? last.t + Math.hypot(last.x - p.x, last.y - p.y) / speed : 9, x: last.x, y: last.y };
}

export function aiTeamUpdate(match, dt) {
  const b = match.ball;
  for (const team of match.teams) {
    const T = team.ai;
    T.t -= dt;
    if (T.t > 0) continue;
    T.t = 0.12;
    const field = team.players.filter((p) => !p.isGK && !p.grounded);
    T.presser = T.cover = T.chaser = T.support = null;
    if (b.owner && b.owner.team !== team) {
      const c = b.owner;
      const byD = field.filter((p) => !p.human).sort((a, d) => dist2(a, c) - dist2(d, c));
      T.presser = byD[0] || null;
      T.cover = byD[1] || null;
    } else if (!b.owner) {
      const path = predictBall(b, 1.8);
      T.path = path;
      const list = field.map((p) => ({ p, ic: intercept(p, path, PLAYER_SPEED * p.stats.speed) })).sort((a, d) => a.ic.t - d.ic.t);
      const ai = list.filter((e) => !e.p.human);
      if (ai[0]) { T.chaser = ai[0].p; T.chasePt = ai[0].ic; }
      if (ai[1] && ai[1].ic.t < 1.3) { T.support = ai[1].p; T.supportPt = ai[1].ic; }
    }
  }
}

function dist2(a, b) { return (a.x - b.x) ** 2 + (a.y - b.y) ** 2; }

export function aiPlayerUpdate(match, p, dt) {
  if (match.phase !== 'play') return;
  const ai = p.ai;
  ai.next -= dt;
  const diff = p.team.human ? MATE_DIFF : match.diff;
  if (ai.next <= 0) {
    ai.next = diff.react * rand(0.6, 1.4);
    think(match, p, diff);
  }
  // Steering every frame toward the current target.
  if (p.state === 'run') {
    const dx = ai.tx - p.x, dy = ai.ty - p.y;
    const d = Math.hypot(dx, dy);
    const slowR = ai.urgent ? 20 : 70;
    const sp = d < 6 ? 0 : Math.min(1, d / slowR);
    let mx = d > 0 ? (dx / d) * sp : 0, my = d > 0 ? (dy / d) * sp : 0;
    if (p.hasBall) {
      // Avoid defenders while carrying.
      for (const o of match.other(p.team).players) {
        if (o.grounded) continue;
        const ox = p.x - o.x, oy = p.y - o.y, od = Math.hypot(ox, oy);
        if (od < 170 && od > 1) { const k = ((170 - od) / 170) * 1.3; mx += (ox / od) * k; my += (oy / od) * k; }
      }
      const m = Math.hypot(mx, my) || 1;
      mx /= m; my /= m;
    }
    p.intent = { mx, my };
  } else {
    p.intent = { mx: 0, my: 0 };
  }
}

function think(match, p, diff) {
  const b = match.ball;
  const team = p.team;
  const T = team.ai;
  p.ai.urgent = false;
  if (p.state !== 'run') return;
  if (p.hasBall) return carrierThink(match, p, diff);
  if (b.owner && b.owner.team === team) return supportThink(match, p);
  if (b.owner) return defendThink(match, p, diff);
  return looseThink(match, p, diff);
}

function formationShifted(match, p, attackBias) {
  const f = match.formationPos(p);
  const b = match.ball;
  const dir = p.team.dir;
  let x = f.x + (b.x - CX) * 0.45 + dir * attackBias;
  let y = f.y + (b.y - CY) * 0.22;
  return { x: clamp(x, 60, W - 60), y: clamp(y, 50, H - 50) };
}

function carrierThink(match, p, diff) {
  const team = p.team, dir = team.dir;
  const gx = match.oppGoalX(team);
  const opps = match.other(team).players.filter((o) => !o.grounded);
  const gk = match.other(team).players.find((o) => o.isGK);
  const dx = Math.abs(gx - p.x);
  let nearest = Infinity, inFront = false;
  for (const o of opps) {
    const d = Math.hypot(o.x - p.x, o.y - p.y);
    if (d < nearest) { nearest = d; inFront = (o.x - p.x) * dir > -20; }
  }

  // Shoot
  const angleOK = Math.abs(p.y - CY) < 360;
  if ((dx < 560 && angleOK) || (dx < 820 && angleOK && chance(0.16 + diff.aggro * 0.12) && laneClear(p, { x: gx, y: CY }, opps, 45))) {
    const gkY = gk ? gk.y : CY;
    const side = gkY > CY ? -1 : 1;
    const err = (1 - diff.aim) * rand(-110, 110);
    const ty = CY + side * (GOAL_HALF - 30) + err;
    const lob = gk && Math.abs(gk.x - gx) > 110 && dx < 650 && chance(0.4);
    match.throwBall(p, { x: gx, y: ty, shot: true }, rand(0.75, 1), lob);
    return;
  }

  // Pressure → pass
  const pressured = (nearest < 125 && inFront) || nearest < 80 || p.holdT > rand(2.2, 3.4);
  if (pressured || chance(0.06)) {
    const pass = bestPass(match, p, opps);
    if (pass && (pressured || pass.score > 250)) {
      match.throwBall(p, { x: pass.m.x, y: pass.m.y, mate: pass.m }, clamp(pass.d / 900, 0.2, 0.8), pass.open < 0.5, true);
      return;
    }
  }

  // Opportunistic: stars and multiplier ramp when unpressured
  if (nearest > 200 && p.holdT > 0.4 && chance(0.3)) {
    const wallY = p.y < CY ? 0 : H;
    const row = match.stars[p.y < CY ? 'top' : 'bottom'];
    if (team.mult < 2 && Math.abs(p.x - CX) < 480 && Math.abs(p.y - wallY) < 460) {
      match.throwBall(p, { x: CX + (p.x - CX) * 0.2, y: wallY }, 0.7, false);
      return;
    }
    const targets = STAR_XS.map((sx, i) => ({ sx, i })).filter((s) => row[s.i] !== team.idx && Math.hypot(s.sx - p.x, wallY - p.y) < 520);
    if (targets.length && Math.abs(p.y - wallY) < 420) {
      const s = pick(targets);
      match.throwBall(p, { x: s.sx, y: wallY }, 0.75, false);
      return;
    }
  }

  // Run toward goal, drifting to the middle lane.
  const ty = CY + (p.y - CY) * 0.6;
  p.ai.tx = gx - dir * 140;
  p.ai.ty = ty;
  p.ai.urgent = true;
}

function laneClear(p, t, opps, r) {
  for (const o of opps) {
    if (o.isGK) continue;
    if (segDist(o.x, o.y, p.x, p.y, t.x, t.y).d < r) return false;
  }
  return true;
}

function bestPass(match, p, opps) {
  const dir = p.team.dir;
  let best = null;
  for (const m of p.team.players) {
    if (m === p || m.grounded || m.isGK) continue;
    const d = Math.hypot(m.x - p.x, m.y - p.y);
    if (d < 130 || d > 950) continue;
    let minLane = 999, mateThreat = 999;
    for (const o of opps) {
      minLane = Math.min(minLane, segDist(o.x, o.y, p.x, p.y, m.x, m.y).d);
      mateThreat = Math.min(mateThreat, Math.hypot(o.x - m.x, o.y - m.y));
    }
    const open = clamp((minLane - 20) / 70, 0, 1);
    const progress = (m.x - p.x) * dir;
    const score = progress * 0.7 + open * 260 + Math.min(mateThreat, 260) - d * 0.15;
    if (!best || score > best.score) best = { m, d, open, score };
  }
  return best;
}

function supportThink(match, p) {
  const team = p.team;
  const carrier = match.ball.owner;
  const bias = p.role === 'FW' ? 360 : p.role === 'MF' ? 250 : 140;
  const t = formationShifted(match, p, bias);
  // Make diagonal runs & keep spacing from the carrier.
  t.y += Math.sin(match.time * 0.9 + p.idx * 2) * 90;
  const dx = t.x - carrier.x, dy = t.y - carrier.y, d = Math.hypot(dx, dy);
  if (d < 200) { t.x += (dx / (d || 1)) * 140; t.y += (dy / (d || 1)) * 140; }
  const og = match.oppGoalX(team);
  if (Math.abs(t.x - og) < 170) t.x = og - team.dir * 170;
  p.ai.tx = clamp(t.x, 50, W - 50);
  p.ai.ty = clamp(t.y, 50, H - 50);
}

function defendThink(match, p, diff) {
  const T = p.team.ai;
  const c = match.ball.owner;
  const own = { x: match.ownGoalX(p.team), y: CY };
  if (p === T.presser) {
    const px = c.x + c.vx * 0.3, py = c.y + c.vy * 0.3;
    p.ai.tx = px; p.ai.ty = py; p.ai.urgent = true;
    const d = Math.hypot(c.x - p.x, c.y - p.y);
    if (d < 115 && d > 20 && p.slideCD <= 0 && c.z < 20 && chance(diff.aggro)) {
      aimSlide(p, px, py, diff);
    }
    return;
  }
  if (p === T.cover) {
    p.ai.tx = c.x + (own.x - c.x) * 0.38;
    p.ai.ty = c.y + (own.y - c.y) * 0.38;
    p.ai.urgent = true;
    const d = Math.hypot(c.x - p.x, c.y - p.y);
    if (d < 95 && p.slideCD <= 0 && chance(diff.aggro * 0.6)) aimSlide(p, c.x, c.y, diff);
    return;
  }
  // Man-mark the opponent nearest to my zone, goal side.
  const home = formationShifted(match, p, -120);
  let mark = null, md = Infinity;
  for (const o of match.other(p.team).players) {
    if (o.isGK || o === c || o.grounded) continue;
    const d = Math.hypot(o.x - home.x, o.y - home.y);
    if (d < md) { md = d; mark = o; }
  }
  if (mark && md < 420) {
    const gx = own.x - mark.x, gy = own.y - mark.y, gd = Math.hypot(gx, gy) || 1;
    p.ai.tx = mark.x + (gx / gd) * 60;
    p.ai.ty = mark.y + (gy / gd) * 60;
    // Cheap shots on the man you mark: it's that kind of sport.
    if (Math.hypot(mark.x - p.x, mark.y - p.y) < 75 && p.slideCD <= 0 && chance(diff.aggro * 0.06)) aimSlide(p, mark.x, mark.y, diff);
  } else {
    p.ai.tx = home.x; p.ai.ty = home.y;
  }
}

function looseThink(match, p, diff) {
  const T = p.team.ai;
  const b = match.ball;
  if (p === T.chaser || p === T.support) {
    const ic = p === T.chaser ? T.chasePt : T.supportPt;
    p.ai.tx = ic.x; p.ai.ty = ic.y; p.ai.urgent = true;
    // Jump for high balls passing overhead.
    const hd = Math.hypot(b.x - p.x, b.y - p.y);
    if (b.z > 68 && b.z < 150 && hd < 90 && p.state === 'run' && chance(0.7)) p.jump();
    // Take out an opponent racing for the same ball.
    for (const o of match.other(p.team).players) {
      if (o.grounded || o.isGK) continue;
      const od = Math.hypot(o.x - p.x, o.y - p.y);
      const obd = Math.hypot(o.x - b.x, o.y - b.y);
      if (od < 90 && obd < 140 && p.slideCD <= 0 && chance(diff.aggro * 0.35)) { aimSlide(p, o.x, o.y, diff); break; }
    }
    return;
  }
  const t = formationShifted(match, p, 0);
  p.ai.tx = t.x; p.ai.ty = t.y;
}

function aimSlide(p, tx, ty, diff) {
  const a = Math.atan2(ty - p.y, tx - p.x) + (1 - diff.aim) * rand(-0.35, 0.35);
  p.facing = a;
  p.intent = { mx: Math.cos(a), my: Math.sin(a) };
  p.slide();
}

// ---------- Goalkeeper ----------
export function gkUpdate(match, p, dt) {
  if (match.phase !== 'play') return;
  const b = match.ball;
  const team = p.team, dir = team.dir;
  const gx = match.ownGoalX(team);
  const homeX = gx + dir * 46;
  const ai = p.ai;
  const skill = team.human ? 0.8 : match.diff.gk;
  if (p.state !== 'run') { p.intent = { mx: 0, my: 0 }; return; }

  if (p.hasBall) {
    p.intent = { mx: 0, my: 0 };
    p.facing = dir > 0 ? 0 : Math.PI;
    if (!ai.holdFor) ai.holdFor = rand(0.6, 1.1);
    if (p.holdT > ai.holdFor) {
      ai.holdFor = 0;
      const opps = match.other(team).players.filter((o) => !o.grounded);
      const pass = bestPass(match, p, opps);
      if (pass) match.throwBall(p, { x: pass.m.x, y: pass.m.y, mate: pass.m }, 0.7, pass.open < 0.6, true);
      else match.throwBall(p, { x: gx + dir * 800, y: CY + rand(-300, 300) }, 0.8, true);
    }
    return;
  }

  let tx = homeX, ty = CY + (b.y - CY) * 0.3;
  let urgent = false;
  const towardGoal = b.vx * -dir > 120 && !b.owner;
  if (towardGoal) {
    const t = (homeX - b.x) / b.vx;
    if (t > 0 && t < 1.4) {
      let yp = b.y + b.vy * t;
      if (yp < 0) yp = -yp; if (yp > H) yp = 2 * H - yp;
      ty = yp;
      urgent = true;
      const reachY = clamp(yp, CY - GOAL_HALF - 15, CY + GOAL_HALF + 15);
      const gap = reachY - p.y;
      const zAt = b.z + b.vz * t - 0.5 * BALL_GRAVITY * t * t;
      if (Math.abs(gap) > 38 && t < 0.3 + skill * 0.12 && Math.abs(yp - CY) < GOAL_HALF + 25 && zAt < 110) {
        if (chance(0.4 + skill * 0.6)) p.dive(Math.sign(gap));
      }
      ty = reachY;
    }
  } else if (!b.owner && Math.hypot(b.x - gx, b.y - CY) < 300 && b.z < 70) {
    tx = b.x; ty = b.y; urgent = true;
  } else if (b.owner && b.owner.team !== team) {
    const c = b.owner;
    const d = Math.hypot(c.x - gx, c.y - CY);
    if (d < 650) {
      // Narrow the angle.
      const k = clamp(90 - d * 0.05, 45, 90);
      tx = gx + ((c.x - gx) / d) * k;
      ty = CY + ((c.y - CY) / d) * k;
    }
  }
  tx = dir > 0 ? clamp(tx, 20, 260) : clamp(tx, W - 260, W - 20);
  ty = clamp(ty, CY - GOAL_HALF - 60, CY + GOAL_HALF + 60);
  const dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy);
  const sp = urgent ? 1.25 : Math.min(1, d / 50);
  p.intent = d > 4 ? { mx: (dx / d) * sp, my: (dy / d) * sp } : { mx: 0, my: 0 };
  if (!urgent || d < 4) p.facing += angleDiff(p.facing, Math.atan2(b.y - p.y, b.x - p.x)) * Math.min(1, dt * 8);
}
