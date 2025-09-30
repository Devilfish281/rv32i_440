#!/usr/bin/env python3
# multi_agent_report_writing_2/src/agent/file_structure/generate_file_structure.py

import io
import os
import re
import sys
import tokenize
from pathlib import Path

from langchain.text_splitter import CharacterTextSplitter, TokenTextSplitter
from langchain_community.document_loaders import TextLoader

# Set of directories to exclude from the file structure
EXCLUDED_DIRS = {
    "__pycache__",
    ".git",
    "venv",
    "node_modules",
    "file_structure",
    "build",
    "db",
    "docs",
    "icons",
    "tests",
    "source",
    ".venv",
}


def read_custom_header(script_dir):
    """
    Reads the custom_header.txt file if it exists. Otherwise, returns the default header.

    :param script_dir: Path object of the script's directory.
    :type script_dir: Path
    :return: Header string.
    :rtype: str
    """
    custom_header_path = script_dir / "custom_header.txt"
    default_header = """\
Developer: Developer: # Project Title
- CPU Design and Simulation Project  class CPSC440

# Role and Objective
- Serve as a Python developer working on the 'CPU Design and Simulation Project' using modern Python tooling and best practices.
- **Programming language:** Python (already installed).
- **Manages virtual environments:** Poetry (already installed).
- **Package installer for Python:** Poetry.
- **Operating System:** Windows 11.
- **Framework:** LangChain, LangGraph.

# Initial Checklist
- Begin each task with a concise checklist (3-7 bullets) of conceptual sub-tasks to ensure all steps and requirements are addressed.

# Instructions
- Use Visual Studio Code on Windows 11 to develop in Python.
- Manage packages and virtual environments with Poetry.
- Implement a meaningful subset of 32-bit RISC-V ISA.
- Employ Git and GitHub for version control.
- Use Sphinx for documentation generation.
- **Check my code for errors and suggest improvements.**

## Coding and Commenting Guidelines
- Write code like a High School Student would.
- When adding new lines of code, annotate with `# Added Code` at the end of the line.
- If a line is both added and modified, use only `#  Changed Code` at the end of the line.
- Do **not** comment on command-line instructions.
- Provide complete code context when submitting changes.
- When editing code:
  1. Clearly state any relevant assumptions.
  2. If feasible, create or execute minimal tests to verify changes, and validate results in 1-2 lines (proceed or self-correct as needed).
  3. Provide review-ready diffs.
  4. Follow the established project style conventions.
- **Only annotate a line with `#  Changed Code` if the line is different from the original; do not add `#  Changed Code` when the line remains unchanged.**

# Context
- **Project Directory:** C:/Users/Me/Documents/Python/CPSC440/Projects/rv32i_440
- **GitHub Repository:** https://github.com/Devilfish281/rv32i_440.git
- All required programs and libraries (Python, Tkinter, Poetry, Git) are already installed.

# Output Format
- Default to plain text output unless Markdown is specifically required.
- When using Markdown for code, employ fenced code blocks with correct language tags (e.g., ```python).
- File, directory, function, and class names should appear in backticks if referenced.
- Escape math notation if present.

# Verbosity
- Use concise summaries for general output.
- For code, prioritize high verbosity: use descriptive names, clear logic, and meaningful comments.

# Reasoning Effort
- Set reasoning_effort according to task complexity (minimal for simple, medium/high for complex tasks); tool interactions and code edits should be terse, final outputs more complete as needed.

# Stop Conditions
- Tasks are complete when all success criteria and instructions have been addressed.
- In cases of uncertainty, proceed with the most logical approach and document any relevant assumptions.
- Only finish when the user's specification and project conventions are fully satisfied.

********************************
Check my code for errors and improvements.

"""
    if custom_header_path.exists():
        try:
            with custom_header_path.open("r", encoding="utf-8") as header_file:
                header = header_file.read()
            print(f"Custom header loaded from '{custom_header_path}'.")
            return header
        except IOError as e:
            print(
                f"Error reading custom header from '{custom_header_path}': {e}",
                file=sys.stderr,
            )
            print("Using default header.")
            return default_header
    else:
        print("Custom header file 'custom_header.txt' not found. Using default header.")
        return default_header


def generate_file_structure(
    root_dir, script_path, output_file, include_tests: bool = False
):  #  Changed Code
    """
    Generates the directory structure of the given root directory and collects .py files.

    :param root_dir: The root directory to generate the file structure from.
    :type root_dir: Path
    :param script_path: The path to the running script to exclude from the file structure.
    :type script_path: Path
    :param output_file: The path to the output file to exclude from the file structure.
    :type output_file: Path
    :param include_tests: If True, the 'tests' directory will be included without prompting.  # Added Code
    :type include_tests: bool  # Added Code
    :return: Tuple containing list of directory structure lines and list of .py file paths.
    :rtype: tuple[list[str], list[Path]]
    """
    lines = ["The File structure for my program is BELOW:\n"]
    py_files = []

    # Initial prompt to include all directories
    while True:
        include_all_response = (
            input("Do you want to include all directories? (y/n): ").strip().lower()
        )
        if include_all_response in {"y", "n"}:
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    include_all = include_all_response == "y"

    for root, dirs, files in os.walk(root_dir):
        # Convert to Path object for easier manipulation
        root_path = Path(root)

        # Exclude specified directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

        if not include_all:
            # Iterate over a copy of dirs to modify dirs in place  #Added Code
            for d in dirs[:]:
                if d == "tests" and include_tests:  # Added Code
                    continue  # skip per-dir prompt for tests when user opted in  # Added Code
                while True:
                    response = (
                        input(f"Do you want to include the directory '{d}'? (y/n): ")
                        .strip()
                        .lower()
                    )
                    if response in {"y", "n"}:
                        break
                    else:
                        print("Invalid input. Please enter 'y' or 'n'.")
                if response == "n":
                    dirs.remove(d)
                    EXCLUDED_DIRS.add(d)
                    print(f"Excluded directory: {d}")

        # Compute the level by relative parts
        try:
            relative_path = root_path.relative_to(root_dir)
            level = len(relative_path.parts)
        except ValueError:
            # In case root_path is same as root_dir
            level = 0

        indent = "    " * level

        # Get directory name
        dir_name = root_path.name if root_path != root_dir else str(root_path.resolve())

        # Determine branch symbol
        branch = "└── " if is_last_item(root_path, dirs, files) else "├── "
        lines.append(f"{indent}{branch}{dir_name}/\n")

        # Prepare indentation for files
        if is_last_item(root_path, dirs, files):
            sub_indent = indent + "    "
        else:
            sub_indent = indent + "│   "

        # Sort files for consistent ordering
        files = sorted(files)
        for idx, f in enumerate(files):
            # Exclude the running script and the output file
            file_path = root_path / f
            if (
                file_path.resolve() == script_path.resolve()
                or file_path.resolve() == output_file.resolve()
            ):
                continue

            # Collect .py files for later processing
            if f.endswith(".py"):
                py_files.append(file_path)

            file_branch = "└── " if idx == len(files) - 1 else "├── "
            lines.append(f"{sub_indent}{file_branch}{f}\n")

    return lines, py_files


def is_last_item(root_path, dirs, files):
    """
    Determines if the current directory is the last item in its parent directory.

    :param root_path: Path object of the current directory.
    :param dirs: List of subdirectories.
    :param files: List of files.
    :return: Boolean indicating if it's the last item.
    """
    parent = root_path.parent
    siblings = [
        s for s in parent.iterdir() if s.is_dir() and s.name not in EXCLUDED_DIRS
    ]
    sorted_siblings = sorted(siblings, key=lambda s: s.name)
    return root_path == sorted_siblings[-1] if siblings else False


def create_chat_gpt_directory(output_file):
    """
    Creates the 'chat_gpt' directory and prepares the output file path.

    :param output_file: The path to the output file.
    :type output_file: Path
    """
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"Directory '{output_file.parent}' is ready.")
    except IOError as e:
        print(
            f"An error occurred while creating '{output_file.parent}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def remove_comments_from_code(source_code: str) -> str:
    """
    Removes all comments from the provided Python source code without altering the original formatting.

    :param source_code: The original Python source code as a string.
    :type source_code: str
    :return: The source code without any comments.
    :rtype: str
    """

    # Regex pattern to match comments
    comment_pattern = re.compile(r"(?<!:)#.*")

    def remove_inline_comment(line: str) -> str:
        """
        Removes inline comments from a single line of code.

        :param line: A single line of Python code.
        :type line: str
        :return: The line without comments.
        :rtype: str
        """
        # Handle cases where '#' is inside a string
        in_single_quote = False
        in_double_quote = False
        escape = False
        for i, char in enumerate(line):
            if char == "\\" and not escape:
                escape = True
                continue
            if not escape:
                if char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == "#" and not in_single_quote and not in_double_quote:
                    return line[:i].rstrip()
            escape = False
        return line.rstrip()

    cleaned_lines = []
    for line in source_code.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("#"):
            # Skip full-line comments
            continue
        else:
            # Remove inline comments
            cleaned_line = remove_inline_comment(line)
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines)


def append_file_contents(output_file, py_files):
    """
    Appends the contents of each .py file to the output file with a header and enhances readability.
    Preserves the first line of the file and removes all comments from the rest of the code.

    :param output_file: The path to the output file.
    :type output_file: Path
    :param py_files: List of paths to .py files.
    :type py_files: list[Path]
    """
    try:
        with output_file.open("a", encoding="utf-8") as file:
            for py_file in py_files:
                separator = "########################################"
                # Write the first separator and header
                file.write(f"\n{separator}\n")
                file.write(f"Here is my code for {py_file.name} BELOW:\n")
                # Write the second separator
                file.write(f"{separator}\n\n")
                # Start of Markdown code block
                file.write(f"```python\n")
                try:
                    with py_file.open("r", encoding="utf-8") as py_f:
                        source_code = py_f.read()
                        if not source_code:
                            cleaned_code = ""
                        else:
                            lines = source_code.splitlines()
                            first_line = lines[0]
                            rest_of_code = "\n".join(lines[1:])
                            # Remove all comments from the rest of the code
                            cleaned_rest = remove_comments_from_code(rest_of_code)
                            # Ensure the first line ends with a newline
                            if not first_line.endswith("\n"):
                                first_line += "\n"
                            cleaned_code = first_line + cleaned_rest
                        file.write(cleaned_code)
                except UnicodeDecodeError:
                    file.write(
                        f"# Could not decode file {py_file} with UTF-8 encoding.\n\n"
                    )
                except IOError as e:
                    file.write(f"# Could not read file {py_file}: {e}\n\n")
                # End of Markdown code block
                file.write(f"```\n")
        print(f"Python file contents appended to '{output_file}'.")
    except IOError as e:
        print(
            f"An error occurred while appending to '{output_file}': {e}",
            file=sys.stderr,
        )


def add_custom_header(output_file, script_dir):
    """
    Adds a custom header to the top of the output file. Reads from 'custom_header.txt' if it exists,
    otherwise uses the default header.

    :param output_file: The path to the output file.
    :type output_file: Path
    :param script_dir: Path object of the script's directory.
    :type script_dir: Path
    """
    header = read_custom_header(script_dir)
    try:
        with output_file.open("w", encoding="utf-8") as file:
            file.write(header + "\n\n")
        print(f"Header written to '{output_file}'.")
    except IOError as e:
        print(
            f"An error occurred while writing header to '{output_file}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def main():
    """
    Entry point of the script. Allows optional command-line arguments for root directory and output file.
    Excludes the script itself and the output directory from the file structure.
    Appends the contents of each .py file after the directory structure.
    Adds a custom header to the top of the output file.
    Enhances readability by adding separators.
    """
    import argparse

    # Determine the script's directory
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent

    parser = argparse.ArgumentParser(
        description=(
            "Generate a comprehensive report of your Python project's directory structure and code.\n\n"
            "This script scans the specified root directory, excluding certain directories and files, "
            "and generates an output file containing the directory structure and the contents of each Python file. "
            "Users can customize the header of the output file by providing a 'custom_header.txt' file in the script's directory.\n\n"
            "Instructions:\n"
            "- If 'custom_header.txt' exists, its contents will be used as the header.\n"
            "- If not, a default header will be used.\n\n"
            "Usage Examples:\n"
            "  python generate_file_structure.py\n"
            "  python generate_file_structure.py --root /path/to/project --output /path/to/output.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-r",
        "--root",
        type=Path,
        default=script_dir.parent,
        help=(
            f"Root directory to scan (default: parent of script's directory: {script_dir.parent})\n"
            "Example: --root /home/user/projects/my_project"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=script_dir / "chat_gpt" / "program_chat_gpt.txt",
        help=(
            f"Output file path (default: ./chat_gpt/program_chat_gpt.txt in script's directory)\n"
            "Example: --output /home/user/projects/my_project/output_structure.txt"
        ),
    )

    args = parser.parse_args()

    # === Ask whether to include tests directory (y/n) ===  # Added Code
    include_tests = False  # Added Code
    try:  # Added Code
        while True:  # Added Code
            resp = (
                input("Do you want to include tests directory? (y/n): ").strip().lower()
            )  # Added Code
            if resp in {"y", "n"}:  # Added Code
                include_tests = resp == "y"  # Added Code
                break  # Added Code
            else:  # Added Code
                print("Invalid input. Please enter 'y' or 'n'.")  # Added Code
    except EOFError:  # Added Code
        include_tests = False  # Added Code

    if include_tests and "tests" in EXCLUDED_DIRS:  # Added Code
        EXCLUDED_DIRS.remove("tests")  # Added Code

    # Exclude the output directory by adding its name to EXCLUDED_DIRS
    EXCLUDED_DIRS.add(args.output.parent.name)

    # Create the output directory if it doesn't exist
    create_chat_gpt_directory(args.output)

    # Add custom header to the output file
    add_custom_header(args.output, script_dir)

    # Generate the file structure and collect .py files
    structure_lines, py_files = generate_file_structure(
        args.root,
        script_path,
        args.output,
        include_tests=include_tests,  #  Changed Code
    )

    # Append the directory structure to the output file after the header
    try:
        with args.output.open("a", encoding="utf-8") as file:
            file.writelines(structure_lines)
        print(f"File structure appended to '{args.output}'.")
    except IOError as e:
        print(
            f"An error occurred while appending directory structure to '{args.output}': {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Append the contents of each .py file
    if py_files:
        append_file_contents(args.output, py_files)
    else:
        print("No Python files found to append.")

    # If tests were requested, also include pytest.ini content in the output  # Added Code
    if include_tests:  # Added Code
        pytest_ini_path = args.root / "pytest.ini"  # Added Code
        try:  # Added Code
            if pytest_ini_path.exists():  # Added Code
                with args.output.open("a", encoding="utf-8") as file:  # Added Code
                    separator = "########################################"  # Added Code
                    file.write(f"\n{separator}\n")  # Added Code
                    file.write("Here is my pytest.ini BELOW:\n")  # Added Code
                    file.write(f"{separator}\n\n")  # Added Code
                    file.write("```ini\n")  # Added Code
                    file.write(
                        pytest_ini_path.read_text(encoding="utf-8")
                    )  # Added Code
                    file.write("\n```\n")  # Added Code
                print(f"pytest.ini appended to '{args.output}'.")  # Added Code
            else:  # Added Code
                print("pytest.ini not found; skipping append.")  # Added Code
        except Exception as e:  # Added Code
            print(f"Failed to append pytest.ini: {e}", file=sys.stderr)  # Added Code


def rag_text():
    import shutil  # Ensure shutil is imported within the function or at the top of the script

    # Define the directory containing the text file and the persistent directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    persistent_directory = os.path.join(current_dir, "db", "rag_chroma_db")
    os.makedirs(os.path.join(current_dir, "db"), exist_ok=True)
    file_path = os.path.join(current_dir, "chat_gpt", "program_chat_gpt.txt")
    chunks_dir = os.path.join(current_dir, "chat_gpt", "chunks")

    if os.path.exists(chunks_dir):
        try:
            shutil.rmtree(chunks_dir)
            print(f"Existing 'chunks' directory '{chunks_dir}' has been removed.")
        except Exception as e:
            print(
                f"Error removing 'chunks' directory '{chunks_dir}': {e}",
                file=sys.stderr,
            )
            sys.exit(1)
    # Create the chunks directory if it doesn't exist
    try:
        os.makedirs(chunks_dir, exist_ok=True)
        print(f"'chunks' directory '{chunks_dir}' has been created.")
    except Exception as e:
        print(f"Error creating 'chunks' directory '{chunks_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    # Check if the Chroma vector store already exists
    # if not os.path.exists(persistent_directory):
    print("Persistent directory does not exist. Initializing vector store...")

    # Ensure the text file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"The file {file_path} does not exist. Please check the path."
        )

    try:
        loader = TextLoader(file_path, encoding="utf-8", autodetect_encoding=True)
        documents = loader.load()
    except UnicodeDecodeError as e:
        # If autdetect failed, try again with latin-1 then raise
        try:
            loader = TextLoader(
                file_path, encoding="latin-1", autodetect_encoding=False
            )  # Added Code
            documents = loader.load()
        except Exception as e2:
            print(f"Unicode decoding failed: {e} and fallback failed: {e2}")
            sys.exit(1)

    # Remove or replace any model special-token markers (like "<|endoftext|>") from text.
    SPECIAL_TOKENS_TO_STRIP = [
        "<|endoftext|>",
        "<|im_start|>",
        "<|im_end|>",
    ]
    for doc in documents:
        if any(tok in doc.page_content for tok in SPECIAL_TOKENS_TO_STRIP):
            for tok in SPECIAL_TOKENS_TO_STRIP:
                if tok in doc.page_content:
                    doc.page_content = doc.page_content.replace(tok, "")
    # --- END: sanitize special tokens ---

    print("\n--- Using Token-based Splitting ---")
    # Use explicit tokenizer config; disallowed_special=() disables strict checks and treats special-token text as normal text.
    token_splitter = TokenTextSplitter(
        chunk_overlap=100,
        chunk_size=32000,
        encoding_name="cl100k_base",  #  (explicit encoding; adjust if you want a different encoding)
        disallowed_special=(),  #  (disables the check so special tokens won't raise ValueError)
    )
    docs = token_splitter.split_documents(documents)

    # Split the document into chunks
    # text_splitter = CharacterTextSplitter(chunk_size=30000, chunk_overlap=0)
    # docs = text_splitter.split_documents(documents)

    # Display information about the split documents
    print("\n--- Document Chunks Information ---")
    print(f"Number of document chunks: {len(docs)}")
    print(f"Sample chunk:\n{docs[0].page_content}\n")

    # Write each chunk to a separate file
    for idx, doc in enumerate(docs, start=1):
        chunk_filename = f"chunk{idx}.txt"
        chunk_path = os.path.join(chunks_dir, chunk_filename)
        try:
            with open(chunk_path, "w", encoding="utf-8") as chunk_file:
                chunk_file.write(doc.page_content)
            print(f"Written {chunk_filename}")
        except IOError as e:
            print(f"Failed to write {chunk_filename}: {e}")

    print("RAG DONE! Chunks have been written to the 'chunks' directory.")

    print("RAG DONE!.")


if __name__ == "__main__":
    main()
    rag_text()
    print("Program DONE!.")
