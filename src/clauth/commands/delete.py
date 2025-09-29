import typer
from clauth.config import get_config_manager
from clauth.aws_utils import (
    delete_aws_profile,
    delete_aws_credentials_profile,
    clear_sso_cache,
    remove_sso_session,
)
from clauth.ui import render_card, render_status, Spinner, style


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
    summary_lines: list[str] = []
    render_status("Starting delete operation", level="info")

    # Step 1: Delete AWS profile and credentials
    with Spinner("Removing AWS profile"):
        removed_profile = delete_aws_profile(profile)
    if removed_profile:
        render_status(f"Removed AWS profile '{profile}'", level="success")
        summary_lines.append(f"AWS profile '{profile}' → removed")
    else:
        render_status(
            f"Failed to remove AWS profile '{profile}'",
            level="error",
        )
        success = False
        summary_lines.append(f"AWS profile '{profile}' → failed")

    with Spinner("Removing AWS credentials profile"):
        removed_credentials = delete_aws_credentials_profile(profile)
    if removed_credentials:
        render_status("Removed AWS credentials profile", level="success")
        summary_lines.append("AWS credentials profile → removed")
    else:
        render_status(
            "Failed to remove AWS credentials profile",
            level="error",
        )
        success = False
        summary_lines.append("AWS credentials profile → failed")

    # Step 2: Clear SSO token cache
    with Spinner("Clearing SSO token cache"):
        cache_cleared = clear_sso_cache(profile)
    if cache_cleared:
        render_status("Cleared SSO token cache", level="success")
        summary_lines.append("SSO token cache → cleared")
    else:
        render_status("Failed to clear SSO token cache", level="error")
        success = False
        summary_lines.append("SSO token cache → failed")

    # Step 3: Remove SSO session configuration
    with Spinner("Removing CLAUTH SSO sessions"):
        default_session_removed = remove_sso_session("claude-auth")
        profile_session_removed = remove_sso_session(config.aws.session_name)
    if default_session_removed:
        render_status("Removed default CLAUTH SSO session", level="success")
        summary_lines.append("Default CLAUTH SSO session → removed")
    else:
        render_status(
            "Failed to remove default CLAUTH SSO session",
            level="warning",
        )
        success = False
        summary_lines.append("Default CLAUTH SSO session → failed")

    if profile_session_removed:
        render_status(
            f"Removed SSO session '{config.aws.session_name}'",
            level="success",
        )
        summary_lines.append(
            f"SSO session '{config.aws.session_name}' → removed"
        )
    else:
        render_status(
            f"Failed to remove SSO session '{config.aws.session_name}'",
            level="warning",
        )
        success = False
        summary_lines.append(
            f"SSO session '{config.aws.session_name}' → failed"
        )

    # Step 4: Delete CLAUTH configuration directory
    try:
        import shutil
        with Spinner("Deleting CLAUTH configuration directory"):
            if config_manager.config_dir.exists():
                shutil.rmtree(config_manager.config_dir)
                render_status(
                    "Removed CLAUTH configuration directory",
                    level="success",
                    footer=str(config_manager.config_dir),
                )
                summary_lines.append("Configuration directory → removed")
            else:
                render_status(
                    "Config directory already removed.",
                    level="info",
                )
                summary_lines.append("Configuration directory → already removed")
    except Exception as e:
        render_status(
            f"Failed to delete CLAUTH configuration: {e}",
            level="error",
        )
        success = False
        summary_lines.append("Configuration directory → failed")

    # Final status
    render_card(
        title="Delete summary",
        body="\n".join(summary_lines),
    )

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
