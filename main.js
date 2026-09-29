// Processus principal Electron : fenêtre plein écran 16:9, sans menu, audio autorisé sans geste utilisateur.
const { app, BrowserWindow, Menu, globalShortcut } = require('electron');
const path = require('path');

const DEV = process.argv.includes('--dev');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
app.commandLine.appendSwitch('disable-frame-rate-limit'); // vsync géré par requestAnimationFrame
app.commandLine.appendSwitch('enable-gpu-rasterization');

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 900,
    minWidth: 960,
    minHeight: 540,
    backgroundColor: '#1b1416',
    title: 'Steel Ball Arena',
    autoHideMenuBar: true,
    fullscreenable: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      autoplayPolicy: 'no-user-gesture-required',
      backgroundThrottling: false,
    },
  });
  Menu.setApplicationMenu(null);
  win.loadFile(path.join(__dirname, 'src', 'index.html'));
  if (DEV) win.webContents.openDevTools({ mode: 'detach' });

  // Auto-test (CI / vérification) : --selftest=/chemin/capture.png => capture après quelques secondes puis quitte.
  const st = process.argv.find((a) => a.startsWith('--selftest='));
  if (st) {
    win.webContents.on('console-message', (_e, level, msg) => { if (level >= 2) console.log('[renderer]', msg); });
    setTimeout(async () => {
      const img = await win.webContents.capturePage();
      require('fs').writeFileSync(st.split('=')[1], img.toPNG());
      console.log('selftest ok');
      app.quit();
    }, 7000);
  }

  win.webContents.on('before-input-event', (e, input) => {
    if (input.type !== 'keyDown') return;
    if (input.key === 'F11' || (input.alt && input.key === 'Enter')) {
      win.setFullScreen(!win.isFullScreen());
      e.preventDefault();
    }
    if (input.key === 'F12' && DEV) win.webContents.toggleDevTools();
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});
app.on('window-all-closed', () => { globalShortcut.unregisterAll(); app.quit(); });
