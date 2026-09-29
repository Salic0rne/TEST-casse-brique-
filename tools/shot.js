// Outil de test : lance le jeu dans Chromium headless, exécute un script et enregistre des captures.
// usage: node tools/shot.js <scenario>
const { execSync, spawn } = require('child_process');
const path = require('path');
const gp = execSync('npm root -g').toString().trim();
const { chromium } = require(path.join(gp, 'playwright'));
const out = process.env.OUT || '/tmp/shots';
require('fs').mkdirSync(out, { recursive: true });
(async () => {
  const server = spawn('node', [path.join(__dirname, 'serve.js')], { env: { ...process.env, PORT: '8123' } });
  await new Promise((r) => setTimeout(r, 600));
  const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required', '--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push('PAGEERR ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 4).join('\n')));
  page.on('console', (m) => { if (['error', 'warning'].includes(m.type())) errors.push(m.type() + ': ' + m.text()); });
  await page.addInitScript(() => { window.__HQ = true; });
  const scenario = require(path.resolve(process.argv[2]));
  try { await scenario({ page, out, sleep: (ms) => new Promise((r) => setTimeout(r, ms)) }); } catch (e) { errors.push('SCENARIO ' + e.stack); }
  console.log(errors.length ? errors.join('\n') : 'no errors');
  await browser.close(); server.kill();
})();
