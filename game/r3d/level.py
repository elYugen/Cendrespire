"""Transforme la grille d'un étage en maillage 3D statique (sol, murs, piliers, torches, décor)."""
import math
import random
from contextlib import contextmanager

from ..dungeon import WALL, FLOOR, BARRIER, PIT, LEDGE, STAIRS, PLAT_H
from ..settings import TILE
from . import camp, city, dressing, dungeon_kit, objmodels
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
# mobilier par ambiance : (famille, modèle, poids) — familles : props (Mini Dungeon), grave (Graveyard Kit)
_P = {
    "prison": [("props", "barrel", 3), ("props", "table", 1), ("props", "chair", 2), ("props", "wood-support", 2),
               ("props", "pot", 2), ("props", "stones", 1)],
    "bones": [("grave", "coffin-old", 2), ("grave", "urn-round", 3), ("grave", "candle-multiple", 3),
              ("grave", "debris", 2), ("grave", "gravestone-broken", 1)],
    "forge": [("props", "barrel", 3), ("props", "wood-structure", 2), ("grave", "fire-basket", 3),
              ("props", "rocks", 2), ("props", "stones", 2)],
    "temple": [("grave", "altar-stone", 1), ("props", "column", 3), ("props", "banner", 2),
               ("grave", "candle-multiple", 3), ("grave", "pillar-obelisk", 1)],
    "crypt": [("grave", "gravestone-round", 3), ("grave", "gravestone-cross", 2), ("grave", "coffin", 2),
              ("grave", "lantern-candle", 2), ("grave", "cross-column", 1)],
    "cave": [("props", "rocks", 4), ("props", "stones", 3), ("grave", "rocks-tall", 2), ("grave", "debris", 2)],
    "hall": [("props", "banner", 3), ("props", "column", 2), ("grave", "fire-basket", 2), ("props", "table", 1),
             ("props", "chair", 1)],
    "throne": [("props", "column", 3), ("props", "banner", 3), ("grave", "fire-basket", 2),
               ("grave", "pillar-obelisk", 1)],
    "mine": [("props", "wood-support", 4), ("props", "wood-structure", 2), ("props", "barrel", 2),
             ("props", "rocks", 2), ("grave", "debris-wood", 2)],
    "library": [("props", "table", 3), ("props", "chair", 3), ("grave", "candle", 3), ("props", "pot", 1),
                ("grave", "bench-damaged", 1)],
    "garden": [("grave", "gravestone-decorative", 2), ("grave", "urn-round", 2), ("props", "rocks", 2),
               ("grave", "bench-damaged", 1), ("grave", "rocks-tall", 1)],
    "necro": [("grave", "gravestone-wide", 2), ("grave", "pillar-obelisk", 2), ("grave", "coffin", 2),
              ("grave", "candle-multiple", 2), ("grave", "column-large", 1)],
}


def _theme(floor, alt, wall, top, torch, sky, ground, sun, props, density=0.07, **kw):
    return dict(floor=floor, alt=alt, wall=wall, top=top, torch=torch, sky=sky, ground=ground, sun=sun,
                props=_P[props], prop_density=density, **kw)


THEMES.update({
    "geoles": _theme((92, 88, 84), (74, 82, 66), (100, 94, 90), (66, 62, 60), (255, 150, 70),
                     (0.34, 0.34, 0.44), (0.17, 0.15, 0.15), (0.32, 0.35, 0.46), "prison"),
    "ossuaire": _theme((128, 116, 96), (150, 142, 120), (124, 112, 94), (90, 80, 66), (255, 170, 90),
                       (0.41, 0.37, 0.34), (0.19, 0.17, 0.14), (0.35, 0.34, 0.32), "bones"),
    "forges": _theme((70, 60, 56), (96, 50, 36), (84, 66, 60), (54, 44, 42), (255, 120, 50),
                     (0.37, 0.24, 0.20), (0.24, 0.10, 0.07), (0.41, 0.22, 0.16), "forge", lava=True),
    "sanctuaire": _theme((88, 78, 104), (110, 96, 130), (100, 88, 122), (66, 58, 82), (190, 120, 255),
                         (0.34, 0.29, 0.46), (0.17, 0.14, 0.20), (0.32, 0.27, 0.46), "temple"),
    "cryptes": _theme((124, 144, 164), (160, 184, 204), (150, 170, 192), (206, 222, 236), (140, 200, 255),
                      (0.44, 0.51, 0.61), (0.20, 0.24, 0.31), (0.41, 0.49, 0.62), "crypt"),
    "fosse": _theme((66, 92, 84), (80, 116, 88), (76, 100, 92), (50, 68, 62), (120, 255, 170),
                    (0.27, 0.41, 0.37), (0.12, 0.19, 0.17), (0.27, 0.41, 0.38), "cave"),
    "ecarlates": _theme((112, 64, 64), (134, 80, 76), (122, 72, 70), (80, 44, 44), (255, 90, 70),
                        (0.44, 0.24, 0.24), (0.20, 0.10, 0.10), (0.43, 0.24, 0.24), "hall"),
    "trone": _theme((54, 52, 60), (96, 84, 52), (72, 66, 64), (150, 124, 60), (255, 200, 90),
                    (0.31, 0.29, 0.34), (0.14, 0.14, 0.15), (0.32, 0.30, 0.35), "throne"),
    "mines": _theme((96, 78, 60), (118, 92, 66), (104, 86, 70), (70, 56, 44), (255, 170, 80),
                    (0.38, 0.32, 0.26), (0.18, 0.14, 0.10), (0.36, 0.30, 0.24), "mine", 0.09),
    "bibliotheque": _theme((104, 76, 60), (130, 96, 70), (96, 78, 96), (70, 54, 66), (255, 196, 120),
                           (0.40, 0.33, 0.36), (0.18, 0.14, 0.13), (0.38, 0.32, 0.34), "library", 0.1),
    "jardins": _theme((70, 96, 58), (92, 120, 64), (86, 104, 78), (58, 80, 50), (200, 255, 140),
                      (0.33, 0.43, 0.30), (0.13, 0.18, 0.11), (0.33, 0.44, 0.30), "garden", 0.08),
    "catacombes": _theme((140, 128, 108), (116, 104, 88), (132, 120, 100), (96, 86, 72), (255, 180, 110),
                         (0.42, 0.38, 0.33), (0.19, 0.17, 0.14), (0.36, 0.34, 0.30), "bones", 0.1),
    "engloutie": _theme((58, 96, 108), (70, 120, 128), (72, 108, 120), (44, 70, 80), (110, 220, 255),
                        (0.26, 0.40, 0.46), (0.10, 0.18, 0.21), (0.25, 0.40, 0.48), "cave"),
    "magma": _theme((50, 40, 40), (110, 44, 28), (64, 48, 46), (40, 30, 30), (255, 110, 40),
                    (0.40, 0.20, 0.14), (0.28, 0.08, 0.04), (0.46, 0.20, 0.12), "forge", lava=True),
    "reliquaire": _theme((196, 188, 168), (214, 196, 140), (206, 198, 180), (170, 150, 96), (255, 220, 140),
                         (0.52, 0.50, 0.46), (0.24, 0.22, 0.18), (0.50, 0.47, 0.40), "temple"),
    "neant": _theme((52, 44, 70), (72, 56, 104), (62, 52, 84), (36, 30, 52), (170, 110, 255),
                    (0.28, 0.24, 0.40), (0.11, 0.09, 0.16), (0.28, 0.22, 0.42), "necro"),
    "necropole": _theme((168, 146, 104), (190, 164, 110), (176, 156, 116), (130, 110, 76), (255, 190, 100),
                        (0.48, 0.42, 0.32), (0.22, 0.18, 0.12), (0.46, 0.40, 0.30), "necro"),
    "cristal": _theme((110, 150, 170), (140, 200, 220), (120, 166, 186), (180, 226, 240), (150, 240, 255),
                      (0.46, 0.58, 0.66), (0.20, 0.27, 0.32), (0.44, 0.58, 0.68), "cave"),
    "arene": _theme((150, 100, 70), (170, 116, 80), (140, 96, 76), (100, 64, 50), (255, 130, 60),
                    (0.46, 0.30, 0.24), (0.22, 0.12, 0.08), (0.46, 0.30, 0.22), "hall"),
    "sommet": _theme((70, 66, 70), (110, 60, 44), (86, 80, 84), (60, 56, 60), (255, 110, 60),
                     (0.36, 0.30, 0.32), (0.20, 0.10, 0.08), (0.40, 0.26, 0.24), "throne", lava=True),
})
# décor au sol remplacé par des modèles importés (famille de assets/models/models.json)
MODEL_DECOR = {"herbe": "grass", "fleur": "flower", "buisson": "bush", "champignon": "mushroom", "souche": "stump",
               "rocher": "rock"}
MAX_FLOOR = 20
FLOOR_THEMES = ["geoles", "ossuaire", "forges", "sanctuaire", "cryptes", "fosse", "ecarlates", "trone", "mines",
                "bibliotheque", "jardins", "catacombes", "engloutie", "magma", "reliquaire", "neant", "necropole",
                "cristal", "arene", "sommet"]

def dark_env(th):
    """Ambiance « dark fantasy » d'un étage : lumière ambiante basse, flaques de lumière chaude des torches,
    brouillard teinté, étalonnage froid dans les ombres et chaud dans les lumières."""
    from .renderer import Env

    def k(c, f):
        return tuple(ch * f for ch in c)
    sky = th["sky"]
    # les ambiances claires (givre, reliquaire, cristal...) sont exposées moins fort : même pénombre partout
    lum = (sum(th["floor"]) + sum(th["wall"])) / (6 * 255)
    expo = 1.3 * min(1.0, (0.36 / max(lum, 0.1)) ** 0.85)
    return Env(sun_col=k(th["sun"], 0.6), amb_sky=k(sky, 0.72), amb_ground=k(th["ground"], 0.6),
               fog=(14.0, 28.0), fog_col=k(sky, 0.05), clear=k(sky, 0.05),
               exposure=expo, bloom=0.5, bloom_threshold=0.85, sat=0.82, contrast=1.1,
               shadow_tint=(0.86, 0.94, 1.1), high_tint=(1.1, 1.0, 0.86), vignette=0.6, grain=0.03, aberr=0.5,
               glow=1.5)


def floor_theme(floor):
    return FLOOR_THEMES[(min(floor, MAX_FLOOR) - 1) % len(FLOOR_THEMES)]


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
        self.stains = []     # (x, y, rayon, opacité, graine) : crasse et taches sombres au sol
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

    house_cells = (getattr(d, "house_cells", set()) | getattr(d, "rampart", set())) if hub else set()

    # dessous sombre (visible dans les joints entre les dalles), percé au droit des gouffres, des marches et
    # des paliers inférieurs
    pits = {(x, y) for y in range(d.h) for x in range(d.w)
            if tiles[y][x] in (PIT, STAIRS) or zt(d, x, y) < 0}
    if pits:
        for x0, z0, x1, z1 in ((-2, -2, d.w + 2, 0), (-2, d.h, d.w + 2, d.h + 2), (-2, 0, 0, d.h), (d.w, 0, d.w + 2, d.h)):
            mb.box(x0, -0.3, z0, x1, -0.1, z1, (0.03, 0.03, 0.035))
        for y in range(d.h):
            x = 0
            while x < d.w:
                if (x, y) in pits:
                    x += 1
                    continue
                x0 = x
                while x < d.w and (x, y) not in pits:
                    x += 1
                mb.box(x0, -0.3, y, x, -0.1, y + 1, (0.03, 0.03, 0.035))
    else:
        mb.box(-2, -0.3, -2, d.w + 2, -0.1, d.h + 2, (0.03, 0.03, 0.035))
    use_kit = not hub and dungeon_kit.available()
    if use_kit:
        dungeon_kit.build(mb, geo, d, th, rng, is_floor)
        for y in range(d.h):
            for x in range(d.w):
                if _plain(d, x, y) and th.get("lava") and rng.random() < 0.05:
                    geo.lava.append(((x + 0.5) * TILE, (y + 0.5) * TILE))
    else:
        for y in range(d.h):
            for x in range(d.w):
                if not is_floor(x, y) or tiles[y][x] in (PIT, STAIRS):
                    continue
                alt = rng.random() < 0.14
                c = _jit(th["floor"], 9, rng)
                if alt:
                    c = tuple(a + (b / 255.0 - a) * 0.35 for a, b in zip(c, th["alt"]))
                near = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if not is_floor(x + dx, y + dy))
                c = tuple(ch * max(0.62, 1.0 - 0.075 * near) for ch in c)
                if hub:
                    _camp_floor(mb, d, x, y, rng)
                    mb.mat = 0
                else:
                    mb.mat = mb.STONE
                    g = 0.03
                    h = rng.uniform(-0.015, 0.0)
                    b = zt(d, x, y) + (PLAT_H / TILE if (x, y) in d.raised else 0.0)
                    mb.box(x + g, b - 0.12, y + g, x + 1 - g, b + h, y + 1 - g, c)
                if _plain(d, x, y) and th.get("lava") and rng.random() < 0.05:
                    geo.lava.append(((x + 0.5) * TILE, (y + 0.5) * TILE))
        mb.mat = 0
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
            mb.mat = mb.GRASS if hub else mb.BRICK
            four = sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if is_floor(x + dx, y + dy))
            if four == 4 and not hub:
                # pilier isolé : colonne ronde
                c = _jit(th["wall"], 6, rng)
                mb.add("cylinder", (x + 0.5, 1.0, y + 0.5), (0.36, 0, 0), (0, 1.0, 0), (0, 0, 0.36), c, 1.0)
                mb.box(x + 0.08, 0, y + 0.08, x + 0.92, 0.25, y + 0.92, _f(th["top"]), 1.0)
                mb.box(x + 0.08, 1.85, y + 0.08, x + 0.92, 2.1, y + 0.92, _f(th["top"]), 1.0)
                continue
            if hub and d.tiles[y][x] == WALL and getattr(d, "tower_tiles", None) and (x, y) in d.tower_tiles:
                mb.box(x, 0, y, x + 1, 0.1, y + 1, _jit((54, 62, 44), 6, rng))
                continue
            if hub and (x, y) in house_cells:
                mb.box(x, 0, y, x + 1, 0.1, y + 1, _jit((54, 62, 44), 6, rng))
                continue
            if hub:
                # clairière : talus herbeux bas couverts d'arbres
                H = rng.uniform(0.3, 0.55)
                mb.mat = mb.DIRT
                mb.box(x, 0, y, x + 1, H, y + 1, _jit((78, 70, 62), 10, rng), 1.0)
                mb.mat = mb.GRASS
                mb.box(x - 0.02, H, y - 0.02, x + 1.02, H + 0.08, y + 1.02, _jit((50, 62, 40), 8, rng), 1.0)
                mb.mat = 0
                if rng.random() < 0.8:
                    camp.tree(mb, x + rng.uniform(0.3, 0.7), H + 0.08, y + rng.uniform(0.3, 0.7), rng)
                continue
            H = rng.uniform(1.5, 1.9) if not hub else rng.uniform(1.0, 2.2)
            c = _jit(th["wall"], 8, rng)
            b0 = min([floor_low(d, x + dx, y + dy) for dx, dy in near] + [0.0])
            mb.box(x, b0, y, x + 1, H, y + 1, c, 1.0)
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
    mb.mat = 0
    if not hub:
        relief(mb, d, th, rng)
        dressing.build(mb, geo, d, th, rng, is_floor)
    # décor au sol
    for kind, x, y in d.decor:
        with lifted(mb, zt(d, x, y)):
            _decor(mb, geo, kind, x, y, rng)
    if hub:
        camp.forest(mb, d, rng, is_floor)
        city.build(mb, geo, d, rng, TILE)
    geo.mesh = mb.build()
    return geo


def _decor(mb, geo, kind, x, y, rng):
    """Un élément de décor posé au sol de la case (x, y), au niveau 0 (relevé ensuite au palier)."""
    if True:
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
        elif kind in MODEL_DECOR and objmodels.place(mb, MODEL_DECOR[kind], cx, 0.0, cz, rng):
            pass    # décor importé (assets/models/models.json) ; sinon repli procédural ci-dessous
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


def _plain(d, x, y):
    """Sol ordinaire, au niveau 0 (ni gouffre, ni estrade, ni marches)."""
    return d.tiles[y][x] in (FLOOR, BARRIER) and (x, y) not in getattr(d, "raised", ())


def zt(d, x, y):
    """Hauteur (en cases) du palier d'une case ; 0 hors de la carte."""
    zb = getattr(d, "zb", None)
    if zb is None or not (0 <= x < d.w and 0 <= y < d.h):
        return 0.0
    return zb[y][x] / TILE


def floor_low(d, x, y):
    """Point le plus bas du sol d'une case (bas des marches) : les murs voisins descendent jusque-là."""
    z = zt(d, x, y)
    st = getattr(d, "stairs", {}).get((x, y)) if 0 <= x < d.w and 0 <= y < d.h else None
    if st:
        z += min(0.0, st[2] / TILE)
    return z


@contextmanager
def lifted(mb, dz):
    """Tout ce qui est ajouté au maillage dans ce bloc est décalé en hauteur de dz (en cases)."""
    n = len(mb.parts)
    yield
    if dz:
        for arr in mb.parts[n:]:
            arr[:, 1] += dz


def relief(mb, d, th, rng):
    """Estrades (masse de pierre, garde-corps), escaliers (estrades et paliers) et gouffres."""
    tiles = d.tiles
    H = PLAT_H / TILE
    raised = getattr(d, "raised", set())
    wall, top = th["wall"], th["top"]

    def top_of(x, y):
        return zt(d, x, y) + (H if (x, y) in raised else 0.0)
    mb.mat = mb.BRICK
    for x, y in raised:
        z = zt(d, x, y)
        mb.box(x, z - 0.1, y, x + 1, z + H - 0.005, y + 1, _jit(wall, 6, rng))
    # garde-corps sur le rebord, du côté du vide
    mb.mat = mb.STONE
    for y in range(d.h):
        for x in range(d.w):
            if tiles[y][x] != LEDGE:
                continue
            B = top_of(x, y)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if (nx, ny) in raised or not (0 <= nx < d.w and 0 <= ny < d.h) or tiles[ny][nx] == WALL:
                    continue
                c = _jit(top, 8, rng)
                t, hh = 0.09, 0.34
                if dx:
                    ex = x + (1 if dx > 0 else 0)
                    mb.box(ex - t * (dx > 0) * 2, B, y, ex + t * (dx < 0) * 2, B + hh, y + 1, c)
                    for py in (y + 0.08, y + 0.92):
                        mb.box(ex - 0.12 if dx > 0 else ex, B, py - 0.07, ex if dx > 0 else ex + 0.12, B + hh + 0.1,
                               py + 0.07, _jit(wall, 5, rng))
                else:
                    ey = y + (1 if dy > 0 else 0)
                    mb.box(x, B, ey - t * (dy > 0) * 2, x + 1, B + hh, ey + t * (dy < 0) * 2, c)
                    for px in (x + 0.08, x + 0.92):
                        mb.box(px - 0.07, B, ey - 0.12 if dy > 0 else ey, px + 0.07, B + hh + 0.1,
                               ey if dy > 0 else ey + 0.12, _jit(wall, 5, rng))
    # marches : quatre degrés par case, du bas vers le haut de la rampe
    for (x, y), (ux, uy, z0, z1) in getattr(d, "stairs", {}).items():
        base = zt(d, x, y)
        lo, hi = base + z0 / TILE, base + z1 / TILE
        bottom = min(lo, base) - 0.15
        for i in range(4):
            a, b = i / 4, (i + 1) / 4
            h = lo + (hi - lo) * (i + 1) / 4
            c = _jit(th["floor"], 10, rng)
            if ux:
                x0, x1 = (x + a, x + b) if ux > 0 else (x + 1 - b, x + 1 - a)
                mb.box(x0, bottom, y, x1, h, y + 1, c)
            else:
                y0, y1 = (y + a, y + b) if uy > 0 else (y + 1 - b, y + 1 - a)
                mb.box(x, bottom, y0, x + 1, h, y1, c)
    # gouffres : parois qui plongent dans le noir (de plus en plus sombres), rebord de pierres, fond
    D = 3.0
    bottom_col = (0.55, 0.16, 0.04) if th.get("lava") else (0.012, 0.012, 0.016)
    bands = ((0.0, -0.8, 0.55), (-0.8, -1.7, 0.28), (-1.7, -D, 0.1))
    mb.mat = 0
    for y in range(d.h):
        for x in range(d.w):
            if tiles[y][x] != PIT:
                continue
            z = zt(d, x, y)
            mb.box(x, z - D - 0.1, y, x + 1, z - D, y + 1, bottom_col)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < d.w and 0 <= ny < d.h and tiles[ny][nx] == PIT:
                    continue
                lip = _jit(top, 10, rng)
                for za, zb_, k in bands:
                    rock = tuple(ch / 255.0 * k * rng.uniform(0.9, 1.1) for ch in wall)
                    if dx:
                        ex = x + (1 if dx > 0 else 0)
                        s = -1 if dx > 0 else 1
                        mb.box(min(ex, ex + s * 0.06), z + zb_, y, max(ex, ex + s * 0.06), z + za, y + 1, rock)
                    else:
                        ey = y + (1 if dy > 0 else 0)
                        s = -1 if dy > 0 else 1
                        mb.box(x, z + zb_, min(ey, ey + s * 0.06), x + 1, z + za, max(ey, ey + s * 0.06), rock)
                if dx:
                    ex = x + (1 if dx > 0 else 0)
                    s = -1 if dx > 0 else 1
                    mb.box(min(ex, ex + s * 0.14), z - 0.18, y - 0.02, max(ex, ex + s * 0.14), z + 0.02, y + 1.02, lip)
                else:
                    ey = y + (1 if dy > 0 else 0)
                    s = -1 if dy > 0 else 1
                    mb.box(x - 0.02, z - 0.18, min(ey, ey + s * 0.14), x + 1.02, z + 0.02, max(ey, ey + s * 0.14), lip)
    mb.mat = 0


def _camp_floor(mb, d, x, y, rng):
    """Sol du campement : herbe aux teintes douces, chemins de terre, place pavée autour du feu."""
    mb.mat = mb.STONE
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
        mb.mat = mb.GRASS
        mb.box(x, -0.12, y, x + 1, 0, y + 1, _jit((60, 74, 46), 4, rng))
        mb.mat = mb.DIRT
        r = rng.uniform(0.66, 0.78)
        mb.add("cylinder", (x + 0.5 + rng.uniform(-0.08, 0.08), 0.004, y + 0.5 + rng.uniform(-0.08, 0.08)), (r, 0, 0),
               (0, 0.004, 0), (0, 0, r), _f((92, 76, 58)))
        if rng.random() < 0.5:
            s = rng.uniform(0.05, 0.09)
            px, pz = x + rng.uniform(0.2, 0.8), y + rng.uniform(0.2, 0.8)
            mb.add("sphere", (px, 0.0, pz), (s, 0, 0), (0, s * 0.5, 0), (0, 0, s * 1.2), _jit((120, 114, 104), 12, rng))
        return
    mb.mat = mb.GRASS
    n = 0.5 + 0.5 * math.sin(x * 0.45 + y * 0.2) * math.cos(y * 0.37 - x * 0.13)
    # herbe fanée, presque grise sous la cendre, avec des plaques plus vertes
    base = tuple(a + (b - a) * n for a, b in zip((56, 66, 46), (80, 94, 56)))
    mb.box(x, -0.12, y, x + 1, 0, y + 1, _jit(base, 4, rng))
