import pytest

import hextol
from hextol.compare import distances, is_match, match_mask


class FakePilImage:
    """Duck-typed stand-in for a PIL Image (hextol never imports PIL)."""

    def __init__(self, pixels):
        self._pixels = pixels

    def getdata(self):
        return list(self._pixels)


class TestTopLevelImport:
    def test_is_match_exported(self):
        assert hextol.is_match is is_match

    def test_import_pulls_no_heavy_dependencies(self):
        """The flagship import must stay zero-dependency (PLAN.md design principle #1)."""
        import subprocess
        import sys

        code = (
            "import sys; import hextol; "
            "bad = [m for m in ('numpy', 'PIL') if m in sys.modules]; "
            "sys.exit(1 if bad else 0)"
        )
        result = subprocess.run([sys.executable, "-c", code])
        assert result.returncode == 0, "importing hextol pulled in numpy or PIL"


class TestSinglePixel:
    def test_exact_match(self):
        assert is_match("#3B82F6", "#3B82F6", tolerance=0)

    def test_close_match(self):
        assert is_match("#3B82F6", "#3A80F0", tolerance=5)

    def test_far_miss(self):
        assert not is_match("#000000", "#FFFFFF", tolerance=50)

    def test_mixed_input_forms(self):
        assert is_match((59, 130, 246), "#3B82F6", tolerance=0)
        assert is_match("#3B82F6", (59, 130, 246), tolerance=0)

    def test_tolerance_is_inclusive(self):
        # channel distance between these is exactly 25.5 normalized ((65/255)*100)
        d = distances((0, 0, 0), (65, 0, 0), method="channel")
        assert is_match((0, 0, 0), (65, 0, 0), tolerance=d, method="channel")

    def test_returns_plain_bool(self):
        assert isinstance(is_match("#000000", "#000000"), bool)


class TestRegion:
    REGION = [(0, 0, 0), (2, 2, 2), (3, 3, 3), (250, 250, 250)]

    def test_majority_default(self):
        # 3 of 4 pixels match black tightly
        assert is_match(self.REGION, "#000000", tolerance=5)

    def test_all(self):
        assert not is_match(self.REGION, "#000000", tolerance=5, aggregate="all")
        assert is_match([(0, 0, 0), (1, 1, 1)], "#000000", tolerance=5, aggregate="all")

    def test_any(self):
        assert is_match(self.REGION, "#FAFAFA", tolerance=5, aggregate="any")

    def test_average(self):
        # mean distance dragged up by the white pixel; passes at a loose tolerance
        assert is_match(self.REGION, "#000000", tolerance=30, aggregate="average")
        assert not is_match(self.REGION, "#000000", tolerance=5, aggregate="average")

    def test_aggregates_can_disagree(self):
        region = [(0, 0, 0), (0, 0, 0), (255, 255, 255)]
        assert is_match(region, "#000000", tolerance=5, aggregate="majority")
        assert not is_match(region, "#000000", tolerance=5, aggregate="all")

    def test_exact_half_fails_majority(self):
        region = [(0, 0, 0), (255, 255, 255)]
        assert not is_match(region, "#000000", tolerance=5, aggregate="majority")

    def test_hex_strings_in_region(self):
        assert is_match(["#000000", "#010101"], "#000000", tolerance=5, aggregate="all")

    def test_rgba_pixels_alpha_ignored(self):
        assert is_match([(0, 0, 0, 255), (1, 1, 1, 0)], "#000000", tolerance=5, aggregate="all")


class TestDuckTyping:
    def test_pil_like_image(self):
        img = FakePilImage([(0, 0, 0, 255), (2, 2, 2, 255), (1, 1, 1, 255)])
        assert is_match(img, "#000000", tolerance=5, aggregate="all")

    def test_pil_like_grayscale_rejected(self):
        img = FakePilImage([0, 128, 255])
        with pytest.raises(ValueError, match="RGB"):
            is_match(img, "#000000")

    def test_numpy_arrays(self):
        np = pytest.importorskip("numpy")
        single = np.array([59, 130, 246])
        flat = np.array([[0, 0, 0], [2, 2, 2]])
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        assert is_match(single, "#3B82F6", tolerance=0)
        assert is_match(flat, "#000000", tolerance=5, aggregate="all")
        assert is_match(image, "#000000", tolerance=0, aggregate="all")

    def test_numpy_rgba_image(self):
        np = pytest.importorskip("numpy")
        image = np.zeros((2, 2, 4), dtype=np.uint8)
        assert is_match(image, "#000000", tolerance=0, aggregate="all")


class TestDistances:
    def test_single_returns_float(self):
        assert distances("#000000", "#FFFFFF") == pytest.approx(100)

    def test_region_returns_list(self):
        result = distances([(0, 0, 0), (255, 255, 255)], "#000000")
        assert result == [0.0, pytest.approx(100)]

    def test_raw_values(self):
        import math

        assert distances("#000000", "#FFFFFF", normalize=False) == pytest.approx(math.sqrt(3) * 255)
        assert distances((0, 0, 0), (65, 0, 0), method="channel", normalize=False) == 65


class TestMatchMask:
    def test_region(self):
        mask = match_mask([(0, 0, 0), (255, 255, 255)], "#000000", tolerance=5)
        assert mask == [True, False]

    def test_single_gives_length_one(self):
        assert match_mask("#000000", "#000000") == [True]


class TestValidation:
    def test_unknown_method(self):
        with pytest.raises(ValueError, match="valid methods"):
            is_match("#000000", "#000000", method="euclidian")

    def test_unknown_aggregate(self):
        with pytest.raises(ValueError, match="valid aggregates"):
            is_match([(0, 0, 0)], "#000000", aggregate="most")

    def test_negative_tolerance(self):
        with pytest.raises(ValueError, match="tolerance"):
            is_match("#000000", "#000000", tolerance=-1)

    def test_empty_region(self):
        with pytest.raises(ValueError, match="empty"):
            is_match([], "#000000")
