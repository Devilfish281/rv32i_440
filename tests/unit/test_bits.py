# tests/unit/test_bits.py
import pytest

from midterm_440.numeric_core.bits import (
    bits_to_u32,
    pretty_bin32,
    pretty_hex32,
    u32_to_bits,
)


class TestBits:
    def test_round_trip_zero(self):
        b = u32_to_bits(0)
        assert len(b) == 32 and all(x in (0, 1) for x in b)
        assert bits_to_u32(b) == 0

    def test_round_trip_max(self):
        val = 0xFFFF_FFFF
        b = u32_to_bits(val)
        assert bits_to_u32(b) == val

    def test_specific_value_deadbeef(self):
        val = 0xDEAD_BEEF
        b = u32_to_bits(val)
        # pretty_bin32 should show MSB-first bytes grouped with underscores
        bin_str = pretty_bin32(b)
        assert isinstance(bin_str, str) and len(bin_str.replace("_", "")) == 32
        # pretty_hex32 must round-trip to 0xDEADBEEF
        assert pretty_hex32(b) == "0xDEADBEEF"
        assert bits_to_u32(b) == val

    def test_invalid_range_negative(self):
        with pytest.raises(ValueError):
            u32_to_bits(-1)

    def test_invalid_range_too_large(self):
        with pytest.raises(ValueError):
            u32_to_bits(0x1_0000_0000)

    def test_bits_validation_length(self):
        with pytest.raises(ValueError):
            bits_to_u32([0, 1])  # too short

    def test_bits_validation_values(self):
        bad = [0] * 31 + [2]  # last element invalid
        with pytest.raises(ValueError):
            bits_to_u32(bad)

    def test_formatting_zero(self):
        b = u32_to_bits(0)
        assert pretty_hex32(b) == "0x00000000"
        assert pretty_bin32(b) == "00000000_00000000_00000000_00000000"
