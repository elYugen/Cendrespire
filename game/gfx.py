"""Primitives graphiques bas niveau, en pixels : dégradés lumineux et formes translucides."""
import pygame

_radial_cache = {}


def radial(radius, color, falloff=1.5):
    """Dégradé radial noir -> couleur, à blitter en mode additif."""
    radius = max(2, int(radius))
    key = (radius, color, falloff)
    s = _radial_cache.get(key)
    if s is None:
        if len(_radial_cache) > 900:
            _radial_cache.clear()
        s = pygame.Surface((radius * 2, radius * 2))
        s.fill((0, 0, 0))
        steps = max(4, min(radius, 110))
        for i in range(steps, 0, -1):
            t = i / steps
            k = max(0.0, (1 - t) ** falloff)
            pygame.draw.circle(s, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (radius, radius),
                               max(1, int(radius * t)))
        _radial_cache[key] = s
    return s


_ellipse_cache = {}


def radial_ellipse(a, b, color, falloff=1.25):
    """Halo elliptique (lumière posée au sol en vue isométrique)."""
    a, b = max(4, int(a) // 6 * 6), max(3, int(b) // 6 * 6)
    key = (a, b, color, falloff)
    s = _ellipse_cache.get(key)
    if s is None:
        if len(_ellipse_cache) > 400:
            _ellipse_cache.clear()
        s = pygame.transform.smoothscale(radial(a, color, falloff), (a * 2, b * 2))
        _ellipse_cache[key] = s
    return s


def glow(surf, x, y, r, color):
    q = (color[0] // 10 * 10, color[1] // 10 * 10, color[2] // 10 * 10)
    tex = radial(int(r), q, 1.3)
    surf.blit(tex, (x - tex.get_width() // 2, y - tex.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)


def _temp(w, h):
    return pygame.Surface((max(1, int(w)), max(1, int(h))), pygame.SRCALPHA)


def alpha_ellipse(surf, color, alpha, center, a, b, width=0):
    if a < 1 or b < 1:
        return
    s = _temp(a * 2 + 4, b * 2 + 4)
    pygame.draw.ellipse(s, (*color[:3], int(alpha)), (2, 2, a * 2, b * 2), int(width))
    surf.blit(s, (center[0] - a - 2, center[1] - b - 2))


def alpha_annulus(surf, color, alpha, center, a, b, a_in, b_in):
    if a < 1 or b < 1:
        return
    s = _temp(a * 2 + 4, b * 2 + 4)
    pygame.draw.ellipse(s, (*color[:3], int(alpha)), (2, 2, a * 2, b * 2))
    if a_in > 1 and b_in > 1:
        pygame.draw.ellipse(s, (0, 0, 0, 0), (2 + a - a_in, 2 + b - b_in, a_in * 2, b_in * 2))
    surf.blit(s, (center[0] - a - 2, center[1] - b - 2))


def alpha_polygon(surf, color, alpha, pts, width=0):
    if len(pts) < 3:
        return
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs) - 2, min(ys) - 2
    w, h = max(xs) - x0 + 4, max(ys) - y0 + 4
    if w > 6000 or h > 6000:
        return
    s = _temp(w, h)
    pygame.draw.polygon(s, (*color[:3], int(alpha)), [(p[0] - x0, p[1] - y0) for p in pts], int(width))
    surf.blit(s, (x0, y0))


def mix(c, d, k):
    return (int(c[0] + (d[0] - c[0]) * k), int(c[1] + (d[1] - c[1]) * k), int(c[2] + (d[2] - c[2]) * k))


def darker(c, k=0.6):
    return (int(c[0] * k), int(c[1] * k), int(c[2] * k))


def lighter(c, k=1.35):
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))
