"""
Config file parser for CodeContextCrafter.

Supports .ccc.conf files with INI-style format.
All command-line parameters can be specified in the config file.
"""

import os
from typing import Dict, List, Optional, Any


def parse_config_file(config_path: str) -> Dict[str, Any]:
    """
    Parse a .ccc.conf configuration file.

    Format:
        # Comments start with #
        key = value
        # Keys can be repeated (e.g., multiple root paths)
        root = /path/to/module1
        root = /path/to/module2

    Args:
        config_path: Path to the config file

    Returns:
        Dictionary with config values. Keys with multiple values are stored as lists.

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file has invalid format
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    config: Dict[str, Any] = {}

    with open(config_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace and skip empty lines or comments
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Parse key = value
            if '=' not in line:
                raise ValueError(
                    f"Invalid config format at line {line_num}: '{line}'\n"
                    f"Expected format: key = value"
                )

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if not key:
                raise ValueError(f"Empty key at line {line_num}")

            # Convert boolean strings
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            # Convert integer strings (for things like dep_depth_max, sig_tokens)
            elif value.isdigit():
                value = int(value)

            # Handle multiple values for the same key (e.g., multiple root paths)
            if key in config:
                # Convert to list if not already
                if not isinstance(config[key], list):
                    config[key] = [config[key]]
                config[key].append(value)
            else:
                config[key] = value

    return config


def apply_config_defaults(args, config: Dict[str, Any]) -> None:
    """
    Apply config file values to argparse namespace.

    Only applies config values if the corresponding CLI argument
    was not explicitly provided (i.e., still has its default value).

    Args:
        args: argparse.Namespace object with CLI arguments
        config: Dictionary from parse_config_file()

    Note:
        Modifies args in-place. CLI arguments always take precedence.
    """
    # Mapping from config keys to argparse attribute names
    # Some may differ due to argparse conventions (e.g., dashes vs underscores)
    key_mapping = {
        'root': 'root',
        'dep_depth_max': 'dep_depth_max',
        'sig_tokens': 'sig_tokens',
        'output': 'output',
        'sig_only': 'sig_only',
        'verbose': 'verbose',
        'find_by': 'find_by',
    }

    # Special handling for 'root' - can be single value or list
    if 'root' in config and hasattr(args, 'root'):
        # Only apply if root wasn't specified on CLI
        # Check if it's the default value (None)
        if args.root is None:
            roots = config['root']
            # If single root, keep as string; if multiple, convert to list
            if isinstance(roots, list):
                args.root = roots
            else:
                args.root = roots

    # Apply other config values
    for config_key, args_attr in key_mapping.items():
        if config_key == 'root':
            continue  # Already handled above

        if config_key in config and hasattr(args, args_attr):
            current_value = getattr(args, args_attr)
            default_value = _get_default_value(args_attr)

            # Only apply config if CLI arg is still at default value
            if current_value == default_value or current_value is None:
                setattr(args, args_attr, config[config_key])


def _get_default_value(arg_name: str) -> Any:
    """
    Get the default value for a given argument.

    Args:
        arg_name: Name of the argument

    Returns:
        Default value for the argument
    """
    defaults = {
        'root': None,
        'dep_depth_max': None,
        'sig_tokens': None,
        'output': None,
        'sig_only': False,
        'verbose': False,
        'find_by': None,
    }
    return defaults.get(arg_name)


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate config file values.

    Args:
        config: Dictionary from parse_config_file()

    Raises:
        ValueError: If config contains invalid values
    """
    # Validate root paths exist
    if 'root' in config:
        roots = config['root'] if isinstance(config['root'], list) else [config['root']]
        for root in roots:
            if not os.path.exists(root):
                raise ValueError(f"Root path does not exist: {root}")

    # Validate numeric values are positive
    if 'dep_depth_max' in config:
        if not isinstance(config['dep_depth_max'], int) or config['dep_depth_max'] < 0:
            raise ValueError(f"dep_depth_max must be a positive integer, got: {config['dep_depth_max']}")

    if 'sig_tokens' in config:
        if not isinstance(config['sig_tokens'], int) or config['sig_tokens'] < 0:
            raise ValueError(f"sig_tokens must be a positive integer, got: {config['sig_tokens']}")

    # Validate boolean values
    for bool_key in ['sig_only', 'verbose']:
        if bool_key in config and not isinstance(config[bool_key], bool):
            raise ValueError(f"{bool_key} must be true or false, got: {config[bool_key]}")
