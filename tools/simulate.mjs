// Simulation "headless" de matchs IA contre IA (sans rendu ni son) : vérifie la stabilité (NaN, blocages)
// et donne des statistiques d'équilibrage (buts, tacles, arrêts...).
// usage : node tools/simulate.mjs [dureeMiTemps=60] [difficulte=1]
import { Match } from '../src/js/game.js';
import { TEAMS } from '../src/js/config.js';

const secs = +process.argv[2] || 60, diff = process.argv[3] !== undefined ? +process.argv[3] : 1;
const nul = new Proxy({}, { get: () => () => ({ set() {}, stop() {} }) });
const input = { slots: [{}, {}] };

function makeFx() {
  const fx = { hitstop: 0, p: [] };
  return new Proxy(fx, { get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; } });
}

function run(a, b) {
  let res = null;
  const m = new Match({ teamA: TEAMS[a], teamB: TEAMS[b], mode2p: false, attract: true, difficulty: diff, duration: secs, audio: nul, music: nul, fx: makeFx(), input, onEnd: (r) => (res = r) });
  let t = 0, bad = 0;
  while (!res && t < secs * 2 + 240) {
    m.update(1 / 60); t += 1 / 60;
    const ball = m.ball;
    if (![ball.x, ball.y, ball.z, ball.vx, ball.vy].every(Number.isFinite)) { bad++; break; }
    for (const p of m.players) if (![p.x, p.y, p.vx, p.vy, p.z].every(Number.isFinite)) bad++;
    if (bad) break;
  }
  return { match: `${TEAMS[a].id} vs ${TEAMS[b].id}`, finished: !!res, simSeconds: Math.round(t), score: m.teams.map((x) => x.score), goals: m.teams.map((x) => x.goals), stats: m.teams.map((x) => x.stats), invalid: bad };
}

let failed = false;
for (const [a, b] of [[0, 1], [2, 3], [1, 2], [3, 0]]) {
  const r = run(a, b);
  console.log(JSON.stringify(r));
  if (!r.finished || r.invalid) failed = true;
}
console.log(failed ? 'ECHEC' : 'OK');
process.exit(failed ? 1 : 0);
