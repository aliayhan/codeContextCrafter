"""
Tests for config file parser and parameter precedence.
"""

import pytest
import os
import tempfile
from argparse import Namespace
from codecontextcrafter.config_parser import (
    parse_config_file,
    apply_config_defaults,
    validate_config,
    _get_default_value
)


class TestParseConfigFile:
    """Test parsing of .ccc.conf files."""

    def test_parse_simple_config(self, tmp_path):
        """Test parsing a simple config file."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
# Comment line
root = /path/to/root
dep_depth_max = 5
verbose = true
sig_only = false
        """)

        config = parse_config_file(str(config_file))

        assert config['root'] == '/path/to/root'
        assert config['dep_depth_max'] == 5
        assert config['verbose'] is True
        assert config['sig_only'] is False

    def test_parse_multiple_roots(self, tmp_path):
        """Test parsing config with multiple root paths."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
root = /path/to/module1
root = /path/to/module2
root = /path/to/module3
        """)

        config = parse_config_file(str(config_file))

        assert isinstance(config['root'], list)
        assert len(config['root']) == 3
        assert config['root'] == ['/path/to/module1', '/path/to/module2', '/path/to/module3']

    def test_parse_empty_lines_and_comments(self, tmp_path):
        """Test that empty lines and comments are ignored."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
# This is a comment

root = /path/to/root

# Another comment
dep_depth_max = 5

        """)

        config = parse_config_file(str(config_file))

        assert len(config) == 2
        assert config['root'] == '/path/to/root'
        assert config['dep_depth_max'] == 5

    def test_parse_boolean_values(self, tmp_path):
        """Test parsing of boolean values."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
verbose = true
sig_only = false
sig_detailed = True
another = False
        """)

        config = parse_config_file(str(config_file))

        assert config['verbose'] is True
        assert config['sig_only'] is False
        assert config['sig_detailed'] is True
        assert config['another'] is False

    def test_parse_integer_values(self, tmp_path):
        """Test parsing of integer values."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
dep_depth_max = 3
sig_tokens = 4000
        """)

        config = parse_config_file(str(config_file))

        assert config['dep_depth_max'] == 3
        assert config['sig_tokens'] == 4000
        assert isinstance(config['dep_depth_max'], int)
        assert isinstance(config['sig_tokens'], int)

    def test_parse_string_values(self, tmp_path):
        """Test parsing of string values."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
output = /path/to/output.md
find_by = find . -name '*.py'
        """)

        config = parse_config_file(str(config_file))

        assert config['output'] == '/path/to/output.md'
        assert config['find_by'] == "find . -name '*.py'"

    def test_parse_whitespace_handling(self, tmp_path):
        """Test that whitespace is properly handled."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
  root   =   /path/to/root
dep_depth_max=5
        """)

        config = parse_config_file(str(config_file))

        assert config['root'] == '/path/to/root'
        assert config['dep_depth_max'] == 5

    def test_parse_nonexistent_file(self):
        """Test that FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError):
            parse_config_file('/nonexistent/path/.ccc.conf')

    def test_parse_invalid_format_no_equals(self, tmp_path):
        """Test that ValueError is raised for invalid format."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
root /path/to/root
        """)

        with pytest.raises(ValueError, match="Invalid config format"):
            parse_config_file(str(config_file))

    def test_parse_empty_key(self, tmp_path):
        """Test that ValueError is raised for empty keys."""
        config_file = tmp_path / ".ccc.conf"
        config_file.write_text("""
 = value
        """)

        with pytest.raises(ValueError, match="Empty key"):
            parse_config_file(str(config_file))


class TestApplyConfigDefaults:
    """Test applying config defaults to argparse namespace."""

    def test_apply_config_when_cli_not_provided(self):
        """Test that config is applied when CLI argument is not provided."""
        args = Namespace(
            root=None,
            dep_depth_max=None,
            verbose=False,
            sig_only=False,
            output=None
        )

        config = {
            'root': '/config/root',
            'dep_depth_max': 5,
            'verbose': True
        }

        apply_config_defaults(args, config)

        assert args.root == '/config/root'
        assert args.dep_depth_max == 5
        assert args.verbose is True
        assert args.sig_only is False  # Not in config, should remain unchanged

    def test_cli_overrides_config(self):
        """Test that CLI arguments override config file settings."""
        args = Namespace(
            root='/cli/root',
            dep_depth_max=1,
            verbose=True,  # Explicitly set (user passed --verbose)
            sig_only=True  # Explicitly set (user passed --sig-only)
        )

        config = {
            'root': '/config/root',
            'dep_depth_max': 5,
            'verbose': False,
            'sig_only': False
        }

        apply_config_defaults(args, config)

        # CLI values should be preserved
        assert args.root == '/cli/root'
        assert args.dep_depth_max == 1
        assert args.verbose is True
        assert args.sig_only is True

    def test_apply_multiple_roots_from_config(self):
        """Test applying multiple root paths from config."""
        args = Namespace(root=None)

        config = {
            'root': ['/path/1', '/path/2', '/path/3']
        }

        apply_config_defaults(args, config)

        assert isinstance(args.root, list)
        assert args.root == ['/path/1', '/path/2', '/path/3']

    def test_apply_single_root_from_config(self):
        """Test applying single root path from config."""
        args = Namespace(root=None)

        config = {
            'root': '/single/path'
        }

        apply_config_defaults(args, config)

        assert args.root == '/single/path'

    def test_partial_config_application(self):
        """Test that only specified config values are applied."""
        args = Namespace(
            root=None,
            dep_depth_max=None,
            verbose=False,
            sig_only=False,
            output=None
        )

        config = {
            'dep_depth_max': 3,
            'output': '/output/file.md'
        }

        apply_config_defaults(args, config)

        assert args.root is None  # Not in config
        assert args.dep_depth_max == 3  # From config
        assert args.verbose is False  # Not in config
        assert args.output == '/output/file.md'  # From config

    def test_config_with_zero_value(self):
        """Test that zero values from config are properly applied."""
        args = Namespace(dep_depth_max=None)

        config = {
            'dep_depth_max': 0
        }

        apply_config_defaults(args, config)

        assert args.dep_depth_max == 0


class TestValidateConfig:
    """Test config validation."""

    def test_validate_valid_config(self, tmp_path):
        """Test that valid config passes validation."""
        root1 = tmp_path / "root1"
        root1.mkdir()

        config = {
            'root': str(root1),
            'dep_depth_max': 3,
            'sig_tokens': 4000,
            'verbose': True,
            'sig_only': False
        }

        # Should not raise any exception
        validate_config(config)

    def test_validate_multiple_roots(self, tmp_path):
        """Test validation with multiple root paths."""
        root1 = tmp_path / "root1"
        root1.mkdir()
        root2 = tmp_path / "root2"
        root2.mkdir()

        config = {
            'root': [str(root1), str(root2)]
        }

        # Should not raise any exception
        validate_config(config)

    def test_validate_nonexistent_root(self):
        """Test that validation fails for non-existent root paths."""
        config = {
            'root': '/nonexistent/path'
        }

        with pytest.raises(ValueError, match="Root path does not exist"):
            validate_config(config)

    def test_validate_negative_dep_depth_max(self):
        """Test that validation fails for negative dep_depth_max."""
        config = {
            'dep_depth_max': -1
        }

        with pytest.raises(ValueError, match="dep_depth_max must be a positive integer"):
            validate_config(config)

    def test_validate_negative_sig_tokens(self):
        """Test that validation fails for negative sig_tokens."""
        config = {
            'sig_tokens': -100
        }

        with pytest.raises(ValueError, match="sig_tokens must be a positive integer"):
            validate_config(config)

    def test_validate_invalid_boolean(self):
        """Test that validation fails for invalid boolean values."""
        config = {
            'verbose': 'not_a_boolean'
        }

        with pytest.raises(ValueError, match="verbose must be true or false"):
            validate_config(config)

    def test_validate_string_dep_depth_max(self):
        """Test that validation fails for string dep_depth_max."""
        config = {
            'dep_depth_max': 'three'
        }

        with pytest.raises(ValueError, match="dep_depth_max must be a positive integer"):
            validate_config(config)


class TestGetDefaultValue:
    """Test getting default values for arguments."""

    def test_get_default_root(self):
        """Test default value for root."""
        assert _get_default_value('root') is None

    def test_get_default_dep_depth_max(self):
        """Test default value for dep_depth_max."""
        assert _get_default_value('dep_depth_max') is None

    def test_get_default_verbose(self):
        """Test default value for verbose."""
        assert _get_default_value('verbose') is False

    def test_get_default_sig_only(self):
        """Test default value for sig_only."""
        assert _get_default_value('sig_only') is False

    def test_get_default_unknown_arg(self):
        """Test default value for unknown argument."""
        assert _get_default_value('unknown_arg') is None


class TestParameterPrecedence:
    """Integration tests for parameter precedence (CLI > Config > Default)."""

    def test_precedence_cli_wins(self):
        """Test that CLI arguments have highest precedence."""
        args = Namespace(
            dep_depth_max=1,  # CLI value
            verbose=True,     # CLI value
            root='/cli/root'  # CLI value
        )

        config = {
            'dep_depth_max': 5,      # Config value
            'verbose': False,        # Config value
            'root': '/config/root'   # Config value
        }

        apply_config_defaults(args, config)

        # All CLI values should win
        assert args.dep_depth_max == 1
        assert args.verbose is True
        assert args.root == '/cli/root'

    def test_precedence_config_over_default(self):
        """Test that config values override defaults."""
        args = Namespace(
            dep_depth_max=None,  # Default value
            verbose=False,       # Default value
            root=None           # Default value
        )

        config = {
            'dep_depth_max': 5,
            'verbose': True,
            'root': '/config/root'
        }

        apply_config_defaults(args, config)

        # Config values should be applied
        assert args.dep_depth_max == 5
        assert args.verbose is True
        assert args.root == '/config/root'

    def test_precedence_mixed_sources(self):
        """Test mixed sources: some from CLI, some from config, some default."""
        args = Namespace(
            dep_depth_max=1,      # CLI (explicit)
            verbose=False,        # Default (not changed)
            root=None,           # Default (not changed)
            output='/cli/out.md'  # CLI (explicit)
        )

        config = {
            'dep_depth_max': 5,          # Should be ignored (CLI wins)
            'verbose': True,             # Should be applied (was at default)
            'root': '/config/root',      # Should be applied (was at default)
            'output': '/config/out.md'   # Should be ignored (CLI wins)
        }

        apply_config_defaults(args, config)

        assert args.dep_depth_max == 1          # CLI wins
        assert args.verbose is True             # Config applied
        assert args.root == '/config/root'      # Config applied
        assert args.output == '/cli/out.md'     # CLI wins
