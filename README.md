# MRA 4 Dashboard

Minimalistisches dunkles Dashboard für MRA 4 Multimeter mit Modbus TCP/IP Kommunikation.

## Features

- **Echtzeit-Monitoring**
  - Spannungs-Anzeige für alle 3 Phasen (L1, L2, L3) mit Gauges
  - Strom-Anzeige für alle 3 Phasen mit Gauges
  - Leistungs-Anzeige pro Phase + Gesamtleistung
  - Netzfrequenz-Überwachung

- **Live-Graphen**
  - Verlaufsdiagramme für Spannung, Strom und Leistung
  - 60 Sekunden Historie (konfigurierbar)
  - Echtzeit-Update alle 1 Sekunde

- **Steuerung**
  - Koppelschalter-Steuerung mit PowerButton
  - Sofortige Statusanzeige

- **Design**
  - Schwarzes minimales Design
  - Neon-Akzente (Grün, Cyan, Pink)
  - Startbildschirm mit Logo-Placeholder
  - Responsive Layout

## Installation

1. Dependencies installieren:
```bash
pip install -r requirements.txt
```

## Start

### Mit Simulator (für Entwicklung):
```bash
python app.py
```

### Mit echtem MRA 4 Gerät:

1. In [app.py](app.py) Zeile 21 ändern:
```python
USE_SIMULATOR = False
```

2. IP-Adresse anpassen (Zeile 24):
```python
mra4 = MRA4Client(host='192.168.1.100', port=502)
```

3. Dashboard starten:
```bash
python app.py
```

## Zugriff

Öffne im Browser:
```
http://localhost:8050
```

Für Zugriff aus dem Netzwerk:
```
http://<DEINE-IP>:8050
```

## Seiten

- **/** - Hauptdashboard mit allen Messwerten und Graphen
- **/settings** - Einstellungen für Modbus-Verbindung und Anzeigeoptionen

## Konfiguration

### Modbus-Register Anpassen

Die Register-Adressen in [modbus_client.py](modbus_client.py) sind Beispiele und müssen an dein MRA 4 angepasst werden:

- Spannung: Zeile 65 (`address = (phase - 1) * 2`)
- Strom: Zeile 92 (`address = 10 + (phase - 1) * 2`)
- Leistung: Zeile 118 (`address = 20 + (phase - 1) * 2`)
- Gesamtleistung: Zeile 139 (`address = 30`)
- Frequenz: Zeile 160 (`address = 40`)
- Koppelschalter: Zeile 181 und 204 (`address = 100`)

### Update-Intervall ändern

In [app.py](app.py) Zeile mit `dcc.Interval`:
```python
dcc.Interval(id='interval-component', interval=1000, n_intervals=0)  # 1000ms = 1 Sekunde
```

### Graph-Historie anpassen

In [app.py](app.py) Zeile 30:
```python
MAX_DATA_POINTS = 60  # Anzahl der Datenpunkte (bei 1s Update = 60 Sekunden)
```

## Simulator

Der integrierte Simulator (`MRA4Simulator`) generiert realistische Testwerte:
- Spannung: ~230V ±5V
- Strom: ~10A ±2A
- Leistung: ~2300W ±200W pro Phase
- Gesamtleistung: ~6900W ±500W
- Frequenz: ~50Hz ±0.1Hz

## Technologie-Stack

- **Dash** - Web-Framework
- **Plotly** - Graphen
- **Dash DAQ** - Gauges und Steuerelemente
- **PyModbus** - Modbus TCP/IP Kommunikation
- **Bootstrap** - Responsive Layout (Cyborg Theme)

## Screenshots

### Startbildschirm
- Neon-Logo mit "MRA 4" Text
- Initialisierungsanzeige

### Hauptdashboard
- Foto-Placeholder oben
- Verbindungsstatus & Frequenz
- 3x Spannungs-Gauges mit Live-Graph
- 3x Strom-Gauges mit Live-Graph
- Leistungs-Anzeige (L1, L2, L3, Gesamt) mit Live-Graph
- Koppelschalter PowerButton

### Einstellungen
- Modbus-Konfiguration (IP, Port, Unit ID)
- Simulator-Toggle
- Verbindungstest
- Update-Intervall & Graph-Historie
- System-Information

## Troubleshooting

### Verbindung schlägt fehl
- IP-Adresse und Port überprüfen
- Firewall-Einstellungen prüfen
- MRA 4 Gerät ist erreichbar (ping)
- Modbus TCP/IP am Gerät aktiviert

### Keine Daten werden angezeigt
- Register-Adressen in [modbus_client.py](modbus_client.py) prüfen
- Unit ID überprüfen
- Logs in der Konsole beachten

### Dashboard lädt nicht
- Port 8050 bereits belegt? Anderen Port verwenden
- Dependencies installiert?
```bash
pip install -r requirements.txt
```

## Lizenz

MIT
