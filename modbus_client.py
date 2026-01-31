"""
Modbus TCP Client für MRA 4 Multimeter
Kommunikation über Modbus TCP/IP
"""

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import logging

# Logging-Konfiguration für Modbus-Kommunikation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MRA4Client:
    """Client zur Kommunikation mit dem MRA 4 Multimeter über Modbus TCP"""

    def __init__(self, host='192.168.1.100', port=502, unit_id=1):
        """
        Initialisiert den Modbus TCP Client

        Args:
            host: IP-Adresse des MRA 4 Geräts
            port: Modbus TCP Port (Standard: 502)
            unit_id: Modbus Unit ID (Standard: 1)
        """
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.client = ModbusTcpClient(host=host, port=port)
        self.connected = False

    def connect(self):
        """Verbindung zum MRA 4 herstellen"""
        try:
            self.connected = self.client.connect()
            if self.connected:
                logger.info(f"Verbunden mit MRA 4 auf {self.host}:{self.port}")
            else:
                logger.error(f"Verbindung zu {self.host}:{self.port} fehlgeschlagen")
            return self.connected
        except Exception as e:
            logger.error(f"Verbindungsfehler: {e}")
            return False

    def disconnect(self):
        """Verbindung trennen"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Verbindung getrennt")

    def read_voltage(self, phase=1):
        """
        Spannung lesen (L1, L2, L3)

        Args:
            phase: Phase 1-3

        Returns:
            Spannung in Volt oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adressen für Spannung UL1, UL2, UL3 (Leiter-Erd-Spannung, Grundwelle)
            # L1: 20136, L2: 20138, L3: 20140 (je 2 Register für Float IEE754)
            # Function Code 4 = Read Input Registers
            address = 20136 + (phase - 1) * 2
            result = self.client.read_input_registers(address=address, count=2, device_id=self.unit_id)

            if not result.isError():
                # 2 Register zu Float kombinieren (Big-Endian)
                value = self._registers_to_float(result.registers, byte_order='big')
                return round(value, 2)
            else:
                logger.error(f"Fehler beim Lesen der Spannung Phase {phase}: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Spannung Phase {phase}: {e}")
            return None

    def read_current(self, phase=1):
        """
        Strom lesen (L1, L2, L3)

        Args:
            phase: Phase 1-3

        Returns:
            Strom in Ampere oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adressen für Strom IL1, IL2, IL3 (Phasenstrom, Grundwelle)
            # L1: 20100, L2: 20102, L3: 20104 (je 2 Register für Float IEE754)
            # Function Code 4 = Read Input Registers
            address = 20100 + (phase - 1) * 2
            result = self.client.read_input_registers(address=address, count=2, device_id=self.unit_id)

            if not result.isError():
                value = self._registers_to_float(result.registers)
                return round(value, 3)
            else:
                logger.error(f"Fehler beim Lesen des Stroms Phase {phase}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Stroms: {e}")
            return None

    def read_power(self, phase=1):
        """
        Leistung lesen pro Phase (berechnet aus Gesamtleistung / 3)

        Hinweis: MRA4 liefert nur Gesamtwirkleistung P, nicht pro Phase.
        Diese Funktion gibt 1/3 der Gesamtleistung zurück als Annäherung.

        Args:
            phase: Phase 1-3 (wird ignoriert, alle Phasen bekommen gleiche Werte)

        Returns:
            Leistung in Watt oder None bei Fehler
        """
        try:
            total = self.read_total_power()
            if total is not None:
                # Approximation: Gesamtleistung gleichmäßig auf 3 Phasen verteilt
                return round(total / 3, 2)
            return None
        except Exception as e:
            logger.error(f"Fehler beim Berechnen der Leistung Phase {phase}: {e}")
            return None

    def read_total_power(self):
        """
        Gesamtwirkleistung P lesen

        Returns:
            Gesamtleistung in Watt oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Wirkleistung P (Input Register)
            # Address: 20154 (2 Register für Float IEE754)
            # Function Code 4 = Read Input Registers
            address = 20154
            result = self.client.read_input_registers(address=address, count=2, device_id=self.unit_id)

            if not result.isError():
                value = self._registers_to_float(result.registers)
                return round(value, 2)
            else:
                logger.error("Fehler beim Lesen der Gesamtleistung")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Gesamtleistung: {e}")
            return None

    def read_frequency(self):
        """
        Netzfrequenz lesen

        Returns:
            Frequenz in Hz oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Frequenz f (Input Register)
            # Address: 20128 (2 Register für Float IEE754)
            # Function Code 4 = Read Input Registers
            address = 20128
            result = self.client.read_input_registers(address=address, count=2, device_id=self.unit_id)

            if not result.isError():
                value = self._registers_to_float(result.registers)
                return round(value, 2)
            else:
                logger.error("Fehler beim Lesen der Frequenz")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Frequenz: {e}")
            return None

    def read_coupling_switch(self):
        """
        Leittechnik-Befehl Status lesen (Rang Leitt-Bef 1)

        Returns:
            True wenn EIN, False wenn AUS, None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Leittechnik-Bef Status (Holding Register)
            # Address: 1005, Bit 0 (0x1) = Leittechnik-Bef 1
            # Function Code 3 = Read Holding Registers
            address = 1005
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                value = result.registers[0]
                # Bit 0 prüfen (0x1)
                is_on = (value & 0x1) != 0
                return is_on
            else:
                logger.error(f"Fehler beim Lesen des Leittechnik-Befehls: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Leittechnik-Befehls: {e}")
            return None

    def read_di_status(self, di_number=1):
        """
        Digitaler Eingang Status lesen (DI Slot X1)
        Register 1000, Bit 0-7 = DI 1-8

        Args:
            di_number: DI Nummer 1-8

        Returns:
            True wenn aktiv, False wenn inaktiv, None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für DI Slot X1 (Holding Register)
            # Address: 1000, Function Code 3
            address = 1000
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                value = result.registers[0]
                # Bit-Maske für DI (DI1=0x1, DI2=0x2, DI3=0x4, etc.)
                bit_mask = 1 << (di_number - 1)
                is_active = (value & bit_mask) != 0
                return is_active
            else:
                logger.error(f"Fehler beim Lesen des DI {di_number}: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen des DI {di_number}: {e}")
            return None

    def read_protection_status(self):
        """
        Schutz-Status lesen (Register 1)

        Returns:
            Dictionary mit Schutz-Status-Bits oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Schutz-Status (Holding Register)
            # Address: 1, Function Code 3
            address = 1
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                value = result.registers[0]
                return {
                    'aktiv': (value & 0x4) != 0,
                    'alarm': (value & 0x100) != 0,
                    'alarm_l1': (value & 0x10) != 0,
                    'alarm_l2': (value & 0x20) != 0,
                    'alarm_l3': (value & 0x40) != 0,
                    'ausl': (value & 0x2000) != 0,  # General-Auslösung
                    'ausl_l1': (value & 0x200) != 0,
                    'ausl_l2': (value & 0x400) != 0,
                    'ausl_l3': (value & 0x800) != 0,
                    'raw_value': value
                }
            else:
                logger.error(f"Fehler beim Lesen des Schutz-Status: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Schutz-Status: {e}")
            return None

    def read_cause_of_trip(self):
        """
        Auslöseursache (COT) lesen
        Register 5004 = COT Code

        Returns:
            COT Code (Integer) oder None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Auslöseursache (Holding Register)
            # Address: 5004, Function Code 3
            address = 5004
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                return result.registers[0]
            else:
                logger.error(f"Fehler beim Lesen der Auslöseursache: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Auslöseursache: {e}")
            return None

    def read_fault_number(self):
        """
        Störfall-Nummer lesen
        Register 57 = Störfall-Nr.

        Returns:
            Störfall-Nummer oder None bei Fehler
        """
        try:
            address = 57
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                return result.registers[0]
            else:
                logger.error(f"Fehler beim Lesen der Störfall-Nr.: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Störfall-Nr.: {e}")
            return None

    def acknowledge_all(self):
        """
        Quittierung durchführen über Leittechnik-Befehl 2
        Register 22021 (Rang Leitt-Bef 2) - einmaliger Impuls

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            import time
            # Leittechnik-Befehl 2 (Rang Leitt-Bef 2) für Quittierung
            # Function Code 5 = Write Single Coil
            address = 22021

            # Impuls EIN
            result = self.client.write_coil(address=address, value=True, device_id=self.unit_id)
            if not result.isError():
                logger.info(f"Quittierung gesendet (Register {address} EIN)")
            else:
                logger.error(f"Fehler beim Quittieren (Register {address}): {result}")
                return False

            # Kurze Pause (100ms)
            time.sleep(0.1)

            # Impuls AUS
            result = self.client.write_coil(address=address, value=False, device_id=self.unit_id)
            if not result.isError():
                logger.info(f"Quittierung abgeschlossen (Register {address} AUS)")
                return True
            else:
                logger.error(f"Fehler beim Quittieren AUS (Register {address}): {result}")
                return False

        except Exception as e:
            logger.error(f"Fehler beim Quittieren: {e}")
            return False

    def acknowledge_device(self):
        """
        Gerät quittieren (LEDs, Ausgangsrelais, Leittechnik, Gerät)
        Register 22003 = Quittierung Gerät - einmaliger Impuls

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            import time
            # MRA 4 Modbus-Adresse für Quittierung Gerät
            # Address: 22003, Function Code 5
            address = 22003

            # Impuls EIN
            result = self.client.write_coil(address=address, value=True, device_id=self.unit_id)
            if not result.isError():
                logger.info(f"Gerät-Quittierung gesendet (Register {address})")
            else:
                logger.error(f"Fehler beim Quittieren: {result}")
                return False

            # Kurze Pause
            time.sleep(0.1)

            # Impuls AUS
            result = self.client.write_coil(address=address, value=False, device_id=self.unit_id)
            if not result.isError():
                logger.info("Gerät quittiert")
                return True
            else:
                logger.error(f"Fehler beim Quittieren AUS: {result}")
                return False

        except Exception as e:
            logger.error(f"Fehler beim Quittieren: {e}")
            return False

    def acknowledge_trip_command(self):
        """
        Auslösebefehl quittieren
        Register 22005 = Quittierung Auslösebefehl - einmaliger Impuls

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            import time
            address = 22005

            # Impuls EIN
            result = self.client.write_coil(address=address, value=True, device_id=self.unit_id)
            if not result.isError():
                logger.info(f"Auslösebefehl-Quittierung gesendet (Register {address})")
            else:
                logger.error(f"Fehler beim Quittieren des Auslösebefehls: {result}")
                return False

            # Kurze Pause
            time.sleep(0.1)

            # Impuls AUS
            result = self.client.write_coil(address=address, value=False, device_id=self.unit_id)
            if not result.isError():
                logger.info("Auslösebefehl quittiert")
                return True
            else:
                logger.error(f"Fehler beim Quittieren AUS: {result}")
                return False

        except Exception as e:
            logger.error(f"Fehler beim Quittieren des Auslösebefehls: {e}")
            return False

    def send_coupling_pulse(self, duration=2.0):
        """
        Impuls an Koppelschalter senden (BA1 = Leittechnik-Befehl 1)
        Sendet Impuls (EIN für duration Sekunden, dann AUS) an Register 22020

        Args:
            duration: Dauer des Impulses in Sekunden (Standard: 2.0)

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            import time
            # Impuls EIN - Register 22020 (Leittechnik-Befehl 1 = Koppelschalter)
            result = self.client.write_coil(address=22020, value=True, device_id=self.unit_id)
            if result.isError():
                logger.error(f"Fehler beim Senden des Impulses (EIN): {result}")
                return False

            logger.info(f"Koppelschalter-Impuls gesendet (EIN auf Register 22020 für {duration}s)")

            # Pause für die angegebene Dauer
            time.sleep(duration)

            # Impuls AUS
            result = self.client.write_coil(address=22020, value=False, device_id=self.unit_id)
            if result.isError():
                logger.error(f"Fehler beim Senden des Impulses (AUS): {result}")
                return False

            logger.info("Koppelschalter-Impuls gesendet (AUS)")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Senden des Impulses: {e}")
            return False

    def write_coupling_switch(self, state):
        """
        Leittechnik-Befehl 1 schalten (Rang Leitt-Bef 1 = Koppelschalter)

        Args:
            state: True für EIN, False für AUS

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Rang Leitt-Bef 1 (Coil)
            # Address: 22020
            # Function Code 5 = Write Single Coil
            # True = On (0xFF00), False = Off (0x0000)
            address = 22020
            result = self.client.write_coil(address=address, value=state, device_id=self.unit_id)

            if not result.isError():
                logger.info(f"Leittechnik-Befehl 1 (Koppelschalter) auf {'EIN' if state else 'AUS'} gesetzt")
                return True
            else:
                logger.error(f"Fehler beim Schalten des Leittechnik-Befehls 1: {result}")
                return False
        except Exception as e:
            logger.error(f"Fehler beim Schalten des Leittechnik-Befehls 1: {e}")
            return False

    def write_fault_recording_trigger(self, state):
        """
        Leittechnik-Befehl 3 schalten (Rang Leitt-Bef 3 = Störschrieb starten)

        Args:
            state: True für EIN (Störschrieb starten), False für AUS

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Rang Leitt-Bef 3 (Coil)
            # Address: 22022
            # Function Code 5 = Write Single Coil
            # True = On (0xFF00), False = Off (0x0000)
            address = 22022
            result = self.client.write_coil(address=address, value=state, device_id=self.unit_id)

            if not result.isError():
                logger.info(f"Leittechnik-Befehl 3 (Störschrieb) auf {'EIN' if state else 'AUS'} gesetzt")
                return True
            else:
                logger.error(f"Fehler beim Schalten des Leittechnik-Befehls 3: {result}")
                return False
        except Exception as e:
            logger.error(f"Fehler beim Schalten des Leittechnik-Befehls 3: {e}")
            return False

    def read_fault_recording_status(self):
        """
        Leittechnik-Befehl 3 Status lesen (Rang Leitt-Bef 3)

        Returns:
            True wenn EIN, False wenn AUS, None bei Fehler
        """
        try:
            # MRA 4 Modbus-Adresse für Leittechnik-Bef 3 Status (Holding Register)
            # Address: 1005, Bit 2 (0x4) = Leittechnik-Bef 3
            # Function Code 3 = Read Holding Registers
            address = 1005
            result = self.client.read_holding_registers(address=address, count=1, device_id=self.unit_id)

            if not result.isError():
                value = result.registers[0]
                # Bit 2 prüfen (0x4)
                is_on = (value & 0x4) != 0
                return is_on
            else:
                logger.error(f"Fehler beim Lesen des Leittechnik-Befehls 3: {result}")
                return None
        except Exception as e:
            logger.error(f"Fehler beim Lesen des Leittechnik-Befehls 3: {e}")
            return None

    def read_all_data(self):
        """
        Alle Messwerte auf einmal lesen

        Returns:
            Dictionary mit allen Messwerten
        """
        data = {
            'voltage': {
                'L1': self.read_voltage(1),
                'L2': self.read_voltage(2),
                'L3': self.read_voltage(3)
            },
            'current': {
                'L1': self.read_current(1),
                'L2': self.read_current(2),
                'L3': self.read_current(3)
            },
            'power': {
                'L1': self.read_power(1),
                'L2': self.read_power(2),
                'L3': self.read_power(3),
                'total': self.read_total_power()
            },
            'frequency': self.read_frequency(),
            'coupling_switch': self.read_coupling_switch(),
            'di_status': self.read_di_status(1),  # DI 1 = Koppelschalter-Rückmeldung
            'protection_status': self.read_protection_status(),
            'cause_of_trip': self.read_cause_of_trip(),
            'fault_number': self.read_fault_number()
        }
        return data

    @staticmethod
    def _registers_to_float(registers, byte_order='big'):
        """
        Konvertiert 2 Modbus-Register zu einem Float-Wert

        Args:
            registers: Liste mit 2 Registern
            byte_order: 'big' für Big-Endian (ABCD), 'little' für Little-Endian (CDAB)

        Returns:
            Float-Wert
        """
        import struct

        if byte_order == 'big':
            # Big-Endian: ABCD (Register 0 ist MSW)
            value = (registers[0] << 16) | registers[1]
            return struct.unpack('>f', struct.pack('>I', value))[0]
        else:
            # Little-Endian: CDAB (Register 1 ist MSW)
            value = (registers[1] << 16) | registers[0]
            return struct.unpack('>f', struct.pack('>I', value))[0]


# Simulator für Tests ohne echtes Gerät
class MRA4Simulator:
    """Simulator für Entwicklung und Tests ohne echtes MRA 4"""

    # COT Code Mapping
    COT_CODES = {
        1: "NORM",
        1001: "AnaP[1]", 1002: "AnaP[2]", 1003: "AnaP[3]", 1004: "AnaP[4]",
        1201: "IE[1]", 1202: "IE[2]", 1203: "IE[3]", 1204: "IE[4]",
        1306: "ExS[1]", 1307: "ExS[2]", 1308: "ExS[3]", 1309: "ExS[4]",
        1310: "LS-Mitnahme",
        1401: "f[1]", 1402: "f[2]", 1403: "f[3]", 1404: "f[4]", 1405: "f[5]", 1406: "f[6]",
        1407: "df/dt", 1408: "delta phi",
        2501: "LVRT[1]", 2502: "LVRT[2]",
        2901: "I2>[1]", 2902: "I2>[2]",
        3001: "U012[1]", 3002: "U012[2]", 3003: "U012[3]", 3004: "U012[4]", 3005: "U012[5]", 3006: "U012[6]",
        3201: "I[1]", 3202: "I[2]", 3203: "I[3]", 3204: "I[4]", 3205: "I[5]", 3206: "I[6]",
        3401: "PQS[1]", 3402: "PQS[2]", 3403: "PQS[3]", 3404: "PQS[4]", 3405: "PQS[5]", 3406: "PQS[6]",
        3407: "P", 3408: "Q",
        3501: "LF[1]", 3502: "LF[2]",
        3601: "Q->&U<", 3801: "ThA",
        4001: "UE[1]", 4002: "UE[2]",
        4101: "U[1]", 4102: "U[2]", 4103: "U[3]", 4104: "U[4]", 4105: "U[5]", 4106: "U[6]",
        4107: "HVRT[1]", 4108: "HVRT[2]"
    }

    def __init__(self, host='localhost', port=502, unit_id=1):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.connected = False
        self.coupling_switch_state = False
        self.fault_recording_state = False  # Leittechnik-Befehl 3 (Störschrieb)
        self.di_states = [False] * 8  # DI 1-8
        self.protection_tripped = False
        self.cause_of_trip = 1  # 1 = NORM (kein Trip)
        self.fault_number = 0

        import random
        self.random = random

        # Current values that will change over time (max 10% delta between updates)
        self.current_voltage = [225.0, 228.0, 223.0]  # L1, L2, L3
        self.current_current = [8.0, 9.0, 7.5]  # L1, L2, L3
        self.current_power = [1800.0, 2050.0, 1675.0]  # L1, L2, L3
        self.current_frequency = 50.0

        # Value ranges
        self.voltage_range = (210.0, 240.0)
        self.current_range = (0.0, 20.0)
        self.power_range = (0.0, 4600.0)  # Max per phase
        self.frequency_range = (49.8, 50.2)

    def connect(self):
        self.connected = True
        logger.info(f"[SIMULATOR] Verbunden mit MRA 4 Simulator")
        return True

    def disconnect(self):
        self.connected = False
        logger.info("[SIMULATOR] Verbindung getrennt")

    def _update_value(self, current_val, value_range, max_delta_percent=0.10):
        """Update a value with max 10% delta, staying within range"""
        max_delta = current_val * max_delta_percent
        delta = self.random.uniform(-max_delta, max_delta)
        new_val = current_val + delta
        # Clamp to range
        new_val = max(value_range[0], min(value_range[1], new_val))
        return new_val

    def read_voltage(self, phase=1):
        # Update voltage with max 10% delta, range 210-240V
        idx = phase - 1
        self.current_voltage[idx] = self._update_value(
            self.current_voltage[idx],
            self.voltage_range,
            0.10
        )
        return round(self.current_voltage[idx], 2)

    def read_current(self, phase=1):
        # Update current with max 10% delta
        idx = phase - 1
        self.current_current[idx] = self._update_value(
            self.current_current[idx],
            self.current_range,
            0.10
        )
        return round(self.current_current[idx], 3)

    def read_power(self, phase=1):
        # Update power with max 10% delta
        idx = phase - 1
        self.current_power[idx] = self._update_value(
            self.current_power[idx],
            self.power_range,
            0.10
        )
        return round(self.current_power[idx], 2)

    def read_total_power(self):
        # Sum of all three phases
        total = sum(self.current_power)
        return round(total, 2)

    def read_frequency(self):
        # Update frequency with max 10% delta
        self.current_frequency = self._update_value(
            self.current_frequency,
            self.frequency_range,
            0.10
        )
        return round(self.current_frequency, 2)

    def read_coupling_switch(self):
        return self.coupling_switch_state

    def send_coupling_pulse(self, duration=2.0):
        """Impuls an Koppelschalter senden (simuliert)"""
        import time
        # Toggle-Zustand - EIN setzen
        self.coupling_switch_state = not self.coupling_switch_state
        self.di_states[0] = self.coupling_switch_state
        logger.info(f"[SIMULATOR] Koppelschalter-Impuls gesendet (EIN für {duration}s)")

        # Nach duration Sekunden wieder AUS setzen (wird vom Callback übernommen)
        return True

    def write_coupling_switch(self, state):
        self.coupling_switch_state = state
        # DI 1 folgt dem Koppelschalter-Befehl (Rückmeldung)
        self.di_states[0] = state
        logger.info(f"[SIMULATOR] Koppelschalter auf {'EIN' if state else 'AUS'} gesetzt")
        return True

    def write_fault_recording_trigger(self, state):
        """Störschrieb-Trigger setzen (Leittechnik-Befehl 3, simuliert)"""
        self.fault_recording_state = state
        logger.info(f"[SIMULATOR] Störschrieb-Trigger auf {'EIN' if state else 'AUS'} gesetzt")
        if state:
            # Bei EIN: Störschrieb starten (simuliert)
            logger.info("[SIMULATOR] Störschrieb gestartet")
        return True

    def read_fault_recording_status(self):
        """Störschrieb-Status lesen (simuliert)"""
        return self.fault_recording_state

    def read_di_status(self, di_number=1):
        """Digitaler Eingang Status lesen (simuliert)"""
        if 1 <= di_number <= 8:
            return self.di_states[di_number - 1]
        return False

    def read_protection_status(self):
        """Schutz-Status lesen (simuliert)"""
        return {
            'aktiv': True,
            'alarm': False,
            'alarm_l1': False,
            'alarm_l2': False,
            'alarm_l3': False,
            'ausl': self.protection_tripped,
            'ausl_l1': False,
            'ausl_l2': False,
            'ausl_l3': False,
            'raw_value': 0x2000 if self.protection_tripped else 0x4
        }

    def read_cause_of_trip(self):
        """Auslöseursache lesen (simuliert)"""
        return self.cause_of_trip

    def read_fault_number(self):
        """Störfall-Nummer lesen (simuliert)"""
        return self.fault_number

    def acknowledge_all(self):
        """Alle Quittierungen durchführen (simuliert)"""
        self.protection_tripped = False
        self.cause_of_trip = 1  # Reset to NORM
        logger.info("[SIMULATOR] Alle Quittierungen durchgeführt (Register 22000-22005)")
        return True

    def acknowledge_device(self):
        """Gerät quittieren (simuliert)"""
        self.protection_tripped = False
        self.cause_of_trip = 1  # Reset to NORM
        logger.info("[SIMULATOR] Gerät quittiert")
        return True

    def acknowledge_trip_command(self):
        """Auslösebefehl quittieren (simuliert)"""
        self.protection_tripped = False
        logger.info("[SIMULATOR] Auslösebefehl quittiert")
        return True

    def simulate_trip(self, cot_code=3201):
        """Simuliere eine Auslösung (nur für Tests)"""
        self.protection_tripped = True
        self.cause_of_trip = cot_code
        self.fault_number += 1
        logger.info(f"[SIMULATOR] Auslösung simuliert: COT={cot_code} ({self.COT_CODES.get(cot_code, 'Unbekannt')})")

    def read_all_data(self):
        data = {
            'voltage': {
                'L1': self.read_voltage(1),
                'L2': self.read_voltage(2),
                'L3': self.read_voltage(3)
            },
            'current': {
                'L1': self.read_current(1),
                'L2': self.read_current(2),
                'L3': self.read_current(3)
            },
            'power': {
                'L1': self.read_power(1),
                'L2': self.read_power(2),
                'L3': self.read_power(3),
                'total': self.read_total_power()
            },
            'frequency': self.read_frequency(),
            'coupling_switch': self.read_coupling_switch(),
            'di_status': self.read_di_status(1),
            'protection_status': self.read_protection_status(),
            'cause_of_trip': self.read_cause_of_trip(),
            'fault_number': self.read_fault_number()
        }
        return data
