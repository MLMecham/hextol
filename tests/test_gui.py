import subprocess
import sys

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


class TestColorPage:
    def test_builds_and_shows_all_methods(self, root):
        from hextol.distance import METHODS
        from hextol.gui import ColorPage

        app = ColorPage(root)
        assert set(app.rows) == set(METHODS)

    def test_refresh_computes_verdicts(self, root):
        from hextol.gui import ColorPage

        app = ColorPage(root)
        app.color_vars["A"].set("#000000")
        app.color_vars["B"].set("#000000")
        app.tolerance.set(0)
        app.refresh()
        assert all(row["verdict"].cget("text") == "MATCH" for row in app.rows.values())

        app.color_vars["B"].set("#FFFFFF")
        app.refresh()
        assert all(row["verdict"].cget("text") == "MISS" for row in app.rows.values())
        assert all(row["dist"].cget("text") == "100.0" for row in app.rows.values())

    def test_invalid_hex_shows_status_not_crash(self, root):
        from hextol.gui import ColorPage

        app = ColorPage(root)
        app.color_vars["A"].set("#NOTHEX")
        app.refresh()
        assert "Invalid" in app.status.cget("text")
        assert all(row["verdict"].cget("text") == "-" for row in app.rows.values())

    def test_no_em_dashes_anywhere_in_ui_text(self, root):
        import hextol.gui as gui_module
        import inspect

        assert "—" not in inspect.getsource(gui_module)


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY20 = (51, 51, 51)  # channel distance 20.0 from black on the normalized scale


class TestRegionStats:
    """One distance pass, four verdicts; is_match is the oracle they must match."""

    REGIONS = {
        "uniform": [BLACK] * 8,
        "half and half": [BLACK] * 4 + [WHITE] * 4,
        "one stray pixel": [BLACK] * 7 + [WHITE],
        "mostly wrong": [BLACK] * 2 + [WHITE] * 6,
        "spread": [(0, 0, 0), (20, 40, 10), (80, 80, 80), (200, 10, 10), (255, 255, 255)],
    }

    @pytest.mark.parametrize("name", list(REGIONS))
    def test_agrees_with_is_match_for_every_aggregate(self, name):
        from hextol.compare import AGGREGATES, is_match
        from hextol.distance import METHODS
        from hextol.gui import region_stats

        region = self.REGIONS[name]
        target = "#3B82F6"
        for method, fn in METHODS.items():
            dists = [fn(px, (59, 130, 246)) for px in region]
            for tolerance in (0, 1, 5, 10, 25, 50, 99, 100):
                stats = region_stats(dists, tolerance)
                for aggregate in AGGREGATES:
                    assert stats.verdicts[aggregate] == is_match(
                        region, target, tolerance, method, aggregate
                    ), f"{name} / {method} / {aggregate} / tol {tolerance}"

    def test_all_implies_majority_implies_any(self):
        from hextol.distance import euclidean
        from hextol.gui import region_stats

        for region in self.REGIONS.values():
            dists = [euclidean(px, BLACK) for px in region]
            for tolerance in (0, 10, 30, 60, 100):
                v = region_stats(dists, tolerance).verdicts
                assert not v["all"] or v["majority"]
                assert not v["majority"] or v["any"]

    def test_average_can_pass_where_majority_fails(self):
        from hextol.distance import channel
        from hextol.gui import region_stats

        # exactly half at distance 0, half at 20: mean lands on the tolerance,
        # but half is not a majority
        dists = [channel(px, BLACK) for px in [BLACK] * 5 + [GREY20] * 5]
        v = region_stats(dists, 10).verdicts
        assert v["average"] and not v["majority"]

    def test_majority_can_pass_where_average_fails(self):
        from hextol.distance import channel
        from hextol.gui import region_stats

        # 80% perfect, 20% as wrong as possible: the outliers drag the mean past
        # the tolerance while four fifths of the pixels are individually fine
        dists = [channel(px, BLACK) for px in [BLACK] * 8 + [WHITE] * 2]
        v = region_stats(dists, 15).verdicts
        assert v["majority"] and not v["average"]

    def test_empty_region_is_rejected(self):
        from hextol.gui import region_stats

        with pytest.raises(ValueError):
            region_stats([], 10)


class TestSubsample:
    def test_leaves_small_regions_alone(self):
        from hextol.gui import _subsample

        rows = [[BLACK, WHITE], [WHITE, BLACK]]
        assert _subsample(rows, limit=8) is rows

    def test_caps_the_longest_edge(self):
        from hextol.gui import _subsample

        rows = [[BLACK] * 400 for _ in range(200)]
        thinned = _subsample(rows, limit=50)
        assert len(thinned[0]) <= 50 and len(thinned) <= 50

    def test_keeps_real_pixel_values_rather_than_blending(self):
        from hextol.gui import _subsample

        rows = [[BLACK, WHITE] * 50 for _ in range(4)]
        for row in _subsample(rows, limit=10):
            assert all(px in (BLACK, WHITE) for px in row)

    def test_empty_region_is_rejected(self):
        from hextol.gui import _subsample

        with pytest.raises(ValueError):
            _subsample([])


class TestRegionPage:
    def test_builds_the_method_by_aggregate_grid(self, root):
        from hextol.compare import AGGREGATES
        from hextol.distance import METHODS
        from hextol.gui import RegionPage

        app = RegionPage(root)
        assert set(app.rows) == set(METHODS)
        for row in app.rows.values():
            assert set(row["verdicts"]) == set(AGGREGATES)

    def test_columns_cover_every_aggregate_the_library_accepts(self):
        from hextol.compare import AGGREGATES
        from hextol.gui import AGGREGATE_HINTS

        # The GUI orders the columns loosest first rather than reusing the
        # library's order, so this guards the two from drifting apart.
        assert set(AGGREGATE_HINTS) == set(AGGREGATES)

    def test_columns_run_loosest_to_strictest(self):
        from hextol.gui import AGGREGATE_HINTS

        assert list(AGGREGATE_HINTS) == ["any", "majority", "all", "average"]

    def test_no_region_leaves_the_grid_empty(self, root):
        from hextol.gui import RegionPage

        app = RegionPage(root)
        assert app.pixels is None
        assert all(
            pill.cget("text") == "-"
            for row in app.rows.values()
            for pill in row["verdicts"].values()
        )

    def test_uniform_region_matching_the_target_passes_everything(self, root):
        from hextol.gui import RegionPage

        app = RegionPage(root)
        app.set_region([[BLACK] * 4 for _ in range(4)], "test")
        app.target.set("#000000")
        app.tolerance.set(0)
        assert all(
            pill.cget("text") == "MATCH"
            for row in app.rows.values()
            for pill in row["verdicts"].values()
        )
        assert all(row["within"].cget("text") == "100%" for row in app.rows.values())

    def test_aggregates_disagree_on_a_split_region(self, root):
        from hextol.gui import RegionPage

        app = RegionPage(root)
        app.set_region([[BLACK] * 4, [BLACK] * 4, [BLACK] * 4, [WHITE] * 4], "test")
        app.target.set("#000000")
        app.tolerance.set(10)
        verdicts = app.rows["channel"]["verdicts"]
        assert verdicts["any"].cget("text") == "MATCH"
        assert verdicts["majority"].cget("text") == "MATCH"
        assert verdicts["all"].cget("text") == "MISS"
        assert verdicts["average"].cget("text") == "MISS"

    def test_invalid_target_shows_status_not_crash(self, root):
        from hextol.gui import RegionPage

        app = RegionPage(root)
        app.set_region([[BLACK] * 2, [BLACK] * 2], "test")
        app.target.set("#NOTHEX")
        assert "Invalid" in app.status.cget("text")

    def test_empty_region_is_refused_with_a_message(self, root):
        from hextol.gui import RegionPage

        app = RegionPage(root)
        app.set_region([], "test")
        assert app.pixels is None
        assert "empty" in app.status.cget("text")

    def test_oversized_region_is_subsampled_before_judging(self, root):
        from hextol.gui import RegionPage, _ANALYSIS_MAX

        app = RegionPage(root)
        app.set_region([[BLACK] * 500 for _ in range(300)], "test")
        assert len(app.pixels[0]) <= _ANALYSIS_MAX
        assert len(app.pixels) <= _ANALYSIS_MAX

    def test_tolerance_can_be_shared_between_pages(self, root):
        from hextol.gui import ColorPage, RegionPage

        shared = tk.DoubleVar(master=root, value=10)
        compare = ColorPage(root, tolerance=shared)
        region = RegionPage(root, tolerance=shared)
        shared.set(42)
        assert compare.tolerance_label.cget("text") == "42.0"
        assert region.tolerance_label.cget("text") == "42.0"


class TestScreenPickerMath:
    class FakeShot:
        width, height = 200, 100

    def test_scales_logical_to_physical_coords(self):
        from hextol.gui import _scaled_coords

        # screenshot is 200x100 physical, window reports 100x50 logical (2x DPI)
        assert _scaled_coords(self.FakeShot(), 50, 25, 100, 50) == (100, 50)

    def test_clamps_to_image_bounds(self):
        from hextol.gui import _scaled_coords

        assert _scaled_coords(self.FakeShot(), 500, 500, 100, 50) == (199, 99)
        assert _scaled_coords(self.FakeShot(), -5, -5, 100, 50) == (0, 0)


class TestCoreStaysClean:
    def test_import_hextol_does_not_import_gui_or_tkinter(self):
        code = (
            "import sys; import hextol; "
            "bad = [m for m in ('hextol.gui', 'tkinter') if m in sys.modules]; "
            "sys.exit(1 if bad else 0)"
        )
        assert subprocess.run([sys.executable, "-c", code]).returncode == 0
