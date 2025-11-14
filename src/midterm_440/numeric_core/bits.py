# src/midterm_440/numeric_core/bits.py
"""Bit-array utilities for the Midterm Numeric Ops Simulator.

This module defines helpers for representing unsigned 32-bit values as
lists of bits (least significant bit first) and for pretty-printing.

This reduces bugs and makes tests readable.

.. important::
   To keep implementation tractable, this module permits bitwise reads
   (``&``, ``>>``) solely for conversion/formatting. Core arithmetic
   (ALU/MDU/FPU) must still avoid host arithmetic/shift ops as required.
"""

from typing import List

_HEX_DIGITS = "0123456789ABCDEF"
_NIBBLE_TO_HEX = {
    (0, 0, 0, 0): "0",
    (0, 0, 0, 1): "1",
    (0, 0, 1, 0): "2",
    (0, 0, 1, 1): "3",
    (0, 1, 0, 0): "4",
    (0, 1, 0, 1): "5",
    (0, 1, 1, 0): "6",
    (0, 1, 1, 1): "7",
    (1, 0, 0, 0): "8",
    (1, 0, 0, 1): "9",
    (1, 0, 1, 0): "A",
    (1, 0, 1, 1): "B",
    (1, 1, 0, 0): "C",
    (1, 1, 0, 1): "D",
    (1, 1, 1, 0): "E",
    (1, 1, 1, 1): "F",
}


def _validate_bits_32(bits: List[int]) -> None:
    """Internal: ensure a 32-length 0/1 list (LSB first).

    :param List[int] bits: Candidate bit list.
    :raises ValueError: If malformed.
    """
    if not isinstance(bits, list):
        raise ValueError("bits must be a list")
    if len(bits) != 32:
        raise ValueError("bits must contain exactly 32 elements")
    for b in bits:
        if b not in (0, 1):
            raise ValueError("bits must contain only 0 or 1")


def u32_to_bits(value: int) -> List[int]:
    """Convert an unsigned 32-bit integer to a 32-length bit list (LSB first).

    :param int value: Unsigned integer expected in range ``[0, 2**32-1]``.
    :returns: Bit list ``bits[0]`` = LSB, ``bits[31]`` = MSB.
    :rtype: List[int]
    :raises ValueError: If value is outside 32-bit unsigned range.
    """
    if not isinstance(value, int):
        raise ValueError("value must be an int")
    if value < 0 or value > 0xFFFF_FFFF:
        raise ValueError("value must be in 0..0xFFFFFFFF")

    bits = [0] * 32
    # Extract bits with right-shift & 1 (LSB first).
    for i in range(32):
        bits[i] = (value >> i) & 1
    return bits


def bits_to_u32(bits: List[int]) -> int:
    """Convert a 32-length bit list (LSB first) to an unsigned 32-bit integer.

    :param List[int] bits: Exactly 32 elements, each 0 or 1.
    :returns: Unsigned 32-bit integer.
    :rtype: int
    :raises ValueError: If length != 32 or elements are not 0/1.
    """
    _validate_bits_32(bits)
    value = 0
    # Reconstruct integer: sum (bit << position).
    for i in range(32):
        if bits[i]:
            value |= 1 << i
    return value


def pretty_bin32(bits: List[int]) -> str:
    """Return a grouped binary string like ``00000000_00000000_00000000_00000000``.

    Bytes are grouped from MSB to LSB, separated by underscores,
    with each byte printed MSB-first inside the group.

    :param List[int] bits: 32-bit list, LSB first.
    :returns: Human-friendly grouped binary string.
    :rtype: str
    """
    _validate_bits_32(bits)
    # Convert to MSB-first string of '0'/'1'.
    msb_first = "".join("1" if b else "0" for b in reversed(bits))
    # Group into bytes from left (MSB) to right.
    groups = [msb_first[i : i + 8] for i in range(0, 32, 8)]
    return "_".join(groups)


def pretty_hex32(bits: List[int]) -> str:
    """Return a zero-padded hex string like ``0xDEADBEEF`` (manual nibbles).

    :param List[int] bits: 32-bit list, LSB first.
    :returns: Hex string with prefix ``0x``.
    :rtype: str
    """
    _validate_bits_32(bits)
    # Build hex a nibble at a time from MSB to LSB (each nibble is 4 bits).
    # Reversed for MSB-first processing.
    msb_first = list(reversed(bits))
    hex_chars: List[str] = []
    for i in range(0, 32, 4):
        n4 = tuple(int(c) for c in msb_first[i : i + 4])
        if len(n4) != 4:
            raise ValueError("internal error: nibble length != 4")
        hex_chars.append(_NIBBLE_TO_HEX[n4])
    return "0x" + "".join(hex_chars)


# --- helper main for manual run ---
def main() -> int:
    """Small demo you can run by executing this file directly."""
    from midterm_440.numeric_core.bits import (
        bits_to_u32,
        pretty_bin32,
        pretty_hex32,
        u32_to_bits,
    )

    b = u32_to_bits(0xDEADBEEF)
    print(pretty_bin32(b))
    print(pretty_hex32(b))
    print(hex(bits_to_u32(b)))
    return 0


if __name__ == "__main__":
    # Make sure the 'src' folder is on sys.path when running this file directly.
    # This keeps imports working with the src/ layout.

    # Put the repo's single 'src' folder on sys.path so imports work when
    # you run this file directly (outside pytest).
    import sys
    from pathlib import Path

    here = Path(__file__).resolve()  # tests/unit/test_twos.py
    project_root = here.parents[2]  # -> .../midterm_440
    src_dir = project_root / "src"  # -> .../midterm_440/src

    # Sanity: avoid src/src mistakes
    if src_dir.name == "src" and src_dir.exists():
        sys.path.insert(0, str(src_dir))

    raise SystemExit(main())
