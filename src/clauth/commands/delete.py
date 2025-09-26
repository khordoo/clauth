import typer
from rich.console import Console
from clauth.config import get_config_manager
from clauth.aws_utils import (
    delete_aws_profile,
    delete_aws_credentials_profile,
    clear_sso_cache,
    remove_sso_session,
)

console = Console()


def delete(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """
    Deletes all CLAUTH configurations and associated AWS profile data.

    This command provides a complete cleanup by:
    - Deleting the entire CLAUTH configuration directory.
    - Removing the associated AWS profile from `~/.aws/config`.
    - Clearing the AWS SSO token cache.
    - Removing any related SSO session configurations.
    """
    # Load configuration to get profile name
    config_manager = get_config_manager()
    config = config_manager.load()
    profile = config.aws.profile

    # Show what will be deleted
    console.print("\n[bold red]WARNING: DELETE OPERATION[/bold red]")
    console.print("This will permanently delete the following:")
    console.print(f"  - AWS profile: [yellow]{profile}[/yellow]")
    console.print("  - AWS credentials profile (if it exists)")
    console.print("  - SSO token cache")
    console.print("  - SSO session configuration")
    console.print("  - [bold red]ENTIRE CLAUTH configuration directory[/bold red]")
    console.print()

    # Confirmation
    if not confirm:
        if not typer.confirm("Are you sure you want to proceed with the deletion?"):
            console.print("[yellow]Delete operation cancelled.[/yellow]")
            raise typer.Exit(0)

    success = True
    console.print("\n[bold blue]Starting delete operation...[/bold blue]")

    # Step 1: Delete AWS profile and credentials
    console.print(f"\n[bold]Step 1: Deleting AWS profile '{profile}'[/bold]")
    if not delete_aws_profile(profile):
        success = False
    if not delete_aws_credentials_profile(profile):
        success = False

    # Step 2: Clear SSO token cache
    console.print("\n[bold]Step 2: Clearing SSO token cache[/bold]")
    if not clear_sso_cache(profile):
        success = False

    # Step 3: Remove SSO session configuration
    console.print("\n[bold]Step 3: Removing SSO session configuration[/bold]")
    if not remove_sso_session("claude-auth"):
        success = False
    if not remove_sso_session(config.aws.session_name):
        success = False

    # Step 4: Delete CLAUTH configuration directory
    console.print(f"\n[bold]Step 4: Deleting CLAUTH configuration[/bold]")
    try:
        import shutil
        if config_manager.config_dir.exists():
            shutil.rmtree(config_manager.config_dir)
            console.print(
                f"[green]SUCCESS: Completely removed config directory: {config_manager.config_dir}[/green]"
            )
        else:
            console.print("[yellow]Config directory already doesn't exist.[/yellow]")
    except Exception as e:
        console.print(f"[red]ERROR: Failed to delete CLAUTH configuration: {e}[/red]")
        success = False

    # Final status
    console.print()
    if success:
        console.print("[bold green]SUCCESS: Deletion completed successfully![/bold green]")
    else:
        console.print("[bold red]WARNING: Deletion completed with some errors.[/bold red]")
        console.print("Check the messages above for details.")
        raise typer.Exit(1)
