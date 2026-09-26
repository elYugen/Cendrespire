"""Menus en jeu, style Zelda BotW : menu plein écran (inventaire avec héros en 3D, personnage, système),
enchantements, marchand, forge, portail, pouvoirs d'anima et mort.
Le menu principal (Personnage · Inventaire · Système) remplace aussi l'ancien menu pause.
Coordonnées « de conception » (1280x720), dessin via ui (net en Retina)."""
import math

import pygame

from . import sfx, ui
from .data import (ATTRS, ATTR_NAMES, ATTR_DESC, SPELLS, ANIMA_POWERS, ANIMA_TIERS, BAG_SIZE, ARTIFACTS, ENCHANTS,
                   CLASSES, xp_needed, floor_name, floor_boss, BOSSES, anima_desc, ench_value)
from .items import (SLOT_NAMES, AFFIX_DEF, ART_SLOTS, buy_price, upgrade_cost, MAX_UPGRADE, item_lines, item_stats,
                    item_value, art_desc)
from .settings import (SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, GOLD, GOLD_BRIGHT, RED, RARITY_COLORS, RARITY_NAMES,
                       WHITE, SHEIKAH, UI_LINE)
from .ui import BOTW_YELLOW

SOFT = (206, 212, 212)
UP = (110, 235, 120)
DOWN = (240, 90, 80)
ENCH_COL = (200, 150, 255)


def item_slot(surf, rect, item, t, selected=False, hovered=False, usable=True, label=None):
    rect = pygame.Rect(rect)
    border = SHEIKAH if hovered else ((150, 150, 146) if item else (80, 82, 80))
    ui.botw_box(surf, rect, 190 if hovered else 150, border, radius=8, fill=(10, 30, 40) if hovered else (0, 0, 0))
    if item:
        col = RARITY_COLORS[item["rarity"]]
        if item["rarity"] != "commun":
            ui.rect(surf, (*col, 38), rect.inflate(-4, -4), 0, 7)
            ui.line(surf, col, (rect.x + 8, rect.bottom - 3), (rect.right - 9, rect.bottom - 3), 2)
        ui.draw_item_icon(surf, item, rect.inflate(-rect.w * 0.22, -rect.h * 0.22), bg=False)
        if item.get("ench") and any(e["id"] for e in item["ench"]):
            ui.circle(surf, ENCH_COL, (rect.right - 7, rect.y + 7), 3)
        if not usable:
            ui.line(surf, DOWN, (rect.x + 6, rect.bottom - 6), (rect.right - 6, rect.y + 6), 2)
    elif label:
        ui.draw_text(surf, label, rect.center, 11, (120, 124, 122), anchor="center", shadow=False)
    if selected:
        ui.selection_frame(surf, rect, t)


def attack_icon(surf, x, y):
    ui.line(surf, WHITE, (x - 8, y + 8), (x + 8, y - 8), 3)
    ui.line(surf, WHITE, (x - 8, y - 2), (x - 2, y + 8), 2)


def shield_icon(surf, x, y):
    ui.polygon(surf, WHITE, [(x - 8, y - 9), (x + 8, y - 9), (x + 8, y + 1), (x, y + 10), (x - 8, y + 1)], 2)


def heart_icon(surf, x, y):
    from .hud import draw_heart
    draw_heart(surf, x - 9, y - 9, 1, 18)


class Panel:
    modal = False

    def __init__(self, world, rect):
        self.world = world
        self.rect = pygame.Rect(rect)

    def handle_event(self, e):
        return False

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def draw_tooltips(self, surf):
        pass

    def contains(self, pos):
        return self.rect.collidepoint(pos)


# =========================================================================== menu plein écran
PAGE_CHAR, PAGE_INV, PAGE_SYS = 0, 1, 2
PAGES = ["Personnage", "Inventaire", "Système"]
CATEGORIES = [("Armes", {"arme"}, "sword"), ("Armures", {"casque", "torse", "gants", "bottes"}, "armor"),
              ("Bijoux", {"amulette", "anneau"}, "ring"), ("Artefacts", {"artefact"}, "star")]
GRID_COLS, GRID_ROWS, CELL, STEP = 5, 4, 84, 98
GRID_X, GRID_Y = 122, 221
PER_PAGE = GRID_COLS * GRID_ROWS
DESC = pygame.Rect(672, 430, 592, 212)
HERO_ZONE = pygame.Rect(860, 110, 420, 318)
CURSOR_KEYS = {26: (0, -1), 4: (-1, 0), 22: (0, 1), 7: (1, 0)}   # ZQSD / WASD physiques
ART_KEYS_SC = (21, 23, 10)                                       # R, T, G
FRAME = (150, 152, 146)


def cat_icon(surf, kind, c, col, k=1.0):
    """Pictogrammes des catégories de l'inventaire (épée, armure, bague, étoile)."""
    x, y = c
    s = 12 * k
    if kind == "sword":
        ui.line(surf, col, (x - s * 0.55, y + s * 0.55), (x + s * 0.95, y - s * 0.95), 4)
        ui.line(surf, col, (x - s * 0.85, y + s * 0.05), (x - s * 0.05, y + s * 0.85), 3)
        ui.line(surf, col, (x - s * 1.05, y + s * 1.05), (x - s * 0.5, y + s * 0.5), 4)
    elif kind == "armor":
        ui.polygon(surf, col, [(x - s * 0.4, y - s), (x - s * 1.05, y - s * 0.55), (x - s * 0.75, y),
                               (x - s * 0.5, y - s * 0.2), (x - s * 0.5, y + s), (x + s * 0.5, y + s),
                               (x + s * 0.5, y - s * 0.2), (x + s * 0.75, y), (x + s * 1.05, y - s * 0.55),
                               (x + s * 0.4, y - s), (x, y - s * 0.65)])
    elif kind == "ring":
        ui.circle(surf, col, (x, y + s * 0.3), s * 0.7, 3)
        ui.polygon(surf, col, [(x, y - s * 1.05), (x + s * 0.42, y - s * 0.62), (x, y - s * 0.2),
                               (x - s * 0.42, y - s * 0.62)])
    else:
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            r = s * (1.05 if i % 2 == 0 else 0.45)
            pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
        ui.polygon(surf, col, pts)


def coin_icon(surf, x, y, r=9):
    ui.circle(surf, (150, 104, 30), (x, y), r)
    ui.circle(surf, GOLD_BRIGHT, (x, y), r - 2)
    ui.circle(surf, (205, 150, 50), (x, y), r - 5, 1)


def small_attack(surf, x, y):
    ui.line(surf, WHITE, (x - 6, y + 6), (x + 6, y - 6), 2)
    ui.line(surf, WHITE, (x - 6, y - 1), (x - 1, y + 6), 2)


def small_shield(surf, x, y):
    ui.polygon(surf, WHITE, [(x - 6, y - 7), (x + 6, y - 7), (x + 6, y + 1), (x, y + 7), (x - 6, y + 1)], 2)


def small_clock(surf, x, y):
    ui.circle(surf, SHEIKAH, (x, y), 7, 2)
    ui.line(surf, SHEIKAH, (x, y), (x, y - 4), 2)
    ui.line(surf, SHEIKAH, (x, y), (x + 3, y + 1), 2)


def chip(surf, x, y, text, col, icon=None, border=None):
    """Petite étiquette encadrée (comme les pastilles d'effet sous le nom d'un objet dans BotW)."""
    tw, _ = ui.text_size(text, 13, "bold")
    r = pygame.Rect(x, y, tw + 16 + (22 if icon else 0), 24)
    ui.botw_box(surf, r, 170, border or ui.darker(col, 0.75), radius=4)
    if icon:
        icon(surf, x + 14, y + 12)
    ui.draw_text(surf, text, (x + (30 if icon else 8), y + 12), 13, col, "bold", anchor="midleft", shadow=False)
    return r.right + 8


def badge_left(surf, key, x, y, size=12, color=WHITE):
    """Pastille de touche dont le bord gauche est en x."""
    w, h = ui.text_size(key, size, "bold")
    return ui.key_badge(surf, key, (x + max(h + 2, w + 10) / 2, y), size, color)


class MenuScreen(Panel):
    """Menu façon Zelda BotW (jeu en pause), trois pages : Personnage · Inventaire · Système.
    La page Système remplace l'ancien menu pause : Échap ouvre directement cette page."""
    modal = True
    fullscreen = True

    def __init__(self, world, page=PAGE_INV):
        super().__init__(world, (0, 0, SCREEN_W, SCREEN_H))
        self.page = page
        self.t = 0.0
        self.cat = 0
        self.grid_page = 0
        self.cursor = 0
        self.ctx = None
        self.rot = 0.0
        self.drag = None
        self._preview_key = None
        self._preview = None
        cx = GRID_X + (GRID_COLS * STEP - (STEP - CELL)) // 2
        self.cat_rects = [pygame.Rect(cx - len(CATEGORIES) * 32 + i * 64, 150, 64, 44) for i in range(len(CATEGORIES))]
        self.cells = [pygame.Rect(GRID_X + (i % GRID_COLS) * STEP, GRID_Y + (i // GRID_COLS) * STEP, CELL, CELL)
                      for i in range(PER_PAGE)]
        self.arrow_rects = (pygame.Rect(80, 392, 32, 60), pygame.Rect(GRID_X + GRID_COLS * STEP, 392, 32, 60))
        self.nav_rects = (pygame.Rect(408, 36, 160, 50), pygame.Rect(712, 36, 160, 50))
        self.plus = {a: pygame.Rect(400, 334 + i * 42, 30, 30) for i, a in enumerate(ATTRS)}
        self.hover_attr = None
        self.ench_rects = []
        self.ench_hover = None
        self.sys_cursor = 0
        self.sys_entries = self.build_system()
        self.sys_rects = [pygame.Rect(150, 160 + i * 58, 420, 48) for i in range(len(self.sys_entries))]

    def portrait_spot(self):
        """Position (conception) et zoom du héros en 3D selon la page ; None : le monde reste visible derrière."""
        if self.page == PAGE_INV:
            return 1010, 352, 1.3
        if self.page == PAGE_CHAR:
            return 145, 226, 0.75
        return None

    def goto(self, page):
        if page != self.page:
            self.page = page
            self.ctx = None
            sfx.play("click")

    # ------------------------------------------------------------------ inventaire : données
    def entries(self):
        """Objets de la catégorie : l'équipement porté d'abord (fond bleu, comme dans BotW), puis le sac."""
        p = self.world.player
        slots = CATEGORIES[self.cat][1]
        eq = [("equip", s, it) for s, it in p.equipment.items() if it and it["slot"] in slots]
        return eq + [("bag", i, it) for i, it in enumerate(p.inventory) if it["slot"] in slots]

    def n_pages(self, ents=None):
        return max(1, math.ceil(len(self.entries() if ents is None else ents) / PER_PAGE))

    def page_entries(self):
        ents = self.entries()
        self.grid_page = min(self.grid_page, self.n_pages(ents) - 1)
        return ents[self.grid_page * PER_PAGE:(self.grid_page + 1) * PER_PAGE]

    def focus(self):
        ents = self.page_entries()
        return ents[self.cursor] if self.cursor < len(ents) else None

    def cell_at(self, pos):
        return next((i for i, rc in enumerate(self.cells) if rc.collidepoint(pos)), None)

    def set_cat(self, cat, last_page=False):
        self.cat = cat % len(CATEGORIES)
        self.grid_page = self.n_pages() - 1 if last_page else 0
        self.ctx = None
        sfx.play("click")

    def flip_grid(self, d):
        page = self.grid_page + d
        if 0 <= page < self.n_pages():
            self.grid_page = page
            sfx.play("click")
        else:
            self.set_cat(self.cat + d, last_page=d < 0)

    def move_cursor(self, dx, dy):
        col, row = self.cursor % GRID_COLS + dx, max(0, min(GRID_ROWS - 1, self.cursor // GRID_COLS + dy))
        if col < 0:
            self.flip_grid(-1)
            col = GRID_COLS - 1
        elif col >= GRID_COLS:
            self.flip_grid(1)
            col = 0
        self.cursor = row * GRID_COLS + col
        self.ctx = None

    def preview(self, item):
        """Variation d'attaque / défense / vie si l'on équipe l'objet (flèches vertes/rouges comme dans BotW)."""
        p = self.world.player
        if not item or item["slot"] == "artefact" or not p.can_equip(item) or item in p.equipment.values():
            return None
        eq = p.equipment[item["slot"]]
        key = (item["uid"], eq["uid"] if eq else None, item.get("upgrade"), eq.get("upgrade") if eq else None)
        if key != self._preview_key:
            hp, mana = p.hp, p.mana
            before = (p.dps_estimate(), p.stats["armor"], p.stats["max_hp"])
            p.equipment[item["slot"]] = item
            p.recompute()
            after = (p.dps_estimate(), p.stats["armor"], p.stats["max_hp"])
            p.equipment[item["slot"]] = eq
            p.recompute()
            p.hp, p.mana = hp, mana
            self._preview_key = key
            self._preview = tuple(a - b for a, b in zip(after, before))
        return self._preview

    # ------------------------------------------------------------------ inventaire : actions
    def actions(self, ent):
        """Choix du menu contextuel d'un objet (clic gauche ou Entrée)."""
        w = self.world
        kind, key, it = ent
        art = it["slot"] == "artefact"
        opts = []
        if kind == "bag":
            if art:
                opts += [(f"Équiper · touche {'RTG'[i]}", lambda s=s: w.assign_artifact(it, s))
                         for i, s in enumerate(ART_SLOTS)]
            elif w.player.can_equip(it):
                opts.append(("Équiper", lambda: w.bag_right_click(key)))
            opts.append(("Recycler", lambda: w.destroy_item(key)))
        else:
            opts.append(("Retirer", lambda: w.unequip(key)))
            if art:
                opts += [(f"Déplacer · touche {'RTG'[i]}", lambda s=s: w.assign_artifact(it, s))
                         for i, s in enumerate(ART_SLOTS) if s != key]
        opts.append(("Annuler", None))
        return opts

    def open_ctx(self, idx):
        ents = self.page_entries()
        if idx >= len(ents):
            return
        opts = self.actions(ents[idx])
        cell = self.cells[idx]
        w, h = 214, len(opts) * 36 + 12
        x = cell.right + 8 if cell.right + 8 + w < 660 else cell.x - 8 - w
        y = max(116, min(cell.y, 640 - h))
        self.ctx = {"opts": opts, "rect": pygame.Rect(x, y, w, h), "sel": 0,
                    "rows": [pygame.Rect(x + 6, y + 6 + i * 36, w - 12, 34) for i in range(len(opts))]}
        sfx.play("click")

    def run_ctx(self, i):
        fn = self.ctx["opts"][i][1]
        self.ctx = None
        if fn:
            fn()
            self._preview_key = None
        else:
            sfx.play("click")

    def quick_use(self, ent):
        """Clic droit : équiper / retirer directement."""
        w = self.world
        kind, key, it = ent
        if kind == "bag":
            w.bag_right_click(key)
        else:
            w.unequip(key)
        self._preview_key = None

    # ------------------------------------------------------------------ système
    def build_system(self):
        w = self.world
        es = [("Reprendre", "Retourner à l'aventure.", w.close_modal)]
        if w.is_tower:
            es.append(("Abandonner l'ascension", "Quitter l'étage et revenir au campement.",
                       lambda: w.exit_to_hub("Vous avez abandonné l'ascension.")))
        es += [("Sauvegarder", "Enregistrer la progression du personnage.", self.do_save),
               ("Plein écran", "Basculer entre fenêtre et plein écran (F11).", w.game.toggle_fullscreen),
               ("Menu principal", "Sauvegarder, puis revenir à l'écran titre.", w.save_and_menu),
               ("Quitter le jeu", "Sauvegarder, puis fermer le jeu.", w.save_and_quit)]
        return es

    def do_save(self):
        self.world.save()
        self.world.message("Partie sauvegardée.", GOLD_BRIGHT)

    def run_sys(self, i):
        sfx.play("click")
        self.sys_entries[i][2]()

    # ------------------------------------------------------------------ événements
    def handle_event(self, e):
        w = self.world
        if e.type == pygame.KEYDOWN:
            if self.ctx and self.ctx_key(e):
                return True
            if e.key == pygame.K_ESCAPE:
                w.close_modal()
            elif e.key in (pygame.K_i, pygame.K_c):
                page = PAGE_INV if e.key == pygame.K_i else PAGE_CHAR
                if self.page == page:
                    w.close_modal()
                else:
                    self.goto(page)
            elif e.key == pygame.K_TAB:
                self.goto((self.page + (-1 if e.mod & pygame.KMOD_SHIFT else 1)) % len(PAGES))
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.goto((self.page + (1 if e.key == pygame.K_RIGHT else -1)) % len(PAGES))
            elif self.page == PAGE_INV:
                self.inv_key(e)
            elif self.page == PAGE_SYS:
                self.sys_key(e)
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag = None
        elif e.type == pygame.MOUSEMOTION and self.drag is not None:
            self.rot += (e.pos[0] - self.drag) * 0.012
            self.drag = e.pos[0]
        elif e.type == pygame.MOUSEWHEEL and self.page == PAGE_INV:
            if HERO_ZONE.collidepoint(ui.mouse_pos()):
                self.rot += e.y * 0.25
            elif not self.ctx:
                self.set_cat(self.cat - e.y)
        if e.type != pygame.MOUSEBUTTONDOWN:
            return True
        for d, rc in zip((-1, 1), self.nav_rects):
            if rc.collidepoint(e.pos) and e.button == 1:
                self.goto((self.page + d) % len(PAGES))
                return True
        if self.page == PAGE_INV:
            self.inv_click(e)
        elif self.page == PAGE_CHAR:
            self.char_click(e)
        elif e.button == 1:
            for i, rc in enumerate(self.sys_rects):
                if rc.collidepoint(e.pos):
                    self.run_sys(i)
        return True

    def ctx_key(self, e):
        c = self.ctx
        if e.key == pygame.K_ESCAPE:
            self.ctx = None
        elif e.key in (pygame.K_UP, pygame.K_DOWN) or e.scancode in (26, 22):
            d = -1 if e.key == pygame.K_UP or e.scancode == 26 else 1
            c["sel"] = (c["sel"] + d) % len(c["opts"])
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.run_ctx(c["sel"])
        else:
            return False
        return True

    def inv_key(self, e):
        ent = self.focus()
        if e.scancode in CURSOR_KEYS:
            self.move_cursor(*CURSOR_KEYS[e.scancode])
        elif e.key in (pygame.K_UP, pygame.K_DOWN):
            self.move_cursor(0, -1 if e.key == pygame.K_UP else 1)
        elif e.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self.set_cat(self.cat + (1 if e.key == pygame.K_PAGEDOWN else -1))
        elif ent and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.open_ctx(self.cursor)
        elif ent and ent[0] == "bag" and e.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.world.destroy_item(ent[1])
        elif ent and ent[2]["slot"] == "artefact" and e.scancode in ART_KEYS_SC:
            self.world.assign_artifact(ent[2], ART_SLOTS[ART_KEYS_SC.index(e.scancode)])

    def inv_click(self, e):
        w = self.world
        if self.ctx:
            if e.button == 1:
                i = next((i for i, rc in enumerate(self.ctx["rows"]) if rc.collidepoint(e.pos)), None)
                if i is not None:
                    self.run_ctx(i)
                    return
            self.ctx = None
            if self.cell_at(e.pos) is None:
                return
        if e.button == 1:
            for i, rc in enumerate(self.cat_rects):
                if rc.collidepoint(e.pos):
                    self.set_cat(i)
                    return
            for d, rc in zip((-1, 1), self.arrow_rects):
                if rc.collidepoint(e.pos):
                    self.flip_grid(d)
                    return
            for rc, item, si, eid in self.ench_rects:
                if rc.collidepoint(e.pos):
                    w.enchant(item, si, eid)
                    self._preview_key = None
                    return
            if HERO_ZONE.collidepoint(e.pos):
                self.drag = e.pos[0]
                return
        idx = self.cell_at(e.pos)
        if idx is None:
            return
        self.cursor = idx
        ents = self.page_entries()
        if idx < len(ents):
            if e.button == 1:
                self.open_ctx(idx)
            elif e.button == 3:
                self.quick_use(ents[idx])

    def char_click(self, e):
        p = self.world.player
        if e.button == 1 and p.points > 0:
            for a, rc in self.plus.items():
                if rc.collidepoint(e.pos):
                    n = min(p.points, 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
                    p.alloc[a] += n
                    p.points -= n
                    p.recompute()
                    sfx.play("click")

    def sys_key(self, e):
        n = len(self.sys_entries)
        if e.key == pygame.K_UP or e.scancode == 26:
            self.sys_cursor = (self.sys_cursor - 1) % n
        elif e.key == pygame.K_DOWN or e.scancode == 22:
            self.sys_cursor = (self.sys_cursor + 1) % n
        elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.run_sys(self.sys_cursor)

    def update(self, dt):
        self.t += dt
        mouse = ui.mouse_pos()
        if self.page == PAGE_INV and not self.ctx:
            idx = self.cell_at(mouse)
            if idx is not None and idx < len(self.page_entries()):
                self.cursor = idx
        elif self.page == PAGE_SYS:
            i = next((i for i, rc in enumerate(self.sys_rects) if rc.collidepoint(mouse)), None)
            if i is not None:
                self.sys_cursor = i

    # ------------------------------------------------------------------ rendu commun
    def draw(self, surf):
        mouse = ui.mouse_pos()
        if self.page == PAGE_SYS:
            ui.veil(surf, (0, 0, 0), 150)
        self.draw_frame(surf)
        if self.page == PAGE_INV:
            self.draw_inventory(surf, mouse)
        elif self.page == PAGE_CHAR:
            self.draw_character(surf, mouse)
        else:
            self.draw_system(surf, mouse)
        self.draw_tooltips(surf)

    def draw_frame(self, surf):
        """Bandeaux haut et bas, cœurs, or, titre de la page et pages voisines (comme L / R dans BotW)."""
        from .hud import draw_hearts
        p = self.world.player
        ui.rect(surf, (0, 0, 0, 80), (0, 0, SCREEN_W, 108))
        ui.rect(surf, (0, 0, 0, 80), (0, 652, SCREEN_W, SCREEN_H - 652))
        ui.rect(surf, (210, 210, 200, 70), (0, 108, SCREEN_W, 1))
        ui.rect(surf, (210, 210, 200, 70), (0, 652, SCREEN_W, 1))
        draw_hearts(surf, self.world, 48, 39)
        coin_icon(surf, 1186, 48)
        ui.draw_text(surf, str(p.gold), (1202, 48), 20, WHITE, "bold", anchor="midleft")
        ui.draw_text(surf, PAGES[self.page], (SCREEN_W // 2, 52), 30, WHITE, "title", anchor="center")
        for i in range(len(PAGES)):
            act = i == self.page
            ui.circle(surf, WHITE if act else (120, 124, 122), (SCREEN_W // 2 + (i - 1) * 9, 76), 2 if act else 1.5)
        mouse = ui.mouse_pos()
        for d, rc in zip((-1, 1), self.nav_rects):
            hov = rc.collidepoint(mouse)
            ui.circle(surf, (12, 14, 16), (rc.centerx, 50), 10)
            ui.circle(surf, WHITE, (rc.centerx, 50), 10, 1)
            x = rc.centerx - d * 3
            ui.polygon(surf, WHITE, [(x - d * 1, 45), (x + d * 6, 50), (x - d * 1, 55)])
            ui.draw_text(surf, PAGES[(self.page + d) % len(PAGES)], (rc.centerx, 74), 17, WHITE if hov else SOFT,
                         anchor="center")
        if self.page == PAGE_INV:
            hints = [("Actions", "Clic"), ("Équiper", "Clic droit"), ("Pivoter", "Glisser"), ("Retour", "Échap")]
        elif self.page == PAGE_CHAR:
            hints = [("Répartir", "Clic"), ("+5", "Maj + clic"), ("Retour", "Échap")]
        else:
            hints = [("Choisir", "Entrée"), ("Retour", "Échap")]
        x = SCREEN_W - 40
        for label, key in reversed(hints):
            w, h = ui.text_size(key, 12, "bold")
            badge = badge_left(surf, key, x - max(h + 2, w + 10), 684)
            r = ui.draw_text(surf, label, (badge.x - 8, 684), 17, WHITE, anchor="midright")
            x = r.x - 28
        msgs = [m for m in self.world.messages if m[2] > 0]
        if msgs:
            ui.draw_text(surf, msgs[-1][0], (40, 684), 15, msgs[-1][1], "bold", anchor="midleft")

    # ------------------------------------------------------------------ inventaire
    def draw_inventory(self, surf, mouse):
        p = self.world.player
        # catégories : pictogrammes, nom au-dessus de la catégorie active
        for i, rc in enumerate(self.cat_rects):
            act = i == self.cat
            hov = rc.collidepoint(mouse)
            col = WHITE if act else ((196, 200, 196) if hov else (112, 116, 114))
            if act:
                ui.glow(surf, rc.centerx, rc.centery, 30, (60, 70, 70))
            cat_icon(surf, CATEGORIES[i][2], rc.center, col, 1.1 if act else 0.95)
        rc = self.cat_rects[self.cat]
        ui.draw_text(surf, CATEGORIES[self.cat][0], (rc.centerx, 128), 15, WHITE, anchor="center")
        ui.circle(surf, WHITE, (rc.centerx, 141), 1.5)
        ui.rect(surf, (220, 220, 210, 150), (rc.x + 6, rc.bottom + 4, rc.w - 12, 2))
        ui.draw_text(surf, f"Sac {len(p.inventory)}/{BAG_SIZE}", (GRID_X, 172), 14, SOFT, anchor="midleft", shadow=False)
        # grille
        ents = self.page_entries()
        for i, cell in enumerate(self.cells):
            self.draw_cell(surf, cell, ents[i] if i < len(ents) else None)
        if ents:
            ui.selection_frame(surf, self.cells[self.cursor], self.t, WHITE)
        pages = self.n_pages(ents if self.grid_page == 0 and len(ents) < PER_PAGE else None)
        for d, rc in zip((-1, 1), self.arrow_rects):
            if 0 <= self.grid_page + d < pages:
                x = rc.centerx - d * 6
                ui.polygon(surf, WHITE, [(x, rc.y + 8), (x + d * 16, rc.centery), (x, rc.bottom - 8)])
        if pages > 1:
            gx = GRID_X + (GRID_COLS * STEP - (STEP - CELL)) // 2
            for i in range(pages):
                ui.circle(surf, WHITE if i == self.grid_page else (110, 114, 112),
                          (gx + (i - (pages - 1) / 2) * 14, 624), 3)
        ent = self.focus()
        self.draw_stats(surf, ent)
        self.draw_description(surf, ent, mouse)
        if self.ctx:
            self.draw_ctx(surf, mouse)

    def draw_cell(self, surf, rc, ent):
        if not ent:
            ui.botw_box(surf, rc, 110, (78, 80, 78), radius=4)
            return
        p = self.world.player
        kind, key, it = ent
        equipped = kind == "equip"
        ui.botw_box(surf, rc, 205 if equipped else 150, SHEIKAH if equipped else FRAME, radius=4,
                    fill=(16, 78, 110) if equipped else (0, 0, 0))
        col = RARITY_COLORS[it["rarity"]]
        if it["rarity"] != "commun":
            ui.rect(surf, (*col, 34), rc.inflate(-4, -4), 0, 3)
            ui.rect(surf, col, (rc.x + 8, rc.bottom - 4, rc.w - 16, 2))
        ui.draw_item_icon(surf, it, rc.inflate(-rc.w * 0.3, -rc.h * 0.3).move(0, -4), bg=False)
        st = item_stats(it) if it["slot"] != "artefact" else {}
        val = int(round(sum(st["dmg"]) / 2)) if "dmg" in st else st.get("armor")
        if val:
            ui.draw_text(surf, str(val), (rc.x + 7, rc.bottom - 5), 15, WHITE, "bold", anchor="bottomleft")
        if it.get("upgrade"):
            ui.draw_text(surf, f"+{it['upgrade']}", (rc.x + 6, rc.y + 4), 12, GOLD_BRIGHT, "bold")
        if it.get("ench") and any(e["id"] for e in it["ench"]):
            ui.circle(surf, ENCH_COL, (rc.right - 9, rc.y + 9), 4)
        if equipped and it["slot"] == "artefact":
            ui.key_badge(surf, "RTG"[ART_SLOTS.index(key)], (rc.right - 12, rc.bottom - 12), 11, SHEIKAH)
        if not p.can_equip(it):
            ui.line(surf, DOWN, (rc.x + 8, rc.bottom - 8), (rc.right - 8, rc.y + 8), 2)

    def draw_stats(self, surf, ent):
        """Attaque / défense / vie à côté du héros, avec la variation si l'on équipe l'objet visé."""
        p = self.world.player
        s = p.stats
        delta = self.preview(ent[2]) if ent else None
        rows = [(attack_icon, p.dps_estimate()), (shield_icon, s["armor"]), (heart_icon, s["max_hp"])]
        for i, (icon, val) in enumerate(rows):
            y = 150 + i * 42
            icon(surf, 710, y)
            r = ui.draw_text(surf, str(int(val)), (732, y), 24, WHITE, "bold", anchor="midleft")
            if delta and abs(delta[i]) >= 1:
                up = delta[i] > 0
                col = UP if up else DOWN
                ax, ay = r.right + 16, y
                ui.polygon(surf, col, [(ax, ay - 8), (ax + 7, ay + 2), (ax - 7, ay + 2)] if up else
                           [(ax, ay + 8), (ax + 7, ay - 2), (ax - 7, ay - 2)])
                ui.draw_text(surf, f"{'+' if up else ''}{int(delta[i])}", (ax + 12, y), 15, col, "bold",
                             anchor="midleft")
        if not ent:
            return
        kind, key, it = ent
        acts = [("Clic", "Actions")]
        if kind == "bag":
            if it["slot"] == "artefact":
                acts.append(("R T G", "Équiper sur la touche"))
            elif p.can_equip(it):
                acts.append(("Clic droit", "Équiper"))
            acts.append(("Suppr", "Recycler"))
        else:
            acts.append(("Clic droit", "Retirer"))
        for i, (k, label) in enumerate(acts):
            y = 290 + i * 30
            b = badge_left(surf, k, 700, y)
            ui.draw_text(surf, label, (b.right + 8, y), 16, WHITE, anchor="midleft")

    def draw_description(self, surf, ent, mouse):
        p = self.world.player
        box = ui.botw_box(surf, DESC, 200, (170, 170, 162), radius=4)
        ui.rect(surf, (80, 82, 80), box.inflate(-8, -8), 1, 3)
        self.ench_rects = []
        self.ench_hover = None
        if not ent:
            ui.draw_text(surf, f"Aucun objet dans « {CATEGORIES[self.cat][0]} ».", box.center, 16, SOFT,
                         anchor="center")
            return
        kind, key, it = ent
        name = it["name"] + (f" +{it['upgrade']}" if it.get("upgrade") else "")
        ui.draw_text(surf, name, (box.x + 24, box.y + 12), 25, WHITE, "title_bold")
        ui.draw_text(surf, f"{item_value(it)} or", (box.right - 20, box.y + 20), 14, GOLD, "bold", anchor="topright")
        x, y = box.x + 24, box.y + 50
        if it["slot"] == "artefact":
            x = chip(surf, x, y, f"Recharge {ARTIFACTS[it['art']]['cd']} s", SHEIKAH, small_clock)
        else:
            st = item_stats(it)
            if "dmg" in st:
                x = chip(surf, x, y, f"{int(st['dmg'][0])}-{int(st['dmg'][1])}", WHITE, small_attack, FRAME)
            elif "armor" in st:
                x = chip(surf, x, y, str(st["armor"]), WHITE, small_shield, FRAME)
        x = chip(surf, x, y, RARITY_NAMES[it["rarity"]], RARITY_COLORS[it["rarity"]])
        sub = SLOT_NAMES[it["slot"]] + (f" · {CLASSES[it['wclass']]['name']}" if it["slot"] == "arme" else "")
        x = chip(surf, x, y, sub, SOFT if p.can_equip(it) else DOWN)
        x = chip(surf, x, y, f"Niv. {it['ilvl']}", SOFT)
        if kind == "equip":
            chip(surf, x, y, "Équipé", SHEIKAH)
        y = box.y + 86
        if it["slot"] == "artefact":
            ui.draw_wrapped(surf, art_desc(it), box.x + 24, y, box.w - 48, 15, WHITE)
            return
        affs = [AFFIX_DEF[k][0].format(v=v) for k, v in item_stats(it)["affixes"].items()]
        if not affs:
            ui.draw_text(surf, "Aucun bonus.", (box.x + 24, y), 15, (130, 134, 134))
        for i, a in enumerate(affs[:6]):
            ui.draw_text(surf, a, (box.x + 24 + (i // 3) * 280, y + (i % 3) * 21), 15, (150, 185, 255))
        self.draw_enchants(surf, it, box, mouse)

    def draw_enchants(self, surf, it, box, mouse):
        """Emplacements d'enchantement : 3 choix par emplacement, puis amélioration jusqu'au niveau III."""
        p = self.world.player
        slots = it.get("ench", [])
        y = box.y + 162
        ui.rect(surf, (110, 112, 108), (box.x + 20, y - 10, box.w - 40, 1))
        if not slots:
            ui.draw_text(surf, "Aucun emplacement d'enchantement", (box.x + 24, y + 18), 13, (130, 134, 134),
                         anchor="midleft")
            return
        ui.draw_text(surf, f"{p.ench_points} point(s) d'enchantement", (box.right - 20, y + 18), 13, ENCH_COL,
                     "bold", anchor="midright")
        for si, e in enumerate(slots):
            sx = box.x + 22 + si * 128
            if e["id"]:
                d = ENCHANTS[e["id"]]
                c = (sx + 18, y + 18)
                r = pygame.Rect(c[0] - 15, c[1] - 15, 30, 30)
                hov = r.collidepoint(mouse)
                ui.circle(surf, (60, 34, 90), c, 15)
                ui.circle(surf, SHEIKAH if hov else ENCH_COL, c, 15, 2)
                ui.draw_text(surf, d["name"][:2], c, 12, WHITE, "bold", anchor="center", shadow=False)
                ui.draw_text(surf, d["name"], (sx + 40, y + 2), 12, WHITE, "bold")
                for lv in range(3):
                    ui.circle(surf, ENCH_COL if lv < e["lvl"] else (60, 56, 70), (sx + 46 + lv * 13, y + 28), 4.5)
                if e["lvl"] < 3:
                    self.ench_rects.append((r, it, si, e["id"]))
                if hov:
                    self.ench_hover = (it, si, e["id"])
            else:
                for ci, eid in enumerate(e["choices"]):
                    c = (sx + 16 + ci * 36, y + 18)
                    r = pygame.Rect(c[0] - 15, c[1] - 15, 30, 30)
                    hov = r.collidepoint(mouse)
                    ui.circle(surf, (40, 26, 60), c, 15)
                    ui.circle(surf, SHEIKAH if hov else (140, 110, 190), c, 15, 2 if hov else 1)
                    ui.draw_text(surf, ENCHANTS[eid]["name"][:2], c, 12, WHITE, "bold", anchor="center",
                                 shadow=False)
                    self.ench_rects.append((r, it, si, eid))
                    if hov:
                        self.ench_hover = (it, si, eid)

    def draw_ctx(self, surf, mouse):
        c = self.ctx
        ui.botw_box(surf, c["rect"], 248, (190, 190, 182), radius=6, fill=(8, 12, 14))
        for i, ((label, _), rc) in enumerate(zip(c["opts"], c["rows"])):
            if rc.collidepoint(mouse):
                c["sel"] = i
            sel = i == c["sel"]
            if sel:
                ui.rect(surf, (255, 255, 255, 36), rc, 0, 4)
                ui.selection_frame(surf, rc, self.t, WHITE)
            col = DOWN if label == "Recycler" else (WHITE if sel else SOFT)
            ui.draw_text(surf, label, (rc.x + 14, rc.centery), 16, col, anchor="midleft")

    # ------------------------------------------------------------------ personnage
    def draw_character(self, surf, mouse):
        p = self.world.player
        s = p.stats
        col = ui.botw_box(surf, (40, 122, 420, 518), 120, FRAME, radius=4)
        ui.draw_text(surf, p.name, (250, 136), 28, WHITE, "title")
        ui.draw_text(surf, p.cls["title"], (252, 174), 15, SOFT)
        ui.draw_text(surf, f"{p.cls['name']}  ·  Niveau {p.level}", (252, 196), 16, BOTW_YELLOW, "bold")
        need = xp_needed(p.level)
        bar = pygame.Rect(252, 226, 180, 8)
        ui.rect(surf, (0, 0, 0), bar.inflate(2, 2), 0, 4)
        ui.rect(surf, (236, 200, 90), (bar.x, bar.y, max(1, bar.w * min(1, p.xp / need)), bar.h), 0, 4)
        ui.draw_text(surf, f"{p.xp} / {need} XP", (bar.x, bar.bottom + 4), 12, SOFT, shadow=False)
        ui.draw_text(surf, f"Points d'enchantement : {p.ench_points}", (252, 260), 13, ENCH_COL, "bold")
        ui.draw_text(surf, "Caractéristiques", (64, 296), 19, WHITE, "title")
        if p.points:
            k = 0.6 + 0.4 * math.sin(self.t * 4)
            ui.draw_text(surf, f"{p.points} point(s) à répartir", (436, 300), 14,
                         (int(110 * k + 60), 235, int(120 * k + 40)), "bold", anchor="topright")
        self.hover_attr = None
        for i, a in enumerate(ATTRS):
            y = 334 + i * 42
            row = pygame.Rect(60, y - 4, 380, 36)
            hov = row.collidepoint(mouse)
            if hov:
                self.hover_attr = a
            ui.botw_box(surf, row, 170 if hov else 120, WHITE if hov else (100, 102, 100), radius=4)
            prim = a == p.cls["primary"]
            ui.draw_text(surf, ATTR_NAMES[a], (80, y + 3), 17, BOTW_YELLOW if prim else WHITE, "bold")
            if prim:
                ui.draw_text(surf, "principale", (206, y + 7), 12, SOFT, shadow=False)
            ui.draw_text(surf, str(int(s[a])), (380, y + 2), 19, WHITE, "bold", anchor="topright")
            if p.points:
                rc = self.plus[a]
                h2 = rc.collidepoint(mouse)
                ui.circle(surf, (40, 110, 60) if h2 else (20, 60, 34), rc.center, 14)
                ui.circle(surf, UP, rc.center, 14, 1)
                ui.draw_text(surf, "+", rc.center, 20, WHITE, "bold", anchor="center", shadow=False)
        if self.hover_attr:
            ui.draw_text(surf, ATTR_DESC[self.hover_attr], (col.centerx, 548), 14, SOFT, anchor="midtop")
        ui.draw_text(surf, f"Étage max {p.max_floor}  ·  {p.kills} monstres vaincus  ·  {p.deaths} mort(s)",
                     (col.centerx, 604), 13, SOFT, anchor="midtop")
        # statistiques
        ui.botw_box(surf, (476, 122, 350, 518), 150, FRAME, radius=4)
        ui.draw_text(surf, "Statistiques", (651, 134), 19, WHITE, "title", anchor="midtop")
        dr = p.damage_reduction() * 100
        rows = [
            ("Vie", f"{int(p.hp)} / {int(s['max_hp'])}"), ("Mana", f"{int(p.mana)} / {int(s['max_mana'])}"),
            ("Dégâts de l'arme", f"{int(s['dmg_min'])} - {int(s['dmg_max'])}"),
            ("Multiplicateur", f"x{s['dmg_mult']:.2f}"), ("Dégâts / seconde", f"{int(p.dps_estimate())}"),
            ("Armure", f"{int(s['armor'])}"), ("Réduction des dégâts", f"{dr:.0f}%"),
            ("Coup critique", f"{s['crit']:.1f}%"), ("Vitesse d'attaque", f"+{s['atk_speed']:.0f}%"),
            ("Vol de vie", f"{s['lifesteal']:.0f}%"), ("Régén. de mana", f"{s['mana_regen']:.1f}/s"),
            ("Recharge des sorts", f"-{s['cdr']:.0f}%"), ("Déplacement", f"+{s['move_speed']:.0f}%"),
            ("Recharge potion / roulade", f"{p.potion_total:.0f} s / {p.roll_total:.1f} s"),
            ("Or trouvé", f"+{s['gold_find']:.0f}%"),
        ]
        y = 168
        for i, (label, val) in enumerate(rows):
            if i % 2 == 0:
                ui.botw_box(surf, (490, y - 3, 322, 24), 70, None, radius=4, fill=(40, 60, 70))
            ui.draw_text(surf, label, (504, y), 14, SOFT)
            ui.draw_text(surf, val, (798, y), 14, WHITE, "bold", anchor="topright")
            y += 25
        if p.anima:
            y += 6
            ui.draw_text(surf, "Pouvoirs d'anima", (651, y), 16, SHEIKAH, "title", anchor="midtop")
            y += 24
            for pid, n in p.anima.items():
                if y > 614:
                    break
                pw = ANIMA_POWERS[pid]
                ui.circle(surf, pw["color"], (504, y + 8), 5)
                ui.draw_text(surf, f"{pw['name']} x{n}", (516, y), 13, WHITE)
                y += 19
        # compétences
        ui.botw_box(surf, (842, 122, 398, 518), 150, FRAME, radius=4)
        ui.draw_text(surf, "Compétences", (1041, 134), 19, WHITE, "title", anchor="midtop")
        a = p.cls["attack"]
        entries = [(a["name"], a.get("color", p.cls["color"]), f"Attaque de base · {int(a['mult'] * 100)}% arme",
                    "Clic gauche maintenu.", True, "LMB")]
        for i, sid in enumerate(p.spells):
            sp = SPELLS[sid]
            entries.append((sp["name"], sp["color"], f"Mana {sp['mana']} · Recharge {sp['cd']} s · Niv {sp['level']}",
                            sp["desc"], p.spell_unlocked(sid), str(i + 1)))
        y = 170
        for name, c, meta, desc, ok, key in entries:
            ui.circle(surf, ui.darker(c, 0.45) if ok else (30, 30, 30), (878, y + 20), 20)
            ui.circle(surf, ui.lighter(c, 1.2) if ok else (90, 90, 90), (878, y + 20), 20, 2)
            ui.draw_text(surf, key, (878, y + 20), 12, WHITE if ok else (120, 120, 120), "bold", anchor="center",
                         shadow=False)
            ui.draw_text(surf, name, (910, y), 16, WHITE if ok else (130, 130, 130), "bold")
            ui.draw_text(surf, meta, (910, y + 21), 12, SHEIKAH if ok else (120, 120, 120), shadow=False)
            yy = y + 39
            for line in ui.wrap(desc, 13, 310)[:2]:
                ui.draw_text(surf, line, (910, yy), 13, SOFT if ok else (110, 110, 110), shadow=False)
                yy += 17
            y = max(yy, y + 60) + 10

    # ------------------------------------------------------------------ système (ancien menu pause)
    def draw_system(self, surf, mouse):
        for i, ((label, desc, _), rc) in enumerate(zip(self.sys_entries, self.sys_rects)):
            sel = i == self.sys_cursor
            ui.botw_box(surf, rc, 190 if sel else 130, WHITE if sel else FRAME, radius=4,
                        fill=(20, 40, 50) if sel else (0, 0, 0))
            ui.draw_text(surf, label, (rc.x + 22, rc.centery), 19, WHITE if sel else SOFT, "title", anchor="midleft")
            if sel:
                ui.selection_frame(surf, rc, self.t, WHITE)
        last = self.sys_rects[-1]
        ui.draw_wrapped(surf, self.sys_entries[self.sys_cursor][1], last.x, last.bottom + 22, last.w, 15, SOFT)
        box = ui.botw_box(surf, (660, 140, 470, 470), 170, FRAME, radius=4)
        ui.draw_text(surf, "Commandes", (box.centerx, box.y + 16), 20, WHITE, "title", anchor="midtop")
        ui.rect(surf, (110, 112, 108), (box.x + 24, box.y + 52, box.w - 48, 1))
        controls = [
            ("ZQSD / WASD / flèches", "Se déplacer"), ("Clic gauche (maintenu)", "Attaque de base"),
            ("1 2 3 4 · clic droit", "Sorts (clic droit = sort 1)"), ("Espace", "Roulade d'esquive"),
            ("R · T · G", "Artefacts"), ("F", "Potion (à recharge)"), ("E", "Interagir"),
            ("I · C · Échap", "Inventaire · Personnage · Système"), ("Tab", "Carte"), ("F11", "Plein écran"),
        ]
        y = box.y + 66
        for i, (k, v) in enumerate(controls):
            if i % 2 == 0:
                ui.rect(surf, (40, 60, 70, 70), (box.x + 16, y - 4, box.w - 32, 36), 0, 4)
            ui.draw_text(surf, k, (box.x + 30, y + 14), 15, BOTW_YELLOW, "bold", anchor="midleft")
            ui.draw_text(surf, v, (box.right - 30, y + 14), 15, SOFT, anchor="midright")
            y += 39

    def draw_tooltips(self, surf):
        if self.page == PAGE_INV and self.ench_hover and not self.ctx:
            it, si, eid = self.ench_hover
            e = it["ench"][si]
            d = ENCHANTS[eid]
            lvl = e["lvl"] if e["id"] == eid else 0
            lines = [(d["name"] + (f" {'I' * lvl}" if lvl else ""), ENCH_COL, 17)]
            if lvl:
                lines.append(("Actuel : " + d["desc"].format(v=ench_value(eid, lvl)), WHITE, 14))
            if lvl < 3:
                lines.append((("Niveau suivant : " if lvl else "") + d["desc"].format(v=ench_value(eid, lvl + 1)),
                              UP, 14))
                lines.append((f"Coût : {lvl + 1} point(s) — clic pour enchanter", SOFT, 13))
            else:
                lines.append(("Niveau maximum", SOFT, 13))
            ui.draw_tooltip_lines(surf, lines, ui.mouse_pos(), ENCH_COL, side="left")


# =========================================================================== sac compact (marchand / forge)
class InventoryPanel(Panel):
    COLS, CELL = 8, 44

    def __init__(self, world):
        super().__init__(world, (SCREEN_W - 408, 16, 392, 620))
        r = self.rect
        cx, top, S = r.centerx, r.y + 64, 52
        self.slot_rects = {
            "casque": pygame.Rect(cx - S // 2, top, S, S),
            "amulette": pygame.Rect(cx + S // 2 + 22, top + 6, 44, 44),
            "arme": pygame.Rect(cx - S // 2 - S - 22, top + S + 8, S, S + 20),
            "torse": pygame.Rect(cx - S // 2, top + S + 8, S, S + 20),
            "anneau": pygame.Rect(cx + S // 2 + 22, top + S + 18, 44, 44),
            "gants": pygame.Rect(cx - S // 2 - S - 22, top + 2 * S + 36, S, S),
            "bottes": pygame.Rect(cx - S // 2, top + 2 * S + 36, S, S),
        }
        base_y = top + 3 * S + 50
        for i, s in enumerate(ART_SLOTS):
            self.slot_rects[s] = pygame.Rect(r.x + 110 + i * 60, base_y, 44, 44)
        gx = r.x + (r.w - self.COLS * self.CELL) // 2
        gy = base_y + 76
        self.bag_rects = [pygame.Rect(gx + (i % self.COLS) * self.CELL, gy + (i // self.COLS) * self.CELL,
                                      self.CELL - 4, self.CELL - 4) for i in range(BAG_SIZE)]
        self.t = 0.0

    def item_at(self, pos):
        p = self.world.player
        for slot, rc in self.slot_rects.items():
            if rc.collidepoint(pos):
                return ("equip", slot, p.equipment[slot])
        for i, rc in enumerate(self.bag_rects):
            if rc.collidepoint(pos):
                return ("bag", i, p.inventory[i] if i < len(p.inventory) else None)
        return None

    def handle_event(self, e):
        w = self.world
        if e.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos):
            hit = self.item_at(e.pos)
            if hit and hit[2]:
                kind, key, item = hit
                if e.button == 3:
                    if kind == "bag":
                        w.bag_right_click(key)
                    else:
                        w.unequip(key)
                elif e.button == 1 and isinstance(w.left_panel, ForgePanel):
                    w.left_panel.select(item)
            return True
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            hit = self.item_at(ui.mouse_pos())
            if hit and hit[0] == "bag" and hit[2]:
                w.destroy_item(hit[1])
                return True
        return False

    def draw(self, surf):
        self.t += 1 / 60
        p = self.world.player
        ui.botw_panel(surf, self.rect, "Sac")
        mouse = ui.mouse_pos()
        sel = self.world.left_panel.selected if isinstance(self.world.left_panel, ForgePanel) else None
        for slot, rc in self.slot_rects.items():
            it = p.equipment[slot]
            item_slot(surf, rc, it, self.t, it is not None and it is sel, rc.collidepoint(mouse) and it is not None,
                      True, SLOT_NAMES[slot])
        r = self.rect
        y = self.bag_rects[0].y - 24
        ui.draw_text(surf, f"{len(p.inventory)}/{BAG_SIZE}", (r.x + 26, y), 15, SOFT)
        ui.draw_text(surf, f"{p.gold} or", (r.right - 26, y), 16, GOLD_BRIGHT, "bold", anchor="topright")
        for i, rc in enumerate(self.bag_rects):
            it = p.inventory[i] if i < len(p.inventory) else None
            item_slot(surf, rc, it, self.t, it is not None and it is sel, rc.collidepoint(mouse) and it is not None,
                      it is None or p.can_equip(it))
        lp = self.world.left_panel
        hint = "Clic droit : vendre" if isinstance(lp, MerchantPanel) else "Clic gauche : choisir l'objet"
        ui.draw_text(surf, hint, (r.centerx, r.bottom - 12), 13, SOFT, anchor="midbottom")

    def draw_tooltips(self, surf):
        pos = ui.mouse_pos()
        if not self.rect.collidepoint(pos):
            return
        hit = self.item_at(pos)
        if not hit or not hit[2]:
            return
        p = self.world.player
        kind, key, item = hit
        tip = ui.item_tooltip(surf, item, pos, p, "Équipé" if kind == "equip" else None, side="left")
        if kind == "bag" and item["slot"] != "artefact":
            eq = p.equipment.get(item["slot"])
            if eq:
                ui.item_tooltip(surf, eq, (tip.x - 4, tip.y - 8), p, "Actuellement équipé", side="left")
        if kind == "bag" and isinstance(self.world.left_panel, MerchantPanel):
            ui.draw_text(surf, f"Vendre : {item_value(item)} or", (tip.centerx, tip.bottom + 4), 15, GOLD, "bold",
                         anchor="midtop")


# =========================================================================== marchand
class MerchantPanel(Panel):
    def __init__(self, world):
        super().__init__(world, (16, 16, 380, 620))
        r = self.rect
        self.rows = [pygame.Rect(r.x + 20, r.y + 70 + i * 56, r.w - 40, 50) for i in range(9)]
        self.hover = None

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos):
            if e.button == 1:
                for i, rc in enumerate(self.rows):
                    if rc.collidepoint(e.pos) and i < len(self.world.shop_stock):
                        self.world.buy_item(i)
            return True
        return False

    def draw(self, surf):
        r = self.rect
        p = self.world.player
        ui.botw_panel(surf, r, "Gorvan le Marchand")
        self.hover = None
        mouse = ui.mouse_pos()
        for i, rc in enumerate(self.rows):
            if i >= len(self.world.shop_stock):
                break
            it = self.world.shop_stock[i]
            hov = rc.collidepoint(mouse)
            if hov:
                self.hover = it
            ui.botw_box(surf, rc, 180 if hov else 110, SHEIKAH if hov else (90, 94, 92), radius=10,
                        fill=(10, 30, 40) if hov else (0, 0, 0))
            item_slot(surf, (rc.x + 4, rc.y + 4, 42, 42), it, 0)
            ui.draw_text(surf, it["name"], (rc.x + 56, rc.y + 5), 15, RARITY_COLORS[it["rarity"]], "bold")
            ui.draw_text(surf, SLOT_NAMES[it["slot"]], (rc.x + 56, rc.y + 27), 13, SOFT)
            price = buy_price(it)
            ui.draw_text(surf, f"{price} or", (rc.right - 10, rc.y + 27), 15, GOLD if p.gold >= price else RED, "bold",
                         anchor="topright")
        ui.draw_text(surf, "Clic gauche : acheter", (r.centerx, r.bottom - 12), 13, SOFT, anchor="midbottom")

    def draw_tooltips(self, surf):
        if self.hover:
            tip = ui.item_tooltip(surf, self.hover, ui.mouse_pos(), self.world.player)
            if self.hover["slot"] != "artefact":
                eq = self.world.player.equipment.get(self.hover["slot"])
                if eq:
                    ui.item_tooltip(surf, eq, (tip.right + 4, tip.y - 8), self.world.player, "Actuellement équipé")


# =========================================================================== forge
class ForgePanel(Panel):
    def __init__(self, world):
        super().__init__(world, (16, 16, 380, 620))
        self.selected = None
        r = self.rect
        self.btn = ui.Button((r.x + 40, r.bottom - 76, r.w - 80, 44), "Améliorer", self.upgrade, 18)

    def select(self, item):
        self.selected = item
        sfx.play("click")

    def upgrade(self):
        it = self.selected
        p = self.world.player
        if not it:
            return
        cost = upgrade_cost(it)
        if it.get("upgrade", 0) >= MAX_UPGRADE:
            self.world.message("Cet objet est déjà au maximum.", RED)
        elif p.gold < cost:
            self.world.message("Pas assez d'or.", RED)
        else:
            p.gold -= cost
            it["upgrade"] = it.get("upgrade", 0) + 1
            p.recompute()
            sfx.play("chest")
            self.world.message(f"{it['name']} amélioré à +{it['upgrade']} !", GOLD_BRIGHT)

    def handle_event(self, e):
        if self.btn.handle(e):
            return True
        return e.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(e.pos)

    def draw(self, surf):
        r = self.rect
        p = self.world.player
        ui.botw_panel(surf, r, "Hilda la Forgeronne")
        y = ui.draw_wrapped(surf, "« Apporte-moi ton équipement, je le rendrai plus redoutable. Chaque amélioration "
                                  "renforce l'objet de 10% (jusqu'à +5). »", r.x + 24, r.y + 64, r.w - 48, 15, SOFT)
        it = self.selected
        if it and it not in p.inventory and it not in p.equipment.values():
            self.selected = it = None
        y += 14
        if not it:
            ui.draw_wrapped(surf, "Cliquez (gauche) sur un objet de votre sac ou de votre équipement.", r.x + 24,
                            y + 20, r.w - 48, 16, (150, 156, 156))
            self.btn.enabled = False
        else:
            item_slot(surf, (r.x + 24, y, 64, 64), it, 0, False)
            ui.draw_text(surf, it["name"], (r.x + 100, y + 6), 17, RARITY_COLORS[it["rarity"]], "bold")
            ui.draw_text(surf, f"Amélioration : +{it.get('upgrade', 0)} / {MAX_UPGRADE}", (r.x + 100, y + 32), 15, SOFT)
            y += 82
            nxt = dict(it, upgrade=min(MAX_UPGRADE, it.get("upgrade", 0) + 1))
            keep = ((240, 240, 240), (125, 150, 255))
            lc = [l for l in item_lines(it) if l[1] in keep]
            ln = [l for l in item_lines(nxt) if l[1] in keep]
            for a, b in zip(lc, ln):
                ui.draw_text(surf, a[0], (r.x + 24, y), 14, TEXT)
                if a[0] != b[0]:
                    val = b[0].split(":")[-1].strip() if ":" in b[0] else b[0].split(" ")[0]
                    ui.draw_text(surf, "→ " + val, (r.right - 24, y), 14, UP, "bold", anchor="topright")
                y += 20
            maxed = it.get("upgrade", 0) >= MAX_UPGRADE
            cost = upgrade_cost(it)
            self.btn.text = "Niveau maximum" if maxed else f"Améliorer — {cost} or"
            self.btn.enabled = not maxed and p.gold >= cost
        ui.draw_text(surf, f"Votre or : {p.gold}", (r.centerx, self.btn.rect.y - 30), 16, GOLD, "bold", anchor="midtop")
        self.btn.draw(surf)


# =========================================================================== portail
class PortalPanel(Panel):
    modal = True

    def __init__(self, world):
        super().__init__(world, (SCREEN_W // 2 - 300, 70, 600, 560))
        self.scroll = max(0, world.player.max_floor - 7)
        self.close_btn = ui.Button((self.rect.centerx - 80, self.rect.bottom - 58, 160, 40), "Fermer",
                                   world.close_modal)

    def rows(self):
        p = self.world.player
        res = []
        for i in range(7):
            f = self.scroll + i + 1
            if f > p.max_floor:
                break
            res.append((f, pygame.Rect(self.rect.x + 30, self.rect.y + 70 + i * 56, self.rect.w - 60, 50)))
        return res

    def handle_event(self, e):
        if self.close_btn.handle(e):
            return True
        if e.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.world.player.max_floor - 7, self.scroll - e.y))
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for f, rc in self.rows():
                if rc.collidepoint(e.pos):
                    sfx.play("portal")
                    self.world.enter_tower(f)
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.world.close_modal()
        return True

    def draw(self, surf):
        ui.botw_panel(surf, self.rect, "Portail de la Tour")
        p = self.world.player
        mouse = ui.mouse_pos()
        t = self.world.time
        for f, rc in self.rows():
            hov = rc.collidepoint(mouse)
            ui.botw_box(surf, rc, 190 if hov else 110, SHEIKAH if hov else (90, 94, 92), radius=12,
                        fill=(10, 34, 44) if hov else (0, 0, 0))
            done = f in p.cleared
            ui.draw_text(surf, f"Étage {f}", (rc.x + 16, rc.y + 4), 21, WHITE, "title")
            ui.draw_text(surf, floor_name(f), (rc.x + 16, rc.y + 29), 14, SOFT)
            b = BOSSES[floor_boss(f)]
            ui.draw_text(surf, f"Gardien : {b['name']}", (rc.right - 16, rc.y + 7), 15, WHITE, "bold", anchor="topright")
            ui.draw_text(surf, "Vaincu" if done else "Jamais vaincu", (rc.right - 16, rc.y + 29), 13,
                         UP if done else DOWN, anchor="topright")
            if hov:
                ui.selection_frame(surf, rc, t, SHEIKAH)
        if p.max_floor > 7:
            ui.draw_text(surf, "Molette : faire défiler", (self.rect.centerx, self.rect.bottom - 80), 13, SOFT,
                         anchor="midbottom")
        self.close_btn.draw(surf)


# =========================================================================== anima
class AnimaPanel(Panel):
    modal = True

    def __init__(self, world, choices):
        super().__init__(world, (SCREEN_W // 2 - 390, 140, 780, 430))
        self.choices = choices
        self.cards = [pygame.Rect(self.rect.x + 30 + i * 245, self.rect.y + 110, 225, 270) for i in range(len(choices))]
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.t > 0.3:
            for (pid, tier), rc in zip(self.choices, self.cards):
                if rc.collidepoint(e.pos):
                    self.world.take_anima(pid, tier)
                    return True
        if e.type == pygame.KEYDOWN and e.scancode in (30, 31, 32, 89, 90, 91) and self.t > 0.3:
            i = {30: 0, 31: 1, 32: 2, 89: 0, 90: 1, 91: 2}[e.scancode]
            if i < len(self.choices):
                self.world.take_anima(*self.choices[i])
        return True

    def draw(self, surf):
        ui.botw_panel(surf, self.rect, "Pouvoir d'Anima")
        ui.draw_text(surf, "Choisissez un pouvoir. Il durera jusqu'à la fin de cette ascension.",
                     (self.rect.centerx, self.rect.y + 64), 16, SOFT, anchor="midtop")
        mouse = ui.mouse_pos()
        p = self.world.player
        for i, ((pid, tier), rc) in enumerate(zip(self.choices, self.cards)):
            pw = ANIMA_POWERS[pid]
            tname, tcol, tval, _ = ANIMA_TIERS[tier]
            hov = rc.collidepoint(mouse)
            ui.botw_box(surf, rc, 200 if hov else 140, tcol if hov else ui.darker(tcol, 0.7), radius=14,
                        fill=(14, 22, 30) if hov else (0, 0, 0))
            ui.draw_text(surf, tname.upper(), (rc.centerx, rc.y + 12), 12, tcol, "bold", anchor="midtop")
            c = (rc.centerx, rc.y + 70)
            ui.glow(surf, c[0], c[1], 44 + 8 * math.sin(self.t * 3 + i), ui.darker(pw["color"], 0.5))
            ui.circle(surf, ui.darker(pw["color"], 0.4), c, 32)
            ui.circle(surf, tcol, c, 32, 2 + tier)
            ui.polygon(surf, pw["color"], [(c[0], c[1] - 18), (c[0] + 14, c[1]), (c[0], c[1] + 18), (c[0] - 14, c[1])])
            ui.draw_text(surf, pw["name"], (rc.centerx, rc.y + 118), 18, WHITE, "bold", anchor="midtop")
            y = rc.y + 152
            for line in ui.wrap(anima_desc(pid, tval), 15, rc.w - 26):
                r = ui.draw_text(surf, line, (rc.centerx, y), 15, SOFT, anchor="midtop")
                y += r.h + 2
            n = p.anima.get(pid, 0)
            if n:
                ui.draw_text(surf, f"Déjà possédé : x{n}", (rc.centerx, rc.bottom - 30), 13, SOFT, anchor="midtop")
            ui.draw_text(surf, f"[{i + 1}]", (rc.x + 10, rc.y + 8), 13, SOFT)
            if hov:
                ui.selection_frame(surf, rc, self.t, tcol)


# =========================================================================== mort
class DeathPanel(Panel):
    modal = True

    def __init__(self, world, lost):
        super().__init__(world, (SCREEN_W // 2 - 270, 260, 540, 250))
        self.lost = lost
        self.t = 0.0
        self.btn = ui.Button((self.rect.centerx - 150, self.rect.bottom - 68, 300, 46), "Retourner au campement",
                             lambda: world.exit_to_hub("Vous vous réveillez au campement, meurtri..."))

    def update(self, dt):
        self.t += dt

    def handle_event(self, e):
        if self.t > 1.0:
            self.btn.handle(e)
        return True

    def draw(self, surf):
        ui.veil(surf, (50, 0, 0), int(min(1, self.t) * 150))
        ui.draw_text(surf, "VOUS ÊTES MORT", (SCREEN_W // 2, 180), 60, (220, 40, 40), "title", anchor="center",
                     alpha=int(255 * min(1, self.t * 1.5)))
        ui.botw_panel(surf, self.rect)
        ui.draw_text(surf, "Cendrespire a eu raison de vous.", (self.rect.centerx, self.rect.y + 34), 20, WHITE,
                     anchor="midtop")
        ui.draw_text(surf, f"Vous perdez {self.lost} pièces d'or récoltées pendant l'ascension.",
                     (self.rect.centerx, self.rect.y + 76), 16, GOLD, anchor="midtop")
        ui.draw_text(surf, "Votre équipement et votre expérience sont conservés.",
                     (self.rect.centerx, self.rect.y + 104), 16, SOFT, anchor="midtop")
        if self.t > 1.0:
            self.btn.draw(surf)
