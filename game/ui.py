"""Boîte à outils d'interface.

Toutes les fonctions prennent des coordonnées « de conception » (1280x720) et dessinent
à la résolution réelle (VIEW.s) : textes et traits restent nets sur écran Retina.
Style visuel : tablette Sheikah (Zelda Breath of the Wild).
"""
import math

import pygame
import pygame.freetype as ft

from . import coins, gfx, sfx
from .gfx import darker, lighter
from .items import item_lines
from .settings import (VIEW, SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, WHITE, SHEIKAH, UI_LINE, RARITY_COLORS, FONT_FILES)

BOTW_LINE = UI_LINE
BOTW_CYAN = SHEIKAH
BOTW_YELLOW = (255, 222, 90)

ft.init()


# --------------------------------------------------------------------------- conversions
def sc():
    return VIEW.s


def P(x, y):
    return (x * VIEW.s, y * VIEW.s)


def R(rect):
    r = pygame.Rect(rect) if not isinstance(rect, pygame.Rect) else rect
    s = VIEW.s
    return pygame.Rect(round(r.x * s), round(r.y * s), round(r.w * s), round(r.h * s))


def W(width):
    return 0 if width == 0 else max(1, round(width * VIEW.s))


def mouse_pos():
    mx, my = pygame.mouse.get_pos()
    return ((mx * VIEW.ratio - VIEW.ox) / VIEW.s, (my * VIEW.ratio - VIEW.oy) / VIEW.s)


# --------------------------------------------------------------------------- polices
_fonts = {}


def font(size, kind="text"):
    px = max(6, int(round(size * VIEW.s)))
    key = (px, kind)
    f = _fonts.get(key)
    if f is None:
        path, idx, k = FONT_FILES.get(kind, FONT_FILES["text"])
        try:
            f = ft.Font(path, max(6, int(round(px * k))), font_index=idx)
        except Exception:
            f = ft.Font(None, px)   # police intégrée à pygame, en dernier recours
        f.origin = True
        f.antialiased = True
        f.kerning = True
        _fonts[key] = f
    return f


_text_cache = {}


def text_surf(text, size, color, kind="text"):
    """Surface du texte en pixels (hauteur de ligne constante pour aligner les lignes), en alpha prémultiplié
    comme tout le calque d'interface : à coller avec premul_blit, sinon les bords lissés deviennent blancs
    (texte gras et crénelé) là où l'interface est transparente."""
    key = (text, size, color, kind, VIEW.version)
    s = _text_cache.get(key)
    if s is None:
        if len(_text_cache) > 5000:
            _text_cache.clear()
        f = font(size, kind)
        asc = f.get_sized_ascender()
        desc = f.get_sized_descender()
        h = asc - desc + 2
        if text:
            r = f.get_rect(text)
            ox = max(0, -r.x)
            s = pygame.Surface((max(1, r.x + r.width + ox + 2), h), pygame.SRCALPHA)
            f.render_to(s, (ox, asc + 1), text, color)
            s = s.premul_alpha()
        else:
            s = pygame.Surface((1, h), pygame.SRCALPHA)
        _text_cache[key] = s
    return s


_shadow_cache = {}


def premul_blit(surf, src, pos):
    """Colle une surface en alpha prémultiplié (couleur déjà multipliée par l'alpha)."""
    surf.blit(src, pos, special_flags=pygame.BLEND_PREMULTIPLIED)


def blit_straight(surf, src, pos, alpha=255):
    """Colle une surface à alpha « classique » (couleur non multipliée) sur le calque prémultiplié."""
    p = src.premul_alpha()
    if alpha < 255:
        a = max(0, min(255, int(alpha)))
        p.fill((a, a, a, a), special_flags=pygame.BLEND_RGBA_MULT)
    premul_blit(surf, p, pos)


def faded(src, alpha):
    """Copie d'une surface prémultipliée, rendue plus transparente (alpha de 0 à 255)."""
    s = src.copy()
    a = max(0, min(255, int(alpha)))
    s.fill((a, a, a, a), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def _shadow_surf(text, size, kind):
    key = (text, size, kind, VIEW.version)
    s = _shadow_cache.get(key)
    if s is None:
        if len(_shadow_cache) > 5000:
            _shadow_cache.clear()
        s = faded(text_surf(text, size, (0, 0, 0), kind), 150)
        _shadow_cache[key] = s
    return s


def text_size(text, size, kind="text"):
    s = text_surf(text, size, (255, 255, 255), kind)
    return s.get_width() / VIEW.s, s.get_height() / VIEW.s


_caps = {}


def cap_box(size, kind="text"):
    """(haut, bas) des majuscules dans la surface d'un texte, en coordonnées de conception : sert à centrer
    un texte sur la hauteur réelle de ses lettres plutôt que sur celle de la ligne."""
    key = (int(round(size * VIEW.s)), kind)
    if key not in _caps:
        r = text_surf("H", size, (255, 255, 255), kind).get_bounding_rect(min_alpha=40)
        _caps[key] = (r.top / VIEW.s, r.bottom / VIEW.s)
    return _caps[key]


def draw_text(surf, text, pos, size=18, color=TEXT, kind="text", anchor="topleft", shadow=False, alpha=255):
    """Dessine un texte ; renvoie son rectangle en coordonnées de conception."""
    s = text_surf(text, size, color, kind)
    x, y = pos[0] * VIEW.s, pos[1] * VIEW.s
    r = s.get_rect(**{anchor: (round(x), round(y))})
    if shadow:
        sh = _shadow_surf(text, size, kind)
        if alpha < 255:
            sh = faded(sh, alpha)
        off = max(1, round(1.5 * VIEW.s))
        premul_blit(surf, sh, r.move(off, off))
    if alpha < 255:
        s = faded(s, alpha)
    premul_blit(surf, s, r)
    k = VIEW.s
    return pygame.Rect(round(r.x / k), round(r.y / k), round(r.w / k), round(r.h / k))


def _money_layout(amount, size):
    parts = coins.split(amount)
    r, gap = size * 0.36, size * 0.3
    widths = [text_size(str(n), size, "bold")[0] + gap * 0.6 + r * 2 for _name, n, _c in parts]
    return parts, r, gap, widths, sum(widths) + gap * (len(parts) - 1)


def money_width(amount, size=16):
    return _money_layout(amount, size)[4]


def draw_money(surf, amount, pos, size=16, anchor="midleft", color=WHITE, alpha=255):
    """Somme en pièces : « 2 (or) 15 (argent) 40 (cuivre) », chaque nombre suivi de sa pièce. Renvoie la largeur."""
    parts, r, gap, widths, total = _money_layout(amount, size)
    x, y = pos
    if anchor.endswith("right") or anchor == "topright":
        x -= total
    elif anchor in ("center", "midtop", "midbottom"):
        x -= total / 2
    if anchor.startswith("top") or anchor == "midtop":
        y += size * 0.6
    elif anchor.startswith("bottom") or anchor == "midbottom":
        y -= size * 0.6
    for (_name, n, col), w in zip(parts, widths):
        tr = draw_text(surf, str(n), (x, y), size, color, "bold", anchor="midleft", alpha=alpha)
        c = (tr.right + gap * 0.6 + r, y)
        a = int(alpha)
        circle(surf, (*darker(col, 0.6), a), c, r)
        circle(surf, (*col, a), c, r * 0.78)
        circle(surf, (*lighter(col, 1.25), a), (c[0] - r * 0.25, c[1] - r * 0.25), r * 0.28)
        x += w + gap
    return total


def speech_bubble(surf, text, bottom, size=14, max_w=280, alpha=255):
    """Bulle de dialogue (parchemin clair, pointe vers le bas) dont la pointe touche bottom. Renvoie son rectangle."""
    lines = wrap(text, size, max_w)
    lh = size * 1.35
    w = max(text_size(line, size)[0] for line in lines) + 26
    h = len(lines) * lh + 16
    r = pygame.Rect(0, 0, w, h)
    r.midbottom = (bottom[0], bottom[1] - 9)
    a = int(alpha)
    rect(surf, (0, 0, 0, int(a * 0.35)), r.move(2, 3), 0, 10)                  # ombre
    rect(surf, (246, 240, 226, int(a * 0.96)), r, 0, 10)
    polygon(surf, (246, 240, 226, int(a * 0.96)), [(bottom[0] - 8, r.bottom - 1), (bottom[0] + 8, r.bottom - 1),
                                                  (bottom[0], bottom[1])])
    rect(surf, (120, 100, 70, a), r, 1, 10)
    for i, line in enumerate(lines):
        draw_text(surf, line, (r.centerx, r.y + 8 + i * lh), size, (48, 38, 28), anchor="midtop", alpha=a)
    return r


def wrap(text, size, width, kind="text"):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if text_size(t, size, kind)[0] <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(surf, text, x, y, width, size=16, color=TEXT, spacing=3, anchor="topleft", kind="text"):
    for line in wrap(text, size, width, kind):
        r = draw_text(surf, line, (x, y), size, color, kind, anchor=anchor)
        y += r.h + spacing
    return y


# --------------------------------------------------------------------------- formes (coordonnées de conception)
def _alpha_target(surf, color, bbox, fn):
    """Dessine fn(target, offset) sur une surface temporaire si la couleur a un alpha."""
    if len(color) == 3 or color[3] >= 255:
        fn(surf, (0, 0), color[:3])
        return
    bx, by, bw, bh = bbox
    t = pygame.Surface((max(1, int(bw) + 4), max(1, int(bh) + 4)), pygame.SRCALPHA)
    t.fill((*color[:3], 0))         # bords lissés : on fond vers la même teinte transparente, pas vers le noir
    fn(t, (-bx + 2, -by + 2), color)
    premul_blit(surf, t.premul_alpha(), (bx - 2, by - 2))


def rect(surf, color, r, width=0, radius=0):
    pr = R(r)
    rad = W(radius) if radius else 0

    def fn(t, o, c):
        r = pr.move(o)
        w = W(width)
        pygame.draw.rect(t, c, r, w, border_radius=rad)
        k = min(rad, r.w // 2, r.h // 2)
        if k >= 2:                       # coins arrondis lissés
            x0, y0, x1, y1 = r.x + k, r.y + k, r.right - k - 1, r.bottom - k - 1
            for cx, cy, q in ((x1, y0, 0), (x0, y0, 1), (x0, y1, 2), (x1, y1, 3)):
                pygame.draw.aacircle(t, c, (cx, cy), k, w, *[i == q for i in range(4)])
    _alpha_target(surf, color, (pr.x, pr.y, pr.w, pr.h), fn)


def circle(surf, color, c, r, width=0):
    cx, cy = P(*c)
    rr = max(1, r * VIEW.s)

    def fn(t, o, col):
        pygame.draw.aacircle(t, col, (cx + o[0], cy + o[1]), rr, W(width))     # bords lissés (icônes nettes)
    _alpha_target(surf, color, (cx - rr, cy - rr, rr * 2, rr * 2), fn)


def line(surf, color, a, b, width=1):
    pygame.draw.aaline(surf, color[:3], P(*a), P(*b), W(width))


def aaline(surf, color, a, b):
    pygame.draw.aaline(surf, color[:3], P(*a), P(*b))


def lines(surf, color, closed, pts, width=1):
    pp = [P(*p) for p in pts]
    if W(width) <= 1:
        pygame.draw.aalines(surf, color[:3], closed, pp)
    else:
        pygame.draw.lines(surf, color[:3], closed, pp, width=W(width))


def polygon(surf, color, pts, width=0):
    pp = [P(*p) for p in pts]
    xs = [p[0] for p in pp]
    ys = [p[1] for p in pp]

    def fn(t, o, c):
        q = [(p[0] + o[0], p[1] + o[1]) for p in pp]
        pygame.draw.polygon(t, c, q, W(width))
        if W(width) <= 1:
            pygame.draw.aalines(t, c, True, q)       # contour lissé
    _alpha_target(surf, color, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)), fn)


def ellipse(surf, color, r, width=0):
    pr = R(r)

    def fn(t, o, c):
        pygame.draw.ellipse(t, c, pr.move(o), W(width))
    _alpha_target(surf, color, (pr.x, pr.y, pr.w, pr.h), fn)


def arc(surf, color, r, a0, a1, width=1):
    pygame.draw.arc(surf, color[:3], R(r), a0, a1, W(width))


def glow(surf, x, y, r, color):
    gfx.glow(surf, x * VIEW.s, y * VIEW.s, r * VIEW.s, color)


def blit(surf, src, pos, anchor="topleft"):
    r = src.get_rect(**{anchor: (round(pos[0] * VIEW.s), round(pos[1] * VIEW.s))})
    blit_straight(surf, src, r)


def veil(surf, color=(6, 12, 16), alpha=200):
    v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    v.fill((*(int(c * alpha / 255) for c in color[:3]), alpha))      # couleur prémultipliée
    premul_blit(surf, v, (0, 0))


# --------------------------------------------------------------------------- éléments BotW
def botw_box(surf, r, alpha=170, border=UI_LINE, radius=10, fill=(0, 0, 0)):
    r = pygame.Rect(r)
    rect(surf, (*fill, alpha), r, 0, radius)
    if border:
        rect(surf, border, r, 1, radius)
    return r


def botw_panel(surf, r, title=None, alpha=205):
    r = botw_box(surf, r, alpha, radius=14)
    rect(surf, (96, 98, 96), r.inflate(-8, -8), 1, 11)
    if title:
        draw_text(surf, title, (r.centerx, r.y + 14), 24, WHITE, "title", anchor="midtop")
        y = r.y + 50
        line(surf, (120, 122, 118), (r.x + 30, y), (r.right - 30, y))
        circle(surf, SHEIKAH, (r.centerx, y), 3)
    return r


draw_panel = botw_panel


def selection_frame(surf, r, t, color=BOTW_YELLOW):
    """Crochets animés autour de l'élément sélectionné (comme dans l'inventaire de BotW)."""
    k = 4 + 2 * math.sin(t * 6)
    r = pygame.Rect(r).inflate(k * 2, k * 2)
    L = max(8, min(r.w, r.h) // 4)
    for (x, y), (dx, dy) in ((r.topleft, (1, 1)), ((r.right, r.top), (-1, 1)),
                             ((r.left, r.bottom), (1, -1)), ((r.right, r.bottom), (-1, -1))):
        line(surf, color, (x, y), (x + dx * L, y), 3)
        line(surf, color, (x, y), (x, y + dy * L), 3)


def key_badge(surf, key, center, size=13, color=WHITE):
    """Touche dans une pastille ronde, façon bouton de manette."""
    w, h = text_size(key, size, "bold")
    rw = max(h + 2, w + 10)
    r = pygame.Rect(0, 0, rw, h + 2)
    r.center = center
    rect(surf, (12, 14, 16), r, 0, r.h // 2)
    rect(surf, color, r, 1, r.h // 2)
    draw_text(surf, key, r.center, size, color, "bold", anchor="center", shadow=False)
    return r


PAD_FACE = {"a": (84, 186, 92), "b": (222, 78, 68), "x": (72, 134, 232), "y": (234, 192, 60)}
DPAD_DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def dpad(surf, center, size=10, lit=None, color=(210, 212, 208)):
    """Croix directionnelle ; la branche « lit » (up, down, left, right) est éclairée."""
    x, y = center
    a = size * 0.36                          # demi-largeur d'une branche
    rect(surf, (18, 20, 22), (x - size - 1, y - a - 1, 2 * size + 2, 2 * a + 2), 0, 3)
    rect(surf, (18, 20, 22), (x - a - 1, y - size - 1, 2 * a + 2, 2 * size + 2), 0, 3)
    rect(surf, (*darker(color, 0.55), 255), (x - size, y - a, 2 * size, 2 * a), 0, 2)
    rect(surf, (*darker(color, 0.55), 255), (x - a, y - size, 2 * a, 2 * size), 0, 2)
    if lit in DPAD_DIRS:
        dx, dy = DPAD_DIRS[lit]
        if dx:
            x0 = x if dx > 0 else x - size
            rect(surf, color, (x0, y - a, size, 2 * a), 0, 2)
        else:
            y0 = y if dy > 0 else y - size
            rect(surf, color, (x - a, y0, 2 * a, size), 0, 2)
    circle(surf, (18, 20, 22), center, a * 0.55)


def pad_button(surf, btn, center, size=10):
    """Pictogramme d'un bouton de manette : A B X Y en pastilles colorées, gâchettes, croix, Start."""
    x, y = center
    if btn in PAD_FACE:
        col = PAD_FACE[btn]
        circle(surf, (14, 16, 18), center, size + 1)
        circle(surf, darker(col, 0.8), center, size)
        circle(surf, col, center, size, 1)
        draw_text(surf, btn.upper(), (x, y + 0.5), int(size * 1.15), WHITE, "bold", anchor="center", shadow=False)
        return pygame.Rect(x - size, y - size, 2 * size, 2 * size)
    if btn in DPAD_DIRS:
        dpad(surf, center, size, btn)
        return pygame.Rect(x - size, y - size, 2 * size, 2 * size)
    if btn in ("lb", "rb", "lt", "rt"):
        w, h = size * 2.7, size * 1.7
        r = pygame.Rect(0, 0, w, h)
        r.center = center
        trig = btn[1] == "t"
        rect(surf, (14, 16, 18), r.inflate(2, 2), 0, int(h * (0.5 if trig else 0.3)))
        rect(surf, (58, 62, 66), r, 0, int(h * (0.5 if trig else 0.3)))
        rect(surf, (200, 204, 204), r, 1, int(h * (0.5 if trig else 0.3)))
        draw_text(surf, btn.upper(), r.center, int(size * 0.95), WHITE, "bold", anchor="center", shadow=False)
        return r
    r = pygame.Rect(0, 0, size * 2.4, size * 1.4)          # start / back
    r.center = center
    rect(surf, (40, 44, 48), r, 0, r.h // 2)
    rect(surf, (200, 204, 204), r, 1, r.h // 2)
    for k in (-1, 0, 1):
        line(surf, WHITE, (x - size * 0.45, y + k * size * 0.3), (x + size * 0.45, y + k * size * 0.3), 1)
    return r


def separator(surf, x1, x2, y):
    line(surf, (120, 122, 118), (x1, y), (x2, y))


class Button:
    def __init__(self, rect_, text, callback, size=19, enabled=True, style="botw"):
        self.rect = pygame.Rect(rect_)
        self.text = text
        self.callback = callback
        self.size = size
        self.enabled = enabled

    def hovered(self):
        return self.enabled and self.rect.collidepoint(mouse_pos())

    def draw(self, surf):
        hover = self.hovered()
        botw_box(surf, self.rect, 210 if hover else 150,
                 SHEIKAH if hover else (UI_LINE if self.enabled else (90, 92, 90)),
                 radius=self.rect.h // 2, fill=(16, 44, 56) if hover else (0, 0, 0))
        col = WHITE if hover else (TEXT if self.enabled else TEXT_DIM)
        draw_text(surf, self.text, self.rect.center, self.size, col, anchor="center")

    def handle(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            if self.enabled:
                sfx.play("click")
                self.callback()
            return True
        return False


# --------------------------------------------------------------------------- icônes d'objets
def draw_artifact_icon(surf, aid, box, color):
    c = box.center
    w = box.w
    x, y = c
    col = color
    if aid == "foudre":
        polygon(surf, col, [(x + w * .08, y - w * .32), (x - w * .16, y + w * .04), (x + w * .02, y + w * .04),
                               (x - w * .08, y + w * .32), (x + w * .18, y - w * .06), (x, y - w * .06)])
    elif aid == "totem":
        rect(surf, (140, 100, 60), (x - w * .06, y - w * .1, w * .12, w * .42))
        circle(surf, col, (x, y - w * .18), w * .14)
    elif aid == "corne":
        arc(surf, col, pygame.Rect(x - w * .28, y - w * .26, w * .56, w * .52), 0.4, 3.0, 4)
        circle(surf, col, (x + w * .22, y - w * .02), w * .08)
    elif aid == "bottes":
        polygon(surf, col, [(x - w * .14, y - w * .28), (x + w * .06, y - w * .28), (x + w * .06, y + w * .12),
                               (x + w * .28, y + w * .18), (x + w * .28, y + w * .3), (x - w * .14, y + w * .3)])
    elif aid == "talisman":
        polygon(surf, col, [(x - w * .24, y - w * .28), (x + w * .24, y - w * .28), (x + w * .24, y + w * .02),
                               (x, y + w * .32), (x - w * .24, y + w * .02)])
    elif aid == "gel":
        for i in range(3):
            a = i * math.pi / 3
            line(surf, col, (x - math.cos(a) * w * .3, y - math.sin(a) * w * .3),
                    (x + math.cos(a) * w * .3, y + math.sin(a) * w * .3), 3)
    elif aid == "crane":
        circle(surf, (230, 226, 210), (x, y - w * .04), w * .24)
        rect(surf, (230, 226, 210), (x - w * .14, y + w * .1, w * .28, w * .14))
        circle(surf, col, (x - w * .09, y - w * .05), w * .06)
        circle(surf, col, (x + w * .09, y - w * .05), w * .06)
    elif aid == "fiole":
        circle(surf, col, (x, y + w * .1), w * .2)
        rect(surf, (200, 200, 210), (x - w * .06, y - w * .3, w * .12, w * .22))
    elif aid == "lanterne":
        rect(surf, (90, 80, 70), (x - w * .18, y - w * .22, w * .36, w * .46), 0, 4)
        rect(surf, col, (x - w * .12, y - w * .14, w * .24, w * .3), 0, 3)
    else:
        from . import icons     # artefact ajouté par data/artifacts.json : pictogramme « icon »
        from .data import ARTIFACTS
        icons.glyph(surf, ARTIFACTS.get(aid, {}).get("icon", "star"), c, w * .3, col)


def draw_item_icon(surf, item, r, bg=True):
    r = pygame.Rect(r)
    col = RARITY_COLORS[item["rarity"]]
    if bg:
        rect(surf, darker(col, 0.16), r, 0, 6)
        rect(surf, darker(col, 0.55), r, 1, 6)
    x, y, w, h = r.x, r.y, r.w, r.h

    def Q(px, py):
        return (x + px * w, y + py * h)

    lw = max(2, w / 14)
    if item["slot"] == "artefact":
        from .data import ARTIFACTS
        draw_artifact_icon(surf, item["art"], r.inflate(-w * 0.1, -h * 0.1), ARTIFACTS[item["art"]]["color"])
        return
    metal, metal_d = (190, 192, 204), (96, 98, 110)
    wood, leather = (140, 94, 52), (130, 90, 58)
    gem = col if item["rarity"] != "commun" else (190, 70, 70)
    slot = item["slot"]
    if slot == "arme":
        wc = item.get("wclass", "barbare")
        if wc == "barbare":
            line(surf, wood, Q(.25, .85), Q(.68, .2), lw + 1)
            pts = [Q(.55, .12), Q(.88, .22), Q(.8, .48), Q(.6, .36)]
            polygon(surf, metal, pts)
            polygon(surf, metal_d, pts, 1)
        elif wc == "paladin":
            line(surf, (236, 226, 190), Q(.3, .78), Q(.78, .2), lw + 1)
            line(surf, (200, 160, 70), Q(.2, .6), Q(.48, .88), lw + 1)
            line(surf, (120, 84, 50), Q(.22, .86), Q(.33, .75), lw + 2)
            circle(surf, gem, Q(.34, .74), w * .06)
        elif wc == "necromancien":
            line(surf, (70, 60, 56), Q(.22, .9), Q(.62, .16), lw + 1)
            arc(surf, (210, 214, 222), pygame.Rect(Q(.2, .08), (w * .6, h * .42)), 0.2, 2.9, lw + 1)
            circle(surf, (140, 255, 170), Q(.62, .16), w * .06)
        elif wc == "assassin":
            for dx in (0, .22):
                line(surf, (220, 222, 236), Q(.2 + dx, .72), Q(.52 + dx, .14), lw)
                line(surf, (100, 76, 120), Q(.12 + dx, .66), Q(.3 + dx, .8), lw)
                line(surf, (70, 50, 60), Q(.1 + dx, .9), Q(.2 + dx, .72), lw + 1)
        elif wc == "sorcier":
            line(surf, wood, Q(.28, .88), Q(.64, .28), lw + 1)
            circle(surf, gem, Q(.68, .22), w * .13)
            circle(surf, (255, 255, 255), Q(.64, .18), max(1, w * .04))
        else:
            ar = pygame.Rect(0, 0, w * .7, h * .8)
            ar.center = Q(.42, .5)
            arc(surf, wood, ar, -math.pi / 2, math.pi / 2, lw + 1)
            line(surf, (230, 230, 210), (ar.centerx, ar.top + 2), (ar.centerx, ar.bottom - 2), 1)
            line(surf, metal, Q(.25, .5), Q(.85, .5), 2)
    elif slot == "casque":
        ellipse(surf, metal, pygame.Rect(Q(.22, .18), (w * .56, h * .6)))
        rect(surf, metal, pygame.Rect(Q(.22, .45), (w * .56, h * .32)))
        line(surf, (30, 30, 30), Q(.3, .55), Q(.7, .55), lw)
        line(surf, (30, 30, 30), Q(.5, .55), Q(.5, .75), lw)
        circle(surf, gem, Q(.5, .3), w * .06)
    elif slot == "torse":
        pts = [Q(.2, .2), Q(.38, .15), Q(.5, .25), Q(.62, .15), Q(.8, .2), Q(.84, .45), Q(.72, .45),
               Q(.72, .85), Q(.28, .85), Q(.28, .45), Q(.16, .45)]
        polygon(surf, leather if item["rarity"] == "commun" else metal, pts)
        polygon(surf, metal_d, pts, 1)
        circle(surf, gem, Q(.5, .45), w * .07)
    elif slot == "gants":
        rect(surf, leather, pygame.Rect(Q(.3, .45), (w * .4, h * .4)), 0, 3)
        for i in range(4):
            rect(surf, leather, pygame.Rect(Q(.3 + i * .1, .2), (w * .08, h * .3)), 0, 2)
        rect(surf, metal, pygame.Rect(Q(.28, .75), (w * .44, h * .1)))
    elif slot == "bottes":
        pts = [Q(.35, .15), Q(.62, .15), Q(.62, .62), Q(.85, .72), Q(.85, .86), Q(.35, .86)]
        polygon(surf, leather, pts)
        polygon(surf, metal_d, pts, 1)
        rect(surf, metal, pygame.Rect(Q(.33, .15), (w * .31, h * .1)))
    elif slot == "amulette":
        ar = pygame.Rect(0, 0, w * .56, h * .6)
        ar.midtop = Q(.5, .1)
        arc(surf, (230, 196, 110), ar, math.pi, 2 * math.pi, 2)
        arc(surf, (230, 196, 110), ar, 0, math.pi, 1)
        circle(surf, (230, 196, 110), Q(.5, .7), w * .15)
        circle(surf, gem, Q(.5, .7), w * .1)
    elif slot == "anneau":
        circle(surf, (230, 196, 110), Q(.5, .58), w * .24, lw)
        circle(surf, gem, Q(.5, .32), w * .1)
    if item.get("upgrade"):
        draw_text(surf, f"+{item['upgrade']}", (r.right - 3, r.bottom - 1), 12, (255, 222, 120), "bold",
                  anchor="bottomright")


# --------------------------------------------------------------------------- infobulles
TIP_W = 330          # largeur maximale du texte d'une infobulle : au-delà, retour à la ligne


def draw_tooltip_lines(surf, lines_, pos, border=UI_LINE, side="right"):
    pad = 10
    # retour à la ligne des lignes trop longues (le titre reste en gras, suivi d'un filet)
    rows = []
    for i, (t, c, sz) in enumerate(lines_):
        kind = "bold" if i == 0 else "text"
        parts = wrap(t, sz, TIP_W, kind) if text_size(t, sz, kind)[0] > TIP_W else [t]
        for j, part in enumerate(parts or [""]):
            rows.append((part, c, sz, kind, i == 0 and j == len(parts) - 1 and len(lines_) > 1))
    sizes = [text_size(t, sz, kind) for t, c, sz, kind, _ in rows]
    w = max(s[0] for s in sizes) + pad * 2
    h = sum(s[1] + 1 for s in sizes) + pad * 2 + 6
    x, y = pos
    if side == "above":             # centrée au-dessus du point donné
        x, y = pos[0] - w / 2, pos[1] - h - 8
    elif side == "right":
        x += 18
        if x + w > SCREEN_W - 4:
            x = pos[0] - w - 14
    else:
        x -= w + 14
        if x < 4:
            x = pos[0] + 18
    y = min(max(4, y + (0 if side == "above" else 8)), SCREEN_H - h - 4)
    x = max(4, min(x, SCREEN_W - w - 4))
    r = pygame.Rect(x, y, w, h)
    botw_box(surf, r, 232, border, radius=8, fill=(6, 9, 12))
    cy = y + pad
    for (t, c, sz, kind, rule), (tw, th) in zip(rows, sizes):
        draw_text(surf, t, (x + pad, cy), sz, c, kind, shadow=False)
        cy += th + 1
        if rule:
            line(surf, darker(border, 0.6), (x + 6, cy + 2), (x + w - 6, cy + 2))
            cy += 6
    return r


def item_tooltip(surf, item, pos, player=None, header=None, side="right"):
    return draw_tooltip_lines(surf, item_lines(item, player, header), pos, RARITY_COLORS[item["rarity"]], side)
