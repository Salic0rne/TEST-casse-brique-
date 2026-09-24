"""PRISMA — casse-brique néon en Python (pygame)."""

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

__all__ = ["main"]


def main():
    from .app import main as _main
    return _main()
