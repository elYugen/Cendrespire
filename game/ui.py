"""Boîte à outils d'interface.

Toutes les fonctions prennent des coordonnées « de conception » (1280x720) et dessinent
à la résolution réelle (VIEW.s) : textes et traits restent nets sur écran Retina.
Style visuel : tablette Sheikah (Zelda Breath of the Wild).
"""
import math

import pygame
import pygame.freetype as ft

from . import gfx, sfx
from .gfx import darker, lighter
from .items import item_lines
from .settings import (VIEW, SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, WHITE, SHEIKAH, UI_LINE, RARITY_COLORS, FONT_FILES,
                       FONT_FALLBACK)

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
        path, idx = FONT_FILES.get(kind, FONT_FILES["text"])
        try:
            f = ft.Font(path, px, font_index=idx)
        except Exception:
            f = ft.SysFont(FONT_FALLBACK.get(kind, "arial"), px)
        f.origin = True
        f.antialiased = True
        f.kerning = True
        _fonts[key] = f
    return f


_text_cache = {}


def text_surf(text, size, color, kind="text"):
    """Surface du texte en pixels (hauteur de ligne constante pour aligner les lignes)."""
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
        else:
            s = pygame.Surface((1, h), pygame.SRCALPHA)
        _text_cache[key] = s
    return s


_shadow_cache = {}


def _shadow_surf(text, size, kind):
    key = (text, size, kind, VIEW.version)
    s = _shadow_cache.get(key)
    if s is None:
        if len(_shadow_cache) > 5000:
            _shadow_cache.clear()
        s = text_surf(text, size, (0, 0, 0), kind).copy()
        s.set_alpha(150)
        _shadow_cache[key] = s
    return s


def text_size(text, size, kind="text"):
    s = text_surf(text, size, (255, 255, 255), kind)
    return s.get_width() / VIEW.s, s.get_height() / VIEW.s


def draw_text(surf, text, pos, size=18, color=TEXT, kind="text", anchor="topleft", shadow=True, alpha=255):
    """Dessine un texte ; renvoie son rectangle en coordonnées de conception."""
    s = text_surf(text, size, color, kind)
    x, y = pos[0] * VIEW.s, pos[1] * VIEW.s
    r = s.get_rect(**{anchor: (round(x), round(y))})
    if shadow:
        sh = _shadow_surf(text, size, kind)
        if alpha < 255:
            sh = sh.copy()
            sh.set_alpha(int(150 * alpha / 255))
        off = max(1, round(1.5 * VIEW.s))
        surf.blit(sh, r.move(off, off))
    if alpha < 255:
        s = s.copy()
        s.set_alpha(int(alpha))
    surf.blit(s, r)
    k = VIEW.s
    return pygame.Rect(round(r.x / k), round(r.y / k), round(r.w / k), round(r.h / k))


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
    fn(t, (-bx + 2, -by + 2), color)
    surf.blit(t, (bx - 2, by - 2))


def rect(surf, color, r, width=0, radius=0):
    pr = R(r)
    rad = W(radius) if radius else 0

    def fn(t, o, c):
        pygame.draw.rect(t, c, pr.move(o), W(width), border_radius=rad)
    _alpha_target(surf, color, (pr.x, pr.y, pr.w, pr.h), fn)


def circle(surf, color, c, r, width=0):
    cx, cy = P(*c)
    rr = max(1, r * VIEW.s)

    def fn(t, o, col):
        pygame.draw.circle(t, col, (cx + o[0], cy + o[1]), rr, W(width))
    _alpha_target(surf, color, (cx - rr, cy - rr, rr * 2, rr * 2), fn)


def line(surf, color, a, b, width=1):
    pygame.draw.line(surf, color[:3], P(*a), P(*b), W(width))


def aaline(surf, color, a, b):
    pygame.draw.aaline(surf, color[:3], P(*a), P(*b))


def lines(surf, color, closed, pts, width=1):
    pygame.draw.lines(surf, color[:3], closed, [P(*p) for p in pts], W(width))


def polygon(surf, color, pts, width=0):
    pp = [P(*p) for p in pts]
    xs = [p[0] for p in pp]
    ys = [p[1] for p in pp]

    def fn(t, o, c):
        pygame.draw.polygon(t, c, [(p[0] + o[0], p[1] + o[1]) for p in pp], W(width))
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
    surf.blit(src, r)


def veil(surf, color=(6, 12, 16), alpha=200):
    v = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    v.fill((*color, alpha))
    surf.blit(v, (0, 0))


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
    L = max(8, r.w // 4)
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
def draw_tooltip_lines(surf, lines_, pos, border=UI_LINE, side="right"):
    pad = 10
    sizes = [text_size(t, sz, "bold" if i == 0 else "text") for i, (t, c, sz) in enumerate(lines_)]
    w = max(s[0] for s in sizes) + pad * 2
    h = sum(s[1] + 1 for s in sizes) + pad * 2 + 6
    x, y = pos
    if side == "right":
        x += 18
        if x + w > SCREEN_W - 4:
            x = pos[0] - w - 14
    else:
        x -= w + 14
        if x < 4:
            x = pos[0] + 18
    y = min(max(4, y + 8), SCREEN_H - h - 4)
    x = max(4, min(x, SCREEN_W - w - 4))
    r = pygame.Rect(x, y, w, h)
    botw_box(surf, r, 232, border, radius=8, fill=(6, 9, 12))
    cy = y + pad
    for i, ((t, c, sz), (tw, th)) in enumerate(zip(lines_, sizes)):
        draw_text(surf, t, (x + pad, cy), sz, c, "bold" if i == 0 else "text", shadow=False)
        cy += th + 1
        if i == 0 and len(lines_) > 1:
            line(surf, darker(border, 0.6), (x + 6, cy + 2), (x + w - 6, cy + 2))
            cy += 6
    return r


def item_tooltip(surf, item, pos, player=None, header=None, side="right"):
    return draw_tooltip_lines(surf, item_lines(item, player, header), pos, RARITY_COLORS[item["rarity"]], side)
