"""Test reading coil status"""
from modbus_client import MRA4Client
import logging
import time

logging.basicConfig(level=logging.INFO)

client = MRA4Client(host='192.168.130.202', port=502, unit_id=255)
if not client.connect():
    print("Connection failed")
    exit(1)

print("=== Testing Coil Read Methods ===\n")

# Write ON
print("1. Writing K1 ON...")
result = client.write_coupling_switch(True)
print(f"   Write result: {result}")
time.sleep(0.1)

# Try different read methods
print("\n2. Reading with read_coils (Function Code 1):")
r1 = client.client.read_coils(address=22020, count=1, device_id=255)
if hasattr(r1, 'isError') and not r1.isError():
    print(f"   Bits: {r1.bits}")
    print(f"   Value: {r1.bits[0] if len(r1.bits) > 0 else 'N/A'}")
else:
    print(f"   Error: {r1}")

print("\n3. Reading with read_holding_registers (Function Code 3):")
r2 = client.client.read_holding_registers(address=22020, count=1, device_id=255)
if hasattr(r2, 'isError') and not r2.isError():
    print(f"   Registers: {r2.registers}")
    print(f"   Value: 0x{r2.registers[0]:04X} = {r2.registers[0]}")
else:
    print(f"   Error: {r2}")

print("\n4. Reading with read_discrete_inputs (Function Code 2):")
r3 = client.client.read_discrete_inputs(address=22020, count=1, device_id=255)
if hasattr(r3, 'isError') and not r3.isError():
    print(f"   Bits: {r3.bits}")
    print(f"   Value: {r3.bits[0] if len(r3.bits) > 0 else 'N/A'}")
else:
    print(f"   Error: {r3}")

print("\n5. Reading with read_input_registers (Function Code 4):")
r4 = client.client.read_input_registers(address=22020, count=1, device_id=255)
if hasattr(r4, 'isError') and not r4.isError():
    print(f"   Registers: {r4.registers}")
    print(f"   Value: {r4.registers[0]}")
else:
    print(f"   Error: {r4}")

# Write OFF and test
print("\n\n6. Writing K1 OFF...")
result = client.write_coupling_switch(False)
print(f"   Write result: {result}")
time.sleep(0.1)

print("\n7. Reading with read_coils after OFF:")
r5 = client.client.read_coils(address=22020, count=1, device_id=255)
if hasattr(r5, 'isError') and not r5.isError():
    print(f"   Bits: {r5.bits}")
    print(f"   Value: {r5.bits[0] if len(r5.bits) > 0 else 'N/A'}")
else:
    print(f"   Error: {r5}")

client.disconnect()
print("\nDone")
