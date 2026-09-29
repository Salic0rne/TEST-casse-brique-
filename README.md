# STEEL CARNAGE

Sport de combat en arène, post-apocalyptique, inspiré de **Speedball 2** (Amiga).
Deux gangs de 6 joueurs (gardien + 5), une balle en acier, 2 × 90 s, aucune pitié.

Ce dépôt couvre uniquement la **partie in-game** : match, règles, IA, rendu, effets, audio.
La progression, les stats évolutives, le championnat et le mercato viendront plus tard
(les points d'extension sont prévus : `player.stats`, `team.credits`, `DIFFICULTIES`, `TEAMS`).

## Lancer le jeu

```bash
npm install
npm start          # application de bureau (Electron)
npm run web        # variante navigateur pour le dev : http://localhost:8080
npm run dist       # exécutable Windows / macOS / Linux (dossier dist/)
```

## Contrôles

| Action | Solo (clavier) | Manette |
|---|---|---|
| Déplacer | ZQSD / WASD / flèches | stick gauche / croix |
| Passe / tir (maintenir = puissance) | Espace / J / X | A |
| Tacle glissé (sans balle) | Espace / J / X | A |
| Lob (avec balle) / saut (sans balle) | K / C / Shift gauche | B / X |
| Changer de joueur | L / V / Tab | LB / RB |
| Pause | Échap / P | Start |

2 joueurs sur un clavier : J1 = ZQSD + Espace / Shift / Tab — J2 = flèches + Pavé 0 / Pavé . / Pavé Entrée.
Avec des manettes, chaque joueur prend automatiquement la sienne.
`F11` plein écran · `M` couper la musique · `F3` compteur de performances.

Visée assistée : si le stick pointe vers un coéquipier ou vers le but, la passe/le tir s'y verrouille (avec anticipation de la course du receveur).

## Règles

- **But** : 10 pts × multiplicateur.
- **Rampe multiplicateur** (au centre des murs haut et bas) : y envoyer la balle donne ×1.5 puis ×2 à ton équipe et remet l'adversaire à ×1.
- **Étoiles** (6 en haut, 6 en bas) : toucher une étoile avec la balle la passe à ta couleur, +2 pts tant qu'elle reste allumée. Toute la rangée = +10 bonus.
- **K.O.** : chaque tacle retire de la santé ; un adversaire mis K.O. rapporte +5.
- **Bumpers** : renvoient et accélèrent la balle.
- **Bobines électriques** : électrifient la balle pour l'équipe qui l'a lancée ; un adversaire qui l'attrape est électrocuté.
- **Jetons** : RAGE (vitesse + tacles dévastateurs), E (balle électrique), F (adversaires entravés), + (soins), $ (crédits).
- Égalité à la fin : **mort subite**, le premier qui marque gagne.

## Choix techniques

- **Electron + JavaScript (modules ES), sans dépendance de jeu** : application de bureau multiplateforme, démarrage immédiat, WebGL et Web Audio intégrés.
- **Tout est procédural**, sans aucun asset graphique ou sonore externe (seules deux polices OFL sont embarquées) :
  - personnages en **pseudo-3D squelettale** (poses 3D, rotation libre, projection oblique, silhouettes contourées) : course, tacle glissé, chute, saut, plongeon du gardien, lancer chargé, célébration ;
  - arène d'acier rouillé générée (bruit fractal, rivets, peinture usée, rampes, étoiles, fosses de but électrifiées, public animé, barils en feu) avec **décalques persistants** (sang, brûlures, traces de glissade) ;
  - **post-process WebGL** : bloom multi-passes, aberration chromatique sur les impacts, ondes de choc, grading teal/orange, vignette, grain, flashs ;
  - **game feel** : hit-stop, ralentis sur les K.O. et les buts, secousses de caméra, caméra dynamique avec anticipation ;
  - **audio Web Audio 100 % synthétisé** : impacts, métal, bumpers FM, électricité, sirène, explosions, foule réactive avec formants, réverbération d'arène à convolution, et **musique procédurale adaptative** (tambours de guerre, guitare saturée, basse, lead) dont l'intensité suit le match.
- Simulation à pas fixe de 1/120 s, rendu découplé.

## Structure

```
electron/main.js        fenêtre Electron (F11 plein écran)
src/main.js             boucle, états (titre, menu, match, pause, résultats)
src/game/               règles (match.js), joueurs, IA, caméra, constantes
src/render/             arène, personnages, particules/FX, post-process WebGL
src/audio/              moteur SFX + foule, musique procédurale
src/ui/hud.js           tableau de score, mini-carte, menus
```
