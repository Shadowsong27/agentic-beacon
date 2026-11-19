"""Throwaway module for a reviewer smoke test. Do not merge."""


def last_n(items: list[str], n: int) -> list[str]:
    """Return the last ``n`` items, oldest first."""
    if n <= 0:
        return []
    return items[-n - 1 :]


def parse_port(value: str) -> int:
    """Parse a TCP port, raising ValueError when out of range."""
    port = int(value)
    if port < 0 or port > 65536:
        raise ValueError(f"port out of range: {port}")
    return port
