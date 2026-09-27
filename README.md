# Cendrespire

Action-RPG roguelike en 3D, écrit en Python. Les inspirations :
- **Torghast** (World of Warcraft) pour la structure : une tour à étages, des pouvoirs d'anima, des gardiens ;
- **Minecraft Dungeons** pour le gameplay : roulade, artefacts, enchantements, potion à recharge ;
- **Diablo** pour l'ambiance des donjons ;
- **Zelda Breath of the Wild** pour l'interface et l'écran titre.

Presque tout est généré par le code : les modèles 3D en formes simples (sphères, cylindres, cônes, blocs), les niveaux et les sons. Seuls l'illustration et le logo du menu principal sont des images (`assets/`).

## Lancer le jeu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Il faut une carte graphique compatible OpenGL 3.3, ce qui est le cas de tout Mac récent. Le jeu s'affiche à la résolution native de l'écran, Retina compris. F11 bascule en plein écran. Les sauvegardes sont écrites dans `saves/`.

## Installeur Windows

```powershell
.\build_installer.ps1
```

Le script empaquette le jeu avec PyInstaller (`dist\Cendrespire`), puis compile l'installeur avec Inno Setup 6 (`winget install JRSoftware.InnoSetup`). Résultat : `installer\Output\Cendrespire-2.0-Setup.exe`. L'installation ne demande pas de droits administrateur et propose un raccourci sur le bureau. La version installée écrit ses sauvegardes dans `%APPDATA%\Cendrespire\saves`.

## Commandes

| Touche | Action |
|---|---|
| ZQSD / WASD / flèches | Se déplacer (touches physiques : AZERTY et QWERTY fonctionnent) |
| Clic gauche (maintenu) | Attaque de base vers le curseur |
| 1 2 3 4 · clic droit | Sorts de classe (le clic droit lance le sort 1) |
| Espace | Roulade d'esquive (invulnérable) |
| R · T · G | Artefacts |
| F | Potion de soins (illimitée, avec temps de recharge) |
| E | Interagir |
| I · C · N · Échap | Menu : pages Inventaire · Personnage · Talents · Système (met le jeu en pause) |
| Tab | Grande carte |

## Boucle de jeu

1. **Campement** : une clairière au pied de la tour, avec feu de camp, chemins, lanternes et lucioles. On y trouve le marchand (équipement et artefacts), la forgeronne (améliorations jusqu'à +5), la couturière (changer d'apparence) et le portail de la Tour.
2. **Étage** : un donjon 3D généré aléatoirement. Chaque étage a son ambiance : Geôles, Ossuaire, Forges avec lave, Sanctuaire, Cryptes de givre…
3. **Sceau du gardien** : il se brise quand 60% des créatures de l'étage sont tuées. L'arène se referme alors sur le gardien.
4. **Victoire** : l'étage suivant est débloqué, le gardien laisse du butin (objet légendaire garanti à la première victoire) et un portail ramène au campement.
5. **Mort** : on revient au campement en perdant la moitié de l'or ramassé pendant l'ascension. L'équipement et l'expérience sont conservés.

## Systèmes

- **Apparence personnalisable** à la création puis chez la couturière : teint, carrure, coiffure, couleur des cheveux, barbe, yeux, marques (peinture de guerre, cicatrice, tatouage runique), deux couleurs de tenue, couvre-chef visible ou non.
- **6 classes**, chacune avec son attaque de base, 4 sorts débloqués aux niveaux 1, 3, 6 et 10 et son arbre de talents :
  - Barbare : corps à corps, fureur ;
  - Sorcier : magie à distance ;
  - Chasseur : archer, pièges ;
  - Paladin : épée et bouclier, consécration qui soigne, jugement céleste ;
  - Nécromancien : lève des squelettes alliés, maudit (+30% de dégâts subis), moissonne les âmes pour se soigner ;
  - Assassin : deux dagues, pas de l'ombre dans le dos de la cible, lames empoisonnées, danse des lames.
- **Talents** (touche N) : 3 branches par classe, 4 paliers par branche. Un palier demande 3 points de plus dans sa branche ; le 4e est un talent ultime. 1 point de talent tous les 2 niveaux. Clic pour apprendre ; clic droit pour retirer un point, ou « Réinitialiser » contre de l'or, uniquement au campement.
- **Caractéristiques** : 5 points à répartir à chaque niveau.
- **Enchantements** : les objets Magiques, Rares et Légendaires ont 1, 2 ou 3 emplacements. Pour chacun, on choisit 1 enchantement parmi 3, puis on l'améliore jusqu'au niveau III. On gagne 1 point d'enchantement par niveau. Les points investis sont rendus quand on vend ou recycle l'objet.
- **Artefacts** : 9 objets actifs avec temps de recharge, à trouver en butin ou chez le marchand. Par exemple : Pierre d'orage, Totem de régénération, Crâne infernal, Lanterne des âmes (qui invoque un feu follet allié)…
- **Pouvoirs d'anima** : ils sont rares. Les orbes tombent parfois sur les élites et dans les coffres. Chaque orbe propose 3 pouvoirs, avec une rareté Commun, Rare ou Épique qui multiplie leur effet. Ils durent jusqu'à la fin de l'ascension.
- **Butin** : 4 raretés et des bonus aléatoires. Dans le menu, des flèches vertes ou rouges indiquent l'effet de l'objet sur l'attaque, la défense et la vie, comme dans BotW.
- **Menu façon BotW** : quatre pages, Personnage · Talents · Inventaire · Système, parcourues avec ← → ou Tab.
  - Personnage : héros en 3D, médaillon de niveau avec anneau d'expérience, attributs (avec leur effet concret), tuiles Attaque / Défense / Vie / Mana, statistiques détaillées et sorts (infobulles au survol).
  - Inventaire : catégories à pictogrammes (armes, armures, bijoux, artefacts), grille 5×4 avec pages, équipement porté sur fond bleu, héros en 3D qu'on fait pivoter à la souris, encadré de description avec enchantements. Clic ou Entrée sur un objet : menu Équiper / Recycler ; clic droit : équiper directement ; R T G sur un artefact : le placer sur cette touche. ZQSD déplace le curseur.
  - Système : l'ancien menu pause (reprendre, abandonner l'ascension, sauvegarder, plein écran, menu principal, quitter) et le rappel des commandes. Échap ouvre directement cette page.
- **Gardiens** : le Boucher, Varkul la Liche, le Golem d'ossements et Mal'zahar. Leurs attaques sont annoncées au sol, on peut donc les esquiver. Chacun passe en phase enragée sous 50% de vie.

## Rendu

- **Moteur 3D maison** (moderngl) :
  - caméra en plongée qui suit le héros ;
  - ombres portées et lumières dynamiques (torches, sorts, lave) ;
  - anticrénelage 4× ;
  - zones d'attaque dessinées au sol ;
  - particules ;
  - murs qui s'effacent quand ils masquent le héros.
- **Interface** (pygame) : dessinée à la résolution native, puis posée sur l'image 3D, ce qui garde les textes nets. Police Lato embarquée (`assets/fonts`, licence OFL) : même rendu sur toutes les machines.
- **HUD façon BotW** :
  - cœurs par quarts en haut à gauche ;
  - roue de mana à côté du héros ;
  - minicarte carrée arrondie ;
  - jauges du sceau et de la menace ;
  - bulles d'interaction ;
  - titres de zone.

## Structure du code

```
main.py              fenêtre OpenGL, boucle, composition 3D + interface
game/data.py         classes, sorts, monstres, boss, anima, artefacts, enchantements  <- équilibrage
game/looks.py        options d'apparence des héros, construction du modèle
game/wardrobe.py     éditeur d'apparence (création, garde-robe du campement)
game/items.py        objets, raretés, affixes, artefacts, emplacements d'enchantement
game/dungeon.py      génération des étages, carte du campement, minicarte
game/entities.py     héros, monstres, projectiles, butin, PNJ, coffres, portails
game/bosses.py       techniques des gardiens
game/spells.py       attaques et sorts
game/artifacts.py    effets des artefacts
game/fx.py           particules 3D, zones au sol, attaques annoncées
game/world.py        scène de jeu : logique, combat, rendu 3D, interface en jeu
game/tower.py        un étage de la tour
game/hub.py          le campement
game/hud.py          HUD façon BotW
game/panels.py       menus (inventaire avec héros 3D, personnage, système, marchand, forge…)
game/scenes.py       écran titre façon BotW (illustration, logo), chargement, création de personnage
game/ui.py, gfx.py   boîte à outils d'interface (nette en Retina)
assets/              illustration et logo du menu principal
game/r3d/            moteur 3D : renderer, shaders, caméra, maillages, modèles, niveaux, décor du campement
```
