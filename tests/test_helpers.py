"""Unit tests for helpers.py."""

import pytest
import tempfile
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import typer

from clauth.helpers import (
    clear_screen,
    show_welcome_logo,
    choose_auth_method,
    get_app_path,
    ExecutableNotFoundError,
    is_sso_profile,
    handle_authentication_failure,
    prompt_for_region_if_needed,
    validate_model_id,
)


def test_clear_screen(mocker):
    """Test clear_screen function."""
    # Mock os.system to avoid actual screen clearing
    mock_system = mocker.patch("os.system")
    clear_screen()
    mock_system.assert_called_once_with("clear")


def test_show_welcome_logo(capsys):
    """Test show_welcome_logo function renders banner content."""
    from rich.console import Console

    console = Console()

    show_welcome_logo(console)

    output = capsys.readouterr().out
    assert "CLAUTH" in output
    assert "Quick setup for Claude Code with AWS Bedrock (SSO or IAM)" in output
    assert "Requires AWS CLI v2" in output


def test_choose_auth_method(mocker):
    """Test choose_auth_method function."""
    # Mock the inquirer.select to return a specific choice
    mock_select = mocker.patch("InquirerPy.inquirer.select")
    mock_select.return_value.execute.return_value = "sso"

    result = choose_auth_method()
    assert result == "sso"
    mock_select.assert_called_once()


def test_get_app_path_success(mocker):
    """Test get_app_path with successful executable finding."""
    mock_which = mocker.patch("shutil.which")
    mock_which.return_value = "/usr/bin/claude"
    mock_echo = mocker.patch("typer.echo")

    result = get_app_path("claude")
    assert result == "/usr/bin/claude"
    mock_echo.assert_called_once_with("Using executable: /usr/bin/claude")


def test_get_app_path_not_found(mocker):
    """Test get_app_path when executable is not found."""
    mock_which = mocker.patch("shutil.which")
    mock_which.return_value = None

    with pytest.raises(ExecutableNotFoundError, match="claude not found in system PATH"):
        get_app_path("claude")


def test_get_app_path_empty_name():
    """Test get_app_path with empty executable name."""
    with pytest.raises(ValueError, match="Invalid executable name provided"):
        get_app_path("")


def test_get_app_path_whitespace_name():
    """Test get_app_path with whitespace-only executable name."""
    with pytest.raises(ValueError, match="Invalid executable name provided"):
        get_app_path("   ")


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_get_app_path_windows_preference(mocker):
    """Test get_app_path Windows preference for .cmd/.exe."""
    mock_which = mocker.patch("shutil.which")
    mock_which.side_effect = ["/usr/bin/claude", "/usr/bin/claude.cmd", None]
    mock_echo = mocker.patch("typer.echo")

    with patch("clauth.helpers.os.name", "nt"):
        result = get_app_path("claude")
        assert result == "/usr/bin/claude.cmd"
        mock_echo.assert_called_once()


def test_is_sso_profile_true(mocker):
    """Test is_sso_profile returns True for SSO profiles."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "https://example.awsapps.com/start\n"

    result = is_sso_profile("test-profile")
    assert result == "https://example.awsapps.com/start"  # Function returns the stripped stdout


def test_is_sso_profile_false(mocker):
    """Test is_sso_profile returns False for non-SSO profiles."""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 1

    result = is_sso_profile("test-profile")
    assert result is False


def test_handle_authentication_failure_sso_success(mocker):
    """Test handle_authentication_failure with SSO profile that succeeds."""
    mock_is_sso = mocker.patch("clauth.helpers.is_sso_profile", return_value=True)
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value.returncode = 0
    mock_status = mocker.patch("clauth.helpers.render_status")

    result = handle_authentication_failure("test-profile")
    assert result is True
    mock_status.assert_any_call(
        "SSO token expired. Attempting to re-authenticate...",
        level="warning",
    )
    mock_status.assert_any_call(
        "Successfully re-authenticated with profile 'test-profile'",
        level="success",
    )


def test_handle_authentication_failure_sso_failure(mocker):
    """Test handle_authentication_failure with SSO profile that fails."""
    mock_is_sso = mocker.patch("clauth.helpers.is_sso_profile", return_value=True)
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(1, "aws sso login")
    mock_status = mocker.patch("clauth.helpers.render_status")

    result = handle_authentication_failure("test-profile")
    assert result is False
    mock_status.assert_any_call(
        "SSO token expired. Attempting to re-authenticate...",
        level="warning",
    )
    mock_status.assert_any_call(
        "SSO login failed. Run `clauth init` for full setup.",
        level="error",
    )


def test_handle_authentication_failure_non_sso(mocker):
    """Test handle_authentication_failure with non-SSO profile."""
    mock_is_sso = mocker.patch("clauth.helpers.is_sso_profile", return_value=False)
    mock_status = mocker.patch("clauth.helpers.render_status")

    result = handle_authentication_failure("test-profile")
    assert result is False
    mock_status.assert_called_with(
        "Authentication required. Run `clauth init` to set up credentials.",
        level="error",
    )


def test_prompt_for_region_if_needed_no_prompt(mocker):
    """Test prompt_for_region_if_needed when region is already provided."""
    mock_config = MagicMock()
    cli_overrides = {"region": True}

    result = prompt_for_region_if_needed(mock_config, cli_overrides)
    assert result is True


def test_prompt_for_region_if_needed_with_prompt(mocker):
    """Test prompt_for_region_if_needed when region needs to be prompted."""
    mock_config = MagicMock()
    mock_config.aws.region = "us-east-1"
    cli_overrides = {"region": False}

    # Mock the inquirer select properly
    mock_select_result = MagicMock()
    mock_select_result.execute.return_value = "us-west-2"
    mock_select = mocker.patch("InquirerPy.inquirer.select", return_value=mock_select_result)

    # Mock the config manager to avoid actual file operations
    mock_config_manager = mocker.patch("clauth.helpers.get_config_manager")
    mock_config_manager.return_value._config = mock_config
    mock_config_manager.return_value.save = MagicMock()

    result = prompt_for_region_if_needed(mock_config, cli_overrides)
    assert result is True
    assert mock_config.aws.region == "us-west-2"


def test_validate_model_id_success(mocker):
    """Test validate_model_id with valid model."""
    mock_list_bedrock = mocker.patch("clauth.helpers.list_bedrock_profiles")
    mock_list_bedrock.return_value = (["claude-3-5-sonnet"], ["arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"])

    result = validate_model_id("claude-3-5-sonnet")
    assert result == "claude-3-5-sonnet"


def test_validate_model_id_invalid(mocker):
    """Test validate_model_id with invalid model."""
    mock_list_bedrock = mocker.patch("clauth.helpers.list_bedrock_profiles")
    mock_list_bedrock.return_value = (["claude-3-5-sonnet"], ["arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"])

    with pytest.raises(typer.BadParameter):
        validate_model_id("invalid-model")
