"""Unit tests for commands/init.py."""

import pytest
from unittest.mock import patch, MagicMock

from clauth.cli import app


def test_init_command_no_models_found(mocker):
    """Test init command when no models are found."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="sso")

    # Mock prompt_for_region_if_needed
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=True)

    # Mock list_bedrock_profiles to return empty
    mock_list_bedrock = mocker.patch("clauth.aws_utils.list_bedrock_profiles")
    mock_list_bedrock.return_value = ([], [])

    # Mock user_is_authenticated
    mocker.patch("clauth.aws_utils.user_is_authenticated", return_value=True)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error


def test_init_command_region_prompt_failure(mocker):
    """Test init command when region prompt fails."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="sso")

    # Mock prompt_for_region_if_needed to fail
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=False)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error


def test_init_command_sso_auth_failure(mocker):
    """Test init command when SSO authentication setup fails."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method to return SSO
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="sso")

    # Mock prompt_for_region_if_needed
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=True)

    # Mock setup_sso_auth to fail
    mock_setup_sso = mocker.patch("clauth.aws_utils.setup_sso_auth", return_value=False)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error


def test_init_command_iam_auth_failure(mocker):
    """Test init command when IAM authentication setup fails."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method to return IAM
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="iam")

    # Mock typer.prompt for access key input
    mock_prompt = mocker.patch("typer.prompt")
    mock_prompt.side_effect = ["AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"]

    # Mock typer.confirm for region confirmation
    mock_confirm = mocker.patch("typer.confirm", return_value=True)

    # Mock prompt_for_region_if_needed
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=True)

    # Mock setup_iam_user_auth to fail
    mock_setup_iam = mocker.patch("clauth.aws_utils.setup_iam_user_auth", return_value=False)

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error


def test_init_command_model_discovery_failure(mocker):
    """Test init command when model discovery fails."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="sso")

    # Mock prompt_for_region_if_needed
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=True)

    # Mock setup_sso_auth to succeed
    mock_setup_sso = mocker.patch("clauth.aws_utils.setup_sso_auth", return_value=True)

    # Mock list_bedrock_profiles to return empty (no models)
    mock_list_bedrock = mocker.patch("clauth.aws_utils.list_bedrock_profiles")
    mock_list_bedrock.return_value = ([], [])

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error


def test_init_command_config_save_failure(mocker):
    """Test init command when configuration save fails."""
    # Mock all the dependencies
    mock_config_manager = mocker.patch("clauth.config.get_config_manager")
    mock_config = MagicMock()
    mock_config_manager.return_value.load.return_value = mock_config

    # Mock choose_auth_method
    mock_choose_auth = mocker.patch("clauth.helpers.choose_auth_method", return_value="sso")

    # Mock prompt_for_region_if_needed
    mock_prompt_region = mocker.patch("clauth.helpers.prompt_for_region_if_needed", return_value=True)

    # Mock setup_sso_auth to succeed
    mock_setup_sso = mocker.patch("clauth.aws_utils.setup_sso_auth", return_value=True)

    # Mock list_bedrock_profiles
    mock_list_bedrock = mocker.patch("clauth.aws_utils.list_bedrock_profiles")
    mock_list_bedrock.return_value = (["claude-3-5-sonnet"], ["arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"])

    # Mock inquirer.select for model selection
    mock_select = mocker.patch("InquirerPy.inquirer.select")
    mock_select_result = MagicMock()
    mock_select_result.execute.return_value = "claude-3-5-sonnet"
    mock_select.return_value = mock_select_result

    # Mock config manager update methods to fail
    mock_config_manager.return_value.update_aws_settings = MagicMock(side_effect=Exception("Save failed"))
    mock_config_manager.return_value.update_model_settings = MagicMock()

    # Call the command
    from typer.testing import CliRunner
    runner = CliRunner()
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 1  # Should exit with error
