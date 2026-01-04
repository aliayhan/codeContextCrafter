---
name: Enhanced Import Detection Across All Languages
about: Replace regex-based import parsing with language-specific AST parsers
title: '[FEATURE] Enhanced Import Detection with AST Parsers'
labels: enhancement, parser, medium-priority
assignees: ''
---

## Problem Statement

Current import detection in `traverse_dependencies.py` uses simple regex patterns, which causes several issues:

**Current Limitations:**
- **Fragile parsing**: Regex patterns miss edge cases
  - Python: `__import__()`, `importlib.import_module()`, conditional imports
  - JavaScript: Dynamic `import()`, path aliases from `tsconfig.json`
  - Java: Static imports, wildcard imports, complex package resolution
- **No context understanding**: Can't distinguish comments from actual imports
- **Poor error handling**: Invalid syntax causes regex failures
- **Limited accuracy**: ~70% success rate on complex real-world code

**Example Failures:**

```python
# Python - These are missed by current regex
import os if sys.platform == 'linux' else None  # Conditional
pkg = __import__('utils')  # Dynamic import
importlib.import_module('config')  # Programmatic import
```

```javascript
// JavaScript - These are missed
const utils = await import('./utils.js');  // Dynamic import
import type { User } from '@types/user';  // TypeScript type-only
import * as helpers from '~/helpers';  // Path alias
```

```java
// Java - Complex imports
import static com.example.Utils.*;  // Static imports
import com.example.{Class1, Class2};  // Multiple in one line
```

## Proposed Solution

Replace regex-based parsing with **language-specific AST parsers** for accurate import extraction.

### Architecture Overview

```
codecontextcrafter/traverser/
├── __init__.py
├── traverse_dependencies.py      # Main orchestrator (keeps BFS logic)
├── parsers/                       # New: Language-specific parsers
│   ├── __init__.py
│   ├── base.py                    # Abstract base class
│   ├── python_parser.py           # Uses Python's ast module
│   ├── javascript_parser.py       # Uses @babel/parser
│   ├── typescript_parser.py       # Uses TypeScript compiler API
│   └── java_parser.py             # Uses tree-sitter or javaparser
```

### Core Abstractions

```python
# codecontextcrafter/traverser/parsers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class ImportKind(Enum):
    """Type of import statement."""
    STATIC = "static"           # import os
    FROM = "from"               # from os import path
    DYNAMIC = "dynamic"         # __import__(), import()
    WILDCARD = "wildcard"       # from x import *
    TYPE_ONLY = "type_only"     # TypeScript type imports

@dataclass
class Import:
    """Represents a single import statement."""
    module: str                 # e.g., "os", "./utils", "com.example.Class"
    kind: ImportKind           # Type of import
    imported_names: List[str]  # Specific names: ["func1", "func2"]
    alias: Optional[str]       # e.g., "pd" in "import pandas as pd"
    line_number: int           # Line where import appears
    is_relative: bool          # True for "./utils", "../config"
    raw_statement: str         # Original import statement

    def __str__(self):
        return f"{self.kind.value}: {self.module} @ line {self.line_number}"

class ImportParser(ABC):
    """Abstract base class for language-specific import parsers."""

    @abstractmethod
    def extract_imports(self, file_path: str) -> List[Import]:
        """
        Extract all imports from a source file.

        Args:
            file_path: Path to source file

        Returns:
            List of Import objects with metadata

        Raises:
            ParseError: If file cannot be parsed
        """
        pass

    @abstractmethod
    def resolve_import(
        self,
        import_obj: Import,
        base_paths: List[str],
        current_file: str
    ) -> Optional[str]:
        """
        Resolve import to absolute file path.

        Args:
            import_obj: Import to resolve
            base_paths: Project root paths
            current_file: File containing the import

        Returns:
            Absolute path to imported file, or None if not found
        """
        pass
```

## Technical Design by Language

### Python Parser (Highest Priority)

**Implementation:** Use Python's built-in `ast` module

```python
# codecontextcrafter/traverser/parsers/python_parser.py

import ast
from pathlib import Path
from typing import List, Optional

class PythonParser(ImportParser):
    """Parse Python imports using ast module."""

    def extract_imports(self, file_path: str) -> List[Import]:
        """Extract imports using AST parsing."""
        code = Path(file_path).read_text(encoding='utf-8')
        tree = ast.parse(code, filename=file_path)

        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # import os, sys
                for alias in node.names:
                    imports.append(Import(
                        module=alias.name,
                        kind=ImportKind.STATIC,
                        imported_names=[],
                        alias=alias.asname,
                        line_number=node.lineno,
                        is_relative=False,
                        raw_statement=ast.unparse(node)
                    ))

            elif isinstance(node, ast.ImportFrom):
                # from os import path
                if node.module is None:
                    continue  # Skip malformed imports

                imports.append(Import(
                    module=node.module,
                    kind=ImportKind.FROM,
                    imported_names=[a.name for a in node.names],
                    alias=None,
                    line_number=node.lineno,
                    is_relative=node.level > 0,
                    raw_statement=ast.unparse(node)
                ))

            elif isinstance(node, ast.Call):
                # __import__('module') or importlib.import_module('module')
                if self._is_dynamic_import(node):
                    module = self._extract_dynamic_module(node)
                    if module:
                        imports.append(Import(
                            module=module,
                            kind=ImportKind.DYNAMIC,
                            imported_names=[],
                            alias=None,
                            line_number=node.lineno,
                            is_relative=False,
                            raw_statement=ast.unparse(node)
                        ))

        return imports

    def _is_dynamic_import(self, node: ast.Call) -> bool:
        """Check if call is __import__() or importlib.import_module()."""
        if isinstance(node.func, ast.Name):
            return node.func.id == '__import__'
        elif isinstance(node.func, ast.Attribute):
            return (
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'importlib' and
                node.func.attr == 'import_module'
            )
        return False

    def resolve_import(
        self,
        import_obj: Import,
        base_paths: List[str],
        current_file: str
    ) -> Optional[str]:
        """Resolve Python import to file path."""
        if import_obj.is_relative:
            # Relative import: from ..utils import func
            return self._resolve_relative(import_obj, current_file)
        else:
            # Absolute import: from package.module import func
            return self._resolve_absolute(import_obj, base_paths)

    def _resolve_relative(self, import_obj: Import, current_file: str) -> Optional[str]:
        """Resolve relative import based on current file location."""
        # Implementation details...
        pass

    def _resolve_absolute(self, import_obj: Import, base_paths: List[str]) -> Optional[str]:
        """Try each base path to find the module."""
        # Implementation details...
        pass
```

**Benefits:**
- ✅ Built-in, no extra dependencies
- ✅ 100% accurate for valid Python code
- ✅ Handles all Python syntax: f-strings, walrus operator, etc.
- ✅ Line-accurate error messages

### JavaScript/TypeScript Parser

**Implementation:** Use `@babel/parser` via subprocess or JavaScript ecosystem tools

**Option 1: Python wrapper around babel**
```python
# codecontextcrafter/traverser/parsers/javascript_parser.py

import json
import subprocess
from pathlib import Path

class JavaScriptParser(ImportParser):
    """Parse JavaScript imports using @babel/parser."""

    def __init__(self):
        # Ensure babel is available
        self._check_babel_installed()

    def extract_imports(self, file_path: str) -> List[Import]:
        """Extract imports by calling babel parser."""
        # Call Node.js script that uses @babel/parser
        result = subprocess.run(
            ['node', 'parse_imports.js', file_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise ParseError(f"Failed to parse {file_path}: {result.stderr}")

        # Parse JSON output from Node.js script
        imports_data = json.loads(result.stdout)
        return [Import(**data) for data in imports_data]
```

**Option 2: Use dependency-cruiser (existing tool)**
```bash
# dependency-cruiser is purpose-built for this
npm install -g dependency-cruiser

# Returns JSON with all dependencies
dependency-cruiser src/main.js --output-type json
```

**Option 3: Use tree-sitter (aligns with #TBD tree-sitter migration)**
```python
# Reuse tree-sitter infrastructure from signature generation
from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_parser

class JavaScriptParser(ImportParser):
    def __init__(self):
        self.parser = get_parser('javascript')
        self.query = self._load_import_query()

    def extract_imports(self, file_path: str) -> List[Import]:
        code = Path(file_path).read_bytes()
        tree = self.parser.parse(code)

        # Use tree-sitter query to find import statements
        captures = self.query.captures(tree.root_node)
        # Parse captures into Import objects
```

**Recommendation:** Option 3 (tree-sitter) - aligns with architecture goal

### Java Parser

**Implementation:** Use tree-sitter or javaparser library

```python
# codecontextcrafter/traverser/parsers/java_parser.py

from tree_sitter import Language, Parser
from tree_sitter_language_pack import get_parser

class JavaParser(ImportParser):
    """Parse Java imports using tree-sitter."""

    def __init__(self):
        self.parser = get_parser('java')
        # Query for: import statements, static imports
        self.query_text = """
        (import_declaration
          (scoped_identifier) @import.path)

        (import_declaration
          (asterisk) @import.wildcard)
        """
        self.query = self.parser.language.query(self.query_text)

    def extract_imports(self, file_path: str) -> List[Import]:
        code = Path(file_path).read_bytes()
        tree = self.parser.parse(code)

        imports = []
        for node, capture_name in self.query.captures(tree.root_node):
            if capture_name == "import.path":
                # com.example.Utils -> com/example/Utils.java
                module = node.text.decode().replace('.', '/')
                imports.append(Import(
                    module=module,
                    kind=ImportKind.STATIC,
                    imported_names=[],
                    alias=None,
                    line_number=node.start_point[0] + 1,
                    is_relative=False,
                    raw_statement=self._get_full_statement(node)
                ))

        return imports

    def resolve_import(
        self,
        import_obj: Import,
        base_paths: List[str],
        current_file: str
    ) -> Optional[str]:
        """Resolve Java import to .java file."""
        # com.example.Utils -> find in base_paths
        # Try: base_path/com/example/Utils.java
        for base_path in base_paths:
            candidate = Path(base_path) / f"{import_obj.module}.java"
            if candidate.exists():
                return str(candidate.resolve())
        return None
```

### Parser Factory

```python
# codecontextcrafter/traverser/parsers/__init__.py

from pathlib import Path
from typing import Dict, Type
from .base import ImportParser
from .python_parser import PythonParser
from .javascript_parser import JavaScriptParser
from .java_parser import JavaParser

PARSER_REGISTRY: Dict[str, Type[ImportParser]] = {
    '.py': PythonParser,
    '.js': JavaScriptParser,
    '.jsx': JavaScriptParser,
    '.ts': JavaScriptParser,  # TypeScript uses same parser
    '.tsx': JavaScriptParser,
    '.java': JavaParser,
}

def get_parser(file_path: str) -> ImportParser:
    """
    Get appropriate parser for file.

    Args:
        file_path: Path to source file

    Returns:
        Parser instance for that language

    Raises:
        ValueError: If no parser available for file type
    """
    ext = Path(file_path).suffix.lower()
    parser_class = PARSER_REGISTRY.get(ext)

    if parser_class is None:
        raise ValueError(f"No parser available for {ext} files")

    return parser_class()
```

### Integration with traverse_dependencies.py

```python
# codecontextcrafter/traverser/traverse_dependencies.py

from .parsers import get_parser, Import

def traverse_code(file_path: str) -> List[str]:
    """
    Extract imports from a source file.

    Now uses language-specific AST parsers instead of regex.
    """
    try:
        parser = get_parser(file_path)
        imports = parser.extract_imports(file_path)

        # Filter out wildcards, type-only imports if needed
        return [
            imp.module
            for imp in imports
            if imp.kind not in [ImportKind.WILDCARD, ImportKind.TYPE_ONLY]
        ]

    except (ValueError, ParseError) as e:
        # Fall back to regex for unsupported file types
        return _traverse_code_regex_fallback(file_path)

def relative_to_absolute(
    base_paths: List[str],
    import_path: str,
    current_file: str
) -> Optional[str]:
    """
    Resolve import to absolute path.

    Now delegates to language-specific resolver.
    """
    parser = get_parser(current_file)

    # Create Import object from path
    import_obj = Import(
        module=import_path,
        kind=ImportKind.STATIC,
        imported_names=[],
        alias=None,
        line_number=0,  # Unknown when called from here
        is_relative='.' in import_path or '..' in import_path,
        raw_statement=import_path
    )

    return parser.resolve_import(import_obj, base_paths, current_file)
```

## Phased Rollout

### Phase 1: Python Parser (Week 1) - MVP
- [ ] Create `parsers/` module structure
- [ ] Implement `base.py` with abstract classes
- [ ] Implement `python_parser.py` using `ast` module
- [ ] Add comprehensive tests for Python
- [ ] Keep regex fallback for other languages
- [ ] Update documentation

**Success Criteria:**
- 100% accuracy on Python imports (vs ~70% with regex)
- All existing Python tests pass
- New tests for edge cases (dynamic imports, conditionals)

### Phase 2: JavaScript/TypeScript (Week 2)
- [ ] Implement tree-sitter-based JavaScript parser
- [ ] Handle: ES6 imports, CommonJS require, dynamic import()
- [ ] TypeScript: Handle type-only imports, path aliases
- [ ] Parse `tsconfig.json` for path mappings
- [ ] Tests against real Node.js/React projects

### Phase 3: Java & Additional Languages (Week 3)
- [ ] Implement Java parser (tree-sitter)
- [ ] Handle package resolution, static imports
- [ ] Optional: Go, Rust, C/C++ parsers
- [ ] Performance optimization

### Phase 4: Integration & Migration (Week 4)
- [ ] Remove all regex-based import parsing
- [ ] Update `traverse_dependencies.py` to use new parsers
- [ ] Comprehensive integration tests
- [ ] Performance benchmarks
- [ ] Documentation updates

## Success Criteria

1. **Accuracy**: 95%+ import detection on real-world projects
2. **Coverage**: Python, JavaScript, TypeScript, Java fully supported
3. **Performance**: No more than 2x slower than regex (acceptable tradeoff)
4. **Robustness**: Graceful handling of syntax errors
5. **Extensibility**: Easy to add new languages

## Benefits

### Immediate Benefits
- ✅ **Accuracy**: 95%+ vs ~70% with regex
- ✅ **Line numbers**: Know exactly where imports are
- ✅ **Context**: Distinguish dynamic vs static, relative vs absolute
- ✅ **Robustness**: Handle syntax errors gracefully

### Enables Future Features
- ✅ **Line-level annotations** (#TBD) - Need line numbers for AI comments
- ✅ **Import analysis** - Unused imports, circular dependencies
- ✅ **Refactoring support** - Safe import updates
- ✅ **Better diagnostics** - "Import X not found at line 42"

## Open Questions

1. **Dependency on Node.js for JavaScript parsing**:
   - Option A: Require Node.js installation (document in README)
   - Option B: Use tree-sitter (consistent with architecture)
   - Option C: Python-based JavaScript parser (limited capabilities)
   - **Recommendation**: Option B (tree-sitter)

2. **Fallback strategy for unsupported languages**:
   - Keep regex as fallback?
   - Explicitly error on unsupported types?
   - **Recommendation**: Keep regex fallback, log warning

3. **Performance vs accuracy tradeoff**:
   - AST parsing is slower but more accurate
   - Cache parsed ASTs?
   - **Recommendation**: No caching (determinism), accept slowdown

4. **Error handling philosophy**:
   - Skip files with syntax errors?
   - Report errors to user?
   - **Recommendation**: Report but continue processing other files

## Related Issues

- #TBD Direct tree-sitter integration (share parser infrastructure)
- #TBD Line-level annotations (requires line number information)
- #TBD CICD integration (better error reporting for CI)

## Testing Strategy

```python
# test/codecontextcrafter/test_parsers.py

class TestPythonParser:
    def test_simple_import(self):
        """Test: import os"""
        code = "import os"
        imports = parser.extract_imports_from_string(code)
        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].kind == ImportKind.STATIC

    def test_from_import(self):
        """Test: from os import path"""
        code = "from os import path"
        imports = parser.extract_imports_from_string(code)
        assert imports[0].module == "os"
        assert imports[0].imported_names == ["path"]

    def test_dynamic_import(self):
        """Test: __import__('module')"""
        code = "pkg = __import__('utils')"
        imports = parser.extract_imports_from_string(code)
        assert imports[0].module == "utils"
        assert imports[0].kind == ImportKind.DYNAMIC

    def test_conditional_import(self):
        """Test: import in if statement"""
        code = """
if sys.platform == 'linux':
    import linux_utils
        """
        imports = parser.extract_imports_from_string(code)
        assert len(imports) == 1
        assert imports[0].module == "linux_utils"

    def test_relative_import(self):
        """Test: from ..utils import func"""
        code = "from ..utils import func"
        imports = parser.extract_imports_from_string(code)
        assert imports[0].is_relative == True
        assert imports[0].module == "utils"
```

## Migration Path

**Backward Compatibility:**
- New parsers produce same output format as regex
- `traverse_dependencies()` API unchanged
- Tests continue to pass without modification

**Gradual Rollout:**
1. Add parsers alongside existing regex code
2. Use feature flag: `use_ast_parser=True`
3. Test extensively before making default
4. Remove regex code in v2.0.0

## Additional Notes

This feature is **prerequisite for**:
- Line-level annotation support (needs line numbers)
- Advanced dependency analysis (needs accurate import graph)
- Import optimization suggestions (needs complete picture)

Should be implemented **after**:
- Direct tree-sitter integration (#TBD) - shares parser infrastructure
