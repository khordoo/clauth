"""Unit tests for launcher.py."""

import pytest
import subprocess
from unittest.mock import patch, MagicMock

from clauth.launcher import launch_claude_cli


def test_launch_claude_cli_success(mocker):
    """Test launch_claude_cli with successful execution."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.launcher.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.default_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"
    mock_config.models.fast_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"
    mock_config.cli.claude_cli_name = "claude"

    # Mock authentication check
    mock_user_is_authenticated = mocker.patch("clauth.launcher.user_is_authenticated", return_value=True)

    # Mock get_app_path
    mock_get_app_path = mocker.patch("clauth.launcher.get_app_path", return_value="/usr/bin/claude")

    # Mock clear_screen
    mock_clear_screen = mocker.patch("clauth.launcher.clear_screen")

    # Mock subprocess.run
    mock_subprocess_run = mocker.patch("subprocess.run")

    # Call the function
    launch_claude_cli()

    # Verify the calls
    mock_config_manager.return_value.load.assert_called_once()
    mock_user_is_authenticated.assert_called_once_with(profile="test-profile")
    mock_get_app_path.assert_called_once_with("claude")
    mock_clear_screen.assert_called_once()
    mock_subprocess_run.assert_called_once()


def test_launch_claude_cli_authentication_failure(mocker):
    """Test launch_claude_cli when authentication fails."""
    # Mock config manager
    mock_config_manager = mocker.patch("clauth.launcher.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"

    # Mock authentication check to fail
    mock_user_is_authenticated = mocker.patch("clauth.launcher.user_is_authenticated", return_value=False)

    # Mock handle_authentication_failure to also fail
    mock_handle_auth_failure = mocker.patch("clauth.launcher.handle_authentication_failure", return_value=False)

    # Call the function - should raise typer.Exit
    from click.exceptions import Exit
    with pytest.raises(Exit):
        launch_claude_cli()

    mock_user_is_authenticated.assert_called_once_with(profile="test-profile")
    mock_handle_auth_failure.assert_called_once_with("test-profile")


def test_launch_claude_cli_missing_model_config(mocker):
    """Test launch_claude_cli when model configuration is missing."""
    # Mock config manager
    mock_config_manager = mocker.patch("clauth.launcher.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.models.default_model_arn = None  # Missing model config
    mock_config.models.fast_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"

    # Mock authentication check
    mock_user_is_authenticated = mocker.patch("clauth.launcher.user_is_authenticated", return_value=True)

    # Mock render_status
    mock_status = mocker.patch("clauth.launcher.render_status")

    # Call the function - should raise typer.Exit
    from click.exceptions import Exit
    with pytest.raises(Exit):
        launch_claude_cli()

    mock_status.assert_called_once_with("Model configuration missing. Run `clauth init` for full setup.", level="error")


def test_launch_claude_cli_executable_not_found(mocker):
    """Test launch_claude_cli when executable is not found."""
    # Mock config manager
    mock_config_manager = mocker.patch("clauth.launcher.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.default_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"
    mock_config.models.fast_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"
    mock_config.cli.claude_cli_name = "claude"

    # Mock authentication check
    mock_user_is_authenticated = mocker.patch("clauth.launcher.user_is_authenticated", return_value=True)

    # Mock get_app_path to raise ExecutableNotFoundError
    from clauth.helpers import ExecutableNotFoundError
    mock_get_app_path = mocker.patch("clauth.launcher.get_app_path", side_effect=ExecutableNotFoundError("claude not found"))

    # Mock render_status
    mock_status = mocker.patch("clauth.launcher.render_status")

    # Call the function - should raise typer.Exit
    from click.exceptions import Exit
    with pytest.raises(Exit):
        launch_claude_cli()

    mock_status.assert_any_call("Launch failed: claude not found", level="error")
    mock_status.assert_any_call("Please install Claude Code CLI and ensure it's in your PATH.", level="warning")


def test_launch_claude_cli_subprocess_error(mocker):
    """Test launch_claude_cli when subprocess fails."""
    # Mock config manager
    mock_config_manager = mocker.patch("clauth.launcher.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.models.default_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"
    mock_config.models.fast_model_arn = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"
    mock_config.cli.claude_cli_name = "claude"

    # Mock authentication check
    mock_user_is_authenticated = mocker.patch("clauth.launcher.user_is_authenticated", return_value=True)

    # Mock get_app_path
    mock_get_app_path = mocker.patch("clauth.launcher.get_app_path", return_value="/usr/bin/claude")

    # Mock clear_screen
    mock_clear_screen = mocker.patch("clauth.launcher.clear_screen")

    # Mock subprocess.run to raise CalledProcessError
    mock_subprocess_run = mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "claude"))

    # Mock render_status
    mock_status = mocker.patch("clauth.launcher.render_status")

    # Call the function - should raise typer.Exit
    from click.exceptions import Exit
    with pytest.raises(Exit):
        launch_claude_cli()

    # Check that the error message was called
    mock_status.assert_any_call("Configuration error: Command 'claude' returned non-zero exit status 1.", level="error")
