# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File für MRA4 Dashboard
Erstellt eine ausführbare .exe mit allen Dependencies
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Pfad zum Hauptverzeichnis
block_cipher = None
app_name = 'MRA4_Dashboard'

# Alle zu inkludierenden Dateien
added_files = [
    ('../app.py', '.'),
    ('../modbus_client.py', '.'),
    ('../config_manager.py', '.'),
    ('../assets', 'assets'),
    ('../MRA4-3.7-DE-Modbus.xlsx', '.'),
]

# Hidden imports für Dash und Modbus
hiddenimports = [
    'dash',
    'dash.dependencies',
    'dash_bootstrap_components',
    'dash_daq',
    'plotly',
    'pymodbus',
    'pymodbus.client',
    'pymodbus.exceptions',
    'pandas',
    'openpyxl',
    'werkzeug',
    'flask',
    'flask_compress',
]

# Dash-spezifische Daten
dash_data = collect_data_files('dash')
dbc_data = collect_data_files('dash_bootstrap_components')
daq_data = collect_data_files('dash_daq')

a = Analysis(
    ['../app.py'],
    pathex=[],
    binaries=[],
    datas=added_files + dash_data + dbc_data + daq_data,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Console-Fenster anzeigen für Logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../assets/icon.ico',  # Icon für die .exe
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
