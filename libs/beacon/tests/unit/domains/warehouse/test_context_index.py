"""Unit tests for describe_context (context index description and naming rules)."""

import pytest
from beacon.domains.warehouse.context_index import describe_context


@pytest.mark.parametrize(
    ("path", "text", "name", "description", "warns"),
    [
        pytest.param(
            "contexts/python.md",
            "---\ndescription: '  Python rules.  '\n---\n# Body\n",
            "python",
            "Python rules.",
            False,
            id="usable-description-stripped",
        ),
        pytest.param(
            "contexts/a.md",
            "# No frontmatter\n",
            "a",
            "",
            True,
            id="no-frontmatter",
        ),
        pytest.param(
            "contexts/a.md",
            "---\ndescription: [unclosed\n---\n",
            "a",
            "",
            True,
            id="yaml-parse-error",
        ),
        pytest.param(
            "contexts/a.md",
            "---\ntitle: Only other keys\n---\n",
            "a",
            "",
            True,
            id="key-absent-other-keys-ignored",
        ),
        pytest.param(
            "contexts/a.md",
            "---\ndescription: '   '\n---\n",
            "a",
            "",
            True,
            id="whitespace-only",
        ),
        pytest.param(
            "contexts/a.md",
            "---\ndescription: 42\n---\n",
            "a",
            "",
            True,
            id="non-string",
        ),
        pytest.param(
            "contexts/a.md",
            None,
            "a",
            "",
            True,
            id="not-utf8",
        ),
        pytest.param(
            "contexts/teams/backend.md",
            "---\ndescription: Backend.\n---\n",
            "teams/backend",
            "Backend.",
            False,
            id="nested-name",
        ),
    ],
)
def test_describe_context(path, text, name, description, warns):
    """Each D3 description case and the D6 naming rule, one parametrized test."""
    entry, warning = describe_context(path, text)
    assert entry.name == name
    assert entry.path == path
    assert entry.description == description
    if warns:
        assert warning is not None
        assert warning.startswith(f"{path}: ")
    else:
        assert warning is None
