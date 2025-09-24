"""
CLAUTH Model Management Commands.

This module provides commands for listing and managing Bedrock models.
"""

import typer
from clauth.config import get_config_manager
from clauth.aws_utils import user_is_authenticated, list_bedrock_profiles
from clauth.helpers import handle_authentication_failure
from rich.console import Console

console = Console()


def list_models(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    show_arn: bool = typer.Option(False, "--show-arn", help="Show model ARNs")
):
    """
    List available Bedrock inference profiles.

    Discovers and displays all available Bedrock models that can be used
    with Claude Code. Optionally shows full ARNs for the models.

    Args:
        profile: AWS profile to use (default from config)
        region: AWS region to use (default from config)
        show_arn: Whether to display full model ARNs
    """
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    if profile is not None:
        config.aws.profile = profile
    if region is not None:
        config.aws.region = region

    if not user_is_authenticated(profile=config.aws.profile):
        if not handle_authentication_failure(config.aws.profile):
            raise typer.Exit(1)

    with console.status("[bold blue]Fetching available models...") as status:
        model_ids, model_arns = list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter
        )
    for model_id, model_arn in zip(model_ids, model_arns):
        if show_arn:
            print(model_id, ' --> ', model_arn)
        else:
            print(model_id)
