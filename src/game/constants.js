// World geometry & tuning. Units are world pixels; the field runs left → right.
export const FIELD_W = 2400;
export const FIELD_H = 1150;
export const CX = FIELD_W / 2;
export const CY = FIELD_H / 2;
export const WALL = 70; // wall thickness drawn around the field
export const GOAL_HALF = 125; // half height of the goal mouth
export const GOAL_DEPTH = 70;
export const GOAL_Z = 95; // ball above this flies over the goal frame (bounces off)

export const GRAVITY = 1500;
export const BALL_GRAVITY = 1150;
export const BALL_R = 11;
export const PLAYER_R = 22;

export const PLAYER_SPEED = 330;
export const CARRIER_SPEED_MUL = 0.93;
export const SLIDE_SPEED = 640;
export const SLIDE_TIME = 0.42;
export const SLIDE_RECOVER = 0.28;
export const JUMP_VZ = 470;
export const THROW_MIN = 900;
export const THROW_MAX = 1400;
export const CHARGE_TIME = 0.45;
export const LOB_VZ = 540;
export const CATCH_R = 34;

export const GOAL_POINTS = 10;
export const STAR_POINTS = 2;
export const STAR_ROW_BONUS = 10;
export const KO_POINTS = 5;

// Arena furniture (fractions of the field).
export const BUMPERS = [
  { x: 0.2, y: 0.22 }, { x: 0.2, y: 0.78 }, { x: 0.8, y: 0.22 }, { x: 0.8, y: 0.78 },
].map((b) => ({ x: b.x * FIELD_W, y: b.y * FIELD_H, r: 34 }));

export const ELECTRO = [
  { x: 0.39, y: 0.5 }, { x: 0.61, y: 0.5 },
].map((b) => ({ x: b.x * FIELD_W, y: b.y * FIELD_H, r: 26 }));

export const STAR_XS = [0.09, 0.2, 0.31, 0.69, 0.8, 0.91].map((f) => f * FIELD_W);

// Score multiplier ramps sit in the middle of the top & bottom walls.
export const RAMP_HALF = 95;
export const RAMP_DEPTH = 70;

export const HALF_OPTIONS = [60, 90, 120];
export const DIFFICULTIES = [
  { name: 'RECRUE', react: 0.34, aggro: 0.35, aim: 0.55, speed: 0.92, gk: 0.55 },
  { name: 'GUERRIER', react: 0.22, aggro: 0.6, aim: 0.75, speed: 0.97, gk: 0.72 },
  { name: 'WARLORD', react: 0.12, aggro: 0.85, aim: 0.92, speed: 1.02, gk: 0.86 },
];

export const TEAMS = [
  {
    name: 'RUST REAVERS',
    short: 'RVR',
    armor: '#c5541f', armorDark: '#6e2a0f', armorLight: '#f08a3c',
    cloth: '#2c1c14', pants: '#6a4630', skin: '#b07a52', accent: '#ffb42a', glow: '#ff7a1a',
    crest: 'mohawk', crestColor: '#e3261b',
  },
  {
    name: 'CHROME JACKALS',
    short: 'JKL',
    armor: '#4f7f95', armorDark: '#1d3440', armorLight: '#9cd3e6',
    cloth: '#161c22', pants: '#3e505c', skin: '#d8d0c4', accent: '#3ff2ff', glow: '#25c8ff',
    crest: 'skull', crestColor: '#e9e4d8',
  },
];

// Role layout for a team attacking toward +x, in field fractions.
export const FORMATION = [
  { role: 'GK', x: 0.035, y: 0.5 },
  { role: 'DF', x: 0.2, y: 0.32 },
  { role: 'DF', x: 0.2, y: 0.68 },
  { role: 'MF', x: 0.38, y: 0.5 },
  { role: 'FW', x: 0.56, y: 0.25 },
  { role: 'FW', x: 0.56, y: 0.75 },
];

export const PLAYER_NAMES = [
  ['GRIMSKULL', 'NUX', 'SLAG', 'KRANK', 'BOLTJAW', 'RUSTFANG'],
  ['VULTCH', 'CHROMA', 'STITCH', 'HEXBONE', 'RAZR', 'DUSTWYRM'],
];
