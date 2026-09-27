# Construit l'installeur Windows de Cendrespire depuis Windows (même procédure que build_installer.sh sur macOS/Linux).
#   Prérequis : Python 3.10+ et NSIS (winget install NSIS.NSIS)
#   Usage (PowerShell, à la racine du projet) :  .\build_installer.ps1 [-Version X.Y]
#   (version par défaut : la plus récente de data/updates/)
#   Résultat : installer\Output\Cendrespire-<version>-Setup.exe
param([string]$Version = "")
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Création de l'environnement virtuel..."
    python -m venv .venv
    if (-not $?) { throw "Impossible de créer .venv (Python est-il installé ?)" }
}
& $py -m pip install --quiet -r requirements.txt
if ($LASTEXITCODE) { throw "pip a échoué" }
if ($Version) { & $py installer\build.py --version $Version } else { & $py installer\build.py }
if ($LASTEXITCODE) { throw "La construction de l'installeur a échoué" }
