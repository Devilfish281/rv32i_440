# rv32i_440.py
"""
Tiny RV32I teaching core with structured logging.

Sphinx:
    This module is prepared for Sphinx autodoc; the header note helps Sphinx
    index the file when using the autodoc extension.
"""

import logging
import os
import sys

from midterm_440.numeric_core.interfaces import (
    add_bits,
    bits_to_u32,
    decode_twos_complement,
    div_restoring,
    encode_twos_complement,
    mul_shift_add,
    sll_bits,
    sra_bits,
    srl_bits,
    sub_bits,
    u32_to_bits,
)
from rv32i_440.alu_adapter import alu_exec
from utilities.load_env import (
    is_register_dump_enabled,
    load_environment,
    read_log_level,
)
from utilities.logger_setup import setup_logger

MASK32 = 0xFFFF_FFFF


def _shift_helper(kind: str, value: int, shamt: int) -> int:
    """Use bit-level shifter from numeric_core for one instruction."""
    bits = u32_to_bits(value & MASK32)
    if kind == "SLL":
        out_bits = sll_bits(bits, shamt)
    elif kind == "SRL":
        out_bits = srl_bits(bits, shamt)
    elif kind == "SRA":
        out_bits = sra_bits(bits, shamt)
    else:
        raise ValueError(f"Unknown shift kind: {kind}")
    return bits_to_u32(out_bits) & MASK32


def _mdu_exec(op: str, rs1: int, rs2: int, *, trace: bool = False) -> dict:
    """Small adapter for MUL/DIV/REM ops using numeric_core.mdu."""
    rs1_u = rs1 & MASK32
    rs2_u = rs2 & MASK32
    a_bits = u32_to_bits(rs1_u)
    b_bits = u32_to_bits(rs2_u)
    if op == "MUL":
        core_out = mul_shift_add(a_bits, b_bits, trace=trace)
        rd_bits = core_out["rd_bits"]
        rd_u = bits_to_u32(rd_bits) & MASK32
        return {
            "rd": rd_u,
            "flags": {"overflow": int(core_out.get("overflow", 0))},
            "trace": core_out.get("trace", []),
        }
    elif op in ("DIV", "DIVU", "REM", "REMU"):
        signed = op in ("DIV", "REM")
        core_out = div_restoring(a_bits, b_bits, signed=signed, trace=trace)
        q_bits = core_out["q_bits"]
        r_bits = core_out["r_bits"]
        if op in ("DIV", "DIVU"):
            rd_bits = q_bits
        else:
            rd_bits = r_bits
        rd_u = bits_to_u32(rd_bits) & MASK32
        flags = core_out.get("flags", {})
        flags = {
            "div_by_zero": int(flags.get("div_by_zero", 0)),
            "overflow": int(flags.get("overflow", 0)),
        }
        return {
            "rd": rd_u,
            "flags": flags,
            "trace": core_out.get("trace", []),
        }
    else:
        raise ValueError(f"Unsupported MDU op: {op!r}")


def u32(x):
    """
    Zero-extend an integer to 32 bits (wrap around like a 32-bit register).

    :param int x: Input integer.
    :return: x modulo 2^32.
    :rtype: int
    """
    return x & MASK32


def get_bits(x, hi, lo):
    """
    Extract a bit slice [hi:lo] (inclusive) from an integer.

    :param int x: Source integer.
    :param int hi: High bit index (0-based, inclusive).
    :param int lo: Low bit index (0-based, inclusive).
    :return: The extracted bitfield as a non-negative integer.
    :rtype: int
    """
    return (x >> lo) & ((1 << (hi - lo + 1)) - 1)


def sext(val, bits):
    """
    Sign-extend a value that is `bits` wide to Python int.

    :param int val: Raw (possibly wider) integer value.
    :param int bits: Bit width of the value to interpret.
    :return: Sign-extended integer.
    :rtype: int
    """
    sign = 1 << (bits - 1)
    val &= (1 << bits) - 1
    return val - (1 << bits) if (val & sign) else val


def imm_i(instr):
    """
    Decode I-type immediate (bits [31:20], sign-extended).

    :param int instr: 32-bit instruction word.
    :return: Sign-extended 12-bit immediate.
    :rtype: int
    """
    return sext(get_bits(instr, 31, 20), 12)


def imm_s(instr):
    """
    Decode S-type immediate from bits [31:25] and [11:7], sign-extended.

    :param int instr: 32-bit instruction word.
    :return: Sign-extended 12-bit immediate.
    :rtype: int
    """
    raw = (get_bits(instr, 31, 25) << 5) | get_bits(instr, 11, 7)
    return sext(raw, 12)


def imm_b(instr):
    """
    Decode B-type branch immediate (assembled from scattered fields), sign-extended.

    :param int instr: 32-bit instruction word.
    :return: Sign-extended 13-bit branch offset (byte addressing).
    :rtype: int
    """
    raw = (
        (get_bits(instr, 31, 31) << 12)
        | (get_bits(instr, 30, 25) << 5)
        | (get_bits(instr, 11, 8) << 1)
        | (get_bits(instr, 7, 7) << 11)
    )
    return sext(raw, 13)


def imm_j(instr):
    """
    Decode J-type jump immediate (assembled from scattered fields), sign-extended.

    :param int instr: 32-bit instruction word.
    :return: Sign-extended 21-bit jump offset (byte addressing).
    :rtype: int
    """
    raw = (
        (get_bits(instr, 31, 31) << 20)
        | (get_bits(instr, 30, 21) << 1)
        | (get_bits(instr, 20, 20) << 11)
        | (get_bits(instr, 19, 12) << 12)
    )
    return sext(raw, 21)


def imm_u(instr):
    """U-type immediate: bits[31:12] << 12 (no sign-extension).

    :param int instr: 32-bit instruction word.
    :return: Upper 20 bits shifted into position as a 32-bit value.
    :rtype: int
    """
    return get_bits(instr, 31, 12) << 12


class TinyCPU:
    """
    Minimal RV32I teaching CPU.

    Features:
        - 32 integer registers (x0 hard-wired to 0)
        - PC, instruction memory (imem), data memory (dmem)
        - Small subset of RV32I: ADDI, ADD, SUB, LW, SW, BEQ, JAL, LUI
        - Structured logging for fetch/decode/execute steps

    Usage:
        Instantiate, load program with :meth:`load_hex_lines`, then run with :meth:`run`.
    """

    def __init__(self):
        """
        Initialize CPU state.

        :ivar list[int] x: Register file (32 x 32-bit).
        :ivar int pc: Program counter (byte address).
        :ivar dict[int,int] imem: Instruction memory map (addr -> word).
        :ivar dict[int,int] dmem: Data memory map (addr -> word).
        :ivar list[tuple[int,int]] trace: Execution trace (pc, instr).
        :ivar logging.Logger logger: Module/class logger.
        """
        self.x = [0] * 32
        self.pc = 0
        self.imem = {}
        self.dmem = {}
        self.trace = []
        self.logger = logging.getLogger(__name__)

    def regs_dump(self, note: str = "") -> None:
        """Log all 32 registers if env toggle is enabled; otherwise do nothing."""
        if not is_register_dump_enabled():
            return
        hdr = f"=== REG DUMP {note} ===".strip()
        self.logger.debug(hdr)
        for i in range(32):
            v = self.x[i]
            s = v if v < 0x8000_0000 else v - (1 << 32)
            self.logger.debug("x%02d = 0x%08X (%11d)", i, v, s)

    def load_hex_lines(self, lines, base_pc=0):
        """
        Load a sequence of 8-hex-digit strings into instruction memory.

        Each non-empty, non-comment line is parsed as a 32-bit instruction
        and stored at addresses base_pc, base_pc+4, ...

        :param list[str] lines: Lines of hex words (e.g., ``"0000006F"``).
        :param int base_pc: Start address for the first instruction.
        :return: None
        :rtype: None
        """
        a = base_pc
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            self.imem[a] = int(s, 16)
            self.logger.debug("IMEM[0x%08X] <- 0x%08X", a, self.imem[a])
            a += 4

    def load_hex_file(self, path: str, base_pc: int = 0) -> None:
        """Load a prog.hex-style file from disk into instruction memory."""
        self.logger.info("Loading program from %s", path)
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.load_hex_lines(lines, base_pc=base_pc)

    def fetch(self):
        """
        Fetch the 32-bit instruction at the current PC.

        :return: The instruction word (0 if address unmapped).
        :rtype: int
        """
        instr = self.imem.get(self.pc, 0)
        self.logger.debug("FETCH pc=0x%08X instr=0x%08X", self.pc, instr)
        return instr

    def step(self):
        """
        Execute one instruction at the current PC.

        Decodes the instruction, executes it (if supported), advances the PC,
        and appends (pc, instr) to the execution trace.

        :return: ``True`` if CPU should continue; ``False`` if halted.
        :rtype: bool
        :raises ValueError: On unaligned LW/SW access.
        """
        instr = self.fetch()
        opcode = instr & 0x7F
        rd = get_bits(instr, 11, 7)
        funct3 = get_bits(instr, 14, 12)
        rs1 = get_bits(instr, 19, 15)
        rs2 = get_bits(instr, 24, 20)
        funct7 = get_bits(instr, 31, 25)
        next_pc = u32(self.pc + 4)

        def X(i):
            """
            Read a register (x0 is always 0).

            :param int i: Register index (0..31).
            :return: Register value (32-bit).
            :rtype: int
            """
            return self.x[i] if i != 0 else 0

        def WR(v):
            """
            Write-back to destination register `rd` if rd != 0.

            :param int v: Value to write (will be masked to 32-bit).
            :return: None
            :rtype: None
            """
            if rd != 0:
                self.x[rd] = u32(v)
                self.logger.debug("x%02d <- 0x%08X", rd, self.x[rd])

        handled = False

        if opcode == 0x13:
            if funct3 == 0x0:
                self.logger.debug("ADDI x%d, x%d, %d", rd, rs1, imm_i(instr))
                self.regs_dump("before ADDI")
                WR(X(rs1) + imm_i(instr))
                self.regs_dump("after ADDI")
                handled = True
            elif funct3 == 0x1:
                shamt = get_bits(instr, 24, 20)
                self.logger.debug("SLLI x%d, x%d, %d", rd, rs1, shamt)
                self.regs_dump("before SLLI")
                res = _shift_helper("SLL", X(rs1), shamt)
                WR(res)
                self.regs_dump("after SLLI")
                handled = True
            elif funct3 == 0x5:
                shamt = get_bits(instr, 24, 20)
                if funct7 == 0x00:
                    self.logger.debug("SRLI x%d, x%d, %d", rd, rs1, shamt)
                    self.regs_dump("before SRLI")
                    res = _shift_helper("SRL", X(rs1), shamt)
                    WR(res)
                    self.regs_dump("after SRLI")
                    handled = True
                elif funct7 == 0x20:
                    self.logger.debug("SRAI x%d, x%d, %d", rd, rs1, shamt)
                    self.regs_dump("before SRAI")
                    res = _shift_helper("SRA", X(rs1), shamt)
                    WR(res)
                    self.regs_dump("after SRAI")
                    handled = True
            elif funct3 == 0x4:  # XORI
                imm = imm_i(instr)
                self.logger.debug("XORI x%d, x%d, %d", rd, rs1, imm)
                self.regs_dump("before XORI")
                WR(X(rs1) ^ imm)
                self.regs_dump("after XORI")
                handled = True
            elif funct3 == 0x6:  # ORI
                imm = imm_i(instr)
                self.logger.debug("ORI x%d, x%d, %d", rd, rs1, imm)
                self.regs_dump("before ORI")
                WR(X(rs1) | imm)
                self.regs_dump("after ORI")
                handled = True
            elif funct3 == 0x7:  # ANDI
                imm = imm_i(instr)
                self.logger.debug("ANDI x%d, x%d, %d", rd, rs1, imm)
                self.regs_dump("before ANDI")
                WR(X(rs1) & imm)
                self.regs_dump("after ANDI")
                handled = True

        elif opcode == 0x33:
            if funct7 == 0x01:
                if funct3 == 0x0:
                    self.logger.debug("MUL x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before MUL")
                    mdu_out = _mdu_exec("MUL", X(rs1), X(rs2), trace=True)
                    WR(mdu_out["rd"])
                    self.logger.debug(
                        "MUL overflow=%d",
                        mdu_out["flags"].get("overflow", 0),
                    )
                    self.regs_dump("after MUL")
                    handled = True
                elif funct3 == 0x4:
                    self.logger.debug("DIV x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before DIV")
                    mdu_out = _mdu_exec("DIV", X(rs1), X(rs2), trace=True)
                    WR(mdu_out["rd"])
                    self.logger.debug(
                        "DIV flags: div_by_zero=%d overflow=%d",
                        mdu_out["flags"].get("div_by_zero", 0),
                        mdu_out["flags"].get("overflow", 0),
                    )
                    self.regs_dump("after DIV")
                    handled = True
                elif funct3 == 0x5:
                    self.logger.debug("DIVU x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before DIVU")
                    mdu_out = _mdu_exec("DIVU", X(rs1), X(rs2), trace=True)
                    WR(mdu_out["rd"])
                    self.logger.debug(
                        "DIVU flags: div_by_zero=%d overflow=%d",
                        mdu_out["flags"].get("div_by_zero", 0),
                        mdu_out["flags"].get("overflow", 0),
                    )
                    self.regs_dump("after DIVU")
                    handled = True
                elif funct3 == 0x6:
                    self.logger.debug("REM x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before REM")
                    mdu_out = _mdu_exec("REM", X(rs1), X(rs2), trace=True)
                    WR(mdu_out["rd"])
                    self.logger.debug(
                        "REM flags: div_by_zero=%d overflow=%d",
                        mdu_out["flags"].get("div_by_zero", 0),
                        mdu_out["flags"].get("overflow", 0),
                    )
                    self.regs_dump("after REM")
                    handled = True
                elif funct3 == 0x7:
                    self.logger.debug("REMU x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before REMU")
                    mdu_out = _mdu_exec("REMU", X(rs1), X(rs2), trace=True)
                    WR(mdu_out["rd"])
                    self.logger.debug(
                        "REMU flags: div_by_zero=%d overflow=%d",
                        mdu_out["flags"].get("div_by_zero", 0),
                        mdu_out["flags"].get("overflow", 0),
                    )
                    self.regs_dump("after REMU")
                    handled = True
            else:
                if funct3 == 0x0 and funct7 == 0x00:
                    self.logger.debug("ADD x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before ADD")
                    alu_out = alu_exec("ADD", X(rs1), X(rs2), trace=True)
                    WR(alu_out["rd"])
                    self.logger.debug(
                        "ADD flags: N=%d Z=%d C=%d V=%d",
                        alu_out["flags"]["N"],
                        alu_out["flags"]["Z"],
                        alu_out["flags"]["C"],
                        alu_out["flags"]["V"],
                    )
                    self.regs_dump("after ADD")
                    handled = True
                elif funct3 == 0x0 and funct7 == 0x20:
                    self.logger.debug("SUB x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before SUB")
                    alu_out = alu_exec("SUB", X(rs1), X(rs2), trace=True)
                    WR(alu_out["rd"])
                    self.logger.debug(
                        "SUB flags: N=%d Z=%d C=%d V=%d",
                        alu_out["flags"]["N"],
                        alu_out["flags"]["Z"],
                        alu_out["flags"]["C"],
                        alu_out["flags"]["V"],
                    )
                    self.regs_dump("after SUB")
                    handled = True
                elif funct3 == 0x1 and funct7 == 0x00:  # SLL (R-type)
                    shamt = X(rs2) & 0x1F
                    self.logger.debug(
                        "SLL x%d, x%d, x%d (shamt=%d)",
                        rd,
                        rs1,
                        rs2,
                        shamt,
                    )
                    self.regs_dump("before SLL")
                    res = _shift_helper("SLL", X(rs1), shamt)
                    WR(res)
                    self.regs_dump("after SLL")
                    handled = True
                elif funct3 == 0x5 and funct7 == 0x00:  # SRL (R-type)
                    shamt = X(rs2) & 0x1F
                    self.logger.debug(
                        "SRL x%d, x%d, x%d (shamt=%d)",
                        rd,
                        rs1,
                        rs2,
                        shamt,
                    )
                    self.regs_dump("before SRL")
                    res = _shift_helper("SRL", X(rs1), shamt)
                    WR(res)
                    self.regs_dump("after SRL")
                    handled = True
                elif funct3 == 0x5 and funct7 == 0x20:  # SRA (R-type)
                    shamt = X(rs2) & 0x1F
                    self.logger.debug(
                        "SRA x%d, x%d, x%d (shamt=%d)",
                        rd,
                        rs1,
                        rs2,
                        shamt,
                    )
                    self.regs_dump("before SRA")
                    res = _shift_helper("SRA", X(rs1), shamt)
                    WR(res)
                    self.regs_dump("after SRA")
                    handled = True
                elif funct3 == 0x4 and funct7 == 0x00:
                    self.logger.debug("XOR x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before XOR")
                    WR(X(rs1) ^ X(rs2))
                    self.regs_dump("after XOR")
                    handled = True
                elif funct3 == 0x6 and funct7 == 0x00:
                    self.logger.debug("OR x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before OR")
                    WR(X(rs1) | X(rs2))
                    self.regs_dump("after OR")
                    handled = True
                elif funct3 == 0x7 and funct7 == 0x00:
                    self.logger.debug("AND x%d, x%d, x%d", rd, rs1, rs2)
                    self.regs_dump("before AND")
                    WR(X(rs1) & X(rs2))
                    self.regs_dump("after AND")
                    handled = True

        elif opcode == 0x03:
            if funct3 == 0x2:
                addr = u32(X(rs1) + imm_i(instr))
                self.logger.debug(
                    "LW x%d, %d(x%d) -> addr=0x%08X", rd, imm_i(instr), rs1, addr
                )
                if addr % 4 != 0:
                    raise ValueError("Unaligned LW")
                self.regs_dump("before LW")
                WR(self.dmem.get(addr, 0))
                self.regs_dump("after LW")
                handled = True
        elif opcode == 0x23:
            if funct3 == 0x2:
                addr = u32(X(rs1) + imm_s(instr))
                self.logger.debug(
                    "SW x%d -> %d(x%d) addr=0x%08X", rs2, imm_s(instr), rs1, addr
                )
                if addr % 4 != 0:
                    raise ValueError("Unaligned SW")
                self.dmem[addr] = u32(X(rs2))
                handled = True

        elif opcode == 0x63:
            if funct3 == 0x0:
                self.logger.debug("BEQ x%d, x%d, offset=%d", rs1, rs2, imm_b(instr))
                if X(rs1) == X(rs2):
                    next_pc = u32(self.pc + imm_b(instr))
                handled = True
            elif funct3 == 0x1:  # BNE
                self.logger.debug("BNE x%d, x%d, offset=%d", rs1, rs2, imm_b(instr))
                if X(rs1) != X(rs2):
                    next_pc = u32(self.pc + imm_b(instr))
                handled = True

        elif opcode == 0x6F:
            self.logger.debug("JAL x%d, offset=%d", rd, imm_j(instr))
            WR(self.pc + 4)
            next_pc = u32(self.pc + imm_j(instr))
            handled = True

        elif opcode == 0x67:  # JALR
            if funct3 == 0x0:
                self.logger.debug("JALR x%d, x%d, offset=%d", rd, rs1, imm_i(instr))
                self.regs_dump("before JALR")
                t = self.pc + 4
                target = u32((X(rs1) + imm_i(instr)) & ~1)
                WR(t)
                next_pc = target
                self.regs_dump("after JALR")
                handled = True

        elif opcode == 0x17:  # AUIPC
            self.logger.debug("AUIPC x%d, 0x%05X", rd, get_bits(instr, 31, 12))
            self.regs_dump("before AUIPC")
            WR(u32(self.pc + imm_u(instr)))
            self.regs_dump("after AUIPC")
            handled = True

        elif opcode == 0x37:
            self.logger.debug("LUI x%d, 0x%05X", rd, get_bits(instr, 31, 12))
            self.regs_dump("before LUI")
            WR(imm_u(instr))
            self.regs_dump("after LUI")
            handled = True

        self.x[0] = 0

        if instr == 0x0000006F:
            self.pc = next_pc
            return False

        if not handled:
            self.logger.warning(
                "Unsupported/unknown opcode 0x%02X at pc=0x%08X (instr=0x%08X)",
                opcode,
                self.pc,
                instr,
            )

        self.trace.append((self.pc, instr))
        self.pc = next_pc
        return True

    def run(self, max_steps=10_000):
        """
        Run the CPU for up to `max_steps` instructions or until halted.

        :param int max_steps: Safety cap on the number of executed steps.
        :return: Number of executed steps.
        :rtype: int
        """
        steps = 0
        while steps < max_steps and self.step():
            steps += 1
        return steps


def _run_demo_program(logger: logging.Logger) -> None:
    """Fallback: run the built-in demo program if no prog.hex is found."""
    program = [
        "00500093",
        "00A00113",
        "002081B3",
        "40110233",
        "000102B7",
        "0032A023",
        "0002A203",
        "00418463",
        "00100313",
        "00200313",
        "0000006F",
    ]

    cpu = TinyCPU()
    cpu.load_hex_lines(program, base_pc=0)
    steps = cpu.run()

    logger.info("Steps: %d", steps)
    logger.info("PC:   0x%08X", cpu.pc)
    for i in [1, 2, 3, 4, 5, 6]:
        v = cpu.x[i]
        s = v if v < 0x8000_0000 else v - (1 << 32)
        logger.info("x%02d = 0x%08X (%d)", i, v, s)

    addr = 0x00010000
    mv = cpu.dmem.get(addr, 0)
    logger.info("mem[0x%08X] = 0x%08X (%d)", addr, mv, mv)


if __name__ == "__main__":

    log_level = read_log_level()
    setup_logger(level=log_level)

    load_environment()

    logger = logging.getLogger(__name__)
    logger.info("Starting TinyRV32I CPU")
    """
    What the whole snippet accomplishes

    Initialize: x1=5, x2=10.

    Compute: x3=15 (add), x4=5 (sub).

    Point x5 to data address 0x00010000 (LUI).

    Store x3 (15) to memory at [0x10000], then load it back into x4 → x4 becomes 15.

    Compare x3 and x4: they're equal, so BEQ …, 8 jumps ahead by 8 bytes, skipping the first ADDI x6,1 and landing on ADDI x6,2, so x6 ends as 2.

    JAL x0,0 loops to itself; your simulator treats that as “halt” (common teaching convention; architecturally it's just a self-jump).
    Courses at UW

   """

    if len(sys.argv) > 1:
        prog_path = sys.argv[1]
    else:
        prog_path = "prog.hex"

    if os.path.exists(prog_path):
        cpu = TinyCPU()
        cpu.load_hex_file(prog_path, base_pc=0)
        steps = cpu.run()

        logger.info("Program file: %s", prog_path)
        logger.info("Steps: %d", steps)
        logger.info("PC:   0x%08X", cpu.pc)
        for i in [1, 2, 3, 4, 5, 6]:
            v = cpu.x[i]
            s = v if v < 0x8000_0000 else v - (1 << 32)
            logger.info("x%02d = 0x%08X (%d)", i, v, s)

        addr = 0x00010000
        mv = cpu.dmem.get(addr, 0)
        logger.info("mem[0x%08X] = 0x%08X (%d)", addr, mv, mv)
    else:
        logger.warning("Program file %s not found; running built-in demo", prog_path)
        _run_demo_program(logger)
