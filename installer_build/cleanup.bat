@echo off
REM ========================================
REM MRA4 Dashboard - Cleanup Script
REM Löscht Build-Artefakte und temporäre Dateien
REM ========================================

echo ========================================
echo MRA4 Dashboard - Cleanup
echo ========================================
echo.
echo Loescht temporaere Build-Dateien...
echo.

cd /d "%~dp0"

if exist build (
    echo Loesche build\...
    rmdir /s /q build
)

if exist dist (
    echo Loesche dist\...
    rmdir /s /q dist
)

if exist venv (
    echo Deaktiviere venv falls aktiv...
    call venv\Scripts\deactivate.bat 2>nul
    timeout /t 2 /nobreak >nul
    echo Beende Python-Prozesse...
    taskkill /F /IM python.exe 2>nul
    timeout /t 1 /nobreak >nul
    echo Loesche venv\...
    rmdir /s /q venv 2>nul
    if exist venv (
        echo [WARNUNG] venv gesperrt, versuche forciert...
        rd /s /q venv 2>nul
    )
)

if exist Output (
    echo Loesche Output\...
    rmdir /s /q Output
)

if exist __pycache__ (
    echo Loesche __pycache__\...
    rmdir /s /q __pycache__
)

echo.
echo Cleanup abgeschlossen!
echo.
pause
