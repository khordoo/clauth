# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH Command Line Interface.

This module provides the main CLI interface for CLAUTH, a tool that streamlines
AWS Bedrock setup for Claude Code. It handles AWS SSO authentication, model
discovery, environment configuration, and Claude Code CLI launching.

Main Commands:
    init: Interactive setup wizard for AWS SSO and model selection
    list-models: Display available Bedrock inference profiles
    claude: Launch Claude Code CLI with proper environment
    config: Configuration management (show, set, reset, profiles)
"""

import typer
import os
from typer.core import TyperGroup
from clauth.commands import (
    model_app,
    config_app,
    init_command,
)
from clauth.launcher import launch_claude_cli
from rich.console import Console
from clauth.ui import render_status
from clauth.commands.config import config_delete
from clauth.commands.models import switch_models



class OrderedGroup(TyperGroup):
    def list_commands(self, ctx):
        return ["init", "model", "sm", "config"]

app = typer.Typer(cls=OrderedGroup, no_args_is_help=False, invoke_without_command=True)
env = os.environ.copy()
console = Console()


@app.callback()
def main(ctx: typer.Context):
    """
    CLAUTH: A streamlined launcher for the Claude Code CLI with AWS Bedrock.
    """
    if ctx.invoked_subcommand is None:
        launch_claude_cli()

# Register commands from modules
app.command(name="init")(init_command)
app.add_typer(model_app, name="model")
app.add_typer(config_app, name="config")


@app.command(name="sm", help="Shortcut for `model switch`.")
def switch_models_shortcut(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    region: str = typer.Option(None, "--region", "-r", help="AWS region to use"),
    default_only: bool = typer.Option(
        False, "--default-only", help="Only change default model"
    ),
    fast_only: bool = typer.Option(False, "--fast-only", help="Only change fast model"),
):
    """Invoke `clauth model switch` with a shorter command."""
    switch_models(
        profile=profile,
        region=region,
        default_only=default_only,
        fast_only=fast_only,
    )


@app.command(name="delete", hidden=True)
def delete_deprecated(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Deprecated: use `clauth config delete`."""
    render_status(
        "`clauth delete` is deprecated. Use `clauth config delete` instead.",
        level="warning",
    )
    config_delete(confirm=confirm)



if __name__ == "__main__":
    app()
