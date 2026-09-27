"""Modèles 3D en formes lisses (sphères, cylindres, cônes, pavés) : héros, monstres, gardiens, décors.

Tout est exprimé en coordonnées logiques : (x, y) au sol, z en hauteur (40 unités = 1 tuile).
Chaque pièce est envoyée au Frame comme une instance de primitive.
"""
import math

UP = (0.0, 0.0, 1.0)


def add(*vs):
    return (sum(v[0] for v in vs), sum(v[1] for v in vs), sum(v[2] for v in vs))


def mul(v, k):
    return (v[0] * k, v[1] * k, v[2] * k)


def norm(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def frame_axes(facing):
    ca, sa = math.cos(facing), math.sin(facing)
    return (ca, sa, 0.0), (-sa, ca, 0.0)


def tint(c, t, k=0.45):
    return (int(c[0] + (t[0] - c[0]) * k), int(c[1] + (t[1] - c[1]) * k), int(c[2] + (t[2] - c[2]) * k))


class Painter:
    """Petit utilitaire pour appliquer flash / teinte à toutes les pièces d'un modèle."""

    def __init__(self, fr, flash=False, tint_col=None, alpha_mul=1.0):
        self.fr = fr
        self.flash = flash
        self.tint = tint_col

    def col(self, c):
        if self.tint:
            c = tint(c, self.tint)
        if self.flash:
            c = tint(c, (255, 255, 255), 0.7)
        return c

    def part(self, mesh, c, ax, ay, az, color, emis=0.0):
        self.fr.part(mesh, c, ax, ay, az, self.col(color), 0.6 if self.flash else emis)

    def ellipsoid(self, c, f, s, rf, rs, rz, color, emis=0.0):
        self.part("sphere", c, mul(f, rf), mul(UP, rz), mul(s, rs), color, emis)

    def rod(self, a, b, r, color, side, mesh="cylinder", emis=0.0):
        """Cylindre (ou cône, pointe en b) entre deux points."""
        c = mul(add(a, b), 0.5)
        ax = mul(add(b, mul(a, -1)), 0.5)
        n1 = norm(cross(ax, side))
        if abs(n1[0]) + abs(n1[1]) + abs(n1[2]) < 1e-6:
            n1 = (1.0, 0.0, 0.0)
        n2 = norm(cross(ax, n1))
        self.part(mesh, c, mul(n1, r), ax, mul(n2, r), color, emis)

    def boxv(self, c, u, v, w, color, emis=0.0):
        self.part("cube", c, u, w, v, color, emis)


def limb(p, piv, f, s, t, r, hl, color, rs=None):
    """Membre cylindrique suspendu à un pivot, incliné de t radians vers l'avant."""
    ct, st = math.cos(t), math.sin(t)
    fp = add(mul(f, ct), mul(UP, st))
    upp = add(mul(UP, ct), mul(f, -st))
    center = add(piv, mul(upp, -hl))
    p.part("cylinder", center, mul(fp, r), mul(upp, hl), mul(s, rs or r), color)
    return add(piv, mul(upp, -2 * hl)), fp, upp


# =========================================================================== spécifications
PLAYER_SPECS = {
    "barbare": dict(body=(128, 82, 52), skin=(224, 172, 128), legs=(86, 62, 44), arms="skin", boots=(64, 44, 30),
                    helmet=(176, 178, 188), horns=(236, 226, 200), pauldrons=(150, 110, 70), belt=(66, 44, 28),
                    beard=(160, 90, 42), weapon="axe", fur=(170, 140, 100)),
    "sorcier": dict(body=(64, 72, 176), skin=(228, 188, 152), robe=True, arms="body", hat=(54, 60, 156),
                    belt=(220, 184, 96), beard=(226, 226, 230), weapon="staff", orb=(200, 140, 255)),
    "chasseur": dict(body=(72, 104, 60), skin=(222, 178, 136), legs=(94, 68, 46), arms="body", boots=(72, 50, 34),
                     hood=(60, 88, 48), cape=(52, 76, 42), belt=(112, 78, 46), weapon="bow", quiver=(110, 76, 44)),
    "paladin": dict(body=(190, 192, 204), skin=(226, 180, 140), legs=(150, 152, 164), arms="body",
                    boots=(120, 110, 100), helmet=(206, 208, 218), pauldrons=(226, 196, 110), belt=(120, 84, 50),
                    weapon="sword", blade=(255, 236, 170), shield=(40, 70, 150), shield_rim=(226, 196, 110),
                    cape=(160, 40, 40)),
    "necromancien": dict(body=(40, 44, 52), skin=(200, 196, 190), robe=True, arms="body", hood=(28, 30, 36),
                         belt=(120, 200, 140), weapon="scythe", orb=(120, 255, 160)),
    "assassin": dict(body=(46, 42, 60), skin=(214, 172, 136), legs=(40, 36, 50), arms="body", boots=(36, 32, 40),
                     hood=(36, 32, 48), mask=(30, 28, 36), cape=(70, 40, 90), belt=(120, 90, 60), weapon="daggers"),
}

MONSTER_SPECS = {
    "squelette": dict(body=(220, 214, 196), skin=(230, 226, 210), legs=(206, 200, 182), arms="skin", thin=True,
                      skull=True, weapon="sword", eyes=(255, 80, 40), ribs=True),
    "archer": dict(body=(204, 198, 178), skin=(224, 220, 202), legs=(190, 186, 166), arms="skin", thin=True,
                   skull=True, weapon="bow", eyes=(255, 120, 40), hood=(74, 64, 54)),
    "zombie": dict(body=(48, 150, 150), skin=(100, 152, 84), legs=(64, 64, 140), arms="skin", reach=True,
                   eyes=(140, 255, 100), hunch=True),
    "diablotin": dict(body=(200, 66, 42), skin=(214, 80, 48), legs=(156, 46, 30), arms="skin", horns=(60, 36, 30),
                      tail=(176, 52, 32), weapon="claws", eyes=(255, 230, 70), small=True, wings=(120, 36, 30)),
    "cultiste": dict(body=(100, 36, 124), skin=(176, 146, 136), robe=True, arms="body", hood=(70, 22, 86),
                     weapon="staff", orb=(255, 90, 220), eyes=(255, 110, 255)),
    "brute": dict(body=(146, 52, 40), skin=(166, 64, 46), legs=(96, 36, 28), arms="skin", horns=(80, 70, 60),
                  weapon="cleaver", eyes=(255, 170, 40), bulky=True, belt=(64, 42, 30)),
    "boucher": dict(body=(180, 112, 102), skin=(196, 128, 114), legs=(92, 58, 48), arms="skin", apron=(156, 28, 28),
                    weapon="cleaver", eyes=(255, 50, 30), bulky=True, belt=(74, 42, 30), hunch=True),
    "liche": dict(body=(48, 62, 104), skin=(228, 232, 222), robe=True, arms="body", skull=True, crown=(240, 200, 84),
                  weapon="staff", orb=(120, 235, 255), eyes=(120, 235, 255), cape=(32, 42, 74)),
    "golem": dict(body=(152, 146, 126), skin=(172, 164, 142), legs=(130, 124, 106), arms="skin", bulky=True,
                  weapon=None, eyes=(255, 150, 40), rocky=True, cracks=(255, 120, 30)),
    "seigneur": dict(body=(80, 30, 102), skin=(104, 42, 74), legs=(48, 20, 58), arms="body", horns=(44, 28, 28),
                     weapon="sword", blade=(120, 255, 150), eyes=(120, 255, 150), bulky=True, wings=(56, 20, 56),
                     pauldrons=(44, 40, 50), cape=(116, 22, 32)),
}

NPC_SPECS = {
    "marchand": dict(detailed=True, body=(124, 90, 56), skin=(216, 174, 134), legs=(82, 60, 42), arms="body",
                     hood=(156, 114, 64), belt=(206, 176, 84), hair_style="Court", hair=(130, 118, 104),
                     beard_style="Longue", beard=(150, 140, 128), eye_col=(104, 66, 38), weapon=None,
                     pack=(112, 82, 50), boots=(70, 50, 34), build=1.05),
    "forgeronne": dict(detailed=True, body=(98, 78, 66), skin=(228, 182, 144), legs=(66, 50, 40), arms="skin",
                       apron=(74, 48, 32), hair_style="Tresses", hair=(206, 96, 44), eye_col=(70, 160, 80),
                       weapon="hammer", build=1.18, boots=(56, 40, 30), bracers=(70, 46, 30), gloves=(80, 56, 36),
                       belt=(60, 40, 26)),
    "couturiere": dict(detailed=True, body=(112, 44, 110), skin=(178, 124, 84), legs=(54, 40, 60), arms="body",
                       hair_style="Queue de cheval", hair=(38, 32, 30), eye_col=(214, 150, 40), weapon=None,
                       sash=(226, 194, 120), collar=(226, 194, 120), boots=(60, 44, 36), marks="Tatouage runique",
                       build=0.9),
}


# =========================================================================== humanoïde
def humanoid(fr, x, y, z0, facing, phase, spec, sc=1.0, flash=False, tint_col=None, swing=0.0, moving=True,
             glow_eyes=True):
    if spec.get("detailed"):
        return hero(fr, x, y, z0, facing, phase, spec, sc, flash, tint_col, swing, moving)
    p = Painter(fr, flash, tint_col)
    f, s = frame_axes(facing)
    walk = math.sin(phase) if moving else 0.0
    bob = abs(math.sin(phase)) * 1.0 * sc if moving else 0.0
    Wd = 1.3 if spec.get("bulky") else (0.78 if spec.get("thin") else 1.0)
    if spec.get("small"):
        sc *= 0.8
    base = (x, y, z0 + bob)
    skin = spec.get("skin", spec["body"])
    arm_c = skin if spec.get("arms") == "skin" else spec["body"]
    legs_c = spec.get("legs", spec["body"])
    hunch = 0.35 if spec.get("hunch") else 0.0

    hip = 15 * sc
    if spec.get("robe"):
        p.part("frustum", add(base, (0, 0, 13.5 * sc)), mul(f, 8.2 * sc * Wd), mul(UP, 13.5 * sc), mul(s, 8.2 * sc * Wd),
               spec["body"])
    else:
        for side in (-1, 1):
            piv = add(base, mul(s, side * 3.2 * sc * Wd), (0, 0, hip))
            end, fp, upp = limb(p, piv, f, s, walk * 0.75 * side, 2.8 * sc * Wd, 7.3 * sc, legs_c)
            boot = spec.get("boots", legs_c)
            p.ellipsoid(add(end, mul(fp, 1.2 * sc), (0, 0, 1.6 * sc)), fp, s, 4.2 * sc, 3.2 * sc * Wd, 2.4 * sc, boot)

    # torse
    tf = add(f, (0, 0, 0))
    torso_c = add(base, mul(f, hunch * 4 * sc), (0, 0, hip + 9 * sc))
    if spec.get("robe"):
        p.ellipsoid(add(base, (0, 0, 27 * sc)), f, s, 5.2 * sc, 7.2 * sc * Wd, 6.5 * sc, spec["body"])
    else:
        p.ellipsoid(torso_c, tf, s, 5.0 * sc * (1.15 if spec.get("bulky") else 1), 7.0 * sc * Wd, 10.0 * sc,
                    spec["body"])
    if spec.get("ribs") and not flash:
        for i in range(3):
            p.part("cylinder", add(torso_c, mul(f, 4.2 * sc), (0, 0, (4 - i * 3.2) * sc)), mul(f, 0.8 * sc),
                   mul(UP, 0.6 * sc), mul(s, 5.2 * sc), (150, 144, 128))
    if spec.get("rocky"):
        for i, (a, h) in enumerate(((0.4, 6), (2.2, -2), (4.0, 4), (5.4, -5))):
            d = add(mul(f, math.cos(a) * 6 * sc), mul(s, math.sin(a) * 8 * sc))
            p.ellipsoid(add(torso_c, d, (0, 0, h * sc)), f, s, 3.4 * sc, 3.4 * sc, 3 * sc, (128, 122, 104))
    if spec.get("belt"):
        p.part("cylinder", add(base, (0, 0, hip + 1.5 * sc)), mul(f, 5.4 * sc), mul(UP, 1.3 * sc),
               mul(s, 7.2 * sc * Wd), spec["belt"])
    if spec.get("fur"):
        p.ellipsoid(add(torso_c, (0, 0, 7 * sc)), f, s, 5.8 * sc, 8.4 * sc * Wd, 3.2 * sc, spec["fur"])
    if spec.get("apron"):
        p.boxv(add(base, mul(f, 5.4 * sc), (0, 0, hip + 5 * sc)), mul(f, 0.6 * sc), mul(s, 5.4 * sc * Wd),
               mul(UP, 9 * sc), spec["apron"])
    if spec.get("cape"):
        sw = 0.18 + 0.15 * abs(walk)
        cc = add(base, mul(f, -5.8 * sc - 5 * sc * math.sin(sw)), (0, 0, 19 * sc))
        p.boxv(cc, mul(norm(add(f, mul(UP, math.sin(sw)))), 0.7 * sc), mul(s, 6.6 * sc * Wd), mul(UP, 12 * sc),
               spec["cape"])
    if spec.get("pack"):
        p.boxv(add(base, mul(f, -7 * sc), (0, 0, 26 * sc)), mul(f, 3 * sc), mul(s, 5 * sc), mul(UP, 6.5 * sc),
               spec["pack"])
    if spec.get("quiver"):
        p.rod(add(base, mul(f, -6 * sc), mul(s, -3 * sc), (0, 0, 20 * sc)),
              add(base, mul(f, -7 * sc), mul(s, 3 * sc), (0, 0, 36 * sc)), 2.4 * sc, spec["quiver"], f)
    if spec.get("wings"):
        flap = math.sin(phase * 0.7) * 0.25
        for side in (-1, 1):
            root = add(base, mul(f, -5 * sc), mul(s, side * 4 * sc), (0, 0, 30 * sc))
            tipv = norm(add(mul(s, side), (0, 0, 0.5 + flap), mul(f, -0.3)))
            p.rod(root, add(root, mul(tipv, 20 * sc)), 5 * sc, spec["wings"], f, mesh="cone")
    if spec.get("tail"):
        p.rod(add(base, mul(f, -4 * sc), (0, 0, 13 * sc)), add(base, mul(f, -13 * sc), (0, 0, 8 * sc)), 1.4 * sc,
              spec["tail"], s, mesh="cone")

    # tête
    hr = 6.4 * sc * (0.9 if spec.get("skull") else 1)
    hc = add(base, mul(f, hunch * 7 * sc), (0, 0, hip + 19 * sc + hr - hunch * 5 * sc))
    p.ellipsoid(hc, f, s, hr, hr, hr * 1.02, skin)
    if spec.get("skull") and not flash:
        for side in (-1, 1):
            p.ellipsoid(add(hc, mul(f, hr * 0.8), mul(s, side * 2.4 * sc), (0, 0, 0.6 * sc)), f, s, 1.2 * sc,
                        1.8 * sc, 1.8 * sc, (30, 22, 22))
    if spec.get("beard"):
        p.ellipsoid(add(hc, mul(f, hr * 0.62), (0, 0, -hr * 0.55)), f, s, 2.6 * sc, 4.6 * sc, 4.2 * sc, spec["beard"])
    if spec.get("hair"):
        p.ellipsoid(add(hc, mul(f, -1.4 * sc), (0, 0, 1.5 * sc)), f, s, hr * 1.05, hr * 1.08, hr * 0.95, spec["hair"])
    if spec.get("helmet"):
        p.ellipsoid(add(hc, (0, 0, 1.6 * sc)), f, s, hr * 1.1, hr * 1.1, hr * 0.8, spec["helmet"])
    if spec.get("hood"):
        p.ellipsoid(add(hc, mul(f, -1.3 * sc), (0, 0, 1.0 * sc)), f, s, hr * 1.15, hr * 1.18, hr * 1.12, spec["hood"])
        p.rod(add(hc, mul(f, -4 * sc), (0, 0, hr * 0.6)), add(hc, mul(f, -10 * sc), (0, 0, hr * 0.9)), 3.2 * sc,
              spec["hood"], s, mesh="cone")
    if spec.get("hat"):
        h = spec["hat"]
        p.part("cylinder", add(hc, (0, 0, hr * 0.75)), mul(f, 11 * sc), mul(UP, 0.8 * sc), mul(s, 11 * sc), h)
        p.rod(add(hc, (0, 0, hr * 0.8)), add(hc, mul(f, -6 * sc), (0, 0, hr + 17 * sc)), 6.2 * sc, h, s, mesh="cone")
    if spec.get("horns"):
        for side in (-1, 1):
            hb = add(hc, mul(s, side * hr * 0.8), (0, 0, hr * 0.45))
            tip = add(hb, mul(s, side * 5 * sc), (0, 0, 8 * sc), mul(f, 1.5 * sc))
            p.rod(hb, tip, 1.9 * sc, spec["horns"], f, mesh="cone")
    if spec.get("crown"):
        for i in range(5):
            a = i / 5 * math.tau
            cp = add(hc, (math.cos(a) * hr * 0.7, math.sin(a) * hr * 0.7, hr * 0.8))
            p.rod(cp, add(cp, (0, 0, 5 * sc)), 1.4 * sc, spec["crown"], f, mesh="cone", emis=0.25)
    eyes = spec.get("eyes")
    if eyes:
        for side in (-1, 1):
            ep = add(hc, mul(f, hr * 0.9), mul(s, side * 2.4 * sc), (0, 0, 0.7 * sc))
            p.part("sphere", ep, (1.0 * sc, 0, 0), (0, 0, 1.0 * sc), (0, 1.0 * sc, 0), eyes, 1.0)
            if glow_eyes:
                fr.glow(ep[0], ep[1], ep[2], 4.5 * sc, eyes, 0.8)

    # bras
    sh_z = hip + 15 * sc
    k = max(0.0, min(1.0, -swing / 1.4)) if swing < 0 else 0.0
    spin = swing > 0.2
    for side in (-1, 1):
        piv = add(base, mul(f, hunch * 5 * sc), mul(s, side * (7.2 * Wd + 2.2) * sc), (0, 0, sh_z))
        if spec.get("reach"):
            t = 1.45 + math.sin(phase * 2 + side) * 0.08
        elif side == 1:
            t = walk * -0.6 + 1.6 * k + (1.3 if spin else 0)
        else:
            t = walk * 0.6 + (1.0 if spec.get("weapon") == "bow" else 0)
        end, fp, upp = limb(p, piv, f, s, t, 2.3 * sc * Wd, 6.8 * sc, arm_c)
        p.part("sphere", end, (2.8 * sc * Wd, 0, 0), (0, 0, 2.8 * sc * Wd), (0, 2.8 * sc * Wd, 0), skin)
        if spec.get("pauldrons"):
            p.ellipsoid(add(piv, (0, 0, 1.5 * sc)), f, s, 4 * sc, 4 * sc, 3 * sc, spec["pauldrons"])
        if side == 1:
            g = 0.35 + 1.6 * k
            wdir = norm(add(mul(UP, math.cos(g)), mul(f, math.sin(g))))
            if spin:
                wdir = norm(add(s, (0, 0, 0.25)))
            _weapon(p, fr, spec, end, f, s, wdir, sc)
        if side == -1 and spec.get("weapon") == "bow":
            _bow(p, end, f, s, sc)


# =========================================================================== héros détaillé
def _sphere(p, c, r, color, emis=0.0):
    p.part("sphere", c, (r, 0, 0), (0, 0, r), (0, r, 0), color, emis)


def _on_head(hc, hr, f, s, fwd, side, up):
    """Point à la surface de la tête (direction donnée dans le repère du visage) et sa normale."""
    n = norm(add(mul(f, fwd), mul(s, side), mul(UP, up)))
    return add(hc, mul(n, hr * 1.0)), n


def _face_mark(p, hc, hr, f, s, fwd, side, up, size, color, emis=0.0):
    c, n = _on_head(hc, hr, f, s, fwd, side, up)
    t = norm(cross(UP, n))
    p.ellipsoid(c, n, t, 0.28 * size[0], size[1], size[2], color, emis)


def _hair(p, spec, hc, hr, f, s, sc):
    style = spec.get("hair_style", "Court")
    col = spec["hair"]
    covered = spec.get("helmet") or spec.get("hat") or spec.get("hood")
    if style == "Rasé":
        return
    if style == "Crête":
        if not covered:
            for i in range(5):
                a = -0.7 + i * 0.35
                c = add(hc, mul(f, math.sin(a) * hr * 0.95), (0, 0, math.cos(a) * hr * 0.92))
                tip = add(c, mul(norm(add(mul(f, math.sin(a)), (0, 0, math.cos(a)))), 3.4 * sc))
                p.rod(c, tip, 1.5 * sc, col, s, mesh="cone")
        return
    # calotte : couvre le haut et l'arrière du crâne en dégageant le visage
    p.ellipsoid(add(hc, mul(f, -1.5 * sc), (0, 0, 2.0 * sc)), f, s, hr * 1.08, hr * 1.07, hr * 0.8, col)
    for side in (-1, 1):   # mèches sur les tempes
        p.ellipsoid(add(hc, mul(f, 1.4 * sc), mul(s, side * hr * 0.82), (0, 0, 1.8 * sc)), f, s, 2.2 * sc, 1.2 * sc,
                    2.6 * sc, col)
    if style == "Long":
        p.ellipsoid(add(hc, mul(f, -3.6 * sc), (0, 0, -3.6 * sc)), f, s, 3.0 * sc, hr * 0.98, 7.2 * sc, col)
    elif style == "Queue de cheval":
        knot = add(hc, mul(f, -hr * 1.02), (0, 0, 1.2 * sc))
        _sphere(p, knot, 1.9 * sc, col)
        p.rod(knot, add(knot, mul(f, -3.5 * sc), (0, 0, -10 * sc)), 2.1 * sc, col, s, mesh="cone")
    elif style == "Tresses":
        for side in (-1, 1):
            top = add(hc, mul(s, side * hr * 0.86), mul(f, -0.8 * sc), (0, 0, -1.2 * sc))
            bot = add(top, mul(s, side * 0.8 * sc), mul(f, 1.4 * sc), (0, 0, -10 * sc))
            p.rod(top, bot, 1.35 * sc, col, f)
            _sphere(p, bot, 1.2 * sc, (220, 184, 96))


def _beard(p, spec, hc, hr, f, s, sc):
    style = spec.get("beard_style", "Aucune")
    col = spec.get("beard", spec.get("hair", (90, 60, 40)))
    if style == "Courte":
        p.ellipsoid(add(hc, mul(f, hr * 0.6), (0, 0, -hr * 0.52)), f, s, 2.8 * sc, 4.4 * sc, 2.8 * sc, col)
    elif style == "Longue":
        p.ellipsoid(add(hc, mul(f, hr * 0.62), (0, 0, -hr * 0.55)), f, s, 2.8 * sc, 4.6 * sc, 3.6 * sc, col)
        p.ellipsoid(add(hc, mul(f, hr * 0.66), (0, 0, -hr * 1.05)), f, s, 2.2 * sc, 3.2 * sc, 4.0 * sc, col)
    if style in ("Longue", "Moustache", "Courte"):
        for side in (-1, 1):
            c = add(hc, mul(f, hr * 0.92), mul(s, side * 1.35 * sc), (0, 0, -1.9 * sc))
            p.ellipsoid(c, f, s, 0.8 * sc, 1.7 * sc, 0.7 * sc, col)


def _face(p, spec, hc, hr, f, s, sc):
    skin = spec["skin"]
    for side in (-1, 1):   # oreilles
        p.ellipsoid(add(hc, mul(s, side * hr * 0.9), (0, 0, -0.2 * sc)), f, s, 1.3 * sc, 0.8 * sc, 1.8 * sc, skin)
    eye_c = spec.get("eye_col", (90, 140, 200))
    brow = spec.get("hair", (60, 40, 30)) if spec.get("hair_style") != "Rasé" else tint(skin, (40, 30, 26), 0.5)
    for side in (-1, 1):
        ep = add(hc, mul(f, hr * 0.8), mul(s, side * 2.2 * sc), (0, 0, 0.5 * sc))
        p.ellipsoid(ep, f, s, 1.0 * sc, 1.3 * sc, 1.5 * sc, (246, 243, 236))
        ip = add(ep, mul(f, 0.62 * sc))
        p.ellipsoid(ip, f, s, 0.5 * sc, 0.85 * sc, 1.0 * sc, eye_c)
        pp = add(ip, mul(f, 0.3 * sc))
        p.ellipsoid(pp, f, s, 0.35 * sc, 0.45 * sc, 0.55 * sc, (18, 14, 16))
        _sphere(p, add(pp, mul(f, 0.3 * sc), mul(s, -0.25 * sc), (0, 0, 0.4 * sc)), 0.2 * sc, (255, 255, 255), 0.8)
        p.ellipsoid(add(hc, mul(f, hr * 0.86), mul(s, side * 2.3 * sc), (0, 0, 2.3 * sc)), f, s, 0.55 * sc, 1.5 * sc,
                    0.45 * sc, brow)
    p.ellipsoid(add(hc, mul(f, hr * 0.93), (0, 0, -0.5 * sc)), f, s, 1.0 * sc, 0.85 * sc, 1.25 * sc,
                tint(skin, (60, 30, 20), 0.12))
    p.ellipsoid(add(hc, mul(f, hr * 0.88), (0, 0, -2.4 * sc)), f, s, 0.4 * sc, 1.3 * sc, 0.35 * sc,
                tint(skin, (120, 40, 40), 0.4))
    marks = spec.get("marks", "Aucune")
    if marks == "Peinture de guerre":
        for side in (-1, 1):
            for k in (0, 1):
                _face_mark(p, hc, hr, f, s, 0.72, side * (0.5 + k * 0.14), -0.12, (1, 0.35 * sc, 1.6 * sc),
                           (54, 100, 196))
        _face_mark(p, hc, hr, f, s, 0.9, 0.0, 0.42, (1, 0.35 * sc, 1.4 * sc), (54, 100, 196))
    elif marks == "Cicatrice":
        for i in range(4):
            _face_mark(p, hc, hr, f, s, 0.8, 0.5 - i * 0.02, 0.48 - i * 0.16, (1, 0.3 * sc, 0.75 * sc),
                       tint(skin, (230, 140, 130), 0.55))
    elif marks == "Tatouage runique":
        _face_mark(p, hc, hr, f, s, 0.86, 0.0, 0.5, (1, 0.9 * sc, 0.3 * sc), (110, 230, 255), 0.9)
        _face_mark(p, hc, hr, f, s, 0.86, 0.0, 0.5, (1, 0.3 * sc, 0.9 * sc), (110, 230, 255), 0.9)
        for side in (-1, 1):
            _face_mark(p, hc, hr, f, s, 0.7, side * 0.55, -0.2, (1, 0.35 * sc, 0.35 * sc), (110, 230, 255), 0.9)


def hero(fr, x, y, z0, facing, phase, spec, sc=1.0, flash=False, tint_col=None, swing=0.0, moving=True):
    """Héros et PNJ détaillés : visage, coiffure, barbe, marques, bras et jambes articulés (coudes, genoux)."""
    p = Painter(fr, flash, tint_col)
    f, s = frame_axes(facing)
    walk = math.sin(phase) if moving else 0.0
    bob = abs(math.sin(phase)) * 1.0 * sc if moving else 0.0
    Wd = spec.get("build", 1.0)
    base = (x, y, z0 + bob)
    skin = spec["skin"]
    body = spec["body"]
    legs_c = spec.get("legs", body)
    boots = spec.get("boots", legs_c)
    robe = spec.get("robe")
    hip = 15 * sc

    # jambes : cuisse + tibia, le genou plie quand la jambe repasse vers l'arrière
    for side in (-1, 1):
        a = walk * 0.7 * side
        if robe:
            foot = add(base, mul(f, 1.6 * sc + walk * side * 3.5 * sc), mul(s, side * 3.2 * sc * Wd), (0, 0, 1.4 * sc))
            p.ellipsoid(foot, f, s, 3.8 * sc, 2.5 * sc * Wd, 1.9 * sc, boots)
            continue
        piv = add(base, mul(s, side * 3.3 * sc * Wd), (0, 0, hip))
        knee, _, _ = limb(p, piv, f, s, a, 2.9 * sc * Wd, 3.9 * sc, legs_c)
        _sphere(p, knee, 2.6 * sc * Wd, legs_c)
        bend = (0.1 + max(0.0, -walk * side) * 0.9) if moving else 0.06
        ankle, fp2, up2 = limb(p, knee, f, s, a - bend, 2.5 * sc * Wd, 3.6 * sc, boots)
        p.part("cylinder", add(knee, mul(up2, -1.6 * sc)), mul(fp2, 2.95 * sc * Wd), mul(up2, 0.9 * sc),
               mul(s, 2.95 * sc * Wd), spec.get("cuff", boots))
        p.ellipsoid(add(ankle, mul(f, 1.6 * sc), (0, 0, 1.0 * sc)), f, s, 4.0 * sc, 2.7 * sc * Wd, 2.0 * sc, boots)

    # bassin, ventre, poitrine
    if robe:
        p.part("frustum", add(base, (0, 0, 13.5 * sc)), mul(f, 8.0 * sc * Wd), mul(UP, 13.5 * sc), mul(s, 8.4 * sc * Wd),
               body)
        if spec.get("trim"):
            p.part("frustum", add(base, (0, 0, 1.6 * sc)), mul(f, 8.1 * sc * Wd), mul(UP, 1.2 * sc),
                   mul(s, 8.5 * sc * Wd), spec["trim"])
    else:
        p.ellipsoid(add(base, (0, 0, hip + 0.5 * sc)), f, s, 4.6 * sc, 6.4 * sc * Wd, 3.4 * sc, legs_c)
    # torse d'un seul volume, élargi aux épaules (silhouette en V)
    p.ellipsoid(add(base, (0, 0, hip + 8.6 * sc)), f, s, 4.5 * sc, 6.3 * sc * Wd, 9.4 * sc, body)
    p.ellipsoid(add(base, mul(f, -0.3 * sc), (0, 0, hip + 14.6 * sc)), f, s, 4.2 * sc, 8.2 * sc * Wd, 3.6 * sc, body)
    belt = spec.get("sash") or spec.get("belt")
    if belt:
        p.part("cylinder", add(base, (0, 0, hip + 2.4 * sc)), mul(f, 4.75 * sc), mul(UP, 1.2 * sc),
               mul(s, 6.35 * sc * Wd), belt)
        p.boxv(add(base, mul(f, 4.8 * sc), (0, 0, hip + 2.4 * sc)), mul(f, 0.5 * sc), mul(s, 1.3 * sc),
               mul(UP, 1.1 * sc), (224, 188, 100), 0.1)
    if spec.get("strap"):
        a = add(base, mul(f, 3.9 * sc), mul(s, -5.2 * sc * Wd), (0, 0, hip + 16 * sc))
        m = add(base, mul(f, 5.5 * sc), mul(s, -0.3 * sc * Wd), (0, 0, hip + 10 * sc))
        b = add(base, mul(f, 4.3 * sc), mul(s, 4.6 * sc * Wd), (0, 0, hip + 3.6 * sc))
        p.rod(a, m, 0.9 * sc, spec["strap"], s)
        p.rod(m, b, 0.9 * sc, spec["strap"], s)
    if spec.get("fur"):
        p.ellipsoid(add(base, (0, 0, hip + 16.8 * sc)), f, s, 5.4 * sc, 8.4 * sc * Wd, 2.8 * sc, spec["fur"])
    if spec.get("collar"):
        p.part("frustum", add(base, (0, 0, hip + 17.4 * sc)), mul(f, 4.6 * sc), mul(UP, 1.6 * sc),
               mul(s, 6.0 * sc * Wd), spec["collar"])
    if spec.get("tabard"):
        for d in (1, -1):
            p.boxv(add(base, mul(f, d * 4.9 * sc), (0, 0, hip + 6.5 * sc)), mul(f, 0.45 * sc), mul(s, 3.6 * sc * Wd),
                   mul(UP, 9.5 * sc), spec["tabard"])
        p.boxv(add(base, mul(f, 5.4 * sc), (0, 0, hip + 10 * sc)), mul(f, 0.2 * sc), mul(s, 0.7 * sc), mul(UP, 3.2 * sc),
               (240, 220, 150), 0.2)
        p.boxv(add(base, mul(f, 5.4 * sc), (0, 0, hip + 11 * sc)), mul(f, 0.2 * sc), mul(s, 2.2 * sc), mul(UP, 0.7 * sc),
               (240, 220, 150), 0.2)
    if spec.get("apron"):
        p.boxv(add(base, mul(f, 5.0 * sc), (0, 0, hip + 5 * sc)), mul(f, 0.6 * sc), mul(s, 5.2 * sc * Wd),
               mul(UP, 9 * sc), spec["apron"])
    if spec.get("cape"):
        sw = 0.18 + 0.15 * abs(walk)
        cc = add(base, mul(f, -5.8 * sc - 5 * sc * math.sin(sw)), (0, 0, 19 * sc))
        p.boxv(cc, mul(norm(add(f, mul(UP, math.sin(sw)))), 0.7 * sc), mul(s, 6.8 * sc * Wd), mul(UP, 12.5 * sc),
               spec["cape"])
    if spec.get("pack"):
        p.boxv(add(base, mul(f, -7 * sc), (0, 0, 26 * sc)), mul(f, 3 * sc), mul(s, 5 * sc), mul(UP, 6.5 * sc),
               spec["pack"])
    if spec.get("quiver"):
        q0 = add(base, mul(f, -6 * sc), mul(s, -3 * sc), (0, 0, 20 * sc))
        q1 = add(base, mul(f, -7 * sc), mul(s, 3 * sc), (0, 0, 36 * sc))
        p.rod(q0, q1, 2.4 * sc, spec["quiver"], f)
        for i in range(3):
            tip = add(q1, mul(s, (i - 1) * 1.2 * sc), (0, 0, 3.5 * sc))
            p.rod(q1, tip, 0.35 * sc, (220, 220, 210), f)
            _sphere(p, tip, 0.8 * sc, (190, 60, 50))

    # cou et tête
    p.part("cylinder", add(base, (0, 0, hip + 18.6 * sc)), (2.1 * sc, 0, 0), (0, 0, 1.8 * sc), (0, 2.1 * sc, 0), skin)
    hr = 6.0 * sc
    hc = add(base, (0, 0, hip + 19.4 * sc + hr))
    p.ellipsoid(hc, f, s, hr * 0.97, hr * 0.93, hr * 1.04, skin)
    _face(p, spec, hc, hr, f, s, sc)
    if spec.get("mask"):
        p.ellipsoid(add(hc, mul(f, hr * 0.5), (0, 0, -hr * 0.42)), f, s, hr * 0.62, hr * 0.9, hr * 0.5, spec["mask"])
    _hair(p, spec, hc, hr, f, s, sc)
    _beard(p, spec, hc, hr, f, s, sc)
    if spec.get("helmet"):
        p.ellipsoid(add(hc, (0, 0, 1.9 * sc)), f, s, hr * 1.1, hr * 1.1, hr * 0.78, spec["helmet"])
        p.part("cylinder", add(hc, (0, 0, 0.9 * sc)), mul(f, hr * 1.12), mul(UP, 0.7 * sc), mul(s, hr * 1.12),
               tint(spec["helmet"], (60, 50, 40), 0.35))
        p.boxv(add(hc, mul(f, hr * 1.04), (0, 0, 1.2 * sc)), mul(f, 0.5 * sc), mul(s, 0.45 * sc), mul(UP, 1.6 * sc),
               spec["helmet"])
    if spec.get("hood"):
        p.ellipsoid(add(hc, mul(f, -1.6 * sc), (0, 0, 1.0 * sc)), f, s, hr * 1.12, hr * 1.16, hr * 1.12, spec["hood"])
        p.rod(add(hc, mul(f, -4 * sc), (0, 0, hr * 0.6)), add(hc, mul(f, -10 * sc), (0, 0, hr * 0.9)), 3.2 * sc,
              spec["hood"], s, mesh="cone")
    if spec.get("hat"):
        h = spec["hat"]
        p.part("cylinder", add(hc, (0, 0, hr * 0.75)), mul(f, 11 * sc), mul(UP, 0.8 * sc), mul(s, 11 * sc), h)
        p.part("cylinder", add(hc, (0, 0, hr * 0.95)), mul(f, 6.4 * sc), mul(UP, 0.9 * sc), mul(s, 6.4 * sc),
               spec.get("trim", h))
        p.rod(add(hc, (0, 0, hr * 0.8)), add(hc, mul(f, -6 * sc), (0, 0, hr + 17 * sc)), 6.2 * sc, h, s, mesh="cone")
    if spec.get("horns"):
        for side in (-1, 1):
            hb = add(hc, mul(s, side * hr * 0.85), (0, 0, hr * 0.45))
            mid = add(hb, mul(s, side * 4.2 * sc), (0, 0, 2.5 * sc), mul(f, 1.0 * sc))
            p.rod(hb, mid, 1.9 * sc, spec["horns"], f)
            p.rod(mid, add(mid, mul(s, side * 1.8 * sc), (0, 0, 6 * sc), mul(f, 1.2 * sc)), 1.9 * sc, spec["horns"], f,
                  mesh="cone")

    # bras : épaule, coude, main
    sh_z = hip + 15.8 * sc
    k = max(0.0, min(1.0, -swing / 1.4)) if swing < 0 else 0.0
    spin = swing > 0.2
    bow = spec.get("weapon") == "bow"
    upper_c = skin if spec.get("arms") == "skin" else body
    hand_c = spec.get("gloves", skin)
    for side in (-1, 1):
        piv = add(base, mul(s, side * (7.0 * Wd + 2.1) * sc), (0, 0, sh_z))
        if side == 1:
            t = walk * -0.6 + 1.6 * k + (1.3 if spin else 0)
            bend = 0.35 - 0.3 * k
        else:
            t = walk * 0.6 + (1.0 if bow else 0)
            bend = 0.35 + (0.25 if bow else 0.0)
        _sphere(p, piv, 2.7 * sc * Wd, upper_c)
        elbow, _, _ = limb(p, piv, f, s, t, 2.3 * sc * Wd, 3.5 * sc, upper_c)
        _sphere(p, elbow, 2.15 * sc * Wd, upper_c)
        hand, fp2, up2 = limb(p, elbow, f, s, t + bend, 2.05 * sc * Wd, 3.3 * sc, upper_c if robe else skin
                              if spec.get("arms") == "skin" else body)
        if robe:
            p.part("frustum", add(elbow, mul(up2, -4.6 * sc)), mul(fp2, 3.0 * sc * Wd), mul(up2, 1.8 * sc),
                   mul(s, 3.0 * sc * Wd), spec.get("trim", body))
        if spec.get("bracers"):
            p.part("cylinder", add(elbow, mul(up2, -4.2 * sc)), mul(fp2, 2.3 * sc * Wd), mul(up2, 1.7 * sc),
                   mul(s, 2.3 * sc * Wd), spec["bracers"])
        _sphere(p, hand, 2.35 * sc * Wd, hand_c)
        if spec.get("pauldrons"):
            p.ellipsoid(add(piv, (0, 0, 1.4 * sc)), f, s, 4.2 * sc, 4.2 * sc, 3.0 * sc, spec["pauldrons"])
            p.part("sphere", add(piv, (0, 0, 3.6 * sc)), (1.0 * sc, 0, 0), (0, 0, 1.0 * sc), (0, 1.0 * sc, 0),
                   (200, 196, 190))
        if side == 1:
            g = 0.35 + 1.6 * k
            wdir = norm(add(mul(UP, math.cos(g)), mul(f, math.sin(g))))
            if spin:
                wdir = norm(add(s, (0, 0, 0.25)))
            _weapon(p, fr, spec, hand, f, s, wdir, sc)
        if side == -1 and bow:
            _bow(p, hand, f, s, sc)
        if side == -1 and spec.get("shield"):
            _shield(p, spec, hand, f, s, sc)
        if side == -1 and spec.get("weapon") == "daggers":
            _weapon(p, fr, dict(weapon="dagger"), hand, f, s, norm(add(mul(UP, 0.5), mul(f, 0.9))), sc)


def _shield(p, spec, hand, f, s, sc):
    """Bouclier rond porté au bras gauche, face vers l'avant."""
    c = add(hand, mul(f, 3.2 * sc), mul(s, -1.2 * sc), (0, 0, 2.0 * sc))
    p.part("cylinder", c, mul(s, 7.4 * sc), mul(f, 0.9 * sc), mul(UP, 8.2 * sc), spec["shield"])
    p.part("cylinder", add(c, mul(f, -0.1 * sc)), mul(s, 7.9 * sc), mul(f, 0.7 * sc), mul(UP, 8.7 * sc),
           spec.get("shield_rim", (200, 200, 210)))
    p.part("sphere", add(c, mul(f, 1.1 * sc)), mul(s, 2.0 * sc), mul(f, 1.2 * sc), mul(UP, 2.0 * sc),
           spec.get("shield_rim", (200, 200, 210)), 0.2)
    p.boxv(add(c, mul(f, 1.0 * sc)), mul(f, 0.3 * sc), mul(s, 0.8 * sc), mul(UP, 5.6 * sc), (240, 226, 170), 0.3)
    p.boxv(add(c, mul(f, 1.0 * sc), (0, 0, 1.4 * sc)), mul(f, 0.3 * sc), mul(s, 4.0 * sc), mul(UP, 0.8 * sc),
           (240, 226, 170), 0.3)


def _weapon(p, fr, spec, hand, f, s, wdir, sc):
    kind = spec.get("weapon")
    if not kind or kind == "bow":
        return
    n = norm(cross(wdir, s))
    wood, metal, dark = (126, 84, 48), (200, 202, 214), (72, 72, 82)
    if kind == "sword":
        blade = spec.get("blade", (214, 218, 228))
        glowing = "blade" in spec
        p.boxv(add(hand, mul(wdir, 14 * sc)), mul(wdir, 11 * sc), mul(s, 1.3 * sc), mul(n, 0.5 * sc), blade,
               0.9 if glowing else 0.0)
        p.boxv(add(hand, mul(wdir, 2.6 * sc)), mul(wdir, 0.8 * sc), mul(s, 3.6 * sc), mul(n, 0.9 * sc), (156, 124, 60))
        if glowing:
            tp = add(hand, mul(wdir, 22 * sc))
            fr.glow(tp[0], tp[1], tp[2], 14 * sc, blade, 0.6)
    elif kind in ("axe", "hammer"):
        p.rod(add(hand, mul(wdir, -3 * sc)), add(hand, mul(wdir, 16 * sc)), 0.9 * sc, wood, s)
        if kind == "axe":
            head = add(hand, mul(wdir, 13 * sc), mul(n, 3 * sc))
            p.boxv(head, mul(wdir, 3.6 * sc), mul(s, 0.7 * sc), mul(n, 3.4 * sc), metal)
            p.ellipsoid(add(head, mul(n, 3.2 * sc)), wdir, s, 4.2 * sc, 0.7 * sc, 1.5 * sc, metal)
        else:
            p.boxv(add(hand, mul(wdir, 15 * sc)), mul(wdir, 2.4 * sc), mul(s, 2.4 * sc), mul(n, 4 * sc), dark)
    elif kind == "cleaver":
        p.rod(hand, add(hand, mul(wdir, 5 * sc)), 1.0 * sc, wood, s)
        p.boxv(add(hand, mul(wdir, 12 * sc), mul(n, 2.6 * sc)), mul(wdir, 7 * sc), mul(s, 0.7 * sc), mul(n, 4.6 * sc),
               (176, 172, 176))
    elif kind == "staff":
        p.rod(add(hand, mul(wdir, -12 * sc)), add(hand, mul(wdir, 20 * sc)), 1.0 * sc, wood, s)
        orb = spec.get("orb", (200, 200, 255))
        oc = add(hand, mul(wdir, 23 * sc))
        p.part("sphere", oc, (2.8 * sc, 0, 0), (0, 0, 2.8 * sc), (0, 2.8 * sc, 0), orb, 1.0)
        fr.glow(oc[0], oc[1], oc[2], 14 * sc, orb, 0.9)
    elif kind in ("dagger", "daggers"):
        p.boxv(add(hand, mul(wdir, 7 * sc)), mul(wdir, 5.5 * sc), mul(s, 0.9 * sc), mul(n, 0.35 * sc),
               (220, 222, 236))
        p.boxv(add(hand, mul(wdir, 1.4 * sc)), mul(wdir, 0.5 * sc), mul(s, 2.2 * sc), mul(n, 0.6 * sc), (90, 70, 110))
    elif kind == "scythe":
        top = add(hand, mul(wdir, 22 * sc))
        p.rod(add(hand, mul(wdir, -12 * sc)), top, 1.0 * sc, (60, 52, 50), s)
        orb = spec.get("orb", (140, 255, 170))
        prev = top
        for i in range(1, 5):
            a = i / 4
            pt = add(top, mul(n, -9 * sc * a), mul(wdir, -5 * sc * a * a))
            p.rod(prev, pt, (1.5 - a * 0.9) * sc, (200, 206, 214), s, mesh="cone" if i == 4 else "cylinder")
            prev = pt
        fr.glow(top[0], top[1], top[2], 10 * sc, orb, 0.8)
    elif kind == "claws":
        for off in (-1.8, 0, 1.8):
            p.rod(add(hand, mul(s, off * sc)), add(hand, mul(f, 6 * sc), mul(s, off * sc)), 0.7 * sc, (236, 228, 210),
                  s, mesh="cone")


def _bow(p, hand, f, s, sc):
    wood = (134, 90, 52)
    pts = []
    for i in range(7):
        t = -1 + 2 * i / 6
        pts.append(add(hand, mul(f, 3 * sc + 4 * sc * (1 - t * t)), (0, 0, t * 12 * sc)))
    for a, b in zip(pts, pts[1:]):
        p.rod(a, b, 0.9 * sc, wood, s)
    p.rod(pts[0], pts[-1], 0.25 * sc, (236, 236, 222), s)


# =========================================================================== décors et objets
def chest(fr, x, y, opened, t=0.0):
    wood, trim, gold = (140, 90, 46), (78, 50, 26), (240, 200, 84)
    fr.box(x, y, 0, 13, 9, 7, wood)
    for dx in (-12.4, 12.4):
        fr.box(x + dx, y, 0, 1.0, 9.4, 7.3, trim)
    if opened:
        fr.part("cube", (x, y - 10.5, 16), (13, 0, 0), (0, -1.5, 7), (0, 1.4, 0), (156, 100, 52))
        fr.glow(x, y, 12, 18, (255, 210, 110), 0.35)
    else:
        fr.part("cylinder", (x, y, 14), (13, 0, 0), (0, 0, 2.6), (0, 9.2, 0), (156, 100, 52))
        fr.box(x, y + 9.4, 8, 2.4, 0.8, 3, gold, 0.5)
        fr.glow(x, y, 16, 26 + 3 * math.sin(t * 3), (255, 200, 90), 0.35)


def portal(fr, x, y, color, t):
    stone, dark = (156, 152, 162), (112, 110, 120)
    f, s = frame_axes(math.pi / 4)
    for side in (-1, 1):
        c = add((x, y, 0), mul(s, side * 30))
        fr.part("cylinder", add(c, (0, 0, 34)), (7, 0, 0), (0, 0, 34), (0, 7, 0), stone)
        fr.part("cube", add(c, (0, 0, 70)), (8.5, 0, 0), (0, 0, 3), (0, 8.5, 0), dark)
    fr.part("cube", (x, y, 78), mul(f, 8), (0, 0, 5), mul(s, 38), stone)
    fr.part("sphere", (x, y, 88), (5, 0, 0), (0, 0, 5), (0, 5, 0), color, 1.0)
    # voile d'énergie
    fr.part("sphere", (x, y, 36), mul(f, 1.5), (0, 0, 33 + 1.5 * math.sin(t * 3)), mul(s, 23), color, 0.9,
            additive=True)
    fr.box(x, y, 0, 30, 30, 1.5, dark, mesh="cylinder")
    for i in range(3):
        a = t * 2 + i * math.tau / 3
        fr.glow(x + math.cos(a) * s[0] * 18, y + math.cos(a) * s[1] * 18, 36 + math.sin(a) * 26, 12, color, 0.8)
    fr.light(x, y, 40, 280, color, 1.3)


def campfire(fr, x, y, t):
    for i in range(9):
        a = i / 9 * math.tau
        fr.part("sphere", (x + math.cos(a) * 20, y + math.sin(a) * 20, 2.5), (4.5, 0, 0), (0, 0, 3.2), (0, 4.5, 0),
                (116, 112, 108))
    for a in (0.6, 2.2, 3.9):
        d = (math.cos(a) * 13, math.sin(a) * 13, 0)
        Painter(fr).rod(add((x, y, 3), mul(d, -1)), add((x, y, 5), d), 2.6, (104, 68, 36), (0, 0, 1))
    fl = 1 + 0.12 * math.sin(t * 11)
    fr.part("cone", (x, y, 14 * fl), (7, 0, 0), (0, 0, 12 * fl), (0, 7, 0), (255, 150, 40), 1.0)
    fr.part("cone", (x, y, 12 * fl), (4, 0, 0), (0, 0, 9 * fl), (0, 4, 0), (255, 230, 120), 1.0)
    fr.glow(x, y, 16, 60 * fl, (255, 140, 50), 0.7)
    fr.light(x, y, 30, 420 + 20 * math.sin(t * 7), (255, 150, 70), 1.6)


def tent(fr, x, y, color, facing=0.0):
    f, s = frame_axes(facing)
    fr.part("cone", (x, y, 24), mul(f, 30), (0, 0, 24), mul(s, 30), color)
    fr.part("cylinder", (x, y, 50), (1.5, 0, 0), (0, 0, 6), (0, 1.5, 0), (90, 64, 40))
    fr.part("cube", add((x, y, 0), mul(f, 24), (0, 0, 10)), mul(f, 1), (0, 0, 10), mul(s, 7), (40, 30, 26))


def anvil(fr, x, y):
    fr.box(x, y, 0, 7, 7, 6, (74, 62, 52))
    fr.box(x, y, 12, 13, 6, 3.5, (86, 88, 98))
    fr.part("cone", (x + 16, y, 15), (0, 0, 0.1), (5, 0, 0), (0, 3, 0), (86, 88, 98))


def crate(fr, x, y, h=9):
    fr.box(x, y, 0, h, h, h, (156, 114, 64))
    fr.box(x, y, h * 2, h * 0.75, h * 0.75, 0.3, (112, 80, 44))


def barrel(fr, x, y):
    fr.box(x, y, 0, 9, 9, 12, (140, 96, 56), mesh="cylinder")
    fr.box(x, y, 7, 9.6, 9.6, 1, (70, 70, 76), mesh="cylinder")
    fr.box(x, y, 16, 9.6, 9.6, 1, (70, 70, 76), mesh="cylinder")


def trap(fr, x, y, armed, t):
    fr.box(x, y, 0, 12, 12, 1.5, (84, 80, 76), mesh="cylinder")
    for i in range(6):
        a = i / 6 * math.tau
        fr.part("cone", (x + math.cos(a) * 7, y + math.sin(a) * 7, 5), (1.6, 0, 0), (0, 0, 4 + (2 if armed else 0)),
                (0, 1.6, 0), (196, 192, 186))
    if armed and int(t * 3) % 2 == 0:
        fr.glow(x, y, 6, 22, (255, 120, 40), 0.9)


def loot_item(fr, x, y, z, color, t, rarity):
    """Butin au sol : gemme qui tourne, avec faisceau pour les objets rares."""
    a = t * 2
    f, s = frame_axes(a)
    zz = z + 10 + 2.5 * math.sin(t * 3)
    fr.part("sphere", (x, y, zz), mul(f, 4.5), (0, 0, 6.5), mul(s, 4.5), color, 0.55)
    fr.decal(x, y, 16, 16, color, 0.35, kind=4)
    if rarity in ("rare", "legendaire"):
        h = 90 if rarity == "rare" else 150
        fr.part("cylinder", (x, y, h / 2), (3, 0, 0), (0, 0, h / 2), (0, 3, 0), color, 0.5, additive=True)
        fr.light(x, y, 20, 110, color, 0.8)
    fr.glow(x, y, zz, 16, color, 0.6)
