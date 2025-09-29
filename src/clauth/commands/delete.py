import typer
from clauth.config import get_config_manager
from clauth.aws_utils import (
    delete_aws_profile,
    delete_aws_credentials_profile,
    clear_sso_cache,
    remove_sso_session,
)
from clauth.ui import render_card, render_status, console, style


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

    render_card(
        title="Delete CLAUTH data",
        body="\n".join(
            [
                f"AWS profile: {profile}",
                "AWS credentials profile (if present)",
                "SSO token cache",
                "SSO session configuration",
                "Entire CLAUTH configuration directory",
            ]
        ),
        footer="This operation cannot be undone.",
        border_style=style("danger"),
    )

    # Confirmation
    if not confirm:
        if not typer.confirm("Are you sure you want to proceed with the deletion?"):
            render_status("Delete operation cancelled.", level="warning")
            raise typer.Exit(0)

    success = True
    render_status("Starting delete operation", level="info")

    # Step 1: Delete AWS profile and credentials
    if delete_aws_profile(profile):
        render_status(f"Removed AWS profile '{profile}'", level="success")
    else:
        render_status(
            f"Failed to remove AWS profile '{profile}'",
            level="error",
        )
        success = False

    if delete_aws_credentials_profile(profile):
        render_status("Removed AWS credentials profile", level="success")
    else:
        render_status(
            "Failed to remove AWS credentials profile",
            level="error",
        )
        success = False

    # Step 2: Clear SSO token cache
    if clear_sso_cache(profile):
        render_status("Cleared SSO token cache", level="success")
    else:
        render_status("Failed to clear SSO token cache", level="error")
        success = False

    # Step 3: Remove SSO session configuration
    if remove_sso_session("claude-auth"):
        render_status("Removed default CLAUTH SSO session", level="success")
    else:
        render_status(
            "Failed to remove default CLAUTH SSO session",
            level="warning",
        )
        success = False

    if remove_sso_session(config.aws.session_name):
        render_status(
            f"Removed SSO session '{config.aws.session_name}'",
            level="success",
        )
    else:
        render_status(
            f"Failed to remove SSO session '{config.aws.session_name}'",
            level="warning",
        )
        success = False

    # Step 4: Delete CLAUTH configuration directory
    try:
        import shutil
        if config_manager.config_dir.exists():
            shutil.rmtree(config_manager.config_dir)
            render_status(
                "Removed CLAUTH configuration directory",
                level="success",
                footer=str(config_manager.config_dir),
            )
        else:
            render_status(
                "Config directory already removed.",
                level="info",
            )
    except Exception as e:
        render_status(
            f"Failed to delete CLAUTH configuration: {e}",
            level="error",
        )
        success = False

    # Final status
    if success:
        render_status(
            "Deletion completed successfully.",
            level="success",
        )
    else:
        render_status(
            "Deletion completed with some errors.",
            level="error",
            footer="Review the messages above for details.",
        )
        raise typer.Exit(1)
