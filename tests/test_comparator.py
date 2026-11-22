from evaluator.comparator import compare_results

def test_compare_equal_integers():
    assert compare_results(5, 5) is True


def test_compare_different_integers():
    assert compare_results(5, 10) is False


def test_compare_equal_strings():
    assert compare_results("hello", "hello") is True