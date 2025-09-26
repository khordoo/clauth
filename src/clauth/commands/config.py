import typer
from rich.console import Console
from clauth.config import get_config_manager, ClauthConfig

config_app = typer.Typer(
    help="Display configuration settings.",
    no_args_is_help=True,
)
console = Console()


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

    console.print("\n[bold cyan]CLAUTH Configuration[/bold cyan]")

    if show_path:
        config_file = config_manager.config_file
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

    console.print("\n[dim]To remove this configuration and start over, run: [bold]clauth delete[/bold][/dim]")
