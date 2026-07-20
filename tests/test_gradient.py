import pytest

from hextol.convert import hex_to_hsl
from hextol.gradient import build_gradient


class TestBasics:
    def test_endpoints_included(self):
        g = build_gradient("#3B82F6", "#FF0000", 5)
        assert g[0] == "#3B82F6"
        assert g[-1] == "#FF0000"

    def test_step_count(self):
        assert len(build_gradient("#000000", "#FFFFFF", 7)) == 7

    def test_two_steps_is_just_endpoints(self):
        assert build_gradient("#000000", "#FFFFFF", 2) == ["#000000", "#FFFFFF"]

    def test_midpoint_gray(self):
        assert build_gradient("#000000", "#FFFFFF", 3)[1] == "#808080"

    def test_rgb_tuples_accepted(self):
        g = build_gradient((0, 0, 0), (255, 255, 255), 3)
        assert g == ["#000000", "#808080", "#FFFFFF"]

    def test_same_color_both_ends(self):
        assert build_gradient("#3B82F6", "#3B82F6", 4) == ["#3B82F6"] * 4


class TestHslSpace:
    def test_endpoints_preserved(self):
        g = build_gradient("#FF0000", "#00FF00", 5, space="hsl")
        assert g[0] == "#FF0000"
        assert g[-1] == "#00FF00"

    def test_hue_takes_shorter_arc(self):
        # red (h=0) to magenta (h=300): shorter arc goes backwards through 330,
        # not forwards through 150 (which would be green-ish)
        mid = build_gradient("#FF0000", "#FF00FF", 3, space="hsl")[1]
        assert mid == "#FF0080"

    def test_hsl_midpoint_stays_vivid_where_rgb_goes_muddy(self):
        # blue -> yellow: RGB midpoint is pure gray, HSL midpoint keeps full saturation
        rgb_mid = build_gradient("#0000FF", "#FFFF00", 3, space="rgb")[1]
        hsl_mid = build_gradient("#0000FF", "#FFFF00", 3, space="hsl")[1]
        assert rgb_mid == "#808080"
        assert round(hex_to_hsl(hsl_mid)[1]) == 100


class TestValidation:
    @pytest.mark.parametrize("bad_steps", [1, 0, -3, 2.5])
    def test_bad_steps(self, bad_steps):
        with pytest.raises(ValueError, match="steps"):
            build_gradient("#000000", "#FFFFFF", bad_steps)

    def test_bad_space(self):
        with pytest.raises(ValueError, match="valid spaces"):
            build_gradient("#000000", "#FFFFFF", 3, space="lab")

    def test_bad_color_propagates(self):
        with pytest.raises(ValueError):
            build_gradient("#XYZ", "#FFFFFF", 3)
