"""
CLAUTH Reset Commands.

This module provides comprehensive reset functionality for testing authentication flows.
"""

import typer
import subprocess
import shutil
from pathlib import Path
from rich.console import Console
from clauth.config import get_config_manager, ClauthConfig

console = Console()


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
        # Get AWS config file path
        home = Path.home()
        aws_config_file = home / ".aws" / "config"

        if not aws_config_file.exists():
            console.print("[yellow]No AWS config file found.[/yellow]")
            return True

        # Read the AWS config file
        import configparser
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
