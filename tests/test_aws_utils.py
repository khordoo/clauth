"""Unit tests for aws_utils.py."""

import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import NoCredentialsError, ClientError

from clauth.aws_utils import user_is_authenticated


@mock_aws
def test_user_is_authenticated_success():
    """Test user_is_authenticated with valid credentials."""
    # Setup mock STS client
    sts = boto3.client("sts", region_name="us-east-1")
    sts.get_caller_identity()

    # The user_is_authenticated function should return True
    assert user_is_authenticated(profile="default") is True


def test_user_is_authenticated_no_credentials(mocker):
    """Test user_is_authenticated when no credentials are found."""
    # Mock boto3.Session to raise NoCredentialsError
    mocker.patch("boto3.Session", side_effect=NoCredentialsError)

    # The user_is_authenticated function should return False
    assert user_is_authenticated(profile="default") is False


def test_user_is_authenticated_expired_token(mocker):
    """Test user_is_authenticated with an expired token."""
    # Mock the STS client to raise an ExpiredToken exception
    mock_sts_client = mocker.MagicMock()
    error_response = {"Error": {"Code": "ExpiredToken", "Message": "Token has expired"}}
    mock_sts_client.get_caller_identity.side_effect = ClientError(
        error_response, "GetCallerIdentity"
    )

    # Mock boto3.Session to return our mocked client
    mock_session = mocker.MagicMock()
    mock_session.client.return_value = mock_sts_client
    mocker.patch("boto3.Session", return_value=mock_session)

    # The user_is_authenticated function should return False
    assert user_is_authenticated(profile="default") is False


def test_list_bedrock_profiles_success(mocker):
    """Test list_bedrock_profiles with valid response."""
    from clauth.aws_utils import list_bedrock_profiles

    # Mock boto3.Session and client
    mock_client = mocker.MagicMock()
    mock_response = {
        "inferenceProfileSummaries": [
            {
                "inferenceProfileArn": "arn:aws:bedrock:us-east-1:123456789012:inference-profile/anthropic.claude-3-5-sonnet-20241022-v2:0",
                "inferenceProfileName": "anthropic.claude-3-5-sonnet-20241022-v2:0"
            },
            {
                "inferenceProfileArn": "arn:aws:bedrock:us-east-1:123456789012:inference-profile/anthropic.claude-3-5-haiku-20241022-v1:0",
                "inferenceProfileName": "anthropic.claude-3-5-haiku-20241022-v1:0"
            }
        ]
    }
    mock_client.list_inference_profiles.return_value = mock_response

    mock_session = mocker.MagicMock()
    mock_session.client.return_value = mock_client
    mocker.patch("boto3.Session", return_value=mock_session)

    # Test the function
    model_ids, model_arns = list_bedrock_profiles("default", "us-east-1", "anthropic")

    assert len(model_ids) == 2
    assert len(model_arns) == 2
    assert "anthropic.claude-3-5-sonnet-20241022-v2:0" in model_ids
    assert "anthropic.claude-3-5-haiku-20241022-v1:0" in model_ids


def test_list_bedrock_profiles_no_models(mocker):
    """Test list_bedrock_profiles when no models are found."""
    from clauth.aws_utils import list_bedrock_profiles

    # Mock boto3.Session and client
    mock_client = mocker.MagicMock()
    mock_client.list_inference_profiles.return_value = {"inferenceProfileSummaries": []}

    mock_session = mocker.MagicMock()
    mock_session.client.return_value = mock_client
    mocker.patch("boto3.Session", return_value=mock_session)

    # Test the function
    model_ids, model_arns = list_bedrock_profiles("default", "us-east-1", "anthropic")

    assert model_ids == []
    assert model_arns == []


def test_list_bedrock_profiles_client_error(mocker):
    """Test list_bedrock_profiles with a client error."""
    from clauth.aws_utils import list_bedrock_profiles

    # Mock boto3.Session to raise a ClientError
    mock_session = mocker.MagicMock()
    mock_session.client.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "ListInferenceProfiles"
    )
    mocker.patch("boto3.Session", return_value=mock_session)

    # Test the function
    model_ids, model_arns = list_bedrock_profiles("default", "us-east-1", "anthropic")

    assert model_ids == []
    assert model_arns == []


def test_setup_iam_user_auth_success(mocker):
    """Test setup_iam_user_auth with successful setup."""
    from clauth.aws_utils import setup_iam_user_auth

    # Mock subprocess.run calls
    mock_run = mocker.patch("subprocess.run")
    mock_user_is_authenticated = mocker.patch("clauth.aws_utils.user_is_authenticated", return_value=True)

    # Mock typer functions
    mocker.patch("typer.secho")
    mocker.patch("typer.echo")

    # Test the function
    result = setup_iam_user_auth("test-profile", "us-east-1")

    assert result is True
    # Verify subprocess.run was called for configure commands
    assert mock_run.call_count >= 2


def test_setup_iam_user_auth_failure(mocker):
    """Test setup_iam_user_auth with authentication failure."""
    from clauth.aws_utils import setup_iam_user_auth

    # Mock subprocess.run to succeed for config but fail for auth check
    mock_run = mocker.patch("subprocess.run")
    mock_user_is_authenticated = mocker.patch("clauth.aws_utils.user_is_authenticated", return_value=False)

    # Mock typer functions
    mocker.patch("typer.secho")
    mocker.patch("typer.echo")

    # Test the function
    result = setup_iam_user_auth("test-profile", "us-east-1")

    assert result is False


def test_setup_sso_auth_success(mocker):
    """Test setup_sso_auth with successful setup."""
    from clauth.aws_utils import setup_sso_auth

    # Mock config object
    mock_config = mocker.MagicMock()
    mock_config.aws.profile = "test-profile"
    mock_config.aws.region = "us-east-1"
    mock_config.aws.output_format = "json"
    mock_config.aws.session_name = "test-session"
    mock_config.aws.sso_start_url = "https://example.awsapps.com/start"

    # Mock subprocess.run
    mock_run = mocker.patch("subprocess.run")

    # Mock get_existing_sso_start_url
    mocker.patch("clauth.aws_utils.get_existing_sso_start_url", return_value=None)

    # Mock typer functions
    mocker.patch("typer.secho")
    mocker.patch("typer.echo")

    # Test the function
    result = setup_sso_auth(mock_config, {})

    assert result is True


def test_get_existing_sso_start_url_success(mocker):
    """Test get_existing_sso_start_url with existing session."""
    from clauth.aws_utils import get_existing_sso_start_url

    # Mock pathlib and configparser
    mock_path = mocker.patch("pathlib.Path")
    mock_config_parser = mocker.patch("configparser.ConfigParser")

    # Setup mocks
    mock_home = mock_path.home.return_value
    mock_config_file = mock_home / ".aws" / "config"
    mock_config_file.exists.return_value = True

    mock_parser_instance = mock_config_parser.return_value
    mock_parser_instance.read.return_value = None
    mock_parser_instance.has_section.return_value = True
    mock_parser_instance.get.return_value = "https://example.awsapps.com/start"

    # Test the function
    result = get_existing_sso_start_url("test-session")

    assert result == "https://example.awsapps.com/start"


def test_remove_sso_session_success(mocker):
    """Test remove_sso_session with successful removal."""
    from clauth.aws_utils import remove_sso_session

    # Mock pathlib and configparser
    mock_path = mocker.patch("pathlib.Path")
    mock_config_parser = mocker.patch("configparser.ConfigParser")

    # Setup mocks
    mock_home = mock_path.home.return_value
    mock_config_file = mock_home / ".aws" / "config"
    mock_config_file.exists.return_value = True

    mock_parser_instance = mock_config_parser.return_value
    mock_parser_instance.read.return_value = None
    mock_parser_instance.sections.return_value = ["sso-session test-session"]
    mock_parser_instance.has_section.return_value = True
    mock_parser_instance.remove_section.return_value = True

    # Test the function
    result = remove_sso_session("test-session")

    assert result is True


def test_clear_sso_cache_success(mocker):
    """Test clear_sso_cache with successful cache clearing."""
    from clauth.aws_utils import clear_sso_cache

    # Mock pathlib
    mock_path = mocker.patch("pathlib.Path")

    # Setup mocks
    mock_home = mock_path.home.return_value
    mock_cache_dir = mock_home / ".aws" / "sso" / "cache"
    mock_cache_dir.exists.return_value = True

    # Mock glob to return some cache files
    mock_cache_file = mocker.MagicMock()
    mock_cache_dir.glob.return_value = [mock_cache_file]

    # Test the function
    result = clear_sso_cache("test-profile")

    assert result is True
    mock_cache_file.unlink.assert_called_once()


def test_delete_aws_credentials_profile_success(mocker):
    """Test delete_aws_credentials_profile with successful deletion."""
    from clauth.aws_utils import delete_aws_credentials_profile

    # Mock pathlib and configparser
    mock_path = mocker.patch("pathlib.Path")
    mock_config_parser = mocker.patch("configparser.ConfigParser")

    # Setup mocks
    mock_home = mock_path.home.return_value
    mock_creds_file = mock_home / ".aws" / "credentials"
    mock_creds_file.exists.return_value = True

    mock_parser_instance = mock_config_parser.return_value
    mock_parser_instance.read.return_value = None
    mock_parser_instance.has_section.return_value = True
    mock_parser_instance.remove_section.return_value = True

    # Test the function
    result = delete_aws_credentials_profile("test-profile")

    assert result is True


def test_delete_aws_profile_success(mocker):
    """Test delete_aws_profile with successful deletion."""
    from clauth.aws_utils import delete_aws_profile

    # Mock pathlib and configparser
    mock_path = mocker.patch("pathlib.Path")
    mock_config_parser = mocker.patch("configparser.ConfigParser")

    # Setup mocks
    mock_home = mock_path.home.return_value
    mock_config_file = mock_home / ".aws" / "config"
    mock_config_file.exists.return_value = True

    mock_parser_instance = mock_config_parser.return_value
    mock_parser_instance.read.return_value = None
    mock_parser_instance.has_section.return_value = True
    mock_parser_instance.remove_section.return_value = True

    # Test the function
    result = delete_aws_profile("test-profile")

    assert result is True
