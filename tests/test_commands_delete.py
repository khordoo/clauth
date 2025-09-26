"""Unit tests for commands/delete.py."""

import pytest
from unittest.mock import patch, MagicMock

from clauth.cli import app


def test_delete_command_success(mocker):
    """Test delete command with successful execution."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"

    # Mock the AWS utility functions
    mocker.patch("clauth.aws_utils.delete_aws_profile", return_value=True)
    mocker.patch("clauth.aws_utils.delete_aws_credentials_profile", return_value=True)
    mocker.patch("clauth.aws_utils.clear_sso_cache", return_value=True)
    mocker.patch("clauth.aws_utils.remove_sso_session", return_value=True)

    # Mock typer.confirm to return True
    mocker.patch("typer.confirm", return_value=True)

    # Mock shutil.rmtree and os.path.exists
    mocker.patch("shutil.rmtree")
    mocker.patch("pathlib.Path.exists", return_value=True)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["delete", "--yes"])

    assert result.exit_code == 0


def test_delete_command_with_confirmation(mocker):
    """Test delete command with user confirmation."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config
    mock_config.aws.profile = "test-profile"

    # Mock the AWS utility functions
    mocker.patch("clauth.aws_utils.delete_aws_profile", return_value=True)
    mocker.patch("clauth.aws_utils.delete_aws_credentials_profile", return_value=True)
    mocker.patch("clauth.aws_utils.clear_sso_cache", return_value=True)
    mocker.patch("clauth.aws_utils.remove_sso_session", return_value=True)

    # Mock typer.confirm to return True
    mocker.patch("typer.confirm", return_value=True)

    # Mock shutil.rmtree and os.path.exists
    mocker.patch("shutil.rmtree")
    mocker.patch("pathlib.Path.exists", return_value=True)

    # Call the command without --yes flag
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["delete"])

    assert result.exit_code == 0


def test_delete_command_user_cancels(mocker):
    """Test delete command when user cancels."""
    # Mock typer.confirm to return False
    mock_confirm = mocker.patch("typer.confirm", return_value=False)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["delete"])

    assert result.exit_code == 0
    mock_confirm.assert_called_once()
