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
