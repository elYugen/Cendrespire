"""Scène de jeu commune (tour et campement) : logique, rendu 3D et interface."""
import math
import random
from collections import deque

import pygame

from . import artifacts, hud, save, sfx, spells, ui
from .data import ANIMA_POWERS, ANIMA_TIERS, BAG_SIZE, SPELLS
from .dungeon import WALL, BARRIER, Minimap
from .entities import Loot
from .fx import Particles, RingFX, Blast, Lightning
from .items import generate_item, item_value, buy_price, ench_spent, ART_SLOTS
from .panels import (InventoryPanel, MenuScreen, MerchantPanel, ForgePanel, AnimaPanel, PausePanel, DeathPanel)
from .r3d import level
from .r3d.camera import Camera3D
from .r3d.renderer import Env
from .settings import (SCREEN_W, SCREEN_H, TILE, VIEW, SC_UP, SC_DOWN, SC_LEFT, SC_RIGHT, SC_SPELLS, SC_POTION,
                       SC_INTERACT, GOLD, GOLD_BRIGHT, TEXT, RED, WHITE, RARITY_COLORS)

SC_ROLL = 44                  # Espace
SC_ARTIFACTS = (21, 23, 10)   # R, T, G


class Scene:
    def __init__(self, game):
        self.game = game

    def handle_event(self, e):
        pass

    def update(self, dt):
        pass

    def render3d(self, fr):
        return None

    def draw_ui(self, surf):
        pass


class World(Scene):
    is_tower = False
    reveal_all = False
    hub = False

    def __init__(self, game, player, dungeon, theme, rng=None):
        super().__init__(game)
        self.rng = rng or random.Random()
        self.player = player
        self.dungeon = dungeon
        self.tiles = dungeon.tiles
        self.W, self.H = dungeon.w, dungeon.h
        self.theme = theme
        th = level.THEMES[theme]
        self.geo = level.build(dungeon, theme, self.rng, hub=self.hub)
        self.torch_col = th["torch"]
        self.env = Env(sun_col=th["sun"], amb_sky=th["sky"], amb_ground=th["ground"])
        self.cam = Camera3D()
        self.barrier_active = False
        self.monsters, self.projectiles, self.effects, self.loot, self.interactables = [], [], [], [], []
        self.allies = []
        self.particles = Particles()
        self.texts = []
        self.flashes = []
        self.blood = deque(maxlen=160)
        self.shake = 0.0
        self.keys = set()
        self.time = 0.0
        self.flow = None
        self.flow_src = None
        self.banner = None
        self.messages = []
        self.notifs = []
        self.minimap = Minimap(dungeon, self.reveal_all)
        self.inv_panel = InventoryPanel(self)
        self.show_inv = False
        self.left_panel = None
        self.modal = None
        self.pending_anima = 0
        self.click_block = False
        self.big_map = False
        self.scheduled = []
        self.skill_rects = []
        self.anima_rects = []
        self.shop_stock = []
        self.wheel_alpha = 0.0
        self.gold_shown = 0.0

    # ------------------------------------------------------------------ utilitaires
    def solid(self, tx, ty):
        if not (0 <= tx < self.W and 0 <= ty < self.H):
            return True
        t = self.tiles[ty][tx]
        return t == WALL or (t == BARRIER and self.barrier_active)

    def solid_at(self, x, y):
        return self.solid(int(x // TILE), int(y // TILE))

    def blocked(self, x, y, r):
        T = TILE
        for ty in range(int((y - r) // T), int((y + r) // T) + 1):
            for tx in range(int((x - r) // T), int((x + r) // T) + 1):
                if self.solid(tx, ty):
                    cx = min(max(x, tx * T), tx * T + T)
                    cy = min(max(y, ty * T), ty * T + T)
                    if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                        return True
        return False

    def move_circle(self, e, dx, dy):
        steps = int(max(abs(dx), abs(dy)) / 8) + 1
        sx, sy = dx / steps, dy / steps
        for _ in range(steps):
            if sx and not self.blocked(e.x + sx, e.y, e.r):
                e.x += sx
            if sy and not self.blocked(e.x, e.y + sy, e.r):
                e.y += sy

    def los(self, x1, y1, x2, y2):
        d = math.hypot(x2 - x1, y2 - y1)
        n = int(d / 16) + 1
        for i in range(1, n):
            t = i / n
            if self.solid_at(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t):
                return False
        return True

    def reachable(self, x0, y0, x1, y1, r):
        d = math.hypot(x1 - x0, y1 - y0)
        n = int(d / 8) + 1
        bx, by = x0, y0
        for i in range(1, n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if self.blocked(x, y, r):
                break
            bx, by = x, y
        return bx, by

    def mouse_px(self):
        mx, my = ui.mouse_pos()
        return mx * VIEW.s, my * VIEW.s

    def aim_point(self):
        return self.cam.ray_ground(*self.mouse_px(), height=22)

    def ground_point(self):
        return self.cam.ray_ground(*self.mouse_px(), height=0)

    def is_moving(self):
        return any(s in self.keys for s in SC_UP + SC_DOWN + SC_LEFT + SC_RIGHT)

    def schedule(self, delay, fn):
        self.scheduled.append([delay, fn])

    def add_text(self, x, y, z, text, color, size=16):
        self.texts.append([x + random.uniform(-8, 8), y + random.uniform(-8, 8), z, text, color, size, 0.95, 0.95])

    def shake_screen(self, amount):
        self.shake = min(14, max(self.shake, amount))

    def flash_light(self, x, y, r, color, dur=0.25):
        self.flashes.append([x, y, r, color, dur, dur])

    def message(self, text, color=TEXT, dur=5.0):
        self.messages.append([text, color, dur])
        self.messages = self.messages[-8:]

    def notify(self, item):
        self.notifs.append([item, 4.0])
        self.notifs = self.notifs[-5:]

    def show_banner(self, text, sub="", color=WHITE, dur=3.4):
        self.banner = [text, sub, color, 0.0, dur]

    def alert(self, src):
        for m in self.monsters:
            if not m.aggro and not m.boss and math.hypot(m.x - src.x, m.y - src.y) < 220:
                m.aggro = True

    def active_boss(self):
        return None

    def hud_title(self):
        return "", ""

    def seal_progress(self):
        return None

    # ------------------------------------------------------------------ chemin vers le joueur
    def update_flow(self):
        p = self.player
        src = (int(p.x // TILE), int(p.y // TILE))
        if src == self.flow_src:
            return
        self.flow_src = src
        W, H = self.W, self.H
        dist = [-1] * (W * H)
        if not (0 <= src[0] < W and 0 <= src[1] < H):
            self.flow = dist
            return
        dist[src[1] * W + src[0]] = 0
        q = deque([src])
        while q:
            x, y = q.popleft()
            d = dist[y * W + x]
            if d > 45:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < H and dist[ny * W + nx] < 0 and not self.solid(nx, ny):
                    dist[ny * W + nx] = d + 1
                    q.append((nx, ny))
        self.flow = dist

    def flow_step(self, x, y):
        if not self.flow:
            return None
        W = self.W
        tx, ty = int(x // TILE), int(y // TILE)
        best, bd = None, None
        cur = self.flow[ty * W + tx] if 0 <= tx < W and 0 <= ty < self.H else -1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx, ny = tx + dx, ty + dy
            if not (0 <= nx < W and 0 <= ny < self.H):
                continue
            if dx and dy and (self.solid(tx + dx, ty) or self.solid(tx, ty + dy)):
                continue
            d = self.flow[ny * W + nx]
            if d >= 0 and (bd is None or d < bd):
                best, bd = (nx, ny), d
        if best is None or (cur >= 0 and bd >= cur):
            return None
        return ((best[0] + 0.5) * TILE, (best[1] + 0.5) * TILE)

    # ------------------------------------------------------------------ combat
    def player_hit(self, m, mult, knock=0, ang=None, stun=0.0, slow=0.0, proc=True):
        p = self.player
        dmg, crit = p.roll_damage(mult)
        n = p.av("givre")
        if n and random.random() * 100 < n:
            slow = max(slow, 2.0)
        if proc and random.random() * 100 < p.ench("entrave"):
            slow = max(slow, 2.0)
        self.damage_monster(m, dmg, crit, knock, ang, stun, slow)
        if p.stats["lifesteal"]:
            p.heal(dmg * p.stats["lifesteal"] / 100)
        if not proc:
            return dmg
        # enchantements d'arme
        if p.ench("echo") and random.random() * 100 < p.ench("echo") and not m.dead:
            self.schedule(0.12, lambda w, m=m: (not m.dead) and w.player_hit(m, mult * 0.6, proc=False))
        if p.ench("embrasement") and random.random() * 100 < p.ench("embrasement") and not m.dead:
            m.burn = 3.0
            m.burn_dps = p.roll_damage(0.35)[0]
        if p.ench("tempete") and random.random() * 100 < p.ench("tempete"):
            self.effects.append(Lightning(m.x, m.y))
            for o in list(self.monsters):
                if not o.dead and o.targetable and math.hypot(o.x - m.x, o.y - m.y) < 70 + o.r:
                    self.player_hit(o, 1.5, proc=False)
        if p.ench("chaine") and random.random() * 100 < p.ench("chaine"):
            others = sorted((o for o in self.monsters if o is not m and not o.dead and o.targetable
                             and math.hypot(o.x - m.x, o.y - m.y) < 200), key=lambda o: math.hypot(o.x - m.x, o.y - m.y))
            for o in others[:2]:
                self.particles.emit((m.x + o.x) / 2, (m.y + o.y) / 2, (170, 200, 255), n=6, speed=60, life=0.3,
                                    size=3, z=25)
                self.player_hit(o, mult * 0.6, proc=False)
        return dmg

    def damage_circle(self, x, y, r, mult, knock=0, stun=0.0, slow=0.0):
        n = 0
        for m in list(self.monsters):
            if m.dead or not m.targetable:
                continue
            if (m.x - x) ** 2 + (m.y - y) ** 2 <= (r + m.r) ** 2:
                self.player_hit(m, mult, knock, math.atan2(m.y - y, m.x - x), stun, slow)
                n += 1
        return n

    def damage_monster(self, m, dmg, crit, knock=0, ang=None, stun=0.0, slow=0.0, quiet=False):
        if m.dead:
            return
        m.hp -= dmg
        m.flash = 0.1
        if not m.aggro:
            m.aggro = True
            self.alert(m)
        if not m.boss:
            if knock and ang is not None:
                m.kx += math.cos(ang) * knock * 5
                m.ky += math.sin(ang) * knock * 5
            if stun:
                m.stun = max(m.stun, stun)
        if slow:
            m.slow = max(m.slow, slow * (0.5 if m.boss else 1))
        top = m.height() + 8
        if crit:
            self.add_text(m.x, m.y, top, f"{int(dmg)}", (255, 214, 70), 24)
        elif dmg >= 1:
            self.add_text(m.x, m.y, top, str(int(dmg)), (245, 245, 240), 17)
        if not quiet:
            bone = m.mid in ("squelette", "archer", "golem", "liche")
            self.particles.emit(m.x, m.y, (210, 205, 185) if bone else (140, 12, 12), n=5, speed=90, life=0.5,
                                size=2.6, glow=False, gravity=500, up=160, z=m.height() * 0.6)
            sfx.play("hit", 0.35)
        if m.hp <= 0:
            self.kill_monster(m)

    def kill_monster(self, m):
        m.dead = True
        p = self.player
        p.kills += 1
        p.gain_xp(m.xp, self)
        sfx.play("death", 0.4)
        self.particles.emit(m.x, m.y, (100, 12, 12), n=14, speed=150, life=0.8, size=3.5, glow=False, gravity=600,
                            up=220, z=20)
        self.particles.emit(m.x, m.y, (200, 200, 220), n=8, speed=40, life=0.8, size=4, up=80, z=20)
        if m.mid not in ("squelette", "archer", "golem"):
            self.blood.append((m.x + random.uniform(-6, 6), m.y + random.uniform(-6, 6), m.r * random.uniform(1, 1.6)))
        if p.av("nova_mort"):
            self.effects.append(Blast(m.x, m.y, 90, 0.05, p.av("nova_mort") / 100, (170, 60, 220), sound="magic"))
        heal = p.av("ferveur") + p.ench("vampirisme") + p.ench("ame_soin")
        if heal:
            p.heal(p.stats["max_hp"] * heal / 100)
        if m.boss:
            self.on_boss_killed(m)
        elif not m.minion:
            self.drop_monster_loot(m)
            self.on_monster_killed(m)

    def floor_level(self):
        return max(1, self.player.max_floor)

    def gold_amount(self, base):
        return max(1, int(base * (1 + 0.5 * (self.floor_level() - 1)) * (1 + self.player.stats["gold_find"] / 100)))

    def drop_monster_loot(self, m):
        f = self.floor_level()
        p = self.player
        if random.random() < (1.0 if m.elite else 0.55):
            self.loot.append(Loot(m.x, m.y, "gold", amount=self.gold_amount(random.randint(2, 6) * (4 if m.elite else 1))))
        n_items = 2 if m.elite else (1 if random.random() < 0.1 else 0)
        for _ in range(n_items):
            self.loot.append(Loot(m.x, m.y, "item", generate_item(f, cls_id=p.cls_id, tier=1 if m.elite else 0)))
        if random.random() < (0.35 if m.elite else 0.05):
            self.loot.append(Loot(m.x, m.y, "orb"))
        if m.elite and random.random() < 0.35:
            self.loot.append(Loot(m.x, m.y, "anima"))

    def on_monster_killed(self, m):
        pass

    def on_boss_killed(self, m):
        pass

    def on_level_up(self):
        p = self.player
        self.show_banner(f"Niveau {p.level}", "+5 points de caractéristique · +1 point d'enchantement", GOLD_BRIGHT)
        self.effects.append(RingFX(p.x, p.y, 10, 160, 0.6, (255, 210, 100), 6))
        self.particles.emit(p.x, p.y, (255, 210, 100), n=50, speed=200, life=0.9, size=4, up=200, z=10)
        for sid in p.spells:
            if SPELLS[sid]["level"] == p.level:
                self.message(f"Nouveau sort débloqué : {SPELLS[sid]['name']} !", GOLD_BRIGHT, 8)
        sfx.play("levelup")

    def on_player_death(self):
        p = self.player
        if p.anima.get("seconde") and not p.second_used:
            p.second_used = True
            p.hp = p.stats["max_hp"] * min(0.9, p.av("seconde") / 100)
            p.invuln = 2.0
            self.show_banner("Le Phylactère vous ramène à la vie !", "", (160, 255, 200))
            self.effects.append(Blast(p.x, p.y, 180, 0, 2.0, (160, 255, 200), knock=120))
            return
        p.hp = 0
        p.dead = True
        p.deaths += 1
        self.death_penalty()

    def death_penalty(self):
        self.modal = DeathPanel(self, 0)

    # ------------------------------------------------------------------ inventaire
    def pickup_item(self, item):
        p = self.player
        if len(p.inventory) >= BAG_SIZE:
            return False
        p.inventory.append(item)
        self.notify(item)
        sfx.play("pickup")
        return True

    def equip(self, item, from_idx=None):
        p = self.player
        if item["slot"] == "artefact":
            target = next((s for s in ART_SLOTS if not p.equipment[s]), ART_SLOTS[0])
        else:
            if not p.can_equip(item):
                self.message("Cette arme n'est pas utilisable par votre classe.", RED)
                return
            target = item["slot"]
        old = p.equipment[target]
        p.equipment[target] = item
        if from_idx is not None:
            p.inventory.pop(from_idx)
            if old:
                p.inventory.insert(from_idx, old)
        p.recompute()
        sfx.play("pickup")

    def bag_right_click(self, idx):
        p = self.player
        it = p.inventory[idx]
        if isinstance(self.left_panel, MerchantPanel):
            p.inventory.pop(idx)
            v = item_value(it)
            p.gold += v
            self.message(f"Vendu : {it['name']} (+{v} or)" + (" · points d'enchantement rendus" if ench_spent(it) else ""),
                         GOLD)
            sfx.play("gold")
            return
        self.equip(it, idx)

    def unequip(self, slot):
        p = self.player
        if len(p.inventory) >= BAG_SIZE:
            self.message("Votre sac est plein.", RED)
            return
        p.inventory.append(p.equipment[slot])
        p.equipment[slot] = None
        p.recompute()
        sfx.play("click")

    def destroy_item(self, idx):
        it = self.player.inventory.pop(idx)
        self.message(f"Recyclé : {it['name']}" + (" (points d'enchantement rendus)" if ench_spent(it) else ""),
                     (170, 170, 170))

    def buy_item(self, i):
        p = self.player
        it = self.shop_stock[i]
        price = buy_price(it)
        if p.gold < price:
            self.message("Pas assez d'or.", RED)
        elif len(p.inventory) >= BAG_SIZE:
            self.message("Votre sac est plein.", RED)
        else:
            p.gold -= price
            p.inventory.append(self.shop_stock.pop(i))
            self.message(f"Acheté : {it['name']}", RARITY_COLORS[it["rarity"]])
            sfx.play("gold")

    def enchant(self, item, slot_i, eid):
        """Choisit ou améliore un enchantement (coût : niveau visé en points)."""
        p = self.player
        e = item["ench"][slot_i]
        if e["id"] and e["id"] != eid:
            return
        if e["lvl"] >= 3:
            return
        cost = e["lvl"] + 1
        if p.ench_points < cost:
            self.message(f"Il faut {cost} point(s) d'enchantement.", RED)
            return
        e["id"] = eid
        e["lvl"] += 1
        p.recompute()
        sfx.play("levelup", 0.4)

    # ------------------------------------------------------------------ anima
    def open_anima_choice(self):
        p = self.player
        pool = [k for k, v in ANIMA_POWERS.items() if not (v.get("unique") and p.anima.get(k))]
        picks = random.sample(pool, 3)
        weights = [t[3] for t in ANIMA_TIERS]
        choices = []
        for pid in picks:
            tier = random.choices(range(len(ANIMA_TIERS)), weights)[0]
            choices.append((pid, tier))
        self.modal = AnimaPanel(self, choices)
        sfx.play("magic")

    def take_anima(self, pid, tier):
        p = self.player
        p.anima[pid] = p.anima.get(pid, 0) + ANIMA_TIERS[tier][2]
        hp_frac = p.hp / p.stats["max_hp"]
        p.recompute()
        p.hp = hp_frac * p.stats["max_hp"]
        self.message(f"Pouvoir d'anima {ANIMA_TIERS[tier][0].lower()} : {ANIMA_POWERS[pid]['name']}",
                     ANIMA_TIERS[tier][1])
        self.pending_anima -= 1
        self.modal = None
        self.click_block = True
        sfx.play("levelup", 0.5)

    # ------------------------------------------------------------------ panneaux
    def close_modal(self):
        self.modal = None
        self.click_block = True

    def close_panels(self):
        self.show_inv = False
        self.left_panel = None

    def open_pause(self):
        self.modal = PausePanel(self)

    def save(self):
        save.save_data(self.player.to_save())

    def save_and_menu(self):
        self.save()
        from .scenes import TitleScene
        self.game.change_scene(TitleScene(self.game, skip_intro=True))

    def save_and_quit(self):
        self.save()
        self.game.running = False

    def exit_to_hub(self, message=None):
        pass

    def ui_contains(self, pos):
        if self.show_inv and self.inv_panel.contains(pos):
            return True
        if self.left_panel and self.left_panel.contains(pos):
            return True
        if any(rc.inflate(8, 8).collidepoint(pos) for rc, _ in self.skill_rects):
            return True
        return hud.minimap_rect().collidepoint(pos)

    # ------------------------------------------------------------------ événements
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            self.keys.add(e.scancode)
        elif e.type == pygame.KEYUP:
            self.keys.discard(e.scancode)
        elif e.type == pygame.WINDOWFOCUSLOST:
            self.keys.clear()
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.click_block = False
        if self.modal:
            if e.type == pygame.MOUSEBUTTONDOWN:
                self.click_block = True
            self.modal.handle_event(e)
            return
        p = self.player
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.show_inv or self.left_panel or self.big_map:
                    self.close_panels()
                    self.big_map = False
                else:
                    self.open_pause()
                return
            if e.key in (pygame.K_i, pygame.K_c):
                self.close_panels()
                self.modal = MenuScreen(self, 0 if e.key == pygame.K_i else 1)
                sfx.play("click")
                return
            if e.key == pygame.K_TAB:
                self.big_map = not self.big_map
                return
            if e.scancode == SC_POTION:
                p.drink_potion(self)
                return
            if e.scancode == SC_ROLL:
                if self.is_moving():
                    dx, dy = p.move_dir
                else:
                    dx, dy = math.cos(p.facing), math.sin(p.facing)
                p.start_roll(self, dx, dy)
                return
            if e.scancode == SC_INTERACT:
                obj = self.nearest_interactable()
                if obj:
                    obj.interact(self)
                return
            for i, sc in enumerate(SC_ARTIFACTS):
                if e.scancode == sc:
                    artifacts.use(self, ART_SLOTS[i])
                    return
            for i, codes in enumerate(SC_SPELLS):
                if e.scancode in codes and i < len(p.spells):
                    spells.cast(self, p.spells[i])
                    return
        for panel in (self.inv_panel if self.show_inv else None, self.left_panel):
            if panel and panel.handle_event(e):
                if e.type == pygame.MOUSEBUTTONDOWN:
                    self.click_block = True
                return
        if e.type == pygame.MOUSEBUTTONDOWN:
            if self.ui_contains(e.pos):
                self.click_block = True
                return
            if e.button == 3:
                spells.cast(self, p.spells[0])

    def nearest_interactable(self):
        p = self.player
        best, bd = None, None
        for o in self.interactables:
            if not o.radius or not o.can_interact(self):
                continue
            d = math.hypot(o.x - p.x, o.y - p.y)
            if d <= o.radius and (bd is None or d < bd):
                best, bd = o, d
        return best

    # ------------------------------------------------------------------ mise à jour
    def update(self, dt):
        self.time += dt
        if self.banner:
            self.banner[3] += dt
            if self.banner[3] > self.banner[4]:
                self.banner = None
        for m in self.messages:
            m[2] -= dt
        for n in self.notifs:
            n[1] -= dt
        self.notifs = [n for n in self.notifs if n[1] > 0]
        if self.modal:
            self.modal.update(dt)
            return
        if self.pending_anima > 0 and not self.player.dead:
            self.open_anima_choice()
            return
        self.update_player(dt)
        self.update_flow()
        for m in list(self.monsters):
            if not m.dead:
                m.update(dt, self)
        self.separate()
        self.monsters = [m for m in self.monsters if not m.dead]
        for a in self.allies:
            a.update(dt, self)
        self.allies = [a for a in self.allies if a.alive]
        for pr in self.projectiles:
            pr.update(dt, self)
        self.projectiles = [pr for pr in self.projectiles if pr.alive]
        for ef in list(self.effects):
            ef.update(dt, self)
        self.effects = [ef for ef in self.effects if ef.alive]
        for s in list(self.scheduled):
            s[0] -= dt
            if s[0] <= 0:
                self.scheduled.remove(s)
                s[1](self)
        self.update_loot(dt)
        self.update_anima_souls(dt)
        self.particles.update(dt)
        for t in self.texts:
            t[2] += 45 * dt
            t[6] -= dt
        self.texts = [t for t in self.texts if t[6] > 0]
        for f in self.flashes:
            f[4] -= dt
        self.flashes = [f for f in self.flashes if f[4] > 0]
        self.shake = max(0.0, self.shake - dt * 30)
        self.gold_shown = max(0.0, self.gold_shown - dt)
        self.update_ambient(dt)
        p = self.player
        self.minimap.reveal(int(p.x // TILE), int(p.y // TILE))
        self.update_extra(dt)

    def update_extra(self, dt):
        pass

    def update_ambient(self, dt):
        p = self.player
        for x, y, z in self.geo.torches:
            if abs(x - p.x) < 700 and abs(y - p.y) < 700 and random.random() < 0.3:
                self.particles.emit(x, y, (255, 150, 50), n=1, speed=8, life=0.5, size=2.5, up=50, z=z + 4, zs=0)

    def update_anima_souls(self, dt):
        n = self.player.anima.get("tourbillon", 0)
        if not n:
            return
        p = self.player
        for i in range(n):
            a = self.time * 2.4 + i * math.tau / n
            sx, sy = p.x + math.cos(a) * 60, p.y + math.sin(a) * 60
            for m in self.monsters:
                if not m.dead and m.targetable and math.hypot(m.x - sx, m.y - sy) < m.r + 12:
                    if getattr(m, "_soul_t", 0) < self.time:
                        m._soul_t = self.time + 0.5
                        self.player_hit(m, 0.45, proc=False)

    def update_player(self, dt):
        p = self.player
        if p.dead:
            return
        p.tick(dt)
        p.moving = False
        if p.leap:
            L = p.leap
            L["t"] += dt
            k = min(1, L["t"] / L["dur"])
            p.x = L["sx"] + (L["ex"] - L["sx"]) * k
            p.y = L["sy"] + (L["ey"] - L["sy"]) * k
            if k >= 1:
                p.leap = None
                L["on_land"](self)
            return
        if p.dash:
            D = p.dash
            D["t"] += dt
            k = min(1, D["t"] / D["dur"])
            p.x = D["sx"] + (D["ex"] - D["sx"]) * k
            p.y = D["sy"] + (D["ey"] - D["sy"]) * k
            p.walk += dt * 30
            if k >= 1:
                p.dash = None
            return
        k = self.keys
        mx = (1 if any(s in k for s in SC_RIGHT) else 0) - (1 if any(s in k for s in SC_LEFT) else 0)
        my = (1 if any(s in k for s in SC_DOWN) else 0) - (1 if any(s in k for s in SC_UP) else 0)
        if mx or my:
            dx, dy = self.cam.screen_to_world_dir(mx, my)
            spd = p.speed()
            self.move_circle(p, dx * spd * dt, dy * spd * dt)
            p.move_dir = (dx, dy)
            p.walk += dt * 10.5
            p.moving = True
        ax, ay = self.aim_point()
        p.facing = math.atan2(ay - p.y, ax - p.x)
        if pygame.mouse.get_pressed()[0] and not self.click_block and not self.ui_contains(ui.mouse_pos()):
            spells.basic_attack(self)

    def separate(self):
        ms = [m for m in self.monsters if not m.dead and (m.aggro or m.boss)]
        p = self.player
        for i, a in enumerate(ms):
            for b in ms[i + 1:]:
                dx = b.x - a.x
                if abs(dx) > 70:
                    continue
                dy = b.y - a.y
                rr = a.r + b.r
                d2 = dx * dx + dy * dy
                if 0.01 < d2 < rr * rr:
                    d = math.sqrt(d2)
                    push = (rr - d) / 2
                    nx, ny = dx / d, dy / d
                    if not a.boss:
                        self.move_circle(a, -nx * push, -ny * push)
                    if not b.boss:
                        self.move_circle(b, nx * push, ny * push)
            dx, dy = a.x - p.x, a.y - p.y
            rr = a.r + p.r
            d2 = dx * dx + dy * dy
            if 0.01 < d2 < rr * rr and not a.boss and not p.leap:
                d = math.sqrt(d2)
                self.move_circle(a, dx / d * (rr - d), dy / d * (rr - d))

    def update_loot(self, dt):
        p = self.player
        keep = []
        for l in self.loot:
            l.update(dt, self)
            d = math.hypot(l.x - p.x, l.y - p.y)
            if p.dead or l.z > 4:
                keep.append(l)
                continue
            if l.kind in ("gold", "orb"):
                if d < 140:
                    l.x += (p.x - l.x) * min(1, dt * 8)
                    l.y += (p.y - l.y) * min(1, dt * 8)
                if d < 26:
                    if l.kind == "gold":
                        p.gold += l.amount
                        self.on_gold(l.amount)
                        self.gold_shown = 3.0
                        self.add_text(p.x, p.y, 60, f"+{l.amount} or", GOLD, 15)
                        sfx.play("gold", 0.5)
                    else:
                        amt = p.stats["max_hp"] * 0.15
                        p.heal(amt)
                        self.add_text(p.x, p.y, 60, f"+{int(amt)}", (110, 240, 110), 15)
                        sfx.play("potion", 0.5)
                    continue
            elif l.kind == "anima" and d < 36:
                self.pending_anima += 1
                sfx.play("magic")
                continue
            elif l.kind == "item" and d < 30:
                if self.pickup_item(l.item):
                    continue
                if not l.warned:
                    l.warned = True
                    self.add_text(p.x, p.y, 60, "Sac plein !", RED, 16)
            elif l.kind == "item" and d > 60:
                l.warned = False
            keep.append(l)
        self.loot = keep

    def on_gold(self, amount):
        pass

    # ------------------------------------------------------------------ rendu 3D
    def render3d(self, fr):
        p = self.player
        t = self.time
        cam = self.cam
        cam.tx += (p.x - cam.tx) * 0.2
        cam.ty += (p.y - cam.ty) * 0.2
        sh = self.shake
        cam.shake_off = (random.uniform(-sh, sh), random.uniform(-sh, sh))
        env = self.env
        env.player = (p.x, p.y, 0)
        if not p.dead:
            p.render(fr, t)
        for m in self.monsters:
            if abs(m.x - p.x) < 1100 and abs(m.y - p.y) < 1100:
                m.render(fr, t)
        for a in self.allies:
            a.render(fr, t)
        for o in self.interactables:
            if abs(o.x - p.x) < 1300 and abs(o.y - p.y) < 1300:
                o.render(fr, t)
        for pr in self.projectiles:
            pr.render(fr, t)
        for ef in self.effects:
            ef.render(fr)
        for l in self.loot:
            l.render(fr, t)
        self.particles.render(fr)
        for bx, by, br in self.blood:
            fr.decal(bx, by, br, br * 0.85, (70, 6, 8), 0.75, kind=0, rot=bx)
        # lumières : lanterne du héros, torches, bougies, lave, éclairs
        fr.light(p.x, p.y, 70, 320, (255, 214, 170), 1.15 + 0.05 * math.sin(t * 9))
        for x, y, z in self.geo.torches:
            if abs(x - p.x) < 900 and abs(y - p.y) < 900:
                f = 1 + 0.12 * math.sin(t * 11 + x) + 0.06 * math.sin(t * 23 + y)
                fr.glow(x, y, z + 5, 18 * f, self.torch_col, 0.95)
                fr.part("cone", (x, y, z + 5), (2.6, 0, 0), (0, 0, 5 * f), (0, 2.6, 0), self.torch_col, 1.0)
                fr.light(x, y, z, 230 * f, self.torch_col, 1.25)
        for x, y, z in self.geo.candles:
            if abs(x - p.x) < 700 and abs(y - p.y) < 700:
                fr.glow(x, y, z, 7, (255, 200, 110), 0.9)
                fr.light(x, y, z, 70, (255, 190, 100), 0.6)
        for x, y in self.geo.lava:
            if abs(x - p.x) < 800 and abs(y - p.y) < 800:
                fr.decal(x, y, 14, 5, (255, 110, 30), 0.85 + 0.15 * math.sin(t * 2 + x), kind=0, rot=x)
                fr.light(x, y, 5, 90, (255, 90, 30), 0.7)
        for x, y, r, c, life, dur in self.flashes:
            fr.light(x, y, 40, r, c, 1.8 * life / dur)
        n = p.anima.get("tourbillon", 0)
        for i in range(n):
            a = t * 2.4 + i * math.tau / n
            fr.glow(p.x + math.cos(a) * 60, p.y + math.sin(a) * 60, 30, 26, (150, 230, 255), 0.9)
        self.render_extra(fr)
        return cam, env

    def render_extra(self, fr):
        pass

    # ------------------------------------------------------------------ interface
    def project(self, x, y, z=0.0):
        pt = self.cam.project(x, y, z)
        if not pt:
            return None
        return pt[0] / VIEW.s, pt[1] / VIEW.s

    def draw_ui(self, surf):
        p = self.player
        for m in self.monsters:
            if (m.hp < m.max_hp or m.elite) and not m.boss:
                pt = self.project(m.x, m.y, m.height() + 12)
                if not pt or not (0 < pt[0] < SCREEN_W and 0 < pt[1] < SCREEN_H):
                    continue
                w = 44 if not m.elite else 70
                r = pygame.Rect(pt[0] - w / 2, pt[1], w, 5)
                ui.rect(surf, (0, 0, 0, 180), r.inflate(2, 2), 0, 3)
                ui.rect(surf, (220, 40, 40), (r.x, r.y, max(1, r.w * max(0, m.hp / m.max_hp)), r.h), 0, 2)
                if m.elite:
                    ui.draw_text(surf, m.name, (pt[0], pt[1] - 3), 13, GOLD_BRIGHT, "bold", anchor="midbottom")
        for o in self.interactables:
            if o.label:
                pt = self.project(o.x, o.y, 78)
                if pt:
                    ui.draw_text(surf, o.label, pt, 14, WHITE, "bold", anchor="midbottom")
        for l in self.loot:
            if l.kind == "item" and (l.item["rarity"] != "commun" or math.hypot(l.x - p.x, l.y - p.y) < 160):
                pt = self.project(l.x, l.y, 30)
                if pt:
                    col = RARITY_COLORS[l.item["rarity"]]
                    tw, th = ui.text_size(l.item["name"], 13, "bold")
                    r = pygame.Rect(0, 0, tw + 14, th + 2)
                    r.midbottom = pt
                    ui.rect(surf, (0, 0, 0, 170), r, 0, r.h // 2)
                    ui.rect(surf, col, r, 1, r.h // 2)
                    ui.draw_text(surf, l.item["name"], r.center, 13, col, "bold", anchor="center", shadow=False)
        for tx in self.texts:
            pt = self.project(tx[0], tx[1], tx[2])
            if pt:
                k = tx[6] / tx[7]
                ui.draw_text(surf, tx[3], pt, tx[5], tx[4], "bold", anchor="center",
                             alpha=255 if k > 0.35 else int(255 * k / 0.35))
        obj = self.nearest_interactable()
        if obj and not self.modal:
            pt = self.project(obj.x, obj.y, 40)
            if pt:
                hud.draw_prompt(surf, obj.prompt, pt)
        if not p.dead:
            pt = self.project(p.x, p.y, 40)
            if pt:
                hud.draw_mana_wheel(surf, self, pt[0] + 34, pt[1] - 20)
        if p.hp < p.stats["max_hp"] * 0.3 and not p.dead:
            k = 0.5 + 0.5 * math.sin(self.time * 6)
            hud.low_hp_veil(surf, 40 + 40 * k)
        if self.big_map:
            hud.draw_big_map(surf, self)
        elif not isinstance(self.modal, MenuScreen):
            hud.draw_hud(surf, self)
        if self.left_panel:
            self.left_panel.draw(surf)
        if self.show_inv:
            self.inv_panel.draw(surf)
        if self.left_panel:
            self.left_panel.draw_tooltips(surf)
        if self.show_inv:
            self.inv_panel.draw_tooltips(surf)
        if not self.modal and not self.big_map:
            hud.draw_hud_tooltips(surf, self)
        if self.modal:
            if not isinstance(self.modal, (DeathPanel, MenuScreen)):
                ui.veil(surf, (0, 0, 0), 140)
            self.modal.draw(surf)
