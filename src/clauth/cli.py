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
from clauth.commands import (
    claude,
    list_models,
    switch_models,
    sm,
    delete,
    config_app,
    init,
)
from clauth.helpers import (
    ExecutableNotFoundError,
    clear_screen,
    get_app_path,
    prompt_for_region_if_needed,
    show_welcome_logo,
    choose_auth_method,
)

from clauth.aws_utils import (
    setup_sso_auth,
    setup_iam_user_auth,
)
from InquirerPy import inquirer
from rich.console import Console
from InquirerPy import get_style


app = typer.Typer()
env = os.environ.copy()
console = Console()


# Register commands from modules
app.command()(init)
app.command()(claude)
app.command()(list_models)
app.command(name="switch-models", help="Interactive model switcher (alias: sm)")(switch_models)
app.command(name="sm", hidden=True)(sm)
app.add_typer(config_app, name="config")
app.command()(delete)



if __name__ == "__main__":
    app()
