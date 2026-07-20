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


class TestComparisonApp:
    def test_builds_and_shows_all_methods(self, root):
        from hextol.distance import METHODS
        from hextol.gui import ComparisonApp

        app = ComparisonApp(root)
        assert set(app.rows) == set(METHODS)

    def test_refresh_computes_verdicts(self, root):
        from hextol.gui import ComparisonApp

        app = ComparisonApp(root)
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
        from hextol.gui import ComparisonApp

        app = ComparisonApp(root)
        app.color_vars["A"].set("#NOTHEX")
        app.refresh()
        assert "Invalid" in app.status.cget("text")
        assert all(row["verdict"].cget("text") == "-" for row in app.rows.values())

    def test_no_em_dashes_anywhere_in_ui_text(self, root):
        import hextol.gui as gui_module
        import inspect

        assert "—" not in inspect.getsource(gui_module)


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
