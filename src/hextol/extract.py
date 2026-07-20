"""Dominant color extraction from images — requires the ``[extract]`` extra.

This module is never imported by ``import hextol``; import it explicitly::

    from hextol.extract import dominant_color

It needs numpy (and Pillow for file paths / PIL Images): install with
``pip install hextol[extract]``.
"""
from __future__ import annotations

try:
    import numpy as np
except ImportError:  # pragma: no cover
    raise ImportError(
        "hextol.extract requires numpy — install the extra: pip install hextol[extract]"
    ) from None

from hextol.convert import rgb_to_hex


def dominant_color(
    image,
    k: int = 3,
    *,
    sample_size: int = 10_000,
    max_iter: int = 20,
    tol: float = 1.0,
    seed: int | None = 0,
) -> list[str]:
    """Return the ``k`` most dominant colors of an image, largest cluster first.

    Hand-rolled, numpy-vectorized k-means — no sklearn. Built for repeated
    calls on small screenshot regions (e.g. a polling loop): pixels are
    subsampled before clustering, iterations are capped, and every k-means
    step is array broadcasting rather than a Python-level pixel loop.

    Args:
        image: A file path, a PIL Image, or a numpy array shaped ``(H, W, 3)``,
            ``(H, W, 4)``, ``(N, 3)``, or ``(N, 4)`` (alpha is ignored).
        k: Number of colors to return. Keep small (2-4) — this answers "what
            is the dominant color of this region", not "build a design
            palette". If the image has fewer distinct colors than ``k``, only
            the distinct colors are returned.
        sample_size: Maximum number of pixels fed to k-means; larger images
            are randomly subsampled to this count first.
        max_iter: Hard cap on k-means iterations.
        tol: Convergence threshold — stop when no centroid moved more than
            this (in RGB units).
        seed: Seed for subsampling and centroid initialization. The default
            (``0``) makes results deterministic; pass ``None`` for random
            initialization each call.

    Returns:
        Hex color strings ordered by cluster size, largest first.
    """
    if not isinstance(k, int) or k < 1:
        raise ValueError(f"k must be an integer >= 1, got {k!r}")
    pixels = _load_pixels(image)
    if pixels.shape[0] == 0:
        raise ValueError("Image contains no pixels")
    rng = np.random.default_rng(seed)

    if pixels.shape[0] > sample_size:
        idx = rng.choice(pixels.shape[0], size=sample_size, replace=False)
        pixels = pixels[idx]

    unique, counts = np.unique(pixels, axis=0, return_counts=True)
    if unique.shape[0] <= k:
        order = np.argsort(counts)[::-1]
        return [rgb_to_hex(*(int(c) for c in unique[i])) for i in order]

    data = pixels.astype(np.float64)
    centroids = unique[rng.choice(unique.shape[0], size=k, replace=False)].astype(np.float64)

    for _ in range(max_iter):
        # (N, k) squared distances via broadcasting; no Python pixel loops
        dists = ((data[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        labels = dists.argmin(axis=1)
        new_centroids = centroids.copy()
        for i in range(k):
            members = data[labels == i]
            if members.shape[0]:
                new_centroids[i] = members.mean(axis=0)
            else:  # empty cluster: reseed to a random pixel
                new_centroids[i] = data[rng.integers(data.shape[0])]
        shift = np.abs(new_centroids - centroids).max()
        centroids = new_centroids
        if shift <= tol:
            break

    dists = ((data[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
    labels = dists.argmin(axis=1)
    sizes = np.bincount(labels, minlength=k)
    order = np.argsort(sizes)[::-1]
    return [rgb_to_hex(*(int(c) for c in np.rint(centroids[i]))) for i in order]


def _load_pixels(image) -> "np.ndarray":
    """Normalize any accepted image form to a ``(N, 3)`` uint8 array."""
    if isinstance(image, (str, bytes)) or hasattr(image, "__fspath__"):
        from PIL import Image  # the [extract] extra guarantees Pillow

        with Image.open(image) as img:
            arr = np.asarray(img.convert("RGB"))
    elif hasattr(image, "getdata"):  # PIL Image already in memory
        arr = np.asarray(image.convert("RGB") if hasattr(image, "convert") else image)
    elif hasattr(image, "ndim"):
        arr = np.asarray(image)
    else:
        raise ValueError(f"Unsupported image input: {type(image).__name__}")

    if arr.ndim == 3 and arr.shape[-1] in (3, 4):
        arr = arr.reshape(-1, arr.shape[-1])
    if arr.ndim != 2 or arr.shape[-1] not in (3, 4):
        raise ValueError(f"Expected (H, W, 3/4) or (N, 3/4) pixel data, got shape {arr.shape}")
    return np.ascontiguousarray(arr[:, :3], dtype=np.uint8)
