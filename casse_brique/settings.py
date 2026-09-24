"""Réglages et records, sauvegardés dans un petit fichier JSON du dossier personnel."""

import json
import os
from pathlib import Path

DEFAULTS = {
    "music_volume": 0.6,
    "sfx_volume": 0.8,
    "crt": True,
    "shake": True,
    "fullscreen": False,
    "best_score": 0,
    "best_level": 1,
}


def _valid(value, default):
    """Vérifie qu'une valeur lue sur disque a le bon type (les booléens ne sont pas des nombres)."""
    if value is None:
        return False
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if isinstance(default, float):
        return isinstance(value, (int, float)) and 0.0 <= value <= 1.0
    return isinstance(value, int) and value >= 0


def default_path():
    custom = os.environ.get("PRISMA_SAVE")
    if custom:
        return Path(custom)
    return Path.home() / ".prisma_casse_brique.json"


class Settings:
    def __init__(self, path=None, **values):
        self.path = Path(path) if path else default_path()
        for k, v in DEFAULTS.items():
            setattr(self, k, values.get(k, v))

    @classmethod
    def load(cls, path=None):
        p = Path(path) if path else default_path()
        data = {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for k, default in DEFAULTS.items():
                    if _valid(raw.get(k), default):
                        data[k] = float(raw[k]) if isinstance(default, float) else raw[k]
        except (OSError, ValueError):
            pass
        return cls(p, **data)

    def save(self):
        data = {k: getattr(self, k) for k in DEFAULTS}
        try:
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass
