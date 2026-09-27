"""Étages construits avec le Modular Dungeon Kit de Kenney (murs, dalles, colonnes) et du mobilier importé.

- Les murs et les dalles sont des instances (un modèle envoyé une fois à la carte graphique, une matrice par pièce) :
  des milliers de pièces sans alourdir le maillage. Leur couleur vient de l'ambiance de l'étage (teinte par instance).
- Au-delà des murs, une masse rocheuse texturée remplace le vide noir.
- Le mobilier (tonneaux, tombes, cierges, étais...) dépend de l'ambiance (THEMES["props"] dans level.py).
Si un modèle manque, level.py revient aux murs procéduraux.
"""
import math
import os

import numpy as np

from ..settings import ASSETS_DIR
from . import objmodels
from .meshes import STRIDE

KIT_DIR = os.path.join(ASSETS_DIR, "models", "dungeon")
PROP_DIRS = {"props": os.path.join(ASSETS_DIR, "models", "props"),
             "grave": os.path.join(ASSETS_DIR, "models", "graveyard")}
WALL_H = 0.4           # échelle verticale des murs du kit (4,15 unités -> 1,66 case)
S = 0.25               # 4 unités du kit = 1 case
_kit = {}


def _gray(arr, flag):
    """Couleurs en niveaux de gris normalisés : la teinte de l'ambiance est appliquée par instance."""
    a = arr.copy()
    lum = a[:, 6:9] @ np.array([0.3, 0.59, 0.11], dtype="f4")
    lum = lum / (float(lum.mean()) or 1.0)
    a[:, 6:9] = np.clip(lum[:, None] * 0.85, 0.0, 1.6)
    a[:, 9] = flag
    return np.ascontiguousarray(a, dtype="f4")


def kit(name, flag):
    key = (name, flag)
    if key not in _kit:
        path = os.path.join(KIT_DIR, name + ".obj")
        _kit[key] = _gray(objmodels.load(path), flag) if os.path.exists(path) else None
    return _kit[key]


def available():
    return kit("template-wall", 3.0) is not None


class Instances:
    def __init__(self):
        self.models = {}
        self.inst = {}

    def add(self, key, arr, x, base, z, rot, sx, sy, sz, tint):
        if arr is None:
            return
        self.models.setdefault(key, arr)
        c, s = math.cos(rot), math.sin(rot)
        self.inst.setdefault(key, []).append((c * sx, 0, -s * sx, 0, sy, 0, s * sz, 0, c * sz, x, base, z,
                                              tint[0], tint[1], tint[2], 0.0))

    def export(self, geo):
        geo.inst_models = self.models
        geo.instances = {k: np.array(v, dtype="f4") for k, v in self.inst.items()}


def _tint(c, rng, j=0.06):
    k = 1 + rng.uniform(-j, j)
    return tuple(max(0.0, min(1.6, ch / 255.0 * k * 1.25)) for ch in c)


def build(mb, geo, d, th, rng, is_floor):
    """Sol, murs, colonnes, masse rocheuse et mobilier d'un étage de la tour."""
    inst = Instances()
    STONE, flag_floor, flag_wall = mb.STONE, 2.0 * 1, 1.0 + 2.0 * 1
    floors = [("template-floor", 0.8), ("template-floor-detail", 0.1), ("template-floor-detail-a", 0.1)]
    walls = [("template-wall", 0.72), ("template-wall-detail-a", 0.28)]
    W, H = d.w, d.h
    # dalles
    for y in range(H):
        for x in range(W):
            if not is_floor(x, y):
                continue
            r = rng.random()
            name = floors[0][0] if r < floors[0][1] else (floors[1][0] if r < 0.9 else floors[2][0])
            col = th["alt"] if rng.random() < 0.12 else th["floor"]
            inst.add(name, kit(name, flag_floor), x + 0.5, 0.0, y + 0.5, rng.randrange(4) * math.pi / 2,
                     S, S, S, _tint(col, rng))
    # murs : une pièce par bord de case murale qui donne sur le sol ; colonnes aux angles saillants
    sides = ((1, 0, math.pi / 2), (-1, 0, -math.pi / 2), (0, 1, 0.0), (0, -1, math.pi))
    for y in range(-1, H + 1):
        for x in range(-1, W + 1):
            if is_floor(x, y):
                continue
            open_sides = [(dx, dy, rot) for dx, dy, rot in sides if is_floor(x + dx, y + dy)]
            if not open_sides:
                continue
            if len(open_sides) == 4:          # pilier isolé
                inst.add("template-detail", kit("template-detail", flag_wall), x + 0.5, 0.0, y + 0.5, 0.0,
                         S * 1.6, WALL_H, S * 1.6, _tint(th["wall"], rng))
                continue
            for dx, dy, rot in open_sides:
                r = rng.random()
                name = walls[0][0] if r < walls[0][1] else walls[1][0]
                inst.add(name, kit(name, flag_wall), x + 0.5 + dx * 0.5, 0.0, y + 0.5 + dy * 0.5, rot,
                         S, WALL_H, S, _tint(th["wall"], rng, 0.04))
            for (ax, ay, _), (bx, by, _) in ((open_sides[i], open_sides[j]) for i in range(len(open_sides))
                                             for j in range(i + 1, len(open_sides))):
                if ax and by or ay and bx:        # deux bords perpendiculaires : angle saillant
                    cx, cz = x + 0.5 + (ax or bx) * 0.5, y + 0.5 + (ay or by) * 0.5
                    inst.add("template-detail", kit("template-detail", flag_wall), cx, 0.0, cz, 0.0,
                             S * 0.9, WALL_H * 1.02, S * 0.9, _tint(th["wall"], rng, 0.03))
    # torches sur les murs
    for (tx, ty) in d.torches:
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            if is_floor(tx + dx, ty + dy):
                px, pz = tx + 0.5 + dx * 0.55, ty + 0.5 + dy * 0.55
                mb.box(px - 0.05, 0.9, pz - 0.05, px + 0.05, 1.2, pz + 0.05, (0.3, 0.22, 0.14), 1.0)
                mb.add("frustum", (px, 1.26, pz), (0.09, 0, 0), (0, 0.07, 0), (0, 0, 0.09), (0.2, 0.2, 0.22), 1.0)
                geo.torches.append((px * 40, pz * 40, 1.4 * 40))
                break
    # masse rocheuse au-delà des murs (blocs fusionnés par rangées) et bordure hors de la carte
    top = tuple(c / 255.0 for c in th["top"])
    mb.mat = STONE
    hr = 4.15 * WALL_H - 0.03
    for y in range(H):
        x = 0
        while x < W:
            if is_floor(x, y):
                x += 1
                continue
            x0 = x
            while x < W and not is_floor(x, y):
                x += 1
            k = 0.85 + 0.3 * rng.random()
            mb.box(x0, hr - 0.04, y, x, hr + rng.uniform(0.0, 0.03), y + 1, tuple(c * k for c in top), 1.0)
    for x0, z0, x1, z1 in ((-30, -30, W + 30, 0), (-30, H, W + 30, H + 30), (-30, 0, 0, H), (W, 0, W + 30, H)):
        mb.box(x0, hr - 0.04, z0, x1, hr, z1, tuple(c * 0.8 for c in top), 0.0)
    mb.mat = 0
    _props(mb, d, th, rng, is_floor)
    inst.export(geo)


def _props(mb, d, th, rng, is_floor):
    """Mobilier le long des murs, choisi selon l'ambiance."""
    choices = th.get("props") or []
    if not choices:
        return
    total = sum(w for _, _, w in choices)
    density = th.get("prop_density", 0.07)
    for y in range(d.h):
        for x in range(d.w):
            if not is_floor(x, y) or rng.random() > density:
                continue
            walls = [(dx, dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if not is_floor(x + dx, y + dy)]
            if not walls:
                continue
            dx, dy = rng.choice(walls)
            r = rng.random() * total
            for fam, name, w in choices:
                r -= w
                if r <= 0:
                    break
            path = os.path.join(PROP_DIRS[fam], name + ".obj")
            if not os.path.exists(path):
                continue
            arr = objmodels.load(path)
            px, pz = x + 0.5 + dx * 0.28, y + 0.5 + dy * 0.28
            rot = math.atan2(-dx, -dy) + rng.uniform(-0.3, 0.3)
            mb.add_model(arr, (px, 0.0, pz), rng.uniform(0.85, 1.1), rot, 0.0, rng.uniform(0.85, 1.05))
