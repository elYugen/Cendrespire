"""Un étage de la Tour des Tourments : salles de monstres, sceau du gardien, boss, portail de sortie."""
import math
import random

import pygame

from . import sfx
from .bosses import Boss
from .data import MONSTERS, ELITE_AFFIXES, floor_name, floor_boss
from .dungeon import Dungeon, BARRIER
from .entities import Monster, Chest, Portal, Loot
from .fx import RingFX, glow
from .items import generate_item
from .panels import DeathPanel
from .settings import TILE, GOLD_BRIGHT, RED, SCREEN_W, SCREEN_H
from .world import World


class TowerScene(World):
    is_tower = True
    theme = "tower"
    ambient = (22, 18, 26)

    def __init__(self, game, player, floor):
        self.floor = floor
        rng = random.Random()
        d = Dungeon(64, 46)
        d.generate(rng, n_rooms=10 + min(4, floor // 2))
        super().__init__(game, player, d, rng)
        player.reset_run()
        sx, sy = d.start_room.center_px
        player.x, player.y = sx, sy
        self.kills = 0
        self.run_gold = 0
        self.barrier_active = True
        self.boss_started = False
        self.boss_dead = False
        self.populate()
        self.snap_camera()
        self.show_banner(f"Étage {floor}", floor_name(floor), GOLD_BRIGHT, 4)
        self.message("Éliminez les créatures pour briser le sceau du gardien.", (220, 210, 190), 8)
        sfx.play("portal")

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
            n = rng.randint(3, 5) + min(3, f // 3) + (1 if room.w * room.h > 90 else 0)
            main = rng.choice(pool)
            elite_i = rng.randrange(n) if rng.random() < 0.28 + min(0.25, f * 0.03) else -1
            for i in range(n):
                mid = main if rng.random() < 0.6 else rng.choice(pool)
                x, y = self.random_point(room, MONSTERS[mid]["radius"] + 8)
                elite = rng.choice(list(ELITE_AFFIXES)) if i == elite_i else None
                self.monsters.append(Monster(mid, x, y, f, elite))
        self.total = len(self.monsters)
        self.seal_needed = max(1, int(self.total * 0.6))
        for room in rng.sample(rooms, min(2, len(rooms))):
            x, y = self.random_point(room, 24)
            self.interactables.append(Chest(x, y))
        bx, by = d.boss_room.center_px
        self.boss = Boss(floor_boss(f), bx, by, f, d.boss_room)
        self.monsters.append(self.boss)

    # ------------------------------------------------------------------ progression
    def hud_title(self):
        title = f"Étage {self.floor} — {floor_name(self.floor)}"
        if self.boss_dead:
            return title, "Le gardien est vaincu. Empruntez le portail."
        if self.boss_started:
            return title, ""
        if self.barrier_active:
            return title, f"Sceau du gardien : {min(self.kills, self.seal_needed)} / {self.seal_needed} créatures"
        return title, "Le sceau est brisé : le gardien vous attend."

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
        room = self.dungeon.boss_room
        if self.barrier_active and not self.boss_started and self.kills >= self.seal_needed:
            self.set_barrier(False)
            self.show_banner("Le sceau est brisé !", "Le gardien de l'étage vous attend.", (255, 90, 60))
            sfx.play("seal")
            self.shake_screen(8)
            for tx, ty in self.dungeon.barrier_tiles:
                self.particles.emit((tx + 0.5) * TILE, (ty + 0.5) * TILE, (255, 60, 40), n=12, speed=120, life=0.8, size=4)
        if not self.boss_started and not self.barrier_active:
            tx, ty = int(p.x // TILE), int(p.y // TILE)
            if room.contains(tx, ty, margin=1):
                self.boss_started = True
                self.boss.active = True
                self.boss.aggro = True
                self.set_barrier(True)
                self.show_banner(self.boss.name, self.boss.title, (255, 80, 60))
                sfx.play("roar")
                self.shake_screen(10)
        if self.barrier_active:
            for tx, ty in self.dungeon.barrier_tiles:
                if random.random() < 0.08:
                    self.particles.emit((tx + random.random()) * TILE, (ty + 1) * TILE, (255, 50, 30), n=1, speed=20,
                                        life=0.9, size=3, up=60)

    def on_boss_killed(self, boss):
        self.boss_dead = True
        self.set_barrier(False)
        p = self.player
        f = self.floor
        first = f not in p.cleared
        p.cleared.add(f)
        p.max_floor = max(p.max_floor, f + 1)
        x, y = boss.x, boss.y
        for _ in range(6):
            self.loot.append(Loot(x, y, "gold", amount=self.gold_amount(random.randint(15, 30))))
        for _ in range(3):
            self.loot.append(Loot(x, y, "item", generate_item(f, cls_id=p.cls_id, tier=2)))
        if first:
            self.loot.append(Loot(x, y, "item", generate_item(f, rarity="legendaire", cls_id=p.cls_id)))
        self.loot.append(Loot(x, y, "potion"))
        self.loot.append(Loot(x, y, "potion"))
        self.particles.emit(x, y - 20, (255, 120, 60), n=80, speed=320, life=1.0, size=5)
        self.effects.append(RingFX(x, y, 20, 320, 0.8, (255, 200, 120), 8))
        self.shake_screen(14)
        sfx.play("explosion")
        cx, cy = self.dungeon.boss_room.center_px
        self.interactables.append(Portal(cx, cy + 90, "Retourner au campement",
                                         lambda w: w.exit_to_hub(f"Étage {f} purifié ! L'étage {f + 1} est désormais accessible.")))
        self.show_banner("Gardien vaincu !", f"L'étage {f + 1} est débloqué." + (" Butin légendaire !" if first else ""),
                         GOLD_BRIGHT, 5)
        for m in self.monsters:
            if m.minion:
                m.dead = True
        self.save()

    def open_chest(self, chest):
        f = self.floor
        p = self.player
        sfx.play("chest")
        for _ in range(3):
            self.loot.append(Loot(chest.x, chest.y, "gold", amount=self.gold_amount(random.randint(6, 14))))
        for _ in range(random.randint(1, 2)):
            self.loot.append(Loot(chest.x, chest.y, "item", generate_item(f, cls_id=p.cls_id, tier=1)))
        if random.random() < 0.5:
            self.loot.append(Loot(chest.x, chest.y, "anima"))
        if random.random() < 0.4:
            self.loot.append(Loot(chest.x, chest.y, "potion"))
        self.particles.emit(chest.x, chest.y - 10, (255, 210, 90), n=30, speed=160, life=0.7, size=3, up=60)

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
        self.game.change_scene(HubScene(self.game, p, message))

    # ------------------------------------------------------------------ rendu
    def draw_ground(self, surf, cx, cy):
        if not self.barrier_active:
            return
        t = self.time
        for tx, ty in self.dungeon.barrier_tiles:
            x, y = tx * TILE - cx, ty * TILE - cy
            if -TILE < x < SCREEN_W and -TILE < y < SCREEN_H:
                s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
                s.fill((170, 20, 20, 90 + int(40 * math.sin(t * 4 + tx + ty))))
                for i in range(4):
                    lx = (i * 11 + t * 30 + tx * 7) % TILE
                    pygame.draw.line(s, (255, 90, 60, 160), (lx, 0), (lx, TILE), 1)
                surf.blit(s, (x, y))

    def draw_post(self, surf, cx, cy):
        if not self.barrier_active:
            return
        for tx, ty in self.dungeon.barrier_tiles:
            x, y = (tx + 0.5) * TILE - cx, (ty + 0.5) * TILE - cy
            if -TILE < x < SCREEN_W + TILE and -TILE < y < SCREEN_H + TILE:
                glow(surf, x, y, 30 + 4 * math.sin(self.time * 5 + tx), (150, 20, 10))

    def collect_lights(self):
        lights = super().collect_lights()
        if self.barrier_active:
            for i, (tx, ty) in enumerate(self.dungeon.barrier_tiles):
                if i % 2 == 0:
                    lights.append(((tx + 0.5) * TILE, (ty + 0.5) * TILE, 110, (170, 30, 20)))
        if self.boss_started and not self.boss_dead:
            b = self.boss
            lights.append((b.x, b.y, 200, (90, 30, 30)))
        return lights
