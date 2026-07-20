# hextol

**Hexadecimal tolerance** — compare colors within a tolerance.

Support package for the epic [KeyDaemon](https://mlmecham.github.io/keydeamon/) — and for anywhere else hex values need comparing. Zero dependencies.

```python
from hextol import is_match

is_match("#3B82F6", (59, 128, 240), tolerance=10)                 # single colors
is_match(pixels, "#3B82F6", tolerance=10, aggregate="majority")   # whole regions
```

`tolerance` lives on a normalized 0–100 scale under every distance method
(`channel`, `euclidean`, `weighted`/redmean), so configs can switch methods
without re-tuning. Raw distances stay available via
`hextol.compare.distances(..., normalize=False)` or `hextol.distance.<method>.raw`.

## Install

```bash
pip install hextol            # comparison core — zero dependencies
pip install hextol[extract]   # + dominant-color extraction (numpy, Pillow)
```

## Development

```bash
git clone https://github.com/MLMecham/hextol
cd hextol
uv sync --extra dev
uv run pytest
```

## Docs

https://mlmecham.github.io/hextol — full API reference and a method/tolerance guide.

See `PLAN.md` for the roadmap (gradients, palette extraction, clustering, GUI).
