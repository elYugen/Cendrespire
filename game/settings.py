"""Constantes globales du jeu."""
import os
import sys

# Résolution « de conception » : toute l'interface est positionnée dans cet espace,
# puis dessinée à la résolution réelle de l'écran (Retina compris) pour rester nette.
SCREEN_W, SCREEN_H = 1280, 720
WINDOW_SIZE = (1920, 1080)       # taille de la fenêtre au lancement (1080p), réduite si l'écran est plus petit
FPS = 60
TILE = 40
TITLE = "Cendrespire"
# Discord Rich Presence (game/discord.py) : identifiant de l'application Discord (« Application ID » sur
# https://discord.com/developers/applications). Vide : désactivé.
DISCORD_APP_ID = "1553856171956375626"

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _save_dir():
    """Depuis les sources : saves/ à côté du code. Version installée (fichier installed.txt posé par l'installeur, ou
    exécutable figé) : dossier de données de l'utilisateur, pour que les sauvegardes survivent aux mises à jour."""
    installed = getattr(sys, "frozen", False) or os.path.exists(os.path.join(ROOT_DIR, "installed.txt"))
    if not installed:
        return os.path.join(ROOT_DIR, "saves")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, TITLE, "saves")


SAVE_DIR = _save_dir()
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")   # illustrations du menu principal


class View:
    """Facteur d'échelle courant entre l'espace de conception et les pixels réels."""
    s = 1.0          # pixels par unité de conception
    w, h = SCREEN_W, SCREEN_H   # taille du canevas en pixels
    ox = oy = 0      # décalage du canevas dans la fenêtre (bandes noires)
    ratio = 1.0      # pixels par point de fenêtre (2 sur écran Retina)
    version = 0      # incrémenté à chaque changement d'échelle (invalide les caches)


VIEW = View()

# Police embarquée (Lato, licence OFL, assets/fonts) : rendu identique sur toutes les machines,
# sans dépendre des polices du système.
_FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
FONT_FILES = {
    "text": (os.path.join(_FONTS_DIR, "Lato-Regular.ttf"), 0),
    "bold": (os.path.join(_FONTS_DIR, "Lato-Bold.ttf"), 0),
    "title": (os.path.join(_FONTS_DIR, "Lato-Regular.ttf"), 0),
    "title_bold": (os.path.join(_FONTS_DIR, "Lato-Bold.ttf"), 0),
}

# Palette
BLACK = (0, 0, 0)
WHITE = (245, 243, 235)
TEXT = (222, 222, 214)
TEXT_DIM = (150, 156, 156)
GOLD = (230, 196, 110)
GOLD_BRIGHT = (255, 222, 120)
GOLD_DARK = (110, 84, 40)
RED = (230, 80, 70)
BLUE = (90, 150, 255)
GREEN = (110, 235, 120)
SHEIKAH = (90, 210, 255)
UI_LINE = (228, 226, 216)

RARITIES = ["commun", "magique", "rare", "legendaire"]
RARITY_COLORS = {
    "commun": (215, 215, 215),
    "magique": (105, 150, 255),
    "rare": (245, 220, 80),
    "legendaire": (255, 138, 28),
}
RARITY_NAMES = {"commun": "Commun", "magique": "Magique", "rare": "Rare", "legendaire": "Légendaire"}

# Scancodes physiques : fonctionnent en AZERTY comme en QWERTY
SC_UP = (26, 82)        # Z (AZERTY) / W (QWERTY), flèche haut
SC_LEFT = (4, 80)       # Q / A, flèche gauche
SC_DOWN = (22, 81)      # S, flèche bas
SC_RIGHT = (7, 79)      # D, flèche droite
SC_SPELLS = ((30, 89), (31, 90), (32, 91), (33, 92))  # 1 2 3 4 (rangée du haut ou pavé numérique)
SC_POTION = 9           # F
SC_INTERACT = 8         # E
