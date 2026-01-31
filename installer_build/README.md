# MRA4 Dashboard - Installer Build

Dieses Verzeichnis enthält alle notwendigen Dateien zum Erstellen eines Windows-Installers für das MRA4 Dashboard.

## 📋 Voraussetzungen

### Erforderlich:
1. **Python 3.8 oder neuer**
   - Download: https://www.python.org/downloads/
   - Bei Installation: "Add Python to PATH" aktivieren

### Optional (für vollständigen Installer):
2. **Inno Setup 6**
   - Download: https://jrsoftware.org/isdl.php
   - Wird benötigt um die .exe in einen Installer zu verpacken

## 🚀 Build-Anleitung

### Automatischer Build (empfohlen):

1. Doppelklick auf `build_installer.bat`
2. Der Build-Prozess läuft automatisch ab
3. Nach Abschluss finden Sie:
   - **Installer**: `Output\MRA4_Dashboard_Setup.exe`
   - **Portable EXE**: `dist\MRA4_Dashboard\MRA4_Dashboard.exe`

### Manueller Build:

```batch
# 1. Virtuelle Umgebung erstellen
python -m venv venv
call venv\Scripts\activate.bat

# 2. Dependencies installieren
pip install -r requirements.txt
pip install pyinstaller

# 3. .exe erstellen
pyinstaller --clean build_spec.py

# 4. Installer erstellen (optional)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer_script.iss
```

## 📦 Dateien im Build-Verzeichnis

- `build_installer.bat` - Automatisches Build-Script
- `build_spec.py` - PyInstaller Konfiguration
- `installer_script.iss` - Inno Setup Konfiguration
- `requirements.txt` - Python Dependencies
- `README.md` - Diese Datei

## 📁 Verzeichnisstruktur nach Build

```
installer_build/
├── dist/
│   └── MRA4_Dashboard/
│       ├── MRA4_Dashboard.exe  ← Portable Version
│       ├── assets/
│       ├── config.json
│       └── ... (alle Dependencies)
├── Output/
│   └── MRA4_Dashboard_Setup.exe  ← Windows Installer
├── build/  (temporär, kann gelöscht werden)
└── venv/   (temporär, kann gelöscht werden)
```

## 🎯 Was macht der Installer?

Der erstellte Installer (`MRA4_Dashboard_Setup.exe`):

1. ✅ Installiert die Anwendung in `C:\Program Files\MRA4 Dashboard\`
2. ✅ Erstellt Desktop-Verknüpfung (optional)
3. ✅ Erstellt Start-Menü-Einträge
4. ✅ Fügt Firewall-Ausnahme hinzu (für Modbus TCP)
5. ✅ Speichert Konfiguration in `%APPDATA%\MRA4_Dashboard\`
6. ✅ Ermöglicht saubere Deinstallation

## ⚙️ Konfiguration anpassen

### PyInstaller-Einstellungen ändern:
Bearbeiten Sie `build_spec.py`:
- Icon ändern: `icon='pfad/zu/icon.ico'`
- Console ausblenden: `console=False`
- Weitere Dateien hinzufügen: `added_files` erweitern

### Installer-Einstellungen ändern:
Bearbeiten Sie `installer_script.iss`:
- Firmenname: `#define MyAppPublisher`
- Version: `#define MyAppVersion`
- Installations-Verzeichnis: `DefaultDirName`

## 🐛 Fehlerbehebung

### "Python nicht gefunden"
- Stellen Sie sicher, dass Python im PATH ist
- Neustart nach Python-Installation

### "PyInstaller Build fehlgeschlagen"
- Prüfen Sie die Fehlermeldung in der Konsole
- Löschen Sie `build/` und `dist/` Ordner
- Führen Sie Build erneut aus

### "Inno Setup nicht gefunden"
- Installer ist optional
- Sie können die .exe aus `dist\MRA4_Dashboard\` direkt verwenden
- Oder Inno Setup installieren für vollständigen Installer

### "Import Error" beim Starten der .exe
- Prüfen Sie `hiddenimports` in `build_spec.py`
- Fügen Sie fehlende Module hinzu

## 📝 Hinweise

- Der erste Build kann 5-10 Minuten dauern
- Die erstellte .exe ist ~150-200 MB groß (enthält alle Dependencies)
- Der Installer ist ~150-200 MB groß
- Die Anwendung benötigt ca. 400 MB Festplattenspeicher nach Installation

## 🔒 Sicherheit

- Der Installer benötigt Administrator-Rechte (für Firewall-Regel)
- Die Anwendung selbst kann danach ohne Admin-Rechte ausgeführt werden
- Config-Dateien werden in `%APPDATA%` gespeichert (benutzerspezifisch)

## 📞 Support

Bei Problemen:
1. Prüfen Sie die Konsolen-Ausgabe auf Fehlermeldungen
2. Lesen Sie diese README vollständig
3. Kontaktieren Sie den Entwickler
