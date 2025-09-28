"""Unit tests for commands/config.py."""

import pytest
from unittest.mock import patch, MagicMock

from clauth.cli import app


def test_config_show_no_path(mocker, capsys):
    """Test config show command without --path flag."""
    # Mock the config manager and config
    mock_config_manager = mocker.patch("clauth.commands.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Set up mock config values
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.aws.sso_start_url = "https://example.awsapps.com/start"
    mock_config.aws.sso_region = "us-east-1"
    mock_config.aws.session_name = "test-session"
    mock_config.aws.output_format = "json"
    mock_config.models.provider_filter = "anthropic"
    mock_config.models.default_model = "claude-3-5-sonnet"
    mock_config.models.fast_model = "claude-3-5-haiku"
    mock_config.cli.claude_cli_name = "claude"
    mock_config.cli.auto_start = True
    mock_config.cli.show_progress = True
    mock_config.cli.color_output = True

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    output = result.output
    assert "AWS settings" in output
    assert "Profile: test-profile" in output
    assert "Region: us-east-1" in output
    assert "Default model: claude-3-5-sonnet" in output
    assert "Fast model: claude-3-5-haiku" in output


def test_config_show_with_path(mocker, capsys):
    """Test config show command with --path flag."""
    # Mock the config manager
    mock_config_manager = mocker.patch("clauth.commands.config.get_config_manager")
    mock_config_manager.return_value.config_file = "/home/user/.clauth/config.toml"

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show", "--path"])

    assert result.exit_code == 0
    output = result.output
    assert "Configuration file" in output
    assert "/home/user/.clauth/config.toml" in output


def test_config_show_missing_sso_url(mocker, capsys):
    """Test config show command when SSO URL is None."""
    # Mock the config manager and config
    mock_config_manager = mocker.patch("clauth.commands.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Set up mock config values with None SSO URL
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.aws.sso_start_url = None
    mock_config.aws.sso_region = "us-east-1"
    mock_config.aws.session_name = "test-session"
    mock_config.aws.output_format = "json"
    mock_config.models.provider_filter = "anthropic"
    mock_config.models.default_model = None
    mock_config.models.fast_model = None
    mock_config.cli.claude_cli_name = "claude"
    mock_config.cli.auto_start = True
    mock_config.cli.show_progress = True
    mock_config.cli.color_output = True

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    output = result.output
    assert "Not configured" in output
    assert "Not set" in output
