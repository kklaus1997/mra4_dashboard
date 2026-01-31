@echo off
REM ========================================
REM MRA4 Dashboard - Automatischer Build
REM Alle Dependencies werden automatisch installiert!
REM ========================================

color 0A
cd /d "%~dp0"

echo.
echo ========================================
echo   MRA4 DASHBOARD - AUTO BUILD
echo ========================================
echo.
echo Alle Dependencies werden automatisch installiert!
echo Keine manuelle Installation erforderlich.
echo.

REM ========================================
REM Schritt 1: Python pruefen
REM ========================================
echo [1/6] Pruefe Python-Installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [FEHLER] Python nicht gefunden!
    echo.
    echo Bitte Python 3.8+ installieren von:
    echo https://www.python.org/downloads/
    echo.
    echo WICHTIG: "Add Python to PATH" aktivieren!
    echo.
    pause
    exit /b 1
)
python --version
echo Python gefunden!
echo.

REM ========================================
REM Schritt 2: Virtuelle Umgebung
REM ========================================
echo [2/6] Erstelle virtuelle Umgebung...
if exist venv (
    echo Deaktiviere alte venv...
    call venv\Scripts\deactivate.bat 2>nul
    timeout /t 2 /nobreak >nul
    echo Loesche alte venv...
    rmdir /s /q venv 2>nul
    if exist venv (
        echo [WARNUNG] venv gesperrt - benenne um...
        move venv venv_old_%RANDOM% 2>nul
        timeout /t 1 /nobreak >nul
    )
)
python -m venv venv
if errorlevel 1 (
    echo [FEHLER] venv konnte nicht erstellt werden!
    echo Moeglicherweise laeuft noch ein Python-Prozess.
    echo Bitte alle Python-Prozesse beenden und neu versuchen.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo Virtuelle Umgebung erstellt!
echo.

REM ========================================
REM Schritt 3: PIP upgraden
REM ========================================
echo [3/6] Aktualisiere pip...
python -m pip install --upgrade pip --quiet
echo pip aktualisiert!
echo.

REM ========================================
REM Schritt 4: Dependencies auto-install
REM ========================================
echo [4/6] Installiere alle Dependencies...
echo Dies kann 2-5 Minuten dauern...
echo.
pip install -r requirements.txt --quiet --disable-pip-version-check
pip install pyinstaller --quiet --disable-pip-version-check
echo.
echo Alle Dependencies installiert!
echo.

REM ========================================
REM Schritt 5: PyInstaller Build
REM ========================================
echo [5/6] Erstelle .exe mit PyInstaller...
echo Dies kann 5-10 Minuten dauern...
echo.
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

pyinstaller build_spec.py

if errorlevel 1 (
    echo.
    echo [FEHLER] PyInstaller Build fehlgeschlagen!
    pause
    exit /b 1
)
echo.
echo PyInstaller Build erfolgreich!
echo.

REM ========================================
REM Schritt 6: Inno Setup Installer
REM ========================================
echo [6/6] Erstelle Windows Installer...

set "INNO_SETUP=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_SETUP%" (
    echo.
    echo [INFO] Inno Setup nicht installiert.
    echo Portable .exe wurde erstellt: dist\MRA4_Dashboard\
    echo.
    echo Fuer vollstaendigen Installer:
    echo https://jrsoftware.org/isdl.php
    echo.
    goto :success
)

"%INNO_SETUP%" installer_script.iss >nul 2>&1

if errorlevel 1 (
    echo [WARNUNG] Installer-Build fehlgeschlagen.
    echo Portable Version verfuegbar: dist\MRA4_Dashboard\
    goto :success
)

:success
cls
echo.
echo.
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@# #@@@@@@@@@@@@@    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@   @@@@*@@@@@@     @@@@      *@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  @@@@@  @      @%%    @ @@       .   @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                              @@      @@@@@@        =@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
echo.
echo                              ======================================================
echo                                        BUILD ERFOLGREICH ABGESCHLOSSEN!
echo                              ======================================================
echo.
if exist "Output\MRA4_Dashboard_Setup.exe" (
    echo                                   INSTALLER ERSTELLT:
    echo                                   Output\MRA4_Dashboard_Setup.exe
    echo.
)
echo                                   PORTABLE VERSION:
echo                                   dist\MRA4_Dashboard\MRA4_Dashboard.exe
echo.
echo                              ======================================================
echo                                 Alle Dependencies sind in der .exe enthalten!
echo                                 Funktioniert auf jedem Windows-PC ohne Installation!
echo                              ======================================================
echo.
echo.
pause

deactivate
exit /b 0
