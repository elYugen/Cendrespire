"""Quêtes des habitants de Cendreval : définitions dans data/quests.json, progression dans la sauvegarde.

État d'une quête pour le héros (player.quests[qid]) : {"state": "active" | "ready" | "done", "n": [compteurs]}
  active : acceptée, objectifs en cours ; ready : objectifs remplis, à rendre ; done : récompense reçue.
Les objectifs « clear » et « floor » se lisent sur la progression du héros (étages vaincus, étage atteint) ;
les autres comptent les événements survenus après l'acceptation (monstres tués, gardiens, discussions).
"""
from . import sfx
from .data import CONTENT, MONSTERS
from .settings import GOLD_BRIGHT, RARITY_NAMES
from . import town

QUESTS = CONTENT["quests"]
NPC_NAMES = dict(town.SHOPKEEPERS, **{v["id"]: v["name"] for v in town.VILLAGERS})
MAX_TRACKED = 4


def clean(data):
    """État des quêtes lu dans une sauvegarde : on ne garde que les quêtes qui existent encore."""
    res = {}
    for qid, st in (data or {}).items():
        if qid in QUESTS and isinstance(st, dict) and st.get("state") in ("active", "ready", "done"):
            n = list(st.get("n", []))
            n += [0] * (len(QUESTS[qid]["objectives"]) - len(n))
            res[qid] = {"state": st["state"], "n": n[:len(QUESTS[qid]["objectives"])]}
    return res


def turn_in_npc(qid):
    q = QUESTS[qid]
    return q.get("turn_in", q["giver"])


# ------------------------------------------------------------------ objectifs
def need(o):
    return 1 if o["type"] in ("clear", "floor", "talk") else o.get("count", 1)


def count(p, qid, i):
    o = QUESTS[qid]["objectives"][i]
    if o["type"] == "clear":
        return 1 if o["floor"] in p.cleared else 0
    if o["type"] == "floor":
        return 1 if p.max_floor >= o["floor"] else 0
    st = p.quests.get(qid)          # quête proposée mais pas encore acceptée : rien de compté
    return min(need(o), st["n"][i]) if st else 0


def objective_text(o):
    if o.get("text"):
        return o["text"]
    t = o["type"]
    if t == "kill":
        what = MONSTERS[o["monster"]]["name"] if o.get("monster") else "monstres"
        return f"Tuer : {what}" + (" (élite)" if o.get("elite") else "")
    if t == "boss":
        return f"Vaincre le gardien de l'étage {o['floor']}" if o.get("floor") else "Vaincre des gardiens d'étage"
    if t == "clear":
        return f"Vaincre le gardien de l'étage {o['floor']}"
    if t == "floor":
        return f"Atteindre l'étage {o['floor']}"
    return f"Parler à {NPC_NAMES[o['npc']]}"


def objectives(p, qid):
    """[(texte, fait, besoin)] pour l'affichage."""
    return [(objective_text(o), count(p, qid, i), need(o)) for i, o in enumerate(QUESTS[qid]["objectives"])]


def complete(p, qid):
    return all(c >= n for _t, c, n in objectives(p, qid))


def reward_text(qid):
    r = QUESTS[qid].get("reward", {})
    parts = []
    if r.get("gold"):
        parts.append(f"{r['gold']} or")
    if r.get("xp"):
        parts.append(f"{r['xp']} XP")
    if r.get("item"):
        parts.append(f"objet {RARITY_NAMES[r['item']].lower()}")
    return " · ".join(parts)


# ------------------------------------------------------------------ disponibilité
def state(p, qid):
    return p.quests.get(qid, {}).get("state")


def unlocked(p, qid):
    q = QUESTS[qid]
    return (qid not in p.quests and p.level >= q.get("min_level", 1)
            and all(state(p, r) == "done" for r in q.get("requires", [])))


def offers(p, npc_id):
    """Quêtes que cet habitant propose maintenant."""
    return [qid for qid, q in QUESTS.items() if q["giver"] == npc_id and unlocked(p, qid)]


def to_turn_in(p, npc_id):
    return [qid for qid in QUESTS if state(p, qid) == "ready" and turn_in_npc(qid) == npc_id]


def in_progress(p, npc_id):
    return [qid for qid in QUESTS if state(p, qid) == "active" and turn_in_npc(qid) == npc_id]


def marker(p, npc_id):
    """« ? » doré : quête à rendre ; « ! » doré : nouvelle quête ; « ? » gris : quête en cours."""
    if not npc_id:
        return None
    if to_turn_in(p, npc_id):
        return "?", GOLD_BRIGHT
    if offers(p, npc_id):
        return "!", GOLD_BRIGHT
    if in_progress(p, npc_id):
        return "?", (170, 170, 170)
    return None


def tracked(p):
    """Quêtes affichées à l'écran : celles à rendre d'abord, puis les quêtes en cours."""
    ready = [q for q in p.quests if p.quests[q]["state"] == "ready"]
    active = [q for q in p.quests if p.quests[q]["state"] == "active"]
    return (ready + active)[:MAX_TRACKED]


# ------------------------------------------------------------------ actions
def accept(world, qid):
    p = world.player
    p.quests[qid] = {"state": "active", "n": [0] * len(QUESTS[qid]["objectives"])}
    world.message(f"Nouvelle quête : {QUESTS[qid]['name']}", GOLD_BRIGHT, 6)
    sfx.play("click")
    _refresh(world, qid)
    world.save()


def turn_in(world, qid):
    from .entities import Loot
    from .items import generate_item
    p = world.player
    p.quests[qid]["state"] = "done"
    r = QUESTS[qid].get("reward", {})
    world.show_banner("Quête accomplie", QUESTS[qid]["name"], GOLD_BRIGHT, 4)
    sfx.play("levelup")
    if r.get("gold"):
        p.gold += r["gold"]
        world.on_gold(r["gold"])
    if r.get("item"):
        it = generate_item(max(1, p.max_floor), rarity=r["item"], cls_id=p.cls_id)
        if not world.pickup_item(it):
            world.loot.append(Loot(p.x, p.y, "item", it))
            world.message("Sac plein : la récompense est posée à vos pieds.", GOLD_BRIGHT, 5)
    if r.get("xp"):
        p.gain_xp(r["xp"], world)
    world.save()


def event(world, kind, **kw):
    """Un événement de jeu fait avancer les quêtes en cours :
    kill (monster, elite, floor), boss (floor), talk (npc), progress (étage vaincu ou atteint)."""
    p = world.player
    for qid, st in p.quests.items():
        if st["state"] != "active":
            continue
        for i, o in enumerate(QUESTS[qid]["objectives"]):
            t = o["type"]
            if kind == "kill" and t == "kill":
                if o.get("monster") and o["monster"] != kw.get("monster"):
                    continue
                if o.get("elite") and not kw.get("elite"):
                    continue
                if kw.get("floor", 0) < o.get("min_floor", 0):
                    continue
            elif kind == "boss" and t == "boss":
                if o.get("floor") and o["floor"] != kw.get("floor"):
                    continue
            elif kind == "talk" and t == "talk":
                if o["npc"] != kw.get("npc"):
                    continue
            else:
                continue
            if st["n"][i] < need(o):
                st["n"][i] += 1
                if kind == "kill" and st["n"][i] < need(o):
                    continue
                world.message(f"{QUESTS[qid]['name']} : {objective_text(o)} ({st['n'][i]}/{need(o)})",
                              (230, 214, 160), 4)
        _refresh(world, qid)


def _refresh(world, qid):
    p = world.player
    st = p.quests[qid]
    if st["state"] == "active" and complete(p, qid):
        st["state"] = "ready"
        world.message(f"Quête terminée : {QUESTS[qid]['name']} — retournez voir {NPC_NAMES[turn_in_npc(qid)]}.",
                      GOLD_BRIGHT, 8)
        sfx.play("seal", 0.5)
