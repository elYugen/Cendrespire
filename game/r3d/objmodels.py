"""Modèles 3D importés (.obj + .mtl) et bibliothèque décrite par assets/models/models.json.

Couleurs : unies (« Kd », Nature Kit) ou lues dans une texture-palette (« map_Kd », Fantasy Town / Survival Kit) :
la couleur de la texture est échantillonnée à chaque sommet, le moteur n'a donc pas besoin de textures.

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


_textures = {}


def _texture(path):
    """Image RGB (tableau numpy [largeur, hauteur, 3], 0-1) ; None si illisible."""
    if path not in _textures:
        try:
            import pygame
            _textures[path] = pygame.surfarray.array3d(pygame.image.load(path)).astype("f4") / 255.0
        except (OSError, ValueError, ImportError) as e:
            print(f"[modèles] texture {path} illisible : {e}")
            _textures[path] = None
    return _textures[path]


def _sample(tex, u, v):
    w, h = tex.shape[0], tex.shape[1]
    x = min(w - 1, max(0, int((u % 1.0) * w)))
    y = min(h - 1, max(0, int((1.0 - (v % 1.0)) * h)))
    return tex[x, y]


def _read_mtl(path):
    """{matériau: (r, g, b) ou ("tex", chemin, (r, g, b))}"""
    mats, cur = {}, None
    folder = os.path.dirname(path)
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
                elif p[0] == "map_Kd" and cur:
                    kd = mats[cur] if isinstance(mats[cur], tuple) and len(mats[cur]) == 3 else (1.0, 1.0, 1.0)
                    mats[cur] = ("tex", os.path.join(folder, " ".join(p[1:])), kd)
    except FileNotFoundError:
        pass
    return mats


def load(path, palette=None):
    """OBJ -> tableau (n, STRIDE) en unités du fichier, axe Y vers le haut (comme le moteur)."""
    key = (path, json.dumps(palette, sort_keys=True) if palette else None)
    if key in _cache:
        return _cache[key]
    vs, ns, ts, out = [], [], [], []
    mats, col, tex = {}, (0.8, 0.8, 0.8), None
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
            elif t == "vt":
                ts.append((float(p[1]), float(p[2]) if len(p) > 2 else 0.0))
            elif t == "mtllib":
                mats.update(_read_mtl(os.path.join(folder, " ".join(p[1:]))))
            elif t == "usemtl":
                name = p[1] if len(p) > 1 else ""
                m = mats.get(name, (0.8, 0.8, 0.8))
                tex = None
                if palette and name in palette:
                    col = tuple(palette[name])
                elif isinstance(m[0], str):
                    tex, col = _texture(m[1]), tuple(m[2])
                else:
                    col = tuple(m)
            elif t == "f":
                idx = []
                for tok in p[1:]:
                    parts = tok.split("/")
                    vi = int(parts[0])
                    ti = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                    ni = int(parts[2]) if len(parts) > 2 and parts[2] else 0
                    idx.append((vi - 1 if vi > 0 else len(vs) + vi,
                                ni - 1 if ni > 0 else (len(ns) + ni if ni else -1),
                                ti - 1 if ti > 0 else (len(ts) + ti if ti else -1)))
                for i in range(1, len(idx) - 1):         # éventail : polygones -> triangles
                    tri = (idx[0], idx[i], idx[i + 1])
                    a, b, c = (np.array(vs[v]) for v, _, _ in tri)
                    fn = np.cross(b - a, c - a)
                    fn = fn / (np.linalg.norm(fn) or 1.0)
                    for v, n, ti in tri:
                        nn = ns[n] if n >= 0 else fn
                        cc = col
                        if tex is not None and ti >= 0:
                            k = _sample(tex, *ts[ti])
                            cc = (k[0] * col[0], k[1] * col[1], k[2] * col[2])
                        out.append((*vs[v], *nn, cc[0], cc[1], cc[2], 0.0))
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
            items, names = [], []
            for name in g.get("files", []):
                fp = os.path.join(MODELS_DIR, g.get("folder", ""), name if name.endswith(".obj") else name + ".obj")
                try:
                    arr = load(fp, pal)
                    if g.get("normals_up"):     # feuillages fins (herbe) : éclairés comme le sol, jamais sombres
                        arr = arr.copy()
                        arr[:, 3:6] = (0.0, 1.0, 0.0)
                    if g.get("grade"):          # étalonnage : saturation et teinte accordées à l'ambiance du jeu
                        arr = _grade(arr, g["grade"])
                    items.append(arr)
                    names.append(name)
                except (OSError, ValueError, IndexError) as e:
                    print(f"[modèles] {fp} ignoré : {e}")
            if items:
                _library[fam] = dict(models=items, scale=g.get("scale", 1.0), jitter=g.get("scale_jitter", 0.0),
                                     tint=g.get("tint_jitter", 0.0), names=names)
    return _library


def _grade(arr, gr):
    arr = arr.copy()
    c = arr[:, 6:9]
    lum = (c @ np.array([0.3, 0.59, 0.11], dtype="f4"))[:, None]
    c = lum + (c - lum) * gr.get("saturation", 1.0)
    c = c * np.array(gr.get("multiply", (1.0, 1.0, 1.0)), dtype="f4") * gr.get("brightness", 1.0)
    arr[:, 6:9] = np.clip(c, 0.0, 1.0)
    return arr


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


def put(mb, fam, x, base, z, rot=0.0, scale=1.0, flag=0.0, name=None):
    """Place un modèle précis d'une famille (par son nom de fichier, sinon le premier), orienté de rot radians."""
    g = family(fam)
    if not g:
        return False
    i = g["names"].index(name) if name in g["names"] else 0
    mb.add_model(g["models"][i], (x, base, z), g["scale"] * scale, rot, flag)
    return True
