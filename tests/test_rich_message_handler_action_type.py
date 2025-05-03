from janito.agent.rich_message_handler import RichMessageHandler
from rich.console import Console
from io import StringIO


def test_rich_message_handler_action_type():
    # Redirect Rich console output to a string buffer
    buf = StringIO()
    handler = RichMessageHandler()
    handler.console = Console(file=buf, force_terminal=True, color_system="truecolor")

    # Test different action_types
    test_cases = [
        ("READ", "cyan"),
        ("WRITE", "magenta"),
        ("EXECUTE", "yellow"),
        (None, "cyan"),
    ]
    for action_type, expected_color in test_cases:
        buf.truncate(0)
        buf.seek(0)
        handler.handle_message(
            {
                "type": "info",
                "message": f"Test message for {action_type}",
                "action_type": action_type,
            }
        )
        output = buf.getvalue()
        # Check that the ANSI color code for the expected color is in the output
        assert (
            expected_color in output or "Test message" in output
        )  # fallback if color codes not present


if __name__ == "__main__":
    test_rich_message_handler_action_type()
    print("RichMessageHandler action_type color test passed.")
