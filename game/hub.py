"""Le campement au pied de la tour : marchand, forgeronne, portail vers les étages."""
import math
import random

from . import sfx
from .dungeon import build_hub
from .entities import NPC, Portal, Campfire
from .items import generate_item
from .panels import MerchantPanel, ForgePanel, PortalPanel
from .render import darker
from .settings import TILE, GOLD_BRIGHT
from .world import World

MERCHANT_SPEC = dict(body=(110, 80, 50), head=(210, 170, 130), legs=(70, 52, 36), hood=(90, 60, 36),
                     weapon=None, arm=(110, 80, 50))
SMITH_SPEC = dict(body=(90, 70, 60), head=(220, 175, 140), legs=(60, 45, 35), apron=(70, 45, 30), weapon="axe",
                  hair=(200, 120, 60), bulky=True, arm=(220, 175, 140))


class HubScene(World):
    theme = "hub"
    ambient = (74, 64, 78)
    reveal_all = True

    def __init__(self, game, player, message=None):
        d = build_hub()
        super().__init__(game, player, d, random.Random())
        player.reset_run()
        player.x, player.y = 17.5 * TILE, 14 * TILE
        self.interactables.append(NPC(6.5 * TILE, 10.5 * TILE, "Gorvan le Marchand", "Commercer", MERCHANT_SPEC,
                                      self.open_merchant, facing=0.3))
        self.interactables.append(NPC(29 * TILE, 10.5 * TILE, "Hilda la Forgeronne", "Forge", SMITH_SPEC,
                                      self.open_forge, facing=math.pi - 0.3))
        self.interactables.append(Portal(17 * TILE, 6.2 * TILE, "Entrer dans la Tour", self.open_portal))
        self.interactables.append(Campfire(17.5 * TILE, 11 * TILE))
        lvl = max(1, player.max_floor)
        self.shop_stock = [generate_item(lvl, cls_id=player.cls_id, tier=random.choice([0, 1, 1])) for _ in range(8)]
        self.snap_camera()
        self.save()
        if message:
            self.show_banner("Le Campement", message, GOLD_BRIGHT, 5)
        else:
            self.show_banner("Le Campement", "Au pied de la Tour des Tourments", GOLD_BRIGHT, 4)
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
        # s'éloigner d'un PNJ ferme son panneau
        p = self.player
        if self.left_panel and not isinstance(self.left_panel, type(None)):
            near = any(isinstance(o, NPC) and math.hypot(o.x - p.x, o.y - p.y) < 140 for o in self.interactables)
            if not near:
                self.close_panels()
        fire = self.interactables[3]
        if random.random() < 0.6:
            self.particles.emit(fire.x + random.uniform(-10, 10), fire.y - 8, random.choice([(255, 140, 40), (255, 200, 90)]),
                                n=1, speed=20, life=0.8, size=5, up=70)
