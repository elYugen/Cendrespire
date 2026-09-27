"""Notes de mise à jour : un fichier JSON par version dans data/updates/ (affichées dans le menu Système).

Format : {"version": "2.1", "date": "2026-09-27", "title": "...", "sections": [{"name": "...", "notes": ["..."]}]}
Un fichier illisible est ignoré (et signalé dans la console) : les notes ne doivent jamais empêcher de jouer.
"""
import glob
import json
import os

from .content import DATA_DIR


def _key(u):
    try:
        return tuple(int(x) for x in str(u.get("version", "0")).split("."))
    except ValueError:
        return (0,)


def load():
    res = []
    for path in glob.glob(os.path.join(DATA_DIR, "updates", "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                u = json.load(f)
            if isinstance(u, dict) and "version" in u:
                res.append(u)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[notes] {os.path.basename(path)} ignoré : {e}")
    return sorted(res, key=_key, reverse=True)


def current_version(default="2.2"):
    """Version affichée par le jeu : celle de la note de mise à jour la plus récente."""
    notes = load()
    return str(notes[0]["version"]) if notes else default

