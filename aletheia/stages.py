"""Metteur en scène (Director) et scripts des six stades."""
import random

from .entities import PF_W, PF_H
from . import enemies as E

LAST = 6

INFO = {
    1: {"num": "ΣΤΑΔΙΟΝ Α'", "name": "THALASSA", "sub": "LA MER DE POSÉIDON", "sub_short": "MER DE POSÉIDON"},
    2: {"num": "ΣΤΑΔΙΟΝ Β'", "name": "LABYRINTHOS", "sub": "LE DÉDALE DE KNOSSOS", "sub_short": "DÉDALE DE KNOSSOS"},
    3: {"num": "ΣΤΑΔΙΟΝ Γ'", "name": "GORGONEION", "sub": "LA NUÉE DE MÉDUSE", "sub_short": "NUÉE DE MÉDUSE"},
    4: {"num": "ΣΤΑΔΙΟΝ Δ'", "name": "HEPHAISTEION", "sub": "LA FORGE D'IO", "sub_short": "FORGE D'IO"},
    5: {"num": "ΣΤΑΔΙΟΝ Ε'", "name": "TARTAROS", "sub": "LES ENFERS DU TROU NOIR", "sub_short": "LES ENFERS"},
    6: {"num": "ΣΤΑΔΙΟΝ ΣΤ'", "name": "OLYMPOS", "sub": "LA CITADELLE DES DIEUX", "sub_short": "CITADELLE DIVINE"},
}
MUSIC = {1: "stage1", 2: "stage2", 3: "stage3", 4: "stage4", 5: "stage5", 6: "stage6"}


class Director:
    """Exécute un script-générateur : `yield n` attend n images, `yield fonction` attend une condition."""

    def __init__(self, w, script):
        self.w = w
        self.gen = script(w, self)
        self.wait = 0
        self.cond = None
        self.done = False
        self.subs = []

    def update(self):
        # sous-scripts parallèles
        keep = []
        for g in self.subs:
            try:
                next(g)
                keep.append(g)
            except StopIteration:
                pass
        self.subs = keep
        if self.done:
            return
        if self.cond is not None:
            if not self.cond():
                return
            self.cond = None
        if self.wait > 0:
            self.wait -= 1
            return
        try:
            r = next(self.gen)
            if isinstance(r, (int, float)):
                self.wait = max(0, int(r) - 1)
            elif callable(r):
                self.cond = r
        except StopIteration:
            self.done = True

    def parallel(self, gen):
        self.subs.append(gen)

    # --- aides ------------------------------------------------------------------------
    def spawn(self, cls, x, y, **kw):
        return self.w.spawn(cls(self.w, x, y, **kw))

    def squad(self, cls, n, gap, fn):
        """Escadrille : fn(i) -> dict (x, y, …)."""
        out = []
        for i in range(n):
            kw = fn(i)
            x = kw.pop("x")
            y = kw.pop("y")
            out.append(self.spawn(cls, x, y, **kw))
            yield gap
        return out

    def wait_clear(self, maxt=600):
        t0 = self.w.t
        return lambda: (not any(not e.dead and not e.BOSSPART for e in self.w.enemies)) or self.w.t - t0 > maxt

    def boss_fight(self, boss_cls, warn=True):
        w = self.w
        if warn:
            w.warning()
            yield 210
        b = boss_cls(w)
        w.spawn(b)
        w.set_boss(b)
        if b.MUSIC and not b.MID:
            w.audio.play_music(b.MUSIC, 300)
        yield lambda: b.dead or b.gone
        return b

    def midboss(self, boss_cls):
        w = self.w
        b = boss_cls(w)
        w.spawn(b)
        w.set_boss(b)
        w.audio.play("roar", PF_W / 2, 0.7)
        yield lambda: b.dead or b.gone
        yield 60
        w.boss = None
        return b


# ---------------------------------------------------------------------------
# Motifs de trajectoires
# ---------------------------------------------------------------------------
def arc_path(side, y0=-10, depth=150):
    """Arc depuis un bord supérieur vers l'autre côté."""
    if side < 0:
        return [(-10, y0 + 30), (60, depth * 0.5), (150, depth), (PF_W + 20, depth * 0.7)]
    return [(PF_W + 10, y0 + 30), (PF_W - 60, depth * 0.5), (PF_W - 150, depth), (-20, depth * 0.7)]


def swoop(x0, down=170):
    """Piqué : descend puis remonte en boucle."""
    d = 1 if x0 < PF_W / 2 else -1
    return [(x0, -12), (x0 + d * 20, down * 0.6), (x0 + d * 70, down), (x0 + d * 120, down * 0.5), (x0 + d * 140, -30)]


# ---------------------------------------------------------------------------
# STADE I — THALASSA
# ---------------------------------------------------------------------------
def boss_only(w):
    a = w.app.args
    return bool(a is not None and getattr(a, "boss", False))


def stage1(w, d):
    from .bosses import Ketos
    if not boss_only(w):
        yield from stage1_waves(w, d)
    w.bg.set_speed(0.35, 0.004)
    yield 60
    # --- BOSS : KÉTOS ---
    yield from d.boss_fight(Ketos)
    yield 150
    w.stage_clear()


def stage1_waves(w, d):
    from .bosses import Skylla
    bg = w.bg
    bg.set_speed(0.6)
    bg.spawn_island(0, 70)
    yield 70
    # vague 1 : escadrilles de Myrmex en arc
    yield from d.squad(E.Myrmex, 6, 9, lambda i: dict(x=-10, y=40, path=arc_path(-1, depth=140), dur=170,
                                                        fire=90 if i % 2 else None))
    yield 40
    yield from d.squad(E.Myrmex, 6, 9, lambda i: dict(x=PF_W + 10, y=40, path=arc_path(1, depth=120), dur=170,
                                                        fire=90 if i % 2 == 0 else None))
    yield 30
    # le premier messager divin
    d.spawn(E.Hermes, -12, 60, side=1, y0=58, drop="orb")
    yield 60
    for x in (60, 196):
        d.spawn(E.Myrmex, x, -10, dive=60, speed=2.6)
        yield 12
    yield 50
    bg.spawn_island(1, 180)
    for i in range(4):
        side = -1 if i % 2 == 0 else 1
        d.spawn(E.Harpy, PF_W / 2 - side * 90, -12, path=swoop(PF_W / 2 - side * 90))
        yield 28
    yield 40
    # île fortifiée : tourelles cyclopes
    sc = bg.spawn_island(2, 90)
    for dx, dy in ((-24, -8), (20, 6), (-4, 20)):
        d.spawn(E.Cyclops, 90 + dx, sc.y + dy)
    yield 60
    d.spawn(E.Hermes, PF_W + 12, 80, side=-1, y0=80, drop="p")
    yield 40
    yield from d.squad(E.Myrmex, 8, 7, lambda i: dict(x=30 + i * 28, y=-10, vy=1.6, sine=14, fire=70 if i % 3 == 0
                                                        else None))
    yield 60
    # champ de jarres de Pandore
    for i in range(8):
        d.spawn(E.Pithos, random.uniform(30, PF_W - 30), -12, vy=0.75)
        yield 16
    yield 40
    d.spawn(E.Stymphalian, 70, -14, tx=70, ty=60)
    d.spawn(E.Stymphalian, 186, -14, tx=186, ty=74)
    yield 80
    yield from d.squad(E.Myrmex, 6, 10, lambda i: dict(x=-10, y=100, path=[(-10, 100), (80, 60), (180, 90),
                                                                             (PF_W + 20, 40)], dur=150))
    yield d.wait_clear(300)
    # trirème escortée
    d.spawn(E.Trireme, PF_W / 2, -40, ty=66)
    yield 100
    for i in range(4):
        d.spawn(E.Harpy, 20 if i % 2 == 0 else PF_W - 20, -12, path=swoop(20 if i % 2 == 0 else PF_W - 20, 150))
        yield 40
    bg.show_statue(150)
    yield 120
    d.spawn(E.Hermes, -12, 50, side=1, y0=50, drop="orb")
    yield d.wait_clear(400)
    for x in (70, 186):
        d.spawn(E.Siren, x, -16, tx=x, ty=60, rings=3)
    yield 60
    yield from d.squad(E.Myrmex, 5, 12, lambda i: dict(x=PF_W / 2 + (i - 2) * 30, y=-10, dive=50 + i * 6))
    yield d.wait_clear(400)
    yield 40
    # --- GARDIENNE : SKYLLA ---
    yield from d.midboss(Skylla)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 60
    bg.spawn_island(0, 180)
    sc = bg.spawn_island(1, 70)
    for dx, dy in ((-14, -4), (16, 10)):
        d.spawn(E.Cyclops, 70 + dx, sc.y + dy, rate=90)
    yield 40
    # phalange d'hoplites
    for i in range(4):
        d.spawn(E.Hoplite, 50 + i * 52, -16, vy=0.7)
    yield 120
    yield from d.squad(E.Myrmex, 8, 8, lambda i: dict(x=PF_W + 10, y=30, path=arc_path(1, depth=180), dur=180,
                                                        fire=80 if i % 2 else None))
    yield 60
    d.spawn(E.Hermes, PF_W + 12, 70, side=-1, y0=70, drop="p")
    for i in range(6):
        d.spawn(E.Pithos, 20 + i * 43, -12, vy=0.9)
        yield 10
    yield 60
    d.spawn(E.Trireme, 80, -40, ty=60, stay=300)
    yield 60
    d.spawn(E.Stymphalian, 200, -14, tx=200, ty=90)
    yield 90
    yield from d.squad(E.Harpy, 6, 20, lambda i: dict(x=20 + (i % 2) * 216, y=-12,
                                                       path=swoop(20 + (i % 2) * 216, 160)))
    yield d.wait_clear(500)
    # dernier assaut
    for k in range(3):
        yield from d.squad(E.Myrmex, 7, 6, lambda i: dict(x=20 + i * 36, y=-10, dive=40 + (i % 3) * 16, speed=3.0))
        yield 50
    d.spawn(E.Hermes, -12, 70, side=1, y0=70, drop="bomb")
    yield d.wait_clear(400)


# ---------------------------------------------------------------------------
# STADE II — LABYRINTHOS
# ---------------------------------------------------------------------------
def stage2(w, d):
    from .bosses2 import Minotauros
    if not boss_only(w):
        yield from stage2_waves(w, d)
    w.bg.set_speed(0.4, 0.004)
    yield 60
    yield from d.boss_fight(Minotauros)
    yield 150
    w.stage_clear()


def stage2_waves(w, d):
    from .bosses2 import Daidalos
    bg = w.bg
    bg.set_speed(0.7)
    yield 70
    for x in (44, 212):
        d.spawn(E.WallGun, x, -12)
    yield 30
    yield from d.squad(E.Myrmex, 6, 8, lambda i: dict(x=PF_W / 2 + (i - 2.5) * 24, y=-10, vy=1.9, sine=22,
                                                        fire=60 if i % 2 else None))
    yield 40
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="orb")
    yield 60
    for i in range(3):
        d.spawn(E.Bull, 50 + i * 78, -14, ty=40 + (i % 2) * 22)
        yield 30
    yield 50
    for x in (64, 128, 192):
        d.spawn(E.WallGun, x, -12, rate=110)
    yield 20
    yield from d.squad(E.Myrmex, 8, 7, lambda i: dict(x=-10, y=40, path=arc_path(-1, depth=160), dur=160,
                                                        fire=70 if i % 3 == 0 else None))
    yield 40
    d.spawn(E.Centaur, 60, -14, vx=0.5)
    d.spawn(E.Centaur, 196, -14, vx=-0.5)
    yield 90
    for i in range(5):
        d.spawn(E.Hoplite, 28 + i * 50, -16, vy=0.75)
    yield 110
    d.spawn(E.Hermes, PF_W + 12, 70, side=-1, y0=70, drop="p")
    for x in (72, 184):
        d.spawn(E.Siren, x, -16, tx=x, ty=62, rings=3)
    yield 60
    yield from d.squad(E.Harpy, 4, 26, lambda i: dict(x=20 + (i % 2) * 216, y=-12, path=swoop(20 + (i % 2) * 216)))
    yield d.wait_clear(500)
    yield 30
    yield from d.midboss(Daidalos)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 80
    for i in range(5):
        d.spawn(E.Bull, 30 + i * 49, -14, ty=30 + (i % 3) * 16)
        yield 20
    yield 50
    for x in (36, 220):
        d.spawn(E.WallGun, x, -12, rate=90)
    yield from d.squad(E.Myrmex, 7, 8, lambda i: dict(x=24 + i * 34, y=-10, dive=46 + (i % 2) * 20, speed=2.8))
    yield 50
    for i in range(10):
        d.spawn(E.Pithos, 20 + (i * 53) % 216, -12, vy=0.9)
        yield 12
    yield 30
    d.spawn(E.Stymphalian, 60, -14, tx=60, ty=70)
    d.spawn(E.Stymphalian, 128, -14, tx=128, ty=54)
    d.spawn(E.Stymphalian, 196, -14, tx=196, ty=70)
    yield 120
    d.spawn(E.Centaur, 40, -14, vx=0.6)
    d.spawn(E.Centaur, 128, -30, vx=-0.4)
    d.spawn(E.Centaur, 216, -14, vx=-0.6)
    d.spawn(E.Hermes, -12, 50, side=1, y0=50, drop="bomb")
    yield 100
    yield from d.squad(E.Myrmex, 10, 6, lambda i: dict(x=PF_W + 10, y=30, path=arc_path(1, depth=200), dur=170,
                                                         fire=80 if i % 2 else None))
    yield 40
    for i in range(4):
        d.spawn(E.Hoplite, 50 + i * 52, -16, vy=0.9)
    yield 60
    d.spawn(E.Hermes, PF_W + 12, 60, side=-1, y0=60, drop="orb")
    yield d.wait_clear(500)


# ---------------------------------------------------------------------------
# STADE III — GORGONEION
# ---------------------------------------------------------------------------
def rock_rain(d, n, gap, big=0.2):
    for i in range(n):
        size = "l" if random.random() < big else random.choice(("s", "m", "m"))
        x = random.uniform(10, PF_W - 10)
        d.spawn(E.Asteroid, x, -18, size=size, vx=random.uniform(-0.5, 0.5), vy=random.uniform(0.7, 1.4))
        yield gap


def stage3(w, d):
    from .bosses2 import Medusa
    if not boss_only(w):
        yield from stage3_waves(w, d)
    w.bg.set_speed(0.4, 0.004)
    yield 60
    yield from d.boss_fight(Medusa)
    yield 150
    w.stage_clear()


def stage3_waves(w, d):
    from .bosses2 import Graiai
    bg = w.bg
    bg.set_speed(0.7)
    yield 60
    yield from rock_rain(d, 8, 22)
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="orb")
    yield from d.squad(E.Myrmex, 6, 9, lambda i: dict(x=-10, y=50, path=arc_path(-1, depth=150), dur=160))
    yield 40
    for x in (60, 196):
        d.spawn(E.GorgonEye, x, -14, vy=0.45)
    yield 90
    yield from rock_rain(d, 6, 18, 0.35)
    yield 30
    d.spawn(E.Serpent, 40, -20, path=[(40, -20), (60, 90), (200, 130), (60, 190), (140, 320)], dur=460, segs=10)
    yield 160
    d.spawn(E.Hermes, PF_W + 12, 80, side=-1, y0=80, drop="p")
    for i in range(4):
        d.spawn(E.Harpy, PF_W / 2 + (-1) ** i * 90, -12, path=swoop(PF_W / 2 + (-1) ** i * 90), col="green")
        yield 30
    yield 60
    bg.show_statue(160)
    for x in (80, 176):
        d.spawn(E.Siren, x, -16, tx=x, ty=66, rings=4)
    yield 90
    yield from rock_rain(d, 10, 16, 0.25)
    yield d.wait_clear(500)
    yield 30
    yield from d.midboss(Graiai)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 60
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="oneup")
    for x in (40, 128, 216):
        d.spawn(E.GorgonEye, x, -14, vy=0.5, period=170)
        yield 20
    yield 60
    d.spawn(E.Serpent, 216, -20, path=[(216, -20), (190, 80), (60, 110), (200, 180), (100, 320)], dur=440, segs=12)
    yield 60
    d.spawn(E.Serpent, 40, -20, path=[(40, -20), (70, 70), (200, 90), (50, 160), (160, 320)], dur=420, segs=9)
    yield 120
    yield from d.squad(E.Stymphalian, 3, 30, lambda i: dict(x=60 + i * 68, y=-14, tx=60 + i * 68, ty=60 + (i % 2) * 20))
    yield 80
    yield from rock_rain(d, 10, 14, 0.3)
    d.spawn(E.Hermes, PF_W + 12, 60, side=-1, y0=60, drop="p")
    yield from d.squad(E.Myrmex, 10, 7, lambda i: dict(x=20 + (i % 5) * 54, y=-10, dive=40 + (i // 5) * 30, speed=3.0))
    yield d.wait_clear(500)


# ---------------------------------------------------------------------------
# STADE IV — HEPHAISTEION
# ---------------------------------------------------------------------------
def stage4(w, d):
    from .bosses3 import Talos
    if not boss_only(w):
        yield from stage4_waves(w, d)
    w.bg.set_speed(0.35, 0.004)
    yield 60
    yield from d.boss_fight(Talos)
    yield 150
    w.stage_clear()


def stage4_waves(w, d):
    from .bosses3 import Kyklopes
    bg = w.bg
    bg.set_speed(0.75)
    yield 60
    for x in (50, 206):
        d.spawn(E.LavaDrone, x, PF_H + 12, tx=x, ty=90)
        yield 20
    yield 40
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="orb")
    for x in (70, 186):
        d.spawn(E.HammerBot, x, -14, vx=0.3 if x < 128 else -0.3)
    yield 60
    yield from d.squad(E.Myrmex, 8, 7, lambda i: dict(x=PF_W + 10, y=40, path=arc_path(1, depth=150), dur=160,
                                                        fire=70 if i % 2 else None))
    yield 40
    for x in (40, 128, 216):
        d.spawn(E.Cyclops, x, -12, rate=95)
    yield 60
    for i in range(4):
        d.spawn(E.LavaDrone, 30 + i * 65, PF_H + 12, tx=30 + i * 65, ty=70 + (i % 2) * 30)
        yield 16
    yield 80
    for i in range(3):
        d.spawn(E.Bull, 60 + i * 68, -14, ty=36 + i * 10)
        yield 28
    d.spawn(E.Hermes, PF_W + 12, 70, side=-1, y0=70, drop="p")
    yield 60
    d.spawn(E.Stymphalian, 70, -14, tx=70, ty=64)
    d.spawn(E.Stymphalian, 186, -14, tx=186, ty=64)
    yield 60
    d.spawn(E.Centaur, 60, -14, vx=0.5)
    d.spawn(E.Centaur, 196, -14, vx=-0.5)
    yield d.wait_clear(500)
    yield 30
    yield from d.midboss(Kyklopes)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 60
    for x in (40, 216):
        d.spawn(E.HammerBot, x, -14, vx=0.35 if x < 128 else -0.35)
    yield from d.squad(E.Myrmex, 8, 7, lambda i: dict(x=-10, y=30, path=arc_path(-1, depth=190), dur=170))
    yield 30
    for i in range(6):
        d.spawn(E.LavaDrone, 20 + (i * 47) % 216, PF_H + 12, tx=20 + (i * 47) % 216, ty=60 + (i % 3) * 25)
        yield 18
    yield 60
    for x in (50, 128, 206):
        d.spawn(E.Cyclops, x, -12, rate=80, burst=4)
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="bomb")
    yield 90
    for i in range(5):
        d.spawn(E.Hoplite, 28 + i * 50, -16, vy=0.8)
    yield 90
    yield from d.squad(E.Harpy, 6, 18, lambda i: dict(x=20 + (i % 2) * 216, y=-12, path=swoop(20 + (i % 2) * 216, 170),
                                                       col="orange"))
    yield 40
    d.spawn(E.Hermes, PF_W + 12, 60, side=-1, y0=60, drop="orb")
    yield d.wait_clear(500)


# ---------------------------------------------------------------------------
# STADE V — TARTAROS
# ---------------------------------------------------------------------------
def stage5(w, d):
    from .bosses3 import Kerberos
    if not boss_only(w):
        yield from stage5_waves(w, d)
    w.bg.set_speed(0.4, 0.004)
    yield 60
    yield from d.boss_fight(Kerberos)
    yield 150
    w.stage_clear()


def stage5_waves(w, d):
    from .bosses3 import Charon
    bg = w.bg
    bg.set_speed(0.7)
    yield 60
    for i in range(4):
        d.spawn(E.Shade, 40 + i * 58, -14, vy=0.55)
        yield 20
    yield 40
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="orb")
    for i in range(3):
        d.spawn(E.Erinys, 60 + i * 68, -14, ty=50 + (i % 2) * 20)
        yield 24
    yield 60
    d.spawn(E.Serpent, 128, -20, path=[(128, -20), (40, 80), (216, 140), (40, 200), (128, 320)], dur=480, segs=12)
    yield 120
    for i in range(8):
        d.spawn(E.Pithos, 20 + (i * 67) % 216, -12, vy=0.85, burst=10)
        yield 12
    yield 40
    for x in (70, 186):
        d.spawn(E.GorgonEye, x, -14, vy=0.45)
    d.spawn(E.Hermes, PF_W + 12, 70, side=-1, y0=70, drop="p")
    yield 90
    for i in range(6):
        d.spawn(E.Shade, 20 + i * 43, -14, vy=0.6)
        yield 14
    yield 30
    for i in range(4):
        d.spawn(E.Erinys, 30 + i * 65, -14, ty=40 + (i % 2) * 30)
        yield 20
    yield d.wait_clear(500)
    yield 30
    yield from d.midboss(Charon)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 60
    # --- chute vers l'Érèbe : section à grande vitesse (façon Super Aleste) ---
    w.banner("CHUTE VERS L'ÉRÈBE", (190, 150, 255), 130)
    w.audio.play("teleport", PF_W / 2, 0.8)
    bg.set_speed(2.8, 0.04)
    yield 60
    for k in range(9):
        side = -1 if k % 2 else 1
        for i in range(4):
            d.spawn(E.Myrmex, PF_W / 2 + side * (20 + i * 22), -12, vy=3.4 + i * 0.2, fire=18 if i == 1 else None)
        if k % 3 == 2:
            d.spawn(E.Pithos, random.uniform(30, PF_W - 30), -14, vy=2.6, burst=8)
        yield 44
    bg.set_speed(0.7, 0.03)
    yield 60
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="oneup")
    for x in (64, 192):
        d.spawn(E.Siren, x, -16, tx=x, ty=60, rings=4)
    yield 80
    d.spawn(E.Serpent, 40, -20, path=[(40, -20), (200, 70), (40, 130), (200, 190), (60, 320)], dur=460, segs=12)
    d.spawn(E.Serpent, 216, -60, path=[(216, -60), (60, 40), (216, 110), (60, 170), (190, 320)], dur=480, segs=10)
    yield 150
    for i in range(5):
        d.spawn(E.Erinys, 26 + i * 51, -14, ty=36 + (i % 2) * 24)
        yield 16
    yield 60
    for i in range(8):
        d.spawn(E.Shade, 16 + i * 32, -14, vy=0.6)
        yield 10
    d.spawn(E.Hermes, PF_W + 12, 60, side=-1, y0=60, drop="bomb")
    yield 80
    yield from d.squad(E.Myrmex, 10, 6, lambda i: dict(x=-10, y=40, path=arc_path(-1, depth=210), dur=170,
                                                         fire=60 if i % 2 else None))
    yield d.wait_clear(500)


# ---------------------------------------------------------------------------
# STADE VI — OLYMPOS
# ---------------------------------------------------------------------------
def pylon_pair(d, x0, x1, y=-14):
    a = d.spawn(E.Pylon, x0, y)
    b = d.spawn(E.Pylon, x1, y, twin=a)
    a.twin = b
    return a, b


def stage6(w, d):
    from .bosses3 import Zeus
    if not boss_only(w):
        yield from stage6_waves(w, d)
    w.bg.set_speed(0.5, 0.004)
    w.bg.storm = True
    yield 60
    yield from d.boss_fight(Zeus)
    yield 200
    w.stage_clear()


def stage6_waves(w, d):
    from .bosses3 import Nike
    bg = w.bg
    bg.set_speed(0.8)
    yield 60
    for i in range(2):
        d.spawn(E.Eagle, 40 + i * 176, -20)
        yield 30
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="orb")
    yield 60
    pylon_pair(d, 40, 216)
    yield 50
    yield from d.squad(E.Harpy, 6, 18, lambda i: dict(x=20 + (i % 2) * 216, y=-12, path=swoop(20 + (i % 2) * 216, 170),
                                                       col="gold"))
    yield 60
    for i in range(5):
        d.spawn(E.Hoplite, 28 + i * 50, -16, vy=0.85)
    yield 60
    d.spawn(E.Trireme, PF_W / 2, -40, ty=70, stay=360)
    yield 120
    d.spawn(E.Hermes, PF_W + 12, 80, side=-1, y0=80, drop="p")
    for i in range(3):
        d.spawn(E.Eagle, PF_W / 2 + (i - 1) * 70, -20, path=[(PF_W / 2 + (i - 1) * 70, -20), (PF_W / 2 + (i - 1) * 40, 90),
                                                             (PF_W / 2 - (i - 1) * 80, 140), (PF_W / 2 - (i - 1) * 120, -30)])
        yield 30
    yield 60
    pylon_pair(d, 30, 128)
    pylon_pair(d, 150, 226, -40)
    yield 60
    for x in (64, 192):
        d.spawn(E.Siren, x, -16, tx=x, ty=60, rings=4)
    yield d.wait_clear(500)
    yield 30
    yield from d.midboss(Nike)
    w.drop_items(PF_W / 2, 60, "orb", 1)
    yield 60
    d.spawn(E.Hermes, -12, 60, side=1, y0=60, drop="bomb")
    yield from d.squad(E.Myrmex, 10, 6, lambda i: dict(x=PF_W + 10, y=40, path=arc_path(1, depth=200), dur=170,
                                                         fire=60 if i % 2 else None))
    yield 40
    for i in range(3):
        d.spawn(E.Stymphalian, 60 + i * 68, -14, tx=60 + i * 68, ty=56 + (i % 2) * 24)
    yield 80
    pylon_pair(d, 50, 206)
    for i in range(4):
        d.spawn(E.Erinys, 30 + i * 65, -14, ty=40 + (i % 2) * 30)
        yield 18
    yield 60
    d.spawn(E.Trireme, 70, -40, ty=60, stay=300)
    d.spawn(E.Trireme, 186, -90, ty=90, stay=280)
    yield 120
    for i in range(4):
        d.spawn(E.Eagle, 30 + i * 65, -20)
        yield 24
    d.spawn(E.Hermes, PF_W + 12, 60, side=-1, y0=60, drop="orb")
    yield 60
    for i in range(6):
        d.spawn(E.Hoplite, 24 + i * 42, -16, vy=0.9)
    yield d.wait_clear(600)


SCRIPTS = {1: stage1, 2: stage2, 3: stage3, 4: stage4, 5: stage5, 6: stage6}
