"""Unit tests for config.py."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from clauth.config import ConfigManager, ClauthConfig, get_config_manager


def test_config_manager_init():
    """Test ConfigManager initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        assert manager.config_dir == config_dir
        assert manager.config_file == config_dir / "config.toml"
        assert manager.profiles_dir == config_dir / "profiles"


def test_config_manager_default_config_dir():
    """Test ConfigManager with default config directory."""
    with patch.dict(os.environ, {"XDG_CONFIG_HOME": "/tmp/test_config"}):
        manager = ConfigManager()
        assert manager.config_dir == Path("/tmp/test_config/clauth")


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
def test_config_manager_windows_config_dir():
    """Test ConfigManager on Windows."""
    with patch("clauth.config.os.name", "nt"), \
         patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
        manager = ConfigManager()
        assert manager.config_dir == Path("C:\\Users\\Test\\AppData\\Roaming\\clauth")


def test_config_manager_load_creates_default():
    """Test that load() creates default config if none exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        config = manager.load()

        assert isinstance(config, ClauthConfig)
        assert config.aws.profile == "clauth"
        assert config.aws.region == "ap-southeast-2"
        assert config.models.provider_filter == "anthropic"


def test_config_manager_save_and_load():
    """Test saving and loading configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        # Create a config with custom values
        config = ClauthConfig()
        config.aws.profile = "test-profile"
        config.models.provider_filter = "test-provider"

        manager._config = config
        manager.save()

        # Load in a new manager
        new_manager = ConfigManager(config_dir)
        loaded_config = new_manager.load()

        assert loaded_config.aws.profile == "test-profile"
        assert loaded_config.models.provider_filter == "test-provider"


def test_config_manager_env_overrides():
    """Test environment variable overrides."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        # Set environment variables
        with patch.dict(os.environ, {
            "CLAUTH_PROFILE": "env-profile",
            "CLAUTH_REGION": "us-west-2",
            "CLAUTH_AUTO_START": "false"
        }):
            config = manager.load()

            assert config.aws.profile == "env-profile"
            assert config.aws.region == "us-west-2"
            assert config.cli.auto_start is False


def test_config_manager_migrate_placeholder_urls():
    """Test migration of placeholder SSO URLs."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        # Create config with placeholder URL
        config = ClauthConfig()
        config.aws.sso_start_url = "https://d-xxxxxxxxxx.awsapps.com/start/"
        manager._config = config
        manager.save()

        # Load should migrate the URL
        loaded_config = manager.load()
        assert loaded_config.aws.sso_start_url is None


def test_config_manager_update_model_settings():
    """Test updating model settings."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        config = manager.load()
        manager.update_model_settings(
            default_model="claude-3-5-sonnet",
            fast_model="claude-3-5-haiku",
            default_arn="arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet",
            fast_arn="arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"
        )

        # Reload and check
        reloaded_config = manager.load()
        assert reloaded_config.models.default_model == "claude-3-5-sonnet"
        assert reloaded_config.models.fast_model == "claude-3-5-haiku"
        assert reloaded_config.models.default_model_arn == "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-sonnet"
        assert reloaded_config.models.fast_model_arn == "arn:aws:bedrock:us-east-1:123456789012:inference-profile/claude-3-5-haiku"


def test_get_config_manager_singleton():
    """Test that get_config_manager returns a singleton."""
    manager1 = get_config_manager()
    manager2 = get_config_manager()

    assert manager1 is manager2


def test_clauth_config_validation():
    """Test ClauthConfig validation."""
    # Valid config should work
    config = ClauthConfig()
    assert config.aws.profile == "clauth"

    # Test SSO URL validation - check that HTTPS URLs work
    config = ClauthConfig()
    config.aws.sso_start_url = "https://valid-url.com"
    assert config.aws.sso_start_url == "https://valid-url.com"


def test_config_manager_list_profiles():
    """Test listing configuration profiles."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        # Initially empty
        assert manager.list_profiles() == []

        # Create some profile files
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "dev.toml").touch()
        (profiles_dir / "prod.toml").touch()

        profiles = manager.list_profiles()
        assert "dev" in profiles
        assert "prod" in profiles
        assert len(profiles) == 2


def test_config_manager_profile_exists():
    """Test checking if a profile exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        assert not manager.profile_exists("test")

        # Create profile
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        (profiles_dir / "test.toml").touch()

        assert manager.profile_exists("test")


def test_config_manager_delete_profile():
    """Test deleting a configuration profile."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "clauth"
        manager = ConfigManager(config_dir)

        # Create profile
        profiles_dir = config_dir / "profiles"
        profiles_dir.mkdir(parents=True, exist_ok=True)
        profile_file = profiles_dir / "test.toml"
        profile_file.touch()

        assert manager.profile_exists("test")

        # Delete profile
        assert manager.delete_profile("test") is True
        assert not manager.profile_exists("test")

        # Try to delete non-existent profile
        assert manager.delete_profile("nonexistent") is False
