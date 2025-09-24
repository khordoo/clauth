"""
CLAUTH Claude Code Launch Command.

This module provides the command to launch Claude Code CLI with proper
AWS Bedrock environment configuration.
"""

import os
import subprocess
import typer
from clauth.config import get_config_manager
from clauth.aws_utils import user_is_authenticated
from clauth.helpers import handle_authentication_failure, get_app_path, clear_screen, ExecutableNotFoundError


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
    if not user_is_authenticated(profile=config.aws.profile):
        if not handle_authentication_failure(config.aws.profile):
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
    except Exception as e:
        if "ExecutableNotFoundError" in str(type(e)):
            typer.secho(f"Launch failed: {e}", fg=typer.colors.RED)
            typer.secho("Please install Claude Code CLI and ensure it's in your PATH.", fg=typer.colors.YELLOW)
        else:
            typer.secho(f"Configuration error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        typer.secho(f"Failed to launch Claude Code. Exit code: {e.returncode}", fg=typer.colors.RED)
        raise typer.Exit(1)
