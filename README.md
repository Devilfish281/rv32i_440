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

This project is a simple 32-bit RISC-V CPU simulator that implements a subset of the RV32I base integer instruction set. The design models a **single-cycle CPU** in Python: each call to `step()` performs fetch → decode → execute → memory → write-back, and `run()` iterates until a halt.

The goal is to give a clear, inspectable reference model for the CPSC 440 project while matching the course requirements:

- Single-cycle 32-bit RV32I CPU (little-endian).
- Meaningful subset of RV32I instructions.
- Program image loader for `prog.hex`.
- Trace/logging support for debugging.
- GitHub repo with feature branches, docs, and tests.

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

---

## 2. Repository Layout

Root:

- `pyproject.toml` — Poetry configuration (`rv32i-440` package).
- `poetry.lock` — Locked dependency versions.
- `README.md` — This file.
- `Makefile`, `make.bat` — Optional helpers for docs/tasks.
- `.env`, `.env.example` — Environment configuration.
- `src/` — Project source tree:
  - `rv32i_440/`
    - `__init__.py`
    - `rv32i_440.py` — Tiny RV32I CPU model.
  - `utilities/`
    - `__init__.py`
    - `load_env.py` — Loads `.env`, validates key vars.
    - `logger_setup.py` — Configures logging.
  - `logs/`
    - `app.log` — Default rotating log file.

(You can add `tests/` and `docs/` as the project grows.)

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
REGISTER_DUMP=0
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

The CPU’s `load_hex_lines()` helper already supports this format when given a list of hex strings. A small wrapper (planned) will add a convenient `load_hex_file("prog.hex")` helper.

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

## 7. Supported Instruction Subset

The current implementation focuses on a minimal but useful subset of RV32I:

- Arithmetic:

  - `ADDI` — `addi rd, rs1, imm`
  - `ADD` — `add rd, rs1, rs2`
  - `SUB` — `sub rd, rs1, rs2`

- Memory:

  - `LW` — `lw rd, imm(rs1)` (word-aligned; unaligned loads raise `ValueError`)
  - `SW` — `sw rs2, imm(rs1)` (word-aligned; unaligned stores raise `ValueError`)

- Control flow:

  - `BEQ` — `beq rs1, rs2, offset`
  - `JAL` — `jal rd, offset` (also used for halt; see below)

- Upper immediates:

  - `LUI` — `lui rd, imm20`

### 7.1 Halt convention

The program uses a simple teaching convention to signal “halt”:

- The instruction `0x0000006F` (`jal x0, 0`) is treated as a halt.
- Architecturally this is just an infinite self-jump, but in this simulator, encountering this instruction causes `step()` to return `False`, and `run()` stops.

(This is convenient for closed-form tests like `test_base.hex`.)

### 7.2 Planned extensions

As part of the course project, the ISA subset will be extended toward the suggested minimum set:

- Logical:

  - `AND`, `OR`, `XOR`, and immediate forms (`ANDI`, `ORI`, `XORI`).

- Shifts:

  - `SLL`, `SRL`, `SRA`, and immediate forms (`SLLI`, `SRLI`, `SRAI`).

- Additional branches:

  - `BNE` and possibly others.

- Jumps and PC-relative:

  - `JALR`
  - `AUIPC`

The README will be updated as more instructions are implemented and tested.

---

## 8. Running the Simulator

### 8.1 Using the built-in demo program

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

### 8.2 Loading from a `.hex` file (planned)

A small wrapper (to be implemented in this project) will allow:

```python
cpu = TinyCPU()
cpu.load_hex_file("prog.hex", base_pc=0)
cpu.run()
```

and a matching CLI entry point such as:

```bash
poetry run python -m rv32i_440.rv32i_440 prog.hex
```

In the meantime, you can:

- Read the contents of `prog.hex` yourself.
- Pass the lines into `TinyCPU.load_hex_lines(lines, base_pc=0)`.

---

## 9. Testing

Pytest will be used for unit and integration testing.

Planned tests:

- **Unit tests** (e.g., `tests/test_immediates.py`):

  - `get_bits`, `sext`, and each `imm_*` decoder.

- **CPU tests** (e.g., `tests/test_cpu_base.py`):

  - Load a known hex program (like the provided `test_base.hex`).
  - Run until halt.
  - Assert final register and memory values match the expected behavior.

Once tests are in place, they will be runnable with:

```bash
poetry run pytest -q
```

---

## 10. Documentation (Sphinx)

Sphinx is configured as a dev dependency. The plan is to add:

- A `docs/` tree with:

  - High-level project overview.
  - Datapath and control description.
  - Supported ISA reference.
  - API docs for `TinyCPU` and helper modules.

Typical Sphinx workflow (once the docs tree exists):

```bash
cd docs
make html
```

The generated HTML docs will live in `docs/_build/html`.

---

## 11. Development Workflow (CPSC 440)

This repo follows the course expectations:

- **GitHub repository**:

  - `main` branch should always be stable.

- **Feature branches**:

  - Use named branches for major components:

    - `feat/alu-and-arith`
    - `feat/memory-and-load-store`
    - `feat/branch-and-jump`
    - `feat/hex-loader`

  - Merge back into `main` after tests pass.

- **Commits**:

  - Small, focused commits with clear messages.
  - Reference features (e.g., “Implement BEQ and branch immediate decoding”).

- **Coding guidelines**:

  - New lines in code are annotated with `# Added Code`.
  - Modified lines are annotated with `#  Changed Code` (only when they differ from the original).

---
