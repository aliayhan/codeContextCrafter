import re
import os
from typing import List, Optional, Any

# Supported file extensions for dependency scanning
EXTENSIONS = ['py', 'js', 'mjs', 'ts', 'java', 'json']

# Regex patterns for extracting imports from different languages
PYTHON_IMPORT_PATTERN = r'^\s*import\s+([^\n#;/]+)'
PYTHON_FROM_IMPORT_PATTERN = r'^\s*from\s+([a-zA-Z0-9_.]+)\s+import'
JAVA_IMPORT_PATTERN = r'^\s*import\s+((?:[a-zA-Z_][\w]*\.)+[A-Za-z_][\w]*)\s*;'
JAVA_STATIC_IMPORT_PATTERN = r'^\s*import\s+static\s+((?:[a-zA-Z_][\w]*\.)+[A-Za-z_][\w]*)\.[A-Za-z_][\w]*\s*;'
typescript_imports_PATTERN = r'^\s*import(?:\s+type)?\s+(?:{[^}]*}|\*\s+as\s+\w+|\w+)?(?:\s+from)?\s*[\'"]([^\'"]+)["\']'
javascript_imports_PATTERN = r'require\s*\(\s*[\'"]([^\'"]+)["\']\s*\)'

def relative_to_absolute(base_paths: List[str], import_path: str) -> Optional[str]:
    """
    Resolve an import path to an absolute file path by trying multiple base paths.

    Args:
        base_paths: List of base directories to try (in order)
        import_path: Import path to resolve (e.g., "package.module" or "./relative")

    Returns:
        Absolute path to the resolved file, or None if not found
    """
    # Ensure base_paths is a list (backward compatibility with single string)
    if isinstance(base_paths, str):
        base_paths = [base_paths]

    path_import = import_path if import_path.startswith(('/', './', '../')) else import_path.replace('.', '/')

    # Try each base path in order
    for base_path in base_paths:
        path_candidate_basename = os.path.normpath(os.path.join(base_path, path_import))
        possible_pathes = [path_candidate_basename] + [f'{path_candidate_basename}.{ext}' for ext in EXTENSIONS]

        for possible_path in possible_pathes:
            if os.path.isfile(possible_path):
                return os.path.abspath(possible_path)

    return None


def traverse_code(code: str) -> set[Any]:
    # --- Python-style import lines ---
    raw_imports = re.findall(PYTHON_IMPORT_PATTERN, code, re.MULTILINE)
    python_modules = []
    for raw_import in raw_imports:
        if (' from ' in raw_import or
                raw_import.strip().startswith('static ') or
                ('{' in raw_import or '}' in raw_import)):
            continue
        import_parts = [i.strip().split('}')[0].strip() for i in raw_import.split(',')]
        for part in import_parts:
            if (not part or
                    (part.startswith('"') or part.startswith("'")) or
                    (part == '}') or ('*' in part)):
                continue
            python_modules.append(part)

    python_imports = re.findall(PYTHON_FROM_IMPORT_PATTERN, code, re.MULTILINE)
    java_imports = re.findall(JAVA_IMPORT_PATTERN, code, re.MULTILINE)
    java_static_imports = re.findall(JAVA_STATIC_IMPORT_PATTERN, code, re.MULTILINE)
    java_modules = java_imports + java_static_imports

    typescript_imports = re.findall(typescript_imports_PATTERN, code, re.MULTILINE)
    javascript_imports = re.findall(javascript_imports_PATTERN, code, re.MULTILINE)
    all_names = python_modules + python_imports + java_modules + typescript_imports + javascript_imports
    all_imports = set()

    for cur_name in all_names:
        if '*' in cur_name:
            continue
        name_pure = cur_name.strip().strip('"').strip("'")
        if name_pure:
            all_imports.add(name_pure)

    return all_imports


def traverse_dependencies(
    file_path: str,
    base_import_roots: Optional[List[str]],
    depth_max: Optional[int] = None,
    is_verbose: bool = False
) -> List[str]:
    """
    Traverse and discover dependencies of a file recursively.

    Args:
        file_path: Path to the source file to analyze
        base_import_roots: List of root directories for resolving imports.
                          If None, uses the file's directory.
                          For backward compatibility, can also accept a single string.
        depth_max: Maximum recursion depth (None for unlimited)
        is_verbose: Whether to print debug information

    Returns:
        List of absolute paths to all discovered dependencies
    """
    # Backward compatibility: convert string to list
    if isinstance(base_import_roots, str):
        base_import_roots = [base_import_roots]

    discovered_dependencies = set()
    already_processed = set()

    absolute_source_path = os.path.abspath(file_path)
    already_processed.add(absolute_source_path)

    bfs_q = [(absolute_source_path, 0)]

    while bfs_q:
        cur_file, cur_depth = bfs_q.pop(0)

        if depth_max is not None and cur_depth > depth_max:
            continue

        if is_verbose:
            print(f"Processing {cur_file} (depth {cur_depth})")

        try:
            with open(cur_file, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            if is_verbose:
                print(f"Error reading {cur_file}: {e}")
            continue

        file_imports = traverse_code(code)

        file_dir = os.path.dirname(cur_file)
        base_paths = [file_dir] if (base_import_roots is None) else base_import_roots

        for import_path in file_imports:
            resolved = relative_to_absolute(base_paths, import_path)

            if resolved is not None:
                absolute_resolved_path = os.path.abspath(resolved)

                if absolute_resolved_path == absolute_source_path:
                    continue

                discovered_dependencies.add(absolute_resolved_path)

                if absolute_resolved_path not in already_processed:
                    already_processed.add(absolute_resolved_path)
                    bfs_q.append((absolute_resolved_path, cur_depth + 1))

    return list(discovered_dependencies)