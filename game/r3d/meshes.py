"""Génération des maillages (numpy) : primitives lisses et assemblage des niveaux.

Format de sommet : position (3), normale (3), couleur RGBA (4) — 10 floats.
La composante alpha de la couleur sert de marqueur (1 = mur coupable par la caméra).
"""
import math

import numpy as np

STRIDE = 10


def _tri(out, a, b, c, na, nb, nc, col):
    for p, n in ((a, na), (b, nb), (c, nc)):
        out.extend((p[0], p[1], p[2], n[0], n[1], n[2], col[0], col[1], col[2], col[3]))


def _quad(out, a, b, c, d, n, col):
    _tri(out, a, b, c, n, n, n, col)
    _tri(out, a, c, d, n, n, n, col)


WHITE = (1.0, 1.0, 1.0, 0.0)


def cube():
    v = []
    for axis in range(3):
        for sign in (1, -1):
            n = [0.0, 0.0, 0.0]
            n[axis] = sign
            u = [0.0, 0.0, 0.0]
            w = [0.0, 0.0, 0.0]
            u[(axis + 1) % 3] = 1
            w[(axis + 2) % 3] = 1
            c = [n[0], n[1], n[2]]
            pts = []
            for su, sw in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
                pts.append([c[i] + u[i] * su + w[i] * sw for i in range(3)])
            _quad(v, pts[0], pts[1], pts[2], pts[3], n, WHITE)
    return np.array(v, dtype="f4")


def sphere(rings=12, segs=20):
    v = []

    def P(i, j):
        th = math.pi * i / rings
        ph = math.tau * j / segs
        return (math.sin(th) * math.cos(ph), math.cos(th), math.sin(th) * math.sin(ph))
    for i in range(rings):
        for j in range(segs):
            a, b, c, d = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)
            _tri(v, a, b, c, a, b, c, WHITE)
            _tri(v, a, c, d, a, c, d, WHITE)
    return np.array(v, dtype="f4")


def cylinder(segs=20, top=1.0):
    """Cylindre (ou tronc de cône si top < 1) le long de Y, de -1 à 1, rayon 1."""
    v = []
    slope = (1.0 - top) / 2.0
    for j in range(segs):
        a0, a1 = math.tau * j / segs, math.tau * (j + 1) / segs
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        n0 = (c0, slope, s0)
        n1 = (c1, slope, s1)
        b0, b1 = (c0, -1, s0), (c1, -1, s1)
        t0, t1 = (c0 * top, 1, s0 * top), (c1 * top, 1, s1 * top)
        _tri(v, b0, t0, t1, n0, n0, n1, WHITE)
        _tri(v, b0, t1, b1, n0, n1, n1, WHITE)
        _tri(v, (0, -1, 0), b1, b0, (0, -1, 0), (0, -1, 0), (0, -1, 0), WHITE)
        if top > 0:
            _tri(v, (0, 1, 0), t0, t1, (0, 1, 0), (0, 1, 0), (0, 1, 0), WHITE)
    return np.array(v, dtype="f4")


def cone(segs=20):
    return cylinder(segs, top=0.0)


def quad2d():
    """Quadrilatère -1..1 (pour décalques, particules, plein écran)."""
    return np.array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1], dtype="f4")


PRIMITIVES = {"cube": cube, "sphere": sphere, "cylinder": cylinder, "cone": cone,
              "frustum": lambda: cylinder(20, 0.55)}


# --------------------------------------------------------------------------- assemblage statique
class MeshBuilder:
    """Accumule des primitives transformées dans un seul maillage statique (niveau, décor)."""

    # matériaux (textures procédurales du shader) : 0 aucun, 1 dalles de pierre, 2 briques, 3 herbe, 4 terre
    NONE, STONE, BRICK, GRASS, DIRT = 0, 1, 2, 3, 4

    def __init__(self):
        self.parts = []
        self.mat = 0
        self._prims = {k: f().reshape(-1, STRIDE) for k, f in PRIMITIVES.items()}

    def add(self, prim, center, ax, ay, az, color, flag=0.0):
        base = self._prims[prim]
        M = np.array([ax, ay, az], dtype="f4").T
        pos = base[:, 0:3] @ M.T + np.array(center, dtype="f4")
        try:
            N = np.linalg.inv(M).T
        except np.linalg.LinAlgError:
            N = M
        nrm = base[:, 3:6] @ N.T
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        col = np.empty((len(base), 4), dtype="f4")
        col[:, 0:3] = color[:3]
        col[:, 3] = flag + 2 * self.mat           # bit « coupable » + 2 × matériau
        self.parts.append(np.hstack([pos, nrm, col]).astype("f4"))

    def box(self, x0, y0, z0, x1, y1, z1, color, flag=0.0):
        """Pavé aligné sur les axes (coordonnées 3D)."""
        c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        self.add("cube", c, ((x1 - x0) / 2, 0, 0), (0, (y1 - y0) / 2, 0), (0, 0, (z1 - z0) / 2), color, flag)

    def raw(self, arr):
        self.parts.append(arr)

    def add_model(self, arr, pos, scale, rot, flag=0.0, tint=1.0):
        """Modèle importé (objmodels.load) : échelle uniforme, rotation autour de l'axe vertical, puis translation."""
        c, s = np.cos(rot), np.sin(rot)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype="f4")
        out = arr.copy()
        out[:, 0:3] = arr[:, 0:3] @ R.T * scale + np.array(pos, dtype="f4")
        out[:, 3:6] = arr[:, 3:6] @ R.T
        out[:, 6:9] = np.clip(arr[:, 6:9] * tint, 0, 1)
        out[:, 9] = flag
        self.parts.append(out)

    def build(self):
        if not self.parts:
            return np.zeros((0, STRIDE), dtype="f4")
        return np.vstack(self.parts).astype("f4")


def quads_array(quads):
    """quads : liste de (a, b, c, d, normale, couleur rgba) -> tableau de sommets."""
    v = []
    for a, b, c, d, n, col in quads:
        _quad(v, a, b, c, d, n, col)
    return np.array(v, dtype="f4").reshape(-1, STRIDE)
