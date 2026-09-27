"""Arbres de talents : 3 branches par classe, 4 paliers par branche.

- 1 point de talent tous les 2 niveaux (niveau 1 : 1 point, niveau 3 : 2 points...).
- Le palier n d'une branche (0 à 3) demande 3 x n points déjà investis dans cette branche.
- Chaque talent a un effet exprimé par rang : (type, cible, valeur par rang).
- Réinitialisation possible au campement contre de l'or.

Types d'effets :
  stat      : bonus de statistique (clé de STAT_DESC)
  sd / sc   : +% dégâts / -% recharge d'un sort précis
  flag      : effet spécial géré par le jeu (clé de FLAG_DESC)
"""
from .content import CONTENT, ContentError
from .data import SPELLS


STAT_DESC = {
    "dmg_pct": "+{v}% de dégâts",
    "spell_pct": "+{v}% de dégâts des sorts",
    "basic_pct": "+{v}% de dégâts de l'attaque de base",
    "crit": "+{v}% de chances de coup critique",
    "crit_dmg": "+{v}% de dégâts des coups critiques",
    "atk_speed": "+{v}% de vitesse d'attaque",
    "move_speed": "+{v}% de vitesse de déplacement",
    "cdr": "-{v}% de temps de recharge des sorts",
    "max_hp_pct": "+{v}% de vie maximum",
    "mana_pct": "+{v}% de mana maximum",
    "mana_regen_pct": "+{v}% de régénération de mana",
    "armor_pct": "+{v}% d'armure",
    "dr": "-{v}% de dégâts subis",
    "lifesteal": "+{v}% de vol de vie",
    "roll_cd": "-{v}% de recharge de la roulade",
    "summon_pct": "+{v}% de dégâts des serviteurs",
    "curse_amp": "Les ennemis maudits subissent +{v}% de dégâts en plus",
    "dot_pct": "+{v}% de dégâts du poison et des brûlures",
    "gold_find": "+{v}% d'or trouvé",
}
FLAG_DESC = {
    "kill_cdr": "Tuer un ennemi réduit toutes les recharges de {v} s",
    "free_cast": "{v}% de chances qu'un sort ne coûte pas de mana",
    "execute": "+{v}% de dégâts contre les ennemis sous 30% de vie",
    "first_strike": "+{v}% de dégâts contre les ennemis indemnes",
    "berserk": "Jusqu'à +{v}% de dégâts selon la vie manquante",
    "low_hp_dr": "-{v}% de dégâts subis sous 35% de vie",
    "last_stand": "Une fois par ascension, sous 20% de vie : rend 40% de vie et 2 s d'invulnérabilité",
    "mana_on_kill": "Tuer un ennemi rend {v} mana",
    "kill_heal": "Tuer un ennemi rend {v}% de vie",
    "heal_on_spell": "Lancer un sort rend {v}% de vie",
    "crit_heal": "Les coups critiques rendent {v}% de vie",
    "thorns": "Renvoie {v}% des dégâts de mêlée subis",
    "extra_summon": "+{v} squelette(s) par invocation (et au maximum)",
}


# =========================================================================== arbres (data/talents.json)
_T = CONTENT["talents"]
TIER_COST = _T["tier_cost"]
RANKS = tuple(_T["ranks"])
TREES = _T["trees"]


def _validate():
    for cid, branches in TREES.items():
        for bi, b in enumerate(branches):
            if len(b["talents"]) > len(RANKS):
                raise ContentError(f"talents.json, {cid} / {b['name']} : {len(b['talents'])} talents pour "
                                   f"{len(RANKS)} paliers.")
            for t in b["talents"]:
                where = f"talents.json, talent « {t.get('id')} »"
                for e in t["effects"]:
                    kind, key = e[0], e[1]
                    if kind == "stat" and key not in STAT_DESC:
                        raise ContentError(f"{where} : statistique « {key} » inconnue "
                                           f"({', '.join(sorted(STAT_DESC))}).")
                    if kind == "flag" and key not in FLAG_DESC:
                        raise ContentError(f"{where} : effet « {key} » inconnu ({', '.join(sorted(FLAG_DESC))}).")
                    if kind in ("sd", "sc") and key not in SPELLS:
                        raise ContentError(f"{where} : sort « {key} » absent de spells.json.")
                    if kind not in ("stat", "flag", "sd", "sc"):
                        raise ContentError(f"{where} : type d'effet « {kind} » inconnu (stat, flag, sd, sc).")


_validate()

TALENTS = {}
for _cls, _branches in TREES.items():
    for _bi, _b in enumerate(_branches):
        for _ti, _t in enumerate(_b["talents"]):
            _t["effects"] = [tuple(e) for e in _t["effects"]]
            _t.update(cls=_cls, branch=_bi, tier=_ti, max=RANKS[_ti])
            TALENTS[_t["id"]] = _t


# =========================================================================== règles
def points_total(level):
    return (level + 1) // 2


def branch_spent(ranks, cls_id, bi):
    return sum(ranks.get(t["id"], 0) for t in TREES[cls_id][bi]["talents"])


def spent(ranks):
    return sum(ranks.values())


def can_learn(ranks, level, tid):
    t = TALENTS[tid]
    if ranks.get(tid, 0) >= t["max"]:
        return False, "Rang maximum atteint"
    if spent(ranks) >= points_total(level):
        return False, "Aucun point de talent disponible"
    need = t["tier"] * TIER_COST
    have = branch_spent(ranks, t["cls"], t["branch"])
    if have < need:
        return False, f"Requiert {need} points dans la branche {TREES[t['cls']][t['branch']]['name']}"
    return True, ""


def can_unlearn(ranks, tid):
    """On ne peut retirer un point que si les paliers supérieurs restent accessibles."""
    t = TALENTS[tid]
    if ranks.get(tid, 0) <= 0:
        return False
    test = dict(ranks)
    test[tid] -= 1
    for other in TREES[t["cls"]][t["branch"]]["talents"]:
        if test.get(other["id"], 0) > 0 and other["tier"] > 0:
            below = sum(test.get(o["id"], 0) for o in TREES[t["cls"]][t["branch"]]["talents"]
                        if o["tier"] < other["tier"])
            if below < other["tier"] * TIER_COST:
                return False
    return True


def reset_cost(level):
    return 25 * level


def effects(ranks):
    """Agrège les effets des talents appris : {clé: valeur}. Clés : stat, 'sd:<sort>', 'sc:<sort>', flag."""
    res = {}
    for tid, r in ranks.items():
        t = TALENTS.get(tid)
        if not t or r <= 0:
            continue
        for kind, key, per in t["effects"]:
            k = key if kind in ("stat", "flag") else f"{kind}:{key}"
            res[k] = res.get(k, 0) + per * r
    return res


def effect_text(kind, key, v):
    if kind == "stat":
        return STAT_DESC[key].format(v=_fmt(v))
    if kind == "flag":
        return FLAG_DESC[key].format(v=_fmt(v))
    name = SPELLS[key]["name"]
    return f"+{_fmt(v)}% de dégâts de {name}" if kind == "sd" else f"-{_fmt(v)}% de recharge de {name}"


def describe(tid, rank):
    t = TALENTS[tid]
    return " · ".join(effect_text(k, key, per * max(1, rank)) for k, key, per in t["effects"])


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}".replace(".", ",")


def clean(ranks, cls_id):
    """Ne garde que des talents valides de la classe (sauvegardes anciennes ou modifiées)."""
    res = {}
    for tid, r in (ranks or {}).items():
        t = TALENTS.get(tid)
        if t and t["cls"] == cls_id and isinstance(r, int) and r > 0:
            res[tid] = min(r, t["max"])
    return res
