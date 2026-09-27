"""Serviteurs alliés : squelettes levés par le Nécromancien."""
import math
import random

from .r3d import models

SPEC = dict(models.MONSTER_SPECS["squelette"], eyes=(120, 255, 160))


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
        models.humanoid(fr, self.x, self.y, -36 * (1 - rise), self.facing, self.phase, SPEC, sc=0.9,
                        swing=self.swing, moving=self.moving)
        fr.decal(self.x, self.y, 16, 16, (120, 255, 160), 0.35, kind=1, inner=0.75)
