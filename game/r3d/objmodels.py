"""Modèles 3D importés (fichiers .obj + .mtl, couleurs unies « Kd ») et bibliothèque décrite par assets/models/models.json.

- load(chemin) lit un OBJ et renvoie un tableau de sommets au format du moteur (position, normale, couleur).
- La bibliothèque regroupe les modèles par famille (« pine », « bush »...) avec une échelle et une palette :
  la palette remplace les couleurs des matériaux pour accorder des modèles achetés / gratuits à l'ambiance du jeu.
- MeshBuilder.add_model() (meshes.py) les place dans les maillages statiques ; si un modèle manque, le décor
  procédural d'origine est utilisé.
"""
import json
import os

import numpy as np

from ..settings import ASSETS_DIR
from .meshes import STRIDE

MODELS_DIR = os.path.join(ASSETS_DIR, "models")

_cache = {}
_library = None


def _read_mtl(path):
    mats, cur = {}, None
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if not p:
                    continue
                if p[0] == "newmtl":
                    cur = p[1]
                    mats[cur] = (0.8, 0.8, 0.8)
                elif p[0] == "Kd" and cur:
                    mats[cur] = tuple(float(v) for v in p[1:4])
    except FileNotFoundError:
        pass
    return mats


def load(path, palette=None):
    """OBJ -> tableau (n, STRIDE) en unités du fichier, axe Y vers le haut (comme le moteur)."""
    key = (path, json.dumps(palette, sort_keys=True) if palette else None)
    if key in _cache:
        return _cache[key]
    vs, ns, out = [], [], []
    mats, col = {}, (0.8, 0.8, 0.8)
    folder = os.path.dirname(path)
    with open(path, encoding="utf-8") as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            t = p[0]
            if t == "v":
                vs.append((float(p[1]), float(p[2]), float(p[3])))
            elif t == "vn":
                ns.append((float(p[1]), float(p[2]), float(p[3])))
            elif t == "mtllib":
                mats.update(_read_mtl(os.path.join(folder, " ".join(p[1:]))))
            elif t == "usemtl":
                name = p[1] if len(p) > 1 else ""
                col = tuple((palette or {}).get(name, mats.get(name, (0.8, 0.8, 0.8))))
            elif t == "f":
                idx = []
                for tok in p[1:]:
                    parts = tok.split("/")
                    vi = int(parts[0])
                    ni = int(parts[2]) if len(parts) > 2 and parts[2] else 0
                    idx.append((vi - 1 if vi > 0 else len(vs) + vi, ni - 1 if ni > 0 else (len(ns) + ni if ni else -1)))
                for i in range(1, len(idx) - 1):         # éventail : polygones -> triangles
                    tri = (idx[0], idx[i], idx[i + 1])
                    a, b, c = (np.array(vs[v]) for v, _ in tri)
                    fn = np.cross(b - a, c - a)
                    fn = fn / (np.linalg.norm(fn) or 1.0)
                    for v, n in tri:
                        nn = ns[n] if n >= 0 else fn
                        out.append((*vs[v], *nn, col[0], col[1], col[2], 0.0))
    arr = np.array(out, dtype="f4").reshape(-1, STRIDE)
    _cache[key] = arr
    return arr


def library():
    """assets/models/models.json : {famille: {"files": [...], "scale": s, "palette": {...}}}."""
    global _library
    if _library is None:
        _library = {}
        path = os.path.join(MODELS_DIR, "models.json")
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[modèles] {path} illisible : {e} (décor procédural utilisé)")
            raw = {}
        palettes = raw.get("palettes", {})
        for fam, g in raw.get("families", {}).items():
            pal = dict(palettes.get(g.get("palette"), {})) if isinstance(g.get("palette"), str) else g.get("palette")
            items = []
            for name in g.get("files", []):
                fp = os.path.join(MODELS_DIR, g.get("folder", ""), name if name.endswith(".obj") else name + ".obj")
                try:
                    arr = load(fp, pal)
                    if g.get("normals_up"):     # feuillages fins (herbe) : éclairés comme le sol, jamais sombres
                        arr = arr.copy()
                        arr[:, 3:6] = (0.0, 1.0, 0.0)
                    items.append(arr)
                except (OSError, ValueError, IndexError) as e:
                    print(f"[modèles] {fp} ignoré : {e}")
            if items:
                _library[fam] = dict(models=items, scale=g.get("scale", 1.0), jitter=g.get("scale_jitter", 0.0),
                                     tint=g.get("tint_jitter", 0.0))
    return _library


def family(name):
    return library().get(name)


def place(mb, fam, x, base, z, rng, scale=1.0, flag=0.0):
    """Place un modèle aléatoire de la famille ; renvoie False si la famille n'existe pas (repli procédural)."""
    g = family(fam)
    if not g:
        return False
    arr = rng.choice(g["models"])
    s = g["scale"] * scale * (1 + rng.uniform(-g["jitter"], g["jitter"]))
    tint = 1 + rng.uniform(-g["tint"], g["tint"])
    mb.add_model(arr, (x, base, z), s, rng.random() * 6.2832, flag, tint)
    return True
