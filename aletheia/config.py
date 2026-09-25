"""Constantes globales, options persistantes et tableau des scores."""
import json
import os

# --- Résolution interne (pixel art) -------------------------------------
SCREEN_W, SCREEN_H = 480, 270
# Zone de jeu (verticale, au centre) et panneaux latéraux
PF_X, PF_Y = 112, 0
PF_W, PF_H = 256, 270
FPS = 60

TITLE = "ALETHEIA"
SUBTITLE = "LA CHUTE DE L'OLYMPE"

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".aletheia")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")
CACHE_DIR = os.path.join(SAVE_DIR, "cache")

DIFFICULTIES = [
    # nom, vitesse balles, densité, cadence, vies, continues
    {"name": "NYMPHE", "desc": "FACILE", "bspeed": 0.78, "density": 0.7, "rate": 0.72, "lives": 4, "continues": 9,
     "start_power": 2},
    {"name": "HÉROS", "desc": "NORMAL", "bspeed": 1.0, "density": 1.0, "rate": 1.0, "lives": 3, "continues": 5,
     "start_power": 1},
    {"name": "DEMI-DIEU", "desc": "DIFFICILE", "bspeed": 1.16, "density": 1.3, "rate": 1.22, "lives": 3, "continues": 3,
     "start_power": 0},
    {"name": "TITAN", "desc": "EXTRÊME", "bspeed": 1.3, "density": 1.6, "rate": 1.45, "lives": 2, "continues": 2,
     "start_power": 0},
]

# Progression : le feu ennemi se durcit de stade en stade (multiplie la vitesse des balles, leur densité,
# la cadence de tir et la résistance des boss de la difficulté choisie). Le premier stade est une mise en
# jambes ; la difficulté nominale est atteinte au quatrième, dépassée pour le final.
STAGE_RAMP = {
    1: {"bspeed": 0.8, "density": 0.62, "rate": 0.68, "hp": 0.78},
    2: {"bspeed": 0.87, "density": 0.72, "rate": 0.76, "hp": 0.88},
    3: {"bspeed": 0.93, "density": 0.84, "rate": 0.87, "hp": 0.95},
    4: {"bspeed": 0.98, "density": 0.95, "rate": 0.97, "hp": 1.0},
    5: {"bspeed": 1.02, "density": 1.02, "rate": 1.02, "hp": 1.0},
    6: {"bspeed": 1.06, "density": 1.08, "rate": 1.08, "hp": 1.0},
}

DEFAULT_OPTIONS = {
    "music": 7,
    "sfx": 8,
    "fullscreen": False,
    "crt": True,
    "shake": True,
    "bloom": True,
    "scale": 0,          # 0 = auto
    "difficulty": 1,
    "smooth": False,
}

DEFAULT_SCORES = [
    ("ZEU", 500000), ("HRA", 400000), ("ATH", 300000), ("APO", 200000), ("ART", 150000),
    ("POS", 100000), ("ARE", 80000), ("HEP", 60000), ("HER", 40000), ("DIO", 20000),
]


class Save:
    """Options + meilleurs scores, stockés en JSON dans ~/.aletheia."""

    def __init__(self):
        self.options = dict(DEFAULT_OPTIONS)
        self.scores = [list(s) for s in DEFAULT_SCORES]
        self.cleared = 0          # nombre de stades atteints (déverrouillage)
        self.load()

    def load(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.options.update({k: v for k, v in data.get("options", {}).items() if k in DEFAULT_OPTIONS})
            sc = data.get("scores")
            if isinstance(sc, list) and sc:
                self.scores = [[str(n)[:3], int(s)] for n, s in sc][:10]
            self.cleared = int(data.get("cleared", 0))
        except (OSError, ValueError, TypeError):
            pass

    def save(self):
        try:
            os.makedirs(SAVE_DIR, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump({"options": self.options, "scores": self.scores, "cleared": self.cleared}, f, indent=1)
        except OSError:
            pass

    @property
    def hiscore(self):
        return max(s for _, s in self.scores)

    def rank_of(self, score):
        for i, (_, s) in enumerate(self.scores):
            if score > s:
                return i
        return None

    def insert_score(self, name, score):
        r = self.rank_of(score)
        if r is None:
            return None
        self.scores.insert(r, [name[:3], int(score)])
        self.scores = self.scores[:10]
        self.save()
        return r
