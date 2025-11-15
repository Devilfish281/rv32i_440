````markdown
# rv32i-440 — Single-Cycle RV32I Teaching CPU (Python)

CPSC 440: CPU Design and Simulation Project  
Author: Matthew Dobley

## Quickstart for the grader

From a fresh clone in PowerShell on Windows:

```bash
git clone https://github.com/Devilfish281/rv32i_440.git
cd rv32i_440
poetry install
copy .env.example .env
poetry run python -m rv32i_440.rv32i_440 prog.hex
```
````

see log file `logs/app.log` for detailed execution trace.

This project is a simple 32-bit RISC-V CPU simulator that implements a subset of the RV32I base integer instruction set (plus RV32M arithmetic via a separate numeric core **for extra-credit multiply/divide support**). The design models a **single-cycle CPU** in Python: each call to `step()` performs fetch → decode → execute → memory → write-back, and `run()` iterates until a halt.

The goal is to give a clear, inspectable reference model for the CPSC 440 project while matching the course requirements:

- Single-cycle 32-bit RV32I CPU (little-endian).
- **Meaningful subset of RV32I instructions (ADDI/ADD/SUB/LW/SW/BEQ/BNE/JAL/JALR/LUI/AUIPC, plus logic and shift ops).**
- **Extra-credit RV32M multiply/divide block: MUL/DIV/DIVU/REM/REMU, wired through a bit-level numeric core.**
- Program image loader for `prog.hex`.
- Trace/logging support for debugging.
- GitHub repo with feature branches, docs, and tests.
- Clean separation between the CPU and a reusable numeric core (ALU/MDU/FPU/shifters).

---

## 1. Project Overview

This repo implements a tiny teaching core:

- 32 integer registers (`x0`–`x31`), with `x0` hard-wired to zero.
- Program counter (`pc`) addressing bytes.
- Instruction memory (`imem`) and data memory (`dmem`) as Python dictionaries keyed by byte address.
- Sign-extension and immediate decoding helpers for RISC-V’s I/S/B/J/U formats.
- A simple run loop that executes until a halt instruction is encountered.

The reference implementation is in:

- `src/rv32i_440/rv32i_440.py` — CPU model and demo `__main__`.
- `src/utilities/load_env.py` — `.env` loading and environment validation.
- `src/utilities/logger_setup.py` — rotating file + console logging.
- `src/midterm_440/numeric_core/` — bit-level ALU, shifters, multiply/divide unit, float32 helpers.

---

## 2. Repository Layout

Root:

- `pyproject.toml` — Poetry configuration (`rv32i-440` package).
- `poetry.lock` — Locked dependency versions.
- `README.md` — This file.
- `Makefile`, `make.bat` — Optional helpers for docs/tasks.
- `.env`, `.env.example` — Environment configuration.

`src/` — Project source tree:

- `rv32i_440/`

  - `__init__.py`
  - `rv32i_440.py` — Tiny RV32I CPU model and CLI entry point.
  - `alu_adapter.py` — Adapter from Python ints to bit-level ALU.

- `midterm_440/`

  - `__init__.py`
  - `numeric_core/`

    - `alu.py` — Bit-level ripple-carry ALU for ADD/SUB with flags (N, Z, C, V).
    - `bits.py` — Utilities for 32-bit bit-vectors and pretty-printing.
    - `fpu_f32.py` — IEEE 754 float32 pack/unpack and host-backed arithmetic (smoke tests).
    - `interfaces.py` — Public API surface for the numeric core.
    - `mdu.py` — Bit-level multiply/divide unit (shift-add MUL, restoring DIV/DIVU).
    - `shifter.py` — Logical/arithmetic shifters (SLL, SRL, SRA) without `<<`/`>>`.
    - `twos.py` — Two’s-complement helpers (encode/decode, sign/zero-extend).
    - `internal/` — Internal helpers (not directly used by the CPU).

- `utilities/`

  - `__init__.py`
  - `load_env.py` — Loads `.env`, validates key vars like `REGISTER_DUMP`.
  - `logger_setup.py` — Configures rotating file + console logging.

- `logs/`

  - `app.log` — Default rotating log file.

`tests/` — Unit tests for the numeric core:

- `unit/test_alu.py`
- `unit/test_bits.py`
- `unit/test_fpu_f32.py`
- `unit/test_mdu.py`
- `unit/test_shifter.py`
- `unit/test_twos.py`

---

## 3. Getting Started

### 3.1 Requirements

- Windows 11
- Python 3.12+
- Poetry

### 3.2 Clone the repository

```bash
git clone https://github.com/Devilfish281/rv32i_440.git
cd rv32i_440
```

### 3.3 Install dependencies with Poetry

```bash
poetry install
```

This installs:

- Runtime: `python-dotenv`, `langchain-core`, `langchain`, `langchain-community`, `tiktoken`.
- Dev: `sphinx`, `sphinx-rtd-theme`, `sphinx-autodoc-typehints`.

(For this project, the core simulator only depends on the standard library + `python-dotenv` and logging; LangChain is present because of the broader tooling environment.)

---

## 4. Configuration and Logging

Environment variables are read from `.env` using `python-dotenv`.

### 4.1 Required environment variable

`REGISTER_DUMP` controls whether full register dumps are logged around certain instructions:

- Allowed values (case-insensitive): `1`, `0`, `true`, `false`, `yes`, `no`, `on`, `off`.
- If the value is missing or invalid, `load_environment()` will log an error and raise `ValueError`.

Examples:

```env
# .env
REGISTER_DUMP=True
LOG_LEVEL=DEBUG
```

### 4.2 Optional environment variable

`LOG_LEVEL` controls global log verbosity:

- Typical values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- Defaults to `INFO` if not set.

### 4.3 Log outputs

The logger is configured in `utilities/logger_setup.py`:

- Console output (stream handler).
- Rotating file handler in `logs/app.log` (5 MB max per file, 3 backups).
- Uniform format: timestamp, log level, logger name, line, message.

---

## 5. Program Image Format (`prog.hex`)

The course standardizes program loading via a simple hex format:

- **Filename**: `prog.hex`

- **Layout**:

  - One 32-bit instruction per line.
  - Exactly 8 hex digits per line (no `0x` prefix).
  - Uppercase or lowercase hex digits are both accepted.

- **Order**:

  - One word per line, in execution order (PC increments by 4 bytes per line).

- **Whitespace**:

  - Blank lines are allowed and ignored.

- **Comments**:

  - For cross-platform compatibility, comments should be avoided in `.hex` files.

The CPU’s `load_hex_lines()` helper already supports this format when given a list of hex strings. The `__main__` block wraps this with a `load_hex_file("prog.hex")` call when a filename is passed on the command line.

---

## 6. CPU Model: `TinyCPU`

The main CPU implementation lives in `rv32i_440.py` and is exposed via the `TinyCPU` class.

### 6.1 State

- `x[0..31]`: 32 general-purpose registers (int, masked to 32 bits).
- `pc`: Program counter (byte address).
- `imem`: Instruction memory map (`addr -> word`).
- `dmem`: Data memory map (`addr -> word`).
- `trace`: List of `(pc, instruction)` tuples for executed instructions.
- `logger`: Per-module logger used for debug messages.

`x[0]` is forced to `0` after every instruction, modelling the RISC-V zero register.

### 6.2 Helper functions

- `u32(x)`: Mask to 32 bits.
- `get_bits(x, hi, lo)`: Returns the bit slice `[hi:lo]` of `x`.
- `sext(val, bits)`: Sign-extends a `bits`-wide value to Python’s `int`.
- `imm_i`, `imm_s`, `imm_b`, `imm_j`, `imm_u`: Decode RISC-V immediates for I/S/B/J/U-type instructions.

---

## 7. Supported Instruction Set

This implementation covers the **standard CPSC 440 RV32I subset** plus some additional instructions and an **RV32M extra-credit block**.

### 7.0 High-level summary

| Group                      | Instructions                                                    | Notes                                             |
| -------------------------- | --------------------------------------------------------------- | ------------------------------------------------- |
| Integer arithmetic / logic | `ADD`, `SUB`, `AND`, `OR`, `XOR`, `ADDI`, `ANDI`, `ORI`, `XORI` | Basic RV32I ALU ops                               |
| Shifts                     | `SLL`, `SRL`, `SRA`, `SLLI`, `SRLI`, `SRAI`                     | Register and immediate forms, 0–31 shamt          |
| Memory                     | `LW`, `SW`                                                      | 32-bit word load/store, word-aligned only         |
| Branch / jump              | `BEQ`, `BNE`, `JAL`, `JALR`                                     | Control flow and function-call primitives         |
| Upper immediates           | `LUI`, `AUIPC`                                                  | PC-relative and absolute upper-immediate patterns |
| **RV32M extra credit**     | **`MUL`, `DIV`, `DIVU`, `REM`, `REMU`**                         | **Extra-credit M-extension via bit-level MDU**    |

Any other RV32I opcodes (e.g., `SLT/SLTU`, byte/halfword loads/stores, system/CSR ops) are **not implemented** and will log a warning if encountered.

---

### 7.1 RV32I arithmetic and logical (register–register)

**R-type (opcode `0x33`, `funct7=0x00` unless noted):**

- `ADD  rd, rs1, rs2` — integer addition via bit-level ALU (`alu_exec("ADD")`).
- `SUB  rd, rs1, rs2` — integer subtraction via bit-level ALU (`alu_exec("SUB")`).
- `AND  rd, rs1, rs2`
- `OR   rd, rs1, rs2`
- `XOR  rd, rs1, rs2`

These operations:

- Read `rs1` and `rs2` from the register file.
- Use the numeric core for `ADD/SUB` (with N/Z/C/V flags logged).
- Write the masked 32-bit result back to `rd` (unless `rd == 0`).

---

### 7.2 RV32I arithmetic and logical (immediate + shifts)

**I-type arithmetic/bitwise (opcode `0x13`):**

- `ADDI  rd, rs1, imm` — add sign-extended 12-bit immediate.
- `XORI  rd, rs1, imm`
- `ORI   rd, rs1, imm`
- `ANDI  rd, rs1, imm`

**I-type shift immediates (opcode `0x13`, `funct3` = shift, `funct7` distinguishes SRLI/SRAI):**

- `SLLI rd, rs1, shamt` — logical left shift.
- `SRLI rd, rs1, shamt` — logical right shift.
- `SRAI rd, rs1, shamt` — arithmetic right shift (sign-extended).

These use the `_shift_helper()` wrapper, which calls the bit-level shifter (`numeric_core.shifter`) so the implementation does not rely on Python `<<`/`>>` for the core math.

---

### 7.3 Shifts (register forms)

In addition to the immediate forms, the CPU implements the register-based (R-type) shift instructions:

- `SLL rd, rs1, rs2` — shift left logical by `rs2 & 0x1F`.
- `SRL rd, rs1, rs2` — shift right logical by `rs2 & 0x1F`.
- `SRA rd, rs1, rs2` — shift right arithmetic by `rs2 & 0x1F`.

The shift amount is taken from the low 5 bits of `rs2` and passed into the same `_shift_helper()` path, which uses the bit-level barrel shifter.

---

### 7.4 Memory

- `LW rd, imm(rs1)` — word load.

  - Effective address = `X[rs1] + imm_i(instr)`.
  - Must be **word-aligned**; unaligned accesses raise `ValueError`.
  - Loads a 32-bit word from `dmem[addr]` (or returns 0 if the address is unmapped).

- `SW rs2, imm(rs1)` — word store.

  - Effective address = `X[rs1] + imm_s(instr)`.
  - Must be **word-aligned**; unaligned accesses raise `ValueError`.
  - Stores `X[rs2]` into `dmem[addr]`.

Only 32-bit word accesses are supported; byte and halfword (B/H) loads/stores are intentionally omitted.

---

### 7.5 Control flow (branches and jumps)

**Branches (opcode `0x63`):**

- `BEQ rs1, rs2, offset` — branch if equal.

  - Uses `imm_b(instr)` to compute a signed byte offset.
  - If `X[rs1] == X[rs2]`, then `pc` is updated to `pc + offset`.

- `BNE rs1, rs2, offset` — branch if not equal.

  - Similar to `BEQ`, but the condition is `X[rs1] != X[rs2]`.

**Jumps:**

- `JAL rd, offset` (opcode `0x6F`)

  - Writes `pc + 4` into `rd`.
  - Sets `pc` to `pc + imm_j(instr)`.
  - `JAL x0, 0` (`0x0000006F`) is treated as the **halt convention** (see 7.7).

- `JALR rd, rs1, offset` (opcode `0x67`, `funct3=0`)

  - Writes `pc + 4` into `rd`.
  - Target = `(X[rs1] + imm_i(instr)) & ~1` (LSB cleared per RISC-V spec).
  - Sets `pc` to this aligned target.

These instructions give you both basic branching and function-call-style control flow.

---

### 7.6 Upper immediates

- `LUI   rd, imm20` (opcode `0x37`)

  - Loads the upper 20 bits of `imm_u(instr)` into `rd` (bits [31:12]), with the low 12 bits set to zero.

- `AUIPC rd, imm20` (opcode `0x17`)

  - Adds `imm_u(instr)` to the current `pc` and writes the result to `rd`.
  - Useful for PC-relative addressing.

---

### 7.7 RV32M multiply/divide (M-extension — **EXTRA CREDIT**)

The following instructions are implemented using the **bit-level multiply/divide unit** in `numeric_core.mdu` and a thin adapter `_mdu_exec()` in `rv32i_440.py`. These go **beyond** the minimal RV32I requirements and are intended as **extra credit for CPSC 440**.

**R-type, `opcode = 0x33`, `funct7 = 0x01`:**

- `MUL  rd, rs1, rs2` — low 32 bits of signed product.

  - Uses classic **shift-add** multiplication in the MDU.
  - Sets an `overflow` flag if the true signed 64-bit product does not fit in 32 bits.

- `DIV  rd, rs1, rs2` — signed division (truncation toward zero).

- `DIVU rd, rs1, rs2` — unsigned division.

- `REM  rd, rs1, rs2` — signed remainder (same sign as dividend).

- `REMU rd, rs1, rs2` — unsigned remainder.

The MDU handles RISC-V M-extension edge cases:

- Divide by zero:

  - Quotient = `0xFFFFFFFF`
  - Remainder = dividend
  - `div_by_zero` flag set.

- `INT_MIN / -1` (signed):

  - Quotient = `INT_MIN`
  - Remainder = `0`
  - `overflow` flag set.

These flags and (optionally) per-step traces are logged to help grading and debugging.

---

### 7.8 Halt convention and unsupported instructions

**Halt convention:**

- The word `0x0000006F` (`jal x0, 0`) is treated as **halt**:

  - Architecturally it is just a self-jump, but in this simulator `step()` will stop and cause `run()` to return when this pattern is encountered.

**Unsupported instructions:**

- Any instruction outside the sets listed above (e.g., `SLT/SLTU`, `LB/LH/SB/SH`, `ECALL/EBREAK`, CSR instructions, F/atomics) is **not implemented**.
- When such an instruction is fetched:

  - The CPU logs a warning with the opcode and `pc`.
  - It still advances `pc` by 4, but the behavior of the instruction is effectively “no-op” from the ISA perspective (other than the warning).

---

## 8. Datapath and Control Description

This implementation models a **single-cycle datapath** in Python. Each call to `TinyCPU.step()` performs one full instruction: fetch → decode → execute → memory → write-back.

### 8.1 Datapath components

Conceptually, the datapath consists of:

- **Program Counter (PC)**

  - A 32-bit register (`self.pc`) that holds the byte address of the current instruction.
  - Normally increments by 4 each step; branches/jumps overwrite it with a new target.

- **Instruction Memory (`imem`)**

  - A dictionary mapping word-aligned addresses to 32-bit instructions.
  - `fetch()` reads `imem[pc]` (or returns 0 if unmapped) and logs `pc` and `instr`.

- **Register File (`x[0..31]`)**

  - A Python list of 32 integers.
  - Register `x0` is forced to 0 after every instruction to obey RISC-V semantics.
  - Helper `X(i)` in `step()` reads a register, automatically treating `x0` as constant zero.
  - Helper `WR(v)` writes the masked 32-bit result back to `rd` (unless `rd == 0`).

- **Immediate Generation**

  - Helpers `imm_i`, `imm_s`, `imm_b`, `imm_j`, and `imm_u` decode instruction bits into sign-extended immediates or U-type upper immediates.
  - These correspond to the I/S/B/J/U formats in the RISC-V spec.

- **ALU / Numeric Core**

  - For `ADD` and `SUB`, the CPU calls `alu_exec()` in `alu_adapter.py`.

    - `alu_exec()` converts 32-bit Python ints to 32-bit bit-vectors using `u32_to_bits()`,
      passes them to the bit-level ripple-carry ALU (`numeric_core.alu`) and then converts the result back with `bits_to_u32()`.
    - Flags (N, Z, C, V) are computed by the numeric core and logged.

  - Immediate arithmetic (`ADDI`, etc.) is done with normal Python arithmetic masked by `u32()` for simplicity (the project still demonstrates the bit-level ALU via `ADD/SUB`).

- **Shifter**

  - `_shift_helper(kind, value, shamt)` calls into `numeric_core.shifter` (`sll_bits`, `srl_bits`, `sra_bits`).
  - Both immediate and register-based shift instructions are executed via this helper; the result is masked back to 32 bits.

- **Multiply/Divide Unit (MDU)**

  - `_mdu_exec(op, rs1, rs2)` calls `mul_shift_add()` or `div_restoring()` from `numeric_core.mdu`.
  - The MDU performs **shift-add multiplication** and **restoring division** entirely in terms of bit-vectors.
  - The CPU receives a 32-bit result, along with flags (`overflow`, `div_by_zero`) for logging.

- **Data Memory (`dmem`)**

  - A dictionary mapping word-aligned addresses to 32-bit words.
  - `LW` reads `dmem[addr]` (or 0 if unmapped).
  - `SW` writes `dmem[addr] = value`.
  - Both enforce word alignment; misalignment raises an exception to make bugs visible.

- **Write-back**

  - At the end of execute/memory, `WR()` writes the result to `rd`.
  - `x0` is explicitly reset to 0 before returning from `step()`.

### 8.2 Control logic (single-cycle control “unit”)

There is no separate control-unit class; instead, the control logic is implemented inside `TinyCPU.step()`:

1. **Decode phase**

   - Extracts `opcode`, `funct3`, `funct7`, `rd`, `rs1`, `rs2` using `get_bits()`.
   - Initializes `next_pc = pc + 4` by default.

2. **Case analysis on `opcode`**

   - `0x13` → I-type arithmetic/logic/shift (ADDI, ANDI, ORI, XORI, SLLI, SRLI, SRAI).
   - `0x33` → R-type arithmetic/logic, plus M-extension operations (ADD/SUB/SLL/SRL/SRA/AND/OR/XOR and MUL/DIV/DIVU/REM/REMU).
   - `0x03` → loads (LW).
   - `0x23` → stores (SW).
   - `0x63` → branches (BEQ/BNE).
   - `0x6F` → jumps (JAL).
   - `0x67` → register jump (JALR).
   - `0x17` → PC-relative upper immediate (AUIPC).
   - `0x37` → upper-immediate (LUI).

3. **Instruction-specific actions**

   - For each supported instruction, `step()`:

     - Logs the mnemonic and operands (e.g., `"ADD x3, x1, x2"`).
     - Optionally emits a **register dump before and after** the instruction if `REGISTER_DUMP` is enabled.
     - Calls the appropriate helpers (`alu_exec`, `_mdu_exec`, `_shift_helper`, `imm_*`, load/store) and then `WR()`.

4. **PC update and halt**

   - Branches and jumps override `next_pc` using `imm_b()` / `imm_j()` or the JALR target.
   - If the instruction word equals `0x0000006F`, `step()` advances `pc` and returns `False` to signal halt.
   - Otherwise, `pc` is set to `next_pc`, `(pc, instr)` is appended to `trace`, and `step()` returns `True`.

Overall, `TinyCPU.step()` acts as a simple single-cycle control unit: decode, choose control signals (what to read, what to write, which functional unit to use), then commit updates.

---

## 9. Additional Features and Notes

A few extra features go beyond the minimal “just works” simulator:

### 9.1 Bit-level numeric core (reused from midterm)

- The `midterm_440.numeric_core` package is a reusable “numeric core” from a previous midterm assignment.

- It provides:

  - A **ripple-carry ALU** with flags (N, Z, C, V).
  - **Shift-add multiply** and **restoring divide** for RV32M.
  - A **barrel shifter** without using Python `<<`/`>>` for core math.
  - A **float32 pack/unpack** and host-backed arithmetic layer for smoke tests.
  - Two’s-complement helpers (`encode_twos_complement`, `decode_twos_complement`, `sign_extend`, `zero_extend`).

- The CPU uses this numeric core in a controlled way:

  - `ADD/SUB` go through `alu_exec()` → bit-level ALU.
  - `MUL/DIV/DIVU/REM/REMU` go through `_mdu_exec()` → bit-level MDU.
  - Shifts (`SLL/SRL/SRA` and `SLLI/SRLI/SRAI`) go through `_shift_helper()` → bit-level shifter.

This separation makes the CPU easier to reason about and grades the bit-level algorithms independently of the CPU control logic.

### 9.2 Tracing and observability

- Most instructions log a short human-readable trace (mnemonics, operands, addresses).
- `REGISTER_DUMP=1` turns on verbose “before/after” dumps of all 32 registers around key instructions (ALU ops, loads/stores, branches, M-extension ops, etc.).
- The MDU and ALU both support internal **per-bit trace** modes:

  - For example, `mul_shift_add(..., trace=True)` logs each multiplication step, showing partial products and accumulator high/low 32-bit values.
  - These traces are returned from `_mdu_exec()` / `alu_exec()` and can be inspected if needed.

### 9.3 Error handling intended to help grading

- Unaligned `LW/SW` raises a `ValueError` instead of silently doing the wrong thing.
- `load_environment()` validates `REGISTER_DUMP` and fails fast if it’s missing or malformed, rather than silently ignoring configuration errors.
- Divide-by-zero and `INT_MIN/-1` are handled explicitly in the MDU and surfaced via flags.

### 9.4 Tests for numeric core correctness

- Unit tests in `tests/unit/` cover:

  - ALU overflow edges and flag behavior.
  - Bit-vector conversions and formatting (`pretty_hex32`, `pretty_bin32`).
  - FPU pack/unpack and basic float arithmetic (smoke tests).
  - MDU behavior including overflow, divide-by-zero, and special cases.
  - Shifter edge cases and illegal arguments.
  - Two’s-complement encode/decode and sign/zero extension.

Although the CPU itself could be tested more extensively (e.g., with hex programs), the numeric core is well-covered, which reduces the risk of low-level arithmetic bugs.

### 9.5 Built-in demo program

- When no `prog.hex` file is found, `__main__` runs a small hard-coded demo sequence that:

  - Initializes registers.
  - Exercises `ADD`, `SUB`, `LUI`, `SW`, `LW`, `BEQ`, and `JAL` (halt).

- This makes it easy to smoke-test the simulator without preparing a hex file first.

---

## 10. Running the Simulator

### 10.1 Using the built-in demo program

The `__main__` block in `rv32i_440.py` contains a small hard-coded test program that:

- Initializes registers (`x1`, `x2`).
- Performs addition and subtraction (`x3`, `x4`).
- Uses `LUI`, `SW`, and `LW` to write and read memory at `0x00010000`.
- Uses `BEQ` to select between two `ADDI` paths for `x6`.
- Halts via `jal x0, 0`.

From the project root:

```bash
poetry run python -m rv32i_440.rv32i_440
```

Expected behavior (at a high level):

- The CPU runs until halt.
- The logger prints final values of key registers and memory:

  - `x1`, `x2`, `x3`, `x4`, `x5`, `x6`
  - `dmem[0x00010000]`

You can see detailed execution logs and optional register dumps in `logs/app.log`.

### 10.2 Loading from a `.hex` file

The main entry point will try to interpret the first command-line argument as a hex program:

```bash
poetry run python -m rv32i_440.rv32i_440 prog.hex
```

Internally this:

- Calls `TinyCPU.load_hex_file("prog.hex", base_pc=0)`.
- Runs `cpu.run()` until halt or the `max_steps` safety limit.
- Logs summary information about steps executed, final PC, and a subset of registers and memory.

You can also load programs manually in Python:

```python
from rv32i_440.rv32i_440 import TinyCPU

cpu = TinyCPU()
cpu.load_hex_file("prog.hex", base_pc=0)
steps = cpu.run()
print("Steps:", steps, "PC:", hex(cpu.pc))
```

---

## 11. Testing

Pytest is used for unit testing the numeric core and (optionally) CPU-level tests.

Run all tests:

```bash
poetry run pytest -q
```

Run only the unit tests folder:

```bash
poetry run pytest -q tests/unit
```

Future work may add integration tests that:

- Load a known hex program (like a `test_base.hex` for CPSC 440).
- Run until halt.
- Assert final register and memory values.

---

## 12. Documentation (Sphinx)

Sphinx is configured as a dev dependency. The plan is to add:

- A `docs/` tree with:

  - High-level project overview.
  - Datapath and control description (expanded from this README).
  - Supported ISA reference.
  - API docs for `TinyCPU` and helper modules.

Typical Sphinx workflow (once the docs tree exists):

```bash
cd docs
make html
```

The generated HTML docs will live in `docs/_build/html`.

---

## 13. Development Workflow (CPSC 440)

This repo follows the course expectations:

- **GitHub repository**:

  - `main` branch should always be stable.

- **Feature branches**:

  - Use named branches for major components:

    - `feat/alu-and-arith`
    - `feat/memory-and-load-store`
    - `feat/branch-and-jump`
    - `feat/hex-loader`
    - `feat/m-extension` (MUL/DIV/REM)
    - `feat/numeric-core-tests`

  - Merge back into `main` after tests pass.

- **Commits**:

  - Small, focused commits with clear messages.
  - Reference features (e.g., “Wire MUL/DIV via numeric_core.mdu”).

---

## 14. Commit History (GitHub Evidence)

This project was developed over time using Git and GitHub. The full commit history is public and can be viewed here:

- Main branch commits: https://github.com/Devilfish281/rv32i_440/commits/main

Each commit shows:

- **What changed** (files added/modified/removed)
- **When it changed** (date/time)
- **Why it changed** (commit message)

For the grader, here is how to interpret the history in terms of project milestones:

1. **Initial project setup**  
   Early commits set up the Poetry project, basic folder structure under `src/`, logging framework, and the `TinyCPU` skeleton in `rv32i_440/rv32i_440.py`.

2. **Instruction set and single-cycle CPU core**  
   A sequence of commits adds RV32I instructions (e.g., ADDI/ADD/SUB, LW/SW, BEQ/BNE, JAL/JALR, LUI/AUIPC) and wires them into the `TinyCPU.step()` control logic.  
   These commits show the gradual build-up of the single-cycle datapath and control unit.

3. **Numeric core integration — **EXTRA CREDIT**  
   Commits involving the `midterm_440.numeric_core` package (ALU, MDU, shifters, float32 helpers, two’s-complement tools) and the `rv32i_440/alu_adapter.py` file document how the CPU was connected to a **bit-level numeric core\*\*:

   - `ADD`/`SUB` routed through the ripple-carry ALU
   - `MUL/DIV/DIVU/REM/REMU` routed through the shift-add / restoring-division MDU
   - Shift instructions using the bit-level shifter  
     This goes beyond the minimum RV32I requirements and is intended as **extra credit** work.

4. **Testing and regression safety**  
   Commits under `tests/unit/` add or refine tests for:

   - ALU (`test_alu.py`)
   - Shifters (`test_shifter.py`)
   - Multiply/divide unit (`test_mdu.py`)
   - Bit utilities (`test_bits.py`)
   - Two’s-complement helpers (`test_twos.py`)
   - Float32 packing/unpacking and basic arithmetic (`test_fpu_f32.py`)  
     These commits show that the numeric core and supporting code were verified with automated tests, not just “happy-path” examples.

5. **Tracing, logging, and environment validation — **EXTRA CREDIT-STYLE POLISH\*\*  
   Additional commits improve developer and grader experience by:
   - Adding structured logging via `utilities/logger_setup.py`
   - Using `.env` configuration and `REGISTER_DUMP` / `LOG_LEVEL` in `utilities/load_env.py`
   - Enforcing safe behavior (e.g., errors for misaligned LW/SW, validation of env vars)  
     These changes are not strictly required for a minimal CPU, but they make the project easier to debug, test, and grade, and they represent **extra effort** beyond the baseline.

### How to view the history locally (optional)

If you clone the repo, you can explore the same history on your own machine:

```bash
git clone https://github.com/Devilfish281/rv32i_440.git
cd rv32i_440

# Compact view of commits (top = most recent)
git log --oneline --graph --decorate

# Show which files changed in each commit
git log --stat

```

## Block Diagram

```plaintext

+------------------+
|   TinyCPU        |  <--- 32-bit RISC-V CPU core
|                  |
|  +--------------+|
|  |  PC (pc)     |  <--- Program Counter (byte address)
|  +--------------+|
|  |  Reg File    |  <--- 32 x 32-bit integer registers
|  +--------------+|
|  |  ALU         |  <--- Arithmetic Logic Unit
|  +--------------+|
|  |  MDU         |  <--- Multiply/Divide Unit
|  +--------------+|
|  |  IMEM        |  <--- Instruction Memory
|  +--------------+|
|  |  DMEM        |  <--- Data Memory
|  +--------------+|
+------------------+

Block diagram
                +--------------------------------------+
                |           Program Loader             |
                |   - reads prog.hex from disk         |
                |   - calls TinyCPU.load_hex_file()    |
                +--------------------+-----------------+
                                     |
                                     v
                          +----------+-----------+
                          |      PC Register     |
                          |   (byte address)     |
                          +----------+-----------+
                                     |
                                     v
                          +----------+-----------+
                          |   Instruction Memory |
                          |       (imem dict)    |
                          +----------+-----------+
                                     |
                                     v
                          +----------+-----------+
                          |   Decode & Control   |
                          | - opcode / funct3    |
                          | - funct7, rs1, rs2   |
                          | - immediate gen      |
                          | - selects ALU/MDU    |
                          |   shift, branch, etc |
                          +----------+-----------+
                                     |
                                     v
                        +------------+-------------+
                        |      Register File       |
                        |   x0..x31 (x[0..31])     |
                        | - x0 hard-wired to 0     |
                        +-------+----------+-------+
                                |          |
                          rs1 value   rs2 value
                                |          |
                                v          v
                     +----------+----------+-------------------+
                     |       Execute / Numeric Core            |
                     |                                         |
                     |  +--------------+    +----------------+ |
                     |  |   ALU        |    | Shifter        | |
                     |  | (ADD, SUB,   |    | SLL, SRL, SRA  | |
                     |  |  XOR, OR, AND)    +----------------+ |
                     |  +--------------+                        |
                     |  +--------------+    +----------------+ |
                     |  |   MDU        |    | FPU (f32)      | |
                     |  | (MUL, DIV,   |    |  (smoke tests) | |
                     |  |  DIVU, REM…) |    +----------------+ |
                     |  +--------------+                        |
                     |   (implemented in midterm_440.numeric_core)
                     +----------+--------------------------------+
                                |
                                | ALU / MDU / shift result
                                v
                        +-------+-----------+
                        |   Data Memory    |
                        |     (dmem dict)  |
                        | - LW / SW        |
                        +-------+-----------+
                                |
                     load data  |  store data
                                v
                        +-------+-----------+
                        |   Write-back      |
                        | - writes rd≠0    |
                        |   into x[rd]     |
                        +-------+-----------+
                                |
                                v
                        +-------+-----------+
                        |   Next PC Logic   |
                        | - PC+4 (normal)   |
                        | - branches (BEQ)  |
                        | - jumps (JAL)     |
                        +-------+-----------+
                                |
                                v
                          (back to PC)


```
