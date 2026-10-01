"""Habillage « dark fantasy » des étages : éboulis au pied des murs, chaînes pendues, ossements épars, crasse au sol.

Tout est ajouté au maillage statique du niveau (aucun coût par image), sauf les taches de crasse (geo.stains),
dessinées comme décalques autour de la caméra.
"""
import math

from ..dungeon import FLOOR

SIDES = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _shade(c, k):
    return tuple(max(0.0, min(1.0, ch / 255.0 * k)) for ch in c)


def build(mb, geo, d, th, rng, is_floor):
    from .level import lifted
    tiles = d.tiles
    raised = getattr(d, "raised", set())
    wall = th["wall"]
    geo.stains = []

    def plain(x, y):
        return 0 <= x < d.w and 0 <= y < d.h and tiles[y][x] == FLOOR and (x, y) not in raised

    for y in range(1, d.h - 1):
        for x in range(1, d.w - 1):
            if not plain(x, y):
                continue
            walls = [(dx, dy) for dx, dy in SIDES if not is_floor(x + dx, y + dy)]
            r = rng.random()
            with lifted(mb, d.zb[y][x] / 40):
                if walls and r < 0.11:
                    _rubble(mb, x, y, rng.choice(walls), wall, rng)
                elif walls and r < 0.15:
                    _chain(mb, x, y, rng.choice(walls), rng)
                elif not walls and r < 0.012:
                    _bones(mb, x + 0.5, y + 0.5, rng)
            if rng.random() < 0.05:
                geo.stains.append(((x + rng.random()) * 40, (y + rng.random()) * 40, rng.uniform(26, 60),
                                   rng.uniform(0.35, 0.6), rng.random() * 9))
    mb.mat = 0


def _rubble(mb, x, y, side, wall, rng):
    """Blocs tombés du mur, entassés contre sa base."""
    dx, dy = side
    mb.mat = mb.STONE
    for _ in range(rng.randint(3, 6)):
        u = rng.uniform(0.1, 0.9)
        v = rng.uniform(0.05, 0.35)
        cx = x + (u if dx == 0 else (1 - v if dx > 0 else v))
        cz = y + (u if dy == 0 else (1 - v if dy > 0 else v))
        s = rng.uniform(0.05, 0.14)
        a = rng.random() * math.pi
        c, si = math.cos(a), math.sin(a)
        mb.add("cube", (cx, s * 0.6, cz), (c * s, 0, si * s), (0, s * 0.7, 0), (-si * s * 0.8, 0, c * s * 0.8),
               _shade(wall, rng.uniform(0.5, 0.8)))


def _chain(mb, x, y, side, rng):
    """Chaîne et anneau scellés au mur, parfois avec une menotte au bout."""
    dx, dy = side
    u = rng.uniform(0.25, 0.75)
    px = x + (u if dx == 0 else (1 - 0.04 if dx > 0 else 0.04))
    pz = y + (u if dy == 0 else (1 - 0.04 if dy > 0 else 0.04))
    top = rng.uniform(1.0, 1.35)
    n = rng.randint(5, 9)
    iron = (0.16, 0.15, 0.16)
    mb.mat = 0
    mb.add("cylinder", (px, top + 0.04, pz), (0.05, 0, 0), (0, 0.012, 0), (0, 0, 0.05), (0.2, 0.18, 0.17))
    for i in range(n):
        h = top - i * 0.075
        if i % 2:
            mb.box(px - 0.012, h - 0.04, pz - 0.028, px + 0.012, h + 0.04, pz + 0.028, iron)
        else:
            mb.box(px - 0.028, h - 0.04, pz - 0.012, px + 0.028, h + 0.04, pz + 0.012, iron)
    if rng.random() < 0.5:
        h = top - n * 0.075
        mb.add("cylinder", (px, h - 0.03, pz), (0.06, 0, 0), (0, 0.025, 0), (0, 0, 0.06), iron)


def _bones(mb, cx, cz, rng):
    """Restes d'un aventurier : crâne et os épars."""
    bone = (0.72, 0.68, 0.58)
    mb.mat = 0
    for _ in range(rng.randint(2, 4)):
        a = rng.random() * math.pi
        ox, oz = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
        L = rng.uniform(0.12, 0.2)
        mb.add("cylinder", (cx + ox, 0.03, cz + oz), (0, 0.03, 0), (math.cos(a) * L, 0, math.sin(a) * L),
               (-math.sin(a) * 0.03, 0, math.cos(a) * 0.03), bone)
    if rng.random() < 0.7:
        mb.add("sphere", (cx + rng.uniform(-0.2, 0.2), 0.09, cz + rng.uniform(-0.2, 0.2)), (0.1, 0, 0), (0, 0.09, 0),
               (0, 0, 0.11), bone)
