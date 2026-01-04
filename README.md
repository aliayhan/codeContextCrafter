# CodeContextCrafter

Build optimized code context for AI assistants with intelligent dependency tracking.

## Overview

When working with AI coding tools, providing the right context is crucial. CodeContextCrafter analyzes your codebase and generates compact, focused context by:
- Delivering complete source code for your target files
- Generating condensed signatures for imported dependencies
- Automatically traversing import chains across your project

## Use Cases

### Controlled Context for LLM Interactions

Work effectively with AI assistants while managing constraints:

- **Large codebases**: Handle 100k+ LOC projects that exceed context windows
- **Security requirements**: Share specific code segments without exposing proprietary systems
- **Focused assistance**: Prevent AI from refactoring unrelated code
- **Token budgets**: Keep costs practical for frequent interactions

Select target files for complete inclusion while automatically pulling dependency signatures.

### Automated Code Review Pipelines

Integrate with CICD workflows and MCP-based review systems:

**Traditional problem**: Git diffs lack context, but full repository scans waste resources.

**CCC approach**:
1. Identify modified files from version control
2. Extract dependencies automatically
3. Package context: full source for changes, signatures for dependencies
4. Provide to review systems via MCP or direct integration

**Example integration**:
```bash
# Generate focused review context for changed files
git diff --name-only origin/main | xargs ccc --dep-depth-max 1 -o review.md

# Use with MCP server for automated reviews
mcp-server --context review.md --reviewer claude
```

Benefits: Reviewers (human or AI) get necessary background without repository-wide scanning.

## Installation

Install the package to use the `ccc` command anywhere:

```bash
pip install -e .
```

After installation, the `ccc` command will be available in your terminal.

**For development:**
```bash
pip install -r requirements-dev.txt
pip install -e .
```

## Quick Start

```bash
# Process a single file with dependency resolution
ccc main.py

# Limit dependency traversal depth
ccc main.py --dep-depth-max 2

# Write output to a file
ccc main.py -o context.md

# Create signature-only output
ccc --find-by "find src -name '*.py'" --sig-only

# For complex projects, use a config file (see Configuration section below)
# CCC automatically loads .ccc.conf from current directory
echo "root = ./src" > .ccc.conf
ccc main.py  # Now uses config settings
```

## Configuration File (.ccc.conf)

For complex projects, especially multi-module repositories, create a `.ccc.conf` file in your project root. CCC automatically discovers and loads it from the current directory.

### Configuration Format

```ini
# .ccc.conf - Project configuration for CodeContextCrafter

# IMPORTANT: You can specify multiple root paths!
# Simply repeat the 'root' line for each module/source directory
# This enables dependency resolution across module boundaries

# Example 1: Single module project
root = /path/to/project/src/main/java

# Example 2: Multi-module project (just repeat the line!)
root = /path/to/module1/src/main/java
root = /path/to/module2/src/main/java
root = /path/to/module3/src/main/java

# Maximum dependency traversal depth
dep_depth_max = 3

# Signature token limit (controls detail level)
sig_tokens = 4000

# Verbose output for debugging
verbose = false

# Output file path
output = context.md
```

**Key Feature: Multiple Root Paths**

The `root` parameter can be repeated as many times as needed. This is essential for:
- **Multi-module Java projects** (e.g., Spring Boot, Maven multi-module)
- **Monorepos** with multiple packages
- **Projects with split source directories** (e.g., separate `src` and `lib` folders)

When CCC encounters an import, it tries each root path in order until it finds a match.

### Parameter Precedence

Settings are applied in this order (highest priority first):
1. **CLI arguments** - Always override everything
2. **Config file** - Applied if no CLI argument provided
3. **Built-in defaults** - Used when neither CLI nor config specify

**Example:**
```bash
# Config has: dep_depth_max = 3
ccc MyFile.java --dep-depth-max 1  # Uses dep-depth-max = 1 (CLI wins)
ccc MyFile.java                    # Uses dep-depth-max = 3 (from config)
```

### Supported Config Parameters

All CLI parameters can be specified in the config file:
- **`root`** - Project root(s) for import resolution
  ⚡ **Can be repeated multiple times** for multi-module projects!
  Example: `root = /module1/src` and `root = /module2/src`
- `dep_depth_max` - Maximum dependency depth (integer)
- `sig_tokens` - Token limit for signatures (integer)
- `verbose` - Enable verbose output (`true` or `false`)
- `sig_only` - Signature-only mode (`true` or `false`)
- `output` - Default output file path (string)
- `find_by` - Shell command for file discovery (string)

## Real-World Example: Apache Commons Lang

Let's analyze the [Apache Commons Lang](https://github.com/apache/commons-lang) library - a popular Java utility library with complex interdependencies.

### Project Structure
```
commons-lang/
├── src/main/java/org/apache/commons/lang3/
│   ├── exception/
│   │   └── ExceptionUtils.java  (imports ArrayUtils, ClassUtils, etc.)
│   ├── ArrayUtils.java
│   ├── ClassUtils.java
│   ├── StringUtils.java
│   └── ...
```

### Step 1: Create Configuration

Create `.ccc.conf` in the commons-lang directory:

```ini
# .ccc.conf for Apache Commons Lang

# Single module project
root = /path/to/commons-lang/src/main/java

# Moderate depth for utility libraries
dep_depth_max = 3

# Limit signature detail for large files
sig_tokens = 4000

# Don't be verbose by default
verbose = false
```

### Step 2: Analyze a File

```bash
cd commons-lang

# Analyze ExceptionUtils with its dependencies
ccc src/main/java/org/apache/commons/lang3/exception/ExceptionUtils.java

# Output includes:
# - Full source: ExceptionUtils.java
# - Signatures for: ArrayUtils, ClassUtils, StringUtils, MethodUtils, etc.
```

### Step 3: Control Depth

```bash
# Direct dependencies only (depth 0)
ccc --dep-depth-max 0 src/main/java/org/apache/commons/lang3/exception/ExceptionUtils.java
# Result: 5 files (ExceptionUtils + 4 discovered dependencies)

# One level deep (depth 1) - override config
ccc --dep-depth-max 1 src/main/java/org/apache/commons/lang3/exception/ExceptionUtils.java
# Result: 16 files (includes transitive dependencies)

# Use config default (depth 3)
ccc src/main/java/org/apache/commons/lang3/exception/ExceptionUtils.java
# Result: 43 files (deep traversal)
```

### Step 4: Save for AI Analysis

```bash
# Generate context for AI code review
ccc src/main/java/org/apache/commons/lang3/exception/ExceptionUtils.java \
  --dep-depth-max 1 \
  --output analysis.md

# Now share analysis.md with your AI assistant for:
# - Code review
# - Refactoring suggestions
# - Bug analysis
# - Documentation generation
```

### Why This Works

CodeContextCrafter automatically:
1. **Parses Java imports** in ExceptionUtils.java
2. **Resolves paths** using the configured root
3. **Finds dependencies** like `org.apache.commons.lang3.ArrayUtils`
4. **Generates signatures** for dependency files (not full source)
5. **Traverses recursively** up to the specified depth

Result: Complete context for ExceptionUtils + compact signatures for all dependencies!

## Multi-Module Java Projects

For projects like [Spring Boot](https://github.com/spring-projects/spring-boot) with multiple modules, use multiple `root` entries:

```ini
# .ccc.conf for Spring Boot

root = /path/to/spring-boot/core/spring-boot/src/main/java
root = /path/to/spring-boot/core/spring-boot-autoconfigure/src/main/java
root = /path/to/spring-boot/module/spring-boot-actuator/src/main/java

dep_depth_max = 3
sig_tokens = 4000
```

Now CCC can find dependencies across module boundaries:
```bash
# File in module A can find imports from module B
ccc module/spring-boot-hibernate/src/main/java/org/springframework/boot/hibernate/autoconfigure/metrics/HibernateMetricsAutoConfiguration.java

# Automatically discovers:
# - AutoConfiguration (from core/spring-boot-autoconfigure)
# - ConditionalOnBean (from core/spring-boot-autoconfigure)
# - HibernateJpaAutoConfiguration (from module/spring-boot-hibernate)
```

## Capabilities

- **Language support**: Python, JavaScript, TypeScript, Java
- **Automatic imports**: Tracks and resolves import statements
- **Token management**: Configure signature verbosity via `--sig-tokens`
- **File discovery**: Leverage shell commands or patterns for file selection

## CLI Options

| Option | Purpose |
|--------|---------|
| `-c, --config` | Path to configuration file (auto-discovers `.ccc.conf` in current directory) |
| `-r, --root` | Specify project root for import resolution (can be overridden from config) |
| `-o, --output` | Write results to file instead of stdout |
| `-st, --sig-tokens` | Configure maximum token count for signatures |
| `-f, --find-by` | Execute shell command to locate files |
| `-dm, --dep-depth-max` | Set maximum depth for dependency traversal |
| `-so, --sig-only` | Output signatures exclusively, no full sources |
| `-sd, --sig-detailed` | Generate more comprehensive signatures |
| `-v, --verbose` | Enable diagnostic output |

## Usage Examples

### Analyzing Python Code
```bash
ccc app/main.py --root . --dep-depth-max 3 -o prompt.md
```

### Processing TypeScript
```bash
ccc src/index.ts --find-by "find src -name '*.ts'"
```

### Working with Java
```bash
ccc src/main/java/com/example/Main.java --root src/main/java
```

### Generating Signature Maps
```bash
ccc --find-by "find . -name '*.py'" --sig-only -o signatures.md
```

## Development Setup

Refer to [DEVELOPMENT.md](DEVELOPMENT.md) for comprehensive development instructions.

```bash
# Install dependencies and verify installation
pip install -r requirements-dev.txt
python -m codecontextcrafter --help
```

## Credits

This project incorporates a customized implementation of [Aider](https://github.com/Aider-AI/aider)'s RepoMap functionality.
Detailed modification information is available in [`codecontextcrafter/aider/FORK_INFO.md`](codecontextcrafter/aider/FORK_INFO.md).

## Licensing

Released under Apache License 2.0 - Full text in [LICENSE](LICENSE)

Contains modified code from [Aider](https://github.com/Aider-AI/aider) (Copyright 2023-2024 Paul Gauthier), licensed under Apache 2.0.
