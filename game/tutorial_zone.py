"""Les Faubourgs de Cendreval : zone d'apprentissage jouée avant la première arrivée en ville.

Quatre salles en enfilade : on apprend à se déplacer, à attaquer un squelette isolé, à esquiver, à lancer un sort
et à boire la potion, puis on nettoie une salle plus peuplée, on ouvre un coffre, on regarde son butin et l'on
franchit le portail vers Cendreval (où le tutoriel continue : habitants, carte, Tour).
Une carte « pop-up » présente chaque étape avec les vraies touches (clavier ou manette)."""
import math
import random

import pygame

from . import controls, hud, sfx, ui
from .dungeon import Dungeon, Room
from .entities import Chest, Loot, Monster, Portal
from .items import generate_item
from .r3d import level
from .settings import GOLD_BRIGHT, SCREEN_W, SHEIKAH, WHITE
from .world import World

SOFT = (206, 212, 212)
DONE = (140, 235, 140)
VILLAGE_STEP = 5            # le tutoriel de la ville reprend aux habitants (voir tutorial.STEPS)

ROOMS = [Room(3, 11, 10, 9), Room(19, 10, 11, 11), Room(36, 8, 13, 15), Room(55, 11, 9, 9)]


def _menu_open(w):
    from .panels import MenuScreen
    return isinstance(w.modal, MenuScreen)


# (titre, texte, touches : actions de controls ou libellés entre crochets, condition de réussite)
STEPS = [
    ("Se déplacer", "Avancez vers la salle suivante, avec les touches de déplacement ou un clic gauche sur le sol.",
     ["up", "left", "down", "right", "[Clic gauche]"], lambda w: w.moved()),
    ("Attaquer", "Un squelette rôde dans la salle suivante. Cliquez sur lui : votre héros s'approche et frappe "
     "tout seul. Maintenez le clic pour enchaîner.", ["attack", "[Clic gauche]"], lambda w: w.first_dead()),
    ("Esquiver", "La roulade vous rend invulnérable un court instant : parfait contre les attaques annoncées au sol.",
     ["roll"], lambda w: w.player.roll_cd > 0),
    ("Lancer un sort", "Vos sorts consomment du mana (le cercle bleu près du héros). Lancez votre premier sort.",
     ["spell1", "[Clic droit]"], lambda w: any(v > 0 for v in w.player.cds.values())),
    ("Se soigner", "La potion rend une partie de votre vie, puis se recharge toute seule. Buvez-la.",
     ["potion"], lambda w: w.player.potion_cd > 0),
    ("Nettoyer la salle", "Plusieurs créatures gardent la grande salle. Éliminez-les toutes.",
     [], lambda w: w.hall_clear()),
    ("Ouvrir le coffre", "Un coffre attend dans la dernière salle. Approchez-vous et interagissez avec lui.",
     ["interact"], lambda w: w.chest.opened),
    ("L'inventaire", "Ramassez le butin en marchant dessus, puis ouvrez l'inventaire pour l'équiper.",
     ["inventory"], lambda w: w.menu_seen),
    ("Rejoindre Cendreval", "Le portail au fond de la salle mène au village, au pied de la Tour.",
     ["interact"], lambda w: False),
]


def build():
    d = Dungeon(68, 32)
    for r in ROOMS:
        d.carve_rect(r)
    for a, b in zip(ROOMS, ROOMS[1:]):
        d.carve_path(a.center, b.center)
    d.rooms = list(ROOMS)
    d.start_room, d.boss_room = ROOMS[0], ROOMS[-1]
    d._decorate(random.Random(7))
    return d


class TutorialZoneScene(World):
    """Zone d'apprentissage (les étapes ne sont pas sauvegardées : on la rejoue en entier si on la quitte)."""
    is_tower = True

    def __init__(self, game, player):
        self.floor = 1
        d = build()
        super().__init__(game, player, d, level.floor_theme(1), random.Random(11))
        player.reset_run()
        sx, sy = ROOMS[0].center_px
        player.x, player.y = sx, sy
        self.cam.tx, self.cam.ty = sx, sy
        self.origin = (sx, sy)
        self.step = 0
        self.done_t = None
        self.pop_t = 0.0                      # animation d'apparition de la carte
        self.t = 0.0
        self.menu_seen = False                # le menu a été ouvert (le monde est en pause pendant ce temps)
        # un squelette seul, puis la grande salle
        cx, cy = ROOMS[1].center_px
        self.first = Monster("squelette", cx + 40, cy, 1)
        self.first.hp = self.first.max_hp = self.first.max_hp * 0.6
        self.hall = []
        hx, hy = ROOMS[2].center_px
        for mid, ox, oy in (("squelette", -60, -50), ("zombie", 70, 10), ("archer", -20, 80)):
            m = Monster(mid, hx + ox, hy + oy, 1)
            m.hp = m.max_hp = m.max_hp * 0.7
            self.hall.append(m)
        self.monsters += [self.first] + self.hall
        ex, ey = ROOMS[3].center_px
        self.chest = Chest(ex - 50, ey + 30)
        self.interactables.append(self.chest)
        self.interactables.append(Portal(ex + 60, ey - 20, "Rejoindre Cendreval", self.leave, (150, 110, 255)))
        self.rect = pygame.Rect(SCREEN_W // 2 - 330, 16, 660, 108)
        self.skip_rect = pygame.Rect(self.rect.right - 92, self.rect.y + 10, 80, 24)
        self.show_banner("Les Faubourgs", "Aux portes de Cendreval", WHITE, 4)
        sfx.music("hub")

    # ------------------------------------------------------------------ conditions
    def moved(self):
        return math.hypot(self.player.x - self.origin[0], self.player.y - self.origin[1]) > 200

    def first_dead(self):
        return self.first.dead or self.first not in self.monsters

    def hall_clear(self):
        return all(m.dead or m not in self.monsters for m in self.hall)

    def floor_level(self):
        return 1

    def hud_title(self):
        return "Les Faubourgs", ""

    def presence(self):
        hero, small = self.hero_presence()
        return "Dans les Faubourgs (tutoriel)", hero, small

    def on_gold(self, amount):
        pass

    # ------------------------------------------------------------------ déroulé
    def update_extra(self, dt):
        self.t += dt
        self.pop_t += dt
        if self.step >= len(STEPS):
            return
        if self.done_t is None:
            if STEPS[self.step][3](self):
                self.done_t = 1.0
                sfx.play("pickup", 0.8)
        else:
            self.done_t -= dt
            if self.done_t <= 0 and not self.modal:
                self.done_t = None
                self.step += 1
                self.pop_t = 0.0
                self.origin = (self.player.x, self.player.y)

    def open_chest(self, chest):
        p = self.player
        sfx.play("chest")
        self.loot.append(Loot(chest.x, chest.y, "item", generate_item(2, rarity="magique", cls_id=p.cls_id)))
        self.loot.append(Loot(chest.x, chest.y, "gold", amount=self.gold_amount(8)))
        self.particles.emit(chest.x, chest.y, (255, 214, 100), n=30, speed=130, life=0.8, size=3, up=200, z=15)

    def death_penalty(self):
        """Dans les Faubourgs, on ne meurt pas vraiment : le héros se relève aussitôt."""
        p = self.player
        p.dead = False
        p.hp = p.stats["max_hp"]
        p.invuln = 2.5
        self.show_banner("Relevez-vous !", "Reculez et esquivez les coups (roulade)", (255, 200, 120), 3)

    def leave(self, world=None, skipped=False):
        from .hub import HubScene
        p = self.player
        p.tutorial = None if skipped else VILLAGE_STEP
        p.reset_run()
        self.save()
        msg = f"Bienvenue, {p.name}. La Tour vous attend."
        self.game.load_scene(lambda: HubScene(self.game, p, msg), "Cendreval", "La ville au pied de Cendrespire")

    def exit_to_hub(self, message=None):
        self.leave()

    # ------------------------------------------------------------------ carte de l'étape
    def handle_event(self, e):
        if not self.modal and e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if self.skip_rect.collidepoint(e.pos):
                self.leave(skipped=True)
            self.click_block = True
            return
        super().handle_event(e)

    def ui_contains(self, pos):
        return self.rect.collidepoint(pos) or super().ui_contains(pos)

    def draw_ui(self, surf):
        if _menu_open(self):
            self.menu_seen = True
        super().draw_ui(surf)
        if self.modal or self.big_map or self.step >= len(STEPS):
            return
        title, text, keys, _ = STEPS[self.step]
        ok = self.done_t is not None
        k = min(1.0, self.pop_t / 0.25)
        r = self.rect.copy()
        r.y = int(self.rect.y - (1 - k) * 30)
        ui.rect(surf, (0, 0, 0, int(90 * k)), r.move(3, 5), 0, 14)
        ui.botw_box(surf, r, int(215 * k), DONE if ok else SHEIKAH, radius=14, fill=(8, 20, 28))
        ui.draw_text(surf, f"TUTORIEL  {self.step + 1} / {len(STEPS)}", (r.x + 20, r.y + 12), 12, SHEIKAH, "bold")
        hov = self.skip_rect.collidepoint(ui.mouse_pos())
        ui.botw_box(surf, self.skip_rect.move(0, r.y - self.rect.y), 180 if hov else 110,
                    SHEIKAH if hov else (110, 112, 110), radius=12)
        ui.draw_text(surf, "Passer", self.skip_rect.move(0, r.y - self.rect.y).center, 12, WHITE if hov else SOFT,
                     anchor="center", shadow=False)
        ui.draw_text(surf, ("Bravo ! " if ok else "") + title, (r.x + 20, r.y + 30), 22, DONE if ok else WHITE,
                     "title")
        y = r.y + 64
        for line in ui.wrap(text, 14, r.w - 40)[:2]:
            ui.draw_text(surf, line, (r.x + 20, y), 14, SOFT)
            y += 19
        # touches de l'étape, en grand, à droite du titre
        x = r.x + 30 + ui.text_size(("Bravo ! " if ok else "") + title, 22, "title")[0] + 14
        pulse = 1 + 0.08 * math.sin(self.t * 5)
        for key in keys:
            if not key.startswith("[") and not hud.pad_btn(key) and key not in controls.keys:
                continue                       # action sans touche du clavier (l'attaque : clic de souris)
            if key.startswith("["):
                label = key[1:-1]
                w = ui.text_size(label, 12, "bold")[0] + 16
                if x + w > self.skip_rect.x - 8:
                    break
                ui.key_badge(surf, label, (x + w / 2, r.y + 44), 12, DONE if ok else GOLD_BRIGHT)
                x += w + 8
            else:
                if x + 30 > self.skip_rect.x - 8:
                    break
                br = hud.key_icon(surf, key, (x + 14, r.y + 44), 12 * (1 if ok else pulse))
                x += max(28, br.w + 8)
        for i in range(len(STEPS)):
            c = (r.centerx - (len(STEPS) - 1) * 9 + i * 18, r.bottom - 1)
            col = DONE if i < self.step or (i == self.step and ok) else (SHEIKAH if i == self.step else (70, 74, 72))
            ui.circle(surf, col, c, 4 if i == self.step else 3)
