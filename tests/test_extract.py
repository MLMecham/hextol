import pytest

np = pytest.importorskip("numpy")
PIL_Image = pytest.importorskip("PIL.Image")

from hextol import is_match  # noqa: E402
from hextol.extract import dominant_color  # noqa: E402


def solid_block(color, n):
    return np.tile(np.array(color, dtype=np.uint8), (n, 1))


class TestDominantColor:
    def test_two_clean_clusters_ordered_by_size(self):
        pixels = np.vstack([solid_block((255, 0, 0), 100), solid_block((0, 0, 255), 30)])
        assert dominant_color(pixels, k=2) == ["#FF0000", "#0000FF"]

    def test_fewer_unique_colors_than_k(self):
        pixels = np.vstack([solid_block((255, 0, 0), 10), solid_block((0, 0, 255), 5)])
        assert dominant_color(pixels, k=5) == ["#FF0000", "#0000FF"]

    def test_single_color_image(self):
        assert dominant_color(solid_block((59, 130, 246), 50), k=3) == ["#3B82F6"]

    def test_noisy_cluster_lands_near_true_color(self):
        rng = np.random.default_rng(42)
        base = solid_block((200, 40, 40), 500).astype(np.int16)
        noisy = np.clip(base + rng.integers(-10, 11, base.shape), 0, 255).astype(np.uint8)
        [result] = dominant_color(noisy, k=1)
        assert is_match(result, (200, 40, 40), tolerance=5)

    def test_deterministic_by_default(self):
        rng = np.random.default_rng(7)
        pixels = rng.integers(0, 256, (2000, 3)).astype(np.uint8)
        assert dominant_color(pixels, k=3) == dominant_color(pixels, k=3)

    def test_subsampling_large_input(self):
        pixels = np.vstack([solid_block((0, 255, 0), 30_000), solid_block((0, 0, 0), 5_000)])
        result = dominant_color(pixels, k=2, sample_size=1_000)
        assert result[0] == "#00FF00"


class TestInputForms:
    def test_image_shaped_array(self):
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        image[:, :5] = (255, 0, 0)
        assert set(dominant_color(image, k=2)) == {"#FF0000", "#000000"}

    def test_rgba_alpha_ignored(self):
        image = np.zeros((4, 4, 4), dtype=np.uint8)
        image[..., 3] = 255
        assert dominant_color(image, k=1) == ["#000000"]

    def test_pil_image(self):
        img = PIL_Image.new("RGB", (8, 8), (59, 130, 246))
        assert dominant_color(img, k=1) == ["#3B82F6"]

    def test_pil_non_rgb_mode_converted(self):
        img = PIL_Image.new("P", (8, 8))
        assert dominant_color(img, k=1) == ["#000000"]

    def test_file_path(self, tmp_path):
        path = tmp_path / "swatch.png"
        PIL_Image.new("RGB", (6, 6), (0, 255, 0)).save(path)
        assert dominant_color(str(path), k=1) == ["#00FF00"]
        assert dominant_color(path, k=1) == ["#00FF00"]


class TestValidation:
    @pytest.mark.parametrize("bad_k", [0, -1, 2.5])
    def test_bad_k(self, bad_k):
        with pytest.raises(ValueError, match="k must be"):
            dominant_color(np.zeros((4, 3), dtype=np.uint8), k=bad_k)

    def test_empty_image(self):
        with pytest.raises(ValueError, match="no pixels"):
            dominant_color(np.zeros((0, 3), dtype=np.uint8))

    def test_bad_shape(self):
        with pytest.raises(ValueError, match="shape"):
            dominant_color(np.zeros((4, 2), dtype=np.uint8))

    def test_unsupported_type(self):
        with pytest.raises(ValueError, match="Unsupported"):
            dominant_color(42)


class TestCoreStaysClean:
    def test_import_hextol_does_not_import_extract(self):
        import subprocess
        import sys

        code = (
            "import sys; import hextol; "
            "sys.exit(1 if 'hextol.extract' in sys.modules else 0)"
        )
        assert subprocess.run([sys.executable, "-c", code]).returncode == 0
