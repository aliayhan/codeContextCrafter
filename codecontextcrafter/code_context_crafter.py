#!/usr/bin/env python3
import sys
import os
import subprocess
import argparse
import tiktoken
from typing import List, Optional, Union

from codecontextcrafter.aider.io import InputOutput
from codecontextcrafter.aider.repomap import RepoMap

from codecontextcrafter.traverser.traverse_dependencies import traverse_dependencies
from codecontextcrafter.config_parser import parse_config_file, apply_config_defaults, validate_config

class DummyModel():
    def tokenizer(self, text):
        return tiktoken.get_encoding("cl100k_base").encode(text)

    def token_count(self, messages):
        try:
            return len(self.tokenizer(messages))
        except Exception as err:
            print(f"Unable to count tokens: {err}")
            return 0

def _read_source_file(file_path: str) -> str:
    """
    Read a source file and return its complete content.

    Args:
        file_path: Path to the file to read

    Returns:
        File content as string, or error message if reading fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as error:
        return f"Error reading: {error}"


def _create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.

    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='ccc',
        description='Extract code context with dependencies for AI assistants'
    )

    # Positional arguments
    parser.add_argument(
        'files',
        help='Source files to analyze (include full content)',
        nargs='*'
    )

    # Options
    parser.add_argument(
        '-c', '--config',
        help='Path to .ccc.conf configuration file',
        default=None
    )

    parser.add_argument(
        '-r', '--root',
        help=(
            'Project root directory for resolving imports. '
            'Useful for Python modules and relative imports. '
            'Can be specified multiple times via config file. '
            '(default: current directory)'
        ),
        default=None
    )

    parser.add_argument(
        '-o', '--output',
        help='Output file path (default: stdout)',
        default=None
    )

    parser.add_argument(
        '-st', '--sig-tokens',
        dest='sig_tokens',
        help=(
            'Maximum tokens for generated signatures. '
            'Controls detail level of dependency signatures. '
            '(default: unlimited detail)'
        ),
        type=int,
        default=None
    )

    parser.add_argument(
        '-f', '--find-by',
        dest='find_by',
        help='Shell command to find files (e.g., "find . -name \'*.py\'")',
        default=None
    )

    parser.add_argument(
        '-dm', '--dep-depth-max',
        dest='dep_depth_max',
        help='Maximum depth for recursive dependency analysis (default: unlimited)',
        type=int,
        default=None
    )

    parser.add_argument(
        '-v', '--verbose',
        help='Enable detailed logging output',
        action='store_true'
    )

    parser.add_argument(
        '-so', '--sig-only',
        dest='sig_only',
        help='Generate only signatures without full file content',
        action='store_true'
    )

    parser.add_argument(
        '-sd', '--sig-detailed',
        dest='sig_detailed',
        help='Include more context in signatures (approximately 50%% of original size)',
        action='store_true'
    )

    return parser


def _collect_files_to_process(args, parser) -> List[str]:
    """
    Collect all files to process based on command-line arguments.

    Args:
        args: Parsed command-line arguments
        parser: Argument parser (for help display if needed)

    Returns:
        List of file paths to process
    """
    to_be_processed = []

    if args.find_by:
        try:
            # Run shell cmd
            result = subprocess.run(
                args.find_by,
                shell=True,
                check=True,
                capture_output=True,
                text=True
            )
            files = [f.strip() for f in result.stdout.splitlines() if f.strip()]

            to_be_processed.extend(files)
        except subprocess.CalledProcessError as error:
            print(f"Error on find: {error}")
            sys.exit(1)

    if args.files:
        to_be_processed.extend(args.files)

    to_be_processed = list(dict.fromkeys(to_be_processed))

    if not to_be_processed:
        print("No files selected.")
        parser.print_help()
        sys.exit(1)

    return [os.path.abspath(f) for f in to_be_processed]


def _resolve_file_dependencies(absolute_file_paths: List[str], args) -> tuple:
    """
    Resolve dependencies for the given files.

    Args:
        absolute_file_paths: List of absolute paths to analyze
        args: Command-line arguments

    Returns:
        Tuple of (primary_files, signature_files)
    """
    if not args.sig_only:
        print(f"Processing {len(absolute_file_paths)} primary files...")
        primary_files = absolute_file_paths

        # Handle root as either string or list (from config file)
        if args.root is not None:
            if isinstance(args.root, list):
                base_import_roots = [os.path.abspath(r) for r in args.root]
            else:
                base_import_roots = [os.path.abspath(args.root)]
        else:
            base_import_roots = None

        discovered_dependencies = set()

        for file_path in absolute_file_paths:
            dependencies = traverse_dependencies(
                file_path,
                base_import_roots,
                depth_max=args.dep_depth_max,
                is_verbose=args.verbose
            )
            discovered_dependencies.update(dependencies)

        signature_files = [dep for dep in discovered_dependencies if dep not in absolute_file_paths]

    else:
        primary_files = []
        signature_files = absolute_file_paths

    return primary_files, signature_files


def _generate_code_signatures(signature_files: List[str], args) -> str:
    """
    Generate code signatures using RepoMap.

    Args:
        signature_files: List of files to generate signatures for
        args: Command-line arguments

    Returns:
        Generated signatures as string
    """
    print(f"Generating file signatures for {len(signature_files)} files...")

    # Set up token counter
    io = InputOutput(dry_run=True)
    token_counter = DummyModel()

    # Create signature generator
    signature_generator = RepoMap(
        map_tokens=args.sig_tokens,
        root='.',
        main_model=token_counter,
        io=io,
        verbose=args.verbose,
        sig_detailed=args.sig_detailed,
    )

    # Generate signatures
    # chat_files: files to show in detail (empty for signature generation)
    # other_files: files to generate signatures for
    signatures = signature_generator.get_repo_map(
        chat_files=[],  # Don't show full content in signatures section
        other_files=signature_files
    )

    return signatures


def _format_output_prompt(primary_files: List[str], signatures: Optional[str], sig_only: bool) -> str:
    """
    Format the final output prompt combining primary files and signatures.

    Args:
        primary_files: List of primary file paths (full content)
        signatures: Generated signatures string
        sig_only: Whether in signatures-only mode

    Returns:
        Formatted prompt as markdown string
    """
    prompt = "# Context\n\n"

    # Add full content of primary files (skip if sig_only is True)
    if not sig_only and primary_files:
        prompt += "## Primary Files (Full Content)\n\n"
        for file_path in sorted(primary_files):
            content = _read_source_file(file_path)

            # Determine language for code block based on file extension
            extension = os.path.splitext(file_path)[1].lower()
            language = ''
            if extension == '.py':
                language = 'python'
            elif extension in ['.js', '.jsx']:
                language = 'javascript'
            elif extension in ['.ts', '.tsx']:
                language = 'typescript'
            elif extension in ['.java']:
                language = 'java'
            elif extension in ['.c', '.cpp', '.h', '.hpp']:
                language = 'cpp'

            prompt += f"### {file_path}\n```{language}\n{content}\n```\n\n"

    # Add signatures (for dependencies or all files if sig_only is True)
    if signatures:
        section_title = "File Signatures" if sig_only else "Dependencies (Signatures)"
        prompt += f"## {section_title}\n\n"
        prompt += signatures

    return prompt


def _write_output(prompt: str, output_path: Optional[str]) -> None:
    """
    Write the generated prompt to file or stdout.

    Args:
        prompt: The formatted prompt to output
        output_path: Output file path, or None for stdout
    """
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as output_file:
            output_file.write(prompt)
        print(f"Prompt written to {output_path}")
    else:
        print(prompt)


def ccc():
    """
    Main entry point for CodeContextCrafter CLI.

    Orchestrates the workflow:
    1. Parse command-line arguments
    2. Load config file if specified
    3. Collect files to process
    4. Resolve dependencies
    5. Generate signatures
    6. Format and output the result
    """
    # Step 1: Parse arguments
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Step 2: Load and apply config file
    # Auto-discover .ccc.conf in current directory if not explicitly specified
    config_file = args.config
    if not config_file and os.path.exists('.ccc.conf'):
        config_file = '.ccc.conf'

    if config_file:
        try:
            config = parse_config_file(config_file)
            validate_config(config)
            apply_config_defaults(args, config)
            if args.verbose:
                print(f"Loaded configuration from {config_file}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading config file: {e}", file=sys.stderr)
            sys.exit(1)

    # Log configuration
    if args.sig_tokens is None and args.verbose:
        print("No --sig-tokens specified: using maximum detail signatures")

    # Step 3: Collect files to process
    absolute_file_paths = _collect_files_to_process(args, parser)

    # Step 3: Resolve dependencies
    primary_files, signature_files = _resolve_file_dependencies(absolute_file_paths, args)

    # Step 4: Generate signatures
    signatures = _generate_code_signatures(signature_files, args)

    # Step 5: Format output prompt
    print("Generating final prompt...")
    prompt = _format_output_prompt(primary_files, signatures, args.sig_only)

    # Step 6: Write output
    _write_output(prompt, args.output)


def main():
    print("CodeContextCrafter is running!")
    ccc()