"""Entités : joueur, monstres, projectiles, butin et objets interactifs (logique + rendu 3D)."""
import math
import random
from collections import defaultdict

from . import coins, looks, sfx, talents
from .data import (ATTR_K, CLASSES, SPELLS, BUFFS, MONSTERS, ATTRS, ELITE_AFFIXES, MAX_LEVEL, MONSTER_XP,
                   POINTS_PER_LEVEL, ANIMA_POWERS, POTION_CD, POTION_HEAL, ROLL_CD, ROLL_DUR, ROLL_DIST, xp_needed,
                   floor_scaling)
from .fx import RingFX
from .items import SLOTS, ART_SLOTS, EQUIP_SLOTS, item_stats, ench_stats, ench_spent, rescale_old
from .r3d import models
from .settings import RARITY_COLORS

SPELL_SLOTS = 4          # sorts équipés (touches 1 à 4)


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
        self.tears = data.get("tears", 0)          # Larmes d'oubli : réinitialisation des attributs
        self.talents = talents.clean(data.get("talents"), self.cls_id, self.level)
        self.loadout = list(data.get("loadout") or [])
        self.tal = {}
        self.stand_used = False
        # bourse en pièces de cuivre (anciennes sauvegardes : une seule monnaie, l'or, convertie)
        self.money = data["money"] if "money" in data else int(data.get("gold", 0) * coins.OLD_GOLD)
        self.max_floor = data.get("max_floor", 1)
        self.cleared = set(data.get("cleared", []))
        eq = data.get("equipment", {})
        self.equipment = {s: eq.get(s) for s in EQUIP_SLOTS}
        self.inventory = list(data.get("inventory", []))
        self.stash = list(data.get("stash", []))       # coffre de la taverne de Cendreval
        self._unique_artifacts()
        for it in self.all_items():
            it.setdefault("ench", [])
            rescale_old(it)
        self.kills = data.get("kills", 0)
        self.deaths = data.get("deaths", 0)
        from . import quests
        self.quests = quests.clean(data.get("quests"))
        self.tutorial = data.get("tutorial")      # étape du tutoriel en cours (None : pas de tutoriel)
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
        self.clock = 0.0          # horloge des animations
        self.anim_state, self.anim_start, self.anim_len, self.anim_speed = None, 0.0, 0.0, 1.0
        self.snare = 0.0          # entravé (toile) : fortement ralenti
        self.hexed = 0.0          # chaînes de Deathstrake : +30% de dégâts subis
        self.atk_total = 0.5
        self.attack_lock = 0.0
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
        self.buffs_total = {}
        self.dead = False
        self.hp = self.mana = 1
        self.recompute()
        self.full_restore()

    @property
    def cls(self):
        return CLASSES[self.cls_id]

    @property
    def known_spells(self):
        """Sorts de la classe, puis ceux débloqués par les talents."""
        return list(self.cls["spells"]) + [s for s in talents.spells_of(self.talents) if s not in self.cls["spells"]]

    @property
    def spells(self):
        """Les 4 sorts équipés (touches 1 à 4) ; un emplacement vide reçoit le premier sort connu non équipé."""
        known = self.known_spells
        out = [s for i, s in enumerate(self.loadout) if s in known and s not in self.loadout[:i]][:SPELL_SLOTS]
        out += [s for s in known if s not in out][:SPELL_SLOTS - len(out)]
        self.loadout = out
        return out

    def equip_spell(self, slot, sid):
        """Place un sort connu dans l'emplacement ; s'il était déjà équipé ailleurs, les deux sorts s'échangent."""
        lo = list(self.spells)
        if sid not in self.known_spells or not 0 <= slot < len(lo):
            return
        if sid in lo:
            j = lo.index(sid)
            lo[j], lo[slot] = lo[slot], sid
        else:
            lo[slot] = sid
        self.loadout = lo

    def all_items(self):
        return [it for it in list(self.equipment.values()) + self.inventory + self.stash if it]

    def to_save(self):
        return {"name": self.name, "cls": self.cls_id, "level": self.level, "xp": self.xp, "alloc": self.alloc,
                "points": self.points, "tears": self.tears, "money": self.money, "max_floor": self.max_floor,
                "cleared": sorted(self.cleared), "equipment": self.equipment, "inventory": self.inventory,
                "stash": self.stash,
                "kills": self.kills, "deaths": self.deaths, "created_at": self.created_at, "look": dict(self.look),
                "talents": dict(self.talents), "loadout": list(self.spells), "quests": self.quests,
                "tutorial": self.tutorial}

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
        self.snare = self.hexed = 0.0
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
        s = {k: c["attrs"].get(k, 0) + self.alloc[k] + gear[k] for k in ATTRS}
        s["max_hp"] = ((c["hp"] + c["hp_lvl"] * (self.level - 1) + s["vit"] * ATTR_K["vit_hp"] + gear["vie"])
                       * (1 + av("vigueur") / 100) * (1 + ench["vitalite"] / 100) * (1 + tv("max_hp_pct", 0) / 100))
        s["max_mana"] = ((c["mana"] + c["mana_lvl"] * (self.level - 1) + s["int"] * ATTR_K["int_mana"] + gear["mana"])
                         * (1 + tv("mana_pct", 0) / 100))
        s["armor"] = ((armor + gear["armure"] + s["force"] * ATTR_K["force_armor"] + s["resistance"] * ATTR_K["res_armor"])
                      * (1 + tv("armor_pct", 0) / 100))
        s["dmg_min"], s["dmg_max"] = dmin, dmax
        s["dmg_pct"] = gear["dmg_pct"] + av("rage") + ench["tranchant"] + tv("dmg_pct", 0)
        s["dmg_mult"] = (1 + s[c["primary"]] / 100) * (1 + s["dmg_pct"] / 100)
        s["crit"] = min(60, 5 + s["dex"] * ATTR_K["dex_crit"] + s["chance"] * ATTR_K["chance_crit"] + gear["crit"] + av("precision") + ench["acuite"] + tv("crit", 0))
        s["crit_mult"] = 1.75 + tv("crit_dmg", 0) / 100
        s["atk_speed"] = s["dex"] * ATTR_K["dex_speed"] + gear["atk_speed"] + av("frenesie") + ench["vivacite"] + tv("atk_speed", 0)
        s["lifesteal"] = gear["lifesteal"] + av("soif") + tv("lifesteal", 0)
        s["mana_regen"] = ((c["mana_regen"] + gear["mana_regen"] + s["harmonie"] * ATTR_K["harm_regen"])
                           * (1 + av("flux") / 100)
                           * (1 + (tv("mana_regen_pct", 0) + s["int"] * ATTR_K["int_regen"]) / 100))
        # chaque attribut sert toutes les classes (l'attribut principal ajoute en plus +1% de dégâts par point)
        s["basic_pct"] = s["force"] * ATTR_K["force_basic"] + tv("basic_pct", 0)
        s["spell_pct"] = s["int"] * ATTR_K["int_spell"] + tv("spell_pct", 0)
        s["move_speed"] = (s["endurance"] * ATTR_K["end_move"] + gear["move_speed"] + av("ombre") + ench["celerite"]
                           + tv("move_speed", 0))
        s["mana_cost"] = min(40, s["harmonie"] * ATTR_K["harm_cost"])      # -% de coût en mana des sorts
        s["snare_res"] = min(60, s["resistance"] * ATTR_K["res_snare"])    # entraves plus courtes
        s["cdr"] = min(50, s["foi"] * ATTR_K["foi_cdr"] + gear["cdr"] + av("esprit") + ench["recharge"] + tv("cdr", 0))
        s["gold_find"] = s["chance"] * ATTR_K["chance_gold"] + gear["gold_find"] + av("cupidite") + tv("gold_find", 0)
        s["heal_pct"] = s["foi"] * ATTR_K["foi_heal"]            # efficacité des soins reçus
        s["loot_pct"] = s["chance"] * ATTR_K["chance_drop"]       # chances de butin en plus
        s["speed"] = c["speed"] * (1 + s["move_speed"] / 100)
        s["dr_bonus"] = (av("carapace") + ench["rempart"] + tv("dr", 0) + s["resistance"] * ATTR_K["res_dr"]) / 100
        s["ench"] = dict(ench)
        self.stats = s
        end_roll = min(40, s["endurance"] * ATTR_K["end_roll"])
        end_potion = min(40, s["endurance"] * ATTR_K["end_potion"])
        self.potion_total = POTION_CD * (1 - ench["potion_vive"] / 100) * (1 - end_potion / 100)
        self.roll_total = (ROLL_CD * (1 - ench["agilite"] / 100) * (1 - tv("roll_cd", 0) / 100)
                           * (1 - end_roll / 100))
        self.hp = min(self.hp, s["max_hp"])
        self.mana = min(self.mana, s["max_mana"])

    def _unique_artifacts(self):
        """Sauvegardes anciennes : un artefact en double retourne dans le sac."""
        seen = set()
        for s in ART_SLOTS:
            it = self.equipment.get(s)
            if it and it["art"] in seen:
                self.inventory.append(it)
                self.equipment[s] = None
            elif it:
                seen.add(it["art"])

    def ench(self, eid):
        return self.stats["ench"].get(eid, 0)

    def damage_reduction(self):
        armor = self.stats["armor"] * (1 + self.buff_sum("armor_pct") / 100)
        dr = armor / (armor + 220) + self.stats["dr_bonus"] + self.buff_sum("dr") / 100
        if self.t("low_hp_dr") and self.hp < self.stats["max_hp"] * 0.35:
            dr += self.t("low_hp_dr") / 100
        return min(0.85, dr)

    def dps_estimate(self):
        s = self.stats
        avg = (s["dmg_min"] + s["dmg_max"]) / 2 * s["dmg_mult"] * (1 + s["crit"] / 100 * (s["crit_mult"] - 1))
        mult = self.cls["attack"]["mult"] * (1 + s["basic_pct"] / 100)
        return avg * mult / (self.cls["attack"]["cd"] / (1 + s["atk_speed"] / 100))

    def roll_damage(self, mult, crit_bonus=0.0):
        s = self.stats
        d = random.uniform(s["dmg_min"], s["dmg_max"]) * mult * s["dmg_mult"]
        d *= 1 + self.buff_sum("dmg_pct") / 100
        if self.t("berserk"):
            missing = 1 - max(0.0, self.hp) / s["max_hp"]
            d *= 1 + self.t("berserk") / 100 * missing
        crit = random.random() * 100 < s["crit"] + crit_bonus
        if crit:
            d *= s["crit_mult"]
        return d, crit

    def mana_cost(self, sid):
        """Coût en mana d'un sort, allégé par l'Harmonie."""
        return round(SPELLS[sid]["mana"] * (1 - self.stats.get("mana_cost", 0) / 100))

    def heal(self, amount):
        """Soin reçu (potion, vol de vie, sorts...), renforcé par la Foi."""
        self.hp = min(self.stats["max_hp"], self.hp + amount * (1 + self.stats.get("heal_pct", 0) / 100))

    def speed(self):
        return self.stats["speed"] * (1 + self.buff_sum("move_pct") / 100) * (0.45 if self.snare > 0 else 1.0)

    def buff_sum(self, key):
        """Somme d'une statistique sur les effets temporaires actifs (data/buffs.json ; "v" = valeur transmise)."""
        total = 0.0
        for bid in self.buffs:
            v = BUFFS.get(bid, {}).get(key)
            if v is not None:
                total += self.buffs_val.get(bid, 0) if v == "v" else v
        return total

    def take_damage(self, world, amount, attacker=None, melee=False):
        if self.invuln > 0 or self.dead or self.leap or self.dash:
            return 0
        if random.random() * 100 < self.ench("esquive"):
            world.add_text(self.x, self.y, 50, "Esquive", (200, 230, 255), 16)
            return 0
        dmg = amount * (1 - self.damage_reduction()) * (1.3 if self.hexed > 0 else 1.0)
        self.hp -= dmg
        self.flash = 0.12
        if not (self.anim_state and self.clock - self.anim_start < self.anim_len):
            self.play("hit", 0.35)
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

    # ------------------------------------------------------------------ animations (héros animés)
    def play(self, state, length=None):
        """Joue une animation ponctuelle (attaque, sort, roulade, coup reçu, mort), accélérée pour tenir en length s."""
        from .r3d import rig
        d = rig.anim_duration(self.spec, state)
        self.anim_state, self.anim_start = state, self.clock
        self.anim_len = length or d
        self.anim_speed = d / self.anim_len if length else 1.0

    def current_anim(self):
        el = self.clock - self.anim_start
        if self.dead:
            return "death", el * self.anim_speed if self.anim_state == "death" else 5.0
        if self.anim_state and el < self.anim_len:
            return self.anim_state, el * self.anim_speed
        if self.moving or self.dash:
            return "run", self.clock * self.speed() / 205
        return ("idle_melee" if self.cls["attack"]["kind"] == "melee" else "idle"), self.clock

    def start_roll(self, world, dx, dy):
        if self.roll_cd > 0 or self.leap or self.dash or self.dead:
            return
        ex, ey = world.reachable(self.x, self.y, self.x + dx * ROLL_DIST, self.y + dy * ROLL_DIST, self.r)
        self.dash = {"sx": self.x, "sy": self.y, "ex": ex, "ey": ey, "t": 0.0, "dur": ROLL_DUR, "roll": True}
        self.invuln = ROLL_DUR + 0.08
        self.roll_cd = self.roll_total
        self.facing = math.atan2(dy, dx)
        self.play("roll", ROLL_DUR + 0.12)
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
        self.attack_lock = max(0.0, self.attack_lock - dt)
        self.clock += dt
        self.snare = max(0.0, self.snare - dt / (1 - self.stats.get("snare_res", 0) / 100))
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
        if self.invuln > 0 and not (self.leap or self.dash) and int(self.invuln * 20) % 2 and not self.dead:
            return
        anim, anim_t = self.current_anim()
        if self.spec.get("rig"):
            sc = 1.0          # la roulade est jouée par l'animation
        models.humanoid(fr, self.x, self.y, lift, self.facing, self.walk, self.spec, sc=sc,
                        flash=self.flash > 0, swing=self.swing, moving=self.moving or bool(self.dash),
                        anim=anim, anim_t=anim_t)
        for bid in self.buffs:
            b = BUFFS.get(bid, {})
            vis, col = b.get("visual"), b.get("color", (255, 255, 255))
            if vis == "ring":
                fr.decal(self.x, self.y, 30, 30, col, 0.5, kind=1, inner=0.75)
            elif vis == "bubble":
                fr.part("sphere", (self.x, self.y, 26), (26, 0, 0), (0, 0, 32), (0, 26, 0), col, 0.25, additive=True)
            elif vis == "glow":
                fr.glow(self.x, self.y, 4, 26, col, 0.6)


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
        self.xp = d["xp"] * MONSTER_XP * (1 + 0.4 * (floor - 1))
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
                if not getattr(self, "boss", False) and random.random() < 0.6:
                    sfx.play("growl", 0.35 + 0.4 * (1 - dist / 340))     # il vous a vu
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
        z = -40 * sc * (1 - rise) + self.lift()
        anim = anim_t = None
        if self.state == "windup":           # modèles animés : le coup se prépare pendant l'avertissement
            anim = "attack_ranged" if self.d.get("ai") in ("ranged", "caster") else "attack_melee"
            anim_t = max(0.0, self.d.get("windup", 0.5) - self.windup) * 1.4
        models.humanoid(fr, self.x, self.y, z, self.facing, self.phase, models.MONSTER_SPECS[self.spec_id], sc=sc,
                        flash=self.flash > 0, tint_col=tint, moving=self.moving, anim=anim, anim_t=anim_t)
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

    def lift(self):
        """Hauteur au-dessus du sol (bond d'un boss)."""
        return 0.0

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
                for m in world.near_monsters(self.x, self.y, self.radius + 6):
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
            for i in range(min(5, 1 + self.amount // 80)):
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
        elif self.kind == "tear":
            zz = z + 14 + 3 * math.sin(self.t * 3)
            fr.part("sphere", (x, y, zz), (4, 0, 0), (0, 0, 6), (0, 4, 0), (200, 170, 255), 1.0)
            fr.part("cone", (x, y, zz + 8), (3, 0, 0), (0, 0, 5), (0, 3, 0), (200, 170, 255), 1.0)
            fr.glow(x, y, zz, 40, (170, 120, 255), 0.9)
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


class Stash(Interactable):
    """Coffre de stockage de la ville : ouvre la fenêtre du coffre."""
    prompt = "Ouvrir le coffre"
    label = "Coffre"

    def __init__(self, x, y, action):
        super().__init__(x, y)
        self.action = action

    def interact(self, world):
        self.action(world)

    def render(self, fr, t):
        models.stash_chest(fr, self.x, self.y, t)


class Portal(Interactable):
    def __init__(self, x, y, prompt, action, color=(120, 100, 255), grand=False):
        super().__init__(x, y)
        self.prompt = prompt
        self.action = action
        self.color = color
        self.grand = grand          # portail monumental du campement (arche dans le décor)

    def interact(self, world):
        self.action(world)

    def render(self, fr, t):
        if self.grand:
            models.grand_portal_veil(fr, self.x, self.y, self.color, t)
        else:
            models.portal(fr, self.x, self.y, self.color, t)


class NPC(Interactable):
    WALK_SPEED = 42
    STOP_DIST = 120      # s'arrête et se tourne vers le héros qui s'approche

    def __init__(self, x, y, name, prompt, spec, action, facing=math.pi / 2, work=False, npc_id=None, route=None):
        super().__init__(x, y)
        self.label = name
        self.prompt, self.spec, self.action = prompt, spec, action
        self.facing = facing
        self.work = work     # frappe l'enclume en boucle
        self.npc_id = npc_id
        self.route = route or []      # tournée en boucle (points en unités logiques)
        self.leg = 1 % max(1, len(self.route))
        self.pause = random.uniform(0.5, 3.0)
        self.walking = False
        self.bubble = None           # (texte, fin) : bulle de dialogue au-dessus de la tête
        self.greet_at = 0.0          # prochain salut possible (temps du monde)

    def say(self, world, text, duration=None):
        """Affiche une réplique dans une bulle (durée selon la longueur du texte)."""
        self.bubble = (text, world.time + (duration or min(9.0, 2.5 + len(text) / 22)))

    def interact(self, world):
        self.action(world)

    def update(self, dt, world):
        self.walking = False
        p = world.player
        if math.hypot(p.x - self.x, p.y - self.y) < self.STOP_DIST:
            self._turn(math.atan2(p.y - self.y, p.x - self.x), dt)
            return
        if len(self.route) < 2:
            return
        if self.pause > 0:
            self.pause -= dt
            return
        tx, ty = self.route[self.leg]
        dx, dy = tx - self.x, ty - self.y
        d = math.hypot(dx, dy)
        step = self.WALK_SPEED * dt
        if d <= step:
            self.x, self.y = tx, ty
            self.leg = (self.leg + 1) % len(self.route)
            self.pause = random.uniform(1.5, 5.0)
            return
        self.x += dx / d * step
        self.y += dy / d * step
        self._turn(math.atan2(dy, dx), dt)
        self.walking = True

    def _turn(self, ang, dt):
        diff = (ang - self.facing + math.pi) % math.tau - math.pi
        self.facing += diff * min(1.0, dt * 6)

    def render(self, fr, t):
        swing = -1.4 * max(0.0, math.sin(t * 2.6)) if self.work else 0.0
        sway = 0.0 if self.work or self.walking else 0.1 * math.sin(t * 0.7)
        anim = "work" if self.work else ("walk" if self.walking else None)
        models.humanoid(fr, self.x, self.y, 0, self.facing + sway, t * 2, self.spec, sc=1.05, moving=self.walking,
                        swing=swing, anim=anim)


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


# =========================================================================== secrets et pièges des étages
class SecretWall(Interactable):
    """Mur fissuré : le briser ouvre le passage vers une salle cachée."""
    prompt = "Briser le mur fissuré"
    radius = 80

    def __init__(self, x, y, tile):
        super().__init__(x, y)
        self.tile = tile
        self.broken = False

    def can_interact(self, world):
        return not self.broken

    def interact(self, world):
        from .dungeon import FLOOR
        self.broken = True
        tx, ty = self.tile
        world.tiles[ty][tx] = FLOOR
        world.flow_src = None
        world.minimap.refresh([(tx, ty)])
        world.shake_screen(7)
        sfx.play("explosion", 0.7)
        world.particles.emit(self.x, self.y, (150, 140, 128), n=40, speed=200, life=0.9, size=5, glow=False,
                             gravity=600, up=240, z=30)
        world.message("Un passage secret s'ouvre !", (255, 226, 140), 4)
        world.interactables.remove(self)

    def render(self, fr, t):
        stone, dark = (112, 104, 96), (40, 34, 30)
        fr.box(self.x, self.y, 0, 20, 20, 36, stone)
        for i, (a, h) in enumerate(((0.4, 10), (-0.5, 20), (0.8, 28))):      # fissures
            fr.part("cube", (self.x - 20.5, self.y + 4 * a, h), (0.6, 0, 0), (1.2, 0, 7), (0, 0.8, 3 * a), dark)
            fr.part("cube", (self.x + 4 * a, self.y + 20.5, h), (1.2, 0, 7), (0, 0.6, 0), (3 * a, 0, 0.8), dark)
        k = 0.5 + 0.5 * math.sin(t * 2.5)
        fr.glow(self.x, self.y, 30, 22, (255, 220, 140), 0.18 + 0.12 * k)


class AnimaShrine(Interactable):
    """Autel d'anima caché : offre un choix de pouvoir d'anima, une seule fois."""
    prompt = "Prier à l'autel d'anima"
    radius = 80

    def __init__(self, x, y):
        super().__init__(x, y)
        self.used = False

    def can_interact(self, world):
        return not self.used

    def interact(self, world):
        self.used = True
        world.open_anima_choice()

    def render(self, fr, t):
        fr.box(self.x, self.y, 0, 16, 16, 8, (84, 80, 92), mesh="cylinder")
        fr.box(self.x, self.y, 8, 10, 10, 10, (104, 100, 112), mesh="cylinder")
        if not self.used:
            z = 30 + 3 * math.sin(t * 2)
            fr.part("sphere", (self.x, self.y, z), (7, 0, 0), (0, 0, 7), (0, 7, 0), (140, 220, 255), 1.0)
            fr.glow(self.x, self.y, z, 46, (120, 200, 255), 0.9)
            fr.light(self.x, self.y, z, 220, (120, 200, 255), 1.2)


class SpikeTrap:
    """Plaque à pointes : repos, avertissement (rougeoiement), puis les pointes jaillissent."""
    IDLE, WARN, UP = 2.6, 0.7, 0.55

    def __init__(self, x, y, dmg, phase):
        self.x, self.y, self.dmg = x, y, dmg
        self.t = phase
        self.hit = False

    def update(self, dt, world):
        cyc = self.IDLE + self.WARN + self.UP
        self.t = (self.t + dt) % cyc
        up = self.t >= self.IDLE + self.WARN
        p = world.player
        if not up:
            self.hit = False
        elif not self.hit and abs(p.x - self.x) < 20 + p.r * 0.5 and abs(p.y - self.y) < 20 + p.r * 0.5:
            self.hit = True
            p.take_damage(world, self.dmg)

    def render(self, fr, t):
        fr.box(self.x, self.y, 0, 18, 18, 0.8, (70, 64, 60))
        warn = self.IDLE <= self.t < self.IDLE + self.WARN
        up = self.t >= self.IDLE + self.WARN
        if warn:
            fr.decal(self.x, self.y, 20, 20, (255, 70, 40), 0.25 + 0.3 * math.sin(t * 20) ** 2, kind=4)
        h = 14 if up else 1.5
        for ox in (-10, 0, 10):
            for oy in (-10, 0, 10):
                fr.part("cone", (self.x + ox, self.y + oy, h / 2), (2.2, 0, 0), (0, 0, h / 2), (0, 2.2, 0),
                        (190, 186, 180))
