"""Unit tests for commands/delete.py."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from clauth.cli import app


def test_delete_command_cancel(mocker):
    """Test that the delete command can be cancelled."""
    mocker.patch("typer.confirm", return_value=False)
    runner = CliRunner()
    result = runner.invoke(app, ["delete"])
    assert "Delete operation cancelled" in result.stdout
    assert result.exit_code == 0


def test_delete_command_with_failures(mocker):
    """Test the delete command when some steps fail."""
    mocker.patch("typer.confirm", return_value=True)
    mocker.patch("clauth.aws_utils.delete_aws_profile", return_value=False)
    mocker.patch("clauth.aws_utils.delete_aws_credentials_profile", return_value=False)
    mocker.patch("clauth.aws_utils.clear_sso_cache", return_value=False)
    mocker.patch("clauth.aws_utils.remove_sso_session", return_value=False)
    mocker.patch("shutil.rmtree", side_effect=Exception("rmtree failed"))

    runner = CliRunner()
    result = runner.invoke(app, ["delete", "--yes"])
    assert "Deletion completed with some errors" in result.stdout
    assert result.exit_code == 1
