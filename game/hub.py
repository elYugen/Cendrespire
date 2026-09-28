"""Cendreval, la ville au pied de la tour : marchand, forgeronne, couturière, habitants, portail vers les étages."""
import math
import random

from . import quests, sfx, ui
from . import town as T
from .dungeon import build_hub
from .entities import NPC, Portal, Prop, Stash
from .items import generate_item, generate_artifact
from .forge import ForgeScreen
from .panels import PortalPanel, QuestPanel, ServicePanel
from .shop import ShopScreen
from .r3d import models, objmodels
from .training import TrainingDummy
from .tutorial import Tutorial
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
        self.add_npc("gorvan", mx, my, mf, "Commercer", models.NPC_SPECS["marchand"], self.open_merchant)
        sx, sy, sf = T.SMITH
        self.add_npc("hilda", sx, sy, sf, "Forge", models.NPC_SPECS["forgeronne"], self.open_forge, work=True)
        tx, ty, tf = T.TAILOR
        self.add_npc("ysolde", tx, ty, tf, "Changer d'apparence", models.NPC_SPECS["couturiere"], self.open_wardrobe)
        ox, oy, of = T.ORIANE
        self.add_npc("oriane", ox, oy, of, "Oublier ses attributs", self.villager_spec("witch", {
            "Purple": (110, 70, 170), "Gold": (210, 200, 240)}), self.open_oblivion)
        dx, dy, df = T.THEODRIC
        self.add_npc("theodric", dx, dy, df, "Oublier ses talents", self.villager_spec("hooded", {
            "Black": (60, 70, 110), "LightBrown": (200, 180, 130)}), self.open_talent_reset)
        px, pz = T.PORTAL
        grand = bool(objmodels.family("dungeon"))
        self.interactables.append(Portal(px * TILE, (pz + (0.05 if grand else 0.3)) * TILE, "Entrer dans la Tour",
                                         self.open_portal, (150, 110, 255), grand=grand))
        self.interactables.append(Stash(T.STASH[0] * TILE, T.STASH[1] * TILE, self.open_stash))
        self.add_villagers()
        self.dummy = TrainingDummy(T.DUMMY[0] * TILE, T.DUMMY[1] * TILE)
        self.monsters.append(self.dummy)
        if not objmodels.family("camp"):      # décor procédural si les modèles importés manquent
            self.interactables.append(Prop(T.ANVIL[0] * TILE, T.ANVIL[1] * TILE, models.anvil))
        self.obstacles = [(x * TILE, y * TILE, r * TILE) for x, y, r in T.obstacles()]
        lvl = max(1, player.max_floor)
        stock = [generate_item(lvl, cls_id=player.cls_id, tier=random.choice([0, 1, 1])) for _ in range(7)]
        stock += [generate_artifact(lvl, random.choice(["commun", "magique", "rare"])) for _ in range(2)]
        self.shop_stock = stock
        self._last_hit = 0.0
        self.tutorial = Tutorial(self) if player.tutorial is not None else None
        self.save()
        sfx.music("hub")
        self.show_banner(T.NAME, message or "La ville au pied de Cendrespire", WHITE, 5)

    def add_npc(self, npc_id, x, y, facing, prompt, spec, action, work=False, route=None):
        """Personnage de la ville : son action habituelle passe d'abord par les quêtes qu'il donne ou reprend."""
        name = T.SHOPKEEPERS.get(npc_id) or next(v["name"] for v in T.VILLAGERS if v["id"] == npc_id)
        npc = NPC(x * TILE, y * TILE, name, prompt, spec, None, facing=facing, work=work, npc_id=npc_id,
                  route=[(px * TILE, py * TILE) for px, py in route or []])
        npc.action = lambda world: self.talk_to(npc, prompt, action)
        self.interactables.append(npc)
        return npc

    @staticmethod
    def villager_spec(model, palette):
        return dict(detailed=True, body=(120, 100, 80), skin=(220, 180, 140), rig={"model": model, "palette": palette})

    def add_villagers(self):
        """Habitants de la ville : animés, certains se promènent ; chacun a une réplique."""
        for v in T.VILLAGERS:
            spec = self.villager_spec(v["model"], v["palette"])

            npc = self.add_npc(v["id"], *v["pos"], v["facing"], "Parler", spec, None, route=v.get("route"))
            npc.greeting = v["line"]
            npc.action = lambda world, npc=npc: self.talk_to(npc, "Parler", lambda w: npc.say(w, npc.greeting))

    def talk_to(self, npc, label, action):
        p = self.player
        if self.tutorial:
            self.tutorial.flags.add("talk")
        quests.event(self, "talk", npc=npc.npc_id)
        if quests.to_turn_in(p, npc.npc_id) or quests.offers(p, npc.npc_id):
            self.close_panels()
            self.modal = QuestPanel(self, npc, label, action)
            sfx.play("click")
            return
        active = quests.in_progress(p, npc.npc_id)
        if active and label == "Parler":
            q = quests.QUESTS[active[0]]
            npc.say(self, q.get("progress", q["desc"]))
            return
        action(self)

    def greet_line(self, npc):
        return getattr(npc, "greeting", None) or T.GREETINGS.get(npc.npc_id)

    def npc_marker(self, o):
        return quests.marker(self.player, getattr(o, "npc_id", None))

    def hud_title(self):
        return "", ""           # pas de nom au-dessus de la minicarte en ville

    # ------------------------------------------------------------------ tutoriel
    def handle_event(self, e):
        if self.tutorial and not self.modal and self.tutorial.handle_event(e):
            self.click_block = True
            return
        super().handle_event(e)

    def ui_contains(self, pos):
        return bool(self.tutorial and self.tutorial.contains(pos)) or super().ui_contains(pos)

    def update(self, dt):
        super().update(dt)
        if self.tutorial:
            self.tutorial.update(dt)
            if self.player.tutorial is None:
                self.tutorial = None

    def draw_ui(self, surf):
        super().draw_ui(surf)
        dm = self.dummy
        if dm.hits and not self.modal and not self.big_map:
            pt = self.project(dm.x, dm.y, dm.height() + 58)
            if pt:
                ui.draw_text(surf, f"{dm.dps():.0f} dégâts / s", pt, 16, (255, 214, 110), "bold",
                             anchor="midbottom")
        if self.tutorial and not self.modal and not self.big_map:
            self.tutorial.draw(surf)

    def presence(self):
        hero, small = self.hero_presence()
        return f"Dans le village de {T.NAME}", hero, small

    def open_merchant(self, world):
        self.close_panels()
        self.modal = ShopScreen(self, "gorvan")
        sfx.play("click")

    def open_forge(self, world):
        self.close_panels()
        self.modal = ForgeScreen(self)
        sfx.play("chest")

    def step_sound(self, p):
        """En ville : pavés dans les rues, herbe et terre ailleurs."""
        from .settings import TILE
        cell = (int(p.x // TILE), int(p.y // TILE))
        return "step_stone" if cell in getattr(self.dungeon, "plaza", ()) else "step_grass"

    def open_stash(self, world):
        from .stash import StashScreen
        self.close_panels()
        self.modal = StashScreen(self)
        sfx.play("chest")

    def open_wardrobe(self, world):
        self.close_panels()
        self.modal = WardrobePanel(self)
        sfx.play("click")

    def open_oblivion(self, world):
        """Oriane : rend tous les points d'attribut répartis contre une Larme d'oubli."""
        p = self.player
        spent = sum(p.alloc.values())
        lines = [("« Les forces que vous avez choisies peuvent être défaites. Donnez-moi une Larme d'oubli, "
                  "et vos points d'attribut vous seront rendus, prêts à être répartis autrement. »", (235, 225, 200)),
                 (f"Points d'attribut répartis : {spent}", WHITE),
                 (f"Larmes d'oubli : {p.tears}  (sur les champions et les gardiens de la tour)", (190, 150, 255))]
        self.close_panels()
        self.modal = ServicePanel(self, "Sanctuaire de l'Oubli", lines, "Oublier mes attributs", self.reset_attributes,
                                  enabled=spent > 0 and p.tears >= 1, cost="1 Larme d'oubli", cost_ok=p.tears >= 1)
        sfx.play("click")

    def open_talent_reset(self, world):
        """Théodric : efface l'arbre de talents contre des pièces."""
        from . import talents
        p = self.player
        cost = talents.reset_cost(p.level)
        n = talents.spent(p.talents)
        lines = [("« Chaque talent est une page que vous avez écrite. Je peux effacer tout le livre, contre de quoi "
                  "entretenir ma bibliothèque. Vos points vous seront rendus. »", (235, 225, 200)),
                 (f"Points de talent dépensés : {n}", WHITE)]
        self.close_panels()
        self.modal = ServicePanel(self, "Bibliothèque de Cendreval", lines, "Oublier mes talents", self.reset_talents,
                                  enabled=n > 0 and p.money >= cost, cost=cost, cost_ok=p.money >= cost)
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
        for o in self.interactables:
            if isinstance(o, NPC) and not o.work:
                o.update(dt, self)
            if isinstance(o, NPC):
                self.greet(o)
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
