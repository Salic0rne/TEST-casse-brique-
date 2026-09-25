"""Gestion du son : bruitages spatialisés (panoramique selon x), limitation de polyphonie,
sons en boucle (rayons), musiques rendues en tâche de fond avec fondus enchaînés."""
import threading
import time

import numpy as np
import pygame

from . import sfx as sfxmod
from . import songs
from .music import Renderer
from .synth import to_int16_stereo

# volume relatif et polyphonie max par bruitage
SFX_MIX = {
    "shot": (0.32, 2), "shot2": (0.32, 2), "hit": (0.5, 3), "tink": (0.5, 2), "eshot": (0.5, 3),
    "eshot2": (0.5, 3), "eshot_big": (0.6, 2), "graze": (0.5, 2), "coin": (0.45, 3), "pickup": (0.7, 2),
    "explo_s": (0.75, 5), "explo_m": (0.85, 3), "explo_l": (0.95, 2), "explo_boss": (1.0, 1),
    "zap": (0.55, 2), "laser": (0.5, 2), "arrow": (0.5, 3), "wave": (0.45, 2), "clang": (0.5, 2),
    "block": (0.45, 3), "mortar": (0.55, 2), "fire_burst": (0.6, 3), "tick": (0.5, 1), "typing": (0.6, 1),
    "chain": (0.55, 1), "menu_move": (0.7, 1), "lightning": (0.8, 2), "thunder": (0.9, 1),
}
LOOPS = ("laser_loop", "zap_beam", "flame_loop")
PF_X0, PF_W = 0.0, 256.0


class Audio:
    def __init__(self, save, enabled=True):
        self.save = save
        self.enabled = enabled and pygame.mixer.get_init() is not None
        self.sounds = {}
        self.music = {}
        self.cur_music = None
        self.want_music = None
        self.want_fade = 800
        self.music_loop = True
        self.voices = {}
        self.loop_ch = {}
        self.last_play = {}
        self.frame = 0
        self._lock = threading.Lock()
        self._thread = None
        self._queue = []
        self.render_progress = {}
        self.music_vol = 1.0
        if self.enabled:
            pygame.mixer.set_num_channels(40)
            pygame.mixer.set_reserved(2 + len(LOOPS))
            self.mch = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.mi = 0
            self.lch = {name: pygame.mixer.Channel(2 + i) for i, name in enumerate(LOOPS)}

    # --- chargement --------------------------------------------------------------
    def build_sfx(self, progress=None):
        data = sfxmod.build_all(progress)
        if not self.enabled:
            return
        for name, (L, R) in data.items():
            # coupe les traînes quasi silencieuses
            amp = np.maximum(np.abs(L), np.abs(R))
            pk = float(amp.max()) or 1.0
            idx = np.nonzero(amp > pk * 0.0015)[0]
            end = int(idx[-1]) + 64 if len(idx) else len(L)
            L, R = L[:end].copy(), R[:end].copy()
            if name not in LOOPS:
                fl = min(len(L), 256)
                L[-fl:] *= np.linspace(1, 0, fl)
                R[-fl:] *= np.linspace(1, 0, fl)
            arr = to_int16_stereo(L, R, peak=0.95)
            self.sounds[name] = pygame.sndarray.make_sound(arr)

    def start_music_thread(self):
        if not self.enabled or self._thread is not None:
            return
        self._queue = [n for n in songs.RENDER_ORDER if n not in self.music]
        self._thread = threading.Thread(target=self._render_loop, daemon=True)
        self._thread.start()

    def render_now(self, name, progress=None):
        """Rendu synchrone (pendant l'écran de chargement)."""
        if not self.enabled or name in self.music:
            return
        L, R = Renderer(songs.SONGS[name]).render(progress)
        snd = pygame.sndarray.make_sound(to_int16_stereo(L, R, peak=0.95))
        with self._lock:
            self.music[name] = snd

    def _render_loop(self):
        while True:
            with self._lock:
                todo = [n for n in self._queue if n not in self.music]
                if self.want_music and self.want_music not in self.music and self.want_music in todo:
                    todo.remove(self.want_music)
                    todo.insert(0, self.want_music)
            if not todo:
                break
            name = todo[0]
            try:
                def prog(p, _n=name):
                    self.render_progress[_n] = p
                    time.sleep(0.002)  # laisse respirer le fil principal
                L, R = Renderer(songs.SONGS[name]).render(prog)
                snd = pygame.sndarray.make_sound(to_int16_stereo(L, R, peak=0.95))
                with self._lock:
                    self.music[name] = snd
            except Exception as e:  # ne jamais tuer le jeu pour une musique
                print("[audio] rendu impossible", name, e)
                with self._lock:
                    self._queue = [n for n in self._queue if n != name]

    def music_ready(self, name):
        return name in self.music

    # --- volumes -----------------------------------------------------------------
    @property
    def sfx_gain(self):
        return (self.save.options.get("sfx", 8) / 10.0) ** 1.4

    @property
    def mus_gain(self):
        return (self.save.options.get("music", 7) / 10.0) ** 1.4 * 0.8

    # --- bruitages -----------------------------------------------------------------
    def play(self, name, x=None, vol=1.0, throttle=2):
        if not self.enabled:
            return None
        snd = self.sounds.get(name)
        if snd is None:
            return None
        last = self.last_play.get(name, -99)
        if self.frame - last < throttle:
            return None
        self.last_play[name] = self.frame
        mix, maxv = SFX_MIX.get(name, (0.8, 4))
        lst = self.voices.setdefault(name, [])
        lst[:] = [c for c in lst if c.get_busy() and c.get_sound() is snd]
        if len(lst) >= maxv:
            ch = lst.pop(0)
            ch.stop()
        else:
            ch = pygame.mixer.find_channel(True)
        if ch is None:
            return None
        g = mix * vol * self.sfx_gain
        if x is None:
            ch.set_volume(g, g)
        else:
            p = max(-1.0, min(1.0, (x - PF_X0) / PF_W * 2 - 1)) * 0.75
            gl = min(1.0, 1 - p)
            gr = min(1.0, 1 + p)
            ch.set_volume(g * gl, g * gr)
        ch.play(snd)
        lst.append(ch)
        return ch

    def loop(self, name, on, vol=1.0, x=None):
        """Démarre/arrête un son en boucle (rayons continus)."""
        if not self.enabled:
            return
        ch = self.lch.get(name)
        if ch is None:
            return
        if on:
            g = vol * self.sfx_gain * 0.7
            if x is not None:
                p = max(-1.0, min(1.0, x / PF_W * 2 - 1)) * 0.5
                ch.set_volume(g * min(1, 1 - p), g * min(1, 1 + p))
            else:
                ch.set_volume(g, g)
            if not ch.get_busy():
                ch.play(self.sounds[name], loops=-1, fade_ms=40)
        else:
            if ch.get_busy():
                ch.fadeout(90)

    def stop_loops(self):
        if not self.enabled:
            return
        for ch in self.lch.values():
            ch.stop()

    # --- musique -------------------------------------------------------------------
    def play_music(self, name, fade=800, loop=True):
        if not self.enabled:
            return
        if name == self.cur_music and name == self.want_music:
            return
        self.want_music = name
        self.want_fade = fade
        self.music_loop = loop
        self._try_start()

    def _try_start(self):
        name = self.want_music
        if name is None or name == self.cur_music:
            return
        with self._lock:
            snd = self.music.get(name)
        if snd is None:
            return
        old = self.mch[self.mi]
        if old.get_busy():
            old.fadeout(self.want_fade)
        self.mi = 1 - self.mi
        ch = self.mch[self.mi]
        g = self.mus_gain * self.music_vol
        ch.set_volume(g, g)
        ch.play(snd, loops=-1 if self.music_loop else 0, fade_ms=min(self.want_fade, 1500))
        self.cur_music = name

    def stop_music(self, fade=800):
        if not self.enabled:
            return
        for ch in self.mch:
            if ch.get_busy():
                ch.fadeout(fade)
        self.cur_music = None
        self.want_music = None

    def set_music_volume(self, k):
        """k multiplicatif (pour baisser pendant la pause par ex.)."""
        self.music_vol = k
        if self.enabled:
            g = self.mus_gain * k
            self.mch[self.mi].set_volume(g, g)

    def update(self):
        self.frame += 1
        if self.enabled and self.want_music and self.want_music != self.cur_music:
            self._try_start()

    def apply_volumes(self):
        self.set_music_volume(self.music_vol)
