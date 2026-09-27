"""Mise à jour automatique depuis les releases GitHub (https://github.com/elYugen/Cendrespire/releases).

- check() interroge l'API GitHub (release la plus récente) dans un fil d'exécution séparé : l'écran titre n'attend pas.
- Si la version publiée (tag « v2.5 » ou « 2.5 ») est plus récente que celle du jeu, l'écran titre le propose.
- apply() télécharge le code source de la release (zipball), vérifie l'archive, puis remplace le code du jeu.
  Les sauvegardes et le contenu personnalisé ne sont jamais touchés : ils sont dans saves/ (version de
  développement) ou dans %APPDATA%\\Cendrespire (version installée), et ces dossiers sont exclus de la copie.
  En cas d'erreur pendant la copie, l'ancienne version est restaurée.
"""
import io
import json
import os
import re
import shutil
import ssl
import sys
import tempfile
import threading
import urllib.request
import zipfile

from . import updates
from .settings import ROOT_DIR, SAVE_DIR

REPO = "elYugen/Cendrespire"
API = f"https://api.github.com/repos/{REPO}/releases/latest"
VERSION_FILE = os.path.join(ROOT_DIR, "version.txt")
# ce que la mise à jour remplace entièrement / fusionne / ne touche jamais
REPLACE_DIRS = ("game", "data")
MERGE_DIRS = ("assets",)
ROOT_FILES = ("main.py", "README.md", "requirements.txt")
NEVER = {"saves", ".git", ".venv", "runtime", "build", "dist", "installer", "backup"}

state = {"status": "idle", "latest": None, "notes": "", "zip": None, "error": None, "progress": 0.0}


def parse(v):
    """« 2.5 », « v2.5 », « alpha2.5 » -> (2, 5)."""
    m = re.search(r"\d+(?:\.\d+)*", str(v))
    return tuple(int(p) for p in m.group(0).split(".")) if m else (0,)


def release_version(rel):
    """Version d'une release : celle du tag (« alpha2.4 ») ou du nom (« alpha 2.2 »), la plus précise des deux."""
    cands = [m.group(0) for m in (re.search(r"\d+(?:\.\d+)*", str(rel.get(k) or "")) for k in ("tag_name", "name")) if m]
    return max(cands, key=lambda v: (len(v.split(".")), parse(v))) if cands else ""


def current_version():
    """Version installée : la plus récente entre les notes de mise à jour et version.txt (écrit par apply)."""
    best = updates.current_version()
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            v = f.read().strip()
        if v and parse(v) > parse(best):
            best = v
    except OSError:
        pass
    return best


def _context():
    for mod in ("certifi", "pip._vendor.certifi"):
        try:
            return ssl.create_default_context(cafile=__import__(mod, fromlist=["where"]).where())
        except (ImportError, OSError):
            continue
    return ssl.create_default_context()


def _get(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": "Cendrespire-updater",
                                               "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout, context=_context())


def is_dev_checkout():
    return os.path.isdir(os.path.join(ROOT_DIR, ".git"))


def _check():
    try:
        with _get(API) as r:
            rel = json.load(r)
        version = release_version(rel)
        state["latest"] = version
        state["notes"] = (rel.get("body") or "").strip()
        state["zip"] = rel.get("zipball_url")
        if version and parse(version) > parse(current_version()) and state["zip"]:
            state["status"] = "available"
        else:
            state["status"] = "uptodate"
    except Exception as e:          # pas de réseau, dépôt sans release, limite de l'API... : on joue simplement
        state["status"], state["error"] = "offline", str(e)


def check():
    """Lance la vérification en arrière-plan (une fois par lancement)."""
    if state["status"] != "idle":
        return
    state["status"] = "checking"
    threading.Thread(target=_check, daemon=True).start()


# --------------------------------------------------------------------------- installation
def _download(url):
    buf = io.BytesIO()
    with _get(url, timeout=30) as r:
        total = int(r.headers.get("Content-Length") or 0)
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            buf.write(chunk)
            if total:
                state["progress"] = min(0.95, buf.tell() / total)
    return buf


def _safe_under(base, path):
    base = os.path.realpath(base)
    return os.path.realpath(path).startswith(base + os.sep) or os.path.realpath(path) == base


def _apply():
    backup = None
    try:
        state["status"] = "downloading"
        data = _download(state["zip"])
        state["status"] = "installing"
        tmp = tempfile.mkdtemp(prefix="cendrespire_maj_")
        with zipfile.ZipFile(data) as z:
            for member in z.namelist():
                if not _safe_under(tmp, os.path.join(tmp, member)):
                    raise ValueError("archive invalide (chemin hors du dossier)")
            z.extractall(tmp)
        tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        src = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
        if not (os.path.isfile(os.path.join(src, "main.py")) and os.path.isdir(os.path.join(src, "game"))):
            raise ValueError("la release ne contient pas le code du jeu (main.py, game/)")
        saves_real = os.path.realpath(SAVE_DIR)
        # sauvegarde de l'ancienne version (pour revenir en arrière en cas d'erreur)
        backup = os.path.join(ROOT_DIR, "backup", "avant-" + current_version())
        if os.path.exists(backup):
            shutil.rmtree(backup)
        os.makedirs(backup)
        for name in REPLACE_DIRS + ROOT_FILES:
            p = os.path.join(ROOT_DIR, name)
            if os.path.exists(p):
                (shutil.copytree if os.path.isdir(p) else shutil.copy2)(p, os.path.join(backup, name))
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", *NEVER)
        for name in REPLACE_DIRS:
            s, d = os.path.join(src, name), os.path.join(ROOT_DIR, name)
            if not os.path.isdir(s):
                continue
            if saves_real.startswith(os.path.realpath(d) + os.sep):
                raise ValueError(f"les sauvegardes sont dans {name}/ : copie refusée")
            if os.path.isdir(d):
                shutil.rmtree(d)
            shutil.copytree(s, d, ignore=ignore)
        for name in MERGE_DIRS:
            s = os.path.join(src, name)
            if os.path.isdir(s):
                shutil.copytree(s, os.path.join(ROOT_DIR, name), dirs_exist_ok=True, ignore=ignore)
        for name in ROOT_FILES:
            s = os.path.join(src, name)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(ROOT_DIR, name))
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(state["latest"] or "")
        shutil.rmtree(tmp, ignore_errors=True)
        state["progress"] = 1.0
        state["status"] = "done"
    except Exception as e:
        state["status"], state["error"] = "failed", str(e)
        if backup and os.path.isdir(backup):          # retour à l'ancienne version
            for name in os.listdir(backup):
                s, d = os.path.join(backup, name), os.path.join(ROOT_DIR, name)
                try:
                    if os.path.isdir(s):
                        if os.path.isdir(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                except OSError:
                    pass


def apply():
    if state["status"] != "available":
        return
    state["status"] = "downloading"
    threading.Thread(target=_apply, daemon=True).start()


def restart():
    """Relance le jeu avec le nouveau code (même interpréteur, mêmes arguments)."""
    import pygame
    pygame.quit()
    os.execv(sys.executable, [sys.executable, os.path.join(ROOT_DIR, "main.py")] + sys.argv[1:])
