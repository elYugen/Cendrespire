"""Affichage : mode (fenêtre ou plein écran) et résolution, enregistrés dans options.json.

prefs["fullscreen"] vaut None tant que le joueur n'a rien choisi : le jeu garde alors son réglage automatique
(fenêtre 1080p, plein écran sur un écran 1080p...). prefs["size"] : taille de la fenêtre, ou résolution du plein
écran (None : celle du bureau).
"""
import pygame

RESOLUTIONS = [(1280, 720), (1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160)]
prefs = {"fullscreen": None, "size": None}


def available():
    """Résolutions proposées : celles qui tiennent dans l'écran principal."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        return RESOLUTIONS[:4]
    res = [r for r in RESOLUTIONS if r[0] <= dw and r[1] <= dh]
    if (dw, dh) not in res:
        res.append((dw, dh))
    return sorted(res)


def current(game):
    """(plein écran, taille) de la fenêtre du jeu."""
    if game.window is None:
        return False, (1280, 720)
    desk = tuple(pygame.display.get_desktop_sizes()[0])
    full = prefs["fullscreen"] if prefs["fullscreen"] is not None else tuple(game.window.size) == desk
    size = tuple(prefs["size"]) if prefs["size"] else tuple(game.window.size)
    return full, size


def apply(game, fullscreen, size):
    """Change le mode et la résolution de la fenêtre, puis l'enregistre."""
    prefs["fullscreen"], prefs["size"] = bool(fullscreen), list(size) if size else None
    w = game.window
    if w is not None:
        try:
            if fullscreen:
                w.set_windowed()
                if size and tuple(size) != tuple(pygame.display.get_desktop_sizes()[0]):
                    w.size = tuple(size)
                    w.set_fullscreen(desktop=False)      # vrai plein écran à cette résolution
                else:
                    w.set_fullscreen(True)                # plein écran sans bordure, résolution du bureau
            else:
                w.set_windowed()
                if size:
                    w.size = tuple(size)
                w.position = pygame.WINDOWPOS_CENTERED
        except pygame.error as e:
            print(f"[affichage] {e}")
        if getattr(game, "renderer", None) is not None:     # au lancement, la vue est préparée ensuite
            game.refresh_view()
    from . import sfx
    sfx.save_options()


def windowed_default():
    """Taille de fenêtre quand on quitte le plein écran sans en avoir choisi : la plus grande sous l'écran."""
    res = available()
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        return res[0]
    smaller = [r for r in res if r[0] < dw and r[1] < dh - 60]
    return smaller[-1] if smaller else res[0]


def toggle(game):
    """F11 : bascule fenêtre / plein écran (sans bordure, à la résolution du bureau)."""
    full, size = current(game)
    if full:
        apply(game, False, size if fits_window(size) else windowed_default())
    else:
        apply(game, True, None)


def fits_window(size):
    """Vrai si une fenêtre de cette taille tient à l'écran avec sa barre de titre."""
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except (pygame.error, IndexError):
        return True
    return size[0] < dw and size[1] < dh - 60


def load(data):
    d = data.get("display") or {}
    if isinstance(d.get("fullscreen"), bool):
        prefs["fullscreen"] = d["fullscreen"]
    s = d.get("size")
    if isinstance(s, list) and len(s) == 2 and all(isinstance(v, int) and v >= 640 for v in s):
        prefs["size"] = s
