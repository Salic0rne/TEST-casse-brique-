"""Scène de jeu : le monde (joueur, ennemis, balles, objets, effets), le score « Kléos »,
le déroulé d'un stade (intro, combat, boss, bilan), continues et fin de partie."""
import math
import random

import pygame

from . import palette as P
from . import config as C
from .config import PF_X, PF_W, PF_H, DIFFICULTIES
from .sprites import S
from .fx import FX, Juice, Particle, K_GLOW, K_FLARE, K_RING, K_TEXT, glow
from .entities import Bullets
from .player import Player
from .items import Item
from . import font as F
from .util import clamp, lerp, ease_out_cubic, ease_out_back, TAU


class Score:
    THRESH = (0, 10, 25, 45, 70, 100, 140, 190)

    def __init__(self, w):
        self.w = w
        self.score = 0
        self.chain = 0
        self.timer = 0
        self.mult = 1
        self.max_chain = 0
        self.kills = 0
        self.stage_kills = 0
        self.coins = 0
        self.next_extend_i = 0
        self.extends = (200000, 500000, 1000000, 2000000, 4000000)
        self.pulse = 0

    def touch(self):
        if self.chain > 0:
            self.timer = max(self.timer, 50)

    def kill(self, e):
        self.chain += 1
        self.timer = 125
        self.max_chain = max(self.max_chain, self.chain)
        self.kills += 1
        self.stage_kills += 1
        m = 1
        for i, th in enumerate(self.THRESH):
            if self.chain >= th:
                m = i + 1
        if m > self.mult:
            self.w.audio.play("chain")
            self.pulse = 30
            self.w.popup(e.x, e.y - 14, f"KLÉOS ×{m}", (255, 220, 120), 45)
        self.mult = m
        gain = self.add(e.SCORE, e.x, e.y, popup=False)
        if e.SCORE >= 500:
            self.w.popup_tiny(e.x, e.y, str(gain), (255, 240, 200))

    def add(self, pts, x=None, y=None, popup=True):
        gain = int(pts * self.mult)
        self.score += gain
        if popup and x is not None:
            self.w.popup_tiny(x, y, str(gain), (255, 240, 200))
        self.check_extend()
        return gain

    def check_extend(self):
        if self.next_extend_i < len(self.extends) and self.score >= self.extends[self.next_extend_i]:
            self.next_extend_i += 1
            w = self.w
            w.player.lives += 1
            w.audio.play("oneup")
            w.banner("VIE SUPPLÉMENTAIRE !", (170, 255, 150), 90)

    def dmg_points(self, dmg):
        # les coups portés aux boss rapportent aussi (10 pts par point de dégât)
        self.acc = getattr(self, "acc", 0.0) + dmg * 10
        if self.acc >= 10:
            n = int(self.acc)
            self.acc -= n
            self.score += n * self.mult
            self.check_extend()

    def break_chain(self, half=False):
        if half:
            self.chain //= 2
        else:
            self.chain = 0
        m = 1
        for i, th in enumerate(self.THRESH):
            if self.chain >= th:
                m = i + 1
        self.mult = m

    def update(self):
        if self.pulse > 0:
            self.pulse -= 1
        if self.chain > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.chain = 0
                self.mult = 1


class Game:
    """Le monde de jeu ; piloté par la scène GameScene."""

    def __init__(self, app, stage=1, difficulty=None):
        self.app = app
        self.audio = app.audio
        self.save = app.save
        self.post = app.post
        di = self.save.options["difficulty"] if difficulty is None else difficulty
        self.diff_i = di
        self.diff = dict(DIFFICULTIES[di])
        self.cheat = app.args.invincible if app.args else False
        self.fx = FX()
        self.juice = Juice()
        self.juice.enabled = self.save.options.get("shake", True)
        self.frame = pygame.Surface((PF_W, PF_H)).convert()
        self.add = pygame.Surface((PF_W, PF_H)).convert()
        self.score = Score(self)
        self.player = Player(self, self.diff["lives"])
        self.bullets = Bullets(self)
        self.enemies = []
        self.shots = []
        self.items = []
        self.hazards = []
        self.targets = []
        self.t = 0
        self.stage_n = stage
        self.bg = None
        self.director = None
        self.boss = None
        self.boss_show = 0.0
        self.banners = []
        self.continues = self.diff["continues"]
        self.state = "intro"
        self.state_t = 0
        self.warning_t = 0
        self.hud_flash_weapon = 0
        self.player_dead_pause = False
        self.no_miss = True
        self.stage_start_score = 0
        self.tally = None
        self.gameover = False
        self.load_stage(stage)
        a = app.args
        if a is not None:
            if getattr(a, "power", 0):
                self.player.power = max(0, min(5, a.power))
            if getattr(a, "weapon", None) in ("zeus", "apollo", "artemis", "poseidon", "athena", "hephaestus"):
                self.player.set_weapon(a.weapon)

    # ------------------------------------------------------------------
    @property
    def scroll(self):
        return self.bg.scroll if self.bg else 0.0

    def load_stage(self, n):
        from . import backgrounds, stages
        self.stage_n = n
        self.enemies.clear()
        self.shots.clear()
        self.items.clear()
        self.hazards.clear()
        self.bullets.clear()
        self.fx.clear()
        self.boss = None
        self.boss_show = 0.0
        self.bg = backgrounds.make(n, self)
        self.director = stages.Director(self, stages.SCRIPTS[n])
        self.state = "intro"
        self.state_t = 0
        self.no_miss = True
        self.score.stage_kills = 0
        self.stage_start_score = self.score.score
        self.stage_spawned = 0
        p = self.player
        p.x, p.y = PF_W / 2, PF_H + 30
        p.control = False
        p.invuln = 0
        self.audio.play_music(stages.MUSIC[n], 1200)
        self.audio.play("stage")

    def player_enter(self):
        self.enter_t = 0
        self.state_enter = True

    # --- créations ------------------------------------------------------
    def spawn(self, e):
        self.enemies.append(e)
        if not e.BOSSPART:
            self.stage_spawned += 1
        return e

    def add_shot(self, s):
        self.shots.append(s)
        return s

    def drop_items(self, x, y, kind, n=1, vx=None, vy=None):
        for i in range(n):
            if kind == "orb":
                self.items.append(Item(self, x, y, "orb"))
            else:
                self.items.append(Item(self, x + random.uniform(-4, 4), y + random.uniform(-4, 4), kind,
                                       vx=vx if vx is not None else None, vy=vy if vy is not None else None))

    def drop_coins(self, x, y, n):
        for i in range(n):
            self.items.append(Item(self, x + random.uniform(-5, 5), y + random.uniform(-5, 5), "coin"))

    def spawn_spark(self, x, y):
        if len(self.items) < 500:
            self.items.append(Item(self, x, y, "spark"))

    def popup(self, x, y, text, col=(255, 255, 255), life=40):
        img = F.FONT.render(text, col, outline=(10, 6, 22))
        x = clamp(x, img.get_width() // 2 + 2, PF_W - img.get_width() // 2 - 2)
        self.fx.text(x, y, img, life, -0.5)

    def popup_tiny(self, x, y, text, col=(255, 255, 255)):
        img = F.TINY.render(text, col)
        self.fx.text(x, y, img, 30, -0.7)

    def banner(self, text, col=(255, 255, 255), life=120, sub=None):
        self.banners.append([text, col, life, life, sub])

    # --- requêtes pour les armes --------------------------------------------
    def nearest_target(self, x, y, maxd=9999):
        best, bd = None, maxd * maxd
        for e in self.targets:
            if e.dead or e.armored():
                continue
            d = (e.x - x) ** 2 + (e.y - y) ** 2
            if d < bd:
                bd, best = d, e
        return best

    def random_target(self):
        ts = [e for e in self.targets if not e.dead and not e.armored()]
        return random.choice(ts) if ts else None

    def vline_hit(self, e, x, hw, ymax):
        """Point le plus bas où la verticale (x ± hw), au-dessus de ymax, touche l'ennemi."""
        if e.dead:
            return None
        if e.hitboxes:
            best = None
            for (dx, dy, bw, bh) in e.hitboxes:
                if abs(x - (e.x + dx)) < bw + hw and e.y + dy - bh < ymax:
                    yb = min(ymax, e.y + dy + bh)
                    if best is None or yb > best:
                        best = yb
            return best
        if abs(x - e.x) < e.RADIUS + hw and e.y - e.RADIUS < ymax:
            return min(ymax, e.y + e.RADIUS * 0.6)
        return None

    def segment_hits_boxes(self, e, x0, y0, dx, dy, hw):
        if not e.hitboxes:
            return False
        for (bx, by, bw, bh) in e.hitboxes:
            cx, cy = e.x + bx - x0, e.y + by - y0
            proj = cx * dx + cy * dy
            if proj < 0:
                continue
            perp = abs(cx * dy - cy * dx)
            if perp < max(bw, bh) + hw:
                return True
        return False

    def area_damage(self, x, y, r, dmg, silent=False):
        for e in self.targets:
            if not e.dead and e.collide(x, y, r):
                e.hit(dmg, e.x, e.y, silent=silent)

    # --- joueur -------------------------------------------------------------------
    def player_hit(self, b=None):
        self.player.hurt()

    def graze(self, b):
        self.score.add(10, popup=False)
        self.score.touch()
        self.audio.play("graze", b.x, 1.0, throttle=3)
        p = self.player
        self.fx.spark_burst((b.x + p.x) / 2, (b.y + p.y) / 2, 2, (200, 230, 255), 2, 8)

    def on_player_death(self):
        self.no_miss = False
        if self.player.lives < 0:
            self.state = "continue"
            self.state_t = 0
            self.audio.stop_loops()

    def continue_game(self):
        p = self.player
        self.continues -= 1
        p.lives = self.diff["lives"] - 1
        p.bombs = 3
        self.score.score = self.score.score % 10 + (self.diff["continues"] - self.continues)
        self.score.next_extend_i = 0
        self.state = "play"
        p.respawn = 20
        self.banner("L'ESPOIR RENAÎT", (170, 230, 255), 90)

    # --- boss ---------------------------------------------------------------------
    def set_boss(self, b):
        self.boss = b

    def warning(self):
        self.warning_t = 200
        self.audio.stop_music(1500)
        self.audio.play("warning")

    def stage_clear(self):
        self.state = "clear"
        self.state_t = 0
        self.audio.stop_loops()
        self.audio.stop_music(2500)
        s = self.score
        rate = 0 if self.stage_spawned == 0 else min(100, int(100 * s.stage_kills / max(1, self.stage_spawned)))
        bonus_rate = rate * 1000
        bonus_miss = 50000 if self.no_miss else 0
        bonus_power = self.player.power * 5000 + self.player.bombs * 10000
        self.tally = {"rate": rate, "chain": s.max_chain, "coins": s.coins, "bonus_rate": bonus_rate,
                      "bonus_miss": bonus_miss, "bonus_power": bonus_power,
                      "total": bonus_rate + bonus_miss + bonus_power, "shown": 0}
        self.player.firing = False

    # --- mise à jour ---------------------------------------------------------------------
    def update(self, inp):
        self.juice.update()
        if self.juice.hitstop > 0:
            self.juice.hitstop -= 1
            return
        if self.juice.slowmo > 0:
            self.juice.slowmo -= 1
            if self.juice.slowmo % 2 == 0:
                return
        self.t += 1
        self.state_t += 1
        st = self.state
        p = self.player
        if st == "continue":
            self.fx.update()
            self.bg.update()
            return
        self.bg.update()
        if st in ("intro",):
            # le vaisseau entre par le bas
            k = min(1.0, self.state_t / 90)
            p.y = lerp(PF_H + 30, PF_H - 50, ease_out_cubic(k))
            p.x = PF_W / 2
            p.update(inp)
            if self.state_t >= 110:
                self.state = "play"
                p.control = True
        elif st == "play":
            if getattr(self, "state_enter", False):
                self.enter_t += 1
                k = min(1.0, self.enter_t / 50)
                p.y = lerp(PF_H + 20, PF_H - 50, ease_out_cubic(k))
                if self.enter_t >= 50:
                    self.state_enter = False
                    p.control = True
            self.director.update()
            p.update(inp)
        elif st == "clear":
            p.control = False
            p.update(inp)
            if self.state_t > 60:
                p.y -= min(6.0, (self.state_t - 60) * 0.08)
            if self.state_t == 30:
                self.audio.play("clear")
            self.update_tally(inp)
        self.player_dead_pause = p.dead
        self.targets = [e for e in self.enemies if not e.dead and e.targetable()]
        for s in self.shots:
            s.update()
        self.shots = [s for s in self.shots if s.alive]
        for e in self.enemies:
            if not e.dead:
                e.update()
        # collisions corps à corps
        if p.vulnerable():
            for e in self.enemies:
                if e.dead or not e.BODY or e.GROUND or not e.onscreen:
                    continue
                if e.collide(p.x, p.y, 3):
                    p.hurt()
                    e.hit(8, p.x, p.y)
                    break
        self.enemies = [e for e in self.enemies if not e.dead and not e.gone]
        for h in self.hazards:
            h.update()
            if h.alive and p.vulnerable() and h.hits(p.x, p.y, p.HIT_R):
                p.hurt()
        self.hazards = [h for h in self.hazards if h.alive]
        self.bullets.update()
        for it in self.items:
            it.update()
        self.items = [i for i in self.items if i.alive]
        self.fx.update()
        self.score.update()
        if self.warning_t > 0:
            self.warning_t -= 1
        if self.boss is not None:
            self.boss_show = min(1.0, self.boss_show + 0.02)
            if self.boss.dead or self.boss.gone:
                self.boss_show = max(0.0, self.boss_show - 0.04)
        if self.hud_flash_weapon > 0:
            self.hud_flash_weapon -= 1
        self.banners = [[a, b, c - 1, d, e] for (a, b, c, d, e) in self.banners if c > 1]

    def update_tally(self, inp):
        tl = self.tally
        if tl is None:
            return
        t = self.state_t
        if 120 < t < 300 and tl["shown"] < tl["total"]:
            step = max(1, tl["total"] // 90)
            tl["shown"] = min(tl["total"], tl["shown"] + step)
            if t % 3 == 0:
                self.audio.play("tick", None, 0.7, throttle=2)
            if tl["shown"] >= tl["total"]:
                self.score.add(0)
        if t == 300:
            self.score.score += tl["total"]
            self.score.check_extend()
            self.audio.play("gong")
        if t > 330 and (inp.pressed("fire") or inp.pressed("confirm")) or t > 560:
            self.tally = None
            self.next_stage()

    def next_stage(self):
        from . import stages
        if self.stage_n >= stages.LAST:
            self.state = "ending"
            self.state_t = 0
            return
        self.save.cleared = max(self.save.cleared, self.stage_n + 1)
        self.save.save()
        self.load_stage(self.stage_n + 1)

    # --- rendu --------------------------------------------------------------------------------
    def draw(self, screen):
        f = self.frame
        a = self.add
        p = self.player
        bg = self.bg
        bg.draw_far(f)
        bg.draw_ground(f)
        if bg.shadows:
            for e in self.enemies:
                if not e.GROUND:
                    e.draw_shadow(f)
            p.draw_shadow(f)
        for e in self.enemies:
            if e.GROUND:
                e.draw(f)
        bg.draw_mid(f)
        for it in self.items:
            it.draw(f)
        for e in self.enemies:
            if not e.GROUND and not e.OWNER_DRAWS:
                e.draw(f)
        for e in self.enemies:
            if e.OWNER_DRAWS and not e.dead:
                e.draw(f)
        for s in self.shots:
            s.draw(f)
        p.draw(f)
        if p.bomb is not None:
            p.bomb.draw(f)
        self.fx.draw_normal(f)
        # calque émissif
        a.fill((0, 0, 0))
        bg.draw_add(a)
        for e in self.enemies:
            e.draw_add(a)
        for s in self.shots:
            s.draw_add(a)
        for it in self.items:
            it.draw_add(a)
        for h in self.hazards:
            h.draw_add(a)
        p.draw_add(a)
        self.fx.draw_add(a)
        self.bullets.draw_add(a)
        f.blit(a, (0, 0), special_flags=pygame.BLEND_ADD)
        if self.save.options.get("bloom", True):
            self.post.bloom(f, a, 1.0)
        bg.draw_fore(f)
        self.bullets.draw(f)
        # post-traitement du terrain de jeu
        j = self.juice
        if j.chroma > 0.5:
            self.post.chroma(f, j.chroma)
        if j.flash_a > 0:
            self.post.flash(f, j.flash_col, j.flash_a)
        f.blit(self.post.vignette, (0, 0))
        self.draw_overlays(f)
        screen.blit(f, (PF_X + j.ox, j.oy))

    def draw_overlays(self, f):
        font = F.FONT
        # barre de vie du boss
        b = self.boss
        if b is not None and self.boss_show > 0:
            k = ease_out_cubic(self.boss_show)
            y = int(-14 + 18 * k)
            w_ = 200
            x0 = PF_W // 2 - w_ // 2
            hpf = b.hp_frac() if hasattr(b, "hp_frac") else max(0.0, b.hp / b.max_hp)
            pygame.draw.rect(f, (10, 6, 22), (x0 - 2, y - 1, w_ + 4, 7))
            pygame.draw.rect(f, (60, 20, 40), (x0, y + 1, w_, 3))
            fill = int(w_ * hpf)
            col = (255, 80, 120) if hpf > 0.3 or (self.t // 6) % 2 else (255, 230, 120)
            if fill > 0:
                pygame.draw.rect(f, col, (x0, y + 1, fill, 3))
                pygame.draw.line(f, (255, 220, 230), (x0, y + 1), (x0 + fill - 1, y + 1))
            for i in range(1, 4):
                pygame.draw.line(f, (10, 6, 22), (x0 + w_ * i // 4, y + 1), (x0 + w_ * i // 4, y + 3))
            font.draw(f, b.NAME, PF_W // 2, y + 7, (255, 220, 200), "center", outline=(10, 6, 22))
        # avertissement
        if self.warning_t > 0:
            self.draw_warning(f)
        # bannières
        yb = 120
        for (text, col, life, total, sub) in self.banners:
            k = min(1.0, (total - life) / 10, life / 10)
            if k <= 0:
                continue
            wdt = font.width(text)
            x = PF_W // 2
            if (life // 4) % 2 or life > 20:
                font.draw(f, text, x, yb, col, "center", outline=(10, 6, 22))
            yb += 14
        st = self.state
        if st == "intro":
            self.draw_stage_card(f)
        elif st == "clear":
            self.draw_tally(f)

    def draw_warning(self, f):
        t = 200 - self.warning_t
        font = F.FONT
        k = min(1.0, t / 15, self.warning_t / 15)
        if k <= 0:
            return
        band_h = int(44 * k)
        y0 = PF_H // 2 - band_h // 2
        band = pygame.Surface((PF_W, band_h), pygame.SRCALPHA)
        band.fill((120, 0, 30, 120))
        f.blit(band, (0, y0))
        red = (255, 60, 80) if (t // 8) % 2 == 0 else (255, 200, 120)
        for yy in (y0, y0 + band_h - 3):
            for x in range(-20, PF_W + 20, 12):
                xx = x + (t * 2 if yy == y0 else -t * 2) % 12
                pygame.draw.polygon(f, red, [(xx, yy), (xx + 6, yy), (xx + 9, yy + 3), (xx + 3, yy + 3)])
        if band_h > 30:
            font.draw(f, "ΚΙΝΔΥΝΟΣ", PF_W // 2, PF_H // 2 - 14, red, "center", outline=(30, 0, 10), scale=2)
            font.draw(f, "ALERTE : DIVINITÉ EN APPROCHE", PF_W // 2, PF_H // 2 + 8, (255, 220, 220), "center",
                      outline=(30, 0, 10))

    def draw_stage_card(self, f):
        from . import stages
        t = self.state_t
        info = stages.INFO[self.stage_n]
        font = F.FONT
        k = min(1.0, t / 20, max(0.0, (110 - t) / 20))
        if k <= 0:
            return
        cx = PF_W // 2
        w_ = int(200 * ease_out_cubic(k))
        y = 96
        pygame.draw.line(f, (255, 210, 110), (cx - w_ // 2, y), (cx + w_ // 2, y))
        pygame.draw.line(f, (255, 210, 110), (cx - w_ // 2, y + 44), (cx + w_ // 2, y + 44))
        # frise grecque
        for x in range(cx - w_ // 2, cx + w_ // 2 - 6, 8):
            pygame.draw.lines(f, (150, 100, 40), False, [(x, y - 2), (x, y - 6), (x + 6, y - 6), (x + 6, y - 3),
                                                         (x + 3, y - 3)])
        if k > 0.6:
            font.draw(f, info["num"], cx, y + 6, (255, 220, 140), "center", outline=(10, 6, 22))
            font.draw(f, info["name"], cx, y + 17, (255, 255, 255), "center", outline=(10, 6, 22), scale=2,
                      grad=((255, 250, 220), (230, 160, 60)))
            font.draw(f, info["sub"], cx, y + 34, (190, 200, 255), "center", outline=(10, 6, 22))

    def draw_tally(self, f):
        tl = self.tally
        if tl is None:
            return
        t = self.state_t
        font = F.FONT
        if t < 40:
            return
        k = min(1.0, (t - 40) / 20)
        cx = PF_W // 2
        panel = pygame.Surface((220, 120), pygame.SRCALPHA)
        panel.fill((8, 6, 24, int(200 * k)))
        f.blit(panel, (cx - 110, 70))
        pygame.draw.rect(f, (200, 150, 60), (cx - 110, 70, 220, 120), 1)
        font.draw(f, "ΝΙΚΗ · VICTOIRE", cx, 78, (255, 230, 140), "center", outline=(10, 6, 22), scale=2,
                  grad=((255, 250, 220), (230, 160, 60)))
        rows = [("TAUX DE DESTRUCTION", f"{tl['rate']}%"), ("CHAÎNE MAX.", str(tl["chain"])),
                ("DRACHMES", str(tl["coins"])), ("SANS PERTE", "50000" if tl["bonus_miss"] else "0")]
        for i, (a_, b_) in enumerate(rows):
            if t > 60 + i * 12:
                font.draw(f, a_, cx - 100, 104 + i * 12, (200, 210, 255))
                font.draw(f, b_, cx + 100, 104 + i * 12, (255, 255, 255), "right")
        if t > 120:
            font.draw(f, "PRIME", cx - 100, 162, (255, 220, 140))
            font.draw(f, str(tl["shown"]), cx + 100, 162, (255, 240, 180), "right")
        if t > 330 and (t // 20) % 2 == 0:
            font.draw(f, "APPUIE SUR TIR", cx, 178, (180, 190, 230), "center")
