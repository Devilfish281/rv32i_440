# tests/unit/test_shifter.py
import pytest

# We test the shifter using the bit helpers already in your project.
from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits
from midterm_440.numeric_core.shifter import sll_bits, sra_bits, srl_bits

# to run these tests, use:
# poetry run pytest -q tests\unit\test_shifter.py


def _hex_u32(bits):  # small helper for pretty asserts
    return f"0x{bits_to_u32(bits):08X}"


def test_sll_basic():  # 0x00000001 << 1 => 0x00000002
    a = u32_to_bits(0x00000001)
    out = sll_bits(a, 1)
    assert _hex_u32(out) == "0x00000002"


def test_sll_drop_msb():  # MSB shifts out
    a = u32_to_bits(0x80000000)
    out = sll_bits(a, 1)
    assert _hex_u32(out) == "0x00000000"


def test_srl_basic():  # logical right: fill with 0s
    a = u32_to_bits(0x80000000)
    out = srl_bits(a, 1)
    assert _hex_u32(out) == "0x40000000"


def test_srl_to_zero():  # 1 >> 1 -> 0
    a = u32_to_bits(0x00000001)
    out = srl_bits(a, 1)
    assert _hex_u32(out) == "0x00000000"


def test_sra_sign_extend_negative():  # arithmetic right: keep sign
    a = u32_to_bits(0x80000001)
    out = sra_bits(a, 1)
    assert _hex_u32(out) == "0xC0000000"


def test_sra_sign_extend_positive():  # positive stays positive on SRA
    a = u32_to_bits(0x7FFFFFFF)
    out = sra_bits(a, 1)
    assert _hex_u32(out) == "0x3FFFFFFF"


def test_edge_shamt_zero():  # shifting by 0 changes nothing
    a = u32_to_bits(0xA5A5A5A5)
    assert _hex_u32(sll_bits(a, 0)) == "0xA5A5A5A5"
    assert _hex_u32(srl_bits(a, 0)) == "0xA5A5A5A5"
    assert _hex_u32(sra_bits(a, 0)) == "0xA5A5A5A5"


def test_edge_shamt_31_patterns():  # big shifts
    # SLL: 1 << 31 -> 0x80000000
    a = u32_to_bits(0x00000001)
    assert _hex_u32(sll_bits(a, 31)) == "0x80000000"
    # SRL: 0x80000000 >> 31 -> 0x00000001 (logical)
    b = u32_to_bits(0x80000000)
    assert _hex_u32(srl_bits(b, 31)) == "0x00000001"
    # SRA: 0x80000000 >> 31 -> 0xFFFFFFFF (arithmetic, sign stays 1)
    assert _hex_u32(sra_bits(b, 31)) == "0xFFFFFFFF"


def test_invalid_shamt():  # out of range should raise
    a = u32_to_bits(0x12345678)
    with pytest.raises(ValueError):
        sll_bits(a, -1)
    with pytest.raises(ValueError):
        srl_bits(a, 32)
    with pytest.raises(ValueError):
        sra_bits(a, 99)


def test_invalid_bits_length():  # must be 32 bits of 0/1
    bad = [0, 1, 0]
    with pytest.raises(ValueError):
        sll_bits(bad, 1)
    with pytest.raises(ValueError):
        srl_bits(bad, 1)
    with pytest.raises(ValueError):
        sra_bits(bad, 1)
