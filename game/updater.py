"""Mise à jour automatique depuis les releases GitHub (https://github.com/elYugen/Cendrespire/releases).

- check() interroge l'API GitHub (release la plus récente) dans un fil d'exécution séparé : l'écran titre n'attend pas.
- Si la version publiée (tag « v2.5 » ou « 2.5 ») est plus récente que celle du jeu, l'écran titre le propose.
- apply() télécharge le code source de la release (zipball), vérifie l'archive, puis remplace le code du jeu.
  Les sauvegardes et le contenu personnalisé ne sont jamais touchés : ils sont dans saves/ (version de
  développement) ou dans %APPDATA%\\Cendrespire (version installée), et ces dossiers sont exclus de la copie.
  En cas d'erreur pendant la copie, l'ancienne version est restaurée.
- Chaque vérification et chaque installation sont racontées dans updater.log (à côté de crash.log : dossier du jeu
  en développement, %APPDATA%\\Cendrespire pour la version installée), avec la trace complète d'une erreur.
"""
import filecmp
import io
import json
import os
import re
import shutil
import ssl
import sys
import tempfile
import threading
import time
import traceback
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
LOG_FILE = os.path.join(os.path.dirname(SAVE_DIR), "updater.log")
_log_lock = threading.Lock()


def log(msg):
    """Ajoute une ligne horodatée à updater.log (jamais bloquant : une erreur d'écriture est ignorée)."""
    try:
        with _log_lock:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg.rstrip() + "\n")
    except OSError:
        pass


def log_error(step):
    log(f"ERREUR pendant « {step} » :\n" + traceback.format_exc())


def parse(v):
    """« 2.5 », « v2.5 », « alpha2.5 » -> (2, 5)."""
    m = re.search(r"\d+(?:\.\d+)*", str(v))
    return tuple(int(p) for p in m.group(0).split(".")) if m else (0,)


def release_version(rel):
    """Version d'une release : celle du tag (« alpha2.4 ») ou du nom (« alpha 2.2 »), la plus précise des deux."""
    cands = [m.group(0) for m in (re.search(r"\d+(?:\.\d+)*", str(rel.get(k) or "")) for k in ("tag_name", "name")) if m]
    return max(cands, key=lambda v: (len(v.split(".")), parse(v))) if cands else ""


_current = None


def current_version():
    """Version installée : la plus récente entre les notes de mise à jour et version.txt (écrit par apply).
    Lue une seule fois : l'écran titre l'affiche à chaque image, et relire data/updates/ 60 fois par seconde
    verrouillait ces fichiers sous Windows pendant que la mise à jour remplaçait data/ (WinError 32)."""
    global _current
    if _current is None:
        _current = _read_version()
    return _current


def _read_version():
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
        log(f"--- vérification : version actuelle {current_version()}, dossier du jeu {ROOT_DIR}, "
            f"Python {sys.version.split()[0]}, {sys.platform}")
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
        log(f"release publiée : {version or '?'} (tag {rel.get('tag_name')}) -> {state['status']}")
    except Exception as e:          # pas de réseau, dépôt sans release, limite de l'API... : on joue simplement
        state["status"], state["error"] = "offline", str(e)
        log_error("vérification")


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


def _merge_tree(src, dst):
    """Copie src dans dst sans toucher aux fichiers identiques. Sous Windows, un fichier ouvert par le jeu
    (musique en cours, police) ne peut pas être remplacé : il est gardé tel quel au lieu de faire échouer la mise
    à jour (les ressources restent utilisables). Renvoie (nombre de fichiers copiés, fichiers conservés)."""
    copied, kept = 0, []
    skip = {"__pycache__", ".DS_Store"} | NEVER
    for base, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip]
        out = os.path.join(dst, os.path.relpath(base, src))
        os.makedirs(out, exist_ok=True)
        for fn in files:
            if fn in skip or fn.endswith(".pyc"):
                continue
            s, d = os.path.join(base, fn), os.path.join(out, fn)
            if os.path.isfile(d) and os.path.getsize(d) == os.path.getsize(s) and filecmp.cmp(s, d, shallow=False):
                continue
            for attempt in range(3):
                try:
                    shutil.copy2(s, d)
                    copied += 1
                    break
                except PermissionError:
                    if attempt == 2:
                        kept.append(os.path.relpath(d, dst))
                    else:
                        time.sleep(0.3)
    return copied, kept


def _rmtree(path):
    """shutil.rmtree qui réessaie quelques instants : sous Windows, un fichier ouvert ailleurs (antivirus,
    indexation, lecture en cours) ne peut pas être supprimé, mais le verrou ne dure en général qu'un instant."""
    for attempt in range(8):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == 7:
                raise
            time.sleep(0.4)


def _apply():
    backup = None
    step = "préparation"
    try:
        log(f"--- installation de la version {state['latest']} depuis {state['zip']}")
        log(f"dossier du jeu : {ROOT_DIR} ; sauvegardes : {SAVE_DIR}")
        step = "téléchargement"
        state["status"] = "downloading"
        data = _download(state["zip"])
        log(f"archive téléchargée : {data.getbuffer().nbytes} octets")
        step = "extraction de l'archive"
        state["status"] = "installing"
        tmp = tempfile.mkdtemp(prefix="cendrespire_maj_")
        with zipfile.ZipFile(data) as z:
            for member in z.namelist():
                if not _safe_under(tmp, os.path.join(tmp, member)):
                    raise ValueError(f"archive invalide (chemin hors du dossier : {member})")
            z.extractall(tmp)
        tops = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        src = os.path.join(tmp, tops[0]) if len(tops) == 1 else tmp
        log(f"archive extraite dans {src} : {sorted(os.listdir(src))}")
        if not (os.path.isfile(os.path.join(src, "main.py")) and os.path.isdir(os.path.join(src, "game"))):
            raise ValueError("la release ne contient pas le code du jeu (main.py, game/)")
        saves_real = os.path.realpath(SAVE_DIR)
        # sauvegarde de l'ancienne version (pour revenir en arrière en cas d'erreur)
        step = "copie de secours de l'ancienne version"
        backup = os.path.join(ROOT_DIR, "backup", "avant-" + current_version())
        if os.path.exists(backup):
            _rmtree(backup)
        os.makedirs(backup)
        for name in REPLACE_DIRS + ROOT_FILES:
            p = os.path.join(ROOT_DIR, name)
            if os.path.exists(p):
                (shutil.copytree if os.path.isdir(p) else shutil.copy2)(p, os.path.join(backup, name))
        log(f"copie de secours : {backup}")
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", *NEVER)
        for name in REPLACE_DIRS:
            step = f"remplacement de {name}/"
            s, d = os.path.join(src, name), os.path.join(ROOT_DIR, name)
            if not os.path.isdir(s):
                log(f"{name}/ absent de la release : conservé")
                continue
            if saves_real.startswith(os.path.realpath(d) + os.sep):
                raise ValueError(f"les sauvegardes sont dans {name}/ : copie refusée")
            if os.path.isdir(d):
                _rmtree(d)
            shutil.copytree(s, d, ignore=ignore)
            log(f"{name}/ remplacé")
        for name in MERGE_DIRS:
            step = f"fusion de {name}/"
            s = os.path.join(src, name)
            if os.path.isdir(s):
                copied, kept = _merge_tree(s, os.path.join(ROOT_DIR, name))
                log(f"{name}/ fusionné : {copied} fichier(s) copié(s)"
                    + (f", {len(kept)} fichier(s) en cours d'utilisation conservé(s) : {kept}" if kept else ""))
        step = "fichiers principaux"
        for name in ROOT_FILES:
            s = os.path.join(src, name)
            if os.path.isfile(s):
                shutil.copy2(s, os.path.join(ROOT_DIR, name))
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(state["latest"] or "")
        shutil.rmtree(tmp, ignore_errors=True)
        state["progress"] = 1.0
        state["status"] = "done"
        log(f"version {state['latest']} installée")
    except Exception as e:
        state["status"], state["error"] = "failed", f"{step} : {e.__class__.__name__} : {e}"
        log_error(step)
        if backup and os.path.isdir(backup):          # retour à l'ancienne version
            for name in os.listdir(backup):
                s, d = os.path.join(backup, name), os.path.join(ROOT_DIR, name)
                try:
                    if os.path.isdir(s):
                        if os.path.isdir(d):
                            _rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                except OSError:
                    log_error(f"restauration de {name}")
            log("ancienne version restaurée")


def apply():
    if state["status"] != "available":
        return
    from . import sfx
    sfx.stop_music()          # sous Windows, le fichier de la musique en cours est verrouillé : on le libère
    state["status"] = "downloading"
    threading.Thread(target=_apply, daemon=True).start()


def restart():
    """Relance le jeu avec le nouveau code (même interpréteur, mêmes arguments)."""
    import pygame
    pygame.quit()
    os.execv(sys.executable, [sys.executable, os.path.join(ROOT_DIR, "main.py")] + sys.argv[1:])
