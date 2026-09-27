# Contenu modifiable de Cendrespire

Tout le contenu du jeu est décrit dans les fichiers JSON de ce dossier. On peut modifier les valeurs ou ajouter des éléments sans toucher au code Python : le jeu relit ces fichiers à chaque lancement.

Si un fichier contient une erreur, le jeu ne se ferme pas : il affiche un écran qui indique le fichier, l'élément et le champ en cause. Avant de construire l'installeur, `installer/check_content.py` fait la même vérification.

## Modifier une version installée

Pas besoin de toucher au dossier d'installation. Il suffit de copier un fichier (par exemple `spells.json`) dans `%APPDATA%\Cendrespire\data` (raccourci « Cendrespire - contenu personnalisé » dans le menu Démarrer) et de le modifier : cette copie remplace celle du jeu. Pour revenir à l'original, supprimez la copie.

## Fichiers

| Fichier | Contenu |
|---|---|
| `classes.json` | Classes : caractéristiques, attaque de base, 4 sorts, armes, noms légendaires, apparence du modèle 3D |
| `spells.json` | Sorts : coût, recharge, niveau requis, puissance, liste d'effets |
| `talents.json` | Arbres de talents : 3 branches par classe, 4 paliers |
| `buffs.json` | Effets temporaires (Cri de guerre, Égide, Célérité…) |
| `artifacts.json` | Artefacts : recharge, puissance selon la rareté, liste d'effets |
| `monsters.json` | Monstres, affixes d'élite, progression par étage |
| `bosses.json` | Boss : statistiques, techniques, ordre d'apparition |
| `anima.json` | Pouvoirs d'anima et paliers de rareté |
| `enchantments.json` | Enchantements par type d'objet |
| `floors.json` | Noms des étages |
| `quests.json` | Quêtes données par les habitants de Cendreval |
| `updates/*.json` | Notes de mise à jour (un fichier par version, affichées dans le menu Système) |

Les couleurs s'écrivent `[rouge, vert, bleu]`, chaque valeur allant de 0 à 255.

## Ajouter un sort

1. Ajoutez une entrée dans `spells.json` :

```json
"eclair_givre": {
  "name": "Éclair de givre", "level": 3, "mana": 18, "cd": 4, "mult": 2.2,
  "color": [150, 210, 255], "icon": "snow", "target": "aim",
  "desc": "Un trait de glace perçant (220%) qui ralentit.",
  "effects": [
    {"type": "projectile", "speed": 800, "radius": 8, "life": 0.9, "pierce": 99, "slow": 2.0, "sound": "ice"}
  ]
}
```

2. Mettez son identifiant dans la liste `spells` d'une classe (`classes.json`). La barre de sorts affiche 4 emplacements.

Champs d'un sort : `level` (niveau requis), `mana`, `cd` (recharge en secondes), `mult` (dégâts en multiple des dégâts d'arme ; 2.2 = 220 %), `target` (`aim` vise le curseur, `ground` vise le sol sous le curseur), `range` (portée maximale du point visé), `icon` (pictogramme).

## Effets (sorts et artefacts)

Un sort ou un artefact enchaîne une liste d'effets. Chaque effet accepte aussi ces paramètres communs :

- `mult` : multiplie la puissance du sort (1 par défaut). `mult_abs` donne une puissance absolue qui ignore celle du sort.
- `color`, `sound`
- `at` : `self` (le héros) ou `target` (le point visé). `range` limite la distance du point visé.
- `then` : effets déclenchés ensuite (à l'atterrissage, à l'arrivée, à l'explosion).
- `fail_text` : message affiché si le premier effet n'a pas pu se déclencher. Dans ce cas, le sort n'est pas lancé et ne coûte rien.

| Type | Paramètres principaux |
|---|---|
| `projectile` | `speed`, `radius`, `life`, `count` + `spread` (en éventail, en degrés) ou `radial` (en couronne), `pierce`, `explode` (rayon d'explosion), `slow`, `knock`, `kind` (`bolt`, `arrow`, `fire`) |
| `nova` | cercle autour du héros : `radius`, `knock`, `stun`, `slow`, `damage` (false = sans dégâts), `heal_per_hit` (% de vie par ennemi touché), `spin`, `style` (`frost`, `souls`), `shake` |
| `blast` | explosion (éventuellement retardée) : `radius`, `delay`, `stun`, `slow`, `knock`, `style` (`meteor`) |
| `line` | explosions en ligne vers le curseur : `count`, `start`, `spacing`, `radius`, `delay`, `delay_step` |
| `zone` | zone au sol : `kind` (`fire`, `arrows`, `holy`, `heal`), `radius`, `duration`, `tick` |
| `buff` | effet temporaire : `id` (défini dans `buffs.json`), `duration`, `value` |
| `heal` | `pct` : % de la vie maximum |
| `restore_mana` | `pct` : % du mana maximum |
| `leap` | bond vers le point visé : `range`, `duration`, puis `then` |
| `dash` | charge : `distance`, `duration`, `invuln`, `direction` (`move` = direction du déplacement), puis `then` |
| `teleport` | `range`, `invuln`, puis `then` |
| `shadowstep` | se place derrière l'ennemi le plus proche du curseur et le frappe : `range`, `crit_bonus` |
| `trap` | piège qui explose au contact : `range`, `radius`, `knock` |
| `strikes` | foudre sur plusieurs ennemis : `search` (rayon de recherche), `count`, `stun`, `stagger` (délai entre les impacts) |
| `summon` | `minion` (`skeleton` ou `wisp`), `count`, `duration`, `cap` (maximum simultané) |
| `curse` | les ennemis maudits subissent plus de dégâts : `radius`, `duration`, `amp` (%), `slow` |
| `multi_strike` | frappes circulaires successives : `count`, `interval`, `radius`, `knock`, `invuln` |
| `fx` | effet purement visuel : `ring` `[rayon début, rayon fin, durée]`, `particles`, `shake`, `text` |

Dans `artifacts.json`, `"v"` vaut la puissance de l'artefact (champ `base` × rareté × amélioration) et `"v%"` vaut cette puissance divisée par 100. Exemple : `"mult_abs": "v%"` avec `base` 220 inflige 220 % des dégâts d'arme.

Sons disponibles : `arrow`, `chest`, `click`, `death`, `explosion`, `fire`, `gold`, `hit`, `hurt`, `ice`, `levelup`, `magic`, `pickup`, `portal`, `potion`, `roar`, `seal`, `swing`.

Pictogrammes disponibles : `whirl`, `shout`, `leap`, `quake`, `flame`, `meteor`, `snow`, `blink`, `shadow`, `fan`, `fan_daggers`, `trap`, `arrow`, `rain`, `shield`, `aegis`, `sun`, `pillar`, `bone`, `skull`, `curse`, `harvest`, `dagger`, `blades`, `drop`, `sword`, `axe`, `orb`, `heart`, `bolt`, `eye`, `clock`, `boot`, `fist`, `summon`, `star`.

## Effets temporaires (`buffs.json`)

Chaque effet a un `name` et une `color`, plus des statistiques : `dmg_pct` (% de dégâts en plus), `armor_pct` (% d'armure en plus), `dr` (% de dégâts subis en moins), `move_pct` (% de vitesse en plus), `atk_speed` (% de vitesse d'attaque en plus), `poison` (les attaques empoisonnent : fraction des dégâts d'arme infligée chaque seconde).

Une statistique égale à `"v"` prend la valeur transmise par l'effet `buff` (utile pour les artefacts). `visual` vaut `ring`, `bubble` ou `glow`. `hidden: true` masque l'effet sous les cœurs.

## Talents (`talents.json`)

Chaque classe a 3 branches de 4 talents. Le talent du palier *n* demande `tier_cost × n` points déjà investis dans sa branche. `ranks` fixe le nombre de rangs de chaque palier. Chaque effet s'écrit `[type, clé, valeur par rang]` :

- `["stat", clé, v]`, avec comme clé : `dmg_pct`, `spell_pct`, `basic_pct`, `crit`, `crit_dmg`, `atk_speed`, `move_speed`, `cdr`, `max_hp_pct`, `mana_pct`, `mana_regen_pct`, `armor_pct`, `dr`, `lifesteal`, `roll_cd`, `summon_pct`, `curse_amp`, `dot_pct`, `gold_find`
- `["sd", sort, v]` : % de dégâts en plus pour ce sort. `["sc", sort, v]` : % de recharge en moins pour ce sort.
- `["flag", clé, v]`, avec comme clé : `kill_cdr`, `free_cast`, `execute`, `first_strike`, `berserk`, `low_hp_dr`, `last_stand`, `mana_on_kill`, `kill_heal`, `heal_on_spell`, `crit_heal`, `thorns`, `extra_summon`

`icon` accepte un pictogramme ou `spell:<id du sort>`.

## Personnages animés (`rig`)

Chaque classe peut utiliser un personnage animé (fichier `.glb` de `assets/models/characters`) :

```json
"rig": {"model": "knight", "colors": {"Skin": "skin", "Hair_White": "hair", "Blue": "main", "Beige": "second", "Gold": "hide"},
        "skip": ["hood"]}
```

`colors` associe un matériau du modèle à `skin` (teint), `hair` (cheveux), `main` / `second` (couleurs de tenue choisies par le joueur), éventuellement assombries (`main:0.7`), ou `hide` pour le masquer. `skip` retire des pièces d'équipement que le modèle possède déjà (capuche…). Sans `rig`, ou si le fichier manque, le héros procédural est utilisé.

Les monstres et les boss peuvent aussi avoir un `rig` dans leur `model` (`monsters.json`, `bosses.json`) : le modèle procédural reste utilisé si le fichier manque. Options en plus :

- `height` : taille par rapport à un héros (0.5 = moitié) ; `speed` : vitesse des animations.
- `anims` : animation à jouer pour un état (`idle`, `run`, `attack_melee`, `attack_ranged`, `hit`, `death`), par exemple `{"attack_melee": "Headbutt"}`. Sans précision, le jeu choisit l'équivalent du modèle (Punch, Spider_Attack, Flying_Idle...).
- Modèles de monstres fournis : `zombie`, `orc`, `ghost`, `ghost_skull`, `spider` (assets/models/characters).

## Ajouter une classe

Ajoutez une entrée dans `classes.json` (copier une classe existante est le plus simple), avec ses 4 sorts dans `spells.json` et son arbre dans `talents.json` sous le même identifiant. Dans `model`, `"main"` et `"second"` désignent les deux couleurs de tenue choisies par le joueur. Les pièces possibles sont : `robe`, `cape`, `hood`, `hat`, `helmet`, `horns`, `mask`, `pauldrons`, `tabard`, `shield`, `quiver`, `orb`, `fur`, `gloves`, `bracers`, `belt`, etc. `weapon` vaut `axe`, `staff`, `bow`, `sword`, `scythe` ou `daggers`. Le champ `headgear` liste les pièces affichées quand le couvre-chef est visible.

## Monstres et boss

`monsters.json` : `hp`, `dmg` `[min, max]`, `speed`, `radius`, `ai` (`melee`, `ranged`, `caster`, `brute`), `range`, `cd`, `windup` (temps d'avertissement avant l'attaque), `xp`, `floor` (premier étage où le monstre apparaît), `model` (apparence).

`bosses.json` : `abilities` liste des `[technique, intervalle en phase 1 (null = inactive), intervalle en phase 2]`. Techniques possibles :

| Technique | Effet |
|---|---|
| `charge`, `slam`, `bolts`, `nova`, `blink`, `boulders`, `waves` | charge, frappe au sol, projectiles, onde, téléportation, rochers, ondes de choc |
| `summon` | invoque `summon_monster` (`summon_count` : [phase 1, phase 2]) |
| `leap` | bond sur la position annoncée du joueur |
| `webs` | toiles au sol qui ralentissent fortement le joueur |
| `beam` | rayon qui balaie l'arène en tournant autour du boss |
| `shield` | invulnérable tant que ses pylônes de cristal tiennent (une fois par phase) |
| `firestorm` | pluie de feu annoncée sur toute l'arène |
| `vortex` | aspire le joueur puis explose autour du boss |
| `clones` | illusions du boss qui tirent à distance |

`fx_color` colore les effets du boss. `order` fixe l'ordre des boss d'un étage à l'autre (un par étage, puis en boucle).

### Étage BOSS : Deathstrake, esprit de la tour

`special` (dans `bosses.json`) : `{"boss": "deathstrake", "every": 10}` — tous les 10 étages (10, 20), le gardien normal est remplacé par ce boss, seul dans une grande arène (pas de monstres ni de sceau). Deathstrake a le modèle du paladin et retourne contre le héros les pouvoirs des artefacts :

| Technique | Effet |
|---|---|
| `fireball` | boule(s) de feu visée(s) qui explosent à l'impact |
| `crown` | couronne de boules de feu tout autour de lui |
| `meteor` | météore annoncé sur le héros, puis sol embrasé |
| `lightning` | éclairs successifs sur la position du héros |
| `frost` | onde de givre : le héros touché est gelé (très ralenti) |
| `horn` | onde qui repousse violemment le héros |
| `chains` | chaînes : +30 % de dégâts subis et ralenti pendant 6 s |
| `runes` | runes explosives autour du héros |
| `shadowstep` | surgit derrière le héros et frappe |
| `wisps` | feux follets qui pourchassent le héros |
| `summon` | lève des squelettes (`summon_monster`, `summon_count`) |
| `totem` | totem qui le soigne tant qu'il n'est pas détruit |
| `ward` | écu sacré : -60 % de dégâts subis pendant 5 s |
| `haste` / `enrage` | plus rapide 5 s / +40 % de dégâts 7 s |

## Quêtes (`quests.json`)

Chaque quête est donnée par un habitant de Cendreval (`giver`). Un « ! » doré au-dessus de sa tête signale une quête à prendre, un « ? » doré une quête terminée à lui rendre (un « ? » gris : quête en cours). Les quêtes (en cours, à rendre, terminées) se consultent dans l'onglet « Quêtes » du menu (Échap, ou touche J).

```json
"os_sans_repos": {
  "name": "Des os sans repos", "giver": "anselme",
  "desc": "Résumé de la quête.",
  "intro": "Ce que dit l'habitant quand il propose la quête.",
  "progress": "Ce qu'il dit tant qu'elle n'est pas terminée.",
  "done": "Ce qu'il dit quand on la lui rend.",
  "requires": ["le_seuil"], "min_level": 1,
  "objectives": [{"type": "kill", "monster": "squelette", "count": 15}],
  "reward": {"gold": 80, "xp": 180, "item": "magique"}
}
```

Habitants : `gorvan`, `hilda`, `ysolde`, `elise`, `anselme`, `mira`, `aldebert`, `garde_nord`, `garde_sud`, `garde_ronde` (liste dans `game/town.py`). `turn_in` désigne un autre habitant à qui rendre la quête. `requires` : quêtes à avoir rendues avant.

| Objectif | Paramètres |
|---|---|
| `kill` | `count`, `monster` (identifiant de `monsters.json`, sinon n'importe quel monstre), `elite` (`true` : élites seulement), `min_floor` |
| `boss` | `count`, `floor` (un étage précis, sinon n'importe quel gardien) |
| `clear` | `floor` : gardien de cet étage déjà vaincu (compte aussi s'il l'a été avant la quête) |
| `floor` | `floor` : étage atteint |
| `talk` | `npc` : parler à cet habitant |

Chaque objectif accepte `text` pour remplacer le texte affiché. `item` de la récompense : `commun`, `magique`, `rare` ou `legendaire` (un objet adapté à la classe du héros).

## Notes de mise à jour

Pour publier une nouvelle version, ajoutez `updates/<version>.json` :

```json
{
  "version": "2.2", "date": "2026-10-15", "title": "Titre de la mise à jour",
  "sections": [{"name": "Nouveautés", "notes": ["…", "…"]}]
}
```

La version la plus récente s'affiche en haut de la boîte « Notes de mise à jour » du menu Système.

## Modèles 3D

Les modèles importés (`.obj` + `.mtl`) se trouvent dans `assets/models`. Leur liste est dans `assets/models/models.json`, rangée par familles :

| Famille | Contenu |
|---|---|
| `pine`, `leafy`, `bush`, `rock`, `mushroom`, `stump`, `flower`, `grass`, `log` | Nature Kit : placés au hasard dans le décor |
| `town` | Fantasy Town Kit : murs des maisons, étal, charrette, lanternes, clôtures… |
| `camp` | Survival Kit : enclume, établis, tonneaux, caisses… |

Réglages d'une famille :
- `scale` : taille (1 unité du fichier = 1 case) ;
- `palette` : remplace les couleurs unies des matériaux ;
- `grade` : étalonne les couleurs des kits à texture-palette (`saturation`, `multiply` `[r, v, b]`, `brightness`) ;
- `normals_up` : éclaire un feuillage fin comme le sol.

Pour ajouter un modèle, copiez son `.obj`, son `.mtl` et sa texture dans le dossier du kit, puis ajoutez son nom à une famille. Les maisons du hameau (position, taille, étages, couleur du toit) sont définies dans `HOUSES`, dans `game/r3d/camp.py`.
