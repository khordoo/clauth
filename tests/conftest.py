"""Pytest configuration and fixtures for clauth tests."""

import pytest
from unittest.mock import Mock, patch
import os
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def mock_aws_profile():
    """Mock AWS profile configuration."""
    return {
        'profile': 'test-profile',
        'region': 'us-east-1',
        'sso_start_url': 'https://test.awsapps.com/start/',
        'sso_region': 'us-east-1',
        'session_name': 'test-session'
    }


@pytest.fixture
def mock_bedrock_models():
    """Mock Bedrock model responses."""
    model_ids = [
        'claude-3-5-sonnet-20241022-v2:0',
        'claude-3-5-haiku-20241022-v1:0',
        'claude-3-opus-20240229-v1:0'
    ]
    model_arns = [
        'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet-20241022-v2:0',
        'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku-20241022-v1:0',
        'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-opus-20240229-v1:0'
    ]
    return model_ids, model_arns


@pytest.fixture
def temp_executable_dir():
    """Create a temporary directory with mock executables for testing."""
    temp_dir = tempfile.mkdtemp()

    # Create mock executables
    claude_exe = Path(temp_dir) / "claude.exe"
    claude_cmd = Path(temp_dir) / "claude.cmd"
    python_exe = Path(temp_dir) / "python.exe"

    # Create the files (empty is fine for testing)
    claude_exe.touch()
    claude_cmd.touch()
    python_exe.touch()

    # Make them executable on Unix-like systems
    if os.name != 'nt':
        claude_exe.chmod(0o755)
        claude_cmd.chmod(0o755)
        python_exe.chmod(0o755)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_typer_echo():
    """Mock typer.echo to capture output in tests."""
    with patch('typer.echo') as mock_echo:
        yield mock_echo


@pytest.fixture
def mock_config_manager():
    """Mock configuration manager."""
    with patch('clauth.cli.get_config_manager') as mock_get_config:
        mock_manager = Mock()
        mock_config = Mock()

        # Set up default config values
        mock_config.aws.profile = 'test-profile'
        mock_config.aws.region = 'us-east-1'
        mock_config.aws.sso_start_url = 'https://test.awsapps.com/start/'
        mock_config.aws.sso_region = 'us-east-1'
        mock_config.aws.session_name = 'test-session'
        mock_config.aws.output_format = 'json'

        mock_config.models.provider_filter = 'anthropic'
        mock_config.models.default_model = 'claude-3-5-sonnet-20241022-v2:0'
        mock_config.models.fast_model = 'claude-3-5-haiku-20241022-v1:0'
        mock_config.models.default_model_arn = 'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet-20241022-v2:0'
        mock_config.models.fast_model_arn = 'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku-20241022-v1:0'

        mock_config.cli.claude_cli_name = 'claude'
        mock_config.cli.auto_start = True
        mock_config.cli.show_progress = True
        mock_config.cli.color_output = True

        mock_manager.load.return_value = mock_config
        mock_get_config.return_value = mock_manager

        yield mock_manager, mock_config


@pytest.fixture
def mock_aws_utils():
    """Mock AWS utility functions."""
    with patch('clauth.cli.aws') as mock_aws:
        mock_aws.user_is_authenticated.return_value = True
        mock_aws.list_bedrock_profiles.return_value = (
            ['claude-3-5-sonnet-20241022-v2:0', 'claude-3-5-haiku-20241022-v1:0'],
            ['arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet-20241022-v2:0',
             'arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku-20241022-v1:0']
        )
        yield mock_aws