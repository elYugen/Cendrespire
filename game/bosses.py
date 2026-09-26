"""Gardiens de fin d'étage : chaque boss a ses propres techniques et une phase 2 à 50% de vie."""
import math
import random

from . import sfx
from .data import BOSSES
from .entities import Monster, Projectile
from .fx import Telegraph, RingFX
from .settings import TILE

# (technique, intervalle phase 1 (None = inactive), intervalle phase 2)
PATTERNS = {
    "boucher": dict(melee=True, keep=0, abilities=[("charge", 7, 5), ("slam", None, 8)]),
    "liche": dict(melee=False, keep=260, abilities=[("bolts", 1.6, 1.1), ("nova", 7, 5.5), ("summon", 12, 10),
                                                    ("blink", 6, 4.5)]),
    "golem": dict(melee=True, keep=0, abilities=[("boulders", 6, 4.5), ("waves", 11, 8)]),
    "seigneur": dict(melee=True, keep=0, abilities=[("charge", 8, 6), ("nova", 9, 6), ("boulders", 7, 5),
                                                    ("summon", None, 12)]),
}


class Boss(Monster):
    boss = True

    def __init__(self, bid, x, y, floor, room):
        super().__init__(BOSSES[bid], x, y, floor)
        self.bid = bid
        self.title = BOSSES[bid]["title"]
        self.room = room
        self.active = False
        self.phase_n = 1
        self.pattern = PATTERNS[bid]
        self.timers = {name: (i1 or i2) * random.uniform(0.4, 0.8) for name, i1, i2 in self.pattern["abilities"]}
        self.pending = None
        self.dash = None
        self.facing = math.pi / 2

    @property
    def targetable(self):
        return self.active

    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt)
        self.slow = max(0.0, self.slow - dt)
        self.phase += dt * 3
        if not self.active or world.player.dead:
            return
        if self.phase_n == 1 and self.hp < self.max_hp / 2:
            self.phase_n = 2
            self.speed *= 1.2
            world.show_banner(f"{self.name} est enragé !", "", (255, 80, 60))
            sfx.play("roar")
            world.shake_screen(10)
            world.effects.append(RingFX(self.x, self.y, 20, 260, 0.6, (255, 60, 30), 8))
        p = world.player
        dx, dy = p.x - self.x, p.y - self.y
        dist = math.hypot(dx, dy) or 0.01
        if self.dash:
            self._update_dash(dt, world)
            return
        if self.state == "windup":
            self.windup -= dt
            if self.windup <= 0:
                self.state = "chase"
                if self.pending:
                    fn, self.pending = self.pending, None
                    fn(world)
            return
        self.cd -= dt
        for k in self.timers:
            self.timers[k] -= dt
        self.los_t -= dt
        if self.los_t <= 0:
            self.los_t = 0.2
            self.has_los = world.los(self.x, self.y, p.x, p.y)
        for name, i1, i2 in self.pattern["abilities"]:
            interval = i2 if self.phase_n == 2 else i1
            if interval is None or self.timers[name] > 0:
                continue
            if self.can_use(name, dist, world):
                self.timers[name] = interval * random.uniform(0.85, 1.15)
                getattr(self, "use_" + name)(world)
                return
        spd = self.speed * (0.7 if self.slow > 0 else 1)
        if self.pattern["melee"]:
            if dist <= self.reach(p):
                self.facing = math.atan2(dy, dx)
                if self.cd <= 0:
                    self.use_melee(world)
            else:
                self.chase(dt, world, dx, dy, dist, spd)
        else:
            keep = self.pattern["keep"]
            if dist < keep - 60:
                self.step(world, -dx / dist, -dy / dist, spd, dt)
            elif dist > keep + 90 or not self.has_los:
                self.chase(dt, world, dx, dy, dist, spd)
            else:
                self.facing = math.atan2(dy, dx)

    def can_use(self, name, dist, world):
        if name == "charge":
            return dist > 140 and self.has_los
        if name == "blink":
            return dist < 130
        if name == "bolts":
            return self.has_los
        if name == "summon":
            return sum(1 for m in world.monsters if m.minion and not m.dead) < 6
        if name == "waves":
            return dist < 380
        return True

    def windup_then(self, t, fn):
        self.state = "windup"
        self.windup = t
        self.pending = fn

    # ------------------------------------------------------------------ techniques
    def use_melee(self, world):
        p = world.player
        ang = math.atan2(p.y - self.y, p.x - self.x)
        self.facing = ang
        fx, fy = self.x + math.cos(ang) * (self.r + 20), self.y + math.sin(ang) * (self.r + 20)
        t = self.d["windup"]
        world.effects.append(Telegraph("circle", t, self.roll_dmg(), fx, fy, self.r + 45, color=(230, 50, 30), sound="hit"))
        self.windup_then(t, None)
        self.cd = self.atk_cd

    def use_slam(self, world):
        world.effects.append(Telegraph("circle", 1.0, self.roll_dmg() * 1.6, self.x, self.y, 170, sound="explosion"))
        self.windup_then(1.0, None)

    def use_charge(self, world):
        p = world.player
        ang = math.atan2(p.y - self.y, p.x - self.x)
        self.facing = ang
        ex, ey = world.reachable(self.x, self.y, self.x + math.cos(ang) * 560, self.y + math.sin(ang) * 560, self.r)
        world.effects.append(Telegraph("line", 0.75, self.roll_dmg() * 1.8, self.x, self.y, x2=ex, y2=ey,
                                       width=self.r * 2 + 10, sound="hit"))

        def go(w):
            self.dash = (ex, ey)
            sfx.play("roar", 0.5)
        self.windup_then(0.75, go)

    def _update_dash(self, dt, world):
        ex, ey = self.dash
        dx, dy = ex - self.x, ey - self.y
        d = math.hypot(dx, dy)
        step = 1300 * dt
        if d <= step:
            self.x, self.y = ex, ey
            self.dash = None
            world.shake_screen(6)
            world.particles.emit(self.x, self.y, (120, 100, 80), n=16, speed=160, life=0.5, size=4, glow=False)
        else:
            self.x += dx / d * step
            self.y += dy / d * step
            world.particles.emit(self.x, self.y, (160, 60, 40), n=2, speed=40, life=0.3, size=4, z=10)

    def use_bolts(self, world):
        p = world.player
        base = math.atan2(p.y - self.y, p.x - self.x)
        n = 3 if self.phase_n == 1 else 5
        for i in range(n):
            a = base + (i - (n - 1) / 2) * 0.22
            world.projectiles.append(Projectile(self.x, self.y, a, 330, "enemy", (120, 230, 255), dmg=self.roll_dmg(),
                                                radius=7, life=2.2))
        sfx.play("magic", 0.5)

    def use_nova(self, world):
        def fire(w, offset=0.0):
            n = 16 if self.phase_n == 1 else 22
            col = (120, 230, 255) if self.bid == "liche" else (140, 255, 140)
            for i in range(n):
                a = i / n * math.tau + offset
                w.projectiles.append(Projectile(self.x, self.y, a, 260, "enemy", col, dmg=self.roll_dmg() * 0.9,
                                                radius=8, life=3.0))
            w.effects.append(RingFX(self.x, self.y, 10, 120, 0.4, col, 5))
            sfx.play("ice", 0.5)
            if self.phase_n == 2 and offset == 0:
                w.schedule(0.45, lambda w2: fire(w2, math.pi / n))
        world.effects.append(RingFX(self.x, self.y, 120, 10, 0.6, (160, 220, 255), 3))
        self.windup_then(0.6, fire)

    def use_summon(self, world):
        mid = "squelette" if self.bid == "liche" else "diablotin"
        n = 3 if self.phase_n == 1 else 4
        for i in range(n):
            a = i / n * math.tau + random.random()
            x, y = self.x + math.cos(a) * 80, self.y + math.sin(a) * 80
            if world.blocked(x, y, 14):
                x, y = self.x, self.y
            m = Monster(mid, x, y, self.floor)
            m.minion = True
            m.aggro = True
            m.xp *= 0.3
            world.monsters.append(m)
            world.particles.emit(x, y, (120, 255, 160), n=14, speed=100, life=0.5, size=3, up=40)
        sfx.play("magic", 0.6)
        self.windup_then(0.5, None)

    def use_blink(self, world):
        p = world.player
        room = self.room
        best = None
        for _ in range(20):
            tx = random.uniform(room.x + 1.5, room.x + room.w - 1.5) * TILE
            ty = random.uniform(room.y + 1.5, room.y + room.h - 1.5) * TILE
            if world.blocked(tx, ty, self.r):
                continue
            d = math.hypot(tx - p.x, ty - p.y)
            if best is None or d > best[0]:
                best = (d, tx, ty)
        if best:
            world.particles.emit(self.x, self.y, (120, 230, 255), n=24, speed=160, life=0.5, size=4)
            self.x, self.y = best[1], best[2]
            world.particles.emit(self.x, self.y, (120, 230, 255), n=24, speed=160, life=0.5, size=4)
            sfx.play("magic", 0.6)

    def use_boulders(self, world):
        p = world.player
        n = 3 if self.phase_n == 1 else 5
        col = (230, 120, 40) if self.bid == "golem" else (140, 255, 140)
        for i in range(n):
            ox, oy = (0, 0) if i == 0 else (random.uniform(-120, 120), random.uniform(-120, 120))
            world.effects.append(Telegraph("circle", 1.1 + i * 0.15, self.roll_dmg() * 1.3, p.x + ox, p.y + oy, 70,
                                           color=col, sound="explosion"))
        self.windup_then(0.4, None)

    def use_waves(self, world):
        dmg = self.roll_dmg() * 1.2
        for i in range(3):
            world.effects.append(Telegraph("ring", 0.9 + i * 0.45, dmg, self.x, self.y, r=130 * (i + 1),
                                           inner=130 * i, color=(230, 140, 40), sound="explosion"))
        self.windup_then(1.8, None)

    # ------------------------------------------------------------------ rendu
    def render(self, fr, t):
        super().render(fr, t)
        if self.active:
            fr.decal(self.x, self.y, self.r * 2.2, self.r * 2.2, (160, 20, 20), 0.35, kind=4)
            fr.light(self.x, self.y, 60, 260, (255, 70, 50), 0.7 + 0.2 * math.sin(t * 3))
        if self.dash:
            fr.glow(self.x, self.y, 30, self.r * 3, (255, 80, 50), 0.6)
