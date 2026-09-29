// Simulation d'un match : joueurs, balle, règles, score, phases (intro → coup d'envoi → jeu → but → mi-temps → fin).
import {
  W, H, CY, GOAL_H, GOAL_D, GOAL_TOP, BALL_R, GRAVITY, FORMATION, BUMPERS, PORTALS, PADS, DIFFICULTY, PAL, TEAMS,
  clamp, lerp, rand, randi, pick, dist, TAU, VIEW_W, VIEW_H,
} from './config.js';
import { thinkOutfield, thinkKeeper } from './ai.js';

const DT = 1 / 120;
const PLAYER_R = 22, KEEPER_R = 36;
const MAX_BALL = 1750;

const blankInput = () => ({ mx: 0, my: 0, a: false, aPressed: false, aReleased: false, bPressed: false, turbo: false, throw: null, swPressed: false });

export class Match {
  constructor(o) {
    this.audio = o.audio; this.music = o.music; this.fx = o.fx; this.inputDev = o.input;
    this.mode2p = !!o.mode2p;
    this.diffIdx = o.difficulty ?? 1;
    this.halfLen = o.duration ?? 90;
    this.onEnd = o.onEnd || (() => {});
    this.defs = [o.teamA, o.teamB];
    this.t = 0; this.acc = 0; this.timeScale = 1; this.targetScale = 1;
    this.half = 1; this.clock = this.halfLen; this.overtime = false;
    this.phase = 'intro'; this.phaseT = 0;
    this.pending = [{ aPressed: false, aReleased: false, bPressed: false, swPressed: false }, { aPressed: false, aReleased: false, bPressed: false, swPressed: false }];
    this.tokens = []; this.tokenTimer = 5;
    this.bumperPulse = BUMPERS.map(() => 0);
    this.pads = PADS.map((p) => ({ ...p, owner: -1, flash: 0 }));
    this.portalCd = 0; this.portalGlow = 0;
    this.goalFlash = [0, 0];
    this.lastGoalSide = -1; // 0 gauche, 1 droite
    this.scoredTeam = -1;
    this.excite = 0.3;
    this.announce = null;   // {text, sub, t, color}
    this.hint = 6;
    this.aiTick = 0;
    this.kickoffPlayed = false;
    this.cam = { x: W / 2, y: CY, zoom: 0.8, kx: 0, ky: 0, targetZoom: 0.86 };
    this.events = [];
    this.result = null;

    this.teams = [0, 1].map((i) => ({
      i, def: this.defs[i], attackDir: i === 0 ? 1 : -1, score: 0, goals: 0, mult: 1, coins: 0, freeze: 0,
      human: o.attract ? -1 : (i === 0 ? 0 : (this.mode2p ? 1 : -1)), ctrl: null, players: [], switchCd: 0, pendingSwitch: null, pendingSwitchT: 0,
      stats: { shots: 0, tackles: 0, saves: 0, pads: 0, coins: 0, hits: 0 },
    }));
    this.players = [];
    for (const t of this.teams) {
      FORMATION.forEach((f, idx) => {
        const p = {
          id: this.players.length, team: t.i, idx, role: f.role, num: idx === 0 ? 1 : idx + 3, x: 0, y: 0, vx: 0, vy: 0, z: 0, vz: 0,
          r: f.role === 'GK' ? KEEPER_R : PLAYER_R, fx: t.attackDir, fy: 0, flip: t.attackDir < 0,
          stun: 0, slideT: 0, slideCd: 0, slideDx: 1, slideDy: 0, jumpT: 0, hasBall: false, chargeT: 0, noPickT: 0,
          stamina: 1, turboOn: false, turboLock: false, speedT: 0, powerT: 0, boostFx: 0,
          runPhase: Math.random() * 6, sq: 0, sqv: 0, celebrate: 0, sad: 0, blink: 0, blinkT: rand(1, 4),
          input: blankInput(), ai: { decideT: rand(0, 0.5), plan: 'dribble', charging: false, chargeLeft: 0, aim: { x: 1, y: 0 }, holdT: 0, trackY: CY, slideChance: 0, seed: Math.random() },
          returnHome: false, reach: [60, -30], stepT: 0, hitCd: 0, hurtT: 0, lastSlideFx: 0,
          chargeSnd: null, moveMag: 0, kick: 0,
        };
        t.players.push(p); this.players.push(p);
      });
    }
    this.ball = { x: W / 2, y: CY, z: 0, vx: 0, vy: 0, vz: 0, r: BALL_R, holder: null, last: null, lastTeam: -1, rot: 0, state: 'launcher', trail: [], heat: 0, noPickAll: 0, thrower: null, thrownT: 0, portalCd: 0, bounceCd: 0, shotBy: -1 };
    this.placeAll(true);
  }

  diff(teamI) {
    // équipe contrôlée par un humain : coéquipiers IA "normal" ; adversaire : difficulté choisie
    const t = this.teams[teamI];
    if (t.human >= 0) return DIFFICULTY[1];
    return DIFFICULTY[this.diffIdx];
  }

  homeFor(p) {
    const t = this.teams[p.team], f = FORMATION[p.idx];
    return { x: t.attackDir > 0 ? f.fx * W : W - f.fx * W, y: f.fy * H };
  }

  placeAll(instant) {
    for (const p of this.players) {
      const h = this.homeFor(p);
      if (instant) { p.x = h.x; p.y = h.y; p.vx = p.vy = 0; p.stun = 0; p.slideT = 0; p.z = 0; p.vz = 0; p.hasBall = false; p.fx = this.teams[p.team].attackDir; p.flip = p.fx < 0; p.celebrate = 0; p.sad = 0; }
    }
  }

  setPhase(n) { this.phase = n; this.phaseT = 0; }

  // ------------------------------------------------------------------ boucle
  update(realDt) {
    const fx = this.fx;
    // hit-stop : la simulation gèle, les effets continuent doucement
    if (fx.hitstop > 0) { fx.hitstop -= realDt; fx.update(realDt * 0.2); this.updateCamera(realDt); return; }
    this.timeScale += (this.targetScale - this.timeScale) * (1 - Math.exp(-8 * realDt));
    this.harvestInput();
    this.acc += Math.min(realDt, 0.05) * this.timeScale;
    let n = 0;
    while (this.acc >= DT && n < 12) { this.step(DT); this.acc -= DT; n++; }
    this.updateCamera(realDt);
    fx.update(realDt * this.timeScale);
    this.audio.updateCrowd(realDt);
    // trace de la balle
    const b = this.ball;
    if (b.state === 'free') { b.trail.push({ x: b.x, y: b.y, z: b.z, s: Math.hypot(b.vx, b.vy) }); if (b.trail.length > 16) b.trail.shift(); }
    else if (b.trail.length) b.trail.shift();
    for (const p of this.pads) p.flash = Math.max(0, p.flash - realDt * 2.5);
    for (let i = 0; i < 2; i++) this.goalFlash[i] = Math.max(0, this.goalFlash[i] - realDt);
    this.portalGlow = Math.max(0, this.portalGlow - realDt);
    for (let i = 0; i < this.bumperPulse.length; i++) this.bumperPulse[i] = Math.max(0, this.bumperPulse[i] - realDt * 4);
    if (this.announce) { this.announce.t += realDt; if (this.announce.t > this.announce.dur) this.announce = null; }
    this.hint = Math.max(0, this.hint - realDt);
    this.excite += (this.targetExcite() - this.excite) * (1 - Math.exp(-2 * realDt));
    this.audio.setCrowd(this.excite);
  }

  targetExcite() {
    const b = this.ball, sp = Math.hypot(b.vx, b.vy);
    let e = 0.25 + Math.min(0.25, sp / 4000);
    const nearGoal = Math.min(b.x, W - b.x);
    if (nearGoal < 320 && this.phase === 'play') e += 0.2;
    if (this.phase === 'goal') e = 1;
    if (this.clock < 15 && this.phase === 'play') e += 0.15;
    return Math.min(1, e);
  }

  harvestInput() {
    const d = this.inputDev;
    for (let s = 0; s < 2; s++) {
      const sl = d.slots[s], pe = this.pending[s];
      pe.aPressed ||= sl.aPressed; pe.aReleased ||= sl.aReleased; pe.bPressed ||= sl.bPressed; pe.swPressed ||= sl.swPressed;
    }
  }

  step(dt) {
    this.t += dt; this.phaseT += dt;
    this.updatePhase(dt);
    const canPlay = this.phase === 'play' || this.phase === 'kickoff' || this.phase === 'overtime';
    // contrôle humain
    for (const t of this.teams) this.updateControl(t, dt);
    // IA (30 Hz)
    this.aiTick += dt;
    const doAI = this.aiTick >= 1 / 30;
    if (doAI) {
      const dtAI = this.aiTick; this.aiTick = 0;
      this.computeChasers();
      for (const p of this.players) {
        const t = this.teams[p.team];
        if (t.human >= 0 && t.ctrl === p) continue;
        if (!(this.phase === 'play' || this.phase === 'overtime')) { this.idleInput(p); continue; }
        if (p.role === 'GK') thinkKeeper(this, p, dtAI); else thinkOutfield(this, p, dtAI);
      }
    }
    for (const p of this.players) {
      const t = this.teams[p.team];
      if (t.human >= 0 && t.ctrl === p) this.fillHumanInput(p, t.human, canPlay);
      this.updatePlayer(p, dt, canPlay);
      p.input.aPressed = p.input.aReleased = p.input.bPressed = p.input.swPressed = false; p.input.throw = null;
    }
    for (let s = 0; s < 2; s++) { const pe = this.pending[s]; pe.aPressed = pe.aReleased = pe.bPressed = pe.swPressed = false; }
    this.collidePlayers(dt);
    this.updateBall(dt);
    this.updateTokens(dt);
    for (const t of this.teams) { if (t.freeze > 0) t.freeze -= dt; t.switchCd -= dt; }
    if (this.portalCd > 0) this.portalCd -= dt;
  }

  idleInput(p) {
    const i = p.input; i.mx = i.my = 0; i.a = false; i.turbo = false; i.throw = null;
    if (p.returnHome) {
      const h = this.homeFor(p), dx = h.x - p.x, dy = h.y - p.y, d = Math.hypot(dx, dy);
      if (d > 12) { i.mx = dx / d; i.my = dy / d; i.turbo = d > 200; } else { p.returnHome = false; }
    }
  }

  // ------------------------------------------------------------------ phases
  updatePhase(dt) {
    const ph = this.phase;
    if (ph === 'intro') {
      if (this.phaseT > 2.4) { this.setPhase('countdown'); this.count = 3; this.audio.sfx('beep'); this.announceText('3', '', PAL.mustardLight, 0.9); this.music.play(this.half === 1 ? 'match' : 'match2'); this.music.setIntensity(0.35); }
    } else if (ph === 'countdown') {
      const n = 3 - Math.floor(this.phaseT / 0.9);
      if (n !== this.count) {
        this.count = n;
        if (n > 0) { this.audio.sfx('beep'); this.announceText(String(n), '', PAL.mustardLight, 0.9); }
      }
      if (this.phaseT >= 2.7) {
        this.audio.sfx('go'); this.audio.sfx('whistle', { dur: 0.55 }); this.announceText('GO !', '', PAL.green, 1.0); this.fx.doFlash(0.5, '#fff6d0'); this.fx.shake(0.4);
        this.setPhase('kickoff'); this.kickoffT = 0; this.launcherArmed = false; this.music.setIntensity(0.5);
      }
    } else if (ph === 'kickoff') {
      this.kickoffT = this.phaseT;
      const b = this.ball;
      if (this.phaseT < 0.1) { b.state = 'launcher'; b.x = W / 2; b.y = CY; b.z = -50; b.vx = b.vy = b.vz = 0; b.holder = null; }
      if (!this.launcherArmed && this.phaseT > 0.05) { this.launcherArmed = true; this.audio.sfx('launcher-charge'); this.fx.ring(W / 2, CY, 0, PAL.mustard, 110, 0.9, 7); }
      if (this.phaseT > 0.4 && this.phaseT < 1.2 && Math.random() < 0.25) this.fx.smoke(W / 2, CY, 6, 1, 20, 'rgba(240,235,224,0.5)', 90);
      if (this.phaseT >= 1.2) this.launchBall();
    } else if (ph === 'play' || ph === 'overtime') {
      if (!this.overtime) {
        this.clock -= dt;
        if (this.clock <= 10 && Math.ceil(this.clock) !== this.lastTick) { this.lastTick = Math.ceil(this.clock); if (this.lastTick > 0 && this.lastTick <= 5) this.audio.sfx('ui-tick'); }
        if (this.clock <= 20 && !this.lastMinuteFlag) { this.lastMinuteFlag = true; this.music.setTempo(1.05); this.music.setIntensity(0.9); }
        if (this.clock <= 0) { this.clock = 0; this.endHalf(); }
      } else if (this.phaseT > 75) {
        this.endHalf(true);
      }
    } else if (ph === 'goal') {
      // ralenti, puis retour aux positions
      if (this.phaseT < 1.1) this.targetScale = 0.28; else if (this.phaseT < 1.5) this.targetScale = 0.6; else this.targetScale = 1;
      if (this.phaseT > 1.9 && !this._retFlag) { this._retFlag = true; for (const p of this.players) { p.returnHome = true; p.celebrate = 0; p.sad = 0; } }
      if (this.phaseT > 3.9) {
        for (const p of this.players) { const h = this.homeFor(p); p.x = h.x; p.y = h.y; p.vx = p.vy = 0; p.returnHome = false; p.stun = 0; }
        this._retFlag = false; this.targetScale = 1;
        if (this.overtime) { this.finishMatch(); return; }
        this.setPhase('kickoff'); this.launcherArmed = false;
        const b = this.ball; b.state = 'launcher'; b.holder = null; b.x = W / 2; b.y = CY; b.z = -50; b.vx = b.vy = b.vz = 0; b.trail.length = 0;
      }
    } else if (ph === 'endhalf') {
      this.targetScale = 1;
      if (this.phaseT > 3.0) {
        if (this.half === 1) this.startHalftime(); else this.afterSecondHalf();
      }
    } else if (ph === 'halftime') {
      if (this.phaseT > 4.2) { this.startSecondHalf(); }
    } else if (ph === 'fulltime') {
      if (this.phaseT > 4.5) this.finishMatch();
    }
  }

  announceText(text, sub = '', color = PAL.mustardLight, dur = 1.6) { this.announce = { text, sub, color, t: 0, dur }; }

  launchBall() {
    const b = this.ball;
    b.state = 'free'; b.x = W / 2; b.y = CY; b.z = 4; b.vz = 1150 + rand(0, 200);
    b.vx = rand(-380, 380); b.vy = rand(-260, 260); b.holder = null; b.noPickAll = 0.45;
    this.audio.sfx('launch'); this.fx.shake(0.35); this.fx.ring(W / 2, CY, 0, PAL.cream, 200, 0.5, 9);
    this.fx.smoke(W / 2, CY, 10, 8, 34, 'rgba(240,235,224,0.7)', 200);
    this.fx.sparks(W / 2, CY, 20, 26, PAL.mustardLight, 700, TAU);
    this.fx.glow(W / 2, CY, 20, 'rgba(255,220,120,0.9)', 220, 0.5);
    this.setPhase(this.overtime ? 'overtime' : 'play');
  }

  endHalf(draw = false) {
    this.setPhase('endhalf');
    this.audio.sfx('buzzer'); this.audio.sfx('whistle', { dur: 0.9 }); this.audio.swell(0.5, 2.5);
    this.announceText(this.half === 1 ? 'FIN DE PÉRIODE' : (draw ? 'MATCH NUL' : 'FIN DU MATCH'), '', PAL.mustardLight, 2.6);
    this.fx.doFlash(0.4, '#fff');
    if (this.ball.holder) this.dropBall(this.ball.holder);
    this.music.setTempo(1);
  }

  startHalftime() {
    this.setPhase('halftime');
    this.music.stop(0.8); this.music.jingle('halftime');
    this.announceText('MI-TEMPS', `${this.teams[0].score} - ${this.teams[1].score}`, PAL.cream, 4);
    for (const p of this.players) { p.hasBall = false; }
    this.ball.holder = null;
  }

  startSecondHalf() {
    this.half = 2; this.clock = this.halfLen; this.lastMinuteFlag = false;
    // changement de côtés
    for (const t of this.teams) t.attackDir *= -1;
    for (const p of this.players) { const h = this.homeFor(p); p.x = h.x; p.y = h.y; p.vx = p.vy = 0; p.fx = this.teams[p.team].attackDir; p.flip = p.fx < 0; p.stun = 0; p.slideT = 0; p.hasBall = false; p.returnHome = false; }
    for (const pd of this.pads) pd.owner = -1;
    for (const t of this.teams) t.mult = 1;
    this.tokens.length = 0;
    const b = this.ball; b.holder = null; b.state = 'launcher'; b.x = W / 2; b.y = CY; b.trail.length = 0;
    this.sidesSwapped = true;
    this.onSwap && this.onSwap();
    this.setPhase('countdown'); this.count = 4;
    this.music.play('match2'); this.music.setIntensity(0.4);
  }

  afterSecondHalf() {
    const a = this.teams[0].score, b = this.teams[1].score;
    if (a === b) {
      // mort subite
      this.overtime = true; this.clock = 0;
      this.announceText('MORT SUBITE !', 'Le prochain point gagne', PAL.salmonLight, 2.6);
      this.audio.sfx('go'); this.fx.doFlash(0.5, '#ffcc88');
      this.setPhase('kickoff'); this.launcherArmed = false;
      const bl = this.ball; bl.state = 'launcher'; bl.holder = null; bl.x = W / 2; bl.y = CY; bl.z = -50; bl.trail.length = 0;
      for (const p of this.players) { const h = this.homeFor(p); p.x = h.x; p.y = h.y; p.vx = p.vy = 0; p.stun = 0; p.hasBall = false; }
      this.music.setIntensity(1);
    } else this.finishGame();
  }

  finishGame() {
    this.setPhase('fulltime');
    const a = this.teams[0].score, b = this.teams[1].score;
    this.winner = a > b ? 0 : b > a ? 1 : -1;
    this.music.stop(0.6);
    for (const p of this.players) { p.celebrate = 0; p.sad = 0; if (this.winner >= 0) { if (p.team === this.winner) p.celebrate = 1; else p.sad = 1; } }
    this.audio.sfx('whistle', { dur: 0.9 });
    if (this.winner >= 0) { this.audio.swell(0.8, 3); this.fx.confetti(this.ball.x, this.ball.y, 80, [PAL.salmon, PAL.mustard, PAL.pink, PAL.sage, PAL.cream], 700, 120); }
  }

  finishMatch() {
    if (this.phase !== 'fulltime') { this.winner = this.teams[0].score > this.teams[1].score ? 0 : this.teams[1].score > this.teams[0].score ? 1 : -1; }
    this.result = {
      scores: [this.teams[0].score, this.teams[1].score], goals: [this.teams[0].goals, this.teams[1].goals],
      stats: [this.teams[0].stats, this.teams[1].stats], winner: this.winner, defs: this.defs, coins: [this.teams[0].coins, this.teams[1].coins],
    };
    this.onEnd(this.result);
  }

  // ------------------------------------------------------------------ contrôle
  updateControl(t, dt) {
    if (t.human < 0) return;
    const b = this.ball, field = t.players.filter((p) => p.role !== 'GK');
    const pe = this.pending[t.human];
    let cur = t.ctrl;
    if (b.holder && b.holder.team === t.i && b.holder.role !== 'GK') cur = b.holder;
    else if (t.pendingSwitchT > 0 && t.pendingSwitch) { t.pendingSwitchT -= dt; cur = t.pendingSwitch; }
    else {
      const tx = b.holder ? b.holder.x : b.x + b.vx * 0.15, ty = b.holder ? b.holder.y : b.y + b.vy * 0.15;
      let best = null, bd = 1e9;
      for (const p of field) { const d = dist(p.x, p.y, tx, ty) + (p.stun > 0 ? 500 : 0); if (d < bd) { bd = d; best = p; } }
      if (!cur || cur.stun > 0 || (best !== cur && dist(cur.x, cur.y, tx, ty) > bd + 70)) cur = best;
      if (pe.swPressed) {
        let bb = null, dd = 1e9;
        for (const p of field) { if (p === cur) continue; const d = dist(p.x, p.y, tx, ty); if (d < dd) { dd = d; bb = p; } }
        if (bb) cur = bb;
      }
    }
    if (cur !== t.ctrl) {
      if (t.ctrl) { this.stopCharge(t.ctrl); t.ctrl.input.a = false; t.ctrl.chargeT = 0; }
      t.ctrl = cur;
      this.fx.ring(cur.x, cur.y, 0, t.def.light, 70, 0.35, 5);
      this.audio.sfx('ui-tick');
    }
  }

  fillHumanInput(p, slot, canPlay) {
    const sl = this.inputDev.slots[slot], pe = this.pending[slot], i = p.input;
    if (!canPlay) { this.idleInput(p); return; }
    i.mx = sl.mx; i.my = sl.my; i.a = sl.a; i.turbo = sl.turbo;
    i.aPressed = pe.aPressed; i.aReleased = pe.aReleased; i.bPressed = pe.bPressed;
  }

  computeChasers() {
    const b = this.ball;
    for (const t of this.teams) {
      const tx = b.holder ? b.holder.x : b.x + b.vx * 0.2, ty = b.holder ? b.holder.y : b.y + b.vy * 0.2;
      const list = t.players.filter((p) => p.role !== 'GK' && p.stun <= 0 && !(t.human >= 0 && t.ctrl === p) && !p.returnHome)
        .map((p) => ({ p, d: dist(p.x, p.y, tx, ty) })).sort((a, c) => a.d - c.d);
      t.chasers = list.map((e) => e.p);
    }
  }

  // ------------------------------------------------------------------ joueurs
  updatePlayer(p, dt, canPlay) {
    const t = this.teams[p.team], inp = p.input, ball = this.ball, D = this.diff(p.team);
    const frozen = t.freeze > 0;
    p.noPickT = Math.max(0, p.noPickT - dt); p.slideCd = Math.max(0, p.slideCd - dt); p.hitCd = Math.max(0, p.hitCd - dt);
    p.speedT = Math.max(0, p.speedT - dt); p.powerT = Math.max(0, p.powerT - dt);
    p.blinkT -= dt; if (p.blinkT < 0) { p.blink = 0.12; p.blinkT = rand(1.8, 4.5); } p.blink = Math.max(0, p.blink - dt);
    // ressort de squash
    p.sqv += (-p.sq * 260 - p.sqv * 16) * dt; p.sq += p.sqv * dt;

    this.airborne(p, dt);
    const isHumanCtrl = t.human >= 0 && t.ctrl === p;
    const base = p.role === 'GK' ? D.keeper : ((p.role === 'FWD' ? 330 : 312) * (isHumanCtrl ? 1.04 : D.speed)) ;
    let maxSp = base;

    // ----- états bloquants
    if (p.stun > 0) {
      p.stun -= dt; p.vx *= Math.exp(-5 * dt); p.vy *= Math.exp(-5 * dt);
      if (p.hasBall) this.dropBall(p);
      this.moveBody(p, dt);
      return;
    }
    if (frozen) { p.vx *= Math.exp(-8 * dt); p.vy *= Math.exp(-8 * dt); this.moveBody(p, dt); return; }
    if (p.celebrate || p.sad) {
      p.vx *= Math.exp(-4 * dt); p.vy *= Math.exp(-4 * dt);
      if (p.celebrate && p.z <= 0 && Math.random() < dt * 1.4) { p.vz = 500; }
      this.moveBody(p, dt); return;
    }
    // ----- tacle glissé
    if (p.slideT > 0) {
      p.slideT -= dt;
      const k = Math.max(0, p.slideT / 0.34), sp = 220 + 700 * k * k;
      p.vx = p.slideDx * sp; p.vy = p.slideDy * sp;
      p.lastSlideFx -= dt;
      if (p.lastSlideFx <= 0) { p.lastSlideFx = 0.03; this.fx.dust(p.x - p.slideDx * 14, p.y + 6, 1, 16, 'rgba(232,224,204,0.7)', 60); }
      if (Math.random() < 0.5) this.fx.scuff(p.x, p.y + 4, -p.slideDx * 0.4, -p.slideDy * 0.4, 20);
      this.slideHits(p);
      this.moveBody(p, dt);
      if (p.slideT <= 0) { p.slideCd = 0.55; p.slideRecover = 0.18; }
      return;
    }
    if (p.slideRecover > 0) { p.slideRecover -= dt; p.vx *= Math.exp(-14 * dt); p.vy *= Math.exp(-14 * dt); this.moveBody(p, dt); return; }

    // ----- saut (attrape les balles hautes)
    if (inp.bPressed && p.z <= 0.01) {
      if (p.hasBall) this.doThrow(p, { lob: true, aim: inp.throw?.aim, power: 0.6 }, true);
      else { p.vz = p.role === 'GK' ? 760 : 680; p.jumpT = 0.6; this.audio.sfx('jump', { pan: this.panOf(p.x) }); p.sqv += -3.2; this.fx.dust(p.x, p.y, 4, 14); }
    }
    // ----- tacle
    if (inp.aPressed && !p.hasBall && p.slideCd <= 0 && p.z <= 0.01 && p.role !== 'GK') {
      const m = Math.hypot(inp.mx, inp.my);
      let dx = m > 0.2 ? inp.mx / m : p.fx, dy = m > 0.2 ? inp.my / m : p.fy;
      const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
      p.slideT = 0.34; p.slideDx = dx; p.slideDy = dy; p.fx = dx; p.fy = dy; if (Math.abs(dx) > 0.15) p.flip = dx < 0;
      this.audio.sfx('slide', { pan: this.panOf(p.x) });
      this.fx.dust(p.x, p.y, 5, 18);
      return;
    }
    // ----- lancer
    if (p.hasBall) {
      if (inp.a) {
        if (p.chargeT === 0 && !p.chargeSnd) p.chargeSnd = this.audio.startCharge();
        p.chargeT += dt; if (p.chargeSnd) p.chargeSnd.set(Math.min(1, p.chargeT / 0.7));
        maxSp *= 0.6;
      }
      if (inp.throw) { this.doThrow(p, inp.throw, false); }
      else if (inp.aReleased) { this.doThrow(p, { lob: false, aim: null, power: null }, true); }
    } else if (p.chargeT > 0) { this.stopCharge(p); p.chargeT = 0; }

    // ----- déplacement
    let mx = inp.mx, my = inp.my; const mag = Math.hypot(mx, my);
    if (mag > 1) { mx /= mag; my /= mag; }
    p.moveMag = Math.min(1, mag);
    // turbo / endurance
    const wantTurbo = inp.turbo && mag > 0.3 && p.role !== 'GK';
    if (p.stamina <= 0.02) p.turboLock = true; if (p.stamina > 0.3) p.turboLock = false;
    const turbo = wantTurbo && !p.turboLock && p.stamina > 0;
    if (turbo) {
      p.stamina = Math.max(0, p.stamina - dt * 0.42);
      if (!p.turboOn) { this.audio.sfx('turbo', { pan: this.panOf(p.x), vol: 0.8 }); this.fx.dust(p.x, p.y, 5, 16); }
      maxSp *= 1.42;
    } else p.stamina = Math.min(1, p.stamina + dt * (mag > 0.1 ? 0.16 : 0.32));
    p.turboOn = turbo;
    if (p.speedT > 0) maxSp *= 1.28;
    if (p.hasBall) maxSp *= 0.94;
    const accel = turbo ? 8 : 12;
    const k = 1 - Math.exp(-accel * dt);
    p.vx += (mx * maxSp - p.vx) * k; p.vy += (my * maxSp - p.vy) * k;
    const sp = Math.hypot(p.vx, p.vy);
    // orientation
    if (mag > 0.25 || (p.hasBall && sp > 40)) {
      const tx = mag > 0.25 ? mx : p.vx / sp, ty = mag > 0.25 ? my : p.vy / sp;
      const rate = p.hasBall ? 14 : 18;
      p.fx += (tx - p.fx) * (1 - Math.exp(-rate * dt)); p.fy += (ty - p.fy) * (1 - Math.exp(-rate * dt));
      const l = Math.hypot(p.fx, p.fy) || 1; p.fx /= l; p.fy /= l;
      if (Math.abs(p.fx) > 0.28) p.flip = p.fx < 0;
    }
    // animation de course
    p.runPhase += sp * dt * 0.052 * (turbo ? 0.9 : 1);
    if (sp > 90 && p.z <= 0.01) {
      p.stepT -= dt;
      if (p.stepT <= 0) { p.stepT = turbo ? 0.16 : 0.24; if (p.role !== 'GK') this.audio.sfx('step', { pan: this.panOf(p.x), id: p.id % 3 }); else this.audio.sfx('step', { pan: this.panOf(p.x), vol: 1.6 }); if (turbo || sp > 260) this.fx.dust(p.x - p.fx * 10, p.y + 2, 1, 10, 'rgba(232,224,204,0.5)', 30); }
    }
    if (turbo) {
      p.boostFx -= dt;
      if (p.boostFx <= 0) { p.boostFx = 0.05; this.fx.ghost(this.makeGhost(p), 0.25); if (Math.random() < 0.5) this.fx.speedLine(p.x - p.fx * 30, p.y - 30 - Math.random() * 40, 0, -p.fx, -p.fy * 0.2, 'rgba(255,255,255,0.45)', 60); }
    }
    this.moveBody(p, dt);
  }

  makeGhost(p) {
    const team = this.teams[p.team];
    const x = p.x, y = p.y, z = p.z, flip = p.flip, col = team.def.light;
    return (ctx, a) => {
      ctx.save(); ctx.translate(x, y - z); ctx.scale(flip ? -1 : 1, 1);
      ctx.fillStyle = col; ctx.beginPath(); ctx.ellipse(0, -50, 22, 46, 0, 0, TAU); ctx.fill(); ctx.restore();
    };
  }

  airborne(p, dt) {
    if (p.z > 0 || p.vz !== 0) {
      p.vz -= 2100 * dt; p.z += p.vz * dt;
      if (p.z <= 0) {
        if (p.vz < -260) { this.audio.sfx('land', { pan: this.panOf(p.x) }); this.fx.dust(p.x, p.y, 5, 16); p.sqv += 3; }
        p.z = 0; p.vz = 0;
      }
    }
  }

  moveBody(p, dt) {
    p.x += p.vx * dt; p.y += p.vy * dt;
    const r = p.r;
    if (p.role === 'GK') {
      const t = this.teams[p.team], left = t.attackDir > 0;
      const gx = left ? 0 : W;
      const minX = left ? 36 : W - 260, maxX = left ? 260 : W - 36;
      p.x = clamp(p.x, minX, maxX); p.y = clamp(p.y, CY - 200, CY + 200);
    } else {
      p.x = clamp(p.x, r, W - r); p.y = clamp(p.y, r + 8, H - r - 2);
    }
    // bumpers solides
    for (let i = 0; i < BUMPERS.length; i++) {
      const b = BUMPERS[i], dx = p.x - b.x, dy = p.y - b.y, d = Math.hypot(dx, dy), min = b.r + p.r * 0.7;
      if (d < min && d > 0.01) { p.x = b.x + dx / d * min; p.y = b.y + dy / d * min; const vn = p.vx * dx / d + p.vy * dy / d; if (vn < 0) { p.vx -= vn * dx / d * 1.3; p.vy -= vn * dy / d * 1.3; } }
    }
  }

  slideHits(p) {
    const b = this.ball;
    // pousse la balle libre
    if (b.state === 'free' && !b.holder && b.z < 45 && dist(p.x, p.y, b.x, b.y) < p.r + b.r + 20 && p.noPickT <= 0) {
      b.vx = p.slideDx * 950; b.vy = p.slideDy * 950; b.vz = 120; b.last = p; b.lastTeam = p.team; b.noPickAll = 0.05;
      this.audio.sfx('deflect', { pan: this.panOf(b.x) }); this.fx.sparks(b.x, b.y, 10, 8, PAL.cream, 400, 2.4, Math.atan2(p.slideDy, p.slideDx));
      p.noPickT = 0.3;
    }
    for (const o of this.players) {
      if (o.team === p.team || o.stun > 0 || o.z > 30 || o.role === 'GK' && false) continue;
      const dx = o.x - p.x, dy = o.y - p.y, d = Math.hypot(dx, dy);
      if (d < p.r + o.r + 12 && (dx * p.slideDx + dy * p.slideDy) > -8) {
        if (p.hitDone === o.id && p.slideT > 0.05) continue;
        p.hitDone = o.id;
        this.tackleHit(p, o, 1);
      }
    }
  }

  tackleHit(a, o, power) {
    const ta = this.teams[a.team];
    const dur = (a.powerT > 0 ? 1.9 : 1.35) * (o.role === 'GK' ? 0.6 : 1);
    o.stun = dur; o.vx = a.slideDx * 380 * power; o.vy = a.slideDy * 380 * power; o.vz = 240;
    const had = o.hasBall;
    if (had) this.dropBall(o, a.slideDx * 260, a.slideDy * 260, 380);
    ta.stats.tackles++; ta.stats.hits++;
    const mx = (a.x + o.x) / 2, my = (a.y + o.y) / 2;
    this.audio.sfx('hit', { pan: this.panOf(mx), power: had ? 1 : 0.7 });
    this.audio.sfx('stun', { pan: this.panOf(mx) });
    this.fx.stop(had ? 0.09 : 0.06); this.fx.shake(had ? 0.6 : 0.4);
    this.fx.sparks(mx, my, 40, 16, PAL.mustardLight, 620);
    this.fx.shard(mx, my, 40, PAL.steel, 5, 380);
    this.fx.ring(mx, my, 40, '#fff', 110, 0.35, 7, false);
    this.fx.glow(mx, my, 40, 'rgba(255,240,180,0.9)', 130, 0.25);
    for (let i = 0; i < 4; i++) this.fx.star(o.x, o.y, 60, PAL.mustardLight, 13);
    this.fx.text(pick(['BAM!', 'CRASH!', 'WHAM!', 'BONK!', 'SMACK!']), mx, my, { size: 58, color: had ? PAL.salmonLight : PAL.mustardLight, z: 70, rise: 90, life: 0.9 });
    o.sqv -= 6; o.hurtT = 0.3;
    this.excite = Math.min(1, this.excite + 0.15); this.audio.swell(0.25, 1);
    this.cam.kx += a.slideDx * 26; this.cam.ky += a.slideDy * 20;
  }

  // ------------------------------------------------------------------ lancer de balle
  stopCharge(p) { if (p.chargeSnd) { p.chargeSnd.stop(); p.chargeSnd = null; } }

  doThrow(p, cmd, human) {
    const b = this.ball, t = this.teams[p.team];
    if (!p.hasBall || b.holder !== p) return;
    const inp = p.input;
    let power = cmd.power ?? Math.min(1, p.chargeT / 0.7);
    const tapped = p.chargeT < 0.18 && cmd.power == null;
    let lob = !!cmd.lob;
    let ax = p.fx, ay = p.fy;
    const m = Math.hypot(inp.mx, inp.my);
    if (cmd.aim) { ax = cmd.aim.x; ay = cmd.aim.y; }
    else if (m > 0.3) { ax = inp.mx / m; ay = inp.my / m; }
    let target = null;
    if (human && !cmd.aim) {
      // aide à la visée : passe sur un coéquipier ou tir cadré
      const goalX = t.attackDir > 0 ? W : 0;
      const ang0 = Math.atan2(ay, ax);
      if (tapped || lob) {
        let best = null, bs = 1e9;
        for (const q of t.players) {
          if (q === p || q.role === 'GK' || q.stun > 0) continue;
          const dx = q.x + q.vx * 0.3 - p.x, dy = q.y + q.vy * 0.3 - p.y, d = Math.hypot(dx, dy);
          if (d < 120 || d > 1100) continue;
          let da = Math.abs(Math.atan2(dy, dx) - ang0); if (da > Math.PI) da = TAU - da;
          if (da > 0.5) continue;
          const s = da * 400 + d * 0.15; if (s < bs) { bs = s; best = q; }
        }
        if (best) {
          target = best; const dx = best.x + best.vx * 0.35 - p.x, dy = best.y + best.vy * 0.35 - p.y, d = Math.hypot(dx, dy);
          ax = dx / d; ay = dy / d;
          if (lob) power = clamp((d / 0.8) / 1100, 0.2, 1); else power = clamp((d * 1.5 + 380 - 650) / 800, 0.05, 1);
        } else if (!lob && tapped) power = 0.28;
      } else {
        // tir chargé : accroche vers la cage si l'angle est proche
        const dx = goalX - p.x, gy = clamp(p.y, CY - 50, CY + 50), dy = gy - p.y;
        let da = Math.abs(Math.atan2(dy, dx) - ang0); if (da > Math.PI) da = TAU - da;
        if (da < 0.34 && (goalX - p.x) * t.attackDir > 0) { const d = Math.hypot(dx, dy); ax = dx / d; ay = dy / d; }
      }
    }
    const l = Math.hypot(ax, ay) || 1; ax /= l; ay /= l;
    let speed, vz;
    const boost = p.powerT > 0 ? 1.28 : 1;
    if (lob) { speed = lerp(520, 1150, power) * (cmd.aim && cmd.speed ? 1 : 1); if (cmd.speed) speed = cmd.speed; vz = 760; }
    else { speed = lerp(680, 1420, power) * boost; vz = 90 + power * 60; }
    speed = Math.min(speed, MAX_BALL);
    b.holder = null; p.hasBall = false; b.last = p; b.lastTeam = p.team; b.thrower = p; b.thrownT = 0;
    b.x = p.x + ax * (p.r + b.r + 2); b.y = p.y + ay * (p.r + b.r + 2) * 0.9; b.z = 34; b.vx = ax * speed + p.vx * 0.25; b.vy = ay * speed + p.vy * 0.25; b.vz = vz;
    p.noPickT = 0.4; p.chargeT = 0; this.stopCharge(p);
    p.sqv += -5; p.kick = 0.2;
    t.pendingSwitch = target; t.pendingSwitchT = target ? 1.2 : 0;
    const pw = clamp(speed / 1500, 0, 1);
    this.audio.sfx(lob ? 'lob' : 'throw', { pan: this.panOf(p.x), power: pw });
    this.fx.sparks(b.x, b.y, 34, lob ? 6 : 10 + pw * 12, PAL.cream, 350 + pw * 350, 1.4, Math.atan2(ay, ax));
    this.fx.ring(b.x, b.y, 30, t.def.light, 60 + pw * 60, 0.3, 5, false);
    if (!lob && pw > 0.55) { this.fx.shake(0.12 + pw * 0.2); this.cam.kx -= ax * 20 * pw; this.cam.ky -= ay * 14 * pw; for (let i = 0; i < 4; i++) this.fx.speedLine(b.x - ax * 20, b.y - 20 + (Math.random() - 0.5) * 50, 0, ax, ay, 'rgba(255,255,255,0.6)', 120); }
    // statistiques : tir vers la cage adverse
    const goalX = t.attackDir > 0 ? W : 0;
    if (!lob && (goalX - p.x) * ax > 0 && Math.abs(goalX - p.x) < 900 && pw > 0.45) { t.stats.shots++; b.shotBy = p.team; }
    else b.shotBy = -1;
  }

  dropBall(p, ix = 0, iy = 0, iz = 260) {
    const b = this.ball;
    if (b.holder !== p) { p.hasBall = false; return; }
    b.holder = null; p.hasBall = false; this.stopCharge(p); p.chargeT = 0;
    b.vx = p.vx * 0.5 + ix + rand(-90, 90); b.vy = p.vy * 0.5 + iy + rand(-90, 90); b.vz = iz; b.z = Math.max(b.z, 30);
    p.noPickT = 0.8; b.shotBy = -1;
  }

  // ------------------------------------------------------------------ collisions joueurs
  collidePlayers(dt) {
    const P = this.players;
    for (let i = 0; i < P.length; i++) for (let j = i + 1; j < P.length; j++) {
      const a = P[i], c = P[j];
      if (Math.abs(a.z - c.z) > 60) continue;
      const dx = c.x - a.x, dy = c.y - a.y, d2 = dx * dx + dy * dy, min = (a.r + c.r) * 0.86;
      if (d2 >= min * min || d2 < 0.0001) continue;
      const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, pen = min - d;
      const ma = a.role === 'GK' ? 3 : 1, mc = c.role === 'GK' ? 3 : 1, tot = ma + mc;
      if (a.slideT <= 0 && a.stun <= 0) { a.x -= nx * pen * (mc / tot); a.y -= ny * pen * (mc / tot); } else { a.x -= nx * pen * 0.2; a.y -= ny * pen * 0.2; }
      if (c.slideT <= 0 && c.stun <= 0) { c.x += nx * pen * (ma / tot); c.y += ny * pen * (ma / tot); } else { c.x += nx * pen * 0.2; c.y += ny * pen * 0.2; }
      // charge d'épaule
      if (a.team !== c.team) {
        const rel = (c.vx - a.vx) * -nx + (c.vy - a.vy) * -ny; // vitesse de rapprochement
        this.shoulder(a, c, nx, ny, rel);
        this.shoulder(c, a, -nx, -ny, rel);
      }
    }
  }

  shoulder(a, c, nx, ny, rel) {
    if (a.hitCd > 0 || c.stun > 0 || a.stun > 0 || a.slideT > 0 || a.role === 'GK') return;
    const va = a.vx * nx + a.vy * ny;      // vitesse de a vers c
    if (!a.turboOn || va < 380) return;
    if (c.role === 'GK' && Math.random() < 0.5) return;
    a.hitCd = 0.6;
    c.stun = a.powerT > 0 ? 1.1 : 0.75; c.vx = nx * 460; c.vy = ny * 460; c.vz = 200;
    const had = c.hasBall; if (had) this.dropBall(c, nx * 300, ny * 300, 340);
    const ta = this.teams[a.team]; ta.stats.hits++;
    const mx = (a.x + c.x) / 2, my = (a.y + c.y) / 2;
    this.audio.sfx('hit', { pan: this.panOf(mx), power: 0.5 });
    this.fx.stop(0.05); this.fx.shake(0.32); this.fx.sparks(mx, my, 40, 12, PAL.cream, 480);
    this.fx.ring(mx, my, 40, '#fff', 90, 0.3, 6, false);
    this.fx.text(pick(['BUMP!', 'OOF!', 'TCHAK!']), mx, my, { size: 46, color: PAL.cream, z: 80, life: 0.7 });
    for (let i = 0; i < 3; i++) this.fx.star(c.x, c.y, 60, PAL.mustardLight, 11);
    c.sqv -= 4; a.sqv += 2;
  }

  // ------------------------------------------------------------------ balle
  panOf(x) { return clamp((x - this.cam.x) * this.cam.zoom / (VIEW_W / 2), -1, 1) * 0.75; }

  updateBall(dt) {
    const b = this.ball;
    if (b.state === 'launcher') return;
    b.noPickAll = Math.max(0, b.noPickAll - dt); b.portalCd = Math.max(0, b.portalCd - dt); b.bounceCd = Math.max(0, b.bounceCd - dt);
    b.thrownT += dt;
    if (b.holder) {
      const p = b.holder;
      if (p.stun > 0 || p.celebrate) { this.dropBall(p); return; }
      const bob = Math.abs(Math.sin(p.runPhase)) * 6 * Math.min(1, Math.hypot(p.vx, p.vy) / 250);
      b.x = p.x + p.fx * (p.r + 6); b.y = p.y + p.fy * (p.r + 6) * 0.8 + 2; b.z = 30 + bob - (p.chargeT > 0 ? 6 : 0);
      b.vx = p.vx; b.vy = p.vy; b.vz = 0; b.rot += Math.hypot(p.vx, p.vy) * dt * 0.05;
      b.heat = Math.max(0, b.heat - dt);
      if (p.chargeT > 0.15) { const k = Math.min(1, p.chargeT / 0.7); if (Math.random() < 0.3 + k * 0.5) this.fx.sparks(b.x, b.y, b.z, 1 + (k > 0.7 ? 1 : 0), k > 0.85 ? '#ffe36a' : PAL.cream, 200 + k * 200); }
      return;
    }
    // ----- physique libre
    b.vz -= GRAVITY * dt;
    b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
    const sp = Math.hypot(b.vx, b.vy);
    if (b.z <= 0) {
      b.z = 0;
      if (b.vz < -200) {
        const rest = 0.52; b.vz = -b.vz * rest; b.vx *= 0.93; b.vy *= 0.93;
        if (b.bounceCd <= 0) { this.audio.sfx('bounce', { pan: this.panOf(b.x), power: Math.min(1, -b.vz / 700) }); b.bounceCd = 0.06; }
        this.fx.ring(b.x, b.y, 0, 'rgba(255,255,255,0.7)', 26 + Math.min(40, Math.abs(b.vz) * 0.06), 0.28, 3);
        this.fx.dust(b.x, b.y, 3, 10, 'rgba(232,224,204,0.55)', 60);
      } else b.vz = 0;
      // frottement au sol
      const drag = Math.exp(-0.75 * dt);
      b.vx *= drag; b.vy *= drag;
      const s2 = Math.hypot(b.vx, b.vy);
      if (s2 > 0 && s2 < 60) { const k = Math.max(0, s2 - 70 * dt) / s2; b.vx *= k; b.vy *= k; }
    } else { const d = Math.exp(-0.12 * dt); b.vx *= d; b.vy *= d; }
    const s3 = Math.hypot(b.vx, b.vy);
    if (s3 > MAX_BALL) { b.vx *= MAX_BALL / s3; b.vy *= MAX_BALL / s3; }
    b.rot += s3 * dt * 0.05; b.heat = clamp(s3 / 1600, 0, 1);

    this.ballWalls(b);
    this.ballBumpers(b);
    this.ballPortals(b);
    this.ballPlayers(b);
    if (this.phase === 'play' || this.phase === 'overtime') this.checkGoal(b);

    // effets de vitesse
    if (s3 > 900 && Math.random() < 0.55) this.fx.speedLine(b.x - b.vx * 0.02, b.y - b.z + (Math.random() - 0.5) * 16, 0, -b.vx / s3 * -1, -b.vy / s3 * -1 + 0.0, 'rgba(255,255,255,0.4)', 60 + s3 * 0.03);
    if (s3 > 500 && Math.random() < 0.3) this.fx.sparks(b.x, b.y, b.z, 1, this.teamColorOf(b.lastTeam), 90, TAU);
    if (b.z > 6) { /* ombre gérée au rendu */ }
  }

  teamColorOf(i) { return i < 0 ? PAL.cream : this.teams[i].def.light; }

  wallHit(b, power, x, y, nx, ny, kind = 'wall') {
    if (power < 0.06) return;
    this.audio.sfx(kind, { pan: this.panOf(x), power });
    if (power > 0.25) { this.fx.sparks(x, y, b.z, Math.round(6 + power * 16), PAL.mustardLight, 300 + power * 450, 1.8, Math.atan2(ny, nx)); this.fx.dust(x, y, 2, 10); }
    if (power > 0.55) { this.fx.shake(0.1 + power * 0.18); this.fx.ring(x, y, b.z, '#fff', 60 + power * 40, 0.25, 5, false); }
  }

  ballWalls(b) {
    const r = b.r, e = 0.86;
    // murs haut / bas
    if (b.y < r) {
      b.y = r; const pw = Math.abs(b.vy) / 1400; b.vy = Math.abs(b.vy) * e; b.vx *= 0.99;
      this.wallHit(b, pw, b.x, 0, 0, 1);
      this.padHit(b, 'top');
    } else if (b.y > H - r) {
      b.y = H - r; const pw = Math.abs(b.vy) / 1400; b.vy = -Math.abs(b.vy) * e; b.vx *= 0.99;
      this.wallHit(b, pw, b.x, H, 0, -1);
      this.padHit(b, 'bottom');
    }
    // extrémités et cages
    for (const side of [0, 1]) {
      const gx = side === 0 ? 0 : W, dir = side === 0 ? 1 : -1;   // dir = direction vers l'intérieur
      const inFront = side === 0 ? b.x < r + 8 : b.x > W - r - 8;
      if (!inFront) continue;
      const inMouth = Math.abs(b.y - CY) < GOAL_H / 2;
      // montants
      for (const py of [CY - GOAL_H / 2, CY + GOAL_H / 2]) {
        const dx = b.x - gx, dy = b.y - py, d = Math.hypot(dx, dy), pr = 9;
        if (d < r + pr && b.z < GOAL_TOP && d > 0.01) {
          const nx = dx / d, ny = dy / d, vn = b.vx * nx + b.vy * ny;
          if (vn < 0) {
            b.x = gx + nx * (r + pr); b.y = py + ny * (r + pr);
            b.vx -= (1 + 0.85) * vn * nx; b.vy -= (1 + 0.85) * vn * ny;
            this.audio.sfx('post', { pan: this.panOf(gx) });
            this.fx.sparks(gx, py, 60, 14, '#fff6c0', 520); this.fx.shake(0.32); this.fx.stop(0.05);
            this.fx.ring(gx, py, 60, '#fff', 90, 0.35, 6, false); this.fx.text('CLANG!', gx + dir * 80, py - 40, { size: 46, color: PAL.mustardLight, z: 60 });
            this.goalFlash[side] = 0.3;
          }
        }
      }
      const beyond = side === 0 ? b.x < r : b.x > W - r;
      if (!beyond) continue;
      if (inMouth && b.z < GOAL_TOP - 8) continue; // entre dans la cage
      // mur plein (ou au-dessus de la barre)
      const pw = Math.abs(b.vx) / 1400;
      if (side === 0) { b.x = r; b.vx = Math.abs(b.vx) * e; } else { b.x = W - r; b.vx = -Math.abs(b.vx) * e; }
      this.wallHit(b, pw, gx, b.y, dir, 0);
      if (inMouth && b.z >= GOAL_TOP - 8) { this.audio.sfx('post', { pan: this.panOf(gx) }); this.fx.text('BARRE!', gx + dir * 100, b.y - b.z - 30, { size: 46 }); }
    }
    // filet : fond et côtés
    for (const side of [0, 1]) {
      const inNet = side === 0 ? b.x < 0 : b.x > W;
      if (!inNet) continue;
      const depth = side === 0 ? -b.x : b.x - W;
      const lo = CY - GOAL_H / 2 + r, hi = CY + GOAL_H / 2 - r;
      if (b.y < lo) { b.y = lo; b.vy = Math.abs(b.vy) * 0.3; b.vx *= 0.7; }
      if (b.y > hi) { b.y = hi; b.vy = -Math.abs(b.vy) * 0.3; b.vx *= 0.7; }
      if (depth > GOAL_D - r) {
        if (side === 0) { b.x = -(GOAL_D - r); b.vx = Math.abs(b.vx) * 0.32; } else { b.x = W + GOAL_D - r; b.vx = -Math.abs(b.vx) * 0.32; }
        b.vy *= 0.6; this.audio.sfx('net', { pan: this.panOf(side === 0 ? 0 : W) }); b.vz = Math.max(b.vz, 60);
        this.fx.dust(b.x, b.y, 4, 16, 'rgba(246,239,223,0.6)', 90);
      }
      b.vx *= Math.exp(-2.4 * (1 / 120)); b.vy *= Math.exp(-2.4 * (1 / 120));
      if (b.z > GOAL_TOP - r) { b.z = GOAL_TOP - r; b.vz = -Math.abs(b.vz) * 0.2; }
    }
  }

  padHit(b, wall) {
    if (b.lastTeam < 0) return;
    for (const p of this.pads) {
      if (p.wall !== wall || Math.abs(b.x - p.x) > p.w / 2 + 4) continue;
      if (p.owner === b.lastTeam) { p.flash = 0.6; this.audio.sfx('ui-tick'); return; }
      const t = this.teams[b.lastTeam];
      p.owner = b.lastTeam; p.flash = 1;
      t.stats.pads++; this.addScore(t, 2, p.x, wall === 'top' ? 10 : H - 20, '+2', false);
      this.audio.sfx('pad', { pan: this.panOf(p.x), note: 72 + (this.pads.filter((q) => q.owner === t.i).length % 5) * 2 });
      const y = wall === 'top' ? 8 : H - 8;
      this.fx.ring(p.x, y, 0, t.def.light, 110, 0.5, 8);
      this.fx.sparks(p.x, y, 20, 14, t.def.light, 420, 2.6, wall === 'top' ? Math.PI / 2 : -Math.PI / 2);
      for (let i = 0; i < 3; i++) this.fx.star(p.x, y, 30, t.def.accent, 12);
      // Star Rush : 6 pads sur 8
      const n = this.pads.filter((q) => q.owner === t.i).length;
      if (n >= 6) {
        t.mult = 2;
        for (const q of this.pads) { q.owner = -1; q.flash = 1; }
        this.audio.sfx('star-rush'); this.fx.doFlash(0.5, t.def.light); this.fx.shake(0.5);
        this.announceText('STAR RUSH x2 !', `${t.def.name} : prochain but doublé`, t.def.light, 2.4);
        this.fx.confetti(p.x, y, 40, [t.def.main, t.def.accent, PAL.cream], 560, 60);
      }
      return;
    }
  }

  ballBumpers(b) {
    if (b.z > 70) return;
    for (let i = 0; i < BUMPERS.length; i++) {
      const bm = BUMPERS[i], dx = b.x - bm.x, dy = b.y - bm.y, d = Math.hypot(dx, dy), min = bm.r + b.r;
      if (d < min && d > 0.01) {
        const nx = dx / d, ny = dy / d, vn = b.vx * nx + b.vy * ny;
        b.x = bm.x + nx * min; b.y = bm.y + ny * min;
        if (vn < 0) {
          b.vx -= 2 * vn * nx; b.vy -= 2 * vn * ny;
          const s = Math.hypot(b.vx, b.vy), ns = Math.max(s * 1.05 + 120, 780);
          b.vx = b.vx / s * ns; b.vy = b.vy / s * ns;
          this.bumperPulse[i] = 1;
          this.audio.sfx('bumper', { pan: this.panOf(bm.x) });
          this.fx.sparks(bm.x + nx * bm.r, bm.y + ny * bm.r, 30, 12, '#ffd23f', 520, 1.6, Math.atan2(ny, nx));
          this.fx.ring(bm.x, bm.y, 0, '#ffd23f', 120, 0.4, 8);
          this.fx.shake(0.12); this.fx.glow(bm.x, bm.y, 30, 'rgba(255,200,120,0.8)', 110, 0.25);
          if (b.lastTeam >= 0 && b.bounceCd <= 0) { b.bounceCd = 0.1; this.addScore(this.teams[b.lastTeam], 1, bm.x, bm.y - 50, '+1', false); }
        }
      }
    }
  }

  ballPortals(b) {
    if (b.portalCd > 0 || b.z > 45) return;
    for (let i = 0; i < PORTALS.length; i++) {
      const pt = PORTALS[i];
      if (dist(b.x, b.y, pt.x, pt.y) < pt.r * 0.8) {
        const o = PORTALS[1 - i], s = Math.max(Math.hypot(b.vx, b.vy) * 1.05, 820);
        this.fx.ring(pt.x, pt.y, 0, '#9adcff', 130, 0.5, 8); this.fx.sparks(pt.x, pt.y, 30, 22, '#bfe8ff', 500);
        this.fx.glow(pt.x, pt.y, 30, 'rgba(160,210,255,0.9)', 160, 0.4);
        b.x = o.x; b.y = o.y; b.portalCd = 0.9;
        const ang = (i === 0 ? Math.PI / 2 : -Math.PI / 2) * -1 + (Math.random() - 0.5) * 1.0;
        const dirY = i === 0 ? -1 : 1;   // sort de l'autre portail vers l'intérieur du terrain
        const a = Math.atan2(dirY, (Math.random() - 0.5) * 1.2);
        b.vx = Math.cos(a) * s; b.vy = Math.sin(a) * s;
        this.audio.sfx('warp', { pan: this.panOf(o.x) });
        this.fx.ring(o.x, o.y, 0, '#ffffff', 150, 0.5, 8); this.fx.sparks(o.x, o.y, 30, 22, '#bfe8ff', 560);
        this.fx.glow(o.x, o.y, 30, 'rgba(160,210,255,0.9)', 190, 0.4); this.fx.doFlash(0.12, '#bfe8ff');
        this.portalGlow = 0.8;
        b.trail.length = 0;
        return;
      }
    }
  }

  ballPlayers(b) {
    if (b.noPickAll > 0) return;
    for (const p of this.players) {
      if (p.noPickT > 0 || p.stun > 0 || p.slideT > 0 || p.celebrate || p.sad) continue;
      if (this.teams[p.team].freeze > 0) continue;
      const gk = p.role === 'GK';
      const rr = p.r + b.r + (gk ? 20 : 2);
      const dx = b.x - p.x, dy = b.y - p.y;
      if (dx * dx + dy * dy > rr * rr) continue;
      const reach = gk ? 155 : 108;
      if (b.z < p.z - 12 || b.z > p.z + reach) continue;
      const sp = Math.hypot(b.vx, b.vy), D = this.diff(p.team), t = this.teams[p.team];
      const enemyShot = b.shotBy >= 0 && b.shotBy !== p.team;
      if (gk) {
        const catchable = sp < 1050 || Math.random() < (0.55 + (D.keeper - 250) / 400);
        if (sp > 260 && b.lastTeam !== p.team) { t.stats.saves += enemyShot ? 1 : 0; }
        if (catchable) { this.pickup(p, b, enemyShot && sp > 600); } else this.deflect(p, b, dx, dy, true, enemyShot);
        return;
      }
      if (sp > 1080) { this.deflect(p, b, dx, dy, false, false); return; }
      this.pickup(p, b, false);
      return;
    }
  }

  pickup(p, b, save) {
    b.holder = p; p.hasBall = true; b.last = p; b.lastTeam = p.team; b.vz = 0; b.thrower = null; b.shotBy = -1;
    p.chargeT = 0; p.ai.decideT = 0.15; p.ai.holdT = rand(0.5, 1.1); p.ai.charging = false;
    const t = this.teams[p.team];
    this.audio.sfx(save ? 'save' : 'catch', { pan: this.panOf(p.x) });
    this.fx.sparks(b.x, b.y, b.z, save ? 22 : 8, save ? '#fff6c0' : PAL.cream, save ? 520 : 260);
    this.fx.ring(b.x, b.y, b.z, t.def.light, 60, 0.3, 5, false);
    p.sqv += -4;
    if (save) {
      this.fx.stop(0.07); this.fx.shake(0.35); this.fx.text('ARRÊT!', p.x + (p.flip ? -60 : 60), p.y, { size: 62, color: t.def.light, z: 130, rise: 60, life: 1.1 });
      this.audio.swell(0.3, 1.5); this.fx.doFlash(0.15, '#fff');
    }
    if (t.human >= 0 && p.role !== 'GK') t.pendingSwitchT = 0;
  }

  deflect(p, b, dx, dy, gk, shot) {
    const d = Math.hypot(dx, dy) || 1, nx = dx / d, ny = dy / d;
    const vn = b.vx * nx + b.vy * ny;
    if (vn < 0) { b.vx -= 1.5 * vn * nx; b.vy -= 1.5 * vn * ny; }
    if (gk) { const s = Math.hypot(b.vx, b.vy); const k = Math.min(1, 900 / s); b.vx *= k; b.vy *= k; b.vz = Math.max(b.vz, 250); b.vy += (Math.random() - 0.5) * 300; }
    else { b.vx *= 0.55; b.vy *= 0.55; b.vz = Math.max(b.vz, 160); }
    b.x = p.x + nx * (p.r + b.r + 3); b.y = p.y + ny * (p.r + b.r + 3);
    b.last = p; b.lastTeam = p.team;
    p.noPickT = 0.25; p.sqv -= 4;
    this.audio.sfx(gk ? 'save' : 'deflect', { pan: this.panOf(p.x) });
    this.fx.sparks(b.x, b.y, b.z, 16, PAL.mustardLight, 520, 2.2, Math.atan2(ny, nx));
    this.fx.shake(gk ? 0.3 : 0.15); this.fx.stop(0.04);
    if (gk) { this.fx.text('PARADE!', p.x + (p.flip ? -60 : 60), p.y, { size: 56, color: this.teams[p.team].def.light, z: 130 }); this.teams[p.team].stats.saves++; }
  }

  // ------------------------------------------------------------------ but
  checkGoal(b) {
    let side = -1;
    if (b.x + b.r * 0.4 < 0) side = 0; else if (b.x - b.r * 0.4 > W) side = 1;
    if (side < 0) return;
    if (Math.abs(b.y - CY) > GOAL_H / 2 || b.z > GOAL_TOP - 8) return;
    // l'équipe qui attaque ce côté marque
    const sc = this.teams.find((t) => (side === 0 ? t.attackDir < 0 : t.attackDir > 0));
    const def = this.teams[1 - sc.i];
    const pts = 10 * sc.mult;
    sc.goals++; this.addScore(sc, pts, side === 0 ? 120 : W - 120, CY - 100, `+${pts}`, true);
    sc.mult = 1;
    this.lastGoalSide = side; this.scoredTeam = sc.i;
    this.setPhase('goal'); this._retFlag = false;
    this.goalFlash[side] = 1.5; this.targetScale = 0.28;
    // réactions
    for (const p of this.players) {
      p.input.a = false; this.stopCharge(p); p.chargeT = 0;
      if (p.hasBall) { p.hasBall = false; }
      if (p.team === sc.i) { p.celebrate = 1; p.vz = p.role === 'GK' ? 0 : 420 + Math.random() * 200; } else if (p.stun <= 0) { p.sad = 1; }
    }
    b.holder = null;
    const gx = side === 0 ? 0 : W;
    this.audio.sfx('goal'); this.audio.duckMusic(0.25, 3.2); this.audio.sfx('confetti');
    this.fx.stop(0.16); this.fx.shake(1); this.fx.doFlash(0.8, sc.def.light);
    this.fx.confetti(gx + (side === 0 ? 100 : -100), CY, 90, [sc.def.main, sc.def.accent, PAL.cream, PAL.mustard, sc.def.light], 900, 80);
    this.fx.ring(gx, CY, 30, sc.def.light, 380, 0.9, 16, false); this.fx.ring(gx, CY, 30, '#fff', 260, 0.7, 10, false);
    this.fx.sparks(gx, CY, 60, 60, PAL.mustardLight, 900);
    const ta = `${sc.score}`;
    this.announceText(pts > 10 ? 'BUT DOUBLE !!' : 'BUT !!', `${sc.def.name}  +${pts}`, sc.def.light, 3.3);
    this.music.setIntensity(Math.min(1, 0.6 + Math.abs(this.teams[0].score - this.teams[1].score) < 12 ? 0.85 : 0.6));
    // Crowd flash photographers
    for (let i = 0; i < 8; i++) setTimeout(() => this.audio.sfx('camera', { pan: (Math.random() - 0.5) * 1.5 }), 200 + i * 130);
    this.goalTeam = sc.i;
  }

  addScore(t, pts, x, y, label, big) {
    t.score += pts;
    t.scorePop = 1;
    if (!big) this.fx.text(label, x, y, { size: 36, color: t.def.light, z: 40, rise: 70, life: 0.9 });
  }

  // ------------------------------------------------------------------ jetons
  updateTokens(dt) {
    if (this.phase === 'play' || this.phase === 'overtime') {
      this.tokenTimer -= dt;
      if (this.tokenTimer <= 0 && this.tokens.length < 3) {
        this.tokenTimer = rand(5, 9);
        const r = Math.random(), type = r < 0.5 ? 'coin' : r < 0.7 ? 'speed' : r < 0.85 ? 'power' : 'freeze';
        let x, y, tries = 0;
        do { x = rand(260, W - 260); y = rand(90, H - 90); tries++; } while (tries < 20 && (BUMPERS.some((b) => dist(x, y, b.x, b.y) < 90) || dist(x, y, W / 2, CY) < 110 || PORTALS.some((p) => dist(x, y, p.x, p.y) < 90)));
        this.tokens.push({ type, x, y, t: 0, life: 14 });
        this.fx.ring(x, y, 0, '#fff', 70, 0.5, 5); this.fx.sparks(x, y, 10, 8, PAL.cream, 240);
      }
    }
    for (let i = this.tokens.length - 1; i >= 0; i--) {
      const k = this.tokens[i]; k.t += dt; k.life -= dt;
      if (k.life <= 0) { this.tokens.splice(i, 1); continue; }
      for (const p of this.players) {
        if (p.z > 60 || p.stun > 0 || Math.hypot(p.x - k.x, p.y - k.y) > p.r + 22) continue;
        this.collect(p, k); this.tokens.splice(i, 1); break;
      }
    }
  }

  collect(p, k) {
    const t = this.teams[p.team], o = this.teams[1 - p.team];
    const pan = this.panOf(k.x);
    this.fx.ring(k.x, k.y, 0, '#fff', 90, 0.4, 6); this.fx.sparks(k.x, k.y, 30, 16, '#fff6c0', 420);
    if (k.type === 'coin') { t.coins++; t.stats.coins++; this.audio.sfx('coin', { pan }); this.fx.text('+1 $', k.x, k.y, { size: 34, color: '#ffd23f', z: 50 }); }
    else if (k.type === 'speed') { p.speedT = 8; this.audio.sfx('powerup', { pan }); this.fx.text('TURBO!', k.x, k.y, { size: 44, color: '#63d6c4', z: 70 }); }
    else if (k.type === 'power') { p.powerT = 8; this.audio.sfx('powerup', { pan }); this.fx.text('POWER!', k.x, k.y, { size: 44, color: '#ff7a59', z: 70 }); }
    else if (k.type === 'freeze') {
      o.freeze = 2.6; this.audio.sfx('freeze', { pan }); this.fx.doFlash(0.3, '#bfe8ff'); this.fx.shake(0.3);
      this.fx.text('GEL !', k.x, k.y, { size: 56, color: '#9adcff', z: 80 });
      for (const q of o.players) { this.fx.ring(q.x, q.y, 0, '#9adcff', 100, 0.6, 6); for (let i = 0; i < 4; i++) this.fx.shard(q.x, q.y, 50, '#bfe8ff', 1, 200); }
    }
  }

  // ------------------------------------------------------------------ caméra
  updateCamera(dt) {
    const cam = this.cam, b = this.ball;
    let tx = b.x, ty = b.y;
    const holder = b.holder;
    if (b.state === 'launcher') { tx = W / 2; ty = CY; }
    else if (holder) { tx = holder.x + holder.fx * 120; ty = holder.y; }
    else { tx = b.x + clamp(b.vx * 0.22, -280, 280); ty = b.y; }
    let zoom = 0.87 - clamp(Math.hypot(b.vx, b.vy) / 1600, 0, 1) * 0.04;
    if (this.phase === 'goal') { const s = this.lastGoalSide; tx = b.x; ty = b.y; zoom = 0.98; }
    else if (this.phase === 'intro') { const k = this.phaseT / 2.4; tx = lerp(200, W - 200, k * k * (3 - 2 * k)); ty = CY; zoom = 0.78 + k * 0.08; }
    else if (this.phase === 'halftime' || this.phase === 'fulltime') { tx = W / 2; ty = CY; zoom = 0.74; }
    else if (this.phase === 'kickoff') { tx = lerp(cam.x, W / 2, 0.1); ty = CY; }
    cam.targetZoom = zoom;
    const kx = this.phase === 'goal' ? 3 : 5.5;
    cam.x += (tx - cam.x) * (1 - Math.exp(-kx * dt));
    cam.y += ((CY - 6 + (ty - CY) * 0.16) - cam.y) * (1 - Math.exp(-3 * dt));
    cam.zoom += (cam.targetZoom - cam.zoom) * (1 - Math.exp(-3 * dt));
    cam.kx *= Math.exp(-9 * dt); cam.ky *= Math.exp(-9 * dt);
    const halfW = VIEW_W / 2 / cam.zoom;
    const minX = halfW - 170, maxX = W - halfW + 170;
    cam.x = minX > maxX ? W / 2 : clamp(cam.x, minX, maxX);
  }
}
