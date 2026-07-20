"""
hextol — hexadecimal comparison utilities.

Support package for KeyDaemon and anywhere else hex values need
comparing. Public API lands as the package takes shape.
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hextol")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
