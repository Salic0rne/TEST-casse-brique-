// Match simulation: rules, ball physics, scoring objects, phases and human control.
// Vertical pitch: goals at the top (y = 0) and bottom (y = H); stars & ramps on the side walls.
import {
  FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, GOAL_Z, BALL_R, BALL_GRAVITY, PLAYER_R,
  THROW_MIN, THROW_MAX, CHARGE_TIME, LOB_VZ, CATCH_R, SLIDE_TIME, GOAL_POINTS, STAR_POINTS, STAR_ROW_BONUS, KO_POINTS,
  BUMPERS, ELECTRO, STAR_YS, RAMP_HALF, TEAMS, FORMATION, PLAYER_NAMES, DIFFICULTIES,
} from './constants.js';
import { Player } from './player.js';
import { aiTeamUpdate, aiPlayerUpdate, gkUpdate } from './ai.js';
import { clamp, rand, pick, chance, lerp, angleDiff, TAU } from '../core/math.js';
import { fx } from '../render/fx.js';
import { audio } from '../audio/audio.js';
import { music } from '../audio/music.js';
import { readDevice } from '../core/input.js';
import { t } from '../core/i18n.js';

export const MULTS = [1, 1.5, 2];
const TOKEN_TYPES = ['rage', 'shock', 'freeze', 'medic', 'cash'];
const UP = -Math.PI / 2, DOWN = Math.PI / 2;

export class Match {
  /** opts: { humans: [{device, team}], difficulty: 0..2, halfLength: seconds, demo: bool } */
  constructor(opts) {
    this.opts = opts;
    this.demo = !!opts.demo;
    this.diff = DIFFICULTIES[opts.difficulty ?? 1];
    this.halfLength = opts.halfLength ?? 90;
    this.time = 0;
    // dir = +1: attacks toward y = H (defends the top goal).
    this.teams = TEAMS.map((def, i) => ({
      idx: i, def, dir: i === 0 ? -1 : 1, score: 0, banked: 0, mult: 0,
      goals: 0, kos: 0, tackles: 0, shots: 0, starsLit: 0, credits: 0,
      rageT: 0, freezeT: 0, players: [], human: false, ai: { presser: null, chaser: null, support: null, cover: null, t: 0 },
    }));
    for (const tm of this.teams) tm.players = FORMATION.map((slot, k) => new Player(tm, k, slot, PLAYER_NAMES[tm.idx][k]));
    this.players = this.teams.flatMap((tm) => tm.players);
    this.humans = (opts.humans || []).map((h, i) => ({
      id: i, device: h.device, team: this.teams[h.team], player: null, switchCD: 0,
      color: i === 0 ? '#ffd23a' : '#7dff5a', input: null, edges: { action: false, jump: false, swap: false },
    }));
    for (const h of this.humans) h.team.human = true;

    this.ball = {
      x: CX, y: CY, z: 0, vx: 0, vy: 0, vz: 0, owner: null, lastTeam: null, lastThrower: null,
      noCatchP: null, noCatchT: 0, electric: 0, elecTeam: -1, spin: 0, trail: [], inGoal: false, isShot: false,
      rampCD: 0, bumpCD: 0,
    };
    this.stars = { left: STAR_YS.map(() => -1), right: STAR_YS.map(() => -1) };
    this.starFlash = { left: STAR_YS.map(() => 0), right: STAR_YS.map(() => 0) };
    this.bumperFlash = BUMPERS.map(() => 0);
    this.electroFlash = ELECTRO.map(() => 0);
    this.rampFlash = [0, 0];
    this.tokens = [];
    this.tokenTimer = rand(8, 12);
    this.half = 1;
    this.clock = this.halfLength;
    this.phase = 'intro';
    this.phaseT = 0;
    this.excitement = 0.3;
    this.announcements = [];
    this.goalInfo = null;
    this.over = false;
    this.lastCountdown = -1;
    this.setupPositions(true);
    if (!this.demo) this.announce(t('half', 1), '#e8d8b8', t('introSub'));
  }

  // ---------- helpers ----------
  ownGoalY(team) { return team.dir > 0 ? 0 : H; }
  oppGoalY(team) { return team.dir > 0 ? H : 0; }
  other(team) { return this.teams[1 - team.idx]; }
  aiSpeed(team) { return team.human ? 1 : this.diff.speed; }
  formationPos(p) {
    const tm = p.team;
    return tm.dir > 0 ? { x: p.slot.x * W, y: p.slot.y * H } : { x: W - p.slot.x * W, y: H - p.slot.y * H };
  }
  pan(x) {
    return clamp((x - CX) / (W * 0.6), -1, 1);
  }
  emit(type, p) {
    if (type === 'land') audio.play('land', { pan: this.pan(p.x) });
    if (type === 'thud') { audio.play('land', { pan: this.pan(p.x) }); fx.dust(p.x, p.y, 6); }
    if (type === 'revive') fx.ring(p.x, p.y, '#9fd08a', 60, 0.5, 3);
  }
  announce(text, color = '#fff', sub = '', dur = 1.8) {
    if (!text || this.demo) return;
    this.announcements.push({ text, color, sub, t: 0, dur });
    if (this.announcements.length > 2) this.announcements.shift();
  }
  get teamScores() { return this.teams.map((tm) => tm.score); }

  recomputeScores() {
    for (const tm of this.teams) {
      const lit = this.stars.left.filter((o) => o === tm.idx).length + this.stars.right.filter((o) => o === tm.idx).length;
      tm.score = tm.banked + lit * STAR_POINTS;
    }
  }

  setupPositions(snap) {
    for (const p of this.players) {
      const f = this.formationPos(p);
      // Kickoff line-up: stay in own half.
      const y = p.team.dir > 0 ? Math.min(f.y, CY - 100) : Math.max(f.y, CY + 100);
      p.home = { x: f.x, y };
      if (snap) {
        p.x = f.x; p.y = y; p.vx = 0; p.vy = 0; p.z = 0; p.vz = 0;
        p.setState('run');
        p.facing = p.team.dir > 0 ? DOWN : UP;
        p.hasBall = false; p.charging = false;
      }
    }
    this.resetBall();
  }

  resetBall() {
    Object.assign(this.ball, { x: CX, y: CY, z: -30, vx: 0, vy: 0, vz: 0, owner: null, lastTeam: null, lastThrower: null, electric: 0, inGoal: false, isShot: false });
    this.ball.trail.length = 0;
  }

  // ---------- main update ----------
  update(dt) {
    this.time += dt;
    this.phaseT += dt;
    for (const a of this.announcements) a.t += dt;
    if (this.announcements.length && this.announcements[0].t >= this.announcements[0].dur) this.announcements.shift();

    switch (this.phase) {
      case 'intro':
        if (this.phaseT > (this.demo ? 0.5 : 2.2)) this.startKickoff();
        break;
      case 'kickoff': {
        const n = 3 - Math.floor(this.phaseT / 0.7);
        if (!this.demo && n !== this.lastCountdown && n >= 1 && n <= 3) {
          this.lastCountdown = n;
          audio.play('beep');
          this.announce(String(n), '#ffffff', '', 0.65);
        }
        if (this.phaseT > 2.1) this.launchBall();
        break;
      }
      case 'play':
        this.clock -= dt;
        if (this.half < 3 && this.clock <= 10.5 && Math.ceil(this.clock) !== this.lastCountdown && this.clock > 0) {
          this.lastCountdown = Math.ceil(this.clock);
          if (!this.demo) audio.play('beep', { high: this.lastCountdown <= 3 });
        }
        if (this.clock <= 0) this.endOfPeriod();
        break;
      case 'goal':
        if (this.phaseT > 3.2) {
          if (this.half === 3) this.finish();
          else this.startKickoff();
        }
        break;
      case 'halftime':
        if (this.phaseT > 3.5) {
          this.half = 2;
          this.clock = this.halfLength;
          for (const tm of this.teams) { tm.dir = -tm.dir; tm.rageT = 0; tm.freezeT = 0; }
          this.phase = 'intro';
          this.phaseT = 0;
          this.setupPositions(true);
          if (!this.demo) this.announce(t('half', 2), '#e8d8b8', t('switchSides'));
        }
        break;
    }

    this.updateHumans(dt);
    aiTeamUpdate(this, dt);

    const walking = this.phase === 'kickoff' || this.phase === 'intro' || this.phase === 'halftime';
    const celebrating = this.phase === 'goal' || this.phase === 'fulltime';
    for (const p of this.players) {
      if (walking) this.walkHome(p, dt);
      else if (celebrating) this.celebrateOrSulk(p, dt);
      else if (p.isGK) gkUpdate(this, p, dt);
      else if (!p.human) aiPlayerUpdate(this, p, dt);
      p.update(dt, this);
    }
    this.separatePlayers();
    if (this.phase === 'play') this.checkSlides();
    this.updateBall(dt);
    this.updateObjects(dt);

    // Music & crowd intensity
    const b = this.ball;
    const nearGoal = 1 - Math.min(b.y, H - b.y) / (H / 2);
    const target = this.phase === 'play' ? 0.35 + nearGoal * 0.4 + (this.clock < 20 ? 0.3 : 0) : this.phase === 'goal' ? 1 : 0.2;
    this.excitement = lerp(this.excitement, target, 1 - Math.exp(-dt * 1.5));
    if (!this.demo) {
      audio.setCrowd(this.excitement);
      music.setIntensity(this.phase === 'play' ? 0.45 + nearGoal * 0.25 + (this.clock < 20 ? 0.35 : 0) + (this.half === 3 ? 0.3 : 0) : 0.4);
    }
  }

  setIntent(p, mx, my) {
    p.intent.mx = mx;
    p.intent.my = my;
  }

  walkHome(p, dt) {
    const dx = p.home.x - p.x, dy = p.home.y - p.y;
    const d = Math.hypot(dx, dy);
    p.charging = false;
    if (p.state !== 'run') { this.setIntent(p, 0, 0); return; }
    if (d > 8) this.setIntent(p, (dx / d) * Math.min(1.3, d / 60), (dy / d) * Math.min(1.3, d / 60));
    else {
      this.setIntent(p, 0, 0);
      p.facing += angleDiff(p.facing, p.team.dir > 0 ? DOWN : UP) * Math.min(1, dt * 6);
    }
  }

  celebrateOrSulk(p, dt) {
    this.setIntent(p, 0, 0);
    p.charging = false;
    const g = this.goalInfo;
    const winners = this.phase === 'fulltime' ? this.winner : g && g.team;
    if (winners && p.team === winners && p.state === 'run' && this.phaseT > 0.4 && chance(dt * 2)) p.setState('celebrate');
    if (p.state === 'celebrate' && g && this.phase === 'goal') {
      const dx = CX - p.x, dy = g.scorerY - p.y, d = Math.hypot(dx, dy);
      if (d > 140) this.setIntent(p, (dx / d) * 0.5, (dy / d) * 0.5);
    }
  }

  startKickoff() {
    this.phase = 'kickoff';
    this.phaseT = 0;
    this.lastCountdown = -1;
    for (const p of this.players) { if (p.state === 'celebrate') p.setState('run'); p.hasBall = false; }
    this.setupPositions(false);
  }

  launchBall() {
    const b = this.ball;
    this.phase = 'play';
    this.phaseT = 0;
    for (const p of this.players) {
      if (Math.hypot(p.x - p.home.x, p.y - p.home.y) > 150) { p.x = p.home.x; p.y = p.home.y; }
    }
    b.x = CX; b.y = CY; b.z = 10;
    const a = rand(0, TAU);
    b.vx = Math.cos(a) * rand(40, 140);
    b.vy = Math.sin(a) * rand(40, 140);
    b.vz = 820;
    b.lastTeam = null;
    b.inGoal = false;
    audio.play('launch');
    if (!this.demo) audio.play('whistle');
    fx.glow(CX, CY, 0, 260, 'rgba(255,200,140,1)', 0.35);
    fx.smoke(CX, CY, 0, 14, 40);
    fx.sparks(CX, CY, 5, 30, 500);
    fx.shake(0.3);
  }

  endOfPeriod() {
    audio.play('whistle', { long: true });
    this.clock = 0;
    const b = this.ball;
    if (b.owner) { b.owner.hasBall = false; b.owner.charging = false; b.owner = null; }
    if (this.half === 1) {
      this.phase = 'halftime';
      this.phaseT = 0;
      if (!this.demo) this.announce(t('halftime'), '#e8d8b8', `${this.teams[0].score} — ${this.teams[1].score}`, 3);
      music.setMode('halftime');
    } else if (this.half === 2 && this.teams[0].score === this.teams[1].score && !this.demo) {
      this.half = 3;
      this.clock = 60;
      this.phase = 'intro';
      this.phaseT = 0;
      this.setupPositions(true);
      this.announce(t('suddenDeath'), '#d42a1a', t('suddenDeathSub'), 2.4);
    } else {
      this.finish();
    }
  }

  finish() {
    this.phase = 'fulltime';
    this.phaseT = 0;
    this.over = true;
    const [a, b] = this.teamScores;
    const winner = a === b ? null : a > b ? this.teams[0] : this.teams[1];
    this.winner = winner;
    if (!this.demo) {
      music.stinger('end');
      audio.crowdReact(1.2, 'cheer');
    }
  }

  // ---------- humans ----------
  /** Called once per rendered frame: button edges stay latched until a sim step consumes them. */
  pollHumans() {
    for (const h of this.humans) {
      const inp = readDevice(h.device);
      if (!inp) continue;
      const e = h.edges;
      e.action ||= inp.actionPressed;
      e.jump ||= inp.jumpPressed;
      e.swap ||= inp.swapPressed;
      h.input = inp;
    }
  }

  updateHumans(dt) {
    const playable = this.phase === 'play';
    for (const h of this.humans) {
      h.switchCD -= dt;
      const inp = h.input;
      if (!inp) continue;
      const e = h.edges;
      const actionPressed = e.action, jumpPressed = e.jump, swapPressed = e.swap;
      e.action = e.jump = e.swap = false;
      this.pickControlled(h, swapPressed && playable);
      const p = h.player;
      if (!p) continue;
      if (!playable) { p.charging = false; continue; }
      this.setIntent(p, inp.mx, inp.my);
      if (p.hasBall) {
        if (p.isGK) continue;
        const m = Math.hypot(inp.mx, inp.my);
        if (m > 0.2) { p.aimX = inp.mx / m; p.aimY = inp.my / m; }
        else { p.aimX = Math.cos(p.facing); p.aimY = Math.sin(p.facing); }
        if (actionPressed && !p.charging) { p.charging = true; p.chargeT = 0; }
        if (p.charging) {
          p.chargeT += dt;
          if (!inp.action) this.humanThrow(p, p.aimX, p.aimY, clamp(p.chargeT / CHARGE_TIME, 0, 1), false);
        }
        if (jumpPressed && p.hasBall) this.humanThrow(p, p.aimX, p.aimY, 0.6, true);
      } else {
        p.charging = false;
        if (actionPressed && p.slide()) audio.play('slide', { pan: this.pan(p.x) });
        if (jumpPressed && p.jump()) audio.play('jump', { pan: this.pan(p.x) });
      }
    }
  }

  pickControlled(h, manual) {
    const team = h.team;
    const b = this.ball;
    let other = null;
    for (const o of this.humans) if (o !== h && o.player) other = o.player;
    const release = (np) => {
      if (h.player === np) return;
      if (h.player) { h.player.human = null; h.player.charging = false; }
      h.player = np;
      if (np) { np.human = h; np.ai.next = 0; }
      h.switchCD = 0.28;
    };
    if (b.owner && b.owner.team === team && !b.owner.isGK) {
      if (b.owner !== other) release(b.owner);
      return;
    }
    const tx = b.owner ? b.owner.x : b.x + b.vx * 0.3;
    const ty = b.owner ? b.owner.y : b.y + b.vy * 0.3;
    const score = (p) => Math.hypot(p.x - tx, p.y - ty) + (p.grounded ? 400 : 0);
    let best = null, bs = Infinity, second = null, ss = Infinity;
    for (const p of team.players) {
      if (p.isGK || p === other) continue;
      const s = score(p);
      if (s < bs) { second = best; ss = bs; best = p; bs = s; } else if (s < ss) { second = p; ss = s; }
    }
    if (manual) {
      const np = best === h.player ? second : best;
      if (np) { release(np); audio.play('ui', { kind: 'move' }); }
      return;
    }
    const cur = h.player && !h.player.isGK && h.player !== other ? h.player : null;
    if (!cur) { release(best); return; }
    if (h.switchCD > 0 || cur.state === 'slide' || cur.state === 'jump') return;
    if (best && best !== cur && bs < score(cur) - 90) release(best);
  }

  humanThrow(p, dx, dy, power, lob) {
    // Aim assist: snap toward the goal or a teammate inside a cone.
    const team = p.team;
    const ang = Math.atan2(dy, dx);
    let best = null, bestScore = Infinity;
    const gy = this.oppGoalY(team);
    const goalAng = Math.atan2(gy - p.y, CX - p.x);
    const goalDist = Math.hypot(CX - p.x, gy - p.y);
    if (Math.abs(angleDiff(ang, goalAng)) < 0.42 && goalDist < 1100) {
      const off = clamp(-angleDiff(goalAng, ang) * 500 * Math.sign(gy - p.y || 1), -GOAL_HALF + 28, GOAL_HALF - 28);
      best = { x: CX + off, y: gy, shot: true };
    }
    if (!best) {
      for (const m of team.players) {
        if (m === p || m.grounded) continue;
        const d = Math.hypot(m.x - p.x, m.y - p.y);
        if (d < 110 || d > 1100) continue;
        const da = Math.abs(angleDiff(ang, Math.atan2(m.y - p.y, m.x - p.x)));
        if (da > 0.5) continue;
        const s = da * 600 + d * 0.3;
        if (s < bestScore) { bestScore = s; best = { x: m.x, y: m.y, mate: m }; }
      }
    }
    this.throwBall(p, best || { x: p.x + dx * 600, y: p.y + dy * 600 }, power, lob, !!(best && best.mate));
  }

  // ---------- ball ----------
  throwBall(p, target, power, lob, lead = false) {
    const b = this.ball;
    if (b.owner !== p) return;
    let tx = target.x, ty = target.y;
    const speed = lerp(THROW_MIN, THROW_MAX, power) * p.stats.throw * (p.team.rageT > 0 ? 1.08 : 1);
    if (lead && target.mate) {
      const d = Math.hypot(tx - p.x, ty - p.y);
      const tt = lob ? 0.95 : d / speed;
      tx += target.mate.vx * tt * 0.9;
      ty += target.mate.vy * tt * 0.9;
    }
    const dx = tx - p.x, dy = ty - p.y;
    const d = Math.max(1, Math.hypot(dx, dy));
    const ux = dx / d, uy = dy / d;
    p.hasBall = false;
    p.charging = false;
    p.chargeT = 0;
    p.facing = Math.atan2(uy, ux);
    p.setState('throw');
    b.owner = null;
    b.x = p.x + ux * 26; b.y = p.y + uy * 26; b.z = 44;
    b.lastTeam = p.team.idx;
    b.lastThrower = p;
    b.noCatchP = p; b.noCatchT = 0.25;
    b.isShot = !!target.shot;
    if (b.electric > 0) b.elecTeam = p.team.idx;
    if (lob) {
      const hs = clamp(d, 280, 980);
      b.vx = ux * hs; b.vy = uy * hs; b.vz = LOB_VZ;
      audio.play('lob', { pan: this.pan(p.x) });
    } else {
      b.vx = ux * speed; b.vy = uy * speed;
      const tt = d / speed;
      b.vz = clamp((34 - 44 + 0.5 * BALL_GRAVITY * tt * tt) / Math.max(0.05, tt), 40, 300);
      audio.play('throw', { power, pan: this.pan(p.x) });
    }
    if (b.isShot) p.team.shots++;
    p.catchCD = 0.2;
    fx.dust(p.x, p.y, 3);
    if (power > 0.85 && !lob) { fx.shake(0.1); fx.sparks(b.x, b.y, b.z, 6, 300, ux, uy, 0.8); }
  }

  releaseBallFrom(p, vx, vy) {
    const b = this.ball;
    if (b.owner !== p) return;
    p.hasBall = false;
    p.charging = false;
    b.owner = null;
    b.x = p.x; b.y = p.y; b.z = 40;
    b.vx = vx; b.vy = vy; b.vz = 280;
    b.noCatchP = p; b.noCatchT = 0.45;
    b.isShot = false;
  }

  updateBall(dt) {
    const b = this.ball;
    b.noCatchT -= dt;
    b.rampCD -= dt;
    b.bumpCD -= dt;
    if (b.electric > 0) {
      b.electric -= dt;
      if (Math.random() < dt * 25) {
        const a = rand(0, TAU);
        fx.arc(b.x, b.y, b.z, b.x + Math.cos(a) * rand(20, 45), b.y + Math.sin(a) * rand(10, 30), b.z + rand(-20, 20));
      }
    }
    if (b.owner) {
      const o = b.owner;
      b.x = o.x + Math.cos(o.facing) * 16;
      b.y = o.y + Math.sin(o.facing) * 16;
      b.z = o.z + 42;
      b.vx = o.vx; b.vy = o.vy; b.vz = 0;
      b.trail.length = 0;
      if (b.electric > 0) b.elecTeam = o.team.idx;
      return;
    }
    if (b.inGoal) {
      const k = Math.exp(-6 * dt);
      b.vx *= k; b.vy *= k;
      b.x += b.vx * dt; b.y += b.vy * dt;
      b.vz -= BALL_GRAVITY * dt;
      b.z = Math.max(0, b.z + b.vz * dt);
      if (b.z <= 0) b.vz = Math.abs(b.vz) * 0.3;
      b.x = clamp(b.x, CX - GOAL_HALF + BALL_R, CX + GOAL_HALF - BALL_R);
      b.y = clamp(b.y, -GOAL_DEPTH * 0.55, H + GOAL_DEPTH * 0.45);
      return;
    }

    const steps = 2;
    const h = dt / steps;
    for (let s = 0; s < steps; s++) {
      b.x += b.vx * h;
      b.y += b.vy * h;
      if (b.z > 0 || b.vz > 0) {
        b.vz -= BALL_GRAVITY * h;
        b.z += b.vz * h;
        if (b.z <= 0) {
          b.z = 0;
          if (b.vz < -120) {
            b.vz = -b.vz * 0.52;
            if (this.phase === 'play' || this.phase === 'goal') audio.play('clank', { power: clamp(-b.vz / 500, 0.15, 0.7), pan: this.pan(b.x) });
            fx.dust(b.x, b.y, 2, '#7a6450', 10);
          } else b.vz = 0;
        }
      }
      if (b.z <= 0) {
        const k = Math.exp(-1.1 * h);
        b.vx *= k; b.vy *= k;
      }
      this.ballWalls(b);
      if (b.inGoal) return;
    }
    b.spin += Math.hypot(b.vx, b.vy) * dt * 0.05;

    // Trail (ring buffer of recent positions)
    if (b.trail.length >= 10) b.trail.shift();
    b.trail.push({ x: b.x, y: b.y - b.z });

    if (this.phase !== 'play') return;

    for (let i = 0; i < BUMPERS.length; i++) {
      const bm = BUMPERS[i];
      if (b.z > 60) continue;
      const dx = b.x - bm.x, dy = b.y - bm.y, d = Math.hypot(dx, dy);
      if (d < bm.r + BALL_R && d > 0.01) {
        const nx = dx / d, ny = dy / d;
        const vn = b.vx * nx + b.vy * ny;
        if (vn < 0) {
          b.vx -= 2 * vn * nx; b.vy -= 2 * vn * ny;
          const m = Math.hypot(b.vx, b.vy) || 1;
          const sp = Math.max(520, m * 1.15);
          b.vx = (b.vx / m) * sp; b.vy = (b.vy / m) * sp;
          b.vz = Math.max(b.vz, 120);
        }
        b.x = bm.x + nx * (bm.r + BALL_R + 1);
        b.y = bm.y + ny * (bm.r + BALL_R + 1);
        this.bumperFlash[i] = 1;
        if (b.bumpCD <= 0) {
          audio.play('bumper', { pan: this.pan(b.x) });
          fx.sparks(b.x, b.y, b.z + 10, 14, 420, nx, ny, 1.6);
          fx.glow(bm.x, bm.y, 30, 160, 'rgba(255,170,90,1)', 0.25);
          fx.shake(0.08);
          b.bumpCD = 0.08;
        }
      }
    }

    for (let i = 0; i < ELECTRO.length; i++) {
      const e = ELECTRO[i];
      if (b.z > 40 || b.lastTeam === null) continue;
      if (Math.hypot(b.x - e.x, b.y - e.y) < e.r + BALL_R) {
        if (b.electric <= 0 || b.elecTeam !== b.lastTeam) {
          audio.play('electrify', { pan: this.pan(b.x) });
          fx.glow(e.x, e.y, 10, 220, 'rgba(90,200,255,1)', 0.35);
          for (let k = 0; k < 6; k++) fx.arc(e.x, e.y, 0, b.x + rand(-30, 30), b.y + rand(-30, 30), b.z + rand(0, 40));
          fx.text(e.x, e.y - 60, t('electricBall'), '#9fe8ff', 26, 1.1);
        }
        b.electric = 5;
        b.elecTeam = b.lastTeam;
        this.electroFlash[i] = 1;
      }
    }

    if (b.z < 120) this.tryCatch(b);
  }

  ballWalls(b) {
    const r = BALL_R;
    // Side walls: bounce, stars, ramps
    if (b.x < r) {
      b.x = r;
      if (b.vx < 0) { this.wallHit(b, 'left'); b.vx = -b.vx * 0.8; }
    } else if (b.x > W - r) {
      b.x = W - r;
      if (b.vx > 0) { this.wallHit(b, 'right'); b.vx = -b.vx * 0.8; }
    }
    // Ends: goals
    for (let side = 0; side < 2; side++) {
      const beyond = side === 0 ? b.y < r : b.y > H - r;
      if (!beyond) continue;
      const inMouth = Math.abs(b.x - CX) < GOAL_HALF - r * 0.5;
      if (inMouth && b.z < GOAL_Z && this.phase === 'play') {
        const crossed = side === 0 ? b.y < -r : b.y > H + r;
        if (crossed) this.goalScored(side);
        continue;
      }
      b.y = side === 0 ? r : H - r;
      const vIn = side === 0 ? -b.vy : b.vy;
      if (vIn > 0) {
        b.vy = -b.vy * 0.8;
        const post = Math.abs(Math.abs(b.x - CX) - GOAL_HALF) < 25 || inMouth;
        if (this.phase === 'play') {
          audio.play('clank', { power: clamp(vIn / 800, 0.2, 1), pan: this.pan(b.x) });
          fx.sparks(b.x, b.y, b.z, post ? 18 : 6, post ? 500 : 250, 0, side === 0 ? 1 : -1, 1.8);
          if (post) { fx.shake(0.15); if (b.isShot) fx.text(b.x, b.y + (side === 0 ? 60 : -60), t('post'), '#e8d8b8', 28, 1); }
        }
      }
    }
  }

  wallHit(b, wall) {
    if (this.phase !== 'play') return;
    const sp = Math.abs(b.vx);
    audio.play('clank', { power: clamp(sp / 900, 0.15, 0.9), pan: this.pan(b.x) });
    if (sp > 300) fx.sparks(b.x, b.y, b.z, 6, 260, wall === 'left' ? 1 : -1, 0, 1.8);
    if (b.lastTeam === null || b.z > 95) return;
    // Ramp → score multiplier
    if (Math.abs(b.y - CY) < RAMP_HALF && b.rampCD <= 0) {
      b.rampCD = 1;
      const tm = this.teams[b.lastTeam], o = this.other(tm);
      this.rampFlash[wall === 'left' ? 0 : 1] = 1.5;
      if (tm.mult < 2) {
        tm.mult++;
        o.mult = 0;
        audio.play('multiplier');
        this.announce(t('multiplier', MULTS[tm.mult]), tm.def.ui, tm.def.name, 1.6);
        fx.glow(b.x, b.y, 20, 260, tm.idx === 0 ? 'rgba(255,120,40,1)' : 'rgba(150,220,255,1)', 0.4);
      }
      return;
    }
    // Stars
    const row = this.stars[wall];
    for (let i = 0; i < STAR_YS.length; i++) {
      const sy = STAR_YS[i];
      if (Math.abs(b.y - sy) >= 36 || row[i] === b.lastTeam) continue;
      row[i] = b.lastTeam;
      this.starFlash[wall][i] = 1;
      const tm = this.teams[b.lastTeam];
      tm.starsLit++;
      const sx = wall === 'left' ? -24 : W + 24;
      audio.play('star', { pan: this.pan(sx), team: tm.idx });
      fx.sparks(sx, sy, 20, 20, 380);
      fx.glow(sx, sy, 20, 150, tm.idx === 0 ? 'rgba(255,140,50,1)' : 'rgba(160,225,255,1)', 0.4);
      fx.text(wall === 'left' ? 60 : W - 60, sy, '+2', tm.def.ui, 26, 1);
      if (row.every((o) => o === tm.idx)) {
        tm.banked += STAR_ROW_BONUS;
        audio.play('starbonus');
        this.announce(t('starRow'), tm.def.ui, `+${STAR_ROW_BONUS}  ${tm.def.name}`, 1.8);
        fx.doFlash(1, 0.85, 0.5, 0.2);
        setTimeout(() => { for (let k = 0; k < row.length; k++) row[k] = -1; this.recomputeScores(); }, 1400);
      }
      this.recomputeScores();
    }
  }

  tryCatch(b) {
    let best = null, bestD = Infinity;
    for (const p of this.players) {
      if (!p.canCatch || p.hasBall) continue;
      if (b.noCatchT > 0 && p === b.noCatchP) continue;
      const reach = p.isGK ? 82 : 70;
      if (b.z < p.z - 12 || b.z > p.z + reach + (p.state === 'dive' ? 20 : 0)) continue;
      const r = CATCH_R * p.stats.catch + (p.state === 'dive' ? 22 : 0) + (p.state === 'slide' ? 8 : 0);
      const d = Math.hypot(b.x - p.x, b.y - p.y);
      if (d < r && d < bestD) { best = p; bestD = d; }
    }
    if (!best) return;
    const p = best;
    const sp = Math.hypot(b.vx - p.vx, b.vy - p.vy);
    if (b.electric > 0 && b.elecTeam !== p.team.idx && b.elecTeam >= 0) {
      this.shockPlayer(p);
      const a = Math.atan2(b.y - p.y, b.x - p.x);
      b.vx = Math.cos(a) * 380; b.vy = Math.sin(a) * 380; b.vz = 250;
      b.noCatchP = p; b.noCatchT = 0.6;
      return;
    }
    const opponent = b.lastTeam !== null && b.lastTeam !== p.team.idx;
    if (p.isGK && b.isShot && opponent) {
      const skill = p.team.human ? 0.8 : this.diff.gk;
      const pSave = clamp(skill + 0.08 - (sp - 850) / 1000, 0.15, 0.92);
      if (!chance(pSave)) {
        if (chance(0.5)) {
          b.vx = b.vx * 0.4 + rand(-300, 300); b.vy = -b.vy * 0.35 + rand(-200, 200); b.vz = 300;
          b.noCatchP = p; b.noCatchT = 0.4;
          audio.play('hit', { power: 0.5, pan: this.pan(p.x) });
          fx.sparks(b.x, b.y, b.z, 12, 350);
          fx.text(p.x, p.y - 110, t('parried'), '#e8d8b8', 26, 0.9);
        } else {
          p.catchCD = 0.5;
        }
        return;
      }
      fx.text(p.x, p.y - 110, t('save'), '#e8d8b8', 26, 0.9);
    } else if (opponent && sp > 1150 && !p.isGK && chance(0.45)) {
      // Too hot to handle: deflects off the body.
      b.vx = -b.vx * 0.3 + rand(-150, 150); b.vy = -b.vy * 0.3 + rand(-150, 150); b.vz = 220;
      b.noCatchP = p; b.noCatchT = 0.4;
      p.setState('stun'); p.stunTime = 0.35;
      audio.play('hit', { power: 0.6, pan: this.pan(p.x) });
      fx.sparks(b.x, b.y, b.z, 10, 300);
      return;
    }
    b.owner = p;
    p.hasBall = true;
    p.holdT = 0;
    b.isShot = false;
    b.lastTeam = p.team.idx;
    audio.play('catch', { pan: this.pan(p.x) });
    if (p.state === 'dive') { fx.dust(p.x, p.y, 8); fx.shake(0.1); }
  }

  shockPlayer(p) {
    p.shockT = 1.2;
    p.health -= 20;
    const ko = p.health <= 0;
    p.knockDown(rand(-60, 60), rand(-60, 60), ko ? 4.5 : 1.3, ko);
    audio.play('zap', { pan: this.pan(p.x), long: true });
    fx.glow(p.x, p.y, 40, 240, 'rgba(90,200,255,1)', 0.4);
    for (let i = 0; i < 8; i++) fx.arc(p.x, p.y, rand(10, 60), p.x + rand(-60, 60), p.y + rand(-30, 30), rand(0, 80));
    fx.sparks(p.x, p.y, 40, 20, 400);
    fx.smoke(p.x, p.y, 40, 6, 22);
    fx.shake(0.35);
    fx.aberrate(0.5);
    fx.decal('burn', p.x, p.y, { r: 30 });
    fx.text(p.x, p.y - 110, t('electrocuted'), '#9fe8ff', 28, 1);
    if (ko) this.registerKO(p, this.teams[this.ball.elecTeam]);
  }

  // ---------- combat ----------
  checkSlides() {
    for (const a of this.players) {
      if (a.state !== 'slide' || a.stateT > SLIDE_TIME * 0.95) continue;
      for (const v of this.players) {
        if (v.team === a.team) continue;
        if (v.grounded || v.hitImmune > 0 || v.z > 22 || (v.state === 'slide' && v.stateT < 0.15)) continue;
        if (Math.hypot(v.x - a.x, v.y - a.y) < PLAYER_R * 2 + 2) this.tackle(a, v);
      }
    }
  }

  tackle(a, v) {
    const dirx = Math.cos(a.facing), diry = Math.sin(a.facing);
    const rage = a.team.rageT > 0 ? 1.5 : 1;
    const dmg = 27 * a.stats.power * rage * rand(0.8, 1.25) * (v.isGK ? 0.7 : 1);
    v.health -= dmg;
    v.hitFlash = 0.07;
    v.hitImmune = 1.4;
    v.wounds = Math.min(6, (v.wounds || 0) + 1);
    const ko = v.health <= 0;
    const hadBall = v.hasBall;
    const force = 380 * rage;
    if (hadBall) this.releaseBallFrom(v, dirx * 260 + v.vx * 0.3 + rand(-120, 120), diry * 260 + v.vy * 0.3 + rand(-120, 120));
    v.knockDown(dirx * force, diry * force, ko ? 4.5 : 1.05, ko);
    a.vx *= 0.45; a.vy *= 0.45;
    a.team.tackles++;

    const hx = (a.x + v.x) / 2, hy = (a.y + v.y) / 2;
    fx.freeze(ko ? 0.09 : 0.045);
    fx.shake(ko ? 0.6 : 0.36);
    fx.aberrate(ko ? 0.6 : 0.25);
    fx.blood(hx, hy, 34, Math.round(16 + dmg * 0.9), dirx, diry, 1.3);
    fx.sparks(hx, hy, 34, 10, 420, dirx, diry, 1.8);
    fx.debris(hx, hy, 30, 4, '#4a3e34');
    fx.dust(v.x, v.y, 8);
    fx.decal('skid', a.x - dirx * 60, a.y - diry * 60, { x2: a.x, y2: a.y, w: 12 });
    fx.decal('splat', v.x + dirx * 30, v.y + diry * 30, { r: 14 + dmg * 0.5, dx: dirx, dy: diry });
    audio.play('hit', { power: 0.8 + dmg / 40, pan: this.pan(hx) });
    if (hadBall) {
      audio.crowdReact(0.7, 'cheer');
      if (chance(0.35)) fx.text(v.x, v.y - 120, pick(t('brutal')), '#c8281a', 30, 0.9);
    }
    if (ko) this.registerKO(v, a.team);
  }

  registerKO(v, byTeam) {
    if (!byTeam) return;
    byTeam.banked += KO_POINTS;
    byTeam.kos++;
    this.recomputeScores();
    fx.slow(0.35, 0.45);
    fx.blood(v.x, v.y, 20, 50, 0, 0, 1.6);
    fx.gore(v.x, v.y, 30);
    fx.shock(v.x, v.y, 0.7);
    fx.doFlash(0.7, 0.02, 0.0, 0.16);
    fx.decal('pool', v.x, v.y, { r: 46 });
    audio.play('ko', { pan: this.pan(v.x) });
    this.announce(t('ko'), '#c8281a', `${t('koSub', v.name)}  +${KO_POINTS}`, 1.4);
  }

  separatePlayers() {
    const ps = this.players;
    const min = PLAYER_R * 1.7, min2 = min * min;
    for (let i = 0; i < ps.length; i++) {
      const a = ps[i];
      if (a.grounded) continue;
      for (let j = i + 1; j < ps.length; j++) {
        const b = ps[j];
        if (b.grounded || Math.abs(a.z - b.z) > 40) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < min2 && d2 > 0.0001) {
          const d = Math.sqrt(d2);
          const push = (min - d) / 2;
          const nx = dx / d, ny = dy / d;
          a.x -= nx * push; a.y -= ny * push;
          b.x += nx * push; b.y += ny * push;
        }
      }
    }
  }

  // ---------- scoring ----------
  goalScored(side) {
    const b = this.ball;
    const gy = side === 0 ? 0 : H;
    const team = this.teams.find((tm) => this.oppGoalY(tm) === gy);
    const pts = Math.round(GOAL_POINTS * MULTS[team.mult]);
    team.banked += pts;
    team.goals++;
    this.recomputeScores();
    b.inGoal = true;
    b.electric = 0;
    this.phase = 'goal';
    this.phaseT = 0;
    const inward = side === 0 ? 1 : -1;
    this.goalInfo = { team, side, pts, gy, scorerY: gy + inward * 380, scorer: b.lastThrower };
    fx.explosion(b.x, gy + inward * 20, 1.1);
    fx.slow(0.3, 0.9);
    fx.shake(0.9);
    fx.doFlash(1, 0.85, 0.65, 0.45);
    fx.aberrate(0.8);
    fx.shock(b.x, gy, 1.2);
    audio.play('goal', { pan: this.pan(b.x) });
    music.stinger('goal');
    const scorerName = b.lastThrower && b.lastThrower.team === team ? b.lastThrower.name : t('ownGoal');
    this.announce(t('goal'), team.def.ui, `${scorerName}  +${pts}`, 2.8);
    for (const p of this.players) {
      const d = Math.hypot(p.x - b.x, p.y - gy);
      if (d < 220 && p.team !== team && !p.grounded) {
        const nx = (p.x - b.x) / (d || 1), ny = (p.y - gy) / (d || 1);
        p.knockDown(nx * 420, ny * 420, 1.6);
        p.hasBall = false;
      }
      p.charging = false;
    }
  }

  // ---------- objects / tokens ----------
  updateObjects(dt) {
    for (let i = 0; i < this.bumperFlash.length; i++) this.bumperFlash[i] = Math.max(0, this.bumperFlash[i] - dt * 3);
    for (let i = 0; i < this.electroFlash.length; i++) this.electroFlash[i] = Math.max(0, this.electroFlash[i] - dt * 2);
    for (const w of ['left', 'right']) for (let i = 0; i < STAR_YS.length; i++) this.starFlash[w][i] = Math.max(0, this.starFlash[w][i] - dt * 2);
    this.rampFlash[0] = Math.max(0, this.rampFlash[0] - dt);
    this.rampFlash[1] = Math.max(0, this.rampFlash[1] - dt);
    for (const tm of this.teams) { tm.rageT -= dt; tm.freezeT -= dt; }

    if (this.phase !== 'play') return;
    this.tokenTimer -= dt;
    if (this.tokenTimer <= 0 && this.tokens.length < 1) {
      this.tokenTimer = rand(12, 18);
      const tk = { x: rand(W * 0.2, W * 0.8), y: rand(H * 0.3, H * 0.7), type: pick(TOKEN_TYPES), t: 0, life: 12 };
      this.tokens.push(tk);
      fx.glow(tk.x, tk.y, 20, 120, 'rgba(255,220,160,1)', 0.3);
    }
    for (const tk of this.tokens) {
      tk.t += dt;
      for (const p of this.players) {
        if (p.grounded || p.z > 30) continue;
        if (Math.hypot(p.x - tk.x, p.y - tk.y) < 34) { this.collectToken(tk, p); break; }
      }
    }
    if (this.tokens.length) this.tokens = this.tokens.filter((tk) => !tk.taken && tk.t < tk.life);
  }

  collectToken(tk, p) {
    tk.taken = true;
    const tm = p.team, o = this.other(tm);
    audio.play('token');
    fx.glow(tk.x, tk.y, 20, 200, 'rgba(255,220,150,1)', 0.35);
    fx.sparks(tk.x, tk.y, 20, 18, 350);
    switch (tk.type) {
      case 'rage':
        tm.rageT = 9;
        this.announce(t('rage'), '#d4321a', t('rageSub', tm.def.name), 1.4);
        break;
      case 'shock':
        this.ball.electric = 7;
        this.ball.elecTeam = tm.idx;
        audio.play('electrify');
        fx.text(tk.x, tk.y - 60, t('electricBall'), '#9fe8ff', 26, 1.1);
        break;
      case 'freeze':
        o.freezeT = 5;
        audio.play('powerdown');
        this.announce(t('freeze'), '#a8d8e8', t('freezeSub', o.def.name), 1.4);
        break;
      case 'medic':
        for (const m of tm.players) {
          m.health = 100;
          m.wounds = 0;
          if (m.state === 'ko' || m.state === 'down') m.stateT = Math.max(m.stateT, m.downTime - 0.2);
        }
        fx.text(tk.x, tk.y - 60, t('medic'), '#9fd08a', 26, 1.1);
        break;
      case 'cash':
        tm.credits += 50;
        tm.banked += 1;
        this.recomputeScores();
        fx.text(tk.x, tk.y - 40, '+50 $', '#e8c050', 26, 1.1);
        break;
    }
  }
}
