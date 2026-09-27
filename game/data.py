"""Règles du jeu et accès au contenu.

Les classes, sorts, talents, monstres, boss, anima, artefacts et enchantements sont décrits dans les fichiers
JSON du dossier data/ (modifiables à tout moment) et chargés par content.py. Ce module expose les mêmes
noms qu'auparavant (CLASSES, SPELLS...) pour le reste du code.
"""
from .content import CONTENT, ERROR, ContentError

if CONTENT is None:
    raise ContentError(ERROR)


ATTRS = ["force", "dex", "int", "vit"]
ATTR_NAMES = {"force": "Force", "dex": "Dextérité", "int": "Intelligence", "vit": "Vitalité"}
MAX_LEVEL = 60
BAG_SIZE = 40
POINTS_PER_LEVEL = 1         # point de caractéristique gagné à chaque niveau

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

_ATTR_EFFECT = {"force": "+0,5 armure par point", "dex": "+0,05% de critique par point",
                "int": "+1,5 mana par point", "vit": "+5 points de vie par point"}
ATTR_DESC = {}
for _a in ATTRS:
    _users = [c["name"] for c in CLASSES.values() if c["primary"] == _a]
    ATTR_DESC[_a] = (f"Dégâts du {' et du '.join(_users)}, " if _users else "") + _ATTR_EFFECT[_a]


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
