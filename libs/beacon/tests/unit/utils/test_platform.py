"""Unit tests for platform support utilities."""

import sys

import pytest
from beacon.utils.platform import UnsupportedPlatformError, ensure_supported_platform


class TestEnsureSupportedPlatform:
    """Test cases for ensure_supported_platform (task 1.1 TCs)."""

    def test_darwin_returns_none(self, monkeypatch):
        """TC1: sys.platform == 'darwin' -> returns None, no exception."""
        monkeypatch.setattr(sys, "platform", "darwin")
        assert ensure_supported_platform() is None

    def test_linux_returns_none(self, monkeypatch):
        """TC2: sys.platform == 'linux' -> returns None, no exception."""
        monkeypatch.setattr(sys, "platform", "linux")
        assert ensure_supported_platform() is None

    def test_win32_raises(self, monkeypatch):
        """TC3: sys.platform == 'win32' -> raises UnsupportedPlatformError."""
        monkeypatch.setattr(sys, "platform", "win32")
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            ensure_supported_platform()
        assert "Windows" in str(exc_info.value)

    def test_cygwin_raises(self, monkeypatch):
        """TC4: sys.platform == 'cygwin' -> raises UnsupportedPlatformError."""
        monkeypatch.setattr(sys, "platform", "cygwin")
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            ensure_supported_platform()
        assert "Windows" in str(exc_info.value)

    def test_error_message_contains_platform_names(self, monkeypatch):
        """TC5: Exception message contains 'Windows' and 'macOS' or 'Linux'."""
        monkeypatch.setattr(sys, "platform", "win32")
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            ensure_supported_platform()
        msg = str(exc_info.value)
        assert "Windows" in msg
        assert "macOS" in msg or "Linux" in msg
