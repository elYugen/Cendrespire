"""Panneaux d'interface en jeu, style tablette Sheikah (Zelda BotW) :
menu plein écran Équipement / Personnage, marchand, forge, portail, anima, pause, mort."""
import math

import pygame

from . import render, sfx
from .data import (ATTRS, ATTR_NAMES, ATTR_DESC, SPELLS, ANIMA_POWERS, BAG_SIZE, xp_needed, floor_name,
                   floor_boss, BOSSES, POTION_PRICE, MAX_POTIONS)
from .items import (SLOT_NAMES, AFFIX_DEF, buy_price, upgrade_cost, MAX_UPGRADE, item_lines, item_stats,
                    item_value)
from .settings import SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, GOLD, GOLD_BRIGHT, RED, RARITY_COLORS, RARITY_NAMES, GREEN
from .ui import (draw_text, wrap, Button, draw_item_icon, item_tooltip, draw_tooltip_lines, darker, lighter,
                 botw_box, botw_panel, selection_frame, text_surf, BOTW_LINE, BOTW_CYAN, BOTW_YELLOW)

WHITE = (245, 243, 235)
SOFT = (200, 205, 205)
UP = (110, 235, 120)
DOWN = (240, 90, 80)


def item_slot(surf, rect, item, t, selected=False, hovered=False, usable=True, label=None):
    rect = pygame.Rect(rect)
    border = BOTW_CYAN if hovered else ((150, 150, 146) if item else (80, 80, 78))
    botw_box(surf, rect, 150 if not hovered else 190, border, radius=8, fill=(0, 0, 0) if not hovered else (10, 30, 40))
    if item:
        col = RARITY_COLORS[item["rarity"]]
        if item["rarity"] != "commun":
            g = pygame.Surface(rect.size, pygame.SRCALPHA)
            for i in range(rect.h // 2):
                a = int(70 * (i / (rect.h / 2)) ** 2)
                pygame.draw.line(g, (*col, a), (4, rect.h // 2 + i), (rect.w - 5, rect.h // 2 + i))
            surf.blit(g, rect)
            pygame.draw.line(surf, col, (rect.x + 8, rect.bottom - 3), (rect.right - 9, rect.bottom - 3), 2)
        draw_item_icon(surf, item, rect.inflate(-rect.w * 0.22, -rect.h * 0.22), bg=False)
        if not usable:
            pygame.draw.line(surf, DOWN, (rect.x + 6, rect.bottom - 6), (rect.right - 6, rect.y + 6), 2)
    elif label:
        draw_text(surf, label, rect.center, 12, (120, 122, 120), anchor="center", shadow=False)
    if selected:
        selection_frame(surf, rect, t)


def veil(surf, alpha=235):
    v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    v.fill((6, 12, 16, alpha))
    surf.blit(v, (0, 0))


def attack_icon(surf, x, y):
    pygame.draw.line(surf, WHITE, (x - 8, y + 8), (x + 8, y - 8), 3)
    pygame.draw.line(surf, WHITE, (x - 8, y - 2), (x - 2, y + 8), 2)


def shield_icon(surf, x, y):
    pts = [(x - 8, y - 9), (x + 8, y - 9), (x + 8, y + 1), (x, y + 10), (x - 8, y + 1)]
    pygame.draw.polygon(surf, WHITE, pts, 2)


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
           ("Bijoux", {"amulette", "anneau"})]


class MenuScreen(Panel):
    """Menu façon Zelda BotW (met le jeu en pause) : onglets Équipement et Personnage."""
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
        self.filter_rects = [pygame.Rect(60 + i * 112, 110, 104, 30) for i in range(len(FILTERS))]
        cell = 74
        self.bag_rects = [pygame.Rect(62 + (i % 8) * (cell + 4), 156 + (i // 8) * (cell + 4), cell, cell)
                          for i in range(BAG_SIZE)]
        S = 64
        self.slot_rects = {
            "arme": pygame.Rect(748, 120, S, S), "torse": pygame.Rect(748, 200, S, S),
            "gants": pygame.Rect(748, 280, S, S), "bottes": pygame.Rect(748, 360, S, S),
            "casque": pygame.Rect(1168, 120, S, S), "amulette": pygame.Rect(1168, 200, S, S),
            "anneau": pygame.Rect(1168, 280, S, S),
        }
        self.plus = {a: pygame.Rect(400, 330 + i * 46, 30, 30) for i, a in enumerate(ATTRS)}
        self.hover_attr = None

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
        """Variation d'attaque / défense / vie si l'on équipe l'objet (flèches à la Zelda)."""
        p = self.world.player
        if not item or not p.can_equip(item) or item in p.equipment.values():
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
                hit = self.hit_test(pygame.mouse.get_pos())
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
        veil(surf)
        # lignes de fond discrètes
        for y in range(0, SCREEN_H, 48):
            pygame.draw.line(surf, (18, 30, 36), (0, y), (SCREEN_W, y))
        mouse = pygame.mouse.get_pos()
        for i, (name, rc) in enumerate(zip(self.TABS, self.tab_rects)):
            active = i == self.tab
            draw_text(surf, name, rc.center, 24 if active else 20, WHITE if active else (130, 135, 135), "title",
                      anchor="center")
            if active:
                pygame.draw.line(surf, BOTW_CYAN, (rc.x + 30, rc.bottom), (rc.right - 30, rc.bottom), 2)
        cx = SCREEN_W // 2
        for d in (-1, 1):
            x = cx + d * 290
            pygame.draw.polygon(surf, (160, 165, 165), [(x, 30), (x, 46), (x + d * 10, 38)])
        if self.tab == 0:
            self.draw_equipment(surf, mouse)
        else:
            self.draw_character(surf, mouse)
        draw_text(surf, "[I] Équipement   [C] Personnage   [Tab] Changer d'onglet   [Échap] Fermer",
                  (SCREEN_W - 30, SCREEN_H - 12), 13, (150, 160, 160), anchor="bottomright")
        msgs = [m for m in self.world.messages if m[2] > 0]
        if msgs:
            draw_text(surf, msgs[-1][0], (30, SCREEN_H - 12), 14, msgs[-1][1], anchor="bottomleft")

    def draw_equipment(self, surf, mouse):
        p = self.world.player
        t = self.t
        # --- sac
        botw_box(surf, (40, 76, 660, 500), 120, (90, 92, 90), radius=14)
        draw_text(surf, f"Sac   {len(p.inventory)}/{BAG_SIZE}", (62, 84), 17, WHITE)
        draw_text(surf, f"{p.gold} or", (680, 84), 17, GOLD_BRIGHT, anchor="topright")
        for i, ((name, _), rc) in enumerate(zip(FILTERS, self.filter_rects)):
            act = i == self.filter
            botw_box(surf, rc, 200 if act else 110, BOTW_CYAN if act else (110, 110, 108), radius=15,
                     fill=(15, 45, 58) if act else (0, 0, 0))
            draw_text(surf, name, rc.center, 14, WHITE if act else SOFT, anchor="center", shadow=False)
        self.hover = None
        items = self.visible_items()
        for n, rc in enumerate(self.bag_rects):
            it = items[n][1] if n < len(items) else None
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = it
            item_slot(surf, rc, it, t, it is not None and it is self.selected, hov, it is None or p.can_equip(it))
        # --- héros et équipement
        botw_box(surf, (720, 76, 520, 500), 120, (90, 92, 90), radius=14)
        fx, fy = 990, 420
        from .fx import glow
        pygame.draw.ellipse(surf, (20, 60, 76), (fx - 110, fy - 24, 220, 48))
        pygame.draw.ellipse(surf, BOTW_CYAN, (fx - 110, fy - 24, 220, 48), 1)
        glows = []
        render.draw_humanoid(surf, fx, fy, 4.6, 0.9 + 0.3 * math.sin(t * 0.8), 0,
                             render.PLAYER_SPECS[p.cls_id], glows=glows)
        for gx, gy, c, r in glows:
            glow(surf, gx, gy, r, c)
        for slot, rc in self.slot_rects.items():
            it = p.equipment[slot]
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = it
            item_slot(surf, rc, it, t, it is not None and it is self.selected, hov, True, SLOT_NAMES[slot])
        draw_text(surf, p.name, (fx, 90), 22, WHITE, "title", anchor="midtop")
        draw_text(surf, f"{p.cls['name']}  ·  Niveau {p.level}", (fx, 118), 15, SOFT, anchor="midtop")
        # stats principales avec variation
        focus = self.hover or self.selected
        delta = self.preview(focus) if focus else None
        s = p.stats
        rows = [(attack_icon, "Attaque", p.dps_estimate(), 0), (shield_icon, "Défense", s["armor"], 1),
                (heart_icon, "Vie", s["max_hp"], 2)]
        for i, (icon, label, val, di) in enumerate(rows):
            x = 800 + i * 140
            y = 480
            botw_box(surf, (x - 50, y - 6, 128, 64), 170, (120, 120, 116), radius=10)
            icon(surf, x - 26, y + 16)
            draw_text(surf, str(int(val)), (x - 6, y + 2), 24, WHITE)
            draw_text(surf, label, (x - 6, y + 32), 12, SOFT, shadow=False)
            if delta and abs(delta[di]) >= 1:
                up = delta[di] > 0
                col = UP if up else DOWN
                ax, ay = x + 56, y + 16
                pts = [(ax, ay - 8), (ax + 7, ay + 1), (ax - 7, ay + 1)] if up else [(ax, ay + 8), (ax + 7, ay - 1), (ax - 7, ay - 1)]
                pygame.draw.polygon(surf, col, pts)
                draw_text(surf, f"{'+' if up else ''}{int(delta[di])}", (ax, ay + 12), 13, col, anchor="midtop")
        # --- fiche de l'objet
        box = botw_box(surf, (40, 590, 1200, 104), 190, (120, 120, 116), radius=14)
        it = focus
        if not it:
            draw_text(surf, "Survolez ou sélectionnez un objet pour afficher ses détails.", box.center, 16, SOFT,
                      anchor="center")
            return
        col = RARITY_COLORS[it["rarity"]]
        item_slot(surf, (box.x + 14, box.y + 14, 76, 76), it, t)
        name = it["name"] + (f" +{it['upgrade']}" if it.get("upgrade") else "")
        draw_text(surf, name, (box.x + 106, box.y + 12), 21, col, "title")
        sub = f"{SLOT_NAMES[it['slot']]} {RARITY_NAMES[it['rarity']].lower()}  ·  Niveau d'objet {it['ilvl']}"
        if it["slot"] == "arme":
            from .data import CLASSES
            sub += f"  ·  Arme de {CLASSES[it['wclass']]['name']}"
        draw_text(surf, sub, (box.x + 106, box.y + 42), 14, SOFT if p.can_equip(it) else DOWN)
        st = item_stats(it)
        main = f"Dégâts {int(st['dmg'][0])}-{int(st['dmg'][1])}" if "dmg" in st else (
            f"Armure {st['armor']}" if "armor" in st else "")
        if main:
            draw_text(surf, main, (box.x + 106, box.y + 66), 17, WHITE)
        affs = [AFFIX_DEF[k][0].format(v=v) for k, v in st["affixes"].items()]
        for i, a in enumerate(affs):
            draw_text(surf, a, (box.x + 420 + (i // 3) * 270, box.y + 14 + (i % 3) * 25), 15, (140, 170, 255))
        equipped = it in p.equipment.values()
        hint = "[Clic droit] Retirer" if equipped else "[Clic droit] Équiper   [Suppr] Détruire"
        draw_text(surf, hint, (box.right - 16, box.bottom - 12), 13, SOFT, anchor="bottomright")
        draw_text(surf, f"Valeur {item_value(it)} or", (box.right - 16, box.y + 12), 14, GOLD, anchor="topright")

    def draw_character(self, surf, mouse):
        p = self.world.player
        s = p.stats
        t = self.t
        # --- colonne identité + caractéristiques
        col = botw_box(surf, (40, 76, 420, 618), 130, (90, 92, 90), radius=14)
        glows = []
        render.shadow(surf, 145, 262, 34)
        render.draw_humanoid(surf, 145, 262, 3.0, 0.9, 0, render.PLAYER_SPECS[p.cls_id], glows=glows)
        from .fx import glow
        for gx, gy, c, r in glows:
            glow(surf, gx, gy, r, c)
        draw_text(surf, p.name, (240, 110), 26, WHITE, "title")
        draw_text(surf, p.cls["title"], (240, 144), 15, SOFT)
        draw_text(surf, f"{p.cls['name']}  ·  Niveau {p.level}", (240, 168), 16, BOTW_YELLOW)
        need = xp_needed(p.level)
        bar = pygame.Rect(240, 200, 190, 8)
        pygame.draw.rect(surf, (0, 0, 0), bar.inflate(2, 2), border_radius=4)
        pygame.draw.rect(surf, (235, 200, 90), (bar.x, bar.y, bar.w * min(1, p.xp / need), bar.h), border_radius=4)
        draw_text(surf, f"{p.xp} / {need} XP", (bar.x, bar.bottom + 4), 12, SOFT, shadow=False)
        draw_text(surf, "Caractéristiques", (64, 290), 18, WHITE, "title")
        if p.points:
            k = 0.6 + 0.4 * math.sin(t * 4)
            draw_text(surf, f"{p.points} point(s) à répartir", (436, 293), 14,
                      (int(110 * k + 60), 235, int(120 * k + 40)), anchor="topright")
        self.hover_attr = None
        for i, a in enumerate(ATTRS):
            y = 330 + i * 46
            row = pygame.Rect(60, y - 4, 380, 38)
            hov = row.collidepoint(mouse)
            if hov:
                self.hover_attr = a
            botw_box(surf, row, 170 if hov else 120, BOTW_CYAN if hov else (100, 100, 98), radius=19)
            prim = a == p.cls["primary"]
            draw_text(surf, ATTR_NAMES[a], (80, y + 4), 17, BOTW_YELLOW if prim else WHITE)
            if prim:
                draw_text(surf, "principale", (200, y + 7), 12, SOFT, shadow=False)
            draw_text(surf, str(int(s[a])), (380, y + 3), 19, WHITE, anchor="topright")
            if p.points:
                rc = self.plus[a]
                h2 = rc.collidepoint(mouse)
                pygame.draw.circle(surf, (40, 110, 60) if h2 else (20, 60, 34), rc.center, 14)
                pygame.draw.circle(surf, UP, rc.center, 14, 1)
                draw_text(surf, "+", rc.center, 20, WHITE, anchor="center", shadow=False)
        if self.hover_attr:
            draw_text(surf, ATTR_DESC[self.hover_attr], (col.centerx, 520), 14, SOFT, anchor="midtop")
        draw_text(surf, "Maj + clic : +5 points", (col.centerx, 546), 12, (130, 135, 135), anchor="midtop", shadow=False)
        draw_text(surf, f"Étage max atteint : {p.max_floor}", (64, 600), 15, SOFT)
        draw_text(surf, f"Monstres vaincus : {p.kills}", (64, 624), 15, SOFT)
        draw_text(surf, f"Morts : {p.deaths}", (64, 648), 15, SOFT)
        # --- statistiques
        botw_box(surf, (476, 76, 350, 618), 130, (90, 92, 90), radius=14)
        draw_text(surf, "Statistiques", (651, 92), 18, WHITE, "title", anchor="midtop")
        dr = p.damage_reduction() * 100
        rows = [
            ("Vie", f"{int(p.hp)} / {int(s['max_hp'])}"), ("Mana", f"{int(p.mana)} / {int(s['max_mana'])}"),
            ("Dégâts de l'arme", f"{int(s['dmg_min'])} - {int(s['dmg_max'])}"),
            ("Multiplicateur", f"x{s['dmg_mult']:.2f}"), ("Dégâts / seconde", f"{int(p.dps_estimate())}"),
            ("Armure", f"{int(s['armor'])}"), ("Réduction des dégâts", f"{dr:.0f}%"),
            ("Coup critique", f"{s['crit']:.1f}%"), ("Vitesse d'attaque", f"+{s['atk_speed']:.0f}%"),
            ("Vol de vie", f"{s['lifesteal']:.0f}%"), ("Régén. de mana", f"{s['mana_regen']:.1f}/s"),
            ("Recharge", f"-{s['cdr']:.0f}%"), ("Déplacement", f"+{s['move_speed']:.0f}%"),
            ("Or trouvé", f"+{s['gold_find']:.0f}%"),
        ]
        y = 130
        for i, (label, val) in enumerate(rows):
            if i % 2 == 0:
                botw_box(surf, (490, y - 3, 322, 26), 70, None, radius=6, fill=(40, 60, 70))
            draw_text(surf, label, (504, y), 15, SOFT)
            draw_text(surf, val, (798, y), 15, WHITE, anchor="topright")
            y += 28
        if p.anima:
            y += 10
            draw_text(surf, "Pouvoirs d'anima", (651, y), 16, BOTW_CYAN, "title", anchor="midtop")
            y += 28
            for pid, n in p.anima.items():
                pw = ANIMA_POWERS[pid]
                pygame.draw.circle(surf, pw["color"], (504, y + 9), 5)
                draw_text(surf, f"{pw['name']} x{n}", (516, y), 14, WHITE)
                y += 20
                if y > 680:
                    break
        # --- compétences
        botw_box(surf, (842, 76, 398, 618), 130, (90, 92, 90), radius=14)
        draw_text(surf, "Compétences", (1041, 92), 18, WHITE, "title", anchor="midtop")
        a = p.cls["attack"]
        entries = [(a["name"], a.get("color", p.cls["color"]), f"Attaque de base · {int(a['mult'] * 100)}% arme",
                    "Clic gauche maintenu.", True, "LMB")]
        for i, sid in enumerate(p.spells):
            sp = SPELLS[sid]
            entries.append((sp["name"], sp["color"], f"Mana {sp['mana']} · Recharge {sp['cd']} s · Niv {sp['level']}",
                            sp["desc"], p.spell_unlocked(sid), str(i + 1)))
        y = 128
        for name, c, meta, desc, ok, key in entries:
            pygame.draw.circle(surf, darker(c, 0.45) if ok else (30, 30, 30), (878, y + 20), 20)
            pygame.draw.circle(surf, lighter(c, 1.2) if ok else (90, 90, 90), (878, y + 20), 20, 2)
            draw_text(surf, key, (878, y + 20), 13, WHITE if ok else (120, 120, 120), anchor="center", shadow=False)
            draw_text(surf, name, (910, y), 16, WHITE if ok else (130, 130, 130))
            draw_text(surf, meta, (910, y + 20), 12, BOTW_CYAN if ok else (120, 120, 120), shadow=False)
            yy = y + 38
            for line in wrap(desc, 13, 310)[:3]:
                draw_text(surf, line, (910, yy), 13, SOFT if ok else (110, 110, 110), shadow=False)
                yy += 16
            y = max(yy, y + 60) + 14


# =========================================================================== sac compact (marchand / forge)
class InventoryPanel(Panel):
    COLS, CELL = 8, 44

    def __init__(self, world):
        super().__init__(world, (SCREEN_W - 408, 16, 392, 600))
        r = self.rect
        cx, top, S = r.centerx, r.y + 64, 56
        self.slot_rects = {
            "casque": pygame.Rect(cx - S // 2, top, S, S),
            "amulette": pygame.Rect(cx + S // 2 + 22, top + 8, 44, 44),
            "arme": pygame.Rect(cx - S // 2 - S - 22, top + S + 8, S, S + 24),
            "torse": pygame.Rect(cx - S // 2, top + S + 8, S, S + 24),
            "anneau": pygame.Rect(cx + S // 2 + 22, top + S + 20, 44, 44),
            "gants": pygame.Rect(cx - S // 2 - S - 22, top + 2 * S + 40, S, S),
            "bottes": pygame.Rect(cx - S // 2, top + 2 * S + 40, S, S),
        }
        gx = r.x + (r.w - self.COLS * self.CELL) // 2
        gy = top + 3 * S + 62
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
            hit = self.item_at(pygame.mouse.get_pos())
            if hit and hit[0] == "bag" and hit[2]:
                w.destroy_item(hit[1])
                return True
        return False

    def draw(self, surf):
        self.t += 1 / 60
        p = self.world.player
        botw_panel(surf, self.rect, "Sac")
        mouse = pygame.mouse.get_pos()
        sel = self.world.left_panel.selected if isinstance(self.world.left_panel, ForgePanel) else None
        for slot, rc in self.slot_rects.items():
            it = p.equipment[slot]
            item_slot(surf, rc, it, self.t, it is not None and it is sel, rc.collidepoint(mouse) and it is not None,
                      True, SLOT_NAMES[slot])
        r = self.rect
        y = self.bag_rects[0].y - 26
        draw_text(surf, f"{len(p.inventory)}/{BAG_SIZE}", (r.x + 26, y), 15, SOFT)
        draw_text(surf, f"{p.gold} or", (r.right - 26, y), 16, GOLD_BRIGHT, anchor="topright")
        for i, rc in enumerate(self.bag_rects):
            it = p.inventory[i] if i < len(p.inventory) else None
            item_slot(surf, rc, it, self.t, it is not None and it is sel, rc.collidepoint(mouse) and it is not None,
                      it is None or p.can_equip(it))
        lp = self.world.left_panel
        hint = "Clic droit : vendre" if isinstance(lp, MerchantPanel) else "Clic gauche : choisir l'objet"
        draw_text(surf, hint, (r.centerx, r.bottom - 14), 14, SOFT, anchor="midbottom")

    def draw_tooltips(self, surf):
        pos = pygame.mouse.get_pos()
        if not self.rect.collidepoint(pos):
            return
        hit = self.item_at(pos)
        if not hit or not hit[2]:
            return
        p = self.world.player
        kind, key, item = hit
        tip = item_tooltip(surf, item, pos, p, "Équipé" if kind == "equip" else None, side="left")
        if kind == "bag":
            eq = p.equipment.get(item["slot"])
            if eq:
                item_tooltip(surf, eq, (tip.x - 4, tip.y - 8), p, "Actuellement équipé", side="left")
            if isinstance(self.world.left_panel, MerchantPanel):
                draw_text(surf, f"Vendre : {item_value(item)} or", (tip.centerx, tip.bottom + 4), 15, GOLD,
                          anchor="midtop")


# =========================================================================== marchand
class MerchantPanel(Panel):
    def __init__(self, world):
        super().__init__(world, (16, 16, 380, 600))
        r = self.rect
        self.rows = [pygame.Rect(r.x + 20, r.y + 122 + i * 54, r.w - 40, 48) for i in range(8)]
        self.potion_btn = Button((r.x + 24, r.y + 66, r.w - 48, 40), f"Potion de soins — {POTION_PRICE} or",
                                 self.buy_potion, 17, style="botw")
        self.hover = None

    def buy_potion(self):
        p = self.world.player
        if p.gold < POTION_PRICE:
            self.world.message("Pas assez d'or.", RED)
        elif p.potions >= MAX_POTIONS:
            self.world.message("Vous ne pouvez pas porter plus de potions.", RED)
        else:
            p.gold -= POTION_PRICE
            p.potions += 1
            sfx.play("gold")

    def handle_event(self, e):
        if self.potion_btn.handle(e):
            return True
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
        botw_panel(surf, r, "Gorvan le Marchand")
        self.potion_btn.enabled = p.gold >= POTION_PRICE and p.potions < MAX_POTIONS
        self.potion_btn.draw(surf)
        self.hover = None
        mouse = pygame.mouse.get_pos()
        for i, rc in enumerate(self.rows):
            if i >= len(self.world.shop_stock):
                break
            it = self.world.shop_stock[i]
            hov = rc.collidepoint(mouse)
            if hov:
                self.hover = it
            botw_box(surf, rc, 180 if hov else 110, BOTW_CYAN if hov else (90, 92, 90), radius=10,
                     fill=(10, 30, 40) if hov else (0, 0, 0))
            item_slot(surf, (rc.x + 4, rc.y + 4, 40, 40), it, 0)
            draw_text(surf, it["name"], (rc.x + 54, rc.y + 5), 15, RARITY_COLORS[it["rarity"]])
            draw_text(surf, SLOT_NAMES[it["slot"]], (rc.x + 54, rc.y + 26), 13, SOFT)
            price = buy_price(it)
            draw_text(surf, f"{price} or", (rc.right - 10, rc.y + 26), 15, GOLD if p.gold >= price else RED,
                      anchor="topright")
        draw_text(surf, "Clic gauche : acheter", (r.centerx, r.bottom - 14), 13, SOFT, anchor="midbottom")

    def draw_tooltips(self, surf):
        if self.hover:
            tip = item_tooltip(surf, self.hover, pygame.mouse.get_pos(), self.world.player)
            eq = self.world.player.equipment.get(self.hover["slot"])
            if eq:
                item_tooltip(surf, eq, (tip.right + 4, tip.y - 8), self.world.player, "Actuellement équipé")


# =========================================================================== forge
class ForgePanel(Panel):
    def __init__(self, world):
        super().__init__(world, (16, 16, 380, 600))
        self.selected = None
        r = self.rect
        self.btn = Button((r.x + 40, r.bottom - 80, r.w - 80, 44), "Améliorer", self.upgrade, 19, style="botw")

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
        botw_panel(surf, r, "Hilda la Forgeronne")
        y = r.y + 66
        for line in wrap("« Apporte-moi ton équipement, je le rendrai plus redoutable. Chaque amélioration renforce "
                         "l'objet de 10% (jusqu'à +5). »", 15, r.w - 48):
            draw_text(surf, line, (r.x + 24, y), 15, SOFT)
            y += 20
        it = self.selected
        if it and it not in p.inventory and it not in p.equipment.values():
            self.selected = it = None
        y += 14
        if not it:
            for line in wrap("Cliquez (gauche) sur un objet de votre sac ou de votre équipement.", 16, r.w - 48):
                draw_text(surf, line, (r.x + 24, y + 20), 16, (150, 155, 155))
                y += 22
            self.btn.enabled = False
        else:
            item_slot(surf, (r.x + 24, y, 64, 64), it, 0, False)
            draw_text(surf, it["name"], (r.x + 100, y + 6), 17, RARITY_COLORS[it["rarity"]])
            draw_text(surf, f"Amélioration : +{it.get('upgrade', 0)} / {MAX_UPGRADE}", (r.x + 100, y + 32), 15, SOFT)
            y += 82
            nxt = dict(it, upgrade=min(MAX_UPGRADE, it.get("upgrade", 0) + 1))
            keep = ((240, 240, 240), (125, 150, 255))
            lc = [l for l in item_lines(it) if l[1] in keep]
            ln = [l for l in item_lines(nxt) if l[1] in keep]
            for a, b in zip(lc, ln):
                draw_text(surf, a[0], (r.x + 24, y), 14, TEXT)
                if a[0] != b[0]:
                    val = b[0].split(":")[-1].strip() if ":" in b[0] else b[0].split(" ")[0]
                    draw_text(surf, "-> " + val, (r.right - 24, y), 14, UP, anchor="topright")
                y += 20
            maxed = it.get("upgrade", 0) >= MAX_UPGRADE
            cost = upgrade_cost(it)
            self.btn.text = "Niveau maximum" if maxed else f"Améliorer — {cost} or"
            self.btn.enabled = not maxed and p.gold >= cost
        draw_text(surf, f"Votre or : {p.gold}", (r.centerx, self.btn.rect.y - 30), 16, GOLD, anchor="midtop")
        self.btn.draw(surf)


# =========================================================================== portail
class PortalPanel(Panel):
    modal = True

    def __init__(self, world):
        super().__init__(world, (SCREEN_W // 2 - 300, 70, 600, 560))
        self.scroll = max(0, world.player.max_floor - 7)
        self.close_btn = Button((self.rect.centerx - 80, self.rect.bottom - 58, 160, 40), "Fermer", world.close_modal,
                                style="botw")

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
        botw_panel(surf, self.rect, "Portail de la Tour")
        p = self.world.player
        mouse = pygame.mouse.get_pos()
        for f, rc in self.rows():
            hov = rc.collidepoint(mouse)
            botw_box(surf, rc, 190 if hov else 110, BOTW_CYAN if hov else (90, 92, 90), radius=12,
                     fill=(10, 34, 44) if hov else (0, 0, 0))
            done = f in p.cleared
            draw_text(surf, f"Étage {f}", (rc.x + 16, rc.y + 5), 20, WHITE, "title")
            draw_text(surf, floor_name(f), (rc.x + 16, rc.y + 29), 14, SOFT)
            b = BOSSES[floor_boss(f)]
            draw_text(surf, f"Gardien : {b['name']}", (rc.right - 16, rc.y + 7), 15, WHITE, anchor="topright")
            draw_text(surf, "Vaincu" if done else "Jamais vaincu", (rc.right - 16, rc.y + 29), 13,
                      UP if done else DOWN, anchor="topright")
            if hov:
                selection_frame(surf, rc, pygame.time.get_ticks() / 1000, BOTW_CYAN)
        if p.max_floor > 7:
            draw_text(surf, "Molette : faire défiler", (self.rect.centerx, self.rect.bottom - 80), 13, SOFT,
                      anchor="midbottom")
        self.close_btn.draw(surf)


# =========================================================================== anima
class AnimaPanel(Panel):
    modal = True

    def __init__(self, world, choices):
        super().__init__(world, (SCREEN_W // 2 - 380, 150, 760, 400))
        self.choices = choices
        self.cards = [pygame.Rect(self.rect.x + 30 + i * 240, self.rect.y + 110, 220, 250) for i in range(len(choices))]

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for pid, rc in zip(self.choices, self.cards):
                if rc.collidepoint(e.pos):
                    self.world.take_anima(pid)
                    return True
        if e.type == pygame.KEYDOWN and e.scancode in (30, 31, 32, 89, 90, 91):
            i = {30: 0, 31: 1, 32: 2, 89: 0, 90: 1, 91: 2}[e.scancode]
            if i < len(self.choices):
                self.world.take_anima(self.choices[i])
        return True

    def draw(self, surf):
        botw_panel(surf, self.rect, "Pouvoir d'Anima")
        draw_text(surf, "Choisissez un pouvoir. Il durera jusqu'à la fin de cette ascension.",
                  (self.rect.centerx, self.rect.y + 64), 16, SOFT, anchor="midtop")
        mouse = pygame.mouse.get_pos()
        p = self.world.player
        t = pygame.time.get_ticks() / 1000
        for i, (pid, rc) in enumerate(zip(self.choices, self.cards)):
            pw = ANIMA_POWERS[pid]
            hov = rc.collidepoint(mouse)
            botw_box(surf, rc, 190 if hov else 120, pw["color"] if hov else (90, 92, 90), radius=14,
                     fill=(14, 22, 30) if hov else (0, 0, 0))
            c = (rc.centerx, rc.y + 60)
            pygame.draw.circle(surf, darker(pw["color"], 0.4), c, 34)
            pygame.draw.circle(surf, pw["color"], c, 34, 2)
            pygame.draw.polygon(surf, pw["color"], [(c[0], c[1] - 18), (c[0] + 14, c[1]), (c[0], c[1] + 18), (c[0] - 14, c[1])])
            draw_text(surf, pw["name"], (rc.centerx, rc.y + 110), 18, WHITE, anchor="midtop")
            y = rc.y + 142
            for line in wrap(pw["desc"], 15, rc.w - 24):
                r = draw_text(surf, line, (rc.centerx, y), 15, SOFT, anchor="midtop")
                y += r.h + 2
            n = p.anima.get(pid, 0)
            if n:
                draw_text(surf, f"Déjà possédé : x{n}", (rc.centerx, rc.bottom - 28), 13, SOFT, anchor="midtop")
            draw_text(surf, f"[{i + 1}]", (rc.x + 10, rc.y + 8), 14, SOFT)
            if hov:
                selection_frame(surf, rc, t)


# =========================================================================== pause / mort
class PausePanel(Panel):
    modal = True

    def __init__(self, world):
        super().__init__(world, (SCREEN_W // 2 - 230, 80, 460, 560))
        r = self.rect
        self.buttons = [Button((r.x + 60, r.y + 72, r.w - 120, 42), "Reprendre", world.close_modal, style="botw")]
        if world.is_tower:
            self.buttons.append(Button((r.x + 60, r.y + 122, r.w - 120, 42), "Abandonner l'ascension",
                                       lambda: world.exit_to_hub("Vous avez abandonné l'ascension."), style="botw"))
        self.buttons.append(Button((r.x + 60, r.y + 172, r.w - 120, 42), "Sauvegarder et menu principal",
                                   world.save_and_menu, style="botw"))
        self.buttons.append(Button((r.x + 60, r.y + 222, r.w - 120, 42), "Sauvegarder et quitter",
                                   world.save_and_quit, style="botw"))

    def handle_event(self, e):
        for b in self.buttons:
            if b.handle(e):
                return True
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.world.close_modal()
        return True

    def draw(self, surf):
        botw_panel(surf, self.rect, "Pause")
        for b in self.buttons:
            b.draw(surf)
        y = self.rect.y + 284
        pygame.draw.line(surf, (120, 120, 116), (self.rect.x + 30, y), (self.rect.right - 30, y))
        controls = [
            ("ZQSD / WASD / flèches", "Se déplacer"), ("Clic gauche (maintenu)", "Attaque de base"),
            ("1 2 3 4 / clic droit", "Sorts (clic droit = sort 1)"), ("F", "Boire une potion"),
            ("E", "Interagir"), ("I  ·  C", "Équipement · Personnage"), ("Tab", "Carte"), ("F11", "Plein écran"),
        ]
        y += 12
        for k, v in controls:
            draw_text(surf, k, (self.rect.x + 36, y), 15, BOTW_YELLOW)
            draw_text(surf, v, (self.rect.right - 36, y), 15, SOFT, anchor="topright")
            y += 26


class DeathPanel(Panel):
    modal = True

    def __init__(self, world, lost):
        super().__init__(world, (SCREEN_W // 2 - 260, 250, 520, 260))
        self.lost = lost
        self.t = 0.0
        self.btn = Button((self.rect.centerx - 150, self.rect.bottom - 70, 300, 46), "Retourner au campement",
                          lambda: world.exit_to_hub("Vous vous réveillez au campement, meurtri..."), style="botw")

    def update(self, dt):
        self.t += dt

    def handle_event(self, e):
        if self.t > 1.0:
            self.btn.handle(e)
        return True

    def draw(self, surf):
        v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        v.fill((50, 0, 0, int(min(1, self.t) * 150)))
        surf.blit(v, (0, 0))
        draw_text(surf, "VOUS ÊTES MORT", (SCREEN_W // 2, 170), 60, (210, 30, 30), "title", anchor="center")
        botw_panel(surf, self.rect)
        draw_text(surf, "Les Tourments ont eu raison de vous.", (self.rect.centerx, self.rect.y + 36), 20, WHITE,
                  anchor="midtop")
        draw_text(surf, f"Vous perdez {self.lost} pièces d'or récoltées pendant l'ascension.",
                  (self.rect.centerx, self.rect.y + 76), 16, GOLD, anchor="midtop")
        draw_text(surf, "Votre équipement et votre expérience sont conservés.", (self.rect.centerx, self.rect.y + 104),
                  16, SOFT, anchor="midtop")
        if self.t > 1.0:
            self.btn.draw(surf)
