"""Grouping similar colors — tolerance-based dedupe over a list of colors.

Pure Python, zero dependencies. All distance math comes from
:mod:`hextol.distance` — one source of truth for "how close are two colors".
"""
from __future__ import annotations

from typing import Sequence

from hextol.convert import Color, rgb_to_hex, to_rgb
from hextol.distance import get_method


def _luminance(rgb: tuple[int, int, int]) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def group_similar(
    colors: Sequence[Color],
    tolerance: float = 10,
    method: str = "euclidean",
) -> list[list[str]]:
    """Group colors into clusters of mutually similar colors.

    Greedy leader clustering: colors are first sorted by luminance (so results
    do not depend on caller ordering), then each color joins the first existing
    group whose *leader* (founding color) is within ``tolerance``, or founds a
    new group. Greedy-by-leader is the documented answer to non-transitivity —
    A may be within tolerance of B, and B of C, without A being within
    tolerance of C; chaining them into one group would defeat a tolerance
    dedupe, so membership is always judged against the leader alone.

    Args:
        colors: Colors to group (hex strings or RGB tuples, mixed freely).
        tolerance: Maximum distance from a group's leader, on the normalized
            0-100 scale (same meaning as everywhere else in hextol).
        method: Distance method name — see :mod:`hextol.distance`.

    Returns:
        Groups as lists of normalized hex strings, each group led by its
        founding color, ordered darkest leader first.

    Examples:
        >>> group_similar(["#000000", "#020202", "#FFFFFF"], tolerance=5)
        [['#000000', '#020202'], ['#FFFFFF']]
    """
    if not isinstance(tolerance, (int, float)) or tolerance < 0:
        raise ValueError(f"tolerance must be a non-negative number, got {tolerance!r}")
    fn = get_method(method)

    rgbs = sorted((to_rgb(c) for c in colors), key=_luminance)
    leaders: list[tuple[int, int, int]] = []
    groups: list[list[str]] = []
    for rgb in rgbs:
        for leader, group in zip(leaders, groups):
            if fn(rgb, leader) <= tolerance:
                group.append(rgb_to_hex(*rgb))
                break
        else:
            leaders.append(rgb)
            groups.append([rgb_to_hex(*rgb)])
    return groups
