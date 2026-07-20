# hextol

**Hexadecimal tolerance** — compare colors within a tolerance. Built as a
zero-dependency support package for
[KeyDaemon](https://mlmecham.github.io/keydeamon/), and for anywhere else hex
values need comparing.

## Install

```bash
pip install hextol          # color/region comparison — zero dependencies
```

## Quick start

```python
from hextol import is_match

# single colors — hex strings and RGB tuples mix freely
is_match("#3B82F6", (59, 128, 240), tolerance=10)            # True

# a perceptual method for human-picked reference colors
is_match("#3B82F6", "#2F7BEE", tolerance=10, method="weighted")

# whole regions (list of pixels, PIL Image, or numpy array)
pixels = [(58, 129, 245), (60, 131, 247), (10, 10, 10)]
is_match(pixels, "#3B82F6", tolerance=10, aggregate="majority")
```

`tolerance` is on a normalized **0–100 scale** under every method — 0 passes
only exact matches, 100 passes anything, and switching `method` doesn't require
re-tuning the number.

## Which method, which tolerance?

| Situation | method | tolerance |
|---|---|---|
| Near-exact pixel check | `"channel"` | 1–5 |
| "Does this look roughly like X" | `"euclidean"` | 10–25 |
| Matching a human-picked color | `"weighted"` | 10–25 |

Need raw (unnormalized) distances? `hextol.compare.distances(..., normalize=False)`
or `hextol.distance.euclidean.raw(a, b)`.

## Development install

```bash
git clone https://github.com/MLMecham/hextol
cd hextol
uv sync --extra dev
uv run pytest
```
