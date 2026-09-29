// Entrées clavier + manettes. Les touches utilisent event.code (positions physiques : ZQSD sur AZERTY = WASD).

const KEYMAP_SOLO = {
  left: ['KeyA', 'ArrowLeft'], right: ['KeyD', 'ArrowRight'], up: ['KeyW', 'ArrowUp'], down: ['KeyS', 'ArrowDown'],
  a: ['Space', 'KeyF', 'KeyJ'], b: ['KeyG', 'KeyK'], turbo: ['ShiftLeft', 'ShiftRight', 'KeyH', 'KeyL'], sw: ['KeyQ', 'KeyE'],
};
const KEYMAP_P1 = {
  left: ['KeyA'], right: ['KeyD'], up: ['KeyW'], down: ['KeyS'],
  a: ['KeyF'], b: ['KeyG'], turbo: ['KeyH'], sw: ['KeyQ'],
};
const KEYMAP_P2 = {
  left: ['ArrowLeft'], right: ['ArrowRight'], up: ['ArrowUp'], down: ['ArrowDown'],
  a: ['KeyK', 'Numpad0'], b: ['KeyL', 'NumpadDecimal'], turbo: ['Semicolon', 'NumpadEnter'], sw: ['KeyO'],
};

function blankSlot() {
  return { mx: 0, my: 0, a: false, aPressed: false, aReleased: false, b: false, bPressed: false, turbo: false, sw: false, swPressed: false };
}

export class Input {
  constructor() {
    this.keys = new Set();
    this.justKeys = new Set();
    this.mode2p = false;
    this.slots = [blankSlot(), blankSlot()];
    this.prev = [{}, {}];
    this.nav = { up: false, down: false, left: false, right: false, ok: false, back: false, pause: false, any: false };
    this._navHold = { up: 0, down: 0, left: 0, right: 0 };
    this._padPrev = {};
    this.mouse = { x: 0, y: 0, down: false, clicked: false, moved: false };
    this.padCount = 0;
    window.addEventListener('keydown', (e) => {
      if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.code)) e.preventDefault();
      if (!this.keys.has(e.code)) this.justKeys.add(e.code);
      this.keys.add(e.code);
    });
    window.addEventListener('keyup', (e) => this.keys.delete(e.code));
    window.addEventListener('blur', () => this.keys.clear());
  }

  _any(list) { for (const c of list) if (this.keys.has(c)) return true; return false; }

  _pad(i) {
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    const list = [];
    for (const p of pads) if (p && p.connected) list.push(p);
    this.padCount = list.length;
    return list[i] || null;
  }

  _padState(p) {
    const dz = 0.22;
    let x = p.axes[0] || 0, y = p.axes[1] || 0;
    if (Math.hypot(x, y) < dz) { x = 0; y = 0; }
    const bt = (i) => !!(p.buttons[i] && p.buttons[i].pressed);
    if (bt(14)) x = -1; if (bt(15)) x = 1; if (bt(12)) y = -1; if (bt(13)) y = 1;
    return { x, y, a: bt(0) || bt(2), b: bt(1), turbo: bt(5) || bt(7) || bt(6), sw: bt(3) || bt(4), start: bt(9), back: bt(8) };
  }

  poll(dt) {
    // --- slots de jeu
    const maps = this.mode2p ? [KEYMAP_P1, KEYMAP_P2] : [KEYMAP_SOLO, null];
    for (let s = 0; s < 2; s++) {
      const slot = this.slots[s], prev = this.prev[s], km = maps[s];
      let mx = 0, my = 0, a = false, b = false, turbo = false, sw = false;
      if (km) {
        if (this._any(km.left)) mx -= 1; if (this._any(km.right)) mx += 1;
        if (this._any(km.up)) my -= 1; if (this._any(km.down)) my += 1;
        a = this._any(km.a); b = this._any(km.b); turbo = this._any(km.turbo); sw = this._any(km.sw);
      }
      const pad = this._pad(s);
      if (pad) {
        const ps = this._padState(pad);
        if (Math.abs(ps.x) > Math.abs(mx) || Math.abs(ps.y) > Math.abs(my)) { mx = ps.x; my = ps.y; }
        a = a || ps.a; b = b || ps.b; turbo = turbo || ps.turbo; sw = sw || ps.sw;
      }
      const m = Math.hypot(mx, my);
      if (m > 1) { mx /= m; my /= m; }
      slot.mx = mx; slot.my = my;
      slot.aPressed = a && !prev.a; slot.aReleased = !a && prev.a; slot.a = a;
      slot.bPressed = b && !prev.b; slot.b = b;
      slot.turbo = turbo;
      slot.swPressed = sw && !prev.sw; slot.sw = sw;
      prev.a = a; prev.b = b; prev.sw = sw;
    }

    // --- navigation menus (toutes sources confondues)
    const nav = this.nav;
    const k = this.keys;
    const pad0 = this._pad(0), pad1 = this._pad(1);
    const raw = { up: false, down: false, left: false, right: false, ok: false, back: false, pause: false };
    raw.up = k.has('ArrowUp') || k.has('KeyW');
    raw.down = k.has('ArrowDown') || k.has('KeyS');
    raw.left = k.has('ArrowLeft') || k.has('KeyA');
    raw.right = k.has('ArrowRight') || k.has('KeyD');
    raw.ok = k.has('Enter') || k.has('Space') || k.has('NumpadEnter');
    raw.back = k.has('Escape') || k.has('Backspace');
    raw.pause = k.has('Escape') || k.has('KeyP');
    for (const p of [pad0, pad1]) {
      if (!p) continue;
      const ps = this._padState(p);
      raw.up ||= ps.y < -0.5; raw.down ||= ps.y > 0.5; raw.left ||= ps.x < -0.5; raw.right ||= ps.x > 0.5;
      raw.ok ||= (p.buttons[0] && p.buttons[0].pressed); raw.back ||= (p.buttons[1] && p.buttons[1].pressed);
      raw.pause ||= ps.start;
    }
    const pp = this._padPrev;
    for (const d of ['up', 'down', 'left', 'right']) {
      let fire = false;
      if (raw[d]) {
        if (!pp[d]) { fire = true; this._navHold[d] = 0.32; }
        else { this._navHold[d] -= dt; if (this._navHold[d] <= 0) { fire = true; this._navHold[d] = 0.11; } }
      }
      nav[d] = fire;
    }
    for (const d of ['ok', 'back', 'pause']) nav[d] = !!raw[d] && !pp[d];
    nav.any = nav.ok || nav.back || nav.up || nav.down || nav.left || nav.right || this.justKeys.size > 0;
    for (const d of Object.keys(raw)) pp[d] = !!raw[d];
  }

  endFrame() {
    this.justKeys.clear();
    this.mouse.clicked = false;
    this.mouse.moved = false;
  }
}
