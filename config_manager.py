"""
Konfigurationsverwaltung für MRA 4 Dashboard
"""
import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / 'config.json'

DEFAULT_CONFIG = {
    "max_power_kw": 12.0,
    "update_interval_ms": 1000,
    "graph_history_seconds": 60,
    "dark_mode": True,
    "modbus": {
        "ip": "192.168.1.100",
        "port": 502,
        "unit_id": 1,
        "use_simulator": True
    },
    "passwords": {
        "general": "2023",
        "hypervisor": "202320"
    }
}

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        """Lade Konfiguration aus Datei oder erstelle Default"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Fehler beim Laden der Config: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            # Erstelle Default-Config
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def save_config(self, config=None):
        """Speichere Konfiguration in Datei"""
        if config is None:
            config = self.config
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern der Config: {e}")
            return False

    def get(self, key, default=None):
        """Hole einzelnen Config-Wert"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key, value):
        """Setze einzelnen Config-Wert"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        return self.save_config()

    def update(self, updates):
        """Update mehrere Config-Werte"""
        for key, value in updates.items():
            self.set(key, value)
        return self.save_config()

# Singleton-Instanz
_config_manager = None

def get_config_manager():
    """Hole Config-Manager Singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def save_config(config_dict):
    """Speichere komplette Konfiguration"""
    manager = get_config_manager()
    manager.config = config_dict
    return manager.save_config()
