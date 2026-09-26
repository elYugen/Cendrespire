"""Écrans hors-jeu : titre, chargement, création de personnage."""
import math
import random

import pygame

from . import render, save, sfx
from .data import CLASSES, SPELLS, ATTR_NAMES, ATTRS
from .entities import Player
from .fx import glow
from .settings import SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, GOLD, GOLD_BRIGHT, RED, TITLE
from .ui import draw_text, draw_panel, Button, wrap
from .world import Scene

NAMES = ["Aldric", "Morwen", "Kaelen", "Sybille", "Thorgar", "Ysolde", "Varian", "Lyra", "Garrosh", "Elowen"]


class Backdrop:
    """Fond animé : silhouette de la tour, braises, lueur rouge."""

    def __init__(self):
        self.embers = []
        self.t = 0.0
        self.bg = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            k = y / SCREEN_H
            pygame.draw.line(self.bg, (int(10 + 40 * k), int(6 + 8 * k), int(10 + 4 * k)), (0, y), (SCREEN_W, y))
        rng = random.Random(4)
        # montagnes
        pts = [(0, SCREEN_H)]
        x = 0
        while x <= SCREEN_W:
            pts.append((x, SCREEN_H - 170 - rng.randint(0, 90)))
            x += 60
        pts.append((SCREEN_W, SCREEN_H))
        pygame.draw.polygon(self.bg, (14, 8, 10), pts)
        # tour
        cx = SCREEN_W // 2
        tw = 120
        pygame.draw.polygon(self.bg, (6, 3, 5), [(cx - tw, SCREEN_H), (cx - 70, 140), (cx + 70, 140), (cx + tw, SCREEN_H)])
        for i in range(7):
            x0 = cx - 80 + i * 26
            pygame.draw.rect(self.bg, (6, 3, 5), (x0, 118, 16, 26))
        pygame.draw.polygon(self.bg, (6, 3, 5), [(cx - 18, 118), (cx, 40), (cx + 18, 118)])
        self.windows = [(cx + rng.randint(-50, 50), rng.randint(200, SCREEN_H - 80)) for _ in range(9)]

    def update(self, dt):
        self.t += dt
        if random.random() < 0.6:
            self.embers.append([random.uniform(0, SCREEN_W), SCREEN_H + 5, random.uniform(-20, 20),
                                random.uniform(-80, -30), random.uniform(3, 7)])
        for e in self.embers:
            e[0] += e[2] * dt + math.sin(self.t * 2 + e[1] * 0.01) * 0.4
            e[1] += e[3] * dt
            e[4] -= dt
        self.embers = [e for e in self.embers if e[4] > 0]

    def draw(self, surf):
        surf.blit(self.bg, (0, 0))
        k = 0.5 + 0.5 * math.sin(self.t * 1.3)
        glow(surf, SCREEN_W // 2, 60, 120 + 20 * k, (120, 20, 10))
        for i, (x, y) in enumerate(self.windows):
            f = 0.6 + 0.4 * math.sin(self.t * 3 + i)
            glow(surf, x, y, 10, (int(200 * f), int(80 * f), 20))
        for e in self.embers:
            glow(surf, e[0], e[1], 5, (int(40 * e[4]), int(12 * e[4]), 0))


class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bd = Backdrop()
        self.saves = save.list_saves()
        cx = SCREEN_W // 2
        self.buttons = []
        y = 420
        if self.saves:
            last = self.saves[0]
            self.buttons.append(Button((cx - 170, y, 340, 48), f"Continuer ({last['name']})",
                                       lambda: self.start(last), 20))
            y += 60
            self.buttons.append(Button((cx - 170, y, 340, 48), "Charger un personnage",
                                       lambda: game.change_scene(LoadScene(game)), 20))
            y += 60
        self.buttons.append(Button((cx - 170, y, 340, 48), "Nouveau personnage",
                                   lambda: game.change_scene(CreateScene(game)), 20))
        y += 60
        self.buttons.append(Button((cx - 170, y, 340, 48), "Quitter", game.quit, 20))

    def start(self, data):
        from .hub import HubScene
        p = Player(data)
        self.game.change_scene(HubScene(self.game, p, f"Bon retour, {p.name}."))

    def handle_event(self, e):
        for b in self.buttons:
            if b.handle(e):
                return

    def update(self, dt):
        self.bd.update(dt)

    def draw(self, surf):
        self.bd.draw(surf)
        draw_text(surf, "TOUR DES", (SCREEN_W // 2, 200), 38, GOLD, "title", anchor="center")
        draw_text(surf, "TOURMENTS", (SCREEN_W // 2, 262), 76, (200, 40, 30), "title", anchor="center")
        draw_text(surf, "Gravissez la tour. Brisez les sceaux. Terrassez les gardiens.", (SCREEN_W // 2, 330), 18,
                  TEXT_DIM, anchor="center")
        for b in self.buttons:
            b.draw(surf)
        draw_text(surf, "v1.0 — pygame", (SCREEN_W - 14, SCREEN_H - 10), 13, TEXT_DIM, anchor="bottomright")


class LoadScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bd = Backdrop()
        self.refresh()

    def refresh(self):
        self.saves = save.list_saves()[:7]
        self.rows = []
        cx = SCREEN_W // 2
        for i, d in enumerate(self.saves):
            r = pygame.Rect(cx - 330, 150 + i * 66, 560, 58)
            self.rows.append((r, d, Button((r.right + 10, r.y + 9, 90, 40), "Suppr.", lambda d=d: self.delete(d), 16)))
        self.back = Button((cx - 100, SCREEN_H - 80, 200, 44), "Retour", lambda: self.game.change_scene(TitleScene(self.game)))
        self.confirm = None

    def delete(self, d):
        if self.confirm is d:
            save.delete(d["name"])
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
                self.game.change_scene(HubScene(self.game, p, f"Bon retour, {p.name}."))
                return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.change_scene(TitleScene(self.game))

    def update(self, dt):
        self.bd.update(dt)

    def draw(self, surf):
        self.bd.draw(surf)
        draw_panel(surf, (SCREEN_W // 2 - 360, 70, 720, 580), "Choisir un personnage")
        mouse = pygame.mouse.get_pos()
        for r, d, b in self.rows:
            hov = r.collidepoint(mouse)
            pygame.draw.rect(surf, (50, 34, 22) if hov else (24, 18, 14), r)
            pygame.draw.rect(surf, GOLD if hov else (90, 70, 40), r, 1)
            c = CLASSES[d["cls"]]
            pygame.draw.circle(surf, c["color"], (r.x + 30, r.centery), 16)
            draw_text(surf, d["name"], (r.x + 60, r.y + 6), 20, GOLD_BRIGHT)
            draw_text(surf, f"{c['name']} niveau {d.get('level', 1)}  ·  Étage max {d.get('max_floor', 1)}  ·  "
                            f"{d.get('gold', 0)} or", (r.x + 60, r.y + 32), 14, TEXT_DIM)
            b.text = "Sûr ?" if self.confirm is d else "Suppr."
            b.draw(surf)
        if not self.rows:
            draw_text(surf, "Aucune sauvegarde.", (SCREEN_W // 2, 300), 18, TEXT_DIM, anchor="center")
        self.back.draw(surf)


class CreateScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.bd = Backdrop()
        self.name = random.choice(NAMES)
        self.cls = "barbare"
        self.t = 0.0
        self.error = ""
        self.cards = {cid: pygame.Rect(90 + i * 370, 170, 350, 400) for i, cid in enumerate(CLASSES)}
        self.name_rect = pygame.Rect(SCREEN_W // 2 - 180, 100, 360, 44)
        self.go = Button((SCREEN_W // 2 + 40, SCREEN_H - 90, 260, 52), "Entrer dans la Tour", self.create, 22)
        self.back = Button((SCREEN_W // 2 - 300, SCREEN_H - 90, 260, 52), "Retour",
                           lambda: game.change_scene(TitleScene(game)), 20)

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
            for cid, r in self.cards.items():
                if r.collidepoint(e.pos):
                    self.cls = cid
                    sfx.play("click")
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif e.key == pygame.K_RETURN:
                self.create()
            elif e.key == pygame.K_ESCAPE:
                self.game.change_scene(TitleScene(self.game))
        elif e.type == pygame.TEXTINPUT:
            if len(self.name) < 16 and (e.text.isalnum() or e.text in " -'"):
                self.name += e.text
                self.error = ""

    def update(self, dt):
        self.bd.update(dt)
        self.t += dt

    def draw(self, surf):
        self.bd.draw(surf)
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 120))
        surf.blit(veil, (0, 0))
        draw_text(surf, "Création du personnage", (SCREEN_W // 2, 50), 32, GOLD, "title", anchor="center")
        r = self.name_rect
        pygame.draw.rect(surf, (20, 15, 12), r)
        pygame.draw.rect(surf, GOLD, r, 2)
        cursor = "|" if int(self.t * 2) % 2 else ""
        draw_text(surf, self.name + cursor, r.center, 22, GOLD_BRIGHT, anchor="center")
        draw_text(surf, "Nom :", (r.x - 12, r.centery), 18, TEXT, anchor="midright")
        mouse = pygame.mouse.get_pos()
        for cid, rc in self.cards.items():
            c = CLASSES[cid]
            sel = cid == self.cls
            hov = rc.collidepoint(mouse)
            draw_panel(surf, rc, alpha=235, border=c["color"] if sel else (90, 70, 44))
            if sel:
                pygame.draw.rect(surf, c["color"], rc, 3)
            # portrait animé
            fx, fy = rc.x + 80, rc.y + 150
            glow(surf, fx, fy - 40, 80 if sel else 50, tuple(v // 3 for v in c["color"]))
            render.shadow(surf, fx, fy, 30)
            glows = []
            ph = self.t * 6 if sel else 0
            render.draw_humanoid(surf, fx, fy, 2.4, math.pi / 2 + 0.4 * math.sin(self.t), ph,
                                 render.PLAYER_SPECS[cid], glows=glows)
            for gx, gy, gc, gr in glows:
                glow(surf, gx, gy, gr, gc)
            draw_text(surf, c["name"], (rc.x + 160, rc.y + 40), 26, GOLD_BRIGHT if sel or hov else GOLD, "title")
            draw_text(surf, c["title"], (rc.x + 160, rc.y + 74), 14, TEXT_DIM)
            y = rc.y + 100
            for a in ATTRS:
                v = c["attrs"][a]
                draw_text(surf, ATTR_NAMES[a][:3], (rc.x + 160, y), 13, TEXT_DIM)
                pygame.draw.rect(surf, (40, 30, 24), (rc.x + 200, y + 4, 120, 7))
                pygame.draw.rect(surf, c["color"], (rc.x + 200, y + 4, 120 * v / 24, 7))
                y += 18
            y = rc.y + 190
            for line in wrap(c["desc"], 15, rc.w - 40):
                draw_text(surf, line, (rc.x + 20, y), 15, TEXT)
                y += 20
            y += 10
            draw_text(surf, "Sorts :", (rc.x + 20, y), 15, GOLD)
            y += 22
            for sid in c["spells"]:
                sp = SPELLS[sid]
                draw_text(surf, f"Niv {sp['level']:>2}  {sp['name']}", (rc.x + 28, y), 14, sp["color"])
                y += 19
        if self.error:
            draw_text(surf, self.error, (SCREEN_W // 2, SCREEN_H - 118), 16, RED, anchor="center")
        self.go.draw(surf)
        self.back.draw(surf)
