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

# Police embarquée (M PLUS Rounded 1c, licence OFL, assets/fonts) : rendu identique sur toutes les machines,
# sans dépendre des polices du système.
_FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
# M PLUS Rounded 1c pour tous les textes : gothique japonaise aux terminaisons arrondies, proche de FOT-Rodin, la
# police de l'interface de Breath of the Wild. Licence OFL (assets/fonts/OFL-MPLUSRounded1c.txt).
# (fichier, index dans le fichier, facteur de taille : police plus large que celle des mises en page d'origine)
FONT_FILES = {                      # graisses légères : Regular pour le texte, Medium pour la mise en valeur
    "text": (os.path.join(_FONTS_DIR, "MPLUSRounded1c-Regular.ttf"), 0, 0.93),
    "bold": (os.path.join(_FONTS_DIR, "MPLUSRounded1c-Medium.ttf"), 0, 0.93),
    "title": (os.path.join(_FONTS_DIR, "MPLUSRounded1c-Regular.ttf"), 0, 0.95),
    "title_bold": (os.path.join(_FONTS_DIR, "MPLUSRounded1c-Medium.ttf"), 0, 0.95),
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

# Touches du clavier et boutons de la manette : game/controls.py (modifiables dans Options)
