"""Gardiens de fin d'étage : chaque boss a ses propres techniques et une phase 2 à 50% de vie."""
import math
import random

from . import sfx
from .data import BOSSES
from .entities import Monster, Projectile
from .fx import Effect, Telegraph, RingFX
from .settings import TILE

# techniques de data/bosses.json : (technique, intervalle phase 1 (None = inactive), intervalle phase 2)
PATTERNS = {bid: dict(melee=b.get("melee", True), keep=b.get("keep", 0), abilities=[tuple(a) for a in b["abilities"]])
            for bid, b in BOSSES.items()}


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
        self.jump = None          # bond : (sx, sy, ex, ey, t, durée)
        self.adds = []            # pylônes et clones liés au boss
        self.shield_uses = 0
        self.facing = math.pi / 2

    @property
    def targetable(self):
        return self.active

    @property
    def shielded(self):
        """Invulnérable tant qu'un de ses pylônes tient debout."""
        return any(isinstance(a, Pylon) and not a.dead for a in self.adds)

    def lift(self):
        if not self.jump:
            return 0.0
        sx, sy, ex, ey, t, dur = self.jump
        return math.sin(math.pi * min(1, t / dur)) * 120

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
        if self.jump:
            self._update_jump(dt, world)
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
        if name == "leap":
            return dist > 120
        if name == "shield":            # une fois par phase
            return not self.shielded and self.shield_uses < self.phase_n
        if name == "clones":
            return not any(isinstance(a, Clone) and not a.dead for a in self.adds)
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
            world.projectiles.append(Projectile(self.x, self.y, a, 330, "enemy", self.bolt_color(), dmg=self.roll_dmg(),
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
        mid = self.d.get("summon_monster") or ("squelette" if self.bid == "liche" else "diablotin")
        n = self.d.get("summon_count", [3, 4])[self.phase_n - 1]
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

    # ------------------------------------------------------------------ nouvelles techniques
    def arena_point(self, margin=1.5):
        room = self.room
        return (random.uniform(room.x + margin, room.x + room.w - margin) * TILE,
                random.uniform(room.y + margin, room.y + room.h - margin) * TILE)

    def bolt_color(self):
        return tuple(self.d.get("fx_color", (120, 230, 255)))

    def color_fx(self):
        return tuple(self.d.get("fx_color", (235, 45, 35)))

    def use_leap(self, world):
        """Bond : le boss s'élève et retombe sur la position (annoncée) du joueur."""
        p = world.player
        tx, ty = world.reachable(self.x, self.y, p.x, p.y, self.r)
        world.effects.append(Telegraph("circle", 1.0, self.roll_dmg() * 1.7, tx, ty, 120,
                                       color=self.color_fx(), sound="explosion"))
        self.jump = (self.x, self.y, tx, ty, 0.0, 1.0)
        sfx.play("roar", 0.4)

    def _update_jump(self, dt, world):
        sx, sy, ex, ey, t, dur = self.jump
        t += dt
        k = min(1.0, t / dur)
        self.x, self.y = sx + (ex - sx) * k, sy + (ey - sy) * k
        self.jump = (sx, sy, ex, ey, t, dur) if k < 1 else None
        if k >= 1:
            world.shake_screen(9)
            world.particles.emit(self.x, self.y, (130, 110, 90), n=26, speed=220, life=0.6, size=4, glow=False,
                                 gravity=500, up=200)

    def use_webs(self, world):
        """Toiles gluantes : zones au sol qui ralentissent fortement le joueur."""
        p = world.player
        n = 3 if self.phase_n == 1 else 5
        for i in range(n):
            x, y = (p.x, p.y) if i == 0 else self.arena_point()
            world.effects.append(Web(x, y, random.uniform(70, 95), 9.0))
        sfx.play("magic", 0.5)
        self.windup_then(0.5, None)

    def use_beam(self, world):
        """Rayon : une ligne annoncée, puis un faisceau qui balaie l'arène en tournant autour du boss."""
        p = world.player
        ang = math.atan2(p.y - self.y, p.x - self.x)
        length = 620
        world.effects.append(Telegraph("line", 1.0, 0, self.x, self.y, x2=self.x + math.cos(ang) * length,
                                       y2=self.y + math.sin(ang) * length, width=40, color=(255, 230, 120),
                                       sound=None))
        speed = random.choice((-1, 1)) * (0.75 if self.phase_n == 1 else 1.05)
        dur = 3.2 if self.phase_n == 1 else 4.2

        def fire(w):
            w.effects.append(Beam(self, ang, speed, dur, length, self.roll_dmg() * 0.55))
            sfx.play("explosion", 0.5)
        self.windup_then(1.0, fire)
        self.facing = ang

    def use_shield(self, world):
        """Bouclier : le boss devient invulnérable tant que ses pylônes de cristal ne sont pas détruits."""
        room = self.room
        n = 3 if self.phase_n == 1 else 4
        corners = [(room.x + 2.5, room.y + 2.5), (room.x + room.w - 2.5, room.y + 2.5),
                   (room.x + 2.5, room.y + room.h - 2.5), (room.x + room.w - 2.5, room.y + room.h - 2.5)]
        random.shuffle(corners)
        self.shield_uses += 1
        for cx, cy in corners[:n]:
            x, y = cx * TILE, cy * TILE
            if world.blocked(x, y, 16):
                x, y = self.arena_point()
            pyl = Pylon(self, x, y)
            self.adds.append(pyl)
            world.monsters.append(pyl)
            world.effects.append(RingFX(x, y, 10, 70, 0.5, (255, 230, 140), 6))
        world.message(f"{self.name} est protégé : détruisez les pylônes !", (255, 230, 140), 5)
        sfx.play("seal", 0.7)
        self.windup_then(0.8, None)

    def use_firestorm(self, world):
        """Pluie de feu : de nombreuses zones annoncées dans toute l'arène, en vagues successives."""
        n = 9 if self.phase_n == 1 else 14
        dmg = self.roll_dmg() * 0.9
        p = world.player
        for i in range(n):
            x, y = (p.x, p.y) if i % 6 == 0 else self.arena_point(1.0)
            world.effects.append(Telegraph("circle", 1.1 + (i % 3) * 0.55, dmg, x, y, 62,
                                           color=(255, 110, 30), sound="explosion" if i % 3 == 0 else None))
        world.shake_screen(4)
        sfx.play("fire", 0.7)
        self.windup_then(0.7, None)

    def use_vortex(self, world):
        """Vortex : le joueur est aspiré vers le boss, puis une explosion frappe tout autour de lui."""
        dur = 2.2
        world.effects.append(Vortex(self, dur, 150 if self.phase_n == 1 else 185))
        world.effects.append(Telegraph("circle", dur, self.roll_dmg() * 1.6, self.x, self.y, 165,
                                       color=(255, 90, 30), sound="explosion"))
        sfx.play("roar", 0.5)
        self.windup_then(dur, None)

    def use_clones(self, world):
        """Illusions : des copies du boss apparaissent et l'attaquent à distance ; le vrai boss se téléporte."""
        n = 2 if self.phase_n == 1 else 3
        for i in range(n):
            x, y = self.arena_point()
            c = Clone(self, x, y)
            self.adds.append(c)
            world.monsters.append(c)
            world.particles.emit(x, y, (170, 110, 255), n=20, speed=140, life=0.5, size=4)
        self.use_blink(world)
        sfx.play("magic", 0.7)

    def on_death(self, world):
        """Les pylônes et les illusions disparaissent avec leur boss."""
        for a in self.adds:
            if not a.dead:
                a.dead = True
                world.particles.emit(a.x, a.y, (220, 220, 255), n=16, speed=120, life=0.5, size=4)

    # ------------------------------------------------------------------ rendu
    def render(self, fr, t):
        if self.jump:
            sx, sy, ex, ey, jt, dur = self.jump
            fr.decal(ex, ey, self.r * 1.4, self.r * 1.4, (0, 0, 0), 0.5 * min(1, jt / dur), kind=4)
        super().render(fr, t)
        if self.shielded:
            h = self.height()
            fr.part("sphere", (self.x, self.y, h * 0.5), (self.r * 1.6, 0, 0), (0, 0, h * 0.75),
                    (0, self.r * 1.6, 0), (255, 220, 120), 0.35, additive=True)
            for a in self.adds:
                if isinstance(a, Pylon) and not a.dead:
                    mx, my = (a.x + self.x) / 2, (a.y + self.y) / 2
                    L = math.hypot(a.x - self.x, a.y - self.y) / 2
                    ang = math.atan2(a.y - self.y, a.x - self.x)
                    fr.part("cube", (mx, my, 40), (math.cos(ang) * L, math.sin(ang) * L, 0), (0, 0, 1.2),
                            (-math.sin(ang) * 1.2, math.cos(ang) * 1.2, 0), (255, 220, 120), 0.8, additive=True)

        if self.active:
            fr.decal(self.x, self.y, self.r * 2.2, self.r * 2.2, (160, 20, 20), 0.35, kind=4)
            fr.light(self.x, self.y, 60, 260, (255, 70, 50), 0.7 + 0.2 * math.sin(t * 3))
        if self.dash:
            fr.glow(self.x, self.y, 30, self.r * 3, (255, 80, 50), 0.6)


# =========================================================================== éléments des nouvelles techniques
class Pylon(Monster):
    """Pylône de cristal : tant qu'il en reste un, son boss est invulnérable."""
    minion = True

    def __init__(self, boss, x, y):
        d = dict(id="pylone", name="Pylône de cristal", hp=boss.d["hp"] * 0.07, dmg=(0, 0), speed=0,
                 radius=16, ai="caster", range=0, cd=99, windup=1, xp=10, floor=1)
        super().__init__(d, x, y, boss.floor)
        self.aggro = True

    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt)
        self.phase += dt

    def height(self):
        return 58

    def render(self, fr, t):
        col = (255, 255, 255) if self.flash > 0 else (255, 224, 140)
        bob = 4 * math.sin(self.phase * 2)
        fr.part("cone", (self.x, self.y, 30 + bob), (9, 0, 0), (0, 0, 22), (0, 9, 0), col, 0.8)
        fr.part("cone", (self.x, self.y, 30 + bob), (9, 0, 0), (0, 0, -18), (0, 9, 0), col, 0.8)
        fr.box(self.x, self.y, 0, 14, 14, 4, (90, 86, 96), mesh="cylinder")
        fr.glow(self.x, self.y, 34 + bob, 40, (255, 220, 120), 0.8)
        fr.light(self.x, self.y, 40, 160, (255, 220, 120), 0.9)
        k = max(0.0, self.hp / self.max_hp)
        fr.decal(self.x, self.y, 22, 22, (255, 220, 120), 0.5, kind=1, inner=1 - 0.25 * k)


class Clone(Monster):
    """Illusion du boss : fragile, tire des projectiles d'ombre."""
    minion = True

    def __init__(self, boss, x, y):
        d = dict(boss.d)
        d.update(hp=boss.d["hp"] * 0.1, ai="caster", range=320, cd=2.2, windup=0.5, xp=5)
        super().__init__(d, x, y, boss.floor)
        self.dmg = (self.dmg[0] * 0.45, self.dmg[1] * 0.45)
        self.name = boss.name + " (illusion)"
        self.aggro = True

    def render(self, fr, t):
        super().render(fr, t)
        fr.glow(self.x, self.y, 30, 30, (170, 110, 255), 0.4)


class Web(Effect):
    """Toile au sol : ralentit fortement le joueur qui la traverse."""

    def __init__(self, x, y, r, dur):
        self.x, self.y, self.r, self.dur = x, y, r, dur
        self.t = 0.0

    def update(self, dt, world):
        self.t += dt
        self.alive = self.t < self.dur
        p = world.player
        if math.hypot(p.x - self.x, p.y - self.y) < self.r:
            p.snare = max(p.snare, 0.15)

    def render(self, fr):
        a = max(0.0, min(1.0, self.t * 3, (self.dur - self.t) * 2))
        fr.decal(self.x, self.y, self.r, self.r, (225, 225, 235), 0.5 * a, kind=1, inner=0.12)
        for i in range(4):
            fr.decal(self.x, self.y, self.r, 2.5, (225, 225, 235), 0.45 * a, kind=0, rot=i * math.pi / 4)


class Beam(Effect):
    """Faisceau tournant autour du boss : touche le joueur qui se trouve sur sa trajectoire."""

    def __init__(self, boss, ang, speed, dur, length, dmg):
        self.boss, self.ang, self.speed, self.dur, self.length, self.dmg = boss, ang, speed, dur, length, dmg
        self.t = 0.0
        self.tick = 0.0
        self.end = (boss.x, boss.y)

    def update(self, dt, world):
        b = self.boss
        self.t += dt
        self.ang += self.speed * dt
        self.alive = self.t < self.dur and not b.dead
        b.state, b.windup, b.pending = "windup", 0.1, None    # le boss reste concentré tant que le rayon brûle
        self.tick -= dt
        p = world.player
        x2, y2 = world.reachable(b.x, b.y, b.x + math.cos(self.ang) * self.length,
                                 b.y + math.sin(self.ang) * self.length, 4)
        self.end = (x2, y2)
        if self.tick <= 0:
            dx, dy = x2 - b.x, y2 - b.y
            L2 = dx * dx + dy * dy or 1
            k = max(0, min(1, ((p.x - b.x) * dx + (p.y - b.y) * dy) / L2))
            if math.hypot(p.x - (b.x + dx * k), p.y - (b.y + dy * k)) < 22 + p.r:
                p.take_damage(world, self.dmg)
                self.tick = 0.25
        if random.random() < 0.6:
            world.particles.emit(x2, y2, (255, 220, 120), n=2, speed=120, life=0.4, size=4, up=80, z=10)

    def render(self, fr):
        b = self.boss
        x2, y2 = self.end
        mx, my = (b.x + x2) / 2, (b.y + y2) / 2
        L = max(1.0, math.hypot(x2 - b.x, y2 - b.y) / 2)
        c, s = math.cos(self.ang), math.sin(self.ang)
        for w, col, e in ((13, (255, 200, 90), 0.7), (5, (255, 255, 230), 1.0)):
            fr.part("cylinder", (mx, my, 34), (0, 0, w), (c * L, s * L, 0), (-s * w, c * w, 0), col, e,
                    additive=True)
        fr.light(x2, y2, 30, 180, (255, 210, 120), 1.2)
        fr.decal(mx, my, L, 16, (255, 190, 80), 0.35, kind=6, rot=self.ang, p1=1.0)


class Vortex(Effect):
    """Aspiration vers le boss : il faut courir (ou rouler) pour échapper à l'explosion qui suit."""

    def __init__(self, boss, dur, pull):
        self.boss, self.dur, self.pull = boss, dur, pull
        self.t = 0.0

    def update(self, dt, world):
        self.t += dt
        b, p = self.boss, world.player
        self.alive = self.t < self.dur and not b.dead
        if p.dash or p.leap:
            return
        dx, dy = b.x - p.x, b.y - p.y
        d = math.hypot(dx, dy)
        if 30 < d < 560:
            world.move_circle(p, dx / d * self.pull * dt, dy / d * self.pull * dt)
        if random.random() < 0.8:
            a = random.random() * math.tau
            rr = random.uniform(120, 300)
            world.particles.emit(b.x + math.cos(a) * rr, b.y + math.sin(a) * rr, (255, 120, 50), n=1,
                                 speed=rr * 1.6, angle=a + math.pi, spread=0.1, life=0.6, size=4, z=20)

    def render(self, fr):
        b = self.boss
        k = self.t / self.dur
        for i in range(3):
            r = 300 * (1 - (k * 2 + i / 3) % 1)
            fr.decal(b.x, b.y, r, r, (255, 110, 40), 0.35, kind=1, inner=0.9)
