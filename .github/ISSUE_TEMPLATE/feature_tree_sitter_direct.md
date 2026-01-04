---
name: Replace RepoMap with Direct Tree-Sitter Integration
about: Technical debt - Remove Aider fork dependency, use tree-sitter directly
title: '[FEATURE] Direct Tree-Sitter Integration - Replace RepoMap'
labels: enhancement, architecture, high-priority
assignees: ''
---

## Problem Statement

Currently, CodeContextCrafter uses a forked version of Aider's RepoMap (~600 lines) as a wrapper around tree-sitter for signature generation. This creates several issues:

- **Technical debt**: Maintaining forked Aider code (1,824 statements, 86% of codebase)
- **Outdated dependencies**: Stuck on older tree-sitter API (0.24.x)
- **Unnecessary complexity**: RepoMap includes token budgeting, caching, network code we don't need
- **Determinism issues**: Had to artificially remove caching from RepoMap
- **Maintenance burden**: Keeping up with upstream Aider changes

## The Core Library: tree-sitter

RepoMap is just a wrapper around tree-sitter, which does the actual parsing:

**What tree-sitter provides:**
- Parses source code into Abstract Syntax Trees (AST)
- Language-agnostic parser generator (originally by GitHub for Atom editor)
- Python bindings: `py-tree-sitter`
- Language-specific parsers: `tree-sitter-language-pack`

**What the .scm query files do:**
- Tree-sitter's query language (S-expression based)
- Define patterns to extract (e.g., "find all function definitions")
- Located in `codecontextcrafter/aider/queries/`
- **These are valuable and well-tested** - we should keep them

**What RepoMap does (that we need to replace):**
1. Loads appropriate tree-sitter parser for language
2. Loads .scm query file for that language
3. Parses code into AST
4. Runs query against AST to extract definitions
5. Formats results as signatures
6. ~~Token budgeting~~ (we don't need)
7. ~~Caching~~ (we removed for determinism)
8. ~~Network code~~ (we don't need)

## Proposed Solution

Create a new `signature_generator.py` module with direct tree-sitter usage:

### Architecture

```
codecontextcrafter/
├── signature_generator.py          # New: Replace repomap.py
├── queries/                         # Keep: Moved from aider/queries/
│   ├── python-tags.scm
│   ├── javascript-tags.scm
│   ├── typescript-tags.scm
│   ├── java-tags.scm
│   └── ...
└── aider/                           # Delete: Remove entire fork
```

### Implementation

```python
# codecontextcrafter/signature_generator.py

from tree_sitter import Language, Parser, Query
from tree_sitter_language_pack import get_language, get_parser
from pathlib import Path
from typing import List, Dict, Optional

class SignatureGenerator:
    """Generate code signatures using tree-sitter directly."""

    def __init__(self, language: str):
        """
        Initialize generator for specific language.

        Args:
            language: Language name (python, javascript, java, etc.)
        """
        self.language = language
        self.parser = get_parser(language)
        self.ts_language = get_language(language)
        self.query = self._load_query()

    def _load_query(self) -> Query:
        """Load .scm query file for this language."""
        query_file = Path(__file__).parent / "queries" / f"{self.language}-tags.scm"
        query_text = query_file.read_text()
        return self.ts_language.query(query_text)

    def parse_file(self, file_path: str) -> List[Dict]:
        """
        Parse file and extract all definitions.

        Args:
            file_path: Path to source file

        Returns:
            List of definitions with metadata:
            [
                {
                    "name": "function_name",
                    "kind": "function",
                    "line": 42,
                    "signature": "def function_name(arg: str) -> int:",
                    "docstring": "Function description"
                },
                ...
            ]
        """
        code = Path(file_path).read_bytes()
        tree = self.parser.parse(code)

        definitions = []
        captures = self.query.captures(tree.root_node)

        for node, capture_name in captures:
            if capture_name == "name.definition.function":
                definitions.append(self._extract_function(node, code))
            elif capture_name == "name.definition.class":
                definitions.append(self._extract_class(node, code))

        return sorted(definitions, key=lambda d: d['line'])

    def _extract_function(self, node, code: bytes) -> Dict:
        """Extract function signature and metadata."""
        return {
            "name": node.text.decode(),
            "kind": "function",
            "line": node.start_point[0] + 1,
            "signature": self._get_signature(node, code),
            "docstring": self._get_docstring(node, code)
        }

    def _extract_class(self, node, code: bytes) -> Dict:
        """Extract class signature and metadata."""
        # Similar to _extract_function
        pass

    def generate_signatures(self, file_paths: List[str]) -> str:
        """
        Generate formatted signatures for multiple files.

        Args:
            file_paths: List of source files

        Returns:
            Formatted markdown with signatures
        """
        output = []

        for file_path in file_paths:
            output.append(f"\n### {file_path}\n")

            definitions = self.parse_file(file_path)
            for defn in definitions:
                # Format: line_number: signature
                output.append(f"{defn['line']}: {defn['signature']}")
                if defn['docstring']:
                    output.append(f"    \"\"\"{defn['docstring']}\"\"\"")
                output.append("")  # blank line

        return "\n".join(output)
```

### Usage Example

```python
# Old (via RepoMap)
from codecontextcrafter.aider.repomap import RepoMap
repo_map = RepoMap(map_tokens=4000, root='.', ...)
signatures = repo_map.get_repo_map(chat_files=[], other_files=files)

# New (direct tree-sitter)
from codecontextcrafter.signature_generator import SignatureGenerator
generator = SignatureGenerator(language='python')
signatures = generator.generate_signatures(file_paths)
```

## Technical Design

### What to Keep from Aider

1. **Query files (.scm)** - Well-tested patterns for extraction
   - Move from `codecontextcrafter/aider/queries/` → `codecontextcrafter/queries/`
   - Keep all existing .scm files unchanged

2. **Query logic** - The patterns work well
   - Function definitions
   - Class definitions
   - Method definitions
   - Import statements

### What to Replace

1. **repomap.py** (~600 lines) → `signature_generator.py` (~200 lines)
2. **All Aider support files**:
   - `io.py` (776 lines) - I/O utilities we don't need
   - `utils.py` (228 lines) - General utilities
   - `mdstream.py` (100 lines) - Markdown streaming
   - `waiting.py` (121 lines) - Async utilities
   - `editor.py` (53 lines) - Editor integration
   - `dump.py` (20 lines) - Debug utilities

3. **Use latest tree-sitter API**:
   - Upgrade: `tree-sitter==0.24.0` → `tree-sitter>=0.25.0`
   - Use modern `QueryCursor` API
   - Better performance, cleaner API

### Dependencies Before/After

**Before:**
```
tiktoken>=0.5.0
tree-sitter==0.24.0
grep-ast>=0.3.0
pygments>=2.15.0
tqdm>=4.65.0
networkx>=3.0
numpy>=1.26.0
scipy>=1.15.0
diskcache>=5.6.0
rich>=13.0.0
prompt-toolkit>=3.0.0
packaging>=23.0
oslex>=0.1.0
```

**After:**
```
tree-sitter>=0.25.0
tree-sitter-language-pack>=0.1.0  # Or individual language parsers
tiktoken>=0.5.0  # Only if we do token counting
```

**Reduction:** 13 dependencies → 2-3 dependencies

### File Structure Before/After

**Before (2,110 statements):**
```
codecontextcrafter/
├── code_context_crafter.py      137 statements
├── config_parser.py              62 statements
├── traverser/
│   └── traverse_dependencies.py  82 statements
└── aider/                        1,824 statements (86% of codebase!)
    ├── repomap.py                458 statements
    ├── io.py                     776 statements
    ├── utils.py                  228 statements
    └── ...
```

**After (~500 statements):**
```
codecontextcrafter/
├── code_context_crafter.py      137 statements
├── config_parser.py              62 statements
├── signature_generator.py       200 statements (new)
├── traverser/
│   └── traverse_dependencies.py  82 statements
└── queries/                      (moved from aider/queries/)
    ├── python-tags.scm
    ├── javascript-tags.scm
    └── ...
```

## Phased Rollout

### Phase 1: Implement Core SignatureGenerator (Week 1)
- [ ] Create `signature_generator.py`
- [ ] Move `.scm` query files to `codecontextcrafter/queries/`
- [ ] Implement for Python only (primary use case)
- [ ] Add basic tests
- [ ] Keep RepoMap in parallel (dual implementation)

### Phase 2: Extend to All Languages (Week 2)
- [ ] Implement JavaScript/TypeScript support
- [ ] Implement Java support
- [ ] Implement Go, Rust, C/C++ support
- [ ] Comprehensive tests for all languages

### Phase 3: Integration & Migration (Week 3)
- [ ] Update `code_context_crafter.py` to use new generator
- [ ] Add configuration option: `--use-legacy-repomap` flag
- [ ] Update documentation
- [ ] Test against real projects (Spring Boot, commons-lang)

### Phase 4: Cleanup (Week 4)
- [ ] Remove `codecontextcrafter/aider/` directory
- [ ] Remove unused dependencies from `pyproject.toml`
- [ ] Update test coverage (should go from 45% → 90%+)
- [ ] Release v2.0.0

## Success Criteria

1. **Functionality**: Generate identical or better signatures than RepoMap
2. **Performance**: At least as fast as current implementation
3. **Test coverage**: Maintain 98%+ coverage on new code
4. **Codebase size**: Reduce from 2,110 → ~500 statements
5. **Dependencies**: Reduce from 13 → 2-3 dependencies
6. **Determinism**: 100% deterministic output (no caching issues)

## Benefits

### Immediate Benefits
- ✅ **Simpler codebase**: ~500 statements vs 2,110
- ✅ **Fewer dependencies**: 2-3 vs 13
- ✅ **Modern API**: tree-sitter 0.25.x with QueryCursor
- ✅ **100% owned code**: No forked dependencies to maintain
- ✅ **Deterministic**: No caching complications

### Long-term Benefits
- ✅ **Easier to extend**: Add new languages by adding .scm query
- ✅ **Better performance**: Latest tree-sitter optimizations
- ✅ **Cleaner architecture**: Single responsibility
- ✅ **Easier testing**: No complex mock requirements
- ✅ **Better coverage**: From 45% → 90%+ (removing untested Aider code)

## Open Questions

1. **Token counting**: Do we still need token-based signature limiting?
   - Option A: Remove entirely (users control via `--dep-depth-max`)
   - Option B: Simple character/line count limits
   - Option C: Keep tiktoken for accurate LLM token counting

2. **Signature detail level**: How much detail per function?
   - Current: Function signature + docstring
   - Option: Include parameter types, return type, decorators?

3. **Query file maintenance**: How to keep .scm files updated?
   - Keep Aider's queries as reference
   - Create our own optimized queries
   - Contribute improvements back to tree-sitter community

4. **Backward compatibility**: Support for old output format?
   - v2.0.0 breaking change vs compatibility mode

## Related Issues

- #TBD Enhanced import detection (could use same tree-sitter infrastructure)
- #TBD Line-level annotations (tree-sitter provides line numbers)

## Additional Notes

This is a **high-priority architectural improvement** that should be completed before:
- Heavy marketing/adoption efforts
- PyPI publication
- MCP server implementation

It addresses the fundamental technical debt in the project and sets a solid foundation for future features.
