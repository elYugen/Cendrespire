"""Effets de jeu : particules 3D, zones au sol, attaques annoncées, sorts à retardement.

Chaque effet a une logique (update) et un rendu 3D (render) qui remplit le Frame du moteur.
Coordonnées logiques : (x, y) au sol, z en hauteur.
"""
import math
import random

from . import sfx
from .r3d import models


class Particles:
    def __init__(self):
        self.items = []

    def emit(self, x, y, color, n=8, speed=120, life=0.5, size=3, glow=True, gravity=0.0, angle=None,
             spread=math.tau, drag=2.0, up=0.0, z=0.0, zs=0.5):
        for _ in range(n):
            a = (angle + (random.random() - 0.5) * spread) if angle is not None else random.random() * math.tau
            sp = speed * random.uniform(0.3, 1.0)
            li = life * random.uniform(0.6, 1.0)
            vz = up * random.uniform(0.5, 1.0) + random.uniform(-1, 1) * speed * zs
            self.items.append([x, y, z, math.cos(a) * sp, math.sin(a) * sp, vz, li, li, color,
                               size * random.uniform(0.7, 1.2), gravity, drag, glow])

    def update(self, dt):
        keep = []
        for p in self.items:
            p[6] -= dt
            if p[6] <= 0:
                continue
            f = max(0.0, 1 - p[11] * dt)
            p[3] *= f
            p[4] *= f
            p[5] = (p[5] * f if not p[10] else p[5]) - p[10] * dt
            p[0] += p[3] * dt
            p[1] += p[4] * dt
            p[2] += p[5] * dt
            if p[2] < 0:
                p[2] = 0
                p[5] = -p[5] * 0.3
                p[3] *= 0.5
                p[4] *= 0.5
            keep.append(p)
        self.items = keep[-2500:]

    def render(self, fr):
        ground = fr.ground
        for p in self.items:
            k = p[6] / p[7]
            z = p[2] + ground(p[0], p[1]) if ground else p[2]       # hauteur au-dessus du sol (paliers)
            if p[12]:
                fr.glow(p[0], p[1], z, p[9] * 3.2 * (0.4 + 0.6 * k), p[8], min(1.0, 0.25 + k))
            else:
                fr.solid(p[0], p[1], z, p[9] * 1.3 * (0.5 + 0.5 * k), p[8], 1.0)


class Effect:
    alive = True

    def update(self, dt, world):
        pass

    def render(self, fr):
        pass


class RingFX(Effect):
    def __init__(self, x, y, r0, r1, dur, color, width=4):
        self.x, self.y, self.r0, self.r1, self.dur, self.color, self.width = x, y, r0, r1, dur, color, width
        self.t = 0

    def update(self, dt, world):
        self.t += dt
        self.alive = self.t < self.dur

    def render(self, fr):
        k = min(1, self.t / self.dur)
        r = self.r0 + (self.r1 - self.r0) * (1 - (1 - k) ** 2)
        inner = max(0.0, 1 - self.width * 2.2 / max(r, 1))
        fr.decal(self.x, self.y, r, r, self.color, 0.9 * (1 - k), kind=1, inner=inner, lift=0.004)


class SwingFX(Effect):
    """Arc de frappe au corps à corps (secteur lumineux au sol), suit son propriétaire."""

    def __init__(self, owner, angle, arc, radius, color, dur=0.16):
        self.owner, self.angle, self.arc, self.radius, self.color, self.dur = owner, angle, arc, radius, color, dur
        self.t = 0

    def update(self, dt, world):
        self.t += dt
        self.alive = self.t < self.dur

    def render(self, fr):
        k = self.t / self.dur
        half = min(math.pi, self.arc / 2)
        fr.decal(self.owner.x, self.owner.y, self.radius, self.radius, self.color, 0.7 * (1 - k), kind=3,
                 rot=self.angle, inner=0.35, p1=half, lift=0.006)


class Blast(Effect):
    """Dégâts de zone du joueur après un délai (séisme, météore...)."""

    def __init__(self, x, y, r, delay, mult, color, stun=0.0, slow=0.0, knock=0, kind=None, sound="explosion",
                 on_done=None):
        self.x, self.y, self.r, self.delay, self.mult, self.color = x, y, r, delay, mult, color
        self.stun, self.slow, self.knock, self.kind, self.sound, self.on_done = stun, slow, knock, kind, sound, on_done
        self.t = 0

    def update(self, dt, world):
        self.t += dt
        if self.t >= self.delay:
            world.damage_circle(self.x, self.y, self.r, self.mult, knock=self.knock, stun=self.stun, slow=self.slow)
            world.particles.emit(self.x, self.y, self.color, n=int(self.r / 3), speed=self.r * 2.5, life=0.5,
                                 size=4, z=6, up=120)
            world.particles.emit(self.x, self.y, (90, 80, 70), n=int(self.r / 5), speed=self.r * 2, life=0.9,
                                 size=4, glow=False, gravity=500, up=260, z=4)
            world.effects.append(RingFX(self.x, self.y, self.r * 0.3, self.r, 0.35, self.color, 6))
            world.effects.append(RingFX(self.x, self.y, self.r * 0.5, self.r * 1.35, 0.22, (255, 240, 210), 2))
            world.effects.append(Scorch(self.x, self.y, self.r * 0.75, self.color))
            world.particles.emit(self.x, self.y, (255, 236, 190), n=int(6 + self.r / 10), speed=self.r * 4, life=0.35,
                                 size=2, z=8, up=200, gravity=900, drag=1.0)
            world.flash_light(self.x, self.y, self.r * 3, self.color)
            world.shake_screen(4 + self.r / 25)
            if self.sound:
                sfx.play(self.sound, 0.7)
            if self.on_done:
                self.on_done(world)
            self.alive = False

    def render(self, fr):
        if self.kind == "meteor":
            k = self.t / self.delay
            fr.decal(self.x, self.y, self.r, self.r, self.color, 0.45, kind=5, p1=k)
            mx, my, mz = self.x - (1 - k) * 200, self.y - (1 - k) * 200, (1 - k) * 600 + 10
            fr.part("sphere", (mx, my, mz), (14, 0, 0), (0, 0, 14), (0, 14, 0), (255, 170, 80), 1.0)
            fr.glow(mx, my, mz, 70, (255, 140, 50), 1.0)
            fr.light(mx, my, mz, 260, (255, 130, 50), 1.5)


class Scorch(Effect):
    """Brûlure laissée au sol par une explosion : braises qui s'éteignent, puis tache sombre qui s'efface."""

    def __init__(self, x, y, r, color, dur=4.0):
        self.x, self.y, self.r, self.color, self.dur = x, y, r, color, dur
        self.t = 0.0
        self.seed = random.random() * 9

    def update(self, dt, world):
        self.t += dt
        self.alive = self.t < self.dur

    def render(self, fr):
        k = 1 - self.t / self.dur
        fr.decal(self.x, self.y, self.r, self.r, (14, 10, 8), 0.75 * min(1.0, k * 2), kind=8, p1=self.seed, lift=0.001)
        hot = max(0.0, 1 - self.t / 1.2)
        if hot > 0:
            fr.decal(self.x, self.y, self.r * 0.9, self.r * 0.9, self.color, hot, kind=7, p1=self.seed, lift=0.002)


class Telegraph(Effect):
    """Attaque ennemie annoncée au sol : le joueur peut l'esquiver."""

    def __init__(self, shape, delay, dmg, x=0, y=0, r=60, inner=0, x2=0, y2=0, width=50,
                 color=(235, 45, 35), sound="explosion", on_fire=None):
        self.shape, self.delay, self.dmg = shape, delay, dmg
        self.x, self.y, self.r, self.inner, self.x2, self.y2, self.width = x, y, r, inner, x2, y2, width
        self.color, self.sound, self.on_fire = color, sound, on_fire
        self.t = 0

    def hits(self, p):
        if self.shape in ("circle", "ring"):
            d = math.hypot(p.x - self.x, p.y - self.y)
            return d <= self.r + p.r and d >= self.inner - p.r
        dx, dy = self.x2 - self.x, self.y2 - self.y
        L2 = dx * dx + dy * dy or 1
        t = max(0, min(1, ((p.x - self.x) * dx + (p.y - self.y) * dy) / L2))
        qx, qy = self.x + dx * t, self.y + dy * t
        return math.hypot(p.x - qx, p.y - qy) <= self.width / 2 + p.r

    def update(self, dt, world):
        self.t += dt
        if self.t >= self.delay:
            p = world.player
            if self.dmg and self.hits(p):
                p.take_damage(world, self.dmg)
            if self.shape == "circle":
                world.particles.emit(self.x, self.y, self.color, n=int(10 + self.r / 4), speed=self.r * 2.2,
                                     life=0.45, size=4, up=150)
                world.effects.append(RingFX(self.x, self.y, self.r * 0.4, self.r, 0.3, self.color, 5))
            elif self.shape == "ring":
                for i in range(18):
                    a = i / 18 * math.tau
                    rr = (self.r + self.inner) / 2
                    world.particles.emit(self.x + math.cos(a) * rr, self.y + math.sin(a) * rr, self.color, n=2,
                                         speed=60, life=0.4, size=4, up=120)
            else:
                steps = int(math.hypot(self.x2 - self.x, self.y2 - self.y) / 30) + 1
                for i in range(steps):
                    t = i / steps
                    world.particles.emit(self.x + (self.x2 - self.x) * t, self.y + (self.y2 - self.y) * t,
                                         (140, 110, 90), n=2, speed=60, life=0.5, size=4, glow=False, up=150,
                                         gravity=500)
            world.flash_light(self.x, self.y, self.r * 2.5, self.color)
            world.shake_screen(3)
            if self.sound:
                sfx.play(self.sound, 0.5)
            if self.on_fire:
                self.on_fire(world)
            self.alive = False

    def render(self, fr):
        k = min(1, self.t / self.delay)
        c = self.color
        if self.shape == "circle":
            fr.decal(self.x, self.y, self.r, self.r, c, 0.55, kind=5, p1=k)
        elif self.shape == "ring":
            fr.decal(self.x, self.y, self.r, self.r, c, 0.25 + 0.4 * k, kind=1,
                     inner=self.inner / max(self.r, 1))
        else:
            L = math.hypot(self.x2 - self.x, self.y2 - self.y)
            ang = math.atan2(self.y2 - self.y, self.x2 - self.x)
            cx, cy = (self.x + self.x2) / 2, (self.y + self.y2) / 2
            fr.decal(cx, cy, L / 2, self.width / 2, c, 0.55, kind=6, rot=ang, p1=k)


class Zone(Effect):
    """Zone persistante du joueur : pluie de flèches, sol enflammé, totem de soin."""

    def __init__(self, x, y, r, dur, tick, mult, kind, color):
        self.x, self.y, self.r, self.dur, self.tick, self.mult, self.kind, self.color = x, y, r, dur, tick, mult, kind, color
        self.t = 0
        self.next = 0.15

    def update(self, dt, world):
        self.t += dt
        self.next -= dt
        if self.next <= 0:
            self.next += self.tick
            if self.kind == "heal":
                p = world.player
                if math.hypot(p.x - self.x, p.y - self.y) < self.r + p.r:
                    p.heal(p.stats["max_hp"] * self.mult / 100 * self.tick)
            elif self.kind == "holy":
                world.damage_circle(self.x, self.y, self.r, self.mult)
                p = world.player
                if math.hypot(p.x - self.x, p.y - self.y) < self.r + p.r:
                    p.heal(p.stats["max_hp"] * 0.02)
            else:
                world.damage_circle(self.x, self.y, self.r, self.mult, slow=0.3 if self.kind == "arrows" else 0)
        for _ in range(3 if self.kind == "arrows" else 2):
            a = random.random() * math.tau
            d = math.sqrt(random.random()) * self.r
            x, y = self.x + math.cos(a) * d, self.y + math.sin(a) * d
            if self.kind == "arrows":
                world.particles.emit(x, y, self.color, n=1, speed=0, life=0.2, size=2.5, z=110, up=-600, zs=0)
            else:
                world.particles.emit(x, y, self.color, n=1, speed=15, life=0.8, size=4, up=70, zs=0)
        self.alive = self.t < self.dur

    def render(self, fr):
        k = 1 - self.t / self.dur
        fr.decal(self.x, self.y, self.r, self.r, self.color, 0.18 + 0.2 * k, kind=0)
        fr.decal(self.x, self.y, self.r, self.r, self.color, 0.7 * k, kind=1, inner=0.93, lift=0.003)
        if self.kind == "heal":
            fr.part("cylinder", (self.x, self.y, 18), (4, 0, 0), (0, 0, 18), (0, 4, 0), (120, 90, 60))
            fr.part("sphere", (self.x, self.y, 42 + 3 * math.sin(self.t * 4)), (7, 0, 0), (0, 0, 7), (0, 7, 0),
                    self.color, 1.0)
            fr.light(self.x, self.y, 40, self.r * 2.2, self.color, 1.0)
        elif self.kind == "holy":
            fr.light(self.x, self.y, 30, self.r * 2.2, (255, 220, 130), 1.1)
            for i in range(6):
                ang = self.t * 1.2 + i * math.tau / 6
                fr.glow(self.x + math.cos(ang) * self.r * 0.8, self.y + math.sin(ang) * self.r * 0.8, 6, 14,
                        self.color, 0.8)
        elif self.kind == "fire":
            fr.light(self.x, self.y, 20, self.r * 2, (255, 110, 40), 1.2 * k + 0.2)


class Trap(Effect):
    def __init__(self, x, y, mult, color, radius=115, knock=60):
        self.x, self.y, self.mult, self.color = x, y, mult, color
        self.radius, self.knock = radius, knock
        self.t = 0

    def update(self, dt, world):
        self.t += dt
        if self.t > 0.5:
            trig = self.t > 12 or any(not m.dead and m.targetable and math.hypot(m.x - self.x, m.y - self.y) < 50 + m.r
                                      for m in world.near_monsters(self.x, self.y, 60))
            if trig:
                world.effects.append(Blast(self.x, self.y, self.radius, 0, self.mult, self.color, knock=self.knock))
                self.alive = False

    def render(self, fr):
        models.trap(fr, self.x, self.y, self.t > 0.5, self.t)


class Lightning(Effect):
    """Éclair vertical (pierre d'orage, enchantement Tempête)."""

    def __init__(self, x, y, color=(170, 200, 255), dur=0.25):
        self.x, self.y, self.color, self.dur = x, y, color, dur
        self.t = 0
        self.jit = [(random.uniform(-10, 10), random.uniform(-10, 10)) for _ in range(6)]

    def update(self, dt, world):
        self.t += dt
        self.alive = self.t < self.dur

    def render(self, fr):
        k = 1 - self.t / self.dur
        pts = [(self.x + jx * (i > 0), self.y + jy * (i > 0), 260 - i * 52) for i, (jx, jy) in enumerate(self.jit)]
        pts[-1] = (self.x, self.y, 0)
        for a, b in zip(pts, pts[1:]):
            models.Painter(fr).rod(a, b, 2.5, self.color, (1, 0, 0), emis=1.0)
            fr.glow(a[0], a[1], a[2], 30, self.color, k)
        fr.light(self.x, self.y, 60, 300, self.color, 2.0 * k)
        fr.decal(self.x, self.y, 40, 40, self.color, 0.6 * k, kind=0)
