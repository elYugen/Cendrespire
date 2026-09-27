"""Tutoriel guidé des nouveaux héros (option « Tutoriel » à la création du personnage).

À la première arrivée à Cendreval, une carte en haut de l'écran présente une action à la fois ; l'étape se valide
d'elle-même quand le joueur l'a faite. L'étape en cours est enregistrée dans la sauvegarde (player.tutorial) :
on reprend où on s'était arrêté, et le tutoriel disparaît une fois terminé ou passé.
"""
import math

import pygame

from . import sfx, ui
from .settings import SCREEN_W, GOLD_BRIGHT, SHEIKAH, WHITE

SOFT = (206, 212, 212)
DONE = (140, 235, 140)


def _moved(w, t):
    sx, sy = t.origin
    return math.hypot(w.player.x - sx, w.player.y - sy) > 160


def _menu(w, t):
    from .panels import MenuScreen
    return isinstance(w.modal, MenuScreen)


def _portal(w, t):
    from .panels import PortalPanel
    return isinstance(w.modal, PortalPanel)


# (titre, texte, touches affichées, condition de réussite)
STEPS = [
    ("Se déplacer", "Marchez dans les rues de Cendreval : touches ZQSD (ou les flèches), ou clic gauche sur le sol.",
     ["Z", "Q", "S", "D"], _moved),
    ("Attaquer", "Maj + clic gauche : frapper sur place. Sur un ennemi, un simple clic suffit : votre héros "
     "s'en approche et attaque tout seul.", ["Maj", "Clic gauche"], lambda w, t: w.player.atk_cd > 0),
    ("Esquiver", "Espace : roulade. Vous êtes invulnérable pendant un court instant, idéal contre les attaques "
     "annoncées au sol.", ["Espace"], lambda w, t: w.player.roll_cd > 0),
    ("Sorts, potion et artefacts", "Clic droit et 1 à 4 lancent vos sorts, F boit la potion de soin, R, T et G "
     "activent vos artefacts. Essayez un sort.", ["Clic droit", "1", "F"],
     lambda w, t: any(v > 0 for v in w.player.cds.values()) or w.player.potion_cd > 0),
    ("Le menu", "I ouvre l'inventaire, C le personnage, N les talents, J le journal de quêtes. Gagnez des niveaux pour débloquer points "
     "de caractéristique et talents.", ["I", "C", "N"], _menu),
    ("Les habitants", "Approchez-vous d'un habitant et appuyez sur E pour lui parler. Un « ! » doré au-dessus de "
     "sa tête : il a une quête pour vous.", ["E"], lambda w, t: "talk" in t.flags),
    ("La carte", "Tab affiche la carte de la ville (et de l'étage, dans la tour).", ["Tab"],
     lambda w, t: w.big_map),
    ("La Tour", "Au-delà de la porte nord, le grand portail mène aux étages de Cendrespire. Éliminez les "
     "créatures pour briser le sceau du gardien, puis terrassez-le.", ["E"], _portal),
]


class Tutorial:
    W, H = 600, 108

    def __init__(self, world):
        self.world = world
        self.origin = (world.player.x, world.player.y)
        self.flags = set()
        self.done_t = None          # délai d'affichage de l'étape réussie avant la suivante
        self.t = 0.0
        self.rect = pygame.Rect(SCREEN_W // 2 - self.W // 2, 16, self.W, self.H)
        self.skip_rect = pygame.Rect(self.rect.right - 92, self.rect.y + 10, 80, 24)

    @property
    def step(self):
        return self.world.player.tutorial

    def update(self, dt):
        self.t += dt
        w = self.world
        if self.step is None:
            return
        if self.done_t is None:
            if STEPS[self.step][3](w, self):
                self.done_t = 1.2
                sfx.play("pickup", 0.8)
        else:
            self.done_t -= dt
            if self.done_t <= 0 and not w.modal:
                self.done_t = None
                self.next()

    def next(self):
        p = self.world.player
        p.tutorial += 1
        self.origin = (p.x, p.y)
        if p.tutorial >= len(STEPS):
            self.finish("Tutoriel terminé", "Bonne ascension, " + p.name)
        self.world.save()

    def finish(self, title, sub):
        self.world.player.tutorial = None
        self.world.show_banner(title, sub, GOLD_BRIGHT, 4)
        sfx.play("levelup", 0.7)
        self.world.save()

    def contains(self, pos):
        return self.step is not None and self.rect.collidepoint(pos)

    def handle_event(self, e):
        if self.step is None:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if self.skip_rect.collidepoint(e.pos):
                self.finish("Tutoriel passé", "Les commandes restent dans Système > Commandes")
            return True
        return False

    def draw(self, surf):
        if self.step is None:
            return
        title, text, keys, _ = STEPS[self.step]
        ok = self.done_t is not None
        r = self.rect
        k = 0.5 + 0.5 * math.sin(self.t * 3)
        ui.botw_box(surf, r, 200, DONE if ok else SHEIKAH, radius=12, fill=(8, 22, 30))
        ui.draw_text(surf, f"TUTORIEL  {self.step + 1} / {len(STEPS)}", (r.x + 18, r.y + 10), 12,
                     SHEIKAH, "bold")
        hov = self.skip_rect.collidepoint(ui.mouse_pos())
        ui.botw_box(surf, self.skip_rect, 180 if hov else 110, SHEIKAH if hov else (110, 112, 110), radius=12)
        ui.draw_text(surf, "Passer", self.skip_rect.center, 12, WHITE if hov else SOFT, anchor="center",
                     shadow=False)
        ui.draw_text(surf, ("Bravo ! " if ok else "") + title, (r.x + 18, r.y + 28), 20, DONE if ok else WHITE,
                     "title")
        y = r.y + 56
        for line in ui.wrap(text, 14, r.w - 36)[:2]:
            ui.draw_text(surf, line, (r.x + 18, y), 14, SOFT)
            y += 19
        # progression : une pastille par étape
        for i in range(len(STEPS)):
            c = (r.centerx - (len(STEPS) - 1) * 9 + i * 18, r.bottom - 1)
            col = DONE if i < self.step or (i == self.step and ok) else (SHEIKAH if i == self.step else (70, 74, 72))
            ui.circle(surf, col, c, 4 if i == self.step else 3)
        x = r.x + 18 + ui.text_size(("Bravo ! " if ok else "") + title, 20, "title")[0] + 16
        for key in keys:
            kw, kh = ui.text_size(key, 11, "bold")
            bw = max(kh + 2, kw + 10)
            if x + bw > self.skip_rect.x - 8:
                break
            ui.key_badge(surf, key, (x + bw / 2, r.y + 41), 11, DONE if ok else ui.lighter(GOLD_BRIGHT, 1 + 0.15 * k))
            x += bw + 6
