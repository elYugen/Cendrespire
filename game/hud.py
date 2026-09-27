"""Interface de jeu façon Zelda Breath of the Wild.

- cœurs en haut à gauche (quarts de cœur), effets actifs juste en dessous ;
- emplacements de sorts en haut à droite, artefacts / potion / roulade en dessous ;
- minicarte carrée arrondie en bas à droite, avec jauge « thermomètre » (sceau) et jauge de « bruit » (menace) ;
- roue de mana à côté du héros (comme la roue d'endurance) ;
- bulles d'interaction avec touche ronde, notifications de butin en bas à gauche, titres de zone au centre.
"""
import math

import pygame

from . import icons, ui
from .data import SPELLS, BUFFS, ANIMA_POWERS, ARTIFACTS, ARTIFACT_KEYS, anima_desc, xp_needed
from .items import ART_SLOTS
from .settings import SCREEN_W, SCREEN_H, VIEW, TEXT, TEXT_DIM, GOLD_BRIGHT, WHITE, SHEIKAH, UI_LINE, RARITY_COLORS

HEART = 19            # taille d'un cœur
HEARTS_PER_ROW = 15
HEART_GAP = 2
MAX_HEARTS = 30
MM = pygame.Rect(SCREEN_W - 24 - 172, SCREEN_H - 24 - 172, 172, 172)
SOFT = (210, 216, 216)


def minimap_rect():
    return MM


# --------------------------------------------------------------------------- cœurs
_heart_cache = {}


def _heart_shape(surf, s, color):
    """Cœur plein (deux lobes + pointe), sans contour : style flat de Zelda BotW."""
    r = s * 0.28
    pygame.draw.circle(surf, color, (s * 0.29, s * 0.35), r)
    pygame.draw.circle(surf, color, (s * 0.71, s * 0.35), r)
    pygame.draw.polygon(surf, color, [(s * 0.03, s * 0.43), (s * 0.97, s * 0.43), (s * 0.5, s * 0.94)])


def heart_surfs(size_px):
    key = (size_px, VIEW.version)
    if key not in _heart_cache:
        big = size_px * 4   # sur-échantillonné puis réduit : bords lisses
        full = pygame.Surface((big, big), pygame.SRCALPHA)
        _heart_shape(full, big, (232, 44, 60))
        empty = pygame.Surface((big, big), pygame.SRCALPHA)
        _heart_shape(empty, big, (24, 26, 30, 150))
        _heart_cache[key] = (pygame.transform.smoothscale(full, (size_px, size_px)),
                             pygame.transform.smoothscale(empty, (size_px, size_px)))
    return _heart_cache[key]


def draw_heart(surf, x, y, frac, size=HEART):
    px = max(4, int(size * VIEW.s))
    full, empty = heart_surfs(px)
    X, Y = round(x * VIEW.s), round(y * VIEW.s)
    surf.blit(empty, (X, Y))
    if frac <= 0:
        return
    if frac >= 1:
        surf.blit(full, (X, Y))
        return
    part = full.copy()
    c = px / 2
    a0 = -math.pi / 2 + math.tau * frac
    pts = [(c, c)] + [(c + math.cos(a0 + math.tau * (1 - frac) * i / 20) * px,
                       c + math.sin(a0 + math.tau * (1 - frac) * i / 20) * px) for i in range(21)]
    pygame.draw.polygon(part, (0, 0, 0, 0), pts)
    surf.blit(part, (X, Y))


def draw_hearts(surf, world, x, y):
    p = world.player
    mx = p.stats["max_hp"]
    n = min(MAX_HEARTS, max(3, round(mx / 25)))
    per = mx / n
    hp = max(0.0, p.hp)
    low = hp < mx * 0.3
    for i in range(n):
        frac = max(0.0, min(1.0, (hp - i * per) / per))
        if 0 < frac < 1:
            frac = math.ceil(frac * 4) / 4
        hx = x + (i % HEARTS_PER_ROW) * (HEART + HEART_GAP)
        hy = y + (i // HEARTS_PER_ROW) * (HEART + HEART_GAP)
        last = frac > 0 and (i + 1 >= n or hp - (i + 1) * per <= 0)
        if low and last:
            k = 1 + 0.2 * max(0, math.sin(world.time * 9))
            size = HEART * k
            draw_heart(surf, hx - (size - HEART) / 2, hy - (size - HEART) / 2, frac, size)
        else:
            draw_heart(surf, hx, hy, frac)
    return y + ((n - 1) // HEARTS_PER_ROW + 1) * (HEART + HEART_GAP)


# --------------------------------------------------------------------------- roue de mana
def _ring(surf, cx, cy, r_out, r_in, frac, color):
    if frac <= 0:
        return
    n = max(3, int(48 * frac))
    outer = [(cx + math.cos(-math.pi / 2 + math.tau * frac * i / n) * r_out,
              cy + math.sin(-math.pi / 2 + math.tau * frac * i / n) * r_out) for i in range(n + 1)]
    inner = [(cx + math.cos(-math.pi / 2 + math.tau * frac * i / n) * r_in,
              cy + math.sin(-math.pi / 2 + math.tau * frac * i / n) * r_in) for i in range(n + 1)]
    pygame.draw.polygon(surf, color, outer + inner[::-1])


def draw_mana_wheel(surf, world, x, y):
    p = world.player
    frac = max(0.0, min(1.0, p.mana / p.stats["max_mana"]))
    target = 0 if frac >= 0.999 else 255
    world.wheel_alpha += (target - world.wheel_alpha) * 0.12
    a = world.wheel_alpha
    if a < 4:
        return
    s = VIEW.s
    ro, ri = 17 * s, 10 * s
    size = int(ro * 2 + 6)
    t = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    _ring(t, c, c, ro, ri, 1.0, (20, 30, 40, 170))
    empty = frac < 0.15 and int(world.time * 6) % 2
    _ring(t, c, c, ro, ri, frac, (235, 90, 70, 255) if empty else (*SHEIKAH, 255))
    pygame.draw.circle(t, (240, 240, 235, 200), (c, c), ro + 1, max(1, int(s)))
    t.set_alpha(int(a))
    surf.blit(t, (x * s - c, y * s - c))


# --------------------------------------------------------------------------- emplacements
def _cooldown(surf, rect, frac, radius=10):
    if frac <= 0:
        return
    pr = ui.R(rect)
    t = pygame.Surface(pr.size, pygame.SRCALPHA)
    cx, cy = pr.w / 2, pr.h / 2
    pts = [(cx, cy)] + [(cx + math.cos(-math.pi / 2 + math.tau * frac * i / 30) * pr.w,
                         cy + math.sin(-math.pi / 2 + math.tau * frac * i / 30) * pr.h) for i in range(31)]
    pygame.draw.polygon(t, (0, 0, 0, 175), pts)
    mask = pygame.Surface(pr.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=int(radius * VIEW.s))
    t.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(t, pr)


def spell_label(name):
    parts = name.replace("'", " ").split()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else parts[0][1])).upper()


def slot_box(surf, rect, border=UI_LINE, alpha=150):
    ui.botw_box(surf, rect, alpha, border, radius=10)


def draw_skill(surf, rect, color, sid, key, cd_frac, cd_left, locked, lacking, level_req=0, attack_cls=None):
    slot_box(surf, rect, UI_LINE if not locked else (110, 110, 105))
    c = rect.center
    if locked:
        icons.spell_icon(surf, sid, c, rect.w * 0.34, color, locked=True, attack_cls=attack_cls)
        ui.draw_text(surf, f"Niv {level_req}", (c[0], c[1] + 1), 12, TEXT_DIM, "bold", anchor="center")
    else:
        icons.spell_icon(surf, sid, c, rect.w * 0.36, color, attack_cls=attack_cls)
        if lacking:
            ui.rect(surf, (30, 60, 170, 120), rect, 0, 10)
        _cooldown(surf, rect, cd_frac)
        if cd_left > 0.95:
            ui.draw_text(surf, f"{cd_left:.0f}", c, 17, WHITE, "bold", anchor="center")
    ui.key_badge(surf, key, (rect.centerx, rect.bottom), 11)


def draw_slots(surf, world):
    p = world.player
    size, gap = 52, 10
    right = SCREEN_W - 22
    y0 = 20
    atk = p.cls["attack"]
    entries = [("attack", None)] + [("spell", sid) for sid in p.spells]
    x0 = right - len(entries) * size - (len(entries) - 1) * gap
    for i, (kind, sid) in enumerate(entries):
        rc = pygame.Rect(x0 + i * (size + gap), y0, size, size)
        if kind == "attack":
            draw_skill(surf, rc, atk.get("color", p.cls["color"]), None, "LMB",
                       p.atk_cd / max(0.01, p.atk_total), 0, False, False, attack_cls=p.cls_id)
        else:
            sp = SPELLS[sid]
            tot = p.cd_total.get(sid, 1) or 1
            cd = p.cds.get(sid, 0)
            draw_skill(surf, rc, sp["color"], sid, str(i), cd / tot, cd,
                       not p.spell_unlocked(sid), p.mana < sp["mana"], sp["level"])
        world.skill_rects.append((rc, (kind, sid)))
    # rangée 2 : artefacts, potion, roulade
    s2, g2 = 44, 12
    y1 = y0 + size + 18
    row = [("roll", None)]
    x1 = right - len(row) * s2 - (len(row) - 1) * g2
    for i, (kind, key) in enumerate(row):
        rc = pygame.Rect(x1 + i * (s2 + g2), y1, s2, s2)
        if kind == "art":
            it = p.equipment.get(key)
            slot_box(surf, rc, RARITY_COLORS[it["rarity"]] if it else (100, 100, 98), 150 if it else 90)
            if it:
                a = ARTIFACTS[it["art"]]
                ui.draw_artifact_icon(surf, it["art"], rc, a["color"])
                cd = p.art_cds.get(key, 0)
                _cooldown(surf, rc, cd / (p.art_total.get(key, 1) or 1))
                if cd > 0.95:
                    ui.draw_text(surf, f"{cd:.0f}", rc.center, 15, WHITE, "bold", anchor="center")
            ui.key_badge(surf, ARTIFACT_KEYS[i], (rc.centerx, rc.bottom), 10)
        elif kind == "potion":
            slot_box(surf, rc)
            fx, fy = rc.centerx, rc.centery + 3
            ui.circle(surf, (210, 34, 46), (fx, fy + 3), 11)
            ui.rect(surf, (210, 34, 46), (fx - 4, fy - 11, 8, 8))
            ui.rect(surf, (230, 220, 200), (fx - 5, fy - 14, 10, 4))
            ui.circle(surf, (255, 170, 170), (fx - 4, fy), 3)
            _cooldown(surf, rc, p.potion_cd / max(0.01, p.potion_total))
            if p.potion_cd > 0.95:
                ui.draw_text(surf, f"{p.potion_cd:.0f}", rc.center, 15, WHITE, "bold", anchor="center")
            ui.key_badge(surf, "F", (rc.centerx, rc.bottom), 10)
        else:
            slot_box(surf, rc)
            c = rc.center
            ui.arc(surf, (180, 230, 190), pygame.Rect(c[0] - 12, c[1] - 12, 24, 24), 0.6, 5.4, 3)
            ui.polygon(surf, (180, 230, 190), [(c[0] + 12, c[1] - 2), (c[0] + 6, c[1] - 12), (c[0] + 16, c[1] - 10)])
            _cooldown(surf, rc, p.roll_cd / max(0.01, p.roll_total))
            ui.key_badge(surf, "Espace", (rc.centerx, rc.bottom), 10)
        world.skill_rects.append((rc, (kind, key)))
    # or : apparaît brièvement quand il change (comme les rubis)
    if world.gold_shown > 0 or world.show_inv:
        a = min(1.0, world.gold_shown / 0.5) if not world.show_inv else 1.0
        r = pygame.Rect(right - 130, y1 + s2 + 20, 130, 28)
        ui.botw_box(surf, r, int(150 * a), None, radius=14)
        ui.circle(surf, (240, 196, 70), (r.x + 16, r.centery), 8)
        ui.circle(surf, (255, 230, 140), (r.x + 14, r.centery - 2), 3)
        ui.draw_text(surf, f"{world.player.gold}", (r.right - 12, r.centery), 16, WHITE, "bold",
                     anchor="midright", alpha=int(255 * a))


# --------------------------------------------------------------------------- effets actifs (sous les cœurs)
def draw_effects(surf, world, x, y):
    p = world.player
    world.anima_rects = []
    items = []
    for key, left in p.buffs.items():
        b = BUFFS.get(key)
        if b and not b.get("hidden"):
            items.append(("buff", key, b["name"], b.get("color", (220, 220, 220)), left))
    for pid, n in p.anima.items():
        items.append(("anima", pid, ANIMA_POWERS[pid]["name"], ANIMA_POWERS[pid]["color"], n))
    for i, (kind, key, name, col, val) in enumerate(items):
        c = (x + 14 + (i % 9) * 32, y + 14 + (i // 9) * 32)
        ui.circle(surf, (0, 0, 0, 170), c, 14)
        ui.circle(surf, ui.darker(col, 0.55), c, 11)
        ui.circle(surf, col, c, 14, 1)
        txt = f"{val:.0f}" if kind == "buff" else f"x{val}"
        ui.draw_text(surf, txt, c, 11, WHITE, "bold", anchor="center")
        world.anima_rects.append((pygame.Rect(c[0] - 14, c[1] - 14, 28, 28), (kind, key, name, val)))


# --------------------------------------------------------------------------- HUD principal
def _potion_glyph(surf, c, k=1.0):
    fx, fy = c[0], c[1] + 3 * k
    ui.circle(surf, (210, 34, 46), (fx, fy + 3 * k), 11 * k)
    ui.rect(surf, (210, 34, 46), (fx - 4 * k, fy - 11 * k, 8 * k, 8 * k))
    ui.rect(surf, (230, 220, 200), (fx - 5 * k, fy - 14 * k, 10 * k, 4 * k))
    ui.circle(surf, (255, 170, 170), (fx - 4 * k, fy), 3 * k)


def draw_artifacts(surf, world, x, y):
    """Façon Breath of the Wild : les 3 artefacts et la potion en croix sous les cœurs, la touche à côté."""
    p = world.player
    R, gap = 19, 44
    cx, cy = x + gap + R, y + gap + R - 4
    # (emplacement, décalage dans la croix, côté de la touche)
    layout = [(ART_SLOTS[0], (0, -1), "right"), (ART_SLOTS[1], (-1, 0), "below"), (ART_SLOTS[2], (1, 0), "below"),
              ("potion", (0, 1), "right")]
    ui.circle(surf, (0, 0, 0, 60), (cx, cy), 9)
    for i, (slot, (ox, oy), side) in enumerate(layout):
        c = (cx + ox * gap, cy + oy * gap)
        box = pygame.Rect(c[0] - R, c[1] - R, 2 * R, 2 * R)
        if slot == "potion":
            key = "F"
            ui.circle(surf, (0, 0, 0, 150), c, R)
            _potion_glyph(surf, c, 0.8)
            cd, tot = p.potion_cd, max(0.01, p.potion_total)
            ring = (210, 34, 46)
        else:
            key = ARTIFACT_KEYS[ART_SLOTS.index(slot)]
            it = p.equipment.get(slot)
            if it:
                ui.circle(surf, (0, 0, 0, 150), c, R)
                ui.draw_artifact_icon(surf, it["art"], box, ARTIFACTS[it["art"]]["color"])
                cd, tot = p.art_cds.get(slot, 0), (p.art_total.get(slot, 1) or 1)
                ring = RARITY_COLORS[it["rarity"]]
            else:
                ui.circle(surf, (0, 0, 0, 90), c, R)
                ui.circle(surf, (150, 150, 146, 120), c, R, 1)
                cd, tot, ring = 0, 1, None
        if cd > 0:
            s = VIEW.s
            _ring(surf, c[0] * s, c[1] * s, R * s, (R - 3) * s, 1 - cd / tot, (240, 240, 235))
            ui.circle(surf, (0, 0, 0, 120), c, R - 3)
            ui.draw_text(surf, f"{cd:.0f}", c, 13, WHITE, "bold", anchor="center")
        elif ring:
            ui.circle(surf, ring, c, R, 2)
        kp = (c[0] + R + 10, c[1]) if side == "right" else (c[0], c[1] + R + 7)
        ui.key_badge(surf, key, kp, 10)
        world.skill_rects.append((box, ("art", slot) if slot != "potion" else ("potion", None)))
    return cy + gap + R + 12


def draw_hud(surf, world):
    p = world.player
    y = draw_hearts(surf, world, 22, 20)
    world.skill_rects = []
    y = draw_artifacts(surf, world, 22, y + 16)
    draw_effects(surf, world, 18, y + 2)
    draw_slots(surf, world)
    draw_minimap(surf, world)
    draw_top(surf, world)
    draw_notifs(surf, world)
    draw_messages(surf, world)


def draw_hud_tooltips(surf, world):
    mouse = ui.mouse_pos()
    p = world.player
    for rc, (kind, sid) in world.skill_rects:
        if not rc.collidepoint(mouse):
            continue
        if kind == "attack":
            a = p.cls["attack"]
            lines = [(a["name"], GOLD_BRIGHT, 17), ("Attaque de base (clic gauche maintenu)", TEXT_DIM, 14),
                     (f"{int(a['mult'] * 100)}% des dégâts de l'arme", TEXT, 15)]
            if a.get("mana_gain"):
                lines.append((f"Chaque ennemi touché rend {a['mana_gain']} mana", (120, 160, 255), 14))
        elif kind == "spell":
            sp = SPELLS[sid]
            lines = [(sp["name"], GOLD_BRIGHT, 17), (f"Mana {sp['mana']}  ·  Recharge {sp['cd']} s", (120, 170, 255), 14)]
            lines += [(l, TEXT, 15) for l in ui.wrap(sp["desc"], 15, 300)]
            if not p.spell_unlocked(sid):
                lines.append((f"Débloqué au niveau {sp['level']}", (240, 100, 80), 14))
        elif kind == "art":
            it = p.equipment.get(sid)
            if it:
                ui.item_tooltip(surf, it, (mouse[0], mouse[1] + 10), p, side="left")
                return
            lines = [("Emplacement d'artefact", GOLD_BRIGHT, 17),
                     ("Équipez un artefact depuis l'inventaire (I).", TEXT, 15)]
        elif kind == "potion":
            lines = [("Potion de soins", GOLD_BRIGHT, 17), ("Rend 50% de la vie maximum (touche F).", TEXT, 15),
                     (f"Recharge : {p.potion_total:.0f} s", (120, 170, 255), 14)]
        else:
            lines = [("Roulade", GOLD_BRIGHT, 17), ("Esquive rapide et invulnérable (Espace).", TEXT, 15),
                     (f"Recharge : {p.roll_total:.1f} s", (120, 170, 255), 14)]
        ui.draw_tooltip_lines(surf, lines, (mouse[0], mouse[1] + 10), side="left")
        return
    for rc, (kind, key, name, val) in world.anima_rects:
        if rc.collidepoint(mouse):
            if kind == "anima":
                pw = ANIMA_POWERS[key]
                ui.draw_tooltip_lines(surf, [(f"{name}  x{val}", pw["color"], 16), (anima_desc(key, val), TEXT, 15),
                                             ("Pouvoir d'anima (dure l'ascension)", TEXT_DIM, 13)], mouse)
            else:
                ui.draw_tooltip_lines(surf, [(name, GOLD_BRIGHT, 16), (f"{val:.1f} s restantes", TEXT, 14)], mouse)
            return


# --------------------------------------------------------------------------- minicarte
_mask_cache = {}


def _round_mask(w, h, r):
    key = (w, h, r)
    if key not in _mask_cache:
        m = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(m, (255, 255, 255, 255), m.get_rect(), border_radius=r)
        _mask_cache[key] = m
    return _mask_cache[key]


def _rot(dx, dy):
    """Rotation de 45° : l'orientation de la carte suit celle de la caméra."""
    return (dx - dy) * 0.7071, (dx + dy) * 0.7071


def _arrow(surf, x, y, ang, size):
    s = VIEW.s
    pts = [(x + math.cos(ang) * size, y + math.sin(ang) * size),
           (x + math.cos(ang + 2.5) * size * 0.8, y + math.sin(ang + 2.5) * size * 0.8),
           (x + math.cos(ang + math.pi) * size * 0.2, y + math.sin(ang + math.pi) * size * 0.2),
           (x + math.cos(ang - 2.5) * size * 0.8, y + math.sin(ang - 2.5) * size * 0.8)]
    pygame.draw.polygon(surf, (255, 224, 60), [(a * s, b * s) for a, b in pts])
    pygame.draw.polygon(surf, (70, 50, 0), [(a * s, b * s) for a, b in pts], max(1, int(s)))


def _in_disc(box, x, y):
    return (x - box.centerx) ** 2 + (y - box.centery) ** 2 <= (box.w / 2 - 4) ** 2


def _markers(surf, world, cx, cy, scale, clip):
    """Repères en coordonnées de conception ; scale = unités de conception par unité monde."""
    p = world.player
    seen = world.minimap.seen

    def pos(x, y):
        u, v = _rot((x - p.x) * scale, (y - p.y) * scale)
        return cx + u, cy + v
    for m in world.monsters:
        if m.dead or (int(m.x // 40), int(m.y // 40)) not in seen:
            continue
        x, y = pos(m.x, m.y)
        if not _in_disc(clip, x, y):
            continue
        if m.boss:
            ui.circle(surf, (255, 70, 70), (x, y), 6)
            ui.circle(surf, WHITE, (x, y), 6, 1)
        elif math.hypot(m.x - p.x, m.y - p.y) < 560:
            ui.circle(surf, (255, 180, 60) if m.elite else (240, 80, 70), (x, y), 3 if m.elite else 2.2)
    for o in world.interactables:
        name = o.__class__.__name__
        if name not in ("Portal", "Chest", "NPC") or (int(o.x // 40), int(o.y // 40)) not in seen:
            continue
        x, y = pos(o.x, o.y)
        if not _in_disc(clip, x, y):
            continue
        if name == "Portal":
            pts = [(x, y - 7), (x + 6, y), (x, y + 7), (x - 6, y)]
            ui.polygon(surf, SHEIKAH, pts)
            ui.polygon(surf, WHITE, pts, 1)
        elif name == "Chest" and not o.opened:
            ui.rect(surf, (244, 204, 80), (x - 4, y - 3, 8, 6))
        elif name == "NPC":
            ui.circle(surf, (250, 222, 130), (x, y), 4.5)
            ui.circle(surf, (60, 40, 10), (x, y), 4.5, 1)
    for l in world.loot:
        if l.kind == "anima":
            x, y = pos(l.x, l.y)
            if _in_disc(clip, x, y):
                ui.circle(surf, (130, 200, 255), (x, y), 3.5)


def draw_minimap(surf, world):
    mm = world.minimap
    p = world.player
    s = VIEW.s
    zoom = 2.2                         # unités de conception par pixel de minicarte
    box = MM
    src = int(box.w * 1.45 / zoom) + 4
    px, py = p.x / 40 * mm.S, p.y / 40 * mm.S
    area = pygame.Surface((src, src), pygame.SRCALPHA)
    area.blit(mm.surf, (-(px - src / 2), -(py - src / 2)))
    rot = pygame.transform.rotate(area, -45)
    k = zoom * s
    rot = pygame.transform.smoothscale(rot, (int(rot.get_width() * k), int(rot.get_height() * k)))
    pb = ui.R(box)
    disc = pygame.Surface(pb.size, pygame.SRCALPHA)
    disc.fill((10, 20, 26, 190))
    disc.blit(rot, (pb.w / 2 - rot.get_width() / 2, pb.h / 2 - rot.get_height() / 2))
    disc.blit(_round_mask(pb.w, pb.h, pb.w // 2), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(disc, pb)
    old = surf.get_clip()
    surf.set_clip(pb)
    _markers(surf, world, box.centerx, box.centery, zoom * mm.S / 40, box)
    surf.set_clip(old)
    ui.circle(surf, (0, 0, 0), box.center, box.w / 2 + 3, 3)
    ui.circle(surf, UI_LINE, box.center, box.w / 2, 2)
    _arrow(surf, box.centerx, box.centery, math.atan2(*reversed(_rot(math.cos(p.facing), math.sin(p.facing)))), 9)
    title, sub = world.hud_title()
    if title:
        ui.draw_text(surf, title, (box.right, box.y - 18), 14, WHITE, "bold", anchor="bottomright")


def draw_gauges(surf, world):
    """Jauge « thermomètre » (sceau du gardien) et jauge de « bruit » (menace) à gauche de la minicarte."""
    t = world.time
    x = MM.x - 22
    prog = world.seal_progress()
    if prog is not None:
        frac, broken = prog
        top, bot = MM.y + 10, MM.bottom - 26
        ui.rect(surf, (0, 0, 0, 170), (x - 6, top - 4, 12, bot - top + 8), 0, 6)
        h = (bot - top) * min(1.0, frac)
        col = (255, 110, 60) if not broken else (120, 230, 140)
        ui.rect(surf, col, (x - 3, bot - h, 6, h), 0, 3)
        for i in range(1, 5):
            yy = top + (bot - top) * i / 5
            ui.line(surf, (200, 200, 196), (x - 9, yy), (x - 6, yy), 1)
        ui.circle(surf, (0, 0, 0, 170), (x, MM.bottom - 12), 11)
        ui.circle(surf, col, (x, MM.bottom - 12), 8)
        ui.rect(surf, UI_LINE, (x - 6, top - 4, 12, bot - top + 8), 1, 6)
        x -= 34
    threat = sum(1 for m in world.monsters if m.aggro and not m.dead)
    cx, cy = x, MM.bottom - 26
    ui.circle(surf, (0, 0, 0, 160), (cx, cy), 16)
    ui.circle(surf, UI_LINE, (cx, cy), 16, 1)
    amp = min(1.0, threat / 8)
    pts = []
    for i in range(17):
        u = -12 + i * 1.5
        pts.append((cx + u, cy + math.sin(t * 12 + i * 0.9) * 9 * amp * (1 - abs(u) / 13)))
    ui.lines(surf, (255, 120, 90) if amp > 0.5 else (230, 230, 220), False, pts, 2)


def draw_big_map(surf, world):
    mm = world.minimap
    p = world.player
    ui.veil(surf, (8, 18, 24), 238)
    for x in range(0, SCREEN_W, 64):
        ui.line(surf, (26, 50, 60), (x, 0), (x, SCREEN_H))
    for y in range(0, SCREEN_H, 64):
        ui.line(surf, (26, 50, 60), (0, y), (SCREEN_W, y))
    rot = pygame.transform.rotate(mm.surf, -45)
    avail_w, avail_h = (SCREEN_W - 180) * VIEW.s, (SCREEN_H - 190) * VIEW.s
    k = min(avail_w / rot.get_width(), avail_h / rot.get_height())
    rot = pygame.transform.smoothscale(rot, (int(rot.get_width() * k), int(rot.get_height() * k)))
    r = rot.get_rect(center=(SCREEN_W / 2 * VIEW.s, (SCREEN_H / 2 + 12) * VIEW.s))
    surf.blit(rot, r)
    # centre de la carte (monde) -> position du joueur à l'écran
    scale = k / VIEW.s * mm.S / 40
    cx0 = mm.surf.get_width() / 2 / mm.S * 40
    cy0 = mm.surf.get_height() / 2 / mm.S * 40
    u, v = _rot((p.x - cx0) * scale, (p.y - cy0) * scale)
    pcx, pcy = r.centerx / VIEW.s + u, r.centery / VIEW.s + v
    _markers(surf, world, pcx, pcy, scale, pygame.Rect(0, 0, SCREEN_W, SCREEN_H))
    _arrow(surf, pcx, pcy, math.atan2(*reversed(_rot(math.cos(p.facing), math.sin(p.facing)))), 13)
    frame = pygame.Rect(40, 40, SCREEN_W - 80, SCREEN_H - 80)
    for (ax, ay), (dx, dy) in (((frame.left, frame.top), (1, 1)), ((frame.right, frame.top), (-1, 1)),
                               ((frame.left, frame.bottom), (1, -1)), ((frame.right, frame.bottom), (-1, -1))):
        ui.line(surf, SHEIKAH, (ax, ay), (ax + dx * 44, ay), 2)
        ui.line(surf, SHEIKAH, (ax, ay), (ax, ay + dy * 44), 2)
    title, sub = world.hud_title()
    ui.draw_text(surf, title or "Carte", (72, 54), 30, WHITE, "title")
    if sub:
        ui.draw_text(surf, sub, (74, 94), 15, (190, 215, 225))
    legend = [((255, 224, 60), "Vous"), (SHEIKAH, "Portail"), ((244, 204, 80), "Coffre"), ((255, 70, 70), "Gardien"),
              ((130, 200, 255), "Anima")]
    lx = SCREEN_W - 70
    for col, name in reversed(legend):
        rr = ui.draw_text(surf, name, (lx, SCREEN_H - 66), 15, WHITE, anchor="bottomright")
        ui.circle(surf, col, (rr.x - 12, rr.centery), 6)
        lx = rr.x - 34
    ui.draw_text(surf, "[Tab] Fermer", (72, SCREEN_H - 66), 15, (190, 215, 225), anchor="bottomleft")


# --------------------------------------------------------------------------- éléments divers
def draw_prompt(surf, text, pt):
    """Bulle d'interaction façon BotW : touche ronde + libellé."""
    tw, th = ui.text_size(text, 15, "bold")
    r = pygame.Rect(0, 0, tw + 46, 30)
    r.midleft = (pt[0] + 26, pt[1])
    ui.botw_box(surf, r, 175, UI_LINE, radius=15)
    b = (r.x + 16, r.centery)
    ui.circle(surf, (245, 243, 235), b, 11)
    ui.draw_text(surf, "E", b, 13, (20, 20, 20), "bold", anchor="center", shadow=False)
    ui.draw_text(surf, text, (r.x + 34, r.centery), 15, WHITE, "bold", anchor="midleft")


def low_hp_veil(surf, alpha):
    w, h = surf.get_size()
    key = ("veil", w, h)
    v = _mask_cache.get(key)
    if v is None:
        v = pygame.Surface((w // 4, h // 4), pygame.SRCALPHA)
        v.fill((150, 0, 0, 255))
        cx, cy = v.get_width() / 2, v.get_height() / 2
        n = 30
        for i in range(n + 1):
            k = i / n
            a = int(255 * (1 - k) ** 2)
            sx, sy = cx * (1.25 - 0.6 * k), cy * (1.25 - 0.6 * k)
            pygame.draw.ellipse(v, (150, 0, 0, a), (cx - sx, cy - sy, sx * 2, sy * 2))
        v = pygame.transform.smoothscale(v, (w, h))
        _mask_cache[key] = v
    t = v.copy()
    t.set_alpha(int(alpha))
    surf.blit(t, (0, 0))


def draw_top(surf, world):
    boss = world.active_boss()
    if boss:
        w = 560
        r = pygame.Rect(SCREEN_W // 2 - w // 2, SCREEN_H - 58, w, 12)
        ui.draw_text(surf, boss.name, (r.x, r.y - 4), 20, WHITE, "title", anchor="bottomleft")
        ui.draw_text(surf, boss.title, (r.right, r.y - 5), 14, SOFT, anchor="bottomright")
        ui.rect(surf, (0, 0, 0), r.inflate(4, 4), 0, 6)
        ui.rect(surf, (60, 10, 12), r, 0, 5)
        fw = r.w * max(0.0, boss.hp / boss.max_hp)
        if fw > 1:
            ui.rect(surf, (226, 40, 52), (r.x, r.y, fw, r.h), 0, 5)
            ui.line(surf, (255, 150, 150), (r.x + 4, r.y + 2), (r.x + fw - 4, r.y + 2))
        ui.rect(surf, UI_LINE, r.inflate(4, 4), 1, 6)
    b = world.banner
    if b:
        text, sub, color, t, dur = b
        k = max(0.0, min(1, t / 0.5, (dur - t) / 0.7))
        if k > 0:
            cy = 150
            if sub:
                ui.draw_text(surf, sub, (SCREEN_W / 2, cy - 30), 16, SOFT, anchor="center", alpha=int(255 * k))
            r = ui.draw_text(surf, text, (SCREEN_W / 2, cy), 40, color, "title", anchor="center", alpha=int(255 * k))
            L = 160 * k
            for d in (-1, 1):
                x0 = SCREEN_W / 2 + d * (r.w / 2 + 18)
                ui.line(surf, color, (x0, cy + 2), (x0 + d * L, cy + 2), 1)
                ui.circle(surf, color, (x0, cy + 2), 2.5)


def draw_notifs(surf, world):
    y = SCREEN_H - 30
    for it, t in reversed(world.notifs):
        k = min(1.0, t / 0.5, (4.0 - t) / 0.25 if t > 3.75 else 1.0)
        col = RARITY_COLORS[it["rarity"]]
        tw, th = ui.text_size(it["name"], 15, "bold")
        r = pygame.Rect(22 - (1 - k) * 60, y - 34, tw + 64, 34)
        ui.botw_box(surf, r, int(170 * k), col, radius=17)
        icon = pygame.Rect(r.x + 5, r.y + 3, 28, 28)
        if it["slot"] == "artefact":
            ui.draw_artifact_icon(surf, it["art"], icon, ARTIFACTS[it["art"]]["color"])
        else:
            ui.draw_item_icon(surf, it, icon, bg=False)
        ui.draw_text(surf, it["name"], (r.x + 42, r.centery), 15, col, "bold", anchor="midleft", alpha=int(255 * k))
        y -= 40


def draw_messages(surf, world):
    y = SCREEN_H - 40 - 40 * len(world.notifs) - 10
    for text, color, t in reversed(world.messages[-5:]):
        if t <= 0:
            continue
        a = int(255 * min(1.0, t))
        ui.draw_text(surf, text, (24, y - 22), 15, color, "bold", alpha=a)
        y -= 24
