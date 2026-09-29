import { PLAYER_R, PLAYER_SPEED, CARRIER_SPEED_MUL, SLIDE_SPEED, SLIDE_TIME, SLIDE_RECOVER, JUMP_VZ, GRAVITY, FIELD_W, FIELD_H, BUMPERS, GOAL_HALF, CY } from './constants.js';
import { clamp, dampAngle, rand } from '../core/math.js';

export class Player {
  constructor(team, idx, slot, name) {
    this.team = team;
    this.idx = idx;
    this.role = slot.role;
    this.slot = slot;
    this.name = name;
    this.number = [1, 4, 5, 8, 9, 11][idx];
    this.x = 0; this.y = 0; this.z = 0;
    this.vx = 0; this.vy = 0; this.vz = 0;
    this.facing = 0;
    this.state = 'run';
    this.stateT = 0;
    this.hasBall = false;
    this.health = 100;
    this.hitFlash = 0;
    this.shockT = 0;
    this.hitImmune = 0;
    this.slideCD = 0;
    this.catchCD = 0;
    this.holdT = 0;
    this.human = null; // human controller object when controlled
    this.intent = { mx: 0, my: 0 };
    this.anim = { phase: rand(0, 6), speed: 0, stateT: 0, charge: 0, diveDir: 1 };
    this.charging = false;
    this.chargeT = 0;
    this.ai = { next: rand(0, 0.2), tx: 0, ty: 0, mode: 'form' };
    // Base attributes — the future progression system will modify these.
    this.stats = {
      speed: slot.role === 'FW' ? 1.04 : slot.role === 'GK' ? 0.9 : 1,
      power: slot.role === 'DF' ? 1.15 : 1,
      catch: slot.role === 'GK' ? 1.3 : 1,
      throw: slot.role === 'FW' ? 1.08 : 1,
    };
  }

  get isGK() { return this.role === 'GK'; }
  get active() { return this.state === 'run' || this.state === 'jump' || this.state === 'throw' || this.state === 'celebrate'; }
  get grounded() { return this.state === 'down' || this.state === 'ko'; }
  get canCatch() {
    return (this.state === 'run' || this.state === 'jump' || this.state === 'dive' || this.state === 'celebrate' || (this.state === 'slide' && this.stateT < SLIDE_TIME)) && this.catchCD <= 0;
  }

  setState(s) {
    this.state = s;
    this.stateT = 0;
  }

  maxSpeed(match) {
    let s = PLAYER_SPEED * this.stats.speed;
    if (this.hasBall) s *= CARRIER_SPEED_MUL;
    const t = this.team;
    if (t.rageT > 0) s *= 1.15;
    if (t.freezeT > 0) s *= 0.55;
    if (!this.human) s *= match.aiSpeed(t);
    return s;
  }

  slide() {
    if (!this.active || this.state === 'jump' || this.hasBall || this.slideCD > 0) return false;
    this.setState('slide');
    const m = Math.hypot(this.intent.mx, this.intent.my);
    if (m > 0.2) this.facing = Math.atan2(this.intent.my, this.intent.mx);
    this.vx = Math.cos(this.facing) * SLIDE_SPEED;
    this.vy = Math.sin(this.facing) * SLIDE_SPEED;
    this.slideCD = SLIDE_TIME + SLIDE_RECOVER + 0.15;
    this.slidHit = false;
    return true;
  }

  jump() {
    if (this.state !== 'run' || this.z > 0) return false;
    this.setState('jump');
    this.vz = JUMP_VZ;
    return true;
  }

  dive(dir) {
    if (this.state !== 'run') return false;
    this.setState('dive');
    this.anim.diveDir = dir;
    // Dive perpendicular to the goal line.
    this.vy = dir * 560;
    this.vx *= 0.3;
    this.vz = 180;
    return true;
  }

  knockDown(vx, vy, time, ko = false) {
    this.setState(ko ? 'ko' : 'down');
    this.downTime = time;
    this.vx = vx; this.vy = vy;
    this.vz = 160;
    this.charging = false;
    this.chargeT = 0;
    if (Math.hypot(vx, vy) > 10) this.facing = Math.atan2(-vy, -vx); // head toward the push direction
  }

  update(dt, match) {
    this.stateT += dt;
    this.hitFlash -= dt;
    this.shockT -= dt;
    this.hitImmune -= dt;
    this.slideCD -= dt;
    this.catchCD -= dt;
    if (this.hasBall) this.holdT += dt; else this.holdT = 0;
    if (this.state !== 'ko') this.health = Math.min(100, this.health + dt * 1.5);

    const st = this.state;
    let control = 0;
    if (st === 'run' || st === 'celebrate') control = 1;
    else if (st === 'jump') control = 0.35;
    else if (st === 'throw') control = 0.5;

    if (control > 0) {
      const ms = this.maxSpeed(match);
      let mx = this.intent.mx, my = this.intent.my;
      const m = Math.hypot(mx, my);
      if (m > 1) { mx /= m; my /= m; }
      const tvx = mx * ms, tvy = my * ms;
      const accel = (this.human ? 14 : 10) * control;
      const k = 1 - Math.exp(-accel * dt);
      this.vx += (tvx - this.vx) * k;
      this.vy += (tvy - this.vy) * k;
      if (this.charging && this.aimX !== undefined) {
        this.facing = dampAngle(this.facing, Math.atan2(this.aimY, this.aimX), 18, dt);
      } else if (m > 0.15 && st !== 'throw') {
        this.facing = dampAngle(this.facing, Math.atan2(my, mx), 16, dt);
      }
    } else {
      // Sliding / tumbling: friction only.
      const fr = st === 'slide' ? (this.stateT < SLIDE_TIME ? 1.1 : 7) : st === 'dive' ? 2.5 : 5;
      const k = Math.exp(-fr * dt);
      this.vx *= k; this.vy *= k;
    }

    this.x += this.vx * dt;
    this.y += this.vy * dt;

    // Vertical
    if (this.z > 0 || this.vz !== 0) {
      this.vz -= GRAVITY * dt;
      this.z += this.vz * dt;
      if (this.z <= 0) {
        this.z = 0;
        const hard = this.vz < -200;
        this.vz = 0;
        if (st === 'jump') { this.setState('run'); match.emit('land', this); }
        else if (hard && (st === 'down' || st === 'ko')) match.emit('thud', this);
      }
    }

    // State timers
    if (st === 'slide' && this.stateT > SLIDE_TIME + SLIDE_RECOVER) this.setState('run');
    else if (st === 'throw' && this.stateT > 0.24) this.setState('run');
    else if (st === 'stun' && this.stateT > (this.stunTime || 0.5)) this.setState('run');
    else if (st === 'dive' && this.stateT > 0.6) { this.setState('down'); this.downTime = 0.35; this.stateT = 0.25; }
    else if (st === 'down' && this.stateT > this.downTime) { this.setState('run'); this.hitImmune = Math.max(this.hitImmune, 0.6); }
    else if (st === 'ko' && this.stateT > this.downTime) { this.setState('run'); this.health = 65; this.hitImmune = 1.5; match.emit('revive', this); }

    this.collideWorld();

    // Animation
    const sp = Math.hypot(this.vx, this.vy);
    this.anim.speed = st === 'run' || st === 'celebrate' ? sp / PLAYER_SPEED : 0;
    this.anim.phase += dt * (5 + 9 * Math.min(1.2, this.anim.speed)) * (this.anim.speed > 0.05 ? 1 : 0);
    this.anim.stateT = this.stateT;
    this.anim.charge = this.charging ? Math.min(1, this.chargeT / 0.45) : 0;
  }

  collideWorld() {
    const r = PLAYER_R;
    let minX = r, maxX = FIELD_W - r;
    // Goalkeepers can step into the mouth line
    if (Math.abs(this.y - CY) < GOAL_HALF - r) { minX = r * 0.6; maxX = FIELD_W - r * 0.6; }
    if (this.x < minX) { this.x = minX; if (this.vx < 0) this.vx *= -0.3; }
    if (this.x > maxX) { this.x = maxX; if (this.vx > 0) this.vx *= -0.3; }
    if (this.y < r) { this.y = r; if (this.vy < 0) this.vy *= -0.3; }
    if (this.y > FIELD_H - r) { this.y = FIELD_H - r; if (this.vy > 0) this.vy *= -0.3; }
    if (this.z < 45) {
      for (const b of BUMPERS) {
        const dx = this.x - b.x, dy = this.y - b.y;
        const d = Math.hypot(dx, dy), min = b.r + r * 0.8;
        if (d < min && d > 0.01) {
          this.x = b.x + (dx / d) * min;
          this.y = b.y + (dy / d) * min;
          const vn = this.vx * (dx / d) + this.vy * (dy / d);
          if (vn < 0) { this.vx -= vn * (dx / d) * 1.3; this.vy -= vn * (dy / d) * 1.3; }
        }
      }
    }
  }
}

export function clampToField(x, y, m = 40) {
  return { x: clamp(x, m, FIELD_W - m), y: clamp(y, m, FIELD_H - m) };
}
