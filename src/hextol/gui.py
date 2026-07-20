"""Interactive comparison explorer — a tkinter visual aid for choosing a method.

Never imported by ``import hextol``; run it explicitly::

    python -m hextol.gui        # or the installed command:  hextol-gui

Pick two colors and drag the tolerance slider: every distance method is shown
side by side — normalized (0-100) and raw values, plus a live match/miss
verdict per method — so you can see how ``channel``, ``euclidean``, and
``weighted`` judge the same pair before committing one to a config file.

Uses only the standard library (tkinter); the ``[gui]`` extra is a marker.
"""
from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import colorchooser, ttk
except ImportError:  # pragma: no cover
    raise ImportError(
        "hextol.gui requires tkinter, which ships with most Python installs "
        "but may need a system package (e.g. python3-tk on Debian/Ubuntu)"
    ) from None

from hextol.convert import rgb_to_hex, to_rgb
from hextol.distance import METHODS
from hextol.gradient import build_gradient

METHOD_HINTS = {
    "channel": "strictest — the worst channel alone decides; near-exact checks",
    "euclidean": "straight line in RGB; the general-purpose default",
    "weighted": "redmean, perceptual — best for human-picked reference colors",
}

_GRADIENT_STEPS = 32
_MATCH_BG = "#B7E1C0"
_MISS_BG = "#F2B8B5"


class ComparisonApp:
    """The explorer window. Instantiate with a ``tk.Tk`` root, then ``mainloop``."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("hextol — comparison explorer")
        root.resizable(False, False)
        body = ttk.Frame(root, padding=12)
        body.grid(sticky="nsew")

        self.color_vars = {}
        self.swatches = {}
        for row, side in enumerate(("A", "B")):
            ttk.Label(body, text=f"Color {side}").grid(row=row, column=0, sticky="w")
            var = tk.StringVar(value="#3B82F6" if side == "A" else "#2F7BEE")
            var.trace_add("write", lambda *_: self.refresh())
            self.color_vars[side] = var
            ttk.Entry(body, textvariable=var, width=10).grid(row=row, column=1, padx=4)
            ttk.Button(
                body, text="Pick…", command=lambda s=side: self._pick(s)
            ).grid(row=row, column=2, padx=2)
            swatch = tk.Frame(body, width=60, height=24, relief="sunken", borderwidth=1)
            swatch.grid(row=row, column=3, padx=6, sticky="w")
            self.swatches[side] = swatch

        ttk.Label(body, text="Between them").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.gradient = tk.Canvas(body, width=320, height=24, highlightthickness=0)
        self.gradient.grid(row=2, column=1, columnspan=3, pady=(10, 0), sticky="w")

        ttk.Label(body, text="Tolerance").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.tolerance = tk.DoubleVar(value=10)
        ttk.Scale(
            body, from_=0, to=100, variable=self.tolerance,
            command=lambda *_: self.refresh(), length=260,
        ).grid(row=3, column=1, columnspan=2, pady=(10, 0), sticky="w")
        self.tolerance_label = ttk.Label(body, text="10.0")
        self.tolerance_label.grid(row=3, column=3, pady=(10, 0), sticky="w")

        table = ttk.Frame(body)
        table.grid(row=4, column=0, columnspan=4, pady=(12, 0), sticky="w")
        for col, heading in enumerate(("method", "distance (0-100)", "raw", "verdict")):
            ttk.Label(table, text=heading, font=("TkDefaultFont", 9, "bold")).grid(
                row=0, column=col, padx=6, sticky="w"
            )
        self.rows = {}
        for r, name in enumerate(METHODS, start=1):
            ttk.Label(table, text=name).grid(row=r, column=0, padx=6, sticky="w")
            dist = ttk.Label(table, text="—", width=14)
            dist.grid(row=r, column=1, padx=6, sticky="w")
            raw = ttk.Label(table, text="—", width=8)
            raw.grid(row=r, column=2, padx=6, sticky="w")
            verdict = tk.Label(table, text="—", width=7)
            verdict.grid(row=r, column=3, padx=6)
            ttk.Label(table, text=METHOD_HINTS[name], foreground="#666666").grid(
                row=r, column=4, padx=6, sticky="w"
            )
            self.rows[name] = {"dist": dist, "raw": raw, "verdict": verdict}

        self.status = ttk.Label(body, text="", foreground="#B3261E")
        self.status.grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.refresh()

    def _pick(self, side: str) -> None:
        current = self.color_vars[side].get()
        try:
            initial = rgb_to_hex(*to_rgb(current))
        except ValueError:
            initial = None
        rgb, _ = colorchooser.askcolor(initialcolor=initial, parent=self.root)
        if rgb:
            self.color_vars[side].set(rgb_to_hex(*(round(c) for c in rgb)))

    def refresh(self) -> None:
        """Recompute every readout from the current inputs. Safe to call any time."""
        tol = self.tolerance.get()
        self.tolerance_label.configure(text=f"{tol:.1f}")
        try:
            a = to_rgb(self.color_vars["A"].get())
            b = to_rgb(self.color_vars["B"].get())
        except ValueError:
            self.status.configure(text="Invalid color — enter hex like #3B82F6")
            for row in self.rows.values():
                row["dist"].configure(text="—")
                row["raw"].configure(text="—")
                row["verdict"].configure(text="—", bg=self.root.cget("bg"))
            return
        self.status.configure(text="")

        self.swatches["A"].configure(bg=rgb_to_hex(*a))
        self.swatches["B"].configure(bg=rgb_to_hex(*b))

        self.gradient.delete("all")
        width = int(self.gradient.cget("width"))
        cell = width / _GRADIENT_STEPS
        for i, color in enumerate(build_gradient(a, b, _GRADIENT_STEPS)):
            self.gradient.create_rectangle(
                i * cell, 0, (i + 1) * cell, 24, fill=color, outline=""
            )

        for name, fn in METHODS.items():
            d = fn(a, b)
            matched = d <= tol
            row = self.rows[name]
            row["dist"].configure(text=f"{d:.1f}")
            row["raw"].configure(text=f"{fn.raw(a, b):.1f}")
            row["verdict"].configure(
                text="MATCH" if matched else "MISS",
                bg=_MATCH_BG if matched else _MISS_BG,
            )


def main() -> None:
    """Launch the comparison explorer window."""
    root = tk.Tk()
    ComparisonApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
