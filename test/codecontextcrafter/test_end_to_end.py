"""
End-to-end integration tests for the complete ccc workflow.
Tests the entire pipeline from CLI invocation to output generation.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from io import StringIO

from codecontextcrafter.code_context_crafter import ccc, main


class TestEndToEnd:
    """End-to-end tests that exercise the complete ccc() workflow."""

    def test_simple_file_to_stdout(self, tmp_path, capsys, monkeypatch):
        """Test processing a single file with output to stdout."""
        # Create a simple test file
        test_file = tmp_path / "simple.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        # Mock sys.argv
        test_args = ['ccc', str(test_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        captured = capsys.readouterr()

        # Verify output contains the file content
        assert "def hello():" in captured.out
        assert "return 'world'" in captured.out
        assert "# Context" in captured.out

    def test_file_with_output_file(self, tmp_path, monkeypatch):
        """Test processing a file with output to a file."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n\ndef main():\n    pass\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(test_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify output file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "def main():" in content
        assert "# Context" in content

    def test_with_dependencies_and_depth(self, tmp_path, monkeypatch):
        """Test dependency resolution with depth limiting."""
        # Create a dependency chain
        utils = tmp_path / "utils.py"
        utils.write_text("def util_func():\n    pass\n")

        main_file = tmp_path / "main.py"
        main_file.write_text("from utils import util_func\n\ndef main():\n    util_func()\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv with depth limit and root
        test_args = [
            'ccc',
            str(main_file),
            '--root', str(tmp_path),
            '--dep-depth-max', '1',
            '--output', str(output_file)
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify output file contains both primary and dependencies
        assert output_file.exists()
        content = output_file.read_text()
        assert "main.py" in content
        assert "## Dependencies (Signatures)" in content

    def test_sig_only_mode(self, tmp_path, monkeypatch):
        """Test signature-only mode."""
        # Create test files
        file1 = tmp_path / "file1.py"
        file1.write_text("def func1():\n    pass\n")

        file2 = tmp_path / "file2.py"
        file2.write_text("def func2():\n    pass\n")

        output_file = tmp_path / "signatures.md"

        # Mock sys.argv for sig-only mode
        test_args = [
            'ccc',
            str(file1),
            str(file2),
            '--sig-only',
            '--output', str(output_file)
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify output contains signatures
        assert output_file.exists()
        content = output_file.read_text()
        assert "## File Signatures" in content
        # Should NOT have primary files section
        assert "Primary Files" not in content

    def test_with_config_file(self, tmp_path, monkeypatch):
        """Test with automatic config file discovery."""
        # Create config file
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text(f"""
root = {tmp_path}
dep_depth_max = 2
sig_tokens = 2000
        """)

        # Create test files
        dep = tmp_path / "dependency.py"
        dep.write_text("def dep_func():\n    pass\n")

        main_file = tmp_path / "main.py"
        main_file.write_text("from dependency import dep_func\n")

        output_file = tmp_path / "output.md"

        # Change to directory with config file
        monkeypatch.chdir(tmp_path)

        # Mock sys.argv - config should be auto-discovered
        test_args = ['ccc', str(main_file), '--output', str(output_file)]

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify config was used (dependencies should be found)
        assert output_file.exists()
        content = output_file.read_text()
        assert "## Dependencies (Signatures)" in content

    def test_explicit_config_file(self, tmp_path, monkeypatch):
        """Test with explicitly specified config file."""
        # Create config file with custom name
        config_file = tmp_path / "my-config.conf"
        config_file.write_text(f"""
root = {tmp_path}
dep_depth_max = 1
        """)

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("import os\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv with explicit config
        test_args = [
            'ccc',
            str(test_file),
            '--config', str(config_file),
            '--output', str(output_file)
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Should complete without error
        assert output_file.exists()

    def test_verbose_mode(self, tmp_path, capsys, monkeypatch):
        """Test verbose output mode."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass\n")

        # Mock sys.argv with verbose flag
        test_args = ['ccc', str(test_file), '--verbose']
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        captured = capsys.readouterr()

        # Verify verbose messages appear
        assert "Processing" in captured.out or "Generating" in captured.out

    def test_invalid_config_file_exits(self, tmp_path, monkeypatch):
        """Test that invalid config file causes exit."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass\n")

        # Mock sys.argv with non-existent config
        test_args = [
            'ccc',
            str(test_file),
            '--config', '/nonexistent/config.conf'
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            with pytest.raises(SystemExit):
                ccc()

    def test_multiple_files(self, tmp_path, monkeypatch):
        """Test processing multiple files at once."""
        # Create multiple test files
        file1 = tmp_path / "file1.py"
        file1.write_text("def func1():\n    pass\n")

        file2 = tmp_path / "file2.py"
        file2.write_text("def func2():\n    pass\n")

        file3 = tmp_path / "file3.py"
        file3.write_text("def func3():\n    pass\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv with multiple files
        test_args = [
            'ccc',
            str(file1),
            str(file2),
            str(file3),
            '--output', str(output_file)
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify all files are in output
        assert output_file.exists()
        content = output_file.read_text()
        assert "func1" in content
        assert "func2" in content
        assert "func3" in content

    def test_find_by_command(self, tmp_path, monkeypatch):
        """Test file discovery via --find-by command."""
        # Create test files
        (tmp_path / "test1.py").write_text("# test1")
        (tmp_path / "test2.py").write_text("# test2")
        (tmp_path / "ignored.txt").write_text("# ignored")

        output_file = tmp_path / "output.md"

        # Mock sys.argv with find-by command
        find_cmd = f"find {tmp_path} -name '*.py'"
        test_args = [
            'ccc',
            '--find-by', find_cmd,
            '--sig-only',
            '--output', str(output_file)
        ]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify Python files were found and processed
        assert output_file.exists()
        content = output_file.read_text()
        assert "test1.py" in content or "test2.py" in content

    def test_multi_module_with_config(self, tmp_path, monkeypatch):
        """Test multi-module project with config file."""
        # Create multi-module structure
        module1 = tmp_path / "module1"
        module2 = tmp_path / "module2"
        module1.mkdir()
        module2.mkdir()

        # Create files in different modules
        utils = module1 / "utils.py"
        utils.write_text("def util_func():\n    pass\n")

        helpers = module2 / "helpers.py"
        helpers.write_text("def helper_func():\n    pass\n")

        main_file = tmp_path / "main.py"
        main_file.write_text("""
from utils import util_func
from helpers import helper_func
        """)

        # Create config with multiple roots
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text(f"""
root = {module1}
root = {module2}
dep_depth_max = 1
        """)

        output_file = tmp_path / "output.md"

        # Change to directory with config
        monkeypatch.chdir(tmp_path)

        # Mock sys.argv
        test_args = ['ccc', str(main_file), '--output', str(output_file)]

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify both modules' dependencies were found
        assert output_file.exists()
        content = output_file.read_text()
        assert "## Dependencies (Signatures)" in content

    def test_javascript_file_language_detection(self, tmp_path, monkeypatch):
        """Test that JavaScript files are properly detected and formatted."""
        # Create JavaScript file
        js_file = tmp_path / "app.js"
        js_file.write_text("function hello() {\n  return 'world';\n}\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(js_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify JavaScript code block
        assert output_file.exists()
        content = output_file.read_text()
        assert "```javascript" in content
        assert "function hello()" in content

    def test_typescript_file_language_detection(self, tmp_path, monkeypatch):
        """Test that TypeScript files are properly detected and formatted."""
        # Create TypeScript file
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("function greet(name: string): string {\n  return `Hello ${name}`;\n}\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(ts_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify TypeScript code block
        assert output_file.exists()
        content = output_file.read_text()
        assert "```typescript" in content
        assert "function greet" in content

    def test_java_file_language_detection(self, tmp_path, monkeypatch):
        """Test that Java files are properly detected and formatted."""
        # Create Java file
        java_file = tmp_path / "Main.java"
        java_file.write_text("public class Main {\n  public static void main(String[] args) {}\n}\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(java_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify Java code block
        assert output_file.exists()
        content = output_file.read_text()
        assert "```java" in content
        assert "public class Main" in content

    def test_main_function(self, tmp_path, capsys, monkeypatch):
        """Test the main() entry point function."""
        # Create simple test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass\n")

        # Mock sys.argv
        test_args = ['ccc', str(test_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            main()

        captured = capsys.readouterr()

        # Verify main() prints the banner and calls ccc()
        assert "CodeContextCrafter is running!" in captured.out
        assert "def test():" in captured.out

    def test_config_verbose_message(self, tmp_path, capsys, monkeypatch):
        """Test that verbose mode shows config loading message."""
        # Create config file
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text(f"root = {tmp_path}\n")

        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass\n")

        # Change to directory with config
        monkeypatch.chdir(tmp_path)

        # Mock sys.argv with verbose
        test_args = ['ccc', str(test_file), '--verbose']

        with patch.object(sys, 'argv', test_args):
            ccc()

        captured = capsys.readouterr()

        # Verify config loading message appears
        assert "Loaded configuration from" in captured.out

    def test_sig_tokens_none_verbose_message(self, tmp_path, capsys, monkeypatch):
        """Test verbose message when sig_tokens is not specified."""
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test():\n    pass\n")

        # Mock sys.argv with verbose but no sig-tokens
        test_args = ['ccc', str(test_file), '--sig-only', '--verbose']
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        captured = capsys.readouterr()

        # Verify message about maximum detail signatures
        assert "maximum detail signatures" in captured.out

    def test_cpp_file_language_detection(self, tmp_path, monkeypatch):
        """Test that C/C++ files are properly detected and formatted."""
        # Create C++ file
        cpp_file = tmp_path / "main.cpp"
        cpp_file.write_text("#include <iostream>\n\nint main() {\n  return 0;\n}\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(cpp_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify C++ code block
        assert output_file.exists()
        content = output_file.read_text()
        assert "```cpp" in content
        assert "#include <iostream>" in content

    def test_c_header_file_language_detection(self, tmp_path, monkeypatch):
        """Test that C header files are properly detected and formatted."""
        # Create C header file
        h_file = tmp_path / "header.h"
        h_file.write_text("#ifndef HEADER_H\n#define HEADER_H\n\nvoid func();\n\n#endif\n")

        output_file = tmp_path / "output.md"

        # Mock sys.argv
        test_args = ['ccc', str(h_file), '--output', str(output_file)]
        monkeypatch.chdir(tmp_path)

        with patch.object(sys, 'argv', test_args):
            ccc()

        # Verify C/C++ code block for header
        assert output_file.exists()
        content = output_file.read_text()
        assert "```cpp" in content
        assert "#ifndef HEADER_H" in content
