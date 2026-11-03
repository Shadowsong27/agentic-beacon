"""Unit tests for the pure rules of abc warehouse reads (AB-122 D4, D7)."""

import pytest
from beacon.domains.warehouse.warehouse_read import (
    InvalidNameError,
    check_agent_name,
    check_board_or_domain,
    check_context_name,
    decision_rules_section,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("## Decision rules\nDR1 a\n## Next\nx\n", "DR1 a"),
        ("## Decision rules\nDR1 a\n---\nx\n", "DR1 a"),
        ("## Decision rules\nDR1 a\nDR2 b", "DR1 a\nDR2 b"),
        ("## Decision rules\n\n\nDR1 a\n\n\n## Next\n", "DR1 a"),
        (
            "## Decision rules\nfirst\n## Decision rules\nsecond\n",
            "first",
        ),
        ("## Decision rules\n## Next\n", ""),
        ("### Decision rules\nnot a match\n", None),
        ("# Intro\nno section here\n", None),
    ],
    ids=[
        "stops-at-h2",
        "stops-at-rule",
        "runs-to-eof",
        "trims-blank-lines",
        "first-heading-only",
        "empty-body",
        "h3-not-matched",
        "no-heading",
    ],
)
def test_decision_rules_section(text, expected):
    assert decision_rules_section(text) == expected


@pytest.mark.parametrize("name", ["alpha", "teams/beta", "a.b-c_d", "Z9"])
def test_valid_context_names_pass(name):
    assert check_context_name(name) == name


@pytest.mark.parametrize("name", ["alpha.md", "../x", "a//b", "a/../b", "-x", ""])
def test_invalid_context_names_raise(name):
    with pytest.raises(InvalidNameError):
        check_context_name(name)


@pytest.mark.parametrize("name", ["context-selector", "x_1"])
def test_valid_agent_names_pass(name):
    assert check_agent_name(name) == name


@pytest.mark.parametrize("name", ["alpha.md", "teams/beta", "../x"])
def test_invalid_agent_names_raise(name):
    with pytest.raises(InvalidNameError):
        check_agent_name(name)


@pytest.mark.parametrize("value", ["AB", "airflow-platform", "a_b"])
def test_valid_board_or_domain_passes(value):
    assert check_board_or_domain(value, "board") == value


@pytest.mark.parametrize("value", ["A/B", "-x", "x.y", "../x", ""])
def test_invalid_board_or_domain_raises(value):
    with pytest.raises(InvalidNameError):
        check_board_or_domain(value, "board")
