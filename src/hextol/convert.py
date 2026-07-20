"""Color representation conversions: hex <-> RGB <-> HSL.

All hex parsing is case-insensitive and accepts an optional leading ``#``.
Three-digit shorthand (``#3BF``) expands per CSS rules (``#33BBFF``).
"""
from __future__ import annotations

import colorsys
from typing import Sequence, Union

Color = Union[str, Sequence[int]]
"""A color as a hex string (``"#3B82F6"``) or an RGB(A) sequence (``(59, 130, 246)``)."""


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a hex color string to an ``(r, g, b)`` tuple.

    Args:
        hex_str: Hex color like ``"#3B82F6"``, ``"3b82f6"``, or shorthand ``"#3BF"``.

    Returns:
        Integer channels in ``0..255``.

    Examples:
        >>> hex_to_rgb("#3B82F6")
        (59, 130, 246)
        >>> hex_to_rgb("3bf")
        (51, 187, 255)
    """
    if not isinstance(hex_str, str):
        raise ValueError(f"Invalid hex color: {hex_str!r}")
    s = hex_str.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"Invalid hex color: {hex_str!r}")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        raise ValueError(f"Invalid hex color: {hex_str!r}") from None


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB channels to an uppercase 6-digit hex string with a leading ``#``.

    Examples:
        >>> rgb_to_hex(59, 130, 246)
        '#3B82F6'
    """
    for v in (r, g, b):
        if not isinstance(v, int) or not 0 <= v <= 255:
            raise ValueError(f"RGB channels must be integers in 0..255, got {(r, g, b)!r}")
    return f"#{r:02X}{g:02X}{b:02X}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert RGB channels to ``(hue, saturation, lightness)``.

    Hue is in degrees ``0..360``; saturation and lightness are percentages ``0..100``.
    """
    h, lightness, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return (h * 360, s * 100, lightness * 100)


def hsl_to_rgb(h: float, s: float, lightness: float) -> tuple[int, int, int]:
    """Convert ``(hue 0..360, saturation 0..100, lightness 0..100)`` to RGB channels."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, lightness / 100, s / 100)
    return (round(r * 255), round(g * 255), round(b * 255))


def hex_to_hsl(hex_str: str) -> tuple[float, float, float]:
    """Convert a hex color string to ``(hue, saturation, lightness)``."""
    return rgb_to_hsl(*hex_to_rgb(hex_str))


def hsl_to_hex(h: float, s: float, lightness: float) -> str:
    """Convert ``(hue, saturation, lightness)`` to an uppercase hex string."""
    return rgb_to_hex(*hsl_to_rgb(h, s, lightness))


def to_rgb(color: Color) -> tuple[int, int, int]:
    """Normalize any accepted color form to an ``(r, g, b)`` tuple.

    Accepts a hex string or a sequence of 3 (RGB) or 4 (RGBA — alpha is
    ignored) integers in ``0..255``. Every public hextol function funnels its
    color arguments through here, so they all accept the same forms.
    """
    if isinstance(color, str):
        return hex_to_rgb(color)
    try:
        channels = tuple(color)
    except TypeError:
        raise ValueError(f"Invalid color: {color!r}") from None
    if len(channels) not in (3, 4):
        raise ValueError(f"Invalid color (expected 3 or 4 channels): {color!r}")
    rgb = []
    for v in channels[:3]:
        try:
            i = int(v)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid color channel {v!r} in {color!r}") from None
        if i != v or not 0 <= i <= 255:
            raise ValueError(f"Invalid color channel {v!r} in {color!r}")
        rgb.append(i)
    return (rgb[0], rgb[1], rgb[2])
