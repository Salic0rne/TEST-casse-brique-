// World geometry & tuning. Units are world pixels.
// Speedball 2 layout: a tall pitch, goals at the top (y = 0) and bottom (y = FIELD_H).
export const FIELD_W = 1200;
export const FIELD_H = 2600;
export const CX = FIELD_W / 2;
export const CY = FIELD_H / 2;
export const GOAL_HALF = 135; // half width of the goal mouth
export const GOAL_DEPTH = 80;
export const GOAL_Z = 100; // ball above this hits the crossbar

export const GRAVITY = 1500;
export const BALL_GRAVITY = 1150;
export const BALL_R = 10;
export const PLAYER_R = 21;

export const PLAYER_SPEED = 345;
export const CARRIER_SPEED_MUL = 0.93;
export const SLIDE_SPEED = 660;
export const SLIDE_TIME = 0.42;
export const SLIDE_RECOVER = 0.28;
export const JUMP_VZ = 470;
export const THROW_MIN = 950;
export const THROW_MAX = 1450;
export const CHARGE_TIME = 0.45;
export const LOB_VZ = 560;
export const CATCH_R = 34;

export const GOAL_POINTS = 10;
export const STAR_POINTS = 2;
export const STAR_ROW_BONUS = 10;
export const KO_POINTS = 5;

// Arena furniture.
export const BUMPERS = [
  { x: 0.2, y: 0.24 }, { x: 0.8, y: 0.24 }, { x: 0.2, y: 0.76 }, { x: 0.8, y: 0.76 },
].map((b) => ({ x: b.x * FIELD_W, y: b.y * FIELD_H, r: 34 }));

export const ELECTRO = [
  { x: 0.22, y: 0.5 }, { x: 0.78, y: 0.5 },
].map((b) => ({ x: b.x * FIELD_W, y: b.y * FIELD_H, r: 26 }));

// Stars on the left and right walls.
export const STAR_YS = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9].map((f) => f * FIELD_H);

// Score multiplier ramps sit in the middle of the left and right walls.
export const RAMP_HALF = 100;

export const HALF_OPTIONS = [60, 90, 120];
export const DIFFICULTIES = [
  { react: 0.34, aggro: 0.35, aim: 0.55, speed: 0.92, gk: 0.55 },
  { react: 0.22, aggro: 0.6, aim: 0.75, speed: 0.97, gk: 0.72 },
  { react: 0.12, aggro: 0.85, aim: 0.92, speed: 1.02, gk: 0.86 },
];

// Gritty, desaturated kits. `mark` is the team identification colour (rags, paint, lights).
export const TEAMS = [
  {
    name: 'RUST REAVERS',
    short: 'RVR',
    mark: '#f2641e', markDark: '#7a2408', glow: '#ff7a1a', ui: '#f07030',
    metal: '#3a3230', metalDark: '#1a1514', metalLight: '#7a6a62',
    leather: '#241a15', pants: '#2e2622', skin: '#8e6448', boot: '#120d0b',
    mask: 'welder',
  },
  {
    name: 'BONE JACKALS',
    short: 'JKL',
    mark: '#c9d4d6', markDark: '#4c5a60', glow: '#8fe8ff', ui: '#b9e2ec',
    metal: '#5b6468', metalDark: '#1f2528', metalLight: '#9aa6aa',
    leather: '#26282a', pants: '#34393c', skin: '#d6d0c6', boot: '#151515',
    mask: 'warboy',
  },
];

// Role layout for a team attacking toward +y: x = lateral fraction, y = depth from own goal.
export const FORMATION = [
  { role: 'GK', x: 0.5, y: 0.03 },
  { role: 'DF', x: 0.3, y: 0.19 },
  { role: 'DF', x: 0.7, y: 0.19 },
  { role: 'MF', x: 0.5, y: 0.35 },
  { role: 'FW', x: 0.24, y: 0.47 },
  { role: 'FW', x: 0.76, y: 0.47 },
];

export const PLAYER_NAMES = [
  ['GRIMSKULL', 'NUX', 'SLAG', 'KRANK', 'BOLTJAW', 'RUSTFANG'],
  ['VULTCH', 'CHALK', 'STITCH', 'HEXBONE', 'RAZR', 'DUSTWYRM'],
];
