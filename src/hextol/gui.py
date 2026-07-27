"""Interactive explorers: tkinter visual aids for choosing a method and tolerance.

Never imported by ``import hextol``; run it explicitly::

    python -m hextol.gui        # or the installed command:  hextol-gui

Two pages, one per form of sample that ``is_match`` accepts, sharing one
tolerance slider:

**Color** takes two single colors and shows every distance method side by side
(normalized and raw values, plus a live match/miss verdict per method) so you
can see how ``channel``, ``euclidean``, and ``weighted`` judge the same pair
before committing one to a config file.

**Region** takes a rectangle of the screen (or an image file) and runs the
whole method x aggregate grid against a target color at once. It answers the
question a single-color comparison cannot: what does ``aggregate="majority"``
actually mean for *this* region, and how far apart do the four aggregates sit.

The core UI is standard library only (tkinter), and so is the region page's
analysis: a region is held as plain RGB tuples and judged by hextol itself, the
same values a caller would hand ``is_match``. Pillow (installed by the
``[extract]`` extra) is only ever the doorway, needed to sample the screen or to
read formats tkinter cannot; PNG and GIF load without it.
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, ttk
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

# Column order for the aggregates, loosest first. "any" passes whenever
# "majority" does, and "majority" whenever "all" does, so laid out this way a
# MATCH fills in from the left as the tolerance opens up and never leaves a
# gap. "average" sits apart at the end because it is the odd one out: it
# thresholds the mean distance instead of counting pixels, so it can break that
# run in either direction.
AGGREGATE_HINTS = {
    "any": "at least one pixel within",
    "majority": "over half the pixels within",
    "all": "every pixel within",
    "average": "mean dist within tolerance",
}

# The four aggregates read one or other of these two numbers, and nothing else.
COLUMN_HINTS = {
    "% within": "share of pixels individually within tolerance",
    "mean dist": "average distance over the whole region, 0-100",
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
FONT_SMALL = ("Segoe UI", 9)
FONT_HEAD = ("Segoe UI", 8, "bold")
FONT_MONO = ("Consolas", 11)
FONT_PAGE = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")

_GRADIENT_STEPS = 48
_GRADIENT_W = 740
_SWATCH_H = 150  # width follows the card, which the controls row underneath sets
_EMPTY = "-"

# Longest edge of the pixel grid the region page actually judges. Every distance
# is computed in pure Python, so this caps a tolerance drag at a few thousand
# comparisons per method instead of a few million.
_ANALYSIS_MAX = 96
_PREVIEW_W, _PREVIEW_H = 300, 210


def _enable_windows_dpi_awareness() -> None:
    """Make the process DPI-aware on Windows so tk windows use physical pixels.

    Without this, on a scaled display (125%, 150%, ...) the fullscreen frozen
    screenshot renders larger than the window and drifts away from the cursor.
    Safe no-op elsewhere, and harmless if awareness was already set.
    """
    import sys

    if sys.platform != "win32":
        return
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _configure_style(widget) -> None:
    """Apply the dark ttk styling. Idempotent, so every page may call it."""
    style = ttk.Style(widget)
    style.theme_use("clam")
    style.configure("TScale", troughcolor=FIELD, background=ACCENT,
                    bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)
    style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    font=FONT_BOLD, padding=(20, 8), borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACCENT)])


def _scaled_coords(image, x: int, y: int, shown_w: int, shown_h: int) -> tuple[int, int]:
    """Map a click at (x, y) on a shown_w x shown_h canvas onto ``image`` coords.

    Handles DPI scaling, where the screenshot's pixel size differs from the
    tkinter window's logical size. Clamped to the image bounds.
    """
    px = min(image.width - 1, max(0, int(x * image.width / max(1, shown_w))))
    py = min(image.height - 1, max(0, int(y * image.height / max(1, shown_h))))
    return px, py


def _padded(bbox, pad_x: int, pad_y: int):
    """Grow a canvas bbox outwards, for drawing a plate behind a text item."""
    return bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y


# --- region pixels ------------------------------------------------------------
# A region is a list of rows, each a list of (r, g, b) tuples. Nothing below
# needs Pillow, tkinter, or numpy: this is the same plain data a caller hands
# is_match, which is the point of the lab.

class Stats(NamedTuple):
    """Everything the aggregate verdicts for one method are derived from."""

    within: float                #: fraction of pixels individually within tolerance
    mean: float                  #: mean distance across the region, 0-100
    verdicts: dict[str, bool]    #: one entry per aggregate name


def region_stats(dists: list[float], tolerance: float) -> Stats:
    """Reduce one method's per-pixel distances to the four aggregate verdicts.

    Mirrors the aggregate rules in ``hextol.compare.is_match`` exactly (a test
    asserts the two agree for every aggregate). The lab derives them from a
    single cached distance pass instead of calling ``is_match`` four times, so
    dragging the tolerance slider stays responsive on a few thousand pixels.

    Note that ``majority``, ``all``, and ``any`` all threshold per pixel and
    then count, while ``average`` thresholds the mean once. That is why the
    first three always agree in order (``all`` implies ``majority`` implies
    ``any``) and ``average`` can break ranks in either direction.
    """
    n = len(dists)
    if not n:
        raise ValueError("Region is empty")
    within = sum(d <= tolerance for d in dists)
    mean = sum(dists) / n
    return Stats(
        within=within / n,
        mean=mean,
        verdicts={
            "majority": within * 2 > n,
            "all": within == n,
            "any": within > 0,
            "average": mean <= tolerance,
        },
    )


def _subsample(rows, limit: int = _ANALYSIS_MAX):
    """Thin a grid of pixels to at most ``limit`` on its longest edge.

    Picks real pixels (nearest neighbour) rather than averaging neighbours: a
    blended pixel is a color that was never on screen, and it would quietly
    change every distance in the table.
    """
    height = len(rows)
    width = len(rows[0]) if height else 0
    if not height or not width:
        raise ValueError("Region is empty")
    step = max(width, height) / limit
    if step <= 1:
        return rows
    new_h = max(1, int(height / step))
    new_w = max(1, int(width / step))
    return [
        [rows[y * height // new_h][x * width // new_w] for x in range(new_w)]
        for y in range(new_h)
    ]


def _rows_from_pil(image, limit: int = _ANALYSIS_MAX):
    """Convert a PIL image to rows of RGB tuples, downsampled first.

    Downsampling before ``getdata`` matters: a full-screen crop is millions of
    tuples, and we only ever judge a few thousand of them.
    """
    from PIL import Image

    width, height = image.size
    step = max(width, height) / limit
    if step > 1:
        image = image.resize(
            (max(1, int(width / step)), max(1, int(height / step))), Image.NEAREST
        )
    image = image.convert("RGB")
    flat = list(image.getdata())
    return [flat[y * image.width:(y + 1) * image.width] for y in range(image.height)]


def _photo_pixel(photo, x: int, y: int) -> tuple[int, int, int]:
    """Read one pixel from a tk.PhotoImage, tolerating both return shapes.

    Tk hands back either a tuple of ints or a "r g b" string depending on the
    build, and neither is documented as stable.
    """
    value = photo.get(x, y)
    if isinstance(value, str):
        value = value.split()
    return tuple(int(c) for c in value[:3])


def _rows_from_photo(photo, limit: int = _ANALYSIS_MAX):
    """Convert a tk.PhotoImage to rows of RGB tuples. No Pillow involved."""
    width, height = photo.width(), photo.height()
    step = int(max(width, height) / limit)
    if step > 1:
        photo = photo.subsample(step)
        width, height = photo.width(), photo.height()
    return [[_photo_pixel(photo, x, y) for x in range(width)] for y in range(height)]


def _rows_from_file(path: str, master):
    """Read an image file into rows of RGB tuples.

    Uses Pillow when it is installed. Without it tkinter still reads PNG and
    GIF natively, which keeps the region page usable on a zero-dependency
    install; anything else raises with the extra named.
    """
    try:
        from PIL import Image
    except ImportError:
        pass
    else:
        with Image.open(path) as image:
            return _rows_from_pil(image)
    if not path.lower().endswith((".png", ".gif")):
        raise ValueError(
            "Reading this format needs Pillow: pip install hextol[extract] "
            "(PNG and GIF load without it)"
        )
    return _rows_from_photo(tk.PhotoImage(master=master, file=path))


def _render_rows(master, rows, max_w: int, max_h: int):
    """Draw a grid of RGB tuples into a tk.PhotoImage, zoomed to fit a box.

    Pure tkinter: ``put`` takes a block of hex strings and ``zoom`` scales by
    whole pixels, so the preview never needs an image library.
    """
    height, width = len(rows), len(rows[0])
    photo = tk.PhotoImage(master=master, width=width, height=height)
    photo.put(" ".join("{" + " ".join(rgb_to_hex(*px) for px in row) + "}" for row in rows))
    zoom = max(1, min(max_w // width, max_h // height))
    return photo.zoom(zoom) if zoom > 1 else photo


# --- shared widgets -----------------------------------------------------------

def _page_header(parent, title: str, subtitle: str):
    frame = tk.Frame(parent, bg=BG)
    tk.Label(frame, text=title, font=FONT_PAGE, fg=TEXT, bg=BG).pack(side="left")
    tk.Label(frame, text="  " + subtitle, font=FONT_SMALL, fg=MUTED, bg=BG).pack(
        side="left", pady=(2, 0)
    )
    return frame


def _flat_button(parent, text: str, command, bg: str = FIELD):
    return tk.Button(parent, text=text, command=command, font=FONT, bg=bg, fg=TEXT,
                     activebackground=ACCENT, activeforeground=BG, relief="flat",
                     padx=10, cursor="hand2")


class _PickerMixin:
    """Color and region acquisition shared by both pages.

    Every route freezes the screen into one fullscreen overlay; only what the
    overlay does with the cursor differs, so the freeze itself lives here once.
    Pages must provide ``self.root`` and ``self.status``.
    """

    def _set_status(self, text: str = "") -> None:
        self.status.configure(text=text)

    def _require_pillow(self, what: str) -> bool:
        try:
            import PIL  # noqa: F401
        except ImportError:
            self._set_status(f"{what} needs Pillow: pip install hextol[extract]")
            return False
        return True

    def _pick_color(self, var: tk.StringVar) -> None:
        try:
            initial = rgb_to_hex(*to_rgb(var.get()))
        except ValueError:
            initial = None
        rgb, _ = colorchooser.askcolor(initialcolor=initial, parent=self.root)
        if rgb:
            var.set(rgb_to_hex(*(round(c) for c in rgb)))

    def _freeze(self, build) -> None:
        """Hide the app, grab the screen, and hand the overlay to ``build``."""
        self.root.withdraw()
        self.root.update()
        self.root.after(150, lambda: self._show_overlay(build))

    def _show_overlay(self, build) -> None:
        from PIL import ImageGrab, ImageTk

        shot = ImageGrab.grab()
        top = tk.Toplevel(self.root)
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        canvas = tk.Canvas(top, highlightthickness=0, bg="black")
        canvas.pack(fill="both", expand=True)
        # With DPI awareness the screenshot and window sizes agree; if they
        # still differ (fallback path), rescale the *display* copy to fit the
        # window while sampling stays on the full-resolution original.
        shown_w, shown_h = top.winfo_screenwidth(), top.winfo_screenheight()
        display = shot
        if (shot.width, shot.height) != (shown_w, shown_h):
            display = shot.resize((shown_w, shown_h))
        photo = ImageTk.PhotoImage(display)
        canvas._photo = photo  # keep a reference or tk garbage-collects it
        canvas.create_image(0, 0, image=photo, anchor="nw")

        def close(_event=None):
            top.destroy()
            self.root.deiconify()

        top.bind("<Escape>", close)
        top.bind("<Button-3>", close)
        build(canvas, shot, (shown_w, shown_h), close)
        top.after(100, top.focus_force)

    # --- point sampling -------------------------------------------------------

    def _pick_screen(self, var: tk.StringVar) -> None:
        """Freeze the screen and let the user click any pixel to sample it."""
        if not self._require_pillow("Screen picking"):
            return
        self._freeze(lambda *args: self._sample_pixel(var, *args))

    def _sample_pixel(self, var, canvas, shot, shown, close) -> None:
        from PIL import Image, ImageDraw, ImageTk

        shown_w, shown_h = shown
        canvas.configure(cursor="none")

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

        def physical(event):
            return _scaled_coords(shot, event.x, event.y, shown_w, shown_h)

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

            # loupe is centered on the cursor: the highlighted center cell IS
            # the pixel that a click samples
            lx, ly = event.x, event.y
            canvas.itemconfigure(loupe, image=zoom_photo)
            canvas.coords(loupe, lx, ly)
            canvas.coords(ring, lx - d / 2, ly - d / 2, lx + d / 2, ly + d / 2)
            s = scale / 2
            canvas.coords(center, lx - s, ly - s, lx + s, ly + s)
            label_y = ly + d / 2 + 16 if ly + d / 2 + 30 < shown_h else ly - d / 2 - 16
            canvas.coords(label, lx, label_y)
            canvas.itemconfigure(label, text=color)
            canvas.coords(label_bg, *_padded(canvas.bbox(label), 6, 3))
            canvas.tag_raise(label)

        def on_click(event):
            px, py = physical(event)
            var.set(rgb_to_hex(*shot.getpixel((px, py))[:3]))
            close()

        canvas.bind("<Motion>", on_move)
        canvas.bind("<Button-1>", on_click)


class ColorPage(_PickerMixin):
    """The single-color page. Builds itself into ``parent`` (a Tk root or frame)."""

    def __init__(self, parent, tolerance: tk.DoubleVar | None = None):
        self.root = parent.winfo_toplevel()
        _configure_style(self.root)

        # No sticky: when the parent gives its row and column weight (as the
        # notebook pages do) the page centers itself, so the shorter page does
        # not sit in a corner of the height the taller one demands.
        body = tk.Frame(parent, bg=BG, padx=24, pady=20)
        body.grid(row=0, column=0)
        self.frame = body

        _page_header(body, "color", "two colors, every distance method").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )

        # --- the two color cards -------------------------------------------
        cards = tk.Frame(body, bg=BG)
        cards.grid(row=1, column=0, columnspan=3, pady=(16, 0))
        self.color_vars = {}
        self.swatches = {}
        for col, side in ((0, "A"), (2, "B")):
            card = tk.Frame(cards, bg=PANEL, padx=10, pady=10,
                            highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=0, column=col)
            swatch = tk.Frame(card, height=_SWATCH_H, bg=FIELD)
            swatch.pack(fill="x")
            swatch.pack_propagate(False)
            self.swatches[side] = swatch
            controls = tk.Frame(card, bg=PANEL)
            controls.pack(fill="x", pady=(10, 0))
            tk.Label(controls, text=side, font=FONT_BOLD, fg=MUTED, bg=PANEL).pack(side="left")
            var = tk.StringVar(master=self.root,
                               value="#3B82F6" if side == "A" else "#2F7BEE")
            var.trace_add("write", lambda *_: self.refresh())
            self.color_vars[side] = var
            entry = tk.Entry(controls, textvariable=var, width=9, font=FONT_MONO,
                             bg=FIELD, fg=TEXT, insertbackground=ACCENT, relief="flat",
                             highlightthickness=1, highlightbackground=BORDER,
                             highlightcolor=ACCENT, justify="center")
            entry.pack(side="left", padx=8, ipady=3)
            for text, action in (("Pick", self._pick_color), ("Screen", self._pick_screen)):
                _flat_button(controls, text, lambda v=var, a=action: a(v)).pack(
                    side="left", padx=(0, 4)
                )
        tk.Label(cards, text="vs", font=FONT_BOLD, fg=MUTED, bg=BG).grid(
            row=0, column=1, padx=14
        )

        # --- gradient strip -------------------------------------------------
        self.gradient = tk.Canvas(body, width=_GRADIENT_W, height=30,
                                  highlightthickness=0, bg=BG)
        self.gradient.grid(row=2, column=0, columnspan=3, pady=(16, 0))

        # --- tolerance ------------------------------------------------------
        self.tolerance = tolerance if tolerance is not None else tk.DoubleVar(
            master=self.root, value=10
        )
        tol_row, self.tolerance_label = _tolerance_row(body, self.tolerance, self.refresh)
        tol_row.grid(row=3, column=0, columnspan=3, sticky="we", pady=(14, 0))

        # --- method table ---------------------------------------------------
        table = tk.Frame(body, bg=PANEL, padx=14, pady=10,
                         highlightbackground=BORDER, highlightthickness=1)
        table.grid(row=4, column=0, columnspan=3, pady=(16, 0), sticky="we")
        for col, (heading, width) in enumerate(
            (("method", 10), ("0-100", 7), ("raw", 7), ("verdict", 8), ("", 0))
        ):
            tk.Label(table, text=heading, font=FONT_HEAD, fg=MUTED,
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
            verdict = tk.Label(table, text=_EMPTY, font=FONT_SMALL, fg=MUTED,
                               bg=FIELD, width=8, pady=2)
            verdict.grid(row=r, column=3, padx=6)
            tk.Label(table, text=METHOD_HINTS[name], font=FONT_SMALL,
                     fg=MUTED, bg=PANEL, anchor="w").grid(row=r, column=4, padx=6, sticky="w")
            self.rows[name] = {"dist": dist, "raw": raw, "verdict": verdict}

        self.status = tk.Label(body, text="", font=FONT, fg=MISS_FG, bg=BG, anchor="w")
        self.status.grid(row=5, column=0, columnspan=3, sticky="we", pady=(10, 0))
        self.refresh()

    def refresh(self) -> None:
        """Recompute every readout from the current inputs. Safe to call any time."""
        tol = self.tolerance.get()
        self.tolerance_label.configure(text=f"{tol:.1f}")
        try:
            a = to_rgb(self.color_vars["A"].get())
            b = to_rgb(self.color_vars["B"].get())
        except ValueError:
            self._set_status("Invalid color: enter hex like #3B82F6")
            for row in self.rows.values():
                row["dist"].configure(text=_EMPTY)
                row["raw"].configure(text=_EMPTY)
                row["verdict"].configure(text=_EMPTY, bg=FIELD, fg=MUTED)
            return
        self._set_status()

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
            row = self.rows[name]
            row["dist"].configure(text=f"{d:.1f}")
            row["raw"].configure(text=f"{fn.raw(a, b):.1f}")
            _set_verdict(row["verdict"], d <= tol)


class RegionPage(_PickerMixin):
    """The region page: one region judged by every method and aggregate at once.

    The region itself is held as plain RGB tuples in ``self.pixels`` (rows of
    ``(r, g, b)``), never as an image object, so the analysis path is exactly
    what a caller would hand ``is_match``.
    """

    def __init__(self, parent, tolerance: tk.DoubleVar | None = None):
        self.root = parent.winfo_toplevel()
        _configure_style(self.root)

        self.pixels = None      # rows of (r, g, b), or None until a region is captured
        self.source = ""        # where the current region came from
        self._dists = {}        # (method, target) -> per-pixel distances

        # No sticky: when the parent gives its row and column weight (as the
        # notebook pages do) the page centers itself, so the shorter page does
        # not sit in a corner of the height the taller one demands.
        body = tk.Frame(parent, bg=BG, padx=24, pady=20)
        body.grid(row=0, column=0)
        self.frame = body

        _page_header(body, "region",
                     "one region, every method and aggregate").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        cards = tk.Frame(body, bg=BG)
        cards.grid(row=1, column=0, columnspan=2, pady=(16, 0), sticky="we")
        # Equal columns and sticky cards so the region and its target read as a
        # pair of same-sized boxes rather than two unrelated panels.
        cards.columnconfigure(0, weight=1, uniform="card")
        cards.columnconfigure(1, weight=1, uniform="card")

        # --- the region -----------------------------------------------------
        region_card = tk.Frame(cards, bg=PANEL, padx=10, pady=10,
                               highlightbackground=BORDER, highlightthickness=1)
        region_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        tk.Label(region_card, text="region", font=FONT_HEAD, fg=MUTED,
                 bg=PANEL, anchor="w").pack(fill="x", pady=(0, 6))
        self.preview = tk.Canvas(region_card, width=_PREVIEW_W, height=_PREVIEW_H,
                                 highlightthickness=0, bg=FIELD)
        self.preview.pack()
        buttons = tk.Frame(region_card, bg=PANEL)
        buttons.pack(fill="x", pady=(10, 0))
        _flat_button(buttons, "Capture region", self._capture_region).pack(
            side="left", padx=(0, 6)
        )
        _flat_button(buttons, "Load image", self._load_image).pack(side="left")
        self.region_info = tk.Label(region_card, text="", font=FONT_SMALL, fg=MUTED,
                                    bg=PANEL, anchor="w")
        self.region_info.pack(fill="x", pady=(8, 0))

        # --- the target -----------------------------------------------------
        target_card = tk.Frame(cards, bg=PANEL, padx=10, pady=10,
                               highlightbackground=BORDER, highlightthickness=1)
        target_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        tk.Label(target_card, text="target color", font=FONT_HEAD, fg=MUTED,
                 bg=PANEL, anchor="w").pack(fill="x", pady=(0, 6))
        self.swatch = tk.Frame(target_card, width=_PREVIEW_W, height=_PREVIEW_H, bg=FIELD)
        self.swatch.pack()
        self.swatch.pack_propagate(False)
        controls = tk.Frame(target_card, bg=PANEL)
        controls.pack(fill="x", pady=(10, 0))
        self.target = tk.StringVar(master=self.root, value="#3B82F6")
        self.target.trace_add("write", lambda *_: self.refresh())
        tk.Entry(controls, textvariable=self.target, width=9, font=FONT_MONO,
                 bg=FIELD, fg=TEXT, insertbackground=ACCENT, relief="flat",
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT, justify="center").pack(
            side="left", padx=(0, 8), ipady=3
        )
        for text, action in (("Pick", self._pick_color), ("Screen", self._pick_screen)):
            _flat_button(controls, text, lambda a=action: a(self.target)).pack(
                side="left", padx=(0, 4)
            )
        self.target_info = tk.Label(target_card, text="", font=FONT_SMALL, fg=MUTED,
                                    bg=PANEL, anchor="w")
        self.target_info.pack(fill="x", pady=(8, 0))

        # --- tolerance ------------------------------------------------------
        self.tolerance = tolerance if tolerance is not None else tk.DoubleVar(
            master=self.root, value=10
        )
        tol_row, self.tolerance_label = _tolerance_row(body, self.tolerance, self.refresh)
        tol_row.grid(row=2, column=0, columnspan=2, sticky="we", pady=(14, 0))

        # --- method x aggregate grid ----------------------------------------
        table = tk.Frame(body, bg=PANEL, padx=14, pady=10,
                         highlightbackground=BORDER, highlightthickness=1)
        table.grid(row=3, column=0, columnspan=2, pady=(16, 0), sticky="we")
        headings = [("method", 10), ("% within", 9), ("mean dist", 10)]
        headings += [(name, 9) for name in AGGREGATE_HINTS]
        for col, (heading, width) in enumerate(headings):
            tk.Label(table, text=heading, font=FONT_HEAD, fg=MUTED, bg=PANEL,
                     width=width, anchor="w" if col < 3 else "center").grid(
                row=0, column=col, padx=6, pady=(0, 2)
            )
        self.rows = {}
        for r, name in enumerate(METHODS, start=1):
            tk.Label(table, text=name, font=FONT_BOLD, fg=TEXT, bg=PANEL,
                     width=10, anchor="w").grid(row=r, column=0, padx=6, pady=4, sticky="w")
            within = tk.Label(table, text=_EMPTY, font=FONT_MONO, fg=TEXT, bg=PANEL,
                              width=7, anchor="w")
            within.grid(row=r, column=1, padx=6, sticky="w")
            mean = tk.Label(table, text=_EMPTY, font=FONT_MONO, fg=MUTED, bg=PANEL,
                            width=7, anchor="w")
            mean.grid(row=r, column=2, padx=6, sticky="w")
            verdicts = {}
            for col, aggregate in enumerate(AGGREGATE_HINTS, start=3):
                pill = tk.Label(table, text=_EMPTY, font=FONT_SMALL, fg=MUTED,
                                bg=FIELD, width=9, pady=2)
                pill.grid(row=r, column=col, padx=4, pady=2)
                verdicts[aggregate] = pill
            self.rows[name] = {"within": within, "mean": mean, "verdicts": verdicts}

        # Two legends, because the table is really two numbers and four readings
        # of them: the first line says what is measured, the second what each
        # aggregate demands of it.
        legends = tk.Frame(body, bg=BG)
        legends.grid(row=4, column=0, columnspan=2, sticky="we", pady=(8, 0))
        for hints in (COLUMN_HINTS, AGGREGATE_HINTS):
            text = "    ".join(f"{name}: {hint}" for name, hint in hints.items())
            tk.Label(legends, text=text, font=FONT_SMALL, fg=MUTED, bg=BG,
                     anchor="w").pack(fill="x", pady=1)

        self.status = tk.Label(body, text="", font=FONT, fg=MISS_FG, bg=BG, anchor="w")
        self.status.grid(row=5, column=0, columnspan=2, sticky="we", pady=(6, 0))

        self._draw_preview()
        self.refresh()

    # --- acquiring a region ---------------------------------------------------

    def set_region(self, pixels, source: str) -> None:
        """Adopt ``pixels`` (rows of RGB tuples) as the region under test.

        Subsamples to the analysis cap first, so callers may pass a grid of any
        size. This is the single entry point for every acquisition route, which
        is what lets the lab be driven headlessly in tests.
        """
        if not pixels or not pixels[0]:
            self._set_status("That selection was empty; nothing captured.")
            return
        self.pixels = _subsample(pixels)
        self.source = source
        self._dists.clear()
        self._draw_preview()
        self.refresh()

    def _capture_region(self) -> None:
        """Freeze the screen and drag out the rectangle to test."""
        if not self._require_pillow("Capturing a screen region"):
            return
        self._freeze(self._select_rect)

    def _select_rect(self, canvas, shot, shown, close) -> None:
        shown_w, shown_h = shown
        canvas.configure(cursor="crosshair")
        # Four shades around the selection: tk canvases cannot punch a hole in
        # one rectangle, so the unselected area is covered by its complement.
        shade = [canvas.create_rectangle(0, 0, 0, 0, fill=BG, outline="",
                                         stipple="gray50") for _ in range(4)]
        canvas.coords(shade[0], 0, 0, shown_w, shown_h)
        box = canvas.create_rectangle(0, 0, 0, 0, outline=ACCENT, width=2, state="hidden")
        readout = canvas.create_text(0, 0, text="", font=FONT_MONO, fill=TEXT,
                                     state="hidden")
        hint = canvas.create_text(
            shown_w / 2, 44, font=FONT, fill=TEXT,
            text="Drag a rectangle over the area to test. Esc or right-click cancels.",
        )
        hint_bg = canvas.create_rectangle(*_padded(canvas.bbox(hint), 14, 8),
                                          fill=BG, outline=BORDER)
        canvas.tag_raise(hint)
        anchor = {}

        def corners(event):
            x0, x1 = sorted((anchor["x"], event.x))
            y0, y1 = sorted((anchor["y"], event.y))
            return x0, y0, x1, y1

        def on_press(event):
            anchor["x"], anchor["y"] = event.x, event.y
            for item in (hint, hint_bg):
                canvas.itemconfigure(item, state="hidden")
            for item in (box, readout):
                canvas.itemconfigure(item, state="normal")

        def on_drag(event):
            if not anchor:
                return
            x0, y0, x1, y1 = corners(event)
            canvas.coords(box, x0, y0, x1, y1)
            canvas.coords(shade[0], 0, 0, shown_w, y0)
            canvas.coords(shade[1], 0, y1, shown_w, shown_h)
            canvas.coords(shade[2], 0, y0, x0, y1)
            canvas.coords(shade[3], x1, y0, shown_w, y1)
            canvas.coords(readout, (x0 + x1) / 2, min(y1 + 18, shown_h - 12))
            canvas.itemconfigure(readout, text=f"{x1 - x0} x {y1 - y0}")

        def on_release(event):
            if not anchor:
                return
            x0, y0, x1, y1 = corners(event)
            close()
            if x1 - x0 < 2 or y1 - y0 < 2:
                self._set_status("That selection was too small; nothing captured.")
                return
            px0, py0 = _scaled_coords(shot, x0, y0, shown_w, shown_h)
            px1, py1 = _scaled_coords(shot, x1, y1, shown_w, shown_h)
            crop = shot.crop((px0, py0, px1 + 1, py1 + 1))
            self.set_region(_rows_from_pil(crop), f"screen {crop.width} x {crop.height}")

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

    def _load_image(self) -> None:
        """Load a region from an image file, standing in for a screen grab."""
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Load a region",
            filetypes=[("Images", "*.png *.gif *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            pixels = _rows_from_file(path, self.root)
        except Exception as exc:
            self._set_status(f"Could not read that image: {exc}")
            return
        self.set_region(pixels, f"file {Path(path).name}")

    # --- rendering ------------------------------------------------------------

    def _draw_preview(self) -> None:
        self.preview.delete("all")
        if self.pixels is None:
            self.preview.create_text(_PREVIEW_W / 2, _PREVIEW_H / 2, font=FONT, fill=MUTED,
                                     text="capture a region or load an image")
            self.region_info.configure(text="no region yet")
            return
        photo = _render_rows(self.root, self.pixels, _PREVIEW_W - 8, _PREVIEW_H - 8)
        self.preview._photo = photo  # keep a reference or tk garbage-collects it
        self.preview.create_image(_PREVIEW_W / 2, _PREVIEW_H / 2, image=photo)
        height, width = len(self.pixels), len(self.pixels[0])
        self.region_info.configure(
            text=f"{self.source}, judging {width} x {height} = {width * height} pixels"
        )

    def _distances(self, method: str, target) -> list[float]:
        """Per-pixel distances for one method, cached until the region changes.

        Moving the tolerance slider does not invalidate this: tolerance is a
        threshold applied after the fact, never an input to the distance.
        """
        key = (method, target)
        cached = self._dists.get(key)
        if cached is None:
            if len(self._dists) > 9:  # a long picking session, not a leak
                self._dists.clear()
            fn = METHODS[method]
            cached = [fn(px, target) for row in self.pixels for px in row]
            self._dists[key] = cached
        return cached

    def _clear_table(self) -> None:
        for row in self.rows.values():
            row["within"].configure(text=_EMPTY)
            row["mean"].configure(text=_EMPTY)
            for pill in row["verdicts"].values():
                pill.configure(text=_EMPTY, bg=FIELD, fg=MUTED)

    def refresh(self) -> None:
        """Recompute every readout from the current inputs. Safe to call any time."""
        tol = self.tolerance.get()
        self.tolerance_label.configure(text=f"{tol:.1f}")
        try:
            target = to_rgb(self.target.get())
        except ValueError:
            self._set_status("Invalid color: enter hex like #3B82F6")
            self.target_info.configure(text="")
            self._clear_table()
            return
        self.swatch.configure(bg=rgb_to_hex(*target))
        self.target_info.configure(text="rgb{}".format(target))
        if self.pixels is None:
            self._set_status()
            self._clear_table()
            return
        self._set_status()
        for name in METHODS:
            stats = region_stats(self._distances(name, target), tol)
            row = self.rows[name]
            row["within"].configure(text=f"{stats.within * 100:.0f}%")
            row["mean"].configure(text=f"{stats.mean:.1f}")
            for aggregate, pill in row["verdicts"].items():
                _set_verdict(pill, stats.verdicts[aggregate])


def _tolerance_row(parent, variable: tk.DoubleVar, on_change):
    """Build the shared tolerance slider; returns ``(row_frame, readout_label)``.

    The callback hangs off the variable rather than the scale so that both
    pages update when either one is dragged.
    """
    row = tk.Frame(parent, bg=BG)
    tk.Label(row, text="tolerance", font=FONT, fg=MUTED, bg=BG).pack(side="left")
    ttk.Scale(row, from_=0, to=100, variable=variable, length=420).pack(
        side="left", padx=12, fill="x", expand=True
    )
    label = tk.Label(row, text="10.0", font=FONT_MONO, fg=ACCENT, bg=BG, width=5)
    label.pack(side="left")
    variable.trace_add("write", lambda *_: on_change())
    return row, label


def _set_verdict(label: tk.Label, matched: bool) -> None:
    label.configure(
        text="MATCH" if matched else "MISS",
        bg=MATCH_BG if matched else MISS_BG,
        fg=MATCH_FG if matched else MISS_FG,
    )


def main() -> None:
    """Launch the explorer window."""
    _enable_windows_dpi_awareness()  # must happen before the Tk root exists
    root = tk.Tk()
    root.title("hextol")
    root.configure(bg=BG)
    root.resizable(False, False)
    _configure_style(root)

    header = tk.Frame(root, bg=BG, padx=24, pady=14)
    header.grid(row=0, column=0, sticky="w")
    tk.Label(header, text="hextol", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(side="left")
    tk.Label(header, text="  comparison explorer", font=FONT,
             fg=MUTED, bg=BG).pack(side="left", pady=(6, 0))

    tolerance = tk.DoubleVar(master=root, value=10)
    notebook = ttk.Notebook(root)
    notebook.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 14))
    for title, page_class in (("Color", ColorPage), ("Region", RegionPage)):
        page = tk.Frame(notebook, bg=BG)
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1)
        notebook.add(page, text=title)
        page_class(page, tolerance=tolerance)

    root.mainloop()


if __name__ == "__main__":
    main()
