"""Règles du jeu et accès au contenu.

Les classes, sorts, talents, monstres, boss, anima, artefacts et enchantements sont décrits dans les fichiers
JSON du dossier data/ (modifiables à tout moment) et chargés par content.py. Ce module expose les mêmes
noms qu'auparavant (CLASSES, SPELLS...) pour le reste du code.
"""
from .content import CONTENT, ERROR, ContentError

if CONTENT is None:
    raise ContentError(ERROR)


ATTRS = ["force", "dex", "int", "vit", "endurance", "resistance", "harmonie", "foi", "chance"]
ATTR_NAMES = {"force": "Force", "dex": "Dextérité", "int": "Intelligence", "vit": "Vitalité",
              "endurance": "Endurance", "resistance": "Résistance", "harmonie": "Harmonie", "foi": "Foi",
              "chance": "Chance"}
MAX_LEVEL = 100
BAG_SIZE = 40
POINTS_PER_LEVEL = 1         # point de caractéristique gagné à chaque niveau
TEAR_DROP = {"elite": 0.12, "brute": 0.02, "cultiste": 0.015}   # chances de Larme d'oubli (+1 par gardien)
MONSTER_XP = 0.6            # part de l'expérience de base donnée par les monstres (et les gardiens)

# Mécaniques inspirées de Minecraft Dungeons
POTION_CD = 22.0          # potion de soin illimitée, avec temps de recharge
POTION_HEAL = 0.35         # part de la vie maximale rendue par la potion
ROLL_CD = 1.2             # roulade d'esquive (Espace)
ROLL_DIST = 170
ROLL_DUR = 0.28
ARTIFACT_SLOTS = 3


def xp_needed(level):
    return int(90 * level ** 1.55)


# --------------------------------------------------------------------------- contenu (data/*.json)
CLASSES = CONTENT["classes"]
SPELLS = CONTENT["spells"]
BUFFS = CONTENT["buffs"]
MONSTERS = CONTENT["monsters"]
ELITE_AFFIXES = CONTENT["elites"]
BOSSES = CONTENT["bosses"]
for _bid, _b in BOSSES.items():
    _b.setdefault("id", _bid)
    _b.setdefault("ai", "boss")
    _b.setdefault("range", 40)
    _b.setdefault("cd", 1.4)
    _b.setdefault("windup", 0.55)
    _b.setdefault("xp", 300)
BOSS_ORDER = CONTENT["boss_order"]
BOSS_SPECIAL = CONTENT["boss_special"]
FLOOR_NAMES = CONTENT["floors"]
ARTIFACTS = CONTENT["artifacts"]
ARTIFACT_KEYS = CONTENT["art_keys"]
ENCHANTS = CONTENT["enchants"]
ENCH_SLOTS = CONTENT["ench_slots"]
ANIMA_POWERS = CONTENT["anima"]
# (nom, couleur, valeur, poids) : même forme qu'auparavant
ANIMA_TIERS = [(t["name"], t["color"], t["value"], t["weight"]) for t in CONTENT["anima_tiers"]]
_SC = CONTENT["scaling"]

# effet de chaque point d'attribut, pour toutes les classes
ATTR_K = {"force_armor": 0.5, "force_basic": 0.3, "dex_crit": 0.1, "dex_speed": 0.2,
          "int_mana": 1.5, "int_spell": 0.3, "int_regen": 1.0, "vit_hp": 5,
          "foi_heal": 0.6, "foi_cdr": 0.1, "chance_gold": 0.8, "chance_crit": 0.05, "chance_drop": 0.6,
          "end_roll": 0.4, "end_potion": 0.25, "end_move": 0.1,        # Endurance (plafond : -40% de recharge)
          "res_dr": 0.08, "res_armor": 0.3, "res_snare": 0.8,          # Résistance
          "harm_cost": 0.25, "harm_regen": 0.04}                        # Harmonie (plafond : -40% de coût)
# effets d'un point, une ligne chacun (infobulles de la page Personnage)
ATTR_LINES = {"force": ["+0,5 armure", "+0,3% de dégâts de l'attaque de base"],
              "dex": ["+0,1% de chances de critique", "+0,2% de vitesse d'attaque"],
              "int": ["+1,5 mana", "+0,3% de dégâts des sorts", "+1% de régénération de mana"],
              "vit": ["+5 points de vie"],
              "endurance": ["-0,4% de recharge de la roulade", "-0,25% de recharge de la potion",
                            "+0,1% de vitesse de déplacement"],
              "resistance": ["+0,08% de réduction des dégâts subis", "+0,3 armure",
                             "Entraves et ralentissements 0,8% plus courts"],
              "harmonie": ["-0,25% de coût en mana des sorts", "+0,04 mana par seconde"],
              "foi": ["+0,6% d'efficacité des soins reçus", "-0,1% de temps de recharge des sorts"],
              "chance": ["+0,8% d'or trouvé", "+0,05% de chances de critique", "+0,6% de chances de butin"]}
ATTR_LORE = {"force": "La puissance brute des bras et des épaules.",
             "dex": "La précision du geste et la vivacité de la main.",
             "int": "La maîtrise des arts arcaniques.",
             "vit": "La robustesse du corps.",
             "endurance": "Le souffle qui permet de rouler et de courir encore.",
             "resistance": "La peau tannée par les coups, qui ne cède plus.",
             "harmonie": "L'accord entre l'esprit et la magie : chaque sort coûte moins.",
             "foi": "La confiance en une lumière plus grande que soi.",
             "chance": "Le hasard qui sourit aux audacieux."}
ATTR_USERS = {a: [c["name"] for c in CLASSES.values() if c["primary"] == a] for a in ATTRS}
ATTR_DESC = {a: " · ".join(ATTR_LINES[a]) + " par point" for a in ATTRS}


def floor_name(f):
    return FLOOR_NAMES[(f - 1) % len(FLOOR_NAMES)]


def boss_floor(f):
    """Étage spécial : arène du boss « special » (Deathstrake), tous les « every » étages."""
    return bool(BOSS_SPECIAL) and f % BOSS_SPECIAL.get("every", 10) == 0


def floor_boss(f):
    if boss_floor(f):
        return BOSS_SPECIAL["boss"]
    return BOSS_ORDER[(f - 1) % len(BOSS_ORDER)]


def floor_scaling(f):
    """Multiplicateurs (vie, dégâts) des monstres selon l'étage (monsters.json, « scaling »)."""
    n = f - 1
    return (1 + _SC["hp"][0] * n + _SC["hp"][1] * n * n, 1 + _SC["dmg"][0] * n + _SC["dmg"][1] * n * n)


def anima_desc(pid, points):
    p = ANIMA_POWERS[pid]
    return p["desc"].format(v=int(p["per"] * points))


def ench_value(eid, level):
    return ENCHANTS[eid]["vals"][max(1, min(3, level)) - 1] if level > 0 else 0
