# Contributing to CodeContextCrafter

Thank you for your interest in contributing to CodeContextCrafter!

## Project Status

CodeContextCrafter v1.0.0 is a stable release with comprehensive test coverage (98% on core modules). However, we have significant architectural improvements planned:

- Direct Tree-Sitter integration (reducing dependency on forked Aider components)
- Enhanced import detection across all supported languages
- CICD/automated review architecture with MCP server integration
- Line-level annotation support for AI-generated comments

We welcome contributions aligned with these goals.

## Development Setup

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup instructions.

Quick start:
```bash
git clone git@github.com:aliayhan/codeContextCrafter.git
cd codeContextCrafter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

## Running Tests

We maintain 98% test coverage on core modules:
```bash
# Run all 121 tests
pytest test/codecontextcrafter/

# Run with coverage
pytest --cov=codecontextcrafter --cov-report=term-missing test/codecontextcrafter/
```

## Pull Request Process

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes** following existing code patterns

3. **Add tests** for new functionality:
   - Unit tests in appropriate test file
   - Maintain or improve coverage percentage
   - All tests must pass

4. **Update documentation** if needed:
   - README.md for user-facing changes
   - DEVELOPMENT.md for developer-facing changes
   - Docstrings for new functions

5. **Commit with clear messages**:
   ```bash
   git commit -m "Add feature: brief description

   Detailed explanation of what changed and why."
   ```

6. **Push and open a PR** with:
   - Clear title describing the change
   - Description explaining the motivation
   - Reference to related issues if applicable

## Code Style

- Follow existing code patterns and structure
- Add type hints to new functions
- Keep functions focused with single responsibility
- Use descriptive variable and function names
- Add docstrings for public functions

## Testing Guidelines

- Write tests before or alongside code changes
- Cover edge cases and error conditions
- Use pytest fixtures for common setup
- Keep tests isolated and independent

## Areas for Contribution

**High Priority:**
- Tree-Sitter integration improvements
- Enhanced import detection
- CICD integration examples
- MCP server implementation

**Medium Priority:**
- Additional language support
- Performance optimizations
- Documentation improvements
- Example workflows

**Good First Issues:**
- Bug fixes
- Test coverage improvements
- Documentation clarifications

## Questions or Ideas?

Open an issue to discuss:
- Architectural changes
- New features
- Significant refactoring

We appreciate your contributions!
