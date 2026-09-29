// Match simulation: rules, ball physics, scoring objects, phases and human control.
import {
  FIELD_W as W, FIELD_H as H, CX, CY, GOAL_HALF, GOAL_DEPTH, GOAL_Z, BALL_R, BALL_GRAVITY, PLAYER_R,
  THROW_MIN, THROW_MAX, CHARGE_TIME, LOB_VZ, CATCH_R, SLIDE_TIME, GOAL_POINTS, STAR_POINTS, STAR_ROW_BONUS, KO_POINTS,
  BUMPERS, ELECTRO, STAR_XS, RAMP_HALF, TEAMS, FORMATION, PLAYER_NAMES, DIFFICULTIES,
} from './constants.js';
import { Player } from './player.js';
import { aiTeamUpdate, aiPlayerUpdate, gkUpdate } from './ai.js';
import { clamp, rand, pick, chance, lerp, angleDiff, TAU } from '../core/math.js';
import { fx } from '../render/fx.js';
import { audio } from '../audio/audio.js';
import { music } from '../audio/music.js';
import { readDevice } from '../core/input.js';

const MULTS = [1, 1.5, 2];
const TOKEN_TYPES = ['rage', 'shock', 'freeze', 'medic', 'cash'];

export class Match {
  /**
   * opts: { humans: [{device, team}], difficulty: 0..2, halfLength: seconds, demo: bool }
   */
  constructor(opts) {
    this.opts = opts;
    this.demo = !!opts.demo;
    this.diff = DIFFICULTIES[opts.difficulty ?? 1];
    this.halfLength = opts.halfLength ?? 90;
    this.time = 0;
    this.teams = TEAMS.map((def, i) => ({
      idx: i, def, dir: i === 0 ? 1 : -1, score: 0, banked: 0, mult: 0,
      goals: 0, kos: 0, tackles: 0, shots: 0, starsLit: 0, credits: 0,
      rageT: 0, freezeT: 0, players: [], human: false, ai: { presser: null, chaser: null, support: null, cover: null, t: 0 },
    }));
    for (const t of this.teams) {
      t.players = FORMATION.map((slot, k) => new Player(t, k, slot, PLAYER_NAMES[t.idx][k]));
    }
    this.players = this.teams.flatMap((t) => t.players);
    this.humans = (opts.humans || []).map((h, i) => ({ id: i, device: h.device, team: this.teams[h.team], player: null, switchCD: 0, color: i === 0 ? '#ffe14a' : '#6dff7a', input: null }));
    for (const h of this.humans) h.team.human = true;

    this.ball = {
      x: CX, y: CY, z: 0, vx: 0, vy: 0, vz: 0, owner: null, lastTeam: null, lastThrower: null,
      noCatchP: null, noCatchT: 0, electric: 0, elecTeam: -1, spin: 0, trail: [], inGoal: false, isShot: false,
      rampCD: 0, bumpCD: 0,
    };
    this.stars = { top: STAR_XS.map(() => -1), bottom: STAR_XS.map(() => -1) };
    this.starFlash = { top: STAR_XS.map(() => 0), bottom: STAR_XS.map(() => 0) };
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
    this.events = [];
    this.goalInfo = null;
    this.over = false;
    this.lastCountdown = -1;
    this.setupPositions(true);
    this.announce(this.demo ? '' : 'MI-TEMPS 1', '#ffd36a', 'SURVIVRE. DOMINER. MARQUER.');
  }

  // ---------- helpers ----------
  ownGoalX(team) { return team.dir > 0 ? 0 : W; }
  oppGoalX(team) { return team.dir > 0 ? W : 0; }
  other(team) { return this.teams[1 - team.idx]; }
  aiSpeed(team) { return team.human ? 1 : this.diff.speed; }
  formationPos(p) {
    const t = p.team;
    const fx_ = t.dir > 0 ? p.slot.x * W : W - p.slot.x * W;
    return { x: fx_, y: p.slot.y * H };
  }
  pan(x) {
    const cam = this.camera;
    if (!cam) return 0;
    return clamp((x - cam.x) / (cam.viewW * 0.6), -1, 1);
  }
  emit(type, p) {
    if (type === 'land') audio.play('land', { pan: this.pan(p.x) });
    if (type === 'thud') { audio.play('land', { pan: this.pan(p.x) }); fx.dust(p.x, p.y, 6); }
    if (type === 'revive') { fx.ring(p.x, p.y, '#7dff9a', 70, 0.5, 4); }
  }
  announce(text, color = '#fff', sub = '', dur = 1.8) {
    if (!text) return;
    this.announcements.push({ text, color, sub, t: 0, dur });
    if (this.announcements.length > 3) this.announcements.shift();
  }
  get teamScores() { return this.teams.map((t) => t.score); }

  recomputeScores() {
    for (const t of this.teams) {
      const lit = this.stars.top.filter((o) => o === t.idx).length + this.stars.bottom.filter((o) => o === t.idx).length;
      t.score = t.banked + lit * STAR_POINTS;
    }
  }

  setupPositions(snap) {
    for (const p of this.players) {
      const f = this.formationPos(p);
      // Kickoff line-up: stay in own half.
      const own = p.team.dir > 0 ? Math.min(f.x, CX - 90) : Math.max(f.x, CX + 90);
      p.home = { x: own, y: f.y };
      if (snap) {
        p.x = own; p.y = f.y; p.vx = 0; p.vy = 0; p.z = 0; p.vz = 0;
        p.setState('run');
        p.facing = p.team.dir > 0 ? 0 : Math.PI;
        p.hasBall = false; p.charging = false;
      }
    }
    const b = this.ball;
    Object.assign(b, { x: CX, y: CY, z: -30, vx: 0, vy: 0, vz: 0, owner: null, lastTeam: null, lastThrower: null, electric: 0, inGoal: false, isShot: false, trail: [] });
  }

  // ---------- main update ----------
  update(dt) {
    this.time += dt;
    this.phaseT += dt;
    for (const a of this.announcements) a.t += dt;
    this.announcements = this.announcements.filter((a) => a.t < a.dur);

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
          for (const t of this.teams) { t.dir = -t.dir; t.rageT = 0; t.freezeT = 0; }
          this.phase = 'intro';
          this.phaseT = 0;
          this.setupPositions(true);
          this.announce('MI-TEMPS 2', '#ffd36a', 'CHANGEMENT DE CAMP');
        }
        break;
      case 'fulltime':
        break;
    }

    this.updateHumans(dt);
    aiTeamUpdate(this, dt);

    for (const p of this.players) {
      if (this.phase === 'kickoff' || this.phase === 'intro' || this.phase === 'halftime') {
        this.walkHome(p, dt);
      } else if (this.phase === 'goal' || this.phase === 'fulltime') {
        this.celebrateOrSulk(p, dt);
      } else if (p.isGK) {
        gkUpdate(this, p, dt);
      } else if (!p.human) {
        aiPlayerUpdate(this, p, dt);
      }
      p.update(dt, this);
    }
    this.separatePlayers();
    if (this.phase === 'play') this.checkSlides();
    this.updateBall(dt);
    this.updateObjects(dt);

    // Music & crowd intensity
    const b = this.ball;
    const nearGoal = 1 - Math.min(Math.abs(b.x - 0), Math.abs(b.x - W)) / (W / 2);
    const target = this.phase === 'play' ? 0.35 + nearGoal * 0.4 + (this.clock < 20 ? 0.3 : 0) : this.phase === 'goal' ? 1 : 0.2;
    this.excitement = lerp(this.excitement, target, 1 - Math.exp(-dt * 1.5));
    if (!this.demo) {
      audio.setCrowd(this.excitement);
      music.setIntensity(this.phase === 'play' ? 0.45 + nearGoal * 0.25 + (this.clock < 20 ? 0.35 : 0) + (this.half === 3 ? 0.3 : 0) : 0.4);
    }
  }

  walkHome(p, dt) {
    const dx = p.home.x - p.x, dy = p.home.y - p.y;
    const d = Math.hypot(dx, dy);
    p.charging = false;
    if (p.state !== 'run') { p.intent = { mx: 0, my: 0 }; return; }
    if (d > 8) p.intent = { mx: dx / d * Math.min(1.3, d / 60), my: dy / d * Math.min(1.3, d / 60) };
    else {
      p.intent = { mx: 0, my: 0 };
      p.facing += angleDiff(p.facing, p.team.dir > 0 ? 0 : Math.PI) * Math.min(1, dt * 6);
    }
  }

  celebrateOrSulk(p, dt) {
    p.intent = { mx: 0, my: 0 };
    p.charging = false;
    const g = this.goalInfo;
    if (this.phase === 'goal' && g && p.team === g.team && p.state === 'run' && this.phaseT > 0.4 && chance(dt * 2)) {
      p.setState('celebrate');
    }
    if (p.state === 'celebrate') {
      if (this.phaseT > 3 || this.phase === 'fulltime') { /* keep celebrating at fulltime */ }
      const tx = g ? g.scorerX : CX, ty = CY;
      const dx = tx - p.x, dy = ty - p.y, d = Math.hypot(dx, dy);
      if (d > 120) p.intent = { mx: dx / d * 0.5, my: dy / d * 0.5 };
    }
  }

  startKickoff() {
    this.phase = 'kickoff';
    this.phaseT = 0;
    this.lastCountdown = -1;
    for (const p of this.players) if (p.state === 'celebrate') p.setState('run');
    this.setupPositions(false);
    const b = this.ball;
    Object.assign(b, { x: CX, y: CY, z: -30, vx: 0, vy: 0, vz: 0, owner: null, lastTeam: null, lastThrower: null, electric: 0, inGoal: false, isShot: false, trail: [] });
    for (const p of this.players) p.hasBall = false;
  }

  launchBall() {
    const b = this.ball;
    this.phase = 'play';
    this.phaseT = 0;
    // Snap stragglers into position so nobody is offside of the launcher.
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
    fx.glow(CX, CY, 0, 260, 'rgba(255,220,150,1)', 0.35);
    fx.smoke(CX, CY, 0, 14, 40);
    fx.sparks(CX, CY, 5, 30, 500);
    fx.ring(CX, CY, '#ffd27a', 260, 0.5, 8);
    fx.shake(0.3);
    this.announce(this.demo ? '' : 'CARNAGE !', '#ff5a1f', '', 0.9);
  }

  endOfPeriod() {
    audio.play('whistle', { long: true });
    this.clock = 0;
    const b = this.ball;
    if (b.owner) { b.owner.hasBall = false; b.owner.charging = false; b.owner = null; }
    if (this.half === 1) {
      this.phase = 'halftime';
      this.phaseT = 0;
      this.announce('MI-TEMPS', '#ffd36a', `${this.teams[0].score} — ${this.teams[1].score}`, 3);
      music.setMode('halftime');
    } else if (this.half === 2 && this.teams[0].score === this.teams[1].score && !this.demo) {
      this.half = 3;
      this.clock = 60;
      this.phase = 'intro';
      this.phaseT = 0;
      this.setupPositions(true);
      this.announce('MORT SUBITE', '#ff2a2a', 'PREMIER QUI MARQUE GAGNE', 2.4);
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
    for (const p of this.players) if (winner && p.team === winner && p.state === 'run') p.setState('celebrate');
    this.announce(winner ? 'VICTOIRE' : 'MATCH NUL', winner ? winner.def.glow : '#ddd', winner ? winner.def.name : '', 3);
    music.stinger('end');
    audio.crowdReact(1.2, 'cheer');
  }

  // ---------- humans ----------
  /** Called once per rendered frame: button edges stay latched until a sim step consumes them. */
  pollHumans() {
    for (const h of this.humans) {
      const inp = readDevice(h.device);
      if (!inp) continue;
      const e = h.edges || (h.edges = { action: false, jump: false, swap: false });
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
      if (!h.input) continue;
      const e = h.edges;
      const inp = { ...h.input, actionPressed: e.action, jumpPressed: e.jump, swapPressed: e.swap };
      e.action = e.jump = e.swap = false;
      this.pickControlled(h, inp.swapPressed && playable);
      const p = h.player;
      if (!p) continue;
      if (!playable) { p.charging = false; continue; }
      p.intent = { mx: inp.mx, my: inp.my };
      if (p.hasBall) {
        if (p.isGK) continue;
        // Aim follows the stick (or facing).
        const m = Math.hypot(inp.mx, inp.my);
        if (m > 0.2) { p.aimX = inp.mx / m; p.aimY = inp.my / m; }
        else { p.aimX = Math.cos(p.facing); p.aimY = Math.sin(p.facing); }
        if (inp.actionPressed && !p.charging) { p.charging = true; p.chargeT = 0; }
        if (p.charging) {
          p.chargeT += dt;
          if (!inp.action) {
            const power = clamp(p.chargeT / CHARGE_TIME, 0, 1);
            this.humanThrow(p, p.aimX, p.aimY, power, false);
          }
        }
        if (inp.jumpPressed && p.hasBall) this.humanThrow(p, p.aimX, p.aimY, 0.6, true);
      } else {
        p.charging = false;
        if (inp.actionPressed) {
          if (p.slide()) audio.play('slide', { pan: this.pan(p.x) });
        }
        if (inp.jumpPressed && p.jump()) audio.play('jump', { pan: this.pan(p.x) });
      }
    }
  }

  pickControlled(h, manual) {
    const team = h.team;
    const b = this.ball;
    const others = new Set(this.humans.filter((o) => o !== h && o.player).map((o) => o.player));
    const release = (np) => {
      if (h.player === np) return;
      if (h.player) { h.player.human = null; h.player.charging = false; }
      h.player = np;
      if (np) { np.human = h; np.ai.next = 0; }
      h.switchCD = 0.28;
    };
    // Carrier on my team → control it (unless goalkeeper).
    if (b.owner && b.owner.team === team && !b.owner.isGK) {
      if (!others.has(b.owner)) release(b.owner);
      return;
    }
    const cands = team.players.filter((p) => !p.isGK && !others.has(p));
    const target = this.ballTargetPoint();
    const score = (p) => Math.hypot(p.x - target.x, p.y - target.y) + (p.grounded ? 400 : 0);
    if (manual) {
      const sorted = cands.filter((p) => p !== h.player).sort((a, c) => score(a) - score(c));
      if (sorted[0]) { release(sorted[0]); audio.play('ui', { kind: 'move' }); }
      return;
    }
    const cur = h.player && !h.player.isGK && !others.has(h.player) ? h.player : null;
    if (!cur) { release(cands.sort((a, c) => score(a) - score(c))[0]); return; }
    if (h.switchCD > 0 || cur.state === 'slide' || cur.state === 'jump') return;
    // Keep control while the player is actively being moved toward the ball.
    let best = cur, bs = score(cur);
    for (const p of cands) { const s = score(p); if (s < bs - 90) { best = p; bs = s; } }
    if (best !== cur) release(best);
  }

  ballTargetPoint() {
    const b = this.ball;
    if (b.owner) return { x: b.owner.x, y: b.owner.y };
    // Where will the ball be reachable soon?
    return { x: b.x + b.vx * 0.3, y: b.y + b.vy * 0.3 };
  }

  humanThrow(p, dx, dy, power, lob) {
    // Aim assist: snap toward a teammate or the goal inside a cone.
    const team = p.team;
    const ang = Math.atan2(dy, dx);
    let best = null, bestScore = Infinity;
    const gx = this.oppGoalX(team);
    const goalAng = Math.atan2(CY - p.y, gx - p.x);
    const goalDist = Math.hypot(gx - p.x, CY - p.y);
    if (Math.abs(angleDiff(ang, goalAng)) < 0.42 && goalDist < 1100) {
      // Aim to the corner the stick leans toward.
      const off = clamp(angleDiff(goalAng, ang) * 500, -GOAL_HALF + 28, GOAL_HALF - 28);
      best = { x: gx, y: CY + off, shot: true };
      bestScore = 0;
    }
    if (!best) {
      for (const m of team.players) {
        if (m === p || m.grounded) continue;
        const d = Math.hypot(m.x - p.x, m.y - p.y);
        if (d < 110 || d > 1100) continue;
        const a = Math.atan2(m.y - p.y, m.x - p.x);
        const da = Math.abs(angleDiff(ang, a));
        if (da > 0.5) continue;
        const s = da * 600 + d * 0.3;
        if (s < bestScore) { bestScore = s; best = { x: m.x, y: m.y, mate: m }; }
      }
    }
    this.throwBall(p, best ? best : { x: p.x + dx * 600, y: p.y + dy * 600 }, power, lob, !!best?.mate);
  }

  // ---------- ball ----------
  throwBall(p, target, power, lob, lead = false) {
    const b = this.ball;
    if (b.owner !== p) return;
    let tx = target.x, ty = target.y;
    const speed = lerp(THROW_MIN, THROW_MAX, power) * p.stats.throw * (p.team.rageT > 0 ? 1.08 : 1);
    if (lead && target.mate) {
      const d = Math.hypot(tx - p.x, ty - p.y);
      const t = lob ? 0.95 : d / speed;
      tx += target.mate.vx * t * 0.9;
      ty += target.mate.vy * t * 0.9;
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
      const tFlight = 1.0;
      const hs = clamp(d / tFlight, 280, 950);
      b.vx = ux * hs; b.vy = uy * hs; b.vz = LOB_VZ;
      audio.play('lob', { pan: this.pan(p.x) });
    } else {
      b.vx = ux * speed; b.vy = uy * speed;
      const t = d / speed;
      // Keep the ball near chest height at the target.
      b.vz = clamp((34 - 44 + 0.5 * BALL_GRAVITY * t * t) / Math.max(0.05, t), 40, 300);
      audio.play('throw', { power, pan: this.pan(p.x) });
    }
    if (b.isShot) p.team.shots++;
    p.catchCD = 0.2;
    fx.dust(p.x, p.y, 3);
    if (power > 0.85 && !lob) { fx.shake(0.12); fx.sparks(b.x, b.y, b.z, 6, 300, ux, uy, 0.8); }
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
      if (Math.random() < 0.5) {
        const a = rand(0, TAU);
        fx.arc(b.x, b.y, b.z + (b.owner ? 0 : 0), b.x + Math.cos(a) * rand(20, 45), b.y + Math.sin(a) * rand(10, 30), b.z + rand(-20, 20));
      }
    }
    if (b.owner) {
      const o = b.owner;
      b.x = o.x + Math.cos(o.facing) * 16;
      b.y = o.y + Math.sin(o.facing) * 16;
      b.z = o.z + 42;
      b.vx = o.vx; b.vy = o.vy; b.vz = 0;
      b.trail.length = 0;
      if (b.electric > 0 && b.elecTeam !== o.team.idx) b.elecTeam = o.team.idx;
      return;
    }
    if (b.inGoal) {
      b.vx *= Math.exp(-6 * dt); b.vy *= Math.exp(-6 * dt);
      b.x += b.vx * dt; b.y += b.vy * dt;
      b.z = Math.max(0, b.z + b.vz * dt); b.vz -= BALL_GRAVITY * dt;
      if (b.z <= 0) b.vz = Math.abs(b.vz) * 0.3;
      b.x = clamp(b.x, -GOAL_DEPTH + BALL_R, W + GOAL_DEPTH - BALL_R);
      b.y = clamp(b.y, CY - GOAL_HALF + BALL_R, CY + GOAL_HALF - BALL_R);
      return;
    }

    // Integrate
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
            fx.dust(b.x, b.y, 2, '#7a5f45', 10);
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

    // Trail
    b.trail.push({ x: b.x, y: b.y - b.z });
    if (b.trail.length > 12) b.trail.shift();

    if (this.phase !== 'play') return;

    // Bumpers
    BUMPERS.forEach((bm, i) => {
      if (b.z > 60) return;
      const dx = b.x - bm.x, dy = b.y - bm.y, d = Math.hypot(dx, dy);
      if (d < bm.r + BALL_R && d > 0.01) {
        const nx = dx / d, ny = dy / d;
        const vn = b.vx * nx + b.vy * ny;
        if (vn < 0) {
          b.vx -= 2 * vn * nx; b.vy -= 2 * vn * ny;
          const sp = Math.max(520, Math.hypot(b.vx, b.vy) * 1.15);
          const m = Math.hypot(b.vx, b.vy) || 1;
          b.vx = (b.vx / m) * sp; b.vy = (b.vy / m) * sp;
          b.vz = Math.max(b.vz, 120);
        }
        b.x = bm.x + nx * (bm.r + BALL_R + 1);
        b.y = bm.y + ny * (bm.r + BALL_R + 1);
        this.bumperFlash[i] = 1;
        if (b.bumpCD <= 0) {
          audio.play('bumper', { pan: this.pan(b.x) });
          fx.sparks(b.x, b.y, b.z + 10, 14, 420, nx, ny, 1.6);
          fx.glow(bm.x, bm.y, 30, 180, 'rgba(255,200,120,1)', 0.25);
          fx.shake(0.08);
          b.bumpCD = 0.08;
        }
      }
    });

    // Electro pads
    ELECTRO.forEach((e, i) => {
      if (b.z > 40 || b.lastTeam === null) return;
      if (Math.hypot(b.x - e.x, b.y - e.y) < e.r + BALL_R) {
        if (b.electric <= 0 || b.elecTeam !== b.lastTeam) {
          audio.play('electrify', { pan: this.pan(b.x) });
          fx.glow(e.x, e.y, 10, 240, 'rgba(90,220,255,1)', 0.35);
          for (let k = 0; k < 6; k++) fx.arc(e.x, e.y, 0, b.x + rand(-30, 30), b.y + rand(-30, 30), b.z + rand(0, 40));
          this.announce('BALLE ÉLECTRIQUE', '#6ff4ff', '', 1.1);
        }
        b.electric = 5;
        b.elecTeam = b.lastTeam;
        this.electroFlash[i] = 1;
      }
    });

    // Catching
    if (b.z < 120) this.tryCatch(b);
  }

  ballWalls(b) {
    const r = BALL_R;
    // Top / bottom walls: bounce, stars, ramps
    if (b.y < r) {
      b.y = r;
      if (b.vy < 0) { this.wallHit(b, 'top'); b.vy = -b.vy * 0.8; }
    } else if (b.y > H - r) {
      b.y = H - r;
      if (b.vy > 0) { this.wallHit(b, 'bottom'); b.vy = -b.vy * 0.8; }
    }
    // Ends: goals
    for (const side of [0, 1]) {
      const beyond = side === 0 ? b.x < r : b.x > W - r;
      if (!beyond) continue;
      const inMouth = Math.abs(b.y - CY) < GOAL_HALF - r * 0.5;
      if (inMouth && b.z < GOAL_Z && this.phase === 'play') {
        const crossed = side === 0 ? b.x < -r : b.x > W + r;
        if (crossed) this.goalScored(side);
        continue;
      }
      // Post / wall bounce
      b.x = side === 0 ? r : W - r;
      const vIn = side === 0 ? -b.vx : b.vx;
      if (vIn > 0) {
        b.vx = -b.vx * 0.8;
        const post = Math.abs(Math.abs(b.y - CY) - GOAL_HALF) < 25 || inMouth;
        if (this.phase === 'play') {
          audio.play('clank', { power: clamp(vIn / 800, 0.2, 1), pan: this.pan(b.x) });
          fx.sparks(b.x, b.y, b.z, post ? 18 : 6, post ? 500 : 250, side === 0 ? 1 : -1, 0, 1.8);
          if (post) { fx.shake(0.15); if (b.isShot) this.announce('POTEAU !', '#ffd36a', '', 0.9); }
        }
      }
    }
  }

  wallHit(b, wall) {
    if (this.phase !== 'play') return;
    const sp = Math.abs(b.vy);
    audio.play('clank', { power: clamp(sp / 900, 0.15, 0.9), pan: this.pan(b.x) });
    if (sp > 300) fx.sparks(b.x, b.y, b.z, 6, 260, 0, wall === 'top' ? 1 : -1, 1.8);
    if (b.lastTeam === null || b.z > 95) return;
    // Ramp → score multiplier
    if (Math.abs(b.x - CX) < RAMP_HALF && b.rampCD <= 0) {
      b.rampCD = 1;
      const t = this.teams[b.lastTeam], o = this.other(t);
      this.rampFlash[wall === 'top' ? 0 : 1] = 1.5;
      if (t.mult < 2) {
        t.mult++;
        o.mult = 0;
        audio.play('multiplier');
        this.announce(`MULTIPLICATEUR x${MULTS[t.mult]}`, t.def.glow, t.def.name, 1.6);
        fx.glow(b.x, b.y, 20, 300, t.idx === 0 ? 'rgba(255,140,40,1)' : 'rgba(60,200,255,1)', 0.4);
      }
      return;
    }
    // Stars
    const row = this.stars[wall];
    STAR_XS.forEach((sx, i) => {
      if (Math.abs(b.x - sx) < 34 && row[i] !== b.lastTeam) {
        row[i] = b.lastTeam;
        this.starFlash[wall][i] = 1;
        const t = this.teams[b.lastTeam];
        t.starsLit++;
        audio.play('star', { pan: this.pan(sx), team: t.idx });
        fx.sparks(sx, wall === 'top' ? -50 : H + 20, 0, 20, 380);
        fx.glow(sx, wall === 'top' ? -50 : H + 20, 0, 160, t.idx === 0 ? 'rgba(255,160,50,1)' : 'rgba(80,220,255,1)', 0.4);
        fx.text(sx, wall === 'top' ? 40 : H - 40, '+2', t.def.accent, 30, 1);
        if (row.every((o) => o === t.idx)) {
          t.banked += STAR_ROW_BONUS;
          audio.play('starbonus');
          this.announce('RANGÉE D\'ÉTOILES', t.def.glow, `+${STAR_ROW_BONUS} ${t.def.name}`, 1.8);
          fx.doFlash(1, 0.85, 0.5, 0.25);
          setTimeout(() => { for (let k = 0; k < row.length; k++) row[k] = -1; this.recomputeScores(); }, 1400);
        }
        this.recomputeScores();
      }
    });
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
    // Electric ball zaps opponents.
    if (b.electric > 0 && b.elecTeam !== p.team.idx && b.elecTeam >= 0) {
      this.shockPlayer(p);
      const a = Math.atan2(b.y - p.y, b.x - p.x);
      b.vx = Math.cos(a) * 380; b.vy = Math.sin(a) * 380; b.vz = 250;
      b.noCatchP = p; b.noCatchT = 0.6;
      return;
    }
    const opponent = b.lastTeam !== null && b.lastTeam !== p.team.idx;
    // Goalkeeper vs shot: save, parry or miss.
    if (p.isGK && b.isShot && opponent) {
      const skill = p.team.human ? 0.8 : this.diff.gk;
      const pSave = clamp(skill + 0.08 - (sp - 850) / 1000, 0.15, 0.92);
      if (!chance(pSave)) {
        if (chance(0.5)) {
          // Parry
          b.vx = -b.vx * 0.35 + rand(-200, 200); b.vy = b.vy * 0.4 + rand(-300, 300); b.vz = 300;
          b.noCatchP = p; b.noCatchT = 0.4;
          audio.play('hit', { power: 0.5, pan: this.pan(p.x) });
          fx.sparks(b.x, b.y, b.z, 12, 350);
          this.announce('DÉVIÉ !', '#ffffff', '', 0.8);
        } else {
          p.catchCD = 0.5;
        }
        return;
      }
      this.announce('ARRÊT !', '#ffffff', '', 0.8);
    } else if (opponent && sp > 1150 && !p.isGK && chance(0.45)) {
      // Too hot to handle: deflects off the body.
      b.vx = -b.vx * 0.3 + rand(-150, 150); b.vy = -b.vy * 0.3 + rand(-150, 150); b.vz = 220;
      b.noCatchP = p; b.noCatchT = 0.4;
      p.setState('stun'); p.stunTime = 0.35;
      audio.play('hit', { power: 0.6, pan: this.pan(p.x) });
      fx.sparks(b.x, b.y, b.z, 10, 300);
      return;
    }
    // Clean catch
    b.owner = p;
    p.hasBall = true;
    p.holdT = 0;
    b.isShot = false;
    b.lastTeam = p.team.idx;
    audio.play('catch', { pan: this.pan(p.x) });
    if (opponent && !p.isGK) {
      fx.text(p.x, p.y - 40, 'INTERCEPTÉ', '#ffffff', 22, 0.8);
    }
    if (p.state === 'dive') { fx.dust(p.x, p.y, 8); fx.shake(0.1); }
  }

  shockPlayer(p) {
    p.shockT = 1.2;
    p.health -= 20;
    const ko = p.health <= 0;
    p.knockDown(rand(-60, 60), rand(-60, 60), ko ? 4.5 : 1.3, ko);
    audio.play('zap', { pan: this.pan(p.x), long: true });
    fx.glow(p.x, p.y, 40, 260, 'rgba(90,220,255,1)', 0.4);
    for (let i = 0; i < 8; i++) fx.arc(p.x, p.y, rand(10, 60), p.x + rand(-60, 60), p.y + rand(-30, 30), rand(0, 80));
    fx.sparks(p.x, p.y, 40, 20, 400);
    fx.smoke(p.x, p.y, 40, 5, 20);
    fx.shake(0.35);
    fx.aberrate(0.6);
    fx.decal('burn', p.x, p.y, { r: 30 });
    this.announce('ÉLECTROCUTÉ !', '#6ff4ff', '', 1);
    if (ko) this.registerKO(p, this.teams[this.ball.elecTeam]);
  }

  // ---------- combat ----------
  checkSlides() {
    for (const a of this.players) {
      if (a.state !== 'slide' || a.stateT > SLIDE_TIME * 0.95) continue;
      for (const v of this.players) {
        if (v.team === a.team || v === a) continue;
        if (v.grounded || v.hitImmune > 0 || v.z > 22 || v.state === 'slide' && v.stateT < 0.15) continue;
        const d = Math.hypot(v.x - a.x, v.y - a.y);
        if (d < PLAYER_R * 2 + 2) this.tackle(a, v);
      }
    }
  }

  tackle(a, v) {
    const dirx = Math.cos(a.facing), diry = Math.sin(a.facing);
    const rage = a.team.rageT > 0 ? 1.5 : 1;
    const dmg = 27 * a.stats.power * rage * rand(0.8, 1.25) * (v.isGK ? 0.7 : 1);
    v.health -= dmg;
    v.hitFlash = 0.09;
    v.hitImmune = 1.4;
    const ko = v.health <= 0;
    const hadBall = v.hasBall;
    const force = 380 * rage;
    if (hadBall) this.releaseBallFrom(v, dirx * 260 + v.vx * 0.3 + rand(-120, 120), diry * 260 + v.vy * 0.3 + rand(-120, 120));
    v.knockDown(dirx * force, diry * force, ko ? 4.5 : 1.05, ko);
    a.vx *= 0.45; a.vy *= 0.45;
    a.team.tackles++;

    const hx = (a.x + v.x) / 2, hy = (a.y + v.y) / 2;
    fx.freeze(ko ? 0.14 : 0.07);
    fx.shake(ko ? 0.7 : 0.42);
    fx.aberrate(ko ? 0.8 : 0.35);
    fx.blood(hx, hy, 34, Math.round(10 + dmg * 0.6), dirx, diry, 1.2);
    fx.sparks(hx, hy, 34, 14, 420, dirx, diry, 1.8);
    fx.debris(hx, hy, 30, 4, '#5a4a3a');
    fx.dust(v.x, v.y, 8);
    fx.glow(hx, hy, 34, 150, 'rgba(255,230,200,1)', 0.12);
    fx.decal('skid', a.x - dirx * 60, a.y - diry * 60, { x2: a.x, y2: a.y, w: 12 });
    audio.play('hit', { power: 0.8 + dmg / 40, pan: this.pan(hx) });
    if (hadBall) {
      audio.crowdReact(0.7, 'cheer');
      if (chance(0.5)) this.announce(pick(['BRUTAL !', 'DÉMOLI !', 'CRUNCH !', 'SANS PITIÉ !']), '#ff4a2a', '', 0.9);
    }
    if (ko) this.registerKO(v, a.team);
  }

  registerKO(v, byTeam) {
    if (!byTeam) return;
    byTeam.banked += KO_POINTS;
    byTeam.kos++;
    this.recomputeScores();
    fx.slow(0.3, 0.5);
    fx.blood(v.x, v.y, 20, 30, 0, 0, 1.4);
    fx.shock(v.x, v.y, 0.8);
    fx.doFlash(0.8, 0.05, 0.02, 0.18);
    fx.text(v.x, v.y - 30, `K.O. +${KO_POINTS}`, '#ff3322', 34, 1.4);
    audio.play('ko', { pan: this.pan(v.x) });
    this.announce('K.O. !', '#ff2a1a', `${v.name} EST AU TAPIS`, 1.4);
  }

  separatePlayers() {
    const ps = this.players;
    for (let i = 0; i < ps.length; i++) {
      const a = ps[i];
      if (a.grounded) continue;
      for (let j = i + 1; j < ps.length; j++) {
        const b = ps[j];
        if (b.grounded) continue;
        if (Math.abs(a.z - b.z) > 40) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const d2 = dx * dx + dy * dy;
        const min = PLAYER_R * 1.7;
        if (d2 < min * min && d2 > 0.0001) {
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
    // side 0 = left goal: scored by the team attacking toward x=0
    const team = this.teams.find((t) => this.oppGoalX(t) === (side === 0 ? 0 : W));
    const pts = Math.round(GOAL_POINTS * MULTS[team.mult]);
    team.banked += pts;
    team.goals++;
    this.recomputeScores();
    b.inGoal = true;
    b.electric = 0;
    this.phase = 'goal';
    this.phaseT = 0;
    const gx = side === 0 ? 0 : W;
    this.goalInfo = { team, side, pts, gx, scorerX: team.dir > 0 ? W - 350 : 350, scorer: b.lastThrower };
    fx.explosion(gx + (side === 0 ? 30 : -30), b.y, 1.2);
    fx.slow(0.25, 1.1);
    fx.shake(1);
    fx.doFlash(1, 0.9, 0.7, 0.55);
    fx.aberrate(1);
    fx.shock(gx, b.y, 1.4);
    fx.text(gx + (side === 0 ? 160 : -160), CY - 60, `+${pts}`, team.def.accent, 60, 2);
    audio.play('goal', { pan: this.pan(gx) });
    music.stinger('goal');
    const scorerName = b.lastThrower && b.lastThrower.team === team ? b.lastThrower.name : 'CONTRE SON CAMP';
    this.announce('BUT !', team.def.glow, `${scorerName}  +${pts}`, 2.8);
    // Knock nearby defenders from the blast.
    for (const p of this.players) {
      const d = Math.hypot(p.x - gx, p.y - b.y);
      if (d < 220 && p.team !== team && !p.grounded) {
        const nx = (p.x - gx) / (d || 1), ny = (p.y - b.y) / (d || 1);
        p.knockDown(nx * 420, ny * 420, 1.6);
        if (p.hasBall) p.hasBall = false;
      }
    }
    for (const p of this.players) { p.charging = false; }
    if (this.half === 3) { /* sudden death: finish after celebration */ }
  }

  // ---------- objects / tokens ----------
  updateObjects(dt) {
    for (let i = 0; i < this.bumperFlash.length; i++) this.bumperFlash[i] = Math.max(0, this.bumperFlash[i] - dt * 3);
    for (let i = 0; i < this.electroFlash.length; i++) this.electroFlash[i] = Math.max(0, this.electroFlash[i] - dt * 2);
    for (const w of ['top', 'bottom']) for (let i = 0; i < STAR_XS.length; i++) this.starFlash[w][i] = Math.max(0, this.starFlash[w][i] - dt * 2);
    this.rampFlash = this.rampFlash.map((v) => Math.max(0, v - dt));
    for (const t of this.teams) { t.rageT -= dt; t.freezeT -= dt; }

    if (this.phase !== 'play') return;
    this.tokenTimer -= dt;
    if (this.tokenTimer <= 0 && this.tokens.length < 2) {
      this.tokenTimer = rand(9, 15);
      const type = pick(TOKEN_TYPES);
      const tk = { x: rand(W * 0.22, W * 0.78), y: rand(H * 0.15, H * 0.85), type, t: 0, life: 11 };
      this.tokens.push(tk);
      fx.ring(tk.x, tk.y, '#fff2b0', 90, 0.5, 4);
      fx.glow(tk.x, tk.y, 20, 140, 'rgba(255,240,180,1)', 0.3);
    }
    for (const tk of this.tokens) {
      tk.t += dt;
      for (const p of this.players) {
        if (p.grounded || p.z > 30) continue;
        if (Math.hypot(p.x - tk.x, p.y - tk.y) < 34) { this.collectToken(tk, p); break; }
      }
    }
    this.tokens = this.tokens.filter((tk) => !tk.taken && tk.t < tk.life);
  }

  collectToken(tk, p) {
    tk.taken = true;
    const t = p.team, o = this.other(t);
    audio.play('token');
    fx.glow(tk.x, tk.y, 20, 220, 'rgba(255,240,160,1)', 0.35);
    fx.sparks(tk.x, tk.y, 20, 18, 350);
    fx.ring(tk.x, tk.y, t.def.glow, 140, 0.45, 6);
    switch (tk.type) {
      case 'rage':
        t.rageT = 9;
        this.announce('RAGE', '#ff3b1a', `${t.def.name} DÉCHAÎNÉS`, 1.4);
        break;
      case 'shock':
        this.ball.electric = 7;
        this.ball.elecTeam = t.idx;
        audio.play('electrify');
        this.announce('BALLE ÉLECTRIQUE', '#6ff4ff', t.def.name, 1.3);
        break;
      case 'freeze':
        o.freezeT = 5;
        audio.play('powerdown');
        this.announce('ENTRAVÉS', '#9fe8ff', `${o.def.name} RALENTIS`, 1.4);
        break;
      case 'medic':
        for (const m of t.players) {
          m.health = 100;
          if (m.state === 'ko' || m.state === 'down') m.stateT = Math.max(m.stateT, m.downTime - 0.2);
          fx.ring(m.x, m.y, '#7dff9a', 60, 0.5, 4);
        }
        this.announce('SOINS', '#7dff9a', t.def.name, 1.2);
        break;
      case 'cash':
        t.credits += 50;
        t.banked += 1;
        this.recomputeScores();
        fx.text(tk.x, tk.y - 20, '+50 $', '#ffd84a', 30, 1.2);
        break;
    }
  }
}
