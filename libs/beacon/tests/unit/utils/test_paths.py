"""Unit tests for path normalization utilities."""

import pytest
from beacon.utils.paths import normalize_relative_path


class TestNormalizeRelativePath:
    """Test cases for normalize_relative_path (PER-184)."""

    def test_plain_path_unchanged(self):
        """A clean relative path passes through unchanged."""
        assert normalize_relative_path("contexts/a.md") == "contexts/a.md"

    def test_leading_dot_slash_stripped(self):
        """Leading './' is removed."""
        assert normalize_relative_path("./contexts/a.md") == "contexts/a.md"

    def test_double_slash_collapsed(self):
        """Redundant '//' separators are collapsed."""
        assert normalize_relative_path("contexts//a.md") == "contexts/a.md"

    def test_nested_dot_segments_collapsed(self):
        """Interior '.' segments are collapsed."""
        assert normalize_relative_path("contexts/./a.md") == "contexts/a.md"

    def test_absolute_path_rejected(self):
        """Absolute paths raise ValueError."""
        with pytest.raises(ValueError, match="[Aa]bsolute"):
            normalize_relative_path("/absolute/path.md")

    def test_parent_traversal_rejected(self):
        """Paths containing '..' raise ValueError."""
        with pytest.raises(ValueError, match="[Pp]arent-directory"):
            normalize_relative_path("../outside.md")

    def test_parent_traversal_interior_rejected(self):
        """A '..' component anywhere in the path is rejected."""
        with pytest.raises(ValueError, match="[Pp]arent-directory"):
            normalize_relative_path("contexts/../../../etc/passwd")

    def test_dotdot_in_filename_not_rejected(self):
        """A literal '..' inside a filename is not a traversal component."""
        assert normalize_relative_path("contexts/foo..bar.md") == "contexts/foo..bar.md"
