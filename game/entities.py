"""Entités : joueur, monstres, projectiles, butin et objets interactifs (logique + rendu 3D)."""
import math
import random
from collections import defaultdict

from . import looks, sfx, talents
from .data import (CLASSES, SPELLS, MONSTERS, ATTRS, ELITE_AFFIXES, MAX_LEVEL, POINTS_PER_LEVEL, ANIMA_POWERS,
                   POTION_CD, POTION_HEAL, ROLL_CD, ROLL_DUR, ROLL_DIST, xp_needed, floor_scaling)
from .fx import RingFX
from .items import SLOTS, ART_SLOTS, EQUIP_SLOTS, item_stats, ench_stats, ench_spent
from .r3d import models
from .settings import RARITY_COLORS


# =========================================================================== joueur
class Player:
    r = 14

    def __init__(self, data):
        self.name = data["name"]
        self.cls_id = data["cls"]
        self.look = looks.clean_look(data.get("look"), self.cls_id)
        self._spec = None
        self.level = data.get("level", 1)
        self.xp = data.get("xp", 0)
        self.alloc = {a: data.get("alloc", {}).get(a, 0) for a in ATTRS}
        self.points = data.get("points", 0)
        self.talents = talents.clean(data.get("talents"), self.cls_id)
        self.tal = {}
        self.stand_used = False
        self.gold = data.get("gold", 0)
        self.max_floor = data.get("max_floor", 1)
        self.cleared = set(data.get("cleared", []))
        eq = data.get("equipment", {})
        self.equipment = {s: eq.get(s) for s in EQUIP_SLOTS}
        self.inventory = list(data.get("inventory", []))
        for it in self.all_items():
            it.setdefault("ench", [])
        self.kills = data.get("kills", 0)
        self.deaths = data.get("deaths", 0)
        self.created_at = data.get("created_at", 0)
        # état en jeu
        self.x = self.y = 0.0
        self.z = 0.0
        self.facing = 0.0
        self.walk = 0.0
        self.moving = False
        self.anima = {}
        self.second_used = False
        self.buffs = {}
        self.cds = {}
        self.cd_total = {}
        self.art_cds = {}
        self.art_total = {}
        self.atk_cd = 0.0
        self.invuln = 0.0
        self.flash = 0.0
        self.swing = 0.0
        self.leap = None
        self.dash = None
        self.move_dir = (1.0, 0.0)
        self.potion_cd = 0.0
        self.potion_total = POTION_CD
        self.roll_cd = 0.0
        self.roll_total = ROLL_CD
        self.buffs_val = {}
        self.dead = False
        self.hp = self.mana = 1
        self.recompute()
        self.full_restore()

    @property
    def cls(self):
        return CLASSES[self.cls_id]

    @property
    def spells(self):
        return self.cls["spells"]

    def all_items(self):
        return [it for it in list(self.equipment.values()) + self.inventory if it]

    def to_save(self):
        return {"name": self.name, "cls": self.cls_id, "level": self.level, "xp": self.xp, "alloc": self.alloc,
                "points": self.points, "gold": self.gold, "max_floor": self.max_floor,
                "cleared": sorted(self.cleared), "equipment": self.equipment, "inventory": self.inventory,
                "kills": self.kills, "deaths": self.deaths, "created_at": self.created_at, "look": dict(self.look),
                "talents": dict(self.talents)}

    @property
    def spec(self):
        """Spécification du modèle 3D, recalculée quand l'apparence change."""
        key = tuple(sorted(self.look.items()))
        if not self._spec or self._spec[0] != key:
            self._spec = (key, looks.hero_spec(self.cls_id, self.look))
        return self._spec[1]

    # ------------------------------------------------------------------ enchantements
    @property
    def ench_points_total(self):
        return self.level - 1

    @property
    def ench_points(self):
        return self.ench_points_total - sum(ench_spent(it) for it in self.all_items())

    # ------------------------------------------------------------------ talents
    @property
    def talent_points_total(self):
        return talents.points_total(self.level)

    @property
    def talent_points(self):
        return self.talent_points_total - talents.spent(self.talents)

    def t(self, key):
        """Valeur totale d'un effet de talent (0 si absent)."""
        return self.tal.get(key, 0)

    def full_restore(self):
        self.hp = self.stats["max_hp"]
        self.mana = self.stats["max_mana"]
        self.dead = False

    def reset_run(self):
        self.anima = {}
        self.second_used = False
        self.stand_used = False
        self.buffs = {}
        self.cds = {}
        self.art_cds = {}
        self.potion_cd = self.roll_cd = 0.0
        self.leap = self.dash = None
        self.recompute()
        self.full_restore()

    def av(self, pid):
        """Valeur totale d'un pouvoir d'anima."""
        return ANIMA_POWERS[pid]["per"] * self.anima.get(pid, 0)

    def recompute(self):
        c = self.cls
        gear = defaultdict(float)
        ench = defaultdict(float)
        armor = 0
        dmin, dmax = 2, 4
        for slot in SLOTS:
            it = self.equipment.get(slot)
            if not it:
                continue
            st = item_stats(it)
            armor += st.get("armor", 0)
            if slot == "arme":
                dmin, dmax = st["dmg"]
            for k, v in st["affixes"].items():
                gear[k] += v
            for k, v in ench_stats(it).items():
                ench[k] += v
        av = self.av
        self.tal = tal = talents.effects(self.talents)
        tv = tal.get
        s = {k: c["attrs"][k] + self.alloc[k] + gear[k] for k in ATTRS}
        s["max_hp"] = ((c["hp"] + c["hp_lvl"] * (self.level - 1) + s["vit"] * 5 + gear["vie"])
                       * (1 + av("vigueur") / 100) * (1 + ench["vitalite"] / 100) * (1 + tv("max_hp_pct", 0) / 100))
        s["max_mana"] = ((c["mana"] + c["mana_lvl"] * (self.level - 1) + s["int"] * 1.5 + gear["mana"])
                         * (1 + tv("mana_pct", 0) / 100))
        s["armor"] = (armor + gear["armure"] + s["force"] * 0.5) * (1 + tv("armor_pct", 0) / 100)
        s["dmg_min"], s["dmg_max"] = dmin, dmax
        s["dmg_pct"] = gear["dmg_pct"] + av("rage") + ench["tranchant"] + tv("dmg_pct", 0)
        s["dmg_mult"] = (1 + s[c["primary"]] / 100) * (1 + s["dmg_pct"] / 100)
        s["crit"] = min(60, 5 + s["dex"] * 0.05 + gear["crit"] + av("precision") + ench["acuite"] + tv("crit", 0))
        s["crit_mult"] = 1.75 + tv("crit_dmg", 0) / 100
        s["atk_speed"] = gear["atk_speed"] + av("frenesie") + ench["vivacite"] + tv("atk_speed", 0)
        s["lifesteal"] = gear["lifesteal"] + av("soif") + tv("lifesteal", 0)
        s["mana_regen"] = ((c["mana_regen"] + gear["mana_regen"]) * (1 + av("flux") / 100)
                           * (1 + tv("mana_regen_pct", 0) / 100))
        s["move_speed"] = gear["move_speed"] + av("ombre") + ench["celerite"] + tv("move_speed", 0)
        s["cdr"] = min(50, gear["cdr"] + av("esprit") + ench["recharge"] + tv("cdr", 0))
        s["gold_find"] = gear["gold_find"] + av("cupidite") + tv("gold_find", 0)
        s["speed"] = c["speed"] * (1 + s["move_speed"] / 100)
        s["dr_bonus"] = av("carapace") / 100 + ench["rempart"] / 100 + tv("dr", 0) / 100
        s["ench"] = dict(ench)
        self.stats = s
        self.potion_total = POTION_CD * (1 - ench["potion_vive"] / 100)
        self.roll_total = ROLL_CD * (1 - ench["agilite"] / 100) * (1 - tv("roll_cd", 0) / 100)
        self.hp = min(self.hp, s["max_hp"])
        self.mana = min(self.mana, s["max_mana"])

    def ench(self, eid):
        return self.stats["ench"].get(eid, 0)

    def damage_reduction(self):
        armor = self.stats["armor"] * (1.5 if "cri" in self.buffs else 1)
        dr = armor / (armor + 220) + self.stats["dr_bonus"]
        if "talisman" in self.buffs:
            dr += self.buffs_val.get("talisman", 0) / 100
        if "egide" in self.buffs:
            dr += 0.35
        if self.t("low_hp_dr") and self.hp < self.stats["max_hp"] * 0.35:
            dr += self.t("low_hp_dr") / 100
        return min(0.85, dr)

    def dps_estimate(self):
        s = self.stats
        avg = (s["dmg_min"] + s["dmg_max"]) / 2 * s["dmg_mult"] * (1 + s["crit"] / 100 * (s["crit_mult"] - 1))
        mult = self.cls["attack"]["mult"] * (1 + self.t("basic_pct") / 100)
        return avg * mult / (self.cls["attack"]["cd"] / (1 + s["atk_speed"] / 100))

    def roll_damage(self, mult, crit_bonus=0.0):
        s = self.stats
        d = random.uniform(s["dmg_min"], s["dmg_max"]) * mult * s["dmg_mult"]
        if "cri" in self.buffs:
            d *= 1.35
        if self.t("berserk"):
            missing = 1 - max(0.0, self.hp) / s["max_hp"]
            d *= 1 + self.t("berserk") / 100 * missing
        crit = random.random() * 100 < s["crit"] + crit_bonus
        if crit:
            d *= s["crit_mult"]
        return d, crit

    def heal(self, amount):
        self.hp = min(self.stats["max_hp"], self.hp + amount)

    def speed(self):
        k = 1.0
        if "bottes" in self.buffs:
            k += self.buffs_val.get("bottes", 0) / 100
        return self.stats["speed"] * k

    def take_damage(self, world, amount, attacker=None, melee=False):
        if self.invuln > 0 or self.dead or self.leap or self.dash:
            return 0
        if random.random() * 100 < self.ench("esquive"):
            world.add_text(self.x, self.y, 50, "Esquive", (200, 230, 255), 16)
            return 0
        dmg = amount * (1 - self.damage_reduction())
        self.hp -= dmg
        self.flash = 0.12
        world.add_text(self.x, self.y, 50, f"-{int(dmg)}", (255, 90, 70), 18)
        world.shake_screen(2 + min(8, dmg / self.stats["max_hp"] * 40))
        world.particles.emit(self.x, self.y, (150, 12, 12), n=6, speed=90, life=0.5, size=3, glow=False,
                             gravity=500, up=180, z=24)
        sfx.play("hurt", 0.6)
        thorns = self.ench("epines") + self.t("thorns")
        if attacker is not None and melee and thorns:
            world.damage_monster(attacker, dmg * thorns / 100, False)
        if (self.t("last_stand") and not self.stand_used and 0 < self.hp < self.stats["max_hp"] * 0.2):
            self.stand_used = True
            self.heal(self.stats["max_hp"] * 0.4)
            self.invuln = 2.0
            world.show_banner("Second souffle !", "", (255, 220, 120), 2.0)
            world.effects.append(RingFX(self.x, self.y, 10, 140, 0.5, (255, 220, 120), 6))
        if self.ench("riposte") and random.random() * 100 < self.ench("riposte"):
            from .fx import Blast
            world.effects.append(Blast(self.x, self.y, 120, 0, 1.0, (255, 120, 40), knock=60, sound="fire"))
        if self.hp <= 0:
            world.on_player_death()
        return dmg

    def gain_xp(self, amount, world):
        if self.level >= MAX_LEVEL:
            return
        self.xp += int(amount)
        leveled = False
        while self.level < MAX_LEVEL and self.xp >= xp_needed(self.level):
            self.xp -= xp_needed(self.level)
            self.level += 1
            self.points += POINTS_PER_LEVEL
            leveled = True
        if leveled:
            self.recompute()
            self.full_restore()
            world.on_level_up()

    def drink_potion(self, world):
        if self.potion_cd > 0 or self.dead:
            return
        if self.hp >= self.stats["max_hp"]:
            world.add_text(self.x, self.y, 60, "Vie au maximum", (200, 220, 200), 15)
            return
        self.potion_cd = self.potion_total
        amt = self.stats["max_hp"] * POTION_HEAL
        self.heal(amt)
        world.add_text(self.x, self.y, 60, f"+{int(amt)}", (110, 240, 110), 18)
        world.particles.emit(self.x, self.y, (90, 230, 100), n=22, speed=70, life=0.8, size=3, up=90, z=10)
        world.effects.append(RingFX(self.x, self.y, 10, 60, 0.4, (110, 240, 120), 3))
        sfx.play("potion")

    def start_roll(self, world, dx, dy):
        if self.roll_cd > 0 or self.leap or self.dash or self.dead:
            return
        ex, ey = world.reachable(self.x, self.y, self.x + dx * ROLL_DIST, self.y + dy * ROLL_DIST, self.r)
        self.dash = {"sx": self.x, "sy": self.y, "ex": ex, "ey": ey, "t": 0.0, "dur": ROLL_DUR, "roll": True}
        self.invuln = ROLL_DUR + 0.08
        self.roll_cd = self.roll_total
        self.facing = math.atan2(dy, dx)
        world.particles.emit(self.x, self.y, (150, 136, 110), n=10, speed=70, life=0.45, size=3, glow=False, up=60)
        sfx.play("swing", 0.5)

    def can_equip(self, item):
        return item["slot"] != "arme" or item.get("wclass") == self.cls_id

    def spell_unlocked(self, sid):
        return self.level >= SPELLS[sid]["level"]

    def tick(self, dt):
        for d in (self.cds, self.art_cds):
            for k in list(d):
                d[k] = max(0.0, d[k] - dt)
        for k in list(self.buffs):
            self.buffs[k] -= dt
            if self.buffs[k] <= 0:
                del self.buffs[k]
        self.atk_cd = max(0.0, self.atk_cd - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.flash = max(0.0, self.flash - dt)
        self.potion_cd = max(0.0, self.potion_cd - dt)
        self.roll_cd = max(0.0, self.roll_cd - dt)
        self.swing = self.swing * max(0, 1 - dt * 12)
        self.mana = min(self.stats["max_mana"], self.mana + self.stats["mana_regen"] * dt)

    def render(self, fr, t):
        lift = 0.0
        sc = 1.0
        if self.leap:
            k = self.leap["t"] / self.leap["dur"]
            lift = math.sin(math.pi * k) * 90
        if self.dash and self.dash.get("roll"):
            k = self.dash["t"] / self.dash["dur"]
            sc = 1 - 0.3 * math.sin(math.pi * k)
        if self.invuln > 0 and not (self.leap or self.dash) and int(self.invuln * 20) % 2:
            return
        models.humanoid(fr, self.x, self.y, lift, self.facing, self.walk, self.spec, sc=sc,
                        flash=self.flash > 0, swing=self.swing, moving=self.moving or bool(self.dash))
        if "cri" in self.buffs:
            fr.decal(self.x, self.y, 30, 30, (255, 60, 30), 0.5, kind=1, inner=0.75)
        if "talisman" in self.buffs:
            fr.part("sphere", (self.x, self.y, 26), (26, 0, 0), (0, 0, 32), (0, 26, 0), (200, 210, 230), 0.25,
                    additive=True)
        if "bottes" in self.buffs:
            fr.glow(self.x, self.y, 4, 26, (120, 220, 230), 0.6)


# =========================================================================== monstres
class Monster:
    boss = False
    minion = False
    targetable = True

    def __init__(self, mdef, x, y, floor, elite=None):
        d = MONSTERS[mdef] if isinstance(mdef, str) else mdef
        self.mid = mdef if isinstance(mdef, str) else d["id"]
        self.d = d
        hpm, dmgm = floor_scaling(floor)
        self.floor = floor
        self.name = d["name"]
        self.max_hp = d["hp"] * hpm
        self.dmg = (d["dmg"][0] * dmgm, d["dmg"][1] * dmgm)
        self.speed = d["speed"]
        self.r = d["radius"]
        self.atk_cd = d["cd"]
        self.xp = d["xp"] * (1 + 0.4 * (floor - 1))
        self.leech = 0
        self.elite = elite
        if elite:
            af = ELITE_AFFIXES[elite]
            self.max_hp *= 3.5 * af.get("hp", 1)
            self.dmg = (self.dmg[0] * 1.4 * af.get("dmg", 1), self.dmg[1] * 1.4 * af.get("dmg", 1))
            self.r = int(self.r * 1.3 * af.get("radius", 1))
            self.speed *= af.get("speed", 1)
            self.atk_cd *= af.get("cd", 1)
            self.leech = af.get("leech", 0)
            self.xp *= 3
            self.name = f"{self.name} [{elite}]"
        self.hp = self.max_hp
        self.x, self.y = x, y
        self.kx = self.ky = 0.0
        self.state = "idle"
        self.aggro = False
        self.cd = random.uniform(0.3, 1.2)
        self.windup = 0.0
        self.atk_angle = 0.0
        self.stun = self.slow = self.flash = 0.0
        self.burn = 0.0
        self.burn_dps = 0.0
        self.burn_tick = 0.0
        self.burn_col = (255, 120, 40)
        self.curse = 0.0
        self.facing = random.random() * math.tau
        self.phase = random.random() * 10
        self.moving = False
        self.los_t = 0.0
        self.has_los = False
        self.wander = None
        self.wander_t = random.uniform(1, 4)
        self.dead = False
        self.spawn_t = 0.0

    @property
    def spec_id(self):
        return self.mid

    def roll_dmg(self):
        return random.uniform(*self.dmg)

    # ------------------------------------------------------------------ IA
    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt)
        self.slow = max(0.0, self.slow - dt)
        self.spawn_t += dt
        self.moving = False
        self.curse = max(0.0, self.curse - dt)
        if self.burn > 0:
            self.burn -= dt
            self.burn_tick -= dt
            if self.burn_tick <= 0:
                self.burn_tick = 0.5
                world.particles.emit(self.x, self.y, self.burn_col, n=4, speed=30, life=0.5, size=3, up=60, z=20)
                world.damage_monster(self, self.burn_dps * 0.5, False, quiet=True)
                if self.dead:
                    return
        if self.kx or self.ky:
            world.move_circle(self, self.kx * dt, self.ky * dt)
            f = max(0, 1 - 8 * dt)
            self.kx *= f
            self.ky *= f
            if abs(self.kx) + abs(self.ky) < 5:
                self.kx = self.ky = 0
        if self.stun > 0:
            self.stun -= dt
            if self.state == "windup":
                self.state = "chase"
            return
        p = world.player
        dx, dy = p.x - self.x, p.y - self.y
        dist = math.hypot(dx, dy) or 0.01
        self.los_t -= dt
        if self.los_t <= 0:
            self.los_t = 0.25
            self.has_los = world.los(self.x, self.y, p.x, p.y)
        if not self.aggro:
            if (dist < 340 and self.has_los) or dist < 110:
                self.aggro = True
                world.alert(self)
            else:
                self._wander(dt, world)
                return
        if p.dead:
            return
        spd = self.speed * (0.4 if self.slow > 0 else 1)
        if self.state == "windup":
            self.windup -= dt
            if self.d["ai"] != "melee":
                self.facing = math.atan2(dy, dx)
            if self.windup <= 0:
                self.attack(world, dist)
                self.state = "chase"
                self.cd = self.atk_cd * random.uniform(0.9, 1.15)
            return
        self.cd -= dt
        self.think(dt, world, dx, dy, dist, spd)

    def _wander(self, dt, world):
        self.wander_t -= dt
        if self.wander_t <= 0:
            self.wander_t = random.uniform(2, 5)
            a = random.random() * math.tau
            self.wander = (math.cos(a), math.sin(a), random.uniform(0.4, 1.2))
        if self.wander and self.wander[2] > 0:
            wx, wy, t = self.wander
            self.wander = (wx, wy, t - dt)
            world.move_circle(self, wx * self.speed * 0.3 * dt, wy * self.speed * 0.3 * dt)
            self.facing = math.atan2(wy, wx)
            self.phase += dt * 5
            self.moving = True

    def reach(self, p):
        return self.d["range"] + self.r + p.r

    def think(self, dt, world, dx, dy, dist, spd):
        ai = self.d["ai"]
        p = world.player
        if ai in ("melee", "brute"):
            if dist <= self.reach(p):
                self.facing = math.atan2(dy, dx)
                if self.cd <= 0:
                    self.start_windup(world)
            else:
                self.chase(dt, world, dx, dy, dist, spd)
        else:
            if dist < 140:
                self.step(world, -dx / dist, -dy / dist, spd * 0.9, dt)
            elif dist > self.d["range"] or not self.has_los:
                self.chase(dt, world, dx, dy, dist, spd)
            else:
                self.facing = math.atan2(dy, dx)
                if self.cd <= 0:
                    self.start_windup(world)

    def start_windup(self, world):
        from .fx import Telegraph
        self.state = "windup"
        self.windup = self.d["windup"]
        p = world.player
        self.atk_angle = math.atan2(p.y - self.y, p.x - self.x)
        self.facing = self.atk_angle
        if self.d["ai"] == "brute":
            fx_, fy_ = self.x + math.cos(self.atk_angle) * 45, self.y + math.sin(self.atk_angle) * 45
            world.effects.append(Telegraph("circle", self.windup, self.roll_dmg() * 1.3, fx_, fy_, 75,
                                           color=(235, 70, 35), sound="hit"))

    def attack(self, world, dist):
        from .fx import Telegraph
        ai = self.d["ai"]
        p = world.player
        if ai == "melee":
            ang = math.atan2(p.y - self.y, p.x - self.x)
            diff = abs((ang - self.atk_angle + math.pi) % math.tau - math.pi)
            if dist <= self.reach(p) + 14 and diff < 1.1:
                dealt = p.take_damage(world, self.roll_dmg(), self, melee=True)
                if dealt and self.leech:
                    self.hp = min(self.max_hp, self.hp + dealt * self.leech * 3)
            sfx.play("swing", 0.4)
        elif ai == "ranged":
            ang = math.atan2(p.y - self.y, p.x - self.x)
            world.projectiles.append(Projectile(self.x, self.y, ang, self.d["proj_speed"], "enemy",
                                                self.d["proj_color"], dmg=self.roll_dmg(), radius=5, life=1.6,
                                                kind="arrow"))
            sfx.play("arrow", 0.4)
        elif ai == "caster":
            world.effects.append(Telegraph("circle", 0.85, self.roll_dmg() * 1.5, p.x, p.y, 55,
                                           color=(210, 70, 255), sound="fire"))
            sfx.play("magic", 0.4)

    def chase(self, dt, world, dx, dy, dist, spd):
        if self.has_los:
            vx, vy = dx / dist, dy / dist
        else:
            tgt = world.flow_step(self.x, self.y)
            if tgt is None:
                return
            vx, vy = tgt[0] - self.x, tgt[1] - self.y
            n = math.hypot(vx, vy) or 1
            vx, vy = vx / n, vy / n
        self.step(world, vx, vy, spd, dt)

    def step(self, world, vx, vy, spd, dt):
        world.move_circle(self, vx * spd * dt, vy * spd * dt)
        self.facing = math.atan2(vy, vx)
        self.phase += dt * spd / 13
        self.moving = True

    # ------------------------------------------------------------------ rendu
    def render(self, fr, t):
        sc = self.r / 14 * 0.95
        tint = (255, 70, 50) if self.state == "windup" else ((150, 210, 255) if self.slow > 0 else None)
        if self.burn > 0:
            tint = tuple(min(255, c + 40) for c in self.burn_col)
        rise = min(1.0, self.spawn_t / 0.35) if self.minion else 1.0
        z = -40 * sc * (1 - rise)
        models.humanoid(fr, self.x, self.y, z, self.facing, self.phase, models.MONSTER_SPECS[self.spec_id], sc=sc,
                        flash=self.flash > 0, tint_col=tint, moving=self.moving)
        if self.curse > 0:
            fr.decal(self.x, self.y, self.r * 1.7, self.r * 1.7, (170, 90, 230), 0.55, kind=1, inner=0.7, rot=t)
            fr.glow(self.x, self.y, self.height() + 10 + 3 * math.sin(t * 5), 12, (190, 110, 255), 0.8)
        if self.elite:
            k = 0.5 + 0.5 * math.sin(t * 4 + self.phase)
            fr.decal(self.x, self.y, self.r * 1.9, self.r * 1.9, (255, 200, 70), 0.35 + 0.25 * k, kind=1, inner=0.78)
            fr.light(self.x, self.y, 30, 120, (255, 190, 80), 0.5)
        if self.state == "windup" and self.d["ai"] == "melee":
            fr.decal(self.x, self.y, self.reach_draw(), self.reach_draw(), (255, 60, 40), 0.35, kind=3,
                     rot=self.atk_angle, p1=1.0, inner=0.2)

    def reach_draw(self):
        return self.d["range"] + self.r + 14

    def height(self):
        return (self.r / 14 * 0.95) * 52


# =========================================================================== projectiles
class Projectile:
    def __init__(self, x, y, ang, speed, owner, color, mult=1.0, dmg=0.0, radius=6, life=1.2, pierce=0,
                 kind="bolt", explode=0, slow=0.0, knock=0):
        self.x, self.y = x, y
        self.ang = ang
        self.vx, self.vy = math.cos(ang) * speed, math.sin(ang) * speed
        self.speed = speed
        self.owner, self.color, self.mult, self.dmg = owner, color, mult, dmg
        self.radius, self.life, self.pierce, self.kind = radius, life, pierce, kind
        self.explode, self.slow, self.knock = explode, slow, knock
        self.hit = set()
        self.alive = True
        self.t = 0
        self.z = 22

    def update(self, dt, world):
        self.life -= dt
        self.t += dt
        if self.life <= 0:
            self.end(world)
            return
        n = int(self.speed * dt / 10) + 1
        for _ in range(n):
            self.x += self.vx * dt / n
            self.y += self.vy * dt / n
            if world.solid_at(self.x, self.y):
                self.end(world)
                return
            if self.owner == "player":
                for m in world.monsters:
                    if m.dead or not m.targetable or id(m) in self.hit:
                        continue
                    rr = m.r + self.radius + 6
                    if (m.x - self.x) ** 2 + (m.y - self.y) ** 2 < rr * rr:
                        self.hit.add(id(m))
                        if self.explode:
                            self.end(world)
                            return
                        world.player_hit(m, self.mult, knock=self.knock, ang=self.ang, slow=self.slow)
                        world.particles.emit(self.x, self.y, self.color, n=5, speed=90, life=0.25, size=3, z=self.z)
                        if self.pierce <= 0:
                            self.alive = False
                            return
                        self.pierce -= 1
            else:
                p = world.player
                rr = p.r + self.radius
                if (p.x - self.x) ** 2 + (p.y - self.y) ** 2 < rr * rr and not p.dead:
                    p.take_damage(world, self.dmg)
                    self.alive = False
                    return
        if self.kind in ("fire", "bolt") and random.random() < 0.8:
            world.particles.emit(self.x, self.y, self.color, n=1, speed=20, life=0.3, size=self.radius * 0.6,
                                 z=self.z, zs=0.2)

    def end(self, world):
        self.alive = False
        if self.explode:
            from .fx import RingFX as _R
            world.damage_circle(self.x, self.y, self.explode, self.mult, knock=40)
            world.particles.emit(self.x, self.y, self.color, n=26, speed=220, life=0.45, size=4, z=12, up=100)
            world.particles.emit(self.x, self.y, (255, 230, 150), n=10, speed=110, life=0.3, size=3, z=12)
            world.effects.append(_R(self.x, self.y, 10, self.explode, 0.3, self.color, 5))
            world.flash_light(self.x, self.y, self.explode * 3, self.color)
            world.shake_screen(3)
            sfx.play("explosion", 0.5)
        else:
            world.particles.emit(self.x, self.y, self.color, n=4, speed=60, life=0.2, size=2, z=self.z)

    def render(self, fr, t):
        z = self.z
        if self.kind == "arrow":
            ca, sa = math.cos(self.ang), math.sin(self.ang)
            tip = (self.x + ca * 10, self.y + sa * 10, z)
            tail = (self.x - ca * 12, self.y - sa * 12, z)
            models.Painter(fr).rod(tail, tip, 1.0, (150, 110, 70), (0, 0, 1))
            models.Painter(fr).rod(tip, (tip[0] + ca * 5, tip[1] + sa * 5, z), 2.0, (200, 200, 210), (0, 0, 1),
                                   mesh="cone")
            if self.owner == "enemy":
                fr.glow(self.x, self.y, z, 12, (255, 140, 90), 0.5)
        else:
            r = self.radius * 1.2
            fr.part("sphere", (self.x, self.y, z), (r, 0, 0), (0, 0, r), (0, r, 0), self.color, 1.0)
            fr.glow(self.x, self.y, z, r * 5, self.color, 0.9)
            fr.light(self.x, self.y, z, 160 if self.explode else 110, self.color, 1.0)


# =========================================================================== butin
class Loot:
    def __init__(self, x, y, kind, item=None, amount=0, tier=1):
        self.x, self.y = x, y
        self.kind, self.item, self.amount, self.tier = kind, item, amount, tier
        a = random.random() * math.tau
        sp = random.uniform(30, 110)
        self.vx, self.vy = math.cos(a) * sp, math.sin(a) * sp
        self.z, self.vz = 0.0, random.uniform(160, 240)
        self.t = random.random()
        self.r = 6
        self.warned = False

    def update(self, dt, world):
        self.t += dt
        if self.vz or self.z > 0:
            self.vz -= 800 * dt
            self.z += self.vz * dt
            world.move_circle(self, self.vx * dt, self.vy * dt)
            if self.z <= 0:
                self.z = 0
                self.vz = 0 if abs(self.vz) < 80 else -self.vz * 0.35
                self.vx *= 0.5
                self.vy *= 0.5

    def render(self, fr, t):
        x, y, z = self.x, self.y, self.z
        if self.kind == "gold":
            for i in range(min(5, 1 + self.amount // 8)):
                ox, oy = (i % 3) * 5 - 5, (i // 3) * 5
                fr.part("cylinder", (x + ox, y + oy, z + 1.2 + i * 0.4), (4, 0, 0), (0, 0, 1.2), (0, 4, 0),
                        (240, 196, 70), 0.3)
            fr.glow(x, y, z + 6, 14, (255, 200, 80), 0.35)
        elif self.kind == "orb":
            zz = z + 12 + 3 * math.sin(self.t * 4)
            fr.part("sphere", (x, y, zz), (6, 0, 0), (0, 0, 6), (0, 6, 0), (230, 40, 50), 0.8)
            fr.glow(x, y, zz, 30, (255, 60, 60), 0.8)
        elif self.kind == "item":
            models.loot_item(fr, x, y, z, RARITY_COLORS[self.item["rarity"]], self.t, self.item["rarity"])
        elif self.kind == "anima":
            zz = z + 20 + 4 * math.sin(self.t * 3)
            col = (120, 190, 255)
            fr.part("sphere", (x, y, zz), (7, 0, 0), (0, 0, 7), (0, 7, 0), (200, 230, 255), 1.0)
            fr.glow(x, y, zz, 60, col, 1.0)
            for i in range(3):
                a = self.t * 3 + i * math.tau / 3
                fr.glow(x + math.cos(a) * 16, y + math.sin(a) * 16, zz + math.sin(a * 2) * 6, 12, col, 0.9)
            fr.light(x, y, 30, 180, col, 1.0)


# =========================================================================== interactifs
class Interactable:
    radius = 70
    prompt = "Interagir"
    r = 16
    label = None

    def __init__(self, x, y):
        self.x, self.y = x, y

    def can_interact(self, world):
        return True

    def interact(self, world):
        pass

    def render(self, fr, t):
        pass


class Chest(Interactable):
    prompt = "Ouvrir"

    def __init__(self, x, y):
        super().__init__(x, y)
        self.opened = False

    def can_interact(self, world):
        return not self.opened

    def interact(self, world):
        self.opened = True
        world.open_chest(self)

    def render(self, fr, t):
        models.chest(fr, self.x, self.y, self.opened, t)
        if not self.opened:
            fr.light(self.x, self.y, 30, 100, (255, 200, 90), 0.6)


class Portal(Interactable):
    def __init__(self, x, y, prompt, action, color=(120, 100, 255)):
        super().__init__(x, y)
        self.prompt = prompt
        self.action = action
        self.color = color

    def interact(self, world):
        self.action(world)

    def render(self, fr, t):
        models.portal(fr, self.x, self.y, self.color, t)


class NPC(Interactable):
    def __init__(self, x, y, name, prompt, spec, action, facing=math.pi / 2, work=False):
        super().__init__(x, y)
        self.label = name
        self.prompt, self.spec, self.action = prompt, spec, action
        self.facing = facing
        self.work = work     # frappe l'enclume en boucle

    def interact(self, world):
        self.action(world)

    def render(self, fr, t):
        swing = -1.4 * max(0.0, math.sin(t * 2.6)) if self.work else 0.0
        models.humanoid(fr, self.x, self.y, 0, self.facing + (0.0 if self.work else 0.1 * math.sin(t * 0.7)), t * 2,
                        self.spec, sc=1.05, moving=False, swing=swing)


class Campfire(Interactable):
    radius = 0

    def can_interact(self, world):
        return False

    def render(self, fr, t):
        models.campfire(fr, self.x, self.y, t)


class Prop(Interactable):
    """Décor 3D sans interaction (tentes, enclume, tonneaux...)."""
    radius = 0

    def __init__(self, x, y, fn, *args):
        super().__init__(x, y)
        self.fn, self.args = fn, args

    def can_interact(self, world):
        return False

    def render(self, fr, t):
        self.fn(fr, self.x, self.y, *self.args)
