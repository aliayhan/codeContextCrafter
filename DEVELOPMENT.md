# Development Guide

Local development setup for CodeContextCrafter.

## Prerequisites

- Python 3.12+
- pip
- Git

## Setup

```bash
# Clone repository
git clone git@github.com:aliayhan/codeContextCrafter.git
cd codeContextCrafter

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies and package
pip install -r requirements-dev.txt
pip install -e .
```

## Clean Install

To perform a clean installation (removes build artifacts and reinstalls):

```bash
# Remove build artifacts
rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Uninstall package
pip uninstall -y codecontextcrafter

# Reinstall fresh
pip install -r requirements-dev.txt
pip install -e .
```

## Running

```bash
# As command
ccc your_file.py

# As module
python -m codecontextcrafter your_file.py
```

## Testing

### Run All Tests

```bash
# Run all 121 tests
pytest test/codecontextcrafter/

# Run with verbose output
pytest test/codecontextcrafter/ -v

# Run with progress information
pytest test/codecontextcrafter/ -v --tb=short
```

### Run Specific Test Files

```bash
# CLI integration tests (35 tests)
pytest test/codecontextcrafter/test_cli_integration.py -v

# Config parser tests (31 tests)
pytest test/codecontextcrafter/test_config_parser.py -v

# Dependency traversal tests (36 tests)
pytest test/codecontextcrafter/test_traverse_dependencies.py -v

# End-to-end workflow tests (19 tests)
pytest test/codecontextcrafter/test_end_to_end.py -v
```

### Run Specific Test Class or Method

```bash
# Run specific test class
pytest test/codecontextcrafter/test_end_to_end.py::TestEndToEnd -v

# Run specific test method
pytest test/codecontextcrafter/test_end_to_end.py::TestEndToEnd::test_multi_module_with_config -v
```

### Test Coverage

```bash
# Run tests with coverage report
pytest --cov=codecontextcrafter --cov-report=term-missing test/codecontextcrafter/

# Generate HTML coverage report
pytest --cov=codecontextcrafter --cov-report=html test/codecontextcrafter/

# Open HTML coverage report (macOS)
open htmlcov/index.html

# Open HTML coverage report (Linux)
xdg-open htmlcov/index.html
```

### Coverage Summary

CodeContextCrafter core modules achieve **98% test coverage**:
- `code_context_crafter.py`: 98%
- `config_parser.py`: 100%
- `traverse_dependencies.py`: 98%

Overall project coverage is 45% due to inclusion of third-party Aider fork components (86% of codebase).

See `TEST_COVERAGE_SUMMARY.md` for detailed coverage information.

## Project Structure

```
codecontextcrafter/
├── codecontextcrafter/              # Main package
│   ├── code_context_crafter.py      # CLI logic and main entry point
│   ├── config_parser.py             # Configuration file parsing
│   ├── traverser/                   # Dependency traversal
│   │   └── traverse_dependencies.py # Import parsing and resolution
│   └── aider/                       # Forked Aider components
│       ├── repomap.py               # Code signature generation
│       ├── io.py                    # I/O utilities
│       └── ...                      # Other Aider utilities
├── test/                            # Test suite (121 tests)
│   └── codecontextcrafter/
│       ├── test_cli_integration.py  # CLI component tests
│       ├── test_config_parser.py    # Config file tests
│       ├── test_traverse_dependencies.py  # Traversal tests
│       └── test_end_to_end.py       # E2E workflow tests
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Development dependencies
├── pyproject.toml                   # Package configuration
├── TEST_COVERAGE_SUMMARY.md         # Test coverage details
└── DEVELOPMENT.md                   # This file
```
