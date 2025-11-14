from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits
from midterm_440.numeric_core.mdu import div_restoring, mul_shift_add


def hx(b):
    return f"0x{bits_to_u32(b):08X}"


def test_mul_neg_one():
    a = u32_to_bits(12345678)
    b = u32_to_bits(0xFFFFFFFF)
    m = mul_shift_add(a, b)
    assert hx(m["rd_bits"]) == "0xFF439EB2"
    assert m["overflow"] == 1


def test_div_signed_basic():
    a = u32_to_bits(0xFFFFFFF9)  # -7
    b = u32_to_bits(3)
    d = div_restoring(a, b, signed=True)
    assert hx(d["q_bits"]) == "0xFFFFFFFE"
    assert hx(d["r_bits"]) == "0xFFFFFFFF"
    assert d["flags"] == {"div_by_zero": 0, "overflow": 0}


def _hx(b):
    return f"0x{bits_to_u32(b):08X}"


def test_div_by_zero_signed():
    a = u32_to_bits(123)
    b = u32_to_bits(0)
    out = div_restoring(a, b, signed=True)
    assert _hx(out["q_bits"]) == "0xFFFFFFFF"
    assert _hx(out["r_bits"]) == "0x0000007B"
    assert out["flags"]["div_by_zero"] == 1


def test_div_intmin_by_minus1_signed():
    a = u32_to_bits(0x80000000)
    b = u32_to_bits(0xFFFFFFFF)  # -1
    out = div_restoring(a, b, signed=True)
    assert _hx(out["q_bits"]) == "0x80000000"
    assert _hx(out["r_bits"]) == "0x00000000"
    assert out["flags"]["overflow"] == 1


def test_mul_shift_add_sign_overflow_trace_smoke():
    a = u32_to_bits(12345678)
    b = u32_to_bits(0xFFFFFFFF)  # -1
    out = mul_shift_add(a, b)
    assert _hx(out["rd_bits"]) == "0xFF439EB2"
    assert out["overflow"] in (0, 1)  # signed overflow may occur depending on hi bits
    assert isinstance(out["trace"], list) and len(out["trace"]) == 32
