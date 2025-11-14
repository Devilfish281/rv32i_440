# src/rv32i_440/alu_adapter.py

from midterm_440.numeric_core.interfaces import (
    add_bits,
    bits_to_u32,
    sub_bits,
    u32_to_bits,
)

MASK32 = 0xFFFF_FFFF


def alu_exec(op: str, rs1: int, rs2: int, *, trace: bool = False) -> dict:
    """Execute a simple ALU op using the midterm_440.numeric_core.

    :param op: "ADD" or "SUB" (RV32I-style mnemonics).
    :param rs1: 32-bit integer value from source register 1
                (Python int, will be masked to 0xFFFF_FFFF).
    :param rs2: 32-bit integer value from source register 2.
    :param trace: If True, request a per-bit trace from the numeric core.
    :returns: dict like:
              {
                  "rd": <32-bit result>,
                  "flags": {"N": int, "Z": int, "C": int, "V": int},
                  "trace": <list or None>,
              }
    """
    # Mask to 32 bits (simulate register wraparound)
    rs1_u = rs1 & MASK32
    rs2_u = rs2 & MASK32

    # Convert to bit-vectors for the numeric core
    a_bits = u32_to_bits(rs1_u)
    b_bits = u32_to_bits(rs2_u)

    # Call into the bit-level ALU
    if op == "ADD":
        core_out = add_bits(a_bits, b_bits, trace=trace)
    elif op == "SUB":
        core_out = sub_bits(a_bits, b_bits, trace=trace)
    else:
        raise ValueError(f"Unsupported ALU op for alu_exec: {op!r}")

    # Handle both tuple and traced-dict return types
    if isinstance(core_out, dict):
        sum_bits = core_out["sum_bits"]
        N = int(core_out["N"])
        Z = int(core_out["Z"])
        C = int(core_out["C"])
        V = int(core_out["V"])
        trace_out = core_out.get("trace", [])
    else:
        sum_bits, N, Z, C, V = core_out
        trace_out = None

    # Convert result bits back to a 32-bit int
    rd_u = bits_to_u32(sum_bits) & MASK32

    return {
        "rd": rd_u,
        "flags": {"N": N, "Z": Z, "C": C, "V": V},
        "trace": trace_out,
    }
