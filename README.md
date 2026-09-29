# Steel Ball Arena

Jeu de sport futuriste inspiré de **Speedball 2** (Amiga), en application de bureau (Electron + Canvas 2D).
Direction artistique cartoon dynamique : gros contours prune, aplats sauge / saumon / rose / moutarde / acier,
personnages à énormes gants mécaniques, gardiens-mécas (référence : planche de Fabien Mense).

> Cette première version se concentre sur **le match** (in-game). Progression, gestion d'équipe,
> évolution des joueurs, championnat, etc. viendront ensuite.

Tout est **généré par le code** : aucun sprite, aucun fichier son.
- graphismes : dessin vectoriel procédural (Canvas 2D),
- SFX : synthèse WebAudio (une cinquantaine de sons),
- musique : séquenceur génératif (batterie, basse, nappes, arpèges, lead, sidechain, delay) qui réagit à l'intensité du match.

## Lancer

```bash
npm install
npm start            # ouvre la fenêtre du jeu (F11 : plein écran)
npm run dev          # avec les outils de développement
npm run dist         # empaquette l'application (electron-builder)
```

Sans Electron (test rapide dans un navigateur) : `npm run serve` puis http://localhost:8123

## Règles (résumé)

- 5 joueurs par équipe (gardien-méca + 4). Deux périodes, mort subite en cas d'égalité.
- **But = 10 points.** Bumpers = 1 point par rebond. Pads étoilés au mur = 2 points ; 6 pads sur 8 → **STAR RUSH : prochain but x2**.
- Les **portails** téléportent la balle de l'autre côté du terrain.
- **Jetons** : `$` pièces · **TURBO** · **POWER** · **GEL** (fige l'adversaire).
- Tacles glissés, charges d'épaule en turbo, balles hautes (lob) et sauts pour les attraper.

## Commandes

| Action | Solo | Duel J1 | Duel J2 | Manette |
|---|---|---|---|---|
| Déplacer | ZQSD / WASD / flèches | ZQSD | flèches | stick / croix |
| Tir / Tacle | Espace, F, J | F | K | A / X |
| Lob / Saut | G, K | G | L | B |
| Turbo | Maj, H | H | ; | RB / RT |
| Changer de joueur | A(Q), E | A(Q) | O | Y / LB |
| Pause | Échap, P | | | Start |

Maintenir « Tir » avec la balle charge un tir puissant ; une simple pression fait une passe assistée.
Le clavier utilise les positions physiques des touches (AZERTY et QWERTY fonctionnent).

## Structure

```
main.js                 processus principal Electron
src/index.html          page unique (canvas)
src/js/config.js        constantes, palette, équipes, difficultés
src/js/game.js          simulation du match (physique, règles, phases, replay)
src/js/ai.js            IA des joueurs et des gardiens
src/js/art.js           personnages, balle, bumpers, portails (dessin vectoriel)
src/js/arena.js         décor pré-rendu, foule, cages, pads
src/js/render.js        caméra, tri en profondeur, lumière, HUD
src/js/fx.js            particules, textes BD, secousses, hit-stop
src/js/audio.js         moteur WebAudio + bibliothèque de SFX
src/js/music.js         séquenceur musical génératif
src/js/ui.js            menus, options, pause, résultats
src/js/input.js         clavier + manettes
tools/shot.js           captures automatiques (Chromium headless) pour vérifier le rendu
```

`npx electron . --selftest=capture.png` lance l'application, sauvegarde une capture et quitte (vérification rapide).

## Licences

Polices : Bangers et Lilita One (SIL Open Font License, voir `src/fonts/`).
