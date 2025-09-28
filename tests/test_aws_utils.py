"""Unit tests for aws_utils.py."""

import pytest
from unittest.mock import patch, MagicMock
from clauth.aws_utils import (
    setup_iam_user_auth,
    setup_sso_auth,
    user_is_authenticated,
    get_existing_sso_start_url,
    remove_sso_session,
    clear_sso_cache,
    delete_aws_credentials_profile,
    delete_aws_profile,
    list_bedrock_profiles,
)


def test_setup_iam_user_auth_success(mocker):
    """Test successful IAM user auth setup."""
    mock_subprocess_run = mocker.patch("subprocess.run")
    mocker.patch("clauth.aws_utils.user_is_authenticated", return_value=True)
    
    assert setup_iam_user_auth("test-profile", "us-east-1") is True
    assert mock_subprocess_run.call_count == 2


def test_setup_iam_user_auth_sso_cleanup_failure(mocker):
    """Test that IAM setup continues even if SSO cleanup fails."""
    mock_subprocess_run = mocker.patch("subprocess.run")
    mocker.patch("clauth.aws_utils.user_is_authenticated", return_value=True)
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("configparser.ConfigParser.read")
    mocker.patch("configparser.ConfigParser.has_section", return_value=True)
    mocker.patch("configparser.ConfigParser.has_option", return_value=True)
    mocker.patch("configparser.ConfigParser.remove_option", side_effect=Exception("Cleanup failed"))

    # Should still return True as the cleanup failure is not critical
    assert setup_iam_user_auth("test-profile", "us-east-1") is True


def test_setup_iam_user_auth_failure(mocker):
    """Test failing IAM user auth setup."""
    import subprocess
    mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
    
    assert setup_iam_user_auth("test-profile", "us-east-1") is False


def test_setup_sso_auth_with_existing_url(mocker):
    """Test SSO auth setup with an existing SSO start URL."""
    mock_subprocess_run = mocker.patch("subprocess.run")
    mocker.patch("clauth.aws_utils.get_existing_sso_start_url", return_value="https://example.com/start")
    mock_config = MagicMock()
    mock_config.aws.profile = "test"
    mock_config.aws.region = "us-east-1"
    mock_config.aws.output_format = "json"
    mock_config.aws.session_name = "test-session"

    assert setup_sso_auth(mock_config, {}) is True
    # More calls to subprocess.run are expected when an existing URL is found
    assert mock_subprocess_run.call_count > 2


def test_setup_sso_auth_success(mocker):
    """Test successful SSO auth setup."""
    mock_subprocess_run = mocker.patch("subprocess.run")
    mocker.patch("clauth.aws_utils.get_existing_sso_start_url", return_value=None)
    mock_config = MagicMock()
    mock_config.aws.profile = "test"
    mock_config.aws.region = "us-east-1"
    mock_config.aws.output_format = "json"
    mock_config.aws.session_name = "test-session"
    
    assert setup_sso_auth(mock_config, {}) is True
    assert mock_subprocess_run.call_count > 0


def test_setup_sso_auth_failure(mocker):
    """Test failing SSO auth setup."""
    import subprocess
    mocker.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd"))
    mock_config = MagicMock()
    
    assert setup_sso_auth(mock_config, {}) is False


def test_user_is_authenticated_no_credentials(mocker):
    """Test user_is_authenticated with NoCredentialsError."""
    from botocore.exceptions import NoCredentialsError
    mocker.patch("boto3.Session", side_effect=NoCredentialsError)
    
    assert user_is_authenticated("test") is False


def test_user_is_authenticated_expired_token(mocker):
    """Test user_is_authenticated with ExpiredToken."""
    from botocore.exceptions import ClientError
    mock_session = MagicMock()
    mock_sts = MagicMock()
    mock_sts.get_caller_identity.side_effect = ClientError({"Error": {"Code": "ExpiredToken"}}, "op")
    mock_session.client.return_value = mock_sts
    mocker.patch("boto3.Session", return_value=mock_session)
    
    assert user_is_authenticated("test") is False


def test_list_bedrock_profiles_no_provider_match(mocker):
    """Test list_bedrock_profiles when no models match the provider filter."""
    mock_boto_session = MagicMock()
    mock_boto_client = MagicMock()
    mock_boto_client.list_inference_profiles.return_value = {
        "inferenceProfileSummaries": [{"inferenceProfileArn": "arn:aws:bedrock:us-east-1::inference-profile/amazon.titan-text-express-v1"}]
    }
    mock_boto_session.client.return_value = mock_boto_client
    mocker.patch("boto3.Session", return_value=mock_boto_session)

    ids, arns = list_bedrock_profiles("test", "us-east-1", provider="anthropic")
    assert ids == []
    assert arns == []


def test_remove_sso_session_not_found(mocker):
    """Test remove_sso_session when the session is not found."""
    mocker.patch("pathlib.Path.exists", return_value=True)
    mock_config_parser = MagicMock()
    mock_config_parser.sections.return_value = []
    mocker.patch("configparser.ConfigParser", return_value=mock_config_parser)
    
    assert remove_sso_session("test-session") is True


def test_clear_sso_cache_no_directory(mocker):
    """Test clear_sso_cache when the cache directory does not exist."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    
    assert clear_sso_cache() is True


def test_delete_aws_credentials_profile_no_file(mocker):
    """Test delete_aws_credentials_profile when the credentials file does not exist."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    
    assert delete_aws_credentials_profile("test-profile") is True


def test_delete_aws_profile_no_file(mocker):
    """Test delete_aws_profile when the config file does not exist."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    
    assert delete_aws_profile("test-profile") is True


def test_get_existing_sso_start_url_exception(mocker):
    """Test get_existing_sso_start_url when an exception occurs."""
    mocker.patch("pathlib.Path.exists", side_effect=Exception("File system error"))
    assert get_existing_sso_start_url("test-session") is None


def test_remove_sso_session_exception(mocker):
    """Test remove_sso_session when an exception occurs."""
    mocker.patch("pathlib.Path.exists", side_effect=Exception("File system error"))
    assert remove_sso_session("test-session") is False


def test_clear_sso_cache_exception(mocker):
    """Test clear_sso_cache when an exception occurs."""
    mocker.patch("pathlib.Path.exists", side_effect=Exception("File system error"))
    assert clear_sso_cache() is False


def test_delete_aws_credentials_profile_exception(mocker):
    """Test delete_aws_credentials_profile when an exception occurs."""
    mocker.patch("pathlib.Path.exists", side_effect=Exception("File system error"))
    assert delete_aws_credentials_profile("test-profile") is False


def test_delete_aws_profile_exception(mocker):
    """Test delete_aws_profile when an exception occurs."""
    mocker.patch("pathlib.Path.exists", side_effect=Exception("File system error"))
    assert delete_aws_profile("test-profile") is False


def test_list_bedrock_profiles_exception(mocker):
    """Test list_bedrock_profiles when a BotoCoreError occurs."""
    from botocore.exceptions import BotoCoreError
    mocker.patch("boto3.Session", side_effect=BotoCoreError)
    ids, arns = list_bedrock_profiles("test", "us-east-1")
    assert ids == []
    assert arns == []


def test_list_bedrock_profiles_no_profiles(mocker):
    """Test list_bedrock_profiles when no profiles are found."""
    mock_boto_session = MagicMock()
    mock_boto_client = MagicMock()
    mock_boto_client.list_inference_profiles.return_value = {"inferenceProfileSummaries": []}
    mock_boto_session.client.return_value = mock_boto_client
    mocker.patch("boto3.Session", return_value=mock_boto_session)
    
    ids, arns = list_bedrock_profiles("test", "us-east-1")
    assert ids == []
    assert arns == []
