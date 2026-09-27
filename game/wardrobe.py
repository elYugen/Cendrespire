"""Personnalisation de l'apparence : éditeur d'options (création du héros) et garde-robe du campement."""
import random

import pygame

from . import looks, sfx, ui
from .settings import SCREEN_W, SCREEN_H, WHITE, SHEIKAH

SOFT = (206, 212, 212)
FRAME = (150, 152, 146)


class LookEditor:
    """Liste d'options façon BotW : « libellé   ◂ valeur ▸ ». Souris (clic, clic droit, molette) ou clavier
    (haut / bas pour choisir la ligne, gauche / droite pour changer la valeur)."""
    ROW_H = 42

    def __init__(self, rect, look, cls_id):
        self.rect = pygame.Rect(rect)
        self.look = look
        self.cls_id = cls_id
        self.sel = 0
        self.t = 0.0
        self.rows = [pygame.Rect(self.rect.x, self.rect.y + i * self.ROW_H, self.rect.w, self.ROW_H - 6)
                     for i in range(len(looks.OPTIONS))]

    @property
    def options(self):
        return looks.options_for(self.cls_id)

    def arrows(self, rc):
        return pygame.Rect(rc.right - 250, rc.y, 34, rc.h), pygame.Rect(rc.right - 38, rc.y, 34, rc.h)

    def change(self, i, d):
        key, _, values = self.options[i]
        self.look[key] = (self.look[key] + d) % len(values)
        self.sel = i
        sfx.play("click")

    def randomize(self):
        self.look.update(looks.random_look(self.cls_id, random))
        sfx.play("magic", 0.5)

    def row_at(self, pos):
        return next((i for i, rc in enumerate(self.rows[:len(self.options)]) if rc.collidepoint(pos)), None)

    def handle_event(self, e):
        n = len(self.options)
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_UP or e.scancode == 26:
                self.sel = (self.sel - 1) % n
            elif e.key == pygame.K_DOWN or e.scancode == 22:
                self.sel = (self.sel + 1) % n
            elif e.key == pygame.K_LEFT or e.scancode == 4:
                self.change(self.sel, -1)
            elif e.key == pygame.K_RIGHT or e.scancode == 7:
                self.change(self.sel, 1)
            else:
                return False
            return True
        if e.type == pygame.MOUSEWHEEL:
            i = self.row_at(ui.mouse_pos())
            if i is not None:
                self.change(i, -e.y)
                return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            i = self.row_at(e.pos)
            if i is None:
                return False
            left, right = self.arrows(self.rows[i])
            self.change(i, -1 if left.collidepoint(e.pos) or e.button == 3 else 1)
            return True
        return False

    def draw(self, surf, t):
        mouse = ui.mouse_pos()
        for i, (rc, (key, label, values)) in enumerate(zip(self.rows, self.options)):
            hov = rc.collidepoint(mouse)
            if hov:
                self.sel = i
            sel = i == self.sel
            ui.botw_box(surf, rc, 190 if sel else 120, WHITE if sel else FRAME, radius=4,
                        fill=(20, 40, 50) if sel else (0, 0, 0))
            if key == "headgear":
                label = looks.HEADGEAR_NAMES[self.cls_id]
            ui.draw_text(surf, label, (rc.x + 18, rc.centery), 17, WHITE if sel else SOFT, "title", anchor="midleft")
            left, right = self.arrows(rc)
            for d, ar in ((-1, left), (1, right)):
                col = WHITE if ar.collidepoint(mouse) else ((200, 204, 200) if sel else (110, 114, 112))
                x = ar.centerx - d * 4
                ui.polygon(surf, col, [(x, rc.centery - 7), (x + d * 9, rc.centery), (x, rc.centery + 7)])
            idx = self.look[key]
            name = looks.value_name(key, idx)
            col = looks.value_color(key, idx)
            mid = (left.right + right.x) // 2
            if col:
                tw, _ = ui.text_size(name, 16)
                ui.circle(surf, col, (mid - tw / 2 - 10, rc.centery), 8)
                ui.circle(surf, WHITE, (mid - tw / 2 - 10, rc.centery), 8, 1)
                ui.draw_text(surf, name, (mid + 8, rc.centery), 16, WHITE, anchor="center")
            else:
                ui.draw_text(surf, name, (mid, rc.centery), 16, WHITE, anchor="center")
            # position dans la liste : petits points sous la valeur
            if sel and len(values) <= 14:
                for j in range(len(values)):
                    ui.circle(surf, WHITE if j == idx else (90, 94, 92),
                              (mid + (j - (len(values) - 1) / 2) * 7, rc.bottom - 5), 1.6 if j == idx else 1.2)
            if sel:
                ui.selection_frame(surf, rc, t, WHITE)


class WardrobePanel:
    """Garde-robe du campement (plein écran, jeu en pause) : héros en 3D à gauche, options à droite."""
    modal = True
    fullscreen = True

    def __init__(self, world):
        self.world = world
        p = world.player
        self.rect = pygame.Rect(0, 0, SCREEN_W, SCREEN_H)
        self.original = dict(p.look)
        self.editor = LookEditor((690, 130, 520, 0), p.look, p.cls_id)
        self.t = 0.0
        self.rot = 0.0
        self.drag = None
        y = SCREEN_H - 118
        self.buttons = [ui.Button((690, y, 160, 44), "Aléatoire", self.editor.randomize, 17),
                        ui.Button((870, y, 160, 44), "Annuler", self.cancel, 17),
                        ui.Button((1050, y, 160, 44), "Valider", self.confirm, 17)]

    def portrait_spot(self):
        return 360, 390, 1.35

    def cancel(self):
        self.world.player.look.clear()
        self.world.player.look.update(self.original)
        self.world.close_modal()

    def confirm(self):
        self.world.save()
        self.world.message("Nouvelle apparence enregistrée.", SHEIKAH)
        self.world.close_modal()
        sfx.play("levelup", 0.4)

    def contains(self, pos):
        return True

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.cancel()
            return True
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.confirm()
            return True
        if any(b.handle(e) for b in self.buttons) or self.editor.handle_event(e):
            return True
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and e.pos[0] < 640:
            self.drag = e.pos[0]
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            self.drag = None
        elif e.type == pygame.MOUSEMOTION and self.drag is not None:
            self.rot += (e.pos[0] - self.drag) * 0.012
            self.drag = e.pos[0]
        return True

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        ui.rect(surf, (0, 0, 0, 80), (0, 0, SCREEN_W, 108))
        ui.rect(surf, (210, 210, 200, 70), (0, 108, SCREEN_W, 1))
        ui.draw_text(surf, "Garde-robe", (SCREEN_W // 2, 52), 30, WHITE, "title", anchor="center")
        ui.draw_text(surf, "Ysolde la Couturière", (SCREEN_W // 2, 80), 15, SOFT, anchor="center")
        self.editor.draw(surf, self.t)
        for b in self.buttons:
            b.draw(surf)
        ui.draw_text(surf, "Glisser : pivoter le héros", (360, SCREEN_H - 60), 14, SOFT, anchor="center")
        ui.draw_text(surf, "Haut / bas : option   ·   Gauche / droite : valeur   ·   Entrée : valider   ·   Échap : annuler",
                     (SCREEN_W - 40, SCREEN_H - 24), 13, (150, 160, 160), anchor="bottomright")

    def draw_tooltips(self, surf):
        pass
