# src/midterm_440/numeric_core/shifter.py
"""Logical and arithmetic shifters implemented without ``<<``/``>>``.

Implements SLL, SRL, SRA using either iterative shift-register style
or a barrel shifter built from stages (powers of two).
"""

from typing import List


def _validate_bits_32(bits: List[int]) -> None:
    if not isinstance(bits, list):
        raise ValueError("bits must be a list")
    if len(bits) != 32:
        raise ValueError("bits must have length 32")
    for b in bits:
        if b not in (0, 1):
            raise ValueError("bits must contain only 0/1")


def _validate_shamt(shamt: int) -> int:
    if not isinstance(shamt, int):
        raise ValueError("shamt must be an int")
    if shamt < 0 or shamt > 31:
        raise ValueError("shamt must be in 0..31")
    return shamt


def _shift_left_by_k(src: List[int], k: int, fill: int = 0) -> List[int]:
    """LSB-first: out[i] = src[i-k] if i>=k else fill."""
    out = [0] * 32
    for i in range(32):
        if i >= k:
            out[i] = src[i - k]
        else:
            out[i] = fill
    return out


def _shift_right_by_k(src: List[int], k: int, fill: int = 0) -> List[int]:
    """LSB-first: out[i] = src[i+k] if i+k<32 else fill."""
    out = [0] * 32
    for i in range(32):
        j = i + k
        if j < 32:
            out[i] = src[j]
        else:
            out[i] = fill
    return out


def sll_bits(bits: List[int], shamt: int) -> List[int]:
    """Shift left logical by ``shamt`` (insert zeros on the right).

    :param List[int] bits: 32-bit list, LSB first.
    :param int shamt: Shift amount in [0, 31].
    :returns: New 32-bit list after SLL.
    :rtype: List[int]
    """
    _validate_bits_32(bits)
    k = _validate_shamt(shamt)

    # Barrel-style cascade: stages 1,2,4,8,16
    out = bits[:]
    stages = (1, 2, 4, 8, 16)
    for idx, stage in enumerate(stages):
        if (k >> idx) & 1:
            out = _shift_left_by_k(out, stage, fill=0)
    return out


def srl_bits(bits: List[int], shamt: int) -> List[int]:
    """Shift right logical by ``shamt`` (insert zeros on the left).

    :param List[int] bits: 32-bit list, LSB first.
    :param int shamt: Shift amount in [0, 31].
    :returns: New 32-bit list after SRL.
    :rtype: List[int]
    """
    _validate_bits_32(bits)
    k = _validate_shamt(shamt)

    out = bits[:]
    stages = (1, 2, 4, 8, 16)
    for idx, stage in enumerate(stages):
        if (k >> idx) & 1:
            out = _shift_right_by_k(out, stage, fill=0)
    return out


def sra_bits(bits: List[int], shamt: int) -> List[int]:
    """Shift right arithmetic by ``shamt`` (replicate original sign bit).

    :param List[int] bits: 32-bit list, LSB first.
    :param int shamt: Shift amount in [0, 31].
    :returns: New 32-bit list after SRA.
    :rtype: List[int]
    """
    _validate_bits_32(bits)
    k = _validate_shamt(shamt)

    sign = bits[31]  # original MSB (sign)
    out = bits[:]
    stages = (1, 2, 4, 8, 16)
    for idx, stage in enumerate(stages):
        if (k >> idx) & 1:
            out = _shift_right_by_k(out, stage, fill=sign)
    return out
