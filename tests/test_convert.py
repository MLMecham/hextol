import pytest

from hextol.convert import (
    hex_to_hsl,
    hex_to_rgb,
    hsl_to_hex,
    rgb_to_hex,
    rgb_to_hsl,
    to_rgb,
)


class TestHexToRgb:
    def test_basic(self):
        assert hex_to_rgb("#3B82F6") == (59, 130, 246)

    def test_no_hash(self):
        assert hex_to_rgb("3B82F6") == (59, 130, 246)

    def test_lowercase(self):
        assert hex_to_rgb("#3b82f6") == (59, 130, 246)

    def test_shorthand_expands_css_style(self):
        assert hex_to_rgb("#3BF") == (0x33, 0xBB, 0xFF)
        assert hex_to_rgb("fff") == (255, 255, 255)

    def test_whitespace_tolerated(self):
        assert hex_to_rgb(" #FFFFFF ") == (255, 255, 255)

    @pytest.mark.parametrize("bad", ["", "#12345", "#GGGGGG", "#12", "12345678", None, 42])
    def test_invalid_raises(self, bad):
        with pytest.raises(ValueError):
            hex_to_rgb(bad)


class TestRgbToHex:
    def test_basic(self):
        assert rgb_to_hex(59, 130, 246) == "#3B82F6"

    def test_uppercase_and_padded(self):
        assert rgb_to_hex(0, 10, 255) == "#000AFF"

    @pytest.mark.parametrize("bad", [(-1, 0, 0), (256, 0, 0), (0.5, 0, 0)])
    def test_invalid_raises(self, bad):
        with pytest.raises(ValueError):
            rgb_to_hex(*bad)


class TestRoundTrip:
    @pytest.mark.parametrize("hex_str", ["#000000", "#FFFFFF", "#3B82F6", "#7F7F7F"])
    def test_hex_rgb_hex(self, hex_str):
        assert rgb_to_hex(*hex_to_rgb(hex_str)) == hex_str

    @pytest.mark.parametrize("hex_str", ["#000000", "#FFFFFF", "#FF0000", "#3B82F6"])
    def test_hex_hsl_hex(self, hex_str):
        assert hsl_to_hex(*hex_to_hsl(hex_str)) == hex_str


class TestHsl:
    def test_red(self):
        h, s, lightness = rgb_to_hsl(255, 0, 0)
        assert (round(h), round(s), round(lightness)) == (0, 100, 50)

    def test_white_has_full_lightness(self):
        assert round(rgb_to_hsl(255, 255, 255)[2]) == 100

    def test_hue_wraps(self):
        assert hsl_to_hex(360, 100, 50) == hsl_to_hex(0, 100, 50)


class TestToRgb:
    def test_hex_passthrough(self):
        assert to_rgb("#3B82F6") == (59, 130, 246)

    def test_tuple(self):
        assert to_rgb((1, 2, 3)) == (1, 2, 3)

    def test_list(self):
        assert to_rgb([1, 2, 3]) == (1, 2, 3)

    def test_rgba_alpha_ignored(self):
        assert to_rgb((1, 2, 3, 255)) == (1, 2, 3)

    def test_integral_floats_accepted(self):
        assert to_rgb((1.0, 2.0, 3.0)) == (1, 2, 3)

    @pytest.mark.parametrize("bad", [(1, 2), (1, 2, 3, 4, 5), (1, 2, 300), (1, 2, 2.5), 42, ("a", "b", "c")])
    def test_invalid_raises(self, bad):
        with pytest.raises(ValueError):
            to_rgb(bad)
