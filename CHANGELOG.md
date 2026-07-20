# Changelog

<!--next-version-placeholder-->

## Unreleased

- `hextol.gradient.build_gradient(color_a, color_b, steps, space)` — ordered
  hex ramps in RGB or HSL space (HSL interpolates hue along the shorter arc).

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
