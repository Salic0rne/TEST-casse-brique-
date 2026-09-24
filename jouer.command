#!/bin/bash
# PRISMA — double-cliquez sur ce fichier dans le Finder pour lancer le jeu.
# Au premier lancement, il prépare un environnement Python dans le dossier .venv
# (une minute environ) ; les fois suivantes, le jeu démarre directement.

cd "$(dirname "$0")" || exit 1

pause_et_quitter() {
    echo
    echo "$1"
    read -r -p "Appuyez sur Entrée pour fermer cette fenêtre…" _
    exit 1
}

VENV_PY=".venv/bin/python"

# environnement absent ou cassé (par exemple après une mise à jour de Python) : on le recrée
if ! "$VENV_PY" -c "import sys" >/dev/null 2>&1; then
    command -v python3 >/dev/null 2>&1 \
        || pause_et_quitter "Python 3 est introuvable : installez-le depuis https://www.python.org/downloads/ puis relancez."
    echo "Préparation de l'environnement Python (une seule fois)…"
    rm -rf .venv
    python3 -m venv .venv \
        || pause_et_quitter "Impossible de créer l'environnement Python. Si une fenêtre propose d'installer les « outils de développement en ligne de commande », acceptez, attendez la fin, puis relancez."
fi

if ! "$VENV_PY" -c "import pygame, numpy" >/dev/null 2>&1; then
    echo "Installation de pygame-ce et numpy (une minute environ, une seule fois)…"
    "$VENV_PY" -m pip install -q --disable-pip-version-check --upgrade pip
    "$VENV_PY" -m pip install -q --disable-pip-version-check -r requirements.txt \
        || pause_et_quitter "L'installation a échoué : vérifiez la connexion internet puis relancez."
fi

echo "Lancement de PRISMA…"
"$VENV_PY" main.py || pause_et_quitter "Le jeu s'est arrêté sur une erreur (détails ci-dessus)."
