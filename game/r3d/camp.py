"""Décor statique du campement : forêt de pins, bancs, étal, forge, puits, lanternes, coin de la couturière.

Coordonnées du maillage statique : (x, hauteur, z) en tuiles, z étant l'axe y logique de la carte.
Le drapeau 1.0 rend la pièce « effaçable » quand elle masque le héros (comme les murs).
"""
import math

LANTERNS = [(15.1, 7.9), (19.9, 7.9), (11.0, 9.3), (24.0, 9.3), (13.6, 13.6), (19.9, 13.9)]
FURNACE = (32.0, 10.6)
WELL = (23.6, 13.7)
WARDROBE = (10.0, 15.95)
MIRROR = (12.9, 15.85)

WOOD = (0.45, 0.31, 0.19)
DARK_WOOD = (0.30, 0.21, 0.13)
STONE = (0.50, 0.48, 0.45)
IRON = (0.22, 0.22, 0.25)


def _jit(c, v, rng):
    d = rng.uniform(-v, v) / 255.0
    return tuple(max(0.0, min(1.0, ch + d)) for ch in c)


def shade(c, k):
    return tuple(max(0.0, min(1.0, ch * k)) for ch in c)


def post(mb, x, z, h, r=0.05, color=DARK_WOOD, base=0.0, flag=0.0):
    mb.add("cylinder", (x, base + h / 2, z), (r, 0, 0), (0, h / 2, 0), (0, 0, r), color, flag)


def log(mb, x, y, z, a, length, r, color=WOOD, flag=0.0):
    """Rondin couché, orienté selon l'angle a dans le plan du sol."""
    ca, sa = math.cos(a), math.sin(a)
    mb.add("cylinder", (x, y, z), (0, r, 0), (ca * length / 2, 0, sa * length / 2), (-sa * r, 0, ca * r), color, flag)


def pine(mb, x, base, z, rng, scale=1.0):
    h = rng.uniform(1.7, 2.8) * scale
    r = rng.uniform(0.42, 0.6) * scale
    mb.add("cylinder", (x, base + 0.3, z), (0.09, 0, 0), (0, 0.3, 0), (0, 0, 0.09), (0.34, 0.24, 0.15), 1.0)
    g = _jit((0.20, 0.38, 0.23), 16, rng)
    for i in range(3):
        k = 1 - i * 0.27
        mb.add("cone", (x, base + 0.45 + i * h * 0.23 + h * 0.17, z), (r * k, 0, 0), (0, h * 0.22, 0), (0, 0, r * k),
               shade(g, 0.85 + i * 0.12), 1.0)


def leafy(mb, x, base, z, rng, scale=1.0):
    h = rng.uniform(0.8, 1.2) * scale
    mb.add("cylinder", (x, base + h / 2, z), (0.1, 0, 0), (0, h / 2, 0), (0, 0, 0.1), (0.36, 0.26, 0.17), 1.0)
    g = _jit((0.30, 0.46, 0.22), 18, rng)
    for i in range(3):
        a = rng.random() * math.tau
        r = rng.uniform(0.35, 0.5) * scale
        mb.add("sphere", (x + math.cos(a) * 0.22, base + h + rng.uniform(0.05, 0.4), z + math.sin(a) * 0.22),
               (r, 0, 0), (0, r * 0.85, 0), (0, 0, r), shade(g, rng.uniform(0.85, 1.1)), 1.0)


def tree(mb, x, base, z, rng, scale=1.0):
    (pine if rng.random() < 0.72 else leafy)(mb, x, base, z, rng, scale)


def forest(mb, d, rng, is_floor):
    """Falaises basses couvertes de pins autour de la clairière, et forêt au-delà des bords de la carte."""
    W, H = d.w, d.h
    ground = (0.20, 0.30, 0.16)
    # sol de forêt tout autour de la carte (cache le vide)
    for x0, z0, x1, z1 in ((-14, -12, W + 14, 0), (-14, H, W + 14, H + 12), (-14, 0, 0, H), (W, 0, W + 14, H)):
        mb.box(x0, -0.1, z0, x1, 0.32, z1, ground)
    for z in range(-10, H + 10):
        for x in range(-12, W + 12):
            if 0 <= x < W and 0 <= z < H:
                continue
            if rng.random() < 0.45:
                tree(mb, x + rng.uniform(0.2, 0.8), 0.32, z + rng.uniform(0.2, 0.8), rng, rng.uniform(0.9, 1.3))


def benches(mb, fx, fz):
    for a in (0.785, 2.356, 3.927, 5.498):
        cx, cz = fx + math.cos(a) * 2.0, fz + math.sin(a) * 2.0
        log(mb, cx, 0.14, cz, a + math.pi / 2, 1.1, 0.14)


def lantern(mb, geo, x, z, tile):
    post(mb, x, z, 1.25, 0.05)
    mb.box(x - 0.02, 1.2, z - 0.02, x + 0.3, 1.25, z + 0.02, DARK_WOOD)
    lx = x + 0.26
    mb.box(lx - 0.09, 0.9, z - 0.09, lx + 0.09, 0.92, z + 0.09, IRON)
    mb.box(lx - 0.09, 1.1, z - 0.09, lx + 0.09, 1.13, z + 0.09, IRON)
    for ox, oz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        mb.box(lx + ox * 0.08 - 0.012, 0.92, z + oz * 0.08 - 0.012, lx + ox * 0.08 + 0.012, 1.1,
               z + oz * 0.08 + 0.012, IRON)
    geo.torches.append((lx * tile, z * tile, 0.86 * tile))


def stall(mb, x, z):
    """Étal du marchand : table chargée et auvent rayé."""
    mb.box(x - 0.35, 0.42, z - 0.9, x + 0.35, 0.48, z + 0.9, WOOD)
    for ox in (-0.3, 0.3):
        for oz in (-0.85, 0.85):
            post(mb, x + ox, z + oz, 0.42, 0.04)
    for ox, oz in ((-0.42, -1.0), (-0.42, 1.0), (0.42, -1.0), (0.42, 1.0)):
        post(mb, x + ox, z + oz, 1.35 if ox < 0 else 1.15, 0.035)
    for i in range(6):
        c = (0.72, 0.22, 0.2) if i % 2 == 0 else (0.9, 0.84, 0.7)
        zz = z - 1.05 + (i + 0.5) * 0.35
        mb.add("cube", (x, 1.25, zz), (0.5, -0.12, 0), (0, 0.025, 0), (0, 0, 0.175), c)
    goods = [(0.8, 0.2, 0.2), (0.25, 0.45, 0.85), (0.85, 0.7, 0.25), (0.35, 0.65, 0.3), (0.6, 0.35, 0.7)]
    for i, c in enumerate(goods):
        zz = z - 0.7 + i * 0.35
        if i % 2:
            mb.add("sphere", (x, 0.55, zz), (0.07, 0, 0), (0, 0.07, 0), (0, 0, 0.07), c)
        else:
            mb.box(x - 0.08, 0.48, zz - 0.08, x + 0.08, 0.6, zz + 0.08, c)


def furnace(mb, x, z):
    mb.box(x - 0.45, 0, z - 0.45, x + 0.45, 0.8, z + 0.45, STONE, 1.0)
    mb.box(x - 0.5, 0.8, z - 0.5, x + 0.5, 0.88, z + 0.5, shade(STONE, 0.8), 1.0)
    mb.add("cylinder", (x + 0.15, 1.5, z + 0.1), (0.16, 0, 0), (0, 0.65, 0), (0, 0, 0.16), shade(STONE, 0.9), 1.0)
    mb.box(x - 0.47, 0.15, z - 0.22, x - 0.4, 0.5, z + 0.22, (0.08, 0.05, 0.04))


def weapon_rack(mb, x, z):
    for oz in (-0.45, 0.45):
        post(mb, x, z + oz, 0.9, 0.04)
    mb.box(x - 0.03, 0.75, z - 0.5, x + 0.03, 0.8, z + 0.5, WOOD)
    for i, oz in enumerate((-0.25, 0.0, 0.25)):
        mb.add("cylinder", (x + 0.06, 0.45, z + oz), (0.02, 0, 0), (0.05, 0.42, 0), (0, 0, 0.02), WOOD)
        if i == 1:
            mb.box(x + 0.02, 0.78, z + oz - 0.02, x + 0.12, 0.98, z + oz + 0.12, (0.7, 0.72, 0.76))
        else:
            mb.add("cone", (x + 0.1, 0.95, z + oz), (0.03, 0, 0), (0, 0.12, 0), (0, 0, 0.03), (0.75, 0.77, 0.8))


def woodpile(mb, x, z, rng):
    for row in range(3):
        for i in range(4 - row):
            log(mb, x + (i - (3 - row) / 2) * 0.17, 0.08 + row * 0.14, z, math.pi / 2, 0.7, 0.08,
                _jit(WOOD, 12, rng))


def well(mb, x, z):
    for i in range(10):
        a = i / 10 * math.tau
        mb.box(x + math.cos(a) * 0.42 - 0.1, 0, z + math.sin(a) * 0.42 - 0.1, x + math.cos(a) * 0.42 + 0.1, 0.45,
               z + math.sin(a) * 0.42 + 0.1, shade(STONE, 0.9 + 0.1 * (i % 2)), 1.0)
    mb.add("cylinder", (x, 0.3, z), (0.33, 0, 0), (0, 0.01, 0), (0, 0, 0.33), (0.1, 0.22, 0.3))
    for ox in (-0.45, 0.45):
        post(mb, x + ox, z, 1.3, 0.05, flag=1.0)
    log(mb, x, 1.05, z, 0.0, 1.0, 0.05, DARK_WOOD)
    mb.add("cone", (x, 1.45, z), (0.62, 0, 0), (0, 0.22, 0), (0, 0, 0.62), (0.45, 0.22, 0.16), 1.0)


def banner(mb, x, z, color):
    post(mb, x, z, 2.5, 0.05, flag=1.0)
    mb.add("cone", (x, 2.56, z), (0.07, 0, 0), (0, 0.08, 0), (0, 0, 0.07), (0.85, 0.72, 0.4))
    mb.box(x - 0.02, 1.35, z - 0.32, x + 0.02, 2.35, z + 0.32, color, 1.0)
    mb.box(x - 0.025, 1.6, z - 0.1, x + 0.025, 2.0, z + 0.1, (0.9, 0.78, 0.45), 1.0)


def signpost(mb, x, z):
    post(mb, x, z, 1.1, 0.05)
    mb.box(x - 0.35, 0.82, z - 0.03, x + 0.3, 0.95, z + 0.03, WOOD)
    mb.box(x - 0.28, 0.62, z - 0.03, x + 0.37, 0.75, z + 0.03, shade(WOOD, 0.85))


def wardrobe(mb, x, z):
    mb.box(x - 0.35, 0, z - 0.18, x + 0.35, 1.3, z + 0.18, (0.42, 0.24, 0.3), 1.0)
    mb.box(x - 0.39, 1.3, z - 0.21, x + 0.39, 1.38, z + 0.21, (0.3, 0.16, 0.22), 1.0)
    mb.box(x - 0.01, 0.1, z - 0.2, x + 0.01, 1.25, z - 0.18, (0.2, 0.1, 0.14))
    for ox in (-0.06, 0.06):
        mb.add("sphere", (x + ox, 0.7, z - 0.2), (0.025, 0, 0), (0, 0.025, 0), (0, 0, 0.025), (0.9, 0.76, 0.4))
    for i, c in enumerate(((0.8, 0.3, 0.35), (0.3, 0.5, 0.8), (0.9, 0.8, 0.5))):   # rouleaux de tissu
        log(mb, x + 0.6 + i * 0.05, 0.1 + i * 0.18, z + 0.1, 0.3, 0.55, 0.09, c)


def mirror(mb, x, z):
    for ox in (-0.25, 0.25):
        post(mb, x + ox, z, 1.2, 0.035, (0.6, 0.48, 0.25))
    mb.box(x - 0.26, 0.35, z - 0.02, x + 0.26, 1.25, z + 0.02, (0.6, 0.48, 0.25))
    mb.box(x - 0.21, 0.4, z - 0.04, x + 0.21, 1.2, z - 0.02, (0.62, 0.8, 0.88))


def build(mb, geo, d, rng, tile):
    fx, fz = 17.5, 10.5
    benches(mb, fx, fz)
    for x, z in LANTERNS:
        lantern(mb, geo, x, z, tile)
    stall(mb, 7.9, 10.5)
    furnace(mb, *FURNACE)
    weapon_rack(mb, 26.2, 8.9)
    woodpile(mb, 33.0, 12.8, rng)
    well(mb, *WELL)
    banner(mb, 14.8, 5.6, (0.62, 0.12, 0.12))
    banner(mb, 19.2, 5.6, (0.62, 0.12, 0.12))
    signpost(mb, 16.1, 15.6)
    wardrobe(mb, *WARDROBE)
    mirror(mb, *MIRROR)
    for x, z in ((4.4, 12.3), (5.1, 12.8)):     # bottes de foin
        log(mb, x, 0.2, z, 0.4, 0.55, 0.2, (0.78, 0.66, 0.34))
