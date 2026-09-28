"""Serviteurs alliés : squelettes levés par le Nécromancien, feu follet de la Lanterne des âmes."""
import math
import random

from .entities import Projectile
from .r3d import models

SPEC = dict(models.MONSTER_SPECS["squelette"], eyes=(120, 255, 160))
SPEC["rig"] = dict(SPEC.get("rig", {}), model="skeleton_minion", slots={"handslot.r": "skel_axe"},
                   anims={"idle": "Idle_Combat", "run": "Running_C", "attack_melee": "1H_Melee_Attack_Slice_Diagonal"},
                   palette={"Glow": (120, 255, 160)})


class SkeletonMinion:
    r = 13

    def __init__(self, x, y, mult, life=15.0):
        self.x, self.y = x, y
        self.mult = mult
        self.life = life
        self.cd = random.uniform(0.2, 0.6)
        self.t = 0.0
        self.facing = random.random() * math.tau
        self.phase = 0.0
        self.moving = False
        self.swing = 0.0
        self.alive = True
        self.target = None

    def update(self, dt, world):
        self.t += dt
        self.life -= dt
        self.cd -= dt
        self.swing *= max(0.0, 1 - dt * 10)
        self.moving = False
        if self.life <= 0:
            self.alive = False
            world.particles.emit(self.x, self.y, (200, 200, 180), n=12, speed=80, life=0.6, size=3, glow=False,
                                 gravity=500, up=150, z=20)
            return
        p = world.player
        tg = self.target
        if not tg or tg.dead or not tg.targetable or math.hypot(tg.x - self.x, tg.y - self.y) > 450:
            cands = [m for m in world.monsters if not m.dead and m.targetable
                     and math.hypot(m.x - p.x, m.y - p.y) < 420]
            tg = self.target = min(cands, key=lambda m: math.hypot(m.x - self.x, m.y - self.y)) if cands else None
        if tg:
            dx, dy = tg.x - self.x, tg.y - self.y
            d = math.hypot(dx, dy) or 1
            self.facing = math.atan2(dy, dx)
            if d > tg.r + self.r + 14:
                world.move_circle(self, dx / d * 150 * dt, dy / d * 150 * dt)
                self.moving = True
            elif self.cd <= 0:
                self.cd = 0.9
                self.swing = -1.4
                world.player_hit(tg, self.mult, knock=10, ang=self.facing, proc=False)
        else:
            dx, dy = p.x - self.x, p.y - self.y
            d = math.hypot(dx, dy) or 1
            if d > 70:
                world.move_circle(self, dx / d * 170 * dt, dy / d * 170 * dt)
                self.facing = math.atan2(dy, dx)
                self.moving = True
        if self.moving:
            self.phase += dt * 11

    def render(self, fr, t):
        rise = min(1.0, self.t / 0.4)
        striking = self.swing < -0.2           # coup en cours : l'animation d'attaque suit l'élan du coup
        models.humanoid(fr, self.x, self.y, -36 * (1 - rise), self.facing, self.phase, SPEC, sc=0.9,
                        swing=self.swing, moving=self.moving, anim="attack_melee" if striking else None,
                        anim_t=(1 + self.swing / 1.4) * 0.5 if striking else None)
        fr.decal(self.x, self.y, 16, 16, (120, 255, 160), 0.35, kind=1, inner=0.75)


def _near(world, x, y, r, n=99):
    ms = [m for m in world.monsters if not m.dead and m.targetable and math.hypot(m.x - x, m.y - y) < r + m.r]
    ms.sort(key=lambda m: math.hypot(m.x - x, m.y - y))
    return ms[:n]


class Wisp:
    """Feu follet allié : suit le héros et tire sur l'ennemi le plus proche."""

    def __init__(self, x, y, mult, life=10.0):
        self.x, self.y, self.z = x, y, 50
        self.mult = mult
        self.life = life
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
