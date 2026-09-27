"""Déplacement au clic (façon Diablo) : recherche de chemin A* sur la grille des cases, puis lissage.

- find_path(world, x0, y0, x1, y1, r) renvoie une liste de points (pixels logiques) jusqu'à la destination, ou []
  si elle est inaccessible (on vise alors la case praticable la plus proche).
- Les obstacles ronds du décor (étal, tentes...) bloquent aussi les cases qu'ils recouvrent.
"""
import heapq
import math

from .settings import TILE

DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
        (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]


def _walkable(world, tx, ty):
    if world.solid(tx, ty):
        return False
    cx, cy = (tx + 0.5) * TILE, (ty + 0.5) * TILE
    for ox, oy, orad in world.obstacles:
        if (cx - ox) ** 2 + (cy - oy) ** 2 < (orad + TILE * 0.35) ** 2:
            return False
    return True


def clear_line(world, x0, y0, x1, y1, r):
    """Vrai si un cercle de rayon r peut glisser en ligne droite de (x0, y0) à (x1, y1)."""
    d = math.hypot(x1 - x0, y1 - y0)
    n = int(d / 10) + 1
    for i in range(1, n + 1):
        t = i / n
        if world.blocked(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, r):
            return False
    return True


def _nearest_walkable(world, tx, ty, max_r=6):
    if _walkable(world, tx, ty):
        return tx, ty
    for rad in range(1, max_r + 1):
        best = None
        for dx in range(-rad, rad + 1):
            for dy in range(-rad, rad + 1):
                if max(abs(dx), abs(dy)) != rad:
                    continue
                if _walkable(world, tx + dx, ty + dy):
                    d = dx * dx + dy * dy
                    if best is None or d < best[0]:
                        best = (d, tx + dx, ty + dy)
        if best:
            return best[1], best[2]
    return None


def find_path(world, x0, y0, x1, y1, r, max_nodes=6000):
    if clear_line(world, x0, y0, x1, y1, r):
        return [(x1, y1)]
    start = (int(x0 // TILE), int(y0 // TILE))
    goal = _nearest_walkable(world, int(x1 // TILE), int(y1 // TILE))
    if goal is None:
        return []
    if goal != (int(x1 // TILE), int(y1 // TILE)):
        x1, y1 = (goal[0] + 0.5) * TILE, (goal[1] + 0.5) * TILE
    openq = [(0.0, 0.0, start)]
    came = {start: None}
    cost = {start: 0.0}
    n = 0
    found = False
    while openq and n < max_nodes:
        _, g, cur = heapq.heappop(openq)
        n += 1
        if cur == goal:
            found = True
            break
        cx, cy = cur
        for dx, dy, c in DIRS:
            nx, ny = cx + dx, cy + dy
            if not _walkable(world, nx, ny):
                continue
            if dx and dy and not (_walkable(world, cx + dx, cy) and _walkable(world, cx, cy + dy)):
                continue            # pas de diagonale qui rase un coin de mur
            ng = g + c
            if ng < cost.get((nx, ny), 1e9):
                cost[(nx, ny)] = ng
                came[(nx, ny)] = cur
                h = math.hypot(goal[0] - nx, goal[1] - ny)
                heapq.heappush(openq, (ng + h, ng, (nx, ny)))
    if not found:
        return []
    cells = []
    node = goal
    while node is not None and node != start:
        cells.append(node)
        node = came[node]
    cells.reverse()
    pts = [((cx + 0.5) * TILE, (cy + 0.5) * TILE) for cx, cy in cells]
    if pts:
        pts[-1] = (x1, y1)
    return smooth(world, x0, y0, pts, r)


def smooth(world, x0, y0, pts, r):
    """Supprime les points intermédiaires quand une ligne droite suffit (chemin plus naturel)."""
    out = []
    cx, cy = x0, y0
    i = 0
    while i < len(pts):
        j = len(pts) - 1
        while j > i and not clear_line(world, cx, cy, pts[j][0], pts[j][1], r):
            j -= 1
        out.append(pts[j])
        cx, cy = pts[j]
        i = j + 1
    return out
