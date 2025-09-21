# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
AWS utilities for CLAUTH.

This module provides AWS-specific functionality including authentication checking,
Bedrock model discovery, and AWS service interactions. It handles AWS SSO
authentication verification and retrieves available Bedrock inference profiles.

Functions:
    user_is_authenticated: Check if user has valid AWS credentials
    list_bedrock_profiles: Discover available Bedrock inference profiles
"""

import boto3 
from botocore.config import Config
from botocore.exceptions import NoCredentialsError, ClientError,BotoCoreError ,TokenRetrievalError





def user_is_authenticated(profile: str) -> bool:
    """Check if user is authenticated with AWS using the specified profile."""
    try:
        session = boto3.Session(profile_name=profile)
        sts = session.client("sts")
        ident = sts.get_caller_identity()
        account_id = ident["Account"]
        # print(f'User account: {account_id}')
        return True
    except (NoCredentialsError, TokenRetrievalError):
        print("No credentials found. Please run 'clauth init' to set up authentication.")
        return False
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("UnauthorizedSSOToken", "ExpiredToken", "InvalidClientTokenId"):
            print(f"Credentials expired or invalid. Please run 'clauth init' to re-authenticate.")
            return False
        else:
            print(f'Error getting token: {e}')
            return False
    except Exception as e:
        print(f'Unexpected error during authentication: {e}')
        return False

def list_bedrock_profiles(profile: str, region: str, provider: str = 'anthropic', sort: bool = True) -> tuple[list[str], list[str]]:
    """
    List available Bedrock inference profiles for the specified provider.

    Args:
        profile: AWS profile name to use
        region: AWS region to query
        provider: Model provider to filter by (default: 'anthropic')
        sort: Whether to sort results in reverse order (default: True)

    Returns:
        Tuple of (model_ids, model_arns) lists
    """
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        client = session.client("bedrock")

        resp = client.list_inference_profiles()
        inference_summaries = resp.get("inferenceProfileSummaries", [])

        if not inference_summaries:
            print(f"No inference profiles found in region {region}")
            return [], []

        model_arns = [p["inferenceProfileArn"] for p in inference_summaries]

        if model_arns and sort:
            model_arns.sort(reverse=True)

        # Filter by provider
        model_arn_by_provider = [arn for arn in model_arns if provider.lower() in arn.lower()]

        if not model_arn_by_provider:
            print(f"No models found for provider '{provider}' in region {region}")
            return [], []

        model_ids = [arn.split('/')[-1] for arn in model_arn_by_provider]
        return model_ids, model_arn_by_provider

    except (BotoCoreError, ClientError) as e:
        print(f"Error listing inference profiles: {e}")
        return [], []
    except Exception as e:
        print(f"Unexpected error listing models: {e}")
        return [], []
    
if __name__=='__main__':
    p=list_bedrock_profiles(profile='clauth',region='ap-southeast-2')
    print('===============')
    print(p)