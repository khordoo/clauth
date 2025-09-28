# Copyright (c) 2025 Mahmood Khordoo
#
# This software is licensed under the MIT License.
# See the LICENSE file in the root directory for details.

"""
Configuration management for CLAUTH.

This module handles persistent configuration storage and management for CLAUTH.
It provides a configuration system using TOML files with support for multiple
profiles, environment variable overrides, and platform-appropriate storage locations.

Classes:
    AwsConfig: AWS-related configuration settings
    ModelConfig: Model selection and provider configuration
    CliConfig: CLI behavior and appearance settings
    ClauthConfig: Main configuration container
    ConfigManager: Configuration file management and operations
"""

import os
import toml
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from clauth.ui import inquirer_style, prompt_toolkit_color


class AWSConfig(BaseModel):
    """AWS-related configuration settings."""

    profile: str = Field(default="clauth", description="AWS profile name")
    region: str = Field(default="ap-southeast-2", description="Default AWS region")
    sso_start_url: Optional[str] = Field(
        default=None,
        description="IAM Identity Center (SSO) start URL (e.g., https://d-xxxxxxxxxx.awsapps.com/start/)",
    )
    sso_region: str = Field(default="ap-southeast-2", description="SSO region")
    session_name: str = Field(default="clauth-session", description="SSO session name")
    output_format: str = Field(default="json", description="AWS CLI output format")

    @field_validator("sso_start_url")
    @classmethod
    def validate_sso_url(cls, v: str) -> Optional[str]:
        if v is not None and not v.startswith("https://"):
            raise ValueError("SSO start URL must be HTTPS")
        return v


class ModelConfig(BaseModel):
    """Model-related configuration settings."""

    provider_filter: str = Field(
        default="anthropic", description="Preferred model provider"
    )
    default_model: Optional[str] = Field(None, description="Default model ID")
    fast_model: Optional[str] = Field(None, description="Fast/small model ID")
    default_model_arn: Optional[str] = Field(None, description="Default model ARN")
    fast_model_arn: Optional[str] = Field(None, description="Fast model ARN")


class CLIConfig(BaseModel):
    """CLI behavior and appearance settings."""

    claude_cli_name: str = Field(
        default="claude", description="Claude CLI executable name"
    )
    auto_start: bool = Field(
        default=True, description="Auto-launch Claude Code after setup"
    )
    show_progress: bool = Field(default=True, description="Show progress indicators")
    color_output: bool = Field(default=True, description="Enable colored output")

    # UI styling
    pointer_style: str = Field(default="❯", description="Menu pointer character")
    selected_color: str = Field(default="ansiblue", description="Selected item color")
    highlighted_color: str = Field(
        default="ansiblue", description="Highlighted item color"
    )


class ClauthConfig(BaseModel):
    """Main CLAUTH configuration container."""

    aws: AWSConfig = Field(default_factory=AWSConfig)
    models: ModelConfig = Field(default_factory=ModelConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)

    model_config = ConfigDict(extra="forbid")


class ConfigManager:
    """Manages CLAUTH configuration loading, saving, and validation."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize ConfigManager with optional custom config directory."""
        self.config_dir = config_dir or self._get_default_config_dir()
        self.config_file = self.config_dir / "config.toml"
        self.profiles_dir = self.config_dir / "profiles"
        self._config: Optional[ClauthConfig] = None

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_config_dir(self) -> Path:
        """Get the default configuration directory."""
        if os.name == "nt":  # Windows
            config_home = Path(
                os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            )
        else:  # Unix-like
            config_home = Path(
                os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
            )

        return config_home / "clauth"

    def load(self, profile: Optional[str] = None) -> ClauthConfig:
        """Load configuration from file with optional profile support."""
        config_file = self._get_config_file(profile)

        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = toml.load(f)
                self._config = ClauthConfig(**config_data)
            except (toml.TomlDecodeError, ValueError) as e:
                # If config is invalid, create default and save it
                print(f"Warning: Invalid config file, creating default: {e}")
                self._config = ClauthConfig()
                self.save()
        else:
            # Create default configuration
            self._config = ClauthConfig()
            self.save()

        # Migrate legacy placeholder URLs
        self._migrate_placeholder_urls()

        # Apply environment variable overrides
        self._apply_env_overrides()

        return self._config

    def save(self, profile: Optional[str] = None) -> None:
        """Save current configuration to file."""
        if self._config is None:
            raise ValueError("No configuration loaded to save")

        config_file = self._get_config_file(profile)
        config_data = self._config.model_dump()

        with open(config_file, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)

    def _get_config_file(self, profile: Optional[str] = None) -> Path:
        """Get the config file path for a specific profile."""
        if profile:
            return self.profiles_dir / f"{profile}.toml"
        return self.config_file

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        if self._config is None:
            return

        # AWS configuration overrides
        if env_profile := os.environ.get("CLAUTH_PROFILE"):
            self._config.aws.profile = env_profile
        if env_region := os.environ.get("CLAUTH_REGION"):
            self._config.aws.region = env_region
        if env_sso_url := os.environ.get("CLAUTH_SSO_START_URL"):
            self._config.aws.sso_start_url = env_sso_url
        if env_sso_region := os.environ.get("CLAUTH_SSO_REGION"):
            self._config.aws.sso_region = env_sso_region
        if env_session_name := os.environ.get("CLAUTH_SESSION_NAME"):
            self._config.aws.session_name = env_session_name

        # CLI configuration overrides
        if env_claude_cli := os.environ.get("CLAUTH_CLAUDE_CLI_NAME"):
            self._config.cli.claude_cli_name = env_claude_cli
        if env_auto_start := os.environ.get("CLAUTH_AUTO_START"):
            self._config.cli.auto_start = env_auto_start.lower() in ("true", "1", "yes")

        # Model configuration overrides
        if env_provider := os.environ.get("CLAUTH_PROVIDER_FILTER"):
            self._config.models.provider_filter = env_provider
        if env_default_model := os.environ.get("CLAUTH_DEFAULT_MODEL"):
            self._config.models.default_model = env_default_model
        if env_fast_model := os.environ.get("CLAUTH_FAST_MODEL"):
            self._config.models.fast_model = env_fast_model

    def _migrate_placeholder_urls(self) -> None:
        """Migrate legacy placeholder SSO URLs to None."""
        if self._config is None:
            return

        # Check if sso_start_url contains the old placeholder
        if (
            self._config.aws.sso_start_url
            and self._config.aws.sso_start_url
            == "https://d-xxxxxxxxxx.awsapps.com/start/"
        ):
            print(
                "Warning: Migrating placeholder SSO start URL to None. You'll need to provide a real URL during init."
            )
            self._config.aws.sso_start_url = None
            # Save the migrated config
            self.save()

    @property
    def config(self) -> ClauthConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config

    def update_model_settings(
        self, default_model: str, fast_model: str, default_arn: str, fast_arn: str
    ) -> None:
        """Update model settings and save configuration."""
        if self._config is None:
            self.load()

        self._config.models.default_model = default_model
        self._config.models.fast_model = fast_model
        self._config.models.default_model_arn = default_arn
        self._config.models.fast_model_arn = fast_arn
        self.save()

    def get_custom_style(self) -> Dict[str, str]:
        """Get InquirerPy custom style based on configuration."""
        cli_config = self.config.cli
        custom = inquirer_style()

        # Allow user overrides from configuration while keeping theme defaults.
        if cli_config.selected_color:
            custom.update(
                {
                    "pointer": prompt_toolkit_color(cli_config.selected_color),
                    "selected": prompt_toolkit_color(
                        cli_config.selected_color, bold=True
                    ),
                }
            )
        if cli_config.highlighted_color:
            custom["highlighted"] = prompt_toolkit_color(
                cli_config.highlighted_color, bold=True
            )
            custom["border"] = prompt_toolkit_color(cli_config.highlighted_color)

        return custom

    def list_profiles(self) -> list[str]:
        """List available configuration profiles."""
        if not self.profiles_dir.exists():
            return []

        profiles = []
        for file in self.profiles_dir.glob("*.toml"):
            profiles.append(file.stem)
        return sorted(profiles)

    def profile_exists(self, profile: str) -> bool:
        """Check if a configuration profile exists."""
        return (self.profiles_dir / f"{profile}.toml").exists()

    def delete_profile(self, profile: str) -> bool:
        """Delete a configuration profile."""
        profile_file = self.profiles_dir / f"{profile}.toml"
        if profile_file.exists():
            profile_file.unlink()
            return True
        return False


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(profile: Optional[str] = None) -> ClauthConfig:
    """Convenience function to get configuration."""
    return get_config_manager().load(profile)
