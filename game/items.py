"""Génération d'équipement : raretés, affixes, noms, valeurs."""
import random

from .content import CONTENT
from .data import CLASSES, ARTIFACTS, ENCHANTS, ENCH_SLOTS, ench_value
from .settings import RARITIES, RARITY_COLORS, RARITY_NAMES, TEXT, TEXT_DIM, GOLD, RED

SLOTS = ["arme", "casque", "torse", "gants", "bottes", "amulette", "anneau"]
ART_SLOTS = ["artefact1", "artefact2", "artefact3"]
EQUIP_SLOTS = SLOTS + ART_SLOTS
SLOT_NAMES = {"arme": "Arme", "casque": "Casque", "torse": "Torse", "gants": "Gants",
              "bottes": "Bottes", "amulette": "Amulette", "anneau": "Anneau", "artefact": "Artefact",
              "artefact1": "Artefact", "artefact2": "Artefact", "artefact3": "Artefact"}
SLOT_DROP_WEIGHTS = {"arme": 18, "casque": 14, "torse": 14, "gants": 14, "bottes": 14, "amulette": 12, "anneau": 14,
                     "artefact": 12}
ART_POWER = CONTENT["art_power"]
ART_BASE = {aid: a["base"] for aid, a in ARTIFACTS.items()}

BASES = {
    "casque": ["Heaume", "Casque à cornes", "Capuche", "Couronne de fer"],
    "torse": ["Cuirasse", "Cotte de mailles", "Tunique de cuir", "Robe runique"],
    "gants": ["Gantelets", "Gants de cuir", "Mitaines cloutées"],
    "bottes": ["Bottes", "Grèves", "Solerets"],
    "amulette": ["Amulette", "Talisman", "Pendentif"],
    "anneau": ["Anneau", "Bague", "Chevalière"],
}
ARMOR_FACTOR = {"casque": 0.6, "torse": 1.0, "gants": 0.4, "bottes": 0.5}

# stat : (libellé, base, par niveau d'objet, plafond)
AFFIX_DEF = {
    "force": ("+{v} Force", 3, 1.4, None),
    "dex": ("+{v} Dextérité", 3, 1.4, None),
    "int": ("+{v} Intelligence", 3, 1.4, None),
    "vit": ("+{v} Vitalité", 3, 1.4, None),
    "vie": ("+{v} Vie", 12, 9, None),
    "mana": ("+{v} Mana", 8, 3, None),
    "armure": ("+{v} Armure", 5, 3, None),
    "dmg_pct": ("+{v}% de dégâts", 5, 0.7, 45),
    "crit": ("+{v}% de chances de critique", 2, 0.3, 12),
    "atk_speed": ("+{v}% de vitesse d'attaque", 4, 0.4, 20),
    "lifesteal": ("+{v}% de vol de vie", 1, 0.12, 6),
    "mana_regen": ("+{v} mana par seconde", 1, 0.35, None),
    "move_speed": ("+{v}% de vitesse de déplacement", 4, 0.3, 15),
    "gold_find": ("+{v}% d'or trouvé", 10, 2, 100),
    "cdr": ("-{v}% de temps de recharge", 3, 0.35, 15),
}
AFFIX_ALLOWED = {
    "move_speed": {"bottes"},
    "atk_speed": {"arme", "gants", "anneau", "amulette"},
    "lifesteal": {"arme", "anneau", "amulette", "gants"},
    "cdr": {"casque", "amulette", "anneau", "arme"},
}
SUFFIXES = {
    "force": "de l'Ours", "dex": "du Faucon", "int": "du Sage", "vit": "du Colosse", "vie": "de Vitalité",
    "mana": "d'Arcane", "armure": "du Rempart", "dmg_pct": "du Carnage", "crit": "de Précision",
    "atk_speed": "de Célérité", "lifesteal": "du Vampire", "mana_regen": "de Clarté", "move_speed": "du Vent",
    "gold_find": "de Fortune", "cdr": "de l'Instant",
}
RARE_A = ["Fléau", "Chant", "Murmure", "Ruine", "Éclat", "Serment", "Colère", "Ombre", "Cri", "Marque", "Linceul", "Faim"]
RARE_B = ["du Crépuscule", "des Damnés", "de Sang", "du Néant", "des Cendres", "de l'Abîme", "du Tourment",
          "de Givre", "des Ossements", "de la Tour", "des Âmes", "du Bourreau"]
LEGENDARY_NAMES = {
    "casque": ["Heaume du Tourment éternel", "Visage du Damné"],
    "torse": ["Cuirasse du Geôlier", "Linceul d'Ombreveuve"],
    "gants": ["Poignes de l'Abîme", "Mains du Bourreau"],
    "bottes": ["Pas du Spectre", "Foulée des Cendres"],
    "amulette": ["Cœur de la Tour", "Larme du Dieu mort"],
    "anneau": ["Anneau du Geôlier", "Sceau de l'Oublié"],
}
LEGENDARY_NAMES.update({cid: c.get("legendary") or [c["name"]] for cid, c in CLASSES.items()})
RARITY_POWER = {"commun": 1.0, "magique": 1.08, "rare": 1.18, "legendaire": 1.32}
RARITY_VALUE = {"commun": 1, "magique": 3, "rare": 8, "legendaire": 25}
AFFIX_COUNT = {"commun": (0, 0), "magique": (1, 2), "rare": (3, 4), "legendaire": (5, 5)}
MAX_UPGRADE = 5


def roll_rarity(rng=random, tier=0):
    """tier 0 = monstre normal, 1 = élite / coffre, 2 = boss."""
    w = {"commun": 60, "magique": 29, "rare": 9.5, "legendaire": 1.5}
    if tier == 1:
        w.update(commun=25, rare=24, legendaire=4.5)
    elif tier == 2:
        w.update(commun=0, magique=40, rare=45, legendaire=12)
    r = rng.random() * sum(w.values())
    for k in RARITIES:
        r -= w[k]
        if r <= 0:
            return k
    return "commun"


def roll_affix(stat, ilvl, rarity, rng):
    _, base, per, cap = AFFIX_DEF[stat]
    v = (base + per * ilvl) * rng.uniform(0.55, 1.0)
    if rarity == "legendaire":
        v *= 1.25
    if cap:
        v = min(v, cap)
    return max(1, int(round(v)))


def generate_item(ilvl, rarity=None, slot=None, cls_id=None, rng=random, tier=0, wclass=None):
    rarity = rarity or roll_rarity(rng, tier)
    if slot is None:
        slots, weights = zip(*SLOT_DROP_WEIGHTS.items())
        slot = rng.choices(slots, weights)[0]
    if slot == "artefact":
        return generate_artifact(ilvl, rarity, rng=rng)
    it = {"uid": rng.getrandbits(48), "slot": slot, "rarity": rarity, "ilvl": ilvl, "upgrade": 0, "affixes": {}}
    p = RARITY_POWER[rarity]
    if slot == "arme":
        if wclass is None:
            wclass = cls_id if (cls_id and rng.random() < 0.75) else rng.choice(list(CLASSES))
        it["wclass"] = wclass
        it["base"] = rng.choice(CLASSES[wclass]["weapons"])
        dmin = (4 + ilvl * 3) * rng.uniform(0.85, 1.15) * p
        dmax = dmin * rng.uniform(1.4, 1.8)
        it["dmg"] = [max(1, int(dmin)), max(2, int(dmax))]
    else:
        it["base"] = rng.choice(BASES[slot])
        if slot in ARMOR_FACTOR:
            it["armor"] = max(1, int((4 + ilvl * 4) * ARMOR_FACTOR[slot] * p * rng.uniform(0.85, 1.15)))

    lo, hi = AFFIX_COUNT[rarity]
    n = rng.randint(lo, hi)
    if slot in ("amulette", "anneau") and n == 0:
        n = 1
    pool = [s for s in AFFIX_DEF if slot in AFFIX_ALLOWED.get(s, SLOTS)]
    chosen = []
    if rarity == "legendaire" and "cdr" in pool:
        chosen.append("cdr")
    rest = [s for s in pool if s not in chosen]
    chosen += rng.sample(rest, min(len(rest), max(0, n - len(chosen))))
    for s in chosen:
        it["affixes"][s] = roll_affix(s, ilvl, rarity, rng)
    it["name"] = make_name(it, rng)
    kind = "arme" if slot == "arme" else "armure"
    pool = [e for e, d in ENCHANTS.items() if d["kind"] == kind]
    it["ench"] = [{"choices": rng.sample(pool, 3), "id": None, "lvl": 0} for _ in range(ENCH_SLOTS[rarity])]
    return it


def generate_artifact(ilvl, rarity=None, aid=None, rng=random):
    rarity = rarity or roll_rarity(rng)
    aid = aid or rng.choice(list(ARTIFACTS))
    return {"uid": rng.getrandbits(48), "slot": "artefact", "art": aid, "rarity": rarity, "ilvl": ilvl, "upgrade": 0,
            "affixes": {}, "base": "Artefact", "name": ARTIFACTS[aid]["name"]}


def art_value(item):
    return int(round(ART_BASE[item["art"]] * ART_POWER[item["rarity"]] * (1 + 0.1 * item.get("upgrade", 0))))


def art_desc(item):
    return ARTIFACTS[item["art"]]["desc"].format(v=art_value(item))


def ench_spent(item):
    """Points d'enchantement investis dans l'objet (1 + 2 + 3 pour un niveau 3)."""
    return sum(e["lvl"] * (e["lvl"] + 1) // 2 for e in item.get("ench", []))


def ench_stats(item):
    """{enchantement: valeur} des enchantements actifs de l'objet."""
    return {e["id"]: ench_value(e["id"], e["lvl"]) for e in item.get("ench", []) if e["id"] and e["lvl"] > 0}


def make_name(it, rng):
    r = it["rarity"]
    if r == "commun":
        return it["base"]
    if r == "magique":
        first = next(iter(it["affixes"]), None)
        return f"{it['base']} {SUFFIXES[first]}" if first else it["base"]
    if r == "rare":
        return f"{rng.choice(RARE_A)} {rng.choice(RARE_B)}"
    key = it["wclass"] if it["slot"] == "arme" else it["slot"]
    return rng.choice(LEGENDARY_NAMES[key])


def item_stats(item):
    """Statistiques effectives d'un objet (amélioration de forge incluse)."""
    m = 1 + 0.1 * item.get("upgrade", 0)
    res = {"affixes": {k: int(round(v * m)) for k, v in item["affixes"].items()}}
    if "dmg" in item:
        res["dmg"] = (item["dmg"][0] * m, item["dmg"][1] * m)
    if "armor" in item:
        res["armor"] = int(round(item["armor"] * m))
    return res


def item_value(item):
    k = 1.5 if item["slot"] == "artefact" else 1.0
    return int((6 + item["ilvl"] * 4) * RARITY_VALUE[item["rarity"]] * (1 + 0.25 * item.get("upgrade", 0)) * k)


def buy_price(item):
    return item_value(item) * 4


def upgrade_cost(item):
    u = item.get("upgrade", 0)
    return int(30 * (u + 1) ** 1.7 * (1 + item["ilvl"] * 0.35) * (1 + RARITY_VALUE[item["rarity"]] / 10))


def item_lines(item, player=None, header=None):
    """Lignes d'infobulle : liste de (texte, couleur, taille)."""
    col = RARITY_COLORS[item["rarity"]]
    lines = []
    if header:
        lines.append((header, TEXT_DIM, 14))
    name = item["name"] + (f" +{item['upgrade']}" if item.get("upgrade") else "")
    lines.append((name, col, 20))
    if item["rarity"] in ("rare", "legendaire") and item["slot"] != "artefact":
        lines.append((item["base"], col, 15))
    lines.append((f"{SLOT_NAMES[item['slot']]} — {RARITY_NAMES[item['rarity']]}", TEXT_DIM, 15))
    if item["slot"] == "artefact":
        lines.append((art_desc(item), (240, 240, 240), 16))
        lines.append((f"Recharge : {ARTIFACTS[item['art']]['cd']} s", (140, 200, 255), 15))
        lines.append((f"Valeur : {item_value(item)} or", GOLD, 14))
        return lines
    st = item_stats(item)
    if "dmg" in st:
        lines.append((f"Dégâts : {int(st['dmg'][0])} - {int(st['dmg'][1])}", (240, 240, 240), 18))
        cname = CLASSES[item["wclass"]]["name"]
        ok = player is None or player.cls_id == item["wclass"]
        lines.append((f"Arme de {cname}" + ("" if ok else " (inutilisable)"), TEXT_DIM if ok else RED, 15))
    if "armor" in st:
        lines.append((f"Armure : {st['armor']}", (240, 240, 240), 18))
    for k, v in st["affixes"].items():
        lines.append((AFFIX_DEF[k][0].format(v=v), (125, 150, 255), 16))
    for e in item.get("ench", []):
        if e["id"] and e["lvl"]:
            d = ENCHANTS[e["id"]]
            lines.append((f"{d['name']} {'I' * e['lvl']} : " + d["desc"].format(v=ench_value(e['id'], e['lvl'])),
                          (200, 150, 255), 15))
    free = sum(1 for e in item.get("ench", []) if not e["id"])
    if free:
        lines.append((f"{free} emplacement(s) d'enchantement libre(s)", (170, 130, 230), 14))
    lines.append((f"Niveau d'objet : {item['ilvl']}", TEXT_DIM, 14))
    lines.append((f"Valeur : {item_value(item)} or", GOLD, 14))
    return lines
