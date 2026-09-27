"""Pictogrammes dessinés (coordonnées de conception) : sorts, attaques de base et talents."""
import math

import pygame

from . import ui
from .data import CLASSES, SPELLS

# pictogrammes choisis dans data/spells.json (« icon ») et data/classes.json (attack.icon)
SPELL_GLYPH = {sid: sp.get("icon", "star") for sid, sp in SPELLS.items()}
ATTACK_GLYPH = {cid: c["attack"].get("icon", "sword") for cid, c in CLASSES.items()}


def _star(surf, c, r, col, n=5, inner=0.45, rot=-math.pi / 2):
    pts = []
    for i in range(n * 2):
        a = rot + i * math.pi / n
        rr = r if i % 2 == 0 else r * inner
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    ui.polygon(surf, col, pts)


def glyph(surf, kind, c, s, col):
    """Dessine un pictogramme de rayon ~s centré en c."""
    x, y = c
    w = max(2, s * 0.16)
    if kind == "whirl":
        for i in range(3):
            a0 = i * math.tau / 3
            ui.arc(surf, col, pygame.Rect(x - s * 0.8, y - s * 0.8, s * 1.6, s * 1.6), a0, a0 + 1.6, max(2, int(w)))
        ui.circle(surf, col, c, s * 0.2)
    elif kind == "shout":
        ui.polygon(surf, col, [(x - s * 0.7, y - s * 0.25), (x - s * 0.3, y - s * 0.25), (x + s * 0.2, y - s * 0.7),
                               (x + s * 0.2, y + s * 0.7), (x - s * 0.3, y + s * 0.25), (x - s * 0.7, y + s * 0.25)])
        for i, rr in enumerate((0.45, 0.75)):
            ui.arc(surf, col, pygame.Rect(x - s * rr + s * 0.3, y - s * rr, s * rr * 2, s * rr * 2), -0.8, 0.8,
                   max(2, int(w * 0.8)))
    elif kind == "leap":
        ui.arc(surf, col, pygame.Rect(x - s * 0.8, y - s * 0.5, s * 1.6, s * 1.4), 0.3, math.pi - 0.3, max(2, int(w)))
        ui.polygon(surf, col, [(x + s * 0.72, y + s * 0.1), (x + s * 0.9, y - s * 0.3), (x + s * 0.45, y - s * 0.12)])
        ui.line(surf, col, (x - s * 0.9, y + s * 0.7), (x + s * 0.9, y + s * 0.7), max(2, int(w)))
    elif kind == "quake":
        ui.lines(surf, col, False, [(x - s * 0.9, y + s * 0.5), (x - s * 0.4, y), (x - s * 0.05, y + s * 0.35),
                                    (x + s * 0.35, y - s * 0.45), (x + s * 0.9, y + s * 0.2)], max(2, int(w)))
        ui.line(surf, col, (x - s * 0.9, y + s * 0.75), (x + s * 0.9, y + s * 0.75), max(2, int(w * 0.7)))
    elif kind in ("flame", "meteor"):
        if kind == "meteor":
            for i in range(3):
                ui.line(surf, col, (x - s * (0.9 - i * 0.15), y - s * (0.85 - i * 0.25)), (x - s * 0.1, y - s * 0.05),
                        max(1, int(w * 0.6)))
            ui.circle(surf, col, (x + s * 0.15, y + s * 0.2), s * 0.45)
        else:
            ui.polygon(surf, col, [(x, y - s * 0.9), (x + s * 0.55, y), (x + s * 0.45, y + s * 0.55), (x, y + s * 0.8),
                                   (x - s * 0.45, y + s * 0.55), (x - s * 0.55, y), (x - s * 0.15, y - s * 0.2)])
            ui.polygon(surf, (255, 255, 255), [(x, y - s * 0.1), (x + s * 0.22, y + s * 0.35), (x, y + s * 0.6),
                                               (x - s * 0.22, y + s * 0.35)])
    elif kind == "snow":
        for i in range(3):
            a = i * math.pi / 3
            dx, dy = math.cos(a) * s * 0.85, math.sin(a) * s * 0.85
            ui.line(surf, col, (x - dx, y - dy), (x + dx, y + dy), max(2, int(w)))
        ui.circle(surf, col, c, s * 0.18)
    elif kind in ("blink", "shadow"):
        for i in range(3):
            k = 1 - i * 0.28
            ui.circle(surf, col, (x - s * 0.5 + i * s * 0.5, y), s * 0.3 * k, 0 if i == 2 else max(1, int(w * 0.6)))
        if kind == "shadow":
            ui.line(surf, col, (x + s * 0.2, y - s * 0.8), (x + s * 0.8, y + s * 0.2), max(2, int(w)))
    elif kind == "fan":
        for i in range(5):
            a = -math.pi / 2 + (i - 2) * 0.35
            ui.line(surf, col, (x, y + s * 0.7), (x + math.cos(a) * s * 0.95, y + s * 0.7 + math.sin(a) * s * 1.4),
                    max(1, int(w * 0.7)))
    elif kind == "fan_daggers":
        for i in range(8):
            a = i * math.tau / 8
            ui.line(surf, col, (x + math.cos(a) * s * 0.3, y + math.sin(a) * s * 0.3),
                    (x + math.cos(a) * s * 0.9, y + math.sin(a) * s * 0.9), max(2, int(w)))
    elif kind == "trap":
        ui.circle(surf, col, c, s * 0.55, max(2, int(w)))
        for i in range(6):
            a = i * math.tau / 6
            ui.line(surf, col, (x + math.cos(a) * s * 0.55, y + math.sin(a) * s * 0.55),
                    (x + math.cos(a) * s * 0.9, y + math.sin(a) * s * 0.9), max(2, int(w)))
    elif kind == "arrow":
        ui.line(surf, col, (x - s * 0.75, y + s * 0.75), (x + s * 0.55, y - s * 0.55), max(2, int(w)))
        ui.polygon(surf, col, [(x + s * 0.85, y - s * 0.85), (x + s * 0.25, y - s * 0.6), (x + s * 0.6, y - s * 0.25)])
        ui.line(surf, col, (x - s * 0.75, y + s * 0.75), (x - s * 0.95, y + s * 0.35), max(1, int(w * 0.7)))
        ui.line(surf, col, (x - s * 0.75, y + s * 0.75), (x - s * 0.35, y + s * 0.95), max(1, int(w * 0.7)))
    elif kind == "rain":
        for i in range(4):
            xx = x - s * 0.6 + i * s * 0.4
            ui.line(surf, col, (xx, y - s * 0.8 + (i % 2) * s * 0.3), (xx, y + s * 0.3 + (i % 2) * s * 0.3),
                    max(1, int(w * 0.8)))
            ui.polygon(surf, col, [(xx - s * 0.12, y + s * 0.3 + (i % 2) * s * 0.3),
                                   (xx + s * 0.12, y + s * 0.3 + (i % 2) * s * 0.3), (xx, y + s * 0.55 + (i % 2) * s * 0.3)])
    elif kind in ("shield", "aegis"):
        pts = [(x - s * 0.7, y - s * 0.75), (x + s * 0.7, y - s * 0.75), (x + s * 0.7, y + s * 0.05), (x, y + s * 0.9),
               (x - s * 0.7, y + s * 0.05)]
        ui.polygon(surf, col, pts, 0 if kind == "shield" else max(2, int(w)))
        if kind == "aegis":
            ui.line(surf, col, (x, y - s * 0.45), (x, y + s * 0.4), max(2, int(w)))
            ui.line(surf, col, (x - s * 0.35, y - s * 0.1), (x + s * 0.35, y - s * 0.1), max(2, int(w)))
    elif kind == "sun":
        ui.circle(surf, col, c, s * 0.38)
        for i in range(8):
            a = i * math.tau / 8
            ui.line(surf, col, (x + math.cos(a) * s * 0.55, y + math.sin(a) * s * 0.55),
                    (x + math.cos(a) * s * 0.9, y + math.sin(a) * s * 0.9), max(2, int(w * 0.8)))
    elif kind == "pillar":
        for dx in (-0.45, 0.0, 0.45):
            ui.rect(surf, col, (x + s * dx - s * 0.1, y - s * 0.85, s * 0.2, s * 1.4))
        ui.line(surf, col, (x - s * 0.8, y + s * 0.7), (x + s * 0.8, y + s * 0.7), max(2, int(w)))
    elif kind == "bone":
        ui.line(surf, col, (x - s * 0.5, y + s * 0.5), (x + s * 0.5, y - s * 0.5), max(3, int(w * 1.4)))
        for ex, ey in ((-0.5, 0.5), (0.5, -0.5)):
            for dx, dy in ((-0.15, -0.15), (0.15, 0.15)):
                ui.circle(surf, col, (x + s * (ex + dx), y + s * (ey - dy)), s * 0.2)
    elif kind == "skull":
        ui.circle(surf, col, (x, y - s * 0.12), s * 0.62)
        ui.rect(surf, col, (x - s * 0.36, y + s * 0.2, s * 0.72, s * 0.5), 0, 3)
        ui.circle(surf, (20, 20, 24), (x - s * 0.24, y - s * 0.1), s * 0.17)
        ui.circle(surf, (20, 20, 24), (x + s * 0.24, y - s * 0.1), s * 0.17)
    elif kind == "curse":
        ui.circle(surf, col, c, s * 0.75, max(2, int(w * 0.8)))
        _star(surf, c, s * 0.55, col, 5, 0.38, math.pi / 2)
    elif kind == "harvest":
        ui.arc(surf, col, pygame.Rect(x - s * 0.8, y - s * 0.8, s * 1.6, s * 1.6), 0.5, 3.0, max(2, int(w)))
        ui.line(surf, col, (x + s * 0.55, y - s * 0.55), (x - s * 0.5, y + s * 0.85), max(2, int(w * 0.8)))
        ui.circle(surf, col, (x + s * 0.1, y + s * 0.1), s * 0.18)
    elif kind in ("dagger", "blades"):
        n = 1 if kind == "dagger" else 3
        for i in range(n):
            a = -math.pi / 4 + (i - (n - 1) / 2) * 0.55
            dx, dy = math.cos(a), math.sin(a)
            ui.line(surf, col, (x - dx * s * 0.2, y - dy * s * 0.2), (x + dx * s * 0.9, y + dy * s * 0.9),
                    max(2, int(w)))
            ui.line(surf, col, (x - dx * s * 0.2 - dy * s * 0.25, y - dy * s * 0.2 + dx * s * 0.25),
                    (x - dx * s * 0.2 + dy * s * 0.25, y - dy * s * 0.2 - dx * s * 0.25), max(2, int(w)))
            ui.line(surf, col, (x - dx * s * 0.2, y - dy * s * 0.2), (x - dx * s * 0.6, y - dy * s * 0.6),
                    max(2, int(w * 1.2)))
    elif kind == "drop":
        ui.polygon(surf, col, [(x, y - s * 0.85), (x + s * 0.5, y + s * 0.05), (x + s * 0.3, y + s * 0.6),
                               (x - s * 0.3, y + s * 0.6), (x - s * 0.5, y + s * 0.05)])
        ui.circle(surf, col, (x, y + s * 0.3), s * 0.5)
    elif kind in ("sword", "axe"):
        ui.line(surf, col, (x - s * 0.6, y + s * 0.6), (x + s * 0.8, y - s * 0.8), max(2, int(w * 1.1)))
        ui.line(surf, col, (x - s * 0.75, y + s * 0.15), (x - s * 0.15, y + s * 0.75), max(2, int(w)))
        if kind == "axe":
            ui.polygon(surf, col, [(x + s * 0.3, y - s * 0.9), (x + s * 0.95, y - s * 0.55), (x + s * 0.6, y - s * 0.1)])
    elif kind == "orb":
        ui.circle(surf, col, c, s * 0.55)
        ui.circle(surf, (255, 255, 255), (x - s * 0.18, y - s * 0.18), s * 0.15)
        ui.circle(surf, col, c, s * 0.85, max(1, int(w * 0.5)))
    elif kind == "heart":
        ui.circle(surf, col, (x - s * 0.3, y - s * 0.2), s * 0.35)
        ui.circle(surf, col, (x + s * 0.3, y - s * 0.2), s * 0.35)
        ui.polygon(surf, col, [(x - s * 0.64, y - s * 0.08), (x + s * 0.64, y - s * 0.08), (x, y + s * 0.7)])
    elif kind == "bolt":
        ui.polygon(surf, col, [(x + s * 0.15, y - s * 0.9), (x - s * 0.5, y + s * 0.1), (x - s * 0.02, y + s * 0.1),
                               (x - s * 0.2, y + s * 0.9), (x + s * 0.55, y - s * 0.15), (x + s * 0.05, y - s * 0.15)])
    elif kind == "eye":
        ui.ellipse(surf, col, pygame.Rect(x - s * 0.85, y - s * 0.45, s * 1.7, s * 0.9), max(2, int(w)))
        ui.circle(surf, col, c, s * 0.28)
    elif kind == "clock":
        ui.circle(surf, col, c, s * 0.75, max(2, int(w)))
        ui.line(surf, col, c, (x, y - s * 0.5), max(2, int(w)))
        ui.line(surf, col, c, (x + s * 0.35, y + s * 0.1), max(2, int(w)))
    elif kind == "boot":
        ui.polygon(surf, col, [(x - s * 0.4, y - s * 0.8), (x + s * 0.15, y - s * 0.8), (x + s * 0.15, y + s * 0.2),
                               (x + s * 0.8, y + s * 0.4), (x + s * 0.8, y + s * 0.75), (x - s * 0.4, y + s * 0.75)])
    elif kind == "fist":
        ui.rect(surf, col, (x - s * 0.55, y - s * 0.4, s * 1.1, s * 0.9), 0, 4)
        for i in range(4):
            ui.line(surf, (20, 20, 24), (x - s * 0.55 + i * s * 0.28, y - s * 0.4), (x - s * 0.55 + i * s * 0.28, y),
                    1)
        ui.rect(surf, col, (x - s * 0.35, y + s * 0.4, s * 0.7, s * 0.45))
    elif kind == "summon":
        _glyph_skull_small(surf, x - s * 0.35, y + s * 0.15, s * 0.45, col)
        _glyph_skull_small(surf, x + s * 0.35, y - s * 0.15, s * 0.45, col)
    else:   # star
        _star(surf, c, s * 0.9, col)


def _glyph_skull_small(surf, x, y, s, col):
    ui.circle(surf, col, (x, y), s * 0.7)
    ui.circle(surf, (20, 20, 24), (x - s * 0.25, y), s * 0.18)
    ui.circle(surf, (20, 20, 24), (x + s * 0.25, y), s * 0.18)


def spell_icon(surf, sid, c, r, color, locked=False, attack_cls=None, flat=False):
    """Médaillon rond d'un sort (ou de l'attaque de base si attack_cls est donné).
    flat : pictogramme seul, sans médaillon ni halo (barre de compétences au style plat)."""
    kind = ATTACK_GLYPH.get(attack_cls, "sword") if attack_cls else SPELL_GLYPH.get(sid, "star")
    if flat:
        glyph(surf, kind, c, r * 0.55, (92, 94, 96) if locked else ui.lighter(color, 1.25))
        return
    if locked:
        ui.circle(surf, (26, 28, 30), c, r)
        ui.circle(surf, (90, 92, 92), c, r, 2)
        glyph(surf, kind, c, r * 0.55, (96, 98, 98))
        return
    ui.glow(surf, c[0], c[1], r * 1.5, ui.darker(color, 0.35))
    ui.circle(surf, ui.darker(color, 0.32), c, r)
    ui.circle(surf, ui.darker(color, 0.55), c, r * 0.78)
    ui.circle(surf, ui.lighter(color, 1.15), c, r, 2)
    glyph(surf, kind, c, r * 0.55, ui.lighter(color, 1.45))


def talent_icon(surf, t, c, r, color, state):
    """state : 'max', 'some', 'open' (apprenable) ou 'locked'."""
    icon = t["icon"]
    kind = SPELL_GLYPH.get(icon[6:], "star") if icon.startswith("spell:") else icon
    capstone = t["tier"] == 3
    if state == "locked":
        bg, ring, fg = (22, 24, 26), (80, 82, 82), (90, 92, 92)
    elif state == "open":
        bg, ring, fg = ui.darker(color, 0.22), ui.darker(color, 0.8), ui.darker(color, 0.95)
    else:
        bg, ring, fg = ui.darker(color, 0.4), ui.lighter(color, 1.1), ui.lighter(color, 1.5)
        ui.glow(surf, c[0], c[1], r * (1.9 if state == "max" else 1.5), ui.darker(color, 0.45 if state == "max" else 0.3))
    if capstone:
        pts = [(c[0] + math.cos(i * math.pi / 3) * r * 1.12, c[1] + math.sin(i * math.pi / 3) * r * 1.12)
               for i in range(6)]
        ui.polygon(surf, bg, pts)
        ui.polygon(surf, ring, pts, 2)
    else:
        ui.circle(surf, bg, c, r)
        ui.circle(surf, ring, c, r, 2)
    glyph(surf, kind, c, r * 0.55, fg)
