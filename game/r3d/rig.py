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
# autres packs (monstres Quaternius) : noms de remplacement, essayés dans l'ordre si le modèle n'a pas l'animation
FALLBACK = {
    "idle": ("Idle", "Flying_Idle", "Spider_Idle", "Rat_Idle"),
    "idle_melee": ("Idle_Sword", "Idle", "Flying_Idle", "Spider_Idle"),
    "run": ("Run", "Walk", "Fast_Flying", "Spider_Walk", "Rat_Run"),
    "walk": ("Walk", "Run", "Fast_Flying", "Spider_Walk", "Rat_Walk"),
    "attack_melee": ("Sword_Slash", "Sword", "Punch", "Headbutt", "Spider_Attack", "Rat_Attack"),
    "attack_ranged": ("Gun_Shoot", "Punch", "Spider_Attack"),
    "attack_cast": ("Punch_Right", "Punch", "Headbutt", "Spider_Attack"),
    "cast": ("Punch_Left", "Punch", "Headbutt", "Spider_Attack"),
    "hit": ("HitRecieve", "HitReact"),
    "death": ("Death", "Spider_Death", "Rat_Death"),
    "work": ("Sword_Slash", "Sword", "Punch"),
}
ONE_SHOT = {"roll", "attack_melee", "attack_ranged", "attack_cast", "cast", "hit", "death"}
HEIGHT = 50.0          # hauteur d'un héros en unités logiques (un peu plus d'une case)
CLOCK = [0.0]          # horloge de rendu (animations de repos des PNJ et des aperçus)


def model_for(spec):
    r = spec.get("rig")
    return skinned.load(r["model"]) if r else None


def anim_name(model, spec, state):
    """Animation jouée pour un état : choix de la spécification (rig « anims »), nom du pack des héros, puis
    noms équivalents des autres packs (FALLBACK)."""
    forced = spec["rig"].get("anims", {}).get(state)
    if forced in model.anims:
        return forced
    for name in (ANIMS.get(state, "Idle"),) + FALLBACK.get(state, ()) + FALLBACK["idle"]:
        if name in model.anims:
            return name
    return next(iter(model.anims), None)


def anim_duration(spec, state):
    m = model_for(spec)
    return m.duration(anim_name(m, spec, state)) if m else 0.5


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
    anim = anim_name(model, spec, state)
    loop = state not in ONE_SHOT
    joints, world = model.pose(anim, t * spec["rig"].get("speed", 1.0), loop=loop)
    build = spec.get("build", 1.0)
    k = HEIGHT * sc * spec["rig"].get("height", 1.0) * U / model.height
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
        _equipment(fr, M3, model, Mw, world, spec, facing, sc, flash, tint_col, state)
    finally:
        fr.outline = prev
    return True


def _grip_dir(M3, ax, side):
    """Direction d'une arme tenue dans le poing : perpendiculaire aux doigts, un peu inclinée vers l'avant."""
    return M3.norm(M3.add(M3.mul(ax[0], -side), M3.mul(ax[2], 0.4)))


def _to3(v):
    return np.array((v[0], v[2], v[1]), dtype="f4")


def _hold(fr, name, length, grip, ydir, zdir, tint, emis=0.0):
    """Place un objet 3D (assets/models/weapons) : poignée en grip, axe Y selon ydir, face Z selon zdir."""
    prop = skinned.load_prop(name)
    if prop is None:
        return False
    y = _to3(ydir)
    y /= np.linalg.norm(y) or 1.0
    z = _to3(zdir)
    z = z - y * float(np.dot(z, y))
    z /= np.linalg.norm(z) or 1.0
    x = np.cross(y, z)
    k = length * U / prop.length
    M = np.eye(4, dtype="f4")
    M[:3, 0], M[:3, 1], M[:3, 2] = x * k, y * k, z * k
    M[:3, 3] = (grip[0] * U, grip[2] * U, grip[1] * U)
    fr.skin(prop, M, np.eye(4, dtype="f4")[None], prop.palette(), tint, emis)
    return True


def _equipment(fr, M3, model, Mw, world, spec, facing, sc, flash, tint_col, state="idle"):
    """Armes et bouclier (modèles 3D importés) dans les mains, et lueurs magiques."""
    f, s = M3.frame_axes(facing)
    bone = {}
    for name, alt in (("Wrist.R", "Middle1.R"), ("Wrist.L", "Middle1.L")):
        i = model.node(name)
        if i < 0:
            i = model.node(alt)     # packs de monstres : pas d'os de poignet, la main finit aux doigts
        if i >= 0:
            bone[name] = _bone(Mw, world, i)
    tint = (1.0, 1.0, 1.0, 0.65) if flash else ((tint_col[0] / 255, tint_col[1] / 255, tint_col[2] / 255, 0.45)
                                                if tint_col else (0.0, 0.0, 0.0, 0.0))
    held = spec.get("rig", {}).get("weapons", {})
    for side_name, bone_name, side in (("right", "Wrist.R", 1), ("left", "Wrist.L", -1)):
        item = held.get(side_name)
        if not item or bone_name not in bone:
            continue
        name, length = item[0], item[1] * sc
        hand, ax = bone[bone_name]
        grip = M3.add(hand, M3.mul(M3.norm(ax[1]), 2.4 * sc))
        if name.startswith("shield"):
            _hold(fr, name, length, M3.add(grip, M3.mul(f, 2.0 * sc)), (0, 0, 1), f, tint)
            continue
        if name == "bow":
            _hold(fr, name, length, grip, M3.norm(M3.add((0, 0, 1), M3.mul(f, 0.25))), M3.mul(s, side), tint)
            continue
        wdir = _grip_dir(M3, ax, side)
        _hold(fr, name, length, grip, wdir, M3.mul(s, side), tint)
        tip = M3.add(grip, M3.mul(wdir, length * 0.9))
        if spec.get("orb") and name in ("staff", "scythe"):
            fr.glow(tip[0], tip[1], tip[2], 13 * sc, spec["orb"], 0.9)
            fr.light(tip[0], tip[1], tip[2], 120, spec["orb"], 0.7)
        if spec.get("blade") and name.startswith("sword"):
            fr.glow(tip[0], tip[1], tip[2], 12 * sc, spec["blade"], 0.5)
