"""Écrans hors-jeu façon Zelda Breath of the Wild : titre (paysage 3D), chargement, création de personnage."""
import datetime
import math
import os
import random

import pygame

from . import looks, save, sfx, ui
from .data import CLASSES, SPELLS, ATTR_NAMES, ATTRS
from .entities import Player
from .r3d import models
from .r3d.camera import Camera3D
from .r3d.renderer import Env
from .settings import SCREEN_W, SCREEN_H, WHITE, SHEIKAH, UI_LINE, TEXT_DIM, RED, GOLD_BRIGHT, TITLE, ASSETS_DIR, VIEW
from .wardrobe import LookEditor
from .world import Scene

SOFT = (214, 218, 218)
NAMES = ["Aldric", "Morwen", "Kaelen", "Sybille", "Thorgar", "Ysolde", "Varian", "Lyra", "Elowen", "Brann"]


# =========================================================================== illustration du menu
BG_FILE = "background menu.png"
LOGO_FILE = "logo.png"
_art_cache = {}


def _art(name):
    img = _art_cache.get(name)
    if img is None:
        img = pygame.image.load(os.path.join(ASSETS_DIR, name))
        if name == LOGO_FILE:   # marges transparentes retirées
            img = img.subsurface(img.get_bounding_rect()).copy()
        _art_cache[name] = img
    return img


def draw_background(surf, t):
    """Illustration plein écran (recadrée comme un fond « cover »), qui dérive très lentement."""
    W, H = surf.get_size()
    key = ("bg", W, H)
    big = _art_cache.get(key)
    if big is None:
        img = _art(BG_FILE)
        k = max(W / img.get_width(), H / img.get_height()) * 1.06
        big = pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))
        for old in [k_ for k_ in _art_cache if isinstance(k_, tuple) and k_[0] == "bg"]:
            del _art_cache[old]
        _art_cache[key] = big
    ex, ey = big.get_width() - W, big.get_height() - H
    ox = ex * (0.5 + 0.5 * math.sin(t * 0.04))
    oy = ey * (0.2 + 0.08 * math.sin(t * 0.03))    # on garde surtout le haut : le vortex et la tour
    surf.blit(big, (0, 0), pygame.Rect(int(ox), int(oy), W, H))


def draw_embers(surf, t, n=44):
    """Braises qui montent devant l'illustration."""
    for i in range(n):
        ph = i * 1.618
        speed = 16 + (i * 37) % 26
        y = SCREEN_H + 20 - ((t * speed + i * 97) % (SCREEN_H + 60))
        x = (i * 211) % SCREEN_W + 26 * math.sin(t * 0.6 + ph)
        k = 0.35 + 0.65 * abs(math.sin(t * 1.7 + ph))
        col = (255, int(110 + 70 * k), 50)
        if i % 4 == 0:
            ui.glow(surf, x, y, 7 + 3 * k, ui.darker(col, 0.5 * k))
        ui.circle(surf, (*col, int(230 * k)), (x, y), 1.1 + (i % 3) * 0.5)


def draw_logo(surf, cx, cy, a=255, width=620):
    key = ("logo", width, VIEW.version)
    img = _art_cache.get(key)
    if img is None:
        src = _art(LOGO_FILE)
        w = round(width * VIEW.s)
        img = pygame.transform.smoothscale(src, (w, round(w * src.get_height() / src.get_width())))
        _art_cache[key] = img
    if a < 255:
        img = img.copy()
        img.set_alpha(a)
    ui.blit(surf, img, (cx, cy), anchor="center")


# =========================================================================== écran titre
class TitleScene(Scene):
    def __init__(self, game, skip_intro=False):
        super().__init__(game)
        self.static_mesh = None
        self.saves = save.list_saves()
        self.phase = "menu" if skip_intro else "press"
        self.t = 0.0
        self.menu_t = 1.0 if skip_intro else 0.0
        self.sel = 0
        self.items = []
        if self.saves:
            last = self.saves[0]
            self.items.append(("Continuer", lambda: self.start(last)))
        self.items.append(("Nouvelle partie", lambda: game.change_scene(CreateScene(game))))
        if self.saves:
            self.items.append(("Charger une partie", lambda: game.change_scene(LoadScene(game))))
        self.items.append(("Plein écran", game.toggle_fullscreen))
        self.items.append(("Quitter", game.quit))

    def start(self, data):
        from .hub import HubScene
        p = Player(data)
        self.game.change_scene(HubScene(self.game, p, f"Bon retour, {p.name}"))

    def item_rects(self):
        return [pygame.Rect(SCREEN_W // 2 - 150, 392 + i * 54, 300, 44) for i in range(len(self.items))]

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
        if self.phase == "menu":
            self.menu_t = min(1.0, self.menu_t + dt * 2.5)

    def draw_ui(self, surf):
        draw_background(surf, self.t)
        draw_embers(surf, self.t)
        # dégradé plein écran : léger en haut, plus sombre en bas pour la lisibilité du menu
        grad = pygame.Surface((1, 90), pygame.SRCALPHA)
        for i in range(90):
            k = i / 89
            alpha = 110 * max(0.0, 1 - k / 0.3) ** 2 + 200 * max(0.0, (k - 0.4) / 0.6) ** 1.5
            grad.set_at((0, i), (int(6 * alpha / 255), int(10 * alpha / 255), int(18 * alpha / 255), int(alpha)))
            # (couleur prémultipliée : l'interface est composée en alpha prémultiplié)
        surf.blit(pygame.transform.smoothscale(grad, surf.get_size()), (0, 0))
        a = int(255 * min(1.0, self.t / 1.5))
        if self.phase == "press":
            draw_logo(surf, SCREEN_W / 2, 250, a, 700)
            k = 0.5 + 0.5 * math.sin(self.t * 3)
            if self.t > 1.2:
                smallcaps(surf, "Appuyez sur une touche", (SCREEN_W / 2, 600), 20, WHITE, int(90 + 165 * k))
        else:
            e = 1 - (1 - self.menu_t) ** 3
            draw_logo(surf, SCREEN_W / 2, 250 - 82 * e, 255, 700 - 80 * e)
            for i, ((label, _), r) in enumerate(zip(self.items, self.item_rects())):
                sel = i == self.sel
                y = r.centery + (1 - e) * 30
                alpha = int(255 * e)
                if sel:
                    cartouche(surf, pygame.Rect(r.x, y - r.h / 2, r.w, r.h), self.t, alpha)
                smallcaps(surf, label, (SCREEN_W / 2, y), 21 if sel else 19, WHITE if sel else (226, 222, 204), alpha)
            if self.saves and self.items[self.sel][0] == "Continuer":
                d = self.saves[0]
                info = (f"{d['name']}  ·  {CLASSES[d['cls']]['name']} niveau {d.get('level', 1)}  ·  "
                        f"étage {d.get('max_floor', 1)}")
                ui.draw_text(surf, info, (SCREEN_W / 2, SCREEN_H - 34), 14, (214, 208, 190), anchor="center",
                             alpha=int(220 * e))
        for i, line in enumerate(("Ver. 2.0", TITLE, "© 2026 Saku Game")):
            ui.draw_text(surf, line, (SCREEN_W - 30, SCREEN_H - 70 + i * 19), 13, (226, 222, 204), anchor="topright",
                         alpha=190)


def smallcaps(surf, text, center, size, color, alpha=255):
    """Texte en petites capitales centré (initiales plus grandes), comme les menus de BotW."""
    pieces = []
    for wi, word in enumerate(text.split(" ")):
        if wi:
            pieces.append((" ", size * 0.8))
        pieces.append((word[0].upper(), size))
        if len(word) > 1:
            pieces.append((word[1:].upper(), size * 0.78))
    widths = [ui.text_size(t, sz, "title")[0] for t, sz in pieces]
    x = center[0] - sum(widths) / 2
    base = center[1] + size * 0.36
    for (t, sz), w in zip(pieces, widths):
        ui.draw_text(surf, t, (x, base), sz, color, "title", anchor="bottomleft", alpha=alpha)
        x += w


def cartouche(surf, r, t, alpha=255):
    """Cartouche du choix actif : pointes latérales, liseré doré, losanges et chevrons aux extrémités."""
    gold = (214, 190, 132)
    cy = r.centery
    pts = [(r.x, cy), (r.x + 18, r.y), (r.right - 18, r.y), (r.right, cy), (r.right - 18, r.bottom),
           (r.x + 18, r.bottom)]
    ui.polygon(surf, (26, 22, 20, int(215 * alpha / 255)), pts)
    ui.polygon(surf, (*gold, alpha), pts, 2)
    inner = [(r.x + 7, cy), (r.x + 21, r.y + 4), (r.right - 21, r.y + 4), (r.right - 7, cy),
             (r.right - 21, r.bottom - 4), (r.x + 21, r.bottom - 4)]
    ui.polygon(surf, (*ui.darker(gold, 0.6), int(alpha * 0.8)), inner, 1)
    k = 2 * math.sin(t * 4)
    for d in (-1, 1):
        x = r.centerx + d * (r.w / 2 - 34) + d * k
        ui.polygon(surf, (*gold, alpha), [(x, cy - 7), (x + 7, cy), (x, cy + 7), (x - 7, cy)])
        ui.polygon(surf, (26, 22, 20, alpha), [(x, cy - 3), (x + 3, cy), (x, cy + 3), (x - 3, cy)])
        ui.polygon(surf, (*gold, alpha), [(x - d * 11, cy - 5), (x - d * 17, cy), (x - d * 11, cy + 5)])


# =========================================================================== chargement
class LoadScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.static_mesh = None
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

    def draw_ui(self, surf):
        draw_background(surf, self.t)
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
        self.class_rects = {cid: pygame.Rect(640 + (i % 3) * 206, 186 + (i // 3) * 62, 196, 54)
                            for i, cid in enumerate(CLASSES)}
        self.name_rect = pygame.Rect(640, 110, 402, 44)
        # étape 0 : nom et classe ; étape 1 : apparence
        self.step = 0
        self.look = looks.default_look(self.cls)
        self.look_edited = False
        self.editor = None
        self.rot = 0.0
        self.drag = None
        self.go = ui.Button((SCREEN_W - 340, SCREEN_H - 84, 300, 50), "Suivant : apparence", self.forward, 20)
        self.back = ui.Button((640, SCREEN_H - 84, 200, 50), "Retour", self.backward, 18)
        self.rand = ui.Button((640, 540, 200, 42), "Aléatoire", self.randomize, 17)

    def name_ok(self):
        name = self.name.strip()
        if len(name) < 2:
            self.error = "Le nom doit contenir au moins 2 caractères."
        elif save.exists(name):
            self.error = "Un personnage porte déjà ce nom."
        else:
            return True
        return False

    def set_class(self, cid):
        self.cls = cid
        if not self.look_edited:
            self.look = looks.default_look(cid)
        sfx.play("click")

    def forward(self):
        if self.step == 1:
            self.create()
        elif self.name_ok():
            self.step = 1
            self.error = ""
            self.editor = LookEditor((640, 104, 600, 0), self.look, self.cls)
            self.go.text = "Entrer dans la Tour"

    def backward(self):
        if self.step == 1:
            self.step = 0
            self.go.text = "Suivant : apparence"
        else:
            self.game.change_scene(TitleScene(self.game, skip_intro=True))

    def randomize(self):
        if self.editor:
            self.editor.randomize()
            self.look_edited = True

    def create(self):
        if not self.name_ok():
            self.step = 0
            self.go.text = "Suivant : apparence"
            return
        name = self.name.strip()
        data = save.new_character(name, self.cls)
        data["look"] = dict(self.look)
        save.save_data(data)
        from .hub import HubScene
        p = Player(data)
        self.game.change_scene(HubScene(self.game, p, f"Bienvenue, {p.name}. La Tour vous attend."))

    def handle_event(self, e):
        if self.go.handle(e) or self.back.handle(e):
            return
        if self.step == 1:
            self.handle_look(e)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for cid, r in self.class_rects.items():
                if r.collidepoint(e.pos):
                    self.set_class(cid)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.forward()
            elif e.key == pygame.K_ESCAPE:
                self.backward()
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                ids = list(CLASSES)
                self.set_class(ids[(ids.index(self.cls) + (1 if e.key == pygame.K_RIGHT else -1)) % len(ids)])
        elif e.type == pygame.TEXTINPUT:
            if len(self.name) < 16 and all(ch.isalnum() or ch in " -'" for ch in e.text):
                self.name += e.text
                self.error = ""

    def handle_look(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.backward()
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.create()
        elif self.rand.handle(e):
            pass
        elif self.editor.handle_event(e):
            self.look_edited = True
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and e.pos[0] < 600:
            self.drag = e.pos[0]
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag = None
        elif e.type == pygame.MOUSEMOTION and self.drag is not None:
            self.rot += (e.pos[0] - self.drag) * 0.012
            self.drag = e.pos[0]

    def update(self, dt):
        self.t += dt

    def render3d(self, fr):
        t = self.t
        PX, PY = 0.0, 0.0
        c = CLASSES[self.cls]["color"]
        spec = looks.hero_spec(self.cls, self.look)
        if self.step == 1:
            models.humanoid(fr, PX, PY, 0, 0.9 + self.rot, 0, spec, moving=False)
        else:
            models.humanoid(fr, PX, PY, 0, 0.9 + t * 0.6, t * 5 if int(t / 4) % 2 else 0, spec,
                            moving=bool(int(t / 4) % 2), swing=0)
        fr.box(PX, PY, -6, 40, 40, 6, (34, 52, 60), mesh="cylinder")
        fr.decal(PX, PY, 46, 46, c, 0.6, kind=1, inner=0.9, lift=0.16)
        for i in range(10):
            a = t * 0.8 + i * math.tau / 10
            fr.glow(PX + math.cos(a) * 44, PY + math.sin(a) * 44, 8 + 6 * math.sin(t * 2 + i), 10, c, 0.8)
        fr.light(PX + 100, PY + 120, 110, 520, (255, 236, 214), 1.4)
        fr.light(PX - 90, PY - 70, 60, 320, c, 1.3)
        cam = self.cam
        cam.dist = 4.2 if self.step == 1 else 5.6
        cam.tx, cam.ty, cam.tz = PX, PY, 26
        cam.ndc_shift = (300 / SCREEN_W * 2 - 1, 1 - 380 / SCREEN_H * 2)
        env = Env(clear=(0.03, 0.055, 0.07), shadow_extent=3.0, cut=0.0, fog=(30.0, 40.0),
                  amb_sky=(0.42, 0.45, 0.52), amb_ground=(0.14, 0.15, 0.17), sun_col=(0.55, 0.55, 0.6),
                  sun_dir=(-0.35, -1.0, -0.55), fog_col=(0.03, 0.055, 0.07), player=(PX, PY, 0))
        return cam, env

    def draw_ui(self, surf):
        ui.draw_text(surf, "Nouveau héros" if self.step == 0 else "Apparence", (60, 50), 36, WHITE, "title")
        ui.line(surf, (120, 124, 120), (60, 92), (520, 92))
        c = CLASSES[self.cls]
        ui.draw_text(surf, c["name"] if self.step == 0 else self.name.strip(), (300, 610), 30, WHITE, "title",
                     anchor="center")
        ui.draw_text(surf, c["title"] if self.step == 0 else f"{c['name']} · glisser pour pivoter", (300, 646), 16,
                     SOFT, anchor="center")
        if self.step == 1:
            self.editor.draw(surf, self.t)
            self.rand.draw(surf)
            self.go.draw(surf)
            self.back.draw(surf)
            return
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
            ui.draw_text(surf, cc["name"], (rc.x + 58, rc.centery), 17 if len(cc["name"]) > 10 else 18,
                         WHITE if sel else SOFT, "title", anchor="midleft")
            if sel:
                ui.selection_frame(surf, rc, self.t, cc["color"])
        # description, caractéristiques, sorts
        box = ui.botw_box(surf, (640, 318, 602, 300), 150, (100, 102, 100), radius=14)
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
