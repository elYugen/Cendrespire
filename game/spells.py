"""Attaque de base, lancement des sorts et interpréteur d'effets.

Les sorts (data/spells.json) et les artefacts (data/artifacts.json) ne sont pas codés un par un : ils sont décrits
par une liste d'effets génériques exécutés ici. Pour ajouter un sort, il suffit de l'écrire dans le JSON.

Paramètres communs à tous les effets :
  mult      multiplicateur relatif au « mult » du sort (1 par défaut)
  mult_abs  multiplicateur absolu des dégâts d'arme (ignore le mult du sort) ; "v" / "v%" pour un artefact
  color     couleur (par défaut celle du sort)
  at        "self" (le héros) ou "target" (le point visé) ; range limite la distance du point visé
  sound     son joué au déclenchement
  then      effets déclenchés ensuite (à l'atterrissage, à l'arrivée, à l'explosion...)
"""
import math
import random

from . import sfx
from .data import SPELLS
from .entities import Projectile
from .fx import Blast, RingFX, SwingFX, Zone, Trap, Lightning


# =========================================================================== attaque de base
MIN_ATTACK_CD = 0.32      # plancher de recharge : impossible de « mitrailler » l'attaque de base


def basic_attack(world, target=None):
    p = world.player
    a = p.cls["attack"]
    if p.atk_cd > 0 or p.leap or p.dash:
        return
    cd = max(MIN_ATTACK_CD, a["cd"] / (1 + (p.stats["atk_speed"] + p.buff_sum("atk_speed")) / 100))
    p.atk_cd = p.atk_total = cd
    p.attack_lock = min(0.22, cd * 0.45)      # le héros s'arrête le temps de porter le coup
    kind = "attack_melee" if a["kind"] == "melee" else ("attack_ranged" if a.get("arrow") else "attack_cast")
    p.play(kind, min(0.55, cd * 0.95))
    ax, ay = target if target else world.aim_point()
    ang = math.atan2(ay - p.y, ax - p.x)
    p.facing = ang
    mult = a["mult"] * (1 + p.stats["basic_pct"] / 100)
    if a["kind"] == "melee":
        p.swing = -1.4
        world.effects.append(SwingFX(p, ang, math.radians(a["arc"]), a["range"] + 18, a.get("color", p.cls["color"])))
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
                world.player_hit(m, mult, knock=25, ang=math.atan2(dy, dx))
                apply_poison(p, m)
                hits += 1
        if hits:
            p.mana = min(p.stats["max_mana"], p.mana + a.get("mana_gain", 0) * min(3, hits))
            sfx.play("hit", 0.6)
    else:
        world.projectiles.append(Projectile(p.x + math.cos(ang) * 10, p.y + math.sin(ang) * 10, ang, a["speed"],
                                            "player", a["color"], mult=mult, radius=a.get("radius", 6),
                                            life=a.get("life", 1.0), kind="arrow" if a.get("arrow") else "bolt"))
        sfx.play("arrow" if a.get("arrow") else "magic", 0.35)


def apply_poison(p, m):
    """Les effets temporaires « poison » (ex. Lames empoisonnées) empoisonnent les cibles touchées."""
    frac = p.buff_sum("poison")
    if frac and not m.dead:
        m.burn = 4.0
        m.burn_dps = p.roll_damage(frac)[0] * (1 + p.t("dot_pct") / 100)
        m.burn_col = (120, 230, 90)


# =========================================================================== sorts
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
    if p.mana < p.mana_cost(sid):
        world.add_text(p.x, p.y, 64, "Pas assez de mana", (110, 150, 255), 16)
        return
    tx, ty = world.ground_point() if sp.get("target") == "ground" else world.aim_point()
    if sp.get("range"):
        tx, ty = clamp_target(p, tx, ty, sp["range"])
    facing = p.facing
    p.facing = math.atan2(ty - p.y, tx - p.x)
    # talents : +% dégâts du sort (et de tous les sorts), -% recharge du sort
    mult = sp["mult"] * (1 + (p.stats["spell_pct"] + p.t("sd:" + sid)) / 100)
    ctx = Ctx(world, tx, ty, mult, sp["color"], spell=sid)
    if run(sp["effects"], ctx) is False:
        p.facing = facing
        return
    p.attack_lock = max(p.attack_lock, 0.14)
    p.play("cast", 0.45)
    if random.random() * 100 < p.t("free_cast"):
        world.add_text(p.x, p.y, 70, "Surcharge !", (190, 150, 255), 15)
    else:
        p.mana -= p.mana_cost(sid)
    if p.t("heal_on_spell"):
        p.heal(p.stats["max_hp"] * p.t("heal_on_spell") / 100)
    cd = sp["cd"] * (1 - p.stats["cdr"] / 100) * (1 - p.t("sc:" + sid) / 100)
    p.cds[sid] = cd
    p.cd_total[sid] = cd


def clamp_target(p, tx, ty, max_d):
    dx, dy = tx - p.x, ty - p.y
    d = math.hypot(dx, dy)
    if d > max_d:
        tx, ty = p.x + dx / d * max_d, p.y + dy / d * max_d
    return tx, ty


# =========================================================================== interpréteur d'effets
class Ctx:
    def __init__(self, world, tx, ty, mult=1.0, color=(255, 255, 255), value=0.0, spell=None):
        self.world, self.tx, self.ty, self.mult, self.color = world, tx, ty, mult, tuple(color)
        self.value = value
        self.spell = spell

    def at(self, x, y):
        return Ctx(self.world, x, y, self.mult, self.color, self.value, self.spell)

    @property
    def p(self):
        return self.world.player


def num(ctx, v):
    if v == "v":
        return ctx.value
    if v == "v%":
        return ctx.value / 100
    return float(v)


def mult_of(e, ctx):
    if "mult_abs" in e:
        return num(ctx, e["mult_abs"])
    return ctx.mult * num(ctx, e.get("mult", 1))


def point(e, ctx, default="target"):
    p = ctx.p
    if e.get("at", default) == "self":
        return p.x, p.y
    x, y = ctx.tx, ctx.ty
    if e.get("range"):
        x, y = clamp_target(p, x, y, e["range"])
    return x, y


def near(world, x, y, r, n=99):
    ms = [m for m in world.monsters if not m.dead and m.targetable and math.hypot(m.x - x, m.y - y) < r + m.r]
    ms.sort(key=lambda m: math.hypot(m.x - x, m.y - y))
    return ms[:n]


def run(effects, ctx):
    """Exécute une liste d'effets ; renvoie False si le premier effet n'a pas pu se déclencher (pas de cible...)."""
    for i, e in enumerate(effects):
        col = tuple(e.get("color", ctx.color))
        ok = HANDLERS[e["type"]](e, ctx, col)
        if ok is False:
            if i == 0:
                if e.get("fail_text"):
                    ctx.world.add_text(ctx.p.x, ctx.p.y, 64, e["fail_text"], (200, 200, 200), 15)
                return False
            continue
        if e.get("sound"):
            sfx.play(e["sound"], e.get("volume", 0.8))
    return True


def _then(e, ctx, x=None, y=None):
    if e.get("then"):
        sub = ctx if x is None else ctx.at(x, y)
        return lambda w: run(e["then"], sub)
    return None


def fx_projectile(e, ctx, col):
    w, p = ctx.world, ctx.p
    ang = math.atan2(ctx.ty - p.y, ctx.tx - p.x)
    if e.get("radial"):
        angles = [p.facing + i * math.tau / e["radial"] for i in range(int(e["radial"]))]
    else:
        n = int(e.get("count", 1))
        spread = math.radians(e.get("spread", 0))
        angles = [ang + (i - (n - 1) / 2) * spread for i in range(n)]
    for a in angles:
        w.projectiles.append(Projectile(p.x, p.y, a, e.get("speed", 600), "player", col, mult=mult_of(e, ctx),
                                        radius=e.get("radius", 6), life=e.get("life", 1.0),
                                        pierce=int(e.get("pierce", 0)), kind=e.get("kind", "bolt"),
                                        explode=e.get("explode", 0), slow=e.get("slow", 0),
                                        knock=e.get("knock", 0)))


def fx_nova(e, ctx, col):
    w, p = ctx.world, ctx.p
    x, y = point(e, ctx, "self")
    r = e["radius"]
    hits = 0
    for m in list(w.monsters):
        if m.dead or not m.targetable or math.hypot(m.x - x, m.y - y) > r + m.r:
            continue
        a = math.atan2(m.y - y, m.x - x)
        stun = e.get("stun", 0) if not m.boss else 0
        if e.get("damage", True):
            w.player_hit(m, mult_of(e, ctx), e.get("knock", 0), a, stun, e.get("slow", 0))
        else:
            w.damage_monster(m, 1, False, knock=e.get("knock", 0), ang=a, stun=stun, slow=e.get("slow", 0),
                             quiet=True)
        hits += 1
    if e.get("heal_per_hit") and hits:
        amt = p.stats["max_hp"] * e["heal_per_hit"] / 100 * hits
        p.heal(amt)
        w.add_text(p.x, p.y, 70, f"+{int(amt)}", (120, 240, 140), 18)
    rc = tuple(e.get("ring_color", col))
    style = e.get("style")
    if style == "souls":
        w.effects.append(RingFX(x, y, r + 10, 20, 0.5, rc, 8))
    else:
        w.effects.append(RingFX(x, y, 20, r + 10, 0.4, rc, 10 if style == "frost" else 8))
    if e.get("spin"):
        w.effects.append(SwingFX(p, p.facing, math.tau, r + 10, (240, 200, 160), 0.25))
        p.swing = 3.0
    if style == "frost":
        for i in range(36):
            a = i / 36 * math.tau
            w.particles.emit(x + math.cos(a) * 30, y + math.sin(a) * 30, (190, 235, 255), n=1, speed=r * 2,
                             angle=a, spread=0.1, life=0.45, size=4, drag=3, z=12, zs=0.05)
    else:
        w.particles.emit(x, y, col, n=22, speed=r * 2.2, life=0.4, size=3, z=20, up=60 if style == "souls" else 0)
    if e.get("shake"):
        w.shake_screen(e["shake"])


def fx_blast(e, ctx, col):
    w = ctx.world
    x, y = point(e, ctx, "target")
    w.effects.append(Blast(x, y, e["radius"], e.get("delay", 0), mult_of(e, ctx), col, stun=e.get("stun", 0),
                           slow=e.get("slow", 0), knock=e.get("knock", 0), kind=e.get("style"),
                           sound=e.get("blast_sound", "explosion"), on_done=_then(e, ctx, x, y)))


def fx_line(e, ctx, col):
    w, p = ctx.world, ctx.p
    ang = math.atan2(ctx.ty - p.y, ctx.tx - p.x)
    for i in range(int(e["count"])):
        d = e.get("start", 60) + i * e.get("spacing", 58)
        x, y = p.x + math.cos(ang) * d, p.y + math.sin(ang) * d
        if w.solid_at(x, y):
            break
        w.effects.append(Blast(x, y, e["radius"], e.get("delay", 0.08) + i * e.get("delay_step", 0.09),
                               mult_of(e, ctx), col, knock=e.get("knock", 0), stun=e.get("stun", 0),
                               sound="hit" if i % 2 else "explosion"))


def fx_zone(e, ctx, col):
    x, y = point(e, ctx, "target")
    ctx.world.effects.append(Zone(x, y, e["radius"], e.get("duration", 3.0), e.get("tick", 0.5), mult_of(e, ctx),
                                  e.get("kind", "fire"), col))
    if e.get("kind") in ("holy", "heal"):
        ctx.world.effects.append(RingFX(x, y, 20, e["radius"] + 10, 0.4, col, 6))


def fx_buff(e, ctx, col):
    p = ctx.p
    p.buffs[e["id"]] = e.get("duration", 5)
    p.buffs_total[e["id"]] = p.buffs[e["id"]]          # durée complète (voile de recharge du HUD)
    if "value" in e:
        p.buffs_val[e["id"]] = num(ctx, e["value"])


def fx_heal(e, ctx, col):
    p = ctx.p
    amt = p.stats["max_hp"] * num(ctx, e["pct"]) / 100
    p.heal(amt)
    ctx.world.add_text(p.x, p.y, 70, f"+{int(amt)}", (120, 240, 120), 18)


def fx_restore_mana(e, ctx, col):
    p = ctx.p
    if p.mana >= p.stats["max_mana"]:
        ctx.world.add_text(p.x, p.y, 64, "Mana au maximum", (140, 170, 255), 15)
        return False
    p.mana = min(p.stats["max_mana"], p.mana + p.stats["max_mana"] * num(ctx, e["pct"]) / 100)
    ctx.world.particles.emit(p.x, p.y, (110, 150, 255), n=24, speed=80, life=0.7, size=3, up=90, z=10)


def fx_leap(e, ctx, col):
    w, p = ctx.world, ctx.p
    tx, ty = clamp_target(p, ctx.tx, ctx.ty, e.get("range", 330))
    ex, ey = w.reachable(p.x, p.y, tx, ty, p.r)
    then = _then(e, ctx)
    p.leap = {"sx": p.x, "sy": p.y, "ex": ex, "ey": ey, "t": 0.0, "dur": e.get("duration", 0.42),
              "on_land": then or (lambda w2: None)}


def fx_dash(e, ctx, col):
    w, p = ctx.world, ctx.p
    ang = math.atan2(ctx.ty - p.y, ctx.tx - p.x)
    if e.get("direction") == "move" and w.is_moving():
        ang = math.atan2(p.move_dir[1], p.move_dir[0])
    dist = e.get("distance", 200)
    ex, ey = w.reachable(p.x, p.y, p.x + math.cos(ang) * dist, p.y + math.sin(ang) * dist, p.r)
    p.dash = {"sx": p.x, "sy": p.y, "ex": ex, "ey": ey, "t": 0.0, "dur": e.get("duration", 0.2),
              "on_end": _then(e, ctx)}
    p.facing = ang
    p.invuln = max(p.invuln, e.get("invuln", 0))
    w.particles.emit(p.x, p.y, col, n=14, speed=90, life=0.4, size=3, z=20)


def fx_teleport(e, ctx, col):
    w, p = ctx.world, ctx.p
    tx, ty = clamp_target(p, ctx.tx, ctx.ty, e.get("range", 380))
    ex, ey = w.reachable(p.x, p.y, tx, ty, p.r)
    if math.hypot(ex - p.x, ey - p.y) < 20:
        return False
    w.particles.emit(p.x, p.y, col, n=26, speed=160, life=0.5, size=4, z=25)
    p.x, p.y = ex, ey
    p.invuln = max(p.invuln, e.get("invuln", 0.25))
    w.particles.emit(p.x, p.y, col, n=26, speed=160, life=0.5, size=4, z=25)
    if e.get("then"):
        run(e["then"], ctx.at(p.x, p.y))


def fx_shadowstep(e, ctx, col):
    w, p = ctx.world, ctx.p
    ms = near(w, p.x, p.y, e.get("range", 420))
    if not ms:
        return False
    m = min(ms, key=lambda m: math.hypot(m.x - ctx.tx, m.y - ctx.ty))
    a = math.atan2(m.y - p.y, m.x - p.x)
    bx, by = m.x + math.cos(a) * (m.r + p.r + 6), m.y + math.sin(a) * (m.r + p.r + 6)
    if w.blocked(bx, by, p.r):
        bx, by = w.reachable(p.x, p.y, m.x, m.y, p.r)
    w.particles.emit(p.x, p.y, col, n=20, speed=120, life=0.5, size=4, z=25)
    p.x, p.y = bx, by
    p.facing = math.atan2(m.y - p.y, m.x - p.x)
    p.swing = -1.4
    p.invuln = max(p.invuln, 0.2)
    w.player_hit(m, mult_of(e, ctx), crit_bonus=e.get("crit_bonus", 0))
    apply_poison(p, m)
    w.particles.emit(p.x, p.y, col, n=20, speed=120, life=0.5, size=4, z=25)


def fx_trap(e, ctx, col):
    w, p = ctx.world, ctx.p
    x, y = clamp_target(p, ctx.tx, ctx.ty, e.get("range", 300))
    x, y = w.reachable(p.x, p.y, x, y, 8)
    w.effects.append(Trap(x, y, mult_of(e, ctx), col, radius=e.get("radius", 115), knock=e.get("knock", 60)))


def fx_strikes(e, ctx, col):
    w = ctx.world
    x, y = point(e, ctx, "target")
    ms = near(w, x, y, e.get("search", 220), int(e.get("count", 6)))
    if not ms:
        return False
    mult = mult_of(e, ctx)
    stagger = e.get("stagger", 0.0)
    for i, m in enumerate(ms):
        def strike(w2, m=m):
            if m.dead:
                return
            w2.effects.append(Lightning(m.x, m.y, col, 0.35))
            w2.player_hit(m, mult, stun=e.get("stun", 0))
            w2.particles.emit(m.x, m.y, col, n=12, speed=120, life=0.5, size=4, up=150, z=10)
        if stagger:
            w.schedule(i * stagger, strike)
        else:
            strike(w)
    w.shake_screen(5)


def fx_summon(e, ctx, col):
    from .allies import SkeletonMinion, Wisp
    w, p = ctx.world, ctx.p
    extra = int(p.t("extra_summon")) if ctx.spell else 0
    mult = mult_of(e, ctx) * (1 + (p.t("summon_pct") if ctx.spell else 0) / 100)
    n = int(e.get("count", 1)) + extra
    kind = e["minion"]
    for i in range(n):
        if kind == "wisp":
            w.allies.append(Wisp(p.x, p.y, mult, e.get("duration", 10)))
            continue
        a = p.facing + (i - (n - 1) / 2) * 0.9
        x, y = w.reachable(p.x, p.y, p.x + math.cos(a) * 60, p.y + math.sin(a) * 60, 13)
        w.allies.append(SkeletonMinion(x, y, mult, e.get("duration", 15)))
        w.particles.emit(x, y, col, n=16, speed=70, life=0.6, size=3, up=140, z=5)
    if kind == "skeleton" and e.get("cap"):
        cap = int(e["cap"]) + extra
        skel = [a for a in w.allies if isinstance(a, SkeletonMinion) and a.life > 0]
        for old in skel[:max(0, len(skel) - cap)]:
            old.life = 0


def fx_curse(e, ctx, col):
    w, p = ctx.world, ctx.p
    x, y = point(e, ctx, "target")
    amp = e.get("amp", 30) / 100 + p.t("curse_amp") / 100
    for m in near(w, x, y, e.get("radius", 150)):
        m.curse = e.get("duration", 6)
        m.curse_amp = amp
        m.slow = max(m.slow, e.get("slow", 0) if not m.boss else e.get("slow", 0) / 2)
    w.effects.append(RingFX(x, y, e.get("radius", 150), 20, 0.5, col, 8))
    w.particles.emit(x, y, col, n=40, speed=160, life=0.8, size=4, up=60, z=5)


def fx_multi_strike(e, ctx, col):
    w, p = ctx.world, ctx.p
    p.invuln = max(p.invuln, e.get("invuln", 0))
    mult = mult_of(e, ctx)
    n = int(e.get("count", 6))
    for i in range(n):
        def strike(w2, i=i):
            a = i * math.tau / n + p.facing
            w2.effects.append(SwingFX(p, a, math.radians(160), e.get("radius", 105) + 5, col, 0.14))
            w2.damage_circle(p.x, p.y, e.get("radius", 105), mult, knock=e.get("knock", 0))
            p.swing = -1.4
            p.facing = a
            sfx.play("swing", 0.4)
        w.schedule(i * e.get("interval", 0.11), strike)


def fx_fx(e, ctx, col):
    w, p = ctx.world, ctx.p
    if e.get("ring"):
        r0, r1, dur = e["ring"]
        w.effects.append(RingFX(p.x, p.y, r0, r1, dur, col, 6))
    if e.get("particles"):
        w.particles.emit(p.x, p.y, col, n=int(e["particles"]), speed=150, life=0.7, size=4, up=90, z=20)
    if e.get("shake"):
        w.shake_screen(e["shake"])
    if e.get("text"):
        w.add_text(p.x, p.y, 70, e["text"], col, 20)


HANDLERS = {"projectile": fx_projectile, "nova": fx_nova, "blast": fx_blast, "line": fx_line, "zone": fx_zone,
            "buff": fx_buff, "heal": fx_heal, "restore_mana": fx_restore_mana, "leap": fx_leap, "dash": fx_dash,
            "teleport": fx_teleport, "shadowstep": fx_shadowstep, "trap": fx_trap, "strikes": fx_strikes,
            "summon": fx_summon, "curse": fx_curse, "multi_strike": fx_multi_strike, "fx": fx_fx}
