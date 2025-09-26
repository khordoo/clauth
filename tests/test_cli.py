"""Unit tests for CLI functions."""

import pytest
from unittest.mock import patch, Mock
import os
import tempfile
import shutil
from pathlib import Path

from clauth.helpers import get_app_path, ExecutableNotFoundError


class TestGetAppPath:
    """Tests for get_app_path function."""

    @pytest.mark.unit
    @patch('os.name', 'posix')  # Mock Unix/Linux
    def test_get_app_path_valid_executable(self, mock_typer_echo):
        """Test get_app_path with a valid executable on Unix/Linux."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/python'
            result = get_app_path('python')

            assert result == '/usr/bin/python'
            mock_which.assert_called_once_with('python')
            mock_typer_echo.assert_called_once_with("Using executable: /usr/bin/python")

    @pytest.mark.unit
    def test_get_app_path_executable_not_found(self):
        """Test get_app_path when executable is not found."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = None

            with pytest.raises(ExecutableNotFoundError) as exc_info:
                get_app_path('nonexistent-exe')

            assert 'nonexistent-exe not found in system PATH' in str(exc_info.value)
            mock_which.assert_called_once_with('nonexistent-exe')

    @pytest.mark.unit
    def test_get_app_path_empty_name(self):
        """Test get_app_path with empty executable name."""
        with pytest.raises(ValueError) as exc_info:
            get_app_path('')

        assert 'Invalid executable name provided' in str(exc_info.value)

    @pytest.mark.unit
    def test_get_app_path_whitespace_name(self):
        """Test get_app_path with whitespace-only executable name."""
        with pytest.raises(ValueError) as exc_info:
            get_app_path('   ')

        assert 'Invalid executable name provided' in str(exc_info.value)

    @pytest.mark.unit
    @patch('os.name', 'nt')  # Mock Windows
    def test_get_app_path_windows_prefers_cmd(self, mock_typer_echo):
        """Test that Windows version prefers .cmd executable when available."""
        with patch('shutil.which') as mock_which:
            # First call returns the basic executable
            # Second call (for .cmd) returns the preferred version
            mock_which.side_effect = [
                'C:\\Users\\test\\AppData\\Roaming\\npm\\claude',
                'C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd'
            ]

            result = get_app_path('claude')

            assert result == 'C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd'
            assert mock_which.call_count == 2
            mock_which.assert_any_call('claude')
            mock_which.assert_any_call('claude.cmd')
            mock_typer_echo.assert_called_once_with(
                "Found multiple claude executables, using: C:\\Users\\test\\AppData\\Roaming\\npm\\claude.cmd"
            )

    @pytest.mark.unit
    @patch('os.name', 'nt')  # Mock Windows
    def test_get_app_path_windows_prefers_exe(self, mock_typer_echo):
        """Test that Windows version prefers .exe executable when .cmd not available."""
        with patch('shutil.which') as mock_which:
            # First call returns the basic executable
            # Second call (.cmd) returns None
            # Third call (.exe) returns the preferred version
            mock_which.side_effect = [
                'C:\\Users\\test\\python',
                None,  # No .cmd version
                'C:\\Users\\test\\python.exe'
            ]

            result = get_app_path('python')

            assert result == 'C:\\Users\\test\\python.exe'
            assert mock_which.call_count == 3
            mock_which.assert_any_call('python')
            mock_which.assert_any_call('python.cmd')
            mock_which.assert_any_call('python.exe')
            mock_typer_echo.assert_called_once_with(
                "Found multiple python executables, using: C:\\Users\\test\\python.exe"
            )

    @pytest.mark.unit
    @patch('os.name', 'nt')  # Mock Windows
    def test_get_app_path_windows_no_preferred_extension(self, mock_typer_echo):
        """Test Windows behavior when no .cmd/.exe variants exist."""
        with patch('shutil.which') as mock_which:
            # First call returns the basic executable
            # Subsequent calls for .cmd and .exe return None
            mock_which.side_effect = [
                'C:\\Users\\test\\some-tool',
                None,  # No .cmd version
                None   # No .exe version
            ]

            result = get_app_path('some-tool')

            assert result == 'C:\\Users\\test\\some-tool'
            assert mock_which.call_count == 3
            mock_typer_echo.assert_called_once_with("Using executable: C:\\Users\\test\\some-tool")

    @pytest.mark.unit
    @patch('os.name', 'posix')  # Mock Unix/Linux
    def test_get_app_path_unix_no_extension_preference(self, mock_typer_echo):
        """Test that Unix systems don't try to add extensions."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/python'

            result = get_app_path('python')

            assert result == '/usr/bin/python'
            mock_which.assert_called_once_with('python')
            mock_typer_echo.assert_called_once_with("Using executable: /usr/bin/python")

    @pytest.mark.unit
    @patch('os.name', 'nt')  # Mock Windows
    def test_get_app_path_windows_already_has_extension(self, mock_typer_echo):
        """Test Windows behavior when executable name already has .cmd/.exe extension."""
        with patch('shutil.which') as mock_which:
            # When name already has extension, we still check for additional extensions
            mock_which.side_effect = [
                'C:\\Users\\test\\claude.cmd',  # First call with original name
                None  # Second call with .exe extension returns None
            ]

            result = get_app_path('claude.cmd')

            assert result == 'C:\\Users\\test\\claude.cmd'
            assert mock_which.call_count == 2
            mock_which.assert_any_call('claude.cmd')
            mock_which.assert_any_call('claude.cmd.exe')
            mock_typer_echo.assert_called_once_with("Using executable: C:\\Users\\test\\claude.cmd")

    @pytest.mark.unit
    @patch('os.name', 'posix')  # Mock Unix/Linux
    def test_get_app_path_default_parameter(self, mock_typer_echo):
        """Test get_app_path with default parameter on Unix/Linux."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/claude'

            # Test calling without parameter (should default to 'claude')
            result = get_app_path()

            assert result == '/usr/bin/claude'
            mock_which.assert_called_once_with('claude')

    @pytest.mark.unit
    def test_get_app_path_none_parameter(self):
        """Test get_app_path with None parameter."""
        with pytest.raises(ValueError) as exc_info:
            get_app_path(None)

        assert 'Invalid executable name provided' in str(exc_info.value)
