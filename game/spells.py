"""Attaques de base et sorts des six classes (les talents modifient dégâts, recharges et coût)."""
import math
import random

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
                world.player_hit(m, a["mult"] * (1 + p.t("basic_pct") / 100), knock=25, ang=math.atan2(dy, dx))
                if "venin" in p.buffs and not m.dead:
                    poison(p, m)
                hits += 1
        if hits:
            p.mana = min(p.stats["max_mana"], p.mana + a.get("mana_gain", 0) * min(3, hits))
            sfx.play("hit", 0.6)
    else:
        world.projectiles.append(Projectile(p.x + math.cos(ang) * 10, p.y + math.sin(ang) * 10, ang, a["speed"],
                                            "player", a["color"], mult=a["mult"] * (1 + p.t("basic_pct") / 100),
                                            radius=a.get("radius", 6),
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
    # talents : +% dégâts du sort (et de tous les sorts), -% recharge du sort
    bonus = p.t("spell_pct") + p.t("sd:" + sid)
    sp = dict(sp, mult=sp["mult"] * (1 + bonus / 100))
    if CASTS[sid](world, p, sp, tx, ty) is False:
        return
    if random.random() * 100 < p.t("free_cast"):
        world.add_text(p.x, p.y, 70, "Surcharge !", (190, 150, 255), 15)
    else:
        p.mana -= sp["mana"]
    if p.t("heal_on_spell"):
        p.heal(p.stats["max_hp"] * p.t("heal_on_spell") / 100)
    cd = sp["cd"] * (1 - p.stats["cdr"] / 100) * (1 - p.t("sc:" + sid) / 100)
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


# --------------------------------------------------------------------------- paladin
def _charge_bouclier(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    ex, ey = world.reachable(p.x, p.y, p.x + math.cos(ang) * 230, p.y + math.sin(ang) * 230, p.r)

    def impact(w):
        w.effects.append(Blast(p.x, p.y, 85, 0, sp["mult"], sp["color"], stun=0.9, knock=110, sound="hit"))
    p.dash = {"sx": p.x, "sy": p.y, "ex": ex, "ey": ey, "t": 0.0, "dur": 0.2, "on_end": impact}
    p.facing = ang
    p.invuln = 0.25
    world.particles.emit(p.x, p.y, sp["color"], n=14, speed=90, life=0.4, size=3, z=20)
    sfx.play("swing")


def _consecration(world, p, sp, tx, ty):
    world.effects.append(Zone(p.x, p.y, 130, 5.0, 0.5, sp["mult"], "holy", sp["color"]))
    world.effects.append(RingFX(p.x, p.y, 20, 140, 0.4, sp["color"], 6))
    sfx.play("seal", 0.6)


def _egide(world, p, sp, tx, ty):
    p.buffs["egide"] = 6.0
    amt = p.stats["max_hp"] * 0.2
    p.heal(amt)
    world.add_text(p.x, p.y, 70, f"+{int(amt)}", (120, 240, 120), 18)
    world.effects.append(RingFX(p.x, p.y, 60, 10, 0.4, sp["color"], 6))
    world.particles.emit(p.x, p.y, sp["color"], n=30, speed=90, life=0.8, size=3, up=120, z=10)
    sfx.play("levelup", 0.5)


def _jugement(world, p, sp, tx, ty):
    from .fx import Lightning
    tx, ty = _clamp_target(p, tx, ty, 480)
    ms = [m for m in world.monsters if not m.dead and m.targetable and math.hypot(m.x - tx, m.y - ty) < 220 + m.r]
    ms.sort(key=lambda m: math.hypot(m.x - tx, m.y - ty))
    if not ms:
        world.add_text(p.x, p.y, 64, "Aucune cible", (200, 200, 200), 15)
        return False
    for i, m in enumerate(ms[:6]):
        def strike(w, m=m):
            if m.dead:
                return
            w.effects.append(Lightning(m.x, m.y, sp["color"], 0.35))
            w.player_hit(m, sp["mult"], stun=0.5)
            w.particles.emit(m.x, m.y, sp["color"], n=12, speed=120, life=0.5, size=4, up=150, z=10)
        world.schedule(i * 0.08, strike)
    world.shake_screen(5)
    sfx.play("explosion", 0.6)


# --------------------------------------------------------------------------- nécromancien
def _lance_os(world, p, sp, tx, ty):
    ang = math.atan2(ty - p.y, tx - p.x)
    world.projectiles.append(Projectile(p.x, p.y, ang, 780, "player", sp["color"], mult=sp["mult"], radius=8,
                                        life=0.9, kind="bolt", pierce=99, knock=30))
    sfx.play("arrow")


def _squelettes(world, p, sp, tx, ty):
    from .allies import SkeletonMinion
    n = 2 + int(p.t("extra_summon"))
    cap = 4 + int(p.t("extra_summon"))
    mult = sp["mult"] * (1 + p.t("summon_pct") / 100)
    for i in range(n):
        a = p.facing + (i - (n - 1) / 2) * 0.9
        x, y = world.reachable(p.x, p.y, p.x + math.cos(a) * 60, p.y + math.sin(a) * 60, 13)
        world.allies.append(SkeletonMinion(x, y, mult))
        world.particles.emit(x, y, sp["color"], n=16, speed=70, life=0.6, size=3, up=140, z=5)
    skel = [a for a in world.allies if a.__class__.__name__ == "SkeletonMinion"]
    for old in skel[:-cap] if len(skel) > cap else []:
        old.life = 0
    sfx.play("magic")


def _malediction(world, p, sp, tx, ty):
    tx, ty = _clamp_target(p, tx, ty, 420)
    amp = 0.3 + p.t("curse_amp") / 100
    for m in world.monsters:
        if not m.dead and m.targetable and math.hypot(m.x - tx, m.y - ty) < 150 + m.r:
            m.curse = 6.0
            m.curse_amp = amp
            m.slow = max(m.slow, 3.0 if not m.boss else 1.5)
    world.effects.append(RingFX(tx, ty, 150, 20, 0.5, sp["color"], 8))
    world.particles.emit(tx, ty, sp["color"], n=40, speed=160, life=0.8, size=4, up=60, z=5)
    sfx.play("ice", 0.5)


def _moisson(world, p, sp, tx, ty):
    n = 0
    for m in list(world.monsters):
        if not m.dead and m.targetable and math.hypot(m.x - p.x, m.y - p.y) < 220 + m.r:
            world.player_hit(m, sp["mult"])
            n += 1
            for _ in range(3):
                world.particles.emit(m.x, m.y, sp["color"], n=1, speed=0, life=0.5, size=4, z=30,
                                     up=60)
    if n:
        amt = p.stats["max_hp"] * 0.04 * n
        p.heal(amt)
        world.add_text(p.x, p.y, 70, f"+{int(amt)}", (120, 240, 140), 18)
    world.effects.append(RingFX(p.x, p.y, 230, 20, 0.5, sp["color"], 8))
    sfx.play("magic")


# --------------------------------------------------------------------------- assassin
def poison(p, m):
    m.burn = 4.0
    m.burn_dps = p.roll_damage(0.4)[0] * (1 + p.t("dot_pct") / 100)
    m.burn_col = (120, 230, 90)


def _pas_ombre(world, p, sp, tx, ty):
    ms = [m for m in world.monsters if not m.dead and m.targetable and math.hypot(m.x - p.x, m.y - p.y) < 420]
    if not ms:
        world.add_text(p.x, p.y, 64, "Aucune cible", (200, 200, 200), 15)
        return False
    m = min(ms, key=lambda m: math.hypot(m.x - tx, m.y - ty))
    a = math.atan2(m.y - p.y, m.x - p.x)
    bx, by = m.x + math.cos(a) * (m.r + p.r + 6), m.y + math.sin(a) * (m.r + p.r + 6)
    if world.blocked(bx, by, p.r):
        bx, by = world.reachable(p.x, p.y, m.x, m.y, p.r)
    world.particles.emit(p.x, p.y, sp["color"], n=20, speed=120, life=0.5, size=4, z=25)
    p.x, p.y = bx, by
    p.facing = math.atan2(m.y - p.y, m.x - p.x)
    p.swing = -1.4
    p.invuln = 0.2
    world.player_hit(m, sp["mult"], crit_bonus=50)
    if "venin" in p.buffs and not m.dead:
        poison(p, m)
    world.particles.emit(p.x, p.y, sp["color"], n=20, speed=120, life=0.5, size=4, z=25)
    sfx.play("hit")


def _eventail(world, p, sp, tx, ty):
    for i in range(12):
        a = i / 12 * math.tau + p.facing
        world.projectiles.append(Projectile(p.x, p.y, a, 700, "player", sp["color"], mult=sp["mult"], radius=5,
                                            life=0.45, kind="arrow"))
    sfx.play("swing")


def _venin(world, p, sp, tx, ty):
    p.buffs["venin"] = 8.0
    world.particles.emit(p.x, p.y, sp["color"], n=24, speed=70, life=0.7, size=3, up=90, z=10)
    sfx.play("potion", 0.5)


def _danse(world, p, sp, tx, ty):
    p.invuln = 0.75
    for i in range(6):
        def strike(w, i=i):
            a = i * math.tau / 6 + p.facing
            w.effects.append(SwingFX(p, a, math.radians(160), 110, sp["color"], 0.14))
            w.damage_circle(p.x, p.y, 105, sp["mult"], knock=20)
            p.swing = -1.4
            p.facing = a
            sfx.play("swing", 0.4)
        world.schedule(i * 0.11, strike)


CASTS = {
    "tourbillon": _tourbillon, "cri_guerre": _cri, "bond": _bond, "seisme": _seisme,
    "boule_feu": _boule_feu, "nova_givre": _nova, "teleport": _teleport, "meteore": _meteore,
    "tir_multiple": _tir_multiple, "piege": _piege, "fleche_perforante": _fleche_perforante, "pluie_fleches": _pluie,
    "charge_bouclier": _charge_bouclier, "consecration": _consecration, "egide": _egide, "jugement": _jugement,
    "lance_os": _lance_os, "squelettes": _squelettes, "malediction": _malediction, "moisson": _moisson,
    "pas_ombre": _pas_ombre, "eventail": _eventail, "venin": _venin, "danse_lames": _danse,
}
GROUND_TARGETED = {"bond", "teleport", "meteore", "piege", "pluie_fleches", "jugement", "malediction"}
