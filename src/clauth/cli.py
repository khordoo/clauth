# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH Command Line Interface.

This module provides the main CLI interface for CLAUTH, a tool that streamlines
AWS Bedrock setup for Claude Code. It handles AWS SSO authentication, model
discovery, environment configuration, and Claude Code CLI launching.

Main Commands:
    init: Interactive setup wizard for AWS SSO and model selection
    list-models: Display available Bedrock inference profiles
    claude: Launch Claude Code CLI with proper environment
    config: Configuration management (show, set, reset, profiles)
"""

import typer
import subprocess
import os
import clauth.aws_utils as aws
from clauth.config import get_config_manager, ClauthConfig
from clauth.commands import claude, list_models
from clauth.helpers import (
    ExecutableNotFoundError, clear_screen, get_app_path,
    handle_authentication_failure, is_sso_profile
)
from InquirerPy import inquirer
from textwrap import dedent
from rich.console import Console
from InquirerPy import get_style
from pyfiglet import Figlet



app = typer.Typer()
env = os.environ.copy()
console = Console()
#TODO: get a list of availbale models from aws cli

# Register commands from modules
app.command()(claude)
app.command()(list_models)


@app.command(
        help=(
        "First-time setup for CLAUTH: configures AWS authentication (SSO or IAM user), "
        "discovers models, and optionally launches the Claude CLI."
    )
)
def init(
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="AWS profile to create or update (saved under [profile <name>] in ~/.aws/config).",
        rich_help_panel="AWS Profile",
    ),
    session_name: str = typer.Option(
        None,
        "--session-name",
        "-s",
        help="Name of the SSO session to create (saved under [sso-session <name>] in ~/.aws/config).",
        rich_help_panel="AWS SSO",
    ),
    sso_start_url: str = typer.Option(
        None,
        "--sso-start-url",
        help="IAM Identity Center (SSO) Start URL (e.g., https://d-…awsapps.com/start/).",
        rich_help_panel="AWS SSO",
    ),
    sso_region: str = typer.Option(
        None,
        "--sso-region",
        help="Region that hosts your IAM Identity Center (SSO) instance.",
        rich_help_panel="AWS SSO",
    ),
    region: str = typer.Option(
        None,
        "--region",
        "-r",
        help="Default AWS client region for this profile (used for STS/Bedrock calls).",
        rich_help_panel="AWS Profile",
    ),
    auto_start: bool = typer.Option(
        None,
        "--auto-start/--no-auto-start",
        help="Launch the Claude CLI immediately after successful setup.",
        rich_help_panel="Behavior",
    ),
  ):
    """
    Interactive setup wizard for CLAUTH.

    Configures AWS authentication (SSO or IAM user), discovers available Bedrock models,
    and optionally launches Claude Code CLI with proper environment variables.
    This is the main entry point for first-time CLAUTH setup.

    Args:
        profile: AWS profile name to create/update (default from config)
        session_name: SSO session name (default from config, SSO only)
        sso_start_url: IAM Identity Center start URL (default from config, SSO only)
        sso_region: SSO region (default from config, SSO only)
        region: Default AWS region for profile (default from config)
        auto_start: Whether to launch Claude Code after setup (default from config)
    """
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    # Override config with CLI parameters if provided
    if profile is not None:
        config.aws.profile = profile
    if session_name is not None:
        config.aws.session_name = session_name
    if sso_start_url is not None:
        config.aws.sso_start_url = sso_start_url
    if sso_region is not None:
        config.aws.sso_region = sso_region
    if region is not None:
        config.aws.region = region
    if auto_start is not None:
        config.cli.auto_start = auto_start

    show_welcome_logo(console=console)

    try:
        # Check if user is already authenticated - skip credential setup if so
        if aws.user_is_authenticated(profile=config.aws.profile):
            typer.secho(f"✅ Already authenticated with AWS profile '{config.aws.profile}'", fg=typer.colors.GREEN)
            typer.echo("Skipping credential setup...")
        else:
            typer.secho("Step 1/3 — Configuring AWS authentication...", fg=typer.colors.BLUE)
            typer.echo()

            auth_method = choose_auth_method()
            typer.echo()

            if auth_method == "skip":
                typer.secho("⏭️ Skipping authentication setup", fg=typer.colors.YELLOW)
                typer.echo("Note: You may need to authenticate manually if commands fail")
            elif auth_method == "iam":
                if not setup_iam_user_auth(config.aws.profile, config.aws.region):
                    raise typer.Exit(1)
            elif auth_method == "sso":
                if not setup_sso_auth(config):
                    raise typer.Exit(1)

        typer.secho("Step 2/3 — Configuring models...", fg=typer.colors.BLUE)

        # Check if we have existing model configuration
        if config.models.default_model_arn and config.models.fast_model_arn:
            typer.echo(f"Found existing model configuration:")
            typer.echo(f"  Default model: {config.models.default_model}")
            typer.echo(f"  Small/Fast model: {config.models.fast_model}")

            # Get custom style from config manager
            custom_style = get_style(config_manager.get_custom_style())

            use_existing = inquirer.confirm(
                message="Use existing model configuration?",
                default=True,
                style=custom_style
            ).execute()

            if use_existing:
                model_id_default = config.models.default_model
                model_id_fast = config.models.fast_model
                model_map = {
                    model_id_default: config.models.default_model_arn,
                    model_id_fast: config.models.fast_model_arn
                }
                typer.echo(f"Using saved models: {model_id_default}, {model_id_fast}")
            else:
                # Re-discover and select models
                with console.status("[bold blue]Discovering available models...") as status:
                    model_ids, model_arns = aws.list_bedrock_profiles(
                        profile=config.aws.profile,
                        region=config.aws.region,
                        provider=config.models.provider_filter
                    )

                model_id_default = inquirer.select(
                    message="Select your [default] model:",
                    instruction="↑↓ move • Enter select",
                    pointer="> ",
                    amark="✔",
                    choices=model_ids,
                    default=config.models.default_model if config.models.default_model in model_ids else (model_ids[0] if model_ids else None),
                    style=custom_style,
                    max_height="100%"
                ).execute()

                model_id_fast = inquirer.select(
                    message="Select your [small/fast] model (you can choose the same as default):",
                    instruction="↑↓ move • Enter select",
                    pointer="> ",
                    amark="✔",
                    choices=model_ids,
                    default=config.models.fast_model if config.models.fast_model in model_ids else (model_ids[-1] if model_ids else None),
                    style=custom_style,
                    max_height="100%"
                ).execute()

                model_map = {id:arn for id,arn in zip(model_ids,model_arns)}

                # Save updated model selections to configuration
                config_manager.update_model_settings(
                    default_model=model_id_default,
                    fast_model=model_id_fast,
                    default_arn=model_map[model_id_default],
                    fast_arn=model_map[model_id_fast]
                )
        else:
            # No existing configuration, do full model discovery and selection
            with console.status("[bold blue]Discovering available models...") as status:
                model_ids, model_arns = aws.list_bedrock_profiles(
                    profile=config.aws.profile,
                    region=config.aws.region,
                    provider=config.models.provider_filter
                )

            # Get custom style from config manager
            custom_style = get_style(config_manager.get_custom_style())

            model_id_default = inquirer.select(
                message="Select your [default] model:",
                instruction="↑↓ move • Enter select",
                pointer="> ",
                amark="✔",
                choices=model_ids,
                default=model_ids[0] if model_ids else None,
                style=custom_style,
                max_height="100%"
            ).execute()

            model_id_fast = inquirer.select(
                message="Select your [small/fast] model (you can choose the same as default):",
                instruction="↑↓ move • Enter select",
                pointer="> ",
                amark="✔",
                choices=model_ids,
                default=model_ids[-1] if model_ids else None,
                style=custom_style,
                max_height="100%"
            ).execute()

            model_map = {id:arn for id,arn in zip(model_ids,model_arns)}

            # Save model selections to configuration
            config_manager.update_model_settings(
                default_model=model_id_default,
                fast_model=model_id_fast,
                default_arn=model_map[model_id_default],
                fast_arn=model_map[model_id_fast]
            )

        typer.echo(f"Default model: {model_id_default}")
        typer.echo(f"Small/Fast model: {model_id_fast}")

        env.update(
            {
                "AWS_PROFILE": config.aws.profile,
                "AWS_REGION": config.aws.region,
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "ANTHROPIC_MODEL": model_map[model_id_default],
                "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_map[model_id_fast],
            }
        )

        typer.echo(f"default model: {model_id_default}\n small/fast model: {model_id_fast}\n")

        if config.cli.auto_start:
            typer.secho("Setup complete ✅", fg=typer.colors.GREEN)
            typer.secho("Step 3/3 — Launching Claude Code...",fg=typer.colors.BLUE)
            try:
                claude_path = get_app_path(config.cli.claude_cli_name)
                clear_screen()
                subprocess.run([claude_path], env=env, check=True)
            except ExecutableNotFoundError as e:
                typer.secho(f"Setup failed: {e}", fg=typer.colors.RED)
                typer.secho(f"Please install Claude Code CLI and ensure it's in your PATH.", fg=typer.colors.YELLOW)
                raise typer.Exit(1)
            except ValueError as e:
                typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
                raise typer.Exit(1)
        else:
            typer.secho("Step 3/3 — Setup complete.", fg=typer.colors.GREEN)
            typer.echo("Run the Claude Code CLI when you're ready: ", nl=False)
            typer.secho(config.cli.claude_cli_name, bold=True)

    except subprocess.CalledProcessError as e:
        typer.secho(f"Setup failed. Exit code: {e.returncode}", fg=typer.colors.RED)
        exit(f"Failed to setup. Error Code: {e.returncode}")
   
def show_welcome_logo(console: Console)->None:
    """
    Display the CLAUTH welcome logo.

    Args:
        console: Rich console instance for styled output
    """
    f = Figlet(font='slant')
    logo = f.renderText('CLAUTH')
    console.print(logo, style="bold cyan")
   
    console.print(dedent("""
        [bold]Welcome to CLAUTH[/bold]
        Let’s set up your environment for Claude Code on Amazon Bedrock.

        Prerequisites:
          • AWS CLI v2
          • Claude Code CLI

        Tip: run [bold]clauth init --help[/bold] to view options.
    """).strip())












@app.command(name="switch-models")
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
    if not aws.user_is_authenticated(profile=config.aws.profile):
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
        model_ids, model_arns = aws.list_bedrock_profiles(
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


@app.command(name="sm")
def sm(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    default_only: bool = typer.Option(False, "--default-only", help="Only change default model"),
    fast_only: bool = typer.Option(False, "--fast-only", help="Only change fast model")
):
    """Shorthand for switch-models. Interactive model switcher for quick model changes."""
    # Delegate to the main switch_models function
    switch_models(profile, region, default_only, fast_only)





def choose_auth_method():
    """
    Interactive authentication method selection.

    Returns:
        str: Selected authentication method ('sso', 'iam', or 'skip')
    """
    from InquirerPy import inquirer
    from clauth.config import get_config_manager

    # Get custom style
    config_manager = get_config_manager()
    custom_style = get_style(config_manager.get_custom_style())

    return inquirer.select(
        message="Choose your authentication method:",
        instruction="↑↓ move • Enter select",
        choices=[
            {"name": "🏢 AWS SSO (for teams/organizations)", "value": "sso"},
            {"name": "🔑 IAM User Access Keys (for solo developers)", "value": "iam"},
            {"name": "⏭️  Skip (I'm already configured)", "value": "skip"}
        ],
        pointer="> ",
        amark="✔",
        style=custom_style,
        max_height="100%"
    ).execute()


def setup_iam_user_auth(profile: str, region: str) -> bool:
    """
    Set up IAM user authentication for solo developers.

    Args:
        profile: AWS profile name to configure
        region: Default AWS region

    Returns:
        bool: True if setup successful, False otherwise
    """
    typer.secho("Setting up IAM user authentication...", fg=typer.colors.BLUE)
    typer.echo("You'll need your AWS Access Key ID and Secret Access Key.")
    typer.echo("Get these from: AWS Console → IAM → Users → [Your User] → Security credentials")
    typer.echo()

    try:
        # Run aws configure for the specific profile
        subprocess.run(["aws", "configure", "--profile", profile], check=True)

        # Set the region
        subprocess.run(["aws", "configure", "set", "region", region, "--profile", profile], check=True)

        typer.secho(f"✅ IAM user authentication configured for profile '{profile}'", fg=typer.colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        typer.secho("❌ Failed to configure IAM user authentication", fg=typer.colors.RED)
        return False


def setup_sso_auth(config) -> bool:
    """
    Set up AWS SSO authentication for enterprise users.

    Args:
        config: Configuration object with SSO settings

    Returns:
        bool: True if setup successful, False otherwise
    """
    # Prompt for SSO start URL if not provided
    if config.aws.sso_start_url is None:
        console.print("\n[bold]SSO Start URL Required[/bold]")
        console.print("Please enter your IAM Identity Center (SSO) start URL.")
        console.print("This looks like: https://d-xxxxxxxxxx.awsapps.com/start/")
        console.print("You can find this in your AWS SSO portal or ask your AWS administrator.\n")

        sso_url = typer.prompt("SSO Start URL")

        # Basic validation
        if not sso_url.startswith('https://'):
            typer.secho("Error: SSO start URL must start with https://", fg=typer.colors.RED)
            return False

        config.aws.sso_start_url = sso_url

        # Save the updated config
        from .config import get_config_manager
        config_manager = get_config_manager()
        config_manager._config = config
        config_manager.save()

        console.print(f"[green]✓ SSO start URL saved: {sso_url}[/green]\n")

    args = {
        "sso_start_url": config.aws.sso_start_url,
        "sso_region": config.aws.sso_region,
        "region": config.aws.sso_region,
        'output': config.aws.output_format,
        'sso_session':'claude-auth',
        'sso_session.session_name.name': config.aws.session_name
    }

    try:
        typer.secho("Configuring AWS SSO profile...", fg=typer.colors.BLUE)
        # Setup the default profile entries for better UX
        for arg, value in args.items():
            subprocess.run(
                ["aws", "configure", "set", arg, value, "--profile", config.aws.profile],
                check=True,
            )

        typer.echo("Opening the AWS SSO wizard. You can accept the defaults unless your team specifies otherwise.")

        subprocess.run(["aws", "configure", "sso", "--profile", config.aws.profile], check=True)
        subprocess.run(["aws", "sso", "login", "--profile", config.aws.profile])
        typer.secho(f"Authentication successful for profile '{config.aws.profile}'.", fg=typer.colors.GREEN)
        return True
    except subprocess.CalledProcessError:
        typer.secho("❌ SSO setup failed", fg=typer.colors.RED)
        return False


def validate_model_id(id: str):
    """
    Validate that a model ID exists in available Bedrock profiles.

    Args:
        id: Model ID to validate

    Returns:
        str: The validated model ID

    Raises:
        typer.Exit: If model ID is not found in available models
    """
    config = get_config_manager().load()
    with console.status("[bold blue]Validating model ID...") as status:
        model_ids, model_arns = aws.list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter
        )
    if id not in model_ids:
        raise typer.BadParameter(f'{id} is not valid or supported model. Valid Models: {model_ids}')
    return id


# Configuration management command group
config_app = typer.Typer(help="Configuration management commands")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    profile: str = typer.Option(None, "--profile", help="Show specific profile configuration"),
    show_path: bool = typer.Option(False, "--path", help="Show configuration file location")
):
    """Display current configuration.

    Shows all configuration settings including AWS, model, and CLI preferences.
    Use --path to show the location of the configuration file.
    Use --profile to show configuration for a specific profile.
    """
    config_manager = get_config_manager()
    config = config_manager.load(profile)

    console.print("\n[bold cyan]CLAUTH Configuration[/bold cyan]")

    if profile:
        console.print(f"[bold]Profile:[/bold] {profile}")
    else:
        console.print("[bold]Profile:[/bold] default")

    if show_path:
        config_file = config_manager._get_config_file(profile)
        console.print(f"[bold]Config File:[/bold] {config_file}")

    console.print(f"\n[bold yellow]AWS Settings:[/bold yellow]")
    console.print(f"  Profile: {config.aws.profile}")
    console.print(f"  Region: {config.aws.region}")
    console.print(f"  SSO Start URL: {config.aws.sso_start_url or 'Not configured'}")
    console.print(f"  SSO Region: {config.aws.sso_region}")
    console.print(f"  Session Name: {config.aws.session_name}")
    console.print(f"  Output Format: {config.aws.output_format}")

    console.print(f"\n[bold yellow]Model Settings:[/bold yellow]")
    console.print(f"  Provider Filter: {config.models.provider_filter}")
    console.print(f"  Default Model: {config.models.default_model or 'Not set'}")
    console.print(f"  Fast Model: {config.models.fast_model or 'Not set'}")

    console.print(f"\n[bold yellow]CLI Settings:[/bold yellow]")
    console.print(f"  Claude CLI Name: {config.cli.claude_cli_name}")
    console.print(f"  Auto Start: {config.cli.auto_start}")
    console.print(f"  Show Progress: {config.cli.show_progress}")
    console.print(f"  Color Output: {config.cli.color_output}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Configuration key (e.g., aws.profile, models.provider_filter)"),
    value: str = typer.Argument(help="Configuration value"),
    profile: str = typer.Option(None, "--profile", help="Set value for specific profile")
):
    """Set a configuration value."""
    config_manager = get_config_manager()
    config = config_manager.load(profile)

    # Parse the key path (e.g., "aws.profile" -> ["aws", "profile"])
    key_parts = key.split('.')
    if len(key_parts) != 2:
        typer.secho("Error: Key must be in format 'section.setting' (e.g., 'aws.profile')", fg=typer.colors.RED)
        raise typer.Exit(1)

    section, setting = key_parts

    # Validate and set the configuration value
    try:
        if section == "aws":
            if hasattr(config.aws, setting):
                # Convert string values to appropriate types
                if setting in ["profile", "region", "sso_start_url", "sso_region", "session_name", "output_format"]:
                    setattr(config.aws, setting, value)
                else:
                    typer.secho(f"Error: Unknown AWS setting '{setting}'", fg=typer.colors.RED)
                    raise typer.Exit(1)
            else:
                typer.secho(f"Error: Unknown AWS setting '{setting}'", fg=typer.colors.RED)
                raise typer.Exit(1)

        elif section == "models":
            if hasattr(config.models, setting):
                if setting in ["provider_filter", "default_model", "fast_model", "default_model_arn", "fast_model_arn"]:
                    setattr(config.models, setting, value)
                else:
                    typer.secho(f"Error: Unknown model setting '{setting}'", fg=typer.colors.RED)
                    raise typer.Exit(1)
            else:
                typer.secho(f"Error: Unknown model setting '{setting}'", fg=typer.colors.RED)
                raise typer.Exit(1)

        elif section == "cli":
            if hasattr(config.cli, setting):
                if setting == "claude_cli_name":
                    setattr(config.cli, setting, value)
                elif setting in ["auto_start", "show_progress", "color_output"]:
                    # Convert to boolean
                    bool_value = value.lower() in ('true', '1', 'yes', 'on')
                    setattr(config.cli, setting, bool_value)
                else:
                    typer.secho(f"Error: Unknown CLI setting '{setting}'", fg=typer.colors.RED)
                    raise typer.Exit(1)
            else:
                typer.secho(f"Error: Unknown CLI setting '{setting}'", fg=typer.colors.RED)
                raise typer.Exit(1)

        else:
            typer.secho(f"Error: Unknown configuration section '{section}'. Valid sections: aws, models, cli", fg=typer.colors.RED)
            raise typer.Exit(1)

        # Save the updated configuration
        config_manager._config = config
        config_manager.save(profile)

        profile_text = f" (profile: {profile})" if profile else ""
        typer.secho(f"Set {key} = {value}{profile_text}", fg=typer.colors.GREEN)

    except Exception as e:
        typer.secho(f"Error: Failed to set configuration: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@config_app.command("reset")
def config_reset(
    profile: str = typer.Option(None, "--profile", help="Reset specific profile configuration"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """Reset configuration to defaults."""
    profile_text = f" for profile '{profile}'" if profile else ""

    if not confirm:
        if not typer.confirm(f"Are you sure you want to reset configuration{profile_text}?"):
            typer.echo("Configuration reset cancelled.")
            raise typer.Exit(0)

    config_manager = get_config_manager()

    # Create new default configuration
    default_config = ClauthConfig()
    config_manager._config = default_config
    config_manager.save(profile)

    typer.secho(f"Configuration reset to defaults{profile_text}", fg=typer.colors.GREEN)


@config_app.command("profiles")
def config_profiles():
    """List available configuration profiles."""
    config_manager = get_config_manager()
    profiles = config_manager.list_profiles()

    if not profiles:
        console.print("[yellow]No configuration profiles found.[/yellow]")
        return

    console.print("\n[bold cyan]Configuration Profiles:[/bold cyan]")
    for profile in profiles:
        console.print(f"  • {profile}")


def delete_aws_profile(profile_name: str) -> bool:
    """Delete an AWS profile from ~/.aws/config.

    Args:
        profile_name: Name of the AWS profile to delete

    Returns:
        bool: True if profile was deleted or didn't exist, False on error
    """
    try:
        # Use AWS CLI to remove the profile
        result = subprocess.run(
            ["aws", "configure", "list-profiles"],
            capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            console.print("[yellow]Warning: Could not list AWS profiles. AWS CLI may not be installed.[/yellow]")
            return True

        existing_profiles = result.stdout.strip().split('\n') if result.stdout.strip() else []

        if profile_name not in existing_profiles:
            console.print(f"[yellow]AWS profile '{profile_name}' does not exist.[/yellow]")
            return True

        # Remove the profile using AWS CLI
        subprocess.run(
            ["aws", "configure", "set", "region", "", "--profile", profile_name],
            check=True, capture_output=True
        )

        # Remove all profile settings
        settings_to_remove = [
            "region", "output", "aws_access_key_id", "aws_secret_access_key",
            "sso_start_url", "sso_region", "sso_account_id", "sso_role_name", "sso_session"
        ]

        for setting in settings_to_remove:
            subprocess.run(
                ["aws", "configure", "set", setting, "", "--profile", profile_name],
                capture_output=True, check=False
            )

        console.print(f"[green]SUCCESS: AWS profile '{profile_name}' deleted successfully.[/green]")
        return True

    except subprocess.CalledProcessError as e:
        console.print(f"[red]ERROR: Failed to delete AWS profile '{profile_name}': {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]ERROR: Unexpected error deleting AWS profile: {e}[/red]")
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
            console.print("[yellow]No SSO cache directory found.[/yellow]")
            return True

        # Clear all SSO cache files
        cache_files_deleted = 0
        for cache_file in aws_cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                cache_files_deleted += 1
            except Exception as e:
                console.print(f"[yellow]Warning: Could not delete cache file {cache_file.name}: {e}[/yellow]")

        if cache_files_deleted > 0:
            console.print(f"[green]SUCCESS: Cleared {cache_files_deleted} SSO cache files.[/green]")
        else:
            console.print("[yellow]No SSO cache files found to clear.[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]ERROR: Error clearing SSO cache: {e}[/red]")
        return False


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
            console.print("[yellow]No AWS config file found.[/yellow]")
            return True

        # Read the AWS config file
        config_parser = configparser.ConfigParser()
        config_parser.read(aws_config_file)

        # SSO sessions are stored as [sso-session <name>]
        sso_section_name = f"sso-session {session_name}"

        if sso_section_name in config_parser.sections():
            config_parser.remove_section(sso_section_name)

            # Write back to file
            with open(aws_config_file, 'w') as f:
                config_parser.write(f)

            console.print(f"[green]SUCCESS: Removed SSO session '{session_name}' from AWS config.[/green]")
        else:
            console.print(f"[yellow]SSO session '{session_name}' not found in AWS config.[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]ERROR: Failed to remove SSO session '{session_name}': {e}[/red]")
        return False


@app.command()
def reset(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to reset (default: from config)"),
    aws_only: bool = typer.Option(False, "--aws-only", help="Only reset AWS profile and SSO tokens"),
    config_only: bool = typer.Option(False, "--config-only", help="Only reset CLAUTH configuration"),
    complete: bool = typer.Option(False, "--complete", help="Completely delete CLAUTH config directory (more thorough)"),
    all_reset: bool = typer.Option(True, "--all", help="Reset everything (default)"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Comprehensive reset for testing authentication flows.

    Clears AWS profiles, SSO tokens, and CLAUTH configuration to allow
    testing the authentication setup process from scratch.
    """
    # Validate conflicting options
    if aws_only and config_only:
        typer.secho("Error: Cannot use both --aws-only and --config-only flags together.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if complete and (aws_only or config_only):
        typer.secho("Error: --complete flag cannot be used with --aws-only or --config-only.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Load configuration to get profile name if not specified
    config_manager = get_config_manager()
    config = config_manager.load()

    if profile is None:
        profile = config.aws.profile

    # Determine what to reset
    if complete:
        reset_aws = True
        reset_config = True
        complete_config_deletion = True
    else:
        reset_aws = not config_only
        reset_config = not aws_only
        complete_config_deletion = False

    # Show what will be reset
    console.print("\n[bold red]WARNING: RESET OPERATION[/bold red]")
    console.print("The following will be deleted:")

    if reset_aws:
        console.print(f"  - AWS profile: [yellow]{profile}[/yellow]")
        console.print("  - SSO token cache")
        console.print("  - SSO session configuration")

    if reset_config:
        if complete_config_deletion:
            console.print("  - [bold red]ENTIRE CLAUTH configuration directory[/bold red]")
        else:
            console.print("  - CLAUTH configuration files")

    console.print()

    # Confirmation
    if not confirm:
        if not typer.confirm("Are you sure you want to proceed with the reset?"):
            console.print("[yellow]Reset operation cancelled.[/yellow]")
            raise typer.Exit(0)

    success = True
    console.print("\n[bold blue]Starting reset operation...[/bold blue]")

    # Reset AWS profile and SSO cache
    if reset_aws:
        console.print(f"\n[bold]Step 1: Resetting AWS profile '{profile}'[/bold]")
        if not delete_aws_profile(profile):
            success = False

        console.print("\n[bold]Step 2: Clearing SSO token cache[/bold]")
        if not clear_sso_cache(profile):
            success = False

        console.print("\n[bold]Step 3: Removing SSO session configuration[/bold]")
        # Remove both hardcoded session name and config session name
        if not remove_sso_session("claude-auth"):
            success = False
        if not remove_sso_session(config.aws.session_name):
            success = False

    # Reset CLAUTH configuration
    if reset_config:
        step_num = 4 if reset_aws else 1
        console.print(f"\n[bold]Step {step_num}: Resetting CLAUTH configuration[/bold]")
        try:
            if complete_config_deletion:
                # Complete deletion - remove entire config directory
                import shutil
                if config_manager.config_dir.exists():
                    shutil.rmtree(config_manager.config_dir)
                    console.print(f"[green]SUCCESS: Completely removed config directory: {config_manager.config_dir}[/green]")
                else:
                    console.print("[yellow]Config directory already doesn't exist.[/yellow]")
            else:
                # Partial reset - reset to defaults and delete profiles
                default_config = ClauthConfig()
                config_manager._config = default_config
                config_manager.save()

                # Delete any profile-specific configs
                profiles = config_manager.list_profiles()
                for profile_name in profiles:
                    if config_manager.delete_profile(profile_name):
                        console.print(f"[green]Deleted profile config: {profile_name}[/green]")
                    else:
                        console.print(f"[yellow]Warning: Could not delete profile config: {profile_name}[/yellow]")

                console.print("[green]SUCCESS: CLAUTH configuration reset to defaults.[/green]")
        except Exception as e:
            console.print(f"[red]ERROR: Failed to reset CLAUTH configuration: {e}[/red]")
            success = False

    # Final status
    console.print()
    if success:
        console.print("[bold green]SUCCESS: Reset completed successfully![/bold green]")
        console.print("\nYou can now run [bold]clauth init[/bold] to test the authentication setup process.")
    else:
        console.print("[bold red]WARNING: Reset completed with some errors.[/bold red]")
        console.print("Check the messages above and try running the command again if needed.")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
