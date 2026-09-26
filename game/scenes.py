"""Écrans hors-jeu façon Zelda Breath of the Wild : titre (paysage 3D), chargement, création de personnage."""
import datetime
import math
import random

import numpy as np
import pygame

from . import save, sfx, ui
from .data import CLASSES, SPELLS, ATTR_NAMES, ATTRS
from .entities import Player
from .r3d import models
from .r3d.camera import Camera3D, U
from .r3d.meshes import MeshBuilder, STRIDE
from .r3d.renderer import Env
from .settings import SCREEN_W, SCREEN_H, WHITE, SHEIKAH, UI_LINE, TEXT_DIM, RED, GOLD_BRIGHT
from .world import Scene

SOFT = (214, 218, 218)
NAMES = ["Aldric", "Morwen", "Kaelen", "Sybille", "Thorgar", "Ysolde", "Varian", "Lyra", "Elowen", "Brann"]
TOWER = (-260.0, -4200.0)     # position logique de la tour au loin


# =========================================================================== paysage 3D
def _height(x, z):
    """Relief en mètres (coordonnées 3D x, z)."""
    h = 0.9 * math.sin(x * 0.13) + 0.7 * math.cos(z * 0.17 + x * 0.05) + 0.4 * math.sin(x * 0.31 + z * 0.23)
    h += 3.2 * math.exp(-(x * x + (z - 1) ** 2) / 30)          # colline du héros
    h -= 2.2 * math.exp(-((z + 30) ** 2) / 260)                 # vallée
    h += 5 * max(0.0, (-z - 80) / 20) ** 1.5 if z < -80 else 0  # plateau de la tour
    return h


def build_landscape(seed=7):
    rng = random.Random(seed)
    mb = MeshBuilder()
    step = 2.0
    xs = np.arange(-70, 70 + step, step)
    zs = np.arange(-130, 16 + step, step)
    quads = []
    for zi in range(len(zs) - 1):
        for xi in range(len(xs) - 1):
            x0, x1, z0, z1 = xs[xi], xs[xi + 1], zs[zi], zs[zi + 1]
            p = [(x0, _height(x0, z0), z0), (x1, _height(x1, z0), z0), (x1, _height(x1, z1), z1),
                 (x0, _height(x0, z1), z1)]
            a, b, c = np.array(p[0]), np.array(p[1]), np.array(p[3])
            n = np.cross(c - a, b - a)
            n = n / (np.linalg.norm(n) + 1e-9)
            if n[1] < 0:
                n = -n
            hmid = sum(q[1] for q in p) / 4
            g = rng.uniform(-0.05, 0.05)
            dry = max(0.0, min(1.0, (hmid - 1.5) * 0.25))
            col = (0.32 + g + dry * 0.25, 0.52 + g + dry * 0.05, 0.22 + g * 0.5)
            if n[1] < 0.8:
                col = (0.46 + g, 0.43 + g, 0.38 + g)
            quads.append((p, n, col))
    v = []
    for p, n, col in quads:
        for tri in ((0, 1, 2), (0, 2, 3)):
            for i in tri:
                v.extend((*p[i], *n, *col, 0.0))
    mb.raw(np.array(v, dtype="f4").reshape(-1, STRIDE))
    # arbres, rochers, herbes
    for _ in range(90):
        x, z = rng.uniform(-65, 65), rng.uniform(-80, 8)
        if abs(x) < 6 and z > -8:
            continue
        h = _height(x, z)
        s = rng.uniform(0.8, 1.6)
        mb.add("cylinder", (x, h + 0.9 * s, z), (0.18 * s, 0, 0), (0, 0.9 * s, 0), (0, 0, 0.18 * s), (0.36, 0.25, 0.16))
        g = rng.uniform(-0.05, 0.05)
        mb.add("cone", (x, h + 2.4 * s, z), (1.1 * s, 0, 0), (0, 1.5 * s, 0), (0, 0, 1.1 * s), (0.2 + g, 0.4 + g, 0.2))
        mb.add("cone", (x, h + 3.3 * s, z), (0.8 * s, 0, 0), (0, 1.1 * s, 0), (0, 0, 0.8 * s), (0.24 + g, 0.46 + g, 0.22))
    for _ in range(60):
        x, z = rng.uniform(-60, 60), rng.uniform(-70, 12)
        s = rng.uniform(0.3, 1.1)
        mb.add("sphere", (x, _height(x, z) + s * 0.3, z), (s, 0, 0), (0, s * 0.6, 0), (0, 0, s * 1.2),
               (0.5, 0.49, 0.46))
    for _ in range(700):
        x, z = rng.gauss(0, 9), rng.gauss(-2, 7)
        h = _height(x, z)
        s = rng.uniform(0.08, 0.2)
        g = rng.uniform(-0.06, 0.06)
        mb.add("cone", (x, h + s, z), (0.03, 0, 0), (rng.uniform(-0.04, 0.04), s, 0), (0, 0, 0.03),
               (0.34 + g, 0.62 + g, 0.24))
    # ruines (clin d'œil au plateau du Prélude)
    for i, (x, z, hh) in enumerate(((6, -6, 2.4), (8.5, -7.5, 1.2), (4.5, -9, 1.8), (9, -4.5, 0.8))):
        h = _height(x, z)
        mb.add("cylinder", (x, h + hh / 2, z), (0.45, 0, 0), (0, hh / 2, 0), (0, 0, 0.45), (0.62, 0.6, 0.56))
    mb.box(5.5, _height(6, -7) + 2.4, -8.2, 9.2, _height(6, -7) + 2.8, -6.8, (0.58, 0.56, 0.52))
    # montagnes lointaines
    for i in range(11):
        x = -150 + i * 30 + rng.uniform(-8, 8)
        z = rng.uniform(-175, -150)
        h = rng.uniform(26, 44)
        rx = rng.uniform(28, 40)
        mb.add("cone", (x, h / 2 - 4, z), (rx, 0, 0), (0, h / 2, 0), (0, 0, rx * 0.8), (0.4, 0.44, 0.58))
        mb.add("cone", (x, h - 4 - h * 0.12, z), (rx * 0.24, 0, 0), (0, h * 0.12, 0), (0, 0, rx * 0.2),
               (0.94, 0.95, 0.98))
    # la tour
    tx, tz = TOWER[0] * U, TOWER[1] * U
    base = _height(tx, tz)
    mb.add("cylinder", (tx, base + 9, tz), (2.6, 0, 0), (0, 9, 0), (0, 0, 2.6), (0.3, 0.28, 0.33))
    mb.add("cylinder", (tx, base + 21, tz), (2.0, 0, 0), (0, 3.5, 0), (0, 0, 2.0), (0.27, 0.25, 0.3))
    mb.add("cylinder", (tx, base + 25, tz), (2.4, 0, 0), (0, 0.5, 0), (0, 0, 2.4), (0.24, 0.22, 0.27))
    mb.add("cone", (tx, base + 29, tz), (1.9, 0, 0), (0, 4, 0), (0, 0, 1.9), (0.2, 0.18, 0.22))
    for i in range(4):
        a = i / 4 * math.tau
        mb.add("cylinder", (tx + math.cos(a) * 4.4, base + 5, tz + math.sin(a) * 4.4), (1.0, 0, 0), (0, 5, 0),
               (0, 0, 1.0), (0.28, 0.26, 0.3))
        mb.add("cone", (tx + math.cos(a) * 4.4, base + 11.5, tz + math.sin(a) * 4.4), (1.1, 0, 0), (0, 1.5, 0),
               (0, 0, 1.1), (0.22, 0.2, 0.25))
    return mb.build(), base


class Landscape:
    """Paysage partagé par les écrans de titre et de chargement."""

    _cache = None

    def __init__(self):
        if Landscape._cache is None:
            Landscape._cache = build_landscape()
        self.mesh, self.tower_base = Landscape._cache
        self.cam = Camera3D(yaw=9, pitch=6, dist=19, fov=44)
        self.t = 0.0
        self.hero_z = _height(0, 0) / U
        self.flies = [[random.uniform(-300, 300), random.uniform(-500, 60), random.uniform(20, 160),
                       random.random() * 10] for _ in range(40)]
        self.hero_cls = "chasseur"

    def update(self, dt):
        self.t += dt

    def render(self, fr):
        t = self.t
        cam = self.cam
        cam.yaw = 9 + 2.5 * math.sin(t * 0.07)
        cam.tx, cam.ty, cam.tz = -70, -590, self.hero_z + 4
        models.humanoid(fr, 0, 0, self.hero_z, -math.pi / 2 + 0.15, 0, models.PLAYER_SPECS[self.hero_cls],
                        sc=1.0, moving=False)
        # tourbillon du Tourment autour de la tour
        tx, ty = TOWER
        top = (self.tower_base + 30) / U
        for i in range(36):
            a = t * 0.45 + i * math.tau / 36
            r = (7 + 2.5 * math.sin(t * 0.8 + i * 1.7)) / U
            z = top + math.sin(a * 3 + t) * 90 + (i % 4) * 50
            fr.glow(tx + math.cos(a) * r, ty + math.sin(a) * r, z, 150, (255, 45, 35), 0.45)
        fr.glow(tx, ty, top + 60, 420, (170, 20, 20), 0.35)
        fr.light(tx, ty, top, 1400, (255, 50, 40), 1.2)
        # nuages doux
        rng = random.Random(11)
        for i in range(9):
            x = ((rng.uniform(0, 8000) + t * 45) % 8000) - 4000
            y = rng.uniform(-6200, -4500)
            z = rng.uniform(1300, 2100)
            for j in range(6):
                fr.glow(x + j * 230 - 600, y + rng.uniform(-150, 150), z + rng.uniform(-70, 70),
                        rng.uniform(380, 560), (250, 214, 214), 0.16)
        # lucioles
        for f in self.flies:
            ph = t * 0.8 + f[3]
            x = f[0] + math.sin(ph) * 30
            y = f[1] + math.cos(ph * 0.7) * 30
            fr.glow(x, y, f[2] + math.sin(ph * 1.3) * 10, 7, (255, 230, 150), 0.5 + 0.5 * math.sin(ph * 3))
        env = Env(sky=((0.16, 0.24, 0.48), (0.78, 0.55, 0.58), (1.0, 0.72, 0.5), (0.63, 0.52, 1.0), (1.0, 0.7, 0.45)),
                  clear=(0.9, 0.62, 0.5), sun_dir=(-0.45, -0.42, 0.78), sun_col=(0.95, 0.72, 0.55),
                  amb_sky=(0.48, 0.46, 0.6), amb_ground=(0.24, 0.2, 0.2), shadows=True, shadow_extent=16.0, cut=0.0,
                  fog_col=(0.93, 0.68, 0.58), fog=(30.0, 240.0), player=(0, 0, 0))
        return cam, env


# =========================================================================== écran titre
class TitleScene(Scene):
    def __init__(self, game, skip_intro=False):
        super().__init__(game)
        self.land = Landscape()
        self.static_mesh = self.land.mesh
        self.saves = save.list_saves()
        if self.saves:
            self.land.hero_cls = self.saves[0]["cls"]
        self.phase = "menu" if skip_intro else "press"
        self.t = 0.0
        self.menu_t = 1.0 if skip_intro else 0.0
        self.sel = 0
        self.items = []
        if self.saves:
            last = self.saves[0]
            self.items.append((f"Continuer  ·  {last['name']}", lambda: self.start(last)))
            self.items.append(("Charger une partie", lambda: game.change_scene(LoadScene(game))))
        self.items.append(("Nouvelle partie", lambda: game.change_scene(CreateScene(game))))
        self.items.append(("Quitter", game.quit))

    def start(self, data):
        from .hub import HubScene
        p = Player(data)
        self.game.change_scene(HubScene(self.game, p, f"Bon retour, {p.name}"))

    def item_rects(self):
        return [pygame.Rect(90, 430 + i * 50, 380, 42) for i in range(len(self.items))]

    def handle_event(self, e):
        if self.phase == "press":
            if e.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and self.t > 0.6:
                self.phase = "menu"
                sfx.play("seal", 0.6)
            return
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w, pygame.K_z):
                self.sel = (self.sel - 1) % len(self.items)
                sfx.play("click")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
                sfx.play("click")
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                sfx.play("click")
                self.items[self.sel][1]()
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.item_rects()):
                if r.collidepoint(e.pos) and self.sel != i:
                    self.sel = i
                    sfx.play("click", 0.4)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.item_rects()):
                if r.collidepoint(e.pos):
                    sfx.play("click")
                    self.items[i][1]()

    def update(self, dt):
        self.t += dt
        self.land.update(dt)
        if self.phase == "menu":
            self.menu_t = min(1.0, self.menu_t + dt * 2.5)

    def render3d(self, fr):
        return self.land.render(fr)

    def draw_logo(self, surf, cx, cy, a):
        ui.draw_text(surf, "LA LÉGENDE DE LA", (cx, cy - 58), 17, (240, 236, 226), "title", anchor="center",
                     alpha=a)
        ui.draw_text(surf, "TOUR DES TOURMENTS", (cx, cy), 58, WHITE, "title", anchor="center", alpha=a)
        w = 300
        ui.line(surf, (236, 206, 140), (cx - w, cy + 40), (cx - 40, cy + 40), 1)
        ui.line(surf, (236, 206, 140), (cx + 40, cy + 40), (cx + w, cy + 40), 1)
        ui.draw_text(surf, "L'Ascension", (cx, cy + 40), 26, (240, 210, 140), "title", anchor="center", alpha=a)

    def draw_ui(self, surf):
        # bas d'écran assombri pour la lisibilité
        grad = pygame.Surface((1, 64), pygame.SRCALPHA)
        for i in range(64):
            grad.set_at((0, i), (0, 0, 0, int(170 * (i / 63) ** 1.6)))
        g = pygame.transform.smoothscale(grad, (surf.get_width(), surf.get_height() // 2))
        surf.blit(g, (0, surf.get_height() // 2))
        a = int(255 * min(1.0, self.t / 1.5))
        if self.phase == "press":
            self.draw_logo(surf, SCREEN_W / 2, 250, a)
            k = 0.5 + 0.5 * math.sin(self.t * 3)
            if self.t > 1.2:
                ui.draw_text(surf, "Appuyez sur une touche", (SCREEN_W / 2, 600), 20, WHITE, anchor="center",
                             alpha=int(90 + 165 * k))
        else:
            k = self.menu_t
            e = 1 - (1 - k) ** 3
            cx = SCREEN_W / 2 + (420 - SCREEN_W / 2) * e
            cy = 250 - 70 * e
            self.draw_logo(surf, cx, cy, 255)
            for i, ((label, _), r) in enumerate(zip(self.items, self.item_rects())):
                sel = i == self.sel
                x = r.x + (1 - e) * -60
                alpha = int(255 * e)
                if sel:
                    ui.rect(surf, (0, 0, 0, int(110 * e)), (x - 10, r.y, r.w, r.h), 0, 21)
                    ui.line(surf, SHEIKAH, (x - 10, r.bottom - 2), (x + r.w - 60, r.bottom - 2), 2)
                    ui.polygon(surf, SHEIKAH, [(x + 4, r.centery - 7), (x + 4, r.centery + 7), (x + 14, r.centery)])
                ui.draw_text(surf, label, (x + 26, r.centery), 22 if sel else 20, WHITE if sel else SOFT, "title",
                             anchor="midleft", alpha=alpha)
            ui.draw_text(surf, "Flèches ou souris : choisir    Entrée ou clic : valider", (SCREEN_W - 26, SCREEN_H - 14), 13,
                         SOFT, anchor="bottomright", alpha=int(200 * e))
        ui.draw_text(surf, "v2.0 · 3D", (26, SCREEN_H - 14), 12, SOFT, anchor="bottomleft", alpha=160)


# =========================================================================== chargement
class LoadScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.land = Landscape()
        self.static_mesh = self.land.mesh
        self.confirm = None
        self.t = 0.0
        self.refresh()

    def refresh(self):
        self.saves = save.list_saves()[:6]
        cx = SCREEN_W // 2
        self.rows = []
        for i, d in enumerate(self.saves):
            r = pygame.Rect(cx - 380, 150 + i * 78, 680, 68)
            self.rows.append((r, d, ui.Button((r.right + 12, r.y + 14, 96, 40), "Suppr.", lambda d=d: self.delete(d), 15)))
        self.back = ui.Button((cx - 110, SCREEN_H - 84, 220, 44), "Retour",
                              lambda: self.game.change_scene(TitleScene(self.game, skip_intro=True)))

    def delete(self, d):
        if self.confirm is d:
            save.delete(d["name"])
            self.confirm = None
            self.refresh()
        else:
            self.confirm = d

    def handle_event(self, e):
        if self.back.handle(e):
            return
        for r, d, b in self.rows:
            if b.handle(e):
                return
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and r.collidepoint(e.pos):
                from .hub import HubScene
                sfx.play("click")
                p = Player(d)
                self.game.change_scene(HubScene(self.game, p, f"Bon retour, {p.name}"))
                return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.change_scene(TitleScene(self.game, skip_intro=True))

    def update(self, dt):
        self.t += dt
        self.land.update(dt)

    def render3d(self, fr):
        return self.land.render(fr)

    def draw_ui(self, surf):
        ui.veil(surf, (6, 12, 16), 170)
        ui.draw_text(surf, "Charger une partie", (SCREEN_W / 2, 84), 34, WHITE, "title", anchor="center")
        ui.line(surf, (120, 124, 120), (SCREEN_W / 2 - 240, 112), (SCREEN_W / 2 + 240, 112))
        mouse = ui.mouse_pos()
        for r, d, b in self.rows:
            hov = r.collidepoint(mouse)
            ui.botw_box(surf, r, 200 if hov else 140, SHEIKAH if hov else (110, 112, 110), radius=12,
                        fill=(12, 34, 44) if hov else (0, 0, 0))
            c = CLASSES[d["cls"]]
            ui.circle(surf, ui.darker(c["color"], 0.5), (r.x + 36, r.centery), 22)
            ui.circle(surf, c["color"], (r.x + 36, r.centery), 22, 2)
            ui.draw_text(surf, c["name"][0], (r.x + 36, r.centery), 20, WHITE, "title_bold", anchor="center")
            ui.draw_text(surf, d["name"], (r.x + 74, r.y + 9), 21, WHITE, "title")
            ui.draw_text(surf, f"{c['name']} · niveau {d.get('level', 1)} · étage max {d.get('max_floor', 1)} · "
                               f"{d.get('gold', 0)} or", (r.x + 74, r.y + 40), 14, SOFT)
            when = d.get("saved_at")
            if when:
                ui.draw_text(surf, datetime.datetime.fromtimestamp(when).strftime("%d/%m/%Y  %H:%M"),
                             (r.right - 16, r.y + 12), 13, TEXT_DIM, anchor="topright")
            if hov:
                ui.selection_frame(surf, r, self.t, SHEIKAH)
            b.text = "Sûr ?" if self.confirm is d else "Suppr."
            b.draw(surf)
        if not self.rows:
            ui.draw_text(surf, "Aucune sauvegarde.", (SCREEN_W / 2, 320), 18, SOFT, anchor="center")
        self.back.draw(surf)


# =========================================================================== création de personnage
class CreateScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.static_mesh = None
        self.name = random.choice(NAMES)
        self.cls = "barbare"
        self.t = 0.0
        self.error = ""
        self.cam = Camera3D(yaw=45, pitch=10, dist=5.6, fov=32)
        self.class_rects = {cid: pygame.Rect(640 + i * 206, 190, 196, 64) for i, cid in enumerate(CLASSES)}
        self.name_rect = pygame.Rect(640, 110, 402, 44)
        self.go = ui.Button((SCREEN_W - 340, SCREEN_H - 84, 300, 50), "Entrer dans la Tour", self.create, 20)
        self.back = ui.Button((640, SCREEN_H - 84, 200, 50), "Retour",
                              lambda: game.change_scene(TitleScene(game, skip_intro=True)), 18)

    def create(self):
        name = self.name.strip()
        if len(name) < 2:
            self.error = "Le nom doit contenir au moins 2 caractères."
            return
        if save.exists(name):
            self.error = "Un personnage porte déjà ce nom."
            return
        data = save.new_character(name, self.cls)
        save.save_data(data)
        from .hub import HubScene
        p = Player(data)
        self.game.change_scene(HubScene(self.game, p, f"Bienvenue, {p.name}. La Tour vous attend."))

    def handle_event(self, e):
        if self.go.handle(e) or self.back.handle(e):
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for cid, r in self.class_rects.items():
                if r.collidepoint(e.pos):
                    self.cls = cid
                    sfx.play("click")
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.create()
            elif e.key == pygame.K_ESCAPE:
                self.game.change_scene(TitleScene(self.game, skip_intro=True))
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                ids = list(CLASSES)
                i = (ids.index(self.cls) + (1 if e.key == pygame.K_RIGHT else -1)) % len(ids)
                self.cls = ids[i]
                sfx.play("click")
        elif e.type == pygame.TEXTINPUT:
            if len(self.name) < 16 and all(ch.isalnum() or ch in " -'" for ch in e.text):
                self.name += e.text
                self.error = ""

    def update(self, dt):
        self.t += dt

    def render3d(self, fr):
        t = self.t
        PX, PY = 0.0, 0.0
        c = CLASSES[self.cls]["color"]
        models.humanoid(fr, PX, PY, 0, 0.9 + t * 0.6, t * 5 if int(t / 4) % 2 else 0,
                        models.PLAYER_SPECS[self.cls], moving=bool(int(t / 4) % 2), swing=0)
        fr.box(PX, PY, -6, 40, 40, 6, (34, 52, 60), mesh="cylinder")
        fr.decal(PX, PY, 46, 46, c, 0.6, kind=1, inner=0.9, lift=0.16)
        for i in range(10):
            a = t * 0.8 + i * math.tau / 10
            fr.glow(PX + math.cos(a) * 44, PY + math.sin(a) * 44, 8 + 6 * math.sin(t * 2 + i), 10, c, 0.8)
        fr.light(PX + 100, PY + 120, 110, 520, (255, 236, 214), 1.4)
        fr.light(PX - 90, PY - 70, 60, 320, c, 1.3)
        cam = self.cam
        cam.tx, cam.ty, cam.tz = PX, PY, 26
        cam.ndc_shift = (300 / SCREEN_W * 2 - 1, 1 - 400 / SCREEN_H * 2)
        env = Env(clear=(0.03, 0.055, 0.07), shadow_extent=3.0, cut=0.0, fog=(30.0, 40.0),
                  amb_sky=(0.42, 0.45, 0.52), amb_ground=(0.14, 0.15, 0.17), sun_col=(0.55, 0.55, 0.6),
                  sun_dir=(-0.35, -1.0, -0.55), fog_col=(0.03, 0.055, 0.07), player=(PX, PY, 0))
        return cam, env

    def draw_ui(self, surf):
        ui.draw_text(surf, "Nouveau héros", (60, 50), 36, WHITE, "title")
        ui.line(surf, (120, 124, 120), (60, 92), (520, 92))
        c = CLASSES[self.cls]
        ui.draw_text(surf, c["name"], (300, 610), 30, WHITE, "title", anchor="center")
        ui.draw_text(surf, c["title"], (300, 646), 16, SOFT, anchor="center")
        # nom
        ui.draw_text(surf, "Nom", (640, 84), 15, SOFT, "bold")
        r = self.name_rect
        ui.botw_box(surf, r, 190, SHEIKAH, radius=22, fill=(8, 24, 30))
        cursor = "|" if int(self.t * 2) % 2 else " "
        ui.draw_text(surf, self.name + cursor, (r.x + 22, r.centery), 22, WHITE, "title", anchor="midleft")
        # classes
        ui.draw_text(surf, "Classe", (640, 164), 15, SOFT, "bold")
        mouse = ui.mouse_pos()
        for cid, rc in self.class_rects.items():
            cc = CLASSES[cid]
            sel = cid == self.cls
            hov = rc.collidepoint(mouse)
            ui.botw_box(surf, rc, 200 if sel else 130, cc["color"] if sel else (SHEIKAH if hov else (100, 102, 100)),
                        radius=14, fill=(14, 30, 36) if sel else (0, 0, 0))
            ui.circle(surf, ui.darker(cc["color"], 0.5), (rc.x + 30, rc.centery), 18)
            ui.circle(surf, cc["color"], (rc.x + 30, rc.centery), 18, 2)
            ui.draw_text(surf, cc["name"][0], (rc.x + 30, rc.centery), 18, WHITE, "title_bold", anchor="center")
            ui.draw_text(surf, cc["name"], (rc.x + 58, rc.centery), 18, WHITE if sel else SOFT, "title", anchor="midleft")
            if sel:
                ui.selection_frame(surf, rc, self.t, cc["color"])
        # description, caractéristiques, sorts
        box = ui.botw_box(surf, (640, 276, 602, 340), 150, (100, 102, 100), radius=14)
        y = ui.draw_wrapped(surf, c["desc"], box.x + 22, box.y + 16, box.w - 44, 16, SOFT)
        y += 10
        for i, a in enumerate(ATTRS):
            v = c["attrs"][a]
            yy = y + i * 24
            ui.draw_text(surf, ATTR_NAMES[a], (box.x + 22, yy), 14, WHITE if a != c["primary"] else GOLD_BRIGHT, "bold")
            bar = pygame.Rect(box.x + 140, yy + 6, 160, 7)
            ui.rect(surf, (0, 0, 0, 180), bar.inflate(2, 2), 0, 4)
            ui.rect(surf, c["color"], (bar.x, bar.y, bar.w * v / 24, bar.h), 0, 4)
        ui.draw_text(surf, "Sorts", (box.x + 330, y - 2), 15, WHITE, "bold")
        for i, sid in enumerate(c["spells"]):
            sp = SPELLS[sid]
            yy = y + 22 + i * 24
            ui.circle(surf, sp["color"], (box.x + 338, yy + 9), 5)
            ui.draw_text(surf, f"{sp['name']}", (box.x + 350, yy), 14, SOFT)
            ui.draw_text(surf, f"niv {sp['level']}", (box.right - 20, yy), 13, TEXT_DIM, anchor="topright")
        ui.draw_text(surf, "Tous les héros disposent aussi de la roulade (Espace), d'une potion à recharge (F)",
                     (box.x + 22, box.bottom - 46), 13, SOFT)
        ui.draw_text(surf, "et de 3 emplacements d'artefacts (R, T, G).", (box.x + 22, box.bottom - 26), 13, SOFT)
        if self.error:
            ui.draw_text(surf, self.error, (SCREEN_W - 40, SCREEN_H - 100), 15, RED, "bold", anchor="bottomright")
        self.go.draw(surf)
        self.back.draw(surf)
