// Tiny static server to run the game in a browser during development: npm run web
const http = require('http');
const fs = require('fs');
const path = require('path');
const root = path.join(__dirname, '..');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.ttf': 'font/ttf', '.css': 'text/css', '.png': 'image/png' };
const port = Number(process.env.PORT) || 8080;
http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0] === '/' ? '/index.html' : req.url.split('?')[0]));
  if (!p.startsWith(root)) { res.writeHead(403); return res.end(); }
  fs.readFile(p, (err, data) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(port, () => console.log(`STEEL CARNAGE on http://localhost:${port}`));
