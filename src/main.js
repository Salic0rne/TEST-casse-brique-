// Boot, main loop and app state machine (title → setup → match ⇄ pause → results).
import { buildArena } from './render/arena.js';
import { Post } from './render/post.js';
import { renderScene } from './render/renderer.js';
import { fx } from './render/fx.js';
import { Match } from './game/match.js';
import { Camera } from './game/camera.js';
import { DIFFICULTIES, HALF_OPTIONS, TEAMS } from './game/constants.js';
import { audio } from './audio/audio.js';
import { music } from './audio/music.js';
import { beginFrame, endFrame, menuInput, keyPressed, connectedPads } from './core/input.js';
import { drawHUD, drawTitle, drawMenu, drawPause, drawResults } from './ui/hud.js';
import { makeCanvas } from './core/math.js';

const wrap = document.getElementById('wrap');
const glCanvas = document.createElement('canvas');
const hudCanvas = document.createElement('canvas');
wrap.append(glCanvas, hudCanvas);
const scene = makeCanvas(16, 9);
const sctx = scene.getContext('2d', { alpha: false });
const hctx = hudCanvas.getContext('2d');
let post = null;
try { post = new Post(glCanvas); if (!post.ok) post = null; } catch (e) { console.warn('WebGL post disabled', e); post = null; }
const fallbackCtx = post ? null : glCanvas.getContext('2d');

let cw = 1280, ch = 720;
function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = window.innerWidth, h = window.innerHeight;
  wrap.style.width = w + 'px';
  wrap.style.height = h + 'px';
  // Cap the render resolution around 1080p for a stable framerate.
  let rw = Math.round(w * dpr), rh = Math.round(h * dpr);
  const maxPixels = 1920 * 1080;
  if (rw * rh > maxPixels) { const k = Math.sqrt(maxPixels / (rw * rh)); rw = Math.round(rw * k); rh = Math.round(rh * k); }
  cw = rw; ch = rh;
  scene.width = cw; scene.height = ch;
  hudCanvas.width = cw; hudCanvas.height = ch;
  if (post) post.resize(cw, ch); else { glCanvas.width = cw; glCanvas.height = ch; }
}
window.addEventListener('resize', resize);
resize();

const settings = {
  mode: 0, // 0 solo, 1 versus, 2 coop, 3 demo
  team: 0,
  difficulty: 1,
  half: 1,
  music: true,
};
const MODES = ['SOLO VS CPU', '2 JOUEURS — VERSUS', '2 JOUEURS — COOP VS CPU', 'DÉMO CPU VS CPU'];

const app = {
  state: 'boot',
  match: null,
  camera: new Camera(),
  menu: null,
  stateT: 0,
  time: 0,
  perf: { update: 0, render: 0 },
  showPerf: false,
};

function newDemo() {
  app.match = new Match({ humans: [], difficulty: 2, halfLength: 60, demo: true });
  app.match.camera = app.camera;
  app.camera.snap(app.match);
  fx.reset();
}

function devicesFor(mode) {
  const pads = connectedPads();
  if (mode === 0) return [{ kind: 'merge' }];
  if (pads.length >= 2) return [{ kind: 'pad', index: pads[0] }, { kind: 'pad', index: pads[1] }];
  if (pads.length === 1) return [{ kind: 'kb', map: 'solo' }, { kind: 'pad', index: pads[0] }];
  return [{ kind: 'kb', map: 'left' }, { kind: 'kb', map: 'right' }];
}

function startMatch() {
  const mode = settings.mode;
  const devs = devicesFor(mode);
  let humans = [];
  if (mode === 0) humans = [{ device: devs[0], team: settings.team }];
  else if (mode === 1) humans = [{ device: devs[0], team: 0 }, { device: devs[1], team: 1 }];
  else if (mode === 2) humans = [{ device: devs[0], team: settings.team }, { device: devs[1], team: settings.team }];
  fx.reset();
  app.match = new Match({ humans, difficulty: settings.difficulty, halfLength: HALF_OPTIONS[settings.half], demo: false });
  app.match.camera = app.camera;
  app.match.spectator = mode === 3;
  app.camera.snap(app.match);
  setState('match');
  music.setMode('game');
  audio.play('ui', { kind: 'select' });
}

function setState(s) {
  app.state = s;
  app.stateT = 0;
}

function setupMenu() {
  const items = [
    { label: 'MODE', key: 'mode', value: MODES[settings.mode], options: MODES.length },
    { label: 'TON ÉQUIPE', key: 'team', value: TEAMS[settings.team].name, options: 2, disabled: settings.mode === 1 || settings.mode === 3 },
    { label: 'DIFFICULTÉ CPU', key: 'difficulty', value: DIFFICULTIES[settings.difficulty].name, options: 3 },
    { label: 'DURÉE MI-TEMPS', key: 'half', value: `${HALF_OPTIONS[settings.half]} S`, options: 3 },
    { label: 'MUSIQUE', key: 'music', value: settings.music ? 'ON' : 'OFF', options: 2 },
    { label: 'ENTRER DANS L\'ARÈNE', action: 'start', big: true },
    { label: 'QUITTER', action: 'quit' },
  ];
  const pads = connectedPads().length;
  const help = `${pads} MANETTE${pads > 1 ? 'S' : ''} DÉTECTÉE${pads > 1 ? 'S' : ''}  •  ↑↓ CHOISIR  ←→ MODIFIER  •  ENTRÉE VALIDER`;
  const index = app.menu && app.menu.kind === 'setup' ? app.menu.index : items.length - 2;
  app.menu = { kind: 'setup', items, index, help };
}

function applySetting(it, delta) {
  const k = it.key;
  if (k === 'music') { settings.music = !settings.music; audio.setMusicVolume(settings.music ? 0.55 : 0); }
  else settings[k] = (settings[k] + delta + it.options) % it.options;
  audio.play('ui', { kind: 'move' });
  setupMenu();
}

function navigate(menu, inp) {
  const n = menu.items.length;
  const step = (d) => {
    let i = menu.index;
    for (let k = 0; k < n; k++) { i = (i + d + n) % n; if (!menu.items[i].disabled) break; }
    menu.index = i;
    audio.play('ui', { kind: 'move' });
  };
  if (inp.up) step(-1);
  if (inp.down) step(1);
}

function update(realDt) {
  const inp = menuInput();
  if (inp.any) { audio.init(); if (!music.playing) music.start(app.state === 'match' ? 'game' : 'menu'); }
  if (keyPressed('KeyM')) { settings.music = !settings.music; audio.setMusicVolume(settings.music ? 0.55 : 0); }
  app.stateT += realDt;
  app.time += realDt;

  switch (app.state) {
    case 'title':
      stepMatch(realDt);
      if (app.match.over && app.match.phaseT > 3) newDemo();
      if (inp.confirm || inp.start) { setupMenu(); setState('setup'); audio.play('ui', { kind: 'select' }); }
      break;
    case 'setup': {
      stepMatch(realDt);
      if (app.match.over && app.match.phaseT > 3) newDemo();
      const m = app.menu;
      navigate(m, inp);
      const it = m.items[m.index];
      if (it.key && (inp.left || inp.right)) applySetting(it, inp.left ? -1 : 1);
      if (inp.confirm) {
        if (it.action === 'start') startMatch();
        else if (it.action === 'quit') window.close();
        else if (it.key) applySetting(it, 1);
      }
      if (inp.back) { setState('title'); audio.play('ui', { kind: 'back' }); }
      break;
    }
    case 'match': {
      const m = app.match;
      if (inp.start) {
        app.menu = { kind: 'pause', items: [{ label: 'REPRENDRE', action: 'resume' }, { label: 'RECOMMENCER', action: 'restart' }, { label: 'QUITTER LE MATCH', action: 'quit' }], index: 0 };
        setState('paused');
        audio.play('ui', { kind: 'select' });
        break;
      }
      if (m.phase === 'play' || m.phase === 'kickoff') music.setMode('game');
      stepMatch(realDt);
      if (m.over && m.phaseT > 3.2) {
        app.menu = { kind: 'results', items: [{ label: 'REVANCHE', action: 'rematch' }, { label: 'MENU', action: 'menu' }], index: 0 };
        setState('results');
        music.setMode('results');
      }
      break;
    }
    case 'paused': {
      const m = app.menu;
      navigate(m, inp);
      if (inp.start || inp.back) { setState('match'); break; }
      if (inp.confirm) {
        const a = m.items[m.index].action;
        if (a === 'resume') setState('match');
        else if (a === 'restart') startMatch();
        else { toTitle(); }
      }
      break;
    }
    case 'results': {
      stepMatch(realDt);
      const m = app.menu;
      if (inp.left || inp.up) { m.index = 0; audio.play('ui', { kind: 'move' }); }
      if (inp.right || inp.down) { m.index = 1; audio.play('ui', { kind: 'move' }); }
      if (inp.confirm && app.stateT > 0.8) {
        if (m.items[m.index].action === 'rematch') startMatch();
        else toTitle();
      }
      break;
    }
  }
}

function toTitle() {
  newDemo();
  setupMenu();
  setState('setup');
  music.setMode('menu');
  audio.setCrowd(0.1);
}

const FIXED = 1 / 120;
function stepMatch(realDt) {
  const m = app.match;
  let simDt = realDt * fx.slowmo;
  if (fx.hitstop > 0) { fx.hitstop -= realDt; simDt = 0; }
  fx.update(simDt, realDt);
  m.pollHumans();
  if (simDt > 0) {
    const n = Math.min(8, Math.ceil(simDt / FIXED));
    for (let i = 0; i < n; i++) m.update(simDt / n);
  }
  app.camera.update(realDt, m, cw / ch);
}

function render() {
  const m = app.match;
  const time = app.time;
  renderScene(sctx, m, app.camera, cw, ch, time);
  const shocks = fx.shocks.map((s) => {
    const v = app.camera.view;
    return { x: (s.x - v.x0) / app.camera.viewW, y: 1 - (s.y - v.y0) / app.camera.viewH, r: s.t * 0.9, s: s.s * (1 - s.t / 0.9) };
  });
  const menuDim = app.state === 'title' || app.state === 'setup' ? 0.78 : 1;
  if (post) {
    post.render(scene, {
      time,
      ca: Math.min(1, fx.ca),
      flash: [...fx.flashColor, Math.min(0.8, fx.flash)],
      shocks,
      bloom: 1.05,
      sat: app.state === 'paused' ? 0.35 : 1.1,
      vignette: 0.6,
      dim: menuDim * (app.state === 'paused' ? 0.7 : 1),
    });
  } else {
    fallbackCtx.drawImage(scene, 0, 0);
  }

  hctx.clearRect(0, 0, cw, ch);
  if (app.state === 'match' || app.state === 'paused') {
    if (!m.demo) drawHUD(hctx, m, app.camera, cw, ch, time);
  }
  if (app.state === 'title') drawTitle(hctx, cw, ch, time);
  else if (app.state === 'setup') drawMenu(hctx, cw, ch, time, app.menu);
  else if (app.state === 'paused') drawPause(hctx, cw, ch, time, app.menu);
  else if (app.state === 'results') drawResults(hctx, cw, ch, time, m, app.menu, app.stateT);
}

let last = performance.now();
let fpsAcc = 0, fpsN = 0;
window.__game = app; // handy for debugging from devtools
window.__audio = audio;
function frame(now) {
  const realDt = Math.min(0.05, (now - last) / 1000);
  last = now;
  fpsAcc += realDt; fpsN++;
  if (fpsAcc > 1) { app.fps = fpsN / fpsAcc; fpsAcc = 0; fpsN = 0; }
  beginFrame();
  const t0 = performance.now();
  update(realDt);
  const t1 = performance.now();
  render();
  const t2 = performance.now();
  const pf = app.perf;
  pf.update += (t1 - t0 - pf.update) * 0.05;
  pf.render += (t2 - t1 - pf.render) * 0.05;
  if (keyPressed('F3')) app.showPerf = !app.showPerf;
  if (app.showPerf) {
    hctx.font = `${Math.round(18 * ch / 1080)}px monospace`;
    hctx.fillStyle = '#9f9';
    hctx.textAlign = 'left';
    hctx.fillText(`FPS ${app.fps ? app.fps.toFixed(0) : '-'}  sim ${pf.update.toFixed(1)}ms  render ${pf.render.toFixed(1)}ms  parts ${fx.parts.length}`, 10, ch - 10);
  }
  endFrame();
  requestAnimationFrame(frame);
}

async function boot() {
  try {
    await Promise.race([
      Promise.all([document.fonts.load('40px BlackOps'), document.fonts.load('40px Bebas')]),
      new Promise((r) => setTimeout(r, 1500)),
    ]);
  } catch (e) { /* fonts optional */ }
  buildArena();
  newDemo();
  setState('title');
  // Electron allows autoplay; in a browser this waits for the first key press.
  audio.init();
  if (audio.ready && audio.ctx.state === 'running') music.start('menu');
  requestAnimationFrame((t) => { last = t; frame(t); });
}
boot();
