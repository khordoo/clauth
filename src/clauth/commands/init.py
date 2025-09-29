# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

import subprocess
import os
import typer
import clauth.aws_utils as aws
from clauth.config import get_config_manager
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
from rich.console import Console
from InquirerPy import inquirer
from InquirerPy import get_style
from clauth.ui import render_card, render_status, Spinner, WizardScreen

app = typer.Typer()
console = Console()
env = os.environ.copy()


def _handle_authentication(config, cli_overrides):
    """Handles the logic for AWS authentication."""
    auth_method = choose_auth_method()

    if not prompt_for_region_if_needed(config, cli_overrides):
        raise typer.Exit(1)

    if auth_method == "skip":
        if not aws.user_is_authenticated(profile=config.aws.profile):
            render_status(
                "No valid authentication found. Please choose an authentication method.",
                level="error",
            )
            raise typer.Exit(1)
        summary = {
            "message": f"Authentication: existing AWS profile '{config.aws.profile}' · Region: {config.aws.region}",
            "level": "success",
        }
    elif auth_method == "iam":
        render_card(
            title="AWS credentials",
            body="Enter your AWS Access Key and Secret Key for CLAUTH.",
            footer="Get from: AWS Console → IAM → Users → your user → Security credentials",
        )
        if not setup_iam_user_auth(config.aws.profile, config.aws.region):
            raise typer.Exit(1)
        summary = {
            "message": f"Authentication: IAM access keys for '{config.aws.profile}' · Region: {config.aws.region}",
            "level": "success",
        }
    elif auth_method == "sso":
        render_card(
            title="Step 2 of 3 · AWS SSO configuration",
            body="CLAUTH will use AWS CLI to open the SSO wizard. Follow the prompts to complete authentication.",
            footer="[Delete configuration: clauth delete -y]\nTip: SSO Start URL usually looks like: https://d-xxxxxx.awsapps.com/start/",
        )

        if not setup_sso_auth(config, cli_overrides):
            raise typer.Exit(1)
        summary = {
            "message": (
                f"Authentication: SSO session '{config.aws.session_name}' "
                f"· Profile: {config.aws.profile} · Region: {config.aws.region}"
            ),
            "level": "success",
        }
    else:  # pragma: no cover - defensive guard
        summary = {
            "message": "Authentication method completed",
            "level": "success",
        }

    return summary


def _launch_claude_cli(config, env):
    """Launches the Claude Code CLI with the given environment."""
    try:
        claude_path = get_app_path(config.cli.claude_cli_name)
        clear_screen()
        subprocess.run([claude_path], env=env, check=True)
    except ExecutableNotFoundError as e:
        render_status(f"Setup failed: {e}", level="error")
        render_status(
            "Please install Claude Code CLI and ensure it's in your PATH.",
            level="warning",
        )
        raise typer.Exit(1)
    except ValueError as e:
        render_status(f"Configuration error: {e}", level="error")
        raise typer.Exit(1)


def _handle_model_selection(config, config_manager, console):
    """Handles the logic for selecting Bedrock models."""
    # Check if we have existing model configuration
    if config.models.default_model_arn and config.models.fast_model_arn:
        render_card(
            title="Existing model configuration",
            body="\n".join(
                [
                    f"Default: {config.models.default_model}",
                    f"Fast: {config.models.fast_model}",
                ]
            ),
            footer="Select `No` below to choose different models.",
        )

        # Get custom style from config manager
        custom_style = get_style(config_manager.get_custom_style())

        use_existing = inquirer.confirm(
            message="Use existing model configuration?",
            default=True,
            style=custom_style,
        ).execute()

        if use_existing:
            model_id_default = config.models.default_model
            model_id_fast = config.models.fast_model
            model_map = {
                model_id_default: config.models.default_model_arn,
                model_id_fast: config.models.fast_model_arn,
            }
            render_status(
                "Models unchanged",
                level="success",
                footer=f"Default: {model_id_default} · Fast: {model_id_fast}",
            )
            return model_id_default, model_id_fast, model_map

    # No existing configuration or user chose not to use it, do full model discovery
    with Spinner("Discovering available models"):
        model_ids, model_arns = aws.list_bedrock_profiles(
            profile=config.aws.profile,
            region=config.aws.region,
            provider=config.models.provider_filter,
        )

    # Get custom style from config manager
    custom_style = get_style(config_manager.get_custom_style())

    model_id_default = inquirer.select(
        message="Select your [default] model:",
        pointer="▶ ",
        amark="✔",
        choices=model_ids,
        default=config.models.default_model
        if config.models.default_model in model_ids
        else (model_ids[0] if model_ids else None),
        style=custom_style,
        max_height="100%",
        instruction=None,
    ).execute()

    model_id_fast = inquirer.select(
        message="Select your [small/fast] model (you can choose the same as default):",
        pointer="▶ ",
        amark="✔",
        choices=model_ids,
        default=config.models.fast_model
        if config.models.fast_model in model_ids
        else (model_ids[-1] if model_ids else None),
        style=custom_style,
        max_height="100%",
        instruction=None,
    ).execute()

    model_map = {id: arn for id, arn in zip(model_ids, model_arns)}

    # Save updated model selections to configuration
    config_manager.update_model_settings(
        default_model=model_id_default,
        fast_model=model_id_fast,
        default_arn=model_map[model_id_default],
        fast_arn=model_map[model_id_fast],
    )
    return model_id_default, model_id_fast, model_map


def init_command(
    profile: str = typer.Option(
        None,
        "--profile",
        "-p",
        help="AWS profile to create or update (saved under [profile <name>] in ~/.aws/config).",
        rich_help_panel="AWS Profile",
    ),
    session_name: str = typer.Option(
        None,
        "--session-name",
        "-s",
        help="Name of the SSO session to create (saved under [sso-session <name>] in ~/.aws/config).",
        rich_help_panel="AWS SSO",
    ),
    sso_start_url: str = typer.Option(
        None,
        "--sso-start-url",
        help="IAM Identity Center (SSO) Start URL (e.g., https://d-…awsapps.com/start/).",
        rich_help_panel="AWS SSO",
    ),
    sso_region: str = typer.Option(
        None,
        "--sso-region",
        help="Region that hosts your IAM Identity Center (SSO) instance.",
        rich_help_panel="AWS SSO",
    ),
    region: str = typer.Option(
        None,
        "--region",
        "-r",
        help="Default AWS client region for this profile (used for STS/Bedrock calls).",
        rich_help_panel="AWS Profile",
    ),
    auto_start: bool = typer.Option(
        None,
        "--auto-start/--no-auto-start",
        help="Launch the Claude CLI immediately after successful setup.",
        rich_help_panel="Behavior",
    ),
):
    """
    Interactive setup wizard for CLAUTH.

    Configures AWS authentication (SSO or IAM user), discovers available Bedrock models,
    and optionally launches Claude Code CLI with proper environment variables.
    This is the main entry point for first-time CLAUTH setup.

    Args:
        profile: AWS profile name to create/update (default from config)
        session_name: SSO session name (default from config, SSO only)
        sso_start_url: IAM Identity Center start URL (default from config, SSO only)
        sso_region: SSO region (default from config, SSO only)
        region: Default AWS region for profile (default from config)
        auto_start: Whether to launch Claude Code after setup (default from config)
    """
    # Load configuration and apply CLI overrides
    config_manager = get_config_manager()
    config = config_manager.load()

    # Track which CLI parameters were provided
    cli_overrides = {
        "profile": profile is not None,
        "session_name": session_name is not None,
        "sso_start_url": sso_start_url is not None,
        "sso_region": sso_region is not None,
        "region": region is not None,
        "auto_start": auto_start is not None,
    }

    # Override config with CLI parameters if provided
    if profile is not None:
        config.aws.profile = profile
    if session_name is not None:
        config.aws.session_name = session_name
    if sso_start_url is not None:
        config.aws.sso_start_url = sso_start_url
    if sso_region is not None:
        config.aws.sso_region = sso_region
    if region is not None:
        config.aws.region = region
    if auto_start is not None:
        config.cli.auto_start = auto_start

    wizard = WizardScreen(banner=lambda: show_welcome_logo(console=console))

    try:
        with wizard.step(
            "Step 1 of 3 · Configure AWS authentication",
            card={
                "title": "Authentication",
                "body": "Choose how CLAUTH should authenticate with AWS Bedrock.",
                "footer": "Recommended: IAM Identity Center (SSO) for team accounts. Controls: ↑/↓ move · Enter select",
            },
        ):
            auth_summary = _handle_authentication(config, cli_overrides)
        wizard.add_summary_entry(auth_summary)

        with wizard.step(
            "Step 2 of 3 · Select Bedrock models",
            card={
                "title": "Model selection",
                "body": "Pick your default and fast Bedrock models. You can reuse existing choices.",
                "footer": "Controls: ↑/↓ move · Enter select",
            },
        ):
            model_id_default, model_id_fast, model_map = _handle_model_selection(
                config, config_manager, console
            )

        wizard.add_summary(
            "Models configured",
            level="success",
            footer=f"Default: {model_id_default} · Fast: {model_id_fast}",
        )

        env.update(
            {
                "AWS_PROFILE": config.aws.profile,
                "AWS_REGION": config.aws.region,
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "ANTHROPIC_MODEL": model_map[model_id_default],
                "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION": model_map[model_id_fast],
            }
        )

        wizard.render(active_message="Step 3 of 3 · Finalize setup")

        if config.cli.auto_start:
            wizard.add_summary(
                "Auto-start enabled",
                level="success",
                footer="Launching Claude Code with your configuration",
            )
            _launch_claude_cli(config, env)
        else:
            wizard.add_summary(
                "Setup complete",
                level="success",
                footer=f"Run `{config.cli.claude_cli_name}` when you're ready.",
            )

    except subprocess.CalledProcessError as e:
        render_status(f"Setup failed. Exit code: {e.returncode}", level="error")
        raise typer.Exit(1)
