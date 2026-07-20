"""Interactive comparison explorer: a tkinter visual aid for choosing a method.

Never imported by ``import hextol``; run it explicitly::

    python -m hextol.gui        # or the installed command:  hextol-gui

Pick two colors and drag the tolerance slider: every distance method is shown
side by side (normalized and raw values, plus a live match/miss verdict per
method) so you can see how ``channel``, ``euclidean``, and ``weighted`` judge
the same pair before committing one to a config file.

The core UI is standard library only (tkinter); the "Screen" buttons
additionally need Pillow (installed by the ``[extract]`` extra) and freeze a
screenshot so you can click any pixel on screen to sample its color.
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
    "channel": "strictest: the worst channel alone decides",
    "euclidean": "straight line in RGB; general-purpose default",
    "weighted": "redmean, perceptual; best for human-picked colors",
}

# Palette: dark navy + teal, matching the hextol branding.
BG = "#0F1526"
PANEL = "#1A2138"
FIELD = "#232B45"
BORDER = "#2E3854"
TEXT = "#E6EAF2"
MUTED = "#8B93A7"
ACCENT = "#2DD4BF"
MATCH_BG, MATCH_FG = "#123B2E", "#4ADE80"
MISS_BG, MISS_FG = "#3F1D25", "#F87171"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas", 11)
FONT_TITLE = ("Segoe UI", 16, "bold")

_GRADIENT_STEPS = 48
_SWATCH_W, _SWATCH_H = 190, 110
_EMPTY = "-"


def _scaled_coords(image, x: int, y: int, shown_w: int, shown_h: int) -> tuple[int, int]:
    """Map a click at (x, y) on a shown_w x shown_h canvas onto ``image`` coords.

    Handles DPI scaling, where the screenshot's pixel size differs from the
    tkinter window's logical size. Clamped to the image bounds.
    """
    px = min(image.width - 1, max(0, int(x * image.width / max(1, shown_w))))
    py = min(image.height - 1, max(0, int(y * image.height / max(1, shown_h))))
    return px, py


class ComparisonApp:
    """The explorer window. Instantiate with a ``tk.Tk`` root, then ``mainloop``."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("hextol comparison explorer")
        root.configure(bg=BG)
        root.resizable(False, False)

        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TScale", troughcolor=FIELD, background=ACCENT,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)

        body = tk.Frame(root, bg=BG, padx=24, pady=20)
        body.grid(sticky="nsew")

        header = tk.Frame(body, bg=BG)
        header.grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(header, text="hextol", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(header, text="  comparison explorer", font=FONT,
                 fg=MUTED, bg=BG).pack(side="left", pady=(6, 0))

        # --- the two color cards -------------------------------------------
        cards = tk.Frame(body, bg=BG)
        cards.grid(row=1, column=0, columnspan=3, pady=(16, 0))
        self.color_vars = {}
        self.swatches = {}
        for col, side in ((0, "A"), (2, "B")):
            card = tk.Frame(cards, bg=PANEL, padx=10, pady=10,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=col)
            swatch = tk.Frame(card, width=_SWATCH_W, height=_SWATCH_H, bg=FIELD)
            swatch.pack()
            swatch.pack_propagate(False)
            self.swatches[side] = swatch
            controls = tk.Frame(card, bg=PANEL)
            controls.pack(fill="x", pady=(10, 0))
            tk.Label(controls, text=side, font=FONT_BOLD, fg=MUTED, bg=PANEL).pack(side="left")
            var = tk.StringVar(value="#3B82F6" if side == "A" else "#2F7BEE")
            var.trace_add("write", lambda *_: self.refresh())
            self.color_vars[side] = var
            entry = tk.Entry(controls, textvariable=var, width=9, font=FONT_MONO,
                             bg=FIELD, fg=TEXT, insertbackground=ACCENT, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER,
                             highlightcolor=ACCENT, justify="center")
            entry.pack(side="left", padx=8, ipady=3)
            for label, command in (("Pick", self._pick), ("Screen", self._pick_screen)):
                tk.Button(controls, text=label,
                          command=lambda s=side, c=command: c(s),
                          font=FONT, bg=FIELD, fg=TEXT, activebackground=ACCENT,
                          activeforeground=BG, relief="flat", padx=10,
                          cursor="hand2").pack(side="left", padx=(0, 4))
        tk.Label(cards, text="vs", font=FONT_BOLD, fg=MUTED, bg=BG).grid(
            row=0, column=1, padx=14
        )

        # --- gradient strip -------------------------------------------------
        self.gradient = tk.Canvas(body, width=560, height=30, highlightthickness=0, bg=BG)
        self.gradient.grid(row=2, column=0, columnspan=3, pady=(16, 0))

        # --- tolerance ------------------------------------------------------
        tol_row = tk.Frame(body, bg=BG)
        tol_row.grid(row=3, column=0, columnspan=3, sticky="we", pady=(14, 0))
        tk.Label(tol_row, text="tolerance", font=FONT, fg=MUTED, bg=BG).pack(side="left")
        self.tolerance = tk.DoubleVar(value=10)
        ttk.Scale(tol_row, from_=0, to=100, variable=self.tolerance,
                  command=lambda *_: self.refresh(), length=420).pack(
            side="left", padx=12, fill="x", expand=True
        )
        self.tolerance_label = tk.Label(tol_row, text="10.0", font=FONT_MONO,
                                        fg=ACCENT, bg=BG, width=5)
        self.tolerance_label.pack(side="left")

        # --- method table ---------------------------------------------------
        table = tk.Frame(body, bg=PANEL, padx=14, pady=10,
                         highlightbackground=BORDER, highlightthickness=1)
        table.grid(row=4, column=0, columnspan=3, pady=(16, 0), sticky="we")
        for col, (heading, width) in enumerate(
            (("method", 10), ("0-100", 7), ("raw", 7), ("verdict", 8), ("", 0))
        ):
            tk.Label(table, text=heading, font=("Segoe UI", 8, "bold"), fg=MUTED,
                     bg=PANEL, width=width or None, anchor="w").grid(
                row=0, column=col, padx=6, sticky="w"
            )
        self.rows = {}
        for r, name in enumerate(METHODS, start=1):
            tk.Label(table, text=name, font=FONT_BOLD, fg=TEXT, bg=PANEL,
                     width=10, anchor="w").grid(row=r, column=0, padx=6, pady=4, sticky="w")
            dist = tk.Label(table, text=_EMPTY, font=FONT_MONO, fg=TEXT, bg=PANEL,
                            width=7, anchor="w")
            dist.grid(row=r, column=1, padx=6, sticky="w")
            raw = tk.Label(table, text=_EMPTY, font=FONT_MONO, fg=MUTED, bg=PANEL,
                           width=7, anchor="w")
            raw.grid(row=r, column=2, padx=6, sticky="w")
            verdict = tk.Label(table, text=_EMPTY, font=("Segoe UI", 9, "bold"),
                               fg=MUTED, bg=FIELD, width=8, pady=2)
            verdict.grid(row=r, column=3, padx=6)
            tk.Label(table, text=METHOD_HINTS[name], font=("Segoe UI", 9),
                     fg=MUTED, bg=PANEL, anchor="w").grid(row=r, column=4, padx=6, sticky="w")
            self.rows[name] = {"dist": dist, "raw": raw, "verdict": verdict}

        self.status = tk.Label(body, text="", font=FONT, fg=MISS_FG, bg=BG, anchor="w")
        self.status.grid(row=5, column=0, columnspan=3, sticky="we", pady=(10, 0))
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

    def _pick_screen(self, side: str) -> None:
        """Freeze the screen and let the user click any pixel to sample it.

        Click to sample, Esc or right-click to cancel. Needs Pillow.
        """
        try:
            from PIL import ImageGrab, ImageTk
        except ImportError:
            self.status.configure(
                text="Screen picking needs Pillow: pip install hextol[extract]"
            )
            return
        self.root.withdraw()
        self.root.update()
        self.root.after(150, lambda: self._grab_and_show(side, ImageGrab, ImageTk))

    def _grab_and_show(self, side: str, ImageGrab, ImageTk) -> None:
        from PIL import Image, ImageDraw

        shot = ImageGrab.grab()
        top = tk.Toplevel(self.root)
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        canvas = tk.Canvas(top, cursor="none", highlightthickness=0, bg="black")
        canvas.pack(fill="both", expand=True)
        photo = ImageTk.PhotoImage(shot)
        canvas._photo = photo  # keep a reference or tk garbage-collects it
        canvas.create_image(0, 0, image=photo, anchor="nw")

        # Magnifier loupe: a circular, pixel-gridded zoom around the cursor.
        src = 11        # source pixels across the loupe
        scale = 12      # display pixels per source pixel
        d = src * scale
        half = src // 2
        mask = Image.new("L", (d, d), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
        loupe = canvas.create_image(0, 0)
        ring = canvas.create_oval(0, 0, 0, 0, outline=TEXT, width=2)
        center = canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT, width=2)
        label_bg = canvas.create_rectangle(0, 0, 0, 0, fill=BG, outline=BORDER)
        label = canvas.create_text(0, 0, text="", font=FONT_MONO, fill=TEXT)

        def close(_event=None):
            top.destroy()
            self.root.deiconify()

        def physical(event):
            return _scaled_coords(
                shot, event.x, event.y, canvas.winfo_width(), canvas.winfo_height()
            )

        def on_move(event):
            px, py = physical(event)
            color = rgb_to_hex(*shot.getpixel((px, py))[:3])
            region = shot.crop((px - half, py - half, px - half + src, py - half + src))
            zoom = region.resize((d, d), Image.NEAREST).convert("RGBA")
            grid = ImageDraw.Draw(zoom)
            for i in range(scale, d, scale):
                grid.line((i, 0, i, d), fill=(255, 255, 255, 40))
                grid.line((0, i, d, i), fill=(255, 255, 255, 40))
            zoom.putalpha(mask)
            zoom_photo = ImageTk.PhotoImage(zoom)
            canvas._zoom_photo = zoom_photo

            # keep the loupe on-screen: flip to the other side near edges
            w, h = canvas.winfo_width(), canvas.winfo_height()
            lx = event.x + 100 if event.x + 100 + d / 2 < w else event.x - 100
            ly = event.y + 100 if event.y + 100 + d / 2 + 30 < h else event.y - 100
            canvas.itemconfigure(loupe, image=zoom_photo)
            canvas.coords(loupe, lx, ly)
            canvas.coords(ring, lx - d / 2, ly - d / 2, lx + d / 2, ly + d / 2)
            s = scale / 2
            canvas.coords(center, lx - s, ly - s, lx + s, ly + s)
            canvas.coords(label, lx, ly + d / 2 + 16)
            canvas.itemconfigure(label, text=color)
            bbox = canvas.bbox(label)
            canvas.coords(label_bg, bbox[0] - 6, bbox[1] - 3, bbox[2] + 6, bbox[3] + 3)
            canvas.tag_raise(label)

        def on_click(event):
            px, py = physical(event)
            self.color_vars[side].set(rgb_to_hex(*shot.getpixel((px, py))[:3]))
            close()

        canvas.bind("<Motion>", on_move)
        canvas.bind("<Button-1>", on_click)
        top.bind("<Escape>", close)
        top.bind("<Button-3>", close)
        top.after(100, top.focus_force)

    def refresh(self) -> None:
        """Recompute every readout from the current inputs. Safe to call any time."""
        tol = self.tolerance.get()
        self.tolerance_label.configure(text=f"{tol:.1f}")
        try:
            a = to_rgb(self.color_vars["A"].get())
            b = to_rgb(self.color_vars["B"].get())
        except ValueError:
            self.status.configure(text="Invalid color: enter hex like #3B82F6")
            for row in self.rows.values():
                row["dist"].configure(text=_EMPTY)
                row["raw"].configure(text=_EMPTY)
                row["verdict"].configure(text=_EMPTY, bg=FIELD, fg=MUTED)
            return
        self.status.configure(text="")

        self.swatches["A"].configure(bg=rgb_to_hex(*a))
        self.swatches["B"].configure(bg=rgb_to_hex(*b))

        self.gradient.delete("all")
        width = int(self.gradient.cget("width"))
        height = int(self.gradient.cget("height"))
        cell = width / _GRADIENT_STEPS
        for i, color in enumerate(build_gradient(a, b, _GRADIENT_STEPS)):
            self.gradient.create_rectangle(
                i * cell, 0, (i + 1) * cell, height, fill=color, outline=""
            )

        for name, fn in METHODS.items():
            d = fn(a, b)
            matched = d <= tol
            row = self.rows[name]
            row["dist"].configure(text=f"{d:.1f}")
            row["raw"].configure(text=f"{fn.raw(a, b):.1f}")
            row["verdict"].configure(
                text="MATCH" if matched else "MISS",
                bg=MATCH_BG if matched else MISS_BG,
                fg=MATCH_FG if matched else MISS_FG,
            )


def main() -> None:
    """Launch the comparison explorer window."""
    root = tk.Tk()
    ComparisonApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
