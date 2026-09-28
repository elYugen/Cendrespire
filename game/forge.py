"""Forge de Hilda : une grande fenêtre en deux parties.
À gauche l'équipement porté et le sac ; à droite l'enclume : l'objet choisi, ses niveaux d'amélioration,
ses caractéristiques avant / après, le coût et le bouton Améliorer."""
import math

import pygame

from . import sfx, ui
from .data import BAG_SIZE
from .items import MAX_UPGRADE, SLOT_NAMES, item_lines, upgrade_cost
from .settings import GOLD, GOLD_BRIGHT, RARITY_COLORS, RED, TEXT_DIM, WHITE

SOFT = (206, 212, 212)
UP = (110, 235, 120)
EMBER = (255, 150, 60)
EQ_SLOTS = ("arme", "casque", "torse", "gants", "bottes", "amulette", "anneau")
STAT_COLS = ((240, 240, 240), (125, 150, 255))     # lignes de caractéristiques dans item_lines


class ForgeScreen:
    """Fenêtre modale de la forge (world.modal)."""
    modal = True
    hide_hud = True
    W = pygame.Rect(40, 34, 1200, 652)

    def __init__(self, world, name="Hilda la Forgeronne"):
        self.world = world
        self.name = name
        self.item = None
        self.hover = None
        self.t = 0.0
        self.flash = -9.0                 # instant de la dernière amélioration (gerbe d'étincelles)
        W = self.W
        top = W.y + 116
        self.left = pygame.Rect(W.x + 24, top, 430, W.bottom - 40 - top)
        self.anvil = pygame.Rect(self.left.right + 24, top, W.right - 24 - self.left.right - 24, W.bottom - 40 - top)
        step = 52
        gx = self.left.x + (self.left.w - 8 * step) // 2 + 2
        self.eq_rects = {s: pygame.Rect(gx + i * step, top + 30, step - 6, step - 6) for i, s in enumerate(EQ_SLOTS)}
        self.cells = [pygame.Rect(gx + (i % 8) * step, top + 132 + (i // 8) * step, step - 6, step - 6)
                      for i in range(BAG_SIZE)]
        self.btn = pygame.Rect(self.anvil.centerx - 170, self.anvil.bottom - 66, 340, 48)
        self.close_btn = pygame.Rect(W.right - 52, W.y + 14, 34, 34)

    # ------------------------------------------------------------------ données
    def owned(self, it):
        p = self.world.player
        return it is not None and (any(it is x for x in p.inventory) or any(it is x for x in p.equipment.values()))

    def hit(self, pos):
        p = self.world.player
        for s, rc in self.eq_rects.items():
            if rc.collidepoint(pos) and p.equipment.get(s):
                return p.equipment[s]
        for i, rc in enumerate(self.cells):
            if rc.collidepoint(pos) and i < len(p.inventory):
                return p.inventory[i]
        return None

    def upgrade(self):
        it = self.item
        p = self.world.player
        if not it:
            return
        cost = upgrade_cost(it)
        if it.get("upgrade", 0) >= MAX_UPGRADE:
            self.world.message("Cet objet est déjà au maximum.", RED)
        elif p.money < cost:
            self.world.message("Pas assez d'argent.", RED)
            sfx.play("click")
        else:
            p.money -= cost
            it["upgrade"] = it.get("upgrade", 0) + 1
            p.recompute()
            self.flash = self.t
            sfx.play("chest")
            self.world.message(f"{it['name']} amélioré à +{it['upgrade']} !", GOLD_BRIGHT)

    # ------------------------------------------------------------------ événements
    def handle_event(self, e):
        w = self.world
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            w.close_modal()
            return True
        if e.type != pygame.MOUSEBUTTONDOWN or e.button != 1:
            return True
        if self.close_btn.collidepoint(e.pos) or not self.W.collidepoint(e.pos):
            w.close_modal()
            sfx.play("click")
            return True
        if self.btn.collidepoint(e.pos):
            self.upgrade()
            return True
        it = self.hit(e.pos)
        if it:
            self.item = it
            sfx.play("click", 0.5)
        return True

    def update(self, dt):
        self.t += dt

    # ------------------------------------------------------------------ dessin
    def draw(self, surf):
        W = self.W
        p = self.world.player
        mouse = ui.mouse_pos()
        self.hover = None
        if not self.owned(self.item):
            self.item = None
        ui.botw_box(surf, W, 238, (140, 96, 60), radius=14, fill=(14, 12, 12))
        med = (W.x + 62, W.y + 56)
        ui.glow(surf, med[0], med[1], 56, (110, 50, 16))
        ui.circle(surf, (26, 18, 14), med, 34)
        ui.circle(surf, EMBER, med, 34, 2)
        ui.draw_text(surf, self.name[0], med, 30, WHITE, "title_bold", anchor="center")
        ui.draw_text(surf, self.name, (W.x + 112, W.y + 22), 26, WHITE, "title")
        ui.draw_text(surf, "« Apportez-moi votre équipement : chaque coup de marteau le rend 10% plus redoutable. »",
                     (W.x + 114, W.y + 62), 14, (214, 186, 150))
        ui.draw_text(surf, "Votre bourse", (W.right - 70, W.y + 24), 12, TEXT_DIM, "bold", anchor="topright")
        ui.draw_money(surf, p.money, (W.right - 70, W.y + 56), 20, "midright")
        self.draw_close(surf, mouse)
        ui.line(surf, (74, 56, 42), (W.x + 20, W.y + 100), (W.right - 20, W.y + 100), 1)
        self.draw_items(surf, mouse)
        self.draw_anvil(surf, mouse)
        ui.draw_text(surf, "Clic : poser l'objet sur l'enclume  ·  Échap : fermer", (W.centerx, W.bottom - 20), 12,
                     TEXT_DIM, anchor="center", shadow=False)
        if self.hover and self.hover is not self.item:
            ui.item_tooltip(surf, self.hover, mouse, p)

    def draw_close(self, surf, mouse):
        r = self.close_btn
        hov = r.collidepoint(mouse)
        ui.circle(surf, (60, 30, 26) if hov else (24, 22, 22), r.center, 16)
        ui.circle(surf, (240, 90, 80) if hov else (110, 100, 90), r.center, 16, 1)
        c = r.center
        col = WHITE if hov else SOFT
        ui.line(surf, col, (c[0] - 6, c[1] - 6), (c[0] + 6, c[1] + 6), 2)
        ui.line(surf, col, (c[0] - 6, c[1] + 6), (c[0] + 6, c[1] - 6), 2)

    def cell(self, surf, rc, it, mouse, label=None):
        hov = rc.collidepoint(mouse) and it is not None
        if hov:
            self.hover = it
        if not it:
            ui.rect(surf, (24, 22, 22), rc, 0, 7)
            if label:
                ui.draw_text(surf, label, rc.center, 10, (90, 88, 86), anchor="center", shadow=False)
            return
        col = RARITY_COLORS[it["rarity"]]
        ui.rect(surf, ui.darker(col, 0.3) if it["rarity"] != "commun" else (36, 34, 34), rc, 0, 7)
        ui.rect(surf, WHITE if hov else ui.darker(col, 0.75), rc, 1, 7)
        ui.draw_item_icon(surf, it, rc.inflate(-12, -12), bg=False)
        if it is self.item:
            ui.rect(surf, EMBER, rc.inflate(5, 5), 2, 9)

    def draw_items(self, surf, mouse):
        L = self.left
        p = self.world.player
        ui.draw_text(surf, "Équipé", (L.x + 4, L.y + 2), 15, WHITE, "title")
        for s, rc in self.eq_rects.items():
            self.cell(surf, rc, p.equipment.get(s), mouse, SLOT_NAMES[s][:3])
        top = self.cells[0].y - 30
        ui.draw_text(surf, "Votre sac", (L.x + 4, top), 15, WHITE, "title")
        ui.draw_text(surf, f"{len(p.inventory)} / {BAG_SIZE}", (L.right - 4, top + 4), 13, TEXT_DIM, "bold",
                     anchor="topright", shadow=False)
        for i, rc in enumerate(self.cells):
            self.cell(surf, rc, p.inventory[i] if i < len(p.inventory) else None, mouse)

    def draw_anvil(self, surf, mouse):
        A = self.anvil
        p = self.world.player
        ui.rect(surf, (22, 17, 14), A, 0, 12)
        ui.rect(surf, (90, 64, 42), A, 1, 12)
        it = self.item
        c = (A.centerx, A.y + 86)
        # socle de l'enclume
        ui.polygon(surf, (44, 40, 40), [(c[0] - 120, c[1] + 58), (c[0] + 120, c[1] + 58), (c[0] + 90, c[1] + 74),
                                        (c[0] - 90, c[1] + 74)])
        ui.rect(surf, (60, 56, 56), (c[0] - 130, c[1] + 50, 260, 10), 0, 3)
        if not it:
            ui.circle(surf, (32, 26, 22), c, 48)
            ui.circle(surf, (80, 60, 44), c, 48, 1)
            ui.draw_text(surf, "?", c, 40, (100, 80, 60), "title_bold", anchor="center")
            for j, line in enumerate(ui.wrap("Choisissez un objet porté ou dans votre sac pour le poser sur l'enclume.",
                                             15, A.w - 120)):
                ui.draw_text(surf, line, (A.centerx, c[1] + 110 + j * 22), 15, TEXT_DIM, anchor="center")
            ui.rect(surf, (34, 30, 28), self.btn, 0, self.btn.h // 2)
            ui.draw_text(surf, "Améliorer", self.btn.center, 17, TEXT_DIM, "bold", anchor="center")
            return
        col = RARITY_COLORS[it["rarity"]]
        k = self.t - self.flash
        ui.glow(surf, c[0], c[1], 70 + (40 * max(0.0, 1 - k * 1.5)), ui.darker(col, 0.45))
        box = pygame.Rect(0, 0, 96, 96)
        box.center = c
        ui.rect(surf, ui.darker(col, 0.35), box, 0, 14)
        ui.rect(surf, col, box, 2, 14)
        ui.draw_item_icon(surf, it, box.inflate(-20, -20), bg=False)
        if 0 <= k < 0.8:                              # gerbe d'étincelles après une amélioration
            for i in range(14):
                a = i / 14 * math.tau + 0.3
                d = 50 + k * 140
                ui.circle(surf, (255, 200, 110), (c[0] + math.cos(a) * d, c[1] + math.sin(a) * d * 0.7),
                          max(1.0, 4 * (1 - k / 0.8)))
        u = it.get("upgrade", 0)
        name = it["name"] + (f" +{u}" if u else "")
        ui.draw_text(surf, name, (A.centerx, c[1] + 92), 20, col, "title", anchor="center")
        ui.draw_text(surf, SLOT_NAMES[it["slot"]], (A.centerx, c[1] + 116), 13, TEXT_DIM, anchor="center",
                     shadow=False)
        # niveaux d'amélioration : 5 losanges
        for i in range(MAX_UPGRADE):
            x = A.centerx + (i - (MAX_UPGRADE - 1) / 2) * 30
            y = c[1] + 144
            pts = [(x, y - 9), (x + 8, y), (x, y + 9), (x - 8, y)]
            ui.polygon(surf, EMBER if i < u else (50, 42, 36), pts)
            ui.polygon(surf, (200, 150, 90) if i < u else (90, 76, 62), pts, 1)
        # caractéristiques : actuel -> après
        maxed = u >= MAX_UPGRADE
        nxt = dict(it, upgrade=min(MAX_UPGRADE, u + 1))
        cur = [l for l in item_lines(it) if l[1] in STAT_COLS]
        new = [l for l in item_lines(nxt) if l[1] in STAT_COLS]
        tab = pygame.Rect(A.x + 60, c[1] + 172, A.w - 120, 0)
        ui.draw_text(surf, "ACTUEL", (tab.x, tab.y), 11, (200, 160, 110), "bold", shadow=False)
        if not maxed:
            ui.draw_text(surf, f"APRÈS +{u + 1}", (tab.right, tab.y), 11, (200, 160, 110), "bold", anchor="topright",
                         shadow=False)
        y = tab.y + 22
        for a, b in zip(cur, new):
            if y > self.btn.y - 60:
                break
            ui.draw_text(surf, a[0], (tab.x, y), 14, a[1], shadow=False)
            if not maxed and a[0] != b[0]:
                val = b[0].split(":")[-1].strip() if ":" in b[0] else b[0].split(" ")[0]
                ui.draw_text(surf, val, (tab.right, y), 14, UP, "bold", anchor="topright", shadow=False)
                ui.draw_text(surf, "→", (tab.right - ui.text_size(val, 14, "bold")[0] - 10, y), 14, TEXT_DIM,
                             anchor="topright", shadow=False)
            y += 22
        # coût et bouton
        cost = upgrade_cost(it)
        ok = not maxed and p.money >= cost
        if not maxed:
            ui.draw_text(surf, "Coût", (self.btn.x, self.btn.y - 22), 13, SOFT, "bold", anchor="midleft", shadow=False)
            ui.draw_money(surf, cost, (self.btn.right, self.btn.y - 22), 15, "midright", WHITE if ok else RED)
        b = self.btn
        hov = b.collidepoint(mouse) and ok
        base = (150, 76, 30)
        ui.rect(surf, ui.lighter(base, 1.25) if hov else (base if ok else (40, 36, 34)), b, 0, b.h // 2)
        ui.rect(surf, (255, 200, 140) if hov else ((200, 140, 90) if ok else (80, 70, 60)), b, 1, b.h // 2)
        text = "Niveau maximum" if maxed else ("Améliorer" if p.money >= cost else "Pas assez d'argent")
        ui.draw_text(surf, text, b.center, 18, WHITE if ok else TEXT_DIM, "bold", anchor="center")
        if maxed:
            ui.draw_text(surf, "Cet objet ne peut plus être amélioré.", (b.centerx, b.y - 22), 13, GOLD,
                         anchor="center", shadow=False)
