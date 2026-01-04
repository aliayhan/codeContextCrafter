---
name: Line-Level Annotation Support for AI-Generated Comments
about: Enable precise code references with line numbers for AI review comments
title: '[FEATURE] Line-Level Annotation Support'
labels: enhancement, review, high-priority
assignees: ''
---

## Problem Statement

Current signature generation produces compact summaries without line numbers, making it impossible for AI to reference specific code locations:

**Current Output:**
```markdown
## Dependencies (Signatures)

### utils.py

def process_data(data: List[str]) -> dict
def validate_input(value: str) -> bool
def format_output(result: dict) -> str
```

**Problem:** If AI wants to comment:
> "The validate_input function doesn't handle None values"

**We can't answer:**
- What line is `validate_input` on?
- How can we post a PR comment at the right location?
- How can users click to jump to the function definition?

This breaks the AI code review workflow and prevents:
- ❌ Precise PR comments (GitHub requires file + line number)
- ❌ Clickable references to dependency code
- ❌ Contextual understanding of surrounding code
- ❌ Accurate blame/history integration

## Proposed Solution

Enhance signature generation to include **line numbers and contextual information** while maintaining compact output.

### Vision: Three-Tier Context System

**Tier 1: Signature Index (Default - Compact)**
```markdown
## Dependencies (Signatures)

### utils.py

15: def process_data(data: List[str]) -> dict
    """Process incoming data and return structured result."""

42: def validate_input(value: str) -> bool
    """Validate user input string."""

67: def format_output(result: dict) -> str
    """Format result as human-readable string."""
```

**Tier 2: Enhanced Signatures (On Request - Detailed)**
```markdown
### utils.py

Function: validate_input
Line: 42-48
Signature: def validate_input(value: str) -> bool

Context:
40: def helper_function():
41:     pass
42:
43: def validate_input(value: str) -> bool:
44:     """Validate user input string."""
45:     if not value:
46:         return False
47:     return True
48:
```

**Tier 3: Full Content (On Demand - Complete)**
```python
# Full file with line numbers (when AI needs it)
# Available via MCP tool: get_file_with_lines(path, start, end)
```

### Key Features

1. **Line numbers in signatures** - Always know where code is
2. **Contextual snippets** - Show 3-5 lines around each definition
3. **On-demand detail** - AI can request full sections when needed
4. **Clickable references** - Generate GitHub URLs for navigation
5. **Smart caching** - Don't re-parse files unnecessarily

## Technical Design

### Architecture

```
codecontextcrafter/
├── signature_generator.py          # Enhanced with line tracking
├── formatters/                     # New: Output formatters
│   ├── __init__.py
│   ├── markdown_formatter.py       # Tier 1: Compact signatures
│   ├── json_formatter.py           # Tier 2: Structured JSON
│   └── review_formatter.py         # Tier 3: Review-optimized
└── mcp_server.py                   # On-demand content retrieval
```

### Core Data Structures

```python
# codecontextcrafter/signature_generator.py

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CodeDefinition:
    """Represents a function, class, or method definition."""

    name: str                   # e.g., "validate_input"
    kind: str                   # "function", "class", "method"
    line_start: int             # Start line (1-indexed)
    line_end: int               # End line (inclusive)
    signature: str              # Full signature
    docstring: Optional[str]    # Docstring if present
    parameters: List[str]       # Parameter names
    return_type: Optional[str]  # Return type annotation
    decorators: List[str]       # @staticmethod, @property, etc.
    context_before: str         # 3 lines before definition
    context_after: str          # 3 lines after definition
    file_path: str              # Absolute path to file

    def to_compact_signature(self) -> str:
        """
        Format as compact signature with line number.

        Output:
        42: def validate_input(value: str) -> bool
            \"\"\"Validate user input.\"\"\"
        """
        lines = [f"{self.line_start}: {self.signature}"]
        if self.docstring:
            lines.append(f'    """{self.docstring}"""')
        return "\n".join(lines)

    def to_detailed_signature(self) -> str:
        """
        Format as detailed signature with context.

        Output:
        Function: validate_input
        Line: 42-48
        Signature: def validate_input(value: str) -> bool

        Context:
        40: def helper_function():
        41:     pass
        42:
        43: def validate_input(value: str) -> bool:
        ...
        """
        output = []
        output.append(f"{self.kind.title()}: {self.name}")
        output.append(f"Line: {self.line_start}-{self.line_end}")
        output.append(f"Signature: {self.signature}")

        if self.docstring:
            output.append(f"Docstring: {self.docstring}")

        output.append("\nContext:")
        output.append(self.context_before)
        # Add the actual definition lines...
        output.append(self.context_after)

        return "\n".join(output)

    def to_json(self) -> dict:
        """Format as JSON for programmatic access."""
        return {
            "name": self.name,
            "kind": self.kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "parameters": self.parameters,
            "return_type": self.return_type,
            "decorators": self.decorators,
            "file_path": self.file_path
        }

    def get_github_link(self, repo_url: str, commit_sha: str) -> str:
        """
        Generate GitHub permalink to this definition.

        Returns: https://github.com/user/repo/blob/{sha}/path/file.py#L42-L48
        """
        relative_path = self.file_path  # Relative to repo root
        return f"{repo_url}/blob/{commit_sha}/{relative_path}#L{self.line_start}-L{self.line_end}"

@dataclass
class FileSignatures:
    """All signatures from a single file."""

    file_path: str
    definitions: List[CodeDefinition]
    total_lines: int
    language: str

    def to_compact_markdown(self) -> str:
        """Tier 1: Compact signatures."""
        output = [f"### {self.file_path}\n"]
        for defn in self.definitions:
            output.append(defn.to_compact_signature())
            output.append("")  # Blank line
        return "\n".join(output)

    def to_json(self) -> dict:
        """Tier 2: Structured JSON."""
        return {
            "file_path": self.file_path,
            "language": self.language,
            "total_lines": self.total_lines,
            "definitions": [d.to_json() for d in self.definitions]
        }
```

### Enhanced SignatureGenerator

```python
# codecontextcrafter/signature_generator.py

class SignatureGenerator:
    """Generate signatures with line number tracking."""

    def parse_file(self, file_path: str) -> FileSignatures:
        """
        Parse file and extract all definitions with line numbers.

        Returns:
            FileSignatures with complete metadata
        """
        code = Path(file_path).read_text()
        lines = code.splitlines()

        tree = self.parser.parse(code.encode())
        definitions = []

        captures = self.query.captures(tree.root_node)

        for node, capture_name in captures:
            if capture_name == "name.definition.function":
                defn = self._extract_function_with_context(node, lines)
                definitions.append(defn)

        return FileSignatures(
            file_path=file_path,
            definitions=sorted(definitions, key=lambda d: d.line_start),
            total_lines=len(lines),
            language=self.language
        )

    def _extract_function_with_context(
        self,
        node,
        lines: List[str]
    ) -> CodeDefinition:
        """Extract function with surrounding context."""

        line_start = node.start_point[0] + 1  # 1-indexed
        line_end = node.end_point[0] + 1

        # Get context (3 lines before/after)
        context_start = max(0, line_start - 4)  # -1 for 0-index, -3 for context
        context_end = min(len(lines), line_end + 3)

        context_before = "\n".join(
            f"{i+1}: {lines[i]}"
            for i in range(context_start, line_start - 1)
        )

        context_after = "\n".join(
            f"{i+1}: {lines[i]}"
            for i in range(line_end, context_end)
        )

        return CodeDefinition(
            name=self._get_function_name(node),
            kind="function",
            line_start=line_start,
            line_end=line_end,
            signature=self._get_signature(node, lines),
            docstring=self._get_docstring(node, lines),
            parameters=self._get_parameters(node),
            return_type=self._get_return_type(node),
            decorators=self._get_decorators(node, lines),
            context_before=context_before,
            context_after=context_after,
            file_path=file_path
        )
```

### Output Formatters

```python
# codecontextcrafter/formatters/markdown_formatter.py

class MarkdownFormatter:
    """Format signatures as Markdown with line numbers."""

    def format_signatures(
        self,
        file_signatures: List[FileSignatures],
        mode: str = "compact"
    ) -> str:
        """
        Format signatures as Markdown.

        Args:
            file_signatures: List of file signatures
            mode: "compact" (Tier 1) or "detailed" (Tier 2)

        Returns:
            Formatted Markdown string
        """
        output = ["## Dependencies (Signatures)\n"]

        for file_sigs in file_signatures:
            if mode == "compact":
                output.append(file_sigs.to_compact_markdown())
            elif mode == "detailed":
                output.append(self._format_detailed(file_sigs))

        return "\n".join(output)

    def _format_detailed(self, file_sigs: FileSignatures) -> str:
        """Format with detailed context."""
        output = [f"### {file_sigs.file_path}\n"]

        for defn in file_sigs.definitions:
            output.append(defn.to_detailed_signature())
            output.append("\n---\n")  # Separator

        return "\n".join(output)

# codecontextcrafter/formatters/json_formatter.py

class JSONFormatter:
    """Format signatures as JSON for programmatic access."""

    def format_signatures(
        self,
        file_signatures: List[FileSignatures],
        include_context: bool = False
    ) -> str:
        """Format as JSON."""
        data = {
            "dependencies": [
                fs.to_json() for fs in file_signatures
            ]
        }

        if include_context:
            # Add full context snippets
            for file_sig in data["dependencies"]:
                for defn in file_sig["definitions"]:
                    defn["context"] = {
                        "before": defn.context_before,
                        "after": defn.context_after
                    }

        return json.dumps(data, indent=2)

# codecontextcrafter/formatters/review_formatter.py

class ReviewFormatter:
    """Format signatures optimized for AI code review."""

    def format_for_review(
        self,
        changed_files: List[str],
        dependencies: List[FileSignatures],
        diff_file: Optional[str] = None,
        repo_url: Optional[str] = None,
        commit_sha: Optional[str] = None
    ) -> dict:
        """
        Format for AI code review with clickable links.

        Returns:
            {
              "changed_files": [...],
              "dependencies": [
                {
                  "file": "utils.py",
                  "definitions": [
                    {
                      "name": "validate_input",
                      "line": 42,
                      "signature": "...",
                      "link": "https://github.com/.../utils.py#L42-L48"
                    }
                  ]
                }
              ]
            }
        """
        output = {
            "changed_files": [],
            "dependencies": []
        }

        # Format dependencies with GitHub links
        for file_sigs in dependencies:
            dep_data = {
                "file": file_sigs.file_path,
                "language": file_sigs.language,
                "definitions": []
            }

            for defn in file_sigs.definitions:
                defn_data = {
                    "name": defn.name,
                    "line": defn.line_start,
                    "signature": defn.signature,
                    "docstring": defn.docstring
                }

                # Add GitHub link if repo info provided
                if repo_url and commit_sha:
                    defn_data["link"] = defn.get_github_link(repo_url, commit_sha)

                dep_data["definitions"].append(defn_data)

            output["dependencies"].append(dep_data)

        return output
```

### CLI Integration

```python
# codecontextcrafter/code_context_crafter.py

def _create_argument_parser():
    # ... existing args ...

    parser.add_argument(
        '--signature-mode',
        choices=['compact', 'detailed', 'json'],
        default='compact',
        help='Signature format: compact (line numbers only), detailed (with context), json (structured)'
    )

    parser.add_argument(
        '--with-github-links',
        action='store_true',
        help='Generate GitHub permalink URLs for definitions (requires --repo-url and --commit-sha)'
    )

    parser.add_argument(
        '--repo-url',
        type=str,
        help='GitHub repository URL (e.g., https://github.com/user/repo)'
    )

    parser.add_argument(
        '--commit-sha',
        type=str,
        help='Git commit SHA for permalinks'
    )

def _generate_code_signatures(signature_files: List[str], args) -> str:
    """Generate signatures with line numbers."""

    generator = SignatureGenerator(language='python')  # Detect from file ext

    # Parse all files
    all_signatures = []
    for file_path in signature_files:
        file_sigs = generator.parse_file(file_path)
        all_signatures.append(file_sigs)

    # Format based on mode
    if args.signature_mode == 'compact':
        formatter = MarkdownFormatter()
        return formatter.format_signatures(all_signatures, mode='compact')

    elif args.signature_mode == 'detailed':
        formatter = MarkdownFormatter()
        return formatter.format_signatures(all_signatures, mode='detailed')

    elif args.signature_mode == 'json':
        formatter = JSONFormatter()
        return formatter.format_signatures(all_signatures, include_context=True)
```

### MCP Server Integration

```python
# codecontextcrafter/mcp_server.py

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """Enhanced with line-level content retrieval."""

    if name == "get_file_with_lines":
        """
        Get file content with line numbers.

        Usage:
        - get_file_with_lines("utils.py") -> Full file
        - get_file_with_lines("utils.py", start_line=40, end_line=50) -> Snippet
        """
        file_path = arguments["file_path"]
        start_line = arguments.get("start_line", 1)
        end_line = arguments.get("end_line")

        content = read_file_with_line_numbers(
            file_path,
            start=start_line,
            end=end_line
        )

        return [TextContent(type="text", text=content)]

    elif name == "get_definition_context":
        """
        Get surrounding context for a specific definition.

        Input: {"file": "utils.py", "function": "validate_input"}
        Output: Lines 40-48 with context
        """
        file_path = arguments["file"]
        function_name = arguments["function"]

        generator = SignatureGenerator.for_file(file_path)
        file_sigs = generator.parse_file(file_path)

        # Find the definition
        for defn in file_sigs.definitions:
            if defn.name == function_name:
                return [TextContent(
                    type="text",
                    text=defn.to_detailed_signature()
                )]

        return [TextContent(type="text", text=f"Function {function_name} not found")]
```

## Usage Examples

### Example 1: Compact Signatures (Default)

```bash
ccc main.py --dep-depth-max 2
```

**Output:**
```markdown
## Dependencies (Signatures)

### utils.py

15: def process_data(data: List[str]) -> dict
    """Process incoming data and return structured result."""

42: def validate_input(value: str) -> bool
    """Validate user input string."""
```

### Example 2: Detailed Signatures

```bash
ccc main.py --dep-depth-max 2 --signature-mode detailed
```

**Output:**
```markdown
### utils.py

Function: validate_input
Line: 42-48
Signature: def validate_input(value: str) -> bool
Docstring: Validate user input string.

Context:
40: def helper_function():
41:     pass
42:
43: def validate_input(value: str) -> bool:
44:     """Validate user input string."""
45:     if not value:
46:         return False
47:     return True
48:
```

### Example 3: JSON with GitHub Links

```bash
ccc main.py --dep-depth-max 2 \
  --signature-mode json \
  --with-github-links \
  --repo-url https://github.com/user/repo \
  --commit-sha abc123
```

**Output:**
```json
{
  "dependencies": [
    {
      "file": "utils.py",
      "language": "python",
      "definitions": [
        {
          "name": "validate_input",
          "line": 42,
          "signature": "def validate_input(value: str) -> bool:",
          "docstring": "Validate user input string.",
          "link": "https://github.com/user/repo/blob/abc123/utils.py#L42-L48"
        }
      ]
    }
  ]
}
```

### Example 4: AI Review with Line References

**AI Prompt:**
```
Review this PR. You have access to:

Dependencies:
- utils.py:42 - validate_input(value: str) -> bool
- utils.py:15 - process_data(data: List[str]) -> dict

Changed file: main.py
25: + result = utils.validate_input(user.name)
```

**AI Output:**
```json
{
  "comments": [
    {
      "file": "main.py",
      "line": 25,
      "severity": "error",
      "message": "Calling validate_input without null check. See utils.py:42 for signature.",
      "suggestion": "if user and user.name:\n    result = utils.validate_input(user.name)",
      "reference": "utils.py:42"
    }
  ]
}
```

**Posted PR Comment:**
```markdown
**ERROR** at main.py:25

Calling `validate_input` without null check.

Reference: [`validate_input` @ utils.py:42](https://github.com/user/repo/blob/abc123/utils.py#L42-L48)

Suggestion:
```python
if user and user.name:
    result = utils.validate_input(user.name)
```
```

## Phased Rollout

### Phase 1: Core Line Tracking (Week 1)
- [ ] Enhance `CodeDefinition` dataclass with line numbers
- [ ] Update `SignatureGenerator` to track line ranges
- [ ] Implement compact format (Tier 1)
- [ ] Tests for line number accuracy

### Phase 2: Formatters (Week 2)
- [ ] Create formatters module
- [ ] Implement `MarkdownFormatter` (compact + detailed)
- [ ] Implement `JSONFormatter`
- [ ] CLI integration: `--signature-mode` flag

### Phase 3: Review Integration (Week 3)
- [ ] Implement `ReviewFormatter` with GitHub links
- [ ] Add `--with-github-links` flag
- [ ] MCP tool: `get_file_with_lines`
- [ ] MCP tool: `get_definition_context`

### Phase 4: Advanced Features (Week 4)
- [ ] Smart context sizing (more lines for complex functions)
- [ ] Blame integration (show last modifier)
- [ ] Historical context (show previous versions)
- [ ] Symbol jump in IDEs

## Success Criteria

1. **Accuracy**: 100% accurate line numbers for all definitions
2. **Completeness**: Track functions, classes, methods across all languages
3. **Performance**: <10% overhead vs current signature generation
4. **Usability**: AI can reference exact lines in 95%+ of comments
5. **Integration**: GitHub links work correctly in all cases

## Benefits

### For AI Code Review
- ✅ Precise PR comments with file:line references
- ✅ Clickable links to dependency definitions
- ✅ Context-aware suggestions (see surrounding code)
- ✅ Accurate blame/history integration

### For Developers
- ✅ Jump to definition from AI comments
- ✅ Understand dependency relationships visually
- ✅ Better debugging (see exact line numbers)
- ✅ IDE integration possibilities

### For CodeContextCrafter
- ✅ Enables CICD review feature (#TBD)
- ✅ Competitive advantage (most tools don't track lines)
- ✅ Foundation for advanced features (refactoring, analysis)

## Open Questions

1. **Context size**: How many lines before/after to show?
   - **Recommendation**: Configurable, default 3 lines

2. **Large functions**: What if function is 100+ lines?
   - **Recommendation**: Show first 10 + last 10, with "..." in middle

3. **GitHub link format**: Permalink vs branch link?
   - **Recommendation**: Permalink with commit SHA (permanent)

4. **Performance**: Cache line number parsing?
   - **Recommendation**: No caching (determinism), acceptable slowdown

5. **Multi-file classes**: How to handle split definitions?
   - **Recommendation**: Track each part separately with line numbers

## Related Issues

- #TBD Direct tree-sitter integration (provides line number support)
- #TBD Enhanced import detection (also needs line numbers)
- #TBD CICD review (#TBD) (depends on this feature)

## Testing Strategy

```python
# test/codecontextcrafter/test_line_annotations.py

def test_line_numbers_accuracy():
    """Test that line numbers match actual file."""
    code = '''
def helper():
    pass

def main():
    return 42
    '''

    generator = SignatureGenerator('python')
    file_sigs = generator.parse_from_string(code)

    assert file_sigs.definitions[0].line_start == 2  # helper
    assert file_sigs.definitions[1].line_start == 5  # main

def test_github_link_generation():
    """Test GitHub permalink generation."""
    defn = CodeDefinition(
        name="validate",
        line_start=42,
        line_end=48,
        file_path="src/utils.py",
        ...
    )

    link = defn.get_github_link(
        "https://github.com/user/repo",
        "abc123def"
    )

    assert link == "https://github.com/user/repo/blob/abc123def/src/utils.py#L42-L48"

def test_context_extraction():
    """Test that context before/after is captured."""
    # Test implementation...
```

## Additional Notes

This is **foundational for AI code review** and should be prioritized highly. Without line numbers, we can't:
- Post accurate PR comments
- Enable clickable references
- Integrate with CICD tools

Should be implemented **after**:
- Direct tree-sitter integration (#TBD) - provides line number support natively

Should be implemented **before**:
- CICD review feature (#TBD) - depends on this feature
