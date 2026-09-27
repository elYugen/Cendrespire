"""Construit l'installeur Windows de Cendrespire (Cendrespire-<version>-Setup.exe) depuis macOS, Linux ou Windows.

Aucun Windows, Docker ni Wine n'est nécessaire :
  1. vérifie le contenu JSON (data/) ;
  2. télécharge le Python officiel pour Windows, version « embarquable » (python.org), mis en cache dans build/cache ;
  3. télécharge les paquets Windows (pygame-ce, moderngl, numpy...) avec pip (--platform win_amd64) ;
  4. assemble le jeu dans build/windows/Cendrespire (code, data, assets, Python, paquets, icône) ;
  5. compile l'installeur avec NSIS (makensis), qui fonctionne sur les trois systèmes.

Prérequis : Python 3.10+ (celui qui lance ce script, avec pygame-ce pour dessiner l'icône) et NSIS :
  macOS   : brew install makensis
  Linux   : sudo apt install nsis
  Windows : winget install NSIS.NSIS

Usage : python installer/build.py [--version X.Y]   (par défaut : dernière version de data/updates/)
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
CACHE = os.path.join(BUILD, "cache")
STAGE = os.path.join(BUILD, "windows", "Cendrespire")
OUTPUT = os.path.join(ROOT, "installer", "Output")

PY_VERSION = "3.12.10"          # dernière 3.12 publiée avec l'archive « embeddable » pour Windows
PY_TAG = "312"
PY_URL = f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip"

GAME_FILES = ["main.py", "README.md"]
GAME_DIRS = ["game", "data", "assets"]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.m4a", "backup", "version.txt")   # m4a : originaux des musiques (.opus)


def step(msg):
    print(f"\n==> {msg}", flush=True)


def run(cmd, **kw):
    print("   $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def find_makensis():
    exe = shutil.which("makensis")
    if exe:
        return exe
    for p in (r"C:\Program Files (x86)\NSIS\makensis.exe", r"C:\Program Files\NSIS\makensis.exe"):
        if os.path.exists(p):
            return p
    sys.exit("NSIS introuvable. Installez-le :\n  macOS   : brew install makensis\n"
             "  Linux   : sudo apt install nsis\n  Windows : winget install NSIS.NSIS")


def check_content():
    step("Vérification du contenu (data/*.json)")
    run([sys.executable, os.path.join(ROOT, "installer", "check_content.py")])


def download(url, dest):
    if os.path.exists(dest):
        print(f"   (en cache) {os.path.basename(dest)}")
        return
    print(f"   téléchargement de {url}")
    tmp = dest + ".part"
    try:
        with urllib.request.urlopen(url, context=_ssl_context()) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
    except OSError as e:
        # certains Python (python.org sur macOS) n'ont pas de certificats installés : on passe par curl
        if not shutil.which("curl"):
            raise
        print(f"   ({e.__class__.__name__} : nouvel essai avec curl)")
        run(["curl", "-L", "--fail", "-o", tmp, url])
    os.replace(tmp, dest)


def _ssl_context():
    """Contexte SSL avec les certificats de certifi (fourni avec pip) si le système n'en propose pas."""
    import ssl
    for mod in ("certifi", "pip._vendor.certifi"):
        try:
            return ssl.create_default_context(cafile=__import__(mod, fromlist=["where"]).where())
        except (ImportError, OSError):
            continue
    return ssl.create_default_context()


def python_runtime(runtime):
    step(f"Python {PY_VERSION} pour Windows (embarquable)")
    os.makedirs(CACHE, exist_ok=True)
    archive = os.path.join(CACHE, os.path.basename(PY_URL))
    download(PY_URL, archive)
    with zipfile.ZipFile(archive) as z:
        z.extractall(runtime)
    # chemins de recherche : bibliothèque standard, paquets, puis le dossier du jeu (parent de runtime)
    with open(os.path.join(runtime, f"python{PY_TAG}._pth"), "w", encoding="utf-8") as f:
        f.write(f"python{PY_TAG}.zip\n.\nLib\\site-packages\n..\nimport site\n")


def packages(runtime):
    step("Paquets Python pour Windows (pip download --platform win_amd64)")
    wheels = os.path.join(CACHE, f"wheels-cp{PY_TAG}")
    os.makedirs(wheels, exist_ok=True)
    run([sys.executable, "-m", "pip", "download", "--quiet", "--only-binary=:all:", "--platform", "win_amd64",
         "--python-version", PY_TAG, "--implementation", "cp", "-d", wheels, "-r",
         os.path.join(ROOT, "requirements.txt")])
    site = os.path.join(runtime, "Lib", "site-packages")
    os.makedirs(site, exist_ok=True)
    found = sorted(glob.glob(os.path.join(wheels, "*.whl")))
    if not found:
        sys.exit("Aucun paquet téléchargé.")
    for whl in found:
        print("   +", os.path.basename(whl))
        with zipfile.ZipFile(whl) as z:      # une roue est une archive zip prête à être copiée
            z.extractall(site)


def stage_game():
    step("Assemblage du jeu")
    if os.path.exists(os.path.dirname(STAGE)):
        shutil.rmtree(os.path.dirname(STAGE))
    os.makedirs(STAGE)
    for f in GAME_FILES:
        shutil.copy2(os.path.join(ROOT, f), STAGE)
    for d in GAME_DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(STAGE, d), ignore=IGNORE)
    icon = os.path.join(STAGE, "cendrespire.ico")
    run([sys.executable, os.path.join(ROOT, "installer", "make_icon.py"), icon])
    # marqueur « version installée » : sauvegardes dans %APPDATA%\Cendrespire (voir game/settings.py)
    with open(os.path.join(STAGE, "installed.txt"), "w", encoding="utf-8") as f:
        f.write("Cendrespire installé : les sauvegardes sont dans %APPDATA%\\Cendrespire\\saves\n")
    return icon


def size_kb(path):
    total = 0
    for base, _dirs, files in os.walk(path):
        for f in files:
            total += os.path.getsize(os.path.join(base, f))
    return total // 1024


def build_installer(version, icon):
    step("Compilation de l'installeur (NSIS)")
    os.makedirs(OUTPUT, exist_ok=True)
    out = os.path.join(OUTPUT, f"Cendrespire-{version}-Setup.exe")
    run([find_makensis(), "-V2", f"-DVERSION={version}", f"-DSTAGE={STAGE}", f"-DOUTFILE={out}",
         f"-DICON={icon}", f"-DSIZE_KB={size_kb(STAGE)}", os.path.join(ROOT, "installer", "cendrespire.nsi")])
    return out


def latest_version():
    """Version de la note de mise à jour la plus récente (data/updates/<version>.json)."""
    import json
    best = (0,)
    for path in glob.glob(os.path.join(ROOT, "data", "updates", "*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                v = str(json.load(f)["version"])
            best = max(best, tuple(int(x) for x in v.split(".")))
        except (OSError, ValueError, KeyError):
            continue
    return ".".join(str(x) for x in best) if best != (0,) else "1.0"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", help="par défaut : la version la plus récente de data/updates/")
    args = ap.parse_args()
    args.version = args.version or latest_version()
    find_makensis()
    check_content()
    icon_stage = stage_game()
    runtime = os.path.join(STAGE, "runtime")
    python_runtime(runtime)
    packages(runtime)
    out = build_installer(args.version, icon_stage)
    print(f"\nInstalleur prêt : {out} ({os.path.getsize(out) // (1024 * 1024)} Mo)")


if __name__ == "__main__":
    main()
