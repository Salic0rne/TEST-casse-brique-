"""Tests sans écran ni carte son :  python -m unittest discover -s tests -v"""

import math
import os
import sys
import tempfile
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
_TMP = tempfile.TemporaryDirectory()
os.environ["PRISMA_SAVE"] = os.path.join(_TMP.name, "save.json")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from casse_brique import config as C  # noqa: E402
from casse_brique.levels import LEVELS, get_level, parse_cell  # noqa: E402
from casse_brique.settings import Settings  # noqa: E402

APP = None


def setUpModule():
    global APP
    from casse_brique.app import App
    APP = App()


def tearDownModule():
    pygame.quit()
    _TMP.cleanup()


def new_game(level=0):
    from casse_brique.game import GameScene
    g = GameScene(APP, level)
    APP.scene = g
    return g


def step(n=1):
    for _ in range(n):
        APP.step(1.0 / 60.0, events=[])


class LevelTests(unittest.TestCase):
    def test_grids_are_well_formed(self):
        for i in range(len(LEVELS) + 12):
            name, rows = get_level(i)
            self.assertTrue(name)
            self.assertLessEqual(len(rows), C.MAX_ROWS, name)
            for row in rows:
                self.assertEqual(len(row), C.COLS, "%s: %r" % (name, row))
            cells = [parse_cell(ch, r, len(rows)) for r, row in enumerate(rows) for ch in row]
            destructible = [c for c in cells if c is not None and c[0] != 3]
            self.assertGreaterEqual(len(destructible), 20, name)

    def test_generator_is_deterministic(self):
        self.assertEqual(get_level(15), get_level(15))
        self.assertNotEqual(get_level(15)[1], get_level(16)[1])

    def test_bricks_stay_above_paddle(self):
        lowest = C.GRID_TOP + C.MAX_ROWS * C.PITCH_Y
        self.assertLess(lowest, C.PADDLE_Y - 150)


class SettingsTests(unittest.TestCase):
    def test_roundtrip_and_validation(self):
        path = os.path.join(_TMP.name, "s.json")
        s = Settings(path)
        s.best_score = 1234
        s.music_volume = 0.3
        s.crt = False
        s.save()
        s2 = Settings.load(path)
        self.assertEqual(s2.best_score, 1234)
        self.assertAlmostEqual(s2.music_volume, 0.3)
        self.assertFalse(s2.crt)
        with open(path, "w") as f:
            f.write('{"best_score": "beaucoup", "music_volume": 7, "crt": 1, "shake": false}')
        s3 = Settings.load(path)
        self.assertEqual(s3.best_score, 0)
        self.assertAlmostEqual(s3.music_volume, 0.6)
        self.assertTrue(s3.crt)
        self.assertFalse(s3.shake)
        with open(path, "w") as f:
            f.write("pas du json")
        self.assertEqual(Settings.load(path).best_score, 0)


class PhysicsTests(unittest.TestCase):
    def _clear_grid(self, g):
        for b in g.bricks:
            b.alive = False
        g.bricks, g.grid = [], {}

    def _add(self, g, col, row, kind_char):
        from casse_brique.entities import Brick
        kind, hue, sat, hp = parse_cell(kind_char, row, 10)
        b = Brick(col, row, kind, hue, sat, hp)
        b.appear = 1.0
        g.bricks.append(b)
        g.grid[(col, row)] = b
        return b

    def test_fast_ball_never_tunnels_through_metal(self):
        g = new_game(0)
        self._clear_grid(g)
        for c in range(C.COLS):
            self._add(g, c, 5, "@")
        g.remaining = 1
        g.set_state("play")
        row_bottom = C.GRID_TOP + 5 * C.PITCH_Y + C.BRICK_H
        for ang in np.linspace(-1.1, 1.1, 23):
            ball = g.balls[0]
            ball.stuck = False
            ball.x, ball.y = C.PF_CX + ang * 200, row_bottom + 120
            ball.speed = 1150.0
            ball.set_angle(ang, ball.speed)
            ball.trail.clear()
            bounced = False
            for _ in range(240):
                g.physics(C.PHYSICS_DT)
                self.assertGreaterEqual(ball.y - ball.r, row_bottom - 0.5, "tunnel à l'angle %.2f" % ang)
                if ball.vy > 0:
                    bounced = True
                    break
            self.assertTrue(bounced, "pas de rebond à l'angle %.2f" % ang)

    def test_seam_between_two_bricks_bounces_straight(self):
        g = new_game(0)
        self._clear_grid(g)
        left = self._add(g, 5, 4, "r")
        right = self._add(g, 6, 4, "r")
        g.remaining = 5
        g.set_state("play")
        ball = g.balls[0]
        ball.stuck = False
        seam_x = right.x - C.BRICK_GAP / 2
        ball.x, ball.y = seam_x, left.y + C.BRICK_H + 60
        ball.speed = 500.0
        ball.vx, ball.vy = 0.0, -500.0
        for _ in range(200):
            g.physics(C.PHYSICS_DT)
            if ball.vy > 0:
                break
        self.assertGreater(ball.vy, 0)
        self.assertLess(abs(ball.vx), 1e-6 + 500 * 0.3)

    def test_ball_stays_inside_playfield_during_long_game(self):
        g = new_game(0)
        step(160)
        self.assertEqual(g.state, "ready")
        g.input_mode = "mouse"
        g.launch()
        destroyed_before = g.total - g.remaining
        for i in range(60 * 45):
            balls = [b for b in g.balls if b.alive and not b.stuck]
            if balls:
                low = max(balls, key=lambda b: b.y)
                g.mouse_x = low.x + 26 * math.sin(i * 0.037)
            elif g.state == "ready":
                g.launch()
            step(1)
            for b in g.balls:
                self.assertGreaterEqual(b.x - b.r, C.PF_LEFT - 0.5)
                self.assertLessEqual(b.x + b.r, C.PF_RIGHT + 0.5)
                self.assertGreaterEqual(b.y - b.r, C.PF_TOP - 0.5)
                for br in g.bricks:
                    if br.alive:
                        inside = br.x < b.x < br.x + C.BRICK_W and br.y < b.y < br.y + C.BRICK_H
                        self.assertFalse(inside and not b.fire, "balle dans une brique")
            if g.state in ("clear", "gameover"):
                break
        self.assertGreater(g.total - g.remaining, destroyed_before + 10)
        self.assertGreater(g.score, 0)

    def test_bomb_chain_reaction(self):
        g = new_game(5)
        step(160)
        g.set_state("play")
        from casse_brique.sprites import BOMB
        bombs = [b for b in g.bricks if b.kind == BOMB]
        self.assertEqual(len(bombs), 7)
        g.damage(bombs[0], 99, "ball")
        for _ in range(90):
            step(1)
        self.assertTrue(all(not b.alive for b in bombs), "la réaction en chaîne doit tout faire sauter")
        self.assertGreaterEqual(g.best_chain, 20)

    def test_combo_multiplier_and_reset_on_paddle(self):
        g = new_game(0)
        step(160)
        g.set_state("play")
        targets = [b for b in g.bricks if b.alive][:13]
        for b in targets:
            g.destroy(b, "ball")
        self.assertEqual(g.chain, 13)
        self.assertEqual(g.multiplier(), 3)
        ball = g.balls[0]
        ball.stuck = False
        ball.x, ball.y = g.paddle.x, g.paddle.top - ball.r + 2
        ball.vx, ball.vy = 0.0, 300.0
        g.collide_paddle(ball)
        self.assertEqual(g.chain, 0)
        self.assertLess(ball.vy, 0)


class PowerupTests(unittest.TestCase):
    def test_every_powerup_can_be_collected(self):
        from casse_brique.entities import Capsule
        from casse_brique.sprites import POWERUPS
        g = new_game(0)
        step(160)
        g.launch()
        for k in POWERUPS:
            g.collect(Capsule(g.paddle.x, g.paddle.y, k))
            step(2)
        self.assertGreaterEqual(len(g.balls), 3)
        self.assertIn("L", g.effects)
        step(60 * 20)  # tous les effets temporaires expirent
        self.assertNotIn("G", g.effects)
        self.assertNotIn("P", g.effects)
        self.assertAlmostEqual(g.paddle.target_w, C.PADDLE_W)


class FlowTests(unittest.TestCase):
    def test_title_to_game_to_game_over(self):
        from casse_brique.scenes import TitleScene
        APP.scene = TitleScene(APP)
        step(30)
        APP.scene.on_action("down")
        APP.scene.on_action("confirm")      # options
        step(10)
        APP.scene.on_action("right")        # volume musique +
        APP.scene.on_action("back")
        APP.scene.on_action("up")
        APP.scene.on_action("confirm")      # jouer
        step(40)
        g = APP.scene
        self.assertEqual(type(g).__name__, "GameScene")
        step(160)
        g.on_action("pause")
        self.assertTrue(g.paused)
        step(10)
        g.on_action("back")
        self.assertFalse(g.paused)
        g.lives = 1
        g.launch()
        step(5)
        for b in g.balls:
            b.alive = False
        step(2)
        self.assertEqual(g.state, "dying")
        step(130)
        self.assertEqual(g.state, "gameover")
        step(90)
        self.assertIsNotNone(g.over_menu)

    def test_start_level_choice_and_intro_skip(self):
        from casse_brique.scenes import TitleScene
        APP.settings.best_level = 4
        APP.scene = TitleScene(APP)
        step(10)
        APP.scene.on_action("right")
        APP.scene.on_action("right")
        APP.scene.on_action("confirm")
        step(60)
        g = APP.scene
        self.assertEqual(g.level, 2)
        self.assertEqual(g.state, "intro")
        g.on_action("confirm")
        step(2)
        self.assertEqual(g.state, "ready")

    def test_abandoned_game_keeps_record(self):
        g = new_game(0)
        APP.settings.best_score = 10
        g.score = 4321
        g.commit_score()
        self.assertEqual(Settings.load().best_score, 4321)

    def test_level_clear_moves_to_next_level(self):
        g = new_game(0)
        step(160)
        g.set_state("play")
        for b in list(g.bricks):
            if b.alive and b.destructible:
                g.destroy(b, "ball")
        step(2)
        self.assertEqual(g.state, "clear")
        step(60 * 5)
        self.assertEqual(g.level, 1)
        self.assertEqual(g.state, "intro")


class AudioTests(unittest.TestCase):
    def test_sfx_are_finite_and_audible(self):
        from casse_brique import audio as A
        for name, (x, peak) in A.build_sfx().items():
            self.assertTrue(np.all(np.isfinite(x)), name)
            self.assertGreater(np.max(np.abs(x)), 1e-3, name)
            self.assertGreater(x.shape[0], 100, name)

    def test_music_loop_stems(self):
        from casse_brique import audio as A
        spec = A.TRACKS[1]
        stems, spectrum, step_len = A.generate_music(spec)
        n = step_len * 16 * len(spec["prog"])
        mix = sum(stems.values())
        for name, x in stems.items():
            self.assertEqual(x.shape, (n, 2), name)
            self.assertTrue(np.all(np.isfinite(x)), name)
            self.assertLess(abs(float(x.mean())), 0.01, name)
        self.assertLessEqual(float(np.max(np.abs(mix))), 0.93)
        self.assertEqual(spectrum.shape[1], 14)


if __name__ == "__main__":
    unittest.main()
