"""Test write coil vs write register"""
from modbus_client import MRA4Client
import logging

logging.basicConfig(level=logging.INFO)

client = MRA4Client(host='192.168.130.202', port=502, unit_id=255)
if not client.connect():
    print("Connection failed")
    exit(1)

print("=== Testing Coupling Switch Write ===\n")

# Test 1: write_coil
print("Test 1: Using write_coil(address=22020, value=True)")
result1 = client.client.write_coil(address=22020, value=True, device_id=255)
if hasattr(result1, 'isError'):
    print(f"  isError: {result1.isError()}")
    if result1.isError():
        print(f"  Error: {result1}")
    else:
        print(f"  Success!")
else:
    print(f"  Result: {result1}")

# Test 2: write_register
print("\nTest 2: Using write_register(address=22020, value=0xFF00)")
result2 = client.client.write_register(address=22020, value=0xFF00, device_id=255)
if hasattr(result2, 'isError'):
    print(f"  isError: {result2.isError()}")
    if result2.isError():
        print(f"  Error: {result2}")
    else:
        print(f"  Success!")
else:
    print(f"  Result: {result2}")

# Test 3: write_registers (plural) - for holding registers
print("\nTest 3: Using write_registers(address=22020, values=[0xFF00])")
result3 = client.client.write_registers(address=22020, values=[0xFF00], device_id=255)
if hasattr(result3, 'isError'):
    print(f"  isError: {result3.isError()}")
    if result3.isError():
        print(f"  Error: {result3}")
    else:
        print(f"  Success!")
else:
    print(f"  Result: {result3}")

# Read back
print("\nReading back with read_holding_registers:")
result = client.read_coupling_switch()
print(f"  Current status: {result}")

client.disconnect()
print("\nDone")
