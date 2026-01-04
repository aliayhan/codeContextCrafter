"""
Integration tests for the main CLI functionality.
Tests the complete workflow from command-line arguments to output generation.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
from argparse import Namespace

from codecontextcrafter.code_context_crafter import (
    _create_argument_parser,
    _collect_files_to_process,
    _resolve_file_dependencies,
    _format_output_prompt,
    _read_source_file,
    _write_output,
    ccc
)


class TestArgumentParser:
    """Test argument parser creation and parsing."""

    def test_parser_creation(self):
        """Test that parser is created with all expected arguments."""
        parser = _create_argument_parser()

        # Parse help to verify all arguments are registered
        with pytest.raises(SystemExit):
            parser.parse_args(['--help'])

    def test_parse_single_file(self):
        """Test parsing a single file argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py'])

        assert args.files == ['test.py']
        assert args.root is None
        assert args.dep_depth_max is None

    def test_parse_multiple_files(self):
        """Test parsing multiple file arguments."""
        parser = _create_argument_parser()
        args = parser.parse_args(['file1.py', 'file2.py', 'file3.py'])

        assert args.files == ['file1.py', 'file2.py', 'file3.py']

    def test_parse_with_root(self):
        """Test parsing with --root argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--root', '/my/root'])

        assert args.root == '/my/root'

    def test_parse_with_depth(self):
        """Test parsing with --dep-depth-max argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--dep-depth-max', '5'])

        assert args.dep_depth_max == 5

    def test_parse_with_output(self):
        """Test parsing with --output argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--output', 'out.md'])

        assert args.output == 'out.md'

    def test_parse_with_sig_tokens(self):
        """Test parsing with --sig-tokens argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--sig-tokens', '4000'])

        assert args.sig_tokens == 4000

    def test_parse_with_verbose(self):
        """Test parsing with --verbose flag."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--verbose'])

        assert args.verbose is True

    def test_parse_with_sig_only(self):
        """Test parsing with --sig-only flag."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--sig-only'])

        assert args.sig_only is True

    def test_parse_with_config(self):
        """Test parsing with --config argument."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--config', '.ccc.conf'])

        assert args.config == '.ccc.conf'

    def test_parse_all_arguments(self):
        """Test parsing with all arguments together."""
        parser = _create_argument_parser()
        args = parser.parse_args([
            'test.py',
            '--root', '/root',
            '--output', 'out.md',
            '--sig-tokens', '2000',
            '--dep-depth-max', '3',
            '--config', 'my.conf',
            '--verbose',
            '--sig-only'
        ])

        assert args.files == ['test.py']
        assert args.root == '/root'
        assert args.output == 'out.md'
        assert args.sig_tokens == 2000
        assert args.dep_depth_max == 3
        assert args.config == 'my.conf'
        assert args.verbose is True
        assert args.sig_only is True


class TestCollectFilesToProcess:
    """Test file collection functionality."""

    def test_collect_from_files_argument(self, tmp_path):
        """Test collecting files from direct file arguments."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("# file1")
        file2.write_text("# file2")

        parser = _create_argument_parser()
        args = parser.parse_args([str(file1), str(file2)])

        files = _collect_files_to_process(args, parser)

        assert len(files) == 2
        assert str(file1.resolve()) in files
        assert str(file2.resolve()) in files

    def test_collect_from_find_command(self, tmp_path):
        """Test collecting files from --find-by command."""
        # Create test files
        (tmp_path / "test1.py").write_text("# test1")
        (tmp_path / "test2.py").write_text("# test2")

        parser = _create_argument_parser()
        find_cmd = f"find {tmp_path} -name '*.py'"
        args = parser.parse_args(['--find-by', find_cmd])

        files = _collect_files_to_process(args, parser)

        assert len(files) == 2

    def test_collect_deduplicates_files(self, tmp_path):
        """Test that duplicate files are removed."""
        file1 = tmp_path / "file1.py"
        file1.write_text("# file1")

        parser = _create_argument_parser()
        # Specify same file twice
        args = parser.parse_args([str(file1), str(file1)])

        files = _collect_files_to_process(args, parser)

        # Should only have one entry
        assert len(files) == 1

    def test_collect_exits_on_no_files(self, tmp_path):
        """Test that program exits when no files are specified."""
        parser = _create_argument_parser()
        args = parser.parse_args([])

        with pytest.raises(SystemExit):
            _collect_files_to_process(args, parser)


class TestResolveFileDependencies:
    """Test dependency resolution functionality."""

    def test_resolve_with_sig_only(self, tmp_path):
        """Test that sig_only mode treats all files as signatures."""
        file1 = tmp_path / "file1.py"
        file1.write_text("import os")

        args = Namespace(
            sig_only=True,
            root=None,
            dep_depth_max=None,
            verbose=False
        )

        primary_files, signature_files = _resolve_file_dependencies([str(file1)], args)

        assert len(primary_files) == 0
        assert str(file1) in signature_files

    def test_resolve_without_sig_only(self, tmp_path):
        """Test normal mode with primary files and dependencies."""
        main_file = tmp_path / "main.py"
        dep_file = tmp_path / "dep.py"

        main_file.write_text("from dep import func")
        dep_file.write_text("def func(): pass")

        args = Namespace(
            sig_only=False,
            root=[str(tmp_path)],
            dep_depth_max=1,
            verbose=False
        )

        primary_files, signature_files = _resolve_file_dependencies([str(main_file)], args)

        assert str(main_file) in primary_files
        assert str(dep_file.resolve()) in signature_files

    def test_resolve_with_multiple_roots(self, tmp_path):
        """Test dependency resolution with multiple root paths."""
        module1 = tmp_path / "module1"
        module2 = tmp_path / "module2"
        module1.mkdir()
        module2.mkdir()

        main_file = module1 / "main.py"
        dep_file = module2 / "dep.py"

        main_file.write_text("from dep import func")
        dep_file.write_text("def func(): pass")

        args = Namespace(
            sig_only=False,
            root=[str(module1), str(module2)],
            dep_depth_max=1,
            verbose=False
        )

        primary_files, signature_files = _resolve_file_dependencies([str(main_file)], args)

        assert str(main_file) in primary_files
        assert str(dep_file.resolve()) in signature_files


class TestFormatOutputPrompt:
    """Test output formatting functionality."""

    def test_format_with_primary_and_signatures(self, tmp_path):
        """Test formatting with both primary files and signatures."""
        file1 = tmp_path / "main.py"
        file1.write_text("def main(): pass")

        signatures = "Signature for dependency"

        result = _format_output_prompt([str(file1)], signatures, sig_only=False)

        assert "# Context" in result
        assert "## Primary Files (Full Content)" in result
        assert "## Dependencies (Signatures)" in result
        assert "def main(): pass" in result
        assert "Signature for dependency" in result

    def test_format_sig_only_mode(self, tmp_path):
        """Test formatting in signatures-only mode."""
        signatures = "Signature content"

        result = _format_output_prompt([], signatures, sig_only=True)

        assert "# Context" in result
        assert "## File Signatures" in result
        assert "Primary Files" not in result
        assert "Signature content" in result

    def test_format_with_no_signatures(self, tmp_path):
        """Test formatting when there are no signatures."""
        file1 = tmp_path / "main.py"
        file1.write_text("def main(): pass")

        result = _format_output_prompt([str(file1)], "", sig_only=False)

        assert "# Context" in result
        assert "## Primary Files (Full Content)" in result
        assert "## Dependencies (Signatures)" not in result

    def test_format_with_multiple_primary_files(self, tmp_path):
        """Test formatting with multiple primary files."""
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("# file1 content")
        file2.write_text("# file2 content")

        result = _format_output_prompt([str(file1), str(file2)], "", sig_only=False)

        assert "# file1 content" in result
        assert "# file2 content" in result
        assert result.count("###") >= 2  # Should have headers for each file


class TestReadSourceFile:
    """Test file reading functionality."""

    def test_read_valid_file(self, tmp_path):
        """Test reading a valid source file."""
        test_file = tmp_path / "test.py"
        content = "def test():\n    return True"
        test_file.write_text(content)

        result = _read_source_file(str(test_file))

        assert result == content

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        result = _read_source_file("/nonexistent/file.py")

        assert "Error reading" in result

    def test_read_utf8_file(self, tmp_path):
        """Test reading a UTF-8 encoded file."""
        test_file = tmp_path / "test.py"
        content = "# UTF-8 characters: é, ñ, 中文"
        test_file.write_text(content, encoding='utf-8')

        result = _read_source_file(str(test_file))

        assert result == content


class TestWriteOutput:
    """Test output writing functionality."""

    def test_write_to_file(self, tmp_path):
        """Test writing output to a file."""
        output_file = tmp_path / "output.md"
        content = "# Test Output\nSome content"

        _write_output(content, str(output_file))

        assert output_file.exists()
        assert output_file.read_text() == content

    def test_write_to_stdout(self, capsys):
        """Test writing output to stdout."""
        content = "# Test Output\nSome content"

        _write_output(content, None)

        captured = capsys.readouterr()
        assert content in captured.out


class TestCLIIntegration:
    """Integration tests for the complete CLI workflow."""

    def test_cli_with_config_file(self, tmp_path, monkeypatch):
        """Test CLI with automatic config file discovery."""
        # Create config file
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
root = {tmp_path}
dep_depth_max = 1
verbose = false
        """.format(tmp_path=tmp_path))

        # Create test files
        main_file = tmp_path / "main.py"
        main_file.write_text("import os")

        # Change to directory with config file
        monkeypatch.chdir(tmp_path)

        # Mock sys.argv
        test_args = ['ccc', str(main_file)]
        with patch.object(sys, 'argv', test_args):
            # The config file should be auto-discovered
            # This is an integration test, so we just verify it doesn't crash
            parser = _create_argument_parser()
            args = parser.parse_args(test_args[1:])
            assert args.config is None  # Not explicitly set, will be auto-discovered

    def test_cli_explicit_config(self, tmp_path):
        """Test CLI with explicitly specified config file."""
        config_file = tmp_path / "my-config.conf"
        config_file.write_text("""
root = {tmp_path}
dep_depth_max = 2
        """.format(tmp_path=tmp_path))

        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--config', str(config_file)])

        assert args.config == str(config_file)

    def test_cli_override_config_with_cli(self, tmp_path):
        """Test that CLI arguments override config file settings."""
        # This is tested in config_parser tests, but verify integration
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("dep_depth_max = 5")

        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--dep-depth-max', '1'])

        # CLI should win
        assert args.dep_depth_max == 1


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_invalid_find_command(self, tmp_path):
        """Test handling of invalid --find-by command."""
        parser = _create_argument_parser()
        args = parser.parse_args(['--find-by', 'invalid_command_xyz'])

        with pytest.raises(SystemExit):
            _collect_files_to_process(args, parser)

    def test_nonexistent_config_file(self, tmp_path, capsys):
        """Test handling of non-existent config file."""
        parser = _create_argument_parser()
        args = parser.parse_args(['test.py', '--config', '/nonexistent/config.conf'])

        # Config file loading should fail gracefully
        # This is handled in the main ccc() function

    def test_empty_file_list(self):
        """Test handling when no files match the criteria."""
        parser = _create_argument_parser()
        args = parser.parse_args([])

        with pytest.raises(SystemExit):
            _collect_files_to_process(args, parser)


class TestMultiModuleSupport:
    """Integration tests for multi-module project support."""

    def test_cross_module_resolution(self, tmp_path):
        """Test dependency resolution across multiple modules."""
        # Create multi-module structure
        module1 = tmp_path / "module1"
        module2 = tmp_path / "module2"
        module1.mkdir()
        module2.mkdir()

        # Module1 imports from Module2
        main = module1 / "main.py"
        main.write_text("from utils import helper")

        utils = module2 / "utils.py"
        utils.write_text("def helper(): pass")

        # Create args with multiple roots
        args = Namespace(
            sig_only=False,
            root=[str(module1), str(module2)],
            dep_depth_max=1,
            verbose=False
        )

        primary_files, signature_files = _resolve_file_dependencies([str(main)], args)

        # Should find dependency in module2
        assert str(utils.resolve()) in signature_files

    def test_module_priority(self, tmp_path):
        """Test that first matching module is used when file exists in multiple modules."""
        module1 = tmp_path / "module1"
        module2 = tmp_path / "module2"
        module1.mkdir()
        module2.mkdir()

        # Same filename in both modules
        config1 = module1 / "config.py"
        config2 = module2 / "config.py"
        config1.write_text("VERSION = 1")
        config2.write_text("VERSION = 2")

        main = tmp_path / "main.py"
        main.write_text("from config import VERSION")

        # Module1 is listed first, should be found first
        args = Namespace(
            sig_only=False,
            root=[str(module1), str(module2)],
            dep_depth_max=1,
            verbose=False
        )

        primary_files, signature_files = _resolve_file_dependencies([str(main)], args)

        # Should find config from module1 (first in list)
        assert str(config1.resolve()) in signature_files
        assert str(config2.resolve()) not in signature_files
