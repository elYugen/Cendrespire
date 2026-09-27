"""Chargement du contenu modifiable (dossier data/ en JSON) : classes, sorts, talents, monstres, boss,
anima, artefacts, enchantements, effets temporaires.

- Les fichiers sont lus au démarrage ; une erreur produit un message clair (fichier, élément, champ).
- Un fichier du même nom placé dans le dossier utilisateur « data » (à côté des sauvegardes) remplace celui du
  jeu : pratique pour modder une version installée sans toucher au dossier d'installation.
"""
import json
import os

from .settings import ROOT_DIR, SAVE_DIR

DATA_DIR = os.path.join(ROOT_DIR, "data")
USER_DATA_DIR = os.path.join(os.path.dirname(SAVE_DIR), "data")

# types d'effets de sort / artefact reconnus par le moteur (voir spells.py)
EFFECT_TYPES = {"projectile", "nova", "blast", "line", "zone", "buff", "heal", "restore_mana", "leap", "dash",
                "teleport", "shadowstep", "trap", "strikes", "summon", "curse", "multi_strike", "fx"}
ZONE_KINDS = {"fire", "arrows", "holy", "heal"}
MINIONS = {"skeleton", "wisp"}
AI_TYPES = {"melee", "ranged", "caster", "brute"}
BOSS_ABILITIES = {"charge", "slam", "bolts", "nova", "summon", "blink", "boulders", "waves"}


class ContentError(Exception):
    pass


def _tuples(o):
    """Les listes de 2 à 4 nombres deviennent des tuples (couleurs, fourchettes de dégâts...)."""
    if isinstance(o, dict):
        return {k: _tuples(v) for k, v in o.items()}
    if isinstance(o, list):
        if 2 <= len(o) <= 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in o):
            return tuple(o)
        return [_tuples(v) for v in o]
    return o


def path_of(name):
    user = os.path.join(USER_DATA_DIR, name)
    return user if os.path.exists(user) else os.path.join(DATA_DIR, name)


def load(name):
    path = path_of(name)
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise ContentError(f"Fichier introuvable : {path}")
    except json.JSONDecodeError as e:
        raise ContentError(f"{name}, ligne {e.lineno}, colonne {e.colno} : JSON invalide ({e.msg}).")
    raw.pop("_info", None)
    return _tuples(raw)


def need(d, keys, where):
    for k in keys:
        if k not in d:
            raise ContentError(f"{where} : champ « {k} » manquant.")


def check_effects(effects, where, spells=None):
    if not isinstance(effects, list) or not effects:
        raise ContentError(f"{where} : « effects » doit être une liste non vide.")
    for i, e in enumerate(effects):
        w = f"{where}, effet n°{i + 1}"
        if not isinstance(e, dict) or e.get("type") not in EFFECT_TYPES:
            raise ContentError(f"{w} : type inconnu « {e.get('type') if isinstance(e, dict) else e} ». "
                               f"Types possibles : {', '.join(sorted(EFFECT_TYPES))}.")
        if e["type"] == "zone" and e.get("kind", "fire") not in ZONE_KINDS:
            raise ContentError(f"{w} : zone « {e.get('kind')} » inconnue ({', '.join(sorted(ZONE_KINDS))}).")
        if e["type"] == "summon" and e.get("minion") not in MINIONS:
            raise ContentError(f"{w} : serviteur « {e.get('minion')} » inconnu ({', '.join(sorted(MINIONS))}).")
        if e["type"] == "buff" and "id" not in e:
            raise ContentError(f"{w} : l'effet buff doit indiquer « id » (voir buffs.json).")
        if "then" in e:
            check_effects(e["then"], w + " (then)")


def load_all():
    """Charge et valide tout le contenu. Renvoie un dictionnaire de sections."""
    c = {}
    c["spells"] = load("spells.json")["spells"]
    for sid, sp in c["spells"].items():
        where = f"spells.json, sort « {sid} »"
        need(sp, ("name", "level", "mana", "cd", "mult", "color", "desc", "effects"), where)
        check_effects(sp["effects"], where)
    c["buffs"] = load("buffs.json")["buffs"]
    for sid, sp in c["spells"].items():
        for e in sp["effects"]:
            if e["type"] == "buff" and e["id"] not in c["buffs"]:
                raise ContentError(f"spells.json, sort « {sid} » : buff « {e['id']} » absent de buffs.json.")
    c["classes"] = load("classes.json")["classes"]
    for cid, cl in c["classes"].items():
        where = f"classes.json, classe « {cid} »"
        need(cl, ("name", "title", "desc", "color", "primary", "attrs", "hp", "hp_lvl", "mana", "mana_lvl",
                  "mana_regen", "speed", "attack", "spells", "weapons", "model"), where)
        for sid in cl["spells"]:
            if sid not in c["spells"]:
                raise ContentError(f"{where} : sort « {sid} » absent de spells.json.")
        need(cl["attack"], ("kind", "name", "mult", "cd"), where + ", attack")
    tal = load("talents.json")
    c["talents"] = tal
    for cid in c["classes"]:
        if cid not in tal["trees"]:
            raise ContentError(f"talents.json : aucun arbre pour la classe « {cid} ».")
    mon = load("monsters.json")
    c["monsters"], c["elites"], c["scaling"] = mon["monsters"], mon["elites"], mon["scaling"]
    for mid, m in c["monsters"].items():
        need(m, ("name", "hp", "dmg", "speed", "radius", "ai", "range", "cd", "windup", "xp", "floor", "model"),
             f"monsters.json, monstre « {mid} »")
        if m["ai"] not in AI_TYPES:
            raise ContentError(f"monsters.json, monstre « {mid} » : ai « {m['ai']} » inconnue "
                               f"({', '.join(sorted(AI_TYPES))}).")
    b = load("bosses.json")
    c["bosses"], c["boss_order"] = b["bosses"], list(b["order"])
    for bid, bo in c["bosses"].items():
        need(bo, ("name", "title", "hp", "dmg", "speed", "radius", "abilities", "model"), f"bosses.json, « {bid} »")
        for ab in bo["abilities"]:
            if ab[0] not in BOSS_ABILITIES:
                raise ContentError(f"bosses.json, « {bid} » : technique « {ab[0]} » inconnue "
                                   f"({', '.join(sorted(BOSS_ABILITIES))}).")
    c["floors"] = list(load("floors.json")["names"])
    an = load("anima.json")
    c["anima_tiers"], c["anima"] = an["tiers"], an["powers"]
    ar = load("artifacts.json")
    c["artifacts"], c["art_power"], c["art_keys"] = ar["artifacts"], ar["rarity_power"], list(ar["keys"])
    for aid, a in c["artifacts"].items():
        where = f"artifacts.json, artefact « {aid} »"
        need(a, ("name", "cd", "color", "desc", "base", "effects"), where)
        check_effects(a["effects"], where)
        for e in a["effects"]:
            if e["type"] == "buff" and e["id"] not in c["buffs"]:
                raise ContentError(f"{where} : buff « {e['id']} » absent de buffs.json.")
    en = load("enchantments.json")
    c["enchants"], c["ench_slots"] = en["enchantments"], en["slots"]
    return c


try:
    CONTENT = load_all()
    ERROR = None
except ContentError as _e:
    CONTENT = None
    ERROR = str(_e)
