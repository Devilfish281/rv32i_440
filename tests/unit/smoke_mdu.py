from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits
from midterm_440.numeric_core.mdu import div_restoring, mul_shift_add

# to run this script, use:
# poetry run python scripts\smoke_mdu.py


def hx(b):
    return f"0x{bits_to_u32(b):08X}"


a = u32_to_bits(12345678)
b = u32_to_bits(0xFFFFFFFF)  # -1
m = mul_shift_add(a, b)
print("MUL 12345678 * -1 -> rd =", hx(m["rd_bits"]), "overflow=", m["overflow"])

a = u32_to_bits(0xFFFFFFF9)  # -7
b = u32_to_bits(3)
d = div_restoring(a, b, signed=True)
print("DIV -7 / 3 -> q =", hx(d["q_bits"]), "r =", hx(d["r_bits"]), d["flags"])

a = u32_to_bits(0x80000000)
b = u32_to_bits(3)
du = div_restoring(a, b, signed=False)
print(
    "DIVU 0x80000000 / 3 -> q =", hx(du["q_bits"]), "r =", hx(du["r_bits"]), du["flags"]
)

a = u32_to_bits(123)
b = u32_to_bits(0)
dz = div_restoring(a, b, signed=True)
print("DIV 123 / 0 -> q =", hx(dz["q_bits"]), "r =", hx(dz["r_bits"]), dz["flags"])

a = u32_to_bits(0x80000000)
b = u32_to_bits(0xFFFFFFFF)  # -1
io = div_restoring(a, b, signed=True)
print("DIV INT_MIN/-1 -> q =", hx(io["q_bits"]), "r =", hx(io["r_bits"]), io["flags"])
