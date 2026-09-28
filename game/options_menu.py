"""Écran des options (menu titre et menu Système en jeu) : son, affichage et commandes.

Commandes : clic sur une touche (ou un bouton de la manette) puis appui sur la nouvelle ; Échap annule.
Affichage : mode fenêtre / plein écran et résolution, appliqués tout de suite.
"""
import pygame

from . import controls, display, gamepad, sfx, ui
from .settings import WHITE, SHEIKAH, TEXT_DIM, UI_LINE
from .ui import BOTW_YELLOW

SOFT = (206, 212, 212)
FRAME = (150, 152, 146)
VOLUMES = [("master", "Volume général"), ("music", "Musique"), ("sfx", "Effets sonores")]


class OptionsScreen:
    BOX = pygame.Rect(90, 64, 1100, 600)

    def __init__(self, game, on_close, message=None):
        self.game, self.on_close = game, on_close
        self.message = message or (lambda text: None)      # courte alerte (touche réservée...)
        self.sel = 0
        self.drag = None
        self.binding = None            # ("key" | "pad", action) : en attente d'une touche ou d'un bouton
        self.bind_rects = []
        self.disp_rects = {}
        self.reset_rect = pygame.Rect(0, 0, 0, 0)

    # ------------------------------------------------------------------ géométrie
    def bar(self, i):
        b = self.BOX
        return pygame.Rect(b.x + 40, b.y + 136 + i * 66, 300, 14)

    @staticmethod
    def control_rows():
        """(libellé, action clavier ou None, texte fixe du clavier, action manette ou None)."""
        rows = [("Attaquer", None, "Clic gauche", "attack")]
        rows += [(label, a, None, a if a in controls.pad else None) for a, label, _d, _s in controls.KEY_ACTIONS]
        rows.append(("Menu", None, "Échap", "pause"))
        return rows

    # ------------------------------------------------------------------ actions
    def close(self):
        sfx.save_options()
        self.binding = None
        gamepad.PAD.capture = None
        self.on_close()

    def set_volume(self, pos):
        bar = self.bar(self.drag)
        sfx.set_volume(VOLUMES[self.drag][0], round((pos[0] - bar.x) / bar.w, 2))

    def start_binding(self, kind, action):
        self.binding = (kind, action)
        sfx.play("click")
        if kind == "pad":
            def got(button, action=action):
                controls.bind_pad(action, button)
                self.binding = None
                sfx.play("click")
            gamepad.PAD.capture = got

    def change_display(self, what, d=0):
        full, size = display.current(self.game)
        if what == "mode":
            display.apply(self.game, not full, size if full else None)
        else:
            res = display.available()
            i = min(range(len(res)), key=lambda k: abs(res[k][0] - size[0]) + abs(res[k][1] - size[1]))
            display.apply(self.game, full, res[(i + d) % len(res)])
        sfx.play("click")

    # ------------------------------------------------------------------ événements
    def handle_event(self, e):
        """Toujours vrai : l'écran capte tout tant qu'il est ouvert."""
        if e.type == pygame.KEYDOWN:
            if self.binding:
                kind, action = self.binding
                if e.key == pygame.K_ESCAPE:
                    gamepad.PAD.capture = None
                elif kind == "key" and not controls.bind_key(action, e.scancode):
                    self.message("Cette touche est réservée.")
                self.binding = None
                sfx.play("click")
            elif e.key in (pygame.K_UP, pygame.K_DOWN):
                self.sel = (self.sel + (1 if e.key == pygame.K_DOWN else -1)) % len(VOLUMES)
            elif e.key in (pygame.K_LEFT, pygame.K_RIGHT):
                key = VOLUMES[self.sel][0]
                sfx.set_volume(key, round(sfx.volumes[key] + (0.1 if e.key == pygame.K_RIGHT else -0.1), 2))
                sfx.play("click")
            elif e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close()
            return True
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.drag is not None:
            self.drag = None
            sfx.play("click")
        elif e.type == pygame.MOUSEMOTION and self.drag is not None:
            self.set_volume(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not self.binding:
            for i in range(len(VOLUMES)):
                if self.bar(i).inflate(20, 24).collidepoint(e.pos):
                    self.sel = self.drag = i
                    self.set_volume(e.pos)
                    return True
            for kind, action, rc in self.bind_rects:
                if rc.collidepoint(e.pos):
                    self.start_binding(kind, action)
                    return True
            for (what, d), rc in self.disp_rects.items():
                if rc.collidepoint(e.pos):
                    self.change_display(what, d)
                    return True
            if self.reset_rect.collidepoint(e.pos):
                controls.reset()
                sfx.play("click")
                return True
            if not self.BOX.collidepoint(e.pos):
                self.close()
        return True

    # ------------------------------------------------------------------ dessin
    def draw(self, surf):
        ui.veil(surf, (0, 0, 0), 200)
        box = ui.botw_box(surf, self.BOX, 255, FRAME, radius=4, fill=(12, 16, 20))
        ui.draw_text(surf, "Options", (box.centerx, box.y + 16), 22, WHITE, "title", anchor="midtop")
        ui.rect(surf, (110, 112, 108), (box.x + 24, box.y + 54, box.w - 48, 1))
        mouse = ui.mouse_pos()
        self.draw_sound(surf, box, mouse)
        self.draw_display(surf, box, mouse)
        self.draw_controls(surf, box, mouse)
        self.reset_rect = pygame.Rect(box.x + 40, box.bottom - 58, 300, 36)
        hov = self.reset_rect.collidepoint(mouse)
        ui.botw_box(surf, self.reset_rect, 200 if hov else 130, SHEIKAH if hov else (100, 102, 100), radius=18,
                    fill=(16, 44, 56) if hov else (0, 0, 0))
        ui.draw_text(surf, "Commandes par défaut", self.reset_rect.center, 14, WHITE, "bold", anchor="center")
        if self.binding:
            msg = "Appuyez sur une touche" if self.binding[0] == "key" else "Appuyez sur un bouton de la manette"
            ui.draw_text(surf, msg, (box.x + 40, box.bottom - 86), 15, BOTW_YELLOW, "bold")

    def draw_sound(self, surf, box, mouse):
        ui.draw_text(surf, "Son", (box.x + 40, box.y + 70), 18, BOTW_YELLOW, "title")
        for i, (key, label) in enumerate(VOLUMES):
            bar = self.bar(i)
            if bar.inflate(20, 24).collidepoint(mouse) and self.drag is None:
                self.sel = i
            sel = i == self.sel
            ui.draw_text(surf, label, (bar.x, bar.y - 20), 16, WHITE if sel else SOFT, "title", anchor="midleft")
            v = sfx.volumes[key]
            ui.rect(surf, (0, 0, 0, 200), bar.inflate(4, 4), 0, 8)
            ui.rect(surf, (60, 64, 66), bar, 0, 7)
            if v > 0:
                ui.rect(surf, BOTW_YELLOW if sel else (200, 200, 190), (bar.x, bar.y, max(6, bar.w * v), bar.h), 0, 7)
            ui.circle(surf, WHITE, (bar.x + bar.w * v, bar.centery), 10)
            ui.draw_text(surf, f"{int(round(v * 100))} %", (bar.right + 42, bar.centery), 15, WHITE, "bold",
                         anchor="center")

    def draw_display(self, surf, box, mouse):
        y0 = box.y + 330
        ui.draw_text(surf, "Affichage", (box.x + 40, y0), 18, BOTW_YELLOW, "title")
        full, size = display.current(self.game)
        rows = [("mode", "Mode", "Plein écran" if full else "Fenêtre"),
                ("size", "Résolution", f"{size[0]} × {size[1]}")]
        self.disp_rects = {}
        for i, (what, label, val) in enumerate(rows):
            y = y0 + 52 + i * 48
            ui.draw_text(surf, label, (box.x + 40, y), 16, SOFT, "title", anchor="midleft")
            field = pygame.Rect(box.x + 170, y - 16, 230, 32)
            ui.rect(surf, (0, 0, 0, 160), field, 0, 6)
            ui.rect(surf, (80, 84, 84), field, 1, 6)
            ui.draw_text(surf, val, field.center, 15, WHITE, "bold", anchor="center")
            for d, cx in ((-1, field.x + 18), (1, field.right - 18)):
                rc = pygame.Rect(cx - 14, y - 14, 28, 28)
                hov = rc.collidepoint(mouse)
                col = BOTW_YELLOW if hov else WHITE
                ui.polygon(surf, col, [(cx - d * 4, y - 7), (cx + d * 5, y), (cx - d * 4, y + 7)])
                self.disp_rects[(what, d)] = rc

    def draw_controls(self, surf, box, mouse):
        x0 = box.x + 440
        cols = (x0 + 14, x0 + 330, x0 + 500)            # action, clavier, manette
        ui.draw_text(surf, "Commandes", (x0, box.y + 70), 18, BOTW_YELLOW, "title")
        ui.draw_text(surf, "Clavier", (cols[1], box.y + 76), 13, SOFT, "bold", anchor="midtop")
        pad_title = "Manette" + ("" if gamepad.PAD.connected else " (non branchée)")
        ui.draw_text(surf, pad_title, (cols[2], box.y + 76), 13, SOFT, "bold", anchor="midtop")
        self.bind_rects = []
        y = box.y + 100
        for i, (label, key_act, fixed, pad_act) in enumerate(self.control_rows()):
            row = pygame.Rect(x0, y, box.right - 24 - x0, 21)
            if i % 2 == 0:
                ui.rect(surf, (40, 60, 70, 70), row, 0, 4)
            ui.draw_text(surf, label, (cols[0], row.centery), 14, SOFT, anchor="midleft")
            for kind, act, cx, text in (("key", key_act, cols[1], fixed), ("pad", pad_act, cols[2], None)):
                if act is None and text is None:
                    continue
                if act is None:
                    ui.draw_text(surf, text, (cx, row.centery), 13, TEXT_DIM, "bold", anchor="center")
                    continue
                waiting = self.binding == (kind, act)
                val = "..." if waiting else (controls.label(act) if kind == "key" else controls.pad_label(act))
                rc = pygame.Rect(0, 0, 130, 19)
                rc.center = (cx, row.centery)
                hov = rc.collidepoint(mouse) and not self.binding
                ui.rect(surf, (60, 90, 100, 200) if hov or waiting else (0, 0, 0, 150), rc, 0, 5)
                ui.rect(surf, BOTW_YELLOW if waiting else (UI_LINE if hov else (80, 84, 84)), rc, 1, 5)
                ui.draw_text(surf, val, rc.center, 13, BOTW_YELLOW if waiting else WHITE, "bold", anchor="center")
                self.bind_rects.append((kind, act, rc))
            y += 22

