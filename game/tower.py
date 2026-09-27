"""Un étage de Cendrespire : salles de monstres, sceau du gardien, boss, portail de sortie."""
import math
import random

from . import seals, sfx
from .bosses import make_boss
from .data import MONSTERS, ELITE_AFFIXES, floor_name, floor_boss, boss_floor
from .dungeon import Dungeon, FLOOR, WALL
from .entities import Monster, Chest, Portal, Loot, SecretWall, AnimaShrine, SpikeTrap, NPC, Prop
from .fx import RingFX
from .items import generate_item
from .panels import DeathPanel, ForgePanel
from .r3d import level, models
from .settings import TILE, GOLD_BRIGHT, WHITE
from .world import World


TOWER_MUSIC = ("inside", "inside2", "inside3")    # une au hasard à chaque étage, jouée en boucle
SURVIVOR_LINES = (
    "C'est un monstre... Il est beaucoup trop puissant. Je l'ai vu balayer une compagnie entière.",
    "Des boules de feu, des éclairs, du givre... comme s'il avait volé les pouvoirs de tous ceux qui sont tombés ici.",
    "S'il plante un totem vert, détruisez-le tout de suite, ou il se relèvera encore et encore.",
    "Quand il lève son écu doré, vos coups glissent sur lui. Attendez que ça passe.",
    "Et quand il s'enrage... reculez. Croyez-moi. Moi, je ne remets plus les pieds dans cette arène.",
)


class TowerScene(World):
    is_tower = True

    def __init__(self, game, player, floor):
        self.floor = floor
        self.arena = boss_floor(floor)      # étage BOSS : une salle d'entrée, un couloir et la grande arène
        rng = random.Random()
        if self.arena:
            d = Dungeon(80, 60)
            d.generate(rng, n_rooms=2, boss_size=(29, 23))
            d.secrets, d.traps = [], []
        else:
            # étages vastes : de nombreuses salles, des cachettes derrière des murs fissurés et des pièges
            d = Dungeon(170, 120)
            d.generate(rng, n_rooms=56 + min(10, floor))
        # les murs fissurés sont dessinés à part (ils se brisent) : le décor fixe les traite comme du sol
        for _room, (tx, ty), _kind in d.secrets:
            d.tiles[ty][tx] = FLOOR
        super().__init__(game, player, d, level.floor_theme(floor), rng)
        for _room, (tx, ty), _kind in d.secrets:
            d.tiles[ty][tx] = WALL
        player.reset_run()
        sx, sy = d.start_room.center_px
        player.x, player.y = sx, sy
        self.cam.tx, self.cam.ty = sx, sy
        self.kills = 0
        self.seal_kind = "kills"
        self.seal_have = 0             # avancement des conditions à objets (fragments, brasiers, élites, clé)
        self.run_gold = 0
        self.barrier_active = True
        self.boss_started = False
        self.boss_dead = False
        self.populate()
        if self.arena:
            self.barrier_active = False
            self.show_banner(floor_name(floor), f"Étage {floor} · étage du boss", (200, 140, 255), 4.5)
            self.message(f"{self.boss.name}, {self.boss.title.lower()}, vous attend dans l'arène.", (210, 170, 255), 8)
        else:
            name, text = seals.KINDS[self.seal_kind]
            self.show_banner(floor_name(floor), f"Étage {floor} · Sceau : {name}", WHITE, 4.5)
            self.message(text, (220, 214, 200), 9)
        sfx.play("portal")
        sfx.music(sfx.pick_music(TOWER_MUSIC), restart=True)

    def floor_level(self):
        return self.floor

    # ------------------------------------------------------------------ peuplement
    def random_point(self, room, r=18, margin=1):
        for _ in range(60):
            x = self.rng.uniform(room.x + margin + 0.5, room.x + room.w - margin - 0.5) * TILE
            y = self.rng.uniform(room.y + margin + 0.5, room.y + room.h - margin - 0.5) * TILE
            if not self.blocked(x, y, r):
                return x, y
        return room.center_px

    def populate(self):
        rng, f, d = self.rng, self.floor, self.dungeon
        self.traps = []
        if self.arena:            # l'esprit de la tour, seul ; la forgeronne, un rescapé et un coffre à l'entrée
            self.total, self.seal_needed = 0, 1
            self.add_camp(d.start_room)
            bx, by = d.boss_room.center_px
            self.boss = make_boss(floor_boss(f), bx, by, f, d.boss_room)
            self.monsters.append(self.boss)
            return
        pool = [mid for mid, m in MONSTERS.items() if m["floor"] <= f]
        rooms = [r for r in d.rooms if r is not d.start_room]
        for room in rooms:
            n = rng.randint(2, 4) + min(3, f // 3) + (1 if room.w * room.h > 110 else 0)
            main = rng.choice(pool)
            elite_i = rng.randrange(n) if rng.random() < 0.28 + min(0.25, f * 0.03) else -1
            for i in range(n):
                mid = main if rng.random() < 0.6 else rng.choice(pool)
                x, y = self.random_point(room, MONSTERS[mid]["radius"] + 8)
                elite = rng.choice(list(ELITE_AFFIXES)) if i == elite_i else None
                self.monsters.append(Monster(mid, x, y, f, elite))
        self.total = len(self.monsters)
        self.setup_seal(rooms)
        for room in rng.sample(rooms, min(5, len(rooms))):
            x, y = self.random_point(room, 24)
            self.interactables.append(Chest(x, y))
        # salles cachées : coffre richement garni ou autel d'anima, derrière un mur fissuré
        for room, (tx, ty), kind in d.secrets:
            self.interactables.append(SecretWall((tx + 0.5) * TILE, (ty + 0.5) * TILE, (tx, ty)))
            cx, cy = room.center_px
            if kind == "coffre":
                c = Chest(cx, cy)
                c.rich = True
                self.interactables.append(c)
            else:
                self.interactables.append(AnimaShrine(cx, cy))
        dmg = 9 * (1 + 0.28 * (f - 1))
        self.traps = [SpikeTrap((tx + 0.5) * TILE, (ty + 0.5) * TILE, dmg, rng.uniform(0, 3.8)) for tx, ty in d.traps]
        bx, by = d.boss_room.center_px
        self.boss = make_boss(floor_boss(f), bx, by, f, d.boss_room)
        self.monsters.append(self.boss)

    def setup_seal(self, rooms):
        """Condition d'ouverture de l'arène du gardien (voir seals.py)."""
        rng, f = self.rng, self.floor
        kind = self.seal_kind = seals.pick(rng, f)
        if kind == "kills":
            self.seal_needed = max(1, min(90, int(self.total * 0.35)))
        elif kind == "shards":
            self.seal_needed = 3 if f < 8 else 4
            for room in seals.far_rooms(self, self.seal_needed):
                self.interactables.append(seals.SealShard(*self.random_point(room, 24)))
        elif kind == "braziers":
            self.seal_needed = 3 if f < 8 else 4
            for room in seals.far_rooms(self, self.seal_needed):
                self.interactables.append(seals.Brazier(*self.random_point(room, 26), room))
        elif kind == "elites":
            self.seal_needed = 3 if f < 8 else 4
            # assez de champions dans l'étage : des monstres ordinaires deviennent des élites
            elites = sum(1 for m in self.monsters if m.elite)
            plain = [m for m in self.monsters if not m.elite]
            for m in rng.sample(plain, max(0, min(len(plain), self.seal_needed + 1 - elites))):
                self.monsters[self.monsters.index(m)] = Monster(m.mid, m.x, m.y, f, rng.choice(list(ELITE_AFFIXES)))
        else:                             # keeper
            self.seal_needed = 1
            self.monsters.append(seals.make_keeper(self, seals.far_rooms(self, 1)[0], f))

    def seal_count(self):
        return self.kills if self.seal_kind == "kills" else self.seal_have

    def ambush(self, x, y, room):
        """Brasier allumé : des créatures surgissent autour du héros."""
        f = self.floor
        pool = [mid for mid, m in MONSTERS.items() if m["floor"] <= f]
        for i in range(3 + min(3, f // 3)):
            mid = self.rng.choice(pool)
            mx, my = self.random_point(room, MONSTERS[mid]["radius"] + 8)
            m = Monster(mid, mx, my, f)
            m.aggro = True
            self.monsters.append(m)
            self.particles.emit(mx, my, (255, 120, 50), n=16, speed=120, life=0.5, size=4, up=80)

    def add_camp(self, room):
        """Salle d'entrée d'un étage BOSS : Hilda la forgeronne (améliorations) et un rescapé terrifié."""
        cx, cy = room.center_px
        sx, sy = cx - 70, cy - 20
        self.interactables.append(NPC(sx, sy, "Hilda la Forgeronne", "Forge", models.NPC_SPECS["forgeronne"],
                                      self.open_forge, facing=0.0, work=True))
        self.interactables.append(Prop(sx + 34, sy, models.anvil))
        self.anvil = (sx + 34, sy)
        spec = dict(detailed=True, body=(96, 84, 70), skin=(214, 176, 140),
                    rig={"model": "hooded", "palette": {"Black": (70, 62, 56), "LightBrown": (150, 132, 104)}})
        lines = iter(())

        def talk(world):
            nonlocal lines
            line = next(lines, None)
            if line is None:
                lines = iter(SURVIVOR_LINES)
                line = next(lines)
            world.message(f"Oswin le Rescapé : « {line} »", (235, 225, 200), 7)
        self.interactables.append(NPC(cx + 80, cy + 10, "Oswin le Rescapé", "Parler", spec, talk, facing=math.pi))
        self.interactables.append(Chest(cx, cy + 90))

    def open_forge(self, world):
        self.left_panel = ForgePanel(self)
        self.show_inv = True
        sfx.play("chest")

    # ------------------------------------------------------------------ progression
    def hud_title(self):
        title = f"Étage {self.floor} · {floor_name(self.floor)}"
        if self.boss_dead:
            return title, "Le gardien est vaincu. Empruntez le portail."
        if self.boss_started:
            return title, ""
        if self.barrier_active:
            if any(isinstance(o, seals.SealKey) for o in self.interactables):
                return title, "Le Geôlier est tombé : ramassez la clé du sceau."
            return title, seals.label(self.seal_kind, self.seal_count(), self.seal_needed)
        if self.arena:
            return title, f"{self.boss.name} vous attend dans l'arène."
        return title, "Le sceau est brisé : le gardien vous attend."

    def presence(self):
        hero, small = self.hero_presence()
        details = f"Étage {self.floor} · {floor_name(self.floor)}"
        if self.boss_started and not self.boss_dead:
            return details, f"Affronte {self.boss.name}", small
        if self.boss_dead:
            return details, "Gardien vaincu", small
        return details, hero, small

    def seal_progress(self):
        return (min(1.0, self.seal_count() / self.seal_needed), not self.barrier_active or self.boss_started)

    def active_boss(self):
        return self.boss if self.boss_started and not self.boss_dead else None

    def on_monster_killed(self, m):
        self.kills += 1
        if self.seal_kind == "elites" and m.elite and self.barrier_active:
            self.seal_have += 1
            self.message(f"Champion abattu ({self.seal_have} / {self.seal_needed})", (255, 200, 90), 4)
        if getattr(m, "keeper", False):
            self.interactables.append(seals.SealKey(m.x, m.y))
            self.message("Le Geôlier lâche la clé du sceau !", seals.KEY_COL, 5)

    def on_gold(self, amount):
        self.run_gold += amount

    def set_barrier(self, active):
        self.barrier_active = active
        self.flow_src = None

    def update_extra(self, dt):
        p = self.player
        if self.left_panel and not any(isinstance(o, NPC) and math.hypot(o.x - p.x, o.y - p.y) < 140
                                       for o in self.interactables):
            self.close_panels()           # forge fermée quand on s'éloigne de Hilda
        if self.arena:                    # étincelles de l'enclume de Hilda
            hit = math.sin(self.time * 2.6)
            if hit < 0 <= getattr(self, "_last_hit", 0.0):
                self.particles.emit(*self.anvil, (255, 190, 90), n=7, speed=70, life=0.5, size=2, up=90, z=16,
                                    zs=0.3)
            self._last_hit = hit
        for trap in self.traps:
            if abs(trap.x - p.x) < 600 and abs(trap.y - p.y) < 600:
                trap.update(dt, self)
        room = self.dungeon.boss_room
        if self.barrier_active and not self.boss_started and self.seal_count() >= self.seal_needed:
            self.set_barrier(False)
            self.show_banner("Le sceau est brisé", "Le gardien de l'étage vous attend", (255, 110, 80))
            sfx.play("seal")
            self.shake_screen(8)
            for tx, ty in self.dungeon.barrier_tiles:
                self.particles.emit((tx + 0.5) * TILE, (ty + 0.5) * TILE, (255, 70, 50), n=14, speed=120, life=0.9,
                                    size=4, up=160, z=20)
        if not self.boss_started and not self.barrier_active:
            tx, ty = int(p.x // TILE), int(p.y // TILE)
            if room.contains(tx, ty, margin=1):
                self.boss_started = True
                self.boss.active = True
                self.boss.aggro = True
                self.set_barrier(True)
                self.show_banner(self.boss.name, self.boss.title, (255, 90, 70))
                sfx.play("roar")
                self.shake_screen(10)
        if self.barrier_active:
            for tx, ty in self.dungeon.barrier_tiles:
                if random.random() < 0.1:
                    self.particles.emit((tx + random.random()) * TILE, (ty + random.random()) * TILE, (255, 60, 40),
                                        n=1, speed=10, life=1.0, size=3, up=90, zs=0)

    def on_boss_killed(self, boss):
        self.boss_dead = True
        self.set_barrier(False)
        p = self.player
        f = self.floor
        first = f not in p.cleared
        p.cleared.add(f)
        from .r3d.level import MAX_FLOOR
        p.max_floor = max(p.max_floor, min(MAX_FLOOR, f + 1))
        if f >= MAX_FLOOR:
            self.show_banner("Cendrespire est conquise !", "Le Sommet est à vous — la tour reste ouverte pour la gloire",
                             (255, 214, 110), 7)
        x, y = boss.x, boss.y
        for _ in range(6):
            self.loot.append(Loot(x, y, "gold", amount=self.gold_amount(random.randint(15, 30))))
        for _ in range(3):
            self.loot.append(Loot(x, y, "item", generate_item(f, cls_id=p.cls_id, tier=2)))
        if first:
            self.loot.append(Loot(x, y, "item", generate_item(f, rarity="legendaire", cls_id=p.cls_id)))
        self.loot.append(Loot(x, y, "orb"))
        self.particles.emit(x, y, (255, 130, 70), n=90, speed=300, life=1.1, size=5, up=260, z=30)
        self.effects.append(RingFX(x, y, 20, 340, 0.8, (255, 200, 120), 8))
        self.flash_light(x, y, 600, (255, 180, 120), 0.8)
        self.shake_screen(14)
        sfx.play("explosion")
        cx, cy = self.dungeon.boss_room.center_px
        self.interactables.append(Portal(cx, cy + 100, "Retourner au campement",
                                         lambda w: w.exit_to_hub(f"Étage {f} purifié. L'étage {f + 1} est accessible.")))
        self.show_banner("Gardien vaincu", f"L'étage {f + 1} est débloqué" + (" · butin légendaire" if first else ""),
                         GOLD_BRIGHT, 5)
        for m in self.monsters:
            if m.minion:
                m.dead = True
        self.save()

    def open_chest(self, chest):
        f = self.floor
        p = self.player
        sfx.play("chest")
        if getattr(chest, "rich", False):       # coffre d'une salle cachée
            self.message("Trésor caché !", GOLD_BRIGHT, 4)
            for _ in range(4):
                self.loot.append(Loot(chest.x, chest.y, "gold", amount=self.gold_amount(random.randint(14, 26))))
            self.loot.append(Loot(chest.x, chest.y, "item", generate_item(f, cls_id=p.cls_id, tier=2)))
            if random.random() < 0.35:
                self.loot.append(Loot(chest.x, chest.y, "item", generate_item(f, rarity="legendaire", cls_id=p.cls_id)))
        for _ in range(3):
            self.loot.append(Loot(chest.x, chest.y, "gold", amount=self.gold_amount(random.randint(6, 14))))
        for _ in range(random.randint(1, 2)):
            self.loot.append(Loot(chest.x, chest.y, "item", generate_item(f, cls_id=p.cls_id, tier=1)))
        if random.random() < 0.4:
            self.loot.append(Loot(chest.x, chest.y, "anima"))
        self.particles.emit(chest.x, chest.y, (255, 214, 100), n=34, speed=140, life=0.8, size=3, up=200, z=15)

    def death_penalty(self):
        lost = self.run_gold // 2
        self.player.gold = max(0, self.player.gold - lost)
        self.modal = DeathPanel(self, lost)
        self.save()

    def exit_to_hub(self, message=None):
        from .hub import HubScene
        p = self.player
        p.reset_run()
        self.save()
        self.game.load_scene(lambda: HubScene(self.game, p, message), "Cendreval", "La ville au pied de Cendrespire")

    # ------------------------------------------------------------------ rendu
    def render_extra(self, fr):
        p = self.player
        for trap in self.traps:
            if abs(trap.x - p.x) < 900 and abs(trap.y - p.y) < 900:
                trap.render(fr, self.time)
        t = self.time
        p = self.player
        room = self.dungeon.boss_room
        cx, cy = room.center_px
        if abs(cx - p.x) < 1000 and abs(cy - p.y) < 1000:
            k = 0.5 + 0.5 * math.sin(t * 1.5)
            fr.decal(cx, cy, 190, 190, (200, 30, 30), 0.25 + 0.15 * k, kind=1, inner=0.9)
            fr.decal(cx, cy, 120, 120, (200, 30, 30), 0.18 + 0.1 * k, kind=1, inner=0.93)
        if not self.barrier_active:
            return
        for i, (tx, ty) in enumerate(self.dungeon.barrier_tiles):
            x, y = (tx + 0.5) * TILE, (ty + 0.5) * TILE
            if abs(x - p.x) > 900 or abs(y - p.y) > 900:
                continue
            k = 0.6 + 0.4 * math.sin(t * 4 + tx + ty)
            fr.part("cube", (x, y, 36), (20, 0, 0), (0, 0, 36), (0, 20, 0), (255, 50, 30), 0.55 * k, additive=True)
            fr.decal(x, y, 22, 22, (255, 60, 40), 0.5, kind=2)
            if i % 2 == 0:
                fr.light(x, y, 30, 150, (255, 50, 30), 0.9)
