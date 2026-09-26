"""Données de jeu : classes, sorts, monstres, boss, étages et pouvoirs d'anima."""

ATTRS = ["force", "dex", "int", "vit"]
ATTR_NAMES = {"force": "Force", "dex": "Dextérité", "int": "Intelligence", "vit": "Vitalité"}
ATTR_DESC = {
    "force": "Dégâts du Barbare, +0,5 armure par point",
    "dex": "Dégâts du Chasseur, +0,05% de critique par point",
    "int": "Dégâts du Sorcier, +1,5 mana par point",
    "vit": "+5 points de vie par point",
}
MAX_LEVEL = 60
BAG_SIZE = 40
POINTS_PER_LEVEL = 5

# Mécaniques inspirées de Minecraft Dungeons
POTION_CD = 22.0          # potion de soin illimitée, avec temps de recharge
POTION_HEAL = 0.5
ROLL_CD = 1.2             # roulade d'esquive (Espace)
ROLL_DIST = 170
ROLL_DUR = 0.28
ARTIFACT_SLOTS = 3


def xp_needed(level):
    return int(90 * level ** 1.55)


# --------------------------------------------------------------------------- classes
CLASSES = {
    "barbare": {
        "name": "Barbare",
        "title": "Fureur des Hautes-Terres",
        "desc": "Un colosse des steppes gelées. Il excelle au corps à corps, encaisse les coups "
                "et fend les hordes. Chaque coup porté régénère sa fureur (mana).",
        "color": (200, 90, 55),
        "primary": "force",
        "attrs": {"force": 20, "dex": 10, "int": 6, "vit": 16},
        "hp": 140, "hp_lvl": 14, "mana": 60, "mana_lvl": 2, "mana_regen": 3.0,
        "speed": 205,
        "attack": {"kind": "melee", "name": "Frappe brutale", "mult": 1.0, "range": 64, "arc": 120,
                   "cd": 0.5, "mana_gain": 3, "color": (230, 200, 170)},
        "spells": ["tourbillon", "cri_guerre", "bond", "seisme"],
        "weapons": ["Hache de guerre", "Épée longue", "Masse d'armes", "Fléau"],
    },
    "sorcier": {
        "name": "Sorcier",
        "title": "Érudit de l'Arcane",
        "desc": "Maître des éléments, il anéantit ses ennemis à distance. Fragile, mais sa "
                "puissance de feu est inégalée et il peut se téléporter hors de danger.",
        "color": (130, 110, 240),
        "primary": "int",
        "attrs": {"force": 6, "dex": 10, "int": 22, "vit": 12},
        "hp": 100, "hp_lvl": 10, "mana": 110, "mana_lvl": 5, "mana_regen": 7.0,
        "speed": 200,
        "attack": {"kind": "projectile", "name": "Trait arcanique", "mult": 0.9, "speed": 640,
                   "cd": 0.42, "color": (170, 120, 255), "life": 0.9, "radius": 6},
        "spells": ["boule_feu", "nova_givre", "teleport", "meteore"],
        "weapons": ["Bâton", "Baguette", "Orbe", "Sceptre"],
    },
    "chasseur": {
        "name": "Chasseur",
        "title": "Traqueur des Ombres",
        "desc": "Archer agile et mortel. Il garde ses distances, pose des pièges explosifs "
                "et crible ses proies d'une pluie de flèches.",
        "color": (100, 175, 85),
        "primary": "dex",
        "attrs": {"force": 9, "dex": 22, "int": 8, "vit": 13},
        "hp": 115, "hp_lvl": 12, "mana": 80, "mana_lvl": 3, "mana_regen": 5.5,
        "speed": 220,
        "attack": {"kind": "projectile", "name": "Flèche", "mult": 0.95, "speed": 820,
                   "cd": 0.36, "color": (235, 215, 165), "life": 0.75, "radius": 5, "arrow": True},
        "spells": ["tir_multiple", "piege", "fleche_perforante", "pluie_fleches"],
        "weapons": ["Arc court", "Arc long", "Arbalète", "Arc composite"],
    },
}

# --------------------------------------------------------------------------- sorts
# level = niveau de déblocage ; mult = multiplicateur de dégâts d'arme
SPELLS = {
    # Barbare
    "tourbillon": dict(name="Tourbillon", level=1, mana=18, cd=2.5, mult=1.7, color=(230, 130, 60),
                       desc="Tournoie sur vous-même et frappe tous les ennemis proches (170% dégâts d'arme)."),
    "cri_guerre": dict(name="Cri de guerre", level=3, mana=20, cd=14, mult=0, color=(240, 60, 40),
                       desc="+35% de dégâts et +50% d'armure pendant 8 s."),
    "bond": dict(name="Bond", level=6, mana=20, cd=6, mult=2.2, color=(210, 170, 90),
                 desc="Bondit vers le curseur, inflige 220% de dégâts à l'atterrissage et étourdit."),
    "seisme": dict(name="Séisme", level=10, mana=35, cd=8, mult=1.5, color=(200, 120, 50),
                   desc="Une série d'ondes de choc déchire le sol devant vous (150% par onde)."),
    # Sorcier
    "boule_feu": dict(name="Boule de feu", level=1, mana=14, cd=0.8, mult=2.0, color=(255, 120, 30),
                      desc="Projectile qui explose au contact (200% dégâts d'arme en zone)."),
    "nova_givre": dict(name="Nova de givre", level=3, mana=28, cd=7, mult=1.1, color=(120, 200, 255),
                       desc="Onde glaciale : 110% de dégâts et ralentit fortement les ennemis."),
    "teleport": dict(name="Téléportation", level=6, mana=18, cd=5, mult=0.8, color=(170, 120, 255),
                     desc="Vous téléporte jusqu'au curseur et libère une onde arcanique."),
    "meteore": dict(name="Météore", level=10, mana=45, cd=8, mult=5.0, color=(255, 90, 20),
                    desc="Invoque un météore dévastateur (500%) qui laisse le sol en feu."),
    # Chasseur
    "tir_multiple": dict(name="Tir multiple", level=1, mana=14, cd=1.0, mult=0.9, color=(230, 210, 150),
                         desc="Tire une volée de 7 flèches en éventail (90% chacune)."),
    "piege": dict(name="Piège explosif", level=3, mana=18, cd=4, mult=3.0, color=(255, 170, 60),
                  desc="Pose un piège qui explose au passage d'un ennemi (300% en zone)."),
    "fleche_perforante": dict(name="Flèche perforante", level=6, mana=16, cd=3, mult=2.6, color=(150, 230, 170),
                              desc="Une flèche lourde qui transperce tous les ennemis alignés (260%)."),
    "pluie_fleches": dict(name="Pluie de flèches", level=10, mana=40, cd=9, mult=0.6, color=(250, 230, 160),
                          desc="Une pluie de flèches s'abat sur la zone pendant 3 s (60% par salve)."),
}

# --------------------------------------------------------------------------- monstres
MONSTERS = {
    "squelette": dict(name="Squelette", hp=34, dmg=(5, 8), speed=100, radius=14, ai="melee",
                      range=26, cd=1.2, windup=0.4, xp=12, floor=1),
    "zombie": dict(name="Goule putride", hp=62, dmg=(8, 12), speed=62, radius=16, ai="melee",
                   range=28, cd=1.6, windup=0.55, xp=16, floor=1),
    "archer": dict(name="Archer squelette", hp=26, dmg=(5, 8), speed=90, radius=14, ai="ranged",
                   range=330, cd=1.9, windup=0.45, xp=14, floor=1,
                   proj_speed=340, proj_color=(235, 220, 180)),
    "diablotin": dict(name="Diablotin", hp=24, dmg=(3, 6), speed=165, radius=12, ai="melee",
                      range=22, cd=0.8, windup=0.25, xp=10, floor=2),
    "cultiste": dict(name="Cultiste des Tourments", hp=42, dmg=(8, 12), speed=85, radius=14, ai="caster",
                     range=360, cd=2.8, windup=0.7, xp=20, floor=3),
    "brute": dict(name="Brute démoniaque", hp=140, dmg=(14, 20), speed=78, radius=21, ai="brute",
                  range=40, cd=2.2, windup=0.8, xp=36, floor=4),
}

ELITE_AFFIXES = {
    "Véloce": {"speed": 1.45, "cd": 0.8},
    "Vampirique": {"leech": 0.6},
    "Robuste": {"hp": 1.6},
    "Frénétique": {"cd": 0.55},
    "Colossal": {"hp": 1.3, "radius": 1.2, "dmg": 1.3},
}

BOSSES = {
    "boucher": dict(id="boucher", name="Le Boucher", title="Geôlier des chairs", hp=650, dmg=(12, 18),
                    speed=125, radius=28, ai="boss", range=40, cd=1.3, windup=0.5, xp=260),
    "liche": dict(id="liche", name="Varkul la Liche", title="Gardienne de l'Ossuaire", hp=560, dmg=(10, 15),
                  speed=95, radius=24, ai="boss", range=40, cd=1.3, windup=0.5, xp=300),
    "golem": dict(id="golem", name="Golem d'ossements", title="Colosse des Forges", hp=900, dmg=(16, 24),
                  speed=72, radius=34, ai="boss", range=50, cd=1.8, windup=0.7, xp=340),
    "seigneur": dict(id="seigneur", name="Mal'zahar", title="Seigneur des Tourments", hp=1150, dmg=(15, 22),
                     speed=115, radius=30, ai="boss", range=44, cd=1.4, windup=0.55, xp=500),
}
BOSS_ORDER = ["boucher", "liche", "golem", "seigneur"]

FLOOR_NAMES = [
    "Les Geôles Maudites", "L'Ossuaire", "Les Forges Hurlantes", "Le Sanctuaire Profané",
    "Les Cryptes de Givre", "La Fosse aux Âmes", "Les Chambres Écarlates", "Le Trône du Tourment",
]


def floor_name(f):
    return FLOOR_NAMES[(f - 1) % len(FLOOR_NAMES)]


def floor_boss(f):
    return BOSS_ORDER[(f - 1) % len(BOSS_ORDER)]


def floor_scaling(f):
    """Multiplicateurs (vie, dégâts) des monstres selon l'étage."""
    n = f - 1
    return 1 + 0.55 * n + 0.08 * n * n, 1 + 0.30 * n + 0.03 * n * n


# --------------------------------------------------------------------------- anima
# Pouvoirs temporaires (une ascension), comme dans Torghast. Ils sont rares et ont trois paliers :
# Commun (x1), Rare (x2), Épique (x3). « per » est la valeur par point.
ANIMA_TIERS = [("Commun", (200, 200, 200), 1, 64), ("Rare", (90, 160, 255), 2, 28), ("Épique", (190, 110, 255), 3, 8)]
ANIMA_POWERS = {
    "rage": dict(name="Rage sanguinaire", desc="+{v}% de dégâts.", per=15, color=(220, 60, 40)),
    "carapace": dict(name="Carapace d'os", desc="-{v}% de dégâts subis.", per=7, color=(200, 190, 160)),
    "soif": dict(name="Soif de sang", desc="+{v}% de vol de vie.", per=3, color=(180, 20, 40)),
    "esprit": dict(name="Esprit vif", desc="-{v}% de temps de recharge.", per=10, color=(120, 200, 255)),
    "ombre": dict(name="Pas de l'ombre", desc="+{v}% de vitesse de déplacement.", per=9, color=(140, 140, 190)),
    "precision": dict(name="Œil du prédateur", desc="+{v}% de chances de coup critique.", per=6, color=(250, 220, 90)),
    "flux": dict(name="Flux arcanique", desc="+{v}% de régénération de mana.", per=45, color=(90, 130, 255)),
    "vigueur": dict(name="Vigueur ancestrale", desc="+{v}% de vie maximum.", per=18, color=(90, 200, 90)),
    "nova_mort": dict(name="Nova funeste", desc="Les ennemis tués explosent ({v}% dégâts d'arme).", per=60,
                      color=(170, 60, 220)),
    "givre": dict(name="Éclats de givre", desc="{v}% de chances de ralentir les ennemis touchés.", per=14,
                  color=(170, 230, 255)),
    "cupidite": dict(name="Cupidité", desc="+{v}% d'or trouvé.", per=45, color=(255, 200, 60)),
    "frenesie": dict(name="Frénésie", desc="+{v}% de vitesse d'attaque.", per=13, color=(255, 120, 60)),
    "ferveur": dict(name="Ferveur", desc="Chaque ennemi tué rend {v}% de vie.", per=3, color=(240, 100, 140)),
    "seconde": dict(name="Phylactère", desc="Vous ressuscitez une fois avec {v}% de vie.", per=30,
                    color=(160, 255, 200), unique=True),
    "tourbillon": dict(name="Âmes tourbillonnantes", desc="{v} âmes tournent autour de vous et blessent les ennemis.",
                       per=1, color=(150, 230, 255)),
}


def anima_desc(pid, points):
    p = ANIMA_POWERS[pid]
    return p["desc"].format(v=int(p["per"] * points))


# --------------------------------------------------------------------------- artefacts (Minecraft Dungeons)
# Objets actifs à équiper dans 3 emplacements (touches R, T, G). Leur puissance dépend du niveau d'objet.
ARTIFACTS = {
    "totem": dict(name="Totem de régénération", cd=24, color=(110, 230, 120),
                  desc="Plante un totem qui soigne de {v}% de vie par seconde dans sa zone pendant 6 s."),
    "foudre": dict(name="Pierre d'orage", cd=10, color=(150, 190, 255),
                   desc="La foudre frappe jusqu'à 6 ennemis proches ({v}% dégâts d'arme)."),
    "corne": dict(name="Corne du Tourment", cd=14, color=(230, 180, 110),
                  desc="Repousse violemment les ennemis proches et les étourdit 1,5 s."),
    "bottes": dict(name="Bottes de célérité", cd=16, color=(120, 220, 230),
                   desc="+{v}% de vitesse de déplacement pendant 5 s."),
    "talisman": dict(name="Talisman de fer", cd=22, color=(200, 200, 210),
                     desc="Réduit les dégâts subis de {v}% pendant 5 s."),
    "gel": dict(name="Orbe de givre", cd=16, color=(170, 230, 255),
                desc="Gèle les ennemis proches pendant 3 s et leur inflige {v}% dégâts d'arme."),
    "crane": dict(name="Crâne infernal", cd=12, color=(255, 120, 50),
                  desc="Libère une couronne de 10 boules de feu ({v}% dégâts d'arme chacune)."),
    "fiole": dict(name="Fiole d'essence", cd=25, color=(110, 150, 255),
                  desc="Rend instantanément {v}% de votre mana."),
    "lanterne": dict(name="Lanterne des âmes", cd=20, color=(160, 255, 220),
                     desc="Invoque un feu follet allié qui attaque pendant 10 s ({v}% dégâts d'arme)."),
}
ARTIFACT_KEYS = ["R", "T", "G"]

# --------------------------------------------------------------------------- enchantements (Minecraft Dungeons)
# Chaque objet (hors bijoux communs) a des emplacements d'enchantement. Pour chacun, on choisit 1 enchantement
# parmi 3, puis on l'améliore (niveaux 1 à 3) avec des points d'enchantement gagnés en montant de niveau.
ENCHANTS = {
    # armes
    "tranchant": dict(name="Tranchant", kind="arme", vals=(10, 20, 30), desc="+{v}% de dégâts."),
    "acuite": dict(name="Acuité", kind="arme", vals=(5, 10, 15), desc="+{v}% de chances de coup critique."),
    "vivacite": dict(name="Vivacité", kind="arme", vals=(8, 16, 24), desc="+{v}% de vitesse d'attaque."),
    "echo": dict(name="Écho", kind="arme", vals=(10, 18, 26), desc="{v}% de chances que l'attaque frappe deux fois."),
    "chaine": dict(name="Chaîne", kind="arme", vals=(12, 20, 28),
                   desc="{v}% de chances d'enchaîner 2 ennemis proches (60%)."),
    "embrasement": dict(name="Embrasement", kind="arme", vals=(15, 25, 35),
                        desc="{v}% de chances d'enflammer la cible (brûlure sur 3 s)."),
    "tempete": dict(name="Tempête", kind="arme", vals=(8, 14, 20),
                    desc="{v}% de chances d'appeler la foudre sur la cible (150% en zone)."),
    "entrave": dict(name="Entrave", kind="arme", vals=(15, 25, 35), desc="{v}% de chances de ralentir la cible."),
    "vampirisme": dict(name="Vampirisme", kind="arme", vals=(2, 4, 6), desc="Tuer un ennemi rend {v}% de vie."),
    # armures et bijoux
    "celerite": dict(name="Célérité", kind="armure", vals=(5, 10, 15), desc="+{v}% de vitesse de déplacement."),
    "rempart": dict(name="Rempart", kind="armure", vals=(4, 8, 12), desc="-{v}% de dégâts subis."),
    "ame_soin": dict(name="Âme bienfaitrice", kind="armure", vals=(1, 2, 3), desc="Tuer un ennemi rend {v}% de vie."),
    "recharge": dict(name="Recharge", kind="armure", vals=(5, 10, 15), desc="-{v}% de temps de recharge."),
    "potion_vive": dict(name="Potion vive", kind="armure", vals=(12, 24, 36),
                        desc="-{v}% de temps de recharge de la potion."),
    "esquive": dict(name="Esquive", kind="armure", vals=(5, 9, 13), desc="{v}% de chances d'éviter un coup."),
    "epines": dict(name="Épines", kind="armure", vals=(25, 50, 75),
                   desc="Renvoie {v}% des dégâts de mêlée à l'attaquant."),
    "riposte": dict(name="Riposte ardente", kind="armure", vals=(15, 25, 35),
                    desc="{v}% de chances de libérer une nova de feu quand vous êtes touché."),
    "vitalite": dict(name="Vitalité", kind="armure", vals=(6, 12, 18), desc="+{v}% de vie maximum."),
    "agilite": dict(name="Agilité", kind="armure", vals=(12, 24, 36), desc="-{v}% de recharge de la roulade."),
}
ENCH_SLOTS = {"commun": 0, "magique": 1, "rare": 2, "legendaire": 3}


def ench_value(eid, level):
    return ENCHANTS[eid]["vals"][max(1, min(3, level)) - 1] if level > 0 else 0
