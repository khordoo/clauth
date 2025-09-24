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


class ExecutableNotFoundError(Exception):
    """Raised when executable cannot be found in system PATH."""
    pass


def clear_screen():
    """Clear the terminal screen in a cross-platform manner."""
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
            capture_output=True, text=True, check=False
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
        typer.secho("SSO token expired. Attempting to re-authenticate...", fg=typer.colors.YELLOW)
        try:
            subprocess.run(["aws", "sso", "login", "--profile", profile], check=True)
            typer.secho(f"Successfully re-authenticated with profile '{profile}'", fg=typer.colors.GREEN)
            return True
        except subprocess.CalledProcessError:
            typer.secho("SSO login failed. Run 'clauth init' for full setup.", fg=typer.colors.RED)
            return False
    else:
        # Non-SSO profile - direct to init
        typer.secho("Authentication required. Please run 'clauth init' to set up authentication.", fg=typer.colors.RED)
        return False
