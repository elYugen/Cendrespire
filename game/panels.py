"""Menus en jeu, style tablette Sheikah (Zelda BotW) : équipement et personnage (plein écran, héros en 3D),
enchantements, marchand, forge, portail, pouvoirs d'anima, pause et mort.
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
FILTERS = [("Tout", None), ("Armes", {"arme"}), ("Armures", {"casque", "torse", "gants", "bottes"}),
           ("Bijoux", {"amulette", "anneau"}), ("Artefacts", {"artefact"})]


class MenuScreen(Panel):
    """Menu façon Zelda BotW (jeu en pause) : Équipement (héros en 3D) et Personnage."""
    modal = True
    TABS = ["Équipement", "Personnage"]

    def __init__(self, world, tab=0):
        super().__init__(world, (0, 0, SCREEN_W, SCREEN_H))
        self.tab = tab
        self.t = 0.0
        self.filter = 0
        self.selected = None
        self.hover = None
        self._preview_key = None
        self._preview = None
        self.tab_rects = [pygame.Rect(SCREEN_W // 2 - 250 + i * 260, 18, 240, 40) for i in range(2)]
        self.filter_rects = [pygame.Rect(58 + i * 118, 110, 110, 30) for i in range(len(FILTERS))]
        cell = 74
        self.bag_rects = [pygame.Rect(62 + (i % 8) * (cell + 4), 156 + (i // 8) * (cell + 4), cell, cell)
                          for i in range(BAG_SIZE)]
        S = 62
        self.slot_rects = {
            "arme": pygame.Rect(744, 100, S, S), "casque": pygame.Rect(744, 172, S, S),
            "torse": pygame.Rect(744, 244, S, S), "gants": pygame.Rect(744, 316, S, S),
            "bottes": pygame.Rect(1154, 100, S, S), "amulette": pygame.Rect(1154, 172, S, S),
            "anneau": pygame.Rect(1154, 244, S, S),
        }
        for i, s in enumerate(ART_SLOTS):
            self.slot_rects[s] = pygame.Rect(885 + i * 72, 400, 56, 56)
        self.plus = {a: pygame.Rect(400, 336 + i * 46, 30, 30) for i, a in enumerate(ATTRS)}
        self.hover_attr = None
        self.ench_rects = []
        self.ench_hover = None

    def portrait_spot(self):
        """Position (conception) et zoom du héros en 3D selon l'onglet."""
        return (985, 250, 1.0) if self.tab == 0 else (150, 200, 0.8)

    # ------------------------------------------------------------------ aides
    def visible_items(self):
        inv = self.world.player.inventory
        allowed = FILTERS[self.filter][1]
        return [(i, it) for i, it in enumerate(inv) if allowed is None or it["slot"] in allowed]

    def hit_test(self, pos):
        p = self.world.player
        for slot, rc in self.slot_rects.items():
            if rc.collidepoint(pos):
                return ("equip", slot, p.equipment[slot])
        for (idx, it), rc in zip(self.visible_items(), self.bag_rects):
            if rc.collidepoint(pos):
                return ("bag", idx, it)
        return None

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

    # ------------------------------------------------------------------ événements
    def handle_event(self, e):
        w = self.world
        p = w.player
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                w.close_modal()
            elif e.key == pygame.K_i:
                if self.tab == 0:
                    w.close_modal()
                else:
                    self.tab = 0
            elif e.key == pygame.K_c:
                if self.tab == 1:
                    w.close_modal()
                else:
                    self.tab = 1
            elif e.key in (pygame.K_TAB, pygame.K_RIGHT, pygame.K_LEFT):
                self.tab = 1 - self.tab
                sfx.play("click")
            elif e.key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self.tab == 0:
                hit = self.hit_test(ui.mouse_pos())
                if hit and hit[0] == "bag":
                    w.destroy_item(hit[1])
            return True
        if e.type != pygame.MOUSEBUTTONDOWN:
            return True
        for i, rc in enumerate(self.tab_rects):
            if rc.collidepoint(e.pos) and e.button == 1:
                self.tab = i
                sfx.play("click")
                return True
        if self.tab == 0:
            for i, rc in enumerate(self.filter_rects):
                if rc.collidepoint(e.pos) and e.button == 1:
                    self.filter = i
                    sfx.play("click")
                    return True
            for rc, item, si, eid in self.ench_rects:
                if rc.collidepoint(e.pos) and e.button == 1:
                    w.enchant(item, si, eid)
                    self._preview_key = None
                    return True
            hit = self.hit_test(e.pos)
            if hit and hit[2]:
                kind, key, item = hit
                if e.button == 1:
                    self.selected = item
                    sfx.play("click")
                elif e.button == 3:
                    if kind == "bag":
                        w.bag_right_click(key)
                    else:
                        w.unequip(key)
                    self._preview_key = None
        else:
            if e.button == 1 and p.points > 0:
                for a, rc in self.plus.items():
                    if rc.collidepoint(e.pos):
                        n = min(p.points, 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
                        p.alloc[a] += n
                        p.points -= n
                        p.recompute()
                        sfx.play("click")
        return True

    def update(self, dt):
        self.t += dt

    # ------------------------------------------------------------------ rendu
    def draw(self, surf):
        mouse = ui.mouse_pos()
        for i, (name, rc) in enumerate(zip(self.TABS, self.tab_rects)):
            active = i == self.tab
            ui.draw_text(surf, name, rc.center, 26 if active else 21, WHITE if active else (130, 136, 136), "title",
                         anchor="center")
            if active:
                ui.line(surf, SHEIKAH, (rc.x + 30, rc.bottom), (rc.right - 30, rc.bottom), 2)
        cx = SCREEN_W // 2
        for d in (-1, 1):
            x = cx + d * 290
            ui.polygon(surf, (170, 176, 176), [(x, 30), (x, 46), (x + d * 10, 38)])
        if self.tab == 0:
            self.draw_equipment(surf, mouse)
        else:
            self.draw_character(surf, mouse)
        ui.draw_text(surf, "[I] Équipement   [C] Personnage   [Tab] Onglet   [Échap] Fermer",
                     (SCREEN_W - 30, SCREEN_H - 10), 13, (150, 160, 160), anchor="bottomright")
        msgs = [m for m in self.world.messages if m[2] > 0]
        if msgs:
            ui.draw_text(surf, msgs[-1][0], (30, SCREEN_H - 10), 14, msgs[-1][1], "bold", anchor="bottomleft")

    def draw_equipment(self, surf, mouse):
        p = self.world.player
        t = self.t
        ui.botw_box(surf, (40, 76, 660, 500), 150, (90, 94, 92), radius=14)
        ui.draw_text(surf, f"Sac   {len(p.inventory)}/{BAG_SIZE}", (62, 84), 17, WHITE, "bold")
        ui.draw_text(surf, f"{p.gold} or", (680, 84), 17, GOLD_BRIGHT, "bold", anchor="topright")
        for i, ((name, _), rc) in enumerate(zip(FILTERS, self.filter_rects)):
            act = i == self.filter
            ui.botw_box(surf, rc, 200 if act else 120, SHEIKAH if act else (110, 112, 110), radius=15,
                        fill=(15, 45, 58) if act else (0, 0, 0))
            ui.draw_text(surf, name, rc.center, 14, WHITE if act else SOFT, anchor="center", shadow=False)
        self.hover = None
        items = self.visible_items()
        for n, rc in enumerate(self.bag_rects):
            it = items[n][1] if n < len(items) else None
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = it
            item_slot(surf, rc, it, t, it is not None and it is self.selected, hov, it is None or p.can_equip(it))
        # héros (dessiné en 3D derrière ce panneau) et équipement
        ui.botw_box(surf, (720, 76, 520, 500), 70, (90, 94, 92), radius=14)
        ui.draw_text(surf, p.name, (985, 84), 22, WHITE, "title", anchor="midtop")
        for slot, rc in self.slot_rects.items():
            it = p.equipment[slot]
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = it
            item_slot(surf, rc, it, t, it is not None and it is self.selected, hov, True, SLOT_NAMES[slot])
        for i, s in enumerate(ART_SLOTS):
            rc = self.slot_rects[s]
            ui.key_badge(surf, "RTG"[i], (rc.centerx, rc.bottom), 10)
        focus = self.hover or self.selected
        delta = self.preview(focus) if focus else None
        s = p.stats
        rows = [(attack_icon, "Attaque", p.dps_estimate(), 0), (shield_icon, "Défense", s["armor"], 1),
                (heart_icon, "Vie", s["max_hp"], 2)]
        for i, (icon, label, val, di) in enumerate(rows):
            x, y = 800 + i * 140, 484
            ui.botw_box(surf, (x - 50, y, 128, 62), 190, (120, 122, 118), radius=10)
            icon(surf, x - 26, y + 22)
            ui.draw_text(surf, str(int(val)), (x - 6, y + 6), 24, WHITE, "bold")
            ui.draw_text(surf, label, (x - 6, y + 38), 12, SOFT, shadow=False)
            if delta and abs(delta[di]) >= 1:
                up = delta[di] > 0
                col = UP if up else DOWN
                ax, ay = x + 58, y + 20
                pts = [(ax, ay - 8), (ax + 7, ay + 1), (ax - 7, ay + 1)] if up else [(ax, ay + 8), (ax + 7, ay - 1),
                                                                                    (ax - 7, ay - 1)]
                ui.polygon(surf, col, pts)
                ui.draw_text(surf, f"{'+' if up else ''}{int(delta[di])}", (ax, ay + 12), 13, col, "bold",
                             anchor="midtop")
        self.draw_details(surf, focus, mouse)

    def draw_details(self, surf, it, mouse):
        p = self.world.player
        box = ui.botw_box(surf, (40, 588, 1200, 108), 205, (120, 122, 118), radius=14)
        self.ench_rects = []
        self.ench_hover = None
        if not it:
            ui.draw_text(surf, "Survolez ou sélectionnez un objet pour afficher ses détails.", box.center, 16, SOFT,
                         anchor="center")
            return
        col = RARITY_COLORS[it["rarity"]]
        item_slot(surf, (box.x + 14, box.y + 16, 76, 76), it, self.t)
        name = it["name"] + (f" +{it['upgrade']}" if it.get("upgrade") else "")
        ui.draw_text(surf, name, (box.x + 104, box.y + 12), 21, col, "title_bold")
        sub = f"{SLOT_NAMES[it['slot']]} {RARITY_NAMES[it['rarity']].lower()}  ·  Niveau d'objet {it['ilvl']}"
        if it["slot"] == "arme":
            sub += f"  ·  {CLASSES[it['wclass']]['name']}"
        ui.draw_text(surf, sub, (box.x + 104, box.y + 42), 14, SOFT if p.can_equip(it) else DOWN)
        if it["slot"] == "artefact":
            ui.draw_wrapped(surf, art_desc(it), box.x + 104, box.y + 64, 600, 15, WHITE)
            ui.draw_text(surf, f"Recharge {ARTIFACTS[it['art']]['cd']} s", (box.x + 730, box.y + 16), 15, SHEIKAH, "bold")
        else:
            st = item_stats(it)
            main = f"Dégâts {int(st['dmg'][0])}-{int(st['dmg'][1])}" if "dmg" in st else (
                f"Armure {st['armor']}" if "armor" in st else "")
            if main:
                ui.draw_text(surf, main, (box.x + 104, box.y + 66), 17, WHITE, "bold")
            affs = [AFFIX_DEF[k][0].format(v=v) for k, v in st["affixes"].items()]
            for i, a in enumerate(affs):
                ui.draw_text(surf, a, (box.x + 390 + (i // 3) * 220, box.y + 14 + (i % 3) * 25), 14, (140, 175, 255))
            self.draw_enchants(surf, it, box, mouse)
        equipped = it in p.equipment.values()
        hint = "[Clic droit] Retirer" if equipped else "[Clic droit] Équiper   [Suppr] Recycler"
        ui.draw_text(surf, hint, (box.x + 104, box.bottom - 8), 12, (150, 156, 156), anchor="bottomleft")
        ui.draw_text(surf, f"Valeur {item_value(it)} or", (box.x + 390, box.bottom - 8), 12, GOLD, anchor="bottomleft")

    def draw_enchants(self, surf, it, box, mouse):
        """Emplacements d'enchantement : 3 choix par emplacement, puis amélioration jusqu'au niveau III."""
        p = self.world.player
        slots = it.get("ench", [])
        x0 = box.right - 16 - len(slots) * 128
        ui.draw_text(surf, f"Points d'enchantement : {p.ench_points}", (box.right - 16, box.y + 8), 13, ENCH_COL,
                     "bold", anchor="topright")
        if not slots:
            ui.draw_text(surf, "Aucun emplacement d'enchantement", (box.right - 16, box.y + 50), 13, (130, 134, 134),
                         anchor="topright")
            return
        for si, e in enumerate(slots):
            sx = x0 + si * 128
            sy = box.y + 34
            ui.botw_box(surf, (sx, sy, 118, 64), 120, (100, 90, 130), radius=10)
            if e["id"]:
                d = ENCHANTS[e["id"]]
                c = (sx + 24, sy + 32)
                r = pygame.Rect(c[0] - 16, c[1] - 16, 32, 32)
                hov = r.collidepoint(mouse)
                ui.circle(surf, (60, 34, 90), c, 16)
                ui.circle(surf, SHEIKAH if hov else ENCH_COL, c, 16, 2)
                ui.draw_text(surf, d["name"][:2], c, 13, WHITE, "bold", anchor="center", shadow=False)
                ui.draw_text(surf, d["name"], (sx + 46, sy + 12), 12, WHITE, "bold")
                for lv in range(3):
                    ui.circle(surf, ENCH_COL if lv < e["lvl"] else (60, 56, 70), (sx + 52 + lv * 14, sy + 40), 4.5)
                if e["lvl"] < 3:
                    self.ench_rects.append((r, it, si, e["id"]))
                if hov:
                    self.ench_hover = (it, si, e["id"])
            else:
                for ci, eid in enumerate(e["choices"]):
                    c = (sx + 20 + ci * 39, sy + 32)
                    r = pygame.Rect(c[0] - 15, c[1] - 15, 30, 30)
                    hov = r.collidepoint(mouse)
                    ui.circle(surf, (40, 26, 60), c, 15)
                    ui.circle(surf, SHEIKAH if hov else (140, 110, 190), c, 15, 2 if hov else 1)
                    ui.draw_text(surf, ENCHANTS[eid]["name"][:2], c, 12, WHITE, "bold", anchor="center", shadow=False)
                    self.ench_rects.append((r, it, si, eid))
                    if hov:
                        self.ench_hover = (it, si, eid)

    def draw_character(self, surf, mouse):
        p = self.world.player
        s = p.stats
        t = self.t
        col = ui.botw_box(surf, (40, 76, 420, 618), 110, (90, 94, 92), radius=14)
        ui.draw_text(surf, p.name, (250, 106), 28, WHITE, "title")
        ui.draw_text(surf, p.cls["title"], (252, 144), 15, SOFT)
        ui.draw_text(surf, f"{p.cls['name']}  ·  Niveau {p.level}", (252, 168), 16, BOTW_YELLOW, "bold")
        need = xp_needed(p.level)
        bar = pygame.Rect(252, 200, 180, 8)
        ui.rect(surf, (0, 0, 0), bar.inflate(2, 2), 0, 4)
        ui.rect(surf, (236, 200, 90), (bar.x, bar.y, max(1, bar.w * min(1, p.xp / need)), bar.h), 0, 4)
        ui.draw_text(surf, f"{p.xp} / {need} XP", (bar.x, bar.bottom + 4), 12, SOFT, shadow=False)
        ui.draw_text(surf, f"Points d'enchantement : {p.ench_points}", (252, 236), 13, ENCH_COL, "bold")
        ui.draw_text(surf, "Caractéristiques", (64, 296), 19, WHITE, "title")
        if p.points:
            k = 0.6 + 0.4 * math.sin(t * 4)
            ui.draw_text(surf, f"{p.points} point(s) à répartir", (436, 300), 14,
                         (int(110 * k + 60), 235, int(120 * k + 40)), "bold", anchor="topright")
        self.hover_attr = None
        for i, a in enumerate(ATTRS):
            y = 336 + i * 46
            row = pygame.Rect(60, y - 4, 380, 38)
            hov = row.collidepoint(mouse)
            if hov:
                self.hover_attr = a
            ui.botw_box(surf, row, 170 if hov else 120, SHEIKAH if hov else (100, 102, 100), radius=19)
            prim = a == p.cls["primary"]
            ui.draw_text(surf, ATTR_NAMES[a], (80, y + 4), 17, BOTW_YELLOW if prim else WHITE, "bold")
            if prim:
                ui.draw_text(surf, "principale", (206, y + 8), 12, SOFT, shadow=False)
            ui.draw_text(surf, str(int(s[a])), (380, y + 3), 19, WHITE, "bold", anchor="topright")
            if p.points:
                rc = self.plus[a]
                h2 = rc.collidepoint(mouse)
                ui.circle(surf, (40, 110, 60) if h2 else (20, 60, 34), rc.center, 14)
                ui.circle(surf, UP, rc.center, 14, 1)
                ui.draw_text(surf, "+", rc.center, 20, WHITE, "bold", anchor="center", shadow=False)
        if self.hover_attr:
            ui.draw_text(surf, ATTR_DESC[self.hover_attr], (col.centerx, 522), 14, SOFT, anchor="midtop")
        ui.draw_text(surf, "Maj + clic : +5 points", (col.centerx, 548), 12, (130, 136, 136), anchor="midtop",
                     shadow=False)
        ui.draw_text(surf, f"Étage max atteint : {p.max_floor}", (64, 600), 15, SOFT)
        ui.draw_text(surf, f"Monstres vaincus : {p.kills}", (64, 624), 15, SOFT)
        ui.draw_text(surf, f"Morts : {p.deaths}", (64, 648), 15, SOFT)
        # statistiques
        ui.botw_box(surf, (476, 76, 350, 618), 150, (90, 94, 92), radius=14)
        ui.draw_text(surf, "Statistiques", (651, 90), 19, WHITE, "title", anchor="midtop")
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
        y = 126
        for i, (label, val) in enumerate(rows):
            if i % 2 == 0:
                ui.botw_box(surf, (490, y - 3, 322, 26), 70, None, radius=6, fill=(40, 60, 70))
            ui.draw_text(surf, label, (504, y), 14, SOFT)
            ui.draw_text(surf, val, (798, y), 14, WHITE, "bold", anchor="topright")
            y += 27
        if p.anima:
            y += 8
            ui.draw_text(surf, "Pouvoirs d'anima", (651, y), 16, SHEIKAH, "title", anchor="midtop")
            y += 26
            for pid, n in p.anima.items():
                pw = ANIMA_POWERS[pid]
                ui.circle(surf, pw["color"], (504, y + 8), 5)
                ui.draw_text(surf, f"{pw['name']} x{n}", (516, y), 13, WHITE)
                y += 19
                if y > 676:
                    break
        # compétences
        ui.botw_box(surf, (842, 76, 398, 618), 150, (90, 94, 92), radius=14)
        ui.draw_text(surf, "Compétences", (1041, 90), 19, WHITE, "title", anchor="midtop")
        a = p.cls["attack"]
        entries = [(a["name"], a.get("color", p.cls["color"]), f"Attaque de base · {int(a['mult'] * 100)}% arme",
                    "Clic gauche maintenu.", True, "LMB")]
        for i, sid in enumerate(p.spells):
            sp = SPELLS[sid]
            entries.append((sp["name"], sp["color"], f"Mana {sp['mana']} · Recharge {sp['cd']} s · Niv {sp['level']}",
                            sp["desc"], p.spell_unlocked(sid), str(i + 1)))
        y = 126
        for name, c, meta, desc, ok, key in entries:
            ui.circle(surf, ui.darker(c, 0.45) if ok else (30, 30, 30), (878, y + 20), 20)
            ui.circle(surf, ui.lighter(c, 1.2) if ok else (90, 90, 90), (878, y + 20), 20, 2)
            ui.draw_text(surf, key, (878, y + 20), 12, WHITE if ok else (120, 120, 120), "bold", anchor="center",
                         shadow=False)
            ui.draw_text(surf, name, (910, y), 16, WHITE if ok else (130, 130, 130), "bold")
            ui.draw_text(surf, meta, (910, y + 21), 12, SHEIKAH if ok else (120, 120, 120), shadow=False)
            yy = y + 39
            for line in ui.wrap(desc, 13, 310)[:3]:
                ui.draw_text(surf, line, (910, yy), 13, SOFT if ok else (110, 110, 110), shadow=False)
                yy += 17
            y = max(yy, y + 60) + 12

    def draw_tooltips(self, surf):
        if self.tab == 0 and self.ench_hover:
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


# =========================================================================== pause / mort
class PausePanel(Panel):
    modal = True

    def __init__(self, world):
        super().__init__(world, (SCREEN_W // 2 - 240, 60, 480, 610))
        r = self.rect
        self.buttons = [ui.Button((r.x + 60, r.y + 72, r.w - 120, 42), "Reprendre", world.close_modal)]
        if world.is_tower:
            self.buttons.append(ui.Button((r.x + 60, r.y + 122, r.w - 120, 42), "Abandonner l'ascension",
                                          lambda: world.exit_to_hub("Vous avez abandonné l'ascension.")))
        self.buttons.append(ui.Button((r.x + 60, r.y + 172, r.w - 120, 42), "Sauvegarder et menu principal",
                                      world.save_and_menu))
        self.buttons.append(ui.Button((r.x + 60, r.y + 222, r.w - 120, 42), "Sauvegarder et quitter",
                                      world.save_and_quit))

    def handle_event(self, e):
        for b in self.buttons:
            if b.handle(e):
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.world.close_modal()
        return True

    def draw(self, surf):
        ui.botw_panel(surf, self.rect, "Pause")
        for b in self.buttons:
            b.draw(surf)
        y = self.rect.y + 282
        ui.separator(surf, self.rect.x + 30, self.rect.right - 30, y)
        controls = [
            ("ZQSD / WASD / flèches", "Se déplacer"), ("Clic gauche (maintenu)", "Attaque de base"),
            ("1 2 3 4 · clic droit", "Sorts (clic droit = sort 1)"), ("Espace", "Roulade d'esquive"),
            ("R · T · G", "Artefacts"), ("F", "Potion (à recharge)"), ("E", "Interagir"),
            ("I · C", "Équipement · Personnage"), ("Tab", "Carte"), ("F11", "Plein écran"),
        ]
        y += 12
        for k, v in controls:
            ui.draw_text(surf, k, (self.rect.x + 36, y), 15, BOTW_YELLOW, "bold")
            ui.draw_text(surf, v, (self.rect.right - 36, y), 15, SOFT, anchor="topright")
            y += 26


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
        ui.draw_text(surf, "Les Tourments ont eu raison de vous.", (self.rect.centerx, self.rect.y + 34), 20, WHITE,
                     anchor="midtop")
        ui.draw_text(surf, f"Vous perdez {self.lost} pièces d'or récoltées pendant l'ascension.",
                     (self.rect.centerx, self.rect.y + 76), 16, GOLD, anchor="midtop")
        ui.draw_text(surf, "Votre équipement et votre expérience sont conservés.",
                     (self.rect.centerx, self.rect.y + 104), 16, SOFT, anchor="midtop")
        if self.t > 1.0:
            self.btn.draw(surf)
