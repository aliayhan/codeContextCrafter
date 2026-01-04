# Aider Code (Vendored)

This directory contains modified code from Aider v0.86.1.

## Legal Notice

- **Original Project**: [Aider](https://github.com/Aider-AI/aider) by Paul Gauthier
- **License**: Apache License 2.0 (both original and this fork)
- **Attribution**: See NOTICE file

## Important Files

- **FORK_INFO.md** - Detailed explanation of modifications
- **NOTICE** - Legal attribution (Apache License 2.0 requirement)
- **aider_0.86.1_repomap_py.original** - Original unmodified repomap.py

## What's Included

This directory contains Aider's RepoMap functionality for generating code signatures using tree-sitter AST analysis. We use this to create condensed representations of dependency files.

**Core component**: `repomap.py`

**Supporting modules**: `io.py`, `utils.py`, `waiting.py`, `dump.py`, `special.py`, `editor.py`

**Resources**: `queries/**/*.scm` (tree-sitter queries), `resources/**` (model metadata)

## Key Modifications

1. **Removed caching** - No persistent cache files created
2. **Removed token budgeting** - Include all files regardless of size
3. **Extended line limits** - 1000 characters instead of 100
4. **Added sig_detailed parameter** - Configurable signature detail

See FORK_INFO.md for complete details.

## Why Vendored?

Using Aider as a library dependency would require:
- Overriding multiple internal methods
- Architectural changes not exposed through configuration
- Risk of breakage on version updates

Vendoring provides stability and control for our specific use case.

## Maintenance

- **Version**: Locked to Aider v0.86.1
- **Updates**: Critical bugfixes backported manually
- **Philosophy**: Stability over feature tracking

## Acknowledgments

Thanks to Paul Gauthier and Aider contributors for excellent code analysis infrastructure. Aider is a powerful AI pair programming tool available at https://github.com/Aider-AI/aider
