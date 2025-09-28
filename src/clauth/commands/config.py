import typer
from clauth.config import get_config_manager
from clauth.ui import render_card, render_status

config_app = typer.Typer(
    help="Display configuration settings.",
    no_args_is_help=True,
)
@config_app.command("show")
def config_show(
    show_path: bool = typer.Option(
        False, "--path", help="Show configuration file location"
    ),
):
    """
    Display current CLAUTH configuration.

    Shows all configuration settings including AWS, model, and CLI preferences.
    """
    config_manager = get_config_manager()
    config = config_manager.load()

    if show_path:
        render_card(
            title="Configuration file",
            body=str(config_manager.config_file),
        )

    render_card(
        title="AWS settings",
        body="\n".join(
            [
                f"Profile: {config.aws.profile}",
                f"Region: {config.aws.region}",
                f"SSO start URL: {config.aws.sso_start_url or 'Not configured'}",
                f"SSO region: {config.aws.sso_region}",
                f"Session name: {config.aws.session_name}",
                f"Output format: {config.aws.output_format}",
            ]
        ),
    )

    render_card(
        title="Model settings",
        body="\n".join(
            [
                f"Provider filter: {config.models.provider_filter}",
                f"Default model: {config.models.default_model or 'Not set'}",
                f"Fast model: {config.models.fast_model or 'Not set'}",
            ]
        ),
    )

    render_card(
        title="CLI settings",
        body="\n".join(
            [
                f"Claude CLI name: {config.cli.claude_cli_name}",
                f"Auto start: {config.cli.auto_start}",
                f"Show progress: {config.cli.show_progress}",
                f"Color output: {config.cli.color_output}",
            ]
        ),
    )

    render_status(
        "To remove this configuration and start over, run `clauth delete`.",
        level="info",
    )
