"""Menus en jeu, style Zelda BotW : menu plein écran (inventaire avec héros en 3D, personnage, système),
enchantements, marchand, forge, portail, pouvoirs d'anima et mort.
Le menu principal (Personnage · Inventaire · Système) remplace aussi l'ancien menu pause.
Coordonnées « de conception » (1280x720), dessin via ui (net en Retina)."""
import math

import pygame

from . import updates, sfx, ui
from .data import (ARTIFACT_KEYS, ATTRS, ATTR_NAMES, ATTR_DESC, SPELLS, ANIMA_POWERS, ANIMA_TIERS, BAG_SIZE, ARTIFACTS, ENCHANTS,
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
PAGE_CHAR, PAGE_TAL, PAGE_INV, PAGE_SYS = 0, 1, 2, 3
PAGES = ["Personnage", "Talents", "Inventaire", "Système"]
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
    """Menu façon Zelda BotW (jeu en pause), quatre pages : Personnage · Talents · Inventaire · Système.
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
        self.hover_info = None
        self.hover_talent = None
        self.flash_node = None
        self.reset_rect = pygame.Rect(0, 0, 0, 0)
        self.ench_rects = []
        self.ench_hover = None
        self.sys_cursor = 0
        self.sys_entries = self.build_system()
        self.sys_sub = None            # "controls" : écran des commandes ouvert par-dessus le menu Système
        self.notes_scroll = 0.0
        self.notes = updates.load()
        self.sys_rects = [pygame.Rect(150, 160 + i * 58, 420, 48) for i in range(len(self.sys_entries))]

    def portrait_spot(self):
        """Position (conception) et zoom du héros en 3D selon la page ; None : le monde reste visible derrière."""
        if self.page == PAGE_INV:
            return 1010, 352, 1.3
        if self.page == PAGE_CHAR:
            return 230, 400, 1.05
        return None

    def goto(self, page):
        if page != self.page:
            self.page = page
            self.ctx = None
            self.sys_sub = None
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
                opts += [(f"Équiper · touche {ARTIFACT_KEYS[i]}", lambda s=s: w.assign_artifact(it, s))
                         for i, s in enumerate(ART_SLOTS)]
            elif w.player.can_equip(it):
                opts.append(("Équiper", lambda: w.bag_right_click(key)))
            opts.append(("Recycler", lambda: w.destroy_item(key)))
        else:
            opts.append(("Retirer", lambda: w.unequip(key)))
            if art:
                opts += [(f"Déplacer · touche {ARTIFACT_KEYS[i]}", lambda s=s: w.assign_artifact(it, s))
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
               ("Commandes", "Afficher les touches du jeu.", self.open_controls),
               ("Plein écran", "Basculer entre fenêtre et plein écran (F11).", w.game.toggle_fullscreen),
               ("Menu principal", "Sauvegarder, puis revenir à l'écran titre.", w.save_and_menu),
               ("Quitter le jeu", "Sauvegarder, puis fermer le jeu.", w.save_and_quit)]
        return es

    def open_controls(self):
        self.sys_sub = "controls"

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
            if self.sys_sub and self.page == PAGE_SYS:
                if e.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_BACKSPACE):
                    self.sys_sub = None
                return True
            if e.key == pygame.K_ESCAPE:
                w.close_modal()
            elif e.key in (pygame.K_i, pygame.K_c, pygame.K_n):
                page = {pygame.K_i: PAGE_INV, pygame.K_c: PAGE_CHAR, pygame.K_n: PAGE_TAL}[e.key]
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
        elif e.type == pygame.MOUSEWHEEL and self.page == PAGE_SYS and not self.sys_sub:
            self.notes_scroll = max(0.0, self.notes_scroll - e.y * 40)
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
        elif self.page == PAGE_TAL:
            self.talent_click(e)
        elif self.sys_sub:
            self.sys_sub = None
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
                    return
        if e.button == 1 and pygame.Rect(40, 240, 380, 340).collidepoint(e.pos):
            self.drag = e.pos[0]

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
        elif self.page == PAGE_TAL:
            ui.veil(surf, (4, 8, 12), 225)
        self.draw_frame(surf)
        if self.page == PAGE_INV:
            self.draw_inventory(surf, mouse)
        elif self.page == PAGE_CHAR:
            self.draw_character(surf, mouse)
        elif self.page == PAGE_TAL:
            self.draw_talents(surf, mouse)
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
            ui.circle(surf, WHITE if act else (120, 124, 122), (SCREEN_W // 2 + (i - (len(PAGES) - 1) / 2) * 9, 76),
                      2 if act else 1.5)
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
            hints = [("Répartir", "Clic"), ("+5", "Maj + clic"), ("Pivoter", "Glisser"), ("Retour", "Échap")]
        elif self.page == PAGE_TAL:
            hints = [("Apprendre", "Clic"), ("Retirer", "Clic droit"), ("Retour", "Échap")]
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
            ui.key_badge(surf, ARTIFACT_KEYS[ART_SLOTS.index(key)], (rc.right - 12, rc.bottom - 12), 11, SHEIKAH)
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
    ATTR_STYLE = {"force": ("fist", (236, 120, 84)), "dex": ("bolt", (130, 220, 120)),
                  "int": ("orb", (140, 160, 255)), "vit": ("heart", (236, 90, 120))}

    def attr_effect(self, a):
        p = self.world.player
        v = p.stats[a]
        prim = a == p.cls["primary"]
        if a == "force":
            return (f"+{v:.0f}% dégâts · " if prim else "") + f"+{v * 0.5:.0f} armure"
        if a == "dex":
            return (f"+{v:.0f}% dégâts · " if prim else "") + f"+{v * 0.05:.1f}% critique".replace(".", ",")
        if a == "int":
            return (f"+{v:.0f}% dégâts · " if prim else "") + f"+{v * 1.5:.0f} mana"
        return f"+{v * 5:.0f} points de vie"

    def draw_character(self, surf, mouse):
        from . import icons
        p = self.world.player
        s = p.stats
        cc = p.cls["color"]
        self.hover_info = None
        # ---- colonne héros
        left = ui.botw_box(surf, (40, 122, 380, 518), 90, FRAME, radius=4)
        ui.glow(surf, 230, 470, 150, ui.darker(cc, 0.28))
        med = (92, 182)
        need = xp_needed(p.level)
        frac = min(1.0, p.xp / need)
        ui.circle(surf, (8, 12, 14), med, 38)
        ui.circle(surf, (60, 64, 64), med, 38, 5)
        if frac > 0:
            pts = [med] + [(med[0] + math.cos(-math.pi / 2 + math.tau * frac * i / 40) * 40,
                            med[1] + math.sin(-math.pi / 2 + math.tau * frac * i / 40) * 40) for i in range(41)]
            ui.polygon(surf, (236, 200, 90), pts)
            ui.circle(surf, (8, 12, 14), med, 34)
        ui.circle(surf, ui.lighter(cc, 1.1), med, 34, 1)
        ui.draw_text(surf, "NIV.", (med[0], med[1] - 14), 10, SOFT, "bold", anchor="center", shadow=False)
        ui.draw_text(surf, str(p.level), (med[0], med[1] + 7), 28, WHITE, "title", anchor="center")
        if pygame.Rect(med[0] - 40, med[1] - 40, 80, 80).collidepoint(mouse):
            self.hover_info = [("Niveau " + str(p.level), BOTW_YELLOW, 17),
                               (f"Expérience : {p.xp} / {need}", WHITE, 14),
                               (f"{int(frac * 100)}% vers le niveau {p.level + 1}", SOFT, 13)]
        ui.draw_text(surf, p.name, (144, 150), 28, WHITE, "title")
        ui.draw_text(surf, p.cls["title"], (146, 186), 14, SOFT)
        chip_r = pygame.Rect(146, 208, ui.text_size(p.cls["name"], 13, "bold")[0] + 22, 22)
        ui.botw_box(surf, chip_r, 200, cc, radius=11, fill=ui.darker(cc, 0.25))
        ui.draw_text(surf, p.cls["name"], chip_r.center, 13, ui.lighter(cc, 1.3), "bold", anchor="center",
                     shadow=False)
        # records en bas de colonne
        recs = [("pillar", f"Étage {p.max_floor}", "Étage le plus haut atteint"),
                ("skull", f"{p.kills}", "Monstres vaincus"), ("heart", f"{p.deaths}", "Morts")]
        x = 64
        for kind, txt, tip in recs:
            w = ui.text_size(txt, 14, "bold")[0] + 44
            r = pygame.Rect(x, 596, w, 30)
            ui.botw_box(surf, r, 150, (100, 104, 102), radius=15)
            icons.glyph(surf, kind, (r.x + 16, r.centery), 8, SOFT)
            ui.draw_text(surf, txt, (r.x + 30, r.centery), 14, WHITE, "bold", anchor="midleft", shadow=False)
            if r.collidepoint(mouse):
                self.hover_info = [(tip, WHITE, 15)]
            x = r.right + 8
        # ---- colonne attributs
        ui.draw_text(surf, "Attributs", (446, 128), 22, WHITE, "title")
        if p.points:
            k = 0.55 + 0.45 * math.sin(self.t * 4)
            txt = f"{p.points} point(s) à répartir"
            r = pygame.Rect(0, 0, ui.text_size(txt, 13, "bold")[0] + 24, 26)
            r.topright = (826, 130)
            ui.botw_box(surf, r, 190, (int(60 + 60 * k), 200, int(90 + 40 * k)), radius=13, fill=(14, 40, 20))
            ui.draw_text(surf, txt, r.center, 13, (170, 250, 170), "bold", anchor="center", shadow=False)
        self.hover_attr = None
        for i, a in enumerate(ATTRS):
            kind, col = self.ATTR_STYLE[a]
            row = pygame.Rect(440, 166 + i * 70, 386, 62)
            hov = row.collidepoint(mouse)
            if hov:
                self.hover_attr = a
            prim = a == p.cls["primary"]
            ui.botw_box(surf, row, 175 if hov else 125, col if hov else ((150, 140, 100) if prim else (96, 100, 98)),
                        radius=6, fill=(18, 26, 30) if hov else (0, 0, 0))
            ui.rect(surf, col, (row.x + 1, row.y + 8, 3, row.h - 16), 0, 2)
            c = (row.x + 36, row.centery)
            ui.circle(surf, ui.darker(col, 0.3), c, 20)
            ui.circle(surf, col, c, 20, 2)
            icons.glyph(surf, kind, c, 11, ui.lighter(col, 1.3))
            ui.draw_text(surf, ATTR_NAMES[a], (row.x + 66, row.y + 10), 17, WHITE, "bold")
            if prim:
                tw = ui.text_size(ATTR_NAMES[a], 17, "bold")[0]
                ui.draw_text(surf, "PRINCIPALE", (row.x + 74 + tw, row.y + 14), 10, BOTW_YELLOW, "bold", shadow=False)
            ui.draw_text(surf, self.attr_effect(a), (row.x + 66, row.y + 35), 13, SOFT, shadow=False)
            ui.draw_text(surf, str(int(s[a])), (row.right - (58 if p.points else 20), row.centery), 26, WHITE,
                         "bold", anchor="midright")
            self.plus[a] = pygame.Rect(row.right - 44, row.centery - 15, 30, 30)
            if p.points:
                rc = self.plus[a]
                h2 = rc.collidepoint(mouse)
                ui.circle(surf, (40, 120, 64) if h2 else (18, 60, 32), rc.center, 15)
                ui.circle(surf, UP, rc.center, 15, 1)
                ui.draw_text(surf, "+", rc.center, 21, WHITE, "bold", anchor="center", shadow=False)
        # grandes tuiles
        dr = p.damage_reduction() * 100
        tiles = [("sword", "Attaque", f"{int(p.dps_estimate())}", "dégâts / seconde", (236, 140, 90)),
                 ("shield", "Défense", f"{int(s['armor'])}", f"-{dr:.0f}% de dégâts subis", (170, 180, 200)),
                 ("heart", "Vie", f"{int(p.hp)}", f"sur {int(s['max_hp'])}", (236, 80, 100)),
                 ("drop", "Mana", f"{int(p.mana)}", f"sur {int(s['max_mana'])}", (100, 150, 255))]
        for i, (kind, label, val, sub, col) in enumerate(tiles):
            r = pygame.Rect(440 + (i % 2) * 196, 454 + (i // 2) * 94, 190, 86)
            ui.botw_box(surf, r, 150, ui.darker(col, 0.7), radius=6)
            icons.glyph(surf, kind, (r.x + 24, r.y + 26), 11, col)
            ui.draw_text(surf, label, (r.x + 42, r.y + 17), 14, SOFT, "bold", shadow=False)
            ui.draw_text(surf, val, (r.x + 18, r.y + 38), 28, WHITE, "bold")
            ui.draw_text(surf, sub, (r.right - 12, r.bottom - 10), 12, SOFT, anchor="bottomright", shadow=False)
        # ---- colonne statistiques + compétences
        box = ui.botw_box(surf, (846, 122, 394, 518), 150, FRAME, radius=4)
        ui.draw_text(surf, "Statistiques", (box.centerx, 134), 20, WHITE, "title", anchor="midtop")
        rows = [
            ("sword", "Dégâts de l'arme", f"{int(s['dmg_min'])} - {int(s['dmg_max'])}", None,
             "Dégâts de base de l'arme équipée."),
            ("fist", "Multiplicateur", f"x{s['dmg_mult']:.2f}", None,
             "Bonus de l'attribut principal et des bonus de dégâts."),
            ("eye", "Coup critique", f"{s['crit']:.1f}%", s["crit"] / 60,
             f"Les critiques infligent x{s['crit_mult']:.2f} dégâts."),
            ("bolt", "Vitesse d'attaque", f"+{s['atk_speed']:.0f}%", s["atk_speed"] / 60, None),
            ("drop", "Vol de vie", f"{s['lifesteal']:.0f}%", s["lifesteal"] / 15, None),
            ("orb", "Régén. de mana", f"{s['mana_regen']:.1f}/s", None, None),
            ("clock", "Recharge des sorts", f"-{s['cdr']:.0f}%", s["cdr"] / 50, "Maximum : 50%."),
            ("boot", "Déplacement", f"+{s['move_speed']:.0f}%", s["move_speed"] / 40, None),
            ("heart", "Potion · roulade", f"{p.potion_total:.0f} s · {p.roll_total:.1f} s", None,
             "Temps de recharge de la potion (F) et de la roulade (Espace)."),
            ("star", "Or trouvé", f"+{s['gold_find']:.0f}%", None, None),
        ]
        y = 170
        for i, (kind, label, val, frac_, tip) in enumerate(rows):
            r = pygame.Rect(box.x + 12, y - 4, box.w - 24, 28)
            hov = r.collidepoint(mouse)
            if i % 2 == 0 or hov:
                ui.rect(surf, (40, 60, 70, 110 if hov else 60), r, 0, 4)
            icons.glyph(surf, kind, (r.x + 16, r.centery), 7, (170, 200, 210))
            ui.draw_text(surf, label, (r.x + 32, r.centery), 14, SOFT, anchor="midleft", shadow=False)
            ui.draw_text(surf, val, (r.right - 10, r.centery), 14, WHITE, "bold", anchor="midright", shadow=False)
            if frac_ is not None:
                bar = pygame.Rect(r.x + 32, r.bottom - 3, 140, 2)
                ui.rect(surf, (60, 64, 66), bar)
                ui.rect(surf, SHEIKAH, (bar.x, bar.y, max(1, bar.w * min(1.0, frac_)), bar.h))
            if hov and tip:
                self.hover_info = [(label, WHITE, 16), (tip, SOFT, 14)]
            y += 31
        # compétences : médaillons
        ui.draw_text(surf, "Compétences", (box.centerx, 488), 18, WHITE, "title", anchor="midtop")
        a = p.cls["attack"]
        entries = [(None, a["name"], a.get("color", cc), "LMB", True,
                    f"Attaque de base · {int(a['mult'] * 100)}% de l'arme · clic gauche maintenu", None)]
        for i, sid in enumerate(p.spells):
            sp = SPELLS[sid]
            entries.append((sid, sp["name"], sp["color"], str(i + 1), p.spell_unlocked(sid), sp["desc"], sp))
        n = len(entries)
        for i, (sid, name, col, key, ok, desc, sp) in enumerate(entries):
            c = (box.x + 42 + i * (box.w - 84) / (n - 1), 556)
            icons.spell_icon(surf, sid, c, 25, col, locked=not ok, attack_cls=p.cls_id if sid is None else None)
            ui.key_badge(surf, key, (c[0], c[1] + 27), 10)
            if not ok:
                ui.draw_text(surf, f"Niv {sp['level']}", (c[0], c[1] + 46), 11, TEXT_DIM, "bold", anchor="center",
                             shadow=False)
            if math.hypot(mouse[0] - c[0], mouse[1] - c[1]) < 27:
                info = [(name, ui.lighter(col, 1.2), 17)]
                if sp:
                    info.append((f"Mana {sp['mana']}  ·  Recharge {sp['cd']} s  ·  Niveau {sp['level']}", SHEIKAH, 13))
                info += [(l, SOFT, 14) for l in ui.wrap(desc, 14, 300)]
                self.hover_info = info
        if p.anima:
            txt = "  ·  ".join(f"{ANIMA_POWERS[k]['name']} x{v}" for k, v in list(p.anima.items())[:3])
            ui.draw_text(surf, "Anima : " + txt, (box.centerx, 620), 12, SHEIKAH, "bold", anchor="center",
                         shadow=False)

    # ------------------------------------------------------------------ talents
    TAL_COL_X = (56, 450, 844)
    TAL_W = 380
    TAL_Y = (262, 356, 450, 548)

    def talent_nodes(self):
        from . import talents
        p = self.world.player
        res = []
        for bi, br in enumerate(talents.TREES[p.cls_id]):
            for t in br["talents"]:
                c = (self.TAL_COL_X[bi] + 58, self.TAL_Y[t["tier"]])
                res.append((t, br, c))
        return res

    def talent_click(self, e):
        from . import talents
        w = self.world
        p = w.player
        if self.reset_rect.collidepoint(e.pos) and e.button == 1:
            if w.reset_talents():
                self._preview_key = None
            return
        for t, br, c in self.talent_nodes():
            if math.hypot(e.pos[0] - c[0], e.pos[1] - c[1]) > 32:
                continue
            if e.button == 1:
                ok, why = talents.can_learn(p.talents, p.level, t["id"])
                if ok:
                    p.talents[t["id"]] = p.talents.get(t["id"], 0) + 1
                    p.recompute()
                    self.flash_node = (t["id"], self.t)
                    sfx.play("levelup", 0.35)
                else:
                    w.message(why, RED, 3)
                    sfx.play("click", 0.4)
            elif e.button == 3:
                if w.is_tower:
                    w.message("Les points de talent se retirent au campement.", RED, 3)
                elif talents.can_unlearn(p.talents, t["id"]):
                    p.talents[t["id"]] -= 1
                    if not p.talents[t["id"]]:
                        del p.talents[t["id"]]
                    p.recompute()
                    sfx.play("click")
                else:
                    w.message("Retirez d'abord les points des paliers supérieurs.", RED, 3)
            return

    def draw_talents(self, surf, mouse):
        from . import icons, talents
        p = self.world.player
        ranks = p.talents
        free = p.talent_points
        self.hover_talent = None
        # bandeau d'information
        ui.draw_text(surf, f"Arbre du {p.cls['name']}", (56, 130), 22, WHITE, "title")
        txt = f"{free} point(s) disponible(s)" if free else "Aucun point disponible"
        r = pygame.Rect(0, 0, ui.text_size(txt, 14, "bold")[0] + 30, 28)
        r.midleft = (330, 146)
        k = 0.6 + 0.4 * math.sin(self.t * 4) if free else 0.0
        ui.botw_box(surf, r, 190, (int(180 + 60 * k), 170, 80) if free else (100, 100, 96), radius=14,
                    fill=(46, 36, 10) if free else (0, 0, 0))
        ui.draw_text(surf, txt, r.center, 14, (255, 222, 120) if free else SOFT, "bold", anchor="center", shadow=False)
        ui.draw_text(surf, f"{talents.spent(ranks)} / {p.talent_points_total} dépensés · 1 point tous les 2 niveaux",
                     (r.right + 16, 146), 13, SOFT, anchor="midleft", shadow=False)
        cost = talents.reset_cost(p.level)
        self.reset_rect = pygame.Rect(1030, 130, 194, 32)
        can_reset = bool(ranks) and not self.world.is_tower
        hov = self.reset_rect.collidepoint(mouse) and can_reset
        ui.botw_box(surf, self.reset_rect, 200 if hov else 130, SHEIKAH if hov else (100, 102, 100),
                    radius=16, fill=(16, 44, 56) if hov else (0, 0, 0))
        ui.draw_text(surf, f"Réinitialiser · {cost} or" if not self.world.is_tower else "Réinitialiser (campement)",
                     self.reset_rect.center, 13, WHITE if can_reset else TEXT_DIM, "bold", anchor="center",
                     shadow=False)
        for bi, br in enumerate(talents.TREES[p.cls_id]):
            col = br["color"]
            x0 = self.TAL_COL_X[bi]
            spent_b = talents.branch_spent(ranks, p.cls_id, bi)
            panel = ui.botw_box(surf, (x0, 176, self.TAL_W, 464), 150, ui.darker(col, 0.6), radius=6)
            ui.rect(surf, (*ui.darker(col, 0.35), 150), (x0 + 1, 177, self.TAL_W - 2, 52), 0, 5)
            hc = (x0 + 34, 203)
            ui.circle(surf, ui.darker(col, 0.3), hc, 19)
            ui.circle(surf, col, hc, 19, 2)
            icons.glyph(surf, br["icon"], hc, 10, ui.lighter(col, 1.3))
            ui.draw_text(surf, br["name"], (x0 + 62, 203), 21, WHITE, "title", anchor="midleft")
            ui.draw_text(surf, f"{spent_b} pt{'s' if spent_b > 1 else ''}", (x0 + self.TAL_W - 16, 203), 15,
                         ui.lighter(col, 1.2), "bold", anchor="midright")
            # chemin reliant les paliers
            nx = x0 + 58
            for tier in range(3):
                y1, y2 = self.TAL_Y[tier] + 31, self.TAL_Y[tier + 1] - 31
                need = (tier + 1) * talents.TIER_COST
                fill = max(0.0, min(1.0, (spent_b - tier * talents.TIER_COST) / talents.TIER_COST))
                ui.rect(surf, (50, 54, 56), (nx - 2, y1, 4, y2 - y1))
                if fill > 0:
                    ui.rect(surf, col, (nx - 2, y1, 4, (y2 - y1) * fill))
                    if fill >= 1:
                        ui.glow(surf, nx, (y1 + y2) / 2, 18, ui.darker(col, 0.4))
                ui.draw_text(surf, f"{need} pts", (nx + 8, (y1 + y2) / 2), 10, TEXT_DIM if fill < 1 else SOFT,
                             "bold", anchor="midleft", shadow=False)
            for t in br["talents"]:
                c = (nx, self.TAL_Y[t["tier"]])
                rk = ranks.get(t["id"], 0)
                ok, _ = talents.can_learn(ranks, p.level, t["id"])
                unlocked = spent_b >= t["tier"] * talents.TIER_COST
                state = "max" if rk >= t["max"] else ("some" if rk else ("open" if unlocked else "locked"))
                fl = getattr(self, "flash_node", None)
                if fl and fl[0] == t["id"] and self.t - fl[1] < 0.5:
                    ui.glow(surf, c[0], c[1], 60 * (1 - (self.t - fl[1]) * 2) + 20, col)
                icons.talent_icon(surf, t, c, 27, col, state)
                if ok and free:
                    ui.circle(surf, (255, 222, 120), c, 31 + 1.5 * math.sin(self.t * 5), 1)
                pip = f"{rk}/{t['max']}"
                pr = pygame.Rect(0, 0, 34, 18)
                pr.center = (c[0] + 22, c[1] + 22)
                ui.botw_box(surf, pr, 220, col if rk else (90, 92, 92), radius=9, fill=(8, 10, 12))
                ui.draw_text(surf, pip, pr.center, 11, WHITE if rk else SOFT, "bold", anchor="center", shadow=False)
                tx = x0 + 104
                name_col = WHITE if unlocked else (130, 134, 134)
                ui.draw_text(surf, t["name"], (tx, c[1] - 26), 16, name_col, "bold")
                desc = talents.describe(t["id"], max(1, rk))
                lines = ui.wrap(desc, 13, self.TAL_W - 118)
                for li, line in enumerate(lines[:3]):
                    ui.draw_text(surf, line, (tx, c[1] - 4 + li * 16), 13,
                                 SOFT if unlocked else (110, 112, 112), shadow=False)
                area = pygame.Rect(x0 + 20, c[1] - 36, self.TAL_W - 30, 74)
                if area.collidepoint(mouse):
                    self.hover_talent = (t, br, rk, ok, unlocked)

    def talent_tooltip(self, surf):
        from . import talents
        t, br, rk, ok, unlocked = self.hover_talent
        col = br["color"]
        lines = [(t["name"], ui.lighter(col, 1.2), 17),
                 (f"{br['name']} · palier {t['tier'] + 1}" + (" · talent ultime" if t["tier"] == 3 else ""), SOFT, 13),
                 (f"Rang {rk} / {t['max']}", WHITE, 14)]
        if rk:
            lines.append(("Actuel : " + talents.describe(t["id"], rk), WHITE, 14))
        if rk < t["max"]:
            lines.append(("Rang suivant : " + talents.describe(t["id"], rk + 1), UP, 14))
            if not unlocked:
                lines.append((f"Requiert {t['tier'] * talents.TIER_COST} points dans {br['name']}", DOWN, 13))
            elif ok:
                lines.append(("Clic : apprendre", BOTW_YELLOW, 13))
            elif self.world.player.talent_points <= 0:
                lines.append(("Aucun point de talent disponible", DOWN, 13))
        if rk:
            lines.append(("Clic droit : retirer un point (au campement)", SOFT, 12))
        ui.draw_tooltip_lines(surf, lines, ui.mouse_pos(), col)

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
        self.draw_notes(surf)
        if self.sys_sub == "controls":
            self.draw_controls(surf)

    def draw_notes(self, surf):
        """Notes de mise à jour (data/updates/*.json), la plus récente en haut ; molette pour défiler."""
        box = ui.botw_box(surf, (660, 140, 470, 470), 170, FRAME, radius=4)
        ui.draw_text(surf, "Notes de mise à jour", (box.centerx, box.y + 16), 20, WHITE, "title", anchor="midtop")
        ui.rect(surf, (110, 112, 108), (box.x + 24, box.y + 52, box.w - 48, 1))
        view = pygame.Rect(box.x + 16, box.y + 60, box.w - 32, box.h - 72)
        if not self.notes:
            ui.draw_text(surf, "Aucune note (dossier data/updates).", view.center, 15, SOFT, anchor="center")
            return
        # contenu mis en page d'abord (pour connaître sa hauteur et borner le défilement)
        items, y = [], 0
        tw = view.w - 28
        for u in self.notes:
            items.append(("ver", u, y))
            y += 30
            if u.get("title"):
                items.append(("title", u["title"], y))
                y += len(ui.wrap(u["title"], 15, tw, "bold")) * 20 + 4
            for sec in u.get("sections", []):
                items.append(("sec", sec.get("name", ""), y))
                y += 24
                for n in sec.get("notes", []):
                    lines = ui.wrap(n, 14, tw - 16)
                    items.append(("note", lines, y))
                    y += len(lines) * 19 + 5
            y += 18
        total = y
        self.notes_scroll = min(self.notes_scroll, max(0.0, total - view.h))
        off = view.y + 4 - self.notes_scroll
        clip = surf.get_clip()
        surf.set_clip(ui.R(view))
        for kind, v, yy in items:
            y0 = off + yy
            if y0 > view.bottom or y0 < view.y - 200:
                continue
            x = view.x + 10
            if kind == "ver":
                ui.rect(surf, (40, 60, 70, 110), (view.x, y0 - 2, view.w, 26), 0, 4)
                ui.draw_text(surf, f"Version {v['version']}", (x, y0 + 11), 16, BOTW_YELLOW, "bold", anchor="midleft")
                if v.get("date"):
                    ui.draw_text(surf, v["date"], (view.right - 10, y0 + 11), 13, SOFT, anchor="midright")
            elif kind == "title":
                ui.draw_wrapped(surf, v, x, y0, tw, 15, WHITE, kind="bold")
            elif kind == "sec":
                ui.draw_text(surf, v, (x, y0 + 2), 14, (150, 200, 220), "bold")
            else:
                ui.circle(surf, SOFT, (x + 5, y0 + 9), 2)
                for k, line in enumerate(v):
                    ui.draw_text(surf, line, (x + 16, y0 + k * 19), 14, SOFT)
        surf.set_clip(clip)
        if total > view.h:          # barre de défilement
            k = view.h / total
            bar_h = max(30, view.h * k)
            by = view.y + (view.h - bar_h) * (self.notes_scroll / max(1, total - view.h))
            ui.rect(surf, (255, 255, 255, 40), (view.right + 4, view.y, 3, view.h), 0, 2)
            ui.rect(surf, (255, 255, 255, 150), (view.right + 4, by, 3, bar_h), 0, 2)

    def draw_controls(self, surf):
        ui.veil(surf, (0, 0, 0), 200)
        box = ui.botw_box(surf, (SCREEN_W // 2 - 330, 92, 660, 576), 255, FRAME, radius=4, fill=(12, 16, 20))
        ui.draw_text(surf, "Commandes", (box.centerx, box.y + 16), 22, WHITE, "title", anchor="midtop")
        ui.rect(surf, (110, 112, 108), (box.x + 24, box.y + 54, box.w - 48, 1))
        controls = [
            ("Clic gauche au sol", "Se déplacer (maintenu : suivre le curseur)"),
            ("Clic gauche sur un ennemi", "Attaquer (s'approche au besoin)"), ("Maj + clic gauche", "Attaquer sur place"),
            ("ZQSD / WASD / flèches", "Se déplacer au clavier"),
            ("1 2 3 4 · clic droit", "Sorts (clic droit = sort 1)"), ("Espace", "Roulade d'esquive"),
            ("R · T · G", "Artefacts"), ("F", "Potion (à recharge)"), ("E · clic", "Interagir / parler / briser un mur fissuré"),
            ("I · C · N", "Inventaire · Personnage · Talents"), ("Tab", "Grande carte · page suivante (menu)"),
            ("← →", "Changer de page du menu"),
            ("Échap", "Menu Système / fermer"), ("F11", "Plein écran"),
        ]
        y = box.y + 68
        for i, (k, v) in enumerate(controls):
            if i % 2 == 0:
                ui.rect(surf, (40, 60, 70, 70), (box.x + 16, y - 3, box.w - 32, 29), 0, 4)
            ui.draw_text(surf, k, (box.x + 30, y + 11), 14, BOTW_YELLOW, "bold", anchor="midleft")
            ui.draw_text(surf, v, (box.right - 30, y + 11), 14, SOFT, anchor="midright")
            y += 31
        ui.draw_text(surf, "Échap ou clic : retour", (box.centerx, box.bottom - 16), 13, SOFT, anchor="midbottom")

    def draw_tooltips(self, surf):
        if self.page == PAGE_CHAR and self.hover_info:
            ui.draw_tooltip_lines(surf, self.hover_info, ui.mouse_pos())
        if self.page == PAGE_CHAR and self.hover_attr and not self.hover_info:
            ui.draw_tooltip_lines(surf, [(ATTR_NAMES[self.hover_attr], WHITE, 16),
                                         (ATTR_DESC[self.hover_attr], SOFT, 14)], ui.mouse_pos())
        if self.page == PAGE_TAL and self.hover_talent:
            self.talent_tooltip(surf)
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
