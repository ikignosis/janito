import subprocess
import sys


def test_capital_of_france():
    """Basic test: Ask janito for the capital of France and check the answer."""
    # This assumes janito/cli/main.py can be run as a CLI tool
    result = subprocess.run(
        [sys.executable, "-m", "janito", "What is the capital of France?"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = result.stdout.lower()
    assert "paris" in output, f"Expected 'paris' in output, got: {output}"


if __name__ == "__main__":
    test_capital_of_france()
    print("Test passed.")
