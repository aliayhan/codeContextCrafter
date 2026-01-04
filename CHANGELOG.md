# Changelog

All notable changes to CodeContextCrafter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-04

### Added
- **Multi-module project support**: Configure multiple root paths for dependency resolution across module boundaries
- **Configuration file system**: Auto-discovery of `.ccc.conf` files with support for repeated root entries
- **Parameter precedence**: CLI arguments override config file settings, config overrides defaults
- **Comprehensive test suite**: 121 tests achieving 98% coverage on core modules
- **Language support**: Python, JavaScript, TypeScript, Java import parsing and dependency resolution
- **Dependency traversal**: BFS-based traversal with configurable depth limiting
- **Signature generation**: Compact code signatures for dependencies using RepoMap
- **Output formatting**: Markdown with syntax highlighting for multiple languages (Python, JS, TS, Java, C/C++)
- **Error handling**: Graceful handling of invalid configs, missing files, and edge cases
- **CLI features**:
  - `--config` for explicit config file path (auto-discovers `.ccc.conf`)
  - `--root` for project root specification (supports multiple values)
  - `--dep-depth-max` for dependency traversal depth limiting
  - `--sig-only` for signature-only output mode
  - `--sig-tokens` for controlling signature detail level
  - `--find-by` for shell command-based file discovery
  - `--output` for writing to file instead of stdout
  - `--verbose` for detailed execution logging

### Technical Details
- **Core modules**:
  - `code_context_crafter.py`: Main CLI logic and orchestration (98% coverage)
  - `config_parser.py`: Configuration file parsing and validation (100% coverage)
  - `traverser/traverse_dependencies.py`: Import parsing and dependency resolution (98% coverage)
- **Third-party integration**: Forked and customized Aider RepoMap for signature generation
- **Test coverage**: 98% on core CodeContextCrafter modules (45% overall including third-party Aider fork)
- **Python requirement**: 3.12+

### Documentation
- Comprehensive README with real-world examples (Apache Commons Lang, Spring Boot)
- Configuration file format documentation with multi-module examples
- Development guide with testing instructions
- Test coverage summary explaining coverage metrics

### Use Cases
- Generate focused code context for AI coding assistants
- Automated code review pipelines with CICD integration
- Handle large codebases (100k+ LOC) within context window constraints
- Security-conscious code sharing (select specific files without exposing entire codebase)

[1.0.0]: https://github.com/aliayhan/codeContextCrafter/releases/tag/v1.0.0
