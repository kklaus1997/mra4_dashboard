"""Test different Modbus address offsets"""
from modbus_client import MRA4Client
import struct

client = MRA4Client(host='192.168.130.202', port=502, unit_id=255)
if not client.connect():
    print("Connection failed")
    exit(1)

print("=== Testing Voltage L1 UL1 (Register 20136) ===\n")

# Test different address interpretations
tests = [
    ("20136 as-is", 20136),
    ("20136 - 1 (0-based)", 20135),
    ("20136 - 20000", 136),
    ("20136 - 30001 (Input Reg offset)", -9865),
]

for name, addr in tests:
    if addr < 0:
        print(f"{name}: Skipped (negative address)\n")
        continue

    print(f"{name}: address={addr}")
    result = client.client.read_input_registers(address=addr, count=2, device_id=255)

    if result.isError():
        print(f"  Error: {result}\n")
    else:
        regs = result.registers
        print(f"  Registers: {regs}")

        # Try to decode as Float32
        if len(regs) == 2:
            # Big-endian
            value_big = (regs[0] << 16) | regs[1]
            float_big = struct.unpack('>f', struct.pack('>I', value_big))[0]

            # Little-endian
            value_little = (regs[1] << 16) | regs[0]
            float_little = struct.unpack('>f', struct.pack('>I', value_little))[0]

            print(f"  As Float (Big-Endian): {float_big:.2f}")
            print(f"  As Float (Little-Endian): {float_little:.2f}\n")

client.disconnect()
print("Done")
