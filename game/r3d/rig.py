"""Héros et PNJ animés : modèle glTF de Quaternius + équipement de classe dessiné sur les os.

La spécification d'un personnage (looks.hero_spec, models.NPC_SPECS) contient une entrée « rig » :
  model   : nom du fichier dans assets/models/characters (sans .glb)
  palette : {matériau du modèle: (r, g, b)} — teint, cheveux et tenues choisis par le joueur
Les accessoires (arme, bouclier, arc, chapeau, casque, capuche, masque, robe) reprennent les pièces des héros
procéduraux, placées sur les os de la main, de la tête et du bassin à chaque image.
"""
import math

import numpy as np

from . import skinned
from .camera import U

# animations du pack « Ultimate Animated Character » (mêmes noms pour tous les modèles)
ANIMS = {
    "idle": "Idle", "idle_melee": "Idle_Sword", "run": "Run", "walk": "Walk", "roll": "Roll",
    "attack_melee": "Sword_Slash", "attack_ranged": "Gun_Shoot", "attack_cast": "Punch_Right",
    "cast": "Punch_Left", "hit": "HitRecieve", "death": "Death", "work": "Sword_Slash", "wave": "Wave",
}
ONE_SHOT = {"roll", "attack_melee", "attack_ranged", "attack_cast", "cast", "hit", "death"}
HEIGHT = 50.0          # hauteur d'un héros en unités logiques (un peu plus d'une case)
CLOCK = [0.0]          # horloge de rendu (animations de repos des PNJ et des aperçus)


def model_for(spec):
    r = spec.get("rig")
    return skinned.load(r["model"]) if r else None


def anim_duration(spec, state):
    m = model_for(spec)
    return m.duration(ANIMS.get(state, "Idle")) if m else 0.5


def _bone(M, world, i):
    """Position (logique) et axes (logiques) d'un nœud du squelette."""
    w = M @ world[i]
    o = w[:3, 3]
    ax = [w[:3, k] / (np.linalg.norm(w[:3, k]) or 1.0) for k in range(3)]
    pos = (float(o[0]) / U, float(o[2]) / U, float(o[1]) / U)
    to_logic = [(float(a[0]), float(a[2]), float(a[1])) for a in ax]
    return pos, to_logic


def draw(fr, x, y, z0, facing, spec, state, t, sc=1.0, flash=False, tint_col=None):
    """Dessine le personnage animé ; renvoie False si le modèle manque (repli procédural)."""
    from . import models as M3
    model = model_for(spec)
    if model is None:
        return False
    anim = ANIMS.get(state, "Idle")
    loop = state not in ONE_SHOT
    joints, world = model.pose(anim, t, loop=loop)
    build = spec.get("build", 1.0)
    k = HEIGHT * sc * U / model.height
    th = math.pi / 2 - facing           # le modèle regarde vers +Z : on l'aligne sur l'orientation logique
    c, s = math.cos(th), math.sin(th)
    R = np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], dtype="f4")
    S = np.diag([k * build, k, k * build, 1.0]).astype("f4")
    T = np.eye(4, dtype="f4")
    T[:3, 3] = (x * U, z0 * U - model.floor * k, y * U)
    Mw = T @ R @ S
    pal = model.palette(spec["rig"].get("palette", {}))
    if flash:
        tint = (1.0, 1.0, 1.0, 0.65)
    elif tint_col:
        tint = (tint_col[0] / 255, tint_col[1] / 255, tint_col[2] / 255, 0.45)
    else:
        tint = (0.0, 0.0, 0.0, 0.0)
    fr.skin(model, Mw, joints, pal, tint, 0.6 if flash else 0.0)
    # ---------------------------------------------------------------- équipement sur les os
    prev = getattr(fr, "outline", False)
    fr.outline = True
    try:
        _equipment(fr, M3, model, Mw, world, spec, facing, sc, flash, tint_col)
    finally:
        fr.outline = prev
    return True


def _grip_dir(M3, ax, side):
    """Direction d'une arme tenue dans le poing : perpendiculaire aux doigts, un peu inclinée vers l'avant."""
    return M3.norm(M3.add(M3.mul(ax[0], -side), M3.mul(ax[2], 0.4)))


def _equipment(fr, M3, model, Mw, world, spec, facing, sc, flash, tint_col):
    p = M3.Painter(fr, flash, tint_col)
    f, s = M3.frame_axes(facing)
    bone = {}
    for name in ("Head", "Head_end", "Wrist.R", "Wrist.L", "Hips", "Fist.R", "Fist.L"):
        i = model.node(name)
        if i >= 0:
            bone[name] = _bone(Mw, world, i)
    head, head_ax = bone["Head"]
    top = bone.get("Head_end", bone["Head"])[0]
    hr = max(3.0, math.dist(head, top) * 0.42)
    up = M3.norm(M3.add(top, M3.mul(head, -1)))
    hc = M3.add(head, M3.mul(up, hr * 0.95))
    if spec.get("helmet"):
        p.ellipsoid(M3.add(hc, M3.mul(up, hr * 0.3)), f, s, hr * 1.4, hr * 1.4, hr * 1.05, spec["helmet"])
        p.part("cylinder", M3.add(hc, M3.mul(up, -hr * 0.05)), M3.mul(f, hr * 1.42), M3.mul(up, 0.6 * sc),
               M3.mul(s, hr * 1.42), M3.tint(spec["helmet"], (60, 50, 40), 0.35))
    if spec.get("horns"):
        for side in (-1, 1):
            hb = M3.add(hc, M3.mul(s, side * hr * 0.85), M3.mul(up, hr * 0.45))
            mid = M3.add(hb, M3.mul(s, side * 3.0 * sc), M3.mul(up, 1.8 * sc))
            p.rod(hb, mid, 1.4 * sc, spec["horns"], f)
            p.rod(mid, M3.add(mid, M3.mul(s, side * 1.3 * sc), M3.mul(up, 4.4 * sc)), 1.4 * sc, spec["horns"], f,
                  mesh="cone")
    if spec.get("hat"):
        h = spec["hat"]
        p.part("cylinder", M3.add(hc, M3.mul(up, hr * 0.75)), M3.mul(f, 8.5 * sc), M3.mul(up, 0.7 * sc),
               M3.mul(s, 8.5 * sc), h)
        p.part("cylinder", M3.add(hc, M3.mul(up, hr * 0.95)), M3.mul(f, 5.0 * sc), M3.mul(up, 0.8 * sc),
               M3.mul(s, 5.0 * sc), spec.get("trim", h))
        p.rod(M3.add(hc, M3.mul(up, hr * 0.8)), M3.add(hc, M3.mul(f, -5 * sc), M3.mul(up, hr + 13 * sc)), 4.8 * sc, h,
              s, mesh="cone")
    if spec.get("hood"):
        p.ellipsoid(M3.add(hc, M3.mul(f, -0.8 * sc), M3.mul(up, hr * 0.15)), f, s, hr * 1.08, hr * 1.1, hr * 1.08,
                    spec["hood"])
        p.rod(M3.add(hc, M3.mul(f, -4 * sc), M3.mul(up, hr * 0.6)), M3.add(hc, M3.mul(f, -10 * sc), M3.mul(up, hr)),
              3.2 * sc, spec["hood"], s, mesh="cone")
    if spec.get("mask"):
        p.ellipsoid(M3.add(hc, M3.mul(f, hr * 0.62), M3.mul(up, -hr * 0.35)), f, s, hr * 0.55, hr * 0.92, hr * 0.5,
                    spec["mask"])
    if spec.get("robe") and "Hips" in bone:
        hips = bone["Hips"][0]
        hz = max(6.0, hips[2] + 3 * sc)
        base = (hips[0], hips[1], 0.0)
        p.part("frustum", M3.add(base, (0, 0, hz / 2)), M3.mul(f, 9.0 * sc), (0, 0, hz / 2), M3.mul(s, 9.4 * sc),
               spec["body"])
        if spec.get("trim"):
            p.part("frustum", M3.add(base, (0, 0, 1.2 * sc)), M3.mul(f, 9.2 * sc), (0, 0, 1.2 * sc),
                   M3.mul(s, 9.6 * sc), spec["trim"])
    kind = spec.get("weapon")
    if "Wrist.R" in bone:
        hand, ax = bone["Wrist.R"]
        grip = M3.add(hand, M3.mul(M3.norm(ax[1]), 2.5 * sc))
        wdir = _grip_dir(M3, ax, 1)
        if kind and kind != "bow":
            M3._weapon(p, fr, spec, grip, f, s, wdir, sc)
    if "Wrist.L" in bone:
        hand, ax = bone["Wrist.L"]
        grip = M3.add(hand, M3.mul(M3.norm(ax[1]), 2.5 * sc))
        if kind == "bow":
            M3._bow(p, grip, f, s, sc)
        if spec.get("shield"):
            M3._shield(p, spec, grip, f, s, sc)
        if kind == "daggers":
            M3._weapon(p, fr, dict(weapon="dagger"), grip, f, s, _grip_dir(M3, ax, -1), sc)
