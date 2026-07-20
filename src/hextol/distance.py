"""Color distance formulas, normalized to a common 0-100 scale by default.

Every method returns ``0.0`` for identical colors and ``100.0`` for the most
distant pair it can produce (black vs white reaches 100 under all of them).
This means a given ``tolerance`` value is roughly comparable across methods —
you can switch ``method`` in a config without re-tuning the number.

Raw (unnormalized) values are available on every method via its ``.raw``
attribute — e.g. ``euclidean.raw(a, b)`` returns the actual straight-line RGB
distance (0..~441.67) instead of the 0-100 scale. Each method also carries
``.max_raw``, the raw value that maps to 100.

Which method to use:

- ``"channel"`` — near-exact pixel checks with a tight tolerance. Strictest:
  a single badly-off channel fails the match even if the others are perfect.
- ``"euclidean"`` — general-purpose default for "is this roughly that color".
- ``"weighted"`` — matching against a human-picked reference color, or when
  screen brightness/gamma may shift the sample. Perceptually truer than
  euclidean at nearly the same cost.
"""
from __future__ import annotations

import math
from functools import wraps

_EUCLIDEAN_MAX = math.sqrt(3) * 255
# The redmean coefficients always sum to 8 + 255/256 regardless of the mean
# red level, so the maximum distance (reached at black vs white) is constant.
_REDMEAN_MAX = 255 * math.sqrt(8 + 255 / 256)

Rgb = tuple[int, int, int]


def _normalized(max_raw: float):
    """Wrap a raw distance formula to return the 0-100 scale by default.

    The wrapped function keeps the raw formula reachable as ``.raw`` and the
    raw value that maps to 100 as ``.max_raw``.
    """

    def deco(fn):
        @wraps(fn)
        def wrapper(a: Rgb, b: Rgb) -> float:
            return fn(a, b) / max_raw * 100

        wrapper.raw = fn
        wrapper.max_raw = max_raw
        return wrapper

    return deco


@_normalized(255)
def channel(a: Rgb, b: Rgb) -> float:
    """Maximum per-channel absolute difference (raw range 0..255).

    The strictest method: the worst channel alone decides the distance.
    Use for near-exact checks with a tight tolerance. This matches the
    per-channel semantics of keydaemon's original ``color_matches``.
    """
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


@_normalized(_EUCLIDEAN_MAX)
def euclidean(a: Rgb, b: Rgb) -> float:
    """Straight-line distance in RGB space (raw range 0..~441.67).

    Naive with respect to human vision (a blue shift reads smaller than an
    equal green shift) but cheap and predictable — the general-purpose default.
    """
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt(dr * dr + dg * dg + db * db)


@_normalized(_REDMEAN_MAX)
def weighted(a: Rgb, b: Rgb) -> float:
    """Redmean distance — a cheap perceptual approximation (raw range 0..~764.83).

    Channel weights vary with the mean red level, tracking the eye's uneven
    color sensitivity far better than plain euclidean at almost the same cost.
    Prefer this when matching against a color a human picked by eye.
    """
    rmean = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt(
        (2 + rmean / 256) * dr * dr
        + 4 * dg * dg
        + (2 + (255 - rmean) / 256) * db * db
    )


METHODS = {
    "channel": channel,
    "euclidean": euclidean,
    "weighted": weighted,
}
"""Registry of distance methods, keyed by the plain string names used in configs."""


def get_method(name: str, raw: bool = False):
    """Look up a distance function by name, with a helpful error on typos.

    Args:
        name: One of the keys in ``METHODS``.
        raw: When ``True``, return the unnormalized formula (the same function
            available as ``METHODS[name].raw``).
    """
    try:
        fn = METHODS[name]
    except KeyError:
        valid = ", ".join(sorted(METHODS))
        raise ValueError(f"Unknown method {name!r}; valid methods: {valid}") from None
    return fn.raw if raw else fn
