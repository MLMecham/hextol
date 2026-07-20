# Changelog

<!--next-version-placeholder-->

## Unreleased

- `hextol.gui` + `hextol-gui` command: tkinter comparison explorer. Pick two
  colors, drag a tolerance slider, and watch all three methods judge the pair
  side by side (normalized + raw distances, live match/miss verdicts, gradient
  strip). Dark theme matching the hextol branding. Never imported by
  `import hextol`; core UI is stdlib-only.
- Screen picker in the explorer (needs Pillow): freeze-frame screenshot with a
  magnifier loupe (pixel grid, center highlight, live hex badge); click to
  sample, Esc or right-click to cancel.

## v0.2.0 (19/07/2026)

- `hextol.gradient.build_gradient(color_a, color_b, steps, space)` — ordered
  hex ramps in RGB or HSL space (HSL interpolates hue along the shorter arc).
- `hextol.extract.dominant_color(image, k)` — dominant colors via hand-rolled
  numpy k-means, largest cluster first; accepts file paths, PIL Images, and
  numpy arrays; subsamples large inputs; deterministic by default (`seed=0`).
  Requires the new `[extract]` extra (numpy + Pillow). `[all]` extra added.
- `hextol.cluster.group_similar(colors, tolerance, method)` — tolerance-based
  dedupe via greedy leader clustering; luminance-sorted input makes results
  order-independent; no chaining through intermediate colors. Zero-dep.

## v0.1.0 (19/07/2026)

Phase 1 of PLAN.md — the zero-dependency comparison core:

- `hextol.is_match(sample, target, tolerance, method, aggregate)` — flagship
  comparison; single colors and regions, always returns `bool`.
- `hextol.compare.distances` / `match_mask` — per-pixel detail;
  `distances(normalize=False)` returns raw method values.
- `hextol.distance` — `channel`, `euclidean`, `weighted` (redmean), all
  normalized to a shared 0–100 scale; raw formulas at `<method>.raw`.
- `hextol.convert` — hex ↔ RGB ↔ HSL, CSS shorthand (`#3BF`) support.
- Samples duck-type PIL Images and numpy arrays without importing either.

## v0.0.1 (19/07/2026)

- Project scaffolding for `hextol` — package renamed out of the template stage.
