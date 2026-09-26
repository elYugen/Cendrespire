"""Génération procédurale des étages de la tour, carte du campement et rendu des tuiles."""
import heapq
import math
import random

import pygame

from .settings import TILE

WALL, FLOOR, BARRIER = 0, 1, 2


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

    def generate(self, rng, n_rooms=10):
        W, H = self.w, self.h
        bw, bh = 15, 13
        boss = Room(rng.randint(3, W - bw - 3), rng.randint(3, H - bh - 3), bw, bh)
        rooms = []
        tries = 0
        while len(rooms) < n_rooms and tries < 3000:
            tries += 1
            w, h = rng.randint(7, 12), rng.randint(6, 10)
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
        for _ in range(2):
            a, b = rng.sample(rooms, 2)
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
        self._decorate(rng)

    def _decorate(self, rng):
        last = {}
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                t = self.tiles[y][x]
                if t == WALL and self.tiles[y + 1][x] == FLOOR and rng.random() < 0.13:
                    if all(abs(x - tx) > 3 or ty != y for tx, ty in last.get(y, [])):
                        self.torches.append((x, y))
                        last.setdefault(y, []).append((x, y))
                elif t == FLOOR and rng.random() < 0.035:
                    self.decor.append((rng.choice(["os", "os", "crane", "bougie", "chaine", "caisse", "rocher"]), x, y))

    def solid_static(self, tx, ty):
        if not (0 <= tx < self.w and 0 <= ty < self.h):
            return True
        return self.tiles[ty][tx] == WALL


HUB_MAP = [
    "##################################",
    "##################################",
    "##############TTTTTT##############",
    "#######......#TTTTTT#.......######",
    "######........TTTTTT.........#####",
    "#####..............................#",
    "####...............................#",
    "###.....##...................##....#",
    "###.....##...................##....#",
    "###................................#",
    "###................................#",
    "###................................#",
    "###.....##...................##....#",
    "###.....##...................##....#",
    "####...............................#",
    "#####.............................##",
    "######...........................###",
    "########.......................#####",
    "##################################",
    "##################################",
]


HUB_FIRE = (17.5, 10.5)
HUB_PLAZA_R = 2.7


def _hub_paths(d, rng):
    """Chemins de terre du campement : du feu vers le portail, le marchand, la forge, la couturière et l'entrée."""
    paths = set()

    def line(x0, y0, x1, y1, width=2):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            x = x0 + (x1 - x0) * i / n
            y = y0 + (y1 - y0) * i / n
            for ox in range(width):
                for oy in range(width):
                    paths.add((int(x - width / 2 + 0.5) + ox, int(y - width / 2 + 0.5) + oy))

    fx, fy = HUB_FIRE
    line(fx - 0.5, fy, fx - 0.5, 5.0)       # portail
    line(fx, fy, 7.5, fy)                    # marchand
    line(fx, fy, 28.0, fy)                   # forge
    line(fx, fy, fx, 16.5)                   # entrée
    line(fx, 14.5, 12.0, 14.5)               # couturière
    line(12.0, 14.5, 11.0, 15.0)
    # bords irréguliers
    for (x, y) in list(paths):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if rng.random() < 0.08:
                paths.add((x + dx, y + dy))
    return {(x, y) for x, y in paths if 0 <= x < d.w and 0 <= y < d.h and d.tiles[y][x] == FLOOR}


def build_hub():
    w = max(len(r) for r in HUB_MAP)
    h = len(HUB_MAP)
    d = Dungeon(w, h)
    for y, row in enumerate(HUB_MAP):
        for x in range(w):
            c = row[x] if x < len(row) else "#"
            d.tiles[y][x] = FLOOR if c == "." else WALL
    d.tower_tiles = {(x, y) for y, row in enumerate(HUB_MAP) for x, c in enumerate(row) if c == "T"}
    rng = random.Random(3)
    fx, fy = HUB_FIRE
    d.plaza = {(x, y) for y in range(h) for x in range(w) if d.tiles[y][x] == FLOOR
               and math.hypot(x + 0.5 - fx, y + 0.5 - fy) < HUB_PLAZA_R}
    d.paths = _hub_paths(d, rng) - d.plaza
    busy = d.plaza | d.paths
    for y in range(h):
        for x in range(w):
            if d.tiles[y][x] == FLOOR and (x, y) not in busy and rng.random() < 0.3:
                d.decor.append((rng.choice(["herbe", "herbe", "herbe", "fleur", "fleur", "buisson", "rocher",
                                            "champignon", "souche"]), x, y))
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
        col = {FLOOR: (150, 176, 186, 150), WALL: None, BARRIER: (230, 70, 60, 230)}[t]
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
