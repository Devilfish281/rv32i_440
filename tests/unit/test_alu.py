# tests/unit/test_alu.py
from midterm_440.numeric_core.alu import add_bits, sub_bits
from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits


# Helpers to view results as unsigned ints (for easy asserts)
def bits_to_u32_hex(bits):
    return f"0x{bits_to_u32(bits):08X}"


def test_add_overflow_positive_edge():
    a = u32_to_bits(0x7FFFFFFF)
    b = u32_to_bits(0x00000001)
    res, N, Z, C, V = add_bits(a, b)
    assert bits_to_u32_hex(res) == "0x80000000"
    assert (V, C, N, Z) == (1, 0, 1, 0)


def test_sub_overflow_negative_edge():
    a = u32_to_bits(0x80000000)
    b = u32_to_bits(0x00000001)
    res, N, Z, C, V = sub_bits(a, b)
    assert bits_to_u32_hex(res) == "0x7FFFFFFF"
    assert (V, C, N, Z) == (1, 1, 0, 0)


def test_add_minus1_plus_minus1():
    a = u32_to_bits(0xFFFFFFFF)  # -1
    b = u32_to_bits(0xFFFFFFFF)  # -1
    res, N, Z, C, V = add_bits(a, b)
    # -1 + -1 = -2 -> 0xFFFFFFFE
    assert bits_to_u32_hex(res) == "0xFFFFFFFE"
    assert (V, C, N, Z) == (0, 1, 1, 0)
