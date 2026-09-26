"""Interface de combat, style Zelda Breath of the Wild :
cœurs en haut à gauche, roue de mana près du héros, minicarte circulaire, grande carte façon tablette Sheikah."""
import math

import pygame

from .data import SPELLS, ANIMA_POWERS, xp_needed
from .settings import SCREEN_W, SCREEN_H, TEXT, TEXT_DIM, GOLD_BRIGHT
from .ui import draw_text, draw_tooltip_lines, text_surf, wrap, darker, lighter

WHITE = (242, 240, 232)
HUD_LINE = (230, 228, 218)
SHEIKAH = (90, 210, 255)
HEART_RED = (222, 38, 52)
MM_R = 86
MM_CENTER = (SCREEN_W - MM_R - 26, SCREEN_H - MM_R - 26)
HEART = 26

# --------------------------------------------------------------------------- cœurs
_heart_cache = {}


def _heart_shape(surf, size, color, inset):
    s = size
    r = s * 0.27 - inset * 0.7
    pygame.draw.circle(surf, color, (s * 0.3, s * 0.36), r)
    pygame.draw.circle(surf, color, (s * 0.7, s * 0.36), r)
    pygame.draw.polygon(surf, color, [(s * 0.05 + inset, s * 0.44), (s * 0.95 - inset, s * 0.44),
                                      (s * 0.5, s * 0.93 - inset * 1.3)])


def heart_surfs(size):
    if size not in _heart_cache:
        full = pygame.Surface((size, size), pygame.SRCALPHA)
        _heart_shape(full, size, (250, 246, 236), 0)
        _heart_shape(full, size, HEART_RED, 2)
        pygame.draw.ellipse(full, (255, 170, 170), (size * 0.2, size * 0.22, size * 0.2, size * 0.14))
        empty = pygame.Surface((size, size), pygame.SRCALPHA)
        _heart_shape(empty, size, (215, 210, 200, 210), 0)
        _heart_shape(empty, size, (22, 16, 16, 190), 2)
        _heart_cache[size] = (full, empty)
    return _heart_cache[size]


def draw_heart(surf, x, y, frac, size=HEART):
    full, empty = heart_surfs(size)
    surf.blit(empty, (x, y))
    if frac <= 0:
        return
    if frac >= 1:
        surf.blit(full, (x, y))
        return
    part = full.copy()
    # efface la portion manquante (en quarts, comme dans Zelda)
    c = size / 2
    a0 = -math.pi / 2 + math.tau * frac
    pts = [(c, c)] + [(c + math.cos(a0 + (math.tau * (1 - frac)) * i / 16) * size,
                       c + math.sin(a0 + (math.tau * (1 - frac)) * i / 16) * size) for i in range(17)]
    pygame.draw.polygon(part, (0, 0, 0, 0), pts)
    surf.blit(part, (x, y))


def draw_hearts(surf, world, x, y):
    p = world.player
    mx = p.stats["max_hp"]
    n = min(20, max(3, round(mx / 25)))
    per = mx / n
    hp = max(0.0, p.hp)
    low = hp < mx * 0.3
    for i in range(n):
        frac = max(0.0, min(1.0, (hp - i * per) / per))
        if 0 < frac < 1:
            frac = math.ceil(frac * 4) / 4
        hx = x + (i % 10) * (HEART + 3)
        hy = y + (i // 10) * (HEART + 3)
        last_filled = frac > 0 and (i + 1 >= n or hp - (i + 1) * per <= 0)
        if low and last_filled:
            k = 1 + 0.18 * max(0, math.sin(world.time * 9))
            size = int(HEART * k)
            d = (size - HEART) // 2
            draw_heart(surf, hx - d, hy - d, frac, size)
        else:
            draw_heart(surf, hx, hy, frac)
    rows = (n - 1) // 10 + 1
    return y + rows * (HEART + 3)


# --------------------------------------------------------------------------- roue de mana (façon endurance)
def draw_mana_wheel(surf, world, sx, sy):
    p = world.player
    frac = max(0.0, min(1.0, p.mana / p.stats["max_mana"]))
    target = 0 if frac >= 0.999 else 255
    a = world.wheel_alpha = world.wheel_alpha + (target - world.wheel_alpha) * 0.12
    if a < 4:
        return
    r_out, r_in = 17, 10
    size = r_out * 2 + 4
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2

    def ring(f, color):
        if f <= 0:
            return
        n = max(2, int(40 * f))
        outer = [(c + math.cos(-math.pi / 2 + math.tau * f * i / n) * r_out,
                  c + math.sin(-math.pi / 2 + math.tau * f * i / n) * r_out) for i in range(n + 1)]
        inner = [(c + math.cos(-math.pi / 2 + math.tau * f * i / n) * r_in,
                  c + math.sin(-math.pi / 2 + math.tau * f * i / n) * r_in) for i in range(n + 1)]
        pygame.draw.polygon(s, color, outer + inner[::-1])
    ring(1.0, (20, 30, 40, 170))
    empty = frac < 0.15 and int(world.time * 6) % 2
    ring(frac, (230, 80, 60, 255) if empty else (*SHEIKAH, 255))
    pygame.draw.circle(s, (240, 240, 235, 200), (c, c), r_out + 1, 1)
    s.set_alpha(int(a))
    surf.blit(s, (sx + 26 - c, sy - 58 - c))


# --------------------------------------------------------------------------- barre de sorts
def rounded_box(surf, rect, alpha=150, border=HUD_LINE, radius=9):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (0, 0, 0, alpha), s.get_rect(), border_radius=radius)
    surf.blit(s, rect)
    pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


def spell_label(name):
    parts = name.replace("'", " ").split()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else parts[0][1])).upper()


def draw_skill_slot(surf, rect, color, label, key, cd_frac, locked, lacking, level_req=0):
    rounded_box(surf, rect, 150, HUD_LINE if not locked else (110, 110, 105))
    if locked:
        draw_text(surf, f"Niv {level_req}", rect.center, 13, TEXT_DIM, anchor="center", shadow=False)
    else:
        pygame.draw.circle(surf, darker(color, 0.45), rect.center, rect.w * 0.34)
        pygame.draw.circle(surf, lighter(color, 1.2), rect.center, rect.w * 0.34, 2)
        draw_text(surf, label, rect.center, 17, WHITE, "title", anchor="center")
        if lacking:
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (30, 60, 160, 120), s.get_rect(), border_radius=9)
            surf.blit(s, rect)
        if cd_frac > 0:
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            cx, cy = rect.w / 2, rect.h / 2
            pts = [(cx, cy)] + [(cx + math.cos(-math.pi / 2 + math.tau * cd_frac * i / 24) * rect.w,
                                 cy + math.sin(-math.pi / 2 + math.tau * cd_frac * i / 24) * rect.h) for i in range(25)]
            pygame.draw.polygon(s, (0, 0, 0, 175), pts)
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=9)
            s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(s, rect)
    key_badge(surf, key, rect)


def key_badge(surf, key, rect):
    w = max(20, text_surf(key, 11, WHITE).get_width() + 10)
    kr = pygame.Rect(0, 0, w, 16)
    kr.center = (rect.centerx, rect.bottom)
    pygame.draw.rect(surf, (15, 15, 15), kr, border_radius=5)
    pygame.draw.rect(surf, HUD_LINE, kr, 1, border_radius=5)
    draw_text(surf, key, kr.center, 11, WHITE, anchor="center", shadow=False)


def draw_skills(surf, world):
    p = world.player
    size, gap = 50, 12
    x0 = SCREEN_W // 2 - (6 * size + 5 * gap) // 2
    y0 = SCREEN_H - size - 26
    world.skill_rects = []
    atk = p.cls["attack"]
    rc = pygame.Rect(x0, y0, size, size)
    draw_skill_slot(surf, rc, atk.get("color", p.cls["color"]), spell_label(atk["name"]), "LMB",
                    p.atk_cd / max(0.01, atk["cd"]), False, False)
    world.skill_rects.append((rc, ("attack", None)))
    for i, sid in enumerate(p.spells):
        sp = SPELLS[sid]
        rc = pygame.Rect(x0 + (i + 1) * (size + gap), y0, size, size)
        tot = p.cd_total.get(sid, 1) or 1
        draw_skill_slot(surf, rc, sp["color"], spell_label(sp["name"]), str(i + 1), p.cds.get(sid, 0) / tot,
                        not p.spell_unlocked(sid), p.mana < sp["mana"], sp["level"])
        world.skill_rects.append((rc, ("spell", sid)))
    rc = pygame.Rect(x0 + 5 * (size + gap), y0, size, size)
    rounded_box(surf, rc)
    fx, fy = rc.centerx, rc.centery + 3
    pygame.draw.circle(surf, (200, 30, 40), (fx, fy + 3), 12)
    pygame.draw.rect(surf, (200, 30, 40), (fx - 4, fy - 12, 8, 8))
    pygame.draw.rect(surf, (230, 220, 200), (fx - 5, fy - 15, 10, 4))
    pygame.draw.circle(surf, (255, 160, 160), (fx - 4, fy), 3)
    if p.potion_cd > 0:
        s = pygame.Surface(rc.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 150), s.get_rect(), border_radius=9)
        surf.blit(s, rc)
    draw_text(surf, f"x{p.potions}", (rc.right - 4, rc.y + 2), 13, WHITE, anchor="topright")
    key_badge(surf, "F", rc)
    world.skill_rects.append((rc, ("potion", None)))


# --------------------------------------------------------------------------- HUD principal
def draw_hud(surf, world):
    p = world.player
    y = draw_hearts(surf, world, 22, 20)
    # niveau et expérience, discrets sous les cœurs
    need = xp_needed(p.level)
    draw_text(surf, f"Niv. {p.level}", (22, y + 4), 15, WHITE)
    bar = pygame.Rect(76, y + 11, 180, 5)
    pygame.draw.rect(surf, (0, 0, 0), bar.inflate(2, 2), border_radius=3)
    pygame.draw.rect(surf, (235, 200, 90), (bar.x, bar.y, bar.w * min(1, p.xp / need), bar.h), border_radius=3)
    y += 26
    if p.points:
        draw_text(surf, f"+{p.points} points à répartir  [C]", (22, y), 14, (140, 235, 140))
        y += 20
    if "cri" in p.buffs:
        draw_text(surf, f"Cri de guerre  {p.buffs['cri']:.0f}s", (22, y), 14, (255, 120, 90))
        y += 20
    draw_text(surf, f"{p.gold} or", (22, y), 14, GOLD_BRIGHT)
    draw_skills(surf, world)
    # pouvoirs d'anima : pastilles en haut à droite
    world.anima_rects = []
    for i, (pid, n) in enumerate(p.anima.items()):
        pw = ANIMA_POWERS[pid]
        c = (SCREEN_W - 30 - (i % 10) * 34, 30 + (i // 10) * 34)
        pygame.draw.circle(surf, (0, 0, 0), c, 14)
        pygame.draw.circle(surf, darker(pw["color"], 0.5), c, 12)
        pygame.draw.circle(surf, HUD_LINE, c, 14, 1)
        draw_text(surf, str(n), c, 13, WHITE, anchor="center")
        world.anima_rects.append((pygame.Rect(c[0] - 14, c[1] - 14, 28, 28), pid))
    if not world.big_map:
        draw_minimap(surf, world)
    draw_top(surf, world)
    draw_messages(surf, world)


def draw_hud_tooltips(surf, world):
    mouse = pygame.mouse.get_pos()
    p = world.player
    for rc, (kind, sid) in world.skill_rects:
        if rc.collidepoint(mouse):
            if kind == "attack":
                a = p.cls["attack"]
                lines = [(a["name"], GOLD_BRIGHT, 18), ("Attaque de base (clic gauche maintenu)", TEXT_DIM, 14),
                         (f"{int(a['mult'] * 100)}% des dégâts de l'arme", TEXT, 15)]
                if a.get("mana_gain"):
                    lines.append((f"Chaque ennemi touché rend {a['mana_gain']} mana", (120, 150, 255), 14))
            elif kind == "spell":
                sp = SPELLS[sid]
                lines = [(sp["name"], GOLD_BRIGHT, 18),
                         (f"Mana : {sp['mana']}   ·   Recharge : {sp['cd']} s", (120, 150, 255), 14)]
                lines += [(l, TEXT, 15) for l in wrap(sp["desc"], 15, 300)]
                if not p.spell_unlocked(sid):
                    lines.append((f"Débloqué au niveau {sp['level']}", (230, 90, 70), 14))
            else:
                lines = [("Potion de soins", GOLD_BRIGHT, 18), ("Rend 45% de la vie maximum (touche F)", TEXT, 15),
                         (f"{p.potions} en réserve", TEXT_DIM, 14)]
            draw_tooltip_lines(surf, lines, (mouse[0], mouse[1] - 160))
            return
    for rc, pid in world.anima_rects:
        if rc.collidepoint(mouse):
            pw = ANIMA_POWERS[pid]
            draw_tooltip_lines(surf, [(f"{pw['name']} x{p.anima[pid]}", pw["color"], 17), (pw["desc"], TEXT, 15)],
                               mouse, side="left")
            return


# --------------------------------------------------------------------------- minicarte circulaire
_mask_cache = {}


def _circle_mask(r):
    if r not in _mask_cache:
        m = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(m, (255, 255, 255, 255), (r, r), r)
        _mask_cache[r] = m
    return _mask_cache[r]


def _player_arrow(surf, x, y, ang, size=9):
    pts = [(x + math.cos(ang) * size, y + math.sin(ang) * size),
           (x + math.cos(ang + 2.5) * size * 0.8, y + math.sin(ang + 2.5) * size * 0.8),
           (x + math.cos(ang + math.pi) * size * 0.25, y + math.sin(ang + math.pi) * size * 0.25),
           (x + math.cos(ang - 2.5) * size * 0.8, y + math.sin(ang - 2.5) * size * 0.8)]
    pygame.draw.polygon(surf, (255, 222, 60), pts)
    pygame.draw.polygon(surf, (60, 40, 0), pts, 1)


def draw_minimap(surf, world):
    mm = world.minimap
    p = world.player
    R = MM_R
    zoom = 2
    k = mm.S * zoom / 40  # pixels écran par pixel monde
    cx, cy = MM_CENTER
    disc = pygame.Surface((R * 2, R * 2), pygame.SRCALPHA)
    disc.fill((12, 22, 28, 175))
    # portion de carte autour du joueur, agrandie
    src_w = int(R * 2 / zoom) + 2
    sx, sy = p.x / 40 * mm.S - src_w / 2, p.y / 40 * mm.S - src_w / 2
    area = pygame.Surface((src_w, src_w), pygame.SRCALPHA)
    area.blit(mm.surf, (-sx, -sy))
    area = pygame.transform.scale(area, (src_w * zoom, src_w * zoom))
    disc.blit(area, (R - src_w * zoom / 2, R - src_w * zoom / 2))
    # repères
    ox, oy = R - p.x * k, R - p.y * k
    seen = mm.seen
    for m in world.monsters:
        if m.dead or (int(m.x // 40), int(m.y // 40)) not in seen:
            continue
        mx, my = ox + m.x * k, oy + m.y * k
        if m.boss:
            pygame.draw.circle(disc, (255, 60, 60), (mx, my), 6)
            pygame.draw.circle(disc, WHITE, (mx, my), 6, 1)
        elif math.hypot(m.x - p.x, m.y - p.y) < 520:
            pygame.draw.circle(disc, (255, 170, 60) if m.elite else (240, 70, 60), (mx, my), 3 if m.elite else 2)
    _markers(disc, world, ox, oy, k)
    disc.blit(_circle_mask(R), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(disc, (cx - R, cy - R))
    # cadre
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), R + 4, 3)
    pygame.draw.circle(surf, HUD_LINE, (cx, cy), R + 1, 2)
    for i in range(24):
        a = i / 24 * math.tau
        l = 6 if i % 6 == 0 else 3
        pygame.draw.line(surf, HUD_LINE, (cx + math.cos(a) * (R + 2), cy + math.sin(a) * (R + 2)),
                         (cx + math.cos(a) * (R + 2 + l), cy + math.sin(a) * (R + 2 + l)), 1)
    nx, ny = cx, cy - R - 2
    pygame.draw.circle(surf, (20, 20, 20), (nx, ny), 10)
    pygame.draw.circle(surf, HUD_LINE, (nx, ny), 10, 1)
    draw_text(surf, "N", (nx, ny), 13, WHITE, anchor="center", shadow=False)
    _player_arrow(surf, cx, cy, p.facing)
    title, _ = world.hud_title()
    if title:
        draw_text(surf, title, (cx, cy + R + 8), 13, WHITE, anchor="midtop")


def _markers(surf, world, ox, oy, k):
    seen = world.minimap.seen
    for o in world.interactables:
        name = o.__class__.__name__
        if (int(o.x // 40), int(o.y // 40)) not in seen or name == "Campfire":
            continue
        x, y = ox + o.x * k, oy + o.y * k
        if name == "Portal":
            pts = [(x, y - 7), (x + 6, y), (x, y + 7), (x - 6, y)]
            pygame.draw.polygon(surf, SHEIKAH, pts)
            pygame.draw.polygon(surf, WHITE, pts, 1)
        elif name == "Chest":
            if not o.opened:
                pygame.draw.rect(surf, (240, 200, 70), (x - 4, y - 3, 8, 6))
                pygame.draw.rect(surf, (80, 50, 10), (x - 4, y - 3, 8, 6), 1)
        else:
            pygame.draw.circle(surf, (250, 220, 120), (x, y), 5)
            pygame.draw.circle(surf, (60, 40, 10), (x, y), 5, 1)


# --------------------------------------------------------------------------- grande carte (Tab)
def draw_big_map(surf, world):
    mm = world.minimap
    p = world.player
    veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    veil.fill((10, 20, 26, 235))
    surf.blit(veil, (0, 0))
    for x in range(0, SCREEN_W, 64):
        pygame.draw.line(surf, (30, 52, 62), (x, 0), (x, SCREEN_H))
    for y in range(0, SCREEN_H, 64):
        pygame.draw.line(surf, (30, 52, 62), (0, y), (SCREEN_W, y))
    area_w, area_h = SCREEN_W - 160, SCREEN_H - 170
    scale = min(area_w / mm.surf.get_width(), area_h / mm.surf.get_height())
    ms = pygame.transform.scale(mm.surf, (int(mm.surf.get_width() * scale), int(mm.surf.get_height() * scale)))
    x0 = (SCREEN_W - ms.get_width()) // 2
    y0 = (SCREEN_H - ms.get_height()) // 2 + 10
    surf.blit(ms, (x0, y0))
    k = mm.S * scale / 40
    seen = mm.seen
    for m in world.monsters:
        if m.boss and not m.dead and (int(m.x // 40), int(m.y // 40)) in seen:
            pygame.draw.circle(surf, (255, 60, 60), (x0 + m.x * k, y0 + m.y * k), 8)
            pygame.draw.circle(surf, WHITE, (x0 + m.x * k, y0 + m.y * k), 8, 1)
    _markers(surf, world, x0, y0, k)
    _player_arrow(surf, x0 + p.x * k, y0 + p.y * k, p.facing, 12)
    # cadre façon tablette
    frame = pygame.Rect(40, 40, SCREEN_W - 80, SCREEN_H - 80)
    for (ax, ay), (dx, dy) in (((frame.left, frame.top), (1, 1)), ((frame.right, frame.top), (-1, 1)),
                               ((frame.left, frame.bottom), (1, -1)), ((frame.right, frame.bottom), (-1, -1))):
        pygame.draw.line(surf, SHEIKAH, (ax, ay), (ax + dx * 40, ay), 2)
        pygame.draw.line(surf, SHEIKAH, (ax, ay), (ax, ay + dy * 40), 2)
    title, sub = world.hud_title()
    draw_text(surf, title or "Carte", (70, 56), 28, WHITE, "title")
    if sub:
        draw_text(surf, sub, (72, 92), 15, (190, 215, 225))
    legend = [((255, 222, 60), "Vous"), (SHEIKAH, "Portail"), ((240, 200, 70), "Coffre"), ((255, 60, 60), "Gardien")]
    lx = SCREEN_W - 70
    for col, name in reversed(legend):
        r = draw_text(surf, name, (lx, SCREEN_H - 70), 15, WHITE, anchor="bottomright")
        pygame.draw.circle(surf, col, (r.x - 12, r.centery), 6)
        lx = r.x - 34
    draw_text(surf, "[Tab] Fermer", (70, SCREEN_H - 70), 15, (190, 215, 225), anchor="bottomleft")


# --------------------------------------------------------------------------- titre, boss, messages
def draw_top(surf, world):
    title, sub = world.hud_title()
    if title and not world.big_map:
        draw_text(surf, title, (SCREEN_W // 2, 12), 20, WHITE, "title", anchor="midtop")
        if sub:
            draw_text(surf, sub, (SCREEN_W // 2, 40), 15, (215, 225, 230), anchor="midtop")
    boss = world.active_boss()
    if boss:
        w = 560
        r = pygame.Rect(SCREEN_W // 2 - w // 2, SCREEN_H - 128, w, 12)
        draw_text(surf, boss.name, (r.x, r.y - 4), 18, WHITE, "title", anchor="bottomleft")
        draw_text(surf, boss.title, (r.right, r.y - 5), 14, (215, 215, 210), anchor="bottomright")
        pygame.draw.rect(surf, (0, 0, 0), r.inflate(4, 4), border_radius=6)
        pygame.draw.rect(surf, (60, 10, 12), r, border_radius=5)
        fw = int(r.w * max(0, boss.hp / boss.max_hp))
        if fw > 0:
            pygame.draw.rect(surf, (225, 40, 50), (r.x, r.y, fw, r.h), border_radius=5)
            pygame.draw.line(surf, (255, 140, 140), (r.x + 4, r.y + 2), (r.x + fw - 4, r.y + 2))
        pygame.draw.rect(surf, HUD_LINE, r.inflate(4, 4), 1, border_radius=6)


def draw_messages(surf, world):
    y = SCREEN_H - 120
    for text, color, t in reversed(world.messages[-6:]):
        if t <= 0:
            continue
        s = text_surf(text, 15, color)
        if t < 1:
            s = s.copy()
            s.set_alpha(int(255 * t))
        surf.blit(s, (22, y))
        y -= 22
    b = world.banner
    if b:
        text, sub, color, t, dur = b
        k = min(1, t / 0.4, (dur - t) / 0.6)
        if k > 0:
            ts = text_surf(text, 38, color, "title").copy()
            ts.set_alpha(int(255 * k))
            sh = text_surf(text, 38, (0, 0, 0), "title").copy()
            sh.set_alpha(int(180 * k))
            r = ts.get_rect(center=(SCREEN_W // 2, 170))
            surf.blit(sh, r.move(2, 2))
            surf.blit(ts, r)
            lw = int(r.w * 0.6 * k)
            pygame.draw.line(surf, color, (SCREEN_W // 2 - lw, r.bottom + 6), (SCREEN_W // 2 + lw, r.bottom + 6), 1)
            if sub:
                ss = text_surf(sub, 19, WHITE).copy()
                ss.set_alpha(int(255 * k))
                surf.blit(ss, ss.get_rect(center=(SCREEN_W // 2, r.bottom + 24)))
