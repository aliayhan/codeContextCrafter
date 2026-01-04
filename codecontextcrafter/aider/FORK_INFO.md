# Aider RepoMap Fork Information

## Attribution

This directory contains code derived from the **Aider** project:
- **Project**: Aider - AI pair programming in your terminal
- **Original Author**: Paul Gauthier and contributors
- **Source Version**: v0.86.1
- **Original Repository**: https://github.com/Aider-AI/aider
- **License**: Apache License 2.0
- **Copyright**: Copyright 2023-2024 Paul Gauthier

## License Compliance

Both Aider and CodeContextCrafter are licensed under the Apache License 2.0, making them fully compatible. All modifications to the Aider code remain under the Apache License 2.0.

Original Aider license: https://github.com/Aider-AI/aider/blob/main/LICENSE.txt

## Why We Vendored (Forked) This Code

CodeContextCrafter requires specific behavior from RepoMap that differs fundamentally from Aider's design goals:

### 1. **No Caching (Deterministic Behavior)**
- **Aider**: Uses SQLite-based disk cache (`.aider.tags.cache.v*`) and in-memory caching for performance in interactive CLI sessions
- **Our Need**: Stateless, deterministic execution for batch processing
- **Change**: Removed all caching layers (disk and memory)

### 2. **Include All Files (No Token Budget Subsetting)**
- **Aider**: Uses binary search algorithm to find optimal subset of files that fit within token budget
- **Our Need**: Generate signatures for ALL requested files, regardless of token count
- **Change**: Removed binary search optimization in `get_ranked_tags_map_uncached`

### 3. **Extended Line Length Limit**
- **Aider**: Truncates output lines to 100 characters (prevents minified JS from breaking display)
- **Our Need**: Preserve long file paths and code lines for AI context
- **Change**: Increased truncation limit from 100 to 1000 characters

### 4. **Configurable Signature Detail**
- **Aider**: Fixed signature detail level
- **Our Need**: Optional wider signatures with child context
- **Change**: Added `sig_detailed` parameter

## Files Included from Aider

The following files are vendored from Aider v0.86.1 with modifications:

- `repomap.py` - Core repo mapping logic (MODIFIED - see below)
- `io.py` - Input/output utilities (MINOR MODIFICATIONS - import paths)
- `dump.py` - Debug dumping utility (UNMODIFIED)
- `special.py` - Important files filter (UNMODIFIED)
- `waiting.py` - Progress spinners (MINOR MODIFICATIONS - import paths)
- `mdstream.py` - Markdown streaming (MINOR MODIFICATIONS - import paths)
- `utils.py` - Utility functions (MINOR MODIFICATIONS - import paths)
- `editor.py` - Editor integration (MINOR MODIFICATIONS - import paths)
- `sendchat.py` - Chat utilities (MINOR MODIFICATIONS - import paths)
- `queries/**/*.scm` - Tree-sitter query files (UNMODIFIED)
- `resources/*.json` - Model metadata (UNMODIFIED)
- `resources/*.yml` - Model settings (UNMODIFIED)

## Major Modifications to repomap.py

### Summary of Changes

| Change | Lines Affected | Reason |
|--------|---------------|--------|
| Removed cache initialization | `__init__` (~3 lines) | No disk cache needed |
| Added `sig_detailed` param | `__init__`, `render_tree` | Configurable detail |
| Null-safe token checks | `get_repo_map` (~2 lines) | Allow unlimited tokens |
| Gutted tag caching | `get_tags` (~20 lines removed) | Deterministic parsing |
| Always show progress | `get_ranked_tags` (~10 lines simplified) | No cache assumptions |
| Removed binary search | `get_ranked_tags_map_uncached` (~60 lines removed) | Include all files |
| Increased truncation | `to_tree` (1 line) | 100 → 1000 chars |

### Detailed Line-by-Line Changes

See the reference file `aider_0.86.1_repomap_py.original` for the unmodified original.

**Key diffs:**

1. **Line 57-62** - Added `sig_detailed=False` parameter
2. **Line 68-69** - Removed `self.load_tags_cache()` and `self.cache_threshold`
3. **Line 109** - Changed `if self.max_map_tokens <= 0:` to `if self.max_map_tokens is not None and self.max_map_tokens <= 0:`
4. **Line 122** - Added null check: `if max_map_tokens is not None and max_map_tokens`
5. **Lines 231-238** - Gutted `get_tags()` method (removed ~20 lines of cache logic)
6. **Lines 341-345** - Simplified progress bar (removed cache size calculation)
7. **Lines 575-616** - Removed binary search algorithm (replaced ~60 lines with direct call)
8. **Line 640** - Changed `child_context=False` to `child_context=self.sig_detailed`
9. **Line 692** - Changed `line[:100]` to `line[:1000]`

## Minor Modifications to Other Files

All other files only have import path changes:
- `from aider.X import Y` → `from codecontextcrafter.aider.X import Y`

These are necessary for the vendored code to work within our package structure.

## Why Not Use Aider as a Dependency?

We evaluated using Aider as a library dependency but determined vendoring was necessary because:

1. **Architectural Incompatibility**: Changes are not configurable via parameters
2. **Core Logic Modifications**: Required overriding 5+ major methods (100+ lines)
3. **Version Fragility**: Subclass overrides would break on Aider updates
4. **Design Philosophy Mismatch**: Interactive CLI tool vs. batch processing utility

## Maintenance Strategy

- **Tracking**: We monitor Aider releases for critical bugfixes
- **Backporting**: Manually evaluate and port fixes as needed
- **Stability**: Version locked to v0.86.1 for predictable behavior
- **Documentation**: This file and original source file provide clear audit trail

## Upstream Contributions

We have not contributed these changes upstream to Aider because:
- They serve CodeContextCrafter's specific batch-processing needs
- They would contradict Aider's interactive CLI design goals
- The changes remove optimizations that are valuable for Aider's use case

## Legal Attribution

As required by Apache License 2.0 Section 4(b), this NOTICE provides attribution for the use of Aider code.

**Original Work**: Aider (https://github.com/Aider-AI/aider)
**Copyright**: Copyright 2023-2024 Paul Gauthier
**License**: Apache License 2.0
**Modifications**: Yes - See above
**Modified By**: CodeContextCrafter Contributors
**Modification Date**: January 2025

---

*For the full Apache License 2.0 text, see the LICENSE file in the project root.*
