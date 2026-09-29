import { FIELD_W as W, FIELD_H as H, CX, CY } from './constants.js';
import { clamp, damp } from '../core/math.js';
import { arenaBounds } from '../render/arena.js';

export const BASE_VIEW_W = 1200;

export class Camera {
  constructor() {
    this.x = CX; this.y = CY;
    this.zoom = 1;
    this.viewW = BASE_VIEW_W;
    this.viewH = BASE_VIEW_W * 9 / 16;
    this.aspect = 16 / 9;
  }

  snap(match) {
    this.x = CX; this.y = CY;
  }

  update(dt, match, aspect) {
    this.aspect = aspect;
    const b = match.ball;
    let fx = b.x, fy = b.y - b.z * 0.4;
    let zoom = 1;
    let rate = 3.2;
    if (b.owner) {
      const o = b.owner;
      fx = o.x + o.vx * 0.45 + o.team.dir * 110;
      fy = o.y + o.vy * 0.3;
    } else {
      fx += b.vx * 0.2;
      fy += b.vy * 0.15;
      if (b.z > 90) zoom = 0.93;
    }
    // Keep human-controlled players in frame.
    const hs = match.humans.filter((h) => h.player);
    if (hs.length === 1) {
      const p = hs[0].player;
      fx = fx * 0.78 + p.x * 0.22;
      fy = fy * 0.78 + p.y * 0.22;
    } else if (hs.length > 1) {
      zoom = Math.min(zoom, 0.9);
    }
    if (match.phase === 'goal' && match.goalInfo) {
      const g = match.goalInfo;
      const t = match.phaseT;
      fx = g.gx + (g.side === 0 ? 260 : -260);
      fy = CY;
      zoom = t < 1.5 ? 1.22 : 1.05;
      rate = 2.4;
    } else if (match.phase === 'intro') {
      const t = match.phaseT;
      fx = CX + Math.sin(t * 0.8) * 200;
      fy = CY;
      zoom = 0.82 + Math.min(1, t / 2.2) * 0.18;
      rate = 2;
    } else if (match.phase === 'halftime' || match.phase === 'fulltime') {
      fx = CX; fy = CY; zoom = 0.8; rate = 1.5;
    } else if (match.phase === 'kickoff') {
      fx = CX; fy = CY; zoom = 1;
    }
    this.zoom = damp(this.zoom, zoom, 2.5, dt);
    this.viewW = BASE_VIEW_W / this.zoom;
    this.viewH = this.viewW / aspect;
    this.x = damp(this.x, fx, rate, dt);
    this.y = damp(this.y, fy, rate, dt);
    this.clamp();
  }

  clamp() {
    const bnd = arenaBounds();
    const hw = this.viewW / 2, hh = this.viewH / 2;
    this.x = bnd.x1 - bnd.x0 < this.viewW ? (bnd.x0 + bnd.x1) / 2 : clamp(this.x, bnd.x0 + hw, bnd.x1 - hw);
    this.y = bnd.y1 - bnd.y0 < this.viewH ? (bnd.y0 + bnd.y1) / 2 : clamp(this.y, bnd.y0 + hh, bnd.y1 - hh);
  }

  get view() {
    return { x0: this.x - this.viewW / 2, y0: this.y - this.viewH / 2, x1: this.x + this.viewW / 2, y1: this.y + this.viewH / 2 };
  }
}
