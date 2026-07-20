"""hextol — hexadecimal tolerance: compare colors within a tolerance.

Flagship usage (zero dependencies)::

    from hextol import is_match

    is_match("#3B82F6", (59, 128, 240), tolerance=10, method="weighted")

Per-pixel detail lives in :mod:`hextol.compare` (``distances``, ``match_mask``);
conversions in :mod:`hextol.convert`; distance formulas in :mod:`hextol.distance`.
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hextol")
except PackageNotFoundError:
    __version__ = "0.0.0"

from hextol.compare import is_match

__all__ = ["is_match", "__version__"]
