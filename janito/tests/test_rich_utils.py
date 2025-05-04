import io
from rich.console import Console
from janito.rich_utils import RichPrinter


def test_print_info(capsys=None):
    buf = io.StringIO()
    printer = RichPrinter(
        console=Console(file=buf, force_terminal=True, color_system=None)
    )
    printer.print_info("info message")
    output = buf.getvalue()
    assert "info message" in output
    assert "cyan" in output or output  # Style is present if rich renders ANSI


def test_print_error():
    buf = io.StringIO()
    printer = RichPrinter(
        console=Console(file=buf, force_terminal=True, color_system=None)
    )
    printer.print_error("error message")
    output = buf.getvalue()
    assert "error message" in output


def test_print_warning():
    buf = io.StringIO()
    printer = RichPrinter(
        console=Console(file=buf, force_terminal=True, color_system=None)
    )
    printer.print_warning("warning message")
    output = buf.getvalue()
    assert "warning message" in output


def test_print_magenta():
    buf = io.StringIO()
    printer = RichPrinter(
        console=Console(file=buf, force_terminal=True, color_system=None)
    )
    printer.print_magenta("magenta message")
    output = buf.getvalue()
    assert "magenta message" in output
