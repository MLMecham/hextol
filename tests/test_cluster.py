import pytest

from hextol.cluster import group_similar


class TestGrouping:
    def test_basic_dedupe(self):
        groups = group_similar(["#000000", "#020202", "#FFFFFF"], tolerance=5)
        assert groups == [["#000000", "#020202"], ["#FFFFFF"]]

    def test_order_independent(self):
        colors = ["#FFFFFF", "#020202", "#000000", "#FDFDFD"]
        shuffled = ["#020202", "#FDFDFD", "#FFFFFF", "#000000"]
        assert group_similar(colors, tolerance=5) == group_similar(shuffled, tolerance=5)

    def test_no_chaining_through_intermediates(self):
        # A~B and B~C but A!~C: leader clustering keeps C out rather than
        # chaining all three together
        a, b, c = (0, 0, 0), (30, 30, 30), (60, 60, 60)
        groups = group_similar([c, a, b], tolerance=15, method="channel")
        assert groups == [["#000000", "#1E1E1E"], ["#3C3C3C"]]

    def test_zero_tolerance_groups_exact_duplicates_only(self):
        groups = group_similar(["#000000", "#000000", "#010101"], tolerance=0)
        assert groups == [["#000000", "#000000"], ["#010101"]]

    def test_all_similar_is_one_group(self):
        groups = group_similar(["#100000", "#000010", "#001000"], tolerance=50)
        assert len(groups) == 1

    def test_mixed_input_forms(self):
        groups = group_similar([(0, 0, 0), "#020202"], tolerance=5)
        assert groups == [["#000000", "#020202"]]

    def test_darkest_leader_first(self):
        groups = group_similar(["#FFFFFF", "#000000", "#808080"], tolerance=5)
        assert [g[0] for g in groups] == ["#000000", "#808080", "#FFFFFF"]

    def test_empty_input(self):
        assert group_similar([], tolerance=10) == []

    def test_method_changes_grouping(self):
        # far apart on one channel only: channel judges strictly, euclidean less so
        by_channel = group_similar([(0, 0, 0), (0, 0, 80)], tolerance=20, method="channel")
        by_euclid = group_similar([(0, 0, 0), (0, 0, 80)], tolerance=20, method="euclidean")
        assert len(by_channel) == 2
        assert len(by_euclid) == 1


class TestValidation:
    def test_negative_tolerance(self):
        with pytest.raises(ValueError, match="tolerance"):
            group_similar(["#000000"], tolerance=-1)

    def test_unknown_method(self):
        with pytest.raises(ValueError, match="valid methods"):
            group_similar(["#000000"], method="euclidian")

    def test_bad_color_propagates(self):
        with pytest.raises(ValueError):
            group_similar(["#XYZ"], tolerance=5)
