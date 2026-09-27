; Installeur Windows de Cendrespire (NSIS 3).
; Ne pas compiler directement : lancer « python installer/build.py », qui prépare d'abord le jeu dans
; build/windows/Cendrespire (code, contenu, Python pour Windows, paquets) puis appelle makensis.
; Fonctionne depuis macOS, Linux ou Windows.

Unicode true
!include "MUI2.nsh"

!define APP "Cendrespire"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"

Name "${APP} ${VERSION}"
OutFile "${OUTFILE}"
; installation pour l'utilisateur courant : pas besoin des droits administrateur
RequestExecutionLevel user
InstallDir "$LOCALAPPDATA\Programs\${APP}"
InstallDirRegKey HKCU "Software\${APP}" "InstallDir"
SetCompressor /SOLID lzma
BrandingText "${APP} ${VERSION}"

!define MUI_ICON "${ICON}"
!define MUI_UNICON "${ICON}"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchGame

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${VERSION}.0.0"
VIAddVersionKey /LANG=${LANG_FRENCH} "ProductName" "${APP}"
VIAddVersionKey /LANG=${LANG_FRENCH} "FileDescription" "Installeur de ${APP}"
VIAddVersionKey /LANG=${LANG_FRENCH} "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=${LANG_FRENCH} "ProductVersion" "${VERSION}"
VIAddVersionKey /LANG=${LANG_FRENCH} "CompanyName" "elyugen"
VIAddVersionKey /LANG=${LANG_FRENCH} "LegalCopyright" "elyugen"

Function LaunchGame
  SetOutPath "$INSTDIR"
  Exec '"$INSTDIR\runtime\pythonw.exe" "$INSTDIR\main.py"'
FunctionEnd

!macro SHORTCUT path
  CreateShortCut "${path}" "$INSTDIR\runtime\pythonw.exe" '"$INSTDIR\main.py"' "$INSTDIR\cendrespire.ico" 0 SW_SHOWNORMAL "" "${APP}"
!macroend

Section "${APP}" SecGame
  SectionIn RO
  ; une mise à jour remplace le code sans toucher aux sauvegardes (%APPDATA%\Cendrespire)
  RMDir /r "$INSTDIR\game"
  RMDir /r "$INSTDIR\runtime"
  RMDir /r "$INSTDIR\data"
  RMDir /r "$INSTDIR\backup"
  Delete "$INSTDIR\version.txt"     ; version posée par la mise à jour intégrée : l'installeur fait foi
  SetOutPath "$INSTDIR"
  File /r "${STAGE}/*"
  CreateDirectory "$APPDATA\${APP}\data"
  CreateDirectory "$SMPROGRAMS\${APP}"
  !insertmacro SHORTCUT "$SMPROGRAMS\${APP}\${APP}.lnk"
  CreateShortCut "$SMPROGRAMS\${APP}\${APP} - contenu personnalisé.lnk" "$APPDATA\${APP}\data"
  CreateShortCut "$SMPROGRAMS\${APP}\Désinstaller ${APP}.lnk" "$INSTDIR\uninstall.exe"
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\${APP}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "elyugen"
  WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\cendrespire.ico"
  WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKCU "${UNINST_KEY}" "EstimatedSize" ${SIZE_KB}
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Raccourci sur le bureau" SecDesktop
  !insertmacro SHORTCUT "$DESKTOP\${APP}.lnk"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APP}.lnk"
  RMDir /r "$SMPROGRAMS\${APP}"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${UNINST_KEY}"
  DeleteRegKey HKCU "Software\${APP}"
  ; les sauvegardes et le contenu personnalisé (%APPDATA%\Cendrespire) sont volontairement conservés
SectionEnd
