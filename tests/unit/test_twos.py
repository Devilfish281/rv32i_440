# tests/unit/test_twos.py
# # To run these tests, use:
# poetry run pytest
import pytest

from midterm_440.numeric_core.bits import u32_to_bits
from midterm_440.numeric_core.twos import (
    decode_twos_complement,
    encode_twos_complement,
    sign_extend,
    zero_extend,
)


# Encode tests
def test_encode_positive():
    # 13 should be normal: no overflow, hex is 0x0000000D
    out = encode_twos_complement(13)
    assert out["overflow_flag"] == 0
    assert out["hex"] == "0x0000000D"
    assert out["bin"].endswith("00001101")


def test_encode_negative():
    # -13 should turn into FFFFFF F3 and no overflow
    out = encode_twos_complement(-13)
    assert out["overflow_flag"] == 0
    assert out["hex"] == "0xFFFFFFF3"
    assert out["bin"].endswith("11110011")


def test_encode_overflow_high():
    # 2^31 does not fit in signed 32-bit, overflow=1
    out = encode_twos_complement(1 << 31)
    assert out["overflow_flag"] == 1
    # Still wraps to 0x80000000 because we store 32 bits
    assert out["hex"] == "0x80000000"


# Decode tests
def test_decode_from_binary_string_positive():
    # Read +13 from a 32-bit string
    val = decode_twos_complement("00000000_00000000_00000000_00001101")["value"]
    assert val == 13


def test_decode_from_binary_string_negative():
    # Read -13 from a 32-bit string
    val = decode_twos_complement("11111111_11111111_11111111_11110011")["value"]
    assert val == -13


def test_decode_from_int_unsigned():
    # 0x80000000 is -2147483648 when read as signed two's complement
    val = decode_twos_complement(0x80000000)["value"]
    assert val == -2147483648


# Sign/Zero extend tests
def test_sign_extend_keep_positive():
    # 0x7B (01111011) sign-extended from 8 to 12 should fill with 0s
    b = u32_to_bits(0x7B)
    out = sign_extend(b, 8, 12)
    assert len(out) == 12
    # High 4 bits should be 0 for positive 8-bit value
    assert out[11] == 0 and out[10] == 0 and out[9] == 0 and out[8] == 0


def test_sign_extend_keep_negative():
    # 0xAB (10101011) is negative if read as 8-bit signed (MSB=1)
    b = u32_to_bits(0xAB)
    out = sign_extend(b, 8, 12)
    # High 4 bits should be 1 to keep the negative value
    assert out[11] == 1 and out[10] == 1 and out[9] == 1 and out[8] == 1


def test_zero_extend_simple():
    # Zero extend 0xAB from 8 to 12: high bits become 0
    b = u32_to_bits(0xAB)
    out = zero_extend(b, 8, 12)
    assert out[11] == 0 and out[10] == 0 and out[9] == 0 and out[8] == 0


# Error handling tests
def test_decode_bad_string_length():
    with pytest.raises(ValueError):
        decode_twos_complement("1010")  # too short


def test_decode_bad_int_range():
    with pytest.raises(ValueError):
        decode_twos_complement(0x1_0000_0000)  # out of 32-bit range


def test_sign_extend_bad_widths():
    b = [0] * 32
    with pytest.raises(ValueError):
        sign_extend(b, 0, 12)  # from_width must be >=1
    with pytest.raises(ValueError):
        sign_extend(b, 8, 4)  # to_width must be >= from_width


def test_zero_extend_bad_bits():
    bad = [0] * 31 + [2]  # not a 0/1 bit
    with pytest.raises(ValueError):
        zero_extend(bad, 8, 12)


# End of tests/unit/test_twos.py
