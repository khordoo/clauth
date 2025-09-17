import typer
import subprocess
import os
import shutil
import clauth.aws_utils as aws
from clauth.config import get_config_manager, ClauthConfig
from InquirerPy import inquirer
from textwrap import dedent
from rich.console import Console
from InquirerPy import get_style


class ExecutableNotFoundError(Exception):
    """Raised when executable cannot be found in system PATH."""
    pass



app = typer.Typer()
env = os.environ.copy()
console = Console()
#TODO: get a list of availbale models from aws cli


@app.command(
        help=(
        "First-time setup for CLAUTH: creates an SSO session, links an AWS profile, "
        "runs the AWS SSO wizard, logs you in, and optionally launches the Claude CLI."
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

    args = {
        "sso_start_url": config.aws.sso_start_url,
        "sso_region": config.aws.sso_region,
        "region": config.aws.sso_region,
        'output': config.aws.output_format,
        'sso_session':'claude-auth',
        'sso_session.session_name.name': config.aws.session_name
    }

    try:
        typer.secho("Step 1/3 — Configuring AWS SSO profile...",fg=typer.colors.BLUE)
        # Setup the default profile entries for better UX
        for arg, value in args.items():
            subprocess.run(
                ["aws", "configure", "set", arg, value, "--profile", config.aws.profile],
                check=True,
            )

        typer.echo("Opening the AWS SSO wizard. You can accept the defaults unless your team specifies otherwise.")

        subprocess.run(["aws", "configure", "sso", "--profile", config.aws.profile], check=True)
        subprocess.run(["aws", "sso", "login", "--profile", config.aws.profile])
        typer.secho(f"SSO login successful for profile '{config.aws.profile}'.", fg=typer.colors.GREEN)

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
                model_ids, model_arns = aws.list_bedrock_profiles(
                    profile=config.aws.profile,
                    region=config.aws.region,
                    provider=config.models.provider_filter
                )

                model_id_default = inquirer.select(
                    message="Select your [default] model:",
                    instruction="↑↓ move • Enter select",
                    pointer="❯",
                    amark="✔",
                    choices=model_ids,
                    default=config.models.default_model if config.models.default_model in model_ids else (model_ids[0] if model_ids else None),
                    style=custom_style,
                    max_height="100%"
                ).execute()

                model_id_fast = inquirer.select(
                    message="Select your [small/fast] model (you can choose the same as default):",
                    instruction="↑↓ move • Enter select",
                    pointer="❯",
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
                pointer="❯",
                amark="✔",
                choices=model_ids,
                default=model_ids[0] if model_ids else None,
                style=custom_style,
                max_height="100%"
            ).execute()

            model_id_fast = inquirer.select(
                message="Select your [small/fast] model (you can choose the same as default):",
                instruction="↑↓ move • Enter select",
                pointer="❯",
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

        typer.echo(f"""default model: {model_id_default}\n small/fast model: {model_id_fast}\n""")

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
    logo = """┌─────────────── CLAUTH ───────────────┐
│  Claude + AWS SSO helper for Bedrock │
└──────────────────────────────────────┘"""
    console.print(logo, style="bold cyan")
   
    console.print(dedent("""
        [bold]Welcome to CLAUTH[/bold]
        Let’s set up your environment for Claude Code on Amazon Bedrock.

        Prerequisites:
          • AWS CLI v2
          • Claude Code CLI

        Tip: run [bold]clauth init --help[/bold] to view options.
    """).strip())


def clear_screen():
    os.system('cls' if os.name=='nt' else 'clear')


def get_app_path(exe_name: str = 'claude') -> str:
    """Find the full path to an executable in a cross-platform way.

    On Windows, prefers .cmd and .exe versions when multiple variants exist,
    matching the original behavior that selected the .cmd version specifically.

    Args:
        exe_name: Name of the executable to find

    Returns:
        Full path to the executable

    Raises:
        ExecutableNotFoundError: If executable is not found in PATH
        ValueError: If executable name is invalid
    """
    if not exe_name or not exe_name.strip():
        raise ValueError(f'Invalid executable name provided: {exe_name!r}')

    # First, try the basic lookup
    claude_path = shutil.which(exe_name)
    if claude_path is None:
        raise ExecutableNotFoundError(f'{exe_name} not found in system PATH. Please ensure it is installed and in your PATH.')

    # On Windows, prefer .cmd/.exe versions if they exist (matches original behavior)
    if os.name == 'nt':
        preferred_extensions = ['.cmd', '.exe']
        for ext in preferred_extensions:
            if not exe_name.lower().endswith(ext):
                preferred_path = shutil.which(exe_name + ext)
                if preferred_path:
                    typer.echo(f"Found multiple {exe_name} executables, using: {preferred_path}")
                    return preferred_path

    typer.echo(f"Using executable: {claude_path}")
    return claude_path



@app.command()
def claude(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use")
):
    """Launch Claude Code with proper environment variables from saved configuration."""
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    if profile is not None:
        config.aws.profile = profile
    if region is not None:
        config.aws.region = region

    # Check if user is authenticated
    if not aws.user_is_authenticated(profile=config.aws.profile):
        typer.secho("Authentication required. Logging in with AWS SSO...", fg=typer.colors.YELLOW)
        try:
            subprocess.run(["aws", "sso", "login", "--profile", config.aws.profile], check=True)
            typer.secho(f"Successfully authenticated with profile '{config.aws.profile}'", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
            typer.secho("Authentication failed. Run 'clauth init' for full setup.", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Check if model settings are configured
    if not config.models.default_model_arn or not config.models.fast_model_arn:
        typer.secho("Model configuration missing. Run 'clauth init' for full setup.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Set up environment variables
    env = os.environ.copy()
    env.update({
        "AWS_PROFILE": config.aws.profile,
        "AWS_REGION": config.aws.region,
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "ANTHROPIC_MODEL": config.models.default_model_arn,
        "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": config.models.fast_model_arn,
    })

    # Launch Claude Code
    typer.secho("Launching Claude Code with Bedrock configuration...", fg=typer.colors.BLUE)
    try:
        claude_path = get_app_path(config.cli.claude_cli_name)
        clear_screen()
        subprocess.run([claude_path], env=env, check=True)
    except ExecutableNotFoundError as e:
        typer.secho(f"Launch failed: {e}", fg=typer.colors.RED)
        typer.secho("Please install Claude Code CLI and ensure it's in your PATH.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)
    except ValueError as e:
        typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to launch Claude Code. Exit code: {e.returncode}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def list_models(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    show_arn: bool = typer.Option(False, "--show-arn", help="Show model ARNs")
):
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    if profile is not None:
        config.aws.profile = profile
    if region is not None:
        config.aws.region = region

    if not aws.user_is_authenticated(profile=config.aws.profile):
        exit("Credentials are missing or expired. Run `clauth init` to authenticate with AWS.")

    model_ids, model_arns = aws.list_bedrock_profiles(
        profile=config.aws.profile,
        region=config.aws.region,
        provider=config.models.provider_filter
    )
    for model_id, model_arn in zip(model_ids,model_arns):
        if show_arn:
            print(model_id , ' --> ', model_arn)
        else:
            print(model_id)




def validate_model_id(id: str):
    config = get_config_manager().load()
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
    console.print(f"  SSO Start URL: {config.aws.sso_start_url}")
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


if __name__ == "__main__":
    app()
