; Installeur Windows de Cendrespire (Inno Setup 6).
; Ne pas compiler directement : lancer build_installer.ps1 à la racine du projet,
; qui construit d'abord le jeu avec PyInstaller dans dist\Cendrespire.

#define AppName "Cendrespire"
#ifndef AppVersion
  #define AppVersion "2.0"
#endif
#define AppExe "Cendrespire.exe"

[Setup]
AppId={{6C1B7E7A-3F2D-4B8E-9A51-C3E1D5F0A2B4}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=elyugen
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; installation pour l'utilisateur courant par défaut (pas besoin des droits administrateur),
; l'installeur propose aussi l'installation pour tous les utilisateurs
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename={#AppName}-{#AppVersion}-Setup
SetupIconFile=cendrespire.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; Les sauvegardes (%APPDATA%\Cendrespire\saves) sont volontairement conservées à la désinstallation.
