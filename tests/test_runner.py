from operator import add
import re
from evaluator.runner import run_function

def test_run_function_with_two_arguments():
    def add(a, b):
        return a + b

    result = run_function(add, (2, 3))

    assert result == 5

def test_run_function_with_string_arguments():
    def greet(name):
        return f'Hello, {name}!' 

    result = run_function(greet, ('Sam',))

    assert result == 'Hello, Sam!'
    