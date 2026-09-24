"""Lance PRISMA, le casse-brique néon :  python main.py"""

import os
import sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

try:
    import numpy  # noqa: F401
    import pygame  # noqa: F401
except ImportError as exc:  # message clair si les dépendances manquent
    sys.stderr.write("Dépendance manquante (%s).\nInstallez-les avec :  pip install -r requirements.txt\n" % exc.name)
    sys.exit(1)

from casse_brique import main

if __name__ == "__main__":
    sys.exit(main())
