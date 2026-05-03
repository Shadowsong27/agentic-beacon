"""Platform support utilities."""

import sys


class UnsupportedPlatformError(Exception):
    """Raised when the current platform is not supported."""

    pass


def ensure_supported_platform() -> None:
    """Raise UnsupportedPlatformError on unsupported platforms.

    Supported: macOS (darwin), Linux (linux).
    Unsupported: Windows (win32, cygwin).
    """
    plat = sys.platform
    if plat in ("darwin", "linux"):
        return
    if plat.startswith("win") or plat == "cygwin":
        raise UnsupportedPlatformError(
            "Windows is not supported. "
            "Please use macOS or Linux for symlink-based artifact sync."
        )
    # For any other unknown platform, also reject
    raise UnsupportedPlatformError(
        f"Platform '{plat}' is not supported. "
        "Please use macOS or Linux for symlink-based artifact sync."
    )
