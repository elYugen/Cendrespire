"""Transforme la grille d'un étage en maillage 3D statique (sol, murs, piliers, torches, décor)."""
import math
import random

from ..dungeon import WALL, FLOOR, BARRIER
from ..settings import TILE
from . import camp
from .meshes import MeshBuilder

# Ambiances : couleurs du sol / des murs, torches, lumière
THEMES = {
    "geoles": dict(floor=(92, 88, 84), alt=(74, 82, 66), wall=(100, 94, 90), top=(66, 62, 60), torch=(255, 150, 70),
                   sky=(0.34, 0.34, 0.44), ground=(0.17, 0.15, 0.15), sun=(0.32, 0.35, 0.46)),
    "ossuaire": dict(floor=(128, 116, 96), alt=(150, 142, 120), wall=(124, 112, 94), top=(90, 80, 66),
                     torch=(255, 170, 90), sky=(0.41, 0.37, 0.34), ground=(0.19, 0.17, 0.14), sun=(0.35, 0.34, 0.32)),
    "forges": dict(floor=(70, 60, 56), alt=(96, 50, 36), wall=(84, 66, 60), top=(54, 44, 42), torch=(255, 120, 50),
                   sky=(0.37, 0.24, 0.20), ground=(0.24, 0.10, 0.07), sun=(0.41, 0.22, 0.16), lava=True),
    "sanctuaire": dict(floor=(88, 78, 104), alt=(110, 96, 130), wall=(100, 88, 122), top=(66, 58, 82),
                       torch=(190, 120, 255), sky=(0.34, 0.29, 0.46), ground=(0.17, 0.14, 0.20), sun=(0.32, 0.27, 0.46)),
    "cryptes": dict(floor=(124, 144, 164), alt=(160, 184, 204), wall=(150, 170, 192), top=(206, 222, 236),
                    torch=(140, 200, 255), sky=(0.44, 0.51, 0.61), ground=(0.20, 0.24, 0.31), sun=(0.41, 0.49, 0.62)),
    "fosse": dict(floor=(66, 92, 84), alt=(80, 116, 88), wall=(76, 100, 92), top=(50, 68, 62), torch=(120, 255, 170),
                  sky=(0.27, 0.41, 0.37), ground=(0.12, 0.19, 0.17), sun=(0.27, 0.41, 0.38)),
    "ecarlates": dict(floor=(112, 64, 64), alt=(134, 80, 76), wall=(122, 72, 70), top=(80, 44, 44),
                      torch=(255, 90, 70), sky=(0.44, 0.24, 0.24), ground=(0.20, 0.10, 0.10), sun=(0.43, 0.24, 0.24)),
    "trone": dict(floor=(54, 52, 60), alt=(96, 84, 52), wall=(72, 66, 64), top=(150, 124, 60), torch=(255, 200, 90),
                  sky=(0.31, 0.29, 0.34), ground=(0.14, 0.14, 0.15), sun=(0.32, 0.30, 0.35)),
    "camp": dict(floor=(86, 132, 62), alt=(118, 96, 64), wall=(122, 116, 106), top=(90, 140, 64), torch=(255, 160, 80),
                 sky=(0.36, 0.38, 0.5), ground=(0.16, 0.16, 0.14), sun=(0.42, 0.44, 0.58)),
}
FLOOR_THEMES = ["geoles", "ossuaire", "forges", "sanctuaire", "cryptes", "fosse", "ecarlates", "trone"]


def floor_theme(floor):
    return FLOOR_THEMES[(floor - 1) % len(FLOOR_THEMES)]


def _jit(c, v, rng):
    d = rng.uniform(-v, v)
    return tuple(max(0.0, min(1.0, (ch + d) / 255.0)) for ch in c)


def _f(c):
    return tuple(ch / 255.0 for ch in c)


class LevelGeometry:
    def __init__(self):
        self.mesh = None
        self.torches = []    # (x, y, z) logiques des flammes
        self.candles = []
        self.lava = []       # (x, y) des fissures incandescentes
        self.tower = None    # hub : position de la tour


def build(d, theme_name, rng=None, hub=False):
    rng = rng or random.Random(1)
    th = THEMES[theme_name]
    mb = MeshBuilder()
    geo = LevelGeometry()
    T = 1.0
    tiles = d.tiles

    def is_floor(x, y):
        return 0 <= x < d.w and 0 <= y < d.h and tiles[y][x] != WALL

    # dessous sombre (visible dans les joints entre les dalles)
    mb.box(-2, -0.3, -2, d.w + 2, -0.1, d.h + 2, (0.03, 0.03, 0.035))
    for y in range(d.h):
        for x in range(d.w):
            if not is_floor(x, y):
                continue
            alt = rng.random() < 0.12
            c = _jit(th["alt"] if alt else th["floor"], 9, rng)
            if hub:
                _camp_floor(mb, d, x, y, rng)
            else:
                g = 0.03
                h = rng.uniform(-0.015, 0.0)
                mb.box(x + g, -0.12, y + g, x + 1 - g, h, y + 1 - g, c)
            if th.get("lava") and rng.random() < 0.05:
                geo.lava.append(((x + 0.5) * TILE, (y + 0.5) * TILE))
    walls = []
    for y in range(d.h):
        for x in range(d.w):
            if is_floor(x, y):
                continue
            near = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if is_floor(x + dx, y + dy)]
            if not near and not hub:
                continue
            walls.append((x, y, near))
    for x, y, near in walls:
        four = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if is_floor(x + dx, y + dy))
        if four == 4 and not hub:
            # pilier isolé : colonne ronde
            c = _jit(th["wall"], 6, rng)
            mb.add("cylinder", (x + 0.5, 1.0, y + 0.5), (0.36, 0, 0), (0, 1.0, 0), (0, 0, 0.36), c, 1.0)
            mb.box(x + 0.08, 0, y + 0.08, x + 0.92, 0.25, y + 0.92, _f(th["top"]), 1.0)
            mb.box(x + 0.08, 1.85, y + 0.08, x + 0.92, 2.1, y + 0.92, _f(th["top"]), 1.0)
            continue
        if hub and d.tiles[y][x] == WALL and getattr(d, "tower_tiles", None) and (x, y) in d.tower_tiles:
            mb.box(x, 0, y, x + 1, 0.1, y + 1, _jit((70, 96, 58), 6, rng))
            continue
        if hub:
            # clairière : talus herbeux bas couverts d'arbres
            H = rng.uniform(0.3, 0.55)
            mb.box(x, 0, y, x + 1, H, y + 1, _jit((104, 96, 84), 10, rng), 1.0)
            mb.box(x - 0.02, H, y - 0.02, x + 1.02, H + 0.08, y + 1.02, _jit((64, 104, 52), 8, rng), 1.0)
            if rng.random() < 0.8:
                camp.tree(mb, x + rng.uniform(0.3, 0.7), H + 0.08, y + rng.uniform(0.3, 0.7), rng)
            continue
        H = rng.uniform(1.5, 1.9) if not hub else rng.uniform(1.0, 2.2)
        c = _jit(th["wall"], 8, rng)
        mb.box(x, 0, y, x + 1, H, y + 1, c, 1.0)
        mb.box(x - 0.03, H, y - 0.03, x + 1.03, H + 0.12, y + 1.03, _jit(th["top"], 6, rng), 1.0)
        # pierres en relief sur les faces visibles
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            if is_floor(x + dx, y + dy) and rng.random() < 0.55:
                for _ in range(rng.randint(1, 2)):
                    u = rng.uniform(0.15, 0.85)
                    v = rng.uniform(0.2, H - 0.3)
                    sz = rng.uniform(0.12, 0.22)
                    px = x + (u if dx == 0 else (1.0 if dx > 0 else 0.0))
                    pz = y + (u if dy == 0 else (1.0 if dy > 0 else 0.0))
                    mb.box(px - sz, v - sz * 0.6, pz - sz, px + sz, v + sz * 0.6, pz + sz,
                           _jit(th["wall"], 14, rng), 1.0)
        # torches
        if (x, y) in d.torches:
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                if is_floor(x + dx, y + dy):
                    px = x + 0.5 + dx * 0.55
                    pz = y + 0.5 + dy * 0.55
                    mb.box(px - 0.05, 0.9, pz - 0.05, px + 0.05, 1.2, pz + 0.05, (0.3, 0.22, 0.14), 1.0)
                    mb.add("frustum", (px, 1.26, pz), (0.09, 0, 0), (0, 0.07, 0), (0, 0, 0.09), (0.2, 0.2, 0.22), 1.0)
                    geo.torches.append((px * TILE, pz * TILE, 1.4 * TILE))
                    break
    # décor au sol
    for kind, x, y in d.decor:
        cx, cz = x + rng.uniform(0.25, 0.75), y + rng.uniform(0.25, 0.75)
        if kind == "os":
            a = rng.random() * math.pi
            mb.add("cylinder", (cx, 0.04, cz), (0, 0.04, 0), (math.cos(a) * 0.2, 0, math.sin(a) * 0.2),
                   (-math.sin(a) * 0.04, 0, math.cos(a) * 0.04), (0.86, 0.83, 0.74))
        elif kind == "crane":
            mb.add("sphere", (cx, 0.1, cz), (0.11, 0, 0), (0, 0.1, 0), (0, 0, 0.11), (0.9, 0.87, 0.78))
        elif kind == "bougie":
            for i in range(rng.randint(1, 3)):
                ox, oz = rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12)
                h = rng.uniform(0.08, 0.18)
                mb.add("cylinder", (cx + ox, h, cz + oz), (0.035, 0, 0), (0, h, 0), (0, 0, 0.035), (0.92, 0.88, 0.76))
                geo.candles.append(((cx + ox) * TILE, (cz + oz) * TILE, (h * 2 + 0.04) * TILE))
        elif kind == "caisse":
            s = rng.uniform(0.16, 0.24)
            mb.box(cx - s, 0, cz - s, cx + s, s * 2, cz + s, (0.6, 0.44, 0.25))
        elif kind == "chaine":
            for i in range(4):
                mb.add("sphere", (cx + i * 0.07, 0.02, cz), (0.04, 0, 0), (0, 0.02, 0), (0, 0, 0.04), (0.35, 0.35, 0.38))
        elif kind == "herbe":
            for _ in range(rng.randint(3, 6)):
                ox, oz = rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)
                h = rng.uniform(0.06, 0.16)
                g = _jit((80, 150, 60), 20, rng)
                mb.add("cone", (cx + ox, h, cz + oz), (0.03, 0, 0), (rng.uniform(-0.03, 0.03), h, 0), (0, 0, 0.03), g)
        elif kind == "fleur":
            col = rng.choice([(0.95, 0.85, 0.3), (0.9, 0.4, 0.5), (0.7, 0.6, 0.95), (1, 1, 1)])
            mb.add("cylinder", (cx, 0.07, cz), (0.01, 0, 0), (0, 0.07, 0), (0, 0, 0.01), (0.3, 0.6, 0.25))
            mb.add("sphere", (cx, 0.15, cz), (0.04, 0, 0), (0, 0.03, 0), (0, 0, 0.04), col)
        elif kind == "buisson":
            g = _jit((70, 128, 56), 18, rng)
            for _ in range(rng.randint(2, 4)):
                ox, oz = rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15)
                r = rng.uniform(0.13, 0.22)
                mb.add("sphere", (cx + ox, r * 0.7, cz + oz), (r, 0, 0), (0, r * 0.8, 0), (0, 0, r), g)
        elif kind == "champignon":
            for _ in range(rng.randint(1, 3)):
                ox, oz = rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12)
                h = rng.uniform(0.05, 0.09)
                mb.add("cylinder", (cx + ox, h / 2, cz + oz), (0.015, 0, 0), (0, h / 2, 0), (0, 0, 0.015), (0.9, 0.88, 0.8))
                mb.add("sphere", (cx + ox, h, cz + oz), (0.045, 0, 0), (0, 0.025, 0), (0, 0, 0.045), (0.8, 0.2, 0.16))
        elif kind == "souche":
            mb.add("cylinder", (cx, 0.07, cz), (0.14, 0, 0), (0, 0.07, 0), (0, 0, 0.14), (0.42, 0.3, 0.2))
            mb.add("cylinder", (cx, 0.141, cz), (0.11, 0, 0), (0, 0.002, 0), (0, 0, 0.11), (0.72, 0.58, 0.38))
        elif kind == "rocher":
            s = rng.uniform(0.12, 0.3)
            mb.add("sphere", (cx, s * 0.5, cz), (s, 0, 0), (0, s * 0.7, 0), (0, 0, s * 1.1), _jit((120, 116, 110), 10, rng))
    if hub:
        camp.forest(mb, d, rng, is_floor)
        camp.build(mb, geo, d, rng, TILE)
    geo.mesh = mb.build()
    return geo


def _camp_floor(mb, d, x, y, rng):
    """Sol du campement : herbe aux teintes douces, chemins de terre, place pavée autour du feu."""
    if (x, y) in getattr(d, "plaza", ()):
        mb.box(x, -0.12, y, x + 1, -0.01, y + 1, (0.2, 0.18, 0.15))
        for i in range(2):
            for j in range(2):
                g = rng.uniform(0.03, 0.05)
                h = rng.uniform(0.0, 0.015)
                mb.box(x + i * 0.5 + g, -0.02, y + j * 0.5 + g, x + i * 0.5 + 0.5 - g, h, y + j * 0.5 + 0.5 - g,
                       _jit((98, 94, 88), 14, rng))
        return
    if (x, y) in getattr(d, "paths", ()):
        # herbe dessous, puis un disque de terre : les disques voisins se chevauchent en un chemin aux bords ronds
        mb.box(x, -0.12, y, x + 1, 0, y + 1, _jit((84, 128, 58), 4, rng))
        r = rng.uniform(0.66, 0.78)
        mb.add("cylinder", (x + 0.5 + rng.uniform(-0.08, 0.08), 0.004, y + 0.5 + rng.uniform(-0.08, 0.08)), (r, 0, 0),
               (0, 0.004, 0), (0, 0, r), _f((118, 96, 68)))
        if rng.random() < 0.5:
            s = rng.uniform(0.05, 0.09)
            px, pz = x + rng.uniform(0.2, 0.8), y + rng.uniform(0.2, 0.8)
            mb.add("sphere", (px, 0.0, pz), (s, 0, 0), (0, s * 0.5, 0), (0, 0, s * 1.2), _jit((120, 114, 104), 12, rng))
        return
    n = 0.5 + 0.5 * math.sin(x * 0.45 + y * 0.2) * math.cos(y * 0.37 - x * 0.13)
    base = tuple(a + (b - a) * n for a, b in zip((72, 120, 52), (108, 150, 66)))
    mb.box(x, -0.12, y, x + 1, 0, y + 1, _jit(base, 4, rng))
