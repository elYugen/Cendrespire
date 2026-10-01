"""Génération procédurale des étages de la tour, carte du campement et rendu des tuiles."""
import heapq
import math
import random
from collections import deque

import pygame

from .settings import TILE

WALL, FLOOR, BARRIER = 0, 1, 2
# relief : gouffre (infranchissable à pied, les tirs passent au-dessus), rebord d'une estrade surélevée (garde-corps,
# même règle), marches qui montent sur l'estrade
PIT, LEDGE, STAIRS = 3, 4, 5
PLAT_H = 26            # hauteur des estrades, en pixels logiques
TIER_H = 36            # dénivelé entre deux niveaux d'un étage (on descend vers l'arène du gardien)


class Room:
    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def center(self):
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def center_px(self):
        return ((self.x + self.w / 2) * TILE, (self.y + self.h / 2) * TILE)

    def contains(self, tx, ty, margin=0):
        return self.x + margin <= tx < self.x + self.w - margin and self.y + margin <= ty < self.y + self.h - margin

    def intersects(self, o, margin=0):
        return (self.x - margin < o.x + o.w and self.x + self.w + margin > o.x and
                self.y - margin < o.y + o.h and self.y + self.h + margin > o.y)


class Dungeon:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.tiles = [[WALL] * w for _ in range(h)]
        self.rooms = []
        self.start_room = None
        self.boss_room = None
        self.barrier_tiles = []
        self.torches = []
        self.decor = []
        self.secrets = []      # salles cachées : (salle, case du mur fissuré (x, y), contenu "coffre" | "anima")
        self.traps = []        # cases piégées (x, y)
        self.trap_phases = {}  # (x, y) -> décalage du cycle (pièges synchronisés en vague) ; absent = aléatoire
        self.trap_rooms = []   # salles piégées : un trésor au centre d'un champ de pointes (ou de flammes)
        self.trap_kinds = {}   # (x, y) -> "spikes" | "flames" (absent : pointes)
        self.darts = []        # lanceurs de fléchettes : (case du mur x, y, direction dx, dy)
        self.saws = []         # lames sur rail : ((x0, y0), (x1, y1)) en cases
        self.raised = set()    # cases surélevées (dessus et rebord des estrades)
        self.stairs = {}       # case de marches -> (dx, dy sens de la montée, z bas, z haut relatifs au niveau de la case)
        self.zb = [[0.0] * w for _ in range(h)]   # hauteur du niveau (palier) de chaque case, en pixels (0 ou négatif)
        self.tiers = 1
        self.daises = []       # estrades au centre d'une salle : (x, y, w, h) du dessus praticable

    def carve_rect(self, r):
        for y in range(r.y, r.y + r.h):
            for x in range(r.x, r.x + r.w):
                self.tiles[y][x] = FLOOR

    def carve_path(self, a, b, forbid=None):
        """A* entre deux tuiles, puis creuse un couloir de 2 tuiles de large."""
        W, H = self.w, self.h

        def ok(x, y):
            if not (1 <= x < W - 2 and 1 <= y < H - 2):
                return False
            if forbid:
                for fx, fy in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    if forbid.contains(fx, fy):
                        return False
            return True

        openq = [(0, a)]
        g = {a: 0}
        came = {}
        while openq:
            _, cur = heapq.heappop(openq)
            if cur == b:
                break
            cx, cy = cur
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if not ok(nx, ny) and (nx, ny) != b:
                    continue
                cost = 1 if self.tiles[ny][nx] == FLOOR else 3
                ng = g[cur] + cost
                if ng < g.get((nx, ny), 1e9):
                    g[(nx, ny)] = ng
                    came[(nx, ny)] = cur
                    heapq.heappush(openq, (ng + abs(nx - b[0]) + abs(ny - b[1]), (nx, ny)))
        if b not in came and a != b:
            return False
        node = b
        while True:
            x, y = node
            for fx, fy in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                if 1 <= fx < W - 1 and 1 <= fy < H - 1:
                    self.tiles[fy][fx] = FLOOR
            if node == a:
                break
            node = came[node]
        return True

    def generate(self, rng, n_rooms=10, boss_size=(21, 17)):
        W, H = self.w, self.h
        bw, bh = boss_size
        boss = Room(rng.randint(3, W - bw - 3), rng.randint(3, H - bh - 3), bw, bh)
        rooms = []
        tries = 0
        while len(rooms) < n_rooms and tries < 12000:
            tries += 1
            w, h = rng.randint(8, 14), rng.randint(7, 11)
            r = Room(rng.randint(2, W - w - 2), rng.randint(2, H - h - 2), w, h)
            if r.intersects(boss, 5) or any(r.intersects(o, 2) for o in rooms):
                continue
            rooms.append(r)
        for r in rooms + [boss]:
            self.carve_rect(r)
        bc = boss.center
        start = max(rooms, key=lambda r: math.dist(r.center, bc))
        forbid = Room(boss.x - 2, boss.y - 2, boss.w + 4, boss.h + 4)
        # arbre couvrant minimal (Prim) + quelques boucles
        connected, remaining = [start], [r for r in rooms if r is not start]
        while remaining:
            best = min(((math.dist(a.center, b.center), a, b) for a in connected for b in remaining),
                       key=lambda t: t[0])
            _, a, b = best
            if not self.carve_path(a.center, b.center, forbid):
                self.carve_path(a.center, b.center)
            connected.append(b)
            remaining.remove(b)
        for _ in range(max(3, len(rooms) // 4)):     # boucles entre salles voisines
            a = rng.choice(rooms)
            b = rng.choice(sorted((r for r in rooms if r is not a), key=lambda r: math.dist(r.center, a.center))[:4])
            self.carve_path(a.center, b.center, forbid)
        # une seule entrée vers la salle du gardien
        near = min(rooms, key=lambda r: math.dist(r.center, bc))
        self.carve_path(near.center, bc)
        # scellé magique à l'entrée
        ring = [(x, boss.y - 1) for x in range(boss.x - 1, boss.x + boss.w + 1)]
        ring += [(x, boss.y + boss.h) for x in range(boss.x - 1, boss.x + boss.w + 1)]
        ring += [(boss.x - 1, y) for y in range(boss.y, boss.y + boss.h)]
        ring += [(boss.x + boss.w, y) for y in range(boss.y, boss.y + boss.h)]
        for x, y in ring:
            if self.tiles[y][x] == FLOOR:
                self.tiles[y][x] = BARRIER
                self.barrier_tiles.append((x, y))
        # piliers dans l'arène
        for px, py in ((3, 3), (boss.w - 4, 3), (3, boss.h - 4), (boss.w - 4, boss.h - 4)):
            self.tiles[boss.y + py][boss.x + px] = WALL
        self.rooms, self.start_room, self.boss_room = rooms, start, boss
        self._secret_rooms(rng, rooms, start, boss)
        self._trap_rooms(rng, rooms, start, boss)
        if len(rooms) >= 8:
            self._relief(rng, rooms, start, boss)
            self._tiers(rng, rooms, start, boss)
        self._traps(rng, rooms, start, boss)
        self._decorate(rng)

    def _secret_rooms(self, rng, rooms, start, boss):
        """Petites salles murées, reliées à une salle par un couloir fermé d'un mur fissuré (à briser)."""
        want = 3 + len(rooms) // 8
        for room in rng.sample(rooms, len(rooms)):
            if len(self.secrets) >= want:
                break
            if room is start:
                continue
            for _ in range(8):
                w, h = rng.randint(5, 7), rng.randint(5, 6)
                side = rng.choice("NSEW")
                gap = rng.randint(2, 4)
                if side == "N":
                    r = Room(room.x + rng.randint(0, max(0, room.w - w)), room.y - gap - h, w, h)
                elif side == "S":
                    r = Room(room.x + rng.randint(0, max(0, room.w - w)), room.y + room.h + gap, w, h)
                elif side == "W":
                    r = Room(room.x - gap - w, room.y + rng.randint(0, max(0, room.h - h)), w, h)
                else:
                    r = Room(room.x + room.w + gap, room.y + rng.randint(0, max(0, room.h - h)), w, h)
                if r.x < 2 or r.y < 2 or r.x + r.w > self.w - 2 or r.y + r.h > self.h - 2 or r.intersects(boss, 4):
                    continue
                area = [(x, y) for y in range(r.y - 1, r.y + r.h + 1) for x in range(r.x - 1, r.x + r.w + 1)]
                if any(self.tiles[y][x] != WALL for x, y in area):
                    continue
                # couloir entre la salle et la cachette (1 case de large), fermé côté salle par le mur fissuré
                if side in "NS":
                    cx = max(r.x, room.x) + (min(r.x + r.w, room.x + room.w) - max(r.x, room.x)) // 2
                    ys = range(r.y + r.h, room.y) if side == "N" else range(room.y + room.h, r.y)
                    cells = [(cx, y) for y in ys]
                    door = cells[-1] if side == "N" else cells[0]
                else:
                    cy = max(r.y, room.y) + (min(r.y + r.h, room.y + room.h) - max(r.y, room.y)) // 2
                    xs = range(r.x + r.w, room.x) if side == "W" else range(room.x + room.w, r.x)
                    cells = [(x, cy) for x in xs]
                    door = cells[-1] if side == "W" else cells[0]
                if any(self.tiles[y][x] != WALL for x, y in cells):
                    continue
                self.carve_rect(r)
                for x, y in cells:
                    if (x, y) != door:
                        self.tiles[y][x] = FLOOR
                self.secrets.append((r, door, "anima" if len(self.secrets) % 2 else "coffre"))
                # le trésor caché est gardé : des pointes en croix autour de l'autel ou du coffre
                cx, cy = r.center
                for i, (dx, dy) in enumerate(rng.sample(((2, 0), (-2, 0), (0, 2), (0, -2)), rng.randint(2, 4))):
                    if r.contains(cx + dx, cy + dy):
                        self.traps.append((cx + dx, cy + dy))
                        self.trap_phases[(cx + dx, cy + dy)] = i * 0.9
                break

    def _trap_rooms(self, rng, rooms, start, boss):
        """Une ou deux salles couvertes de pointes qui jaillissent en vague, un coffre au centre."""
        cands = [r for r in rooms if r is not start and r.w >= 9 and r.h >= 8]
        for room in rng.sample(cands, min(len(cands), 1 + (len(rooms) >= 18))):
            kind = rng.choice(("spikes", "flames"))
            cx, cy = room.center
            for y in range(room.y + 1, room.y + room.h - 1):
                for x in range(room.x + 1, room.x + room.w - 1):
                    if (x + y) % 2 or (abs(x - cx) <= 1 and abs(y - cy) <= 1):
                        continue
                    self.traps.append((x, y))
                    self.trap_phases[(x, y)] = ((x - room.x) * 0.38) % 3.85
                    self.trap_kinds[(x, y)] = kind
            self.trap_rooms.append(room)

    # ------------------------------------------------------------------ relief
    def _all_connected(self):
        """Toutes les cases praticables (murs fissurés compris) restent reliées entre elles."""
        doors = {door for _r, door, _k in self.secrets}

        def walk(x, y):
            return self.tiles[y][x] in (FLOOR, STAIRS, BARRIER) or (x, y) in doors
        cells = [(x, y) for y in range(self.h) for x in range(self.w) if walk(x, y)]
        if not cells:
            return True
        seen = {cells[0]}
        st = [cells[0]]
        while st:
            x, y = st.pop()
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in seen and 0 <= n[0] < self.w and 0 <= n[1] < self.h and walk(*n):
                    seen.add(n)
                    st.append(n)
        return len(seen) == len(cells)

    def _try(self, changes, raised=(), stairs=None):
        """Applique {case: type} ; annule tout si l'étage se retrouve coupé en morceaux."""
        old = {(x, y): self.tiles[y][x] for x, y in changes}
        if any(t != FLOOR for t in old.values()):
            return False
        for (x, y), t in changes.items():
            self.tiles[y][x] = t
        if not self._all_connected():
            for (x, y), t in old.items():
                self.tiles[y][x] = t
            return False
        self.raised.update(raised)
        self.stairs.update(stairs or {})
        return True

    def _closed(self, cells):
        """Vrai si aucune de ces cases (autour d'une salle) n'est un passage : couloir, mur fissuré."""
        doors = {door for _r, door, _k in self.secrets}
        return all(self.tiles[y][x] == WALL and (x, y) not in doors for x, y in cells)

    def _relief(self, rng, rooms, start, boss):
        """Estrades à escaliers, mezzanines le long d'un mur, gouffres franchis par un pont, trous."""
        pool = [r for r in rooms if r is not start and r not in self.trap_rooms]
        rng.shuffle(pool)
        want = {"dais": 2 + len(rooms) // 10, "mezz": 2, "chasm": 1 + len(rooms) // 12, "holes": 2}
        for room in pool:
            for kind in rng.sample(list(want), len(want)):
                if want[kind] > 0 and getattr(self, "_" + kind)(rng, room):
                    want[kind] -= 1
                    break

    # ------------------------------------------------------------------ paliers
    def _tiers(self, rng, rooms, start, boss):
        """Découpe l'étage en 2 ou 3 paliers de hauteurs différentes, de plus en plus profonds vers le gardien.

        Chaque case prend le palier de la salle la plus proche (en marchant) : les frontières tombent au milieu
        des couloirs. Une frontière nette (couloir droit de 2 cases de large) devient un escalier ; sinon les deux
        salles sont mises au même palier. On recommence jusqu'à ce que toutes les frontières soient des escaliers."""
        W, H = self.w, self.h
        allr = rooms + [boss]
        B = len(allr) - 1
        doors = {door for _r, door, _k in self.secrets}

        def walk(x, y):
            return 0 <= x < W and 0 <= y < H and (self.tiles[y][x] != WALL or (x, y) in doors)
        label = [[-1] * W for _ in range(H)]
        q = deque()
        for i, r in enumerate(allr):
            for y in range(r.y, r.y + r.h):
                for x in range(r.x, r.x + r.w):
                    if walk(x, y) and label[y][x] < 0:
                        label[y][x] = i
                        q.append((x, y))
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if walk(nx, ny) and label[ny][nx] < 0:
                    label[ny][nx] = label[y][x]
                    q.append((nx, ny))
        edges = []                       # (case a, case b, direction a -> b) entre deux zones différentes
        adj = {i: set() for i in range(len(allr))}
        for y in range(H):
            for x in range(W):
                la = label[y][x]
                if la < 0:
                    continue
                for dx, dy in ((1, 0), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if nx < W and ny < H and label[ny][nx] >= 0 and label[ny][nx] != la:
                        edges.append(((x, y), (nx, ny), (dx, dy)))
                        adj[la].add(label[ny][nx])
                        adj[label[ny][nx]].add(la)
        # palier voulu : selon l'éloignement (en salles) depuis le départ
        si = allr.index(start)
        hop = {si: 0}
        bq = deque([si])
        while bq:
            i = bq.popleft()
            for j in adj[i]:
                if j not in hop:
                    hop[j] = hop[i] + 1
                    bq.append(j)
        T = 3 if len(rooms) >= 12 else 2
        order = sorted((i for i in range(B) if i in hop), key=lambda i: (hop[i], rng.random()))
        want = {i: min(T - 1, k * T // max(1, len(order))) for k, i in enumerate(order)}
        parent = list(range(len(allr)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a, b):
            a, b = find(a), find(b)
            if a != b:
                if want.get(a, 0) > want.get(b, 0):
                    a, b = b, a
                parent[b] = a              # le groupe prend le palier le plus haut des deux
        want[B] = max((want.get(j, 0) for j in adj[B]), default=0)
        for j in adj[B]:
            union(B, j)                    # l'arène est au palier de la salle qui y mène

        def tier(i):
            return want.get(find(i), 0)

        def plain(c):
            x, y = c
            return self.tiles[y][x] == FLOOR and c not in self.raised and c not in doors
        crossings = []
        for _ in range(40):
            groups = {}
            for a, b, d in edges:
                la, lb = find(label[a[1]][a[0]]), find(label[b[1]][b[0]])
                if la != lb:
                    groups.setdefault((min(la, lb), max(la, lb)), []).append((a, b, d))
            merged = False
            crossings = []
            for (la, lb), es in groups.items():
                if abs(tier(la) - tier(lb)) != 1:
                    union(la, lb)
                    merged = True
                    continue
                # composantes de la frontière (arêtes voisines)
                comps, left = [], list(es)
                while left:
                    comp = [left.pop()]
                    grew = True
                    while grew:
                        grew = False
                        for e in list(left):
                            if any(abs(e[0][0] - c[0][0]) + abs(e[0][1] - c[0][1]) <= 1 for c in comp):
                                comp.append(e)
                                left.remove(e)
                                grew = True
                    comps.append(comp)
                ok = []
                for comp in comps:
                    st = self._stair_cells(comp, label, find, tier, plain, walk)
                    if not st:
                        break
                    ok.append(st)
                else:
                    crossings += ok
                    continue
                union(la, lb)
                merged = True
            if not merged:
                break
        tiers_used = set()
        for y in range(H):
            for x in range(W):
                if label[y][x] >= 0:
                    t = tier(label[y][x])
                    tiers_used.add(t)
                    self.zb[y][x] = -TIER_H * t
        for lows, highs, (ux, uy) in crossings:
            for c in lows:
                self.tiles[c[1]][c[0]] = STAIRS
                self.stairs[c] = (ux, uy, 0.0, TIER_H / 2)
            for c in highs:
                self.tiles[c[1]][c[0]] = STAIRS
                self.stairs[c] = (ux, uy, -TIER_H / 2, 0.0)
        self.tiers = len(tiers_used)
        # murs : à la hauteur du sol le plus bas qu'ils bordent (repères, lanceurs de fléchettes...)
        for y in range(H):
            for x in range(W):
                if self.tiles[y][x] == WALL and label[y][x] < 0:
                    near = [self.zb[ny][nx] for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
                            if 0 <= nx < W and 0 <= ny < H and label[ny][nx] >= 0]
                    if near:
                        self.zb[y][x] = min(near)

    def _stair_cells(self, comp, label, find, tier, plain, walk):
        """Frontière nette dans un couloir droit de 2 de large ? Renvoie (cases basses, cases hautes, montée)."""
        if len(comp) != 2 or comp[0][2] != comp[1][2]:
            return None
        dx, dy = comp[0][2]
        cells = []
        for a, b, _d in comp:
            ta, tb = tier(label[a[1]][a[0]]), tier(label[b[1]][b[0]])
            low, high = (a, b) if ta > tb else (b, a)        # palier plus grand = plus profond
            cells.append((low, high))
        ux, uy = cells[0][1][0] - cells[0][0][0], cells[0][1][1] - cells[0][0][1]
        if any((h[0] - l[0], h[1] - l[1]) != (ux, uy) for l, h in cells):
            return None
        lows, highs = [c[0] for c in cells], [c[1] for c in cells]
        px, py = lows[1][0] - lows[0][0], lows[1][1] - lows[0][1]
        if abs(px) + abs(py) != 1 or (px, py) in ((ux, uy), (-ux, -uy)):
            return None
        if not all(plain(c) for c in lows + highs):
            return None
        # couloir : murs de part et d'autre, sol du même palier avant et après les marches
        for row in (lows, highs):
            a, b = row
            for c in ((a[0] - px, a[1] - py), (b[0] + px, b[1] + py)) if (b[0] - a[0], b[1] - a[1]) == (px, py) \
                    else ((a[0] + px, a[1] + py), (b[0] - px, b[1] - py)):
                if walk(*c):
                    return None
        for c in lows:
            back = (c[0] - ux, c[1] - uy)
            if not plain(back) or find(label[back[1]][back[0]]) != find(label[c[1]][c[0]]):
                return None
        for c in highs:
            fwd = (c[0] + ux, c[1] + uy)
            if not plain(fwd) or find(label[fwd[1]][fwd[0]]) != find(label[c[1]][c[0]]):
                return None
        return lows, highs, (ux, uy)

    def _dais(self, rng, r):
        """Estrade au milieu de la salle, garde-corps tout autour, un ou deux escaliers."""
        if r.w < 11 or r.h < 9:
            return False
        w, h = rng.randint(5, min(7, r.w - 4)), rng.randint(4, min(6, r.h - 4))
        x0 = r.x + 2 + rng.randint(0, r.w - 4 - w)
        y0 = r.y + 2 + rng.randint(0, r.h - 4 - h)
        cells = {(x, y) for y in range(y0, y0 + h) for x in range(x0, x0 + w)}
        changes = {c: LEDGE for c in cells}
        for x in range(x0 + 1, x0 + w - 1):
            for y in range(y0 + 1, y0 + h - 1):
                changes[(x, y)] = FLOOR
        stairs = {}
        sides = [("N", (0, 1)), ("S", (0, -1)), ("W", (1, 0)), ("E", (-1, 0))]
        for side, up in rng.sample(sides, rng.randint(1, 2)):
            if side in "NS":
                mx = x0 + w // 2 - 1
                y = y0 if side == "N" else y0 + h - 1
                steps = [(mx, y), (mx + 1, y)]
            else:
                my = y0 + h // 2 - 1
                x = x0 if side == "W" else x0 + w - 1
                steps = [(x, my), (x, my + 1)]
            for c in steps:
                changes[c] = STAIRS
                stairs[c] = (*up, 0.0, PLAT_H)
        if not self._try(changes, cells - set(stairs), stairs):
            return False
        self.daises.append((x0 + 1, y0 + 1, w - 2, h - 2))
        return True

    def _mezz(self, rng, r):
        """Mezzanine : une bande surélevée de 4 cases contre un mur de la salle, un escalier pour y monter."""
        side = rng.choice("NSEW")
        D = 4
        if side in "NS" and (r.h < 10 or r.w < 8) or side in "EW" and (r.w < 11 or r.h < 7):
            return False
        if side == "N":
            band = Room(r.x, r.y, r.w, D)
            out = [(x, r.y - 1) for x in range(r.x - 1, r.x + r.w + 1)] + \
                  [(x, y) for y in range(r.y, r.y + D) for x in (r.x - 1, r.x + r.w)]
            ring = [(x, r.y + D - 1) for x in range(r.x, r.x + r.w)]
            up = (0, -1)
        elif side == "S":
            band = Room(r.x, r.y + r.h - D, r.w, D)
            out = [(x, r.y + r.h) for x in range(r.x - 1, r.x + r.w + 1)] + \
                  [(x, y) for y in range(r.y + r.h - D, r.y + r.h) for x in (r.x - 1, r.x + r.w)]
            ring = [(x, r.y + r.h - D) for x in range(r.x, r.x + r.w)]
            up = (0, 1)
        elif side == "W":
            band = Room(r.x, r.y, D, r.h)
            out = [(r.x - 1, y) for y in range(r.y - 1, r.y + r.h + 1)] + \
                  [(x, y) for x in range(r.x, r.x + D) for y in (r.y - 1, r.y + r.h)]
            ring = [(r.x + D - 1, y) for y in range(r.y, r.y + r.h)]
            up = (-1, 0)
        else:
            band = Room(r.x + r.w - D, r.y, D, r.h)
            out = [(r.x + r.w, y) for y in range(r.y - 1, r.y + r.h + 1)] + \
                  [(x, y) for x in range(r.x + r.w - D, r.x + r.w) for y in (r.y - 1, r.y + r.h)]
            ring = [(r.x + r.w - D, y) for y in range(r.y, r.y + r.h)]
            up = (1, 0)
        if not self._closed(out):
            return False
        cells = {(x, y) for y in range(band.y, band.y + band.h) for x in range(band.x, band.x + band.w)}
        changes = {c: FLOOR for c in cells}
        for c in ring:
            changes[c] = LEDGE
        n = len(ring)
        stairs = {}
        for i in ([rng.randint(1, n - 3)] if n < 12 else [rng.randint(1, n // 2 - 2), rng.randint(n // 2, n - 3)]):
            for c in ring[i:i + 2]:
                changes[c] = STAIRS
                stairs[c] = (*up, 0.0, PLAT_H)
        return self._try(changes, cells - set(stairs), stairs)

    def _chasm(self, rng, r):
        """Gouffre qui coupe la salle en deux, un pont de 2 cases pour le traverser."""
        vertical = r.w >= r.h
        L, Wd = (r.w, r.h) if vertical else (r.h, r.w)
        if L < 10 or Wd < 7:
            return False
        k = rng.randint(2, 3)
        a = rng.randint(3, L - 3 - k)
        b = rng.randint(1, Wd - 3)                  # pont
        changes = {}
        for i in range(a, a + k):
            for j in range(Wd):
                if b <= j < b + 2:
                    continue
                changes[(r.x + i, r.y + j) if vertical else (r.x + j, r.y + i)] = PIT
        if vertical:
            edge = [(r.x + i, r.y - 1) for i in range(a, a + k)] + [(r.x + i, r.y + r.h) for i in range(a, a + k)]
        else:
            edge = [(r.x - 1, r.y + i) for i in range(a, a + k)] + [(r.x + r.w, r.y + i) for i in range(a, a + k)]
        return self._closed(edge) and self._try(changes)

    def _holes(self, rng, r):
        """Quelques trous de 2x2 au milieu de la salle."""
        if r.w < 9 or r.h < 8:
            return False
        changes = {}
        for _ in range(rng.randint(2, 3)):
            x, y = rng.randint(r.x + 2, r.x + r.w - 4), rng.randint(r.y + 2, r.y + r.h - 4)
            if any(abs(x - cx) < 4 and abs(y - cy) < 4 for cx, cy in changes):
                continue
            for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                changes[c] = PIT
        return bool(changes) and self._try(changes)

    def _traps(self, rng, rooms, start, boss):
        """Plaques à pointes dans les salles et les couloirs (jamais dans la salle de départ ni l'arène)."""
        n = len(self.traps) + 6 + len(rooms) // 2
        tries = 0
        while len(self.traps) < n and tries < n * 40:
            tries += 1
            x, y = rng.randrange(2, self.w - 2), rng.randrange(2, self.h - 2)
            if self.tiles[y][x] != FLOOR or start.contains(x, y, -2) or boss.contains(x, y, -3):
                continue
            if any(r.contains(x, y, -1) for r in self.trap_rooms):
                continue
            if any(abs(x - tx) + abs(y - ty) < 3 for tx, ty in self.traps):
                continue
            self.traps.append((x, y))
            if rng.random() < 0.4:
                self.trap_kinds[(x, y)] = "flames"
        self._darts(rng, start, boss)
        self._saws(rng, rooms, start, boss)

    def _darts(self, rng, start, boss):
        """Lanceurs de fléchettes dans les murs, face à une ligne droite d'au moins 5 cases de sol."""
        want = 4 + len(self.rooms) // 4
        for _ in range(want * 60):
            if len(self.darts) >= want:
                break
            x, y = rng.randrange(2, self.w - 2), rng.randrange(2, self.h - 2)
            if self.tiles[y][x] != WALL:
                continue
            dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
            line = [(x + dx * i, y + dy * i) for i in range(1, 6)]
            if not all(0 <= a < self.w and 0 <= b < self.h and self.tiles[b][a] == FLOOR
                       and (a, b) not in self.raised for a, b in line):
                continue
            if any(start.contains(a, b, -2) or boss.contains(a, b, -3) for a, b in line):
                continue
            if any(abs(x - ox) + abs(y - oy) < 6 for ox, oy, _dx, _dy in self.darts):
                continue
            self.darts.append((x, y, dx, dy))

    def _saws(self, rng, rooms, start, boss):
        """Lames qui vont et viennent sur un rail droit de 4 à 7 cases, en travers d'une salle."""
        want = 2 + len(rooms) // 6
        pool = [r for r in rooms if r is not start and r not in self.trap_rooms]
        for room in rng.sample(pool, len(pool)):
            if len(self.saws) >= want:
                break
            for _ in range(12):
                horiz = rng.random() < 0.5
                n = rng.randint(4, 7)
                if horiz:
                    if room.w - 2 < n:
                        continue
                    x0, y0 = rng.randint(room.x + 1, room.x + room.w - 1 - n), rng.randint(room.y + 1, room.y + room.h - 2)
                    cells = [(x0 + i, y0) for i in range(n)]
                else:
                    if room.h - 2 < n:
                        continue
                    x0, y0 = rng.randint(room.x + 1, room.x + room.w - 2), rng.randint(room.y + 1, room.y + room.h - 1 - n)
                    cells = [(x0, y0 + i) for i in range(n)]
                if all(self.tiles[b][a] == FLOOR and (a, b) not in self.raised and (a, b) not in self.traps
                       for a, b in cells):
                    self.saws.append((cells[0], cells[-1]))
                    break

    def _decorate(self, rng):
        last = {}
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                t = self.tiles[y][x]
                if t == WALL and self.tiles[y + 1][x] == FLOOR and rng.random() < 0.13:
                    if all(abs(x - tx) > 3 or ty != y for tx, ty in last.get(y, [])):
                        self.torches.append((x, y))
                        last.setdefault(y, []).append((x, y))
                elif t == FLOOR and (x, y) not in self.raised and rng.random() < 0.035:
                    self.decor.append((rng.choice(["os", "os", "crane", "bougie", "chaine", "caisse", "rocher"]), x, y))

    def solid_static(self, tx, ty):
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return True
        return self.tiles[ty][tx] == WALL


def build_hub():
    """Cendreval (game/town.py) : grille praticable, rues pavées, remparts, maisons, décor des jardins."""
    from . import town as T
    d = Dungeon(T.W, T.H)
    walk = T.walkable_cells()
    for y in range(T.H):
        for x in range(T.W):
            d.tiles[y][x] = FLOOR if (x, y) in walk else WALL
    d.tower_tiles = set(T.TOWER_CELLS)
    d.house_cells = T.house_cells() | (T.arena_ring_cells() - walk)     # sol dégagé sous les gradins de l'arène
    d.rampart = T.rampart_cells()
    d.plaza = T.street_cells() & walk          # pavés
    d.paths = (T.training_cells() | T.arena_cells()) & walk     # terre battue : cour d'entraînement, arène
    rng = random.Random(3)
    near_obs = {(int(x), int(y)) for x, y, _r in T.obstacles()}
    for y in range(T.H):
        for x in range(T.W):
            if (x, y) in walk and (x, y) not in d.plaza and (x, y) not in near_obs and rng.random() < 0.28:
                d.decor.append((rng.choice(["herbe", "herbe", "herbe", "fleur", "fleur", "fleur", "buisson",
                                            "rocher", "champignon"]), x, y))
    return d


class Minimap:
    S = 3

    def __init__(self, d, reveal_all=False):
        self.d = d
        self.surf = pygame.Surface((d.w * self.S, d.h * self.S), pygame.SRCALPHA)
        self.seen = set()
        if reveal_all:
            for y in range(d.h):
                for x in range(d.w):
                    self._paint(x, y)

    def _paint(self, x, y):
        self.seen.add((x, y))
        t = self.d.tiles[y][x]
        col = {FLOOR: (150, 176, 186, 150), WALL: None, BARRIER: (230, 70, 60, 230), PIT: (16, 18, 26, 230),
               LEDGE: (200, 186, 150, 210), STAIRS: (226, 210, 160, 220)}[t]
        if t == FLOOR and (x, y) in getattr(self.d, "raised", ()):
            col = (186, 206, 214, 175)
        zb = getattr(self.d, "zb", None)
        if col and zb and zb[y][x] < 0 and t != PIT:      # paliers inférieurs : plus sombres sur la carte
            k = max(0.45, 1 + zb[y][x] / 110)
            col = (int(col[0] * k), int(col[1] * k), int(col[2] * k), col[3])
        if col is None:
            if any(0 <= x + dx < self.d.w and 0 <= y + dy < self.d.h and self.d.tiles[y + dy][x + dx] != WALL
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                col = (225, 232, 230, 220)
            else:
                return
        self.surf.fill(col, (x * self.S, y * self.S, self.S, self.S))

    def reveal(self, tx, ty, rad=8):
        for y in range(ty - rad, ty + rad + 1):
            for x in range(tx - rad, tx + rad + 1):
                if 0 <= x < self.d.w and 0 <= y < self.d.h and (x, y) not in self.seen:
                    if (x - tx) ** 2 + (y - ty) ** 2 <= rad * rad:
                        self._paint(x, y)

    def refresh(self, tiles_list):
        for x, y in tiles_list:
            if (x, y) in self.seen:
                self._paint(x, y)
