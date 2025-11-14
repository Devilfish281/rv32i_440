# src/midterm_440/numeric_core/alu.py
"""Ripple-carry ALU for ADD/SUB with flags N,Z,C,V (RV32).

The ALU operates on 32-bit bit arrays (LSB first) using 1-bit full adders.
No host ``+``/``-`` or shifts are used in the final implementation.

Overflow (V) rules (two's complement):
- ADD: overflow iff operands share sign and result sign differs.
- SUB: implement as ``a + (~b + 1)`` and apply ADD rule.

Flags:
- N: msb(result)
- Z: 1 if all result bits are 0
- C: carry out of MSB (for subtraction via a + (~b + 1), C=1 implies no borrow)
- V: signed overflow as above
"""

from typing import Dict, List, Tuple, Union  # Changed Code


def _validate_bits_32(a: List[int], b: List[int]) -> None:
    """Quick checks: lists, 32 bits, only 0/1."""
    if not (isinstance(a, list) and isinstance(b, list)):
        raise ValueError("a and b must be lists")
    if len(a) != 32 or len(b) != 32:
        raise ValueError("a and b must be 32 bits long")
    for x in a + b:
        if x not in (0, 1):
            raise ValueError("bits must be 0/1")


def _add_bits_with_cin(
    a: List[int], b: List[int], cin0: int, *, trace: bool = False
) -> Union[Tuple[List[int], int, int, int, int], Dict[str, object]]:
    """Full-adder ripple with selectable initial carry-in (0 or 1).

    If trace=True, returns a dict with fields: sum_bits, N,Z,C,V, and a 'trace' list.
    Otherwise, returns the historical 5-tuple (sum_bits, N, Z, C, V).
    """
    _validate_bits_32(a, b)
    out = [0] * 32
    cin = cin0
    carry_into_msb = 0
    carry_out_msb = 0  #  Changed Code
    steps: List[dict] = [] if trace else None  #  Changed Code

    if trace:  #  Changed Code
        steps.append(  #  Changed Code
            {  #  Changed Code
                "phase": "start",  #  Changed Code
                "a_hex": f"0x{sum(bit << i for i, bit in enumerate(a)):08X}",  #  Changed Code
                "b_hex": f"0x{sum(bit << i for i, bit in enumerate(b)):08X}",  #  Changed Code
                "cin": int(cin0),  #  Changed Code
            }  #  Changed Code
        )  #  Changed Code

    for i in range(32):
        ai = a[i]
        bi = b[i]
        axb = ai ^ bi  # a XOR b
        s = axb ^ cin  # sum = a XOR b XOR cin
        cout = (ai & bi) | (cin & axb)  # cout = a·b OR cin·(a XOR b)
        out[i] = s
        if i == 31:  # capture carries around MSB for V
            carry_into_msb = cin
            carry_out_msb = cout
        if trace:  #  Changed Code
            steps.append(  #  Changed Code
                {  #  Changed Code
                    "phase": "iter",  #  Changed Code
                    "bit": i,  #  Changed Code
                    "ai": int(ai),  #  Changed Code
                    "bi": int(bi),  #  Changed Code
                    "cin": int(cin),  #  Changed Code
                    "sum_bit": int(s),  #  Changed Code
                    "cout": int(cout),  #  Changed Code
                }  #  Changed Code
            )  #  Changed Code
        cin = cout  # ripple

    N = out[31]
    Z = 1 if all(bit == 0 for bit in out) else 0
    C = cin
    V = 1 if carry_into_msb != carry_out_msb else 0

    if not trace:  #  Changed Code
        return out, N, Z, C, V  # historical tuple  #  Changed Code

    # traced return payload  #  Changed Code
    steps.append(  #  Changed Code
        {  #  Changed Code
            "phase": "finish",  #  Changed Code
            "result_hex": f"0x{sum(bit << i for i, bit in enumerate(out)):08X}",  #  Changed Code
            "N": int(N),  #  Changed Code
            "Z": int(Z),  #  Changed Code
            "C": int(C),  #  Changed Code
            "V": int(V),  #  Changed Code
        }  #  Changed Code
    )  #  Changed Code
    return {  #  Changed Code
        "sum_bits": out,  #  Changed Code
        "N": int(N),  #  Changed Code
        "Z": int(Z),  #  Changed Code
        "C": int(C),  #  Changed Code
        "V": int(V),  #  Changed Code
        "trace": steps,  #  Changed Code
    }  #  Changed Code


def add_bits(
    a: List[int], b: List[int], *, trace: bool = False
) -> Union[Tuple[List[int], int, int, int, int], Dict[str, object]]:
    """Add two 32-bit vectors using a ripple of 1-bit full adders.

    :param List[int] a: 32-bit list, LSB first.
    :param List[int] b: 32-bit list, LSB first.
    :param bool trace: If True, return a dict with a per-bit trace.
    :returns: (sum_bits, N, Z, C, V) or a dict when trace=True.
    """
    return _add_bits_with_cin(a, b, 0, trace=trace)  #  Changed Code


def _invert_bits(bits: List[int]) -> List[int]:
    """Bitwise NOT for 0/1 lists."""
    return [0 if b == 1 else 1 for b in bits]


def sub_bits(
    a: List[int], b: List[int], *, trace: bool = False
) -> Union[Tuple[List[int], int, int, int, int], Dict[str, object]]:
    """Subtract ``b`` from ``a`` via two's-complement addition.

    :param List[int] a: Minuend, 32-bit list, LSB first.
    :param List[int] b: Subtrahend, 32-bit list, LSB first.
    :param bool trace: If True, return a dict with a per-bit trace.
    :returns: (diff_bits, N, Z, C, V) or a dict when trace=True.

    Two's-complement subtraction is a single ripple: a + (~b) + 1.
    """
    _validate_bits_32(a, b)
    b_inv = _invert_bits(b)
    return _add_bits_with_cin(a, b_inv, 1, trace=trace)  #  Changed Code
