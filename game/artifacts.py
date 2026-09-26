"""Artefacts (inspirés de Minecraft Dungeons) : objets actifs à recharge, équipés dans 3 emplacements."""
import math
import random

from . import sfx
from .data import ARTIFACTS
from .entities import Projectile
from .fx import Zone, RingFX, Lightning
from .items import art_value


def use(world, slot):
    p = world.player
    it = p.equipment.get(slot)
    if not it or p.dead or p.leap:
        return
    if p.art_cds.get(slot, 0) > 0:
        return
    aid = it["art"]
    v = art_value(it)
    ok = EFFECTS[aid](world, p, v)
    if ok is False:
        return
    cd = ARTIFACTS[aid]["cd"] * (1 - p.stats["cdr"] / 100)
    p.art_cds[slot] = cd
    p.art_total[slot] = cd


def _near(world, x, y, r, n=99):
    ms = [m for m in world.monsters if not m.dead and m.targetable and math.hypot(m.x - x, m.y - y) < r + m.r]
    ms.sort(key=lambda m: math.hypot(m.x - x, m.y - y))
    return ms[:n]


def _totem(world, p, v):
    world.effects.append(Zone(p.x, p.y, 110, 6.0, 0.5, v, "heal", (110, 240, 130)))
    sfx.play("potion")


def _foudre(world, p, v):
    targets = _near(world, p.x, p.y, 340, 6)
    if not targets:
        world.add_text(p.x, p.y, 64, "Aucune cible", (200, 200, 200), 15)
        return False
    for m in targets:
        world.effects.append(Lightning(m.x, m.y))
        world.player_hit(m, v / 100, stun=0.3)
    world.shake_screen(5)
    sfx.play("explosion", 0.6)


def _corne(world, p, v):
    for m in _near(world, p.x, p.y, 190):
        a = math.atan2(m.y - p.y, m.x - p.x)
        world.damage_monster(m, 1, False, knock=170, ang=a, stun=1.5, quiet=True)
    world.effects.append(RingFX(p.x, p.y, 20, 210, 0.5, (240, 200, 130), 8))
    world.particles.emit(p.x, p.y, (230, 200, 150), n=40, speed=320, life=0.5, size=4, z=10, zs=0.1)
    world.shake_screen(7)
    sfx.play("roar", 0.7)


def _bottes(world, p, v):
    p.buffs["bottes"] = 5.0
    p.buffs_val["bottes"] = v
    world.particles.emit(p.x, p.y, (120, 220, 230), n=20, speed=120, life=0.5, size=3, z=5)
    sfx.play("magic", 0.5)


def _talisman(world, p, v):
    p.buffs["talisman"] = 5.0
    p.buffs_val["talisman"] = v
    world.effects.append(RingFX(p.x, p.y, 40, 10, 0.4, (210, 215, 230), 5))
    sfx.play("chest", 0.6)


def _gel(world, p, v):
    for m in _near(world, p.x, p.y, 210):
        world.player_hit(m, v / 100, stun=0 if m.boss else 3.0, slow=3.0)
        world.particles.emit(m.x, m.y, (200, 240, 255), n=10, speed=60, life=0.8, size=4, z=20)
    world.effects.append(RingFX(p.x, p.y, 20, 220, 0.45, (170, 230, 255), 10))
    sfx.play("ice")


def _crane(world, p, v):
    for i in range(10):
        a = i / 10 * math.tau
        world.projectiles.append(Projectile(p.x, p.y, a, 420, "player", (255, 120, 40), mult=v / 100, radius=8,
                                            life=0.9, kind="fire", explode=55))
    sfx.play("fire")


def _fiole(world, p, v):
    if p.mana >= p.stats["max_mana"]:
        world.add_text(p.x, p.y, 64, "Mana au maximum", (140, 170, 255), 15)
        return False
    p.mana = min(p.stats["max_mana"], p.mana + p.stats["max_mana"] * v / 100)
    world.particles.emit(p.x, p.y, (110, 150, 255), n=24, speed=80, life=0.7, size=3, up=90, z=10)
    sfx.play("potion")


def _lanterne(world, p, v):
    world.allies.append(Wisp(p.x, p.y, v / 100))
    sfx.play("magic")


EFFECTS = {"totem": _totem, "foudre": _foudre, "corne": _corne, "bottes": _bottes, "talisman": _talisman,
           "gel": _gel, "crane": _crane, "fiole": _fiole, "lanterne": _lanterne}


class Wisp:
    """Feu follet allié : suit le héros et tire sur l'ennemi le plus proche."""

    def __init__(self, x, y, mult):
        self.x, self.y, self.z = x, y, 50
        self.mult = mult
        self.life = 10.0
        self.cd = 0.3
        self.t = 0.0
        self.alive = True

    def update(self, dt, world):
        self.t += dt
        self.life -= dt
        self.alive = self.life > 0
        p = world.player
        a = self.t * 1.8
        tx, ty = p.x + math.cos(a) * 50, p.y + math.sin(a) * 50
        self.x += (tx - self.x) * min(1, dt * 4)
        self.y += (ty - self.y) * min(1, dt * 4)
        self.cd -= dt
        if self.cd <= 0:
            tg = _near(world, self.x, self.y, 380, 1)
            if tg:
                m = tg[0]
                ang = math.atan2(m.y - self.y, m.x - self.x)
                pr = Projectile(self.x, self.y, ang, 560, "player", (160, 255, 220), mult=self.mult, radius=6, life=1.0)
                world.projectiles.append(pr)
                self.cd = 0.7
        if random.random() < 0.5:
            world.particles.emit(self.x, self.y, (160, 255, 220), n=1, speed=15, life=0.5, size=3, z=self.z)

    def render(self, fr, t):
        z = self.z + 5 * math.sin(self.t * 5)
        fr.part("sphere", (self.x, self.y, z), (6, 0, 0), (0, 0, 6), (0, 6, 0), (200, 255, 235), 1.0)
        fr.glow(self.x, self.y, z, 40, (140, 255, 210), 0.9)
        fr.light(self.x, self.y, z, 150, (140, 255, 210), 0.8)
