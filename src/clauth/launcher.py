# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
CLAUTH Application Launcher.

This module contains the core logic for launching the Claude Code CLI
with the correct environment configuration.
"""

import os
import subprocess
import typer
from clauth.config import get_config_manager
from clauth.aws_utils import user_is_authenticated
from clauth.helpers import handle_authentication_failure, get_app_path, clear_screen, ExecutableNotFoundError
from clauth.ui import render_status


def launch_claude_cli():
    """Launch Claude Code with proper environment variables from saved configuration."""
    # Load configuration
    config_manager = get_config_manager()
    config = config_manager.load()

    # Check if user is authenticated
    if not user_is_authenticated(profile=config.aws.profile):
        if not handle_authentication_failure(config.aws.profile):
            raise typer.Exit(1)

    # Check if model settings are configured
    if not config.models.default_model_arn or not config.models.fast_model_arn:
        render_status("Model configuration missing. Run `clauth init` for full setup.", level="error")
        raise typer.Exit(1)

    # Set up environment variables
    env = os.environ.copy()
    env.update({
        "AWS_PROFILE": config.aws.profile,
        "AWS_REGION": config.aws.region,
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "ANTHROPIC_MODEL": config.models.default_model_arn,
        "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": config.models.fast_model_arn,
    })

    # Launch Claude Code
    render_status("Launching Claude Code with Bedrock configuration...", level="info")
    try:
        claude_path = get_app_path(config.cli.claude_cli_name)
        clear_screen()
        subprocess.run([claude_path], env=env, check=True)
    except Exception as e:
        if "ExecutableNotFoundError" in str(type(e)):
            render_status(f"Launch failed: {e}", level="error")
            render_status("Please install Claude Code CLI and ensure it's in your PATH.", level="warning")
        else:
            render_status(f"Configuration error: {e}", level="error")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        render_status(f"Failed to launch Claude Code. Exit code: {e.returncode}", level="error")
        raise typer.Exit(1)
