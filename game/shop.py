"""Échoppe d'un marchand : une seule grande fenêtre en trois colonnes.
Étal (Acheter / Racheter) · fiche de l'objet choisi, comparée à l'équipement porté · sac du héros.
Clic : choisir un objet · double-clic ou clic droit : acheter / vendre tout de suite."""
import pygame

from . import coins, sfx, ui
from .items import AFFIX_DEF, SLOT_NAMES, buy_price, item_lines, item_stats, item_value
from .data import BAG_SIZE
from .settings import GOLD, RARITY_COLORS, RED, SHEIKAH, TEXT_DIM, WHITE
from .ui import BOTW_YELLOW

SOFT = (206, 212, 212)
UP = (110, 235, 120)
DOWN = (240, 90, 80)
INK = (236, 226, 200)
DOUBLE_CLICK = 0.35
EQ_SLOTS = ("arme", "casque", "torse", "gants", "bottes", "amulette", "anneau")


def item_power(it):
    """Valeur de comparaison d'un objet : dégâts moyens (arme), armure, sinon valeur marchande."""
    st = item_stats(it)
    if "dmg" in st:
        return (st["dmg"][0] + st["dmg"][1]) / 2
    if st.get("armor"):
        return st["armor"]
    return item_value(it)


def compare_mark(surf, it, player, c):
    """Flèche verte (mieux que l'objet porté), rouge (moins bien), ou rien."""
    if it["slot"] == "artefact" or not player.can_equip(it):
        return
    eq = player.equipment.get(it["slot"])
    d = item_power(it) - (item_power(eq) if eq else 0)
    if abs(d) < 0.5:
        return
    x, y = c
    if d > 0:
        ui.polygon(surf, UP, [(x - 6, y + 4), (x + 6, y + 4), (x, y - 5)])
    else:
        ui.polygon(surf, DOWN, [(x - 6, y - 4), (x + 6, y - 4), (x, y + 5)])


def stat_diff(it, eq):
    """Écarts de statistiques entre un objet et celui porté : [(texte, meilleur ?)]."""
    a, b = item_stats(it), item_stats(eq) if eq else {"affixes": {}}
    out = []
    if "dmg" in a:
        d = sum(a["dmg"]) / 2 - (sum(b["dmg"]) / 2 if "dmg" in b else 0)
        if abs(d) >= 0.5:
            out.append((f"{d:+.0f} dégâts moyens", d > 0))
    d = a.get("armor", 0) - b.get("armor", 0)
    if abs(d) >= 0.5:
        out.append((f"{d:+.0f} armure", d > 0))
    for k in list(dict.fromkeys(list(a["affixes"]) + list(b["affixes"]))):
        d = a["affixes"].get(k, 0) - b["affixes"].get(k, 0)
        if not d:
            continue
        tpl = AFFIX_DEF[k][0]
        v = round(abs(d), 1)
        v = int(v) if v == int(v) else v
        txt = tpl.format(v=v)
        good = d > 0
        if d < 0:                                     # le signe du modèle s'inverse
            txt = ("-" if txt[0] == "+" else "+") + txt[1:]
        out.append((txt, good))
    return out


class ShopScreen:
    """Fenêtre modale du marchand (world.modal)."""
    modal = True
    hide_hud = True              # le HUD s'efface derrière cette fenêtre
    TABS = ("Acheter", "Racheter")
    W = pygame.Rect(40, 34, 1200, 652)

    def __init__(self, world, npc_id="gorvan"):
        from . import town
        self.world = world
        self.name = town.SHOPKEEPERS.get(npc_id, "Marchand")
        self.quote = "« Tout se vend, tout s'achète. »"
        self.tab = 0
        self.sel = None                   # ("stock" | "bag", index)
        self.hover = None                 # (source, index, objet)
        self.last_click = (None, -1.0)
        self.t = 0.0
        W = self.W
        top = W.y + 116
        self.stall = pygame.Rect(W.x + 24, top, 520, W.bottom - 40 - top)
        self.detail = pygame.Rect(self.stall.right + 20, top, 300, W.bottom - 40 - top)
        self.bag = pygame.Rect(self.detail.right + 20, top, W.right - 24 - self.detail.right - 20, W.bottom - 40 - top)
        self.tab_rects = []
        x = self.stall.x
        for name in self.TABS:
            w = ui.text_size(name, 17, "title")[0] + 44
            self.tab_rects.append(pygame.Rect(x, top, w, 34))
            x += w + 6
        self.cards = [pygame.Rect(self.stall.x + (i % 2) * 265, top + 50 + (i // 2) * 82, 255, 74) for i in range(10)]
        cols, step = 7, 42
        gx = self.bag.x + (self.bag.w - cols * step) // 2 + 2
        # équipement porté (au-dessus du sac) : pour comparer d'un coup d'œil
        self.eq_rects = {s: pygame.Rect(gx + i * step, top + 30, step - 4, step - 4) for i, s in enumerate(EQ_SLOTS)}
        self.cells = [pygame.Rect(gx + (i % cols) * step, top + 118 + (i // cols) * step, step - 4, step - 4)
                      for i in range(BAG_SIZE)]
        self.act_btn = pygame.Rect(self.detail.x + 16, self.detail.bottom - 58, self.detail.w - 32, 42)
        self.junk_btn = pygame.Rect(self.bag.x + 12, self.cells[-1].bottom + 18, self.bag.w - 24, 38)
        self.close_btn = pygame.Rect(W.right - 52, W.y + 14, 34, 34)

    # ------------------------------------------------------------------ données
    def stock(self):
        w = self.world
        return w.shop_stock if self.tab == 0 else w.__dict__.setdefault("buyback", [])

    def selected(self):
        if not self.sel:
            return None
        src, i = self.sel
        if src == "equip":
            return self.world.player.equipment.get(i)
        items = self.stock() if src == "stock" else self.world.player.inventory
        return items[i] if i < len(items) else None

    def price(self, src, it):
        if src == "bag":
            return item_value(it)
        return buy_price(it) if self.tab == 0 else item_value(it)

    def junk(self):
        return [it for it in self.world.player.inventory if it["rarity"] == "commun" and it["slot"] != "artefact"]

    # ------------------------------------------------------------------ actions
    def act(self, src, i):
        w = self.world
        if src == "equip":
            return
        if src == "bag":
            w.sell_item(i)
        elif self.tab == 0:
            w.buy_item(i)
        else:
            w.buy_back(i)
        self.sel = None

    def sell_junk(self):
        w = self.world
        p = w.player
        junk = self.junk()
        if not junk:
            w.message("Aucun objet commun dans le sac.", SOFT, 3)
            return
        total = sum(item_value(it) for it in junk)
        for it in junk:
            p.inventory.remove(it)
            w.__dict__.setdefault("buyback", []).insert(0, it)
        del w.buyback[8:]
        p.money += total
        self.sel = None
        w.message(f"{len(junk)} objet(s) vendu(s) : +{coins.text(total)}", GOLD)
        sfx.play("gold")

    def hit(self, pos):
        for i, rc in enumerate(self.cards):
            if rc.collidepoint(pos) and i < len(self.stock()):
                return "stock", i
        for i, rc in enumerate(self.cells):
            if rc.collidepoint(pos) and i < len(self.world.player.inventory):
                return "bag", i
        for s, rc in self.eq_rects.items():
            if rc.collidepoint(pos) and self.world.player.equipment.get(s):
                return "equip", s
        return None

    def handle_event(self, e):
        w = self.world
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            w.close_modal()
            return True
        if e.type != pygame.MOUSEBUTTONDOWN:
            return True
        pos = e.pos
        if e.button == 1 and (self.close_btn.collidepoint(pos) or not self.W.collidepoint(pos)):
            w.close_modal()
            sfx.play("click")
            return True
        for i, rc in enumerate(self.tab_rects):
            if e.button == 1 and rc.collidepoint(pos) and self.tab != i:
                self.tab = i
                if self.sel and self.sel[0] == "stock":
                    self.sel = None
                sfx.play("click")
                return True
        if e.button == 1 and self.junk_btn.collidepoint(pos):
            self.sell_junk()
            return True
        if e.button == 1 and self.act_btn.collidepoint(pos) and self.selected():
            self.act(*self.sel)
            return True
        h = self.hit(pos)
        if h and e.button == 3:
            self.act(*h)
        elif h and e.button == 1:
            prev, when = self.last_click
            if prev == h and self.t - when < DOUBLE_CLICK:
                self.act(*h)
                self.last_click = (None, -1.0)
            else:
                self.sel = h
                self.last_click = (h, self.t)
                sfx.play("click", 0.5)
        return True

    def update(self, dt):
        self.t += dt

    # ------------------------------------------------------------------ dessin
    def draw(self, surf):
        W = self.W
        p = self.world.player
        mouse = ui.mouse_pos()
        self.hover = None
        ui.botw_box(surf, W, 238, (120, 104, 72), radius=14, fill=(12, 12, 14))
        # en-tête : enseigne du marchand, bourse du héros
        med = (W.x + 62, W.y + 56)
        ui.glow(surf, med[0], med[1], 54, (90, 66, 20))
        ui.circle(surf, (24, 20, 16), med, 34)
        ui.circle(surf, GOLD, med, 34, 2)
        ui.draw_text(surf, self.name[0], med, 30, WHITE, "title_bold", anchor="center")
        ui.draw_text(surf, self.name, (W.x + 112, W.y + 22), 26, WHITE, "title")
        ui.draw_text(surf, self.quote, (W.x + 114, W.y + 62), 14, (210, 196, 160))
        ui.draw_text(surf, "Votre bourse", (W.right - 70, W.y + 24), 12, TEXT_DIM, "bold", anchor="topright")
        ui.draw_money(surf, p.money, (W.right - 70, W.y + 56), 20, "midright")
        self.draw_close(surf, mouse)
        ui.line(surf, (70, 62, 48), (W.x + 20, W.y + 100), (W.right - 20, W.y + 100), 1)
        self.draw_stall(surf, mouse)
        self.draw_detail(surf, mouse)
        self.draw_bag(surf, mouse)
        ui.draw_text(surf, "Clic : examiner  ·  Double-clic ou clic droit : acheter / vendre  ·  Échap : fermer",
                     (W.centerx, W.bottom - 20), 12, TEXT_DIM, anchor="center", shadow=False)
        self.draw_tooltips(surf)

    def draw_close(self, surf, mouse):
        r = self.close_btn
        hov = r.collidepoint(mouse)
        ui.circle(surf, (60, 30, 26) if hov else (24, 22, 22), r.center, 16)
        ui.circle(surf, DOWN if hov else (110, 100, 90), r.center, 16, 1)
        c = r.center
        col = WHITE if hov else SOFT
        ui.line(surf, col, (c[0] - 6, c[1] - 6), (c[0] + 6, c[1] + 6), 2)
        ui.line(surf, col, (c[0] - 6, c[1] + 6), (c[0] + 6, c[1] - 6), 2)

    def draw_stall(self, surf, mouse):
        p = self.world.player
        for i, (name, rc) in enumerate(zip(self.TABS, self.tab_rects)):
            act = i == self.tab
            hov = rc.collidepoint(mouse)
            n = len(self.world.shop_stock) if i == 0 else len(self.world.__dict__.get("buyback", []))
            ui.draw_text(surf, name, (rc.x + 4, rc.centery), 17, WHITE if act else (SOFT if hov else TEXT_DIM),
                         "title", anchor="midleft")
            tw = ui.text_size(name, 17, "title")[0]
            b = pygame.Rect(rc.x + tw + 12, rc.centery - 10, 24, 20)
            ui.rect(surf, (60, 50, 26) if act else (30, 30, 30), b, 0, 10)
            ui.draw_text(surf, str(n), b.center, 11, BOTW_YELLOW if act else SOFT, "bold", anchor="center",
                         shadow=False)
            if act:
                ui.rect(surf, BOTW_YELLOW, (rc.x + 2, rc.bottom - 3, rc.w - 8, 3), 0, 2)
        ui.line(surf, (50, 50, 50), (self.stall.x, self.tab_rects[0].bottom + 2),
                (self.stall.right, self.tab_rects[0].bottom + 2), 1)
        items = self.stock()
        if not items:
            msg = ("L'étal est vide : revenez après votre prochaine ascension." if self.tab == 0
                   else "Les objets que vous vendez ici peuvent être rachetés tant que vous restez en ville.")
            for j, line in enumerate(ui.wrap(msg, 14, 380)):
                ui.draw_text(surf, line, (self.stall.centerx, self.cards[0].y + 60 + j * 20), 14, TEXT_DIM,
                             anchor="center")
        for i, rc in enumerate(self.cards):
            if i >= len(items):
                break
            it = items[i]
            col = RARITY_COLORS[it["rarity"]]
            hov = rc.collidepoint(mouse)
            sel = self.sel == ("stock", i)
            if hov:
                self.hover = ("stock", i, it)
            ui.rect(surf, (28, 30, 34) if hov or sel else (20, 21, 24), rc, 0, 8)
            ui.rect(surf, BOTW_YELLOW if sel else (ui.darker(col, 0.8) if hov else (46, 46, 50)), rc, 2 if sel else 1, 8)
            ic = pygame.Rect(rc.x + 8, rc.y + 8, 58, 58)
            ui.rect(surf, (*ui.darker(col, 0.35), 255), ic, 0, 8)
            ui.rect(surf, ui.darker(col, 0.8), ic, 1, 8)
            ui.draw_item_icon(surf, it, ic.inflate(-14, -14), bg=False)
            name = it["name"]
            while ui.text_size(name, 14, "bold")[0] > rc.w - 86 and len(name) > 4:
                name = name[:-2] + "…"
            ui.draw_text(surf, name, (rc.x + 76, rc.y + 9), 14, col, "bold", shadow=False)
            ok = p.can_equip(it)
            sub = f"{SLOT_NAMES[it['slot']]} · niv. {it.get('ilvl', 1)}"
            ui.draw_text(surf, sub if ok else "Autre classe", (rc.x + 76, rc.y + 29), 12,
                         TEXT_DIM if ok else (220, 130, 120), shadow=False)
            price = self.price("stock", it)
            ui.draw_money(surf, price, (rc.right - 10, rc.bottom - 16), 13, "midright",
                          WHITE if p.money >= price else RED)
            compare_mark(surf, it, p, (rc.x + 84, rc.bottom - 15))

    def draw_detail(self, surf, mouse):
        d = self.detail
        p = self.world.player
        ui.rect(surf, (18, 17, 16), d, 0, 10)
        ui.rect(surf, (74, 64, 46), d, 1, 10)
        it = self.selected()
        if not it:
            self.sel = None
            c = (d.centerx, d.y + 150)
            ui.circle(surf, (30, 28, 26), c, 44)
            ui.circle(surf, (70, 62, 48), c, 44, 1)
            ui.draw_text(surf, "?", c, 40, (90, 82, 66), "title_bold", anchor="center")
            for j, line in enumerate(ui.wrap("Choisissez un objet de l'étal ou de votre sac pour l'examiner.", 14,
                                             d.w - 60)):
                ui.draw_text(surf, line, (d.centerx, c[1] + 70 + j * 20), 14, TEXT_DIM, anchor="center")
            return
        src, i = self.sel
        col = RARITY_COLORS[it["rarity"]]
        ic = pygame.Rect(d.x + 16, d.y + 16, 64, 64)
        ui.glow(surf, ic.centerx, ic.centery, 50, ui.darker(col, 0.4))
        ui.rect(surf, ui.darker(col, 0.35), ic, 0, 10)
        ui.rect(surf, col, ic, 1, 10)
        ui.draw_item_icon(surf, it, ic.inflate(-14, -14), bg=False)
        y = d.y + 18
        for line in ui.wrap(it["name"] + (f" +{it['upgrade']}" if it.get("upgrade") else ""), 16, d.w - 112,
                            "bold")[:2]:
            ui.draw_text(surf, line, (ic.right + 12, y), 16, col, "bold", shadow=False)
            y += 21
        ui.draw_text(surf, f"{SLOT_NAMES[it['slot']]}", (ic.right + 12, y + 2), 12, TEXT_DIM, shadow=False)
        y = ic.bottom + 14
        limit = self.act_btn.y - 44
        # caractéristiques (sans le nom, le type ni la valeur, déjà affichés)
        skip = {it["name"], it.get("base")}
        for text, c, sz in item_lines(it, p):
            if text in skip or text.startswith(("Valeur", SLOT_NAMES[it["slot"]] + " —")) or \
                    text.startswith(it["name"]):
                continue
            size = max(12, sz - 3)
            for line in ui.wrap(text, size, d.w - 32):
                if y > limit:
                    break
                ui.draw_text(surf, line, (d.x + 16, y), size, c, shadow=False)
                y += size + 5
        # comparaison avec l'objet porté
        if src != "equip" and it["slot"] != "artefact" and p.can_equip(it) and y < limit - 30:
            eq = p.equipment.get(it["slot"]) if not (src == "bag" and it is p.equipment.get(it["slot"])) else None
            y += 6
            ui.line(surf, (60, 54, 42), (d.x + 16, y), (d.right - 16, y), 1)
            y += 8
            head = "Par rapport à " + (eq["name"] if eq else "l'emplacement vide")
            while ui.text_size(head, 12, "bold")[0] > d.w - 32 and len(head) > 16:
                head = head[:-2] + "…"
            ui.draw_text(surf, head, (d.x + 16, y), 12, SHEIKAH, "bold", shadow=False)
            y += 20
            diffs = stat_diff(it, eq)
            if not diffs:
                ui.draw_text(surf, "Aucune différence", (d.x + 16, y), 12, TEXT_DIM, shadow=False)
            for text, good in diffs:
                if y > limit:
                    break
                ui.polygon(surf, UP if good else DOWN,
                           [(d.x + 18, y + 11), (d.x + 26, y + 11), (d.x + 22, y + 4)] if good else
                           [(d.x + 18, y + 5), (d.x + 26, y + 5), (d.x + 22, y + 12)])
                ui.draw_text(surf, text, (d.x + 34, y), 12, UP if good else DOWN, shadow=False)
                y += 18
        if src == "equip":
            b = self.act_btn
            ui.rect(surf, (30, 40, 34), b, 0, b.h // 2)
            ui.rect(surf, UP, b, 1, b.h // 2)
            ui.draw_text(surf, "Porté actuellement", b.center, 16, UP, "bold", anchor="center")
            return
        # prix et bouton
        price = self.price(src, it)
        verb = "Vendre" if src == "bag" else ("Acheter" if self.tab == 0 else "Racheter")
        afford = src == "bag" or p.money >= price
        ui.draw_text(surf, "Prix de vente" if src == "bag" else "Prix", (d.x + 16, self.act_btn.y - 22), 13, SOFT,
                     "bold", anchor="midleft", shadow=False)
        ui.draw_money(surf, price, (d.right - 16, self.act_btn.y - 22), 15, "midright", WHITE if afford else RED)
        b = self.act_btn
        hov = b.collidepoint(mouse) and afford
        base = (120, 60, 40) if src == "bag" else (40, 100, 60)
        ui.rect(surf, ui.lighter(base, 1.3) if hov else (base if afford else (40, 40, 40)), b, 0, b.h // 2)
        ui.rect(surf, (230, 210, 160) if hov else (120, 110, 90), b, 1, b.h // 2)
        ui.draw_text(surf, verb if afford else "Pas assez d'argent", b.center, 17, WHITE if afford else TEXT_DIM,
                     "bold", anchor="center")

    def draw_bag(self, surf, mouse):
        r = self.bag
        p = self.world.player
        # équipement porté ; l'emplacement de l'objet examiné est éclairé
        ui.draw_text(surf, "Équipé", (r.x + 4, r.y + 2), 15, WHITE, "title")
        h = self.hit(mouse)
        if h and h[0] != "equip":
            focus = (self.stock() if h[0] == "stock" else p.inventory)[h[1]]
        else:
            focus = self.selected() if self.sel else None
        for s, rc in self.eq_rects.items():
            it = p.equipment.get(s)
            lit = focus is not None and focus.get("slot") == s
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = ("equip", s, it)
            if it:
                col = RARITY_COLORS[it["rarity"]]
                ui.rect(surf, ui.darker(col, 0.3) if it["rarity"] != "commun" else (34, 34, 36), rc, 0, 6)
                ui.rect(surf, WHITE if hov else ui.darker(col, 0.75), rc, 1, 6)
                ui.draw_item_icon(surf, it, rc.inflate(-10, -10), bg=False)
            else:
                ui.rect(surf, (22, 22, 24), rc, 0, 6)
                ui.draw_text(surf, SLOT_NAMES[s][:3], rc.center, 10, (90, 92, 92), anchor="center", shadow=False)
            if lit or self.sel == ("equip", s):
                ui.rect(surf, BOTW_YELLOW, rc.inflate(4, 4), 2, 8)
        top = self.cells[0].y - 30
        ui.draw_text(surf, "Votre sac", (r.x + 4, top), 15, WHITE, "title")
        ui.draw_text(surf, f"{len(p.inventory)} / {BAG_SIZE}", (r.right - 4, top + 4), 13,
                     RED if len(p.inventory) >= BAG_SIZE else TEXT_DIM, "bold", anchor="topright", shadow=False)
        for i, rc in enumerate(self.cells):
            it = p.inventory[i] if i < len(p.inventory) else None
            hov = rc.collidepoint(mouse) and it is not None
            if hov:
                self.hover = ("bag", i, it)
            if not it:
                ui.rect(surf, (22, 22, 24), rc, 0, 6)
                continue
            col = RARITY_COLORS[it["rarity"]]
            ui.rect(surf, ui.darker(col, 0.3) if it["rarity"] != "commun" else (34, 34, 36), rc, 0, 6)
            ui.rect(surf, WHITE if hov else ui.darker(col, 0.75), rc, 1, 6)
            ui.draw_item_icon(surf, it, rc.inflate(-10, -10), bg=False)
            if not p.can_equip(it) and it["slot"] != "artefact":
                ui.line(surf, DOWN, (rc.x + 5, rc.bottom - 5), (rc.right - 5, rc.y + 5), 2)
            if self.sel == ("bag", i):
                ui.rect(surf, BOTW_YELLOW, rc.inflate(4, 4), 2, 8)
        # vente du commun
        junk = self.junk()
        b = self.junk_btn
        hov = b.collidepoint(mouse) and junk
        ui.rect(surf, (60, 44, 30) if hov else (30, 26, 22), b, 0, b.h // 2)
        ui.rect(surf, (200, 170, 110) if junk else (70, 64, 56), b, 1, b.h // 2)
        ui.draw_text(surf, f"Vendre le commun ({len(junk)})", b.center, 14, WHITE if junk else TEXT_DIM, "bold",
                     anchor="center")
        if junk:
            ui.draw_text(surf, "pour", (r.centerx - 10, b.bottom + 16), 12, TEXT_DIM, anchor="midright",
                         shadow=False)
            ui.draw_money(surf, sum(item_value(it) for it in junk), (r.centerx - 4, b.bottom + 16), 12, "midleft")

    def draw_tooltips(self, surf):
        if not self.hover or (self.hover[0], self.hover[1]) == self.sel:
            return
        src, i, it = self.hover
        ui.item_tooltip(surf, it, ui.mouse_pos(), self.world.player, side="left" if src in ("bag", "equip") else "right")
