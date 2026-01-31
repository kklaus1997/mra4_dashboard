@echo off
REM ========================================
REM MRA4 Dashboard - Portable Build
REM Alle Dependencies werden automatisch installiert!
REM ========================================

color 0B
cd /d "%~dp0"

echo.
echo ========================================
echo   MRA4 DASHBOARD - PORTABLE BUILD
echo ========================================
echo.
echo Alle Dependencies werden automatisch installiert!
echo.

echo [1/5] Pruefe Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden!
    pause
    exit /b 1
)
python --version
echo.

echo [2/5] Erstelle virtuelle Umgebung...
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
echo.

echo [3/5] Installiere Dependencies...
echo Dies kann 2-5 Minuten dauern...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
echo Alle Dependencies installiert!
echo.

echo [4/5] Erstelle portable .exe...
echo Dies kann 5-10 Minuten dauern...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

pyinstaller build_spec.py

if errorlevel 1 (
    echo [FEHLER] Build fehlgeschlagen!
    pause
    exit /b 1
)
echo.

cls
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
echo                                   PORTABLE VERSION ERFOLGREICH ERSTELLT!
echo                              ======================================================
echo.
echo                                   SPEICHERORT:
echo                                   dist\MRA4_Dashboard\MRA4_Dashboard.exe
echo.
echo                              ======================================================
echo                                 Gesamten Ordner kopieren - keine Installation noetig!
echo                                 Funktioniert auf jedem Windows-PC!
echo                              ======================================================
echo.
pause

deactivate
exit /b 0
