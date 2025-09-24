"""
CLAUTH Model Management Commands.

This module provides commands for listing and managing Bedrock models.
"""

import typer
from clauth.config import get_config_manager
from clauth.aws_utils import user_is_authenticated, list_bedrock_profiles
from clauth.helpers import handle_authentication_failure
from rich.console import Console
from InquirerPy import inquirer, get_style

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


def switch_models(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    default_only: bool = typer.Option(False, "--default-only", help="Only change default model"),
    fast_only: bool = typer.Option(False, "--fast-only", help="Only change fast model")
):
    """
    Interactive model switcher for quick model changes.

    Shows current models and provides an interactive menu to select new
    default and fast models without going through full setup.

    Args:
        profile: AWS profile to use (default from config)
        region: AWS region to use (default from config)
        default_only: Only change the default model, keep fast model unchanged
        fast_only: Only change the fast model, keep default model unchanged
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
        typer.secho("Error: Cannot use both --default-only and --fast-only flags together.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Check authentication
    if not user_is_authenticated(profile=config.aws.profile):
        if not handle_authentication_failure(config.aws.profile):
            raise typer.Exit(1)

    # Check if models are configured
    if not config.models.default_model or not config.models.fast_model:
        typer.secho("Model configuration missing. Run 'clauth init' for initial setup.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Show current models
    console.print("\n[bold cyan]Current Models[/bold cyan]")
    console.print(f"  Default: [green]{config.models.default_model}[/green]")
    console.print(f"  Fast: [green]{config.models.fast_model}[/green]")
    console.print()

    # Discover available models
    with console.status("[bold blue]Discovering available models...") as status:
        model_ids, model_arns = list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter
        )

    if not model_ids:
        typer.secho("No models found. Check your AWS permissions and region.", fg=typer.colors.RED)
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
        # Select new default model
        new_default_model = inquirer.select(
            message="Select new default model:",
            instruction="↑↓ move • Enter select",
            pointer="> ",
            amark="✔",
            choices=model_ids,
            default=config.models.default_model if config.models.default_model in model_ids else (model_ids[0] if model_ids else None),
            style=custom_style,
            max_height="100%"
        ).execute()

    if not default_only:
        # Select new fast model
        new_fast_model = inquirer.select(
            message="Select new small/fast model:",
            instruction="↑↓ move • Enter select",
            pointer="> ",
            amark="✔",
            choices=model_ids,
            default=config.models.fast_model if config.models.fast_model in model_ids else (model_ids[-1] if model_ids else None),
            style=custom_style,
            max_height="100%"
        ).execute()

    # Check if anything changed
    if new_default_model == config.models.default_model and new_fast_model == config.models.fast_model:
        console.print("[yellow]No changes made.[/yellow]")
        return

    # Update configuration
    config_manager.update_model_settings(
        default_model=new_default_model,
        fast_model=new_fast_model,
        default_arn=model_map[new_default_model],
        fast_arn=model_map[new_fast_model]
    )

    # Show confirmation
    console.print("\n[bold green]✅ Models updated successfully![/bold green]")
    console.print(f"  Default: [green]{new_default_model}[/green]")
    console.print(f"  Fast: [green]{new_fast_model}[/green]")


def sm(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    default_only: bool = typer.Option(False, "--default-only", help="Only change default model"),
    fast_only: bool = typer.Option(False, "--fast-only", help="Only change fast model")
):
    """Shorthand for switch-models. Interactive model switcher for quick model changes."""
    # Delegate to the main switch_models function
    switch_models(profile, region, default_only, fast_only)
