// Petit serveur statique pour tester dans un navigateur (les modules ES ne se chargent pas en file:// hors Electron).
const http = require('http'), fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..', 'src');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.woff2': 'font/woff2', '.css': 'text/css', '.png': 'image/png' };
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]); if (p === '/') p = '/index.html';
  const f = path.join(root, p);
  if (!f.startsWith(root) || !fs.existsSync(f)) { res.writeHead(404); return res.end('nf'); }
  res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(process.env.PORT || 8123, () => console.log('http://localhost:' + (process.env.PORT || 8123)));
