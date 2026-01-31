"""Scan Modbus registers for non-zero values"""
from modbus_client import MRA4Client

client = MRA4Client(host='192.168.130.202', port=502, unit_id=255)
if not client.connect():
    print("Connection failed")
    exit(1)

print("=== Scanning Input Registers for non-zero values ===\n")

# Scan ranges from the datenpunktliste
ranges_to_scan = [
    ("Datum/Uhrzeit", 20000, 6),
    ("StW (Current)", 20100, 10),
    ("SpW (Voltage)", 20128, 20),
    ("PQSZ (Power)", 20152, 10),
]

for name, start, count in ranges_to_scan:
    print(f"\n{name}: Registers {start}-{start+count*2-1}")
    result = client.client.read_input_registers(address=start, count=count*2, device_id=255)

    if result.isError():
        print(f"  Error: {result}")
    else:
        regs = result.registers
        # Show only non-zero registers
        non_zero = [(i, regs[i]) for i in range(len(regs)) if regs[i] != 0]
        if non_zero:
            for idx, val in non_zero:
                print(f"  Reg {start + idx}: {val} (0x{val:04X})")
        else:
            print(f"  All registers are 0")

client.disconnect()
print("\nDone")
