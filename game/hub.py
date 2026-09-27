"""Cendreval, la ville au pied de la tour : marchand, forgeronne, couturière, habitants, portail vers les étages."""
import math
import random

from . import sfx
from . import town as T
from .dungeon import build_hub
from .entities import NPC, Portal, Prop
from .items import generate_item, generate_artifact
from .panels import MerchantPanel, ForgePanel, PortalPanel
from .r3d import models, objmodels
from .wardrobe import WardrobePanel
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
        self.env.fog = (16.0, 28.0)
        self.env.sun_dir = (-0.6, -0.8, -0.25)
        player.reset_run()
        player.x, player.y = T.SPAWN[0] * TILE, T.SPAWN[1] * TILE
        player.facing = -math.pi / 2
        self.cam.tx, self.cam.ty = player.x, player.y
        mx, my, mf = T.MERCHANT
        self.interactables.append(NPC(mx * TILE, my * TILE, "Gorvan le Marchand", "Commercer",
                                      models.NPC_SPECS["marchand"], self.open_merchant, facing=mf))
        sx, sy, sf = T.SMITH
        self.interactables.append(NPC(sx * TILE, sy * TILE, "Hilda la Forgeronne", "Forge",
                                      models.NPC_SPECS["forgeronne"], self.open_forge, facing=sf, work=True))
        tx, ty, tf = T.TAILOR
        self.interactables.append(NPC(tx * TILE, ty * TILE, "Ysolde la Couturière", "Changer d'apparence",
                                      models.NPC_SPECS["couturiere"], self.open_wardrobe, facing=tf))
        px, pz = T.PORTAL
        grand = bool(objmodels.family("dungeon"))
        self.interactables.append(Portal(px * TILE, (pz + (0.05 if grand else 0.3)) * TILE, "Entrer dans la Tour",
                                         self.open_portal, (150, 110, 255), grand=grand))
        self.add_villagers()
        if not objmodels.family("camp"):      # décor procédural si les modèles importés manquent
            self.interactables.append(Prop(T.ANVIL[0] * TILE, T.ANVIL[1] * TILE, models.anvil))
        self.obstacles = [(x * TILE, y * TILE, r * TILE) for x, y, r in T.obstacles()]
        lvl = max(1, player.max_floor)
        stock = [generate_item(lvl, cls_id=player.cls_id, tier=random.choice([0, 1, 1])) for _ in range(7)]
        stock += [generate_artifact(lvl, random.choice(["commun", "magique", "rare"])) for _ in range(2)]
        self.shop_stock = stock
        self._last_hit = 0.0
        self.save()
        sfx.music("hub")
        self.show_banner(T.NAME, message or "La ville au pied de Cendrespire", WHITE, 5)
        self.message("Échap : menu · les touches sont dans Système > Commandes", (220, 215, 200), 8)

    def add_villagers(self):
        """Habitants de la ville : animés, ils ont chacun une réplique."""
        for x, y, facing, name, model, pal, line in T.VILLAGERS:
            spec = dict(detailed=True, body=(120, 100, 80), skin=(220, 180, 140), rig={"model": model, "palette": pal})

            def talk(world, name=name, line=line):
                world.message(f"{name} : « {line} »", (235, 225, 200), 6)
            self.interactables.append(NPC(x * TILE, y * TILE, name, "Parler", spec, talk, facing=facing))

    def hud_title(self):
        return T.NAME, ""

    def open_merchant(self, world):
        self.left_panel = MerchantPanel(self)
        self.show_inv = True
        sfx.play("click")

    def open_forge(self, world):
        self.left_panel = ForgePanel(self)
        self.show_inv = True
        sfx.play("chest")

    def open_wardrobe(self, world):
        self.close_panels()
        self.modal = WardrobePanel(self)
        sfx.play("click")

    def open_portal(self, world):
        self.close_panels()
        self.modal = PortalPanel(self)
        sfx.play("portal")

    def enter_tower(self, floor):
        from .tower import TowerScene
        self.save()
        from .data import floor_name
        self.game.load_scene(lambda: TowerScene(self.game, self.player, floor), f"Étage {floor}", floor_name(floor))

    def update_extra(self, dt):
        p = self.player
        if self.left_panel:
            near = any(isinstance(o, NPC) and math.hypot(o.x - p.x, o.y - p.y) < 140 for o in self.interactables)
            if not near:
                self.close_panels()
        # fontaine : gerbe d'eau au sommet de la statue
        fx, fy = T.FOUNTAIN
        if random.random() < 0.6:
            a = random.random() * math.tau
            self.particles.emit(fx * TILE + math.cos(a) * 6, fy * TILE + math.sin(a) * 6, (170, 215, 255), n=1,
                                speed=30, life=0.7, size=3, glow=False, gravity=260, up=110, z=64)
        # forge : étincelles quand le marteau frappe, fumée de la cheminée du four
        ax, ay = T.ANVIL
        hit = math.sin(self.time * 2.6)
        if hit < 0 <= self._last_hit:
            self.particles.emit(ax * TILE, ay * TILE, (255, 190, 90), n=7, speed=70, life=0.5, size=2, up=90,
                                z=16, zs=0.3)
            if math.hypot(p.x - ax * TILE, p.y - ay * TILE) < 260:
                sfx.play("hit", 0.08)
        self._last_hit = hit
        kx, ky = T.FURNACE
        if random.random() < 0.25:
            self.particles.emit((kx + 0.15) * TILE, (ky + 0.1) * TILE, random.choice([(90, 88, 92), (120, 116, 118)]),
                                n=1, speed=6, life=2.6, size=7, glow=False, up=40, z=88, zs=0.1)

    def render_extra(self, fr):
        # Cendrespire, la tour qui domine le campement
        t = self.time
        tx, ty = T.TOWER[0] * TILE, T.TOWER[1] * TILE
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
        # bouche du four de la forge
        fx, fz = T.FURNACE
        k = 1 + 0.15 * math.sin(t * 9) + 0.08 * math.sin(t * 23)
        fr.glow((fx - 0.5) * TILE, fz * TILE, 13, 22 * k, (255, 120, 40), 0.9)
        fr.light((fx - 0.8) * TILE, fz * TILE, 20, 220 * k, (255, 120, 50), 1.3)
        # lucioles au-dessus des jardins
        for i in range(32):
            ph = i * 2.399
            gx, gy, gw, gh = T.FIREFLIES[i % len(T.FIREFLIES)]
            x = (gx + (i * 7.3) % gw + 1.2 * math.sin(t * 0.3 + ph)) * TILE
            y = (gy + (i * 3.7) % gh + 1.0 * math.cos(t * 0.23 + ph * 1.3)) * TILE
            a = max(0.0, math.sin(t * 1.7 + ph * 3))
            if a > 0.05:
                fr.glow(x, y, 26 + 14 * math.sin(t * 0.9 + ph), 7, (200, 255, 120), 0.8 * a)
