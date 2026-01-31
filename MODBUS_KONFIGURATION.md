# MRA4 Modbus-Konfiguration

## Erfolgreiche Fehlerbehebungen

### 1. Pymodbus API (Version 3.11.4)
**Problem**: Parameter `slave=` wurde nicht akzeptiert
**Lösung**: Geändert zu `device_id=` (neue API ab pymodbus 3.10.0+)

```python
# ALT (funktioniert nicht mehr):
result = client.read_holding_registers(address=20136, count=2, slave=1)

# NEU (korrekt):
result = client.read_input_registers(address=20136, count=2, device_id=255)
```

### 2. Modbus Function Codes
**Problem**: Alle Lesevorgänge schlugen fehl mit "Illegal Data Address" (Exception Code 2)
**Lösung**: Messwerte verwenden Function Code 4 (Read Input Registers), nicht Function Code 3 (Read Holding Registers)

**Aus der Datenpunktliste MRA4-3.7-DE-Modbus.xlsx:**
- **Measure-Sheet** (alle Messwerte): Function Code 4 = Read Input Registers
- **Command-Sheet** (Befehle/Schalter): Function Code 5/6 = Write Coil/Register

```python
# Messwerte (Spannung, Strom, Leistung, Frequenz):
result = client.read_input_registers(address=20136, count=2, device_id=255)

# Koppelschalter (Befehle):
result = client.read_holding_registers(address=22020, count=1, device_id=255)
```

### 3. Korrekte Modbus-Adressen

Basierend auf **MRA4-3.7-DE-Modbus.xlsx** (Measure-Sheet):

| Parameter | Register | Adresse | Format | Function Code |
|-----------|----------|---------|--------|---------------|
| Frequenz f | 20128 | 20128 | Float IEE754 (2 Reg) | 4 (Input) |
| Spannung UL1 | 20136 | 20136 | Float IEE754 (2 Reg) | 4 (Input) |
| Spannung UL2 | 20138 | 20138 | Float IEE754 (2 Reg) | 4 (Input) |
| Spannung UL3 | 20140 | 20140 | Float IEE754 (2 Reg) | 4 (Input) |
| Strom IL1 | 20100 | 20100 | Float IEE754 (2 Reg) | 4 (Input) |
| Strom IL2 | 20102 | 20102 | Float IEE754 (2 Reg) | 4 (Input) |
| Strom IL3 | 20104 | 20104 | Float IEE754 (2 Reg) | 4 (Input) |
| Wirkleistung P | 20154 | 20154 | Float IEE754 (2 Reg) | 4 (Input) |
| Koppelschalter | 22020 | 22020 | 0xFF00/0x0000 (1 Reg) | 3/5 (Holding) |

**Wichtig:**
- Modbus-Adressen werden **ohne Offset** verwendet (20136 = Adresse 20136)
- **Kein 30001-Offset** für Input Registers
- **Kein -1 Offset** (nicht 0-basiert in diesem Fall)

## Aktuelle Konfiguration

**IP-Adresse**: 192.168.130.202
**Port**: 502
**Unit ID**: 255
**Simulator**: EIN (für Tests)

### Status der Modbus-Kommunikation
✅ Verbindung erfolgreich
✅ Keine Modbus-Fehler
✅ Alle Register lesbar
⚠️ Messwerte sind 0.0 (Gerät nicht an Messspannung angeschlossen)

## Float-Konvertierung

Das MRA4 verwendet **Float IEE754** Format mit **Big-Endian** Byte-Order:

```python
def _registers_to_float(registers, byte_order='big'):
    import struct
    if byte_order == 'big':
        # Big-Endian: ABCD (Register 0 ist MSW)
        value = (registers[0] << 16) | registers[1]
        return struct.unpack('>f', struct.pack('>I', value))[0]
```

## Wechsel zwischen Simulator und echtem Gerät

**Simulator aktivieren** (für Tests ohne Hardware):
```json
{
    "modbus": {
        "use_simulator": true
    }
}
```

**Echtes Gerät aktivieren** (wenn an Messspannung angeschlossen):
```json
{
    "modbus": {
        "ip": "192.168.130.202",
        "port": 502,
        "unit_id": 255,
        "use_simulator": false
    }
}
```

Oder über das Dashboard: **Einstellungen** → Simulator-Modus umschalten → **Übernehmen**

## Leistungsberechnung pro Phase

**Hinweis**: Das MRA4 liefert nur die **Gesamtwirkleistung P** (Register 20154), nicht einzeln pro Phase.

Die Funktion `read_power(phase)` gibt daher eine **Approximation** zurück:
- Leistung pro Phase = Gesamtleistung / 3
- Dies ist eine Vereinfachung und gilt nur bei symmetrischer Last

Für genaue phasenspezifische Leistungswerte müsste man:
1. P = U × I × cos(φ) für jede Phase berechnen
2. Phasenlage-Informationen verwenden (phi UL1/IL1, etc.)

## Test-Scripts

### test_modbus.py
Testet alle Messwerte einzeln:
```bash
python test_modbus.py
```

### test_single_reads.py
Testet einzelne Register-Lesevorgänge:
```bash
python test_single_reads.py
```

### scan_registers.py
Scannt Register-Bereiche nach Werten:
```bash
python scan_registers.py
```

## Troubleshooting

### Problem: "Connection refused"
- Prüfen Sie IP-Adresse und Port in config.json
- Stellen Sie sicher, dass das MRA4-Gerät eingeschaltet ist
- Prüfen Sie Netzwerkverbindung (ping 192.168.130.202)

### Problem: "Illegal Data Address" (Exception Code 2)
- Prüfen Sie, ob der richtige Function Code verwendet wird
- Messwerte: read_input_registers (Function Code 4)
- Befehle: read_holding_registers (Function Code 3)

### Problem: Alle Werte sind 0.0
- Das ist normal, wenn das Gerät nur an Versorgungsspannung angeschlossen ist
- Verwenden Sie den Simulator für Tests: `"use_simulator": true`

### Problem: "ModbusException: Slave device is busy"
- Reduzieren Sie die Abfragegeschwindigkeit (update_interval_ms erhöhen)
- Standard: 1000ms (1 Sekunde)
