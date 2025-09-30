# rv32i_440.py
"""
Tiny RV32I teaching core with structured logging.

Sphinx:
    This module is prepared for Sphinx autodoc; the header note helps Sphinx
    index the file when using the autodoc extension.
"""

import logging
import os
from ast import If

from utilities.load_env import (
    is_register_dump_enabled,
    load_environment,
    read_log_level,
)
from utilities.logger_setup import setup_logger

MASK32 = 0xFFFF_FFFF


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

        # I-type: ADDI
        if opcode == 0x13:
            if funct3 == 0x0:
                self.logger.debug("ADDI x%d, x%d, %d", rd, rs1, imm_i(instr))
                self.regs_dump("before ADDI")
                WR(X(rs1) + imm_i(instr))
                self.regs_dump("after ADDI")
                handled = True

        # R-type: ADD/SUB
        elif opcode == 0x33:
            if funct3 == 0x0 and funct7 == 0x00:
                self.logger.debug("ADD x%d, x%d, x%d", rd, rs1, rs2)
                self.regs_dump("before ADD")
                WR(X(rs1) + X(rs2))
                self.regs_dump("after ADD")
                handled = True
            elif funct3 == 0x0 and funct7 == 0x20:  # SUB
                self.logger.debug("SUB x%d, x%d, x%d", rd, rs1, rs2)
                self.regs_dump("before SUB")
                WR(X(rs1) - X(rs2))
                self.regs_dump("after SUB")
                handled = True

        # Semantics: LW rd, imm(rs1)
        # Read a 32-bit word from memory at address rs1 + imm and write it to register rd.
        # Endianness: Little-endian (byte at lowest address is the least-significant byte of the word).
        # Alignment: Architecturally requires naturally aligned addresses (address % 4 == 0). Do not assume alignment and raise an exception.

        # Encoding (I-type)
        # opcode: 0000011₂ (0x03)
        # funct3: 010₂ (selects word)
        # rd: destination register
        # rs1: base register
        # imm[11:0]: 12-bit signed immediate (sign-extended)

        # Bit fields (31..0):
        # imm[11:0] (31:20) | rs1 (19:15) | funct3=010 (14:12) | rd (11:7) | opcode=0000011 (6:0)

        # Load: LW
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
        # SW (Store Word) in RV32IS
        # Semantics: SW rs2, imm(rs1)
        # Store the 32-bit value from register rs2 into memory at address rs1 + imm.
        # Endianness: Little-endian (byte at lowest address is the least-significant byte of the word).
        # Alignment: Architecturally requires naturally aligned addresses (address % 4 == 0). Do not assume alignment and raise an exception.
        # Store: SW
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

        # BEQ (Branch if Equal)
        # Compare registers rs1 and rs2.
        # If equal, branch to new PC = current PC + sign-extended offset.
        # Otherwise, fall through: PC = PC + 4.
        # Branch: BEQ
        elif opcode == 0x63:
            if funct3 == 0x0:
                self.logger.debug("BEQ x%d, x%d, offset=%d", rs1, rs2, imm_b(instr))
                if X(rs1) == X(rs2):
                    next_pc = u32(self.pc + imm_b(instr))
                handled = True

        # JAL (Jump and Link)
        # Semantics: JAL rd, offset
        # Write the return address (PC + 4) to register rd.
        # Jump to the target address (PC + sign-extended offset).

        # Jump: JAL
        elif opcode == 0x6F:
            self.logger.debug("JAL x%d, offset=%d", rd, imm_j(instr))
            WR(self.pc + 4)
            next_pc = u32(self.pc + imm_j(instr))
            handled = True

        # Upper-immediate: LUI
        elif opcode == 0x37:
            self.logger.debug("LUI x%d, 0x%05X", rd, get_bits(instr, 31, 12))
            self.regs_dump("before LUI")
            WR(imm_u(instr))
            self.regs_dump("after LUI")
            handled = True

        self.x[0] = 0

        # Halt convention: JAL x0, 0
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


if __name__ == "__main__":

    # Option A: set via param
    log_level = read_log_level()  # reads LOG_LEVEL env var
    setup_logger(level=log_level)

    # Load env (.env + real env) first so logging and flags are ready.  # Added Code
    load_environment()  # Added Code

    # Option B: set via environment variable (export LOG_LEVEL=DEBUG)
    # setup_logger()  # reads LOG_LEVEL env var

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
    program = [
        "00500093",  # ADDI x1, x0, 5  # x1 = 5
        "00A00113",  # ADDI x2, x0, 10  # x2 = 10
        "00A00113",  # ADDI x2, x0, 10  # x2 = 10
        "002081B3",  # ADD x3, x1, x2  # x3 = x1 + x2 = 15
        "40110233",  # SUB x4, x2, x1  # x4 = x2 − x1 = 5
        "000102B7",  # LUI x5, 0x00010 # x5 = 0x00010000 (upper 20 bits << 12)
        "0032A023",  # SW x3, 0(x5) # mem[0x00010000] = x3 (15)
        "0002A203",  # LW x4, 0(x5) # x4 = mem[0x00010000] → 15
        "00418463",  # BEQ x3, x4, 8 # if x3==x4, PC = PC + 8 (skip next instr)
        "00100313",  # ADDI x6, x0, 1 # (will be skipped because BEQ taken)
        "00200313",  # ADDI x6, x0, 2 # executed after the skip → x6 = 2
        "0000006F",  # JAL x0, 0 # jump to self; in your core this is the halt convention
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
