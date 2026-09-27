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
from .data import SPELLS

TIER_COST = 3          # points dans la branche pour débloquer le palier suivant
RANKS = (3, 3, 2, 1)   # rangs maximum par palier

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


def T(tid, name, icon, *effects):
    return {"id": tid, "name": name, "icon": icon, "effects": list(effects)}


# =========================================================================== arbres
TREES = {
    "barbare": [
        dict(name="Carnage", color=(230, 80, 60), icon="sword", talents=[
            T("ba_force", "Force brute", "sword", ("stat", "dmg_pct", 4)),
            T("ba_tourb", "Tourbillon sanglant", "spell:tourbillon", ("sd", "tourbillon", 15)),
            T("ba_exec", "Exécution", "skull", ("flag", "execute", 15)),
            T("ba_rage", "Rage sans fin", "star", ("flag", "kill_cdr", 0.5)),
        ]),
        dict(name="Rempart", color=(170, 176, 190), icon="shield", talents=[
            T("ba_peau", "Peau de pierre", "shield", ("stat", "armor_pct", 8)),
            T("ba_vig", "Vigueur des steppes", "heart", ("stat", "max_hp_pct", 5)),
            T("ba_mur", "Dos au mur", "shield", ("flag", "low_hp_dr", 12)),
            T("ba_souffle", "Second souffle", "star", ("flag", "last_stand", 1)),
        ]),
        dict(name="Fureur", color=(255, 150, 60), icon="bolt", talents=[
            T("ba_fren", "Frénésie", "bolt", ("stat", "atk_speed", 4)),
            T("ba_bond", "Bond dévastateur", "spell:bond", ("sd", "bond", 15)),
            T("ba_berz", "Berserker", "fist", ("flag", "berserk", 15)),
            T("ba_seisme", "Séisme primordial", "spell:seisme", ("sd", "seisme", 40), ("sc", "seisme", 25)),
        ]),
    ],
    "sorcier": [
        dict(name="Feu", color=(255, 120, 40), icon="flame", talents=[
            T("so_braise", "Braises", "flame", ("stat", "spell_pct", 4)),
            T("so_pyro", "Pyromancie", "spell:boule_feu", ("sd", "boule_feu", 15)),
            T("so_meteor", "Météore ardent", "spell:meteore", ("sd", "meteore", 20)),
            T("so_surch", "Surcharge", "star", ("flag", "free_cast", 20)),
        ]),
        dict(name="Givre", color=(130, 210, 255), icon="snow", talents=[
            T("so_froid", "Esprit froid", "eye", ("stat", "crit", 3)),
            T("so_hiver", "Hiver éternel", "spell:nova_givre", ("sd", "nova_givre", 15)),
            T("so_coeur", "Cœur de glace", "shield", ("stat", "dr", 4)),
            T("so_temps", "Distorsion temporelle", "clock", ("stat", "cdr", 15)),
        ]),
        dict(name="Arcane", color=(170, 120, 255), icon="orb", talents=[
            T("so_reserv", "Réserves", "orb", ("stat", "mana_pct", 8)),
            T("so_flux", "Flux", "drop", ("stat", "mana_regen_pct", 12)),
            T("so_blink", "Clignement", "spell:teleport", ("sc", "teleport", 15)),
            T("so_fontaine", "Fontaine arcanique", "star", ("flag", "heal_on_spell", 2)),
        ]),
    ],
    "chasseur": [
        dict(name="Précision", color=(250, 220, 110), icon="eye", talents=[
            T("ch_faucon", "Œil de faucon", "eye", ("stat", "crit", 3)),
            T("ch_acier", "Pointes d'acier", "spell:fleche_perforante", ("sd", "fleche_perforante", 15)),
            T("ch_mortel", "Tir mortel", "skull", ("stat", "crit_dmg", 20)),
            T("ch_elite", "Tireur d'élite", "star", ("flag", "first_strike", 50)),
        ]),
        dict(name="Survie", color=(120, 210, 120), icon="boot", talents=[
            T("ch_pas", "Pas léger", "boot", ("stat", "move_speed", 4)),
            T("ch_acro", "Acrobate", "bolt", ("stat", "roll_cd", 12)),
            T("ch_peau", "Seconde peau", "heart", ("stat", "max_hp_pct", 6)),
            T("ch_instinct", "Instinct de survie", "star", ("flag", "low_hp_dr", 25)),
        ]),
        dict(name="Pièges", color=(255, 170, 70), icon="trap", talents=[
            T("ch_salve", "Salves", "sword", ("stat", "spell_pct", 4)),
            T("ch_poudre", "Poudre noire", "spell:piege", ("sd", "piege", 15)),
            T("ch_deluge", "Déluge", "spell:pluie_fleches", ("sd", "pluie_fleches", 15)),
            T("ch_prime", "Chasseur de primes", "star", ("flag", "mana_on_kill", 6), ("stat", "gold_find", 25)),
        ]),
    ],
    "paladin": [
        dict(name="Justice", color=(255, 214, 110), icon="sword", talents=[
            T("pa_juste", "Juste cause", "sword", ("stat", "dmg_pct", 4)),
            T("pa_jugement", "Verdict", "spell:jugement", ("sd", "jugement", 15)),
            T("pa_zele", "Zèle", "eye", ("stat", "crit", 4)),
            T("pa_colere", "Colère divine", "star", ("flag", "execute", 30)),
        ]),
        dict(name="Protection", color=(180, 190, 210), icon="shield", talents=[
            T("pa_plates", "Plates bénies", "shield", ("stat", "armor_pct", 8)),
            T("pa_charge", "Bouclier sacré", "spell:charge_bouclier", ("sd", "charge_bouclier", 20)),
            T("pa_epines", "Représailles", "shield", ("flag", "thorns", 25)),
            T("pa_martyr", "Martyr", "star", ("flag", "last_stand", 1)),
        ]),
        dict(name="Sainteté", color=(255, 244, 200), icon="heart", talents=[
            T("pa_foi", "Foi inébranlable", "heart", ("stat", "max_hp_pct", 4)),
            T("pa_terre", "Terre consacrée", "spell:consecration", ("sd", "consecration", 15)),
            T("pa_lumiere", "Lumière guérisseuse", "drop", ("flag", "heal_on_spell", 1.5)),
            T("pa_egide", "Égide éternelle", "spell:egide", ("sc", "egide", 30)),
        ]),
    ],
    "necromancien": [
        dict(name="Os", color=(230, 226, 200), icon="skull", talents=[
            T("ne_moelle", "Moelle noire", "skull", ("stat", "spell_pct", 4)),
            T("ne_lance", "Lance barbelée", "spell:lance_os", ("sd", "lance_os", 15)),
            T("ne_eclats", "Éclats d'os", "eye", ("stat", "crit_dmg", 20)),
            T("ne_ossature", "Ossature", "star", ("flag", "kill_cdr", 0.4)),
        ]),
        dict(name="Invocation", color=(130, 255, 170), icon="summon", talents=[
            T("ne_liens", "Liens d'outre-tombe", "summon", ("stat", "summon_pct", 10)),
            T("ne_appel", "Appel pressant", "spell:squelettes", ("sc", "squelettes", 10)),
            T("ne_fureur", "Fureur des morts", "summon", ("stat", "summon_pct", 15)),
            T("ne_seigneur", "Seigneur des morts", "star", ("flag", "extra_summon", 2)),
        ]),
        dict(name="Fléau", color=(170, 90, 230), icon="drop", talents=[
            T("ne_sang", "Sang corrompu", "drop", ("stat", "lifesteal", 1)),
            T("ne_mal", "Malédiction profonde", "spell:malediction", ("stat", "curse_amp", 10)),
            T("ne_moisson", "Grande moisson", "spell:moisson", ("sd", "moisson", 20)),
            T("ne_devoreur", "Dévoreur d'âmes", "star", ("flag", "kill_heal", 2), ("flag", "mana_on_kill", 5)),
        ]),
    ],
    "assassin": [
        dict(name="Assassinat", color=(200, 80, 90), icon="dagger", talents=[
            T("as_lame", "Lame affûtée", "eye", ("stat", "crit", 3)),
            T("as_ombre", "Frappe de l'ombre", "spell:pas_ombre", ("sd", "pas_ombre", 15)),
            T("as_jugul", "Jugulaire", "skull", ("stat", "crit_dmg", 25)),
            T("as_premier", "Premier sang", "star", ("flag", "first_strike", 60)),
        ]),
        dict(name="Poisons", color=(120, 230, 90), icon="drop", talents=[
            T("as_toxine", "Toxines", "drop", ("stat", "dot_pct", 12)),
            T("as_venin", "Réserve de venin", "spell:venin", ("sc", "venin", 10)),
            T("as_eventail", "Pluie d'acier", "spell:eventail", ("sd", "eventail", 20)),
            T("as_mortel", "Venin mortel", "star", ("flag", "execute", 25)),
        ]),
        dict(name="Ombres", color=(150, 130, 230), icon="boot", talents=[
            T("as_furtif", "Furtivité", "boot", ("stat", "move_speed", 4)),
            T("as_vif", "Mains vives", "bolt", ("stat", "atk_speed", 4)),
            T("as_voile", "Voile d'ombre", "bolt", ("stat", "roll_cd", 15)),
            T("as_danse", "Danse macabre", "spell:danse_lames", ("sd", "danse_lames", 40), ("flag", "kill_cdr", 0.3)),
        ]),
    ],
}

TALENTS = {}
for _cls, _branches in TREES.items():
    for _bi, _b in enumerate(_branches):
        for _ti, _t in enumerate(_b["talents"]):
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
