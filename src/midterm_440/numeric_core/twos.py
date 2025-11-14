# src/midterm_440/numeric_core/twos.py
"""Two's-complement tools for 32-bit values (RV32).

This file gives you simple helpers to work with signed 32-bit numbers.
You can turn a Python int into two's-complement bits and back.
You can also grow a smaller value to a bigger width by copying the sign
(sign-extend) or by adding zeros (zero-extend).

Reminder about overflow in two's-complement math:
- Overflow is about the sign being wrong, not about the carry bit.
- If you add two numbers with the same sign and the result flips sign,
  that means overflow.
Example: 0x7FFFFFFF + 1 → 0x80000000 has signed overflow.
"""
# to run test, use:
# poetry run pytest -q tests\unit\test_twos.py
# to run all tests, use:
# poetry run pytest -q
from typing import Dict, List

from midterm_440.numeric_core.bits import (
    bits_to_u32,
    pretty_bin32,
    pretty_hex32,
    u32_to_bits,
)

# Signed 32-bit range (two's complement): -2^31 .. 2^31-1.
_INT32_MIN = -(1 << 31)
_INT32_MAX = (1 << 31) - 1
_MASK32 = 0xFFFF_FFFF


def _validate_bit_string_32(s: str) -> str:
    """Make sure we got a clean 32-bit '0'/'1' string. Underscores are ok.
    Returns the cleaned 32 characters (MSB..LSB).
    """
    if not isinstance(s, str):
        raise ValueError("bits_in must be a string or int")

    cleaned = s.replace("_", "").strip()
    if len(cleaned) != 32 or any(ch not in "01" for ch in cleaned):
        raise ValueError("binary string must be 32 characters of '0'/'1'")
    return cleaned


def encode_twos_complement(value: int) -> Dict[str, object]:
    """Turn a Python int into a 32-bit two's-complement pattern.

    :param int value: The number you want to encode (can be negative).
    :returns: A dictionary with:
              ``bin`` (str): 32 bits grouped like ``00000000_...``;
              ``hex`` (str): hex string like ``0x0000000D``;
              ``overflow_flag`` (int): 1 if value is outside -2^31..2^31-1.
    :rtype: Dict[str, object]

    Example: value = -13 → bin looks like 1111...0011, hex=0xFFFFFFF3.

    To get the two's-complement representation of a negative number (for an N-bit word):

    Write the absolute value in binary using N bits (pad with leading zeros).

    Flip every bit (0 → 1, 1 → 0).

    Add 1 to the flipped result (ignore any carry beyond N bits).

    Example: represent -5 in 8 bits.
    +5 in 8 bits = 00000101.
    Flip bits → 11111010.
    Add 1 → 11111011 (this is -5 in 8-bit two's-complement).

    """
    if not isinstance(value, int):
        raise ValueError("value must be an int")
    # Check for overflow (out of signed 32-bit range).
    overflow = 0 if (_INT32_MIN <= value <= _INT32_MAX) else 1
    # Wrap into 32 bits using bitwise AND with mask.
    unsigned = value & _MASK32  # wrap into 32 bits (what hardware does)
    # Convert an unsigned 32-bit integer to a 32-length bit list (LSB first).
    bits = u32_to_bits(unsigned)
    # pretty_bin32 Return a grouped binary string like 00000000_00000000_00000000_00000000.
    # pretty_hex32 Return a hex string like 0x00000000.
    # Return both representations and the overflow flag.
    return {
        "bin": pretty_bin32(bits),
        "hex": pretty_hex32(bits),
        "overflow_flag": overflow,
    }


def decode_twos_complement(bits_in: object) -> Dict[str, int]:
    """Read a 32-bit pattern and return the signed value.

    :param object bits_in: A 32-char '0'/'1' string (underscores ok)
                           or an unsigned 32-bit integer.
    :returns: ``{'value': int}`` in [-2**31, 2**31-1].
    :rtype: Dict[str, int]

    Tip: If the top bit (bit 31) is 1, the number is negative.
    """
    if isinstance(bits_in, str):
        cleaned = _validate_bit_string_32(bits_in)
        # We store lists LSB-first, but strings are MSB-first. Flip it.
        bits = [1 if cleaned[31 - i] == "1" else 0 for i in range(32)]
        u = bits_to_u32(bits)
    elif isinstance(bits_in, int):
        if bits_in < 0 or bits_in > _MASK32:
            raise ValueError("integer input must be in 0..0xFFFFFFFF")
        u = bits_in
    else:
        raise ValueError("bits_in must be a 32-bit binary string or unsigned int")

    # Two's-complement read: if sign bit is 1, subtract 2^32.
    value = u if (u & (1 << 31)) == 0 else (u - (1 << 32))
    return {"value": value}


def sign_extend(bits: List[int], from_width: int, to_width: int) -> List[int]:
    """Grow a value by copying its sign bit.

    :param List[int] bits: Bits are LSB first (bits[0] is the rightmost bit).
    :param int from_width: How many low bits are the “real” value now.
    :param int to_width: New width (must be >= from_width).
    :returns: New list with length ``to_width``.

    Why this works: in two's complement, repeating the top bit keeps the value.
    (If sign=1, we fill with 1s; if sign=0, we fill with 0s.)
    """
    if not isinstance(bits, list) or any(b not in (0, 1) for b in bits):
        raise ValueError("bits must be a list of 0/1")
    if not (1 <= from_width <= len(bits)):
        raise ValueError("from_width must be in 1..len(bits)")
    if to_width < from_width:
        raise ValueError("to_width must be >= from_width")

    sign = bits[from_width - 1]  # the current top bit (the sign)
    out = bits[:from_width] + [sign] * (to_width - from_width)
    return out[:to_width]


def zero_extend(bits: List[int], from_width: int, to_width: int) -> List[int]:
    """Grow a value by adding zeros on the left.

    :param List[int] bits: Bits are LSB first (bits[0] is the rightmost bit).
    :param int from_width: How many low bits are the “real” value now.
    :param int to_width: New width (must be >= from_width).
    :returns: New list with length ``to_width``.

    Use this when you want an unsigned view or you know the value is non-negative.
    """
    if not isinstance(bits, list) or any(b not in (0, 1) for b in bits):
        raise ValueError("bits must be a list of 0/1")
    if not (1 <= from_width <= len(bits)):
        raise ValueError("from_width must be in 1..len(bits)")
    if to_width < from_width:
        raise ValueError("to_width must be >= from_width")

    out = bits[:from_width] + [0] * (to_width - from_width)
    return out[:to_width]


def main() -> int:
    """Small demo so you can run this file directly.

    This only runs when you execute the module as a script,
    not when you import it in other code.
    """
    # From the Midterm Alternative Project.
    print(encode_twos_complement(13))
    print(encode_twos_complement(-13))
    print(decode_twos_complement("00000000_00000000_00000000_00001101"))
    print(decode_twos_complement("11111111_11111111_11111111_11110011"))
    b = u32_to_bits(0xAB)
    print(sign_extend(b, 8, 12))
    print(zero_extend(b, 8, 12))
    return 0


if __name__ == "__main__":
    # This makes sure main() only runs when this file is executed directly,
    # not when it is imported as a module.
    raise SystemExit(main())
