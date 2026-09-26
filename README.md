# Tour des Tourments

Action-RPG en Python / pygame, inspiré de **Torghast** (World of Warcraft) pour la structure,
de **Diablo** pour l'ambiance du monde et de **Zelda Breath of the Wild** pour l'interface.
Tous les graphismes et les sons sont générés par le code : il n'y a aucun fichier d'asset.

## Lancer le jeu

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Les sauvegardes sont écrites dans `saves/` (un fichier JSON par personnage).

## Commandes

| Touche | Action |
|---|---|
| ZQSD / WASD / flèches | Se déplacer (touches physiques : AZERTY et QWERTY fonctionnent) |
| Clic gauche (maintenu) | Attaque de base vers le curseur |
| 1 2 3 4 · clic droit | Sorts (le clic droit lance le sort 1) |
| F | Boire une potion |
| E | Parler / ouvrir / emprunter un portail |
| I · C | Menu Équipement · Personnage (met le jeu en pause) |
| Tab | Grande carte |
| Échap | Pause |
| F11 | Plein écran |

## Concept

### Boucle de jeu
1. **Campement** (hub) : on y trouve le marchand, la forgeronne et le portail de la Tour.
2. **Portail** : on choisit un étage déjà débloqué.
3. **Étage** : un donjon généré aléatoirement, avec des salles remplies de monstres.
   - L'entrée de la salle du gardien est protégée par un **sceau**. Il se brise quand 60% des créatures de l'étage sont tuées.
   - En entrant dans l'arène, le sceau se referme : impossible de fuir.
   - Une fois le boss vaincu, l'**étage suivant est débloqué**, un butin tombe (objet légendaire garanti à la première victoire) et un portail ramène au campement.
4. **Mort** : on revient au campement. On perd la moitié de l'or ramassé pendant l'ascension, mais on garde l'équipement et l'expérience.

### Classes
| Classe | Style | Sorts (niveau de déblocage) |
|---|---|---|
| **Barbare** (Force) | Corps à corps, résistant, ses coups rendent du mana | Tourbillon (1), Cri de guerre (3), Bond (6), Séisme (10) |
| **Sorcier** (Intelligence) | Magie à distance, fragile | Boule de feu (1), Nova de givre (3), Téléportation (6), Météore (10) |
| **Chasseur** (Dextérité) | Archer mobile | Tir multiple (1), Piège explosif (3), Roulade (6), Pluie de flèches (10) |

Chaque niveau donne 5 points de caractéristiques à répartir (menu Personnage).

### Pouvoirs d'Anima (façon Torghast)
Les élites et les coffres laissent tomber des orbes d'anima. En ramasser un propose **3 pouvoirs au choix**
(dégâts, vol de vie, explosion des ennemis tués, résurrection…). Ils se cumulent, mais disparaissent à la fin de l'ascension.

### Butin
- **Raretés** : Commun, Magique, Rare, Légendaire. Leurs couleurs reprennent celles de Diablo.
- **7 emplacements** : arme, casque, torse, gants, bottes, amulette, anneau.
- **Affixes** aléatoires : caractéristiques, % de dégâts, critique, vitesse d'attaque, vol de vie, recharge, vitesse de déplacement…
- Les armes sont liées à une classe. La plupart des armes qui tombent sont de votre classe.
- **Forgeronne** : améliore un objet jusqu'à +5 (+10% de statistiques par niveau), contre de l'or.
- **Marchand** : vend des potions et un stock d'objets renouvelé à chaque retour au campement, et rachète vos objets.

### Monstres et gardiens
- **Monstres** : squelettes, goules, archers, diablotins (à partir de l'étage 2), cultistes qui lancent des attaques au sol (étage 3), brutes démoniaques (étage 4).
- **Élites** : plus gros, avec un affixe (Véloce, Vampirique, Robuste, Frénétique, Colossal) et un butin garanti.
- **Gardiens** en rotation : le Boucher (charge), Varkul la Liche (novas, invocations, clignement), le Golem d'ossements (rochers, ondes de choc), puis Mal'zahar (qui combine tout). Chacun passe en phase 2 (enragé) sous 50% de vie.
- Toutes les grosses attaques ennemies sont **annoncées au sol** (zones rouges) : on peut les esquiver.
- La difficulté augmente à chaque étage, sans limite.

### Interface façon Breath of the Wild
- **Vie** : des cœurs en haut à gauche, remplis par quarts. Le dernier cœur bat quand la vie est basse.
- **Mana** : une roue à côté du héros, comme l'endurance de Link. Elle disparaît quand elle est pleine.
- **Minicarte** : circulaire, avec le nord, la flèche jaune du joueur, les ennemis, les coffres et les portails.
- **Grande carte** : style tablette Sheikah (grille, cadre cyan, légende).
- **Menu Équipement / Personnage** : plein écran. Au survol d'un objet, des flèches vertes ou rouges montrent son effet sur l'attaque, la défense et la vie.

## Structure du code

```
main.py            boucle principale, transitions entre scènes
game/settings.py   constantes, palette, touches
game/data.py       classes, sorts, monstres, boss, étages, pouvoirs d'anima  <- équilibrage ici
game/items.py      génération d'objets, affixes, prix
game/dungeon.py    génération procédurale des étages, carte du campement, rendu des tuiles
game/entities.py   joueur, monstres, projectiles, butin, PNJ, coffres, portails
game/bosses.py     techniques des gardiens
game/spells.py     attaques de base et sorts
game/world.py      scène de jeu commune : collisions, IA de déplacement, combat, éclairage
game/tower.py      logique d'un étage (sceau, boss, récompenses)
game/hub.py        le campement
game/hud.py        HUD façon BotW (cœurs, roue de mana, minicarte, carte)
game/panels.py     menus en jeu (équipement, personnage, marchand, forge, portail…)
game/scenes.py     écran titre, chargement, création de personnage
game/render.py     dessin procédural des personnages
game/fx.py         lumières, particules, zones d'effet, attaques annoncées
game/sfx.py        sons synthétisés
```

## Pistes pour la suite
- Vraies images (sprites) à la place du dessin procédural.
- Coffre de stockage au campement et crafting.
- Arbres de talents par classe.
- Étages « à thème » (givre, feu) avec des modificateurs de difficulté.
- Musique d'ambiance.
