// Vertical-scrolling camera (Speedball 2 style): the whole pitch width stays in view,
// the camera scrolls along the length and looks ahead in the direction of attack.
import { FIELD_W as W, FIELD_H as H, CX, CY } from './constants.js';
import { clamp, damp } from '../core/math.js';
import { arenaBounds } from '../render/arena.js';

// Pitch width + both side walls + a slice of the stands.
export const BASE_VIEW_W = W + 2 * 250;

export class Camera {
  constructor() {
    this.x = CX; this.y = CY;
    this.zoom = 1;
    this.viewW = BASE_VIEW_W;
    this.viewH = BASE_VIEW_W * 9 / 16;
    this.look = 0;
  }

  snap() {
    this.x = CX; this.y = CY; this.look = 0;
  }

  update(dt, match, aspect) {
    const b = match.ball;
    let fx = b.x, fy = b.y - b.z * 0.3;
    let zoom = 1;
    let rate = 3.4;
    let look = 0;
    if (b.owner) {
      const o = b.owner;
      fy = o.y + o.vy * 0.35;
      look = o.team.dir * 200; // see the pitch in front of the carrier
    } else {
      fx += b.vx * 0.15;
      fy += b.vy * 0.3;
      if (b.z > 90) zoom = 0.94;
    }
    const hs = match.humans.filter((h) => h.player);
    if (hs.length === 1) {
      const p = hs[0].player;
      fy = fy * 0.8 + p.y * 0.2;
    } else if (hs.length > 1) {
      zoom = Math.min(zoom, 0.9);
    }
    if (match.phase === 'goal' && match.goalInfo) {
      const g = match.goalInfo;
      fx = CX;
      fy = g.gy + (g.side === 0 ? 300 : -300);
      look = 0;
      zoom = match.phaseT < 1.5 ? 1.12 : 1;
      rate = 2.4;
    } else if (match.phase === 'intro') {
      fx = CX; fy = CY + Math.sin(match.phaseT * 0.9) * 150; look = 0;
      zoom = 0.88 + Math.min(1, match.phaseT / 2.2) * 0.12;
      rate = 2;
    } else if (match.phase === 'halftime' || match.phase === 'fulltime') {
      fx = CX; fy = CY; look = 0; zoom = 0.85; rate = 1.5;
    } else if (match.phase === 'kickoff') {
      fx = CX; fy = CY; look = 0;
    }
    this.look = damp(this.look, look, 2.2, dt);
    this.zoom = damp(this.zoom, zoom, 2.5, dt);
    this.viewW = BASE_VIEW_W / this.zoom;
    this.viewH = this.viewW / aspect;
    // Horizontal: stay mostly centred, drift slightly toward the action.
    const tx = CX + (fx - CX) * (this.viewW >= W + 200 ? 0.12 : 0.8);
    this.x = damp(this.x, tx, rate, dt);
    this.y = damp(this.y, fy + this.look, rate, dt);
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
