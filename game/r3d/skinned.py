"""Personnages animés importés (glTF binaire .glb, squelette + animations), animés sur la carte graphique.

- load(nom) lit assets/models/characters/<nom>.glb une seule fois : sommets (position, normale, articulations,
  poids, numéro de matériau), squelette, animations.
- Model.pose(anim, t) calcule les matrices des articulations pour un instant donné (interpolation linéaire des
  positions, sphérique des rotations). Le calcul des sommets déformés est fait par le shader (SKIN_VS).
- Les couleurs viennent d'une palette par personnage (un numéro de matériau par sommet) : teint, cheveux et
  tenues de la personnalisation remplacent les couleurs d'origine.
"""
import json
import math
import os
import struct

import numpy as np

from ..settings import ASSETS_DIR

CHAR_DIR = os.path.join(ASSETS_DIR, "models", "characters")
MAX_JOINTS = 64
MAX_MATS = 16
STRIDE = 3 + 3 + 1 + 3 + 4 + 4    # position, normale, matériau, couleur, articulations, poids

SKIP_MESHES = {"Backpack"}
# étalonnage des couleurs par modèle (saturation, luminosité, rotation de teinte en degrés) : les modèles à texture
# ne se recolorent pas par matériau
GRADE = {"zombie": (0.75, 0.95, -115.0),      # zombie bleu du pack -> goule verdâtre
         "yeti_block": (0.12, 0.92, 0.0)}      # yéti bleu et blanc -> golem d'os et de pierre        # accessoires encombrants du pack, remplacés par l'équipement du jeu
_COMP = {5120: "b", 5121: "B", 5122: "h", 5123: "H", 5125: "I", 5126: "f"}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
_models = {}
ENABLED = True          # passe à False si la carte graphique ne compile pas le shader d'animation


def _srgb(c):
    """Couleurs glTF linéaires -> sRGB (couleurs affichées par le moteur)."""
    return tuple(max(0.0, min(1.0, v)) ** (1 / 2.2) for v in c[:3])


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]], dtype="f4")


def trs(t, r, s):
    m = np.eye(4, dtype="f4")
    m[:3, :3] = quat_mat(r) * np.array(s, dtype="f4")[None, :]
    m[:3, 3] = t
    return m


def slerp(a, b, k):
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        q = a + (b - a) * k
    else:
        th = math.acos(d)
        q = (math.sin((1 - k) * th) * a + math.sin(k * th) * b) / math.sin(th)
    return q / (np.linalg.norm(q) or 1.0)


class Model:
    def __init__(self, path):
        with open(path, "rb") as f:
            data = f.read()
        jlen = struct.unpack("<I", data[12:16])[0]
        g = json.loads(data[20:20 + jlen])
        off = 20 + jlen
        blen = struct.unpack("<I", data[off:off + 4])[0]
        binary = data[off + 8:off + 8 + blen]
        self.g = g

        def acc(i):
            a = g["accessors"][i]
            v = g["bufferViews"][a["bufferView"]]
            n, comps = a["count"], _NCOMP[a["type"]]
            fmt = np.dtype("<" + _COMP[a["componentType"]])
            start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
            stride = v.get("byteStride", 0) or fmt.itemsize * comps
            raw = np.frombuffer(binary, dtype=np.uint8, count=stride * (n - 1) + fmt.itemsize * comps, offset=start)
            if stride == fmt.itemsize * comps:
                arr = np.frombuffer(raw.tobytes(), dtype=fmt).reshape(n, comps)
            else:
                arr = np.stack([np.frombuffer(raw[i * stride:i * stride + fmt.itemsize * comps].tobytes(), dtype=fmt)
                                for i in range(n)])
            if a.get("normalized") and fmt.kind in "iu":
                arr = arr.astype("f4") / np.iinfo(fmt).max
            return arr

        nodes = g["nodes"]
        self.names = [n.get("name", "") for n in nodes]
        self.parent = [-1] * len(nodes)
        for i, n in enumerate(nodes):
            for c in n.get("children", []):
                self.parent[c] = i
        self.rest = [(np.array(n.get("translation", (0, 0, 0)), "f4"), np.array(n.get("rotation", (0, 0, 0, 1)), "f4"),
                      np.array(n.get("scale", (1, 1, 1)), "f4")) for n in nodes]
        # ordre de calcul : parents avant enfants
        self.order = []
        seen = set()

        def visit(i):
            if i in seen:
                return
            if self.parent[i] >= 0:
                visit(self.parent[i])
            seen.add(i)
            self.order.append(i)
        for i in range(len(nodes)):
            visit(i)

        skin = g["skins"][0]
        self.joints = skin["joints"]
        self.ibm = acc(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1).astype("f4")
        jidx = {n: k for k, n in enumerate(self.joints)}
        self.materials = [m.get("name", f"mat{i}") for i, m in enumerate(g.get("materials", []))]
        self.base_colors = [_srgb(m.get("pbrMetallicRoughness", {}).get("baseColorFactor", (0.8, 0.8, 0.8, 1)))
                            for m in g.get("materials", [])]
        self.tex_factor = [tuple(m.get("pbrMetallicRoughness", {}).get("baseColorFactor", (1, 1, 1, 1))[:3])
                           for m in g.get("materials", [])]
        # textures-palettes (atlas de couleurs) : la couleur est lue à chaque sommet
        images = {}

        def texture(mi):
            m = g["materials"][mi] if mi is not None and mi < len(g.get("materials", [])) else {}
            t = m.get("pbrMetallicRoughness", {}).get("baseColorTexture")
            if t is None:
                return None
            src = g["textures"][t["index"]]["source"]
            if src not in images:
                import io
                import pygame
                im = g["images"][src]
                v = g["bufferViews"][im["bufferView"]]
                raw = binary[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]
                try:
                    images[src] = pygame.surfarray.array3d(pygame.image.load(io.BytesIO(raw))).astype("f4") / 255
                except (pygame.error, ValueError):
                    images[src] = None
            return images[src]

        verts = []
        for ni, n in enumerate(nodes):
            if "mesh" not in n or "skin" not in n or n.get("name") in SKIP_MESHES:
                continue            # objets non articulés (épée tenue...) : ignorés, le jeu dessine ses armes
            sk = g["skins"][n["skin"]]
            remap = np.array([jidx[j] for j in sk["joints"]], dtype="f4")
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                at = prim["attributes"]
                pos = acc(at["POSITION"]).astype("f4")
                nor = acc(at["NORMAL"]).astype("f4")
                jn = remap[acc(at["JOINTS_0"]).astype("i4")]
                wt = acc(at["WEIGHTS_0"]).astype("f4")
                wt /= wt.sum(1, keepdims=True) + 1e-9
                mi = prim.get("material", 0)
                mat = np.full((len(pos), 1), mi, "f4")
                base = np.array(self.base_colors[mi] if mi < len(self.base_colors) else (0.8, 0.8, 0.8), "f4")
                col = np.tile(base, (len(pos), 1))
                tex = texture(mi)
                if tex is not None and "TEXCOORD_0" in at:
                    uv = acc(at["TEXCOORD_0"]).astype("f4")
                    w, h = tex.shape[0], tex.shape[1]
                    xs = np.clip(((uv[:, 0] % 1.0) * w).astype(int), 0, w - 1)
                    ys = np.clip(((uv[:, 1] % 1.0) * h).astype(int), 0, h - 1)
                    col = tex[xs, ys] * np.array(self.tex_factor[mi], "f4")
                v = np.hstack([pos, nor, mat, col, jn, wt]).astype("f4")
                idx = acc(prim["indices"]).reshape(-1) if "indices" in prim else np.arange(len(pos))
                verts.append(v[idx])
        self.vertices = np.ascontiguousarray(np.vstack(verts), dtype="f4")
        grade = GRADE.get(os.path.splitext(os.path.basename(path))[0])
        if grade:
            sat, bright, hue = grade
            col = self.vertices[:, 7:10]
            if hue:                      # rotation de teinte autour de l'axe des gris
                a = math.radians(hue)
                c, s_, k = math.cos(a), math.sin(a), 1 / 3
                sq = math.sqrt(k)
                rot = np.array([[c + (1 - c) * k, k * (1 - c) - sq * s_, k * (1 - c) + sq * s_],
                                [k * (1 - c) + sq * s_, c + k * (1 - c), k * (1 - c) - sq * s_],
                                [k * (1 - c) - sq * s_, k * (1 - c) + sq * s_, c + k * (1 - c)]], "f4")
                col = col @ rot.T
            gray = col.mean(1, keepdims=True)
            self.vertices[:, 7:10] = np.clip((gray + (col - gray) * sat) * bright, 0.0, 1.0)
        self.anims = {}
        for a in g.get("animations", []):
            # « CharacterArmature|Run » -> « Run » ; certains exports répètent l'armature et tronquent la fin
            # (« CharacterArmature|...|Death|CharacterArmature|Dea ») : on garde le premier nom qui n'est pas une armature
            parts = [q for q in a["name"].split("|") if q and "Armatur" not in q]
            name = parts[0] if parts else a["name"]
            chans = []
            dur = 0.0
            for ch in a["channels"]:
                smp = a["samplers"][ch["sampler"]]
                times = acc(smp["input"]).reshape(-1)
                vals = acc(smp["output"]).astype("f4")
                dur = max(dur, float(times[-1]))
                chans.append((ch["target"]["node"], ch["target"]["path"], times, vals))
            self.anims[name] = (chans, dur)
        # taille au repos (sommets déformés par le squelette), pour mettre tous les modèles à la même échelle
        mats, _ = self.pose(None, 0.0)
        v = self.vertices
        P = np.hstack([v[:, 0:3], np.ones((len(v), 1), "f4")])
        J = v[:, 10:14].astype(int)
        M = np.einsum("nk,nkij->nij", v[:, 14:18], mats[J])
        out = np.einsum("nij,nj->ni", M, P)[:, :3]
        self.height = float(out[:, 1].max() - out[:, 1].min()) or 1.0
        self.floor = float(out[:, 1].min())

    def world_matrices(self, anim, t):
        local = {}
        if anim in self.anims:
            chans, dur = self.anims[anim]
            for node, path, times, vals in chans:
                i = int(np.searchsorted(times, t))
                if i <= 0:
                    v = vals[0]
                elif i >= len(times):
                    v = vals[-1]
                else:
                    k = (t - times[i - 1]) / max(1e-6, times[i] - times[i - 1])
                    v = slerp(vals[i - 1], vals[i], k) if path == "rotation" else vals[i - 1] + (vals[i] - vals[i - 1]) * k
                local.setdefault(node, {})[path] = v
        world = [None] * len(self.names)
        for i in self.order:
            t0, r0, s0 = self.rest[i]
            o = local.get(i)
            m = trs(o.get("translation", t0), o.get("rotation", r0), o.get("scale", s0)) if o else trs(t0, r0, s0)
            p = self.parent[i]
            world[i] = world[p] @ m if p >= 0 else m
        return world

    def duration(self, anim):
        return self.anims[anim][1] if anim in self.anims else 1.0

    def pose(self, anim, t, loop=True):
        """Matrices des articulations (J, 4, 4) et matrices « monde » des nœuds, à l'instant t (secondes)."""
        d = self.duration(anim)
        t = (t % d) if loop else min(t, d - 1e-3)
        world = self.world_matrices(anim, t)
        mats = np.array([world[j] @ self.ibm[k] for k, j in enumerate(self.joints)], dtype="f4")
        return mats, world

    def node(self, name):
        return self.names.index(name) if name in self.names else -1

    def palette(self, overrides):
        """Couleurs des matériaux (0-1), en remplaçant celles indiquées {nom de matériau: (r, g, b) 0-255}."""
        pal = np.zeros((MAX_MATS, 4), dtype="f4")      # rgb + 1 si la couleur remplace celle du modèle
        for i, name in enumerate(self.materials[:MAX_MATS]):
            c = overrides.get(name)
            if c == "hide":
                pal[i] = (-1.0, -1.0, -1.0, 1.0)     # matériau masqué (le shader ne le dessine pas)
            elif c:
                pal[i] = (c[0] / 255, c[1] / 255, c[2] / 255, 1.0)
        return pal


def load(name):
    if not ENABLED:
        return None
    if name not in _models:
        path = os.path.join(CHAR_DIR, name + ".glb")
        try:
            _models[name] = Model(path)
        except (OSError, ValueError, KeyError, IndexError, struct.error) as e:
            print(f"[personnages] {path} illisible : {e} (modèle procédural utilisé)")
            _models[name] = None
    return _models[name]


# =========================================================================== objets tenus (armes, boucliers)
PROP_DIR = os.path.join(ASSETS_DIR, "models", "weapons")
_props = {}


class Prop:
    """Objet glTF non animé (arme, bouclier), dessiné comme un personnage à un seul os : la matrice de cet os
    place l'objet dans la main à chaque image. Axe de l'objet : +Y, poignée vers le bas."""

    def __init__(self, path):
        m = Model.__new__(Model)
        with open(path, "rb") as f:
            data = f.read()
        jlen = struct.unpack("<I", data[12:16])[0]
        g = json.loads(data[20:20 + jlen])
        off = 20 + jlen
        blen = struct.unpack("<I", data[off:off + 4])[0]
        binary = data[off + 8:off + 8 + blen]
        nodes = g["nodes"]
        parent = [-1] * len(nodes)
        for i, n in enumerate(nodes):
            for c in n.get("children", []):
                parent[c] = i

        def local(n):
            if "matrix" in n:
                return np.array(n["matrix"], "f4").reshape(4, 4).T
            return trs(n.get("translation", (0, 0, 0)), n.get("rotation", (0, 0, 0, 1)), n.get("scale", (1, 1, 1)))

        def world(i):
            mtx = local(nodes[i])
            while parent[i] >= 0:
                i = parent[i]
                mtx = local(nodes[i]) @ mtx
            return mtx

        def acc(i):
            a = g["accessors"][i]
            v = g["bufferViews"][a["bufferView"]]
            comps = _NCOMP[a["type"]]
            fmt = np.dtype("<" + _COMP[a["componentType"]])
            start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
            stride = v.get("byteStride", 0) or fmt.itemsize * comps
            if stride == fmt.itemsize * comps:
                return np.frombuffer(binary, dtype=fmt, count=a["count"] * comps, offset=start).reshape(-1, comps)
            return np.stack([np.frombuffer(binary, dtype=fmt, count=comps, offset=start + k * stride)
                             for k in range(a["count"])])
        mats = g.get("materials", [])
        cols = [_srgb(mm.get("pbrMetallicRoughness", {}).get("baseColorFactor", (0.8, 0.8, 0.8, 1))) for mm in mats]
        verts = []
        for i, n in enumerate(nodes):
            if "mesh" not in n:
                continue
            W = world(i)
            N = np.linalg.inv(W[:3, :3]).T
            for prim in g["meshes"][n["mesh"]]["primitives"]:
                at = prim["attributes"]
                pos = acc(at["POSITION"]).astype("f4")
                nor = acc(at["NORMAL"]).astype("f4") if "NORMAL" in at else np.tile((0, 1, 0), (len(pos), 1)).astype("f4")
                pos = pos @ W[:3, :3].T + W[:3, 3]
                nor = nor @ N.T
                nor /= np.linalg.norm(nor, axis=1, keepdims=True) + 1e-9
                mi = prim.get("material", 0)
                col = np.tile(np.array(cols[mi] if mi < len(cols) else (0.8, 0.8, 0.8), "f4"), (len(pos), 1))
                n0 = len(pos)
                v = np.hstack([pos, nor, np.full((n0, 1), mi, "f4"), col, np.zeros((n0, 4), "f4"),
                               np.tile((1, 0, 0, 0), (n0, 1)).astype("f4")]).astype("f4")
                idx = acc(prim["indices"]).reshape(-1) if "indices" in prim else np.arange(n0)
                verts.append(v[idx])
        self.vertices = np.ascontiguousarray(np.vstack(verts), dtype="f4")
        self.materials = [mm.get("name", "") for mm in mats]
        p = self.vertices[:, 0:3]
        self.lo, self.hi = p.min(0), p.max(0)
        self.length = float(self.hi[1] - self.lo[1]) or 1.0

    def palette(self, overrides=None):
        return np.zeros((MAX_MATS, 4), dtype="f4")


def load_prop(name):
    if not ENABLED:
        return None
    if name not in _props:
        path = os.path.join(PROP_DIR, name + ".glb")
        try:
            _props[name] = Prop(path)
        except (OSError, ValueError, KeyError, IndexError, struct.error) as e:
            print(f"[armes] {path} illisible : {e}")
            _props[name] = None
    return _props[name]
