"""Gradient building — ordered color ramps interpolated between two endpoints.

A convenience on top of :mod:`hextol.convert`; nothing here is used by the
comparison core. Its one mission-aligned job is visualizing tolerance (e.g.
showing a config author what colors sit near a target).
"""
from __future__ import annotations

from hextol.convert import Color, rgb_to_hex, rgb_to_hsl, hsl_to_rgb, to_rgb

SPACES = ("rgb", "hsl")


def build_gradient(color_a: Color, color_b: Color, steps: int, space: str = "rgb") -> list[str]:
    """Return ``steps`` evenly spaced hex colors from ``color_a`` to ``color_b``.

    Both endpoints are included, so ``steps=2`` returns exactly the two input
    colors (as normalized hex strings).

    Args:
        color_a: Start color (hex string or RGB tuple).
        color_b: End color.
        steps: Total number of colors returned, including both endpoints (>= 2).
        space: Interpolation space:

            - ``"rgb"`` — straight line through the RGB cube. Simple and
              predictable, but some pairs (e.g. blue to yellow) pass through a
              muddy gray middle.
            - ``"hsl"`` — interpolates hue along the shorter arc of the hue
              wheel, keeping intermediate colors vivid. Note that grays have no
              meaningful hue, so gradients starting or ending on a gray can
              take an arbitrary hue path.

    Examples:
        >>> build_gradient("#000000", "#FFFFFF", 3)
        ['#000000', '#808080', '#FFFFFF']
        >>> build_gradient("#FF0000", "#FF00FF", 3, space="hsl")
        ['#FF0000', '#FF0080', '#FF00FF']
    """
    if not isinstance(steps, int) or steps < 2:
        raise ValueError(f"steps must be an integer >= 2, got {steps!r}")
    if space not in SPACES:
        valid = ", ".join(SPACES)
        raise ValueError(f"Unknown space {space!r}; valid spaces: {valid}")

    a, b = to_rgb(color_a), to_rgb(color_b)
    ts = [i / (steps - 1) for i in range(steps)]

    if space == "rgb":
        return [
            rgb_to_hex(
                round(a[0] + (b[0] - a[0]) * t),
                round(a[1] + (b[1] - a[1]) * t),
                round(a[2] + (b[2] - a[2]) * t),
            )
            for t in ts
        ]

    ha, sa, la = rgb_to_hsl(*a)
    hb, sb, lb = rgb_to_hsl(*b)
    dh = ((hb - ha + 180) % 360) - 180  # shorter arc around the hue wheel
    return [
        rgb_to_hex(
            *hsl_to_rgb(
                (ha + dh * t) % 360,
                sa + (sb - sa) * t,
                la + (lb - la) * t,
            )
        )
        for t in ts
    ]
