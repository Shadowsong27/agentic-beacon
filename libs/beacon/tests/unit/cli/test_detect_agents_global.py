"""Tests for detect_agents_global() function.

TDD Test Cases:
- TC1: Both ~/.config/opencode/ and ~/.claude/ exist → ["opencode", "claudecode"]
- TC2: Only ~/.config/opencode/ exists → ["opencode"]
- TC3: Only ~/.claude/ exists → ["claudecode"]
- TC4: Neither exists → []
- TC5: ~/.config/opencode is a file (not dir) → not counted
"""

from beacon.domains.artifact.agent import detect_agents_global


class TestDetectAgentsGlobal:
    """Tests for detect_agents_global() covering TC1-TC5."""

    def test_tc1_both_dirs_exist(self, tmp_path, monkeypatch):
        """TC1: Both ~/.config/opencode/ and ~/.claude/ exist → ["opencode", "claudecode"]."""
        fake_home = tmp_path / "home"
        (fake_home / ".config" / "opencode").mkdir(parents=True)
        (fake_home / ".claude").mkdir(parents=True)
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = detect_agents_global()

        assert "opencode" in result
        assert "claudecode" in result

    def test_tc2_only_opencode_exists(self, tmp_path, monkeypatch):
        """TC2: Only ~/.config/opencode/ exists → ["opencode"]."""
        fake_home = tmp_path / "home"
        (fake_home / ".config" / "opencode").mkdir(parents=True)
        fake_home.mkdir(exist_ok=True)
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = detect_agents_global()

        assert result == ["opencode"]

    def test_tc3_only_claude_exists(self, tmp_path, monkeypatch):
        """TC3: Only ~/.claude/ exists → ["claudecode"]."""
        fake_home = tmp_path / "home"
        (fake_home / ".claude").mkdir(parents=True)
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = detect_agents_global()

        assert result == ["claudecode"]

    def test_tc4_neither_exists(self, tmp_path, monkeypatch):
        """TC4: Neither exists → []."""
        fake_home = tmp_path / "home"
        fake_home.mkdir(parents=True)
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = detect_agents_global()

        assert result == []

    def test_tc5_opencode_is_file_not_dir(self, tmp_path, monkeypatch):
        """TC5: ~/.config/opencode is a file (not dir) → not counted."""
        fake_home = tmp_path / "home"
        (fake_home / ".config").mkdir(parents=True)
        (fake_home / ".config" / "opencode").write_text("not a dir")
        monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)

        result = detect_agents_global()

        assert "opencode" not in result
