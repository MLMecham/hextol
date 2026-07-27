# Changelog

<!--next-version-placeholder-->

## Unreleased

- `hextol.gui` + `hextol-gui` command: tkinter comparison explorer, now two
  tabs sharing one tolerance slider, one per form of sample `is_match` accepts.
  Dark theme matching the hextol branding. Never imported by `import hextol`;
  core UI is stdlib-only.
- **Color** tab: pick two colors, drag the tolerance slider, and watch all
  three methods judge the pair side by side (normalized + raw distances, live
  match/miss verdicts, gradient strip).
- **Region** tab: capture a screen rectangle or load an image, then read the
  whole method x aggregate grid at once against a target color. Shows the two
  numbers every verdict derives from (share of pixels individually within
  tolerance, and mean distance), with aggregate columns ordered loosest first
  so a MATCH fills in from the left. A region is held as plain RGB tuples and
  judged by hextol itself, so the analysis path needs no extras; PNG and GIF
  load through tkinter alone.
- Screen picker in the explorer (needs Pillow): freeze-frame screenshot with a
  magnifier loupe (pixel grid, center highlight, live hex badge); click to
  sample, Esc or right-click to cancel. Region capture reuses the same freeze
  with a drag-out rectangle and dimmed surroundings.

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
