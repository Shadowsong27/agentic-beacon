"""Offline/cache-cold guard for integration tests that invoke uv with PEP 723 deps.

Policy: set BEACON_OFFLINE=1 to skip network-dependent integration tests.
When to set it: working offline, on a flaky network, or deliberately running the
suite without hitting any package registry.

Future extension point: a pytest fixture with autouse=True could add a cache-warm
probe behind a second env var, but ship only the env-var path for now.
"""

from __future__ import annotations

import os


def _is_offline_or_cache_cold() -> bool:
    """Return True if BEACON_OFFLINE=1 is set in the environment."""
    return os.environ.get("BEACON_OFFLINE") == "1"
