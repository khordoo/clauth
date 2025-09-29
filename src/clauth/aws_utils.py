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

import typer
import subprocess
import boto3
from rich.console import Console
from clauth.ui import render_status
from botocore.config import Config
from botocore.exceptions import (
    NoCredentialsError,
    ClientError,
    BotoCoreError,
    TokenRetrievalError,
)


console = Console()


def setup_iam_user_auth(profile: str, region: str) -> bool:
    """
    Set up IAM user authentication for solo developers.

    Args:
        profile: AWS profile name to configure
        region: Default AWS region

    Returns:
        bool: True if setup successful, False otherwise
    """
    try:
        # Set the region first, so it's the default in the interactive prompt
        subprocess.run(
            ["aws", "configure", "set", "region", region, "--profile", profile],
            check=True,
        )

        # Run aws configure for the specific profile to get keys
        subprocess.run(["aws", "configure", "--profile", profile], check=True)

        # Clear any lingering SSO settings using configparser to ensure they are removed
        try:
            from pathlib import Path
            import configparser

            home = Path.home()
            aws_config_file = home / ".aws" / "config"

            if aws_config_file.exists():
                config_parser = configparser.ConfigParser()
                config_parser.read(aws_config_file)
                profile_section = f"profile {profile}"
                if config_parser.has_section(profile_section):
                    sso_settings_to_clear = [
                        "sso_start_url",
                        "sso_region",
                        "sso_account_id",
                        "sso_role_name",
                        "sso_session",
                    ]
                    for setting in sso_settings_to_clear:
                        if config_parser.has_option(profile_section, setting):
                            config_parser.remove_option(profile_section, setting)
                    with open(aws_config_file, "w") as f:
                        config_parser.write(f)
        except Exception as e:
            render_status(
                f"Warning: Could not clean SSO settings from AWS config: {e}",
                level="warning",
            )

        # Verify that the credentials are valid
        if not user_is_authenticated(profile=profile):
            render_status(
                "IAM authentication failed. Please check your credentials and try again.",
                level="error",
            )
            return False
        render_status(
            f"IAM user authentication configured for profile '{profile}'",
            level="success",
        )
        return True
    except subprocess.CalledProcessError:
        render_status(
            "Failed to configure IAM user authentication.",
            level="error",
        )
        return False


def setup_sso_auth(config, cli_overrides) -> bool:
    """
    Set up AWS SSO authentication for enterprise users.

    Args:
        config: Configuration object with SSO settings
        cli_overrides: Dict indicating which CLI parameters were provided

    Returns:
        bool: True if setup successful, False otherwise
    """
    # Set up basic profile configuration before SSO
    args = {
        "region": config.aws.region,  # Pass default AWS region to avoid extra prompt
        "output": config.aws.output_format,
        "sso_session": config.aws.session_name,  # Pre-set session name for consistency
        "sso_region": config.aws.region,
    }

    try:
        # Setup the basic profile entries
        for arg, value in args.items():
            subprocess.run(
                [
                    "aws",
                    "configure",
                    "set",
                    arg,
                    value,
                    "--profile",
                    config.aws.profile,
                ],
                check=True,
            )

        subprocess.run(
            ["aws", "configure", "sso", "--profile", config.aws.profile], check=True
        )
        # Check for existing SSO session to reuse sso_start_url, cli complnas if its not availbane in profile but swet in session
        # aws cli will complain if sso_start_url is not set in session but set in profile):

        existing_sso_start_url = (
            get_existing_sso_start_url(config.aws.session_name)
            or config.aws.sso_start_url
        )
        if existing_sso_start_url:
            render_status(
                f"Reusing existing SSO Start URL from session '{config.aws.session_name}'",
                level="info",
            )
            subprocess.run(
                [
                    "aws",
                    "configure",
                    "set",
                    "sso_start_url",
                    existing_sso_start_url,
                    "--profile",
                    config.aws.profile,
                ]
            )
        subprocess.run(["aws", "sso", "login", "--profile", config.aws.profile])
        render_status(
            f"Authentication successful for profile '{config.aws.profile}'.",
            level="success",
        )
        return True
    except subprocess.CalledProcessError:
        render_status("SSO setup failed.", level="error")
        return False


# Configuration management command group
# config_app = typer.Typer(help="Configuration management commands")
# app.add_typer(config_app, name="config")


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
        render_status(
            "No credentials found. Please run `clauth init` to set up authentication.",
            level="error",
        )
        return False
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in (
            "UnauthorizedSSOToken",
            "ExpiredToken",
            "InvalidClientTokenId",
        ):
            render_status(
                "Credentials expired or invalid. Please run `clauth init` to re-authenticate.",
                level="error",
            )
            return False
        else:
            render_status(f"Error getting token: {e}", level="error")
            return False
    except Exception as e:
        render_status(f"Unexpected error during authentication: {e}", level="error")
        return False


def get_existing_sso_start_url(session_name: str) -> str | None:
    """Get the existing SSO start URL from an SSO session.

    Args:
        session_name: Name of the SSO session to check

    Returns:
        str | None: The SSO start URL if found, None otherwise
    """
    try:
        from pathlib import Path
        import configparser

        aws_config_file = Path.home() / ".aws" / "config"
        if not aws_config_file.exists():
            return None

        config_parser = configparser.ConfigParser()
        config_parser.read(aws_config_file)

        session_section = f"sso-session {session_name}"
        if config_parser.has_section(session_section):
            return config_parser.get(session_section, "sso_start_url", fallback=None)

        return None

    except Exception:
        # If we can't read the config, return None
        return None


def remove_sso_session(session_name: str) -> bool:
    """Remove SSO session section from ~/.aws/config.

    Args:
        session_name: Name of the SSO session to remove

    Returns:
        bool: True if session was removed or didn't exist, False on error
    """
    try:
        from pathlib import Path
        import configparser

        # Get AWS config file path
        home = Path.home()
        aws_config_file = home / ".aws" / "config"

        if not aws_config_file.exists():
            render_status("No AWS config file found.", level="info")
            return True

        # Read the AWS config file
        config_parser = configparser.ConfigParser()
        config_parser.read(aws_config_file)

        # SSO sessions are stored as [sso-session <name>]
        sso_section_name = f"sso-session {session_name}"

        if sso_section_name in config_parser.sections():
            config_parser.remove_section(sso_section_name)

            # Write back to file
            with open(aws_config_file, "w") as f:
                config_parser.write(f)

            render_status(
                f"Removed SSO session '{session_name}' from AWS config.",
                level="success",
            )
        else:
            render_status(
                f"SSO session '{session_name}' not found in AWS config.",
                level="info",
            )

        return True

    except Exception as e:
        render_status(
            f"Failed to remove SSO session '{session_name}': {e}",
            level="error",
        )
        return False


def clear_sso_cache(profile_name: str = None) -> bool:
    """Clear AWS SSO token cache.

    Args:
        profile_name: Optional profile name for targeted cleanup

    Returns:
        bool: True if cache was cleared successfully, False on error
    """
    try:
        import shutil
        from pathlib import Path

        # Get AWS cache directory
        home = Path.home()
        aws_cache_dir = home / ".aws" / "sso" / "cache"

        if not aws_cache_dir.exists():
            render_status("No SSO cache directory found.", level="info")
            return True

        # Clear all SSO cache files
        cache_files_deleted = 0
        for cache_file in aws_cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cache_files_deleted += 1
            except Exception as e:
                render_status(
                    f"Warning: Could not delete cache file {cache_file.name}: {e}",
                    level="warning",
                )

        if cache_files_deleted > 0:
            render_status(
                f"Cleared {cache_files_deleted} SSO cache files.",
                level="success",
            )
        else:
            render_status("No SSO cache files found to clear.", level="info")

        return True

    except Exception as e:
        render_status(f"Error clearing SSO cache: {e}", level="error")
        return False


def delete_aws_credentials_profile(profile_name: str) -> bool:
    """Delete an AWS profile from ~/.aws/credentials.

    Args:
        profile_name: Name of the AWS profile to delete

    Returns:
        bool: True if profile was deleted or didn't exist, False on error
    """
    try:
        from pathlib import Path
        import configparser

        home = Path.home()
        aws_credentials_file = home / ".aws" / "credentials"

        if not aws_credentials_file.exists():
            render_status(
                "No AWS credentials file found to delete profile from.",
                level="info",
            )
            return True

        config_parser = configparser.ConfigParser()
        config_parser.read(aws_credentials_file)

        if config_parser.has_section(profile_name):
            config_parser.remove_section(profile_name)
            with open(aws_credentials_file, "w") as f:
                config_parser.write(f)
            render_status(
                f"AWS credentials for profile '{profile_name}' deleted successfully.",
                level="success",
            )
        else:
            render_status(
                f"AWS credentials for profile '{profile_name}' do not exist.",
                level="info",
            )

        return True

    except Exception as e:
        render_status(
            f"Unexpected error deleting AWS credentials profile: {e}",
            level="error",
        )
        return False


def delete_aws_profile(profile_name: str) -> bool:
    """Delete an AWS profile from ~/.aws/config.

    Args:
        profile_name: Name of the AWS profile to delete

    Returns:
        bool: True if profile was deleted or didn't exist, False on error
    """
    try:
        from pathlib import Path
        import configparser

        home = Path.home()
        aws_config_file = home / ".aws" / "config"

        if not aws_config_file.exists():
            render_status(
                "No AWS config file found to delete profile from.",
                level="info",
            )
            return True

        config_parser = configparser.ConfigParser()
        config_parser.read(aws_config_file)

        profile_section = f"profile {profile_name}"
        if config_parser.has_section(profile_section):
            config_parser.remove_section(profile_section)
            with open(aws_config_file, "w") as f:
                config_parser.write(f)
            render_status(
                f"AWS profile '{profile_name}' deleted successfully.",
                level="success",
            )
        else:
            render_status(
                f"AWS profile '{profile_name}' does not exist in config file.",
                level="info",
            )

        return True

    except Exception as e:
        render_status(
            f"Unexpected error deleting AWS profile: {e}",
            level="error",
        )
        return False


def list_bedrock_profiles(
    profile: str, region: str, provider: str = "anthropic", sort: bool = True
) -> tuple[list[str], list[str]]:
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
        model_arn_by_provider = [
            arn for arn in model_arns if provider.lower() in arn.lower()
        ]

        if not model_arn_by_provider:
            print(f"No models found for provider '{provider}' in region {region}")
            return [], []

        model_ids = [arn.split("/")[-1] for arn in model_arn_by_provider]
        return model_ids, model_arn_by_provider

    except (BotoCoreError, ClientError) as e:
        print(f"Error listing inference profiles: {e}")
        return [], []
    except Exception as e:
        print(f"Unexpected error listing models: {e}")
        return [], []


if __name__ == "__main__":
    p = list_bedrock_profiles(profile="clauth", region="ap-southeast-2")
    print("===============")
    print(p)
