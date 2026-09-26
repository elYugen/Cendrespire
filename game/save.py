"""Sauvegardes JSON, un fichier par personnage dans le dossier saves/."""
import json
import os
import re
import time

from . import items
from .data import ATTRS
from .settings import SAVE_DIR


def _path(name):
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip().lower()) or "heros"
    return os.path.join(SAVE_DIR, slug + ".json")


def list_saves():
    os.makedirs(SAVE_DIR, exist_ok=True)
    res = []
    for fn in os.listdir(SAVE_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(SAVE_DIR, fn), encoding="utf-8") as f:
                res.append(json.load(f))
        except (OSError, ValueError):
            continue
    res.sort(key=lambda d: d.get("saved_at", 0), reverse=True)
    return res


def exists(name):
    return os.path.exists(_path(name))


def new_character(name, cls_id):
    weapon = items.generate_item(1, rarity="commun", slot="arme", wclass=cls_id)
    art = items.generate_artifact(1, "commun", aid="foudre")
    return {"name": name, "cls": cls_id, "level": 1, "xp": 0, "alloc": {a: 0 for a in ATTRS}, "points": 0,
            "gold": 25, "max_floor": 1, "cleared": [], "equipment": {"arme": weapon, "artefact1": art},
            "inventory": [], "kills": 0, "deaths": 0, "created_at": time.time()}


def save_data(data):
    os.makedirs(SAVE_DIR, exist_ok=True)
    data["saved_at"] = time.time()
    path = _path(data["name"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def delete(name):
    if exists(name):
        os.remove(_path(name))
