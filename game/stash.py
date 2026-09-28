"""Coffre de Cendreval : un espace de stockage de plus que le sac, gardé à la taverne.
Clic (gauche ou droit) sur un objet : il passe du coffre au sac, ou l'inverse."""
import pygame

from . import sfx, ui
from .data import BAG_SIZE
from .settings import RARITIES, RARITY_COLORS, TEXT_DIM, WHITE

SOFT = (206, 212, 212)
STASH_SIZE = 60
WOOD = (150, 110, 64)
ORDER = {"arme": 0, "casque": 1, "torse": 2, "gants": 3, "bottes": 4, "amulette": 5, "anneau": 6, "artefact": 7}


class StashScreen:
    """Fenêtre modale du coffre (world.modal)."""
    modal = True
    hide_hud = True
    W = pygame.Rect(40, 60, 1200, 600)

    def __init__(self, world):
        self.world = world
        self.hover = None
        W = self.W
        top = W.y + 104
        step = 50
        self.stash_rects = [pygame.Rect(W.x + 120 + (i % 10) * step, top + 34 + (i // 10) * step, step - 6, step - 6)
                            for i in range(STASH_SIZE)]
        bx = W.x + 120 + 10 * step + 60
        self.bag_rects = [pygame.Rect(bx + (i % 8) * step, top + 34 + (i // 8) * step, step - 6, step - 6)
                          for i in range(BAG_SIZE)]
        self.sort_btn = pygame.Rect(W.x + 120, self.stash_rects[-1].bottom + 22, 160, 36)
        self.close_btn = pygame.Rect(W.right - 52, W.y + 14, 34, 34)

    def move(self, src, i):
        p = self.world.player
        if src == "stash":
            if len(p.inventory) >= BAG_SIZE:
                self.world.message("Votre sac est plein.", (240, 90, 80))
                return
            p.inventory.append(p.stash.pop(i))
        else:
            if len(p.stash) >= STASH_SIZE:
                self.world.message("Le coffre est plein.", (240, 90, 80))
                return
            p.stash.append(p.inventory.pop(i))
        sfx.play("pickup", 0.6)

    def sort(self):
        p = self.world.player
        p.stash.sort(key=lambda it: (-RARITIES.index(it["rarity"]), ORDER.get(it["slot"], 9), -it.get("ilvl", 1)))
        sfx.play("click")

    def hit(self, pos):
        p = self.world.player
        for i, rc in enumerate(self.stash_rects):
            if rc.collidepoint(pos) and i < len(p.stash):
                return "stash", i
        for i, rc in enumerate(self.bag_rects):
            if rc.collidepoint(pos) and i < len(p.inventory):
                return "bag", i
        return None

    def handle_event(self, e):
        w = self.world
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            w.close_modal()
            return True
        if e.type != pygame.MOUSEBUTTONDOWN or e.button not in (1, 3):
            return True
        if e.button == 1 and (self.close_btn.collidepoint(e.pos) or not self.W.collidepoint(e.pos)):
            w.close_modal()
            return True
        if e.button == 1 and self.sort_btn.collidepoint(e.pos):
            self.sort()
            return True
        h = self.hit(e.pos)
        if h:
            self.move(*h)
        return True

    def update(self, dt):
        pass

    def grid(self, surf, rects, items, mouse, src):
        for i, rc in enumerate(rects):
            it = items[i] if i < len(items) else None
            if not it:
                ui.rect(surf, (26, 22, 18), rc, 0, 7)
                continue
            hov = rc.collidepoint(mouse)
            if hov:
                self.hover = (src, it)
            col = RARITY_COLORS[it["rarity"]]
            ui.rect(surf, ui.darker(col, 0.3) if it["rarity"] != "commun" else (38, 34, 30), rc, 0, 7)
            ui.rect(surf, WHITE if hov else ui.darker(col, 0.75), rc, 1, 7)
            ui.draw_item_icon(surf, it, rc.inflate(-12, -12), bg=False)

    def draw(self, surf):
        W = self.W
        p = self.world.player
        mouse = ui.mouse_pos()
        self.hover = None
        ui.botw_box(surf, W, 238, WOOD, radius=14, fill=(16, 13, 11))
        ui.draw_text(surf, "Coffre de la taverne", (W.x + 40, W.y + 24), 26, WHITE, "title")
        ui.draw_text(surf, "Ce que vous y rangez reste en sécurité, même au fond de la tour.", (W.x + 42, W.y + 62),
                     14, (214, 190, 150))
        r = self.close_btn
        hov = r.collidepoint(mouse)
        ui.circle(surf, (60, 30, 26) if hov else (24, 22, 22), r.center, 16)
        ui.circle(surf, (240, 90, 80) if hov else (110, 100, 90), r.center, 16, 1)
        c = r.center
        ui.line(surf, WHITE, (c[0] - 6, c[1] - 6), (c[0] + 6, c[1] + 6), 2)
        ui.line(surf, WHITE, (c[0] - 6, c[1] + 6), (c[0] + 6, c[1] - 6), 2)
        ui.line(surf, (74, 60, 44), (W.x + 20, W.y + 92), (W.right - 20, W.y + 92), 1)
        s0, b0 = self.stash_rects[0], self.bag_rects[0]
        ui.draw_text(surf, "Coffre", (s0.x, s0.y - 30), 17, WHITE, "title")
        ui.draw_text(surf, f"{len(p.stash)} / {STASH_SIZE}", (self.stash_rects[9].right, s0.y - 26), 13, TEXT_DIM,
                     "bold", anchor="topright", shadow=False)
        ui.draw_text(surf, "Sac", (b0.x, b0.y - 30), 17, WHITE, "title")
        ui.draw_text(surf, f"{len(p.inventory)} / {BAG_SIZE}", (self.bag_rects[7].right, b0.y - 26), 13, TEXT_DIM,
                     "bold", anchor="topright", shadow=False)
        mid = (self.stash_rects[9].right + b0.x) // 2
        ui.line(surf, (60, 50, 38), (mid, s0.y - 10), (mid, self.stash_rects[-1].bottom), 1)
        self.grid(surf, self.stash_rects, p.stash, mouse, "stash")
        self.grid(surf, self.bag_rects, p.inventory, mouse, "bag")
        b = self.sort_btn
        hov = b.collidepoint(mouse)
        ui.rect(surf, (60, 44, 30) if hov else (32, 26, 20), b, 0, b.h // 2)
        ui.rect(surf, (200, 160, 110), b, 1, b.h // 2)
        ui.draw_text(surf, "Trier le coffre", b.center, 14, WHITE if hov else SOFT, "bold", anchor="center")
        ui.draw_text(surf, "Clic sur un objet : le ranger ou le reprendre  ·  Échap : fermer",
                     (W.centerx, W.bottom - 20), 12, TEXT_DIM, anchor="center", shadow=False)
        if self.hover:
            src, it = self.hover
            ui.item_tooltip(surf, it, mouse, p, side="left" if src == "bag" else "right")
