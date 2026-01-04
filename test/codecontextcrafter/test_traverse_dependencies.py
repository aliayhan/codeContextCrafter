import pytest
import os
from pathlib import Path
from codecontextcrafter.traverser.traverse_dependencies import (
    traverse_dependencies,
    traverse_code,
    relative_to_absolute
)


class TestTraverseCode:
    """Test the traverse_code function that extracts imports from source code."""

    def test_python_simple_imports(self):
        """Test basic Python import statements."""
        code = """
import os
import sys
import json
        """
        result = traverse_code(code)
        assert result == {'os', 'sys', 'json'}

    def test_python_from_imports(self):
        """Test Python from...import statements."""
        code = """
from typing import List, Dict
from os.path import join, exists
from mypackage.module import MyClass
        """
        result = traverse_code(code)
        assert result == {'typing', 'os.path', 'mypackage.module'}

    def test_python_mixed_imports(self):
        """Test combination of import styles."""
        code = """
import os, sys, json
from typing import List
from .relative import something
        """
        result = traverse_code(code)
        assert 'os' in result
        assert 'sys' in result
        assert 'json' in result
        assert 'typing' in result

    def test_javascript_imports(self):
        """Test JavaScript/TypeScript import statements."""
        code = """
import { Component } from 'react';
import './styles.css';
import utils from '../utils';
const fs = require('fs');
const path = require('path');
        """
        result = traverse_code(code)
        assert 'react' in result
        assert './styles.css' in result
        assert '../utils' in result
        assert 'fs' in result
        assert 'path' in result

    def test_typescript_type_imports(self):
        """Test TypeScript type imports."""
        code = """
import type { UserType } from './types';
import { API } from '../api';
        """
        result = traverse_code(code)
        assert './types' in result
        assert '../api' in result

    def test_java_imports(self):
        """Test Java import statements."""
        code = """
import java.util.List;
import java.util.ArrayList;
import static java.lang.Math.PI;
import com.example.MyClass;
        """
        result = traverse_code(code)
        assert 'java.util.List' in result
        assert 'java.util.ArrayList' in result
        assert 'java.lang.Math' in result
        assert 'com.example.MyClass' in result

    def test_ignore_wildcard_imports(self):
        """Test that wildcard imports are ignored."""
        code = """
import *
from something import *
import java.util.*;
        """
        result = traverse_code(code)
        # Wildcard imports should be filtered out
        assert '*' not in str(result)

    def test_multiline_and_comments(self):
        """Test imports with comments and various formatting."""
        code = """
import os  # Operating system interface
import sys  // Another comment style
from typing import List  /* Block comment */
        """
        result = traverse_code(code)
        assert 'os' in result
        assert 'sys' in result
        assert 'typing' in result


class TestRelativeToAbsolute:
    """Test the relative_to_absolute function that resolves import paths to files."""

    def test_relative_import_existing_file(self, tmp_path):
        """Test resolving a relative import to an existing file."""
        # Create a file structure
        target_file = tmp_path / "module.py"
        target_file.write_text("# module content")

        result = relative_to_absolute(str(tmp_path), "./module.py")
        assert result == str(target_file.resolve())

    def test_relative_import_without_extension(self, tmp_path):
        """Test resolving import without file extension."""
        target_file = tmp_path / "module.py"
        target_file.write_text("# module content")

        result = relative_to_absolute(str(tmp_path), "./module")
        assert result == str(target_file.resolve())

    def test_parent_directory_import(self, tmp_path):
        """Test resolving imports from parent directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        target_file = tmp_path / "module.py"
        target_file.write_text("# module content")

        result = relative_to_absolute(str(subdir), "../module")
        assert result == str(target_file.resolve())

    def test_package_style_import(self, tmp_path):
        """Test resolving package-style imports (dot notation)."""
        package_dir = tmp_path / "mypackage"
        package_dir.mkdir()
        target_file = package_dir / "module.py"
        target_file.write_text("# module content")

        result = relative_to_absolute(str(tmp_path), "mypackage.module")
        assert result == str(target_file.resolve())

    def test_nonexistent_file(self, tmp_path):
        """Test that nonexistent files return None."""
        result = relative_to_absolute(str(tmp_path), "nonexistent")
        assert result is None

    def test_multiple_extensions(self, tmp_path):
        """Test that function tries multiple extensions."""
        # Create a .js file
        target_file = tmp_path / "module.js"
        target_file.write_text("// js content")

        result = relative_to_absolute(str(tmp_path), "./module")
        assert result == str(target_file.resolve())

    def test_absolute_path_import(self, tmp_path):
        """Test handling absolute path imports."""
        target_file = tmp_path / "module.py"
        target_file.write_text("# module content")

        result = relative_to_absolute(str(tmp_path), str(target_file))
        assert result is not None


class TestTraverseDependencies:
    """Test the main traverse_dependencies function."""

    def test_simple_python_dependency_chain(self, tmp_path):
        """Test a simple chain of Python dependencies."""
        # Create file structure:
        # main.py -> utils.py -> helpers.py

        helpers = tmp_path / "helpers.py"
        helpers.write_text("def helper(): pass")

        utils = tmp_path / "utils.py"
        utils.write_text("from helpers import helper")

        main = tmp_path / "main.py"
        main.write_text("from utils import something")

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(utils.resolve()) in result
        assert str(helpers.resolve()) in result
        assert len(result) == 2

    def test_multiple_direct_dependencies(self, tmp_path):
        """Test file with multiple direct dependencies."""
        # Create file structure:
        # main.py -> dep1.py, dep2.py, dep3.py

        dep1 = tmp_path / "dep1.py"
        dep1.write_text("def func1(): pass")

        dep2 = tmp_path / "dep2.py"
        dep2.write_text("def func2(): pass")

        dep3 = tmp_path / "dep3.py"
        dep3.write_text("def func3(): pass")

        main = tmp_path / "main.py"
        main.write_text("""
from dep1 import func1
from dep2 import func2
from dep3 import func3
        """)

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(dep1.resolve()) in result
        assert str(dep2.resolve()) in result
        assert str(dep3.resolve()) in result
        assert len(result) == 3

    def test_circular_dependencies(self, tmp_path):
        """Test that circular dependencies don't cause infinite loops."""
        # Create circular structure:
        # a.py -> b.py -> c.py -> a.py

        a = tmp_path / "a.py"
        b = tmp_path / "b.py"
        c = tmp_path / "c.py"

        a.write_text("from b import something")
        b.write_text("from c import something")
        c.write_text("from a import something")

        result = traverse_dependencies(str(a), str(tmp_path))

        # Should find both b and c, but not loop infinitely
        assert str(b.resolve()) in result
        assert str(c.resolve()) in result
        assert len(result) == 2

    def test_depth_limiting(self, tmp_path):
        """Test that depth_max parameter limits traversal depth.

        Depth limiting works by limiting how deep we PROCESS files.
        When we process a file at depth N, we discover its dependencies and add them
        at depth N+1. If depth N+1 > depth_max, those dependencies won't be processed,
        but they're still in the results.

        Example with depth_max=1:
        - main.py (depth 0): processed, discovers dep1
        - dep1.py (depth 1): processed (1 <= 1), discovers dep2
        - dep2.py (depth 2): not processed (2 > 1), but already in results

        So depth_max=1 means: process main + 1 level of dependencies (dep1),
        which will discover up to 2 levels (dep1 and dep2).
        """
        # Create chain: main -> dep1 -> dep2 -> dep3

        dep3 = tmp_path / "dep3.py"
        dep3.write_text("def func3(): pass")

        dep2 = tmp_path / "dep2.py"
        dep2.write_text("from dep3 import func3")

        dep1 = tmp_path / "dep1.py"
        dep1.write_text("from dep2 import func2")

        main = tmp_path / "main.py"
        main.write_text("from dep1 import func1")

        # Limit depth to 0 - should only discover direct dependencies of main
        result = traverse_dependencies(str(main), str(tmp_path), depth_max=0)
        assert str(dep1.resolve()) in result
        assert str(dep2.resolve()) not in result
        assert str(dep3.resolve()) not in result
        assert len(result) == 1

        # Limit depth to 1 - processes main and dep1, discovers dep1 and dep2
        result = traverse_dependencies(str(main), str(tmp_path), depth_max=1)
        assert str(dep1.resolve()) in result
        assert str(dep2.resolve()) in result
        assert str(dep3.resolve()) not in result
        assert len(result) == 2

        # Limit depth to 2 - processes main, dep1, and dep2, discovers all
        result = traverse_dependencies(str(main), str(tmp_path), depth_max=2)
        assert str(dep1.resolve()) in result
        assert str(dep2.resolve()) in result
        assert str(dep3.resolve()) in result
        assert len(result) == 3

    def test_no_depth_limit(self, tmp_path):
        """Test traversal without depth limit."""
        # Create deep chain
        dep3 = tmp_path / "dep3.py"
        dep3.write_text("def func3(): pass")

        dep2 = tmp_path / "dep2.py"
        dep2.write_text("from dep3 import func3")

        dep1 = tmp_path / "dep1.py"
        dep1.write_text("from dep2 import func2")

        main = tmp_path / "main.py"
        main.write_text("from dep1 import func1")

        result = traverse_dependencies(str(main), str(tmp_path), depth_max=None)

        assert str(dep1.resolve()) in result
        assert str(dep2.resolve()) in result
        assert str(dep3.resolve()) in result

    def test_javascript_dependencies(self, tmp_path):
        """Test traversing JavaScript/TypeScript dependencies."""
        # Create JS file structure

        utils = tmp_path / "utils.js"
        utils.write_text("export function util() {}")

        main = tmp_path / "main.js"
        main.write_text("import { util } from './utils';")

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(utils.resolve()) in result

    def test_typescript_with_extensions(self, tmp_path):
        """Test TypeScript files with .ts extension."""

        types_file = tmp_path / "types.ts"
        types_file.write_text("export interface User {}")

        main = tmp_path / "main.ts"
        main.write_text("import type { User } from './types';")

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(types_file.resolve()) in result

    def test_package_structure_with_subdirectories(self, tmp_path):
        """Test dependencies in package structures with subdirectories."""
        # Create package structure:
        # main.py
        # package/
        #   module.py
        #   subpackage/
        #     submodule.py

        package_dir = tmp_path / "package"
        package_dir.mkdir()
        subpackage_dir = package_dir / "subpackage"
        subpackage_dir.mkdir()

        submodule = subpackage_dir / "submodule.py"
        submodule.write_text("def sub_func(): pass")

        module = package_dir / "module.py"
        module.write_text("from package.subpackage.submodule import sub_func")

        main = tmp_path / "main.py"
        main.write_text("from package.module import something")

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(module.resolve()) in result
        assert str(submodule.resolve()) in result

    def test_relative_imports_without_base_root(self, tmp_path):
        """Test that relative imports work when base_import_root is None."""

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        dep = subdir / "dep.py"
        dep.write_text("def func(): pass")

        main = subdir / "main.py"
        main.write_text("from dep import func")

        # Use None as base_import_root - should use file's directory
        result = traverse_dependencies(str(main), None)

        assert str(dep.resolve()) in result

    def test_external_imports_ignored(self, tmp_path):
        """Test that external library imports are ignored if files don't exist."""

        main = tmp_path / "main.py"
        main.write_text("""
import os
import sys
from typing import List
import nonexistent_local_module
        """)

        result = traverse_dependencies(str(main), str(tmp_path))

        # External libraries and nonexistent files should not be in results
        assert len(result) == 0

    def test_self_import_ignored(self, tmp_path):
        """Test that a file importing itself is ignored."""

        main = tmp_path / "main.py"
        main.write_text("from main import something")

        result = traverse_dependencies(str(main), str(tmp_path))

        # Should not include itself
        assert str(main.resolve()) not in result
        assert len(result) == 0

    def test_mixed_language_dependencies(self, tmp_path):
        """Test project with mixed Python and JavaScript files."""
        # This tests that the function can handle mixed file types
        # though typically you wouldn't import across languages

        py_dep = tmp_path / "pydep.py"
        py_dep.write_text("def func(): pass")

        js_dep = tmp_path / "jsdep.js"
        js_dep.write_text("export function func() {}")

        # Python file with Python import
        py_main = tmp_path / "pymain.py"
        py_main.write_text("from pydep import func")

        # JS file with JS import
        js_main = tmp_path / "jsmain.js"
        js_main.write_text("import { func } from './jsdep';")

        py_result = traverse_dependencies(str(py_main), str(tmp_path))
        assert str(py_dep.resolve()) in py_result

        js_result = traverse_dependencies(str(js_main), str(tmp_path))
        assert str(js_dep.resolve()) in js_result

    def test_verbose_mode(self, tmp_path, capsys):
        """Test that verbose mode prints debug information."""

        dep = tmp_path / "dep.py"
        dep.write_text("def func(): pass")

        main = tmp_path / "main.py"
        main.write_text("from dep import func")

        traverse_dependencies(str(main), str(tmp_path), is_verbose=True)

        captured = capsys.readouterr()
        assert "Processing" in captured.out

    def test_diamond_dependency_structure(self, tmp_path):
        """Test diamond dependency pattern: main -> a,b -> common."""

        common = tmp_path / "common.py"
        common.write_text("def common_func(): pass")

        a = tmp_path / "a.py"
        a.write_text("from common import common_func")

        b = tmp_path / "b.py"
        b.write_text("from common import common_func")

        main = tmp_path / "main.py"
        main.write_text("""
from a import something
from b import something_else
        """)

        result = traverse_dependencies(str(main), str(tmp_path))

        assert str(a.resolve()) in result
        assert str(b.resolve()) in result
        assert str(common.resolve()) in result
        # common should only appear once despite being imported by both a and b
        assert len(result) == 3

    def test_unreadable_file_handling(self, tmp_path):
        """Test that unreadable files are handled gracefully."""

        dep = tmp_path / "dep.py"
        dep.write_text("def func(): pass")
        # Make file unreadable
        dep.chmod(0o000)

        main = tmp_path / "main.py"
        main.write_text("from dep import func")

        try:
            # Should not crash, just skip the unreadable file
            result = traverse_dependencies(str(main), str(tmp_path))
            # Result might be empty or contain dep depending on permissions
        finally:
            # Restore permissions for cleanup
            dep.chmod(0o644)

    def test_java_package_imports(self, tmp_path):
        """Test Java-style package imports."""
        # Create Java file structure
        com_dir = tmp_path / "com" / "example"
        com_dir.mkdir(parents=True)

        util_file = com_dir / "Util.java"
        util_file.write_text("package com.example; public class Util {}")

        main_file = com_dir / "Main.java"
        main_file.write_text("""
package com.example;
import com.example.Util;
public class Main {}
        """)

        result = traverse_dependencies(str(main_file), str(tmp_path))

        assert str(util_file.resolve()) in result

    def test_empty_file(self, tmp_path):
        """Test handling of empty files."""

        empty = tmp_path / "empty.py"
        empty.write_text("")

        result = traverse_dependencies(str(empty), str(tmp_path))

        assert len(result) == 0

    def test_file_with_no_imports(self, tmp_path):
        """Test file with no import statements."""

        main = tmp_path / "main.py"
        main.write_text("""
def my_function():
    return 42

if __name__ == '__main__':
    print(my_function())
        """)

        result = traverse_dependencies(str(main), str(tmp_path))

        assert len(result) == 0

    def test_multiple_base_paths(self, tmp_path):
        """Test multi-module project with multiple base paths."""
        # Create multi-module structure:
        # module1/
        #   utils.py
        # module2/
        #   helpers.py
        # main.py (imports from both modules)

        module1 = tmp_path / "module1"
        module1.mkdir()
        utils = module1 / "utils.py"
        utils.write_text("def util_func(): pass")

        module2 = tmp_path / "module2"
        module2.mkdir()
        helpers = module2 / "helpers.py"
        helpers.write_text("def helper_func(): pass")

        main = tmp_path / "main.py"
        main.write_text("""
from utils import util_func
from helpers import helper_func
        """)

        # Use multiple base paths
        base_paths = [str(module1), str(module2)]
        result = traverse_dependencies(str(main), base_paths)

        assert str(utils.resolve()) in result
        assert str(helpers.resolve()) in result
        assert len(result) == 2

    def test_multiple_base_paths_with_priority(self, tmp_path):
        """Test that first matching base path is used when file exists in multiple locations."""
        # Create structure where same file exists in multiple modules

        module1 = tmp_path / "module1"
        module1.mkdir()
        config1 = module1 / "config.py"
        config1.write_text("VERSION = 1")

        module2 = tmp_path / "module2"
        module2.mkdir()
        config2 = module2 / "config.py"
        config2.write_text("VERSION = 2")

        main = tmp_path / "main.py"
        main.write_text("from config import VERSION")

        # First base path should win
        base_paths = [str(module1), str(module2)]
        result = traverse_dependencies(str(main), base_paths)

        assert str(config1.resolve()) in result
        assert str(config2.resolve()) not in result
        assert len(result) == 1

    def test_cross_module_dependencies(self, tmp_path):
        """Test dependencies that span across multiple modules."""
        # Create structure:
        # module1/
        #   a.py -> imports b from module2
        # module2/
        #   b.py -> imports c from module3
        # module3/
        #   c.py
        # main.py -> imports a from module1

        module1 = tmp_path / "module1"
        module1.mkdir()
        module2 = tmp_path / "module2"
        module2.mkdir()
        module3 = tmp_path / "module3"
        module3.mkdir()

        c = module3 / "c.py"
        c.write_text("def c_func(): pass")

        b = module2 / "b.py"
        b.write_text("from c import c_func")

        a = module1 / "a.py"
        a.write_text("from b import b_func")

        main = tmp_path / "main.py"
        main.write_text("from a import a_func")

        # Use all three modules as base paths
        base_paths = [str(module1), str(module2), str(module3)]
        result = traverse_dependencies(str(main), base_paths)

        assert str(a.resolve()) in result
        assert str(b.resolve()) in result
        assert str(c.resolve()) in result
        assert len(result) == 3
