"""Décor statique du campement : forêt de pins, bancs, étal, forge, puits, lanternes, coin de la couturière.

Coordonnées du maillage statique : (x, hauteur, z) en tuiles, z étant l'axe y logique de la carte.
Le drapeau 1.0 rend la pièce « effaçable » quand elle masque le héros (comme les murs).
"""
import math

from . import objmodels

# maisons du hameau, sur les cases de lisière (non praticables) : (x, z, modules, étages, rotation, toit)
HOUSES = [(3.4, 2.5, 2, 2, 0.0, (0.62, 0.24, 0.2)), (10.6, 1.4, 1, 1, 0.0, (0.30, 0.50, 0.46)),
          (30.9, 2.3, 2, 1, 0.0, (0.30, 0.50, 0.46)), (1.2, 10.5, 2, 1, -math.pi / 2, (0.62, 0.24, 0.2))]
# obstacles ronds du décor (x, z, rayon) en tuiles : le héros et les monstres les contournent
OBSTACLES = [(8.2, 10.5, 0.7), (4.7, 13.2, 0.6), (27.6, 11.6, 0.35), (23.6, 13.7, 0.55), (5.0, 8.2, 0.8),
             (32.6, 7.9, 0.8), (7.6, 12.85, 0.45), (26.4, 12.9, 0.3)]


def house_tiles():
    """Cases occupées par les maisons (le talus et les arbres n'y sont pas dessinés)."""
    tiles = set()
    for x, z, n, _fl, rot, _roof in HOUSES:
        hl, hw = n * 1.0 + 0.2, 1.2          # demi-longueur et demi-largeur (modules de 2 tuiles)
        if abs(math.sin(rot)) > 0.5:
            hl, hw = hw, hl
        for tx in range(int(x - hl), int(x + hl) + 1):
            for tz in range(int(z - hw), int(z + hw) + 1):
                tiles.add((tx, tz))
    return tiles


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
    """Arbre du décor : modèle importé (assets/models, familles pine / leafy) ou, à défaut, arbre procédural."""
    is_pine = rng.random() < 0.72
    if objmodels.place(mb, "pine" if is_pine else "leafy", x, base, z, rng, scale, 1.0):
        return
    (pine if is_pine else leafy)(mb, x, base, z, rng, scale)


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
    if objmodels.put(mb, "town", x, 0.0, z, 0.0, 1.0, 0.0, "lantern"):
        geo.torches.append((x * tile, z * tile, 1.38 * tile))
        return
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
    """Étal du marchand : étal à auvent du Fantasy Town Kit, ou table et auvent rayé procéduraux."""
    if objmodels.put(mb, "town", x, 0.0, z, -math.pi / 2, 1.8, 0.0, "stall-red"):
        objmodels.put(mb, "town", x - 1.25, 0.0, z + 0.4, 0.0, 1.8, 0.0, "stall-stool")
        return
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
    if objmodels.put(mb, "camp", x, 0.0, z, 0.3, 3.0, 0.0, "signpost"):
        return
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
    stall(mb, 8.2, 10.5)
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
    village(mb, rng)


def village(mb, rng):
    """Hameau et mobilier de camp importés (Fantasy Town Kit, Survival Kit) ; rien si les modèles manquent."""
    if not objmodels.family("town"):
        return
    for x, z, n, fl, rot, roof in HOUSES:
        house(mb, x, z, n, fl, rot, 2.0, door=0, roof=roof)
    put = objmodels.put
    put(mb, "town", 4.7, 0.0, 13.2, 0.5, 1.4, 0.0, "cart")                 # charrette du marchand
    put(mb, "camp", 7.6, 0.0, 12.85, 0.2, 2.6, 0.0, "barrel")
    put(mb, "camp", 8.3, 0.0, 12.7, 0.6, 2.4, 0.0, "box-large")
    put(mb, "camp", 5.6, 0.0, 9.0, 1.1, 2.4, 0.0, "box")
    put(mb, "camp", 5.4, 0.0, 12.0, 0.0, 2.6, 0.0, "barrel-open")
    put(mb, "camp", 27.6, 0.0, 11.6, 2.3, 2.3, 0.0, "workbench-anvil")     # forge
    put(mb, "camp", 26.4, 0.0, 12.9, 0.9, 2.4, 0.0, "barrel")
    put(mb, "camp", 30.3, 0.0, 12.5, 2.0, 2.2, 0.0, "workbench-grind")
    put(mb, "camp", 29.8, 0.0, 8.6, 0.4, 2.4, 0.0, "workbench")
    put(mb, "camp", 29.9, 0.62, 8.6, 1.2, 2.0, 0.0, "tool-hammer")
    put(mb, "camp", 21.2, 0.0, 12.9, 2.2, 1.8, 0.0, "bedroll")             # couchage près du feu
    put(mb, "camp", 20.6, 0.0, 8.0, 0.5, 2.0, 0.0, "bedroll-packed")
    for i in range(6):                                                      # clôture au nord-est
        put(mb, "town", 21.5 + i, 0.0, 3.25, math.pi / 2, 1.0, 0.0, "fence" if i != 3 else "fence-broken")
    for i in range(4):                                                      # clôture au nord-ouest
        put(mb, "town", 8.5 + i, 0.0, 3.25, math.pi / 2, 1.0, 0.0, "fence")



# =========================================================================== maisons modulaires (Fantasy Town Kit)
def _local(x, z, rot, s, lx, lz):
    c, sn = math.cos(rot), math.sin(rot)
    return x + (c * lx + sn * lz) * s, z + (-sn * lx + c * lz) * s


def house(mb, x, z, length=2, floors=1, rot=0.0, s=2.0, door=0, chimney=True, roof=(0.62, 0.24, 0.2)):
    """Maison du Fantasy Town Kit assemblée pièce par pièce : rez-de-chaussée en pierre, étage à colombages, toit à
    pignons. (x, z) : centre au sol ; length : nombre de modules le long de l'axe local x ; s : taille d'un module."""
    put = objmodels.put
    for fl in range(floors):
        y = fl * s
        stone = fl == 0
        for i in range(length):
            lx = i - (length - 1) / 2
            px, pz = _local(x, z, rot, s, lx, 0)
            # (côté, rotation de la pièce) : +z devant, -z derrière, extrémités en -x / +x
            sides = [(-math.pi / 2, "front"), (math.pi / 2, "back")]
            if i == 0:
                sides.append((math.pi, "end"))
            if i == length - 1:
                sides.append((0.0, "end"))
            for r, kind in sides:
                if stone:
                    name = "wall-door" if (kind == "front" and i == door) else (
                        "wall-window-shutters" if (kind != "end" or length == 1) else "wall")
                else:
                    name = "wall-wood-window-shutters" if kind != "end" else "wall-wood-window-round"
                put(mb, "town", px, y, pz, rot + r, s, 1.0, name)
    _roof(mb, x, z, rot, length * s, s, floors * s, roof)
    if chimney:
        L = length * s
        px, pz = _local(x, z, rot, 1.0, L / 2 - 0.45 * s, -0.22 * s)
        top = floors * s + 0.75 * s
        mb.box(px - 0.13 * s, floors * s * 0.5, pz - 0.13 * s, px + 0.13 * s, top, pz + 0.13 * s, (0.46, 0.44, 0.46), 1.0)
        mb.box(px - 0.16 * s, top, pz - 0.16 * s, px + 0.16 * s, top + 0.08 * s, pz + 0.16 * s, (0.34, 0.33, 0.35), 1.0)


def _roof(mb, x, z, rot, L, W, H, color):
    """Toit à deux pans : faîtage selon l'axe local x (longueur L), largeur W, posé à la hauteur H."""
    rh, o, th = 0.55 * W, 0.14 * W, 0.06 * W
    c, sn = math.cos(rot), math.sin(rot)

    def vec(lx, ly, lz):
        return (c * lx + sn * lz, ly, -sn * lx + c * lz)

    def pt(lx, ly, lz):
        v = vec(lx, ly, lz)
        return (x + v[0], v[1], z + v[2])

    run = W / 2 + o
    drop = o * rh / (W / 2)
    for sg in (-1, 1):
        a = (0.0, H + rh, 0.0)
        b = (0.0, H - drop, sg * run)
        mid = ((a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
        dy, dz = (b[1] - a[1]) / 2, (b[2] - a[2]) / 2
        ln = math.hypot(dy, dz)
        ny, nz = -dz / ln * th * -sg, dy / ln * th * -sg
        mb.add("cube", pt(0, mid[0], mid[1]), vec(L / 2 + o, 0, 0), vec(0, dy, dz), vec(0, ny, nz), color, 1.0)
        # rangées de tuiles : fines bandes plus sombres le long de la pente
        for k in (0.3, 0.62):
            ty, tz = a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k
            mb.add("cube", pt(0, ty + ny * 1.2, tz + nz * 1.2), vec(L / 2 + o, 0, 0), vec(0, dy * 0.06, dz * 0.06),
                   vec(0, ny * 0.5, nz * 0.5), shade(color, 0.78), 1.0)
    # pignons triangulaires (colombages) aux deux extrémités
    from .meshes import quads_array
    wall = (0.56, 0.36, 0.22)
    tris = []
    for ex in (-L / 2, L / 2):
        p0, p1, p2 = pt(ex, H, -W / 2), pt(ex, H, W / 2), pt(ex, H + rh * 0.96, 0)
        n = vec(1 if ex > 0 else -1, 0, 0)
        tris.append((p0, p1, p2, p2, n, (*wall, 1.0)))
    mb.raw(quads_array(tris))
    # faîtière
    mb.add("cylinder", pt(0, H + rh + th * 0.4, 0), vec(0, W * 0.04, 0), vec(L / 2 + o, 0, 0), vec(0, 0, W * 0.04),
           shade(color, 0.6), 1.0)

