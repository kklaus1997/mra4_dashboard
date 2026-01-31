"""
Test Modbus Connection
"""
from modbus_client import MRA4Client
from config_manager import get_config_manager
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get config
config = get_config_manager()
ip = config.get('modbus.ip', '192.168.1.100')
port = config.get('modbus.port', 502)
unit_id = config.get('modbus.unit_id', 1)

print(f"\n=== Modbus Connection Test ===")
print(f"IP: {ip}")
print(f"Port: {port}")
print(f"Unit ID: {unit_id}")
print(f"================================\n")

# Create client
client = MRA4Client(host=ip, port=port, unit_id=unit_id)

# Connect
print("Connecting...")
if client.connect():
    print("Connection successful\n")

    # Test read voltage
    print("Testing read voltage L1 (address 20136)...")
    voltage = client.read_voltage(1)
    print(f"Result: {voltage} V\n")

    # Test read current
    print("Testing read current L1 (address 20100)...")
    current = client.read_current(1)
    print(f"Result: {current} A\n")

    # Test read power
    print("Testing read total power (address 20154)...")
    power = client.read_total_power()
    print(f"Result: {power} W\n")

    # Test read frequency
    print("Testing read frequency (address 20128)...")
    freq = client.read_frequency()
    print(f"Result: {freq} Hz\n")

    # Test coupling switch
    print("Testing read coupling switch (address 22020)...")
    switch = client.read_coupling_switch()
    print(f"Result: {switch}\n")

    # Disconnect
    client.disconnect()
    print("OK Disconnected")
else:
    print("ERROR Connection failed")
