# prov/version.py
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _dist_version

# Fallback for dev/editable/uninstalled contexts
__version__ = "0.1.2"

# IMPORTANT: this must match your distribution name in pyproject.toml
_DIST_NAME = "provenance-recorder"


def get_version(verbose: bool = False) -> str:
    """
    Returns the installed distribution version if available, otherwise __version__.

    If verbose=True, include both values when they differ.
    """
    fallback = __version__
    try:
        dist = _dist_version(_DIST_NAME)
    except PackageNotFoundError:
        dist = None

    if not verbose:
        return dist or fallback

    if dist is None:
        return f"{fallback} (fallback; dist not installed)"

    if dist == fallback:
        return f"{dist}"
    return f"{dist} (dist), fallback={fallback}"
