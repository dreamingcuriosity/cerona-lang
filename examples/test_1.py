import io
import sys
from cerona.main import execute

def run_cerona(code: str) -> str:
    """Capture stdout from executing Cerona code."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        execute(code)
        return sys.stdout.getvalue().strip()
    finally:
        sys.stdout = old_stdout

# Basic I/O tests
def test_print():
    output = run_cerona('print ("Hello, Cerona!")')
    assert output == "Hello, Cerona!"

def test_print_number():
    output = run_cerona('print(42)')
    assert output == "42"

# Arithmetic tests
def test_set_and_add():
    code = """
    set x 10
    set y 20
    set sum x + y
    print(sum)
    """
    output = run_cerona(code)
    assert output == "30"

def test_subtraction():
    code = """
    set a 50
    set b 15
    set diff a - b
    print(diff)
    """
    output = run_cerona(code)
    assert output == "35"

def test_multiplication():
    code = """
    set x 7
    set y 6
    set product x * y
    print(product)
    """
    output = run_cerona(code)
    assert output == "42"

def test_division():
    code = """
    set x 100
    set y 4
    set quotient x / y
    print(quotient)
    """
    output = run_cerona(code)
    assert output == "25.0"

# Conditional tests
def test_if_then_print():
    code = """
    set x 5
    if x less 10 then print("small")
    if x greater 10 then print("big")
    """
    output = run_cerona(code)
    assert output == "small"

def test_if_greater():
    code = """
    set score 85
    if score greater 80 then print("passed")
    """
    output = run_cerona(code)
    assert output == "passed"

def test_if_equal():
    code = """
    set x 10
    set y 10
    if x equals y then print("same")
    """
    output = run_cerona(code)
    assert output == "same"

def test_multiple_conditions():
    code = """
    set temp 75
    if temp less 60 then print("cold")
    if temp greater 60 then print("warm")
    if temp greater 80 then print("hot")
    """
    output = run_cerona(code)
    assert "warm" in output

# Complex expression tests
def test_chained_operations():
    code = """
    set a 5
    set b 3
    set c 2
    set result a + b * c
    print(result)
    """
    output = run_cerona(code)
    # Test based on your operator precedence

def test_variable_reassignment():
    code = """
    set counter 0
    set counter counter + 1
    set counter counter + 1
    print(counter)
    """
    output = run_cerona(code)
    assert output == "2"

# Multiple print statements
def test_multiple_prints():
    code = """
    print("Line 1")
    print("Line 2")
    print("Line 3")
    """
    output = run_cerona(code)
    lines = output.split('\n')
    assert len(lines) == 3
    assert lines[0] == "Line 1"
    assert lines[1] == "Line 2"
    assert lines[2] == "Line 3"

# Edge cases
def test_zero_value():
    code = """
    set x 0
    print(x)
    """
    output = run_cerona(code)
    assert output == "0"

def test_negative_numbers():
    code = """
    set x 10
    set y 20
    set neg x - y
    print(neg)
    """
    output = run_cerona(code)
    assert output == "-10"

def test_string_with_spaces():
    output = run_cerona('print("Hello World Test")')
    assert output == "Hello World Test"

# Comparison edge cases
def test_equal_comparison():
    code = """
    set x 100
    if x equals 100 then print("exact")
    """
    output = run_cerona(code)
    assert output == "exact"

def test_boundary_comparison():
    code = """
    set x 10
    if x less 11 then print("yes")
    """
    output = run_cerona(code)
    assert output == "yes"

def test_OOP():
    code = """
    class Counter
        set count 0

        func init initial
            set count initial
        endfunc

        func increment
            set count count + 1
        endfunc

        func get_value
            print(count)
        endfunc
    endclass

    # Create instances
    new Counter c1 0
    new Counter c2 10

    # Use methods
    call c1.increment
    call c1.increment
    call c1.get_value

    call c2.get_value
    """
    output = run_cerona(code)
    assert output == "2\n10"
