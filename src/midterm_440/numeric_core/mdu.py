# src/midterm_440/numeric_core/mdu.py
"""Multiply/Divide Unit (MDU) for RV32M using bit-level algorithms.

We do classic **shift-add** for MUL and **restoring division** for DIV.
Everything uses 0/1 lists (LSB first) and ripple-carry adders.

RISC-V DIV rules to cover in flags/edges (summarized):
- DIV/DIVU by zero => quotient all 1s (0xFFFFFFFF), remainder = dividend.
- Signed DIV of INT_MIN by -1 => quotient INT_MIN, remainder 0 (saturates).
These match the M extension semantics.
(See RISC-V M docs and guides.)
"""

from typing import Dict, List, Optional, Tuple  # Changed Code

# Reuse our ALU and shifter helpers so we stay pure bit-level.
from midterm_440.numeric_core.alu import add_bits, sub_bits
from midterm_440.numeric_core.bits import bits_to_u32, u32_to_bits
from midterm_440.numeric_core.shifter import sll_bits, srl_bits

# to run smoke tests, use:
# poetry run python tests\unit\smoke_mdu.py
# poetry run pytest -q tests\unit\test_mdu.py

MASK32 = 0xFFFF_FFFF
INT32_MIN = 0x80000000


# -------------------- small bit helpers --------------------
def _check32(bits: List[int]) -> None:
    if not isinstance(bits, list) or len(bits) != 32:
        raise ValueError("need 32 bits")
    for b in bits:
        if b not in (0, 1):
            raise ValueError("bits must be 0/1")


def _not_bits(bits: List[int]) -> List[int]:
    return [0 if b == 1 else 1 for b in bits]


def _add_n(a: List[int], b: List[int]) -> Tuple[List[int], int]:
    """Add same-length bit lists, return (sum_bits, carry_out)."""
    if len(a) != len(b):
        raise ValueError("lengths must match")
    out = [0] * len(a)
    cin = 0
    for i in range(len(a)):
        ai, bi = a[i], b[i]
        axb = ai ^ bi
        s = axb ^ cin
        cout = (ai & bi) | (cin & axb)
        out[i] = s
        cin = cout
    return out, cin


def _sub_n(a: List[int], b: List[int]) -> Tuple[List[int], int]:
    """Compute a - b as a + (~b + 1); returns (diff, borrow_flag_like)."""
    nb = _not_bits(b)
    tmp, cin = _add_n(a, nb)
    diff, cin2 = _add_n(tmp, [1] + [0] * (len(a) - 1))
    # For two's complement, final carry-out 1 => no borrow.
    borrow = 0 if cin2 == 1 else 1
    return diff, borrow


def _sll_n(bits: List[int], k: int) -> List[int]:
    out = bits[:]
    stages = (1, 2, 4, 8, 16, 32, 64)
    for idx, st in enumerate(stages):
        if (k >> idx) & 1:
            tmp = [0] * len(out)
            for i in range(len(out)):
                if i >= st:
                    tmp[i] = out[i - st]
            out = tmp
    return out


def _srl_n(bits: List[int], k: int, fill: int = 0) -> List[int]:
    out = bits[:]
    stages = (1, 2, 4, 8, 16, 32, 64)
    for idx, st in enumerate(stages):
        if (k >> idx) & 1:
            tmp = [fill] * len(out)
            for i in range(len(out)):
                j = i + st
                if j < len(out):
                    tmp[i] = out[j]
            out = tmp
    return out


def _sign_extend_to_64(x: List[int]) -> List[int]:
    sign = x[31]
    return x[:] + [sign] * 32


def _zero_extend_to_64(x: List[int]) -> List[int]:
    return x[:] + [0] * 32


def _twos_neg(bits: List[int]) -> List[int]:
    inv = _not_bits(bits)
    res, _ = _add_n(inv, [1] + [0] * (len(bits) - 1))
    return res


def _is_zero(bits: List[int]) -> bool:
    return all(b == 0 for b in bits)


# -------------------- MUL (shift-add) --------------------


def mul_shift_add(
    rs1_bits: List[int],
    rs2_bits: List[int],
    *,
    trace: bool = True,  # keep default to satisfy tests  #  Changed Code
) -> Dict[str, object]:
    """Signed 32×32 → low32 product using classic shift-add with optional trace.

    Trace shows step#, add?, acc_low32, acc_hi32, mul_bit.
    Overflow flag = 1 when the true 64-bit signed product doesn't fit in 32-bit signed.
    """
    _check32(rs1_bits)
    _check32(rs2_bits)
    trace_rows: Optional[List[dict]] = [] if trace else None  #  Changed Code

    # Make signed 64-bit versions so negatives work naturally via two's complement.
    a64 = _sign_extend_to_64(rs1_bits)
    b32 = rs2_bits[:]
    acc = [0] * 64

    # Loop over 32 bits of the multiplier (LSB first).
    for i in range(32):
        add_now = 1 if b32[i] == 1 else 0
        if add_now:
            addend = _sll_n(a64, i)
            acc, _ = _add_n(acc, addend)
        if trace:  #  Changed Code
            low32 = acc[:32]  #  Changed Code
            hi32 = acc[32:]  #  Changed Code
            trace_rows.append(  #  Changed Code
                {  #  Changed Code
                    "step": i,  #  Changed Code
                    "mul_bit": int(b32[i]),  #  Changed Code
                    "added": add_now,  #  Changed Code
                    "acc_low32_hex": f"0x{bits_to_u32(low32):08X}",  #  Changed Code
                    "acc_hi32_hex": f"0x{bits_to_u32(hi32):08X}",  #  Changed Code
                }  #  Changed Code
            )  #  Changed Code

    # Result low 32 bits is MUL rd.
    rd_bits = acc[:32]

    # Overflow check: does the full 64-bit signed product fit in 32-bit signed?
    sign32 = rd_bits[31]
    overflow = 0
    for j in range(32, 64):
        if acc[j] != sign32:
            overflow = 1
            break

    return {  #  Changed Code
        "rd_bits": rd_bits,
        "overflow": overflow,
        "trace": (
            trace_rows if trace else []
        ),  # exactly 32 rows when enabled  #  Changed Code
    }  #  Changed Code


# -------------------- DIV (restoring division) --------------------
def _cmp_unsigned(a: List[int], b: List[int]) -> int:
    """Compare same-length unsigned bit lists (MSB first compare)."""
    assert len(a) == len(b)
    for i in range(len(a) - 1, -1, -1):
        if a[i] != b[i]:
            return 1 if a[i] > b[i] else -1
    return 0


def _abs_sign(bits: List[int]) -> Tuple[List[int], int]:
    """Return (abs_bits, sign) for 32-bit two's complement input."""
    if bits[31] == 1:
        return _twos_neg(bits), 1
    else:
        return bits[:], 0


def _clip32(x: List[int]) -> List[int]:
    return x[:32]


def div_restoring(
    dividend_bits: List[int],
    divisor_bits: List[int],
    signed: bool = True,
    *,
    trace: bool = True,  # default True for parity with mul; safe for existing callers  #  Changed Code
) -> Dict[str, object]:
    """Binary restoring division with 32 iterations and an optional trace.

    - If signed=True: handle signs like RISC-V DIV/REM (quot trunc toward 0; rem same sign as dividend).
    - Edge cases: div-by-zero and INT_MIN/-1 per RISC-V M.
    """
    _check32(dividend_bits)
    _check32(divisor_bits)
    flags = {"div_by_zero": 0, "overflow": 0}
    trace_rows: Optional[List[dict]] = [] if trace else None  #  Changed Code

    if trace:  #  Changed Code
        trace_rows.append(  #  Changed Code
            {  #  Changed Code
                "phase": "start",  #  Changed Code
                "dividend_hex": f"0x{bits_to_u32(dividend_bits):08X}",  #  Changed Code
                "divisor_hex": f"0x{bits_to_u32(divisor_bits):08X}",  #  Changed Code
                "signed": bool(signed),  #  Changed Code
            }  #  Changed Code
        )  #  Changed Code

    # ---- Handle divide-by-zero per RISC-V M rules ----
    if _is_zero(divisor_bits):
        flags["div_by_zero"] = 1
        q_bits = [1] * 32  # 0xFFFFFFFF (quotient all ones)
        r_bits = dividend_bits[:]  # remainder = dividend
        if trace:  #  Changed Code
            trace_rows.append(  #  Changed Code
                {  #  Changed Code
                    "phase": "finish",  #  Changed Code
                    "note": "div-by-zero",  #  Changed Code
                    "q_hex": f"0x{bits_to_u32(q_bits):08X}",  #  Changed Code
                    "r_hex": f"0x{bits_to_u32(r_bits):08X}",  #  Changed Code
                }  #  Changed Code
            )  #  Changed Code
        return {
            "q_bits": q_bits,
            "r_bits": r_bits,
            "flags": flags,
            "trace": trace_rows if trace else [],  #  Changed Code
        }

    # Signed path: map to unsigned by taking absolute values, but remember signs.
    if signed:
        # INT_MIN / -1 special: quotient = INT_MIN, remainder = 0.
        if (
            bits_to_u32(dividend_bits) == INT32_MIN
            and bits_to_u32(divisor_bits) == MASK32
        ):
            q_bits = u32_to_bits(INT32_MIN)
            r_bits = u32_to_bits(0)
            flags["overflow"] = 1
            if trace:  #  Changed Code
                trace_rows.append(  #  Changed Code
                    {  #  Changed Code
                        "phase": "finish",  #  Changed Code
                        "note": "INT_MIN / -1 special",  #  Changed Code
                        "q_hex": f"0x{bits_to_u32(q_bits):08X}",  #  Changed Code
                        "r_hex": f"0x{bits_to_u32(r_bits):08X}",  #  Changed Code
                        "flags": dict(flags),  #  Changed Code
                    }  #  Changed Code
                )  #  Changed Code
            return {
                "q_bits": q_bits,
                "r_bits": r_bits,
                "flags": flags,
                "trace": trace_rows if trace else [],  #  Changed Code
            }
        dvd_abs, dvd_sign = _abs_sign(dividend_bits)
        dvs_abs, dvs_sign = _abs_sign(divisor_bits)
        q_sign = dvd_sign ^ dvs_sign
    else:  # unsigned mode
        dvd_abs, dvs_abs = dividend_bits[:], divisor_bits[:]
        q_sign = 0

    # ---- Restoring division (unsigned core) ----
    R = [0] * 33  # remainder (33b so it can go 'negative' during subtract)
    Q = dvd_abs[:]  # quotient register starts as dividend
    D = dvs_abs[:]  # divisor (32)
    D33 = D[:] + [0]  # width match for subtract with R

    for step in range(32):
        # (R,Q) <<= 1; bring in Q[31] to R[0]
        msb_q = Q[31]
        R = [msb_q] + R[:32]
        Q = [0] + Q[:31]
        # Try subtract: R' = R - D33
        R_try, borrow = _sub_n(R, D33)
        if R_try[32] == 1:  # negative -> restore, qb=0
            qb = 0
            # keep R as-is (restored)
        else:  # non-negative -> keep R', qb=1
            R = R_try
            qb = 1
        Q[0] = qb
        if trace:  #  Changed Code
            trace_rows.append(  #  Changed Code
                {  #  Changed Code
                    "phase": "iter",  #  Changed Code
                    "step": step,  #  Changed Code
                    "qb": qb,  #  Changed Code
                    "R_top_hex": f"0x{bits_to_u32(R[1:33]):08X}",  #  Changed Code
                    "Q_hex": f"0x{bits_to_u32(Q):08X}",  #  Changed Code
                }  #  Changed Code
            )  #  Changed Code

    q_bits_unsigned = Q
    r_bits_unsigned = R[0:32]

    # ---- Fix signs back for signed mode ----
    if signed and q_sign == 1:
        q_bits_unsigned = _twos_neg(q_bits_unsigned)
    if signed and (dividend_bits[31] == 1):  # remainder keeps dividend's sign
        if not _is_zero(r_bits_unsigned):
            r_bits_unsigned = _twos_neg(r_bits_unsigned)

    q_bits = _clip32(q_bits_unsigned)
    r_bits = _clip32(r_bits_unsigned)

    if trace:  #  Changed Code
        trace_rows.append(  #  Changed Code
            {  #  Changed Code
                "phase": "finish",  #  Changed Code
                "q_hex": f"0x{bits_to_u32(q_bits):08X}",  #  Changed Code
                "r_hex": f"0x{bits_to_u32(r_bits):08X}",  #  Changed Code
                "flags": dict(flags),  #  Changed Code
            }  #  Changed Code
        )  #  Changed Code

    return {
        "q_bits": q_bits,
        "r_bits": r_bits,
        "flags": flags,
        "trace": (
            trace_rows if trace else []
        ),  # always present, empty if disabled  #  Changed Code
    }
