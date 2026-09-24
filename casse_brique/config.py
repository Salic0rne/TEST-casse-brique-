"""Constantes globales : résolution, aire de jeu, gameplay."""

TITLE = "PRISMA"
SUBTITLE = "CASSE-BRIQUE NÉON"
VERSION = "1.0"

# Résolution interne (mise à l'échelle automatiquement par pygame.SCALED)
WIDTH, HEIGHT = 1280, 720
FPS = 60

# Aire de jeu au centre, panneaux d'information à gauche et à droite
PF_LEFT, PF_TOP, PF_RIGHT, PF_BOTTOM = 200, 24, 1080, 720
PF_W = PF_RIGHT - PF_LEFT
PF_H = PF_BOTTOM - PF_TOP
PF_CX = (PF_LEFT + PF_RIGHT) // 2

# Grille de briques
COLS = 13
BRICK_W, BRICK_H = 62, 24
BRICK_GAP = 4
PITCH_X = BRICK_W + BRICK_GAP
PITCH_Y = BRICK_H + BRICK_GAP
GRID_LEFT = PF_LEFT + (PF_W - (COLS * PITCH_X - BRICK_GAP)) // 2
GRID_TOP = PF_TOP + 56
MAX_ROWS = 13

# Raquette
PADDLE_Y = 664
PADDLE_H = 16
PADDLE_W = 112
PADDLE_W_WIDE = 176
PADDLE_W_NARROW = 70
PADDLE_KEY_SPEED = 1050.0

# Balle
BALL_R = 8
BALL_SPEED_START = 440.0
BALL_SPEED_LEVEL_STEP = 16.0
BALL_SPEED_HIT_STEP = 1.6
BALL_SPEED_MAX = 860.0
MAX_BALLS = 12

# Simulation à pas fixe (évite que la balle traverse les briques)
PHYSICS_DT = 1.0 / 240.0

# Décor synthwave
HORIZON = 400

START_LIVES = 3
MAX_LIVES = 7
EXTRA_LIFE_EVERY = 30000
