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

def test_print():
    output = run_cerona('print "Hello, Cerona!"')
    assert output == "Hello, Cerona!"

def test_set_and_add():
    code = """
    set x 10
    set y 20
    set sum x + y
    print sum
    """
    output = run_cerona(code)
    assert output == "30"

def test_if_then_print():
    code = """
    set x 5
    if x less 10 then print "small"
    if x greater 10 then print "big"
    """
    output = run_cerona(code)
    assert output == "small"
