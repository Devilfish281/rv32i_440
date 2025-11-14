# tests/unit/test_fpu_f32.py
# to run: poetry run pytest tests\unit\test_fpu_f32.py -q
from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits
from midterm_440.numeric_core.fpu_f32 import (
    fadd_f32,
    fmul_f32,
    fsub_f32,
    pack_f32,
    unpack_f32,
)


def test_pack_unpack_zero_inf_nan():
    for u in (0x00000000, 0x80000000):  # +0, -0
        bits = u32_to_bits(u)
        out = unpack_f32(bits)
        pk = pack_f32(out["value"])
        assert bits_to_u32(pk["bits"]) == u

    for u in (0x7F800000, 0xFF800000):  # +inf, -inf
        bits = u32_to_bits(u)
        d = unpack_f32(bits)
        assert d["class"] == "inf"

    nan_bits = u32_to_bits(0x7FC00001)  # quiet NaN exemplar
    d = unpack_f32(nan_bits)
    assert d["class"] == "nan"


def test_add_sub_mul_smoke():
    a = pack_f32(1.5)["bits"]
    b = pack_f32(2.25)["bits"]
    s = fadd_f32(a, b)
    assert unpack_f32(s["res_bits"])["value"] == 3.75

    d = fsub_f32(b, a)
    assert unpack_f32(d["res_bits"])["value"] == 0.75

    m = fmul_f32(a, b)
    assert abs(unpack_f32(m["res_bits"])["value"] - 3.375) < 1e-7
