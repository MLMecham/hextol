"""Tolerance-based color comparison — hextol's flagship module.

``is_match`` always returns a plain ``bool``. For per-pixel detail use
``distances`` or ``match_mask``.

A *sample* may be a single color (hex string or RGB tuple) or a collection of
pixels: a list of colors, a PIL Image (duck-typed via ``.getdata()`` — PIL is
never imported), or a numpy array shaped ``(3,)``, ``(N, 3)``, or ``(H, W, 3)``
(duck-typed via ``.ndim`` — numpy is never required). RGBA pixels are accepted;
alpha is ignored.
"""
from __future__ import annotations

from typing import Sequence, Union

from hextol.convert import Color, to_rgb
from hextol.distance import get_method

Sample = Union[Color, Sequence[Color]]

AGGREGATES = ("majority", "all", "any", "average")


def _as_pixels(sample) -> tuple[list[tuple[int, int, int]], bool]:
    """Normalize a sample to ``(list_of_rgb_tuples, is_single)``."""
    if isinstance(sample, str):
        return [to_rgb(sample)], True
    if hasattr(sample, "getdata"):  # PIL Image, duck-typed
        pixels = list(sample.getdata())
        if pixels and not isinstance(pixels[0], (tuple, list)):
            raise ValueError("Image must be RGB or RGBA (convert with .convert('RGB'))")
        return [to_rgb(p) for p in pixels], False
    if hasattr(sample, "ndim"):  # numpy array, duck-typed
        if sample.ndim == 1:
            return [to_rgb(sample.tolist())], True
        if sample.ndim == 2:
            return [to_rgb(p) for p in sample.tolist()], False
        if sample.ndim == 3:
            flat = sample.reshape(-1, sample.shape[-1]).tolist()
            return [to_rgb(p) for p in flat], False
        raise ValueError(f"Array sample must have 1-3 dimensions, got {sample.ndim}")
    try:
        items = list(sample)
    except TypeError:
        raise ValueError(f"Invalid sample: {sample!r}") from None
    if not items:
        raise ValueError("Sample is empty")
    if isinstance(items[0], (int, float)):
        return [to_rgb(items)], True
    return [to_rgb(p) for p in items], False


def distances(sample: Sample, target: Color, method: str = "euclidean", normalize: bool = True):
    """Distance from ``target``, per pixel.

    Returns a single float for a single-color sample, or a list of floats
    (one per pixel) for a region sample.

    By default distances are on the normalized 0-100 scale. Pass
    ``normalize=False`` for the method's raw value (e.g. actual straight-line
    RGB distance for ``"euclidean"``, max per-channel difference in 0..255 for
    ``"channel"``). The raw formulas are also directly available as
    ``hextol.distance.<method>.raw``.

    Examples:
        >>> round(distances("#000000", "#FFFFFF"))
        100
        >>> round(distances("#000000", "#FFFFFF", normalize=False))
        442
        >>> distances([(0, 0, 0), (255, 255, 255)], "#000000")
        [0.0, 100.0]
    """
    fn = get_method(method, raw=not normalize)
    t = to_rgb(target)
    pixels, single = _as_pixels(sample)
    if single:
        return fn(pixels[0], t)
    return [fn(p, t) for p in pixels]


def match_mask(
    sample: Sample,
    target: Color,
    tolerance: float = 10,
    method: str = "euclidean",
) -> list[bool]:
    """Per-pixel match verdicts: ``True`` where within ``tolerance`` of ``target``.

    Always returns a list (length 1 for a single-color sample). ``tolerance``
    is on the normalized 0-100 scale, as everywhere tolerance appears.
    """
    _check_tolerance(tolerance)
    fn = get_method(method)
    t = to_rgb(target)
    pixels, _ = _as_pixels(sample)
    return [fn(p, t) <= tolerance for p in pixels]


def is_match(
    sample: Sample,
    target: Color,
    tolerance: float = 10,
    method: str = "euclidean",
    aggregate: str = "majority",
) -> bool:
    """Return whether ``sample`` matches ``target`` within ``tolerance``.

    The flagship function: always returns a plain ``bool``, for single colors
    and whole regions alike. ``tolerance`` is on the normalized 0-100 scale
    (0 = only an exact match passes, 100 = anything passes) and means roughly
    the same strictness under every ``method``. The comparison is inclusive
    (distance equal to ``tolerance`` passes).

    Args:
        sample: A single color or a region (see module docstring for forms).
        target: The expected color (hex string or RGB tuple).
        tolerance: Maximum allowed distance, 0-100.
        method: ``"channel"``, ``"euclidean"``, or ``"weighted"`` — see
            ``hextol.distance`` for when to use which.
        aggregate: How a region collapses to one verdict (ignored for a
            single-color sample):

            - ``"majority"`` (default) — more than half of the pixels are
              individually within tolerance. Robust to icon edges and
              anti-aliasing without letting a half-wrong region pass.
            - ``"all"`` — every pixel within tolerance.
            - ``"any"`` — at least one pixel within tolerance.
            - ``"average"`` — mean distance across the region is within
              tolerance.

    Examples:
        >>> is_match("#3B82F6", "#3A80F0", tolerance=5)
        True
        >>> is_match([(0, 0, 0), (2, 2, 2), (250, 250, 250)], "#000000", tolerance=5)
        True
    """
    _check_tolerance(tolerance)
    if aggregate not in AGGREGATES:
        valid = ", ".join(AGGREGATES)
        raise ValueError(f"Unknown aggregate {aggregate!r}; valid aggregates: {valid}")
    fn = get_method(method)
    t = to_rgb(target)
    pixels, single = _as_pixels(sample)
    if single:
        return fn(pixels[0], t) <= tolerance
    dists = [fn(p, t) for p in pixels]
    if aggregate == "average":
        return sum(dists) / len(dists) <= tolerance
    within = sum(d <= tolerance for d in dists)
    if aggregate == "all":
        return within == len(dists)
    if aggregate == "any":
        return within > 0
    return within * 2 > len(dists)  # majority


def _check_tolerance(tolerance) -> None:
    if not isinstance(tolerance, (int, float)) or tolerance < 0:
        raise ValueError(f"tolerance must be a non-negative number, got {tolerance!r}")
