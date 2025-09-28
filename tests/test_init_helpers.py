"""Unit tests for the helper functions in commands/init.py."""

import pytest
from unittest.mock import patch, MagicMock
from typer import Exit
from clauth.commands.init import (
    _handle_authentication,
    _handle_model_selection,
    _launch_claude_cli,
)


def test_handle_authentication_skip_success(mocker):
    """Test _handle_authentication with 'skip' method and user is authenticated."""
    mock_config = MagicMock()
    mock_config.aws.profile = "test-profile"
    mocker.patch("clauth.commands.init.choose_auth_method", return_value="skip")
    mocker.patch("clauth.commands.init.prompt_for_region_if_needed", return_value=True)
    mocker.patch("clauth.commands.init.aws.user_is_authenticated", return_value=True)

    _handle_authentication(mock_config, {})


def test_handle_authentication_iam_success(mocker):
    """Test _handle_authentication with 'iam' method."""
    mock_config = MagicMock()
    mocker.patch("clauth.commands.init.choose_auth_method", return_value="iam")
    mocker.patch("clauth.commands.init.prompt_for_region_if_needed", return_value=True)
    mock_setup_iam = mocker.patch("clauth.commands.init.setup_iam_user_auth", return_value=True)

    _handle_authentication(mock_config, {})
    mock_setup_iam.assert_called_once()


def test_handle_authentication_sso_success(mocker):
    """Test _handle_authentication with 'sso' method."""
    mock_config = MagicMock()
    cli_overrides = {}
    mocker.patch("clauth.commands.init.choose_auth_method", return_value="sso")
    mocker.patch("clauth.commands.init.prompt_for_region_if_needed", return_value=True)
    mock_setup_sso = mocker.patch("clauth.commands.init.setup_sso_auth", return_value=True)

    _handle_authentication(mock_config, cli_overrides)
    mock_setup_sso.assert_called_once_with(mock_config, cli_overrides)


def test_handle_authentication_skip_failure(mocker):
    """Test _handle_authentication with 'skip' method and user is not authenticated."""
    mock_config = MagicMock()
    mock_config.aws.profile = "test-profile"
    mocker.patch("clauth.commands.init.choose_auth_method", return_value="skip")
    mocker.patch("clauth.commands.init.prompt_for_region_if_needed", return_value=True)
    mocker.patch("clauth.commands.init.aws.user_is_authenticated", return_value=False)

    with pytest.raises(Exit):
        _handle_authentication(mock_config, {})


def test_handle_model_selection_rediscover_models(mocker):
    """Test _handle_model_selection when user chooses to re-discover models."""
    mock_config = MagicMock()
    mock_config.models.default_model_arn = "arn:default"
    mock_config.models.fast_model_arn = "arn:fast"
    
    mock_config_manager = MagicMock()
    mock_console = MagicMock()

    mocker.patch("InquirerPy.inquirer.confirm").return_value.execute.return_value = False  # Don't use existing
    mocker.patch("clauth.commands.init.aws.list_bedrock_profiles", return_value=(["new-model"], ["arn:new"]))
    mocker.patch("InquirerPy.inquirer.select").return_value.execute.return_value = "new-model"

    default, fast, model_map = _handle_model_selection(mock_config, mock_config_manager, mock_console)

    assert default == "new-model"
    assert fast == "new-model"
    mock_config_manager.update_model_settings.assert_called_once()


def test_handle_model_selection_existing_config_use_existing(mocker):
    """Test _handle_model_selection with existing config and user chooses to use it."""
    mock_config = MagicMock()
    mock_config.models.default_model_arn = "arn:default"
    mock_config.models.fast_model_arn = "arn:fast"
    mock_config.models.default_model = "default-model"
    mock_config.models.fast_model = "fast-model"
    
    mock_config_manager = MagicMock()
    mock_console = MagicMock()
    
    mocker.patch("InquirerPy.inquirer.confirm").return_value.execute.return_value = True
    
    default, fast, model_map = _handle_model_selection(mock_config, mock_config_manager, mock_console)
    
    assert default == "default-model"
    assert fast == "fast-model"
    assert model_map == {"default-model": "arn:default", "fast-model": "arn:fast"}


def test_launch_claude_cli_not_found(mocker):
    """Test _launch_claude_cli when the executable is not found."""
    from clauth.helpers import ExecutableNotFoundError

    mock_config = MagicMock()
    mock_config.cli.claude_cli_name = "claude"
    mocker.patch("clauth.commands.init.get_app_path", side_effect=ExecutableNotFoundError("claude not found"))

    with pytest.raises(Exit):
        _launch_claude_cli(mock_config, {})


def test_launch_claude_cli_success(mocker):
    """Test _launch_claude_cli successfully launches the CLI."""
    mock_config = MagicMock()
    mock_config.cli.claude_cli_name = "claude"
    mock_env = {}

    mocker.patch("clauth.commands.init.get_app_path", return_value="/path/to/claude")
    mock_subprocess_run = mocker.patch("clauth.commands.init.subprocess.run")

    _launch_claude_cli(mock_config, mock_env)

    mock_subprocess_run.assert_called_once_with(["/path/to/claude"], env=mock_env, check=True)
