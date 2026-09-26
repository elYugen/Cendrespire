"""Attaques de base et sorts des trois classes."""
import math

from . import sfx
from .data import SPELLS
from .entities import Projectile
from .fx import Blast, RingFX, SwingFX, Zone, Trap


def basic_attack(world):
    p = world.player
    a = p.cls["attack"]
    if p.atk_cd > 0 or p.leap or p.dash:
        return
    p.atk_cd = a["cd"] / (1 + p.stats["atk_speed"] / 100)
    ax, ay = world.aim_point()
    ang = math.atan2(ay - p.y, ax - p.x)
    p.facing = ang
    if a["kind"] == "melee":
        p.swing = -1.4
        world.effects.append(SwingFX(p, ang, math.radians(a["arc"]), a["range"] + 18, a["color"]))
        sfx.play("swing", 0.5)
        hits = 0
        for m in list(world.monsters):
            if m.dead or not m.targetable:
                continue
            dx, dy = m.x - p.x, m.y - p.y
            d = math.hypot(dx, dy)
            if d > a["range"] + m.r:
                continue
            diff = abs((math.atan2(dy, dx) - ang + math.pi) % math.tau - math.pi)
            if diff <= math.radians(a["arc"]) / 2 or d < m.r + p.r:
                world.player_hit(m, a["mult"], knock=25, ang=math.atan2(dy, dx))
                hits += 1
        if hits:
            p.mana = min(p.stats["max_mana"], p.mana + a.get("mana_gain", 0) * min(3, hits))
            sfx.play("hit", 0.6)
    else:
        world.projectiles.append(Projectile(p.x + math.cos(ang) * 10, p.y + math.sin(ang) * 10, ang, a["speed"],
                                            "player", a["color"], mult=a["mult"], radius=a.get("radius", 6),
                                            life=a.get("life", 1.0), kind="arrow" if a.get("arrow") else "bolt"))
        sfx.play("arrow" if a.get("arrow") else "magic", 0.35)


def cast(world, sid):
    p = world.player
    sp = SPELLS[sid]
    if p.leap or p.dash or p.dead:
        return
    if not p.spell_unlocked(sid):
        world.add_text(p.x, p.y, 64, f"{sp['name']} : niveau {sp['level']} requis", (200, 200, 200), 15)
        return
    if p.cds.get(sid, 0) > 0:
        return
    if p.mana < sp["mana"]:
        world.add_text(p.x, p.y, 64, "Pas assez de mana", (110, 150, 255), 16)
        return
    tx, ty = world.ground_point() if sid in GROUND_TARGETED else world.aim_point()
    if CASTS[sid](world, p, sp, tx, ty) is False:
        return
    p.mana -= sp["mana"]
    cd = sp["cd"] * (1 - p.stats["cdr"] / 100)
    p.cds[sid] = cd
    p.cd_total[sid] = cd


def _clamp_target(p, tx, ty, max_d):
    dx, dy = tx - p.x, ty - p.y
    d = math.hypot(dx, dy)
    if d > max_d:
        tx, ty = p.x + dx / d * max_d, p.y + dy / d * max_d
    return tx, ty


# --------------------------------------------------------------------------- barbare
def _tourbillon(world, p, sp, tx, ty):
    world.damage_circle(p.x, p.y, 110, sp["mult"], knock=70)
    world.effects.append(RingFX(p.x, p.y, 30, 125, 0.3, sp["color"], 8))
    world.effects.append(SwingFX(p, p.facing, math.tau, 120, (240, 200, 160), 0.25))
    world.particles.emit(p.x, p.y, sp["color"], n=22, speed=260, life=0.35, size=3, z=20)
    p.swing = 3.0
    sfx.play("swing")


def _cri(world, p, sp, tx, ty):
    p.buffs["cri"] = 8.0
    world.effects.append(RingFX(p.x, p.y, 20, 200, 0.5, sp["color"], 6))
    world.particles.emit(p.x, p.y, sp["color"], n=30, speed=200, life=0.6, size=4, z=30)
    world.add_text(p.x, p.y, 70, "Cri de guerre !", (255, 90, 60), 20)
    world.shake_screen(5)
    sfx.play("roar", 0.6)


def _bond(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 330)
    ex, ey = world.reachable(p.x, p.y, tx, ty, p.r)

    def land(w):
        w.effects.append(Blast(p.x, p.y, 115, 0, sp["mult"], sp["color"], stun=1.2, knock=90))
    p.leap = {"sx": p.x, "sy": p.y, "ex": ex, "ey": ey, "t": 0.0, "dur": 0.42, "on_land": land}
    sfx.play("swing")


def _seisme(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    for i in range(6):
        d = 60 + i * 58
        x, y = p.x + math.cos(ang) * d, p.y + math.sin(ang) * d
        if world.solid_at(x, y):
            break
        world.effects.append(Blast(x, y, 62, 0.08 + i * 0.09, sp["mult"], sp["color"], knock=40,
                                   sound="hit" if i % 2 else "explosion"))


# --------------------------------------------------------------------------- sorcier
def _boule_feu(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    world.projectiles.append(Projectile(p.x, p.y, ang, 520, "player", sp["color"], mult=sp["mult"], radius=9,
                                        life=1.1, kind="fire", explode=75))
    sfx.play("fire", 0.6)


def _nova(world, p, sp, tx, ty):
    world.damage_circle(p.x, p.y, 200, sp["mult"], slow=3.0)
    world.effects.append(RingFX(p.x, p.y, 20, 210, 0.45, sp["color"], 10))
    for i in range(36):
        a = i / 36 * math.tau
        world.particles.emit(p.x + math.cos(a) * 30, p.y + math.sin(a) * 30, (190, 235, 255), n=1, speed=400,
                             angle=a, spread=0.1, life=0.45, size=4, drag=3, z=12, zs=0.05)
    sfx.play("ice")


def _teleport(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 380)
    ex, ey = world.reachable(p.x, p.y, tx, ty, p.r)
    if math.hypot(ex - p.x, ey - p.y) < 20:
        return False
    world.particles.emit(p.x, p.y, sp["color"], n=26, speed=160, life=0.5, size=4, z=25)
    p.x, p.y = ex, ey
    p.invuln = 0.25
    world.particles.emit(p.x, p.y, sp["color"], n=26, speed=160, life=0.5, size=4, z=25)
    world.effects.append(Blast(p.x, p.y, 90, 0, sp["mult"], sp["color"], knock=80, sound="magic"))


def _meteore(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 520)

    def burn(w):
        w.effects.append(Zone(tx, ty, 95, 3.0, 0.5, 0.35, "fire", (255, 110, 30)))
    world.effects.append(Blast(tx, ty, 120, 0.9, sp["mult"], sp["color"], knock=80, kind="meteor", on_done=burn))
    sfx.play("fire")


# --------------------------------------------------------------------------- chasseur
def _tir_multiple(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    for i in range(7):
        a = ang + (i - 3) * math.radians(9)
        world.projectiles.append(Projectile(p.x, p.y, a, 760, "player", sp["color"], mult=sp["mult"], radius=5,
                                            life=0.6, kind="arrow"))
    sfx.play("arrow")


def _piege(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 300)
    tx, ty = world.reachable(p.x, p.y, tx, ty, 8)
    world.effects.append(Trap(tx, ty, sp["mult"], sp["color"]))
    sfx.play("click")


def _fleche_perforante(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    world.projectiles.append(Projectile(p.x, p.y, ang, 900, "player", sp["color"], mult=sp["mult"], radius=9,
                                        life=0.9, kind="bolt", pierce=99, knock=40))
    sfx.play("arrow")


def _pluie(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 480)
    world.effects.append(Zone(tx, ty, 130, 3.0, 0.25, sp["mult"], "arrows", sp["color"]))
    sfx.play("arrow")


CASTS = {
    "tourbillon": _tourbillon, "cri_guerre": _cri, "bond": _bond, "seisme": _seisme,
    "boule_feu": _boule_feu, "nova_givre": _nova, "teleport": _teleport, "meteore": _meteore,
    "tir_multiple": _tir_multiple, "piege": _piege, "fleche_perforante": _fleche_perforante, "pluie_fleches": _pluie,
}
GROUND_TARGETED = {"bond", "teleport", "meteore", "piege", "pluie_fleches"}
