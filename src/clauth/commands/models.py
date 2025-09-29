"""
CLAUTH Model Management Commands.

This module provides commands for listing and managing Bedrock models,
organized under a 'model' subcommand group.
"""

import typer
from clauth.config import get_config_manager
from clauth.aws_utils import user_is_authenticated, list_bedrock_profiles
from clauth.helpers import handle_authentication_failure
from InquirerPy import inquirer, get_style
from clauth.ui import render_card, render_status, console, Spinner

model_app = typer.Typer(
    name="model",
    help="Manage and switch between Bedrock models.",
    no_args_is_help=True,
)


@model_app.command("list")
def list_models(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    show_arn: bool = typer.Option(False, "--show-arn", help="Show model ARNs"),
):
    """
    List available Bedrock models.
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

    with Spinner("Discovering Bedrock models"):
        model_ids, model_arns = list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter,
        )

    if not model_ids:
        render_status(
            "No models found for the current profile and region.",
            level="warning",
            footer="Check your AWS permissions or choose a different region.",
        )
        return

    lines: list[str] = []
    for model_id, model_arn in zip(model_ids, model_arns):
        if show_arn:
            lines.append(f"{model_id}\n  {model_arn}")
        else:
            lines.append(model_id)

    render_card(
        title="Available models",
        body="\n".join(lines),
        footer=f"Found {len(model_ids)} model(s) in {config.aws.region}.",
    )


@model_app.command("switch")
def switch_models(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    default_only: bool = typer.Option(
        False, "--default-only", help="Only change default model"
    ),
    fast_only: bool = typer.Option(False, "--fast-only", help="Only change fast model"),
):
    """
    Interactively switch the default and fast models.
    """
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    if profile is not None:
        config.aws.profile = profile
    if region is not None:
        config.aws.region = region

    # Validate that both flags aren't set
    if default_only and fast_only:
        render_status(
            "Cannot use both --default-only and --fast-only together.",
            level="error",
        )
        raise typer.Exit(1)

    # Check authentication
    if not user_is_authenticated(profile=config.aws.profile):
        if not handle_authentication_failure(config.aws.profile):
            raise typer.Exit(1)

    # Check if models are configured
    if not config.models.default_model or not config.models.fast_model:
        render_status(
            "Model configuration missing. Run `clauth init` first.",
            level="error",
        )
        raise typer.Exit(1)

    render_card(
        title="Current models",
        body="\n".join(
            [
                f"Default: {config.models.default_model}",
                f"Fast: {config.models.fast_model}",
            ]
        ),
    )

    # Discover available models
    with Spinner("Finding available models"):
        model_ids, model_arns = list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter,
        )

    if not model_ids:
        render_status(
            "No models found for the current profile and region.",
            level="error",
            footer="Check AWS permissions or try a different region.",
        )
        raise typer.Exit(1)

    # Create model map for ARN lookup
    model_map = {id: arn for id, arn in zip(model_ids, model_arns)}

    # Get custom style for inquirer
    custom_style = get_style(config_manager.get_custom_style())

    # Initialize with current values
    new_default_model = config.models.default_model
    new_fast_model = config.models.fast_model

    # Interactive model selection
    if not fast_only:
        render_card(
            title="Select default model",
            body="Choose the main model CLAUTH should use for Claude Code.",
            footer="Controls: ↑/↓ move · Enter select",
        )
        # Select new default model
        new_default_model = inquirer.select(
            message="Select new default model:",
            instruction=None,
            pointer="▶ ",
            amark="✔",
            choices=model_ids,
            default=config.models.default_model
            if config.models.default_model in model_ids
            else (model_ids[0] if model_ids else None),
            style=custom_style,
            max_height="100%",
        ).execute()

    if not default_only:
        render_card(
            title="Select fast model",
            body="Choose the small/fast model for quick tasks.",
            footer="Controls: ↑/↓ move · Enter select",
        )
        # Select new fast model
        new_fast_model = inquirer.select(
            message="Select new small/fast model:",
            instruction=None,
            pointer="▶ ",
            amark="✔",
            choices=model_ids,
            default=config.models.fast_model
            if config.models.fast_model in model_ids
            else (model_ids[-1] if model_ids else None),
            style=custom_style,
            max_height="100%",
        ).execute()

    # Check if anything changed
    if (
        new_default_model == config.models.default_model
        and new_fast_model == config.models.fast_model
    ):
        render_status("No changes made.", level="info")
        return

    # Update configuration
    config_manager.update_model_settings(
        default_model=new_default_model,
        fast_model=new_fast_model,
        default_arn=model_map[new_default_model],
        fast_arn=model_map[new_fast_model],
    )

    # Show confirmation
    render_card(
        title="Models updated",
        body="\n".join(
            [
                f"Default: {new_default_model}",
                f"Fast: {new_fast_model}",
            ]
        ),
        footer="Updates saved to CLAUTH configuration.",
    )
