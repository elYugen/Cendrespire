# Construit l'installeur Windows de Cendrespire.
#   1. installe les dépendances et PyInstaller dans .venv (créé si besoin) ;
#   2. génère l'icône ;
#   3. empaquette le jeu avec PyInstaller dans dist\Cendrespire (avec assets\ : polices, modèles 3D,
#      et data\ : contenu JSON modifiable et notes de mise à jour) ;
#   4. compile l'installeur avec Inno Setup : installer\Output\Cendrespire-<version>-Setup.exe
#
# Usage (PowerShell, à la racine du projet) :  .\build_installer.ps1
# Prérequis : Python 3.10+ et Inno Setup 6 (winget install JRSoftware.InnoSetup).
param([string]$Version = "2.1")
# les outils natifs écrivent leur journal sur stderr : on se fie à leurs codes de retour
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$py = ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Création de l'environnement virtuel..."
    python -m venv .venv
    if (-not $?) { throw "Impossible de créer .venv (Python est-il installé ?)" }
}

Write-Host "Dépendances..."
& $py -m pip install --quiet -r requirements.txt pyinstaller
if ($LASTEXITCODE) { throw "pip a échoué" }

Write-Host "Icône..."
& $py installer\make_icon.py installer\cendrespire.ico
if ($LASTEXITCODE) { throw "Génération de l'icône échouée" }

Write-Host "Vérification du contenu (data\*.json)..."
& $py installer\check_content.py
if ($LASTEXITCODE) { throw "Le contenu JSON est invalide (voir le message ci-dessus)" }

Write-Host "Empaquetage PyInstaller..."
& $py -m PyInstaller main.py --noconfirm --clean --windowed --onedir --log-level WARN `
    --name Cendrespire --icon "$PSScriptRoot\installer\cendrespire.ico" `
    --collect-submodules glcontext --hidden-import glcontext.wgl `
    --add-data "$PSScriptRoot\assets;assets" `
    --add-data "$PSScriptRoot\data;data" `
    --distpath dist --workpath build\pyinstaller --specpath build
if ($LASTEXITCODE) { throw "PyInstaller a échoué" }

$iscc = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source,
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 introuvable : winget install JRSoftware.InnoSetup" }

Write-Host "Compilation de l'installeur..."
& $iscc /Qp "/DAppVersion=$Version" installer\cendrespire.iss
if ($LASTEXITCODE) { throw "Inno Setup a échoué" }

Write-Host ""
Write-Host "Installeur prêt : installer\Output\Cendrespire-$Version-Setup.exe"
