"""Unit tests for commands/models.py."""

import pytest
from unittest.mock import patch, MagicMock

from clauth.cli import app


def test_models_list_command(mocker):
    """Test models list command."""
    # Mock the config manager
    mock_config_manager = mocker.patch("clauth.commands.models.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.provider_filter = "anthropic"

    # Mock list_bedrock_profiles
    mock_list_bedrock = mocker.patch("clauth.commands.models.list_bedrock_profiles")
    mock_list_bedrock.return_value = (["claude-3-5-sonnet", "claude-3-5-haiku"], ["arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet", "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"])

    # Mock user_is_authenticated
    mocker.patch("clauth.commands.models.user_is_authenticated", return_value=True)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["model", "list"])

    assert result.exit_code == 0
    assert "claude-3-5-sonnet" in result.output
    assert "claude-3-5-haiku" in result.output


def test_models_list_command_no_models(mocker):
    """Test models list command when no models are found."""
    # Mock the config manager
    mock_config_manager = mocker.patch("clauth.commands.models.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.provider_filter = "anthropic"

    # Mock list_bedrock_profiles to return empty lists
    mock_list_bedrock = mocker.patch("clauth.commands.models.list_bedrock_profiles")
    mock_list_bedrock.return_value = ([], [])

    # Mock user_is_authenticated
    mocker.patch("clauth.commands.models.user_is_authenticated", return_value=True)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["model", "list"])

    assert result.exit_code == 0
    assert "No models found" in result.output


def test_models_list_command_authentication_failure(mocker):
    """Test models list command when authentication fails."""
    # Mock user_is_authenticated to fail
    mocker.patch("clauth.commands.models.user_is_authenticated", return_value=False)

    # Mock handle_authentication_failure
    mocker.patch("clauth.commands.models.handle_authentication_failure", return_value=False)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["model", "list"])

    assert result.exit_code == 1  # Should exit with error


def test_models_switch_command(mocker):
    """Test models switch command."""
    # Mock the config manager
    mock_config_manager = mocker.patch("clauth.commands.models.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.provider_filter = "anthropic"
    mock_config.models.default_model = "claude-3-5-sonnet"
    mock_config.models.fast_model = "claude-3-5-haiku"

    # Mock list_bedrock_profiles
    mock_list_bedrock = mocker.patch("clauth.commands.models.list_bedrock_profiles")
    mock_list_bedrock.return_value = (["claude-3-5-sonnet", "claude-3-5-haiku"], ["arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet", "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"])

    # Mock user_is_authenticated
    mocker.patch("clauth.commands.models.user_is_authenticated", return_value=True)

    # Mock inquirer.select
    mock_select = mocker.patch("clauth.commands.models.inquirer.select")
    mock_select_result = MagicMock()
    mock_select_result.execute.return_value = "claude-3-5-haiku"
    mock_select.return_value = mock_select_result

    # Mock config manager update_model_settings
    mock_config_manager.return_value.update_model_settings = MagicMock()

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["model", "switch"])

    assert result.exit_code == 0
    mock_config_manager.return_value.update_model_settings.assert_called_once()


def test_models_switch_command_invalid_model(mocker):
    """Test models switch command with invalid model selection."""
    # Mock the config manager
    mock_config_manager = mocker.patch("clauth.commands.models.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.provider_filter = "anthropic"
    mock_config.models.default_model = "claude-3-5-sonnet"
    mock_config.models.fast_model = "claude-3-5-haiku"

    # Mock list_bedrock_profiles to return empty
    mock_list_bedrock = mocker.patch("clauth.commands.models.list_bedrock_profiles")
    mock_list_bedrock.return_value = ([], [])

    # Mock user_is_authenticated
    mocker.patch("clauth.commands.models.user_is_authenticated", return_value=True)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["model", "switch"])

    assert result.exit_code == 1  # Should exit with error
    assert "No models found" in result.output
