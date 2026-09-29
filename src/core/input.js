// Keyboard + gamepad input, abstracted into "devices" that each human player owns.

const down = new Set();
const pressed = new Set();
const PREVENT = new Set(['Space', 'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ShiftLeft', 'ShiftRight']);

window.addEventListener('keydown', (e) => {
  if (PREVENT.has(e.code)) e.preventDefault();
  if (!down.has(e.code)) pressed.add(e.code);
  down.add(e.code);
});
window.addEventListener('keyup', (e) => down.delete(e.code));
window.addEventListener('blur', () => down.clear());

const KEYMAPS = {
  // Solo: every comfortable layout works at once.
  solo: {
    up: ['KeyW', 'ArrowUp', 'KeyZ'], down: ['KeyS', 'ArrowDown'], left: ['KeyA', 'ArrowLeft', 'KeyQ'], right: ['KeyD', 'ArrowRight'],
    action: ['Space', 'KeyJ', 'KeyX'], jump: ['KeyK', 'KeyC', 'ShiftLeft'], swap: ['KeyL', 'KeyV', 'Tab'],
  },
  // Shared keyboard, left player (AZERTY friendly: Z/Q also move).
  left: {
    up: ['KeyW', 'KeyZ'], down: ['KeyS'], left: ['KeyA', 'KeyQ'], right: ['KeyD'],
    action: ['Space', 'KeyF'], jump: ['ShiftLeft', 'KeyG'], swap: ['Tab', 'KeyR'],
  },
  // Shared keyboard, right player.
  right: {
    up: ['ArrowUp'], down: ['ArrowDown'], left: ['ArrowLeft'], right: ['ArrowRight'],
    action: ['Numpad0', 'ControlRight', 'Slash'], jump: ['NumpadDecimal', 'ShiftRight', 'Period'], swap: ['NumpadEnter', 'Comma', 'Numpad1'],
  },
};

const anyOf = (codes, set) => codes.some((c) => set.has(c));

const padPrev = new Map();
let padNow = new Map();

function readPads() {
  padNow = new Map();
  const pads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const p of pads) {
    if (!p || !p.connected) continue;
    padNow.set(p.index, {
      axes: p.axes.slice(0, 4),
      buttons: p.buttons.map((b) => b.pressed || b.value > 0.5),
    });
  }
}

export function connectedPads() {
  return [...padNow.keys()].sort((a, b) => a - b);
}

function padState(index) {
  const s = padNow.get(index);
  const prev = padPrev.get(index);
  if (!s) return null;
  const b = (i) => !!s.buttons[i];
  const bp = (i) => !!s.buttons[i] && !(prev && prev.buttons[i]);
  let mx = s.axes[0] || 0, my = s.axes[1] || 0;
  const mag = Math.hypot(mx, my);
  if (mag < 0.22) { mx = 0; my = 0; } else { const k = Math.min(1, (mag - 0.22) / 0.7) / mag; mx *= k; my *= k; }
  if (b(12)) my = -1; if (b(13)) my = 1; if (b(14)) mx = -1; if (b(15)) mx = 1;
  return {
    mx, my,
    action: b(0) || b(7), actionPressed: bp(0) || bp(7),
    jump: b(1) || b(2) || b(6), jumpPressed: bp(1) || bp(2) || bp(6),
    swapPressed: bp(4) || bp(5) || bp(3),
    startPressed: bp(9),
    backPressed: bp(1) || bp(8),
    upPressed: bp(12) || (my < -0.6 && !(prev && (prev.axes[1] || 0) < -0.6)),
    downPressed: bp(13) || (my > 0.6 && !(prev && (prev.axes[1] || 0) > 0.6)),
    leftPressed: bp(14) || (mx < -0.6 && !(prev && (prev.axes[0] || 0) < -0.6)),
    rightPressed: bp(15) || (mx > 0.6 && !(prev && (prev.axes[0] || 0) > 0.6)),
  };
}

function kbState(mapName) {
  const m = KEYMAPS[mapName];
  let mx = 0, my = 0;
  if (anyOf(m.left, down)) mx -= 1;
  if (anyOf(m.right, down)) mx += 1;
  if (anyOf(m.up, down)) my -= 1;
  if (anyOf(m.down, down)) my += 1;
  if (mx && my) { mx *= Math.SQRT1_2; my *= Math.SQRT1_2; }
  return {
    mx, my,
    action: anyOf(m.action, down), actionPressed: anyOf(m.action, pressed),
    jump: anyOf(m.jump, down), jumpPressed: anyOf(m.jump, pressed),
    swapPressed: anyOf(m.swap, pressed),
    startPressed: pressed.has('Escape') || pressed.has('KeyP'),
    backPressed: pressed.has('Escape') || pressed.has('Backspace'),
    upPressed: anyOf(m.up, pressed), downPressed: anyOf(m.down, pressed),
    leftPressed: anyOf(m.left, pressed), rightPressed: anyOf(m.right, pressed),
  };
}

/** A device is {kind:'kb', map} or {kind:'pad', index}. */
export function readDevice(dev) {
  if (!dev) return null;
  if (dev.kind === 'pad') return padState(dev.index) || kbState('solo');
  if (dev.kind === 'merge') {
    // Solo player: keyboard and first gamepad both drive the same player.
    const k = kbState('solo');
    const first = [...padNow.keys()].sort((a, b) => a - b)[0];
    const p = first !== undefined ? padState(first) : null;
    if (!p) return k;
    const out = {};
    for (const key in k) out[key] = typeof k[key] === 'boolean' ? k[key] || p[key] : k[key];
    if (Math.hypot(p.mx, p.my) > Math.hypot(k.mx, k.my)) { out.mx = p.mx; out.my = p.my; }
    return out;
  }
  return kbState(dev.map);
}

/** Menu input merges every source. */
export function menuInput() {
  const s = kbState('solo');
  const r = {
    up: s.upPressed, down: s.downPressed, left: s.leftPressed, right: s.rightPressed,
    confirm: pressed.has('Enter') || pressed.has('Space') || pressed.has('KeyJ') || pressed.has('NumpadEnter'),
    back: pressed.has('Escape') || pressed.has('Backspace'),
    start: pressed.has('Escape') || pressed.has('KeyP'),
    any: pressed.size > 0,
  };
  for (const i of padNow.keys()) {
    const p = padState(i);
    r.up ||= p.upPressed; r.down ||= p.downPressed; r.left ||= p.leftPressed; r.right ||= p.rightPressed;
    r.confirm ||= p.actionPressed || p.startPressed;
    r.back ||= p.backPressed && !p.actionPressed;
    r.start ||= p.startPressed;
    r.any ||= p.actionPressed || p.startPressed;
  }
  return r;
}

export function keyPressed(code) {
  return pressed.has(code);
}

export function beginFrame() {
  readPads();
}

export function endFrame() {
  pressed.clear();
  for (const [k, v] of padNow) padPrev.set(k, v);
}
