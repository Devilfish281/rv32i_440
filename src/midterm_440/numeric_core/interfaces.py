# src/midterm_440/numeric_core/interfaces.py
"""Public API surface for the Midterm Numeric Core.

This thin layer centralizes import paths for the numeric core so the
later CPU project can integrate a stable, pure-functional interface.
"""

from typing import Any, Dict, List, Tuple

# Re-export selected functions for consumers.
# (Adjust as you implement.)
try:
    from .alu import add_bits, sub_bits
    from .bits import bits_to_u32, pretty_bin32, pretty_hex32, u32_to_bits
    from .fpu_f32 import fadd_f32, fmul_f32, fsub_f32, pack_f32, unpack_f32
    from .mdu import div_restoring, mul_shift_add
    from .shifter import sll_bits, sra_bits, srl_bits
    from .twos import (
        decode_twos_complement,
        encode_twos_complement,
        sign_extend,
        zero_extend,
    )
except Exception:
    # During early scaffolding, modules may be incomplete; that's OK.
    pass


def main() -> int:
    """Optional CLI entry point for manual smoke tests.

    :returns: Process exit code (0 success).
    :rtype: int
    """
    # Keep empty for now; populate later with a tiny demo that prints
    # pretty_hex32(predefined_bits) etc.
    return 0
