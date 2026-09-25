#!/usr/bin/env python3
"""ALETHEIA — La Chute de l'Olympe.

Shoot'em up vertical inspiré de Super Aleste (SNES), mythologie grecque + science-fiction.
Lancement :  python main.py
"""
import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description="ALETHEIA — La Chute de l'Olympe (shoot'em up)")
    ap.add_argument("--stage", type=int, default=0, help="commencer directement au stade N (1-6)")
    ap.add_argument("--boss", action="store_true", help="aller directement au boss du stade")
    ap.add_argument("--weapon", type=str, default=None,
                    help="arme de départ : zeus, apollo, artemis, poseidon, athena, hephaestus")
    ap.add_argument("--power", type=int, default=0, help="niveau de puissance de départ (0-5)")
    ap.add_argument("--invincible", action="store_true", help="mode invincible (tests)")
    ap.add_argument("--mute", action="store_true", help="sans son")
    ap.add_argument("--fps", action="store_true", help="afficher les images/seconde (F3)")
    ap.add_argument("--autoplay", action="store_true", help="pilote automatique (démo/tests)")
    ap.add_argument("--frames", type=int, default=0, help="quitter après N images (tests)")
    ap.add_argument("--shots", type=str, default=None, help="dossier de captures d'écran périodiques")
    ap.add_argument("--shot-every", dest="shot_every", type=int, default=300)
    ap.add_argument("--turbo", action="store_true", help="ne pas limiter à 60 i/s (tests)")
    args = ap.parse_args()
    try:
        import pygame  # noqa: F401
        import numpy  # noqa: F401
    except ImportError as e:
        print("Il manque une dépendance :", e)
        print("Installe-les avec :  pip install -r requirements.txt")
        sys.exit(1)
    from aletheia.app import App
    App(args).run()


if __name__ == "__main__":
    main()
