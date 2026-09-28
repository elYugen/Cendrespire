"""Décor 3D de Cendreval (plan : game/town.py) : remparts et tours, portes, maisons, place à la fontaine,
marché, forge, taverne, atelier de la couturière, jardins, lanternes et portail de la tour.

Coordonnées du maillage statique : (x, hauteur, z) en cases, z étant l'axe y du plan.
"""
import math

from .. import town as T
from . import camp, objmodels
from .camp import shade, STONE, DARK_WOOD

WALL_H = 1.75            # hauteur des remparts (cases)
WALL_STONE = (0.52, 0.49, 0.46)
SLATE_ROOF = (0.28, 0.30, 0.38)


def _runs(cells, axis_fixed, fixed):
    """Suites de cases consécutives d'une rangée (horizontale ou verticale) de remparts."""
    if axis_fixed == "y":
        xs = sorted(x for x, y in cells if y == fixed)
    else:
        xs = sorted(y for x, y in cells if x == fixed)
    runs, start, prev = [], None, None
    for v in xs:
        if start is None:
            start = prev = v
        elif v == prev + 1:
            prev = v
        else:
            runs.append((start, prev))
            start = prev = v
    if start is not None:
        runs.append((start, prev))
    return runs


def _wall_segment(mb, x0, z0, x1, z1, rng):
    """Mur crénelé plein, de la case (x0, z0) à la case (x1, z1) incluses."""
    mb.mat = mb.BRICK
    mb.box(x0 + 0.05, 0.0, z0 + 0.05, x1 + 0.95, WALL_H, z1 + 0.95, WALL_STONE, 1.0)
    mb.mat = mb.STONE
    mb.box(x0 - 0.02, WALL_H, z0 - 0.02, x1 + 1.02, WALL_H + 0.1, z1 + 1.02, shade(WALL_STONE, 0.8), 1.0)
    horizontal = z0 == z1
    n = (x1 - x0 + 1) if horizontal else (z1 - z0 + 1)
    for i in range(n * 2):
        if i % 2:
            continue
        a = i * 0.5 + 0.08
        if horizontal:
            for side in (0.08, 0.72):
                mb.box(x0 + a, WALL_H + 0.1, z0 + side, x0 + a + 0.34, WALL_H + 0.42, z0 + side + 0.2,
                       shade(WALL_STONE, 0.95), 1.0)
        else:
            for side in (0.08, 0.72):
                mb.box(x0 + side, WALL_H + 0.1, z0 + a, x0 + side + 0.2, WALL_H + 0.42, z0 + a + 0.34,
                       shade(WALL_STONE, 0.95), 1.0)
    mb.mat = 0


def _tower(mb, x, z, r=0.95, h=2.9, roof=SLATE_ROOF):
    """Tour ronde de rempart : fût en pierre, couronne, toit conique."""
    mb.mat = mb.BRICK
    mb.add("cylinder", (x, h / 2, z), (r, 0, 0), (0, h / 2, 0), (0, 0, r), WALL_STONE, 1.0)
    mb.mat = mb.STONE
    mb.add("cylinder", (x, h + 0.08, z), (r * 1.12, 0, 0), (0, 0.1, 0), (0, 0, r * 1.12), shade(WALL_STONE, 0.8), 1.0)
    mb.mat = 0
    mb.add("cone", (x, h + 0.8, z), (r * 1.25, 0, 0), (0, 0.7, 0), (0, 0, r * 1.25), roof, 1.0)
    for i in range(4):                                              # meurtrières
        a = i * math.pi / 2 + 0.4
        mb.box(x + math.cos(a) * r - 0.05, h * 0.55, z + math.sin(a) * r - 0.05,
               x + math.cos(a) * r + 0.05, h * 0.55 + 0.35, z + math.sin(a) * r + 0.05, (0.12, 0.11, 0.1), 1.0)
    camp.post(mb, x, z, 0.5, 0.025, DARK_WOOD, base=h + 1.45, flag=1.0)
    mb.box(x + 0.02, h + 1.62, z - 0.01, x + 0.34, h + 1.84, z + 0.01, (0.7, 0.16, 0.14), 1.0)


def _gate(mb, z):
    """Porte fortifiée : deux tours et un linteau crénelé au-dessus de l'avenue."""
    x0, x1 = T.GATE_X0, T.GATE_X1 + 1
    _tower(mb, x0 - 0.5, z + 0.5, 0.9, 3.1)
    _tower(mb, x1 + 0.5, z + 0.5, 0.9, 3.1)
    mb.mat = mb.BRICK
    mb.box(x0 - 0.2, 2.35, z + 0.15, x1 + 0.2, 3.1, z + 0.85, WALL_STONE, 1.0)
    mb.mat = 0
    mb.box(x0 - 0.25, 3.1, z + 0.1, x1 + 0.25, 3.2, z + 0.9, shade(WALL_STONE, 0.8), 1.0)
    for i in range(6):
        xx = x0 + 0.1 + i * (x1 - x0 - 0.2) / 5
        mb.box(xx - 0.15, 3.2, z + 0.15, xx + 0.15, 3.45, z + 0.35, shade(WALL_STONE, 0.95), 1.0)
    # herse relevée (barreaux de bois sous le linteau)
    for i in range(9):
        xx = x0 + 0.3 + i * (x1 - x0 - 0.6) / 8
        mb.box(xx - 0.04, 2.0, z + 0.45, xx + 0.04, 2.35, z + 0.55, DARK_WOOD, 1.0)


def ramparts(mb, rng):
    cells = T.rampart_cells()
    for fixed in (T.WALL_Y0, T.WALL_Y1):
        for a, b in _runs(cells, "y", fixed):
            _wall_segment(mb, a, fixed, b, fixed, rng)
    for fixed in (T.WALL_X0, T.WALL_X1):
        for a, b in _runs({c for c in cells if T.WALL_Y0 < c[1] < T.WALL_Y1}, "x", fixed):
            _wall_segment(mb, fixed, a, fixed, b, rng)
    for x, z in ((T.WALL_X0, T.WALL_Y0), (T.WALL_X1, T.WALL_Y0), (T.WALL_X0, T.WALL_Y1), (T.WALL_X1, T.WALL_Y1),
                 (T.WALL_X0, 26), (T.WALL_X0, 43), (T.WALL_X1, 43)):
        _tower(mb, x + 0.5, z + 0.5)
    _gate(mb, T.WALL_Y0)
    _gate(mb, T.WALL_Y1)
    _east_gate(mb)


def _east_gate(mb):
    """Porte est (vers la zone d'entraînement) : deux tours et un linteau au-dessus de la rue du marché."""
    x, z0, z1 = T.WALL_X1, T.EAST_GATE_Y0, T.EAST_GATE_Y1 + 1
    _tower(mb, x + 0.5, z0 - 0.5, 0.85, 3.0)
    _tower(mb, x + 0.5, z1 + 0.5, 0.85, 3.0)
    mb.mat = mb.BRICK
    mb.box(x + 0.15, 2.3, z0 - 0.2, x + 0.85, 3.0, z1 + 0.2, WALL_STONE, 1.0)
    mb.mat = 0
    mb.box(x + 0.1, 3.0, z0 - 0.25, x + 0.9, 3.1, z1 + 0.25, shade(WALL_STONE, 0.8), 1.0)
    for i in range(7):
        zz = z0 + 0.1 + i * (z1 - z0 - 0.2) / 6
        mb.box(x + 0.4, 1.95, zz - 0.04, x + 0.5, 2.3, zz + 0.04, DARK_WOOD, 1.0)


def training(mb, rng):
    """Cour d'entraînement : palissade, mannequin (dessiné à part : il réagit aux coups), cibles, râteliers."""
    x0, z0, x1, z1 = T.TRAINING
    x1, z1 = x1 + 1, z1 + 1
    gate = (T.EAST_GATE_Y0, T.EAST_GATE_Y1 + 1)

    def fence(ax, az, bx, bz):
        n = max(1, int(round(max(abs(bx - ax), abs(bz - az)))))
        for i in range(n + 1):
            k = i / n
            camp.post(mb, ax + (bx - ax) * k, az + (bz - az) * k, 0.75, 0.06)
        for h in (0.32, 0.62):
            if az == bz:
                mb.box(ax, h, az - 0.035, bx, h + 0.07, az + 0.035, shade(DARK_WOOD, 1.15))
            else:
                mb.box(ax - 0.035, h, az, ax + 0.035, h + 0.07, bz, shade(DARK_WOOD, 1.15))
    fence(x0, z0, x1, z0)
    fence(x0, z1, x1, z1)
    fence(x1, z0, x1, z1)
    fence(x0, z0, x0, gate[0])            # côté ouest : ouvert face à la porte est
    fence(x0, gate[1], x0, z1)
    for x, z in T.TARGETS:                # cibles de paille
        mb.add("cylinder", (x, 0.45, z), (0.5, 0, 0), (0, 0.45, 0), (0, 0, 0.5), (0.8, 0.68, 0.38), 1.0)
        for r, col in ((0.42, (0.92, 0.9, 0.84)), (0.28, (0.72, 0.2, 0.18)), (0.12, (0.92, 0.9, 0.84))):
            mb.add("cylinder", (x - 0.5, 0.5, z), (0.012, 0, 0), (0, r, 0), (0, 0, r), col, 1.0)
    for x, z in T.RACKS:
        camp.weapon_rack(mb, x, z)
    camp.signpost(mb, *T.TRAINING_SIGN)
    camp.banner(mb, x0 + 0.3, z0 + 0.3, (0.62, 0.12, 0.12))
    camp.banner(mb, x0 + 0.3, z1 - 0.3, (0.62, 0.12, 0.12))


def fountain(mb):
    fx, fz = T.FOUNTAIN
    if not objmodels.put(mb, "town", fx, 0.0, fz, 0.0, 2.3, 1.0, "fountain-round-detail"):
        mb.add("cylinder", (fx, 0.2, fz), (1.9, 0, 0), (0, 0.2, 0), (0, 0, 1.9), STONE, 1.0)
    mb.add("cylinder", (fx, 0.29, fz), (0.9, 0, 0), (0, 0.02, 0), (0, 0, 0.9), (0.28, 0.52, 0.66))
    # statue : socle, flamme de pierre (emblème de Cendreval)
    mb.add("cylinder", (fx, 0.75, fz), (0.3, 0, 0), (0, 0.45, 0), (0, 0, 0.3), shade(STONE, 1.1), 1.0)
    mb.add("cone", (fx, 1.55, fz), (0.26, 0, 0), (0, 0.4, 0), (0, 0, 0.26), (0.72, 0.62, 0.44), 1.0)


def market(mb, rng):
    put = objmodels.put
    camp.stall(mb, *T.MERCHANT_STALL)
    for x, z, rot in T.MARKET_STALLS:
        put(mb, "town", x, 0.0, z, rot, 1.6, 0.0, rng.choice(["stall-red", "stall-green"]))
        put(mb, "camp", x + 0.7, 0.0, z + 0.2, rng.random() * 6.28, 2.3, 0.0, rng.choice(["box", "barrel", "box-large"]))
    camp.well(mb, *T.WELL)
    for x, z in ((7.6, 18.6), (16.6, 24.2), (7.5, 24.0)):
        put(mb, "camp", x, 0.0, z, rng.random() * 6.28, 2.5, 0.0, rng.choice(["barrel", "box-large"]))


def forge(mb, rng):
    put = objmodels.put
    camp.furnace(mb, *T.FURNACE)
    put(mb, "camp", T.ANVIL[0], 0.0, T.ANVIL[1], 1.6, 2.3, 0.0, "workbench-anvil")
    put(mb, "camp", T.GRIND[0], 0.0, T.GRIND[1], 2.0, 2.2, 0.0, "workbench-grind")
    camp.weapon_rack(mb, *T.RACK)
    camp.woodpile(mb, 39.6, 17.6, rng)
    for x, z in ((36.3, 18.3), (31.0, 23.8), (38.8, 24.0)):
        put(mb, "camp", x, 0.0, z, rng.random() * 6.28, 2.4, 0.0, "barrel")
    put(mb, "camp", 30.2, 0.0, 19.0, 0.4, 2.2, 0.0, "workbench")


def tailor(mb):
    camp.wardrobe(mb, *T.WARDROBE)
    camp.mirror(mb, *T.MIRROR)


def tavern(mb, rng):
    put = objmodels.put
    for x, z in T.TAVERN_TABLES:
        if objmodels.family("town"):
            put(mb, "town", x, 0.0, z, 0.0, 1.2, 0.0, "stall-bench")
            put(mb, "town", x, 0.0, z + 0.55, math.pi, 1.2, 0.0, "stall-stool")
            put(mb, "town", x, 0.0, z - 0.55, 0.0, 1.2, 0.0, "stall-stool")
    # enseigne du Tison : poteau et panneau suspendu
    sx, sz = T.TAVERN[0] + 2.6, T.TAVERN[1] - 1.7
    camp.post(mb, sx, sz, 1.6, 0.05, DARK_WOOD, flag=1.0)
    mb.box(sx - 0.02, 1.5, sz - 0.02, sx + 0.5, 1.55, sz + 0.02, DARK_WOOD, 1.0)
    mb.box(sx + 0.12, 1.08, sz - 0.03, sx + 0.48, 1.46, sz + 0.03, (0.52, 0.34, 0.2), 1.0)
    mb.add("cone", (sx + 0.3, 1.27, sz - 0.04), (0.08, 0, 0), (0, 0.12, 0), (0, 0, 0.01), (0.95, 0.5, 0.15))


def streets(mb, geo, tile, rng):
    put = objmodels.put
    for x, z in T.LAMPS:
        camp.lantern(mb, geo, x, z, tile)
    for x, z in T.GARDEN_TREES:
        camp.tree(mb, x, 0.0, z, rng, rng.uniform(0.75, 0.95))
    for x, z, rot in T.CARTS:
        put(mb, "town", x, 0.0, z, rot, 1.4, 0.0, "cart-high")
    for x, z, rot in T.BENCHES:
        put(mb, "town", x, 0.0, z, rot, 1.4, 0.0, "stall-bench")
    for x, z in T.BANNERS:
        camp.banner(mb, x, z, (0.62, 0.12, 0.12))
    # haies basses devant les jardins des quartiers nord et sud
    for x0, x1, z in ((3.2, 20.2, 15.6), (26.2, 43.2, 15.6), (3.2, 20.2, 37.1), (26.2, 43.2, 37.1)):
        mb.mat = mb.GRASS
        x = x0
        while x < x1:
            if not any(abs(x - hx) < n + 0.2 for hx, hz, n, _f, _r, _c in T.HOUSES if abs(hz - z) < 2.5):
                mb.box(x, 0.0, z - 0.1, min(x1, x + 1.0), 0.32, z + 0.1, (0.25, 0.42, 0.2))
            x += 1.0
        mb.mat = 0
    # tonneaux et bottes de foin près des maisons
    for x, z in ((9.4, 12.2), (22.0 - 1.6, 14.0), (36.4, 12.4), (10.0, 40.4), (35.2, 40.2)):
        put(mb, "camp", x, 0.0, z, rng.random() * 6.28, 2.4, 0.0, "barrel")


def temple_quarter(mb, geo, rng, tile):
    """Quartier du Temple : statue de la place des Oracles, sanctuaire de l'Oubli, bibliothèque."""
    put = objmodels.put
    ox, oz = T.ORACLES
    # socle à degrés et statue (obélisque ou colonne procédurale)
    for i, (r, h) in enumerate(((1.25, 0.18), (0.95, 0.36), (0.6, 0.55))):
        mb.add("cylinder", (ox, h / 2, oz), (r, 0, 0), (0, h / 2, 0), (0, 0, r), shade(STONE, 1.0 - i * 0.07), 1.0)
    mb.mat = mb.STONE
    mb.box(ox - 0.32, 0.55, oz - 0.32, ox + 0.32, 0.75, oz + 0.32, shade(STONE, 0.9), 1.0)
    mb.box(ox - 0.24, 0.75, oz - 0.24, ox + 0.24, 2.55, oz + 0.24, shade(STONE, 1.08), 1.0)
    mb.box(ox - 0.34, 2.55, oz - 0.34, ox + 0.34, 2.72, oz + 0.34, shade(STONE, 0.9), 1.0)
    mb.mat = 0
    for a in (0.0, math.pi / 2, math.pi, 1.5 * math.pi):      # griffes qui tiennent l'orbe
        c, s = math.cos(a), math.sin(a)
        mb.add("cone", (ox + c * 0.2, 2.9, oz + s * 0.2), (0.05, 0, 0), (0, 0.2, 0), (0, 0, 0.05), (0.7, 0.6, 0.4), 1.0)
    mb.add("sphere", (ox, 3.1, oz), (0.22, 0, 0), (0, 0.22, 0), (0, 0, 0.22), (0.62, 0.52, 0.95), 1.0)
    geo.torches.append((ox * tile, oz * tile, 3.1 * tile))
    for a in (0.8, 2.35, 3.9, 5.45):             # urnes autour du socle
        put(mb, "grave", ox + math.cos(a) * 1.7, 0.0, oz + math.sin(a) * 1.7, a, 1.6, 0.0, "urn-round")
    # sanctuaire de l'Oubli : chandeliers devant la porte, lueur violette
    for x, z in T.CANDLES:
        if not put(mb, "grave", x, 0.0, z, 0.0, 1.8, 0.0, "candle-multiple"):
            camp.post(mb, x, z, 0.9, 0.04, DARK_WOOD, flag=1.0)
        geo.torches.append((x * tile, z * tile, 0.8 * tile))
    sx, sz = T.SANCTUARY
    mb.add("sphere", (sx + 1.25, 2.3, sz), (0.16, 0, 0), (0, 0.16, 0), (0, 0, 0.16), (0.7, 0.5, 1.0), 1.0)
    # bibliothèque : pupitres, caisses de livres
    for x, z in T.LECTERNS:
        camp.post(mb, x, z, 0.75, 0.05, DARK_WOOD)
        mb.box(x - 0.28, 0.72, z - 0.2, x + 0.28, 0.8, z + 0.2, (0.42, 0.28, 0.16), 1.0)
        mb.box(x - 0.2, 0.8, z - 0.14, x + 0.2, 0.86, z + 0.14, (0.86, 0.82, 0.7), 1.0)
    lx, lz = T.LIBRARY
    for dz in (-2.6, 2.6):
        put(mb, "camp", lx - 2.2, 0.0, lz + dz, rng.random() * 6.28, 2.3, 0.0, rng.choice(["box", "box-large"]))
    for x, z in ((4.6, 44.9), (41.6, 54.8), (16.4, 54.9)):
        put(mb, "camp", x, 0.0, z, rng.random() * 6.28, 2.4, 0.0, "barrel")


def esplanade(mb, geo, tile):
    """Esplanade de la tour : grand portail, obélisques, braseros."""
    x, z = T.PORTAL
    if objmodels.put(mb, "dungeon", x, 0.12, z, 0.0, 0.8, 1.0, "gate"):
        for i, (w, h) in enumerate(((2.4, 0.06), (2.1, 0.12))):
            mb.box(x - w, 0.0, z - 0.8 + i * 0.12, x + w, h, z + 0.8 - i * 0.12, shade(STONE, 0.95 - i * 0.08), 1.0)
        for side in (-1, 1):
            bx = x + side * 1.45
            objmodels.put(mb, "dungeon", bx, 0.12, z, 0.0, 0.22, 1.0, "template-detail")
            objmodels.put(mb, "grave", bx, 1.1, z, 0.0, 1.6, 0.0, "fire-basket")
            geo.torches.append((bx * tile, z * tile, 1.3 * tile))
    for ox in (-4.5, 4.5):
        objmodels.put(mb, "grave", x + ox, 0.0, z + 1.2, 0.0, 1.6, 1.0, "pillar-obelisk")


def arena(mb, geo, rng, tile):
    """Arène au sud de la ville : gradins de pierre en couronne, ouverts au nord sur l'avenue, braseros, bannières."""
    cx, cz = T.ARENA
    r0 = T.ARENA_R
    n = 72
    for i in range(n):
        a = (i + 0.5) / n * math.tau
        # entrée nord (vers la ville) : direction -z
        if abs((a + math.pi / 2 + math.pi) % math.tau - math.pi) < T.ARENA_GATE:
            continue
        c, s = math.cos(a), math.sin(a)
        half = math.pi * (r0 + 1.5) / n + 0.06
        for step in range(3):
            r = r0 + 0.2 + step * 0.9
            h = 0.35 + step * 0.4
            px, pz = cx + c * (r + 0.45), cz + s * (r + 0.45)
            mb.mat = mb.STONE
            mb.add("cube", (px, h / 2, pz), (c * 0.46, 0, s * 0.46),
                   (0, h / 2, 0), (-s * half, 0, c * half), shade(WALL_STONE, 0.92 - step * 0.06), 1.0)
        mb.mat = 0
    # mur d'enceinte extérieur
    for i in range(n):
        a = (i + 0.5) / n * math.tau
        if abs((a + math.pi / 2 + math.pi) % math.tau - math.pi) < T.ARENA_GATE:
            continue
        c, s = math.cos(a), math.sin(a)
        r = r0 + 3.0
        half = math.pi * r / n + 0.05
        mb.mat = mb.BRICK
        mb.add("cube", (cx + c * r, 0.9, cz + s * r), (c * 0.3, 0, s * 0.3), (0, 0.9, 0), (-s * half, 0, c * half),
               WALL_STONE, 1.0)
        mb.mat = 0
    # piliers de l'entrée, bannières, braseros
    for side in (-1, 1):
        a = -math.pi / 2 + side * (T.ARENA_GATE + 0.05)
        x, z = cx + math.cos(a) * (r0 + 1.6), cz + math.sin(a) * (r0 + 1.6)
        _tower(mb, x, z, 0.55, 2.4, (0.5, 0.14, 0.12))
    for x, z in T.ARENA_BRAZIERS:
        objmodels.put(mb, "grave", x, 0.0, z, 0.0, 1.6, 0.0, "fire-basket")
        geo.torches.append((x * tile, z * tile, 0.9 * tile))
    for i in range(6):
        a = math.pi / 2 + (i - 2.5) * 0.42
        camp.banner(mb, cx + math.cos(a) * (r0 + 2.9), cz + math.sin(a) * (r0 + 2.9), (0.55, 0.12, 0.12))
    # emblème au centre de la piste
    mb.add("cylinder", (cx, 0.01, cz), (1.6, 0, 0), (0, 0.01, 0), (0, 0, 1.6), (0.46, 0.34, 0.24))
    mb.add("cylinder", (cx, 0.02, cz), (1.2, 0, 0), (0, 0.01, 0), (0, 0, 1.2), (0.62, 0.48, 0.32))


def build(mb, geo, d, rng, tile):
    ramparts(mb, rng)
    for hx, hz, n, fl, rot, roof in T.HOUSES:
        camp.house(mb, hx, hz, n, fl, rot, 2.0, door=0, roof=roof)
    fountain(mb)
    market(mb, rng)
    forge(mb, rng)
    tailor(mb)
    tavern(mb, rng)
    streets(mb, geo, tile, rng)
    esplanade(mb, geo, tile)
    temple_quarter(mb, geo, rng, tile)
    training(mb, rng)
    arena(mb, geo, rng, tile)
