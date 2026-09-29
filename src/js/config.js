// Constantes globales, palette et définition des équipes.

export const VIEW_W = 1600;      // résolution logique
export const VIEW_H = 900;

// Arène (coordonnées monde, origine coin haut-gauche du terrain)
export const W = 1900;
export const H = 760;
export const CY = H / 2;
export const GOAL_H = 220;       // ouverture de la cage
export const GOAL_D = 140;       // profondeur du filet
export const GOAL_TOP = 130;     // hauteur de la barre transversale
export const WALL_FACE = 74;     // hauteur visible du mur du fond
export const BALL_R = 15;
export const GRAVITY = 1900;

// Palette cartoon (sauge, saumon, rose, moutarde, acier) + contour prune très sombre.
export const PAL = {
  outline: '#2b181d',
  cream: '#f6efdf',
  sage: '#a9b77a', sageDark: '#5f7040', sageLight: '#d3dca4',
  salmon: '#e0685a', salmonDark: '#8b3a33', salmonLight: '#f5a08c',
  pink: '#ff8fc7', pinkDark: '#b45aa8', pinkLight: '#ffd0e8',
  mustard: '#e8b84a', mustardDark: '#a97a1e', mustardLight: '#ffe08a',
  steel: '#9aa3ad', steelDark: '#5a6472', steelLight: '#d4dbe2',
  navy: '#3a4a6b', navyDark: '#232e47',
  floor: '#3f5666', floorDark: '#2f4250', floorLight: '#587589',
  skin1: '#f0c7a0', skin2: '#c98a62', skin3: '#7a4a33', skin4: '#f4d6bd',
  green: '#b6f26a', teal: '#63d6c4',
};

// side: index d'équipe -> couleurs. type: humains (gros gants mécaniques) ou robots.
export const TEAMS = [
  {
    id: 'bric', name: 'BRICOLEURS', short: 'BRI', tag: 'Clé à molette et mauvaise humeur',
    kind: 'human', keeper: 'bug',
    main: PAL.salmon, dark: PAL.salmonDark, light: PAL.salmonLight, accent: PAL.mustard, accentDark: PAL.mustardDark,
    hair: ['#231512', '#5b2f22', '#231512'], skin: [PAL.skin2, PAL.skin3, PAL.skin1], headgear: ['cap', 'afro', 'ponytail'],
    stats: { speed: 3, power: 4, defense: 3 },
  },
  {
    id: 'moss', name: 'MOSS MECHS', short: 'MOS', tag: 'Lourds, verts et rancuniers',
    kind: 'human', keeper: 'box',
    main: PAL.sage, dark: PAL.sageDark, light: PAL.sageLight, accent: '#e6e39a', accentDark: '#a09c4a',
    hair: ['#3a2a1e', '#a8703a', '#1e1e24'], skin: [PAL.skin1, PAL.skin4, PAL.skin2], headgear: ['helmet', 'cap', 'helmet'],
    stats: { speed: 2, power: 5, defense: 4 },
  },
  {
    id: 'pink', name: 'PINK PULSE', short: 'PNK', tag: 'Vives, roses et sans pitié',
    kind: 'human', keeper: 'pod',
    main: PAL.pink, dark: PAL.pinkDark, light: PAL.pinkLight, accent: '#9d7ad6', accentDark: '#5e3f99',
    hair: ['#6b3a2a', '#e8c26a', '#2a1f3a'], skin: [PAL.skin4, PAL.skin1, PAL.skin2], headgear: ['cap', 'ponytail', 'cap'],
    stats: { speed: 5, power: 2, defense: 2 },
  },
  {
    id: 'knick', name: 'STEEL KNICKS', short: 'STK', tag: 'Géants d\'acier, dunk interdit',
    kind: 'robot', keeper: 'crab',
    main: PAL.navy, dark: PAL.navyDark, light: '#6a83b8', accent: '#f08a3c', accentDark: '#a5531a',
    hair: [PAL.steel, PAL.steel, PAL.steel], skin: [PAL.steel, PAL.steelLight, PAL.steel], headgear: ['bot', 'botcap', 'bot'],
    stats: { speed: 3, power: 3, defense: 5 },
  },
];

export const DIFFICULTY = [
  { name: 'FACILE', speed: 0.9, aimNoise: 0.26, keeper: 250, keeperReact: 0.22, tackle: 0.35, think: 0.55 },
  { name: 'NORMAL', speed: 1.0, aimNoise: 0.13, keeper: 320, keeperReact: 0.12, tackle: 0.6, think: 0.38 },
  { name: 'DIFFICILE', speed: 1.07, aimNoise: 0.05, keeper: 390, keeperReact: 0.04, tackle: 0.9, think: 0.22 },
];

export const DURATIONS = [60, 90, 120, 180];

// Rôles: fx = position de base (0..1 dans le sens de l'attaque), fy = 0..1 sur la hauteur.
export const FORMATION = [
  { role: 'GK', fx: 0.03, fy: 0.5 },
  { role: 'DEF', fx: 0.2, fy: 0.27 },
  { role: 'DEF', fx: 0.2, fy: 0.73 },
  { role: 'FWD', fx: 0.4, fy: 0.36 },
  { role: 'FWD', fx: 0.4, fy: 0.64 },
];

export const BUMPERS = [
  { x: W * 0.35, y: H * 0.27, r: 36 },
  { x: W * 0.65, y: H * 0.27, r: 36 },
  { x: W * 0.35, y: H * 0.73, r: 36 },
  { x: W * 0.65, y: H * 0.73, r: 36 },
];

export const PORTALS = [
  { x: W * 0.5, y: 118, r: 42 },
  { x: W * 0.5, y: H - 118, r: 42 },
];

export const PADS = (() => {
  const xs = [0.15, 0.29, 0.71, 0.85];
  const out = [];
  for (const wall of ['top', 'bottom']) for (const f of xs) out.push({ wall, x: W * f, w: 110 });
  return out;
})();

export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const rand = (a, b) => a + Math.random() * (b - a);
export const randi = (a, b) => Math.floor(rand(a, b + 1));
export const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
export const dist = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);
export const TAU = Math.PI * 2;
export const easeOutBack = (t) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
export const easeOutElastic = (t) => { if (t <= 0) return 0; if (t >= 1) return 1; const c4 = (2 * Math.PI) / 3; return Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1; };
export const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
export const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
