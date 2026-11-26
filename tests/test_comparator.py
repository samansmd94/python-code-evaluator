from evaluator.comparator import compare_results

def test_compare_equal_integers():
    assert compare_results(5, 5) is True


def test_compare_different_integers():
    assert compare_results(5, 10) is False


def test_compare_equal_strings():
    assert compare_results("hello", "hello") is True


def test_comparison_is_exact_by_default():
    assert compare_results(1, 1.0) is True
    assert compare_results(0.1 + 0.2, 0.3) is False


def test_comparison_supports_numeric_tolerance_recursively():
    assert compare_results([1.0, {"value": 2.01}], [1, {"value": 2}], tolerance=0.02)
    assert not compare_results([1.0, 2.1], [1.0, 2.0], tolerance=0.02)


def test_tolerance_keeps_none_and_different_types_distinct():
    assert compare_results(None, None, tolerance=0.1)
    assert not compare_results(None, 0, tolerance=0.1)
    assert not compare_results(True, 1, tolerance=0.1)


def test_negative_tolerance_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="non-negative"):
        compare_results(1, 1, tolerance=-0.1)
