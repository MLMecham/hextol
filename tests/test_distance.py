import math

import pytest

from hextol.distance import METHODS, channel, euclidean, get_method, weighted

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


class TestNormalizationContract:
    """Every method shares the 0-100 scale: identity -> 0, black vs white -> 100."""

    @pytest.mark.parametrize("name", sorted(METHODS))
    def test_identity_is_zero(self, name):
        assert METHODS[name]((59, 130, 246), (59, 130, 246)) == 0

    @pytest.mark.parametrize("name", sorted(METHODS))
    def test_black_vs_white_is_100(self, name):
        assert METHODS[name](BLACK, WHITE) == pytest.approx(100)

    @pytest.mark.parametrize("name", sorted(METHODS))
    def test_symmetry(self, name):
        a, b = (10, 200, 30), (200, 10, 130)
        assert METHODS[name](a, b) == pytest.approx(METHODS[name](b, a))

    @pytest.mark.parametrize("name", sorted(METHODS))
    def test_range(self, name):
        pairs = [((0, 0, 255), (255, 255, 0)), ((1, 2, 3), (4, 5, 6)), ((255, 0, 0), (0, 255, 255))]
        for a, b in pairs:
            assert 0 <= METHODS[name](a, b) <= 100 + 1e-9

    def test_comparable_magnitudes_across_methods(self):
        """The same pair lands in the same ballpark under every method."""
        a, b = (59, 130, 246), (100, 160, 200)
        values = [METHODS[name](a, b) for name in METHODS]
        assert max(values) - min(values) < 15


class TestKnownValues:
    def test_channel_raw_is_max_abs_diff(self):
        assert channel.raw((10, 20, 30), (10, 25, 90)) == 60

    def test_euclidean_raw(self):
        assert euclidean.raw(BLACK, WHITE) == pytest.approx(math.sqrt(3) * 255)
        assert euclidean.raw((0, 0, 0), (3, 4, 0)) == 5

    def test_weighted_raw_black_white(self):
        assert weighted.raw(BLACK, WHITE) == pytest.approx(255 * math.sqrt(8 + 255 / 256))

    def test_raw_and_normalized_are_proportional(self):
        a, b = (59, 130, 246), (200, 10, 130)
        for fn in METHODS.values():
            assert fn(a, b) == pytest.approx(fn.raw(a, b) / fn.max_raw * 100)


class TestGetMethod:
    def test_lookup(self):
        assert get_method("euclidean") is euclidean

    def test_raw_lookup(self):
        assert get_method("euclidean", raw=True) is euclidean.raw

    def test_unknown_lists_valid_names(self):
        with pytest.raises(ValueError, match="channel, euclidean, weighted"):
            get_method("euclidian")
