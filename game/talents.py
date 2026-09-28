"""Grand arbre de talents : un seul arbre par classe, qui part d'une racine et s'étend en trois domaines (couleurs de
« branches ») reliés par des talents « ponts ».

- 1 point de talent par niveau à partir du niveau 10 (91 points au niveau 100).
- La racine s'apprend seule ; tout autre talent doit toucher (links, dans un sens ou dans l'autre) un talent appris.
- La ligne y de l'arbre demande ROW_COST x (y - 1) points déjà dépensés dans tout l'arbre.
- Un talent peut exiger qu'un autre soit maîtrisé (rang maximum) d'abord : « req ».
- Chaque talent a un effet exprimé par rang : (type, cible, valeur par rang).
- Réinitialisation en ville, contre de l'or.

Types d'effets :
  stat      : bonus de statistique (clé de STAT_DESC)
  sd / sc   : +% dégâts / -% recharge d'un sort précis
  flag      : effet spécial géré par le jeu (clé de FLAG_DESC)
  spell     : débloque un nouveau sort, à équiper dans l'un des 4 emplacements (page Personnage)
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
ROW_COST = _T.get("row_cost", 3)
FIRST_LEVEL = 10          # niveau du premier point de talent
TREES = _T["trees"]
EFFECT_KINDS = ("stat", "flag", "sd", "sc", "spell")


def _validate():
    for cid, tree in TREES.items():
        ids = {n.get("id") for n in tree["nodes"]}
        for t in tree["nodes"]:
            where = f"talents.json, talent « {t.get('id')} »"
            if not isinstance(t.get("x"), int) or not isinstance(t.get("y"), int) or t.get("max", 0) < 1:
                raise ContentError(f"{where} : x, y (entiers) et max (1 ou plus) requis.")
            if not -1 <= t.get("branch", -1) < len(tree["branches"]):
                raise ContentError(f"{where} : branch doit valoir -1 ou l'indice d'une des « branches ».")
            for other in t.get("links", []) + ([t["req"]] if t.get("req") else []):
                if other not in ids:
                    raise ContentError(f"{where} : talent lié « {other} » absent de l'arbre {cid}.")
            for e in t["effects"]:
                kind, key = e[0], e[1]
                if kind == "stat" and key not in STAT_DESC:
                    raise ContentError(f"{where} : statistique « {key} » inconnue ({', '.join(sorted(STAT_DESC))}).")
                if kind == "flag" and key not in FLAG_DESC:
                    raise ContentError(f"{where} : effet « {key} » inconnu ({', '.join(sorted(FLAG_DESC))}).")
                if kind in ("sd", "sc", "spell") and key not in SPELLS:
                    raise ContentError(f"{where} : sort « {key} » absent de spells.json.")
                if kind not in EFFECT_KINDS:
                    raise ContentError(f"{where} : type d'effet « {kind} » inconnu ({', '.join(EFFECT_KINDS)}).")


_validate()

TALENTS = {}
NEIGHBORS = {}            # voisins de chaque talent (liens dans les deux sens)
ROWS = {}                 # classe -> dernière ligne de l'arbre
for _cls, _tree in TREES.items():
    _last = max(n["y"] for n in _tree["nodes"])
    ROWS[_cls] = _last
    for _t in _tree["nodes"]:
        _t["effects"] = [tuple(e) for e in _t["effects"]]
        _t.update(cls=_cls, root=not _t.get("links"), capstone=_t["y"] == _last)
        TALENTS[_t["id"]] = _t
        NEIGHBORS.setdefault(_t["id"], set())
    for _t in _tree["nodes"]:
        for _o in _t.get("links", []):
            NEIGHBORS[_t["id"]].add(_o)
            NEIGHBORS[_o].add(_t["id"])


# =========================================================================== règles
def points_total(level):
    return max(0, level - FIRST_LEVEL + 1)


def spent(ranks):
    return sum(ranks.values())


def row_need(t):
    """Points à avoir dépensés dans l'arbre pour ouvrir la ligne de ce talent."""
    return max(0, t["y"] - 1) * ROW_COST


def req_met(ranks, t):
    r = t.get("req")
    return not r or ranks.get(r, 0) >= TALENTS[r]["max"]


def connected(ranks, t):
    """La racine, ou un talent qui touche un talent appris."""
    return t["root"] or any(ranks.get(o, 0) > 0 for o in NEIGHBORS[t["id"]])


def can_learn(ranks, level, tid):
    t = TALENTS[tid]
    if ranks.get(tid, 0) >= t["max"]:
        return False, "Rang maximum atteint"
    if spent(ranks) >= points_total(level):
        return False, "Aucun point de talent disponible"
    if not connected(ranks, t):
        return False, "Doit toucher un talent déjà appris"
    if spent(ranks) < row_need(t):
        return False, f"Requiert {row_need(t)} points dépensés dans l'arbre"
    if not req_met(ranks, t):
        return False, f"Requiert {TALENTS[t['req']]['name']} au rang maximum"
    return True, ""


def _valid(ranks, cls_id):
    """Vrai si les talents appris forment un arbre relié à la racine, dont chaque ligne était accessible."""
    learned = {k for k, r in ranks.items() if r > 0}
    roots = [k for k in learned if TALENTS[k]["root"]]
    seen, todo = set(roots), list(roots)
    while todo:
        k = todo.pop()
        for o in NEIGHBORS[k]:
            if o in learned and o not in seen:
                seen.add(o)
                todo.append(o)
    if seen != learned:
        return False
    for k in learned:
        t = TALENTS[k]
        if not req_met(ranks, t):
            return False
        below = sum(r for o, r in ranks.items() if TALENTS[o]["y"] < t["y"])
        if below < row_need(t):
            return False
    return True


def reset_cost(level):
    """En pièces de cuivre."""
    return 250 * level


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
    if kind == "spell":
        return f"Nouveau sort : {name}"
    return f"+{_fmt(v)}% de dégâts de {name}" if kind == "sd" else f"-{_fmt(v)}% de recharge de {name}"


def spells_of(ranks):
    """Sorts débloqués par les talents appris."""
    return [key for tid, r in ranks.items() if r > 0 and tid in TALENTS
            for kind, key, _ in TALENTS[tid]["effects"] if kind == "spell"]


def describe(tid, rank):
    t = TALENTS[tid]
    return " · ".join(effect_text(k, key, per * max(1, rank)) for k, key, per in t["effects"])


def _fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:.1f}".replace(".", ",")


def clean(ranks, cls_id, level=None):
    """Ne garde que des talents valides de la classe (sauvegardes anciennes ou arbre modifié) : les points
    d'un talent devenu inaccessible sont rendus au joueur."""
    res = {}
    for tid, r in (ranks or {}).items():
        t = TALENTS.get(tid)
        if t and t["cls"] == cls_id and isinstance(r, int) and r > 0:
            res[tid] = min(r, t["max"])
    root = next((n["id"] for n in TREES[cls_id]["nodes"] if not n.get("links")), None)
    if res and root and root not in res:           # arbre d'une ancienne version : on le rattache à la racine
        res[root] = 1
    budget = points_total(level) if level else None
    while res and (not _valid(res, cls_id) or (budget is not None and spent(res) > budget)):
        top = max(res, key=lambda k: (TALENTS[k]["y"], TALENTS[k]["id"]))     # on retire par le haut de l'arbre
        res[top] -= 1
        if not res[top]:
            del res[top]
    return res
