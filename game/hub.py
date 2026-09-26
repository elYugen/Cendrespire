"""Le campement au pied de la tour : marchand, forgeronne, portail vers les étages."""
import math
import random

from . import sfx
from .dungeon import build_hub
from .entities import NPC, Portal, Campfire, Prop
from .items import generate_item, generate_artifact
from .panels import MerchantPanel, ForgePanel, PortalPanel
from .r3d import models
from .settings import TILE, WHITE
from .world import World


class HubScene(World):
    hub = True
    reveal_all = True

    def __init__(self, game, player, message=None):
        d = build_hub()
        super().__init__(game, player, d, "camp", random.Random(4))
        self.env.sky = ((0.10, 0.12, 0.25), (0.32, 0.26, 0.42), (0.55, 0.36, 0.34), (0.8, 0.9, 0.5), (0.5, 0.35, 0.3))
        self.env.fog_col = (0.16, 0.14, 0.24)
        self.env.fog = (15.0, 26.0)
        self.env.sun_dir = (-0.6, -0.8, -0.25)
        player.reset_run()
        player.x, player.y = 17.5 * TILE, 13.5 * TILE
        self.cam.tx, self.cam.ty = player.x, player.y
        self.interactables.append(NPC(6.5 * TILE, 10.5 * TILE, "Gorvan le Marchand", "Commercer",
                                      models.NPC_SPECS["marchand"], self.open_merchant, facing=0.3))
        self.interactables.append(NPC(29 * TILE, 10.5 * TILE, "Hilda la Forgeronne", "Forge",
                                      models.NPC_SPECS["forgeronne"], self.open_forge, facing=math.pi - 0.3))
        self.interactables.append(Portal(17 * TILE, 6.4 * TILE, "Entrer dans la Tour", self.open_portal))
        self.fire = Campfire(17.5 * TILE, 10.5 * TILE)
        self.interactables.append(self.fire)
        self.interactables.append(Prop(5 * TILE, 8.2 * TILE, models.tent, (170, 70, 60), 0.4))
        self.interactables.append(Prop(8.2 * TILE, 12.8 * TILE, models.crate))
        self.interactables.append(Prop(7.4 * TILE, 12.9 * TILE, models.barrel))
        self.interactables.append(Prop(30.5 * TILE, 8.5 * TILE, models.tent, (70, 90, 150), 2.6))
        self.interactables.append(Prop(27.6 * TILE, 11.6 * TILE, models.anvil))
        self.interactables.append(Prop(26.6 * TILE, 12.8 * TILE, models.barrel))
        lvl = max(1, player.max_floor)
        stock = [generate_item(lvl, cls_id=player.cls_id, tier=random.choice([0, 1, 1])) for _ in range(7)]
        stock += [generate_artifact(lvl, random.choice(["commun", "magique", "rare"])) for _ in range(2)]
        self.shop_stock = stock
        self.save()
        self.show_banner("Le Campement", message or "Au pied de la Tour des Tourments", WHITE, 5)
        self.message("ZQSD/WASD : se déplacer · E : parler · I : équipement · C : personnage · Échap : pause",
                     (220, 215, 200), 12)

    def hud_title(self):
        return "Le Campement", ""

    def open_merchant(self, world):
        self.left_panel = MerchantPanel(self)
        self.show_inv = True
        sfx.play("click")

    def open_forge(self, world):
        self.left_panel = ForgePanel(self)
        self.show_inv = True
        sfx.play("chest")

    def open_portal(self, world):
        self.close_panels()
        self.modal = PortalPanel(self)
        sfx.play("portal")

    def enter_tower(self, floor):
        from .tower import TowerScene
        self.save()
        self.game.change_scene(TowerScene(self.game, self.player, floor))

    def update_extra(self, dt):
        p = self.player
        if self.left_panel:
            near = any(isinstance(o, NPC) and math.hypot(o.x - p.x, o.y - p.y) < 140 for o in self.interactables)
            if not near:
                self.close_panels()
        f = self.fire
        if random.random() < 0.7:
            self.particles.emit(f.x + random.uniform(-8, 8), f.y + random.uniform(-8, 8),
                                random.choice([(255, 140, 40), (255, 200, 90)]), n=1, speed=12, life=0.9, size=4,
                                up=110, z=12, zs=0)
        if random.random() < 0.08:
            self.particles.emit(f.x, f.y, (255, 170, 60), n=1, speed=30, life=2.0, size=2, up=160, z=30, zs=0.2)

    def render_extra(self, fr):
        # la Tour des Tourments, qui domine le campement
        t = self.time
        tx, ty = 17 * TILE, 3 * TILE
        fr.part("cylinder", (tx, ty, 200), (95, 0, 0), (0, 0, 200), (0, 95, 0), (70, 66, 74))
        fr.part("cylinder", (tx, ty, 420), (80, 0, 0), (0, 0, 22), (0, 80, 0), (56, 52, 60))
        for i in range(10):
            a = i / 10 * math.tau
            fr.part("cube", (tx + math.cos(a) * 88, ty + math.sin(a) * 88, 450), (12, 0, 0), (0, 0, 14), (0, 12, 0),
                    (70, 66, 74))
        for i in range(6):
            a = i / 6 * math.tau + 0.3
            h = 120 + (i % 3) * 90
            fr.part("cube", (tx + math.cos(a) * 96, ty + math.sin(a) * 96, h), (3, 0, 0), (0, 0, 12), (0, 3, 0),
                    (255, 60, 40), 1.0)
        for i in range(8):
            a = t * 0.7 + i * math.tau / 8
            r = 130 + 20 * math.sin(t + i)
            fr.glow(tx + math.cos(a) * r, ty + math.sin(a) * r, 470 + 30 * math.sin(t * 1.3 + i), 60, (255, 60, 40), 0.7)
        fr.light(tx, ty + 120, 60, 420, (255, 60, 40), 0.9)
