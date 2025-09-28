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
    delete,
    config_app,
    init_command,
)
from clauth.launcher import launch_claude_cli
from rich.console import Console



class OrderedGroup(TyperGroup):
    def list_commands(self, ctx):
        return ["init", "model", "config", "delete"]

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
app.command()(delete)



if __name__ == "__main__":
    app()
