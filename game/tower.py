"""Un étage de Cendrespire : salles de monstres, sceau du gardien, boss, portail de sortie."""
import math
import random

from . import sfx
from .bosses import Boss
from .data import MONSTERS, ELITE_AFFIXES, floor_name, floor_boss
from .dungeon import Dungeon, FLOOR, WALL
from .entities import Monster, Chest, Portal, Loot, SecretWall, AnimaShrine, SpikeTrap
from .fx import RingFX
from .items import generate_item
from .panels import DeathPanel
from .r3d import level
from .settings import TILE, GOLD_BRIGHT, WHITE
from .world import World


class TowerScene(World):
    is_tower = True

    def __init__(self, game, player, floor):
        self.floor = floor
        rng = random.Random()
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
        self.run_gold = 0
        self.barrier_active = True
        self.boss_started = False
        self.boss_dead = False
        self.populate()
        self.show_banner(floor_name(floor), f"Étage {floor}", WHITE, 4.5)
        self.message("Éliminez les créatures pour briser le sceau du gardien.", (220, 214, 200), 8)
        sfx.play("portal")
        sfx.music("inside")

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
        self.seal_needed = max(1, min(90, int(self.total * 0.35)))
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
        self.boss = Boss(floor_boss(f), bx, by, f, d.boss_room)
        self.monsters.append(self.boss)

    # ------------------------------------------------------------------ progression
    def hud_title(self):
        title = f"Étage {self.floor} · {floor_name(self.floor)}"
        if self.boss_dead:
            return title, "Le gardien est vaincu. Empruntez le portail."
        if self.boss_started:
            return title, ""
        if self.barrier_active:
            return title, f"Sceau du gardien : {min(self.kills, self.seal_needed)} / {self.seal_needed} créatures"
        return title, "Le sceau est brisé : le gardien vous attend."

    def seal_progress(self):
        return (min(1.0, self.kills / self.seal_needed), not self.barrier_active or self.boss_started)

    def active_boss(self):
        return self.boss if self.boss_started and not self.boss_dead else None

    def on_monster_killed(self, m):
        self.kills += 1

    def on_gold(self, amount):
        self.run_gold += amount

    def set_barrier(self, active):
        self.barrier_active = active
        self.flow_src = None

    def update_extra(self, dt):
        p = self.player
        for trap in self.traps:
            if abs(trap.x - p.x) < 600 and abs(trap.y - p.y) < 600:
                trap.update(dt, self)
        room = self.dungeon.boss_room
        if self.barrier_active and not self.boss_started and self.kills >= self.seal_needed:
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
