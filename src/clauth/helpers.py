# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH Shared Utility Functions.

This module contains utility functions used across multiple CLI commands
and modules to avoid circular imports.
"""

import os
import shutil
import subprocess
import typer
from clauth.config import get_config_manager
from clauth.aws_utils import list_bedrock_profiles
from InquirerPy import inquirer
from rich.console import Console
from pyfiglet import Figlet
from textwrap import dedent
from InquirerPy import get_style

console = Console()


class ExecutableNotFoundError(Exception):
    """Raised when executable cannot be found in system PATH."""

    pass


def clear_screen():
    """Clear the terminal screen in a cross-platform manner."""
    os.system("cls" if os.name == "nt" else "clear")


def show_welcome_logo(console: Console) -> None:
    """
    Display the CLAUTH welcome logo.

    Args:
        console: Rich console instance for styled output
    """
    f = Figlet(font="slant")
    logo = f.renderText("CLAUTH")
    console.print(logo, style="bold cyan")

    console.print(
        dedent("""
        [bold]Welcome to CLAUTH[/bold]
        Let’s set up your environment for Claude Code on Amazon Bedrock.

        Prerequisites:
          • AWS CLI v2
          • Claude Code CLI

        Tip: run [bold]clauth init --help[/bold] to view options.
    """).strip()
    )


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
            {"name": "AWS SSO (for teams/organizations)", "value": "sso"},
            {"name": "IAM User Access Keys (for solo developers)", "value": "iam"},
            {"name": "Skip (I'm already configured)", "value": "skip"},
        ],
        pointer="▶ ",
        amark="✔",
        style=custom_style,
        max_height="100%",
    ).execute()


def get_app_path(exe_name: str = "claude") -> str:
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
        raise ValueError(f"Invalid executable name provided: {exe_name!r}")

    # First, try the basic lookup
    claude_path = shutil.which(exe_name)
    if claude_path is None:
        raise ExecutableNotFoundError(
            f"{exe_name} not found in system PATH. Please ensure it is installed and in your PATH."
        )

    # On Windows, prefer .cmd/.exe versions if they exist (matches original behavior)
    if os.name == "nt":
        preferred_extensions = [".cmd", ".exe"]
        for ext in preferred_extensions:
            if not exe_name.lower().endswith(ext):
                preferred_path = shutil.which(exe_name + ext)
                if preferred_path:
                    typer.echo(
                        f"Found multiple {exe_name} executables, using: {preferred_path}"
                    )
                    return preferred_path

    typer.echo(f"Using executable: {claude_path}")
    return claude_path


def is_sso_profile(profile: str) -> bool:
    """
    Check if a given AWS profile is configured for SSO.

    Args:
        profile: AWS profile name to check

    Returns:
        bool: True if profile has SSO configuration, False otherwise
    """
    try:
        result = subprocess.run(
            ["aws", "configure", "get", "sso_start_url", "--profile", profile],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip()
    except Exception:
        return False


def handle_authentication_failure(profile: str) -> bool:
    """
    Handle authentication failure with appropriate method based on profile type.

    For SSO profiles, attempts automatic re-authentication.
    For non-SSO profiles, directs user to run clauth init.

    Args:
        profile: AWS profile name that failed authentication

    Returns:
        bool: True if successfully authenticated, False otherwise
    """
    if is_sso_profile(profile):
        typer.secho(
            "SSO token expired. Attempting to re-authenticate...",
            fg=typer.colors.YELLOW,
        )
        try:
            subprocess.run(["aws", "sso", "login", "--profile", profile], check=True)
            typer.secho(
                f"Successfully re-authenticated with profile '{profile}'",
                fg=typer.colors.GREEN,
            )
            return True
        except subprocess.CalledProcessError:
            typer.secho(
                "SSO login failed. Run 'clauth init' for full setup.",
                fg=typer.colors.RED,
            )
            return False
    else:
        # Non-SSO profile - direct to init
        typer.secho(
            "Authentication required. Please run 'clauth init' to set up authentication.",
            fg=typer.colors.RED,
        )
        return False


def prompt_for_region_if_needed(config, cli_overrides):
    """Prompt user for AWS region if not provided."""
    if not cli_overrides.get("region"):
        console.print("\n[bold]AWS Region Selection[/bold]")
        console.print("Please select your preferred AWS region.")
        console.print("This will be used for default AWS services.\n")

        custom_region_option = "Other (enter custom region)"
        region_options = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
            "ap-southeast-2",
            "ap-northeast-1",
            "ca-central-1",
            custom_region_option,
        ]

        selected_option = inquirer.select(
            message="Select your AWS region:",
            instruction="↑↓ move • Enter select",
            choices=region_options,
            default=config.aws.region
            if config.aws.region in region_options
            else "us-east-1",
            pointer="▶ ",
            amark="✔",
        ).execute()

        if selected_option == custom_region_option:
            custom_region = typer.prompt("AWS Region")
            if not custom_region or not custom_region.replace("-", "").isalnum():
                typer.secho("Error: Invalid region format.", fg=typer.colors.RED)
                return False
            selected_region = custom_region
        else:
            selected_region = selected_option

        config.aws.region = selected_region
        get_config_manager()._config = config
        get_config_manager().save()
        console.print(f"[green]✓ Region set to: {selected_region}[/green]\n")
    return True


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
        model_ids, model_arns = list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter,
        )
    if id not in model_ids:
        raise typer.BadParameter(
            f"{id} is not valid or supported model. Valid Models: {model_ids}"
        )
    return id
