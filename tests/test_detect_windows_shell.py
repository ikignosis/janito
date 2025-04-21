from janito.agent.profile_manager import detect_windows_shell


def test_detect_windows_shell():
    shell = detect_windows_shell()
    print(f"Detected shell: {shell}")
    assert isinstance(shell, str)
    assert shell  # Should not be empty


if __name__ == "__main__":
    test_detect_windows_shell()
