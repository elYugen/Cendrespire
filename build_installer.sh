#!/bin/sh
# Construit l'installeur Windows de Cendrespire depuis macOS ou Linux (aucun Windows, Docker ni Wine nécessaire).
#   Prérequis : Python 3.10+ et NSIS (macOS : brew install makensis · Linux : sudo apt install nsis)
#   Usage     : ./build_installer.sh [version]      ->  installer/Output/Cendrespire-<version>-Setup.exe
#               (version par défaut : la plus récente de data/updates/)
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet -r requirements.txt
.venv/bin/python installer/build.py ${1:+--version "$1"}
