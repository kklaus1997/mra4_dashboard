"""Test single register reads"""
from modbus_client import MRA4Client
import struct

def decode_float(regs):
    """Decode 2 registers as Float32"""
    if len(regs) != 2:
        return None
    value = (regs[0] << 16) | regs[1]
    return struct.unpack('>f', struct.pack('>I', value))[0]

client = MRA4Client(host='192.168.130.202', port=502, unit_id=255)
if not client.connect():
    print("Connection failed")
    exit(1)

print("=== Testing Individual Registers ===\n")

tests = [
    ("Frequenz f", 20128, 2),
    ("Voltage UL1", 20136, 2),
    ("Voltage UL2", 20138, 2),
    ("Voltage UL3", 20140, 2),
    ("Power P", 20154, 2),
    ("Current IL1", 20100, 2),
    ("Current IL2", 20102, 2),
    ("Current IL3", 20104, 2),
]

for name, addr, count in tests:
    result = client.client.read_input_registers(address=addr, count=count, device_id=255)

    if result.isError():
        print(f"{name} @ {addr}: ERROR - {result}")
    else:
        regs = result.registers
        if count == 2:
            float_val = decode_float(regs)
            print(f"{name} @ {addr}: {regs} -> {float_val:.3f}")
        else:
            print(f"{name} @ {addr}: {regs}")

client.disconnect()
print("\nDone")
