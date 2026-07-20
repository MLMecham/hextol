# hextol — Implementation Plan

## What It Is

A Python library for comparing colors within a tolerance ("hexadecimal tolerance"),
extracting dominant colors from images, and building gradients/palettes. Built as a
lightweight core dependency for other projects — most immediately `keydaemon`, which
needs "does this region of the screen look roughly like the color I expect" as an
automation trigger condition.

**Design principle #1: the flagship export (`is_match`) is free to import.**
The core install has **zero dependencies**. Anything heavier (numpy, Pillow) lives
behind extras. A background daemon pulling hextol pays nothing but the import.

PyPI name verified free as of 2026-07-19.

---

## Core Mental Model

```
"#3B82F6"  ─┐
(59,130,246)─┤→ convert → RGB tuples → distance (0–100 scale) → compare to tolerance → bool
PIL Image  ─┤                             ↑
list/array ─┘                       method by string name
```

Every distance method is **normalized to a common 0–100 scale** (0 = identical,
100 = black vs white). `tolerance=25` means roughly the same strictness under every
method — config authors can switch methods without re-tuning. This is the package's
most important usability decision.

**`is_match` always returns a plain `bool`.** Per-pixel detail lives in separate
functions (`distances`, `match_mask`) — no return types that change based on a
parameter value.

**Space vs time:** aggregating many pixels at one moment is `is_match(aggregate=...)`.
Aggregating one region across many moments is `matches_across(rule=...)` (v2).
The two never share parameter names.

---

## Distribution / Install Matrix

| Use case | Install | Deps pulled |
|---|---|---|
| Color/region comparison (keydaemon's case) | `pip install hextol` | **none** |
| + dominant color / palette extraction | `pip install hextol[extract]` | numpy, Pillow |
| + desktop GUI app | `pip install hextol[gui]` | none (tkinter is stdlib — extra is a documentation marker only) |
| everything | `pip install hextol[all]` | numpy, Pillow |

numpy is **not** a core dependency (keydaemon has no numpy in its tree, and a
single-pixel check is three subtractions; even a 50×50 region is ~1ms in pure
Python). Where numpy is genuinely needed — k-means in `extract.py` — it's behind
the extra. Core functions duck-type their input: if handed a numpy array and numpy
is importable, they may take a vectorized fast path, but never require it.

---

## Module Layout

```
hextol/
├── __init__.py     # exports is_match (+ __version__) — zero-dep import, always
├── convert.py      # hex <-> rgb <-> hsl; input normalization
├── distance.py     # distance formulas, all normalized 0–100, registry by string name
├── compare.py      # is_match / distances / match_mask
├── gradient.py     # build_gradient
├── cluster.py      # group_similar (pure Python, built on distance.py)
└── extract.py      # dominant_color — requires [extract]; imported explicitly, never
                    # pulled in by `import hextol`
```

`from hextol import is_match` works with zero extras. `extract.py` raises a clear
ImportError naming the extra (`pip install hextol[extract]`) if numpy/Pillow are missing.

---

## convert.py

- `hex_to_rgb(s) -> (r, g, b)` — accepts `#3B82F6`, `3B82F6`, `#3BF` (3-digit
  shorthand expands per CSS rules), case-insensitive. Clear ValueError otherwise.
- `rgb_to_hex(r, g, b) -> "#RRGGBB"` (uppercase, always 6-digit, leading `#`).
- `hex_to_hsl` / `hsl_to_rgb` etc. — needed by gradient's HSL mode.
- `to_rgb(color)` — internal normalizer used by every public function: accepts hex
  str, `(r, g, b)` tuple/list, and validates range.

## distance.py

All methods return a float on the **0–100 normalized scale** and are registered in
a `METHODS` dict keyed by string name (TOML-friendly — no enums):

- `"channel"` — max per-channel absolute difference. Fast, strict, best for
  near-exact checks. (This is exactly what keydaemon's `color_matches` does today.)
- `"euclidean"` — straight-line RGB distance. Naive but general-purpose default.
- `"weighted"` — **redmean** (`ΔC² = (2+r̄/256)ΔR² + 4ΔG² + (2+(255-r̄)/256)ΔB²`):
  a cheap perceptual approximation, chosen over fixed luma weights (those model
  brightness sensitivity, not color difference). Barely costs more than euclidean.
- (v2, only if `weighted` proves insufficient) `"delta_e"` — CIELAB ΔE. Start with
  ΔE76 (Euclidean in Lab — cheap even in pure Python) before considering CIEDE2000.

Docstrings state *when to use which*, since keydaemon config authors pick a method
by name without reading the math:
- near-exact pixel check → `channel`, tight tolerance
- "does this area look roughly like X" → `euclidean` or `weighted`, looser tolerance
- matching a human-eyeballed reference color → `weighted`

## compare.py — flagship

```python
is_match(sample, target, tolerance=10, method="euclidean", aggregate="majority") -> bool
distances(sample, target, method="euclidean") -> float | list[float]
match_mask(sample, target, tolerance=10, method="euclidean") -> list[bool]
```

- `sample` / `target`: hex str or RGB tuple. `sample` may also be a collection of
  pixels — list of tuples, flat `(N, 3)` or image-shaped `(H, W, 3)` numpy array,
  or a PIL Image (duck-typed via `.getdata()`; no PIL import required).
- `aggregate` (region samples only): `"majority"` (default — more than half of
  pixels individually within tolerance), `"all"`, `"any"`, `"average"` (mean
  distance vs tolerance). Majority is the default because average lets a
  half-right/half-wildly-wrong region sneak under a loose tolerance, and majority
  is robust to icon edges/anti-aliasing while staying trivially explainable.
- `is_match` returns `bool`, always. `distances`/`match_mask` are the escape
  hatches for per-pixel inspection.

TOML maps 1:1 onto the signature, no translation layer:

```toml
[screen_check]
region = [100, 200, 50, 50]
expected_color = "#3B82F6"
method = "weighted"
tolerance = 25
```

## gradient.py

`build_gradient(color_a, color_b, steps, space="rgb") -> list[hex_str]` — evenly
spaced interpolation in RGB or HSL (HSL avoids the muddy middle on some pairs;
hue interpolates along the shorter arc). Pure `convert.py` reuse.

## cluster.py

`group_similar(colors, tolerance, method="euclidean") -> list[list[hex_str]]` —
greedy leader clustering: each color joins the first existing group whose leader
is within tolerance, else founds a new group. Greedy is the documented, honest
answer to non-transitivity (A≈B, B≈C, A≉C). Distance math comes from
`distance.py` only — one source of truth.

## extract.py (requires `[extract]`)

`dominant_color(image, k=3) -> list[hex_str]` — hand-rolled numpy k-means (no
sklearn, ever), clusters ordered largest-first:
- accepts file path, PIL Image, or numpy array (no disk round-trip for callers
  holding a screenshot)
- downsample before clustering (subsample pixels, don't cluster every pixel)
- assign/recompute steps are numpy broadcasting, no Python-level pixel loops
- iteration cap + convergence threshold; `k` small by default (2–4)

---

## Testing

- pytest, mirroring keydaemon's layout (`tests/test_convert.py`, `test_distance.py`, …).
- Distance properties per method: identity → 0, symmetry, black-vs-white → 100,
  known color pairs land in expected bands.
- Tolerance-scale regression tests: the *same* pair under different methods yields
  comparable magnitudes (the 0–100 normalization contract).
- Round-trip conversions (`hex → rgb → hex`), shorthand/edge-case parsing.
- Aggregates: constructed regions where majority/all/any/average disagree.
- Extract: synthetic images with known dominant colors; determinism via seeded init.

## Documentation

- Docstrings explain *why to pick a method*, not just types — the audience includes
  TOML authors who never read source.
- README + docs get a "which method / which tolerance / which aggregate" guide table.
- Future (not yet): browser-based interactive color-picker demo on the docs site —
  explicitly *instead of* a screen-picker in the Python GUI.

## Explicit Non-Goals (v1)

- No numpy in core. No sklearn anywhere, ever.
- No screen capture inside hextol — sampling the screen is keydaemon's job;
  hextol only judges colors it's handed.
- No delta_e until `weighted` proves insufficient in practice.
- No multi-frame features until single-frame primitives are solid — they must be
  thin compositions over v1 functions, not parallel implementations.
- No GUI screen-picker (docs-site demo instead).

---

## Build Order

1. **Core** — `convert.py` + `distance.py` + `compare.py` + tests + docstrings.
   Alone sufficient for keydaemon to adopt. → tag **v0.1.0**, publish to PyPI.
2. **Gradient** — `gradient.py`, cheap `convert.py` reuse.
3. **Extract** — `extract.py` + `[extract]` extra wiring in pyproject.
4. **Cluster** — `cluster.py` on top of `distance.py`.  → **v0.2.0**
5. **keydaemon integration** — swap `screen.py`'s hand-rolled `hex_to_rgb` /
   `color_matches` for hextol calls (`channel` method, per-channel semantics
   preserved); add region + method + tolerance support to its TOML schema.
6. **v2** — `matches_across(frames, target, tolerance, method, rule)` (time-axis
   twin of `is_match`), `dominant_color_multi(frames, k)` (pool pixels before
   clustering), `delta_e` if warranted.
7. **GUI** — tkinter app (`[gui]`): two color inputs + picker, method selector,
   tolerance slider, live match indicator, optional palette-from-image. A thin
   skin over the working library, built last.
