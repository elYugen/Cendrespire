"""Commandes modifiables : touches du clavier et boutons de la manette, enregistrés dans options.json.

Clavier : chaque action a une touche principale (modifiable, en scancode : position physique de la touche, donc
indépendante de la disposition AZERTY / QWERTY) et parfois des touches secondaires fixes (flèches, pavé numérique).
Manette : chaque action de jeu a un bouton (noms façon Xbox, voir gamepad.BTN). Les menus gardent leur pilotage
fixe à la manette (A : clic, B : retour, LB / RB : pages).
"""
import ctypes
import json
import os

import pygame

# (id, libellé, touche principale par défaut, touches secondaires fixes)
KEY_ACTIONS = [
    ("up", "Avancer", 26, (82,)), ("down", "Reculer", 22, (81,)),
    ("left", "Aller à gauche", 4, (80,)), ("right", "Aller à droite", 7, (79,)),
    ("spell1", "Sort 1", 30, (89,)), ("spell2", "Sort 2", 31, (90,)),
    ("spell3", "Sort 3", 32, (91,)), ("spell4", "Sort 4", 33, (92,)),
    ("roll", "Roulade", 44, ()), ("potion", "Potion", 9, ()), ("interact", "Interagir", 8, ()),
    ("art1", "Artefact 1", 21, ()), ("art2", "Artefact 2", 23, ()), ("art3", "Artefact 3", 10, ()),
    ("inventory", "Inventaire", 12, ()), ("character", "Personnage", 6, ()), ("talents", "Talents", 17, ()),
    ("quests", "Quêtes", 13, ()), ("map", "Grande carte", 43, ()),
]
KEY_LABELS = {a: label for a, label, _d, _s in KEY_ACTIONS}
SECONDARY = {a: s for a, _l, _d, s in KEY_ACTIONS}
DEFAULT_KEYS = {a: d for a, _l, d, _s in KEY_ACTIONS}
LOCKED_KEYS = {41}            # Échap : réservé au menu

# actions de la manette en jeu -> bouton par défaut
PAD_ACTIONS = [
    ("attack", "Attaquer (maintenu)", "rt"), ("interact", "Interagir (sinon attaquer)", "a"),
    ("spell1", "Sort 1", "x"), ("spell2", "Sort 2", "y"), ("spell3", "Sort 3", "b"), ("spell4", "Sort 4", "rb"),
    ("roll", "Roulade", "lb"), ("potion", "Potion", "lt"),
    ("art1", "Artefact 1", "left"), ("art2", "Artefact 2", "up"), ("art3", "Artefact 3", "right"),
    ("map", "Carte", "down"), ("pause", "Menu", "start"),
]
PAD_LABELS = {a: label for a, label, _d in PAD_ACTIONS}
DEFAULT_PAD = {a: d for a, _l, d in PAD_ACTIONS}
PAD_NAMES = {"a": "A", "b": "B", "x": "X", "y": "Y", "lb": "LB", "rb": "RB", "lt": "LT", "rt": "RT",
             "start": "Start", "back": "Select", "up": "Croix ↑", "down": "Croix ↓", "left": "Croix ←",
             "right": "Croix →"}

keys = dict(DEFAULT_KEYS)
pad = dict(DEFAULT_PAD)


# ------------------------------------------------------------------ lecture
def codes(action):
    """Scancodes qui déclenchent l'action (touche principale + secondaires)."""
    return (keys[action],) + SECONDARY[action]


def key_action(scancode):
    """Action du clavier liée à ce scancode (ou None)."""
    for a in keys:
        if scancode in codes(a):
            return a
    return None


def pad_action(button):
    return next((a for a, b in pad.items() if b == button), None)


# ------------------------------------------------------------------ noms des touches (selon la disposition du clavier)
_sdl = []


def _key_from_scancode(sc):
    """SDL_GetKeyFromScancode (via la bibliothèque SDL livrée avec pygame) : « z » en AZERTY, « w » en QWERTY."""
    if not _sdl:
        lib = None
        base = os.path.dirname(pygame.__file__)
        for name in ("SDL2.dll", "libSDL2-2.0.0.dylib", ".dylibs/libSDL2-2.0.0.dylib", "libSDL2-2.0.so.0"):
            try:
                lib = ctypes.CDLL(os.path.join(base, name))
                break
            except OSError:
                continue
        if lib is not None:
            lib.SDL_GetKeyFromScancode.restype = ctypes.c_int32
            lib.SDL_GetKeyFromScancode.argtypes = [ctypes.c_int]
        _sdl.append(lib)
    lib = _sdl[0]
    return lib.SDL_GetKeyFromScancode(sc) if lib is not None else None


NAMES_FR = {"space": "Espace", "tab": "Tab", "left shift": "Maj gauche", "right shift": "Maj droite",
            "left ctrl": "Ctrl gauche", "right ctrl": "Ctrl droite", "left alt": "Alt", "return": "Entrée",
            "backspace": "Retour arr.", "up": "↑", "down": "↓", "left": "←", "right": "→"}


def key_name(sc):
    k = _key_from_scancode(sc)
    name = pygame.key.name(k) if k else ""
    if not name:
        name = pygame.key.name(pygame.key.key_code(chr(ord("a") + sc - 4))) if 4 <= sc <= 29 else f"#{sc}"
    return NAMES_FR.get(name, name.upper() if len(name) == 1 else name.capitalize())


def label(action):
    return key_name(keys[action])


def pad_label(action):
    return PAD_NAMES.get(pad[action], pad[action])


# ------------------------------------------------------------------ modification
def bind_key(action, sc):
    """Lie la touche ; l'action qui l'avait déjà prend l'ancienne touche (échange). Faux si touche réservée."""
    if sc in LOCKED_KEYS or sc == 0:
        return False
    old = keys[action]
    for a, v in keys.items():
        if a != action and v == sc:
            keys[a] = old
    keys[action] = sc
    save()
    return True


def bind_pad(action, button):
    old = pad[action]
    for a, v in pad.items():
        if a != action and v == button:
            pad[a] = old
    pad[action] = button
    save()


def reset():
    keys.update(DEFAULT_KEYS)
    pad.update(DEFAULT_PAD)
    save()


# ------------------------------------------------------------------ fichier (options.json, avec les volumes)
def _path():
    from .sfx import OPTIONS_PATH
    return OPTIONS_PATH


def load():
    try:
        with open(_path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return
    for a, sc in (data.get("keys") or {}).items():
        if a in keys and isinstance(sc, int) and sc not in LOCKED_KEYS:
            keys[a] = sc
    for a, b in (data.get("pad") or {}).items():
        if a in pad and b in PAD_NAMES:
            pad[a] = b


def save():
    from .sfx import save_options
    save_options()
